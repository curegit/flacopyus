# TODO: Drop dependency on private modules
from paranoia.utils.filesys import itreemap, treemap, tree

import time
import os
import shutil
import subprocess as sp
from pathlib import Path
from contextlib import nullcontext
from threading import RLock
from concurrent.futures import ThreadPoolExecutor, Future
from collections.abc import Callable, Iterable
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn, MofNCompleteColumn

import rich.console

console = rich.console.Console(stderr=True)


def filter_split[T](predicate: Callable[[T], bool], iterable: Iterable[T]):
    trues: list[T] = []
    falses: list[T] = []
    for item in iterable:
        if predicate(item):
            trues.append(item)
        else:
            falses.append(item)
    return trues, falses


class Error:
    pass


def main(src: Path, dest: Path, *, bitrate: int=128, wav: bool, delete: bool = False, delete_excluded: bool = False, copy_exts: list[str] = [], fix_case: bool = False):
    encode = build_opusenc_func(bitrate=bitrate, )
    delete = delete or delete_excluded

    copy_exts = [e.lower() for e in copy_exts]

    extmap = {"flac": "opus"}
    if wav:
        extmap |= {"wav": "opus"}

    for k in extmap:
        if k in copy_exts:
            raise ValueError()

    ds: list[Path] = []
    if delete:
        if dest.exists():
            if delete_excluded:
                ds = tree(dest)
            else:
                ds = tree(dest, ext=["opus", *copy_exts])
    will_del_dict: dict[Path, bool] = {p: True for p in ds}

    def fix_case_file(path: Path):
        physical = path.resolve(strict=True)
        if physical.name != path.name:
            physical.rename(path)

    def cp_main(s: Path, d: Path):
        stat_s = s.stat()
        s_ns = stat_s.st_mtime_ns
        # TODO: --bitrate 変更を検知できるようにする()-- しない。マニュアル対応の方が増分エンコードできて良い
        # TODO: 送り先がフォルダで衝突しているとき
        if not d.exists() or s_ns != d.stat().st_mtime_ns:
            cp = encode(s, d)
            copy_mod(s_ns, d)
        if fix_case:
            fix_case_file(d)
        # TODO: Thread safe?
        will_del_dict[d] = False
        return True

    def cp_i(pool: ThreadPoolExecutor, pending: list[tuple[Path, Future[bool]]]):
        def f(s: Path, d: Path):
            future = pool.submit(cp_main, s, d)
            pending.append((s, future))

        return f

    poll = 0.1
    concurrency = os.cpu_count()
    pending: list[tuple[Path, Future[bool]]] = []
    copy_list = []

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        try:
            treemap(cp_i(executor, pending), src, dest=dest, extmap=extmap, mkdir=True, mkdir_empty=False, fix_case=fix_case, progress=False)
            # Finish remaining tasks
            progress_display = Progress(TextColumn("[bold]{task.description}"), BarColumn(), MofNCompleteColumn(), TaskProgressColumn(), TimeRemainingColumn(), console=console)
            task = progress_display.add_task("Processing", total=len(pending))
            with progress_display:
                while pending:
                    time.sleep(poll)
                    done, pending = filter_split(lambda x: x[1].done(), pending)
                    progress_display.update(task, advance=len(done), refresh=True)
        except KeyboardInterrupt:
            # Exit quickly when interrupted
            executor.shutdown(cancel_futures=True)
            raise

    def ff_(s: Path, d: Path):
        # TODO: 送り先がフォルダで衝突しているとき
        if not d.exists():
            shutil.copyfile(s, d)
            copy_mod(s, d)
        if s.stat().st_mtime_ns != d.stat().st_mtime_ns or s.stat().st_size != d.stat().st_size:
            shutil.copyfile(s, d)
            copy_mod(s, d)
            if fix_case:
                fix_case_file(d)
        will_del_dict[d] = False
        return True

    def cp(pool, pending):
        def f(s, d):
            future = pool.submit(ff_, s, d)
            pending.append((s, future))

        return f

    pending: list[tuple[Path, Future[bool]]] = []
    with ThreadPoolExecutor(max_workers=1) as executor_cp:
        try:
            treemap(cp(executor_cp, pending), src, dest=dest, extmap=copy_exts, mkdir=True, mkdir_empty=False, progress=False)
            progress_display = Progress(TextColumn("[bold]{task.description}"), BarColumn(), MofNCompleteColumn(), TaskProgressColumn(), TimeRemainingColumn(), console=console)
            task = progress_display.add_task("Copying", total=len(pending))
            with progress_display:
                while pending:
                    time.sleep(poll)
                    done, pending = filter_split(lambda x: x[1].done(), pending)
                    for d, fu in done:
                        # Unwrap for collecting exceptions
                        fu.result()
                    progress_display.update(task, advance=len(done), refresh=True)
        except KeyboardInterrupt:
            # Exit quickly when interrupted
            executor.shutdown(cancel_futures=True)
            raise

    for p, is_deleted in will_del_dict.items():
        if is_deleted:
            p.unlink()

    del_dir = True
    purge_dir = True

    try_del = set()

    if del_dir or purge_dir:
        found_emp = None
        while found_emp is not False:
            found_emp = False
            for d, s, is_empty in itreemap(lambda d, s: not any(d.iterdir()), dest, src, file=False, directory=True, mkdir=False):
                if is_empty:
                    if purge_dir or not s.exists() or not s.is_dir():
                        if d not in try_del:
                            found_emp = True
                            try_del.add(d)
                            d.rmdir()
                            break
                        # TODO: 広いファイル名空間へのマッピング時にフォルダがのこる可能性あり
                        pass

    return 0



def which(cmd: str) -> str:
    match shutil.which(cmd):
        case None:
            raise RuntimeError(f"Command not found: {cmd}")
        case path:
            return path



def build_opusenc_func(*, bitrate:int, use_lock: bool = True):
    opusenc_bin = which("opusenc")
    cmd_line = [opusenc_bin, "--bitrate", str(bitrate), "-", "-"]
    lock = RLock()

    def encode(src_file: Path, dest_opus_file: Path):
        buf = None
        with open(src_file, "rb") as src_fp:
            if use_lock:
                with lock:
                    buf = src_fp.read()
                in_stream = None
            else:
                in_stream = src_fp
            cp = sp.run(cmd_line, text=False, input=buf, stdin=in_stream, capture_output=True, check=True)
        with lock if use_lock else nullcontext():
            with open(dest_opus_file, "wb") as dest_fp:
                dest_fp.write(cp.stdout)
        return cp

    return encode


def copy_mod(s: int | Path, d: Path):
    if isinstance(s, int):
        ns_s = s
    else:
        ns_s = s.stat().st_mtime_ns
    os.utime(d, ns=(time.time_ns(), ns_s))

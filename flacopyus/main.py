# TODO: Drop dependency on private modules
from paranoia.utils.filesys import itreemap, treemap, tree

import time
import os
import shutil
import subprocess as sp
from pathlib import Path
from contextlib import nullcontext
from functools import cache
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


def main(src: Path, dest: Path, *, delete: bool = False, delete_excluded: bool = False, copy_exts: list[str] | bool = False):
    # copy_extensions: list[str] | None = "opus"

    ds: list[Path] = []
    if dest.exists():
        if delete_excluded or copy_exts is True:
            ds = tree(dest)
        else:
            # TODO: fixme
            ds = tree(dest, ext=copy_exts)
    will_del_dict: dict[Path, bool] = {p: True for p in ds}

    def cp_main(s: Path, d: Path):
        stat_s = s.stat()
        s_ns = stat_s.st_mtime_ns
        # TODO: --bitrate 変更を検知できるようにする()-- しない。マニュアル対応の方が増分エンコードできて良い
        # TODO: 送り先がフォルダで衝突しているとき
        if not d.exists() or s_ns != d.stat().st_mtime_ns:
            cp = opusenc_func()(s, d)
            with open(d, "wb") as f:
                f.write(cp.stdout)
            copy_mod(s_ns, d)
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
            treemap(cp_i(executor, pending), src, dest=dest, extmap={"flac": "opus"}, mkdir=True, mkdir_empty=False, progress=False)
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
        if not d.exists():
            shutil.copy2(s, d)
        if s.stat().st_mtime_ns != d.stat().st_mtime_ns or s.stat().st_size != d.stat().st_size:
            shutil.copy2(s, d)
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
            treemap(cp(executor_cp, pending), src, dest=dest, extmap=["mp3", "m4a"], mkdir=True, mkdir_empty=False, progress=False)
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

    return 0


def build_cmds(*cmdline_or_arglist: str | Iterable[str]) -> list[str]:
    args = []
    for arg in cmdline_or_arglist:
        match arg:
            case str() as cmdline:
                cmds = cmdline.split()
                args.extend(cmds)
            case Iterable():
                args.extend(arg)
            case _:
                raise ValueError(f"Invalid argument: {arg}")
    return args


def which(cmd: str) -> str:
    match shutil.which(cmd):
        case None:
            raise RuntimeError(f"Command not found: {cmd}")
        case path:
            return path


@cache
def opusenc_func(l: bool = True):
    lock = RLock()
    opusenc = which("opusenc")
    cmd = build_cmds([opusenc], "--bitrate 128 - -")

    def r(s: Path, d: Path):
        i = None
        with open(s, "rb") as to_stdin:
            if l:
                with lock:
                    i = to_stdin.read()
                sd = None
            else:
                sd = to_stdin
            cp = sp.run(cmd, text=False, input=i, stdin=sd, capture_output=True, check=True)
        with lock if l else nullcontext():
            with open(d, "wb") as fp:
                fp.write(cp.stdout)
        return cp

    return r


def copy_mod(s: int | Path, d: Path):
    if isinstance(s, int):
        ns_s = s
    else:
        ns_s = s.stat().st_mtime_ns
    os.utime(d, ns=(time.time_ns(), ns_s))

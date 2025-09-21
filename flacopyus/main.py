# TODO: Drop dependency on private modules
from paranoia.utils.spr import which, build_treemap_spfunc
from paranoia.utils.filesys import itreemap, treemap, tree

import time
import os
import shutil
from pathlib import Path
from functools import cache
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

    def cp_i(pool, copy_list, pending: list[tuple[Path, Future[bool]]]):
        def f(s: Path, d: Path):
            if s.suffix.lower() in [".mp3", ".m4a"]:

                copy_list.append((s, d))
                return
                #pending.append((s, future))
                #return future



            future = pool.submit(cp_main, s, d)
            pending.append((s, future))
            #return future

        return f

    poll = 0.1
    concurrency = os.cpu_count()
    pending: list[tuple[Path, Future[bool]]] = []
    copy_list = []

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        treemap(cp_i(executor, copy_list, pending), src, dest=dest, extmap={"flac": "opus", "m4a": "m4a", "mp3": "mp3"}, mkdir=True, mkdir_empty=False, raises_on_error=True, progress=False)
        # Finish remaining tasks
        progress_display = Progress(TextColumn("[bold]{task.description}"), BarColumn(), MofNCompleteColumn(), TaskProgressColumn(), TimeRemainingColumn(), console=console)
        task = progress_display.add_task("Processing", total=len(pending))
        with progress_display:
            while pending:
                time.sleep(poll)
                done, pending = filter_split(lambda x: x[1].done(), pending)
                progress_display.update(task, advance=len(done), refresh=True)

    with ThreadPoolExecutor(max_workers=1) as executor_cp:
        def cp(s,d):
            if s.stat().st_mtime_ns != d.stat().st_mtime_ns or s.stat().st_size != d.stat().st_size:
                shutil.copy2(s, d)
            return True
        for s,d in copy_list:
            future = executor_cp.submit(cp, s, d)



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
                        if  d not  in try_del:
                            found_emp = True
                            try_del.add(d)
                            d.rmdir()
                            break

    return 0


@cache
def opusenc_func():
    opusenc = which("opusenc")
    return build_treemap_spfunc([opusenc], "--bitrate 128 - -", emulate_redirect_stdin=True, emulate_redirect_stdout=True, capture_output=True)


def copy_mod(s: int | Path, d: Path):
    if isinstance(s, int):
        ns_s = s
    else:
        ns_s = s.stat().st_mtime_ns
    os.utime(d, ns=(time.time_ns(), ns_s))

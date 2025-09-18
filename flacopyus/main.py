# TODO: Drop dependency on private modules
from paranoia.utils.spr import which, build_treemap_spfunc
from paranoia.utils.filesys import treemap

import time
import os
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



def main(src: Path, dest: Path):
    poll = 0.1
    concurrency = os.cpu_count()
    pending: list[tuple[Path, Future[bool]]] = []
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        treemap(cp_i(executor, pending), src, dest=dest, extmap={"flac": "opus"}, raises_on_error=True, progress=False)
        # Finish remaining tasks
        progress_display = Progress(TextColumn("[bold]{task.description}"), BarColumn(), MofNCompleteColumn(), TaskProgressColumn(), TimeRemainingColumn(), console=console)
        task = progress_display.add_task("Processing", total=len(pending))
        with progress_display:
            while pending:
                time.sleep(poll)
                done, pending = filter_split(lambda x: x[1].done(), pending)
                progress_display.update(task, advance=len(done), refresh=True)
    return 0

@cache
def opusenc_func():
    opusenc = which("opusenc")
    return build_treemap_spfunc([opusenc], "--bitrate 128 - -", emulate_redirect_stdin=True, emulate_redirect_stdout=True, capture_output=True)


def cp_main(s: Path, d: Path):
    stat_s = s.stat()
    s_ns = stat_s.st_mtime_ns
    # TODO: bitrate 変更を検知できるようにする
    # TODO: 送り先がフォルダで衝突しているとき
    if not d.exists() or s_ns != d.stat().st_mtime_ns:
        cp = opusenc_func()(s, d)
        with open(d, "wb") as f:
            f.write(cp.stdout)
        copy_mod(s_ns, d)
    return True




def cp_i(pool, pending: list[tuple[Path, Future[bool]]]):
    def f(s: Path, d: Path):
        future = pool.submit(cp_main, s, d)
        pending.append((s, future))
        return future
    return f



def copy_mod(s: int | Path, d: Path):
    if isinstance(s, int):
        ns_s = s
    else:
        ns_s = s.stat().st_mtime_ns
    os.utime(d, ns=(time.time_ns(), ns_s))

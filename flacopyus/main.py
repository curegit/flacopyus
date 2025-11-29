import os
import shutil
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, Future
from .opus import OpusOptions, build_opusenc_func
from .funs import filter_split
from .spr import get_opusenc
from .stdio import reprint, progress_bar, error_console
from .filesys import itreemap, itree, copy_mtime, sync_disk


def main(
    src: Path,
    dest: Path,
    *,
    force: bool = False,
    opus_options: OpusOptions = OpusOptions(),
    re_encode: bool = False,
    wav: bool = False,
    delete: bool = False,
    delete_excluded: bool = False,
    copy_exts: list[str] = [],
    fix_case: bool = False,
    encoding_concurrency: bool | int | None = None,
    allow_parallel_io: bool = False,
    copying_concurrency: int = 1,
    opusenc_executable: str | None = None,
    prefer_external: bool = False,
    verbose: bool = False,
) -> int:
    with get_opusenc(opusenc_executable=opusenc_executable, prefer_external=prefer_external) as opusenc_binary:
        encode = build_opusenc_func(
            opusenc_binary,
            options=opus_options,
            use_lock=(not allow_parallel_io),
        )

        delete = delete or delete_excluded

        copy_exts = [e.lower() for e in copy_exts]

        extmap = {"flac": "opus"}
        if wav:
            extmap |= {"wav": "opus"}

        for k in extmap:
            if k in copy_exts:
                raise ValueError()

        # TODO: Check SRC and DEST tree overlap for safety
        # TODO: Check some flacs are in SRC to avoid swapped SRC DEST disaster (unlimit with -f)
        if not force:
            pass

        ds: list[Path] = []
        if delete:
            if dest.exists(follow_symlinks=False):
                if delete_excluded:
                    ds = list(itree(dest))
                else:
                    ds = list(itree(dest, ext=["opus", *copy_exts]))
        will_del_dict: dict[Path, bool] = {p: True for p in ds}

        def fix_case_file(path: Path):
            physical = path.resolve(strict=True)
            if physical.name != path.name:
                physical.rename(path)

        def cp_main(s: Path, d: Path):
            stat_s = s.stat()
            s_ns = stat_s.st_mtime_ns
            # TODO: remove symlink
            if d.is_symlink():
                pass
            # TODO: handle case where destination is a folder and conflicts
            if re_encode or not d.exists(follow_symlinks=False) or s_ns != d.stat().st_mtime_ns:
                if verbose:
                    reprint(str(s))
                cp = encode(s, d)
                copy_mtime(s_ns, d)
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
        match encoding_concurrency:
            case bool() as b:
                concurrency = max(1, 1 if (cpus := os.cpu_count()) is None else cpus - 1) if b else 1
            case int() as n:
                concurrency = n if n > 0 else max(1, 1 if (cpus := os.cpu_count()) is None else cpus - 1)
            case None:
                concurrency = 1
            case _:
                raise ValueError()
        pending: list[tuple[Path, Future[bool]]] = []

        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            try:
                for _ in itreemap(cp_i(executor, pending), src, dest=dest, extmap=extmap, mkdir=True, mkdir_empty=False, fix_case=fix_case, progress=False):
                    pass
                # Finish remaining tasks
                progress_display = progress_bar(error_console)
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

    def copyfile_fsync(s: Path, d: Path):
        with open(s, "rb") as s_fp:
            with open(d, "wb") as d_fp:
                shutil.copyfileobj(s_fp, d_fp)
                d_fp.flush()
                sync_disk(d_fp)

    def ff_(s: Path, d: Path):
        # TODO: remove symlink
        if d.is_symlink():
            pass
        # TODO: handle case where destination is a folder and conflicts
        if not d.exists():
            copyfile_fsync(s, d)
            copy_mtime(s, d)
        if s.stat().st_mtime_ns != d.stat().st_mtime_ns or s.stat().st_size != d.stat().st_size:
            copyfile_fsync(s, d)
            copy_mtime(s, d)
            if fix_case:
                fix_case_file(d)
        will_del_dict[d] = False
        return True

    def cp(pool, pending):
        def f(s, d):
            future = pool.submit(ff_, s, d)
            pending.append((s, future))

        return f

    pending_cp: list[tuple[Path, Future[bool]]] = []
    with ThreadPoolExecutor(max_workers=copying_concurrency) as executor_cp:
        try:
            for _ in itreemap(cp(executor_cp, pending_cp), src, dest=dest, extmap=copy_exts, mkdir=True, mkdir_empty=False, progress=False):
                pass
            progress_display = progress_bar(error_console)
            task = progress_display.add_task("Copying", total=len(pending_cp))
            with progress_display:
                while pending_cp:
                    time.sleep(poll)
                    done, pending_cp = filter_split(lambda x: x[1].done(), pending_cp)
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

    # TODO: parameterize
    del_dir = True
    purge_dir = True

    try_del = set()

    if del_dir or purge_dir:
        found_emp = None
        while found_emp is not False:
            found_emp = False
            for d, s, is_empty in itreemap(lambda d, s: not any(d.iterdir()), dest, src, file=False, directory=True, mkdir=False):
                if is_empty:
                    # TODO: remove symlink
                    if purge_dir or not s.exists() or not s.is_dir():
                        if d not in try_del:
                            found_emp = True
                            try_del.add(d)
                            d.rmdir()
                            break
                        # TODO: 広いファイル名空間へのマッピング時にフォルダがのこる可能性あり
                        pass

    return 0

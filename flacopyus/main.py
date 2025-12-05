import os
import shutil
import time
from pathlib import Path
from threading import RLock
from concurrent.futures import ThreadPoolExecutor, Future
from .opus import OpusOptions, build_opusenc_func
from .funs import filter_split
from .spr import get_opusenc
from .stdio import reprint, progress_bar, error_console
from .filesys import itreemap, itree, copy_mtime, sync_disk, hashfile


def main(
    src: Path,
    dest: Path,
    *,
    force: bool = False,
    opus_options: OpusOptions = OpusOptions(),
    re_encode: bool = False,
    wav: bool = False,
    aiff: bool = False,
    delete: bool = False,
    delete_excluded: bool = False,
    delete_dir: bool = False,
    purge_dir: bool = False,
    modtime_window: float = 0.0,
    checksum: bool = False,
    copy_exts: list[str] = [],
    fix_case: bool = False,
    encoding_concurrency: bool | int | None = None,
    allow_parallel_io: bool = False,
    copying_concurrency: int = 1,
    opusenc_executable: Path | None = None,
    prefer_external: bool = False,
    verbose: bool = False,
) -> int:
    progress_display = progress_bar(error_console)
    with progress_display:
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
            if aiff:
                extmap |= {"aif": "opus"}
                extmap |= {"aiff": "opus"}
            for k in extmap:
                if k in copy_exts:
                    raise ValueError(f"Unable to copy .{k} files, which are supposed to be encoded.")

            if not src.exists(follow_symlinks=True) or not src.is_dir(follow_symlinks=True):
                raise ValueError(f"Source directory {src} does not exist or is not a directory.")

            # Check some FLAC/WAV/AIFF are in SRC to avoid swapped SRC DEST disaster (unlimit with -f)
            if not force:
                # Check if there are any FLAC/WAV/AIFF files in src
                has_flac_etc = False
                for _ in itree(
                    src, ext=[*extmap.keys()], recursive=True, file=True, directory=False, follow_symlinks=True, include_broken_symlinks=False, error_broken_symlinks=False, raises_on_error=False
                ):
                    has_flac_etc = True
                    break
                if not has_flac_etc:
                    raise RuntimeError(f"No {', '.join(extmap.keys())} files found in source directory {src}. Did you swap SRC and DEST? Use --force to continue anyway.")

            dest_files_before: list[Path] = []
            if delete:
                if dest.exists(follow_symlinks=False):
                    if delete_excluded:
                        dest_files_before = list(itree(dest, follow_symlinks=True, include_broken_symlinks=True, error_broken_symlinks=False))
                    else:
                        dest_files_before = list(itree(dest, ext=[*list(set(extmap.values())), *copy_exts], follow_symlinks=True, include_broken_symlinks=True, error_broken_symlinks=False))
            would_delete_flags: dict[Path, bool] = {p: True for p in dest_files_before}
            lock_delete_flags = RLock()

            # int stands for modification time in nanoseconds
            # float stands for modification time in seconds
            def is_updated(s: Path | int | float, d: Path):
                match s:
                    case int() as ns:
                        return abs(d.stat().st_mtime_ns - ns) <= modtime_window * 1e9
                    case float() as sec:
                        return abs(d.stat().st_mtime - sec) <= modtime_window
                    case Path() as p:
                        return is_updated(p.stat().st_mtime_ns, d)
                    case _:
                        raise TypeError()

            def remove_symlink_from_dest(path: Path):
                if delete:
                    path.unlink()
                    with lock_delete_flags:
                        if path in would_delete_flags:
                            would_delete_flags.pop(path)
                else:
                    raise FileExistsError(f"Destination {path} is a symlink but deletion is not allowed. Use --delete or --delete-excluded to remove it.")

            def remove_folder_from_dest(folder: Path):
                if not delete:
                    raise FileExistsError(f"Destination {folder} is a folder but deletion is not allowed. Use --delete or --delete-excluded to remove it.")
                for p in itree(folder, follow_symlinks=False, include_broken_symlinks=True, error_broken_symlinks=False):
                    if p.is_symlink():
                        remove_symlink_from_dest(p)
                        continue
                    with lock_delete_flags:
                        if p in would_delete_flags:
                            p.unlink()
                            would_delete_flags.pop(p)
                        else:
                            raise FileExistsError(f"Destination {p} is not in the deletion list. Try --delete-excluded to remove it.")
                shutil.rmtree(folder)

            def fix_case_file(path: Path):
                physical = path.resolve(strict=True)
                if physical.name != path.name:
                    physical.rename(path)

            def encode_task(s: Path, d: Path):
                is_for_encoding = False
                stat_s = s.stat()
                mtime_sec_or_ns = stat_s.st_mtime if modtime_window > 0 else stat_s.st_mtime_ns
                if d.is_symlink():
                    remove_symlink_from_dest(d)
                if d.is_dir():
                    remove_folder_from_dest(d)
                if re_encode or not d.exists(follow_symlinks=False) or not is_updated(mtime_sec_or_ns, d):
                    is_for_encoding = True
                    with lock_for_encoding:
                        for_encoding.append(s)
                    if verbose:
                        reprint(f"{s} -> {d} (Encoding)")
                    encode(s, d)
                    copy_mtime(mtime_sec_or_ns, d)
                if fix_case:
                    fix_case_file(d)
                with lock_delete_flags:
                    would_delete_flags[d] = False
                return is_for_encoding

            def cp_i(pool: ThreadPoolExecutor, pending: list[tuple[Path, Future[bool]]]):
                def f(s: Path, d: Path):
                    future = pool.submit(encode_task, s, d)
                    pending.append((s, future))

                return f

            pending: list[tuple[Path, Future[bool]]] = []
            for_encoding: list[Path] = []
            lock_for_encoding = RLock()
            poll = 0.1
            match encoding_concurrency:
                case bool() as b:
                    concurrency = max(1, 1 if (cpus := os.cpu_count()) is None else cpus - 1) if b else 1
                case int() as n:
                    concurrency = n if n > 0 else max(1, 1 if (cpus := os.cpu_count()) is None else cpus - 1)
                case None:
                    concurrency = 1
                case _:
                    raise TypeError()
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                task = progress_display.add_task("Traversing", total=len(pending))
                try:
                    for i, _ in enumerate(
                        itreemap(
                            cp_i(executor, pending),
                            src,
                            dest=dest,
                            extmap=extmap,
                            mkdir=True,
                            mkdir_empty=False,
                            fix_case=fix_case,
                            follow_symlinks=True,
                            include_broken_symlinks=False,
                            error_broken_symlinks=False,
                            progress=False,
                        )
                    ):
                        if i % 42 == 0:
                            progress_display.update(task, total=len(pending), refresh=True)
                    # Finish remaining tasks
                    with lock_for_encoding:
                        task_e = progress_display.add_task("Encoding", total=len(for_encoding))
                    done_encoding_count = 0
                    while pending:
                        time.sleep(poll)
                        done, pending = filter_split(lambda x: x[1].done(), pending)
                        for _, fut in done:
                            # Unwrap first for collecting exceptions
                            really_encoded = fut.result()
                            if really_encoded:
                                done_encoding_count += 1
                        progress_display.update(task, advance=len(done), refresh=True)
                        progress_display.update(task_e, completed=done_encoding_count, total=len(for_encoding), refresh=True)
                except (KeyboardInterrupt, Exception):
                    # Exit quickly when interrupted/failed
                    executor.shutdown(cancel_futures=True)
                    raise

        def copyfile_fsync(s: Path, d: Path):
            with open(s, "rb") as s_fp:
                with open(d, "wb") as d_fp:
                    shutil.copyfileobj(s_fp, d_fp)
                    d_fp.flush()
                    sync_disk(d_fp)

        def ff_(s: Path, d: Path):
            if d.is_symlink():
                remove_symlink_from_dest(d)
            if d.is_dir():
                remove_folder_from_dest(d)
            if not d.exists():
                copyfile_fsync(s, d)
                copy_mtime(s, d)
                if verbose:
                    reprint(f"{s} -> {d} (New file)")
            else:
                mtime_sec_or_ns = s.stat().st_mtime if modtime_window > 0 else s.stat().st_mtime_ns
                updated = s.stat().st_size == d.stat().st_size and is_updated(mtime_sec_or_ns, d)
                if checksum:
                    updated_checksum = hashfile(s) == hashfile(d)
                    if updated_checksum and not updated:
                        updated = True
                        copy_mtime(mtime_sec_or_ns, d)
                    if not updated_checksum:
                        updated = False
                if not updated:
                    copyfile_fsync(s, d)
                    copy_mtime(mtime_sec_or_ns, d)
                    if verbose:
                        reprint(f"{s} -> {d} (Updated file)")
            if fix_case:
                fix_case_file(d)
            with lock_delete_flags:
                would_delete_flags[d] = False
            return True

        def cp(pool, pending):
            def f(s, d):
                future = pool.submit(ff_, s, d)
                pending.append((s, future))

            return f

        pending_cp: list[tuple[Path, Future[bool]]] = []
        with ThreadPoolExecutor(max_workers=copying_concurrency) as executor_cp:
            try:
                for _ in itreemap(
                    cp(executor_cp, pending_cp),
                    src,
                    dest=dest,
                    extmap=copy_exts,
                    mkdir=True,
                    mkdir_empty=False,
                    follow_symlinks=True,
                    include_broken_symlinks=False,
                    error_broken_symlinks=False,
                    progress=False,
                ):
                    pass
                task_c = progress_display.add_task("Copying", total=len(pending_cp))

                while pending_cp:
                    time.sleep(poll)
                    done, pending_cp = filter_split(lambda x: x[1].done(), pending_cp)
                    for d, fu in done:
                        # Unwrap for collecting exceptions
                        fu.result()
                    progress_display.update(task_c, advance=len(done), refresh=True)
            except (KeyboardInterrupt, Exception):
                # Exit quickly when interrupted/failed
                executor.shutdown(cancel_futures=True)
                raise

        # Deletion phase
        for p, would_be_deleted in would_delete_flags.items():
            if would_be_deleted:
                p.unlink()

        # Directory deletion phase
        del_dir = delete_dir or purge_dir
        try_del: set[Path] = set()
        if del_dir:
            found_emp: bool | None = None
            while found_emp is not False:
                found_emp = False
                for d, s, is_empty in itreemap(
                    lambda d, s: not any(d.iterdir()),
                    dest,
                    src,
                    file=False,
                    directory=True,
                    mkdir=False,
                    follow_symlinks=True,
                    include_broken_symlinks=False,
                    error_broken_symlinks=False,
                    progress=False,
                ):
                    if is_empty:
                        if d.is_symlink():
                            if d not in try_del:
                                found_emp = True
                                try_del.add(d)
                                d.unlink()
                                break
                        if purge_dir or not s.exists() or not s.is_dir():
                            if d not in try_del:
                                found_emp = True
                                try_del.add(d)
                                d.rmdir()
                                break

    return 0

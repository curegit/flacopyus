import os
import shutil
import io
import time
import functools
import contextlib
import rich.console
from pathlib import Path
from collections.abc import Generator, Callable
from .funs import greedy
from .stdio import progress_bar, error_console


@functools.cache
def fsync_func() -> Callable[[int], None]:
    # Available on Unix
    if fdatasync := getattr(os, "fdatasync", None):
        return fdatasync
    return os.fsync


def sync_disk(fd_like: io.IOBase | int, /):
    fd = fd_like if isinstance(fd_like, int) else fd_like.fileno()
    fsync_func()(fd)


# int stands for modification time in nanoseconds
# float stands for modification time in seconds
def copy_mtime(src: int | float | Path, dest: Path, /):
    match src:
        case int() as ns:
            atime_ns = time.time_ns()
            os.utime(dest, ns=(atime_ns, ns))
        case float() as sec:
            atime = time.time()
            os.utime(dest, times=(atime, sec))
        case Path() as p:
            mtime_ns = p.stat().st_mtime_ns
            atime_ns = time.time_ns()
            os.utime(dest, ns=(atime_ns, mtime_ns))
        case _:
            raise TypeError()


def itree(
    path: Path | str = Path("."),
    *,
    ext: str | list[str] | None = None,
    recursive: bool = True,
    file: bool = True,
    directory: bool = False,
    follow_symlinks: bool = False,
    include_broken_symlinks: bool = False,
    error_broken_symlinks: bool = True,
    raises_on_error: bool = True,
    error_list: list[Exception] | None = None,
) -> Generator[Path, None, list[Exception]]:
    exceptions_list: list[Exception] = [] if error_list is None else error_list
    for _, p, _ in itreemap(
        greedy,
        path,
        path,
        extmap=ext,
        recursive=recursive,
        file=file,
        directory=directory,
        copy_filtered_files=False,
        mkdir=False,
        follow_symlinks=follow_symlinks,
        include_broken_symlinks=include_broken_symlinks,
        error_broken_symlinks=error_broken_symlinks,
        progress=False,
        raises_on_error=raises_on_error,
        error_list=exceptions_list,
    ):
        yield p
    return exceptions_list


def itreemap[T](
    func: Callable[[Path, Path], T],
    /,
    path: Path | str,
    dest: Path | str,
    *,
    dry: bool = False,
    extmap: str | list[str] | dict[str, str] | None = None,
    recursive: bool = True,
    file: bool = True,
    directory: bool = False,
    copy_filtered_files: bool = False,
    copy_ext: str | list[str] | None = None,
    mkdir: bool = True,
    mkdir_empty: bool = True,
    fix_case: bool = True,
    follow_symlinks: bool = False,
    include_broken_symlinks: bool = False,
    error_broken_symlinks: bool = True,
    raises_on_error: bool = True,
    error_list: list[Exception] | None = None,
    progress: bool | None = None,
    console: rich.console.Console | None = None,
    progress_label: str = "Processing",
    progress_copying_label: str = "Copying",
    verbose: bool = False,
) -> Generator[tuple[Path, Path, T], None, list[Exception]]:
    if console is None:
        console = error_console

    exceptions_list: list[Exception] = [] if error_list is None else error_list

    copy_exts = [copy_ext] if isinstance(copy_ext, str) else copy_ext
    exts = list(extmap.keys()) if isinstance(extmap, dict) else [extmap] if isinstance(extmap, str) else extmap
    if exts is not None:
        exts = [e.lower() for e in exts]
    if isinstance(path, str):
        path = Path(path)
    if isinstance(dest, str):
        dest = Path(dest)
    if progress is None:
        progress = console.is_terminal
    if dry:
        progress = False

    def eprint(*objects: object):
        console.print(*(str(x) for x in objects))

    def error_handler(e: Exception):
        exceptions_list.append(e)
        if raises_on_error:
            raise e
        else:
            fn = getattr(e, "filename", None)
            if fn is not None:
                eprint(fn, e)
            else:
                eprint(e)

    def dry_run(path: Path, dest: Path):
        eprint(path, "->", dest)

    def dry_run_dir(path: Path, dest: Path):
        eprint(path, "->", dest, "(dir)")

    def dry_run_copy(path: Path, dest: Path):
        eprint(path, "->", dest, "(copy)")

    def dry_run_mkdir(dest: Path):
        eprint(dest, "(mkdir)")

    if not path.is_dir():
        raise ValueError(f"Path is not a directory: {path}")

    task = None
    copy_task = None
    total_copy = 0
    progress_display = None
    if progress:
        total = sum(
            1
            for _ in itree(
                path,
                ext=exts,
                recursive=recursive,
                file=file,
                directory=directory,
                follow_symlinks=follow_symlinks,
                include_broken_symlinks=include_broken_symlinks,
                error_broken_symlinks=error_broken_symlinks,
                raises_on_error=raises_on_error,
            )
        )
        progress_display = progress_bar(console=console)
        task = progress_display.add_task(progress_label, total=total)
        if copy_filtered_files:
            copy_task = progress_display.add_task(progress_copying_label, total=None)

    with contextlib.nullcontext() if progress_display is None else progress_display:
        for rootpath, dirnames, filenames in path.walk(top_down=True, on_error=error_handler, follow_symlinks=follow_symlinks):
            relatives = rootpath.relative_to(path, walk_up=False)
            dest_rootpath = dest / relatives
            dirnames_copy = [*dirnames]
            if not recursive:
                while dirnames:
                    dirnames.pop()
            applypaths = []
            copypaths = []
            applydirs = []
            for f in filenames:
                filepath = rootpath / f
                # 壊れたシンボリックリンク
                if not filepath.exists(follow_symlinks=True):
                    if error_broken_symlinks:
                        try:
                            raise FileNotFoundError(f"Broken symlink: {filepath}")
                        except Exception as e:
                            error_handler(e)
                    if not include_broken_symlinks:
                        continue
                if file:
                    # follow_symlinks=False のとき、ディレクトリへのリンクが混入する
                    if filepath.is_dir():
                        if directory:
                            applydirs.append(filepath)
                        continue
                    if filepath.suffix:
                        assert filepath.suffix[0] == os.extsep
                        ext = filepath.suffix[1:]
                    else:
                        ext = filepath.suffix
                        assert ext == ""
                    if exts is not None and ext.lower() not in exts:
                        if copy_filtered_files:
                            if copy_exts is None or ext.lower() in copy_exts:
                                copypaths.append((filepath, f, ext))
                    else:
                        applypaths.append((filepath, f, ext))
            if directory:
                for d in dirnames_copy:
                    applydirs.append(rootpath / d)
            if mkdir or copypaths:
                if (applypaths or copypaths or applydirs) or mkdir_empty:
                    if dry:
                        dry_run_mkdir(dest_rootpath)
                    else:
                        if verbose:
                            dry_run_mkdir(dest_rootpath)
                        try:
                            dest_rootpath.mkdir(parents=True, exist_ok=True)
                        except Exception as e:
                            error_handler(e)
                        if fix_case:
                            cur_root = rootpath
                            cur_dest_root = dest
                            for part in relatives.parts:
                                cur_root = cur_root / part
                                cur_dest_root = cur_dest_root / part
                                try:
                                    if cur_dest_root.is_symlink():
                                        cur_dest_root.rename(cur_dest_root.absolute())
                                        continue
                                    physical = cur_dest_root.resolve(strict=True)
                                    if physical.name != cur_dest_root.name:
                                        physical.rename(cur_dest_root.absolute())
                                except Exception as e:
                                    error_handler(e)

            for applypath, name, ext in applypaths:
                if isinstance(extmap, dict):
                    extmap_lower = {k.lower(): v for k, v in extmap.items()}
                    new_ext = extmap_lower[ext.lower()]
                else:
                    new_ext = ext
                destpath = (dest_rootpath / name).with_suffix(os.extsep + new_ext if new_ext else "")
                if dry:
                    dry_run(applypath, destpath)
                else:
                    if verbose:
                        dry_run(applypath, destpath)
                    try:
                        res = func(applypath, destpath)
                    except Exception as e:
                        error_handler(e)
                    else:
                        if progress_display is not None and task is not None:
                            progress_display.update(task, advance=1)
                        yield applypath, destpath, res
            for copypath, name, _ in copypaths:
                destpath = dest_rootpath / name
                if dry:
                    dry_run_copy(copypath, destpath)
                else:
                    if verbose:
                        dry_run_copy(copypath, destpath)
                    try:
                        shutil.copy2(copypath, destpath, follow_symlinks=False)
                        if fix_case:
                            physical = destpath.resolve(strict=True)
                            if destpath.name != physical.name:
                                physical.rename(destpath.absolute())
                    except Exception as e:
                        error_handler(e)
                    else:
                        if progress_display is not None and copy_task is not None:
                            progress_display.update(copy_task, advance=1)
                    finally:
                        total_copy += 1
            for applydir in applydirs:
                destdir = dest_rootpath / applydir
                if dry:
                    dry_run_dir(applydir, destdir)
                else:
                    if verbose:
                        dry_run_dir(applydir, destdir)
                    try:
                        res = func(applydir, destdir)
                    except Exception as e:
                        error_handler(e)
                    else:
                        if progress_display is not None and task is not None:
                            progress_display.update(task, advance=1)
                        yield applydir, destdir, res

        if progress_display is not None and copy_task is not None:
            progress_display.update(copy_task, total=total_copy)

    return exceptions_list

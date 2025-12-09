import shutil
import platform
from pathlib import Path
from contextlib import AbstractContextManager, nullcontext
from .assets import use_opusenc_binary_windows
from .stdio import reprint, red


def which(cmd: str) -> str:
    match shutil.which(cmd):
        case None:
            raise RuntimeError(f"Command not found: `{cmd}`")
        case path:
            return path


def get_opusenc(*, opusenc_executable: Path | None, prefer_external: bool = False, verbose: bool = False) -> AbstractContextManager[Path]:
    if opusenc_executable is not None:
        if verbose:
            reprint(f"Using specified opusenc executable: '{opusenc_executable}'")
        try:
            return nullcontext[Path](opusenc_executable.resolve(strict=True))
        except Exception:
            reprint(red(f"`opusenc` executable not found: '{opusenc_executable}'."))
            raise
    if not prefer_external:
        # This does not distinguish between x86 and ARM64 Windows.
        # But it sounds OK as Windows has x86 emulation for ARM64.
        if platform.system().lower() == "windows":
            if verbose:
                reprint("Using bundled opusenc binary for Windows")
            return use_opusenc_binary_windows()
    try:
        if verbose:
            reprint("Using external opusenc binary in PATH")
        return nullcontext(Path(which("opusenc")))
    except Exception:
        reprint(red("`opusenc` executable not found.\n\nPlease ensure opus-tools package is installed and available in the PATH environment variable."))
        raise

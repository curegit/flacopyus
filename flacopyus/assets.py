import importlib.resources
from pathlib import Path
from contextlib import AbstractContextManager
from collections.abc import Iterator

from . import __spec__ as spec

root = importlib.resources.files(spec.parent if spec is not None else __package__)


def use_opusenc_binary_windows() -> AbstractContextManager[Path]:
    return importlib.resources.as_file(root / "bin" / "opusenc.exe")


def get_test_streams() -> Iterator[AbstractContextManager[Path]]:
    for name in ("system-shutdown.wav", "drum-loop.flac"):
        yield importlib.resources.as_file(root / "audio" / name)

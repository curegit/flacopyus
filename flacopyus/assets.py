import importlib.resources

from . import __spec__ as spec

root = importlib.resources.files(spec.parent if spec is not None else __package__)


def use_opusenc_binary_windows():
    return importlib.resources.as_file(root / "bin" / "opusenc.exe")

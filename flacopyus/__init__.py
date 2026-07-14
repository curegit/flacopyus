__version__ = "0.4.0"


def pyinstaller_hooks_dir():
    from pathlib import Path

    return [str(Path(__file__).with_name("pyinstaller").resolve())]

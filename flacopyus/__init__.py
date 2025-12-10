__version__ = "0.3.4"


def pyinstaller_hooks_dir():
    from pathlib import Path

    return [str(Path(__file__).with_name("pyinstaller").resolve())]

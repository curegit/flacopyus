from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from .main import main as main_func

from pathlib import Path

import sys

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def main(argv: list[str] | None = None) -> int:
    from . import __version__ as version

    try:
        parser = ArgumentParser(prog="flacopyus", allow_abbrev=False, formatter_class=ArgumentDefaultsHelpFormatter, description="")
        parser.add_argument("-v", "--version", action="version", version=version)
        parser.add_argument("src", metavar="SRC", type=str, help="source directory")
        parser.add_argument("dest", metavar="DEST", type=str, help="destination directory")
        args = parser.parse_args(argv)
        return main_func(Path(args.src), Path(args.dest))

    except KeyboardInterrupt:
        eprint("KeyboardInterrupt")
        exit_code = 128 + 2
        return exit_code

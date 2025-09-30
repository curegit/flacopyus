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
        parser.add_argument("-b", "--bitrate", metavar="KBPS", type=int, help="")
        parser.add_argument("--wav", action="store_true", help="")
        # group = parser.add_mutually_exclusive_group()
        # group.add_argument("--copy", )
        # group.add_argument("--copy-all", )
        group = parser.add_mutually_exclusive_group()
        group.add_argument("--delete", action="store_true", help="")
        group.add_argument("--delete-excluded", action="store_true", help="")
        parser.add_argument("-P", "--parallel-encoding", metavar="N", type=int, help="")
        parser.add_argument("--allow-parallel-io", action="store_true", help="")
        parser.add_argument("--parallel-copy", metavar="N", type=int, help="")
        parser.add_argument("--fix-case", action="store_true", help="")
        args = parser.parse_args(argv)
        return main_func(
            src=Path(args.src),
            dest=Path(args.dest),
            wav=args.wav,
            delete=(args.delete or args.delete_excluded),
            delete_excluded=args.delete_excluded,
        )

    except KeyboardInterrupt:
        eprint("KeyboardInterrupt")
        exit_code = 128 + 2
        return exit_code

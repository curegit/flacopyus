from pathlib import Path
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from .main import main as main_func
from .stdio import eprint


def opus_bitrate(kbps: str):
    b = int(kbps)
    if 6 <= b <= 256:
        return b
    raise ValueError()


def main(argv: list[str] | None = None) -> int:
    from . import __version__ as version

    try:
        parser = ArgumentParser(prog="flacopyus", allow_abbrev=False, formatter_class=ArgumentDefaultsHelpFormatter, description="Mirror your FLAC audio library to a portable lossy Opus version")
        parser.add_argument("-v", "--version", action="version", version=version)
        parser.add_argument("src", metavar="SRC", type=str, help="source directory")
        parser.add_argument("dest", metavar="DEST", type=str, help="destination directory")
        parser.add_argument("-b", "--bitrate", metavar="KBPS", type=opus_bitrate, default=128, help="")
        parser.add_argument("--wav", action="store_true", help="")
        parser.add_argument("--copy", metavar="EXT", nargs="+", action="extend", help="mirror files whose extension is .EXT (case-insensitive)")
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
            bitrate=args.bitrate,
            wav=args.wav,
            delete=(args.delete or args.delete_excluded),
            delete_excluded=args.delete_excluded,
            copy_exts=([] if args.copy is None else args.copy),
            fix_case=args.fix_case,
        )

    except KeyboardInterrupt:
        eprint("KeyboardInterrupt")
        exit_code = 128 + 2
        return exit_code

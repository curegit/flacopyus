from pathlib import Path
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter, SUPPRESS
from .main import main as main_func, OpusOptions, BitrateMode, LowBitrateTuning, Downmix
from .stdio import eprint
from .args import uint, natural, opus_bitrate, some_string


def main(argv: list[str] | None = None) -> int:
    from . import __version__ as version

    try:
        parser = ArgumentParser(
            prog="flacopyus",
            allow_abbrev=False,
            formatter_class=ArgumentDefaultsHelpFormatter,
            description="Mirror your FLAC audio library to a portable lossy Opus version",
            epilog="A '--' is usable to terminate option parsing so remaining arguments are treated as positional arguments.",
        )
        parser.add_argument("-v", "--version", action="version", version=version)
        parser.add_argument("src", metavar="SRC", type=some_string, help="source directory containing FLAC files")
        parser.add_argument("dest", metavar="DEST", type=some_string, help="destination directory saving Opus files")

        opus_group = parser.add_argument_group(
            "Opus encoding options",
            description="Note that changing these options will NOT trigger re-encoding of existing Opus files so that the change will affect incrementally. Use '--re-encode' to recreate all Opus files.",
        )
        opus_group.add_argument("-b", "--bitrate", metavar="KBPS", type=opus_bitrate, default=128, help="target bitrate in kbps of Opus files (integer in 6-256)")
        group = opus_group.add_mutually_exclusive_group()
        group.add_argument("--vbr", dest="bitrate_mode", action="store_const", const=BitrateMode.VBR, default=BitrateMode.VBR, help="use Opus variable bitrate mode")
        group.add_argument("--cbr", dest="bitrate_mode", action="store_const", const=BitrateMode.CBR, default=SUPPRESS, help="use Opus constrained variable bitrate mode")
        group.add_argument("--hard-cbr", dest="bitrate_mode", action="store_const", const=BitrateMode.HardCBR, default=SUPPRESS, help="use Opus hard constant bitrate mode")
        group = opus_group.add_mutually_exclusive_group()
        group.add_argument("--music", action="store_true", help="force Opus encoder to tune low bitrates for music")
        group.add_argument("--speech", action="store_true", help="force Opus encoder to tune low bitrates for speech")
        group = opus_group.add_mutually_exclusive_group()
        group.add_argument("--downmix-mono", action="store_true", help="downmix to mono")
        group.add_argument("--downmix-stereo", action="store_true", help="downmix to stereo (if having more than 2 channels)")

        mirroring_group = parser.add_argument_group("mirroring options")
        mirroring_group.add_argument("--re-encode", action="store_true", help="force re-encoding of all Opus files")
        mirroring_group.add_argument("--wav", action="store_true", help="also encode WAV files to Opus files")
        mirroring_group.add_argument("-c", "--copy", metavar="EXT", type=some_string, nargs="+", action="extend", help="copy files whose extension is .EXT (case-insensitive) from SRC to DEST")
        group = mirroring_group.add_mutually_exclusive_group()
        group.add_argument("--delete", action="store_true", help="delete any files in DEST that are not in SRC")
        group.add_argument("--delete-excluded", action="store_true", help="delete any files in DEST that are not in SRC")
        mirroring_group.add_argument("--fix-case", action="store_true", help="fix file/directory name cases to match the source directory (for filesystems that are case-insensitive)")

        concurrency_group = parser.add_argument_group("concurrency options")
        concurrency_group.add_argument("-P", "--parallel-encoding", metavar="THREADS", type=uint, nargs="?", help="enable parallel encoding with THREADS threads [THREADS = max(1, number of CPU cores - 1)]")
        concurrency_group.add_argument("--allow-parallel-io", action="store_true", help="disable mutual exclusion for disk I/O operations during parallel encoding (not recommended for Hard Disk drives)")
        concurrency_group.add_argument("--parallel-copy", metavar="THREADS", type=natural, default=1, help="concurrency of copy operations")

        args = parser.parse_args(argv)
        return main_func(
            src=Path(args.src),
            dest=Path(args.dest),
            opus_options=OpusOptions(
                bitrate=args.bitrate,
                bitrate_mode=args.bitrate_mode,
                low_bitrate_tuning=(LowBitrateTuning.Music if args.music else LowBitrateTuning.Speech if args.speech else None),
                downmix=(Downmix.Mono if args.downmix_mono else Downmix.Stereo if args.downmix_stereo else None),
            ),
            re_encode=args.re_encode,
            wav=args.wav,
            copy_exts=([] if args.copy is None else args.copy),
            delete=(args.delete or args.delete_excluded),
            delete_excluded=args.delete_excluded,
            fix_case=args.fix_case,
            encoding_concurrency=args.parallel_encoding,
            allow_parallel_io=args.allow_parallel_io,
            copying_concurrency=args.parallel_copy,
        )

    except KeyboardInterrupt:
        eprint("KeyboardInterrupt")
        exit_code = 128 + 2
        return exit_code

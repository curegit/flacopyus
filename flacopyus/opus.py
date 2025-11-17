import subprocess as sp
from pathlib import Path
from enum import StrEnum
from dataclasses import dataclass
from contextlib import nullcontext
from threading import RLock
from .filesys import sync_disk


class BitrateMode(StrEnum):
    VBR = "--vbr"
    CBR = "--cbr"
    HardCBR = "--hard-cbr"


class LowBitrateTuning(StrEnum):
    Music = "--music"
    Speech = "--speech"


class Downmix(StrEnum):
    Mono = "--downmix-mono"
    Stereo = "--downmix-stereo"


@dataclass(kw_only=True, frozen=True)
class OpusOptions:
    bitrate: int = 128
    bitrate_mode: BitrateMode = BitrateMode.VBR
    low_bitrate_tuning: LowBitrateTuning | None = None
    downmix: Downmix | None = None


def build_opusenc_func(opusenc_executable: Path, /, options: OpusOptions, *, use_lock: bool = True):
    cmd_line = [str(opusenc_executable)]
    cmd_line.append(["--bitrate", str(options.bitrate)])
    cmd_line.append(options.bitrate_mode.value)
    if options.low_bitrate_tuning is not None:
        cmd_line.append(options.low_bitrate_tuning.value)
    if options.downmix is not None:
        cmd_line.append(options.downmix.value)
    cmd_line.extend(["-", "-"])

    lock = RLock()

    def encode(src_file: Path, dest_opus_file: Path):
        buf = None
        with open(src_file, "rb") as src_fp:
            if use_lock:
                with lock:
                    buf = src_fp.read()
                in_stream = None
            else:
                in_stream = src_fp
            cp = sp.run(cmd_line, text=False, input=buf, stdin=in_stream, capture_output=True, check=True)
        with lock if use_lock else nullcontext():
            with open(dest_opus_file, "wb") as dest_fp:
                dest_fp.write(cp.stdout)
                dest_fp.flush()
                sync_disk(dest_fp)
        return cp

    return encode

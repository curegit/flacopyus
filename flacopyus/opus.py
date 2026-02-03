import subprocess as sp
from io import BytesIO
from pathlib import Path
from enum import StrEnum, unique
from dataclasses import dataclass
from contextlib import nullcontext
from threading import RLock
from .filesys import sync_disk
from typing import final


@final
@unique
class BitrateMode(StrEnum):
    VBR = "--vbr"
    CBR = "--cbr"
    HardCBR = "--hard-cbr"


@final
@unique
class LowBitrateTuning(StrEnum):
    Music = "--music"
    Speech = "--speech"


@final
@unique
class Downmix(StrEnum):
    Mono = "--downmix-mono"
    Stereo = "--downmix-stereo"


@final
@dataclass(kw_only=True, frozen=True, slots=True)
class OpusOptions:
    bitrate: int = 128
    bitrate_mode: BitrateMode = BitrateMode.VBR
    low_bitrate_tuning: LowBitrateTuning | None = None
    downmix: Downmix | None = None


def build_opusenc_func(opusenc_executable: Path, /, options: OpusOptions, *, use_lock: bool = True):
    cmd_line = [str(opusenc_executable)]
    cmd_line.extend(["--bitrate", str(options.bitrate)])
    cmd_line.append(options.bitrate_mode.value)
    if options.low_bitrate_tuning is not None:
        cmd_line.append(options.low_bitrate_tuning.value)
    if options.downmix is not None:
        cmd_line.append(options.downmix.value)
    cmd_line.extend(["-", "-"])

    lock = RLock()

    def encode(src_file: Path, dest_opus_file: Path | None, /):
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
            with BytesIO() if dest_opus_file is None else open(dest_opus_file, "wb") as dest_fp:
                length = dest_fp.write(cp.stdout)
                if not isinstance(dest_fp, BytesIO):
                    dest_fp.flush()
                    sync_disk(dest_fp)
        return length

    return encode

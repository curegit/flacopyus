from pathlib import Path
from .spr import get_opusenc
from .opus import OpusOptions, build_opusenc_func
from .assets import get_test_streams
from .stdio import rprint, green


def main(
    *,
    opusenc_executable: Path | None = None,
    prefer_external: bool = False,
    verbose: bool = False,
) -> int:
    with get_opusenc(opusenc_executable=opusenc_executable, prefer_external=prefer_external, verbose=True) as opusenc_binary:
        encode = build_opusenc_func(
            opusenc_binary,
            OpusOptions(),
        )
        rprint(f"Opus encoder found: {opusenc_binary}")
        rprint("Testing encode...")
        for src in get_test_streams():
            with src as src_file:
                length = encode(src_file, None)
                if verbose:
                    rprint(f"{src_file} -> {length} bytes Opus")
                assert length
    rprint(green("Test completed successfully"))
    return 0

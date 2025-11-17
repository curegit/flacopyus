from .spr import get_opusenc
from .opus import OpusOptions, build_opusenc_func


def main(
    *,
    opusenc_executable: str | None = None,
    prefer_external: bool = False,
    verbose: bool = False,
) -> int:
    # TODO: summary result
    with get_opusenc( opusenc_executable=opusenc_executable, prefer_external=prefer_external) as opusenc_binary:
        encode = build_opusenc_func(
            opusenc_binary,
            OpusOptions(),
        )
        # TODO: test encode
        pass
    return 0

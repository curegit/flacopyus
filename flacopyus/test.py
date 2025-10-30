from .opus import OpusOptions, build_opusenc_func


def main(
    *,
    verbose: bool = False,
) -> int:
    f = build_opusenc_func(OpusOptions())
    return 0

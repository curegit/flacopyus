from .opus import OpusOptions, build_opusenc_func


def main(
    *,
    opus_options: OpusOptions = OpusOptions(),
    verbose: bool = False,
) -> int:
    f = build_opusenc_func(opus_options)
    return 0

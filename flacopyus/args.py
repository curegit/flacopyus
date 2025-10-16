def uint(string: str):
    value = int(string)
    if value >= 0:
        return value
    raise ValueError()


def natural(string: str):
    value = int(string)
    if value > 0:
        return value
    raise ValueError()


def opus_bitrate(kbps: str):
    b = int(kbps)
    if 6 <= b <= 256:
        return b
    raise ValueError()


def nonempty(string: str):
    if string:
        return string
    else:
        raise ValueError()

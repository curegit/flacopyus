from math import isfinite


def uint(string: str) -> int:
    value = int(string)
    if value >= 0:
        return value
    raise ValueError()


def natural(string: str) -> int:
    value = int(string)
    if value > 0:
        return value
    raise ValueError()


def real(string: str) -> float:
    value = float(string)
    if isfinite(value):
        return value
    raise ValueError()


def ufloat(string: str) -> float:
    value = real(string)
    if value >= 0:
        return value
    raise ValueError()


def opus_bitrate(kbps: str) -> int:
    b = int(kbps)
    if 6 <= b <= 256:
        return b
    raise ValueError()


def some_string(string: str) -> str:
    if string:
        return string
    else:
        raise ValueError()

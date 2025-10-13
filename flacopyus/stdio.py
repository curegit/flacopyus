from  rich.console import Console

from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn, MofNCompleteColumn

import rich
import rich.text
import rich.console
from types import EllipsisType

type StrLike = str | bytes | bool | int | float | complex | BaseException | EllipsisType | None

type StyledText = tuple[str, str]

console = rich.console.Console()
error_console = rich.console.Console(stderr=True)


def print(*objects: object, sep: str = " ", end: str = "\n"):
    rprint(*(str(x) for x in objects), sep=sep, end=end)


def eprint(*objects: object, sep: str = " ", end: str = "\n"):
    reprint(*(str(x) for x in objects), sep=sep, end=end)


def rprint(*strlikes: StyledText | StrLike, sep: str | None = " ", end: str = "\n", stderr: bool = False, **kwargs):
    str_list: list[str | StyledText] = list(s if isinstance(s, tuple | str) else str(s) for s in strlikes)
    if sep:
        seps = [sep] * (len(str_list) - 1)
        strs = str_list + seps
        strs[::2] = str_list
        strs[1::2] = seps
    else:
        strs = str_list
    t = rich.text.Text.assemble(*strs, end="")
    if stderr:
        error_console.print(t, end=end, **kwargs)
    else:
        console.print(t, end=end, **kwargs)


def reprint(*strlikes: StyledText | StrLike, sep: str | None = " ", end="\n", **kwargs):
    rprint(*strlikes, sep=sep, end=end, stderr=True, **kwargs)


def styled_text(s: object, /, color: str, *, bold: bool = False) -> StyledText:
    return (str(s), f"bold {color}" if bold else color)


def red(s: object, /, *, bold: bool = False) -> StyledText:
    return styled_text(s, "red", bold=bold)


def yellow(s: object, /, *, bold: bool = False) -> StyledText:
    return styled_text(s, "yellow", bold=bold)


def green(s: object, /, *, bold: bool = False) -> StyledText:
    return styled_text(s, "green", bold=bold)


def blue(s: object, /, *, bold: bool = False) -> StyledText:
    return styled_text(s, "blue", bold=bold)


def cyan(s: object, /, *, bold: bool = False) -> StyledText:
    return styled_text(s, "cyan", bold=bold)


def magenta(s: object, /, *, bold: bool = False) -> StyledText:
    return styled_text(s, "magenta", bold=bold)



def progress_bar(console: Console = error_console):
    return Progress(TextColumn("[bold]{task.description}"), BarColumn(), MofNCompleteColumn(), TaskProgressColumn(), TimeRemainingColumn(), console=console)


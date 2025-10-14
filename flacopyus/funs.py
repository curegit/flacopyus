from collections.abc import Callable, Iterable


def greedy(*args, **kwargs):
    return greedy


def filter_split[T](predicate: Callable[[T], bool], iterable: Iterable[T]):
    trues: list[T] = []
    falses: list[T] = []
    for item in iterable:
        if predicate(item):
            trues.append(item)
        else:
            falses.append(item)
    return trues, falses

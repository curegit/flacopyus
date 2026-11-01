from collections.abc import Callable, Iterable


def greedy(*args, **kwargs):
    return greedy


def icount[T](xs: Iterable[T], /) -> int:
    """Count items in an iterable, including ones that are not sized.

    >>> icount([1, 2, 3])
    3
    >>> icount("ab")
    2
    >>> icount([])
    0
    >>> xs = iter([1, 2])
    >>> icount(xs)
    2
    >>> icount(xs)
    0
    """
    return sum(1 for _ in xs)


def filter_split[T](predicate: Callable[[T], bool], iterable: Iterable[T]):
    """Split an iterable into items that match a predicate and those that do not.

    Order within each group is preserved.

    >>> filter_split(lambda n: n % 2 == 0, range(5))
    ([0, 2, 4], [1, 3])
    >>> filter_split(bool, [0, 1, "", "a"])
    ([1, 'a'], [0, ''])
    >>> filter_split(lambda n: n > 0, [])
    ([], [])
    """
    trues: list[T] = []
    falses: list[T] = []
    for item in iterable:
        if predicate(item):
            trues.append(item)
        else:
            falses.append(item)
    return trues, falses

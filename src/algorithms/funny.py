"""Sorts nobody should run, kept because what they do wrong is worth seeing."""

import random
from collections.abc import Iterator

from algorithms import untested
from tracked_array import Color, Snapshot, TrackedArray, from_hex

_FLIP_END: Color = from_hex("#f9844a")


def pancake_sort(array: TrackedArray) -> Iterator[Snapshot]:
    """Sort `array` ascending in place using prefix reversals only.

    Bring the largest unsorted value to the front, then flip it to the back.
    O(n) flips, but each flip touches a whole prefix.
    """
    n = len(array)

    for size in range(n, 1, -1):
        largest = 0

        for i in range(1, size):

            if array[i] > array[largest]:
                largest = i

            yield array.snapshot()

        if largest != size - 1:

            if largest != 0:
                yield from _flip(array, largest)

            yield from _flip(array, size - 1)

    if n > 1:
        yield array.snapshot()


def _flip(array: TrackedArray, end: int) -> Iterator[Snapshot]:
    """Reverse the prefix [0, end] with swaps, so every move reaches the counters."""
    array.mark(end, _FLIP_END)
    low = 0
    high = end

    while low < high:
        array.swap(low, high)
        yield array.snapshot()
        low += 1
        high -= 1

    array.unmark(end)


def stooge_sort(array: TrackedArray) -> Iterator[Snapshot]:
    """Sort `array` ascending in place by sorting overlapping two-thirds of it.

    Deterministic and correct, but O(n^2.71): three recursive calls on 2n/3
    each, where merge sort makes two on n/2.
    """
    yield from _stooge_sort(array, 0, len(array) - 1)

    if len(array) > 1:
        yield array.snapshot()


def _stooge_sort(array: TrackedArray, low: int, high: int) -> Iterator[Snapshot]:
    """Sort the closed interval [low, high] of `array`."""
    if low >= high:
        return

    if array[low] > array[high]:
        array.swap(low, high)

    yield array.snapshot()

    if high - low + 1 > 2:
        third = (high - low + 1) // 3
        # the third pass repairs what the second one displaced
        yield from _stooge_sort(array, low, high - third)
        yield from _stooge_sort(array, low + third, high)
        yield from _stooge_sort(array, low, high - third)


@untested
def slow_sort(array: TrackedArray) -> Iterator[Snapshot]:
    """Sort `array` ascending in place by multiply and surrender.

    Merge sort's structure with the useful half removed: sort both halves,
    keep the larger of their maxima, sort everything but it again. Untested
    because it is not polynomial — a few dozen elements already take forever.
    """
    yield from _slow_sort(array, 0, len(array) - 1)

    if len(array) > 1:
        yield array.snapshot()


def _slow_sort(array: TrackedArray, low: int, high: int) -> Iterator[Snapshot]:
    """Sort the closed interval [low, high] of `array`."""
    if low >= high:
        return

    mid = (low + high) // 2
    yield from _slow_sort(array, low, mid)
    yield from _slow_sort(array, mid + 1, high)

    if array[mid] > array[high]:
        array.swap(mid, high)

    yield array.snapshot()
    yield from _slow_sort(array, low, high - 1)


@untested
def bogo_sort(array: TrackedArray) -> Iterator[Snapshot]:
    """Sort `array` ascending in place, yielding a Snapshot per comparison/shuffle."""
    n = len(array)

    while True:
        sorted_ = True

        for i in range(n - 1):
            if array[i] > array[i + 1]:
                sorted_ = False
                yield array.snapshot()
                break
            yield array.snapshot()

        if sorted_:
            break

        for i in range(n - 1, 0, -1):
            j = random.randint(0, i)
            array.swap(i, j)
            yield array.snapshot()


@untested
def bozo_sort(array: TrackedArray) -> Iterator[Snapshot]:
    """Sort `array` ascending in place, yielding a Snapshot per comparison/swap."""
    n = len(array)

    while True:
        sorted_ = True

        for i in range(n - 1):
            if array[i] > array[i + 1]:
                sorted_ = False
                yield array.snapshot()
                break
            yield array.snapshot()

        if sorted_:
            break

        i, j = random.sample(range(n), 2)
        array.swap(i, j)
        yield array.snapshot()

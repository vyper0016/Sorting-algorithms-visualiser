"""Hybrid sorts: per sub-problem, whichever of the simple sorts wins on it."""

from collections.abc import Iterator

from algorithms.sorts import (
    _HEAP_BOUNDARY,
    _insertion_sort_range,
    _merge,
    _partition,
    _sift_down,
)
from tracked_array import Snapshot, TrackedArray

# CPython picks a run length in [32, 64]; the visualiser sorts fewer elements
# than that, so a shorter run keeps the merge half of the algorithm visible.
_MIN_RUN: int = 8

_INTRO_THRESHOLD: int = 16


def tim_sort(array: TrackedArray) -> Iterator[Snapshot]:
    """Insertion sort short runs of `array`, then merge them pairwise.

    What `list.sort` does, minus natural-run detection and galloping merges.
    """
    n = len(array)

    for start in range(0, n, _MIN_RUN):
        yield from _insertion_sort_range(array, start, min(start + _MIN_RUN, n) - 1)

    size = _MIN_RUN

    while size < n:

        for left in range(0, n, 2 * size):
            mid = min(left + size, n) - 1
            right = min(left + 2 * size, n) - 1

            if mid < right:
                yield from _merge(array, left, mid, right)

        size *= 2

    if n > 1:
        yield array.snapshot()


def intro_sort(array: TrackedArray) -> Iterator[Snapshot]:
    """Quick sort `array`, escaping to heap sort when it goes quadratic.

    What `std::sort` does: a recursion deeper than 2*log2(n) is taken as
    evidence of bad pivots, and short intervals go to insertion sort.
    """
    n = len(array)

    if n > 1:
        yield from _intro_sort(array, 0, n - 1, 2 * (n.bit_length() - 1))
        yield array.snapshot()


def _intro_sort(
    array: TrackedArray, low: int, high: int, depth_limit: int
) -> Iterator[Snapshot]:
    """Sort the closed interval [low, high] of `array` within `depth_limit` splits."""
    while low < high:

        if high - low + 1 <= _INTRO_THRESHOLD:
            yield from _insertion_sort_range(array, low, high)
            return

        if depth_limit == 0:
            yield from _heap_sort_range(array, low, high)
            return

        depth_limit -= 1
        pivot = yield from _partition(array, low, high)
        yield from _intro_sort(array, low, pivot - 1, depth_limit)
        # tail call as a loop: the right half is sorted by the next round
        low = pivot + 1


def _heap_sort_range(array: TrackedArray, low: int, high: int) -> Iterator[Snapshot]:
    """Heap sort the closed interval [low, high] of `array`, leaving the rest alone."""
    size = high - low + 1

    for root in range(size // 2 - 1, -1, -1):
        yield from _sift_down(array, root, size, low)

    for end in range(size - 1, 0, -1):
        array.mark(low + end, _HEAP_BOUNDARY)
        array.swap(low, low + end)
        yield array.snapshot()
        array.unmark(low + end)
        yield from _sift_down(array, 0, end, low)

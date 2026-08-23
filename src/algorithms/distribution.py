"""Non-comparison sorts: they place values by arithmetic, not by comparing them."""

from collections.abc import Generator, Iterator

from tracked_array import Color, Snapshot, TrackedArray, from_hex
from tracked_integer import TrackedInteger

# the radix sorts follow Timo Bingmann's sound-of-sorting, which buckets on
# base-4 digits: few enough buckets that a single pass stays watchable
_RADIX: int = 4

_BUCKET_EDGE: Color = from_hex("#ffd166")
_RANGE_END: Color = from_hex("#4cc9f0")


def counting_sort(array: TrackedArray) -> Iterator[Snapshot]:
    """Sort `array` ascending in place by counting how often each value occurs.

    O(n + k) for k values of spread: cheap for a small spread, ruinous for a large one.
    """
    array.set_current_algo("counting sort")
    n = len(array)

    if n < 2:
        return

    lowest, highest = yield from _range_of(array)
    counts = array.buffer(int(highest - lowest) + 1)

    for i in range(n):
        slot = int(array[i] - lowest)
        counts[slot] = counts[slot] + 1
        yield array.snapshot()

    write = 0

    for slot in range(len(counts)):
        for _ in range(int(counts[slot])):
            array[write] = lowest + slot
            write += 1
            yield array.snapshot()

    yield array.snapshot()


def radix_sort_lsd(array: TrackedArray) -> Iterator[Snapshot]:
    """Sort `array` ascending in place, one digit at a time, least significant first.

    One counting pass per digit, each copying the array out and handing it back
    in bucket order. Stable, so the order won by the lower digits survives.
    """
    array.set_current_algo("radix sort (LSD)")
    n = len(array)

    if n < 2:
        return

    lowest, highest = yield from _range_of(array)
    passes = _lsd_passes(int(highest - lowest))

    try:
        for p in range(passes):
            array.set_status(f"digit {p + 1} of {passes}, least significant first")
            yield from _lsd_pass(array, _RADIX**p, int(lowest))

    finally:
        array.unmark_all()
        array.set_status("")

    yield array.snapshot()


def radix_sort_msd(array: TrackedArray) -> Iterator[Snapshot]:
    """Sort `array` ascending in place, one digit at a time, most significant first.

    Each level buckets its range on one digit in place, then recurses into every
    bucket still holding more than one element.
    """
    array.set_current_algo("radix sort (MSD)")
    n = len(array)

    if n < 2:
        return

    lowest, highest = yield from _range_of(array)
    deepest = _msd_depth(int(highest - lowest))

    try:
        yield from _msd_sort(array, 0, n, 0, deepest, int(lowest))
    finally:
        array.unmark_all()

    yield array.snapshot()


def _range_of(
    array: TrackedArray,
) -> Generator[Snapshot, None, tuple[TrackedInteger, TrackedInteger]]:
    """The smallest and largest element of `array`, in one pass."""
    lowest = highest = array[0]

    for i in range(1, len(array)):
        value = array[i]

        if value < lowest:
            lowest = value
        elif value > highest:
            highest = value

        yield array.snapshot()

    return lowest, highest


def _lsd_pass(array: TrackedArray, base: int, lowest: int) -> Iterator[Snapshot]:
    """Stably reorder `array` by the digit `base` selects, through a full copy.

    Filling each bucket from its start upwards is what keeps the pass stable.
    """
    n = len(array)
    counts = array.buffer(_RADIX)
    copy = array.buffer(n)

    for i in range(n):
        value = array[i]
        copy[i] = value
        digit = _digit(value, lowest, base)
        counts[digit] = counts[digit] + 1
        yield array.snapshot()

    # exclusive prefix sum: buckets[d] is where bucket d starts
    buckets = array.buffer(_RADIX + 1)

    for digit in range(_RADIX):
        buckets[digit + 1] = buckets[digit] + counts[digit]

    for digit in range(_RADIX):
        start = int(buckets[digit])

        if start < n:
            array.mark(start, _BUCKET_EDGE)

    for i in range(n):
        value = copy[i]
        digit = _digit(value, lowest, base)
        array[int(buckets[digit])] = value
        buckets[digit] = buckets[digit] + 1
        yield array.snapshot()

    array.unmark_all()


def _msd_sort(
    array: TrackedArray, low: int, high: int, depth: int, deepest: int, lowest: int
) -> Iterator[Snapshot]:
    """Bucket [low, high) on the digit at `depth`, then recurse into each bucket.

    The ends of the range are marked, and the last slot of every bucket with them.
    """
    array.mark(low, _RANGE_END)
    array.mark(high - 1, _RANGE_END)
    array.set_status(f"digit {depth + 1} of {deepest + 1} on [{low}:{high}]")

    base = _RADIX ** (deepest - depth)
    counts = array.buffer(_RADIX)

    for i in range(low, high):
        digit = _digit(array[i], lowest, base)
        counts[digit] = counts[digit] + 1
        yield array.snapshot()

    # inclusive prefix sum: buckets[d] is where bucket d ends, and the cycle
    # walk below eats it back down to where bucket d starts
    buckets = array.buffer(_RADIX)
    buckets[0] = counts[0]

    for digit in range(1, _RADIX):
        buckets[digit] = buckets[digit - 1] + counts[digit]

    for digit in range(_RADIX):
        end = int(buckets[digit])

        if end > 0:
            array.mark(low + end - 1, _BUCKET_EDGE)

    yield from _msd_permute(array, low, high, base, lowest, counts, buckets)

    array.unmark_all()

    if depth + 1 > deepest:
        return

    start = low

    for digit in range(_RADIX):
        size = int(counts[digit])

        if size > 1:
            yield from _msd_sort(array, start, start + size, depth + 1, deepest, lowest)

        start += size


def _msd_permute(
    array: TrackedArray,
    low: int,
    high: int,
    base: int,
    lowest: int,
    counts: TrackedArray,
    buckets: TrackedArray,
) -> Iterator[Snapshot]:
    """Move every element of [low, high) into its bucket without a copy.

    The element at `i` is swapped to the free slot at the end of its bucket, which
    drops another on `i`, until one lands on `i` itself — a closed cycle. `i` then
    skips the finished bucket.
    """
    i = 0

    while i < high - low:
        while True:
            digit = _digit(array[low + i], lowest, base)
            buckets[digit] = buckets[digit] - 1
            target = int(buckets[digit])

            if target <= i:
                break

            array.swap(low + i, low + target)
            yield array.snapshot()

        i += int(counts[_digit(array[low + i], lowest, base)])


def _lsd_passes(spread: int) -> int:
    """How many base-RADIX digits the widest value has: ceil(log(spread + 1))."""
    passes, place = 0, 1

    while place < spread + 1:
        passes += 1
        place *= _RADIX

    return passes


def _msd_depth(spread: int) -> int:
    """The deepest digit an MSD pass reaches: floor(log(spread + 1)).

    One less than `_lsd_passes`, except on an exact power of RADIX, where
    sound-of-sorting spends a first pass on a digit zero for every element.
    """
    depth, place = 0, _RADIX

    while place <= spread + 1:
        depth += 1
        place *= _RADIX

    return depth


def _digit(value: TrackedInteger, lowest: int, base: int) -> int:
    """The base-RADIX digit of `value - lowest` at the place `base` selects.

    sound-of-sorting reads the digit straight off the value; its arrays never hold
    one below 1. Shifting by the smallest element keeps that working for negatives.
    """
    return int((value - lowest) // base) % _RADIX

"""Non-comparison sorts: they place values by arithmetic, not by comparing them."""

from collections.abc import Generator, Iterator

from tracked_array import Snapshot, TrackedArray
from tracked_integer import TrackedInteger

_RADIX: int = 10


def counting_sort(array: TrackedArray) -> Iterator[Snapshot]:
    """Sort `array` ascending in place by counting how often each value occurs.

    O(n + k) for k values of spread, and only the range scan compares
    anything. Cheap for a small spread, ruinous for a large one.
    """
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


def radix_sort(array: TrackedArray) -> Iterator[Snapshot]:
    """Sort `array` ascending in place, one digit at a time, least significant first.

    Digits are taken from `value - lowest`, so negative values work without
    the array ever holding a shifted value.
    """
    n = len(array)

    if n < 2:
        return

    lowest, highest = yield from _range_of(array)
    spread = int(highest - lowest)
    output = array.buffer(n)
    exponent = 1

    while True:
        yield from _digit_pass(array, output, exponent, int(lowest))

        if spread // (exponent * _RADIX) == 0:
            break

        exponent *= _RADIX

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


def _digit_pass(
    array: TrackedArray, output: TrackedArray, exponent: int, lowest: int
) -> Iterator[Snapshot]:
    """Stably reorder `array` by one digit, using `output` as scratch space.

    Walking backwards and filling each bucket from its end down is what keeps
    the pass stable, and stability per digit is what makes the passes compose.
    """
    n = len(array)
    counts = array.buffer(_RADIX)

    for i in range(n):
        digit = _digit(array[i], lowest, exponent)
        counts[digit] = counts[digit] + 1
        yield array.snapshot()

    for digit in range(1, _RADIX):
        counts[digit] = counts[digit] + counts[digit - 1]

    for i in range(n - 1, -1, -1):
        value = array[i]
        digit = _digit(value, lowest, exponent)
        counts[digit] = counts[digit] - 1
        output[int(counts[digit])] = value
        yield array.snapshot()

    for i in range(n):
        array[i] = output[i]
        yield array.snapshot()


def _digit(value: TrackedInteger, lowest: int, exponent: int) -> int:
    """The base-10 digit of `value - lowest` at the place `exponent` selects."""
    return int((value - lowest) // exponent) % _RADIX

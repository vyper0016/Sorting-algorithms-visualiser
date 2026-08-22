from collections.abc import Generator, Iterator

from tracked_array import Color, Snapshot, TrackedArray, from_hex
from tracked_integer import TrackedInteger

_RUN_END: Color = from_hex("#ffd166")
_SPLIT: Color = from_hex("#c792ea")
_PIVOT: Color = from_hex("#ef476f")
_HEAP_BOUNDARY: Color = from_hex("#06d6a0")
_CYCLE_START: Color = from_hex("#4cc9f0")


def bubble_sort(array: TrackedArray) -> Iterator[Snapshot]:
    """Sort `array` ascending in place, yielding a Snapshot per comparison."""
    n = len(array)

    for i in range(n):
        swapped = False

        for j in range(0, n - i - 1):

            if array[j] > array[j + 1]:
                array.swap(j, j + 1)
                swapped = True

            yield array.snapshot()

        if not swapped:
            break


def insertion_sort(array: TrackedArray) -> Iterator[Snapshot]:
    """Sort `array` ascending in place, yielding a Snapshot per comparison."""
    yield from _insertion_sort_range(array, 0, len(array) - 1)


def _insertion_sort_range(
    array: TrackedArray, left: int, right: int
) -> Iterator[Snapshot]:
    """Insertion sort the closed interval [left, right] of `array`."""
    for i in range(left + 1, right + 1):
        j = i

        while j > left and array[j - 1] > array[j]:
            array.swap(j - 1, j)
            yield array.snapshot()
            j -= 1

        yield array.snapshot()


def merge_sort(array: TrackedArray) -> Iterator[Snapshot]:
    """Sort `array` ascending in place, yielding a Snapshot per element moved."""
    yield from _merge_sort(array, 0, len(array) - 1)

    if len(array) > 1:
        yield array.snapshot()


def _merge_sort(array: TrackedArray, left: int, right: int) -> Iterator[Snapshot]:
    """Sort the closed interval [left, right] of `array`."""
    if left < right:
        mid = (left + right) // 2
        yield from _merge_sort(array, left, mid)
        yield from _merge_sort(array, mid + 1, right)
        yield from _merge(array, left, mid, right)


def _merge(array: TrackedArray, left: int, mid: int, right: int) -> Iterator[Snapshot]:
    """Merge the sorted runs [left, mid] and [mid + 1, right] back into `array`.

    The window being merged is marked
    """

    left_size = mid - left + 1
    right_size = right - mid

    left_run = array.buffer(left_size)
    right_run = array.buffer(right_size)

    array.mark(left, _RUN_END)
    array.mark(right, _RUN_END)
    array.mark(mid, _SPLIT)

    for i in range(left_size):
        left_run[i] = array[left + i]
        yield array.snapshot()

    for j in range(right_size):
        right_run[j] = array[mid + 1 + j]
        yield array.snapshot()

    i = j = 0
    k = left

    while i < left_size and j < right_size:
        if left_run[i] <= right_run[j]:
            array[k] = left_run[i]
            i += 1
        else:
            array[k] = right_run[j]
            j += 1
        k += 1
        yield array.snapshot()

    while i < left_size:
        array[k] = left_run[i]
        i += 1
        k += 1
        yield array.snapshot()

    while j < right_size:
        array[k] = right_run[j]
        j += 1
        k += 1
        yield array.snapshot()

    array.unmark(left)
    array.unmark(mid)
    array.unmark(right)


def selection_sort(array: TrackedArray) -> Iterator[Snapshot]:
    """Sort `array` ascending in place, yielding a Snapshot per comparison."""
    n = len(array)

    for i in range(n - 1):
        min_index = i

        for j in range(i + 1, n):
            if array[j] < array[min_index]:
                min_index = j
            yield array.snapshot()

        if min_index != i:
            array.swap(i, min_index)
            yield array.snapshot()


def quick_sort(array: TrackedArray) -> Iterator[Snapshot]:
    """Sort `array` ascending in place, yielding a Snapshot per comparison."""
    yield from _quick_sort(array, 0, len(array) - 1)

    if len(array) > 1:
        yield array.snapshot()


def _quick_sort(array: TrackedArray, low: int, high: int) -> Iterator[Snapshot]:
    """Sort the closed interval [low, high] of `array`."""
    if low < high:
        pivot_index = yield from _partition(array, low, high)
        yield from _quick_sort(array, low, pivot_index - 1)
        yield from _quick_sort(array, pivot_index + 1, high)


def _partition(
    array: TrackedArray, low: int, high: int
) -> Generator[Snapshot, None, int]:
    """Partition [low, high] around the element at `high`, returning its final index."""
    array.mark(high, _PIVOT)
    pivot = array[high]
    i = low

    for j in range(low, high):
        if array[j] < pivot:
            array.swap(i, j)
            i += 1
        yield array.snapshot()

    array.swap(i, high)
    yield array.snapshot()
    array.unmark(high)

    return i


def heap_sort(array: TrackedArray) -> Iterator[Snapshot]:
    """Sort `array` ascending in place, yielding a Snapshot per comparison."""
    n = len(array)

    for root in range(n // 2 - 1, -1, -1):
        yield from _sift_down(array, root, n)

    for end in range(n - 1, 0, -1):
        array.mark(end, _HEAP_BOUNDARY)
        array.swap(0, end)
        yield array.snapshot()
        array.unmark(end)
        yield from _sift_down(array, 0, end)

    if n > 1:
        yield array.snapshot()


def _sift_down(
    array: TrackedArray, root: int, size: int, low: int = 0
) -> Iterator[Snapshot]:
    """Restore the max-heap property for `root` in the heap [low, low + size)."""
    while True:
        largest = root
        left = 2 * root + 1
        right = 2 * root + 2

        if left < size:
            if array[low + left] > array[low + largest]:
                largest = left
            yield array.snapshot()

        if right < size:
            if array[low + right] > array[low + largest]:
                largest = right
            yield array.snapshot()

        if largest == root:
            break

        array.swap(low + root, low + largest)
        yield array.snapshot()
        root = largest


def shell_sort(array: TrackedArray) -> Iterator[Snapshot]:
    """Insertion sort over a shrinking gap, yielding a Snapshot per comparison."""
    n = len(array)
    gap = n // 2

    while gap > 0:

        for i in range(gap, n):
            j = i

            while j >= gap and array[j - gap] > array[j]:
                array.swap(j - gap, j)
                yield array.snapshot()
                j -= gap

            yield array.snapshot()

        gap //= 2


def comb_sort(array: TrackedArray) -> Iterator[Snapshot]:
    """Bubble sort over a gap shrinking by 1.3, yielding a Snapshot per comparison."""
    n = len(array)
    gap = n
    sorted_ = False

    while not sorted_:
        gap = gap * 10 // 13

        if gap <= 1:
            gap = 1
            sorted_ = True

        for i in range(n - gap):

            if array[i] > array[i + gap]:
                array.swap(i, i + gap)
                sorted_ = False

            yield array.snapshot()


def cocktail_shaker_sort(array: TrackedArray) -> Iterator[Snapshot]:
    """Bubble sort alternating direction, yielding a Snapshot per comparison."""
    start = 0
    end = len(array) - 1
    swapped = True

    while swapped and start < end:
        swapped = False

        for i in range(start, end):

            if array[i] > array[i + 1]:
                array.swap(i, i + 1)
                swapped = True

            yield array.snapshot()

        end -= 1

        if not swapped:
            break

        swapped = False

        for i in range(end, start, -1):

            if array[i - 1] > array[i]:
                array.swap(i - 1, i)
                swapped = True

            yield array.snapshot()

        start += 1


def gnome_sort(array: TrackedArray) -> Iterator[Snapshot]:
    """Insertion sort with a single index, yielding a Snapshot per comparison."""
    n = len(array)

    if n < 2:
        return

    position = 1

    while position < n:

        if array[position - 1] <= array[position]:
            position += 1
        else:
            array.swap(position - 1, position)
            position = max(position - 1, 1)

        yield array.snapshot()


def odd_even_sort(array: TrackedArray) -> Iterator[Snapshot]:
    """Bubble sort by odd then even pairs, yielding a Snapshot per comparison."""
    n = len(array)
    sorted_ = False

    while not sorted_:
        sorted_ = True

        for parity in (1, 0):

            for i in range(parity, n - 1, 2):

                if array[i] > array[i + 1]:
                    array.swap(i, i + 1)
                    sorted_ = False

                yield array.snapshot()


def cycle_sort(array: TrackedArray) -> Iterator[Snapshot]:
    """Sort `array` ascending in place with the minimum number of writes.

    Each element is counted into its final slot and written there once,
    picking up whatever it displaced.
    """
    n = len(array)

    for cycle_start in range(n - 1):
        array.mark(cycle_start, _CYCLE_START)
        item = array[cycle_start]
        position = yield from _destination(array, item, cycle_start)

        if position != cycle_start:
            position = yield from _skip_duplicates(array, item, position)
            item = yield from _place(array, item, position)

            while position != cycle_start:
                position = yield from _destination(array, item, cycle_start)
                position = yield from _skip_duplicates(array, item, position)
                item = yield from _place(array, item, position)

        array.unmark(cycle_start)

    if n > 1:
        yield array.snapshot()


def _destination(
    array: TrackedArray, item: TrackedInteger, cycle_start: int
) -> Generator[Snapshot, None, int]:
    """The slot `item` belongs in: `cycle_start` plus the smaller elements after it."""
    position = cycle_start

    for i in range(cycle_start + 1, len(array)):

        if array[i] < item:
            position += 1

        yield array.snapshot()

    return position


def _skip_duplicates(
    array: TrackedArray, item: TrackedInteger, position: int
) -> Generator[Snapshot, None, int]:
    """Walk `position` past elements equal to `item`, keeping the sort stable-ish."""
    while item == array[position]:
        position += 1
        yield array.snapshot()

    return position


def _place(
    array: TrackedArray, item: TrackedInteger, position: int
) -> Generator[Snapshot, None, TrackedInteger]:
    """Write `item` into `position`, returning the element it displaced."""
    displaced = array[position]
    array[position] = item
    yield array.snapshot()
    return displaced


if __name__ == "__main__":
    from generator import generate_random_array

    example = generate_random_array(10)
    print(example)
    frames = list(bubble_sort(example))
    print(example)
    print(f"{len(frames)} frames, {frames[-1]}")

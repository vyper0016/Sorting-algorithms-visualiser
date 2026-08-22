import random
from collections.abc import Generator, Iterator

from algorithms import untested
from tracked_array import Color, Snapshot, TrackedArray, from_hex

_RUN_END: Color = from_hex("#ffd166")
_SPLIT: Color = from_hex("#c792ea")
_PIVOT: Color = from_hex("#ef476f")
_HEAP_BOUNDARY: Color = from_hex("#06d6a0")


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
    n = len(array)

    for i in range(1, n):
        j = i

        while j > 0 and array[j - 1] > array[j]:
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


def _sift_down(array: TrackedArray, root: int, size: int) -> Iterator[Snapshot]:
    """Restore the max-heap property for the subtree rooted at `root` in [0, size)."""
    while True:
        largest = root
        left = 2 * root + 1
        right = 2 * root + 2

        if left < size:
            if array[left] > array[largest]:
                largest = left
            yield array.snapshot()

        if right < size:
            if array[right] > array[largest]:
                largest = right
            yield array.snapshot()

        if largest == root:
            break

        array.swap(root, largest)
        yield array.snapshot()
        root = largest


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


if __name__ == "__main__":
    from generator import generate_random_array

    example = generate_random_array(10)
    print(example)
    frames = list(bubble_sort(example))
    print(example)
    print(f"{len(frames)} frames, {frames[-1]}")

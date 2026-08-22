from collections.abc import Iterator

from tracked_array import Color, Snapshot, TrackedArray, from_hex

_RUN_END: Color = from_hex("#ffd166")
_SPLIT: Color = from_hex("#c792ea")


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


if __name__ == "__main__":
    from generator import generate_random_array

    example = generate_random_array(10)
    print(example)
    frames = list(bubble_sort(example))
    print(example)
    print(f"{len(frames)} frames, {frames[-1]}")

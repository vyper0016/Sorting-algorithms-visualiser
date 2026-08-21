from collections.abc import Iterator

from trackables import Snapshot, TrackedArray


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


if __name__ == "__main__":
    from generator import generate_random_array

    example = generate_random_array(10)
    print(example)
    frames = list(bubble_sort(example))
    print(example)
    print(f"{len(frames)} frames, {frames[-1]}")

import random

import icontract

from stats import Stats
from trackables import TrackedArray, TrackedInteger


@icontract.require(lambda size: size >= 0)
@icontract.require(lambda min_value, max_value: min_value <= max_value)
def generate_random_array(
    size: int, min_value: int = 0, max_value: int = 100
) -> TrackedArray:
    """Build a TrackedArray of `size` random ints in [min_value, max_value].

    >>> arr = generate_random_array(5, 0, 10)
    >>> len(arr)
    5
    >>> all(0 <= x <= 10 for x in arr)
    True
    """
    stats = Stats()
    values = [random.randint(min_value, max_value) for _ in range(size)]
    return TrackedArray([TrackedInteger(v, stats) for v in values], stats)


@icontract.require(lambda step: step != 0)
def generate_sorted_array(
    start: int, stop: int | None = None, step: int = 1
) -> TrackedArray:
    """Build a TrackedArray of the ints produced by `range`.

    >>> generate_sorted_array(5)
    [0, 1, 2, 3, 4]
    >>> generate_sorted_array(4, -1, -1)
    [4, 3, 2, 1, 0]
    >>> generate_sorted_array(3, 6)
    [3, 4, 5]
    >>> generate_sorted_array(0, 10, 3)
    [0, 3, 6, 9]
    >>> generate_sorted_array(0)
    []
    """
    if stop is None:
        start, stop = 0, start
    stats = Stats()
    return TrackedArray(
        [TrackedInteger(v, stats) for v in range(start, stop, step)], stats
    )


if __name__ == "__main__":
    print(generate_sorted_array(10))

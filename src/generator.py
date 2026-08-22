import random

import icontract

from stats import Stats
from tracked_array import TrackedArray
from tracked_integer import TrackedInteger


@icontract.require(lambda size: size >= 0)
@icontract.require(lambda min_value, max_value: min_value <= max_value)
@icontract.require(
    lambda size, min_value, max_value, distinct: (
        not distinct or size <= max_value - min_value + 1
    ),
    "not enough distinct values in range for the requested size",
)
def generate_random_array(
    size: int,
    min_value: int = 0,
    max_value: int = 100,
    distinct: bool = False,
    seed: int | None = None,
) -> TrackedArray:
    """Build a TrackedArray of `size` random ints in [min_value, max_value].

    With `distinct`, no value repeats.
    `seed` used for the rng.

    >>> arr = generate_random_array(5, 0, 10)
    >>> len(arr)
    5
    >>> all(0 <= x <= 10 for x in arr)
    True
    """
    rng = random.Random(seed)
    if distinct:
        values = rng.sample(range(min_value, max_value + 1), size)
    else:
        values = [rng.randint(min_value, max_value) for _ in range(size)]
    stats = Stats()
    return TrackedArray([TrackedInteger(v, stats) for v in values], stats)


@icontract.require(lambda step: step != 0)
def generate_range_array(
    start: int, stop: int | None = None, step: int = 1
) -> TrackedArray:
    """Build a TrackedArray of the ints produced by `range`.

    >>> generate_range_array(5)
    [0, 1, 2, 3, 4]
    >>> generate_range_array(4, -1, -1)
    [4, 3, 2, 1, 0]
    >>> generate_range_array(3, 6)
    [3, 4, 5]
    >>> generate_range_array(0, 10, 3)
    [0, 3, 6, 9]
    >>> generate_range_array(0)
    []
    """
    if stop is None:
        start, stop = 0, start
    stats = Stats()
    return TrackedArray(
        [TrackedInteger(v, stats) for v in range(start, stop, step)], stats
    )


def generate_shuffled_array(
    start: int, stop: int | None = None, seed: int | None = None
) -> TrackedArray:
    """Build a TrackedArray holding `range(start, stop)` in random order.

    >>> sorted(generate_shuffled_array(5))
    [0, 1, 2, 3, 4]
    >>> sorted(generate_shuffled_array(3, 6))
    [3, 4, 5]
    >>> generate_shuffled_array(0, 5, seed=1)
    [2, 3, 4, 0, 1]
    >>> generate_shuffled_array(0)
    []
    """
    if stop is None:
        start, stop = 0, start
    values = list(range(start, stop))
    random.Random(seed).shuffle(values)
    stats = Stats()
    return TrackedArray([TrackedInteger(v, stats) for v in values], stats)


if __name__ == "__main__":
    print(generate_range_array(10))

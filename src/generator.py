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


@icontract.require(lambda size: size >= 0)
@icontract.require(lambda min_value, max_value: min_value <= max_value)
def generate_sorted_array(
    size: int, min_value: int = 0, max_value: int = 100, reverse: bool = True
) -> TrackedArray:
    """Build a TrackedArray of `size` ints, sorted (descending by default).

    >>> arr = generate_sorted_array(5, 0, 10, reverse=False)
    >>> list(arr) == sorted(arr)
    True
    >>> arr = generate_sorted_array(5, 0, 10)
    >>> list(arr) == sorted(arr, reverse=True)
    True
    """
    stats = Stats()
    values = sorted(
        (random.randint(min_value, max_value) for _ in range(size)), reverse=reverse
    )
    return TrackedArray([TrackedInteger(v, stats) for v in values], stats)

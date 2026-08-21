import logging
from collections import Counter
from dataclasses import dataclass

import icontract

from stats import Stats

logger = logging.getLogger(__name__)


class TrackedInteger(int):
    """An int that records every comparison it takes part in via Stats."""

    stats: Stats

    def __new__(cls, value: int, stats: Stats) -> "TrackedInteger":
        instance = super().__new__(cls, value)
        instance.stats = stats
        return instance

    # to track comparisons
    def __gt__(self, value: int) -> bool:
        logger.debug(f"Comparing {self} > {value}")
        self.stats.on_comparison()
        return super().__gt__(value)

    def __lt__(self, value: int) -> bool:
        logger.debug(f"Comparing {self} < {value}")
        self.stats.on_comparison()
        return super().__lt__(value)

    def __eq__(self, value: object) -> bool:
        logger.debug(f"Comparing {self} == {value}")
        self.stats.on_comparison()
        return super().__eq__(value)

    def __ge__(self, value: int) -> bool:
        logger.debug(f"Comparing {self} >= {value}")
        self.stats.on_comparison()
        return super().__ge__(value)

    def __le__(self, value: int) -> bool:
        logger.debug(f"Comparing {self} <= {value}")
        self.stats.on_comparison()
        return super().__le__(value)

    def __hash__(self) -> int:
        return super().__hash__()


@dataclass(frozen=True)
class Snapshot:
    """Immutable record of a TrackedArray's contents and counters at one moment.

    One snapshot is one frame for the visualiser, and the point at which the
    array's contents are checked for corruption.

    >>> snap = Snapshot((3, 1, 2), reads=4, writes=2, comparisons=7)
    >>> snap.values
    (3, 1, 2)
    >>> snap.reads, snap.writes, snap.comparisons
    (4, 2, 7)
    """

    values: tuple[int, ...]
    reads: int
    writes: int
    comparisons: int


class TrackedArray(list[TrackedInteger]):
    """A list of TrackedInteger that records reads and writes.

    A sorting algorithm may only permute the array: it must not resize it or
    introduce values that were not there to begin with. That is checked as a
    postcondition of `snapshot`, not as a class invariant, so an algorithm pays
    O(n) per frame instead of O(n) per element access.

    >>> stats = Stats()
    >>> arr = TrackedArray([TrackedInteger(v, stats) for v in (3, 1, 2)], stats)
    >>> arr.swap(0, 2)
    >>> arr.snapshot()
    Snapshot(values=(2, 1, 3), reads=2, writes=2, comparisons=0)
    """

    def __init__(self, data: list[TrackedInteger], stats: Stats | None = None) -> None:
        super().__init__(data)
        self.stats = stats or Stats()
        self._original_length = len(self)
        self._original_elements: Counter[int] = Counter(int(x) for x in self)

    def __getitem__(self, index: int) -> TrackedInteger:  # type: ignore[override]
        self.stats.on_read()
        return super().__getitem__(index)

    def __setitem__(self, index: int, value: TrackedInteger) -> None:  # type: ignore[override]
        self.stats.on_write()
        super().__setitem__(index, value)

    def swap(self, i: int, j: int) -> None:
        """Swap the elements at indices i and j."""
        self[i], self[j] = self[j], self[i]

    @icontract.ensure(
        lambda self, result: len(result.values) == self._original_length,
        "array was resized",
    )
    @icontract.ensure(
        lambda self, result: Counter(result.values) == self._original_elements,
        "array is no longer a permutation of its original elements",
    )
    def snapshot(self) -> Snapshot:
        """Capture contents and counters, verifying the array is still intact.

        Iterating `self` goes through `list.__iter__`, not `__getitem__`, so
        taking a snapshot does not itself count as a read.

        >>> stats = Stats()
        >>> arr = TrackedArray([TrackedInteger(1, stats)], stats)
        >>> arr.snapshot()
        Snapshot(values=(1,), reads=0, writes=0, comparisons=0)
        """
        return Snapshot(
            values=tuple(int(x) for x in self),
            reads=self.stats.reads,
            writes=self.stats.writes,
            comparisons=self.stats.comparisons,
        )


if __name__ == "__main__":
    # Example usage
    stats = Stats()
    tracked_array = TrackedArray([TrackedInteger(i, stats) for i in range(5)], stats)

    print(tracked_array.snapshot())
    tracked_array.swap(1, 3)
    print(tracked_array.snapshot())

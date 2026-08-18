import logging

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


@icontract.invariant(lambda self: len(self) == self._original_length)
@icontract.invariant(lambda self: {int(x) for x in self} == self._original_elements)
class TrackedArray(list[TrackedInteger]):
    """A list of TrackedInteger that records reads/writes and forbids resizing
    or modification of elements."""

    def __init__(self, data: list[TrackedInteger], stats: Stats | None = None) -> None:
        super().__init__(data)
        self.stats = stats or Stats()
        self._original_length = len(self)
        self._original_elements = frozenset(int(x) for x in self)

    def __getitem__(self, index: int) -> TrackedInteger:  # type: ignore[override]
        self.stats.on_read()
        return super().__getitem__(index)

    def __setitem__(self, index: int, value: TrackedInteger) -> None:  # type: ignore[override]
        self.stats.on_write()
        super().__setitem__(index, value)

    def swap(self, i: int, j: int) -> None:
        """Swap the elements at indices i and j."""
        self[i], self[j] = self[j], self[i]

    def __len__(self) -> int:
        return super().__len__()

    # override explicitly to ensure icontract
    def append(self, value):  # type: ignore[no-untyped-def]
        return super().append(value)

    def extend(self, iterable):  # type: ignore[no-untyped-def]
        return super().extend(iterable)

    def insert(self, index, value):  # type: ignore[no-untyped-def]
        return super().insert(index, value)

    def remove(self, value):  # type: ignore[no-untyped-def]
        return super().remove(value)

    def pop(self, index=-1):  # type: ignore[no-untyped-def]
        return super().pop(index)

    def clear(self):  # type: ignore[no-untyped-def]
        return super().clear()


if __name__ == "__main__":
    # Example usage
    stats = Stats()
    tracked_array = TrackedArray([TrackedInteger(i, stats) for i in range(5)], stats)

    print(tracked_array)
    tracked_array.swap(1, 3)
    print(tracked_array)
    print(
        f"Reads: {stats.reads}, Writes: {stats.writes}, "
        f"Comparisons: {stats.comparisons}"
    )

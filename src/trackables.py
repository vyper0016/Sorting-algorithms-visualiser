import logging
from collections.abc import Iterable
from dataclasses import dataclass
from typing import NoReturn, SupportsIndex, overload

import icontract

from stats import Stats

logger = logging.getLogger(__name__)


class TrackedInteger(int):
    """An int that records every comparison it takes part in via Stats.

    >>> stats = Stats()
    >>> doubled = TrackedInteger(3, stats) * 2
    >>> type(doubled).__name__, doubled.stats is stats
    ('TrackedInteger', True)
    """

    stats: Stats

    def __new__(cls, value: int, stats: Stats) -> "TrackedInteger":
        instance = super().__new__(cls, value)
        instance.stats = stats
        return instance

    def _tracked(self, value: object) -> "TrackedInteger":
        """Rebuild an arithmetic result on this Stats, or defer to the other operand."""
        if not isinstance(value, int):
            return NotImplemented  # type: ignore[no-any-return]
        return TrackedInteger(value, self.stats)

    # to track comparisons
    def __gt__(self, value: int) -> bool:
        logger.debug("Comparing %s > %s", self, value)
        self.stats.on_comparison()
        return super().__gt__(value)

    def __lt__(self, value: int) -> bool:
        logger.debug("Comparing %s < %s", self, value)
        self.stats.on_comparison()
        return super().__lt__(value)

    def __eq__(self, value: object) -> bool:
        logger.debug("Comparing %s == %s", self, value)
        self.stats.on_comparison()
        return super().__eq__(value)

    def __ge__(self, value: int) -> bool:
        logger.debug("Comparing %s >= %s", self, value)
        self.stats.on_comparison()
        return super().__ge__(value)

    def __le__(self, value: int) -> bool:
        logger.debug("Comparing %s <= %s", self, value)
        self.stats.on_comparison()
        return super().__le__(value)

    def __hash__(self) -> int:
        return super().__hash__()

    # to keep derived values tracked
    def __add__(self, value: int) -> "TrackedInteger":
        return self._tracked(super().__add__(value))

    def __radd__(self, value: int) -> "TrackedInteger":
        return self._tracked(super().__radd__(value))

    def __sub__(self, value: int) -> "TrackedInteger":
        return self._tracked(super().__sub__(value))

    def __rsub__(self, value: int) -> "TrackedInteger":
        return self._tracked(super().__rsub__(value))

    def __mul__(self, value: int) -> "TrackedInteger":
        return self._tracked(super().__mul__(value))

    def __rmul__(self, value: int) -> "TrackedInteger":
        return self._tracked(super().__rmul__(value))

    def __floordiv__(self, value: int) -> "TrackedInteger":
        return self._tracked(super().__floordiv__(value))

    def __rfloordiv__(self, value: int) -> "TrackedInteger":
        return self._tracked(super().__rfloordiv__(value))

    def __mod__(self, value: int) -> "TrackedInteger":
        return self._tracked(super().__mod__(value))

    def __rmod__(self, value: int) -> "TrackedInteger":
        return self._tracked(super().__rmod__(value))

    def __neg__(self) -> "TrackedInteger":
        return self._tracked(super().__neg__())

    def __abs__(self) -> "TrackedInteger":
        return self._tracked(super().__abs__())


@dataclass(frozen=True)
class Snapshot:
    """Immutable record of a TrackedArray's contents and counters at one moment.

    One snapshot is one frame for the visualiser.

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

    >>> stats = Stats()
    >>> arr = TrackedArray([TrackedInteger(v, stats) for v in (3, 1, 2)], stats)
    >>> arr.swap(0, 2)
    >>> arr.snapshot()
    Snapshot(values=(2, 1, 3), reads=2, writes=2, comparisons=0)
    >>> arr.append(TrackedInteger(4, stats))
    Traceback (most recent call last):
        ...
    TypeError: append would resize the array being measured
    >>> head = arr[:2]
    >>> type(head).__name__, head.stats is stats
    ('TrackedArray', True)
    """

    @icontract.require(
        lambda data: len({id(element.stats) for element in data}) <= 1,
        "every element must carry the same Stats",
    )
    @icontract.require(
        lambda data, stats: stats is None or not data or data[0].stats is stats,
        "stats must be the Stats the elements already carry",
    )
    def __init__(self, data: list[TrackedInteger], stats: Stats | None = None) -> None:
        super().__init__(data)
        self.stats = stats if stats is not None else self._shared_stats(data)
        self._original_length = len(self)

    @staticmethod
    def _shared_stats(data: list[TrackedInteger]) -> Stats:
        """The Stats the elements share, or a fresh one when there are none."""
        return data[0].stats if data else Stats()

    def _reject(self, operation: str, effect: str) -> NoReturn:
        """Refuse an operation that would leave the counters lying."""
        raise TypeError(f"{operation} would {effect} the array being measured")

    @overload
    def __getitem__(self, index: SupportsIndex) -> TrackedInteger: ...

    @overload
    def __getitem__(self, index: slice) -> "TrackedArray": ...

    def __getitem__(
        self, index: SupportsIndex | slice
    ) -> "TrackedInteger | TrackedArray":
        if isinstance(index, slice):
            items = super().__getitem__(index)

            for _ in items:
                self.stats.on_read()

            return TrackedArray(items, self.stats)

        self.stats.on_read()
        return super().__getitem__(index)

    @overload
    def __setitem__(self, index: SupportsIndex, value: TrackedInteger) -> None: ...

    @overload
    def __setitem__(self, index: slice, value: Iterable[TrackedInteger]) -> None: ...

    def __setitem__(
        self,
        index: SupportsIndex | slice,
        value: "TrackedInteger | Iterable[TrackedInteger]",
    ) -> None:
        if isinstance(index, slice):
            values = list(value)  # type: ignore[arg-type]

            if len(values) != len(range(*index.indices(len(self)))):
                self._reject("slice assignment of a different length", "resize")

            for _ in values:
                self.stats.on_write()

            super().__setitem__(index, values)
            return

        self.stats.on_write()
        super().__setitem__(index, value)  # type: ignore[assignment]

    def swap(self, i: int, j: int) -> None:
        """Swap the elements at indices i and j."""
        self[i], self[j] = self[j], self[i]

    def copy(self) -> "TrackedArray":
        """Return a TrackedArray of the same elements, billing one read each."""
        return self[:]

    # rejected: an algorithm may not resize the array it was handed
    def append(self, value: TrackedInteger) -> NoReturn:
        self._reject("append", "resize")

    def extend(self, values: Iterable[TrackedInteger]) -> NoReturn:
        self._reject("extend", "resize")

    def insert(self, index: SupportsIndex, value: TrackedInteger) -> NoReturn:
        self._reject("insert", "resize")

    def pop(self, index: SupportsIndex = -1) -> NoReturn:
        self._reject("pop", "resize")

    def remove(self, value: TrackedInteger) -> NoReturn:
        self._reject("remove", "resize")

    def clear(self) -> NoReturn:
        self._reject("clear", "resize")

    def __delitem__(self, index: SupportsIndex | slice) -> NoReturn:
        self._reject("deleting an element", "resize")

    def __iadd__(self, values: Iterable[TrackedInteger]) -> NoReturn:  # type: ignore[misc,override]
        self._reject("+=", "resize")

    def __imul__(self, count: SupportsIndex) -> NoReturn:
        self._reject("*=", "resize")

    # rejected: moves every element in C, so the counters never see the work
    def reverse(self) -> NoReturn:
        self._reject("reverse", "silently rewrite")

    @icontract.require(lambda size: size >= 0)
    def buffer(self, size: int = 0) -> "TrackedArray":
        """Return zero-filled scratch space that bills to this array's stats.

        Useful for out-of-place algorithms.

        >>> stats = Stats()
        >>> arr = TrackedArray([TrackedInteger(v, stats) for v in (3, 1)], stats)
        >>> buf = arr.buffer(2)
        >>> buf[0] = arr[0]
        >>> stats.reads, stats.writes
        (1, 1)
        """
        return TrackedArray(
            [TrackedInteger(0, self.stats) for _ in range(size)], self.stats
        )

    @icontract.ensure(
        lambda self, result: len(result.values) == self._original_length,
        "array was resized",
    )
    def snapshot(self) -> Snapshot:
        """Capture contents and counters, verifying the array is still intact.

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

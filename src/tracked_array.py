import operator
from collections.abc import Iterable
from typing import NoReturn, SupportsIndex, overload

import icontract

from metrics import DEFAULT_MARK_COLOR, Color, Snapshot, Stats, Touch
from tracked_integer import TrackedInteger


class TrackedArray(list[TrackedInteger]):
    """A list of TrackedInteger that records reads and writes.

    >>> stats = Stats()
    >>> arr = TrackedArray([TrackedInteger(v, stats) for v in (3, 1, 2)], stats)
    >>> arr.swap(0, 2)
    >>> snap = arr.snapshot()
    >>> snap.values, (snap.reads, snap.writes, snap.comparisons)
    ((2, 1, 3), (2, 2, 0))
    >>> [(index, str(touch)) for index, touch in snap.touches]
    [(2, 'read'), (0, 'read'), (0, 'write'), (2, 'write')]
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
        self._touches: list[tuple[int, Touch]] = []
        self._marks: dict[int, Color] = {}
        self.current_algo = ""
        self.status = ""

    @staticmethod
    def _shared_stats(data: list[TrackedInteger]) -> Stats:
        """The Stats the elements share, or a fresh one when there are none."""
        return data[0].stats if data else Stats()

    def _reject(self, operation: str, effect: str) -> NoReturn:
        """Refuse an operation that would leave the counters lying."""
        raise TypeError(f"{operation} would {effect} the array being measured")

    def _normalise(self, index: SupportsIndex) -> int:
        """Turn any in-range index into its non-negative equivalent."""
        return operator.index(index) % len(self)

    def _record(self, index: SupportsIndex, touch: Touch) -> None:
        """Remember which slot an access hit, for the next snapshot."""
        self._touches.append((self._normalise(index), touch))

    @overload
    def __getitem__(self, index: SupportsIndex) -> TrackedInteger: ...

    @overload
    def __getitem__(self, index: slice) -> "TrackedArray": ...

    def __getitem__(
        self, index: SupportsIndex | slice
    ) -> "TrackedInteger | TrackedArray":
        if isinstance(index, slice):
            items = super().__getitem__(index)

            for position in range(*index.indices(len(self))):
                self.stats.on_read()
                self._touches.append((position, Touch.READ))

            return TrackedArray(items, self.stats)

        # access first: an out-of-range index must raise before it is recorded
        value = super().__getitem__(index)
        self.stats.on_read()
        self._record(index, Touch.READ)
        return value

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
            positions = range(*index.indices(len(self)))

            if len(values) != len(positions):
                self._reject("slice assignment of a different length", "resize")

            super().__setitem__(index, values)

            for position in positions:
                self.stats.on_write()
                self._touches.append((position, Touch.WRITE))

            return

        super().__setitem__(index, value)  # type: ignore[assignment]
        self.stats.on_write()
        self._record(index, Touch.WRITE)

    def swap(self, i: int, j: int) -> None:
        """Swap the elements at indices i and j."""
        self[i], self[j] = self[j], self[i]

    def set_current_algo(self, algo: str) -> None:
        """Name the algorithm at work, for the visualiser to show.

        >>> stats = Stats()
        >>> arr = TrackedArray([TrackedInteger(v, stats) for v in (3, 1)], stats)
        >>> arr.set_current_algo("bubble sort")
        >>> arr.snapshot().current_algo
        'bubble sort'
        >>> stats.reads, stats.writes
        (0, 0)
        """
        self.current_algo = algo

    def set_status(self, status: str) -> None:
        """Say what the algorithm is doing, for the visualiser to show.
        Set to empty string to clear
        """
        self.status = status

    def copy(self) -> "TrackedArray":
        """Return a TrackedArray of the same elements, billing one read each."""
        return self[:]

    # marking: annotation for the visualiser, never billed to the counters
    @icontract.require(
        lambda self, index: -len(self) <= operator.index(index) < len(self),
        "index out of range",
    )
    def mark(self, index: SupportsIndex, color: Color = DEFAULT_MARK_COLOR) -> None:
        """Colour one slot until it is unmarked.

        >>> stats = Stats()
        >>> arr = TrackedArray([TrackedInteger(v, stats) for v in (3, 1, 2)], stats)
        >>> arr.mark(0)
        >>> arr.mark(-1, (0, 255, 0))
        >>> arr.snapshot().marks
        ((0, (255, 0, 0)), (2, (0, 255, 0)))
        >>> stats.reads, stats.writes
        (0, 0)
        """
        self._marks[self._normalise(index)] = color

    @icontract.require(
        lambda self, index: -len(self) <= operator.index(index) < len(self),
        "index out of range",
    )
    def unmark(self, index: SupportsIndex) -> None:
        """Drop the colour on one slot

        >>> stats = Stats()
        >>> arr = TrackedArray([TrackedInteger(v, stats) for v in (3, 1)], stats)
        >>> arr.mark(0)
        >>> arr.unmark(0)
        >>> arr.unmark(1)
        >>> arr.snapshot().marks
        ()
        """
        self._marks.pop(self._normalise(index), None)

    def unmark_all(self) -> None:
        """Drop every colour.

        >>> stats = Stats()
        >>> arr = TrackedArray([TrackedInteger(v, stats) for v in (3, 1)], stats)
        >>> arr.mark(0)
        >>> arr.mark(1)
        >>> arr.unmark_all()
        >>> arr.snapshot().marks
        ()
        """
        self._marks.clear()

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

    def sort(self, **kwargs: object) -> NoReturn:
        self._reject("sort", "silently rewrite")

    @icontract.require(lambda size: size >= 0)
    def buffer(self, size: int = 0) -> "TrackedArray":
        """Return zero-filled scratch space that bills to this array's stats.

        Useful for out-of-place algorithms. It carries its own touches and marks,
        because index 3 of a buffer is not index 3 of the array it serves.

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
        """Capture contents, counters, and the accesses since the last snapshot."""
        snapshot = Snapshot(
            values=tuple(int(x) for x in self),
            reads=self.stats.reads,
            writes=self.stats.writes,
            comparisons=self.stats.comparisons,
            touches=tuple(self._touches),
            marks=tuple(sorted(self._marks.items())),
            current_algo=self.current_algo,
            status=self.status,
        )
        self._touches.clear()
        return snapshot


if __name__ == "__main__":
    # Example usage
    stats = Stats()
    tracked_array = TrackedArray([TrackedInteger(i, stats) for i in range(5)], stats)

    print(tracked_array.snapshot())
    tracked_array.swap(1, 3)
    print(tracked_array.snapshot())

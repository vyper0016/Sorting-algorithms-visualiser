import logging

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

from dataclasses import dataclass


@dataclass
class Stats:
    """Counters for reads, writes, and comparisons on a tracked collection.

    >>> stats = Stats()
    >>> stats.on_read()
    >>> stats.on_write()
    >>> stats.on_comparison()
    >>> stats.reads, stats.writes, stats.comparisons
    (1, 1, 1)
    """

    reads: int = 0
    writes: int = 0
    comparisons: int = 0

    def on_read(self) -> None:
        """Record one read."""
        self.reads += 1

    def on_write(self) -> None:
        """Record one write."""
        self.writes += 1

    def on_comparison(self) -> None:
        """Record one comparison."""
        self.comparisons += 1

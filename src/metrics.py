import re
from dataclasses import dataclass
from enum import StrEnum

import icontract

Color = tuple[int, int, int]

_HEX_COLOR = re.compile(r"#?[0-9a-fA-F]{6}\Z")


@icontract.require(
    lambda code: _HEX_COLOR.match(code) is not None,
    "colour must be six hex digits, optionally prefixed with #",
)
def from_hex(code: str) -> Color:
    """The (red, green, blue) channels of an #rrggbb colour.

    >>> from_hex("#ff0000")
    (255, 0, 0)
    >>> from_hex("00ff7f")
    (0, 255, 127)
    >>> from_hex("#FFFFFF")
    (255, 255, 255)
    """
    value = int(code.lstrip("#"), 16)
    return (value >> 16 & 0xFF, value >> 8 & 0xFF, value & 0xFF)


DEFAULT_MARK_COLOR: Color = from_hex("#ff0000")


class Touch(StrEnum):
    """What an access did to a slot, so the visualiser can colour it."""

    READ = "read"
    WRITE = "write"


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


@dataclass(frozen=True)
class Snapshot:
    """Immutable record of a TrackedArray's contents and counters at one moment.

    One snapshot is one frame for the visualiser.

    >>> snap = Snapshot((3, 1, 2), reads=4, writes=2, comparisons=7)
    >>> snap.values
    (3, 1, 2)
    >>> snap.reads, snap.writes, snap.comparisons
    (4, 2, 7)
    >>> snap.touches, snap.marks
    ((), ())
    >>> snap.current_algo, snap.status
    ('', '')
    """

    values: tuple[int, ...]
    reads: int
    writes: int
    comparisons: int
    touches: tuple[tuple[int, Touch], ...] = ()
    marks: tuple[tuple[int, Color], ...] = ()
    current_algo: str = ""
    status: str = ""

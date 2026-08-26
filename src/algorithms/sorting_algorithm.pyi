from collections.abc import Iterator

from metrics import Snapshot
from tracked_array import TrackedArray

def sorting_algorithm(array: TrackedArray) -> Iterator[Snapshot]:
    """Sort `array` in place, yielding a Snapshot at every drawable step."""
    ...

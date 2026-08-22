from collections.abc import Iterator

from tracked_array import Snapshot, TrackedArray

def sorting_algorithm(array: TrackedArray) -> Iterator[Snapshot]:
    """Sort `array` in place, yielding a Snapshot at every drawable step."""
    ...

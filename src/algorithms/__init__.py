"""Discovery of the tracked sorting algorithms in this package.

Every generator function defined at the top level of a module in this package
is treated as a sorting algorithm, so a new file needs no registration.

>>> "bubble_sort" in ALGORITHMS
True
>>> ALGORITHMS["bubble_sort"].__module__
'algorithms.sorts'
"""

import importlib
import inspect
import pkgutil
from collections.abc import Callable, Iterator
from typing import TypeVar

from metrics import Snapshot
from tracked_array import TrackedArray

SortingAlgorithm = Callable[[TrackedArray], Iterator[Snapshot]]

F = TypeVar("F", bound=SortingAlgorithm)

_untested_names: set[str] = set()


def untested(function: F) -> F:
    """Mark a sorting algorithm as excluded from the automated test suite."""
    _untested_names.add(function.__name__)
    return function


def discover_algorithms() -> dict[str, SortingAlgorithm]:
    """Import every module in this package and collect its generator functions.

    Private names and functions merely imported into a module are skipped.
    """
    found: dict[str, SortingAlgorithm] = {}

    for module_info in pkgutil.iter_modules(__path__):
        module = importlib.import_module(f"{__name__}.{module_info.name}")

        for name, function in inspect.getmembers(module, inspect.isgeneratorfunction):
            if not name.startswith("_") and function.__module__ == module.__name__:
                found[name] = function

    return dict(sorted(found.items()))


ALGORITHMS: dict[str, SortingAlgorithm] = discover_algorithms()

TESTABLE_ALGORITHMS: dict[str, SortingAlgorithm] = {
    name: algorithm
    for name, algorithm in ALGORITHMS.items()
    if name not in _untested_names
}

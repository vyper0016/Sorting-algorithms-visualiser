# Writing a tracked algorithm

Every algorithm here follows the contract in
[sorting_algorithm.pyi](sorting_algorithm.pyi):

```python
def sorting_algorithm(array: TrackedArray) -> Iterator[Snapshot]: ...
```

## What differs from a normal implementation

| Normal | Tracked |
| --- | --- |
| Returns a new sorted list | Sorts `array` **in place** and returns nothing |
| Runs to completion | Is a **generator**: `yield array.snapshot()` at every step the visualiser should draw |
| Any container works | Takes a `TrackedArray`, so `[]`, `[] =` and `swap` count reads/writes |
| Free to build new values | May only **permute** the elements it was given |

Details:

- **Yield frames, don't return.** One `yield array.snapshot()` = one animation
  frame. `snapshot()` is O(n), so yield per comparison/swap, not per element
  touched.
- **Sort in place.** No `return sorted(array)`, no reassigning `array`. The
  caller keeps a reference to the same object.
- **Go through the array.** `array[j]` counts a read, `array[j] = x` a write,
  `array.swap(i, j)` two of each. Copying into a plain local list and sorting
  there hides the work from the counters.
- **Compare with operators.** `TrackedInteger` counts comparisons in `<`, `>`,
  `<=`, `>=`, `==`. `sorted()`, `list.sort()` and `heapq` use those too, but
  they do the sorting for you — write the loops yourself.
- **Write back only elements you took out.** `snapshot()` asserts the array is
  still the same length and the same multiset of values (an `icontract`
  postcondition). Inserting a fresh `int` or a sentinel raises there, not where
  the bug is. Temporaries (merge buffers, pivots) are fine as long as everything
  ends up back in the array.
- **Handle size 0 and 1** — they must yield no frames.

## Registration

None needed. [__init__.py](__init__.py) imports every module in this package and
collects each public generator function it defines into `ALGORITHMS`, keyed by
function name:

```python
from algorithms import ALGORITHMS   # {"bubble_sort": <function bubble_sort>, ...}
```

So drop the function into `sorts.py` or a new module beside it and it is picked
up by the visualiser and by the shared suite in
[test_sorts.py](../../tests/test_sorts.py). Consequences:

- The function must be a generator (contain a `yield`) � a plain `def` is
  invisible to discovery.
- Helper generators need a leading underscore, or they are collected as
  algorithms too. Helpers imported from another module are skipped already.

## Minimal bubble sort

Untracked:

```python
def bubble_sort(array: list[int]) -> list[int]:
    n = len(array)
    for i in range(n):
        for j in range(n - i - 1):
            if array[j] > array[j + 1]:
                array[j], array[j + 1] = array[j + 1], array[j]
    return array
```

Tracked — same loops, three changes: generator, `swap`, `yield`:

```python
def bubble_sort(array: TrackedArray) -> Iterator[Snapshot]:
    """Sort `array` ascending in place, yielding a Snapshot per comparison."""
    n = len(array)
    for i in range(n):
        for j in range(n - i - 1):
            if array[j] > array[j + 1]:
                array.swap(j, j + 1)
            yield array.snapshot()
```

Drive it by exhausting the generator:

```python
arr = generate_random_array(10)
frames = list(bubble_sort(arr))   # or `for frame in ...` to draw each one
```

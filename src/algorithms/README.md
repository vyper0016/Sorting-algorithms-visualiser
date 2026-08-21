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
| Free to allocate scratch lists | Takes scratch space from `array.buffer(n)`, so work done in it still counts |
| Free to build new values | Must end with the **same elements** it was given |

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
- **Take scratch space from the array.** Out-of-place algorithms need somewhere
  to put elements: `buf = array.buffer(n)` gives a zero-filled `TrackedArray`
  that bills its reads and writes to the same counters, so the totals stay
  honest. Buffers are never drawn — only the array you were handed is. A plain
  `[0] * n` works too, but hides that work from the counters.
- **Write back only elements you took out.** `append`, `extend`, `insert`,
  `pop`, `remove`, `clear`, `del arr[i]`, `arr += ...`, `arr *= ...` and a
  slice assignment that changes the length all raise `TypeError` where you call
  them — an algorithm may not resize the array it was handed. `reverse()` is
  refused too: it would move every element in C without counting a write.
  `snapshot()` still checks the length as a last line of defence, for a resize
  that went round the API. Values are checked per frame by the shared suite
  instead: a frame may not contain a value the input did not. Mid-merge a value
  may legitimately appear twice — while it is being copied back out of a
  buffer, memory really does hold it twice — so it is the finished array that
  must be a permutation of the input.

  Not refused, but still a hole: `arr.sort()` counts its comparisons and none
  of its writes, and does the algorithm for you. Don't.

- **Slices and arithmetic stay tracked.** `arr[i:j]` bills one read per element
  copied and hands back a `TrackedArray` on the same counters, not a plain
  list; `arr.copy()` is the same thing. `TrackedInteger` arithmetic (`+`, `-`,
  `*`, `//`, `%`, unary `-`, `abs`) returns a `TrackedInteger` on the same
  `Stats`, so a derived value keeps counting its comparisons.
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

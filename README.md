# Sorting algorithms visualiser

Visualise sorting algorithms with sound.
A Python take on
[The Sound of Sorting](https://panthema.net/2013/sound-of-sorting/).

The algorithms sort a `TrackedArray`, a list-like class that counts every read,
write and comparison, so the picture and the counters come from the algorithm
itself rather than from a separate trace.

## Demo

Bars are coloured by their last access: green a read, red a write, anything else
a mark the algorithm set. The header line holds the live counters.

![Gnome sort, n = 39](demo/gnome_sort.gif)

<video src="demo/merge_sort.mp4" controls muted loop width="720"></video>

<video src="demo/tim_sort_n_546.mp4" controls muted loop width="720"></video>

All three came out of the **Export…** button. The MP4s carry the sound track —
[merge sort, `n = 64`](demo/merge_sort.mp4) and
[tim sort, `n = 546`](demo/tim_sort_n_546.mp4); GIF exports are silent.

## Features

* 22 algorithms, from `bubble_sort` to `tim_sort`, `radix_sort_msd` and
  `bogo_sort` — discovered by name, so a new module needs no registration
* Reads, writes and comparisons counted by the array itself, shown live
* Five starting distributions, a seed for a repeatable run, sizes up to 2048
* One tone per snapshot, with volume, sustain and pitch to hand
* Every setting applies mid-run; Pydantic reports a bad value in the window
* MP4 and GIF export, and display profiles saved to JSON
* The settings windows follow the system light or dark theme; the bars keep
  the colours set in **Settings…**

![The configurator](demo/configurator.png)

The settings and the transport buttons. Start / Pause runs the algorithm, Step
advances one snapshot, Reset builds a fresh array.

| ![Export a run](demo/export_dialog.png) | ![Display settings](demo/display_settings.png) |
| --- | --- |
| **Export…** — format, size, frame rate and a length cap | **Settings…** — colours, font size, and which labels show |

## Requirements

* Python 3.11 or newer
* Tk — bundled with the python.org installers on Windows and macOS; on Debian or
  Ubuntu install `python3-tk` separately

Everything else is pulled in by `pip`. Video export uses the `ffmpeg` binary that
ships inside `imageio-ffmpeg`, so no system install is needed.

## Installation

```sh
python -m venv .venv
.venv\Scripts\activate      # Windows;  source .venv/bin/activate  elsewhere
pip install .
```

For development, install the extra tooling and the git hooks as well:

```sh
pip install -e ".[dev]"
pre-commit install
```

## Running

After `pip install .`:

```sh
sortvis
```

From a checkout, without installing:

```sh
python src/gui.py
```

On Windows, double-clicking `src/main.pyw` starts it without a console window.

Two windows open: the **configurator** shown above, and the pygame window that
draws the array.

## Writing your own algorithm

Drop a generator function into [src/algorithms/sorts.py](src/algorithms/sorts.py)
or a new module beside it — it is discovered by name, no registration needed:

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

[src/algorithms/README.md](src/algorithms/README.md) describes the full contract:
what `TrackedArray` counts, how to take scratch space that still counts, how to
colour slots, and which list methods are refused.

## Project layout

| Path | Contents |
| --- | --- |
| [src/tracked_array.py](src/tracked_array.py) | The counting array handed to every algorithm |
| [src/tracked_integer.py](src/tracked_integer.py) | An `int` whose comparisons and arithmetic are counted |
| [src/algorithms/](src/algorithms/) | The algorithms, discovered automatically |
| [src/config.py](src/config.py) | Pydantic settings models |
| [src/configurator.py](src/configurator.py) | The CustomTkinter settings window |
| [src/dialogs.py](src/dialogs.py) | The export and display windows it opens |
| [src/forms.py](src/forms.py) | Widgets bound to a settings model, shared by all three |
| [src/gui.py](src/gui.py) | The pygame window and the main loop |
| [src/painter.py](src/painter.py) | Drawing one snapshot |
| [src/audio.py](src/audio.py) | Tone synthesis |
| [src/export.py](src/export.py) | MP4 and GIF rendering |
| [tests/](tests/) | pytest suite; doctests live in the modules |
| [demo/](demo/) | The clips and screenshots shown above |

## Development

```sh
pytest                 # unit tests and doctests
mypy --strict src tests
ruff check .
ruff format .
interrogate -c pyproject.toml src
```

`pre-commit` runs all of these on commit; see
[.pre-commit-config.yaml](.pre-commit-config.yaml).

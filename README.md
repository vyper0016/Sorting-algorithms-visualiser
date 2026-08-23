# Sorting algorithms visualiser

Visualise sorting algorithms with sound.
A Python take on
[The Sound of Sorting](https://panthema.net/2013/sound-of-sorting/).

The algorithms sort a `TrackedArray`, a list-like class that counts every read,
write and comparison, so the picture and the counters come from the algorithm
itself rather than from a separate trace.

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

Two windows open. The **configurator** holds the settings and the transport
buttons; the **pygame window** draws the array.

| Button | Effect |
| --- | --- |
| Start / Pause | Run or hold the algorithm |
| Step | Advance one snapshot while paused |
| Reset | Build a fresh array from the current settings |
| Export… | Write the run to an MP4 or GIF file |
| Settings… | Change the font size, the colours, and which labels show |

Every setting applies while a run is in flight: algorithm, starting distribution,
array size, seed, delay per step, and the volume, sustain and pitch of the sound.
Values are validated by Pydantic, so an out-of-range entry is reported in the
window instead of crashing the program.

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

import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import customtkinter as ctk
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from algorithms import ALGORITHMS
from generator import (
    generate_random_array,
    generate_range_array,
    generate_shuffled_array,
)
from tracked_array import TrackedArray

_ERROR_COLOR = "#ff5555"
_LABEL_GRID: dict[str, Any] = {"sticky": "w", "padx": 8, "pady": 4}
_MAX_STEPS = 2000


def _step_count(low: float, high: float, steps: int | None, integer: bool) -> int:
    """How many detents a slider over `low`..`high` gets."""
    if steps is not None:
        return steps

    span = high - low

    if integer:
        return max(1, round(span))

    return max(1, min(round(span * 100), _MAX_STEPS))


class Distribution(StrEnum):
    """The shape of the array a run starts from.

    The values of every distribution span roughly the array's own length, so a
    bar chart of one looks like a bar chart of any other. RANDOM_DISTINCT draws
    from twice that range, which is what keeps it from being a permutation of
    0..n-1 like SHUFFLED.
    """

    ASCENDING = "ascending"
    DESCENDING = "descending"
    RANDOM = "random"
    RANDOM_DISTINCT = "random distinct"
    SHUFFLED = "shuffled"


class Config(BaseModel):
    """Validated settings of one visualisation run."""

    model_config = ConfigDict(validate_assignment=True)

    algorithm: str = "bubble_sort"
    distribution: Distribution = Distribution.SHUFFLED
    array_size: int = Field(default=2**6, ge=2, le=2**11)
    seed: int | None = None
    delay_ms: float = Field(default=50.0, ge=0.0, le=2000.0)
    sound_enabled: bool = True
    volume: float = Field(default=0.3, ge=0.0, le=1.0)
    sustain_ms: float = Field(default=80.0, ge=1.0, le=1000.0)
    pitch: float = Field(default=1.0, ge=0.01, le=1.8)

    @field_validator("algorithm")
    @classmethod
    def _known_algorithm(cls, name: str) -> str:
        """Reject a name that the algorithms package does not offer."""
        if name not in ALGORITHMS:
            raise ValueError(f"unknown algorithm {name!r}")

        return name

    def update_fields(self, **changes: Any) -> None:
        """Apply `changes` in one step, or raise ValidationError and change nothing."""
        validated = self.model_validate({**self.model_dump(), **changes})
        self.__dict__.update(validated.__dict__)

    def build_array(self) -> TrackedArray:
        """A freshly generated array for these settings.

        >>> Config(array_size=5, distribution="ascending").build_array()
        [0, 1, 2, 3, 4]
        >>> Config(array_size=5, distribution="descending").build_array()
        [4, 3, 2, 1, 0]
        >>> sorted(Config(array_size=5, distribution="shuffled").build_array())
        [0, 1, 2, 3, 4]
        >>> values = Config(array_size=6, distribution="random distinct").build_array()
        >>> len(values) == len(set(values))
        True
        >>> len(Config(array_size=6, distribution="random").build_array())
        6
        """
        size = self.array_size

        match self.distribution:
            case Distribution.ASCENDING:
                return generate_range_array(size)
            case Distribution.DESCENDING:
                return generate_range_array(size - 1, -1, -1)
            case Distribution.RANDOM:
                return generate_random_array(size, 0, size - 1, seed=self.seed)
            case Distribution.RANDOM_DISTINCT:
                return generate_random_array(
                    size, 0, 2 * size - 1, distinct=True, seed=self.seed
                )
            case Distribution.SHUFFLED:
                return generate_shuffled_array(size, seed=self.seed)


@dataclass
class Controls:
    """Playback state the visualiser polls once per frame."""

    running: bool = False
    reset_requested: bool = True
    steps_pending: int = 0

    def toggle(self) -> None:
        """Flip between running and paused."""
        self.running = not self.running

    def request_reset(self) -> None:
        """Ask the visualiser for a new array and a new run of the algorithm."""
        self.reset_requested = True

    def consume_reset(self) -> bool:
        """Whether a reset is pending, clearing the request."""
        pending = self.reset_requested
        self.reset_requested = False
        return pending

    def request_step(self) -> None:
        """Ask for one single frame, pausing a run that is under way.

        >>> controls = Controls(running=True)
        >>> controls.request_step()
        >>> controls.running, controls.steps_pending
        (False, 1)
        """
        self.running = False
        self.steps_pending += 1

    def consume_step(self) -> bool:
        """Whether a single frame is owed, spending one of them.

        >>> controls = Controls()
        >>> controls.request_step(); controls.request_step()
        >>> controls.consume_step(), controls.consume_step(), controls.consume_step()
        (True, True, False)
        """
        if self.steps_pending == 0:
            return False

        self.steps_pending -= 1
        return True


def _first_message(error: ValidationError) -> str:
    """The first complaint in `error`, without pydantic's preamble.

    >>> try:
    ...     Config(algorithm="nonexistent_sort")
    ... except ValidationError as error:
    ...     _first_message(error)
    "unknown algorithm 'nonexistent_sort'"
    """
    message: str = error.errors()[0]["msg"]
    return message.removeprefix("Value error, ")


def _parse_seed(text: str) -> int | None:
    """The seed an entry holds, where blank means a fresh random one.

    >>> _parse_seed(" 42 ")
    42
    >>> _parse_seed("   ") is None
    True
    """
    stripped = text.strip()
    return int(stripped) if stripped else None


class Configurator(ctk.CTk):  # type: ignore[misc]
    """The settings window, a second top level window beside the pygame one.

    It is driven by `pump()` from the pygame frame loop rather than by `mainloop()`
    """

    def __init__(
        self, settings: Config | None = None, controls: Controls | None = None
    ) -> None:
        super().__init__()
        self.settings = settings if settings is not None else Config()
        self.controls = controls if controls is not None else Controls()

        self._alive = True
        self._setters: dict[str, Callable[[Any], None]] = {}
        self._entries: dict[str, ctk.CTkEntry] = {}

        self.title("Sorting visualiser")
        self.geometry("470x370")
        self.grid_columnconfigure(1, weight=1)

        self._status = ctk.CTkLabel(self, text="", anchor="w")
        self._build_widgets()
        self._refresh()

        self.protocol("WM_DELETE_WINDOW", self.close)

    def _build_widgets(self) -> None:
        """Lay out every control, top to bottom."""
        row = 0
        self._add_menu(row, "Algorithm", "algorithm", list(ALGORITHMS))

        row += 1
        self._add_menu(row, "Array", "distribution", [d.value for d in Distribution])

        row += 1
        self._add_slider(
            row, "Array size", "array_size", 2, 2**11, reset=True, editable=True
        )

        row += 1
        self._add_entry(row, "Seed (blank: random)", "seed", self._apply_seed)

        row += 1
        self._add_slider(
            row, "Delay (ms)", "delay_ms", 0, 2000, integer=False, editable=True
        )

        row += 1
        self._add_switch(row, "Sound", "sound_enabled")

        row += 1
        self._add_slider(row, "Volume", "volume", 0, 1, steps=20, integer=False)

        row += 1
        self._add_slider(row, "Sustain (ms)", "sustain_ms", 1, 1000, integer=False)

        row += 1
        self._add_slider(row, "Pitch", "pitch", 0.01, 1.8, integer=False)

        row += 1
        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=row, column=0, columnspan=3, sticky="ew", padx=4, pady=(12, 4))
        buttons.grid_columnconfigure((0, 1, 2), weight=1)

        self._toggle_button = ctk.CTkButton(
            buttons, text="Start", command=self._on_toggle
        )
        self._toggle_button.grid(row=0, column=0, sticky="ew", padx=4)
        ctk.CTkButton(buttons, text="Step", command=self._on_step).grid(
            row=0, column=1, sticky="ew", padx=4
        )
        ctk.CTkButton(buttons, text="Reset", command=self._on_reset).grid(
            row=0, column=2, sticky="ew", padx=4
        )

        row += 1
        self._status.grid(row=row, column=0, columnspan=3, sticky="ew", padx=8, pady=8)

    def _add_menu(self, row: int, label: str, field: str, choices: list[str]) -> None:
        """Add a labelled drop down writing `field`, which always resets the run."""
        ctk.CTkLabel(self, text=label).grid(row=row, column=0, **_LABEL_GRID)
        menu = ctk.CTkOptionMenu(
            self,
            values=choices,
            command=lambda choice: self._apply({field: choice}, reset=True),
        )
        menu.grid(row=row, column=1, columnspan=2, sticky="ew", padx=8, pady=4)
        self._setters[field] = menu.set

    def _add_slider(
        self,
        row: int,
        label: str,
        field: str,
        low: float,
        high: float,
        steps: int | None = None,
        integer: bool = True,
        reset: bool = False,
        editable: bool = False,
    ) -> None:
        """Add a labelled slider writing `field`, with a live read-out.

        `editable` swaps the read-out for an entry the user can type a value
        into directly, committed on Return or focus loss.
        """
        ctk.CTkLabel(self, text=label).grid(row=row, column=0, **_LABEL_GRID)
        slider = ctk.CTkSlider(
            self,
            from_=low,
            to=high,
            number_of_steps=_step_count(low, high, steps, integer),
        )
        slider.grid(row=row, column=1, sticky="ew", padx=(8, 4), pady=4)

        readout: ctk.CTkEntry | ctk.CTkLabel
        if editable:
            readout = ctk.CTkEntry(self, width=48, justify="right")
        else:
            readout = ctk.CTkLabel(self, text="", width=48, anchor="e")

        readout.grid(row=row, column=2, sticky="e", padx=(0, 8), pady=4)

        def show(value: float) -> None:
            slider.set(value)

            if editable:
                readout.delete(0, "end")
                readout.insert(0, f"{value:g}")
            else:
                readout.configure(text=f"{value:g}")

        def dragged(raw: float) -> None:
            """Write the dragged value, then show whatever the settings kept."""
            self._apply({field: int(raw) if integer else round(float(raw), 2)}, reset)
            show(getattr(self.settings, field))

        slider.configure(command=dragged)
        self._setters[field] = show

        if editable:

            def commit(_event: object = None) -> None:
                """Parse the typed value and apply it, reverting if invalid."""
                text = readout.get().strip()

                try:
                    value = int(text) if integer else float(text)
                except ValueError:
                    self._report(f"{label} must be a number")
                    self._refresh()
                    return

                self._apply({field: value}, reset)
                show(getattr(self.settings, field))

            readout.bind("<Return>", commit)
            readout.bind("<FocusOut>", commit)

    def _add_entry(
        self, row: int, label: str, field: str, commit: Callable[[], None]
    ) -> None:
        """Add a labelled entry for `field`, committed on Return or focus loss."""
        ctk.CTkLabel(self, text=label).grid(row=row, column=0, **_LABEL_GRID)
        entry = ctk.CTkEntry(self)
        entry.grid(row=row, column=1, columnspan=2, sticky="ew", padx=8, pady=4)
        entry.bind("<Return>", lambda _event: commit())
        entry.bind("<FocusOut>", lambda _event: commit())

        def show(value: object) -> None:
            entry.delete(0, "end")
            entry.insert(0, "" if value is None else str(value))

        self._setters[field] = show
        self._entries[field] = entry

    def _add_switch(self, row: int, label: str, field: str) -> None:
        """Add a switch writing the boolean `field`."""
        switch = ctk.CTkSwitch(self, text=label)
        switch.configure(command=lambda: self._apply({field: bool(switch.get())}))
        switch.grid(row=row, column=0, columnspan=3, sticky="w", padx=8, pady=4)

        def show(value: bool) -> None:
            if value:
                switch.select()
            else:
                switch.deselect()

        self._setters[field] = show

    def _apply(self, changes: dict[str, Any], reset: bool = False) -> None:
        """Write `changes` to the settings, or report them and revert the widgets."""
        try:
            self.settings.update_fields(**changes)
        except ValidationError as error:
            self._report(_first_message(error))
            self._refresh()
            return

        self._report("")

        if reset:
            self.controls.request_reset()

    def _apply_seed(self) -> None:
        """Commit the seed entry, where blank means a fresh random array."""
        try:
            seed = _parse_seed(self._entries["seed"].get())
        except ValueError:
            self._report("seed must be a whole number or blank")
            self._refresh()
            return

        self._apply({"seed": seed}, reset=True)

    def _refresh(self) -> None:
        """Push every settings field back into its widget."""
        for field, setter in self._setters.items():
            setter(getattr(self.settings, field))

        self.sync()

    def sync(self) -> None:
        """Match the buttons to controls that something else changed.

        The visualiser calls this after an algorithm has run out of frames.
        """
        self._toggle_button.configure(
            text="Pause" if self.controls.running else "Start"
        )

    def _report(self, message: str) -> None:
        """Show `message` in the status line, an empty one clearing it."""
        self._status.configure(
            text=message, text_color=_ERROR_COLOR if message else ("gray10", "gray90")
        )

    def _on_toggle(self) -> None:
        """Start or pause the run."""
        self.controls.toggle()
        self._refresh()

    def _on_step(self) -> None:
        """Pause the run and advance it by a single frame."""
        self.controls.request_step()
        self._refresh()

    def _on_reset(self) -> None:
        """Throw the current run away and generate a new array."""
        self.controls.request_reset()
        self._report("")

    def get_config(self) -> Config:
        """The live settings object, shared with the visualiser."""
        return self.settings

    def pump(self) -> bool:
        """Serve pending Tk events once, False once the window is gone.

        Called once per pygame frame in place of `mainloop()`.
        """
        if not self._alive:
            return False

        try:
            self.update()
        except tk.TclError:
            self._alive = False

        return self._alive

    def close(self) -> None:
        """Stop the run and destroy the window."""
        self.controls.running = False
        self._alive = False
        self.destroy()


if __name__ == "__main__":
    Configurator().mainloop()

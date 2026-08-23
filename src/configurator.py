import threading
import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog
from typing import Any, Generic, TypeVar

import customtkinter as ctk
import pygame
from pydantic import ValidationError

from algorithms import ALGORITHMS
from config import (
    MAX_HEIGHT,
    MAX_WIDTH,
    MIN_HEIGHT,
    MIN_WIDTH,
    Config,
    Distribution,
    ExportConfig,
    FileFormat,
    ValidatedSettings,
    parse_seed,
)
from export import ExportError, render

_ERROR_COLOR = "#ff5555"
_LABEL_GRID: dict[str, Any] = {"sticky": "w", "padx": 8, "pady": 4}
_MAX_STEPS = 2000

Settings = TypeVar("Settings", bound=ValidatedSettings)


def _step_count(low: float, high: float, steps: int | None, integer: bool) -> int:
    """How many detents a slider over `low`..`high` gets."""
    if steps is not None:
        return steps

    span = high - low

    if integer:
        return max(1, round(span))

    return max(1, min(round(span * 100), _MAX_STEPS))


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


def _visualiser_size() -> tuple[int, int] | None:
    """The size the visualiser window is showing at, or None when it is closed."""
    surface = pygame.display.get_surface()
    return surface.get_size() if surface is not None else None


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


class _FieldForm(Generic[Settings]):
    """Widgets bound to the fields of one ValidatedSettings object.

    Both windows are built from these, so a value the model refuses is
    reported and reverted the same way wherever it was typed.
    """

    settings: Settings

    def _init_form(self) -> None:
        """Prepare the widget bookkeeping and the status line."""
        self._setters: dict[str, Callable[[Any], None]] = {}
        self._entries: dict[str, ctk.CTkEntry] = {}
        self._status = ctk.CTkLabel(self, text="", anchor="w")

    def _add_menu(self, row: int, label: str, field: str, choices: list[str]) -> None:
        """Add a labelled drop down writing `field`."""
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

    def _add_switch(self, row: int, label: str, field: str) -> ctk.CTkSwitch:
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
        return switch

    def _apply(self, changes: dict[str, Any], reset: bool = False) -> None:
        """Write `changes` to the settings, or report them and revert the widgets."""
        try:
            self.settings.update_fields(**changes)
        except ValidationError as error:
            self._report(_first_message(error))
            self._refresh()
            return

        self._report("")
        self._after_apply(changes, reset)

    def _after_apply(self, changes: dict[str, Any], reset: bool) -> None:
        """React to settings that were just accepted."""

    def _refresh(self) -> None:
        """Push every settings field back into its widget."""
        for field, setter in self._setters.items():
            setter(getattr(self.settings, field))

    def _report(self, message: str, error: bool = True) -> None:
        """Show `message` in the status line, an empty one clearing it."""
        normal = ("gray10", "gray90")
        self._status.configure(
            text=message, text_color=_ERROR_COLOR if message and error else normal
        )


class ExportDialog(ctk.CTkToplevel, _FieldForm[ExportConfig]):  # type: ignore[misc]
    """The second settings window, opened by the configurator's Export button."""

    def __init__(
        self, master: ctk.CTk, settings: ExportConfig, on_save: Callable[[], None]
    ) -> None:
        super().__init__(master)
        self.settings = settings
        self._on_save = on_save

        self.title("Export a run")
        self.geometry("420x300")
        self.grid_columnconfigure(1, weight=1)

        self._init_form()
        self._build_widgets()
        self._refresh()

        self.transient(master)

    def _build_widgets(self) -> None:
        """Lay out every control, top to bottom."""
        row = 0
        self._add_menu(row, "Format", "file_format", [f.value for f in FileFormat])

        row += 1
        self._add_slider(row, "Width", "width", MIN_WIDTH, MAX_WIDTH, editable=True)

        row += 1
        self._add_slider(row, "Height", "height", MIN_HEIGHT, MAX_HEIGHT, editable=True)

        row += 1
        self._add_slider(row, "Frames per second", "fps", 5, 60)

        row += 1
        self._add_slider(row, "Max length (min)", "max_minutes", 0.1, 10, integer=False)

        row += 1
        self._sound = self._add_switch(row, "Sound", "sound_enabled")

        row += 1
        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=row, column=0, columnspan=3, sticky="ew", padx=4, pady=(12, 4))
        buttons.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(buttons, text="Save…", command=self._save).grid(
            row=0, column=0, sticky="ew", padx=4
        )
        ctk.CTkButton(buttons, text="Cancel", command=self.destroy).grid(
            row=0, column=1, sticky="ew", padx=4
        )

        row += 1
        self._status.grid(row=row, column=0, columnspan=3, sticky="ew", padx=8, pady=8)

    def _after_apply(self, changes: dict[str, Any], reset: bool) -> None:
        """Grey the sound switch out for a GIF, which carries no audio."""
        self._sound.configure(
            state=(
                "normal" if self.settings.file_format is FileFormat.MP4 else "disabled"
            )
        )

    def _refresh(self) -> None:
        """Push every field back into its widget, the sound switch included."""
        super()._refresh()
        self._after_apply({}, False)

    def _save(self) -> None:
        """Hand the settings back to the configurator and close."""
        self.destroy()
        self._on_save()


class Configurator(ctk.CTk, _FieldForm[Config]):  # type: ignore[misc]
    """The settings window, a second top level window beside the pygame one.

    It is driven by `pump()` from the pygame frame loop rather than by `mainloop()`
    """

    def __init__(
        self, settings: Config | None = None, controls: Controls | None = None
    ) -> None:
        super().__init__()
        self.settings = settings if settings is not None else Config()
        self.controls = controls if controls is not None else Controls()
        self.export_settings = ExportConfig()

        self._alive = True
        self._dialog: ExportDialog | None = None
        self._worker: threading.Thread | None = None
        self._progress = ""
        self._shown = ""

        self.title("Sorting visualiser")
        self.geometry("470x400")
        self.grid_columnconfigure(1, weight=1)

        self._init_form()
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
        self._add_slider(
            row, "Sustain (ms)", "sustain_ms", 1, 1000, integer=False, editable=True
        )

        row += 1
        self._add_slider(row, "Pitch", "pitch", 0.01, 8, integer=False, editable=True)

        row += 1
        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=row, column=0, columnspan=3, sticky="ew", padx=4, pady=(12, 4))
        buttons.grid_columnconfigure((0, 1, 2, 3), weight=1)

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
        ctk.CTkButton(buttons, text="Export…", command=self._on_export).grid(
            row=0, column=3, sticky="ew", padx=4
        )

        row += 1
        self._status.grid(row=row, column=0, columnspan=3, sticky="ew", padx=8, pady=8)

    def _after_apply(self, changes: dict[str, Any], reset: bool) -> None:
        """Start the run over when the changed setting shaped the array."""
        if reset:
            self.controls.request_reset()

    def _apply_seed(self) -> None:
        """Commit the seed entry, where blank means a fresh random array."""
        try:
            seed = parse_seed(self._entries["seed"].get())
        except ValueError:
            self._report("seed must be a whole number or blank")
            self._refresh()
            return

        self._apply({"seed": seed}, reset=True)

    def _refresh(self) -> None:
        """Push every settings field back into its widget."""
        super()._refresh()
        self.sync()

    def sync(self) -> None:
        """Match the buttons to controls that something else changed.

        The visualiser calls this after an algorithm has run out of frames.
        """
        self._toggle_button.configure(
            text="Pause" if self.controls.running else "Start"
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

    def _on_export(self) -> None:
        """Open the export settings window, or raise the one already open."""
        if self._worker is not None and self._worker.is_alive():
            self._report("an export is already running")
            return

        if self._dialog is not None and self._dialog.winfo_exists():
            self._dialog.focus()
            return

        size = _visualiser_size()

        if size is not None:
            self.export_settings.match(*size)

        self._dialog = ExportDialog(self, self.export_settings, self._start_export)

    def _start_export(self) -> None:
        """Ask for a file name, then render the run to it in the background."""
        suffix = f".{self.export_settings.file_format.value}"
        chosen = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=suffix,
            filetypes=[(f"{suffix[1:].upper()} file", f"*{suffix}")],
        )

        if not chosen:
            return

        config = Config.model_validate(self.settings.model_dump())
        options = ExportConfig.model_validate(self.export_settings.model_dump())
        self._progress = "starting the export"
        self._worker = threading.Thread(
            target=self._export, args=(config, options, Path(chosen)), daemon=True
        )
        self._worker.start()

    def _export(self, config: Config, options: ExportConfig, path: Path) -> None:
        """Render one export, reporting through the status line as it goes."""
        try:
            result = render(config, options, path, self._note)
        except (ExportError, OSError) as error:
            self._note(f"export failed: {' '.join(str(error).splitlines())}")
        else:
            self._note(result.describe())

    def _note(self, message: str) -> None:
        """Leave `message` for `pump` to show, called from the worker thread."""
        self._progress = message

    def pump(self) -> bool:
        """Serve pending Tk events once, False once the window is gone.

        Called once per pygame frame in place of `mainloop()`.
        """
        if not self._alive:
            return False

        if self._progress != self._shown:
            self._shown = self._progress
            self._report(self._progress, error=self._progress.startswith("export"))

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

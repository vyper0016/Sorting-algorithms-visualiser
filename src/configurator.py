"""The main settings window and the playback state it writes."""

import threading
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog
from typing import Any

import customtkinter as ctk
import pygame

from algorithms import ALGORITHMS
from config import Config, DisplayConfig, Distribution, ExportConfig, parse_seed
from dialogs import ExportDialog, SettingsDialog
from export import ExportError, render
from forms import FieldForm, button_row


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


class Configurator(ctk.CTk, FieldForm[Config]):  # type: ignore[misc]
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
        self.display_settings = DisplayConfig()

        self._alive = True
        self._dialog: ExportDialog | None = None
        self._settings_dialog: SettingsDialog | None = None
        self._worker: threading.Thread | None = None
        self._progress = ""
        self._shown = ""
        self._done: Path | None = None

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
        transport = button_row(self, row, columns=3)
        self._toggle_button = ctk.CTkButton(
            transport, text="Start", command=self._on_toggle
        )
        self._toggle_button.grid(row=0, column=0, sticky="ew", padx=4)
        ctk.CTkButton(transport, text="Step", command=self._on_step).grid(
            row=0, column=1, sticky="ew", padx=4
        )
        ctk.CTkButton(transport, text="Reset", command=self._on_reset).grid(
            row=0, column=2, sticky="ew", padx=4
        )

        row += 1
        windows = button_row(self, row, pady=(0, 4))
        ctk.CTkButton(windows, text="Export…", command=self._on_export).grid(
            row=0, column=0, sticky="ew", padx=4
        )
        ctk.CTkButton(windows, text="Settings…", command=self._on_settings).grid(
            row=0, column=1, sticky="ew", padx=4
        )

        row += 1
        self._grid_status(row)

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
        """Open the export window, or raise the one already open."""
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

    def _on_settings(self) -> None:
        """Open the display settings window, or raise the one already open."""
        if self._settings_dialog is not None and self._settings_dialog.winfo_exists():
            self._settings_dialog.focus()
            return

        self._settings_dialog = SettingsDialog(
            self, self.display_settings, self.settings, self._refresh
        )

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
        display = DisplayConfig.model_validate(self.display_settings.model_dump())
        self._progress = "starting the export"
        self._done = None
        self._worker = threading.Thread(
            target=self._export,
            args=(config, options, display, Path(chosen)),
            daemon=True,
        )
        self._worker.start()

    def _export(
        self,
        config: Config,
        options: ExportConfig,
        display: DisplayConfig,
        path: Path,
    ) -> None:
        """Render one export, reporting through the status line as it goes."""
        try:
            result = render(config, options, path, self._note, display)
        except (ExportError, OSError) as error:
            self._note(f"export failed: {' '.join(str(error).splitlines())}")
        else:
            self._done = result.path
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

        if self._dialog is not None and self._dialog.winfo_exists():
            self._dialog.set_running(
                self._worker is not None and self._worker.is_alive()
            )

            if self._progress != self._shown:
                self._shown = self._progress
                self._dialog.show_progress(
                    self._progress,
                    error=self._progress.startswith("export"),
                    path=self._done,
                )

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

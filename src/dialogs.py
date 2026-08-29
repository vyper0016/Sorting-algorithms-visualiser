"""The two windows the configurator opens beside itself."""

from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog
from typing import Any

import customtkinter as ctk
from pydantic import ValidationError

from config import (
    MAX_HEIGHT,
    MAX_WIDTH,
    MIN_HEIGHT,
    MIN_WIDTH,
    DisplayConfig,
    ExportConfig,
    FileFormat,
    SettingsProfile,
    SoundConfig,
)
from forms import FieldForm, button_row

_JSON_FILES = [("JSON file", "*.json"), ("All files", "*.*")]

_COLORS = (
    ("Font colour", "text_color"),
    ("Background colour", "background_color"),
    ("Bar colour", "bar_color"),
    ("Read colour", "read_color"),
    ("Write colour", "write_color"),
)

_LABEL_SWITCHES = (
    ("Size", "show_size", "Reads", "show_reads"),
    ("Writes", "show_writes", "Comparisons", "show_comparisons"),
    ("Snapshots", "show_snapshots", "Delay", "show_delay"),
    ("Playback", "show_playback", "Algorithm", "show_algo"),
    ("Algorithm status", "show_status", "", ""),
)


def _describe(error: ValidationError) -> str:
    """The first complaint in `error`, named by the setting it came from.

    >>> try:
    ...     SettingsProfile.model_validate({"display": {"font_size": 2}})
    ... except ValidationError as error:
    ...     _describe(error)
    'display.font_size: Input should be greater than or equal to 8'
    """
    first = error.errors()[0]
    field = ".".join(str(part) for part in first["loc"])
    message = first["msg"].removeprefix("Value error, ")
    return f"{field}: {message}" if field else message


class ExportDialog(ctk.CTkToplevel, FieldForm[ExportConfig]):  # type: ignore[misc]
    """The export window, opened by the configurator's Export button."""

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
        self._report("exporter standby", error=False)

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
        buttons = button_row(self, row)
        self._save_button = ctk.CTkButton(buttons, text="Save…", command=self._save)
        self._save_button.grid(row=0, column=0, sticky="ew", padx=4)
        ctk.CTkButton(buttons, text="Cancel", command=self.destroy).grid(
            row=0, column=1, sticky="ew", padx=4
        )

        row += 1
        self._grid_status(row)

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
        """Hand the settings to the configurator, staying open to show progress."""
        self._on_save()

    def show_progress(
        self, message: str, error: bool = False, path: Path | None = None
    ) -> None:
        """Post one export status update, as pushed by the configurator's worker.

        `path` is the finished file, offered beside the message as a link.
        """
        self._report(message, error=error)

        if path is not None:
            self._offer_open(path)

    def set_running(self, running: bool) -> None:
        """Grey the Save button out while an export is under way."""
        self._save_button.configure(state="disabled" if running else "normal")


class SettingsDialog(ctk.CTkToplevel, FieldForm[DisplayConfig]):  # type: ignore[misc]
    """The look window, opened by the configurator's Settings button.

    What it writes is read again by the next painted frame, so no restart.
    """

    def __init__(
        self,
        master: ctk.CTk,
        settings: DisplayConfig,
        sound: SoundConfig,
        on_import: Callable[[], None],
    ) -> None:
        super().__init__(master)
        self.settings = settings
        self.sound = sound
        self._on_import = on_import

        self.title("Display settings")
        self.geometry("370x455")
        self.grid_columnconfigure(1, weight=1)

        self._init_form()
        self._build_widgets()
        self._refresh()

        self.transient(master)

    def _build_widgets(self) -> None:
        """Lay out every control, top to bottom."""
        row = 0
        self._add_number(row, "Font size", "font_size")

        for label, field in _COLORS:
            row += 1
            self._add_color(row, label, field)

        for left, left_field, right, right_field in _LABEL_SWITCHES:
            row += 1
            self._add_switch(row, left, left_field, column=0, span=1)

            if right:
                self._add_switch(row, right, right_field, column=1, span=2)

        row += 1
        buttons = button_row(self, row)
        ctk.CTkButton(buttons, text="Defaults", command=self._restore).grid(
            row=0, column=0, sticky="ew", padx=4
        )
        ctk.CTkButton(buttons, text="Close", command=self.destroy).grid(
            row=0, column=1, sticky="ew", padx=4
        )

        row += 1
        transfer = button_row(self, row, pady=(0, 4))
        ctk.CTkButton(transfer, text="Export…", command=self._export).grid(
            row=0, column=0, sticky="ew", padx=4
        )
        ctk.CTkButton(transfer, text="Import…", command=self._import).grid(
            row=0, column=1, sticky="ew", padx=4
        )

        row += 1
        self._grid_status(row)

    def _restore(self) -> None:
        """Put every setting back the way it started."""
        self._apply(DisplayConfig().model_dump())
        self._refresh()

    def _export(self) -> None:
        """Ask for a file name and write these settings to it as JSON."""
        chosen = filedialog.asksaveasfilename(
            parent=self, defaultextension=".json", filetypes=_JSON_FILES
        )

        if not chosen:
            return

        profile = SettingsProfile.capture(self.settings, self.sound)

        try:
            Path(chosen).write_text(profile.model_dump_json(indent=2), encoding="utf-8")
        except OSError as error:
            self._report(f"could not save: {error.strerror or error}")
            return

        self._report(f"saved to {Path(chosen).name}", error=False)
        self._offer_open(Path(chosen))

    def _import(self) -> None:
        """Read a settings file back, leaving everything as it was if it is bad."""
        chosen = filedialog.askopenfilename(parent=self, filetypes=_JSON_FILES)

        if not chosen:
            return

        try:
            profile = SettingsProfile.model_validate_json(
                Path(chosen).read_text(encoding="utf-8")
            )
        except OSError as error:
            self._report(f"could not read: {error.strerror or error}")
            return
        except UnicodeDecodeError:
            self._report("that file is not text")
            return
        except ValidationError as error:
            self._report(_describe(error))
            return

        profile.apply_to(self.settings, self.sound)
        self._refresh()
        self._on_import()
        self._report(f"loaded {Path(chosen).name}", error=False)

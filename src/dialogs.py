"""The two windows the configurator opens beside itself."""

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from config import (
    MAX_HEIGHT,
    MAX_WIDTH,
    MIN_HEIGHT,
    MIN_WIDTH,
    DisplayConfig,
    ExportConfig,
    FileFormat,
)
from forms import FieldForm, button_row

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


class ExportDialog(ctk.CTkToplevel, FieldForm[ExportConfig]):  # type: ignore[misc]
    """The export window, opened by the configurator's Export button."""

    def __init__(
        self, master: ctk.CTk, settings: ExportConfig, on_save: Callable[[], None]
    ) -> None:
        super().__init__(master)
        self.settings = settings
        self._on_save = on_save

        self.title("Export a run")
        self.geometry("420x260")
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
        buttons = button_row(self, row)
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


class SettingsDialog(ctk.CTkToplevel, FieldForm[DisplayConfig]):  # type: ignore[misc]
    """The look window, opened by the configurator's Settings button.

    What it writes is read again by the next painted frame, so no restart.
    """

    def __init__(self, master: ctk.CTk, settings: DisplayConfig) -> None:
        super().__init__(master)
        self.settings = settings

        self.title("Display settings")
        self.geometry("370x420")
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
        self._status.grid(row=row, column=0, columnspan=3, sticky="ew", padx=8, pady=8)

    def _restore(self) -> None:
        """Put every setting back the way it started."""
        self._apply(DisplayConfig().model_dump())
        self._refresh()

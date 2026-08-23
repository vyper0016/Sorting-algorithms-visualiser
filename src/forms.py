"""The widget layer every settings window is built from."""

import tkinter as tk
from collections.abc import Callable
from tkinter import colorchooser
from typing import Any, Generic, TypeVar, cast

import customtkinter as ctk
from pydantic import ValidationError

from config import ValidatedSettings

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


def button_row(
    window: Any, row: int, columns: int = 2, pady: tuple[int, int] = (12, 4)
) -> ctk.CTkFrame:
    """An evenly split frame holding one row of buttons."""
    frame = ctk.CTkFrame(window, fg_color="transparent")
    frame.grid(row=row, column=0, columnspan=3, sticky="ew", padx=4, pady=pady)
    frame.grid_columnconfigure(tuple(range(columns)), weight=1)
    return frame


def _first_message(error: ValidationError) -> str:
    """The first complaint in `error`, without pydantic's preamble.

    >>> from config import Config
    >>> try:
    ...     Config(algorithm="nonexistent_sort")
    ... except ValidationError as error:
    ...     _first_message(error)
    "unknown algorithm 'nonexistent_sort'"
    """
    message: str = error.errors()[0]["msg"]
    return message.removeprefix("Value error, ")


class FieldForm(Generic[Settings]):
    """Widgets bound to the fields of one ValidatedSettings object.

    Every window is built from these, so a value the model refuses is
    reported and reverted the same way wherever it was typed.
    """

    settings: Settings

    def _init_form(self) -> None:
        """Prepare the widget bookkeeping and the status line."""
        self._setters: dict[str, Callable[[Any], None]] = {}
        self._entries: dict[str, ctk.CTkEntry] = {}
        self._status = ctk.CTkLabel(self, text="", anchor="w")

    def _on_commit(self, entry: ctk.CTkEntry, commit: Callable[[], None]) -> None:
        """Run `commit` on Return and on focus loss."""
        entry.bind("<Return>", lambda _event: commit())
        entry.bind("<FocusOut>", lambda _event: commit())

    def _number_commit(
        self,
        entry: ctk.CTkEntry,
        label: str,
        field: str,
        show: Callable[[Any], None],
        integer: bool,
        reset: bool = False,
    ) -> Callable[[], None]:
        """A commit that parses `entry` into `field`, then shows what stuck."""

        def commit() -> None:
            text = entry.get().strip()

            try:
                value = int(text) if integer else float(text)
            except ValueError:
                self._report(f"{label} must be a number")
                self._refresh()
                return

            self._apply({field: value}, reset)
            show(getattr(self.settings, field))

        return commit

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

        `editable` swaps the read-out for an entry the user can type into.
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

            if isinstance(readout, ctk.CTkEntry):
                readout.delete(0, "end")
                readout.insert(0, f"{value:g}")
            else:
                readout.configure(text=f"{value:g}")

        def dragged(raw: float) -> None:
            self._apply({field: int(raw) if integer else round(float(raw), 2)}, reset)
            show(getattr(self.settings, field))

        slider.configure(command=dragged)
        self._setters[field] = show

        if isinstance(readout, ctk.CTkEntry):
            self._on_commit(
                readout,
                self._number_commit(readout, label, field, show, integer, reset),
            )

    def _add_entry(
        self, row: int, label: str, field: str, commit: Callable[[], None]
    ) -> None:
        """Add a labelled entry for `field`, committed by `commit`."""
        ctk.CTkLabel(self, text=label).grid(row=row, column=0, **_LABEL_GRID)
        entry = ctk.CTkEntry(self)
        entry.grid(row=row, column=1, columnspan=2, sticky="ew", padx=8, pady=4)
        self._on_commit(entry, commit)

        def show(value: object) -> None:
            entry.delete(0, "end")
            entry.insert(0, "" if value is None else str(value))

        self._setters[field] = show
        self._entries[field] = entry

    def _add_number(self, row: int, label: str, field: str) -> None:
        """Add a labelled entry for the whole number `field`."""
        ctk.CTkLabel(self, text=label).grid(row=row, column=0, **_LABEL_GRID)
        entry = ctk.CTkEntry(self, width=64, justify="right")
        entry.grid(row=row, column=1, sticky="w", padx=8, pady=4)

        def show(value: int) -> None:
            entry.delete(0, "end")
            entry.insert(0, str(value))

        self._on_commit(entry, self._number_commit(entry, label, field, show, True))
        self._setters[field] = show

    def _add_color(self, row: int, label: str, field: str) -> None:
        """Add a labelled hex entry for `field`, beside a swatch that opens a picker."""
        ctk.CTkLabel(self, text=label).grid(row=row, column=0, **_LABEL_GRID)
        entry = ctk.CTkEntry(self)
        entry.grid(row=row, column=1, sticky="ew", padx=(8, 4), pady=4)
        swatch = ctk.CTkButton(self, text="", width=40, border_width=1)
        swatch.grid(row=row, column=2, sticky="e", padx=(0, 8), pady=4)

        def show(value: str) -> None:
            entry.delete(0, "end")
            entry.insert(0, value)
            swatch.configure(fg_color=value, hover_color=value)

        def write(color: str) -> None:
            self._apply({field: color})
            show(getattr(self.settings, field))

        def pick() -> None:
            chosen = colorchooser.askcolor(
                color=getattr(self.settings, field), parent=cast(tk.Misc, self)
            )[1]

            if chosen:
                write(chosen)

        self._on_commit(entry, lambda: write(entry.get()))
        swatch.configure(command=pick)
        self._setters[field] = show

    def _add_switch(
        self, row: int, label: str, field: str, column: int = 0, span: int = 3
    ) -> ctk.CTkSwitch:
        """Add a switch writing the boolean `field`."""
        switch = ctk.CTkSwitch(self, text=label)
        switch.configure(command=lambda: self._apply({field: bool(switch.get())}))
        switch.grid(row=row, column=column, columnspan=span, sticky="w", padx=8, pady=4)

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

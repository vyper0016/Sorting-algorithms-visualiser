"""Painting one Snapshot onto a surface, shared by the window and the export."""

import pygame

from config import DisplayConfig
from metrics import Color, Snapshot, Touch, from_hex

_MIN_SPAN_FOR_GAP = 3.0
_MARGIN = 8
_MONOSPACE = "consolas,dejavusansmono,liberationmono,couriernew,monospace"


def _touch_colors(snapshot: Snapshot, display: DisplayConfig) -> dict[int, Color]:
    """The colour of every slot the snapshot singles out.

    A write outranks a read on the same slot, and an algorithm's own mark
    outranks both.

    >>> look = DisplayConfig()
    >>> _touch_colors(Snapshot((1, 2), 0, 0, 0, touches=((0, Touch.READ),)), look)
    {0: (61, 220, 132)}
    >>> both = ((1, Touch.WRITE), (1, Touch.READ))
    >>> _touch_colors(Snapshot((1, 2), 0, 0, 0, touches=both), look)
    {1: (255, 85, 85)}
    >>> _touch_colors(Snapshot((1, 2), 0, 0, 0, marks=((0, (9, 9, 9)),)), look)
    {0: (9, 9, 9)}
    """
    read, write = from_hex(display.read_color), from_hex(display.write_color)
    colors: dict[int, Color] = {}

    for index, touch in snapshot.touches:
        if touch is Touch.WRITE or colors.get(index) != write:
            colors[index] = write if touch is Touch.WRITE else read

    colors.update(snapshot.marks)
    return colors


def _column(index: int, count: int, width: int) -> tuple[int, int]:
    """The left edge and the thickness of bar `index`, in pixels."""
    span = width / count
    left = min(round(index * span), width - 1)
    gap = 1 if span >= _MIN_SPAN_FOR_GAP else 0
    return left, max(1, min(round((index + 1) * span), width) - left - gap)


def _draw_bars(
    surface: pygame.Surface,
    values: tuple[int, ...],
    colors: dict[int, Color],
    highest: int,
    display: DisplayConfig,
) -> None:
    """Draw one bottom aligned bar per value, coloured by its last access."""
    width, height = surface.get_size()
    chart = height - display.header
    bar = from_hex(display.bar_color)

    for index, value in enumerate(values):
        left, thickness = _column(index, len(values), width)
        share = min(value / highest, 1.0)
        tall = max(1, round(share * (chart - 2)))
        rect = pygame.Rect(left, height - tall, thickness, tall)
        pygame.draw.rect(surface, colors.get(index, bar), rect)


def _counters(
    snapshot: Snapshot,
    steps: int,
    playback: str,
    delay_ms: float,
    display: DisplayConfig,
) -> str:
    """The counter row, holding only the readings left switched on.

    >>> _counters(Snapshot((1, 2), 3, 0, 0), 4, "paused", 50.0, DisplayConfig())
    'n 2   reads 3   writes 0   comparisons 0   snapshots 4   paused'
    """
    readings = (
        (display.show_size, f"n {len(snapshot.values)}"),
        (display.show_reads, f"reads {snapshot.reads}"),
        (display.show_writes, f"writes {snapshot.writes}"),
        (display.show_comparisons, f"comparisons {snapshot.comparisons}"),
        (display.show_snapshots, f"snapshots {steps}"),
        (display.show_delay, f"delay {delay_ms:g}ms"),
        (display.show_playback, playback),
    )
    return "   ".join(text for shown, text in readings if shown)


def _rows(snapshot: Snapshot, counters: str, display: DisplayConfig) -> tuple[str, ...]:
    """Every header row the settings switch on, in order.

    A row that is on but has nothing to say keeps its place, so an algorithm
    naming itself late does not shove its status line up.
    """
    wanted = (
        (display.shows_counters, counters),
        (display.show_algo, snapshot.current_algo),
        (display.show_status, snapshot.status),
    )
    return tuple(text for shown, text in wanted if shown)


def _draw_stats(
    surface: pygame.Surface,
    snapshot: Snapshot,
    font: pygame.font.Font,
    steps: int,
    playback: str,
    delay_ms: float,
    display: DisplayConfig,
) -> None:
    """Write the counters of `snapshot`, then each label it carries, one per line."""
    counters = _counters(snapshot, steps, playback, delay_ms, display)
    color = from_hex(display.text_color)

    for row, line in enumerate(_rows(snapshot, counters, display)):
        if line:
            top = _MARGIN // 2 + row * display.line_height
            surface.blit(font.render(line, True, color), (_MARGIN, top))


def paint(
    surface: pygame.Surface,
    snapshot: Snapshot,
    highest: int,
    font: pygame.font.Font,
    steps: int,
    playback: str,
    display: DisplayConfig,
    delay_ms: float = 0.0,
) -> None:
    """Paint `snapshot` as a bar chart with the header lines above it."""
    surface.fill(from_hex(display.background_color))
    values = snapshot.values

    if values:
        _draw_bars(surface, values, _touch_colors(snapshot, display), highest, display)

    _draw_stats(surface, snapshot, font, steps, playback, delay_ms, display)


def status_font(size: int) -> pygame.font.Font:
    """A fresh monospaced font of `size`, so no two threads share one."""
    return pygame.font.SysFont(_MONOSPACE, size)

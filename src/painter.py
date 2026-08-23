"""Painting one Snapshot onto a surface, shared by the window and the export."""

import pygame

from tracked_array import Color, Snapshot, Touch, from_hex

BACKGROUND: Color = from_hex("#12141c")
BAR: Color = from_hex("#8fb8de")
READ: Color = from_hex("#3ddc84")
WRITE: Color = from_hex("#ff5555")
TEXT: Color = from_hex("#e6e6e6")

HEADER = 28
STATUS_FONT_SIZE = 18
_MIN_SPAN_FOR_GAP = 3.0


def _touch_colors(snapshot: Snapshot) -> dict[int, Color]:
    """The colour of every slot the snapshot singles out.

    A write outranks a read on the same slot, and an algorithm's own mark
    outranks both.

    >>> _touch_colors(Snapshot((1, 2), 0, 0, 0, touches=((0, Touch.READ),)))
    {0: (61, 220, 132)}
    >>> both = ((1, Touch.WRITE), (1, Touch.READ))
    >>> _touch_colors(Snapshot((1, 2), 0, 0, 0, touches=both))
    {1: (255, 85, 85)}
    >>> _touch_colors(Snapshot((1, 2), 0, 0, 0, marks=((0, (9, 9, 9)),)))
    {0: (9, 9, 9)}
    """
    colors: dict[int, Color] = {}

    for index, touch in snapshot.touches:
        if touch is Touch.WRITE or colors.get(index) is not WRITE:
            colors[index] = WRITE if touch is Touch.WRITE else READ

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
) -> None:
    """Draw one bottom aligned bar per value, coloured by its last access."""
    width, height = surface.get_size()
    chart = height - HEADER

    for index, value in enumerate(values):
        left, thickness = _column(index, len(values), width)
        share = min(value / highest, 1.0)
        bar = max(1, round(share * (chart - 2)))
        rect = pygame.Rect(left, height - bar, thickness, bar)
        pygame.draw.rect(surface, colors.get(index, BAR), rect)


def _draw_stats(
    surface: pygame.Surface,
    snapshot: Snapshot,
    font: pygame.font.Font,
    steps: int,
    status: str,
) -> None:
    """Write the counters of `snapshot` across the top of the surface."""
    line = (
        f"n {len(snapshot.values)}   reads {snapshot.reads}   "
        f"writes {snapshot.writes}   comparisons {snapshot.comparisons}   "
        f"snapshots {steps}   {status}"
    )
    surface.blit(font.render(line, True, TEXT), (8, 6))


def paint(
    surface: pygame.Surface,
    snapshot: Snapshot,
    highest: int,
    font: pygame.font.Font,
    steps: int,
    status: str,
) -> None:
    """Paint `snapshot` as a bar chart with a line of counters above it."""
    surface.fill(BACKGROUND)
    values = snapshot.values

    if values:
        _draw_bars(surface, values, _touch_colors(snapshot), highest)

    _draw_stats(surface, snapshot, font, steps, status)


def status_font() -> pygame.font.Font:
    """A fresh font for the counter line, so no two threads share one."""
    return pygame.font.SysFont("consolas", STATUS_FONT_SIZE)

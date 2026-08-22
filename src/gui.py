import math
import struct
from collections.abc import Iterator

import pygame

from algorithms import ALGORITHMS
from configurator import Config, Configurator, Controls
from tracked_array import Color, Snapshot, Touch, from_hex

_BACKGROUND: Color = from_hex("#12141c")
_BAR: Color = from_hex("#8fb8de")
_READ: Color = from_hex("#3ddc84")
_WRITE: Color = from_hex("#ff5555")
_TEXT: Color = from_hex("#e6e6e6")

_HEADER = 28
_MIN_SPAN_FOR_GAP = 3.0
_FPS = 60
_MAX_STEPS_PER_FRAME = 512

# sound constants
_SAMPLE_RATE = 44100
_CHANNELS = 16
_MIN_FREQUENCY = 100.0
_MAX_FREQUENCY = 1100.0
_AMPLITUDE = 0.6


def _frequency(value: int, highest: int, pitch: float = 1.0) -> float:
    """The pitch of `value`, small bars deep and tall bars bright.

    >>> [_frequency(v, 10) for v in (0, 5, 10)]
    [100.0, 600.0, 1100.0]
    >>> _frequency(3, 0)
    100.0
    >>> _frequency(10, 10, 2.0)
    2200.0
    """
    if highest <= 0:
        return _MIN_FREQUENCY * pitch

    share = min(max(value / highest, 0.0), 1.0)
    return (_MIN_FREQUENCY + share * (_MAX_FREQUENCY - _MIN_FREQUENCY)) * pitch


def _tone(frequency: float, duration_ms: float) -> bytes:
    """One mono 16 bit sine burst, faded in and out so it does not click.

    >>> len(_tone(440.0, 10.0))
    882
    >>> _tone(440.0, 10.0)[:2]
    b'\\x00\\x00'
    >>> _tone(440.0, 0.0)
    b''
    """
    samples = int(_SAMPLE_RATE * duration_ms / 1000)
    fade = max(1, samples // 8)
    step = 2 * math.pi * frequency / _SAMPLE_RATE
    peak = 32767 * _AMPLITUDE
    frames = [
        int(peak * min(i, samples - 1 - i, fade) / fade * math.sin(step * i))
        for i in range(samples)
    ]
    return struct.pack(f"<{samples}h", *frames)


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
        if touch is Touch.WRITE or colors.get(index) is not _WRITE:
            colors[index] = _WRITE if touch is Touch.WRITE else _READ

    colors.update(snapshot.marks)
    return colors


def _sounding_value(snapshot: Snapshot) -> int | None:
    """The value of the slot touched last, or None when nothing was touched.

    >>> _sounding_value(Snapshot((5, 7), 0, 0, 0, touches=((1, Touch.WRITE),)))
    7
    >>> _sounding_value(Snapshot((5, 7), 0, 0, 0)) is None
    True
    """
    if not snapshot.touches:
        return None

    index, _touch = snapshot.touches[-1]
    return snapshot.values[index]


def _column(index: int, count: int, width: int) -> tuple[int, int]:
    """The left edge and the thickness of bar `index`, in pixels."""
    span = width / count
    left = min(round(index * span), width - 1)
    gap = 1 if span >= _MIN_SPAN_FOR_GAP else 0
    return left, max(1, min(round((index + 1) * span), width) - left - gap)


def _budget(overdue: float, delay_ms: float, running: bool) -> tuple[int, float]:
    """The frames to take now, and the waiting time left over afterwards."""
    if not running:
        return 0, 0.0

    if delay_ms <= 0:
        return _MAX_STEPS_PER_FRAME, 0.0

    steps = min(int(overdue // delay_ms), _MAX_STEPS_PER_FRAME)

    if steps == _MAX_STEPS_PER_FRAME:
        return steps, 0.0

    return steps, overdue - steps * delay_ms


class GUI:
    """The visualisation window: one bar per element, one tone per drawn frame.

    It reads the settings fresh on every frame instead of copying them, so a
    slider moved mid-run is heard and seen at once.
    """

    def __init__(
        self, width: int, height: int, settings: Config, controls: Controls
    ) -> None:
        self.settings = settings
        self.controls = controls
        self._alive = True
        self._highest = 1
        self._finished = False
        self._tones: dict[int, pygame.mixer.Sound] = {}
        self._voice = (settings.sustain_ms, settings.pitch)

        pygame.mixer.pre_init(_SAMPLE_RATE, -16, 1, 512)
        pygame.init()
        self._audio = self._start_mixer()

        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        pygame.display.set_caption("Sorting visualiser")
        self._font = pygame.font.SysFont("consolas", 15)

    @staticmethod
    def _start_mixer() -> bool:
        """Whether the machine gave us an audio device to play through."""
        try:
            pygame.mixer.init()
        except pygame.error:
            return False

        pygame.mixer.set_num_channels(_CHANNELS)
        return True

    def handle_events(self) -> bool:
        """Serve the window's events once, False once the user closed it.

        The run itself is driven from the settings window alone.
        """
        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                self._alive = False

        return self._alive

    def begin(self, snapshot: Snapshot) -> None:
        """Fix the vertical scale and the pitch range to the array `snapshot`."""
        self._highest = max(max(snapshot.values, default=1), 1)
        self._finished = False

    def finish(self) -> None:
        """Mark the run as complete, so the status line reads "done!"."""
        self._finished = True

    def draw(self, snapshot: Snapshot) -> None:
        """Paint `snapshot` as a bar chart with a line of counters above it."""
        self.screen.fill(_BACKGROUND)
        values = snapshot.values

        if values:
            self._draw_bars(values, _touch_colors(snapshot))

        self._draw_stats(snapshot)
        pygame.display.flip()

    def _draw_bars(self, values: tuple[int, ...], colors: dict[int, Color]) -> None:
        """Draw one bottom aligned bar per value, coloured by its last access."""
        width, height = self.screen.get_size()
        chart = height - _HEADER

        for index, value in enumerate(values):
            left, thickness = _column(index, len(values), width)
            share = min(value / self._highest, 1.0)
            bar = max(1, round(share * (chart - 2)))
            rect = pygame.Rect(left, height - bar, thickness, bar)
            pygame.draw.rect(self.screen, colors.get(index, _BAR), rect)

    def _draw_stats(self, snapshot: Snapshot) -> None:
        """Write the counters of `snapshot` across the top of the window."""
        if self._finished:
            status = "done!"
        else:
            status = "running" if self.controls.running else "paused"

        line = (
            f"n {len(snapshot.values)}   reads {snapshot.reads}   "
            f"writes {snapshot.writes}   comparisons {snapshot.comparisons}   "
            f"{status}"
        )
        self.screen.blit(self._font.render(line, True, _TEXT), (8, 6))

    def play_sound(self, value: int) -> None:
        """Play the tone of `value`, silently doing nothing without a device."""
        if not self._audio or not self.settings.sound_enabled:
            return

        sound = self._tone_for(value)
        sound.set_volume(self.settings.volume)
        sound.play()

    def _tone_for(self, value: int) -> pygame.mixer.Sound:
        """The cached burst for `value`, rebuilt when the voice was changed."""
        voice = (self.settings.sustain_ms, self.settings.pitch)

        if voice != self._voice:
            self._tones.clear()
            self._voice = voice

        sustain, pitch = voice
        hertz = round(_frequency(value, self._highest, pitch))

        if hertz not in self._tones:
            self._tones[hertz] = pygame.mixer.Sound(buffer=_tone(hertz, sustain))

        return self._tones[hertz]

    def close(self) -> None:
        """Shut the window and release the audio device."""
        self._alive = False
        pygame.quit()


def run(width: int = 960, height: int = 540) -> None:
    """Open both windows and drive them from this loop until either one closes."""
    window = Configurator()
    gui = GUI(width, height, window.settings, window.controls)
    settings, controls = window.settings, window.controls

    frames: Iterator[Snapshot] = iter(())
    latest: Snapshot | None = None
    clock = pygame.time.Clock()
    overdue = 0.0
    running = controls.running

    while window.pump() and gui.handle_events():
        overdue += clock.tick(_FPS)

        if controls.consume_reset():
            array = settings.build_array()
            frames = ALGORITHMS[settings.algorithm](array)
            latest = array.snapshot()
            gui.begin(latest)
            overdue = 0.0

        steps, overdue = _budget(overdue, settings.delay_ms, controls.running)

        if controls.consume_step():
            steps = max(steps, 1)

        for _ in range(steps):
            snapshot = next(frames, None)

            if snapshot is None:
                controls.running = False
                gui.finish()
                break

            latest = snapshot

        if latest is not None:
            gui.draw(latest)
            value = _sounding_value(latest)

            if value is not None and steps:
                gui.play_sound(value)

        if controls.running != running:
            running = controls.running
            window.sync()

    window.close()
    gui.close()


if __name__ == "__main__":
    run()

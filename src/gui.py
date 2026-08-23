from collections.abc import Iterator

import pygame

from algorithms import ALGORITHMS
from audio import SAMPLE_RATE, frequency, interleave, sounding_value, tone
from config import Config
from configurator import Configurator, Controls
from pacing import budget
from painter import paint, status_font
from tracked_array import Snapshot

_FPS = 60
_CHANNELS = 16


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
        self._steps = 0
        self._tones: dict[int, pygame.mixer.Sound] = {}
        self._voice = (settings.sustain_ms, settings.pitch)
        self._channels = 1

        pygame.mixer.pre_init(SAMPLE_RATE, -16, 1, 512)
        pygame.init()
        self._audio = self._start_mixer()

        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        pygame.display.set_caption("Sorting visualiser")
        self._font = status_font()

    def _start_mixer(self) -> bool:

        if pygame.mixer.get_init() is not None:
            pygame.mixer.quit()

        try:
            pygame.mixer.init(SAMPLE_RATE, -16, 1, 512, allowedchanges=0)
        except pygame.error:
            try:
                pygame.mixer.init()
            except pygame.error:
                return False

        opened = pygame.mixer.get_init()
        self._channels = opened[2] if opened else 1
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
        self._steps = 0

    def step(self) -> None:
        """Count one snapshot taken from the algorithm, paused frames aside."""
        self._steps += 1

    def finish(self) -> None:
        """Mark the run as complete, so the status line reads "done!"."""
        self._finished = True

    def draw(self, snapshot: Snapshot) -> None:
        """Paint `snapshot` onto the window."""
        if self._finished:
            playback = "done!"
        else:
            playback = "running" if self.controls.running else "paused"

        paint(self.screen, snapshot, self._highest, self._font, self._steps, playback)
        pygame.display.flip()

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
        hertz = round(frequency(value, self._highest, pitch))

        if hertz not in self._tones:
            burst = interleave(tone(hertz, sustain), self._channels)
            self._tones[hertz] = pygame.mixer.Sound(buffer=burst)

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

        steps, overdue = budget(overdue, settings.delay_ms, controls.running)

        if controls.consume_step():
            steps = max(steps, 1)

        for _ in range(steps):
            snapshot = next(frames, None)

            if snapshot is None:
                controls.running = False
                gui.finish()
                break

            latest = snapshot
            gui.step()

        if latest is not None:
            gui.draw(latest)
            value = sounding_value(latest)

            if value is not None and steps:
                gui.play_sound(value)

        if controls.running != running:
            running = controls.running
            window.sync()

    window.close()
    gui.close()


if __name__ == "__main__":
    run()

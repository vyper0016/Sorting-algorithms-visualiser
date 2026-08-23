"""Rendering a whole run to a GIF or an MP4"""

import array
import os
import random
import shutil
import subprocess
import tempfile
import wave
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

import pygame

from algorithms import ALGORITHMS
from audio import PEAK, SAMPLE_RATE, frequency, sounding_value, tone
from config import Config, ExportConfig, FileFormat
from pacing import budget
from painter import paint, status_font
from tracked_array import Snapshot

_TAIL_SECONDS = 1.0
_GIF_FILTER = "[0:v] split [a][b];[a] palettegen [p];[b][p] paletteuse"
_STDERR_LINES = 12

Progress = Callable[[str], None]


class ExportError(Exception):
    """Raised when no encoder was found or ffmpeg refused to write the file."""


@dataclass(frozen=True)
class ExportResult:
    """What one finished export produced."""

    path: Path
    frames: int
    seed: int
    truncated: bool

    def describe(self) -> str:
        """A one line report for the status bar.

        >>> ExportResult(Path("run.mp4"), 90, 7, False).describe()
        'saved run.mp4, 90 frames, seed 7'
        >>> ExportResult(Path("run.gif"), 90, 7, True).describe()
        'saved run.gif, 90 frames, seed 7 (cut short at the length limit)'
        """
        cut = " (cut short at the length limit)" if self.truncated else ""
        return f"saved {self.path.name}, {self.frames} frames, seed {self.seed}{cut}"


def _clamp(sample: int) -> int:
    """`sample` held inside the range one 16 bit frame can carry.

    >>> _clamp(40000), _clamp(-40000), _clamp(17)
    (32767, -32767, 17)
    """
    return max(-PEAK, min(PEAK, sample))


def ffmpeg_executable() -> str | None:
    """The ffmpeg to encode with, preferring the one pip installed for us."""
    try:
        import imageio_ffmpeg
    except ImportError:
        return shutil.which("ffmpeg")

    return str(imageio_ffmpeg.get_ffmpeg_exe())


def _require_ffmpeg() -> str:
    """The ffmpeg executable, or a readable complaint that there is none."""
    executable = ffmpeg_executable()

    if executable is None:
        raise ExportError(
            "no ffmpeg found: install it, or `pip install imageio-ffmpeg`"
        )

    return executable


def _prepare_pygame() -> None:
    """Make sure a surface can be drawn on, with or without a window."""
    if not pygame.display.get_init():
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        pygame.display.init()

    if not pygame.font.get_init():
        pygame.font.init()


def _start(
    executable: str, arguments: list[str], errors: Path
) -> subprocess.Popen[bytes]:
    """Start ffmpeg with `arguments`, its complaints going to the file `errors`."""
    command = [executable, "-y", "-loglevel", "error", *arguments]

    with errors.open("wb") as stream:
        return subprocess.Popen(command, stdin=subprocess.PIPE, stderr=stream)


def _finish(process: subprocess.Popen[bytes], errors: Path) -> None:
    """Wait for ffmpeg, raising ExportError with its last words if it failed."""
    if process.stdin is not None and not process.stdin.closed:
        process.stdin.close()

    if process.wait() == 0:
        return

    tail = errors.read_text(errors="replace").strip().splitlines()[-_STDERR_LINES:]
    raise ExportError("ffmpeg failed:\n" + "\n".join(tail))


def _video_arguments(options: ExportConfig, target: Path) -> list[str]:
    """The ffmpeg arguments that turn piped raw frames into `target`."""
    width, height = options.size
    arguments = [
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "-s", f"{width}x{height}",
        "-r", str(options.fps),
        "-i", "pipe:0",
    ]  # fmt: skip

    if options.file_format is FileFormat.GIF:
        arguments += ["-filter_complex", _GIF_FILTER]
    else:
        arguments += [
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
        ]  # fmt: skip

    return [*arguments, str(target)]


def _mux_arguments(video: Path, sound: Path, target: Path) -> list[str]:
    """The ffmpeg arguments that lay `sound` under the already encoded `video`."""
    return [
        "-i", str(video),
        "-i", str(sound),
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        str(target),
    ]  # fmt: skip


def _opening(config: Config) -> tuple[Iterator[Snapshot], Snapshot, int]:
    """The run's frames, its opening snapshot, and the tallest value in it."""
    values = config.build_array()
    frames = ALGORITHMS[config.algorithm](values)
    first = values.snapshot()
    return frames, first, max(max(first.values, default=1), 1)


def _write_frames(
    process: subprocess.Popen[bytes],
    config: Config,
    options: ExportConfig,
    progress: Progress,
) -> tuple[list[int | None], int, bool]:
    """Paint the whole run into ffmpeg's stdin."""
    assert process.stdin is not None
    frames, latest, highest = _opening(config)
    surface = pygame.Surface(options.size)
    font = status_font()
    frame_ms = 1000 / options.fps
    limit = options.max_frames

    sounds: list[int | None] = []
    overdue = 0.0
    steps = 0
    running = True

    while running and len(sounds) < limit:
        overdue += frame_ms
        taken, overdue = budget(overdue, config.delay_ms, True)
        advanced = 0

        for _ in range(taken):
            snapshot = next(frames, None)

            if snapshot is None:
                running = False
                break

            latest = snapshot
            steps += 1
            advanced += 1

        paint(surface, latest, highest, font, steps, "running")
        process.stdin.write(pygame.image.tobytes(surface, "RGB"))
        sounds.append(sounding_value(latest) if advanced else None)

        if len(sounds) % options.fps == 0:
            progress(f"rendering frame {len(sounds)} of at most {limit}")

    paint(surface, latest, highest, font, steps, "done!")
    tail = pygame.image.tobytes(surface, "RGB")

    for _ in range(round(_TAIL_SECONDS * options.fps)):
        process.stdin.write(tail)
        sounds.append(None)

    return sounds, highest, running


def _burst(hertz: int, config: Config) -> array.array[int]:
    """One tone at `hertz`, already scaled by the run's volume."""
    samples = array.array("h")
    samples.frombytes(tone(hertz, config.sustain_ms))
    return array.array("h", [round(sample * config.volume) for sample in samples])


def _mix(
    sounds: list[int | None],
    highest: int,
    config: Config,
    options: ExportConfig,
    progress: Progress,
) -> bytes:
    """Lay every frame's tone onto one silent track, letting them overlap.

    `highest` is the tallest value the run started with, the same scale the
    window pitches its tones against.
    """
    total = len(sounds) * SAMPLE_RATE // options.fps + SAMPLE_RATE
    track = array.array("h", bytes(2 * total))
    cache: dict[int, array.array[int]] = {}

    for index, value in enumerate(sounds):
        if value is None:
            continue

        if index % options.fps == 0:
            progress(f"mixing sound, frame {index} of {len(sounds)}")

        hertz = round(frequency(value, highest, config.pitch))

        if hertz not in cache:
            cache[hertz] = _burst(hertz, config)

        start = index * SAMPLE_RATE // options.fps

        for offset, sample in enumerate(cache[hertz], start):
            track[offset] = _clamp(track[offset] + sample)

    return track.tobytes()


def _write_wave(path: Path, samples: bytes) -> None:
    """Write `samples` out as a mono 16 bit wave file."""
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(SAMPLE_RATE)
        stream.writeframes(samples)


def render(
    config: Config,
    options: ExportConfig,
    path: Path,
    progress: Progress = lambda _message: None,
) -> ExportResult:
    """Render one run of `config` to `path` and report what came out.

    A run without a seed of its own is given a fresh one here rather than a
    different array on every attempt, so the file can always be reproduced.
    """
    executable = _require_ffmpeg()
    _prepare_pygame()

    seed = config.seed if config.seed is not None else random.randrange(2**32)
    run = config.model_copy(update={"seed": seed})

    with tempfile.TemporaryDirectory(prefix="sortvis") as folder:
        scratch = Path(folder)
        errors = scratch / "ffmpeg.log"
        sounding = options.writes_sound()
        video = scratch / f"video.{options.file_format.value}" if sounding else path

        process = _start(executable, _video_arguments(options, video), errors)

        try:
            sounds, highest, truncated = _write_frames(process, run, options, progress)
        except BrokenPipeError:
            _finish(process, errors)
            raise

        _finish(process, errors)

        if sounding:
            sound = scratch / "tones.wav"
            _write_wave(sound, _mix(sounds, highest, run, options, progress))
            progress("adding the sound track")
            _finish(
                _start(executable, _mux_arguments(video, sound, path), errors), errors
            )

    return ExportResult(path, len(sounds), seed, truncated)

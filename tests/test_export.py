import wave
from typing import Any, cast

import pytest
from pydantic import ValidationError

import export
from algorithms import ALGORITHMS
from audio import SAMPLE_RATE
from config import Config, Distribution, ExportConfig, FileFormat
from pacing import MAX_STEPS_PER_FRAME, budget


def _snapshots_taken(delay_ms, fps, seconds):
    """How many snapshots `seconds` worth of frames advance through."""
    overdue = 0.0
    taken = 0

    for _ in range(fps * seconds):
        overdue += 1000 / fps
        steps, overdue = budget(overdue, delay_ms, True)
        taken += steps

    return taken


@pytest.mark.parametrize("delay_ms", [20.0, 50.0, 100.0, 1000.0])
def test_pacing_follows_the_delay_rather_than_the_frame_rate(delay_ms):
    seconds = 10
    assert _snapshots_taken(delay_ms, 60, seconds) == pytest.approx(
        seconds * 1000 / delay_ms, abs=1
    )


def test_no_delay_takes_the_whole_step_cap():
    assert budget(0.0, 0.0, True) == (MAX_STEPS_PER_FRAME, 0.0)


def test_clamp_saturates_instead_of_wrapping():
    assert export._clamp(2**20) == 32767
    assert export._clamp(-(2**20)) == -32767


def test_size_is_rounded_down_to_even_sides():
    assert ExportConfig(width=1281, height=721).size == (1280, 720)


def test_max_frames_follows_length_and_rate():
    assert ExportConfig(fps=30, max_minutes=2.0).max_frames == 3600


def test_gif_never_writes_sound():
    assert not ExportConfig(
        file_format=FileFormat.GIF, sound_enabled=True
    ).writes_sound()


@pytest.mark.parametrize("changes", [{"fps": 1}, {"fps": 120}, {"width": 10}])
def test_out_of_range_settings_are_refused(changes):
    with pytest.raises(ValidationError):
        ExportConfig(**changes)


def test_mixed_track_covers_every_frame():
    options = ExportConfig(fps=30)
    samples = export._mix([1, 2, 3], 3, Config(array_size=4), options, lambda _: None)
    expected = 3 * SAMPLE_RATE // options.fps + SAMPLE_RATE
    assert len(samples) == 2 * expected


def test_silent_frames_stay_silent():
    samples = export._mix([None, None], 63, Config(), ExportConfig(), lambda _: None)
    assert set(samples) == {0}


class _Sink:
    """A stand in for ffmpeg that throws the frames away."""

    class stdin:
        closed = False

        @staticmethod
        def write(data):
            return len(data)


def _painted(config, options):
    """The sounds and scale one export would produce, without encoding it."""
    export._prepare_pygame()
    return export._write_frames(cast(Any, _Sink()), config, options, lambda _: None)


def test_one_tone_per_snapshot_at_the_live_pace():
    config = Config(algorithm="bubble_sort", array_size=16, delay_ms=50.0, seed=1)
    options = ExportConfig(fps=60, width=160, height=120, max_minutes=10.0)
    snapshots = len(list(ALGORITHMS["bubble_sort"](config.build_array())))

    sounds, highest, truncated = _painted(config, options)

    assert not truncated
    assert len([sound for sound in sounds if sound is not None]) == snapshots
    assert len(sounds) > snapshots


def test_tones_are_pitched_against_the_starting_array():
    config = Config(distribution=Distribution.RANDOM_DISTINCT, array_size=16, seed=1)
    _sounds, highest, _truncated = _painted(config, ExportConfig(max_minutes=0.1))

    assert highest == max(config.build_array())


def test_written_wave_is_mono_sixteen_bit(tmp_path):
    path = tmp_path / "tones.wav"
    export._write_wave(path, b"\x00\x01" * 100)

    with wave.open(str(path), "rb") as stream:
        assert stream.getnchannels() == 1
        assert stream.getsampwidth() == 2
        assert stream.getframerate() == SAMPLE_RATE
        assert stream.getnframes() == 100


needs_ffmpeg = pytest.mark.skipif(
    export.ffmpeg_executable() is None, reason="no ffmpeg installed"
)


@needs_ffmpeg
@pytest.mark.parametrize("file_format", list(FileFormat))
def test_render_writes_a_playable_file(tmp_path, file_format):
    config = Config(algorithm="bubble_sort", array_size=8, delay_ms=50.0, seed=1)
    options = ExportConfig(
        file_format=file_format, width=160, height=120, fps=10, max_minutes=0.1
    )
    path = tmp_path / f"run.{file_format.value}"

    result = export.render(config, options, path)

    assert path.exists() and path.stat().st_size > 0
    assert result.seed == 1
    assert result.frames > 0


@needs_ffmpeg
def test_render_stops_at_the_length_limit(tmp_path):
    config = Config(algorithm="bogo_sort", array_size=9, delay_ms=50.0, seed=2)
    options = ExportConfig(
        file_format=FileFormat.GIF, width=160, height=120, fps=10, max_minutes=0.1
    )

    result = export.render(config, options, tmp_path / "bogo.gif")

    assert result.truncated
    assert result.frames == options.max_frames + options.fps


@needs_ffmpeg
def test_render_picks_and_reports_a_seed_when_none_was_given(tmp_path):
    config = Config(algorithm="bubble_sort", array_size=8, delay_ms=50.0)
    options = ExportConfig(
        file_format=FileFormat.GIF, width=160, height=120, fps=10, max_minutes=0.1
    )

    result = export.render(config, options, tmp_path / "run.gif")

    assert isinstance(result.seed, int)

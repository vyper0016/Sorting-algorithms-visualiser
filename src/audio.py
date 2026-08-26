"""The tones a run makes: one sine burst per drawn frame."""

import array
import math
import struct

from metrics import Snapshot

SAMPLE_RATE = 44100
MIN_FREQUENCY = 100.0
MAX_FREQUENCY = 1100.0
AMPLITUDE = 0.6
PEAK = 32767


def frequency(value: int, highest: int, pitch: float = 1.0) -> float:
    """The pitch of `value`, small bars deep and tall bars bright.

    >>> [frequency(v, 10) for v in (0, 5, 10)]
    [100.0, 600.0, 1100.0]
    >>> frequency(3, 0)
    100.0
    >>> frequency(10, 10, 2.0)
    2200.0
    """
    if highest <= 0:
        return MIN_FREQUENCY * pitch

    share = min(max(value / highest, 0.0), 1.0)
    return (MIN_FREQUENCY + share * (MAX_FREQUENCY - MIN_FREQUENCY)) * pitch


def tone(hertz: float, duration_ms: float) -> bytes:
    """One mono 16 bit sine burst, faded in and out so it does not click.

    >>> len(tone(440.0, 10.0))
    882
    >>> tone(440.0, 10.0)[:2]
    b'\\x00\\x00'
    >>> tone(440.0, 0.0)
    b''
    """
    samples = int(SAMPLE_RATE * duration_ms / 1000)
    fade = max(1, samples // 8)
    step = 2 * math.pi * hertz / SAMPLE_RATE
    peak = PEAK * AMPLITUDE
    frames = [
        int(peak * min(i, samples - 1 - i, fade) / fade * math.sin(step * i))
        for i in range(samples)
    ]
    return struct.pack(f"<{samples}h", *frames)


def interleave(raw: bytes, channels: int) -> bytes:
    """`raw` mono samples copied across `channels`"""
    if channels <= 1:
        return raw

    samples = array.array("h")
    samples.frombytes(raw)
    spread = array.array("h", [s for s in samples for _ in range(channels)])
    return spread.tobytes()


def sounding_value(snapshot: Snapshot) -> int | None:
    """The value of the slot touched last, or None when nothing was touched."""
    if not snapshot.touches:
        return None

    index, _touch = snapshot.touches[-1]
    return snapshot.values[index]

"""The validated settings objects the two windows write into."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from algorithms import ALGORITHMS
from generator import (
    generate_random_array,
    generate_range_array,
    generate_shuffled_array,
)
from tracked_array import TrackedArray


class ValidatedSettings(BaseModel):
    """Settings that validate every assignment, so a form can bind straight to them."""

    model_config = ConfigDict(validate_assignment=True)

    def update_fields(self, **changes: Any) -> None:
        """Apply `changes` in one step, or raise ValidationError and change nothing."""
        validated = self.model_validate({**self.model_dump(), **changes})
        self.__dict__.update(validated.__dict__)


class Distribution(StrEnum):
    """The shape of the array a run starts from."""

    ASCENDING = "ascending"
    DESCENDING = "descending"
    RANDOM = "random"
    RANDOM_DISTINCT = "random distinct"
    SHUFFLED = "shuffled"


class Config(ValidatedSettings):
    """Validated settings of one visualisation run."""

    algorithm: str = "bubble_sort"
    distribution: Distribution = Distribution.SHUFFLED
    array_size: int = Field(default=2**6, ge=2, le=2**11)
    seed: int | None = None
    delay_ms: float = Field(default=50.0, ge=0.0, le=2000.0)
    sound_enabled: bool = True
    volume: float = Field(default=0.3, ge=0.0, le=1.0)
    sustain_ms: float = Field(default=80.0, ge=1.0, le=1000.0)
    pitch: float = Field(default=1.0, ge=0.01, le=8.0)

    @field_validator("algorithm")
    @classmethod
    def _known_algorithm(cls, name: str) -> str:
        """Reject a name that the algorithms package does not offer."""
        if name not in ALGORITHMS:
            raise ValueError(f"unknown algorithm {name!r}")

        return name

    def build_array(self) -> TrackedArray:
        """A freshly generated array for these settings.

        >>> Config(array_size=5, distribution="ascending").build_array()
        [0, 1, 2, 3, 4]
        >>> Config(array_size=5, distribution="descending").build_array()
        [4, 3, 2, 1, 0]
        >>> sorted(Config(array_size=5, distribution="shuffled").build_array())
        [0, 1, 2, 3, 4]
        >>> values = Config(array_size=6, distribution="random distinct").build_array()
        >>> len(values) == len(set(values))
        True
        >>> len(Config(array_size=6, distribution="random").build_array())
        6
        """
        size = self.array_size

        match self.distribution:
            case Distribution.ASCENDING:
                return generate_range_array(size)
            case Distribution.DESCENDING:
                return generate_range_array(size - 1, -1, -1)
            case Distribution.RANDOM:
                return generate_random_array(size, 0, size - 1, seed=self.seed)
            case Distribution.RANDOM_DISTINCT:
                return generate_random_array(
                    size, 0, 2 * size - 1, distinct=True, seed=self.seed
                )
            case Distribution.SHUFFLED:
                return generate_shuffled_array(size, seed=self.seed)


class FileFormat(StrEnum):
    """A container an exported run can be written to."""

    MP4 = "mp4"
    GIF = "gif"


MIN_WIDTH, MAX_WIDTH = 160, 3840
MIN_HEIGHT, MAX_HEIGHT = 120, 2160


class ExportConfig(ValidatedSettings):
    """Validated settings of one export."""

    file_format: FileFormat = FileFormat.MP4
    width: int = Field(default=960, ge=MIN_WIDTH, le=MAX_WIDTH)
    height: int = Field(default=540, ge=MIN_HEIGHT, le=MAX_HEIGHT)
    fps: int = Field(default=60, ge=5, le=60)
    max_minutes: float = Field(default=1.0, ge=0.1, le=10.0)
    sound_enabled: bool = True

    @property
    def max_frames(self) -> int:
        """The frame limit, so a run that never ends still yields a file.

        >>> ExportConfig().max_frames
        3600
        >>> ExportConfig(fps=25, max_minutes=0.5).max_frames
        750
        """
        return round(self.max_minutes * 60 * self.fps)

    @property
    def size(self) -> tuple[int, int]:
        """The frame size, rounded down to the even sides libx264 demands.

        >>> ExportConfig(width=1281, height=721).size
        (1280, 720)
        >>> ExportConfig().size
        (960, 540)
        """
        return self.width - self.width % 2, self.height - self.height % 2

    def match(self, width: int, height: int) -> None:
        """Take a window's size, held inside the sizes an encoder accepts.

        >>> options = ExportConfig()
        >>> options.match(1280, 720)
        >>> options.size
        (1280, 720)
        >>> options.match(4000, 40)
        >>> options.size
        (3840, 120)
        """
        self.update_fields(
            width=min(max(width, MIN_WIDTH), MAX_WIDTH),
            height=min(max(height, MIN_HEIGHT), MAX_HEIGHT),
        )

    def writes_sound(self) -> bool:
        """Whether this export carries an audio track.

        >>> ExportConfig().writes_sound()
        True
        >>> ExportConfig(file_format="gif").writes_sound()
        False
        """
        return self.sound_enabled and self.file_format is not FileFormat.GIF


def parse_seed(text: str) -> int | None:
    """The seed an entry holds, where blank means a fresh random one.

    >>> parse_seed(" 42 ")
    42
    >>> parse_seed("   ") is None
    True
    """
    stripped = text.strip()
    return int(stripped) if stripped else None

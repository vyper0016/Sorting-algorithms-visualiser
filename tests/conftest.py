import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from metrics import Stats  # noqa: E402


@pytest.fixture
def stats():
    return Stats()

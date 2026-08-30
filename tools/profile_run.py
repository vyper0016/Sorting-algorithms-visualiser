"""Profile one sorting run headlessly and write a .prof for snakeviz.

uv run python tools/profile_run.py
uv run snakeviz profiles/quick_sort_n2000.prof
"""

import cProfile
import pstats
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from algorithms import ALGORITHMS  # noqa: E402
from generator import generate_shuffled_array  # noqa: E402

ALGORITHM = "quick_sort"
SIZE = 2000
SEED = 1
OUT = ROOT / "profiles" / f"{ALGORITHM}_n{SIZE}.prof"


def main() -> None:
    """Profile the run, dump the stats, and print the hottest functions."""
    array = generate_shuffled_array(0, SIZE, seed=SEED)
    profiler = cProfile.Profile()

    profiler.enable()
    snapshots = sum(1 for _ in ALGORITHMS[ALGORITHM](array))
    profiler.disable()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    profiler.dump_stats(OUT)

    stats = array.stats
    print(
        f"{ALGORITHM}: n={SIZE} snapshots={snapshots} "
        f"comparisons={stats.comparisons} reads={stats.reads} writes={stats.writes}"
    )
    pstats.Stats(profiler).sort_stats("tottime").print_stats(10)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()

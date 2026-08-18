from dataclasses import dataclass


@dataclass
class Stats:
    reads: int = 0
    writes: int = 0
    comparisons: int = 0

    def on_read(self) -> None:
        self.reads += 1

    def on_write(self) -> None:
        self.writes += 1

    def on_comparison(self) -> None:
        self.comparisons += 1

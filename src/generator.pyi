from src.trackables import TrackedArray
import random

def generate_random_array(
    size: int, min_value: int = 0, max_value: int = 100
) -> TrackedArray: ...
def generate_sorted_array(
    size: int, min_value: int = 0, max_value: int = 100, reverse: bool = True
) -> TrackedArray: ...

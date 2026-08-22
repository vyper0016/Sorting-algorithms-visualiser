import pytest

from algorithms import ALGORITHMS
from generator import (
    generate_random_array,
    generate_range_array,
    generate_shuffled_array,
)


@pytest.mark.parametrize("algorithm", ALGORITHMS.values(), ids=list(ALGORITHMS))
class TestSorts:
    def test_sorts_random_array(self, algorithm):
        arr = generate_random_array(40, 0, 100, seed=1)
        expected = sorted(int(x) for x in arr)
        list(algorithm(arr))
        assert [int(x) for x in arr] == expected

    def test_sorts_reversed_array(self, algorithm):
        arr = generate_range_array(9, -1, -1)
        list(algorithm(arr))
        assert list(arr) == list(range(10))

    def test_handles_duplicates(self, algorithm):
        arr = generate_random_array(30, 0, 2, seed=2)
        expected = sorted(int(x) for x in arr)
        list(algorithm(arr))
        assert [int(x) for x in arr] == expected

    @pytest.mark.parametrize("size", [0, 1])
    def test_handles_tiny_arrays(self, algorithm, size):
        arr = generate_range_array(size)
        assert list(algorithm(arr)) == []

    def test_last_frame_matches_final_array(self, algorithm):
        arr = generate_random_array(15, 0, 30, seed=3)
        frames = list(algorithm(arr))
        assert frames[-1].values == tuple(int(x) for x in arr)

    def test_frames_stay_drawable(self, algorithm):
        """Every frame must be something the visualiser can draw."""
        arr = generate_shuffled_array(20, seed=4)
        legal = {int(x) for x in arr}
        size = len(arr)

        for i, frame in enumerate(algorithm(arr)):
            assert len(frame.values) == size, f"frame {i} resized the array"
            invented = set(frame.values) - legal
            assert not invented, f"frame {i} invented {sorted(invented)}"

    def test_marks_stay_in_range(self, algorithm):
        arr = generate_random_array(20, 0, 50, seed=5)
        size = len(arr)

        for i, frame in enumerate(algorithm(arr)):
            for index, _color in frame.marks:
                assert 0 <= index < size, f"frame {i} marked slot {index}"

    def test_finished_array_is_unmarked(self, algorithm):
        """A run must clean up after itself, or the last frame stays coloured."""
        arr = generate_random_array(20, 0, 50, seed=6)
        frames = list(algorithm(arr))
        assert frames[-1].marks == ()
        assert arr.snapshot().marks == ()

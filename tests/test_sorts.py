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
        """Every frame must be something the visualiser can draw.

        Nothing at runtime stops an algorithm from writing a value it invented,
        so this is where that is caught. A shuffled range gives a known legal
        set. Buffers mean a frame may repeat a value, so this checks membership,
        not a multiset: the end-of-run permutation is covered by
        `test_sorts_random_array`.
        """
        arr = generate_shuffled_array(20, seed=4)
        legal = {int(x) for x in arr}
        size = len(arr)

        for i, frame in enumerate(algorithm(arr)):
            assert len(frame.values) == size, f"frame {i} resized the array"
            invented = set(frame.values) - legal
            assert not invented, f"frame {i} invented {sorted(invented)}"

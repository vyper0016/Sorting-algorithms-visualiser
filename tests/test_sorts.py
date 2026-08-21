import pytest

from algorithms import ALGORITHMS
from generator import generate_random_array, generate_sorted_array


@pytest.mark.parametrize("algorithm", ALGORITHMS.values(), ids=list(ALGORITHMS))
class TestSorts:
    def test_sorts_random_array(self, algorithm):
        arr = generate_random_array(40, 0, 100)
        expected = sorted(int(x) for x in arr)
        list(algorithm(arr))
        assert [int(x) for x in arr] == expected

    def test_sorts_reversed_array(self, algorithm):
        arr = generate_sorted_array(9, -1, -1)
        list(algorithm(arr))
        assert list(arr) == list(range(10))

    def test_handles_duplicates(self, algorithm):
        arr = generate_random_array(30, 0, 2)
        expected = sorted(int(x) for x in arr)
        list(algorithm(arr))
        assert [int(x) for x in arr] == expected

    @pytest.mark.parametrize("size", [0, 1])
    def test_handles_tiny_arrays(self, algorithm, size):
        arr = generate_sorted_array(size)
        assert list(algorithm(arr)) == []

    def test_last_frame_matches_final_array(self, algorithm):
        arr = generate_random_array(15, 0, 30)
        frames = list(algorithm(arr))
        assert frames[-1].values == tuple(int(x) for x in arr)

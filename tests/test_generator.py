import icontract
import pytest

from generator import generate_random_array, generate_sorted_array
from stats import Stats
from trackables import TrackedArray


class TestGenerateRandomArray:
    def test_length(self):
        arr = generate_random_array(10, 0, 100)
        assert len(arr) == 10

    def test_values_in_range(self):
        arr = generate_random_array(50, 5, 15)
        assert all(5 <= x <= 15 for x in arr)

    def test_zero_size(self):
        arr = generate_random_array(0)
        assert len(arr) == 0

    def test_returns_tracked_array_with_own_stats(self):
        arr = generate_random_array(5)
        assert isinstance(arr, TrackedArray)
        assert isinstance(arr.stats, Stats)

    def test_defaults(self):
        arr = generate_random_array(20)
        assert all(0 <= x <= 100 for x in arr)

    def test_negative_size_rejected(self):
        with pytest.raises(icontract.ViolationError):
            generate_random_array(-1)

    def test_min_greater_than_max_rejected(self):
        with pytest.raises(icontract.ViolationError):
            generate_random_array(5, 10, 1)


class TestGenerateSortedArray:
    def test_length(self):
        arr = generate_sorted_array(10, 0, 100)
        assert len(arr) == 10

    def test_default_descending(self):
        arr = generate_sorted_array(30, 0, 100)
        assert list(arr) == sorted(arr, reverse=True)

    def test_ascending_when_reverse_false(self):
        arr = generate_sorted_array(30, 0, 100, reverse=False)
        assert list(arr) == sorted(arr)

    def test_values_in_range(self):
        arr = generate_sorted_array(50, 5, 15)
        assert all(5 <= x <= 15 for x in arr)

    def test_zero_size(self):
        arr = generate_sorted_array(0)
        assert len(arr) == 0

    def test_returns_tracked_array_with_own_stats(self):
        arr = generate_sorted_array(5)
        assert isinstance(arr, TrackedArray)
        assert isinstance(arr.stats, Stats)

    def test_negative_size_rejected(self):
        with pytest.raises(icontract.ViolationError):
            generate_sorted_array(-1)

    def test_min_greater_than_max_rejected(self):
        with pytest.raises(icontract.ViolationError):
            generate_sorted_array(5, 10, 1)

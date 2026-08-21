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
    def test_ascending_by_default(self):
        assert list(generate_sorted_array(5)) == [0, 1, 2, 3, 4]

    def test_negative_step_descends(self):
        assert list(generate_sorted_array(4, -1, -1)) == [4, 3, 2, 1, 0]

    def test_single_arg_is_stop_and_starts_at_zero(self):
        assert list(generate_sorted_array(3)) == [0, 1, 2]

    def test_start_inclusive_stop_exclusive(self):
        assert list(generate_sorted_array(3, 6)) == [3, 4, 5]

    def test_step(self):
        assert list(generate_sorted_array(0, 10, 3)) == [0, 3, 6, 9]

    def test_negative_bounds(self):
        assert list(generate_sorted_array(-3, 0)) == [-3, -2, -1]

    def test_empty_when_step_points_away_from_stop(self):
        assert len(generate_sorted_array(5, 5)) == 0
        assert len(generate_sorted_array(6, 3)) == 0
        assert len(generate_sorted_array(3, 6, -1)) == 0

    def test_zero_stop(self):
        assert len(generate_sorted_array(0)) == 0

    def test_returns_tracked_array_with_own_stats(self):
        arr = generate_sorted_array(5)
        assert isinstance(arr, TrackedArray)
        assert isinstance(arr.stats, Stats)
        assert all(x.stats is arr.stats for x in arr)

    def test_zero_step_rejected(self):
        with pytest.raises(icontract.ViolationError):
            generate_sorted_array(0, 10, 0)

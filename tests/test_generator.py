import icontract
import pytest

from generator import (
    generate_random_array,
    generate_range_array,
    generate_shuffled_array,
)
from metrics import Stats
from tracked_array import TrackedArray


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

    def test_same_seed_same_array(self):
        assert list(generate_random_array(30, 0, 100, seed=7)) == list(
            generate_random_array(30, 0, 100, seed=7)
        )

    def test_different_seed_different_array(self):
        assert list(generate_random_array(30, 0, 100, seed=7)) != list(
            generate_random_array(30, 0, 100, seed=8)
        )

    def test_seed_does_not_disturb_global_random(self):
        """Seeding one array must not make an unseeded one reproducible."""
        generate_random_array(5, seed=7)
        first = list(generate_random_array(30, 0, 100))
        generate_random_array(5, seed=7)
        assert list(generate_random_array(30, 0, 100)) != first

    def test_distinct_has_no_repeats(self):
        arr = generate_random_array(10, 0, 20, distinct=True, seed=7)
        assert len(set(arr)) == 10

    def test_distinct_values_in_range(self):
        arr = generate_random_array(10, 5, 15, distinct=True, seed=7)
        assert all(5 <= x <= 15 for x in arr)

    def test_distinct_exhausting_the_range_allowed(self):
        arr = generate_random_array(11, 0, 10, distinct=True, seed=7)
        assert sorted(int(x) for x in arr) == list(range(11))

    def test_distinct_larger_than_range_rejected(self):
        with pytest.raises(icontract.ViolationError):
            generate_random_array(12, 0, 10, distinct=True)


class TestGenerateShuffledArray:
    def test_is_permutation_of_the_range(self):
        assert sorted(int(x) for x in generate_shuffled_array(20)) == list(range(20))

    def test_single_arg_is_stop_and_starts_at_zero(self):
        assert sorted(int(x) for x in generate_shuffled_array(3)) == [0, 1, 2]

    def test_start_inclusive_stop_exclusive(self):
        assert sorted(int(x) for x in generate_shuffled_array(3, 6)) == [3, 4, 5]

    def test_negative_bounds(self):
        assert sorted(int(x) for x in generate_shuffled_array(-3, 0)) == [-3, -2, -1]

    def test_matches_sorted_array_of_same_bounds(self):
        assert sorted(int(x) for x in generate_shuffled_array(4, 12)) == [
            int(x) for x in generate_range_array(4, 12)
        ]

    def test_empty_when_stop_precedes_start(self):
        assert len(generate_shuffled_array(6, 3)) == 0

    def test_zero_stop(self):
        assert len(generate_shuffled_array(0)) == 0

    def test_actually_shuffles(self):
        assert list(generate_shuffled_array(50, seed=7)) != list(range(50))

    def test_same_seed_same_array(self):
        assert list(generate_shuffled_array(30, seed=7)) == list(
            generate_shuffled_array(30, seed=7)
        )

    def test_different_seed_different_array(self):
        assert list(generate_shuffled_array(30, seed=7)) != list(
            generate_shuffled_array(30, seed=8)
        )

    def test_returns_tracked_array_with_own_stats(self):
        arr = generate_shuffled_array(5)
        assert isinstance(arr, TrackedArray)
        assert isinstance(arr.stats, Stats)
        assert all(x.stats is arr.stats for x in arr)


class TestGenerateSortedArray:
    def test_ascending_by_default(self):
        assert list(generate_range_array(5)) == [0, 1, 2, 3, 4]

    def test_negative_step_descends(self):
        assert list(generate_range_array(4, -1, -1)) == [4, 3, 2, 1, 0]

    def test_single_arg_is_stop_and_starts_at_zero(self):
        assert list(generate_range_array(3)) == [0, 1, 2]

    def test_start_inclusive_stop_exclusive(self):
        assert list(generate_range_array(3, 6)) == [3, 4, 5]

    def test_step(self):
        assert list(generate_range_array(0, 10, 3)) == [0, 3, 6, 9]

    def test_negative_bounds(self):
        assert list(generate_range_array(-3, 0)) == [-3, -2, -1]

    def test_empty_when_step_points_away_from_stop(self):
        assert len(generate_range_array(5, 5)) == 0
        assert len(generate_range_array(6, 3)) == 0
        assert len(generate_range_array(3, 6, -1)) == 0

    def test_zero_stop(self):
        assert len(generate_range_array(0)) == 0

    def test_returns_tracked_array_with_own_stats(self):
        arr = generate_range_array(5)
        assert isinstance(arr, TrackedArray)
        assert isinstance(arr.stats, Stats)
        assert all(x.stats is arr.stats for x in arr)

    def test_zero_step_rejected(self):
        with pytest.raises(icontract.ViolationError):
            generate_range_array(0, 10, 0)

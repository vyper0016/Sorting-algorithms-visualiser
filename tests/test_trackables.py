import icontract
import pytest

from stats import Stats
from trackables import TrackedArray, TrackedInteger


@pytest.fixture
def stats():
    return Stats()


def make_array(values, stats):
    return TrackedArray([TrackedInteger(v, stats) for v in values], stats)


class TestTrackedInteger:
    def test_value(self, stats):
        assert TrackedInteger(5, stats) == 5

    @pytest.mark.parametrize(
        "op",
        [
            lambda a, b: a > b,
            lambda a, b: a < b,
            lambda a, b: a == b,
            lambda a, b: a >= b,
            lambda a, b: a <= b,
        ],
    )
    def test_comparison_tracked(self, stats, op):
        a = TrackedInteger(3, stats)
        b = TrackedInteger(4, stats)
        op(a, b)
        assert stats.comparisons == 1

    def test_comparison_result_correct(self, stats):
        a = TrackedInteger(3, stats)
        b = TrackedInteger(4, stats)
        assert a < b
        assert b > a
        assert not a == b
        assert a <= b
        assert b >= a

    def test_hash_matches_int(self, stats):
        assert hash(TrackedInteger(7, stats)) == hash(7)

    def test_no_comparison_without_op(self, stats):
        TrackedInteger(1, stats)
        assert stats.comparisons == 0


class TestTrackedArrayBasics:
    def test_init_length_and_stats(self, stats):
        arr = make_array([3, 1, 2], stats)
        assert len(arr) == 3
        assert arr.stats is stats

    def test_default_stats_created(self):
        arr = TrackedArray([TrackedInteger(1, Stats())])
        assert isinstance(arr.stats, Stats)

    def test_getitem_tracks_read(self, stats):
        arr = make_array([1, 2, 3], stats)
        arr[0]
        assert stats.reads == 1
        arr[1]
        assert stats.reads == 2

    def test_getitem_returns_value(self, stats):
        arr = make_array([10, 20], stats)
        assert arr[1] == 20

    def test_setitem_tracks_write(self, stats):
        arr = make_array([1, 2, 3], stats)
        arr[0] = TrackedInteger(1, stats)
        assert stats.writes == 1

    def test_setitem_same_multiset_ok(self, stats):
        arr = make_array([1, 2, 3], stats)
        arr[0] = TrackedInteger(1, stats)
        assert list(arr) == [1, 2, 3]

    def test_swap_tracks_two_reads_two_writes(self, stats):
        arr = make_array([1, 2, 3], stats)
        arr.swap(0, 2)
        assert stats.reads == 2
        assert stats.writes == 2

    def test_swap_swaps_values(self, stats):
        arr = make_array([1, 2, 3], stats)
        arr.swap(0, 2)
        assert list(arr) == [3, 2, 1]


class TestTrackedArrayInvariant:
    @pytest.mark.parametrize(
        "mutate",
        [
            lambda arr, stats: arr.__setitem__(0, TrackedInteger(99, stats)),
            lambda arr, stats: arr.append(TrackedInteger(4, stats)),
            lambda arr, stats: arr.extend([TrackedInteger(4, stats)]),
            lambda arr, stats: arr.insert(0, TrackedInteger(4, stats)),
            lambda arr, stats: arr.remove(TrackedInteger(2, stats)),
            lambda arr, stats: arr.pop(),
            lambda arr, stats: arr.clear(),
        ],
        ids=["setitem", "append", "extend", "insert", "remove", "pop", "clear"],
    )
    def test_mutation_violates_invariant(self, stats, mutate):
        arr = make_array([1, 2, 3], stats)
        with pytest.raises(icontract.ViolationError):
            mutate(arr, stats)

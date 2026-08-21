from dataclasses import FrozenInstanceError

import icontract
import pytest

from algorithms import ALGORITHMS
from stats import Stats
from trackables import Snapshot, TrackedArray, TrackedInteger


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


class TestSnapshot:
    def test_values_and_counters(self, stats):
        arr = make_array([3, 1, 2], stats)
        arr.swap(0, 2)
        snap = arr.snapshot()
        assert snap.values == (2, 1, 3)
        assert (snap.reads, snap.writes, snap.comparisons) == (2, 2, 0)

    def test_snapshot_is_not_an_access(self, stats):
        arr = make_array([1, 2, 3], stats)
        arr.snapshot()
        assert (stats.reads, stats.writes, stats.comparisons) == (0, 0, 0)

    def test_snapshot_holds_plain_ints(self, stats):
        arr = make_array([1, 2, 3], stats)
        assert all(type(v) is int for v in arr.snapshot().values)

    def test_snapshot_is_frozen(self, stats):
        snap = make_array([1, 2, 3], stats).snapshot()
        with pytest.raises(FrozenInstanceError):
            snap.values = ()

    def test_snapshot_detached_from_later_mutation(self, stats):
        arr = make_array([1, 2, 3], stats)
        snap = arr.snapshot()
        arr.swap(0, 2)
        assert snap.values == (1, 2, 3)
        assert arr.snapshot().values == (3, 2, 1)

    def test_empty_array(self, stats):
        assert make_array([], stats).snapshot() == Snapshot((), 0, 0, 0)


class TestSnapshotValidation:
    """Only resizing is a runtime error."""

    @pytest.mark.parametrize(
        "mutate",
        [
            lambda arr, stats: arr.append(TrackedInteger(4, stats)),
            lambda arr, stats: arr.extend([TrackedInteger(4, stats)]),
            lambda arr, stats: arr.insert(0, TrackedInteger(4, stats)),
            lambda arr, stats: arr.remove(TrackedInteger(2, stats)),
            lambda arr, stats: arr.pop(),
            lambda arr, stats: arr.clear(),
        ],
        ids=["append", "extend", "insert", "remove", "pop", "clear"],
    )
    def test_resize_detected_at_snapshot(self, stats, mutate):
        arr = make_array([1, 2, 3], stats)
        mutate(arr, stats)
        with pytest.raises(icontract.ViolationError):
            arr.snapshot()

    def test_permutation_of_duplicates_allowed(self, stats):
        arr = make_array([1, 1, 2], stats)
        arr.swap(0, 2)
        assert arr.snapshot().values == (2, 1, 1)

    def test_duplicate_mid_copy_allowed(self, stats):
        """Copying out of a buffer really does put a value in memory twice."""
        arr = make_array([1, 2, 3], stats)
        buf = arr.buffer(1)
        buf[0] = arr[2]
        arr[2] = arr[0]
        assert arr.snapshot().values == (1, 2, 1)


class TestBuffer:
    def test_length_and_zero_filled(self, stats):
        assert list(make_array([1, 2, 3], stats).buffer(4)) == [0, 0, 0, 0]

    def test_default_is_empty(self, stats):
        assert list(make_array([1], stats).buffer()) == []

    def test_negative_size_rejected(self, stats):
        with pytest.raises(icontract.ViolationError):
            make_array([1], stats).buffer(-1)

    def test_shares_parent_stats(self, stats):
        assert make_array([1, 2], stats).buffer(2).stats is stats

    def test_accesses_bill_to_parent_stats(self, stats):
        arr = make_array([1, 2, 3], stats)
        buf = arr.buffer(2)
        buf[0] = TrackedInteger(9, stats)
        buf[0]
        assert (stats.reads, stats.writes) == (1, 1)

    def test_elements_compare_on_parent_stats(self, stats):
        buf = make_array([1, 2, 3], stats).buffer(2)
        _ = buf[0] < buf[1]
        assert stats.comparisons == 1


class TestSnapshotDoesNotDisturbStats:

    def test_counters_unchanged_after_activity(self, stats):
        arr = make_array([3, 1, 2], stats)
        arr.swap(0, 2)
        _ = arr[1] > arr[2]
        before = (stats.reads, stats.writes, stats.comparisons)
        arr.snapshot()
        assert (stats.reads, stats.writes, stats.comparisons) == before

    @pytest.mark.parametrize("algorithm", ALGORITHMS.values(), ids=ALGORITHMS)
    def test_sort_costs_the_same_without_snapshots(self, stats, algorithm, monkeypatch):
        """A run that snapshots every step must cost exactly what a silent run costs."""
        values = [5, 3, 4, 1, 2, 1]
        with_frames = make_array(values, stats)
        assert list(algorithm(with_frames))
        tracked = (stats.reads, stats.writes, stats.comparisons)

        monkeypatch.setattr(TrackedArray, "snapshot", lambda self: None)
        silent_stats = Stats()
        silent = make_array(values, silent_stats)
        list(algorithm(silent))

        assert tracked == (
            silent_stats.reads,
            silent_stats.writes,
            silent_stats.comparisons,
        )
        assert list(with_frames) == list(silent)

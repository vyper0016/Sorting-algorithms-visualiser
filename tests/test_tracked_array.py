from dataclasses import FrozenInstanceError

import icontract
import pytest

from algorithms import TESTABLE_ALGORITHMS
from stats import Stats
from tracked_array import DEFAULT_MARK_COLOR, Snapshot, Touch, TrackedArray, from_hex
from tracked_integer import TrackedInteger


def make_array(values, stats):
    return TrackedArray([TrackedInteger(v, stats) for v in values], stats)


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


class TestSharedStats:
    """The array counts on the same Stats its elements carry."""

    def test_stats_derived_from_elements(self, stats):
        arr = TrackedArray([TrackedInteger(v, stats) for v in (1, 2)])
        assert arr.stats is stats

    def test_empty_array_gets_a_fresh_stats(self):
        arr = TrackedArray([])
        assert isinstance(arr.stats, Stats)

    def test_elements_on_different_stats_rejected(self, stats):
        with pytest.raises(icontract.ViolationError):
            TrackedArray([TrackedInteger(1, stats), TrackedInteger(2, Stats())])

    def test_stats_not_matching_elements_rejected(self, stats):
        with pytest.raises(icontract.ViolationError):
            TrackedArray([TrackedInteger(1, stats)], Stats())

    def test_element_comparison_lands_on_array_stats(self, stats):
        arr = TrackedArray([TrackedInteger(v, stats) for v in (1, 2)])
        _ = arr[0] < arr[1]
        assert (arr.stats.reads, arr.stats.comparisons) == (2, 1)


class TestSlices:
    def test_slice_reads_every_element_copied(self, stats):
        arr = make_array([1, 2, 3, 4], stats)
        arr[1:3]
        assert stats.reads == 2

    def test_slice_returns_tracked_array_sharing_stats(self, stats):
        head = make_array([1, 2, 3], stats)[:2]
        assert type(head) is TrackedArray
        assert head.stats is stats
        assert list(head) == [1, 2]

    def test_copy_is_tracked_and_billed(self, stats):
        arr = make_array([1, 2, 3], stats)
        duplicate = arr.copy()
        assert type(duplicate) is TrackedArray
        assert list(duplicate) == [1, 2, 3]
        assert stats.reads == 3

    def test_same_length_slice_assignment_counts_writes(self, stats):
        arr = make_array([1, 2, 3], stats)
        arr[0:2] = [TrackedInteger(9, stats), TrackedInteger(8, stats)]
        assert list(arr) == [9, 8, 3]
        assert stats.writes == 2


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


class TestTouches:
    """Every access names the slot it hit, for one frame only."""

    def test_read_recorded(self, stats):
        arr = make_array([1, 2, 3], stats)
        arr[1]
        assert arr.snapshot().touches == ((1, Touch.READ),)

    def test_write_recorded(self, stats):
        arr = make_array([1, 2, 3], stats)
        arr[2] = TrackedInteger(9, stats)
        assert arr.snapshot().touches == ((2, Touch.WRITE),)

    def test_negative_index_normalised(self, stats):
        arr = make_array([1, 2, 3], stats)
        arr[-1]
        assert arr.snapshot().touches == ((2, Touch.READ),)

    def test_order_and_repeats_kept(self, stats):
        arr = make_array([1, 2, 3], stats)
        arr.swap(0, 2)
        assert arr.snapshot().touches == (
            (2, Touch.READ),
            (0, Touch.READ),
            (0, Touch.WRITE),
            (2, Touch.WRITE),
        )

    def test_slice_read_names_every_slot(self, stats):
        arr = make_array([1, 2, 3, 4], stats)
        arr[1:3]
        assert arr.snapshot().touches == ((1, Touch.READ), (2, Touch.READ))

    def test_slice_write_names_every_slot(self, stats):
        arr = make_array([1, 2, 3], stats)
        arr[0:2] = [TrackedInteger(9, stats), TrackedInteger(8, stats)]
        assert arr.snapshot().touches == ((0, Touch.WRITE), (1, Touch.WRITE))

    def test_out_of_range_read_records_nothing(self, stats):
        arr = make_array([1, 2, 3], stats)
        with pytest.raises(IndexError):
            arr[5]
        assert arr.snapshot().touches == ()

    def test_snapshot_spends_the_touches(self, stats):
        arr = make_array([1, 2, 3], stats)
        arr[0]
        assert arr.snapshot().touches == ((0, Touch.READ),)
        assert arr.snapshot().touches == ()

    def test_frames_do_not_accumulate(self, stats):
        arr = make_array([1, 2, 3], stats)
        frames = []
        for index in range(3):
            arr[index]
            frames.append(arr.snapshot().touches)
        assert frames == [
            ((0, Touch.READ),),
            ((1, Touch.READ),),
            ((2, Touch.READ),),
        ]

    def test_marks_outlive_the_frame(self, stats):
        arr = make_array([1, 2, 3], stats)
        arr.mark(1)
        assert arr.snapshot().marks == ((1, DEFAULT_MARK_COLOR),)
        assert arr.snapshot().marks == ((1, DEFAULT_MARK_COLOR),)


class TestFromHex:
    """Hex codes are for the author to read; the model still stores channels."""

    @pytest.mark.parametrize(
        ("code", "color"),
        [
            ("#000000", (0, 0, 0)),
            ("#ffffff", (255, 255, 255)),
            ("#ff0000", (255, 0, 0)),
            ("#00ff00", (0, 255, 0)),
            ("#0000ff", (0, 0, 255)),
            ("#00ff7f", (0, 255, 127)),
        ],
    )
    def test_channels(self, code, color):
        assert from_hex(code) == color

    def test_hash_is_optional(self):
        assert from_hex("00ff7f") == from_hex("#00ff7f")

    def test_case_insensitive(self):
        assert from_hex("#AaBbCc") == from_hex("#aabbcc")

    def test_default_mark_color_is_red(self):
        assert DEFAULT_MARK_COLOR == from_hex("#ff0000")

    @pytest.mark.parametrize(
        "code", ["", "#", "#fff", "#fffffff", "#gggggg", "0xff0000", "#ff 000"]
    )
    def test_malformed_code_rejected(self, code):
        with pytest.raises(icontract.ViolationError):
            from_hex(code)


class TestMarks:
    """Colours the algorithm author sets by hand, free and persistent."""

    def test_default_color(self, stats):
        arr = make_array([1, 2, 3], stats)
        arr.mark(1)
        assert arr.snapshot().marks == ((1, DEFAULT_MARK_COLOR),)

    def test_custom_color(self, stats):
        arr = make_array([1, 2, 3], stats)
        arr.mark(0, (0, 0, 255))
        assert arr.snapshot().marks == ((0, (0, 0, 255)),)

    def test_remark_replaces_color(self, stats):
        arr = make_array([1, 2, 3], stats)
        arr.mark(0, (0, 0, 255))
        arr.mark(0, (0, 255, 0))
        assert arr.snapshot().marks == ((0, (0, 255, 0)),)

    def test_marks_sorted_by_index(self, stats):
        arr = make_array([1, 2, 3], stats)
        arr.mark(2)
        arr.mark(0)
        assert [index for index, _ in arr.snapshot().marks] == [0, 2]

    def test_negative_index_normalised(self, stats):
        arr = make_array([1, 2, 3], stats)
        arr.mark(-1)
        assert arr.snapshot().marks == ((2, DEFAULT_MARK_COLOR),)

    def test_marks_survive_snapshots(self, stats):
        arr = make_array([1, 2, 3], stats)
        arr.mark(1)
        arr.snapshot()
        assert arr.snapshot().marks == ((1, DEFAULT_MARK_COLOR),)

    def test_unmark_removes(self, stats):
        arr = make_array([1, 2, 3], stats)
        arr.mark(1)
        arr.unmark(1)
        assert arr.snapshot().marks == ()

    def test_unmark_unmarked_is_harmless(self, stats):
        arr = make_array([1, 2, 3], stats)
        arr.unmark(1)
        assert arr.snapshot().marks == ()

    def test_unmark_all(self, stats):
        arr = make_array([1, 2, 3], stats)
        arr.mark(0)
        arr.mark(2)
        arr.unmark_all()
        assert arr.snapshot().marks == ()

    @pytest.mark.parametrize("index", [3, -4])
    def test_out_of_range_rejected(self, stats, index):
        arr = make_array([1, 2, 3], stats)
        with pytest.raises(icontract.ViolationError):
            arr.mark(index)
        with pytest.raises(icontract.ViolationError):
            arr.unmark(index)

    def test_marking_is_free(self, stats):
        arr = make_array([1, 2, 3], stats)
        arr.mark(0)
        arr.unmark(0)
        assert (stats.reads, stats.writes, stats.comparisons) == (0, 0, 0)

    def test_mark_is_not_a_touch(self, stats):
        arr = make_array([1, 2, 3], stats)
        arr.mark(0)
        assert arr.snapshot().touches == ()


class TestRejectedMutation:
    """Resizing or moving elements uncounted fails where it is called."""

    @pytest.mark.parametrize(
        "mutate",
        [
            lambda arr, stats: arr.append(TrackedInteger(4, stats)),
            lambda arr, stats: arr.extend([TrackedInteger(4, stats)]),
            lambda arr, stats: arr.insert(0, TrackedInteger(4, stats)),
            lambda arr, stats: arr.remove(TrackedInteger(2, stats)),
            lambda arr, stats: arr.pop(),
            lambda arr, stats: arr.clear(),
            lambda arr, stats: arr.reverse(),
            lambda arr, stats: arr.__delitem__(0),
            lambda arr, stats: arr.__iadd__([TrackedInteger(4, stats)]),
            lambda arr, stats: arr.__imul__(2),
            lambda arr, stats: arr.__setitem__(slice(0, 2), []),
        ],
        ids=[
            "append",
            "extend",
            "insert",
            "remove",
            "pop",
            "clear",
            "reverse",
            "del",
            "iadd",
            "imul",
            "resizing_slice_assignment",
        ],
    )
    def test_rejected_at_call(self, stats, mutate):
        arr = make_array([1, 2, 3], stats)
        with pytest.raises(TypeError):
            mutate(arr, stats)

    def test_rejection_leaves_array_and_counters_untouched(self, stats):
        arr = make_array([1, 2, 3], stats)
        with pytest.raises(TypeError):
            arr.append(TrackedInteger(4, stats))
        assert list(arr) == [1, 2, 3]
        assert (stats.reads, stats.writes) == (0, 0)


class TestSnapshotValidation:

    def test_resize_detected_at_snapshot(self, stats):
        arr = make_array([1, 2, 3], stats)
        list.append(arr, TrackedInteger(4, stats))
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

    @pytest.mark.parametrize(
        "algorithm", TESTABLE_ALGORITHMS.values(), ids=TESTABLE_ALGORITHMS
    )
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

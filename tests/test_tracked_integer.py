import pytest

from tracked_integer import TrackedInteger


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

    @pytest.mark.parametrize(
        "op",
        [
            lambda a: a + 1,
            lambda a: 1 + a,
            lambda a: a - 1,
            lambda a: 1 - a,
            lambda a: a * 2,
            lambda a: 2 * a,
            lambda a: a // 2,
            lambda a: 8 // a,
            lambda a: a % 2,
            lambda a: 8 % a,
            lambda a: -a,
            lambda a: abs(a),
        ],
        ids=[
            "add",
            "radd",
            "sub",
            "rsub",
            "mul",
            "rmul",
            "floordiv",
            "rfloordiv",
            "mod",
            "rmod",
            "neg",
            "abs",
        ],
    )
    def test_arithmetic_stays_tracked(self, stats, op):
        result = op(TrackedInteger(3, stats))
        assert isinstance(result, TrackedInteger)
        assert result.stats is stats

    def test_arithmetic_value_correct(self, stats):
        assert TrackedInteger(7, stats) // 2 == 3
        assert 10 - TrackedInteger(4, stats) == 6

    def test_arithmetic_does_not_count_a_comparison(self, stats):
        TrackedInteger(3, stats) + 1
        assert stats.comparisons == 0

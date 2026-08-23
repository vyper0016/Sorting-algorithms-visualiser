"""How many snapshots one drawn frame consumes, shared by the window and the export."""

MAX_STEPS_PER_FRAME = 512


def budget(overdue: float, delay_ms: float, running: bool) -> tuple[int, float]:
    """The snapshots to take now, and the waiting time left over afterwards.

    A delay longer than one frame leaves whole frames with nothing to take,
    which is what keeps a slow run slow instead of one step per frame.

    >>> budget(16.7, 50.0, True)
    (0, 16.7)
    >>> budget(150.0, 50.0, True)
    (3, 0.0)
    >>> budget(16.7, 50.0, False)
    (0, 0.0)
    >>> budget(16.7, 0.0, True)
    (512, 0.0)
    """
    if not running:
        return 0, 0.0

    if delay_ms <= 0:
        return MAX_STEPS_PER_FRAME, 0.0

    steps = min(int(overdue // delay_ms), MAX_STEPS_PER_FRAME)

    if steps == MAX_STEPS_PER_FRAME:
        return steps, 0.0

    return steps, overdue - steps * delay_ms

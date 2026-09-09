from agent.workflow.sla import SlaTimer, priority


def test_matrix_corners():
    assert priority(1, 1) == 1
    assert priority(3, 3) == 5


def test_timer_breach_with_fake_clock():
    t = {"now": 0.0}
    timer = SlaTimer(target_min=10, clock=lambda: t["now"])
    timer.start()
    t["now"] = 5 * 60
    assert not timer.breached()
    t["now"] = 11 * 60
    assert timer.breached()

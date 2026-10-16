"""End-to-end test: full 4-member cycle with mixed partial payments."""

from decimal import Decimal
import pytest

from susu.group import SusuGroup
from susu.report import build_report, render_report
from susu.errors import GroupCompletedError


def test_four_member_full_cycle_with_partial_payments():
    """
    Four members, GHS 40.00 weekly.
    Pot per week = 40 * 4 = GHS 160.00.

    Payment pattern per week — deliberately varied:
      Week 1: Ama full, Kofi 2x partial, Esi 4x partial, Yaw full  -> Ama gets 160
      Week 2: everyone pays in one shot                             -> Kofi gets 160
      Week 3: Ama full, Kofi partial+partial, Esi full, Yaw full   -> Esi gets 160
      Week 4: all at once                                           -> Yaw gets 160
    """
    g = SusuGroup("40")
    g.add_member("ama",  "Ama")
    g.add_member("kofi", "Kofi")
    g.add_member("esi",  "Esi")
    g.add_member("yaw",  "Yaw")

    # ------------------------------------------------------------------ Week 1
    g.record_contribution("ama",  "40")               # full
    g.record_contribution("kofi", "15")               # partial
    g.record_contribution("kofi", "25")               # completes Kofi
    g.record_contribution("esi",  "10")
    g.record_contribution("esi",  "10")
    g.record_contribution("esi",  "10")
    g.record_contribution("esi",  "10")               # 4 x 10 = 40
    g.record_contribution("yaw",  "40")

    # Verify balances before close
    assert g.is_paid_in_full("ama")
    assert g.is_paid_in_full("kofi")
    assert g.is_paid_in_full("esi")
    assert g.is_paid_in_full("yaw")

    r1 = g.close_week()
    assert r1.closed is True
    assert r1.payout.member_id == "ama"
    assert r1.payout.amount == Decimal("160.00")
    assert g.current_week == 2

    # ------------------------------------------------------------------ Week 2
    for mid in ("ama", "kofi", "esi", "yaw"):
        g.record_contribution(mid, "40")

    r2 = g.close_week()
    assert r2.closed is True
    assert r2.payout.member_id == "kofi"
    assert r2.payout.amount == Decimal("160.00")
    assert g.current_week == 3

    # ------------------------------------------------------------------ Week 3
    g.record_contribution("ama",  "40")
    g.record_contribution("kofi", "20")
    g.record_contribution("kofi", "20")               # two partial payments
    g.record_contribution("esi",  "40")
    g.record_contribution("yaw",  "40")

    r3 = g.close_week()
    assert r3.closed is True
    assert r3.payout.member_id == "esi"
    assert r3.payout.amount == Decimal("160.00")
    assert g.current_week == 4

    # ------------------------------------------------------------------ Week 4 — last
    for mid in ("ama", "kofi", "esi", "yaw"):
        g.record_contribution(mid, "40")

    r4 = g.close_week()
    assert r4.closed is True
    assert r4.payout.member_id == "yaw"
    assert r4.payout.amount == Decimal("160.00")

    # ------------------------------------------------------------------ Completion
    assert g._completed is True
    assert g.next_recipient() is None
    assert len(g.payout_history) == 4

    total = sum(p.amount for p in g.payout_history)
    assert total == Decimal("640.00")   # 160 * 4

    # ------------------------------------------------------------------ Report
    report = build_report(g)
    assert report.week_label == "completed"
    assert report.total_pot_paid_out == Decimal("640.00")
    assert len(report.payout_history) == 4
    assert report.paid_in_full == []
    assert report.owing == {}

    text = render_report(report)
    assert "completed" in text
    assert "GHS 640.00" in text

    # ------------------------------------------------------------------ Completed guard
    with pytest.raises(GroupCompletedError):
        g.record_contribution("ama", "40")

    with pytest.raises(GroupCompletedError):
        g.close_week()


def test_partial_close_attempt_changes_no_state():
    """A failed close in the middle of a cycle must leave everything unchanged."""
    g = SusuGroup("50")
    g.add_member("p", "P")
    g.add_member("q", "Q")

    g.record_contribution("p", "30")
    # Q has not paid at all

    week_before = g.current_week
    history_len = len(g.payout_history)

    result = g.close_week()

    assert result.closed is False
    assert g.current_week == week_before
    assert len(g.payout_history) == history_len
    # P's partial payment is still intact
    assert g.amount_paid("p") == Decimal("30.00")
    assert g.amount_owed("q") == Decimal("50.00")

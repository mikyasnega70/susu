"""Tests for SusuGroup.close_week() and next_recipient()."""

import pytest
from decimal import Decimal

from susu.group import SusuGroup
from susu.errors import GroupCompletedError
from susu.models import WeekCloseResult, Payout


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_group(*names: str, contribution: str = "50") -> SusuGroup:
    """Create a SusuGroup with the given member names (used as IDs too)."""
    g = SusuGroup(contribution)
    for name in names:
        g.add_member(name.lower(), name)
    return g


def pay_all(group: SusuGroup, *member_ids: str) -> None:
    """Pay the full weekly contribution for every listed member."""
    for mid in member_ids:
        group.record_contribution(mid, group.weekly_contribution)


# ---------------------------------------------------------------------------
# Spec example: Ama, Kofi, Esi — week 1
# ---------------------------------------------------------------------------

class TestSpecExample:
    def setup_method(self):
        self.g = make_group("Ama", "Kofi", "Esi")

    def test_close_fails_when_esi_owes_20(self):
        """Close is rejected; outstanding shows Ama, Kofi, Esi all owe 50."""
        result = self.g.close_week()
        assert result.closed is False
        assert result.week == 1
        assert result.payout is None
        assert set(result.outstanding.keys()) == {"ama", "kofi", "esi"}

    def test_close_fails_after_esi_pays_30(self):
        self.g.record_contribution("esi", "30")
        result = self.g.close_week()
        assert result.closed is False
        # Esi still owes exactly 20.00
        assert result.outstanding["esi"] == Decimal("20.00")
        # Ama and Kofi each owe 50.00
        assert result.outstanding["ama"] == Decimal("50.00")
        assert result.outstanding["kofi"] == Decimal("50.00")

    def test_close_fails_does_not_change_state(self):
        self.g.record_contribution("esi", "30")
        before_week = self.g.current_week
        self.g.close_week()
        assert self.g.current_week == before_week
        assert self.g.payout_history == []

    def test_close_succeeds_when_all_paid(self):
        pay_all(self.g, "ama", "kofi")
        self.g.record_contribution("esi", "30")
        self.g.record_contribution("esi", "20")

        result = self.g.close_week()

        assert result.closed is True
        assert result.week == 1
        assert result.outstanding == {}

    def test_week_1_payout_goes_to_ama(self):
        """join_order 1 == week 1, so Ama gets the pot."""
        pay_all(self.g, "ama", "kofi", "esi")
        result = self.g.close_week()

        assert result.payout is not None
        assert result.payout.member_id == "ama"

    def test_payout_amount_is_contribution_x_members(self):
        pay_all(self.g, "ama", "kofi", "esi")
        result = self.g.close_week()
        assert result.payout.amount == Decimal("150.00")  # 50 * 3

    def test_week_advances_to_2_after_close(self):
        pay_all(self.g, "ama", "kofi", "esi")
        self.g.close_week()
        assert self.g.current_week == 2

    def test_week_2_next_recipient_is_kofi(self):
        pay_all(self.g, "ama", "kofi", "esi")
        self.g.close_week()
        assert self.g.next_recipient().id == "kofi"  # join_order 2

    def test_payout_appended_to_history(self):
        pay_all(self.g, "ama", "kofi", "esi")
        result = self.g.close_week()
        assert len(self.g.payout_history) == 1
        assert self.g.payout_history[0] is result.payout


# ---------------------------------------------------------------------------
# Full multi-week cycle through completion
# ---------------------------------------------------------------------------

class TestFullCycle:
    def test_two_member_full_cycle(self):
        g = make_group("Alice", "Bob", contribution="100")
        # Week 1: Alice receives pot
        pay_all(g, "alice", "bob")
        r1 = g.close_week()
        assert r1.closed is True
        assert r1.payout.member_id == "alice"
        assert r1.payout.amount == Decimal("200.00")  # 100 * 2

        # Week 2: Bob receives pot
        pay_all(g, "alice", "bob")
        r2 = g.close_week()
        assert r2.closed is True
        assert r2.payout.member_id == "bob"
        assert r2.payout.amount == Decimal("200.00")

        assert len(g.payout_history) == 2
        assert g._completed is True

    def test_three_member_full_cycle_payouts_exact(self):
        g = make_group("X", "Y", "Z", contribution="10")
        expected_recipients = ["x", "y", "z"]

        for i, expected_id in enumerate(expected_recipients, start=1):
            pay_all(g, "x", "y", "z")
            result = g.close_week()
            assert result.closed is True
            assert result.payout.member_id == expected_id
            assert result.payout.amount == Decimal("30.00")
            assert result.week == i

        assert g._completed is True
        assert g.next_recipient() is None

    def test_completed_raises_on_contribution(self):
        g = make_group("A", "B", contribution="10")
        pay_all(g, "a", "b")
        g.close_week()
        pay_all(g, "a", "b")
        g.close_week()
        assert g._completed is True
        with pytest.raises(GroupCompletedError):
            g.record_contribution("a", "10")

    def test_completed_raises_on_close(self):
        g = make_group("A", "B", contribution="10")
        for _ in range(2):
            pay_all(g, "a", "b")
            g.close_week()
        with pytest.raises(GroupCompletedError):
            g.close_week()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestCloseWeekEdgeCases:
    def test_minimum_member_guard(self):
        g = SusuGroup("50")
        g.add_member("solo")
        with pytest.raises(ValueError, match="2 members"):
            g.close_week()

    def test_failed_close_leaves_history_empty(self):
        g = make_group("P", "Q")
        g.record_contribution("p", "10")
        g.close_week()
        assert g.payout_history == []

    def test_payout_amount_exact_decimal(self):
        """Pot must be exact Decimal multiplication, not float arithmetic."""
        g = make_group("A", "B", "C", contribution="33.33")
        pay_all(g, "a", "b", "c")
        result = g.close_week()
        assert result.payout.amount == Decimal("99.99")

    def test_next_recipient_before_any_close(self):
        g = make_group("One", "Two")
        assert g.next_recipient().id == "one"

    def test_outstanding_contains_only_unpaid_members(self):
        g = make_group("A", "B", "C")
        pay_all(g, "a", "b")   # C has not paid
        result = g.close_week()
        assert "c" in result.outstanding
        assert "a" not in result.outstanding
        assert "b" not in result.outstanding

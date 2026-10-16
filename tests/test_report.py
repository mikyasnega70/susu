"""Tests for susu.report: build_report and render_report."""

import pytest
from decimal import Decimal

from susu.group import SusuGroup
from susu.report import build_report, render_report, SusuReport, PayoutRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_ama_kofi_esi() -> SusuGroup:
    """Three-member group from the spec: Ama, Kofi, Esi at GHS 50."""
    g = SusuGroup("50")
    g.add_member("ama", "Ama")
    g.add_member("kofi", "Kofi")
    g.add_member("esi", "Esi")
    return g


def pay_all(group: SusuGroup) -> None:
    for m in group.members:
        group.record_contribution(m.id, group.weekly_contribution)


# ---------------------------------------------------------------------------
# build_report — data correctness
# ---------------------------------------------------------------------------

class TestBuildReportNoMembers:
    def test_empty_group(self):
        g = SusuGroup("50")
        r = build_report(g)
        assert r.week_label == "1"
        assert r.weekly_contribution == Decimal("50.00")
        assert r.next_recipient_name is None
        assert r.paid_in_full == []
        assert r.owing == {}
        assert r.payout_history == []
        assert r.total_pot_paid_out == Decimal("0.00")


class TestBuildReportMidWeek:
    """Spec example: week 1, Esi has paid 30, Ama and Kofi have not paid."""

    def setup_method(self):
        self.g = make_ama_kofi_esi()
        self.g.record_contribution("esi", "30")
        self.r = build_report(self.g)

    def test_week_label(self):
        assert self.r.week_label == "1"

    def test_next_recipient_is_ama(self):
        assert self.r.next_recipient_name == "Ama"

    def test_nobody_paid_in_full(self):
        assert self.r.paid_in_full == []

    def test_owing_contains_all_three(self):
        assert self.r.owing == {
            "Ama": Decimal("50.00"),
            "Kofi": Decimal("50.00"),
            "Esi": Decimal("20.00"),
        }

    def test_no_payout_history(self):
        assert self.r.payout_history == []

    def test_total_paid_out_zero(self):
        assert self.r.total_pot_paid_out == Decimal("0.00")


class TestBuildReportAfterWeek1Closes:
    """Spec example: everyone pays, week 1 closes, Ama receives GHS 150."""

    def setup_method(self):
        self.g = make_ama_kofi_esi()
        pay_all(self.g)
        self.g.close_week()
        self.r = build_report(self.g)

    def test_week_label(self):
        assert self.r.week_label == "2"

    def test_next_recipient_is_kofi(self):
        assert self.r.next_recipient_name == "Kofi"

    def test_nobody_paid_in_full_for_week_2_yet(self):
        assert self.r.paid_in_full == []

    def test_everyone_owes_for_week_2(self):
        assert set(self.r.owing.keys()) == {"Ama", "Kofi", "Esi"}
        for owed in self.r.owing.values():
            assert owed == Decimal("50.00")

    def test_payout_history_has_one_entry(self):
        assert len(self.r.payout_history) == 1
        rec = self.r.payout_history[0]
        assert rec.week == 1
        assert rec.member_name == "Ama"
        assert rec.amount == Decimal("150.00")

    def test_total_paid_out(self):
        assert self.r.total_pot_paid_out == Decimal("150.00")


class TestBuildReportEveryonePaidCurrentWeek:
    def test_all_in_paid_in_full_list(self):
        g = make_ama_kofi_esi()
        pay_all(g)
        r = build_report(g)
        assert set(r.paid_in_full) == {"Ama", "Kofi", "Esi"}
        assert r.owing == {}


class TestBuildReportCompleted:
    def test_completed_group(self):
        g = SusuGroup("10")
        g.add_member("x", "X")
        g.add_member("y", "Y")
        for _ in range(2):
            pay_all(g)
            g.close_week()

        r = build_report(g)
        assert r.week_label == "completed"
        assert r.next_recipient_name is None
        assert r.paid_in_full == []
        assert r.owing == {}
        assert len(r.payout_history) == 2
        assert r.total_pot_paid_out == Decimal("40.00")  # 10*2 * 2 weeks


class TestBuildReportDoesNotPrint:
    def test_returns_dataclass_not_none(self):
        g = make_ama_kofi_esi()
        result = build_report(g)
        assert isinstance(result, SusuReport)


# ---------------------------------------------------------------------------
# render_report — text output
# ---------------------------------------------------------------------------

class TestRenderReportContents:
    def setup_method(self):
        self.g = make_ama_kofi_esi()
        self.g.record_contribution("esi", "30")
        self.text = render_report(build_report(self.g))

    def test_header_present(self):
        assert "SUSU REPORT" in self.text

    def test_week_shown(self):
        assert "Week" in self.text
        assert "1" in self.text

    def test_contribution_shown(self):
        assert "GHS 50.00" in self.text

    def test_next_recipient_shown(self):
        assert "Ama" in self.text

    def test_esi_owed_amount(self):
        assert "Esi" in self.text
        assert "GHS 20.00" in self.text

    def test_no_payout_history_message(self):
        assert "none yet" in self.text


class TestRenderReportAfterClose:
    def setup_method(self):
        self.g = make_ama_kofi_esi()
        pay_all(self.g)
        self.g.close_week()
        self.text = render_report(build_report(self.g))

    def test_week_2_shown(self):
        assert "2" in self.text

    def test_kofi_next_recipient(self):
        assert "Kofi" in self.text

    def test_payout_history_shows_ama(self):
        assert "Ama" in self.text
        assert "GHS 150.00" in self.text

    def test_total_paid_out_shown(self):
        assert "GHS 150.00" in self.text


class TestRenderReportCompleted:
    def test_completed_label(self):
        g = SusuGroup("10")
        g.add_member("a", "A")
        g.add_member("b", "B")
        for _ in range(2):
            pay_all(g)
            g.close_week()
        text = render_report(build_report(g))
        assert "completed" in text

    def test_no_next_recipient_shown(self):
        g = SusuGroup("10")
        g.add_member("a", "A")
        g.add_member("b", "B")
        for _ in range(2):
            pay_all(g)
            g.close_week()
        text = render_report(build_report(g))
        assert "—" in text  # dash for missing next recipient

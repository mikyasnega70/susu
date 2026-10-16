"""Tests for SusuGroup.record_contribution and related query helpers."""

import pytest
from decimal import Decimal

from susu.group import SusuGroup
from susu.errors import (
    GroupCompletedError,
    GroupLockedError,
    InvalidAmountError,
    OverpaymentError,
    UnknownMemberError,
)


@pytest.fixture
def group():
    """A group with two members, weekly contribution of GHS 50."""
    g = SusuGroup("50")
    g.add_member("esi", "Esi")
    g.add_member("kofi", "Kofi")
    return g


class TestPartialPayments:
    def test_esi_pays_30_then_20(self, group):
        group.record_contribution("esi", "30")
        assert group.amount_paid("esi") == Decimal("30.00")
        assert group.amount_owed("esi") == Decimal("20.00")
        assert group.is_paid_in_full("esi") is False

        group.record_contribution("esi", "20")
        assert group.amount_paid("esi") == Decimal("50.00")
        assert group.amount_owed("esi") == Decimal("0.00")
        assert group.is_paid_in_full("esi") is True

    def test_exact_full_payment_in_one_go(self, group):
        group.record_contribution("kofi", "50")
        assert group.is_paid_in_full("kofi") is True
        assert group.amount_paid("kofi") == Decimal("50.00")

    def test_ten_payments_of_five(self, group):
        for _ in range(10):
            group.record_contribution("esi", "5")
        assert group.amount_paid("esi") == Decimal("50.00")
        assert group.is_paid_in_full("esi") is True

    def test_five_hundred_payments_of_010(self, group):
        for _ in range(500):
            group.record_contribution("esi", "0.10")
        assert group.amount_paid("esi") == Decimal("50.00")
        assert group.is_paid_in_full("esi") is True

    def test_returns_cumulative_after_each_call(self, group):
        r1 = group.record_contribution("esi", "10")
        assert r1 == Decimal("10.00")
        r2 = group.record_contribution("esi", "15")
        assert r2 == Decimal("25.00")


class TestOverpayment:
    def test_overpayment_by_one_cent(self, group):
        # owed is 50.00; paying 50.01 triggers OverpaymentError referencing 50.00
        with pytest.raises(OverpaymentError, match="50.00"):
            group.record_contribution("esi", "50.01")

    def test_overpayment_after_partial(self, group):
        group.record_contribution("esi", "30")
        with pytest.raises(OverpaymentError, match="20.00"):
            group.record_contribution("esi", "20.01")

    def test_overpayment_message_contains_remaining(self, group):
        group.record_contribution("esi", "45")
        with pytest.raises(OverpaymentError) as exc_info:
            group.record_contribution("esi", "5.01")
        assert "5.00" in str(exc_info.value)


class TestInvalidAmount:
    def test_zero_amount(self, group):
        with pytest.raises(InvalidAmountError):
            group.record_contribution("esi", "0")

    def test_negative_amount(self, group):
        with pytest.raises(InvalidAmountError):
            group.record_contribution("esi", "-1")

    def test_float_amount(self, group):
        with pytest.raises(InvalidAmountError):
            group.record_contribution("esi", 10.0)

    def test_too_many_decimal_places(self, group):
        with pytest.raises(InvalidAmountError):
            group.record_contribution("esi", "1.001")

    def test_nonsense_string(self, group):
        with pytest.raises(InvalidAmountError):
            group.record_contribution("esi", "abc")


class TestUnknownMember:
    def test_unknown_member_raises(self, group):
        with pytest.raises(UnknownMemberError):
            group.record_contribution("ghost", "10")

    def test_unknown_member_in_amount_paid(self, group):
        with pytest.raises(UnknownMemberError):
            group.amount_paid("nobody")

    def test_unknown_member_in_amount_owed(self, group):
        with pytest.raises(UnknownMemberError):
            group.amount_owed("nobody")


class TestGroupCompletedError:
    def test_rejects_contribution_when_completed(self, group):
        group._completed = True
        with pytest.raises(GroupCompletedError):
            group.record_contribution("esi", "50")


class TestMemberCountGuard:
    def test_fewer_than_2_members_rejected(self):
        g = SusuGroup("50")
        g.add_member("solo")
        with pytest.raises(ValueError, match="2 members"):
            g.record_contribution("solo", "50")


class TestLockRule:
    def test_first_contribution_locks_member_list(self, group):
        assert group._locked is False
        group.record_contribution("esi", "10")
        assert group._locked is True

    def test_cannot_add_member_after_first_contribution(self, group):
        group.record_contribution("esi", "10")
        with pytest.raises(GroupLockedError):
            group.add_member("newperson")

    def test_can_still_add_before_any_contribution(self, group):
        group.add_member("third")   # should not raise
        assert len(group.members) == 3


class TestWeekSpecificQueries:
    def test_amount_paid_for_specific_week(self, group):
        group.record_contribution("esi", "50")
        # week 2 not yet started; esi has paid nothing there
        assert group.amount_paid("esi", week=2) == Decimal("0.00")

    def test_amount_owed_for_specific_week(self, group):
        group.record_contribution("esi", "50")
        assert group.amount_owed("esi", week=2) == Decimal("50.00")

    def test_is_paid_in_full_specific_week(self, group):
        group.record_contribution("esi", "50")
        assert group.is_paid_in_full("esi", week=1) is True
        assert group.is_paid_in_full("esi", week=2) is False

"""Tests for SusuGroup member management."""

import pytest
from decimal import Decimal

from susu.group import SusuGroup
from susu.errors import (
    DuplicateMemberError,
    GroupLockedError,
    InvalidAmountError,
)


class TestSusuGroupInit:
    def test_valid_contribution(self):
        g = SusuGroup("50")
        assert g.weekly_contribution == Decimal("50.00")

    def test_contribution_as_int(self):
        g = SusuGroup(20)
        assert g.weekly_contribution == Decimal("20.00")

    def test_contribution_as_decimal(self):
        g = SusuGroup(Decimal("10.50"))
        assert g.weekly_contribution == Decimal("10.50")

    def test_rejects_zero(self):
        with pytest.raises(InvalidAmountError):
            SusuGroup("0")

    def test_rejects_negative(self):
        with pytest.raises(InvalidAmountError):
            SusuGroup("-5")

    def test_rejects_float(self):
        with pytest.raises(InvalidAmountError):
            SusuGroup(10.0)

    def test_rejects_too_many_decimals(self):
        with pytest.raises(InvalidAmountError):
            SusuGroup("10.999")

    def test_starts_at_week_1(self):
        g = SusuGroup("50")
        assert g.current_week == 1


class TestAddMember:
    def setup_method(self):
        self.group = SusuGroup("50")

    def test_add_single_member(self):
        m = self.group.add_member("alice", "Alice")
        assert m.id == "alice"
        assert m.name == "Alice"
        assert m.join_order == 1

    def test_join_order_increments(self):
        self.group.add_member("alice")
        m2 = self.group.add_member("bob")
        assert m2.join_order == 2

    def test_id_is_normalised_lowercase(self):
        m = self.group.add_member("  Alice  ")
        assert m.id == "alice"

    def test_duplicate_exact(self):
        self.group.add_member("alice")
        with pytest.raises(DuplicateMemberError):
            self.group.add_member("alice")

    def test_duplicate_case_insensitive(self):
        self.group.add_member("alice")
        with pytest.raises(DuplicateMemberError):
            self.group.add_member("ALICE")

    def test_duplicate_with_whitespace(self):
        self.group.add_member("alice")
        with pytest.raises(DuplicateMemberError):
            self.group.add_member("  alice  ")

    def test_rejects_blank_id(self):
        with pytest.raises(ValueError):
            self.group.add_member("   ")

    def test_rejects_empty_id(self):
        with pytest.raises(ValueError):
            self.group.add_member("")

    def test_members_list_ordered_by_join(self):
        self.group.add_member("charlie")
        self.group.add_member("alice")
        self.group.add_member("bob")
        ids = [m.id for m in self.group.members]
        assert ids == ["charlie", "alice", "bob"]

    def test_name_defaults_to_member_id(self):
        m = self.group.add_member("dave")
        assert m.name == "dave"


class TestGroupLock:
    def test_locked_after_lock_called(self):
        g = SusuGroup("50")
        g.add_member("alice")
        g._lock()
        with pytest.raises(GroupLockedError):
            g.add_member("bob")

    def test_not_locked_initially(self):
        g = SusuGroup("50")
        # Should not raise before any contributions
        g.add_member("alice")
        g.add_member("bob")

"""SusuGroup: manages members and state for one rotating savings group."""

from decimal import Decimal
from collections import defaultdict

from .errors import (
    DuplicateMemberError,
    GroupCompletedError,
    GroupLockedError,
    InvalidAmountError,
    OverpaymentError,
    UnknownMemberError,
)
from .models import Member, Payout, WeekCloseResult
from .money import parse_amount


class SusuGroup:
    """A rotating savings group (susu).

    Args:
        weekly_contribution: Fixed amount every member pays each week.
                             Must be > 0. Accepts str, int, or Decimal.
    """

    def __init__(self, weekly_contribution: str | int | Decimal) -> None:
        try:
            amount = parse_amount(weekly_contribution)
        except (TypeError, ValueError) as exc:
            raise InvalidAmountError(str(exc)) from exc

        if amount <= Decimal("0.00"):
            raise InvalidAmountError("Weekly contribution must be greater than zero")

        self._weekly_contribution: Decimal = amount
        self._members: dict[str, Member] = {}  # normalised_id -> Member
        self._locked: bool = False              # True once week-1 contributions start
        self._completed: bool = False
        self.current_week: int = 1
        # payments[week][normalised_member_id] -> cumulative Decimal paid
        self._payments: dict[int, dict[str, Decimal]] = defaultdict(
            lambda: defaultdict(lambda: Decimal("0.00"))
        )
        self.payout_history: list[Payout] = []

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def weekly_contribution(self) -> Decimal:
        """The fixed weekly contribution amount."""
        return self._weekly_contribution

    @property
    def members(self) -> list[Member]:
        """All members ordered by join_order."""
        return sorted(self._members.values(), key=lambda m: m.join_order)

    # ------------------------------------------------------------------
    # Member management
    # ------------------------------------------------------------------

    def add_member(self, member_id: str, name: str = "") -> Member:
        """Add a new member to the group.

        Args:
            member_id: Unique identifier for the member (trimmed, case-insensitive).
            name: Optional display name (defaults to member_id).

        Returns:
            The newly created Member.

        Raises:
            GroupLockedError: If a contribution has already been recorded in week 1.
            ValueError: If member_id is blank.
            DuplicateMemberError: If the ID already exists.
        """
        if self._locked:
            raise GroupLockedError(
                "Cannot add members after contributions have started"
            )

        normalised = member_id.strip().lower()
        if not normalised:
            raise ValueError("member_id must not be blank")

        if normalised in self._members:
            raise DuplicateMemberError(
                f"A member with id {member_id!r} already exists"
            )

        join_order = len(self._members) + 1
        display_name = name.strip() or member_id.strip()
        member = Member(id=normalised, name=display_name, join_order=join_order)
        self._members[normalised] = member
        return member

    # ------------------------------------------------------------------
    # Internal helpers (used by later stages)
    # ------------------------------------------------------------------

    def _lock(self) -> None:
        """Lock the group so no more members can be added."""
        self._locked = True

    def _resolve_week(self, week: int | None) -> int:
        """Return current_week when week is None, else the given week."""
        return self.current_week if week is None else week

    def _check_member(self, normalised_id: str) -> None:
        """Raise UnknownMemberError if the ID is not in the group."""
        if normalised_id not in self._members:
            raise UnknownMemberError(f"No member with id {normalised_id!r}")

    # ------------------------------------------------------------------
    # Contribution recording
    # ------------------------------------------------------------------

    def record_contribution(
        self, member_id: str, amount: str | int | Decimal
    ) -> Decimal:
        """Record a (partial or full) contribution for the current week.

        Args:
            member_id: Member making the payment (trimmed, case-insensitive).
            amount: Amount being paid. Must be > 0 and not exceed what is still owed.

        Returns:
            The member's cumulative payment for this week after recording.

        Raises:
            GroupCompletedError: If the group has already finished.
            ValueError: If fewer than 2 members are in the group.
            UnknownMemberError: If member_id is not recognised.
            InvalidAmountError: If amount is zero, negative, or malformed.
            OverpaymentError: If amount exceeds the remaining balance owed.
        """
        if self._completed:
            raise GroupCompletedError("This group has already completed")

        if len(self._members) < 2:
            raise ValueError(
                "At least 2 members are required before recording contributions"
            )

        normalised = member_id.strip().lower()
        self._check_member(normalised)

        try:
            parsed = parse_amount(amount)
        except (TypeError, ValueError) as exc:
            raise InvalidAmountError(str(exc)) from exc

        if parsed <= Decimal("0.00"):
            raise InvalidAmountError("Contribution amount must be greater than zero")

        owed = self.amount_owed(normalised)
        if parsed > owed:
            raise OverpaymentError(
                f"Payment of {parsed} exceeds the remaining amount owed: {owed}"
            )

        # Lock member list on the very first successful contribution in week 1
        if not self._locked:
            self._lock()

        self._payments[self.current_week][normalised] += parsed
        return self._payments[self.current_week][normalised]

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def amount_paid(self, member_id: str, week: int | None = None) -> Decimal:
        """Return how much member_id has paid in the given week (default: current)."""
        normalised = member_id.strip().lower()
        self._check_member(normalised)
        w = self._resolve_week(week)
        return self._payments[w][normalised]

    def amount_owed(self, member_id: str, week: int | None = None) -> Decimal:
        """Return how much member_id still owes in the given week (default: current)."""
        paid = self.amount_paid(member_id, week)
        return self._weekly_contribution - paid

    def is_paid_in_full(self, member_id: str, week: int | None = None) -> bool:
        """Return True if member_id has paid the full contribution for the week."""
        return self.amount_owed(member_id, week) == Decimal("0.00")

    # ------------------------------------------------------------------
    # Week closing and payouts
    # ------------------------------------------------------------------

    def close_week(self) -> WeekCloseResult:
        """Attempt to close the current week and issue a payout.

        If every member has paid in full the pot is awarded to the member
        whose join_order equals current_week, payout_history is updated,
        and current_week advances.  If any member still owes money no state
        is changed and closed=False is returned.

        Returns:
            WeekCloseResult with the outcome.

        Raises:
            GroupCompletedError: If the group has already finished.
            ValueError: If fewer than 2 members are in the group.
        """
        if self._completed:
            raise GroupCompletedError("This group has already completed")

        if len(self._members) < 2:
            raise ValueError(
                "At least 2 members are required before closing a week"
            )

        # Collect outstanding balances
        outstanding: dict[str, Decimal] = {
            m.id: self.amount_owed(m.id)
            for m in self.members
            if not self.is_paid_in_full(m.id)
        }

        if outstanding:
            return WeekCloseResult(
                closed=False,
                week=self.current_week,
                payout=None,
                outstanding=outstanding,
            )

        # Everyone paid — find this week's recipient by join_order
        recipient = next(
            m for m in self.members if m.join_order == self.current_week
        )
        pot = self._weekly_contribution * len(self._members)
        payout = Payout(
            week=self.current_week,
            member_id=recipient.id,
            amount=pot,
        )
        self.payout_history.append(payout)

        closed_week = self.current_week
        self.current_week += 1

        # Mark complete when the last member has been paid
        if closed_week == len(self._members):
            self._completed = True

        return WeekCloseResult(closed=True, week=closed_week, payout=payout)

    # ------------------------------------------------------------------
    # Recipient query
    # ------------------------------------------------------------------

    def next_recipient(self) -> Member | None:
        """Return the member due the pot this week, or None if completed."""
        if self._completed:
            return None
        return next(
            (m for m in self.members if m.join_order == self.current_week), None
        )

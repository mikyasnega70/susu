"""SusuGroup: manages members and state for one rotating savings group."""

from decimal import Decimal

from .errors import (
    DuplicateMemberError,
    GroupLockedError,
    InvalidAmountError,
)
from .models import Member
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
        self.current_week: int = 1

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

"""Dataclasses representing core domain objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class Member:
    """A participant in the susu group.

    Attributes:
        id: Unique, case-normalised member identifier.
        name: Human-readable display name.
        join_order: 1-based position in which the member joined.
    """

    id: str
    name: str
    join_order: int


@dataclass
class Payout:
    """A record of a payout made in a given week.

    Attributes:
        week: The week number in which the payout occurred.
        member_id: ID of the member who received the payout.
        amount: Total amount paid out.
    """

    week: int
    member_id: str
    amount: Decimal


@dataclass
class WeekCloseResult:
    """Result returned by SusuGroup.close_week().

    Attributes:
        closed: True if the week was successfully closed and a payout made.
        week: The week number that was attempted.
        payout: The Payout issued, or None if the week did not close.
        outstanding: Mapping of member_id -> amount still owed (empty when closed=True).
    """

    closed: bool
    week: int
    payout: Payout | None
    outstanding: dict[str, Decimal] = field(default_factory=dict)

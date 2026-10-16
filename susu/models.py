"""Dataclasses representing core domain objects."""

from dataclasses import dataclass
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

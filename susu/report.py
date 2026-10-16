"""Reporting: build a structured report from a SusuGroup and render it as text."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING

from .money import format_ghs

if TYPE_CHECKING:
    from .group import SusuGroup


@dataclass
class PayoutRecord:
    """A single entry in the payout history summary."""

    week: int
    member_name: str
    amount: Decimal


@dataclass
class SusuReport:
    """Structured snapshot of a SusuGroup's current state.

    Attributes:
        week_label:          "completed" or the current week number as a string.
        weekly_contribution: Fixed contribution amount.
        next_recipient_name: Display name of this week's pot recipient, or None.
        paid_in_full:        Names of members who have paid this week in full.
        owing:               Mapping of member display name -> amount still owed.
        payout_history:      Ordered list of PayoutRecord for all closed weeks.
        total_pot_paid_out:  Sum of all payout amounts so far.
    """

    week_label: str
    weekly_contribution: Decimal
    next_recipient_name: str | None
    paid_in_full: list[str] = field(default_factory=list)
    owing: dict[str, Decimal] = field(default_factory=dict)
    payout_history: list[PayoutRecord] = field(default_factory=list)
    total_pot_paid_out: Decimal = field(default=Decimal("0.00"))


def build_report(group: "SusuGroup") -> SusuReport:
    """Build a SusuReport from the current state of a SusuGroup.

    This function is pure: it reads group state and returns a dataclass.
    It does not print or mutate anything.
    """
    # Resolve member name lookup (id -> display name)
    id_to_name: dict[str, str] = {m.id: m.name for m in group.members}

    week_label = "completed" if group._completed else str(group.current_week)

    recipient = group.next_recipient()
    next_recipient_name = id_to_name.get(recipient.id) if recipient else None

    paid_in_full: list[str] = []
    owing: dict[str, Decimal] = {}

    if not group._completed:
        for member in group.members:
            if group.is_paid_in_full(member.id):
                paid_in_full.append(member.name)
            else:
                owing[member.name] = group.amount_owed(member.id)

    history: list[PayoutRecord] = [
        PayoutRecord(
            week=p.week,
            member_name=id_to_name.get(p.member_id, p.member_id),
            amount=p.amount,
        )
        for p in group.payout_history
    ]

    total = sum((p.amount for p in group.payout_history), Decimal("0.00"))

    return SusuReport(
        week_label=week_label,
        weekly_contribution=group.weekly_contribution,
        next_recipient_name=next_recipient_name,
        paid_in_full=paid_in_full,
        owing=owing,
        payout_history=history,
        total_pot_paid_out=total,
    )


def render_report(report: SusuReport) -> str:
    """Render a SusuReport as an aligned plain-text string."""
    lines: list[str] = []

    lines.append("===== SUSU REPORT =====")
    lines.append(f"Week                 : {report.week_label}")
    lines.append(f"Weekly contribution  : {format_ghs(report.weekly_contribution)}")

    if report.next_recipient_name:
        lines.append(f"Next recipient       : {report.next_recipient_name}")
    else:
        lines.append("Next recipient       : —")

    # Paid in full
    if report.paid_in_full:
        lines.append(f"Paid in full         : {', '.join(report.paid_in_full)}")
    else:
        lines.append("Paid in full         : —")

    # Owing
    if report.owing:
        for i, (name, owed) in enumerate(report.owing.items()):
            label = "Owes                 :" if i == 0 else "                      "
            lines.append(f"{label} {name} - {format_ghs(owed)}")
    else:
        lines.append("Owes                 : —")

    # Payout history
    lines.append("Payout history")
    if report.payout_history:
        for rec in report.payout_history:
            lines.append(f"  Week {rec.week} -> {rec.member_name:<12} {format_ghs(rec.amount)}")
    else:
        lines.append("  (none yet)")

    lines.append(f"Total paid out       : {format_ghs(report.total_pot_paid_out)}")

    return "\n".join(lines)

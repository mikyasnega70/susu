"""Interactive CLI and --demo mode for the susu program."""

from __future__ import annotations

from decimal import Decimal

from .errors import SusuError
from .group import SusuGroup
from .money import format_ghs
from .report import build_report, render_report


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def run_demo() -> None:
    """Run the spec example end-to-end, printing each step."""
    _print_banner("SUSU DEMO")
    print("Creating group with weekly contribution GHS 50.00")
    group = SusuGroup("50")

    for member_id, name in [("ama", "Ama"), ("kofi", "Kofi"), ("esi", "Esi")]:
        group.add_member(member_id, name)
        print(f"  Added member: {name}")

    print("\n--- Week 1 ---")
    print("Ama pays GHS 50.00")
    group.record_contribution("ama", "50")
    print("Kofi pays GHS 50.00")
    group.record_contribution("kofi", "50")
    print("Esi pays GHS 30.00 (partial)")
    group.record_contribution("esi", "30")

    print("\nAttempting to close week 1 before Esi finishes...")
    result = group.close_week()
    if not result.closed:
        for mid, owed in result.outstanding.items():
            display = next(m.name for m in group.members if m.id == mid)
            print(f"  Cannot close — {display} still owes {format_ghs(owed)}")

    print("\nEsi pays remaining GHS 20.00")
    group.record_contribution("esi", "20")

    print("\nClosing week 1...")
    result = group.close_week()
    p = result.payout
    recipient_name = next(m.name for m in group.members if m.id == p.member_id)
    print(f"  Week {p.week} closed — {recipient_name} receives {format_ghs(p.amount)}")

    print()
    print(render_report(build_report(group)))


# ---------------------------------------------------------------------------
# Interactive menu
# ---------------------------------------------------------------------------

def run_interactive() -> None:
    """Run the interactive menu loop."""
    _print_banner("SUSU")
    print("Welcome. Type a menu number and press Enter.\n")

    group: SusuGroup | None = None

    menu = (
        "1) Create group        2) Add member        3) Record contribution\n"
        "4) Close week          5) Show report       6) Exit"
    )

    while True:
        print(f"\n{menu}")
        choice = input("Choice: ").strip()

        if choice == "1":
            new_group = _cmd_create_group()
            if new_group is not None:
                group = new_group

        elif choice == "2":
            if _require_group(group):
                _cmd_add_member(group)  # type: ignore[arg-type]

        elif choice == "3":
            if _require_group(group):
                _cmd_record_contribution(group)  # type: ignore[arg-type]

        elif choice == "4":
            if _require_group(group):
                _cmd_close_week(group)  # type: ignore[arg-type]

        elif choice == "5":
            if _require_group(group):
                print()
                print(render_report(build_report(group)))  # type: ignore[arg-type]

        elif choice == "6":
            print("Goodbye.")
            break

        else:
            print(f"  '{choice}' is not a valid option. Please enter 1–6.")


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def _cmd_create_group() -> SusuGroup | None:
    raw = input("  Weekly contribution (e.g. 50.00): ").strip()
    try:
        group = SusuGroup(raw)
        print(f"  Group created. Contribution: {format_ghs(group.weekly_contribution)}")
        return group
    except SusuError as exc:
        print(f"  Error: {exc}")
    except Exception:
        print("  Error: invalid amount.")
    return None


def _cmd_add_member(group: SusuGroup) -> None:
    member_id = input("  Member ID            : ").strip()
    name = input("  Display name (blank to use ID): ").strip()
    try:
        m = group.add_member(member_id, name)
        print(f"  Added '{m.name}' (join order {m.join_order}).")
    except (SusuError, ValueError) as exc:
        print(f"  Error: {exc}")


def _cmd_record_contribution(group: SusuGroup) -> None:
    member_id = input("  Member ID: ").strip()
    raw = input("  Amount   : ").strip()
    try:
        total = group.record_contribution(member_id, raw)
        owed = group.amount_owed(member_id)
        print(
            f"  Recorded. Total paid this week: {format_ghs(total)}  |  "
            f"Still owed: {format_ghs(owed)}."
        )
    except (SusuError, ValueError) as exc:
        print(f"  Error: {exc}")


def _cmd_close_week(group: SusuGroup) -> None:
    try:
        result = group.close_week()
    except (SusuError, ValueError) as exc:
        print(f"  Error: {exc}")
        return

    if result.closed:
        p = result.payout
        recipient_name = next(
            m.name for m in group.members if m.id == p.member_id
        )
        print(f"  Week {p.week} closed. {recipient_name} receives {format_ghs(p.amount)}.")
        if group._completed:
            print("  The group has completed. All members have received the pot.")
    else:
        print("  Cannot close — the following members still owe:")
        for mid, owed in result.outstanding.items():
            display = next(m.name for m in group.members if m.id == mid)
            print(f"    {display}: {format_ghs(owed)}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _print_banner(title: str) -> None:
    bar = "=" * (len(title) + 12)
    print(f"\n{bar}")
    print(f"      {title}")
    print(f"{bar}\n")


def _require_group(group: SusuGroup | None) -> bool:
    if group is None:
        print("  No group yet. Choose option 1 first.")
        return False
    return True

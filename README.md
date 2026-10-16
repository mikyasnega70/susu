# Susu — Rotating Savings Group Manager

A small Python 3.11+ command-line program for managing one rotating savings group (susu / tontine).

---

## How to run

```bash
# Interactive menu
python -m susu

# Scripted demo (spec example: Ama, Kofi, Esi at GHS 50)
python -m susu --demo
```

No installation required beyond Python 3.11+. No third-party dependencies.

---

## How to test

```bash
pip install pytest          # one-time
python -m pytest tests/ -v
```

All 5 test files, 108 tests, zero dependencies beyond pytest.

---

## Project structure

```
susu/
  __init__.py       package marker
  __main__.py       entry point (python -m susu)
  cli.py            interactive menu + --demo runner
  errors.py         custom exception hierarchy
  models.py         Member, Payout, WeekCloseResult, dataclasses
  money.py          parse_amount(), format_ghs(), Decimal only
  group.py          SusuGroup — all business logic
  report.py         build_report(), render_report(), pure presentation
tests/
  test_money.py
  test_group_members.py
  test_contributions.py
  test_close_week.py
  test_report.py
  test_end_to_end.py
```

---

## Assumptions

Every design decision made during development is listed here.

### Money

- All monetary values use `decimal.Decimal` throughout. `float` is rejected at the
  boundary (`parse_amount`) and never used internally.
- Amounts are quantized to exactly 2 decimal places (`0.01`).
- Values with more than 2 decimal places are **rejected**, not silently rounded.
  `"10.999"` raises `InvalidAmountError`; `"10.99"` is accepted.
- `Infinity` and `NaN` are rejected by `parse_amount`.
- The pot is computed as `weekly_contribution * member_count` using Decimal
  multiplication — no intermediate float conversion, no rounding.

### Members

- Member IDs are trimmed of whitespace and lowercased before storage.
  `"Alice"`, `"  alice  "`, and `"ALICE"` all resolve to the same member.
- Display names are stored as entered (after trimming); they default to the
  original (un-lowercased) member ID string if left blank.
- **Members can only be added before the first contribution is recorded in week 1.**
  The member list is locked on the first successful `record_contribution` call.
  Attempting to add a member after that raises `GroupLockedError`.
- **At least 2 members are required** before contributions can be recorded or a
  week can be closed.

### Contributions

- Contributions apply only to the **current week**. There is no back-dating or
  advance payment.
- **Partial payments are allowed** and accumulate. Multiple calls to
  `record_contribution` for the same member in the same week sum together.
- A contribution cannot exceed what the member still owes that week
  (`OverpaymentError`).
- Zero and negative amounts are rejected (`InvalidAmountError`).

### Week closing and payouts

- `close_week()` succeeds only when **every member** has paid the full weekly
  contribution. If anyone owes, it returns `closed=False` and changes **no state**
  — no week advances, no payout is issued, no partial state is written.
- The recipient of the pot each week is determined solely by **join order**:
  the member who joined first receives the pot in week 1, second in week 2, etc.
- Payout amount = `weekly_contribution × number of members` (exact Decimal).

### Group completion

- The group is marked **completed** once the last member has received the pot
  (i.e. after the close of week N where N = total member count).
- A completed group is **read-only for operations**: further contributions or
  close attempts raise `GroupCompletedError`. Reports can still be generated.

### Persistence

- State is **in-memory only**. Nothing is written to disk. Restarting the program
  starts a fresh group.

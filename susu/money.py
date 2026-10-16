"""Money utilities for the susu app. All amounts use Decimal, never float."""

from decimal import Decimal, ROUND_DOWN, InvalidOperation


def parse_amount(value: str | int | Decimal) -> Decimal:
    """Parse a money value into a Decimal quantized to 0.01.

    Accepts str, int, or Decimal. Rejects float, negative values,
    and values with more than 2 decimal places.
    """
    if isinstance(value, float):
        raise TypeError("float is not allowed for money; use str or Decimal instead")

    try:
        d = Decimal(str(value)) if isinstance(value, int) else Decimal(value)
    except InvalidOperation:
        raise ValueError(f"Cannot parse {value!r} as a monetary amount")

    if d < 0:
        raise ValueError(f"Amount cannot be negative: {value!r}")

    # Reject more than 2 decimal places — do NOT silently round
    quantized = d.quantize(Decimal("0.01"))
    if quantized != d:
        raise ValueError(
            f"Amount {value!r} has more than 2 decimal places; will not round"
        )

    return quantized


def format_ghs(amount: Decimal) -> str:
    """Format a Decimal amount as a GHS currency string, e.g. 'GHS 50.00'."""
    return f"GHS {amount:.2f}"

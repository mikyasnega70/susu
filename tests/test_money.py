"""Tests for susu.money: parse_amount and format_ghs."""

import pytest
from decimal import Decimal

from susu.money import parse_amount, format_ghs


class TestParseAmount:
    def test_string_integer(self):
        assert parse_amount("50") == Decimal("50.00")

    def test_string_with_decimals(self):
        assert parse_amount("50.00") == Decimal("50.00")

    def test_int_input(self):
        assert parse_amount(10) == Decimal("10.00")

    def test_decimal_input(self):
        assert parse_amount(Decimal("9.99")) == Decimal("9.99")

    def test_zero(self):
        assert parse_amount("0") == Decimal("0.00")

    def test_addition_precision(self):
        """0.1 + 0.2 must equal exactly 0.30 with Decimal."""
        result = parse_amount("0.1") + parse_amount("0.2")
        assert result == Decimal("0.30")

    def test_rejects_float(self):
        with pytest.raises(TypeError, match="float is not allowed"):
            parse_amount(10.5)

    def test_rejects_float_zero(self):
        with pytest.raises(TypeError):
            parse_amount(0.0)

    def test_rejects_too_many_decimal_places(self):
        with pytest.raises(ValueError, match="more than 2 decimal places"):
            parse_amount("10.999")

    def test_rejects_three_decimal_places_boundary(self):
        with pytest.raises(ValueError):
            parse_amount("1.001")

    def test_rejects_negative(self):
        with pytest.raises(ValueError, match="negative"):
            parse_amount("-1.00")

    def test_rejects_invalid_string(self):
        with pytest.raises(ValueError):
            parse_amount("abc")

    def test_returns_quantized_decimal(self):
        result = parse_amount("5")
        assert result == Decimal("5.00")
        # Ensure the exponent is exactly -2
        assert result.as_tuple().exponent == -2


class TestFormatGhs:
    def test_basic(self):
        assert format_ghs(Decimal("50.00")) == "GHS 50.00"

    def test_zero(self):
        assert format_ghs(Decimal("0.00")) == "GHS 0.00"

    def test_large_amount(self):
        assert format_ghs(Decimal("1000.50")) == "GHS 1000.50"

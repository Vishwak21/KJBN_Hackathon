from datetime import date
from decimal import Decimal
import pytest
from backend.rules import (
    DomainError,
    breakdown,
    business_date,
    decimal_value,
    payout_totals,
    week_start,
)


@pytest.mark.parametrize(
    "moisture,deduction", [("14", "0"), ("14.99", "0"), ("17.6", "3"), ("28", "10")]
)
def test_moisture_boundaries(moisture, deduction):
    result = breakdown("100.125", moisture, "14", "28", "25.55", 1)
    assert result["deduction_pct"] == deduction
    assert Decimal(result["gross_kg"]) == Decimal(result["deduction_kg"]) + Decimal(
        result["net_kg"]
    )


def test_half_up():
    assert breakdown("0.5", "14", "14", "28", "2.01", 1)["amount"] == "1.01"


@pytest.mark.parametrize("value", ["0", "-1", "NaN", "Infinity", "1.001", True, "1000000001", "x"])
def test_invalid_numbers(value):
    with pytest.raises(DomainError):
        decimal_value(value, "test")


def test_max_rejection():
    with pytest.raises(DomainError, match="maximum"):
        breakdown("10", "28.01", "14", "28", "1", 1)


def test_recovery_and_rounding():
    assert payout_totals(["0.05"], "1") == {"gross": "0.05", "deduction": "0.01", "net": "0.04"}
    assert payout_totals(["10.01", "20.02"], "5") == {
        "gross": "30.03",
        "deduction": "5.00",
        "net": "25.03",
    }
    assert payout_totals(["-10"], "50")["deduction"] == "0.00"


def test_dates():
    assert week_start(date(2026, 10, 18)) == date(2026, 10, 12)
    assert week_start(date(2026, 10, 19)) == date(2026, 10, 19)
    assert business_date("2026-10-19", date(2026, 10, 19)) == date(2026, 10, 19)
    for value in ("wrong", "2026-10-20"):
        with pytest.raises(DomainError):
            business_date(value, date(2026, 10, 19))

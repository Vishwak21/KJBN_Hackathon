"""Pure pricing and payout arithmetic. No HTTP or database dependencies."""

from datetime import date, timedelta
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

CENT = Decimal("0.01")


class DomainError(Exception):
    def __init__(self, code, message, status=422):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def decimal_value(value, label, places=2, positive=True):
    try:
        if isinstance(value, bool):
            raise ValueError()
        number = Decimal(str(value))
        if not number.is_finite() or abs(number) > Decimal("1000000000"):
            raise ValueError()
        if number != number.quantize(Decimal(1).scaleb(-places)):
            raise ValueError()
        if positive and number <= 0:
            raise ValueError()
        return number
    except (ValueError, ArithmeticError):
        raise DomainError(
            "invalid_number",
            f"{label} must be finite, positive and have at most {places} decimal places.",
        ) from None


def money(value):
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def week_start(day):
    return day - timedelta(days=day.weekday())


def breakdown(weight, moisture, threshold, maximum, price, price_id):
    weight = decimal_value(weight, "Weight", 3)
    moisture = decimal_value(moisture, "Moisture")
    threshold, maximum = Decimal(threshold), Decimal(maximum)
    if moisture > maximum:
        raise DomainError("moisture_rejected", f"Moisture exceeds maximum accepted ({maximum}%).")
    deduction_pct = min(
        Decimal(10), max(Decimal(0), (moisture - threshold).to_integral_value(rounding=ROUND_DOWN))
    )
    # Keep exact kg through multiplication; only payable money is rounded.
    deduction_kg = weight * deduction_pct / 100
    net_kg = weight - deduction_kg
    return {
        "gross_kg": str(weight),
        "moisture": str(moisture),
        "deduction_pct": str(deduction_pct),
        "deduction_kg": str(deduction_kg),
        "net_kg": str(net_kg),
        "applied_price": str(price),
        "price_id": price_id,
        "amount": str(money(net_kg * Decimal(price))),
    }


def payout_totals(amounts, outstanding):
    gross = sum((Decimal(a) for a in amounts), Decimal(0))
    cap = max(Decimal(0), gross * Decimal("0.30")).quantize(CENT, rounding=ROUND_DOWN)
    deduction = min(Decimal(outstanding), cap)
    return {
        "gross": str(money(gross)),
        "deduction": str(money(deduction)),
        "net": str(money(gross - deduction)),
    }


def business_date(value, today):
    try:
        parsed = date.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise DomainError("invalid_date", "Use a calendar date in YYYY-MM-DD format.") from None
    if parsed > today:
        raise DomainError("future_date", "Date cannot be in the future.")
    return parsed

"""Use cases. Call with a transaction held for every read-modify-write."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from .rules import DomainError, breakdown, business_date, decimal_value, payout_totals, week_start


def now():
    return datetime.now(timezone.utc).isoformat()


def row(c, table, identifier):
    # Table names are internal constants, never request input.
    result = c.execute(f"SELECT * FROM {table} WHERE id=?", (identifier,)).fetchone()
    if result is None:
        raise DomainError("not_found", f"{table.rstrip('s').capitalize()} {identifier} not found.", 404)
    return dict(result)


def insert(c, table, data):
    columns = ",".join(data)
    placeholders = ",".join("?" for _ in data)
    identifier = c.execute(
        f"INSERT INTO {table}({columns}) VALUES({placeholders})", tuple(data.values())
    ).lastrowid
    return row(c, table, identifier)


def outstanding(c, farmer_id):
    row(c, "farmers", farmer_id)
    advances = sum((Decimal(r[0]) for r in c.execute(
        "SELECT amount FROM advances WHERE farmer_id=?", (farmer_id,))), Decimal(0))
    recovered = sum((Decimal(r[0]) for r in c.execute(
        "SELECT deduction FROM payouts WHERE farmer_id=? AND status!='Draft'", (farmer_id,))), Decimal(0))
    return str((advances - recovered).quantize(Decimal("0.01")))


def create_farmer(c, data):
    return insert(c, "farmers", data)


def create_crop(c, data):
    threshold = decimal_value(data["threshold"], "Threshold", positive=False)
    maximum = decimal_value(data["max_moisture"], "Maximum moisture")
    if not 0 <= threshold < maximum <= 100:
        raise DomainError("invalid_crop", "Require 0 <= threshold < maximum <= 100.")
    grades = data["grades"]
    if not grades or len(set(grades)) != len(grades) or any("," in g or not g.strip() for g in grades):
        raise DomainError("invalid_grades", "Specify distinct nonempty grades without commas.")
    return insert(c, "crops", {**data, "grades": ",".join(grades),
                              "threshold": str(threshold), "max_moisture": str(maximum)})


def create_price(c, data):
    crop = row(c, "crops", data["crop_id"])
    if data["grade"] not in crop["grades"].split(","):
        raise DomainError("invalid_grade", "Grade is not allowed for this crop.")
    price = decimal_value(data["price"], "Price")
    # Future effective prices are allowed; delivery dates still cannot be future.
    try:
        effective = date.fromisoformat(data["effective_from"]).isoformat()
    except ValueError:
        raise DomainError("invalid_date", "Use YYYY-MM-DD for effective_from.") from None
    return insert(c, "prices", {**data, "price": str(price), "effective_from": effective})


def create_advance(c, data, today):
    row(c, "farmers", data["farmer_id"])
    amount = decimal_value(data["amount"], "Amount")
    given_on = business_date(data["given_on"], today)
    result = insert(c, "advances", {**data, "amount": str(amount),
                                   "given_on": given_on.isoformat(), "created_at": now()})
    return {**result, "outstanding": outstanding(c, data["farmer_id"])}


def preview_delivery(c, data, today):
    row(c, "farmers", data["farmer_id"])
    crop = row(c, "crops", data["crop_id"])
    if data["grade"] not in crop["grades"].split(","):
        raise DomainError("invalid_grade", f"Allowed grades: {crop['grades']}.")
    delivered = business_date(data["delivered_on"], today).isoformat()
    price = c.execute(
        "SELECT * FROM prices WHERE crop_id=? AND grade=? AND effective_from<=? "
        "ORDER BY effective_from DESC LIMIT 1", (data["crop_id"], data["grade"], delivered)
    ).fetchone()
    if price is None:
        raise DomainError("missing_price",
                          f"No price for {crop['name']} / {data['grade']} on or before {delivered}.")
    values = breakdown(data["gross_kg"], data["moisture"], crop["threshold"],
                       crop["max_moisture"], price["price"], price["id"])
    return {**data, **values, "delivered_on": delivered}


def create_delivery(c, data, today):
    return insert(c, "deliveries", {**preview_delivery(c, data, today), "created_at": now()})


def edit_delivery(c, identifier, data, today):
    old = row(c, "deliveries", identifier)
    if old["payout_id"] is not None or old["original_id"] is not None:
        raise DomainError("immutable_delivery", "Assigned deliveries and correction notes cannot be edited; use a correction note.", 409)
    values = preview_delivery(c, data, today)
    assignments = ",".join(f"{key}=?" for key in values)
    c.execute(f"UPDATE deliveries SET {assignments} WHERE id=?", (*values.values(), identifier))
    return row(c, "deliveries", identifier)


def create_correction(c, original_id, data, today):
    original = row(c, "deliveries", original_id)
    if original["original_id"] or original["payout_id"] is None:
        raise DomainError("invalid_correction", "Reference a regular delivery in a finalised payout.", 409)
    payout = row(c, "payouts", original["payout_id"])
    if payout["status"] == "Draft":
        raise DomainError("invalid_correction", "Original payout must be finalised first.", 409)
    correction_date = business_date(data["delivered_on"], today)
    if correction_date <= date.fromisoformat(payout["week"]) + timedelta(days=6):
        raise DomainError("invalid_correction_date", "Correction must land after the original payout week.")
    amount = decimal_value(data["amount"], "Adjustment amount", positive=False)
    if amount == 0:
        raise DomainError("invalid_correction", "Correction amount cannot be zero.")
    return insert(c, "deliveries", {
        "farmer_id": original["farmer_id"], "crop_id": original["crop_id"],
        "grade": original["grade"], "delivered_on": correction_date.isoformat(),
        "amount": str(amount), "original_id": original_id, "reason": data["reason"],
        "created_at": now(),
    })


def payout_detail(c, identifier):
    payout = row(c, "payouts", identifier)
    payout["deliveries"] = [dict(r) for r in c.execute(
        "SELECT * FROM deliveries WHERE payout_id=? ORDER BY delivered_on,id", (identifier,))]
    if payout["status"] == "Draft":
        payout.update(payout_totals([r["amount"] for r in payout["deliveries"]],
                                    outstanding(c, payout["farmer_id"])))
    return payout


def generate_payout(c, farmer_id, requested_week):
    row(c, "farmers", farmer_id)
    try:
        start = week_start(date.fromisoformat(requested_week))
    except ValueError:
        raise DomainError("invalid_date", "Use YYYY-MM-DD for week.") from None
    end = start + timedelta(days=6)
    existing = c.execute("SELECT id FROM payouts WHERE farmer_id=? AND week=? AND status='Draft'",
                         (farmer_id, start.isoformat())).fetchone()
    identifier = existing["id"] if existing else None
    deliveries = [dict(r) for r in c.execute(
        "SELECT * FROM deliveries WHERE farmer_id=? AND delivered_on BETWEEN ? AND ? "
        "AND (payout_id IS NULL OR payout_id=?) ORDER BY id",
        (farmer_id, start.isoformat(), end.isoformat(), identifier))]
    if not deliveries:
        raise DomainError("empty_week", "No unassigned deliveries in this farmer's week.", 409)
    totals = payout_totals([r["amount"] for r in deliveries], outstanding(c, farmer_id))
    if identifier is None:
        payout = insert(c, "payouts", {"farmer_id": farmer_id, "week": start.isoformat(),
                                      "status": "Draft", **totals, "created_at": now()})
        identifier = payout["id"]
    else:
        c.execute("UPDATE payouts SET gross=?,deduction=?,net=? WHERE id=?",
                  (*totals.values(), identifier))
    c.executemany("UPDATE deliveries SET payout_id=? WHERE id=?",
                  [(identifier, d["id"]) for d in deliveries])
    return payout_detail(c, identifier)


def finalise_payout(c, identifier):
    payout = payout_detail(c, identifier)
    if payout["status"] != "Draft":
        raise DomainError("invalid_transition", "Only a draft payout can be finalised.", 409)
    c.execute(
        "UPDATE payouts SET status='Finalised',gross=?,deduction=?,net=?,finalised_at=? WHERE id=?",
        (payout["gross"], payout["deduction"], payout["net"], now(), identifier))
    return payout_detail(c, identifier)


def pay_payout(c, identifier):
    payout = row(c, "payouts", identifier)
    if payout["status"] != "Finalised":
        raise DomainError("invalid_transition", "Only a finalised payout can be marked paid.", 409)
    c.execute("UPDATE payouts SET status='Paid',paid_at=? WHERE id=?", (now(), identifier))
    return payout_detail(c, identifier)


def ledger(c, farmer_id, limit=100, offset=0):
    farmer = row(c, "farmers", farmer_id)
    result = {"farmer": farmer, "outstanding": outstanding(c, farmer_id),
              "limit": limit, "offset": offset}
    for table in ("deliveries", "advances", "payouts"):
        result[table] = [dict(r) for r in c.execute(
            f"SELECT * FROM {table} WHERE farmer_id=? ORDER BY id DESC LIMIT ? OFFSET ?",
            (farmer_id, limit, offset))]
        result[f"{table}_total"] = c.execute(
            f"SELECT count(*) FROM {table} WHERE farmer_id=?", (farmer_id,)).fetchone()[0]
    return result

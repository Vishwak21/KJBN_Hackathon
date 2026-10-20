"""Idempotent invented demo data; never erase existing work."""

from datetime import datetime, timedelta, timezone
from . import services
from .db import migrate, transaction


def seed(path=None, sample_deliveries=False):
    migrate(path)
    with transaction(path) as c:
        if c.execute("SELECT count(*) FROM farmers").fetchone()[0]:
            return
        c.executemany(
            "INSERT INTO farmers(name,phone,village,bank_reference) VALUES(?,?,?,?)",
            [
                ("Demo Farmer A", "0000000001", "Sample Village East", "DEMO-BANK-A"),
                ("Demo Farmer B", "0000000002", "Sample Village West", "DEMO-BANK-B"),
            ],
        )
        c.executemany(
            "INSERT INTO crops(name,grades,threshold,max_moisture) VALUES(?,?,?,?)",
            [
                ("Maize", "A,B,C", "14", "28"),
                ("Turmeric", "A,B", "10", "22"),
                ("Groundnut", "A,B,C", "8", "20"),
            ],
        )
        for crop_id, base in [(1, 25), (2, 120), (3, 65)]:
            grades = ("A", "B") if crop_id == 2 else ("A", "B", "C")
            for offset, grade in enumerate(grades):
                c.execute(
                    "INSERT INTO prices(crop_id,grade,price,effective_from) VALUES(?,?,?,?)",
                    (crop_id, grade, str(base - offset * 2), "2020-01-01"),
                )
        c.execute(
            "INSERT INTO advances(farmer_id,amount,given_on,created_at) VALUES(1,?,?,?)",
            (
                "5000.00",
                (
                    datetime.now(timezone(timedelta(hours=5, minutes=30))).date()
                    - timedelta(days=30)
                ).isoformat(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        if sample_deliveries:
            day = datetime.now(timezone(timedelta(hours=5, minutes=30))).date()
            last_week = day - timedelta(days=day.weekday() + 7)
            original = services.create_delivery(
                c,
                {
                    "farmer_id": 1,
                    "crop_id": 1,
                    "grade": "A",
                    "gross_kg": "100",
                    "moisture": "14",
                    "delivered_on": last_week.isoformat(),
                },
                day,
            )
            payout = services.generate_payout(c, 1, last_week.isoformat())
            services.finalise_payout(c, payout["id"])
            services.pay_payout(c, payout["id"])
            for farmer, crop, weight, moisture in [
                (1, 1, "250.125", "17.6"),
                (2, 2, "60", "11.5"),
                (2, 3, "130", "10"),
            ]:
                services.create_delivery(
                    c,
                    {
                        "farmer_id": farmer,
                        "crop_id": crop,
                        "grade": "A",
                        "gross_kg": weight,
                        "moisture": moisture,
                        "delivered_on": day.isoformat(),
                    },
                    day,
                )
            services.create_correction(
                c,
                original["id"],
                {
                    "amount": "-25.00",
                    "reason": "Demo scale adjustment",
                    "delivered_on": day.isoformat(),
                },
                day,
            )


if __name__ == "__main__":
    seed(sample_deliveries=True)
    print("Schema migrated; demo seed loaded (existing data retained).")

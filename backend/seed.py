"""Idempotent invented demo data; never erase existing work."""
from datetime import date, datetime, timezone
from .db import migrate, transaction


def seed(path=None):
    migrate(path)
    with transaction(path) as c:
        if c.execute("SELECT count(*) FROM farmers").fetchone()[0]:
            return
        c.executemany(
            "INSERT INTO farmers(name,phone,village,bank_reference) VALUES(?,?,?,?)",
            [("Demo Farmer A", "0000000001", "Sample Village East", "DEMO-BANK-A"),
             ("Demo Farmer B", "0000000002", "Sample Village West", "DEMO-BANK-B")],
        )
        c.executemany(
            "INSERT INTO crops(name,grades,threshold,max_moisture) VALUES(?,?,?,?)",
            [("Maize", "A,B,C", "14", "28"), ("Turmeric", "A,B", "10", "22"),
             ("Groundnut", "A,B,C", "8", "20")],
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
            ("5000.00", date.today().isoformat(), datetime.now(timezone.utc).isoformat()),
        )


if __name__ == "__main__":
    seed()
    print("Schema migrated; demo seed loaded (existing data retained).")

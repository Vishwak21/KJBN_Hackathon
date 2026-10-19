from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
import pytest
from backend.db import transaction
from backend.seed import seed
from backend import services as s
from backend.rules import DomainError

TODAY = date(2026, 10, 19)


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "test.db")
    seed(path)
    return path


def delivery(day="2026-10-12", **kw):
    return dict(farmer_id=1, crop_id=1, grade="A", gross_kg="100", moisture="17.6",
                delivered_on=day, **kw)


def test_freeze_price_and_exact_effective_date(db):
    with transaction(db) as c:
        p = s.create_price(c, dict(crop_id=1, grade="A", price="30", effective_from="2026-10-12"))
        d = s.create_delivery(c, delivery(), TODAY)
        assert d["price_id"] == p["id"] and d["amount"] == "2910.00"
        s.create_price(c, dict(crop_id=1, grade="A", price="100", effective_from="2026-10-11"))
        assert s.row(c, "deliveries", d["id"])["amount"] == "2910.00"


def test_missing_price_names_combination(db):
    with transaction(db) as c, pytest.raises(DomainError, match="Maize / A"):
        s.preview_delivery(c, delivery("2019-01-01"), TODAY)


@pytest.mark.parametrize("patch", [{"grade": "Z"}, {"gross_kg": "0"}, {"moisture": "-1"},
                                   {"delivered_on": "2026-10-20"}, {"farmer_id": 999}])
def test_bad_delivery(db, patch):
    with transaction(db) as c, pytest.raises(DomainError):
        s.create_delivery(c, {**delivery(), **patch}, TODAY)


def test_repeated_recovery_and_status_transitions(db):
    with transaction(db) as c:
        for day in ["2026-09-28", "2026-10-05", "2026-10-12"]:
            s.create_delivery(c, {**delivery(day), "gross_kg": "100", "moisture": "14"}, TODAY)
            p = s.generate_payout(c, 1, day)
            before = s.outstanding(c, 1)
            assert s.generate_payout(c, 1, day)["id"] == p["id"]
            assert s.outstanding(c, 1) == before
            final = s.finalise_payout(c, p["id"])
            assert final["deduction"] == "750.00"
            assert Decimal(final["gross"]) == Decimal(final["net"]) + Decimal(final["deduction"])
            paid = s.pay_payout(c, p["id"])
            assert paid["gross"] == final["gross"]
            with pytest.raises(DomainError):
                s.finalise_payout(c, p["id"])
            with pytest.raises(DomainError):
                s.pay_payout(c, p["id"])
        assert s.outstanding(c, 1) == "2750.00"


def test_empty_week_and_edit_lock(db):
    with transaction(db) as c:
        with pytest.raises(DomainError, match="No unassigned"):
            s.generate_payout(c, 1, "2026-10-12")
        d = s.create_delivery(c, delivery(), TODAY)
        updated = s.edit_delivery(c, d["id"], {**delivery(), "gross_kg": "20"}, TODAY)
        assert updated["gross_kg"] == "20"
        p = s.generate_payout(c, 1, "2026-10-18")
        with pytest.raises(DomainError):
            s.edit_delivery(c, d["id"], delivery(), TODAY)
        with pytest.raises(DomainError):
            s.create_correction(c, d["id"], dict(amount="-5", reason="Test", delivered_on="2026-10-19"), TODAY)
        s.finalise_payout(c, p["id"])
        note = s.create_correction(c, d["id"], dict(amount="-5", reason="Test", delivered_on="2026-10-19"), TODAY)
        assert note["original_id"] == d["id"]
        correction_payout = s.generate_payout(c, 1, "2026-10-19")
        assert correction_payout["net"] == "-5.00"
        with pytest.raises(DomainError):
            s.create_correction(c, d["id"], dict(amount="1", reason="Test", delivered_on="2026-10-18"), TODAY)


def test_concurrent_finalise_only_once(db):
    with transaction(db) as c:
        s.create_delivery(c, delivery(), TODAY)
        p = s.generate_payout(c, 1, "2026-10-12")
    def finalise(_):
        try:
            with transaction(db) as c:
                return s.finalise_payout(c, p["id"])["status"]
        except DomainError:
            return "rejected"
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(finalise, range(2))) == ["Finalised", "rejected"]
    with transaction(db) as c:
        assert s.outstanding(c, 1) == "4272.50"


def test_manage_and_ledger(db):
    with transaction(db) as c:
        f = s.create_farmer(c, dict(name="Invented", phone="0000000003", village="Demo", bank_reference="Demo"))
        crop = s.create_crop(c, dict(name="New", grades=["A"], threshold="10", max_moisture="20"))
        assert crop["grades"] == "A"
        a = s.create_advance(c, dict(farmer_id=f["id"], amount="2.50", given_on="2026-10-19"), TODAY)
        assert a["outstanding"] == "2.50"
        assert s.ledger(c, f["id"])["advances_total"] == 1
        assert s.ledger(c, f["id"])["outstanding"] == "2.50"


@pytest.mark.parametrize("patch", [{"threshold": "21"}, {"max_moisture": "101"}, {"grades": ["A", "A"]},
                                  {"grades": []}, {"grades": ["A,B"]}])
def test_crop_validation(db, patch):
    with transaction(db) as c, pytest.raises(DomainError):
        s.create_crop(c, {**dict(name="New", grades=["A"], threshold="10", max_moisture="20"), **patch})

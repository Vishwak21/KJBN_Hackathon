from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from backend.api import app
from backend.db import transaction
from backend.seed import seed
from backend import services as s
from backend.rules import DomainError

DAY = date(2026, 10, 19)


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = str(tmp_path / "boundary.db")
    monkeypatch.setenv("DATABASE_PATH", path)
    seed(path)
    return path


def delivery(day):
    return dict(farmer_id=1, crop_id=1, grade="A", gross_kg="100", moisture="14", delivered_on=day)


def test_huge_identifiers_are_validation_errors(db):
    with TestClient(app) as client:
        for path in (
            "/api/farmers/999999999999999999999/ledger",
            "/api/payouts/999999999999999999999",
            "/api/prices?crop_id=999999999999999999999",
            "/api/payouts?farmer_id=999999999999999999999",
            "/api/farmers?offset=999999999999999999999",
        ):
            assert client.get(path).status_code == 422
        response = client.post(
            "/api/deliveries", json={**delivery("2026-10-12"), "farmer_id": 999999999999999999999}
        )
        assert response.status_code == 422


def test_seed_is_idempotent(db):
    seed(db)
    with transaction(db) as c:
        assert c.execute("SELECT count(*) FROM farmers").fetchone()[0] == 2


def test_new_deliveries_join_draft_and_later_payout(db):
    with transaction(db) as c:
        first = s.create_delivery(c, delivery("2026-10-12"), DAY)
        draft = s.generate_payout(c, 1, "2026-10-12")
        second = s.create_delivery(c, delivery("2026-10-18"), DAY)
        refreshed = s.generate_payout(c, 1, "2026-10-18")
        assert refreshed["id"] == draft["id"]
        assert {d["id"] for d in refreshed["deliveries"]} == {first["id"], second["id"]}
        s.finalise_payout(c, draft["id"])
        third = s.create_delivery(c, delivery("2026-10-13"), DAY)
        later = s.generate_payout(c, 1, "2026-10-12")
        assert later["id"] != draft["id"]
        assert [d["id"] for d in later["deliveries"]] == [third["id"]]


def test_concurrent_generation_has_one_draft_and_no_duplicate_membership(db):
    with transaction(db) as c:
        s.create_delivery(c, delivery("2026-10-12"), DAY)

    def generate(_):
        with transaction(db) as c:
            return s.generate_payout(c, 1, "2026-10-12")["id"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(generate, range(2)))
    assert ids[0] == ids[1]
    with transaction(db) as c:
        assert c.execute("SELECT count(*) FROM payouts").fetchone()[0] == 1


def test_two_drafts_recompute_against_remaining_balance(db):
    with transaction(db) as c:
        c.execute("DELETE FROM advances")
        s.create_advance(c, dict(farmer_id=1, amount="1000", given_on="2026-10-01"), DAY)
        drafts = []
        for day in ("2026-10-05", "2026-10-12"):
            s.create_delivery(c, delivery(day), DAY)
            drafts.append(s.generate_payout(c, 1, day))
        assert [p["deduction"] for p in drafts] == ["750.00", "750.00"]

    def finalise(identifier):
        with transaction(db) as c:
            return s.finalise_payout(c, identifier)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(finalise, [p["id"] for p in drafts]))
    assert sum(Decimal(r["deduction"]) for r in results) == Decimal("1000")
    with transaction(db) as c:
        assert s.outstanding(c, 1) == "0.00"


@pytest.mark.parametrize(
    "values",
    [
        dict(crop_id=1, grade="Z", price="1", effective_from="2026-10-01"),
        dict(crop_id=1, grade="A", price="1", effective_from="invalid"),
    ],
)
def test_price_validation(db, values):
    with transaction(db) as c, pytest.raises(DomainError):
        s.create_price(c, values)


def test_correction_rejections_and_edit_immutability(db):
    with transaction(db) as c:
        original = s.create_delivery(c, delivery("2026-10-12"), DAY)
        values = dict(amount="-1", delivered_on="2026-10-19", reason="Scale")
        with pytest.raises(DomainError):
            s.create_correction(c, original["id"], values, DAY)
        payout = s.generate_payout(c, 1, "2026-10-12")
        s.finalise_payout(c, payout["id"])
        with pytest.raises(DomainError):
            s.create_correction(c, original["id"], {**values, "amount": "0"}, DAY)
        note = s.create_correction(c, original["id"], values, DAY)
        with pytest.raises(DomainError):
            s.edit_delivery(c, note["id"], delivery("2026-10-19"), DAY)
        with pytest.raises(DomainError):
            s.create_correction(c, note["id"], values, DAY)
        with pytest.raises(DomainError):
            s.generate_payout(c, 1, "invalid")


def test_parallel_http_requests_keep_connections_request_scoped(db):
    with TestClient(app) as client:

        def fetch(index):
            paths = ["/api/farmers", "/api/crops", "/health"]
            return client.get(paths[index % len(paths)]).status_code

        with ThreadPoolExecutor(max_workers=8) as pool:
            statuses = list(pool.map(fetch, range(30)))
        assert statuses == [200] * 30


def test_full_demo_seed_includes_paid_history_and_correction(tmp_path):
    path = str(tmp_path / "demo.db")
    seed(path, sample_deliveries=True)
    seed(path, sample_deliveries=True)
    with transaction(path) as c:
        assert c.execute("SELECT count(*) FROM deliveries").fetchone()[0] == 5
        assert c.execute("SELECT status FROM payouts").fetchone()[0] == "Paid"
        assert s.outstanding(c, 1) == "4250.00"
        assert (
            c.execute("SELECT count(*) FROM deliveries WHERE original_id IS NOT NULL").fetchone()[0]
            == 1
        )

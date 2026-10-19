import sqlite3
import pytest
from fastapi.testclient import TestClient
from backend.api import app, connection
from backend.seed import seed


@pytest.fixture
def client(tmp_path, monkeypatch):
    path = str(tmp_path / "api.db")
    monkeypatch.setenv("DATABASE_PATH", path)
    monkeypatch.setenv("ALLOW_TEST_CLOCK", "true")
    seed(path)
    with TestClient(app) as client:
        client.headers["X-Test-Clock"] = "2026-10-19T12:00:00+05:30"
        yield client


def payload(**patch):
    return {**dict(farmer_id=1, crop_id=1, grade="A", gross_kg="100",
                   moisture="17.6", delivered_on="2026-10-12"), **patch}


def test_full_workflow(client):
    assert client.get("/health").status_code == 200
    assert client.get("/docs").status_code == 200
    assert client.get("/api/farmers").json()["total"] == 2
    assert len(client.get("/api/crops").json()["items"]) == 3
    assert client.get("/api/prices?crop_id=1&grade=A").json()["total"] == 1
    preview = client.post("/api/deliveries/preview", json=payload())
    assert preview.json()["amount"] == "2425.00"
    assert client.get("/api/farmers/1/ledger").json()["deliveries_total"] == 0
    d = client.post("/api/deliveries", json=payload()).json()
    assert d["amount"] == preview.json()["amount"]
    assert client.put(f"/api/deliveries/{d['id']}", json=payload()).status_code == 200
    p = client.post("/api/payouts", json=dict(farmer_id=1, week="2026-10-18")).json()
    assert p["week"] == "2026-10-12"
    assert client.post(f"/api/payouts/{p['id']}/pay").status_code == 409
    assert client.post(f"/api/payouts/{p['id']}/finalise").json()["deduction"] == "727.50"
    assert client.put(f"/api/deliveries/{d['id']}", json=payload()).status_code == 409
    assert client.post(f"/api/payouts/{p['id']}/finalise").status_code == 409
    assert client.post(f"/api/payouts/{p['id']}/pay").json()["status"] == "Paid"
    assert client.get(f"/api/payouts/{p['id']}").json()["gross"] == "2425.00"
    assert client.get("/api/payouts?farmer_id=1").json()["total"] == 1
    note = client.post(f"/api/deliveries/{d['id']}/corrections",
                       json=dict(amount="-25", delivered_on="2026-10-19", reason="Scale correction"))
    assert note.status_code == 201
    assert client.get("/api/farmers/1/ledger").json()["outstanding"] == "4272.50"


@pytest.mark.parametrize("data", [{}, [], None, {"farmer_id": True}, payload(gross_kg=10),
                                  payload(moisture="NaN"), payload(grade="Z"),
                                  payload(delivered_on="garbage"), payload(extra="bad")])
def test_malformed_requests(client, data):
    response = client.post("/api/deliveries", json=data)
    assert response.status_code == 422
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]
    assert "Traceback" not in response.text


def test_crud_and_conflicts(client):
    farmer = dict(name="Demo C", phone="0000000003", village="Demo", bank_reference="Demo")
    r = client.post("/api/farmers", json=farmer)
    assert r.status_code == 201
    assert client.put(f"/api/farmers/{r.json()['id']}", json={**farmer, "village": "Other"}).status_code == 200
    crop = dict(name="New crop", grades=["A"], threshold="10", max_moisture="25")
    assert client.post("/api/crops", json=crop).status_code == 201
    assert client.post("/api/crops", json=crop).status_code == 409
    price = dict(crop_id=1, grade="A", price="26.50", effective_from="2026-10-12")
    assert client.post("/api/prices", json=price).status_code == 201
    assert client.post("/api/prices", json=price).status_code == 409
    assert client.post("/api/advances", json=dict(farmer_id=1, amount="10", given_on="2026-10-19")).status_code == 201
    assert client.get("/api/farmers/999/ledger").status_code == 404
    assert client.get("/missing").json()["error"]["code"] == "http_error"
    assert client.get("/api/farmers?limit=10000").status_code == 422


def test_clock(client, monkeypatch):
    assert client.post("/api/deliveries/preview", json=payload(delivered_on="2026-10-20")).status_code == 422
    client.headers["X-Test-Clock"] = "not a clock"
    assert client.post("/api/deliveries/preview", json=payload()).status_code == 422
    client.headers["X-Test-Clock"] = "2026-10-19"
    assert client.post("/api/deliveries/preview", json=payload()).status_code == 422
    monkeypatch.setenv("ALLOW_TEST_CLOCK", "false")
    assert client.post("/api/deliveries/preview", json=payload()).status_code == 403
    del client.headers["X-Test-Clock"]
    assert client.post("/api/deliveries/preview", json=payload(delivered_on="2020-01-01")).status_code == 200


@pytest.mark.parametrize("exception,status,code", [(sqlite3.OperationalError("secret"), 503, "database_unavailable"),
                                                   (RuntimeError("secret"), 500, "internal_error")])
def test_database_and_unexpected_failure(client, exception, status, code):
    def fail():
        raise exception
    app.dependency_overrides[connection] = fail
    try:
        result = client.get("/health")
        assert result.status_code == status
        assert result.json()["error"]["code"] == code
        assert "secret" not in result.text
    finally:
        app.dependency_overrides.clear()

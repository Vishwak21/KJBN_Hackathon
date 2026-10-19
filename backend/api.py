"""HTTP transport. All domain decisions live in rules/services."""
import json
import logging
import os
import sqlite3
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import Depends, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from . import schemas, services
from .db import migrate, transaction
from .rules import DomainError

IST = timezone(timedelta(hours=5, minutes=30))
log = logging.getLogger("harvest")
log.setLevel(logging.INFO)
if not log.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(handler)
    log.propagate = False


def event(level, name, **fields):
    log.log(level, json.dumps({"timestamp": services.now(), "level": logging.getLevelName(level),
                               "event": name, **fields}))


def error(request, status, code, message, details=None):
    request_id = getattr(request.state, "request_id", uuid4().hex)
    return JSONResponse(status_code=status, content={
        "error": {"code": code, "message": message, "details": details or [],
                  "request_id": request_id}}, headers={"X-Request-ID": request_id})


def connection():
    with transaction() as conn:
        yield conn


def today(request: Request):
    override = request.headers.get("X-Test-Clock")
    if override:
        if os.getenv("ALLOW_TEST_CLOCK", "false").lower() != "true":
            raise DomainError("clock_disabled", "Reviewer clock is disabled.", 403)
        try:
            stamp = datetime.fromisoformat(override.replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                raise ValueError()
            return stamp.astimezone(IST).date()
        except ValueError:
            raise DomainError("invalid_clock", "X-Test-Clock requires a timezone-aware ISO timestamp.") from None
    return datetime.now(IST).date()


@asynccontextmanager
async def lifespan(app):
    migrate()
    yield


app = FastAPI(title="Harvest Ledger API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware,
                   allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
                   allow_methods=["GET", "POST", "PUT"], allow_headers=["Content-Type", "X-Test-Clock"],
                   expose_headers=["X-Request-ID"])


@app.middleware("http")
async def request_log(request: Request, call_next):
    request.state.request_id = uuid4().hex
    started = time.monotonic()
    try:
        response = await call_next(request)
    except Exception:
        event(logging.ERROR, "unexpected_error", request_id=request.state.request_id,
              method=request.method, path=request.url.path)
        response = error(request, 500, "internal_error", "Unexpected server error. Quote the request ID.")
    response.headers["X-Request-ID"] = request.state.request_id
    event(logging.INFO, "request", request_id=request.state.request_id,
          method=request.method, path=request.url.path, status=response.status_code,
          duration_ms=round((time.monotonic() - started) * 1000))
    return response


@app.exception_handler(DomainError)
async def domain_error(request, exc):
    event(logging.WARNING, "rule_violation", request_id=request.state.request_id,
          code=exc.code, path=request.url.path)
    return error(request, exc.status, exc.code, exc.message)


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    details = [{"field": ".".join(str(p) for p in e["loc"]), "message": e["msg"]} for e in exc.errors()]
    return error(request, 422, "validation_error", "Check the submitted fields.", details)


@app.exception_handler(sqlite3.IntegrityError)
async def conflict(request, exc):
    event(logging.WARNING, "database_constraint", request_id=request.state.request_id)
    return error(request, 409, "conflict", "An entry already exists or a referenced record is invalid.")


@app.exception_handler(sqlite3.OperationalError)
async def database_failure(request, exc):
    event(logging.ERROR, "database_unavailable", request_id=request.state.request_id)
    return error(request, 503, "database_unavailable", "Database temporarily unavailable. Retry shortly.")


@app.exception_handler(HTTPException)
async def http_error(request, exc):
    return error(request, exc.status_code, "http_error", str(exc.detail))


@app.get("/health")
def health(c=Depends(connection)):
    c.execute("SELECT 1")
    return {"status": "ok", "timestamp": services.now()}


@app.get("/api/farmers")
def farmers(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), c=Depends(connection)):
    rows = [dict(r) for r in c.execute("SELECT * FROM farmers ORDER BY id LIMIT ? OFFSET ?", (limit, offset))]
    return {"items": [{**r, "outstanding": services.outstanding(c, r["id"])} for r in rows],
            "total": c.execute("SELECT count(*) FROM farmers").fetchone()[0]}


@app.post("/api/farmers", status_code=201)
def add_farmer(data: schemas.Farmer, c=Depends(connection)):
    return services.create_farmer(c, data.model_dump())


@app.put("/api/farmers/{identifier}")
def update_farmer(identifier: int, data: schemas.Farmer, c=Depends(connection)):
    services.row(c, "farmers", identifier)
    c.execute("UPDATE farmers SET name=?,phone=?,village=?,bank_reference=? WHERE id=?",
              (*data.model_dump().values(), identifier))
    return services.row(c, "farmers", identifier)


@app.get("/api/crops")
def crops(c=Depends(connection)):
    return {"items": [dict(r) for r in c.execute("SELECT * FROM crops ORDER BY name")]}


@app.post("/api/crops", status_code=201)
def add_crop(data: schemas.Crop, c=Depends(connection)):
    return services.create_crop(c, data.model_dump())


@app.get("/api/prices")
def prices(crop_id: int | None = None, grade: str | None = None,
           limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), c=Depends(connection)):
    params = (crop_id, crop_id, grade, grade)
    where = "WHERE (? IS NULL OR crop_id=?) AND (? IS NULL OR grade=?)"
    rows = c.execute("SELECT * FROM prices " + where + " ORDER BY effective_from DESC,id DESC LIMIT ? OFFSET ?",
                     (*params, limit, offset))
    return {"items": [dict(r) for r in rows],
            "total": c.execute("SELECT count(*) FROM prices " + where, params).fetchone()[0]}


@app.post("/api/prices", status_code=201)
def add_price(data: schemas.Price, c=Depends(connection)):
    return services.create_price(c, data.model_dump())


@app.post("/api/advances", status_code=201)
def add_advance(data: schemas.Advance, day=Depends(today), c=Depends(connection)):
    return services.create_advance(c, data.model_dump(), day)


@app.post("/api/deliveries/preview")
def preview(data: schemas.Delivery, day=Depends(today), c=Depends(connection)):
    return services.preview_delivery(c, data.model_dump(), day)


@app.post("/api/deliveries", status_code=201)
def add_delivery(data: schemas.Delivery, day=Depends(today), c=Depends(connection)):
    return services.create_delivery(c, data.model_dump(), day)


@app.put("/api/deliveries/{identifier}")
def edit_delivery(identifier: int, data: schemas.Delivery, day=Depends(today), c=Depends(connection)):
    return services.edit_delivery(c, identifier, data.model_dump(), day)


@app.post("/api/deliveries/{identifier}/corrections", status_code=201)
def correct(identifier: int, data: schemas.Correction, day=Depends(today), c=Depends(connection)):
    return services.create_correction(c, identifier, data.model_dump(), day)


@app.post("/api/payouts", status_code=201)
def generate(data: schemas.Payout, c=Depends(connection)):
    return services.generate_payout(c, data.farmer_id, data.week)


@app.get("/api/payouts")
def payouts(farmer_id: int | None = None, limit: int = Query(100, ge=1, le=500),
            offset: int = Query(0, ge=0), c=Depends(connection)):
    params = (farmer_id, farmer_id)
    return {"items": [dict(r) for r in c.execute(
        "SELECT * FROM payouts WHERE (? IS NULL OR farmer_id=?) ORDER BY id DESC LIMIT ? OFFSET ?",
        (*params, limit, offset))],
        "total": c.execute("SELECT count(*) FROM payouts WHERE (? IS NULL OR farmer_id=?)", params).fetchone()[0]}


@app.get("/api/payouts/{identifier}")
def payout(identifier: int, c=Depends(connection)):
    return services.payout_detail(c, identifier)


@app.post("/api/payouts/{identifier}/finalise")
def finalise(identifier: int, c=Depends(connection)):
    return services.finalise_payout(c, identifier)


@app.post("/api/payouts/{identifier}/pay")
def pay(identifier: int, c=Depends(connection)):
    return services.pay_payout(c, identifier)


@app.get("/api/farmers/{identifier}/ledger")
def ledger(identifier: int, limit: int = Query(100, ge=1, le=500),
           offset: int = Query(0, ge=0), c=Depends(connection)):
    return services.ledger(c, identifier, limit, offset)

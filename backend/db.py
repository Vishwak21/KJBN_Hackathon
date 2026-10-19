"""SQLite persistence and transaction boundary."""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


def connect(path=None):
    target = path or os.getenv("DATABASE_PATH", "./data/procurement.db")
    Path(target).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target, timeout=15, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def migrate(path=None):
    with transaction(path) as conn:
        conn.executescript(Path(__file__).with_name("schema.sql").read_text())


@contextmanager
def transaction(path=None):
    conn = connect(path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

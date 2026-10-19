"""M1 executable contract for the required persistence model."""
from backend.db import migrate, transaction


def test_schema_and_foreign_keys(tmp_path):
    path = str(tmp_path / "test.db")
    migrate(path)
    with transaction(path) as conn:
        names = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master")}
        assert {"farmers", "crops", "prices", "advances", "deliveries", "payouts"} <= names
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1

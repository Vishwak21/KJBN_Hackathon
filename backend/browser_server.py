"""Isolated seeded server used only by Playwright."""

import os
import tempfile
from pathlib import Path
import uvicorn
from .seed import seed

if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="harvest-e2e-") as directory:
        os.environ["DATABASE_PATH"] = str(Path(directory) / "demo.db")
        os.environ["CORS_ORIGINS"] = "http://127.0.0.1:5173"
        seed()
        uvicorn.run("backend.api:app", host="127.0.0.1", port=8000, log_level="warning")

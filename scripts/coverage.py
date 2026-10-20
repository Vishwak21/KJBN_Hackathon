"""Run all backend tests and generate a small, reproducible committed summary."""

import subprocess
import sys
from pathlib import Path

result = subprocess.run(
    [
        sys.executable,
        "-m",
        "pytest",
        "--cov=backend",
        "--cov-report=term-missing",
        "--cov-report=json:coverage.json",
    ],
    check=False,
)
if result.returncode:
    raise SystemExit(result.returncode)
with Path("coverage.txt").open("w", encoding="utf-8") as report:
    subprocess.run(
        [sys.executable, "-m", "coverage", "report", "--show-missing"], stdout=report, check=True
    )

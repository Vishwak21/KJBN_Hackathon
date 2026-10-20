#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export DATABASE_PATH="${DATABASE_PATH:-$PWD/data/procurement.db}"
export STATIC_DIR="$PWD/frontend/dist"
export ALLOW_TEST_CLOCK="${ALLOW_TEST_CLOCK:-false}"
"$PWD/.venv/bin/python" -m backend.seed
exec "$PWD/.venv/bin/python" -m uvicorn backend.api:app --uds "${DOMAIN_SOCKET:?Provider must supply DOMAIN_SOCKET}"

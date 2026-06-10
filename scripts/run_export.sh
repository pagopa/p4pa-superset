#!/bin/bash

# ── Unico argomento posizionale: TAG ─────────────────────────────────────────
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <TAG>"
    echo "  All other variables must be set as environment variables."
    echo ""
    echo "  Required env vars:"
    echo "    SUPERSET_URL, SUPERSET_USER, SUPERSET_PASSWORD"
    exit 1
fi

TAG="$1"

# ── Validazione env var ───────────────────────────────────────────────────────
function checkEnv() {
    if [ -z "$(printenv "$1")" ]; then
        echo "An error occurred: $1 is not set"
        exit 1
    fi
}

checkEnv SUPERSET_URL
checkEnv SUPERSET_USER
checkEnv SUPERSET_PASSWORD

# ── Path ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_SCRIPT="$SCRIPT_DIR/export/export.py"

if [ ! -f "$PY_SCRIPT" ]; then
    echo "Cannot find export.py at: $PY_SCRIPT"
    exit 1
fi

# ── Invocazione Python ────────────────────────────────────────────────────────
cd "$SCRIPT_DIR/export" && python3 -m pipenv run python "$PY_SCRIPT" \
    "$SUPERSET_URL" \
    "$SUPERSET_USER" \
    "$SUPERSET_PASSWORD" \
    "$TAG"
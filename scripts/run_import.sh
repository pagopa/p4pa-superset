#!/bin/bash

# ── Unico argomento posizionale: TAG ─────────────────────────────────────────
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <TAG>"
    echo "  All other variables must be set as environment variables."
    echo ""
    echo "  Required env vars:"
    echo "    SUPERSET_URL, SUPERSET_USER, SUPERSET_PASSWORD"
    echo "    ANALYTICS_DB_USER, ANALYTICS_DB_PASSWORD"
    echo "    ANALYTICS_DB_HOST, ANALYTICS_DB_PORT, ANALYTICS_DB_NAME"
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
checkEnv ANALYTICS_DB_USER
checkEnv ANALYTICS_DB_PASSWORD
checkEnv ANALYTICS_DB_HOST
checkEnv ANALYTICS_DB_PORT
checkEnv ANALYTICS_DB_NAME

# ── Path ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_SCRIPT="$SCRIPT_DIR/import/import.py"
MANIFESTS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)/manifests/$TAG"
BUILD_DIR="$SCRIPT_DIR/import/build"

if [ ! -f "$PY_SCRIPT" ]; then
    echo "Cannot find import.py at: $PY_SCRIPT"
    exit 1
fi

if [ ! -d "$MANIFESTS_DIR" ]; then
    echo "Manifests folder not found for tag '$TAG': $MANIFESTS_DIR"
    exit 1
fi

echo "Importing assets for tag: $TAG"
echo "Manifests dir: $MANIFESTS_DIR"

# ── Invocazione Python ────────────────────────────────────────────────────────
cd "$SCRIPT_DIR/import" && python3 -m pipenv run python "$PY_SCRIPT" \
    "$TAG" \
    "$MANIFESTS_DIR" \
    "$BUILD_DIR"
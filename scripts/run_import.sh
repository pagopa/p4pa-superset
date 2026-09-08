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
BUILDER_SCRIPT="$SCRIPT_DIR/import/manifest_builder.py"
IMPORT_SCRIPT="$SCRIPT_DIR/import/import.py"
MANIFESTS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)/manifests/$TAG"
BUILD_DIR="$SCRIPT_DIR/import/build/$TAG"

if [ ! -f "$BUILDER_SCRIPT" ]; then
    echo "Cannot find manifest_builder.py at: $BUILDER_SCRIPT"
    exit 1
fi

if [ ! -f "$IMPORT_SCRIPT" ]; then
    echo "Cannot find import.py at: $IMPORT_SCRIPT"
    exit 1
fi

if [ ! -d "$MANIFESTS_DIR" ]; then
    echo "Manifests folder not found for tag '$TAG': $MANIFESTS_DIR"
    exit 1
fi

echo "Building manifests for tag: $TAG"
echo "Manifests dir: $MANIFESTS_DIR"

# ── Invocazione Python ────────────────────────────────────────────────────────
cd "$SCRIPT_DIR/import" && \
    python -m pipenv run python3 "$BUILDER_SCRIPT" \
        "$TAG" \
        "$MANIFESTS_DIR" \
        "$BUILD_DIR" && \
    python -m pipenv run python3 "$IMPORT_SCRIPT" \
        "$TAG" \
        "$BUILD_DIR"
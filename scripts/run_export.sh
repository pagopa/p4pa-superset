#!/bin/bash

if [ "$#" -ge 1 ]; then export SUPERSET_URL="$1"; fi
if [ "$#" -ge 2 ]; then export SUPERSET_USER="$2"; fi
if [ "$#" -ge 3 ]; then export SUPERSET_PASSWORD="$3"; fi

function print_help() {
    echo "To run the script you have to provide the following parameters:"
    echo "1. SUPERSET_URL"
    echo "2. SUPERSET_USER"
    echo "3. SUPERSET_PASSWORD"
    echo ""
}

function checkEnv() {
    if [ -z "$(printenv "$1")" ]; then
        print_help
        echo "An error occurred: $1 is not set"
        exit 1
    fi
}

checkEnv SUPERSET_URL
checkEnv SUPERSET_USER
checkEnv SUPERSET_PASSWORD

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_SCRIPT="$SCRIPT_DIR/export/export.py"
MANIFESTS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)/manifests"

if [ ! -f "$PY_SCRIPT" ]; then
    echo "Cannot find export.py at: $PY_SCRIPT"
    exit 1
fi

cd "$SCRIPT_DIR/export" && python3 -m pipenv run python "$PY_SCRIPT" \
    "$SUPERSET_URL" \
    "$SUPERSET_USER" \
    "$SUPERSET_PASSWORD" \
    "$MANIFESTS_DIR"
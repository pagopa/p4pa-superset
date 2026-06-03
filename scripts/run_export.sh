#!/bin/bash

if [ "$#" -ge 1 ]; then export TAG="$1"; fi

function print_help() {
    echo "To run the script you must provide the TAG as a parameter:"
    echo "Usage: $0 <TAG>"
    echo ""
    echo "The following environment variables must also be set:"
    echo "- SUPERSET_URL"
    echo "- SUPERSET_USER"
    echo "- SUPERSET_PASSWORD"
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
checkEnv TAG

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_SCRIPT="$SCRIPT_DIR/export/export.py"

if [ ! -f "$PY_SCRIPT" ]; then
    echo "Cannot find export.py at: $PY_SCRIPT"
    exit 1
fi

cd "$SCRIPT_DIR/export" && python3 -m pipenv run python "$PY_SCRIPT" \
    "$SUPERSET_URL" \
    "$SUPERSET_USER" \
    "$SUPERSET_PASSWORD" \
    "$TAG"
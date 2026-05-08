#!/bin/bash

if [ "$#" -ge 1 ]; then export SUPERSET_URL="$1"; fi
if [ "$#" -ge 2 ]; then export SUPERSET_USER="$2"; fi
if [ "$#" -ge 3 ]; then export SUPERSET_PASSWORD="$3"; fi
if [ "$#" -ge 4 ]; then export ANALYTICS_DB_HOST="$4"; fi
if [ "$#" -ge 5 ]; then export ANALYTICS_DB_PORT="$5"; fi
if [ "$#" -ge 6 ]; then export ANALYTICS_DB_NAME="$6"; fi
if [ "$#" -ge 7 ]; then export ANALYTICS_DB_USER="$7"; fi
if [ "$#" -ge 8 ]; then export ANALYTICS_DB_PASSWORD="$8"; fi

function print_help() {
    echo "To run the script you have to provide the following parameters:"
    echo "1. SUPERSET_URL"
    echo "2. SUPERSET_USER"
    echo "3. SUPERSET_PASSWORD"
    echo "4. ANALYTICS_DB_HOST"
    echo "5. ANALYTICS_DB_PORT"
    echo "6. ANALYTICS_DB_NAME"
    echo "7. ANALYTICS_DB_USER"
    echo "8. ANALYTICS_DB_PASSWORD"
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
checkEnv ANALYTICS_DB_HOST
checkEnv ANALYTICS_DB_PORT
checkEnv ANALYTICS_DB_NAME
checkEnv ANALYTICS_DB_USER
checkEnv ANALYTICS_DB_PASSWORD

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_SCRIPT="$SCRIPT_DIR/import/import.py"
MANIFESTS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)/manifests/superset_full_export"
BUILD_DIR="$SCRIPT_DIR/import/build"

if [ ! -f "$PY_SCRIPT" ]; then
    echo "Cannot find import.py at: $PY_SCRIPT"
    exit 1
fi

cd "$SCRIPT_DIR/import" && python3 -m pipenv run python "$PY_SCRIPT" \
    "$SUPERSET_URL" \
    "$SUPERSET_USER" \
    "$SUPERSET_PASSWORD" \
    "$ANALYTICS_DB_USER" \
    "$ANALYTICS_DB_PASSWORD" \
    "$ANALYTICS_DB_HOST" \
    "$ANALYTICS_DB_PORT" \
    "$ANALYTICS_DB_NAME" \
    "$MANIFESTS_DIR" \
    "$BUILD_DIR"
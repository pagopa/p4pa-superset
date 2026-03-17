#!/bin/bash

# If arguments are provided, use them to export environment variables. Otherwise, assume they're already set.
if [ "$#" -ge 4 ]; then
    export SUPERSET_URL="$1"
    export SUPERSET_USER="$2"
    export SUPERSET_PASSWORD="$3"
    export DB_PASS="$4"
fi

if [ "$#" -ge 5 ]; then
    export ZIP_FILE="$5"
fi

function print_help() {
    echo "To run the script you must ensure the following environment variables are set:"
    echo "1. SUPERSET_URL"
    echo "2. SUPERSET_USER"
    echo "3. SUPERSET_PASSWORD"
    echo "4. DB_PASS"
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
checkEnv DB_PASS

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_SCRIPT="$SCRIPT_DIR/import.py"

if [ ! -f "$PY_SCRIPT" ]; then
    echo "Cannot find import.py at: $PY_SCRIPT"
    exit 1
fi

if [ -n "$ZIP_FILE" ]; then
    if [ ! -f "$ZIP_FILE" ]; then
        echo "Cannot find ZIP file: $ZIP_FILE"
        exit 1
    fi
    echo "Using ZIP file: $ZIP_FILE"
    python3 "$PY_SCRIPT" --file "$ZIP_FILE"
else
    echo "No ZIP file specified, looking for the latest export in exports/..."
    python "$PY_SCRIPT"
fi
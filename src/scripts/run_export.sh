#!/bin/bash

# If arguments are provided, use them to export environment variables. Otherwise, assume they're already set.
if [ "$#" -ge 3 ]; then
    export SUPERSET_URL="$1"
    export SUPERSET_USER="$2"
    export SUPERSET_PASSWORD="$3"
fi

function print_help() {
    echo "To run the script you must ensure the following environment variables are set:"
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
PY_SCRIPT="$SCRIPT_DIR/export.py"

if [ ! -f "$PY_SCRIPT" ]; then
    echo "Cannot find export.py at: $PY_SCRIPT"
    exit 1
fi

python "$PY_SCRIPT"

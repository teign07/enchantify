#!/bin/bash
# Enchantify — Fuel Logger compatibility wrapper.
# Usage: bash scripts/log-fuel.sh "coffee and oatmeal" 350 8
# New code lives in food_log.py so lower-tier agents have one durable path.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESCRIPTION="${1:-unknown}"
CALORIES="${2:-0}"
PROTEIN="${3:-0}"

python3 "$SCRIPT_DIR/food_log.py" log "$DESCRIPTION" --calories "$CALORIES" --protein "$PROTEIN"

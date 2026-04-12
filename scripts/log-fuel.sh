#!/bin/bash
# Enchantify — Fuel Logger
# Called by the main agent when the player mentions food.
# Usage: bash scripts/log-fuel.sh "coffee and oatmeal" 350 8
#   arg1: description (what they ate)
#   arg2: estimated calories (can be 0 if unknown)
#   arg3: estimated protein grams (can be 0 if unknown)
#
# The agent estimates cal/protein from the description if not provided.
# The log is append-only; never delete entries.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FUEL_LOG="${SCRIPT_DIR}/fuel-log.txt"
HEARTBEAT_SCRIPT="${SCRIPT_DIR}/update-weather.sh"

DESCRIPTION="${1:-unknown}"
CALORIES="${2:-0}"
PROTEIN="${3:-0}"
TIMESTAMP=$(date +"%Y-%m-%d|%H:%M")

# Append entry: date|time|description|calories|protein
echo "${TIMESTAMP}|${DESCRIPTION}|${CALORIES}|${PROTEIN}" >> "$FUEL_LOG"

echo "✓ Logged: ${DESCRIPTION} (~${CALORIES} cal, ~${PROTEIN}g protein)"

# Refresh heartbeat so the change is reflected immediately
if [ -f "$HEARTBEAT_SCRIPT" ]; then
    bash "$HEARTBEAT_SCRIPT" > /dev/null 2>&1 &
fi

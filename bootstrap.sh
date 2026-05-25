#!/bin/bash
# Enchantify — local bootstrap.
# Run from a cloned repository with: bash bootstrap.sh

set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║   Enchantify — The Labyrinth of Stories     ║"
echo "  ╚══════════════════════════════════════════════╝"
echo ""
echo "  The book checks the desk before it opens."
echo ""

for cmd in git node npm python3; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "  Missing requirement: $cmd"
        exit 1
    fi
done

if ! command -v openclaw >/dev/null 2>&1; then
    echo "  OpenClaw is missing. Installing with npm..."
    npm install -g openclaw
fi

bash "$ROOT/hooks/on-install.sh"

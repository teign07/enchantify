#!/bin/bash
# Enchantify — Bootstrap
# The single entry point for a new install.
# Run this from the enchantify directory: bash bootstrap.sh
#
# What this does:
#   1. Checks Node.js, npm, Python 3
#   2. Installs OpenClaw (and ClawHub) if not present
#   3. Hands off to hooks/on-install.sh for the full setup wizard
#
# Re-running is safe — on-install.sh will skip steps already done.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║   📖  Enchantify — The Labyrinth of Stories  ║"
echo "  ╚══════════════════════════════════════════════╝"
echo ""
echo "     A living world inside a book."
echo "     Setup takes about five minutes."
echo ""

# ── 1. Check Node.js / npm ────────────────────────────────────────────────────

if ! command -v node &>/dev/null || ! command -v npm &>/dev/null; then
    echo "  ❌ Node.js and npm are required."
    echo "     Install from: https://nodejs.org  (LTS version recommended)"
    echo ""
    exit 1
fi
echo "  ✓ Node.js $(node --version)"

# ── 2. Check Python 3 ────────────────────────────────────────────────────────

if ! command -v python3 &>/dev/null; then
    echo "  ❌ Python 3.9+ is required."
    echo "     Install from: https://python.org"
    echo ""
    exit 1
fi
PY_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
echo "  ✓ Python $PY_VERSION"

# ── 3. Install OpenClaw ──────────────────────────────────────────────────────

if ! command -v openclaw &>/dev/null; then
    echo ""
    echo "  Installing OpenClaw..."
    npm install -g openclaw
    if [ $? -ne 0 ]; then
        echo "  ❌ OpenClaw install failed."
        echo "     Try: sudo npm install -g openclaw"
        exit 1
    fi
    echo "  ✓ OpenClaw installed"
else
    echo "  ✓ OpenClaw found"
fi

# ClawHub — best effort (optional for now, will be required for clawhub install)
if ! command -v clawhub &>/dev/null; then
    echo "  Installing ClawHub..."
    npm install -g clawhub 2>/dev/null && echo "  ✓ ClawHub installed" || \
        echo "  ℹ  ClawHub not available — continuing without it"
fi

# ── 4. Run the setup wizard ──────────────────────────────────────────────────

echo ""

INSTALL_HOOK="$SCRIPT_DIR/hooks/on-install.sh"

if [ ! -f "$INSTALL_HOOK" ]; then
    echo "  ❌ hooks/on-install.sh not found."
    echo "     Make sure you're running this from the enchantify directory."
    exit 1
fi

bash "$INSTALL_HOOK"

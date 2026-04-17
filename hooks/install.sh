#!/bin/bash
# ════════════════════════════════════════════════════════════════════════════
#  Enchantify — The Wanderer's Path
#  For people who don't have OpenClaw yet.
#
#  curl -fsSL https://raw.githubusercontent.com/teign07/enchantify/main/install.sh | bash
#
#  This script:
#    1. Installs OpenClaw if not present
#    2. Clones Enchantify into ~/.openclaw/workspace/enchantify
#    3. Hands off to hooks/on-install.sh for the full interactive wizard
# ════════════════════════════════════════════════════════════════════════════

set -e

ENCHANTIFY_DIR="$HOME/.openclaw/workspace/enchantify"

clear
echo ""
echo "  ╔══════════════════════════════════════════════════════════╗"
echo "  ║                                                          ║"
echo "  ║     📖  The Labyrinth of Stories                        ║"
echo "  ║                                                          ║"
echo "  ║     You found it. That means something.                 ║"
echo "  ║                                                          ║"
echo "  ╚══════════════════════════════════════════════════════════╝"
echo ""
sleep 1

# ── 1. Check Node.js ─────────────────────────────────────────────────────────

if ! command -v node &>/dev/null; then
    echo "  Node.js is required to install OpenClaw."
    echo ""
    echo "  Install it from: https://nodejs.org  (choose the LTS version)"
    echo "  Then run this installer again."
    echo ""
    exit 1
fi

if ! command -v python3 &>/dev/null; then
    echo "  Python 3.9+ is required."
    echo "  Install it from: https://python.org"
    echo ""
    exit 1
fi

# ── 2. Install OpenClaw if not present ───────────────────────────────────────

if ! command -v openclaw &>/dev/null; then
    echo "  OpenClaw is not installed. Installing it now..."
    echo "  (This is the AI agent platform Enchantify runs on.)"
    echo ""

    if curl -fsSL https://openclaw.ai/install.sh | bash; then
        echo ""
        echo "  ✓ OpenClaw installed."
    else
        echo ""
        echo "  Could not install via the official installer. Trying npm..."
        npm i -g openclaw
        echo "  ✓ OpenClaw installed via npm."
    fi

    echo ""
    echo "  ─────────────────────────────────────────────────────────"
    echo "  OpenClaw needs a quick setup before Enchantify can run."
    echo "  Run: openclaw onboard"
    echo ""
    echo "  Once that's done, run this installer again:"
    echo "  curl -fsSL https://raw.githubusercontent.com/teign07/enchantify/main/install.sh | bash"
    echo "  ─────────────────────────────────────────────────────────"
    echo ""
    exit 0
fi

echo "  ✓ OpenClaw found ($(openclaw --version 2>/dev/null || echo 'installed'))"
echo ""

# ── 3. Clone or update Enchantify ────────────────────────────────────────────

if [ -d "$ENCHANTIFY_DIR/.git" ]; then
    echo "  Enchantify is already installed. Pulling latest..."
    git -C "$ENCHANTIFY_DIR" pull --quiet
    echo "  ✓ Updated."
elif [ -d "$ENCHANTIFY_DIR" ]; then
    echo "  Found existing Enchantify directory (not a git repo)."
    echo "  Running setup wizard from existing install."
else
    echo "  Downloading Enchantify..."
    mkdir -p "$(dirname "$ENCHANTIFY_DIR")"
    git clone --quiet https://github.com/teign07/enchantify.git "$ENCHANTIFY_DIR"
    echo "  ✓ Downloaded."
fi

echo ""

# ── 4. Hand off to the wizard ────────────────────────────────────────────────

cd "$ENCHANTIFY_DIR"
bash hooks/on-install.sh --wanderer

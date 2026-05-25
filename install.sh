#!/bin/bash
# ════════════════════════════════════════════════════════════════════════════
#  Enchantify — The Wanderer's Path
#
#  One-command install:
#    curl -fsSL https://raw.githubusercontent.com/teign07/enchantify/main/install.sh | bash
#
#  This script installs/checks OpenClaw, clones or updates Enchantify, then
#  hands the reader to the in-world setup wizard.
# ════════════════════════════════════════════════════════════════════════════

set -e

REPO_URL="https://github.com/teign07/enchantify.git"
ENCHANTIFY_DIR="${ENCHANTIFY_DIR:-$HOME/.openclaw/workspace/enchantify}"

clear
echo ""
echo "  ╔══════════════════════════════════════════════════════════╗"
echo "  ║                                                          ║"
echo "  ║     The Labyrinth of Stories                            ║"
echo "  ║                                                          ║"
echo "  ║     You found it. That means something.                 ║"
echo "  ║                                                          ║"
echo "  ╚══════════════════════════════════════════════════════════╝"
echo ""
sleep 1

need() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "  $2"
        exit 1
    fi
}

need git "Git is required. Install Git, then run this installer again."
need node "Node.js is required. Install the LTS version from https://nodejs.org, then run this installer again."
need npm "npm is required. Install Node.js from https://nodejs.org, then run this installer again."
need python3 "Python 3.9+ is required. Install Python, then run this installer again."

if ! command -v openclaw >/dev/null 2>&1; then
    echo "  OpenClaw is not installed. Installing it with npm..."
    npm install -g openclaw
    echo ""
    echo "  OpenClaw is installed. Run its onboarding if needed:"
    echo ""
    echo "      openclaw onboard"
    echo ""
    echo "  Then run this Enchantify installer again."
    exit 0
fi

mkdir -p "$(dirname "$ENCHANTIFY_DIR")"
if [ -d "$ENCHANTIFY_DIR/.git" ]; then
    echo "  Enchantify is already here. Pulling the latest pages..."
    git -C "$ENCHANTIFY_DIR" pull --ff-only
elif [ -d "$ENCHANTIFY_DIR" ]; then
    echo "  Found $ENCHANTIFY_DIR, but it is not a git checkout."
    echo "  I will use it as-is and run the setup wizard."
else
    echo "  Downloading Enchantify..."
    git clone "$REPO_URL" "$ENCHANTIFY_DIR"
fi

cd "$ENCHANTIFY_DIR"
bash hooks/on-install.sh --wanderer

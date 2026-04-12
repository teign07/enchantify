#!/bin/bash
# Enchantify Bootstrap Sequence
# This script installs OpenClaw if missing, then installs Enchantify.

echo "================================================="
echo "   Welcome to the Enchantify Bootstrap Sequence  "
echo "================================================="
echo ""

# 1. Check for OpenClaw
if ! command -v openclaw &> /dev/null; then
    echo "ℹ OpenClaw is not currently installed on your system."
    echo "  We will now attempt to install it globally via npm."
    echo "  (This may require sudo or administrator privileges depending on your setup.)"
    echo ""
    npm install -g openclaw
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install OpenClaw. Please install it manually and try again."
        exit 1
    fi
    echo "✓ OpenClaw installed successfully."
else
    echo "✓ OpenClaw is already installed."
fi

echo ""
# 2. Check for ClawHub (usually installed with OpenClaw, but good to be safe)
if ! command -v clawhub &> /dev/null; then
    echo "ℹ ClawHub is not found. Attempting to install clawhub globally..."
    npm install -g clawhub
fi

echo "================================================="
echo "   Entering the Labyrinth...                     "
echo "================================================="
echo ""

# 3. Hand off to the standard installation process
clawhub install enchantify

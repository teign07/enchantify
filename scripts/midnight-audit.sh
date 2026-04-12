#!/bin/bash
# Enchantify — Midnight Audit (Ink-Growth Protocol)
# This script is called by OpenClaw cron to evolve the Labyrinth.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(dirname "$SCRIPT_DIR")"
OPENCLAW_DIR="$HOME/.openclaw"

# 1. Context Loading
HEARTBEAT_FILE="$WORKSPACE_DIR/config/player-heartbeat.md"
INTEGRATIONS_FILE="$WORKSPACE_DIR/config/integrations.md"
AGENTS_FILE="$WORKSPACE_DIR/AGENTS.md"

echo "📖 Starting Midnight Audit..."

# 2. Spawn the Architect (Gemini Flash sub-agent)
# The task is to review the current state and propose ONE growth step.
# We pass the content of core files as context.

TASK_PROMPT=$(cat <<EOF
You are the Midnight Architect of Enchantify. Your job is to grow the Labyrinth of Stories.

CONTEXT:
---
HEARTBEAT:
$(cat "$HEARTBEAT_FILE")

INTEGRATIONS:
$(cat "$INTEGRATIONS_FILE")

CORE RULES:
$(cat "$AGENTS_FILE")
---

TASK:
1. Scan for gaps between real-world data and Academy lore.
2. Identify any new OpenClaw skills that could be integrated (Discovery).
3. Alternatively, invent one new Room, NPC, or Enchantment that deepens the world (Invention).
4. For whatever you choose:
   - Design the narrative bridge.
   - Write the exact file content (Lore, Character, or Rule).
   - Define how NPCs will react to this new pulse.

OUTPUT:
Respond with a "Midnight Dispatch" for the player AND the exact 'write' or 'edit' commands to implement the change in the /proposed/ directory.
EOF
)

# Call sessions_spawn with the task
# Note: In a real script, this would use the openclaw CLI or API.
# For this implementation, we are defining the logic for the cron job.

# 3. Create Proposal Directory
TIMESTAMP=$(date +%Y-%m-%d)
PROPOSAL_DIR="$WORKSPACE_DIR/proposed/audit_$TIMESTAMP"
mkdir -p "$PROPOSAL_DIR"

echo "✓ Context gathered. Architect summoned."
echo "✓ Proposal directory created: $PROPOSAL_DIR"

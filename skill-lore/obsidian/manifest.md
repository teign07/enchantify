---
name: Obsidian Vault
id: obsidian
skill: obsidian
version: 1.0.0
description: Your Obsidian vault becomes the Academy Library — new notes arrive as manuscripts, linked notes reveal connections, orphans suggest lost works.
author: The Doobaleedoos
triggers:
  - type: session-open
  - type: cron
    schedule: "0 8 * * *"
config:
  - key: ENCHANTIFY_OBSIDIAN_VAULT
    description: Absolute path to your Obsidian vault directory
    required: true
  - key: ENCHANTIFY_OBSIDIAN_DAYS
    description: How many days back to scan for new/modified notes (default 1)
    required: false
requires:
  pip: []
  bins: []
---

## What OpenClaw Skill This Wraps

The `obsidian` skill — installed at `/opt/homebrew/lib/node_modules/openclaw/skills/obsidian/`.
The Labyrinth can also call this skill interactively ("what's in my vault?").

## What It Reads

Your Obsidian vault directory (`ENCHANTIFY_OBSIDIAN_VAULT`). Scans for:
- Notes created or modified in the last N days
- Notes with no outgoing links (orphans)
- Notes linked to many others (hubs)

## What It Writes

Writes to tick-queue (`memory/tick-queue.md`). One entry per note worth surfacing.

## Setup

Set `ENCHANTIFY_OBSIDIAN_VAULT` in `scripts/enchantify-config.sh`:
```bash
export ENCHANTIFY_OBSIDIAN_VAULT="/Users/yourname/Documents/MyVault"
export ENCHANTIFY_OBSIDIAN_DAYS="2"
```

## Interactive Use

The player can say:
- *"What's in my vault?"* → Labyrinth reads recent notes as Library acquisitions
- *"Is there anything in the vault about [topic]?"* → Labyrinth searches and frames results as Library research
- *"What are my orphan notes?"* → Labyrinth narrates these as lost manuscripts no one has cited

---
name: Template
id: template
skill: skill-name-in-openclaw
version: 1.0.0
description: One sentence — what real-world thing this brings into the game.
author: your name or handle
triggers:
  - type: cron
    schedule: "0 6 * * *"
  - type: session-open
config:
  - key: ENCHANTIFY_TEMPLATE_SETTING
    description: Where to find it, what it looks like
    required: true
  - key: ENCHANTIFY_TEMPLATE_OPTIONAL
    description: What it changes if set
    required: false
requires:
  pip: []
  bins: []
---

## What OpenClaw Skill This Wraps

Name the skill from `openclaw channels list` or the OpenClaw skills directory.
If no skill exists yet, describe the underlying tool/API this reads instead.

## What It Reads

The real-world data source. Be specific: which API endpoint, which file path,
which CLI command, which service. Include a link if there's a setup page.

## What It Writes

This contract writes to: **tick-queue** (`memory/tick-queue.md`)

Every entry follows this format:
```
## [template] 2026-04-09 14:00
*Raw: [the actual data — one fact, one event, one state]*
Narrative seed: [one sentence — what this means, not just what it is]
```

The Labyrinth processes the tick queue at session open and during the 4-hour
simulation. It reads `lore.md` (in this directory) to know how to narrate each
entry. The skill-lore contract doesn't control the story — it supplies material.

## Setup

Any one-time steps beyond setting config variables. OAuth flows, CLI installs,
enabling an API. Be concrete. Numbered list. Include exact commands.

## Interactive Use

Beyond the background pipeline, the Labyrinth can call the underlying skill
directly during conversation. Describe what that looks like — what the player
can say to invoke it, and what the Labyrinth does with the result.

Example: *"What's in my vault?" → Labyrinth uses the obsidian skill, then
frames the response as the Library revealing a manuscript.*

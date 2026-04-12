---
name: Things 3 (To-Do)
id: things
skill: things-mac
version: 1.0.0
description: Your tasks become Academy obligations — completed work earns Belief, overdue items invite the Nothing, and abandoned projects leave a shape in the world.
author: The Doobaleedoos
triggers:
  - type: cron
    schedule: "0 7 * * *"
  - type: session-open
config: []
requires:
  pip: []
  bins: [osascript]
---

## What OpenClaw Skill This Wraps

The `things-mac` skill — reads Things 3 via AppleScript on macOS.
macOS only. Requires Things 3 installed and at least one project or area set up.

## What It Reads

Today's tasks and overdue items via AppleScript. Looks at:
- Tasks due today (not yet complete)
- Tasks that became overdue in the last 2 days
- Tasks completed in the last 24 hours
- Projects with no recent activity (stalled)

## What It Writes

Writes to tick-queue (`memory/tick-queue.md`). Surfaces overdue items
as Nothing pressure; completions as Belief rewards.

## Setup

Requires macOS + Things 3. No additional configuration needed — Things 3
doesn't require an API key; AppleScript reads it directly.

## Interactive Use

- *"What do I have to do today?"* → Labyrinth reads today's tasks as the day's Academy obligations
- *"What have I been avoiding?"* → Labyrinth reads overdue items and frames them as the Nothing's territory
- *"I finished [task]"* → Labyrinth awards Belief and narrates the completion as an Academy achievement

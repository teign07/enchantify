---
name: Home Assistant
id: home-assistant
skill: none
version: 1.0.0
description: Your home becomes part of the Academy — presence, lights, temperature, doors, and routines all bleed into the world's atmosphere.
author: The Doobaleedoos
triggers:
  - type: cron
    schedule: "*/30 * * * *"
  - type: session-open
  - type: event
    event-type: home-assistant
config:
  - key: ENCHANTIFY_HA_URL
    description: Your Home Assistant URL (e.g. http://homeassistant.local:8123)
    required: true
  - key: ENCHANTIFY_HA_TOKEN
    description: Long-lived access token (HA → Profile → Long-Lived Access Tokens)
    required: true
  - key: ENCHANTIFY_HA_ENTITIES
    description: Comma-separated entity IDs to watch (leave blank to auto-discover interesting ones)
    required: false
requires:
  pip: [requests]
  bins: []
---

## What OpenClaw Skill This Wraps

No existing OpenClaw skill — reads Home Assistant's REST API directly.
Works with any HA instance on your local network or via Nabu Casa remote access.

## What It Reads

Home Assistant entity states via `GET /api/states`.
By default watches:
- `person.*` — presence (home/away)
- `binary_sensor.*door*`, `*motion*`, `*occupancy*` — activity
- `sensor.*temperature*` — ambient feel
- `light.*` — ambiance state
- `input_boolean.*` — manual signals you define

With `ENCHANTIFY_HA_ENTITIES` set, watches only those specific entities.

## What It Writes

Writes to tick-queue (`memory/tick-queue.md`).
Significant state changes only — filters out noise.

## Setup

1. Open Home Assistant → Profile (bottom left) → Long-Lived Access Tokens
2. Create token named "Enchantify"
3. Add to `scripts/enchantify-config.sh`:

```bash
export ENCHANTIFY_HA_URL="http://homeassistant.local:8123"
export ENCHANTIFY_HA_TOKEN="eyJ0eXAiOiJKV1QiLC..."
# Optional — watch only these:
export ENCHANTIFY_HA_ENTITIES="person.bj,binary_sensor.front_door,sensor.living_room_temperature"
```

Also run: `pip3 install requests`

## Interactive Use

- *"What's happening at home?"* → Labyrinth reads current HA state and narrates it
- *"Set the mood to [arc phase]"* → Labyrinth adjusts lights via openhue/HA to match story tone
- *"The Nothing is near"* → Labyrinth dims lights, lowers warmth via HA automations

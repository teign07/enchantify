---
name: Calendar
id: calendar
skill: none
version: 1.0.0
description: Your calendar becomes the Academy's schedule — meetings are gatherings, deadlines are looming events, free time opens windows for Compass Runs.
author: The Doobaleedoos
triggers:
  - type: cron
    schedule: "0 6 * * *"
  - type: session-open
config:
  - key: ENCHANTIFY_ICAL_URL
    description: Your calendar's iCal/ICS URL (Google Calendar, Apple Calendar, Fastmail, etc.)
    required: true
  - key: ENCHANTIFY_ICAL_DAYS_AHEAD
    description: How many days ahead to scan (default 2)
    required: false
requires:
  pip: [icalendar, requests]
  bins: []
---

## What OpenClaw Skill This Wraps

No existing OpenClaw skill — this reads iCal/ICS format directly.
Works with any calendar that exports an iCal URL: Google Calendar,
Apple Calendar, Fastmail, Proton Calendar, Outlook, Nextcloud, etc.

## What It Reads

Your calendar via iCal URL (`ENCHANTIFY_ICAL_URL`). Looks at events
in the next 1–2 days. Extracts: title, time, duration, attendee count,
recurrence (ritual vs one-off), and whether the time is blocked or free.

## What It Writes

Writes to tick-queue (`memory/tick-queue.md`). One entry per notable event.

## Setup

**Google Calendar:**
1. Open calendar.google.com → Settings → your calendar → Integrate calendar
2. Copy the "Secret address in iCal format"
3. Paste as `ENCHANTIFY_ICAL_URL` in `scripts/enchantify-config.sh`

**Apple Calendar:**
1. File → Export → Export... (for a one-time export)
2. For live URL: use iCloud Calendar sharing → Copy link → change `webcal://` to `https://`

**Then:**
```bash
export ENCHANTIFY_ICAL_URL="https://calendar.google.com/calendar/ical/..."
export ENCHANTIFY_ICAL_DAYS_AHEAD="2"
```

Also run: `pip3 install icalendar requests`

## Interactive Use

- *"What's on my calendar today?"* → Labyrinth narrates the day's encounters
- *"Do I have any free time this afternoon?"* → Labyrinth checks and suggests a Compass Run window
- *"What's the big thing this week?"* → Labyrinth identifies the heaviest event and frames it

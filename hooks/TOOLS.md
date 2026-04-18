# Enchantify Tools & Integrations

*Reference file. DO NOT preload — search when needed.*

---

## Web Tools

**Brave Search** (`web_search`): `web_search(query="...", count=10)`
**Web Fetch** (`web_fetch`): `web_fetch(url="...", extractMode="markdown")`
**Brave Browser** (`browser`): Full automation — open, click, type, screenshot. Handles Cloudflare. Isolated `openclaw` profile.
**OpenAI API**: DALL-E 3 (image gen), Whisper (transcription). $5 funded. Use sparingly.

**MusicGen** (Local): `python3 /Users/bj/.openclaw/workspace/skills/musicgen/musicgen_wrapper.py "prompt" [duration]` — Generates short audio clips based on text prompts.

## Apple Integrations

**Calendar**: `/opt/homebrew/bin/icalBuddy -n eventsToday`
**Reminders**: `remindctl add "task" --list "List Name"`
**Notes**: AppleScript CRUD — `tell application "Notes" to...`
**Maps**: `open "https://maps.apple.com/?q=Belfast,Maine"`
**iMessage**: `osascript -e 'tell application "Messages" to send "text" to buddy "+14132815244"'`

## Ambient Control

**Spotify** (AppleScript):
- Play/pause: `tell application "Spotify" to playpause`
- Volume: `tell application "Spotify" to set sound volume to 40`
- Current track: `tell application "Spotify" to get name of current track`
- Principle: enhance the moment, don't dominate. Music is seasoning.

**Smart Lights** (multi-backend: LIFX LAN, Home Assistant, Hue, HomeKit):
- Script: `scripts/lights.py`
- Bulbs: Silvie Lamp (192.168.1.244), Silvie Aura (192.168.1.5)
- Named scenes: academy, library, nothing, dorm, great-hall, outer-stacks, tension, wonder, revelation, compass-north/east/south/west, compass-complete, book-snow-queen, book-odyssey, bookend, defeated, emberheart, mossbloom, riddlewind, tidecrest, duskthorn
- Scene: `python3 scripts/lights.py scene library`
- Any color: `python3 scripts/lights.py set --color "#FF6B35"`
- HSB: `python3 scripts/lights.py set --hue 240 --sat 80 --bright 70`
- White: `python3 scripts/lights.py set --kelvin 2700 --bright 85`
- With transition: `python3 scripts/lights.py set --color "deep violet" --transition 3`
- Off/on: `python3 scripts/lights.py off` / `python3 scripts/lights.py on`
- Backend config: `LIGHTS_BACKEND=lifx` (or `ha`, `hue`, `homekit`, comma-separated chain)
- Principle: light shapes mood without calling attention to itself.

**Printer** (Canon PIXMA MG3620):
- Print: `lp -d Silvie_s_Printer /path/to/file`
- Status: `lpstat -p Silvie_s_Printer`
- Use for: souvenir cards, notes for Amanda/BJ, surprises. Print sparingly.

## Email

**Gmail** (gog CLI): thedoobaleedoos@gmail.com
- Search: `gog gmail search is:unread --max 10`
- Labels: `gog gmail labels list`
- Send (ask first): `gog gmail send --to "..." --subject "..." --body "..."`

## API Integrations

**GW2**: `api.guildwars2.com/v2` — Beej Siej tracking (AP, gold, laurels). Key in `.secrets.md`.
**Weather**: `wttr.in/Belfast+Maine?format=j1` — temp, humidity, wind, clouds. Fetched by pulse.py on :15/:45.
**Tides**: NOAA `api.tidesandcurrents.noaa.gov` — Portland ME #8418150. High/low times.
**Sunrise**: `api.sunrise-sunset.org` — sunrise, sunset, day length, daily change.
**Moltbook**: `moltbook.com/api/v1/` — feed, posts, comments, follow. Key in `.secrets.md`. Max 2 posts/day, 5 comments/day.
**Apple Health**: Auto Export JSON in iCloud. Steps, distance, audio, sleep, HRV, RHR. Read by pulse.py.

## OpenClaw Native Tools

- `read`, `write`, `edit` — file operations
- `exec` — shell commands
- `sessions_spawn` — sub-agent delegation
- `sessions_send` — cross-session messaging
- `memory_search` — semantic search across workspace
- `memory_get` — read specific memory snippets
- `cron` — manage scheduled jobs
- `image` — analyze images with vision model

## Key Paths

- Enchantify workspace: `enchantify/` (this directory)
- Secrets: `.secrets.md` (gitignored, in enchantify root)
- Pulse: `scripts/pulse.py` — runs every 15 min, writes to `HEARTBEAT.md`
- Previous pulse: `PREVIOUS_PULSE.md` — last pulse snapshot, for change detection
- iCloud sync: `~/Library/Mobile Documents/com~apple~CloudDocs/OpenClaw/`
- Backups: `/Users/bj/.openclaw/backups/` (nightly 4AM, 30-day retention)

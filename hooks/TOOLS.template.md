# Enchantify Tools & Integrations

*Reference file. DO NOT preload — search when needed.*

---

## Web Tools

**Brave Search** (`web_search`): `web_search(query="...", count=10)`
**Web Fetch** (`web_fetch`): `web_fetch(url="...", extractMode="markdown")`
**Brave Browser** (`browser`): Full automation — open, click, type, screenshot. Handles Cloudflare. Isolated `openclaw` profile.
**OpenAI API**: DALL-E 3 (image gen), Whisper (transcription). Use sparingly.

**MusicGen** (Local, optional): If installed — `python3 {{MUSICGEN_PATH}} "prompt" [duration]` — Generates short audio clips. Check if present before using.

## Apple Integrations

**Calendar**: `/opt/homebrew/bin/icalBuddy -n eventsToday`
**Reminders**: `remindctl add "task" --list "List Name"`
**Notes**: AppleScript CRUD — `tell application "Notes" to...`
**Maps**: `open "https://maps.apple.com/?q=Your+Location"`
**iMessage** (draft only — player sends): Queue drafts via scripts/pact-drivers/imessage.py; do NOT send directly without explicit player approval.

## Ambient Control

**Spotify** (AppleScript):
- Play/pause: `tell application "Spotify" to playpause`
- Volume: `tell application "Spotify" to set sound volume to 40`
- Current track: `tell application "Spotify" to get name of current track`
- Principle: enhance the moment, don't dominate. Music is seasoning.

**Smart Lights** (multi-backend: LIFX LAN, Home Assistant, Hue, HomeKit):
- Script: `scripts/lights.py`
- Backend: configured in `config/secrets.env` as `LIGHTS_BACKEND`
- Named scenes: academy, library, nothing, dorm, great-hall, outer-stacks, tension, wonder, revelation, compass-north/east/south/west, compass-complete, book-snow-queen, book-odyssey, bookend, defeated, emberheart, mossbloom, riddlewind, tidecrest, duskthorn
- Scene: `python3 scripts/lights.py scene library`
- Any color: `python3 scripts/lights.py set --color "#FF6B35"`
- HSB: `python3 scripts/lights.py set --hue 240 --sat 80 --bright 70`
- White: `python3 scripts/lights.py set --kelvin 2700 --bright 85`
- With transition: `python3 scripts/lights.py set --color "deep violet" --transition 3`
- Off/on: `python3 scripts/lights.py off` / `python3 scripts/lights.py on`
- Principle: light shapes mood without calling attention to itself.

**Printer** (if configured): `lp -d "{{PRINTER_NAME}}" /path/to/file` — Check `lpstat -p` for available printers. Use for souvenir cards, surprises. Print sparingly.

## Email

**Gmail** (gog CLI, if configured): `{{PLAYER_EMAIL}}`
- Search: `gog gmail search is:unread --max 10`
- Labels: `gog gmail labels list`
- Send (ask first): `gog gmail send --to "..." --subject "..." --body "..."`

## API Integrations

**Weather**: `wttr.in/{{PLAYER_LOCATION}}?format=j1` — temp, humidity, wind, clouds. Fetched by pulse.py on :15/:45.
**Tides**: NOAA `api.tidesandcurrents.noaa.gov` — local station ID in config/secrets.env.
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

- Enchantify workspace: `{{ENCHANTIFY_DIR}}/` (this directory)
- Secrets: `.secrets.md` (gitignored, in enchantify root)
- Pulse: `scripts/pulse.py` — runs every 15 min, writes to `HEARTBEAT.md`
- Previous pulse: `PREVIOUS_PULSE.md` — last pulse snapshot, for change detection
- iCloud sync: `~/Library/Mobile Documents/com~apple~CloudDocs/OpenClaw/`
- Backups: `{{OPENCLAW_HOME}}/backups/` (nightly 4AM, 30-day retention)

## Anchors & Outer Stacks

**GPS check-in** (player shares Telegram location):
- `python3 scripts/anchor-check.py [player] [lat] [lon] --checkin`

**Pocket anchors** (remote visit — Labyrinth runs these, never the player):
- Check charges: `python3 scripts/pocket-anchor.py status [player]`
- Open 30-min window: `python3 scripts/pocket-anchor.py activate [player] "[Anchor Name]"`
- Enter room: `python3 scripts/anchor-check.py [player] --pocket "[Anchor Name]"`
- Monthly refill (auto via tick.py day 1): `python3 scripts/pocket-anchor.py refill [player]`

**Flow:** Player says they want to visit → check GPS → not nearby → check charges → offer calling card → activate + get directive → lights scene `outer-stacks` → narrate with clock → fade at expiry.

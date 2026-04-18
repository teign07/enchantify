# Enchantify — Packaging Plan

*For when we're ready to share with the world. Not yet. Play first.*

---

## The Goal

**One command. Five minutes. They're in a living world.**

```bash
clawhub install enchantify
```

or for people without OpenClaw:

```bash
curl -fsSL https://raw.githubusercontent.com/teign07/enchantify/main/install.sh | bash
```

No configuration. No API key hunting. No lore to read before playing.

---

## What's Complete

### 0. **Privileged Access (BJ's Setup Only)** ✅

Your Enchantify has FULL access to Silvie's tools — Spotify, LIFX, printer, web search, browser, calendar, maps, notes, reminders, iMessage, email, GW2 API, Moltbook, Apple Health, image analysis, OpenAI. External users get weather/tides/sunrise by default, plus whatever they configure during the wizard.

---

### 1. **Install Path** ✅

**`install.sh`** — curl | bash entry point:
- Checks Node.js + Python 3.9+
- Installs OpenClaw if not present (official installer, npm fallback)
- Clones enchantify into `~/.openclaw/workspace/enchantify`
- Hands off to `hooks/on-install.sh --wanderer`

**`hooks/on-install.sh`** — interactive wizard (~1100 lines):
- OS detection; environment inventory (OpenClaw version, Python, Node)
- Returning player detection (skips name/player-file if save exists)
- Player name (what the Labyrinth calls you)
- Model selection (Sonnet 4.6 recommended; Opus, Haiku, GPT-4o, or custom)
- Location (city/state, lat/lon, NOAA tide station)
- Health data (Health Auto Export, Garmin, Fitbit, manual, or skip)
- Telegram setup (bot token + chat ID)
- **The Pact Ceremony** — which apps open to the Talisman War (Spotify, Notes, Reminders, Calendar, Obsidian, Moltbook, Bluesky, X, Reddit, Telegram, iMessage)
- Smart lights (LIFX, Home Assistant, Philips Hue, HomeKit, multi-backend chain)
- Spotify ambient control
- Voice acting (Kokoro TTS via Docker, optional)
- Image generation (DALL-E 3 or Stable Diffusion, optional)
- Memory plugins (QMD semantic search, Lossless Claw context engine)
- Agent registration in `openclaw.json` (main or named agent)
- Path substitution: patches `IDENTITY.md`, `SPAWN-HELPER.md`, generates `TOOLS.md` from `TOOLS.template.md`
- Player file creation (from inline template)
- Memory template generation (`arc-spine.md`, `patterns.md` from templates)
- Cron installation (8 jobs, staggered to avoid simultaneous firing)
- First pulse run

---

### 2. **The Living World — Simulation Engine** ✅

**`scripts/pulse.py`** — runs every 15 min:
- Weather, tides, sunrise/sunset, moon phase
- Apple Health (with EDEADLK retry on iCloud lock)
- Garmin, Fitbit backends
- Writes `HEARTBEAT.md`
- Auto-regenerates `mission-control.html` on every run

**`scripts/tick.py`** — runs every 4 hours:
- Entity Belief decay/growth (world register entities)
- NPC free investments into threads
- Thread escalation/cooling signals → `memory/tick-queue.md`
- Thread seed detection (NPC crosses Belief 20 with no thread)
- Fae bargain enforcement
- Pocket anchor monthly refill (day 1)
- Anchor Belief decay (absence)
- NPC talisman investments
- **Talisman behavior nudge** — HEARTBEAT.md signals (steps, sleep, HRV, calendar, fuel) shift talisman Belief ±1, capped at 2 talismans per tick

**`scripts/arc-tick.py`** — runs every 4 hours:
- Arc phase advancement
- Arc-specific entity stirring

**`scripts/world-pulse.py`** — runs every 4 hours:
- World-level narrative beats
- Nothing progression

**`scripts/reach-out.py`** — runs every 2 hours:
- Characters and talismans initiate direct contact via Telegram when conditions warrant

**`scripts/labyrinth-intelligence.py`** — runs nightly 11 PM:
- Story log update
- Arc spine update
- NPC research notes

**`scripts/dream.py`** — runs 2:03 AM:
- Dream generation

**`scripts/sparky.py`** — runs 8 AM:
- Daily "Shiny" — a small strange thing Sparky noticed
- Empty response guard: skips write if agent returns blank, retries next run

**`scripts/bleed.py`** — runs 6 PM:
- The Bleed broadsheet generation + delivery

**`scripts/wallpaper.py`** — runs 7 AM:
- Daily wallpaper generation

**`scripts/mission-control.py`**:
- Live game state HTML dashboard
- Threads, world state, cron jobs (openclaw + system crontab), bleed issues

---

### 3. **Talisman War — Pact System** ✅

**`scripts/pact-engine.py`** — core pact resolution engine

**`scripts/pact-drivers/`** — per-app action drivers:
- `spotify.py`, `apple_notes.py`, `apple_reminders.py`, `apple_calendar.py`
- `obsidian.py`, `moltbook.py`, `bluesky.py`, `x_twitter.py`, `reddit.py`
- `telegram.py`, `imessage.py`

**`lore/app-register.md`** — app territory definitions and chapter assignments

**`config/consent.json`** — player pact choices (written by installer, editable anytime)

---

### 4. **Story Thread System** ✅

**`lore/threads.md`** — thread registry with birth/lifecycle/closure rules:
- Belief-phase ladder (dormant → setup → rising → climax → resolution)
- Thread birth from three sources (tick seed, Labyrinth proposal, player investment)
- Natural resolution and Nothing victory closures
- Ley line thread template
- Archive section

**`lore/world-register.md`** — `## Active Threads` table, entity Belief scores

**`scripts/write-entity.py`** — surgical in-place thread belief updates via `--thread` flag (prevents destructive remove/reinsert pattern)

---

### 5. **Anchors & Outer Stacks** ✅

**`scripts/anchor-check.py`** — GPS check-in + pocket anchor entry:
- `--checkin`: records physical visit, updates anchor Belief
- `--pocket ANCHOR`: enters via pocket anchor window (no GPS required)
- Pocket session active check; suggests pocket if player isn't nearby

**`scripts/pocket-anchor.py`** — remote access state manager:
- Charge system (1 per anchor, max 1 stacked)
- 30-minute session windows
- Monthly refill via calling cards (Goblin Index Empire delivery)
- `config/pocket-anchors.json` (gitignored)

**`lore/ley-lines.md`** — anchor mechanics, ley line lore

**`lore/outer-stacks.md`** — Outer Stacks rooms, pocket anchor full visit rules

**Player inventory integration** — calling cards appear as items in `players/[name].md`, removed on use

---

### 6. **Combat, Dice, Beliefs** ✅

**`scripts/belief-attack.py`** — belief combat resolution
**`scripts/dice.py`** / `scripts/roll-dice.py`** — dice mechanics
**`mechanics/belief-dice.md`**, `mechanics/belief-combat.md`**, `lore/belief-investments.md`**

---

### 7. **Session Infrastructure** ✅

**`scripts/session-entry.py`**, `scripts/session-checkin.py`**, `scripts/close-session.py`**
**`scripts/scene-director.py`** — scene construction with Rule of Three
**`scripts/schedule.py`** — schedule awareness, state sync
**`scripts/ambient-state.py`** — ambient world state
**`mechanics/scene-construction.md`**, `mechanics/routing.md`**

---

### 8. **NPC System** ✅

**`scripts/npc-research.py`** — NPC research note generation
**`scripts/npc_log.py`** — NPC log management
**`memory/npc-research/`** — research note files (gitignored)
**`mechanics/npc.md`**, `lore/characters.md`**

---

### 9. **Player Management** ✅

**`scripts/update-player.py`** — player file updates
**`scripts/write-souvenir.py`** — Compass Run souvenir archival
**`scripts/write-diary.py`** — diary entries
**`scripts/complete-quest.py`** — quest completion
**`lore/player-management.md`**

---

### 10. **Lights & Ambient** ✅

**`scripts/lights.py`** — multi-backend smart lights:
- Backends: LIFX LAN, Home Assistant, Philips Hue, HomeKit (Shortcuts)
- Multi-backend chain (e.g. `lifx,ha` as fallback)
- Named scenes: academy, library, nothing, dorm, great-hall, outer-stacks, tension, wonder, revelation, compass-north/east/south/west, compass-complete, book-snow-queen, book-odyssey, bookend, defeated, emberheart, mossbloom, riddlewind, tidecrest, duskthorn
- Any color, HSB, kelvin, transition duration

---

### 11. **Cron Schedule (8 jobs, staggered)** ✅

| Job | Schedule | Purpose |
|-----|----------|---------|
| `pulse.py` | `*/15 * * * *` | Heartbeat, health, weather |
| `arc-tick.py` + `tick.py` + `world-pulse.py` | `30 */4 * * *` | World simulation |
| `schedule.py` | `0 */4 * * *` | Schedule state sync |
| `reach-out.py` | `10 */2 * * *` | Character outreach |
| `labyrinth-intelligence.py` | `0 23 * * *` | Nightly intelligence |
| `dream.py` | `3 2 * * *` | Dream generation |
| `wallpaper.py` | `0 7 * * *` | Morning wallpaper |
| `sparky.py` | `0 8 * * *` | Daily shiny |
| `bleed.py` | `0 18 * * *` | Evening broadsheet |

---

### 12. **Documentation** ✅

- `hooks/SKILL.md` — ClawHub listing (evocative, full features, install commands)
- `hooks/QUICKSTART.md` — player-facing guide
- `hooks/README.md` — GitHub readme
- `hooks/PLAYER-GUIDE.md` — full player reference
- `hooks/Enchantify-Capabilities.md` — v6.0.0 full capabilities reference
- `hooks/EXTENDING.md` — customization guide
- `hooks/TOOLS.template.md` — tools reference (personal data substituted at install time)

---

### 13. **Template & Gitignore System** ✅

Personal data is excluded from the repo:
- `config/secrets.env` (credentials)
- `config/consent.json` (pact choices)
- `config/pocket-anchors.json` (pocket anchor state)
- `players/` (player files)
- `memory/` (personal arc spine, patterns, NPC research, diary, dreams)
- `logs/`
- `lore/world-register.md`, `lore/app-register.md` (live world state)

Templates provided:
- `memory/arc-spine.template.md`, `memory/patterns.template.md`
- `hooks/USER.md.example`
- `config/secrets.env.example`

---

## Graceful Degradation

**Required:** OpenClaw + Python 3.9+ + Node.js 18+

**Optional (configured during wizard):**
- Health data → richer HEARTBEAT.md; without it, world simulation runs on weather/calendar only
- Telegram → characters reach out + dispatches; without it, world runs silently
- Lights → atmosphere shifts; without it, story-only
- Spotify → mood music; without it, text-only
- Voice (Kokoro) → NPCs speak aloud; without it, text-only
- Image gen → NPC portraits, scene illustrations; without it, described
- QMD + Lossless Claw → better memory in long sessions; without it, standard context window

**Minimum viable install:** A name and a location. Everything else is texture.

---

## What Needs Work Before External Release

- ⏳ **Windows support** — installer is bash; needs a PowerShell path or WSL note
- ⏳ **Playtesting by non-BJ users** — the installer assumes some technical comfort; may need softening
- ⏳ **ClawHub submission** — SKILL.md is ready; actual `clawhub install enchantify` flow untested
- ✅ **Player file template** — full structure generated at install (all sections, anchors file)
- ✅ **First-session tutorial** — `tutorial_director.py` detects T1 on first open; wizard hands off correctly
- ✅ **TOOLS.template.md completeness** — wizard now asks for printer name (auto-detects via `lpstat`) and email; substituted into TOOLS.md at install time

---

## Timeline

**When ready:** ~2 hours to final test + submit to ClawHub.

**For now:** Play. Test. Fix. Let the world breathe.

---

*Updated: April 2026*
*By: Silvie + BJ*
*For: When the world is ready*

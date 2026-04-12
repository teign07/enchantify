# Enchantify — Packaging Plan

*For when we're ready to share with the world. Not yet. Play first.*

---

## The Goal

**One command. Five minutes. They're in a living world.**

```bash
clawhub install enchantify
```

That's it. No configuration. No API key hunting. No lore to read before playing.

---

## What's Complete

### 0. **Privileged Access (BJ's Setup Only)** ✅

**Your Enchantify has FULL access to Silvie's tools:**
- **Symlink:** `enchantify/TOOLS.md` → `workspace/TOOLS.md`
- **What it enables:** Spotify, LIFX, printer, web search, browser, calendar, maps, notes, reminders, iMessage, email, GW2 API, Moltbook, Apple Health, image analysis, OpenAI
- **External users:** Get basic weather system only (wttr.in, sunrise-sunset.org)
- **You get:** The full ambient, embodied experience

**This is intentional.** Your Enchantify is privileged. It's not just a game — it's a living world that touches your actual life.

---

### 1. **SKILL.md** ✅
- What Enchantify is (evocative description)
- "The Living World" section (hourly updates, Unsent Messages)
- Model requirements (Sonnet first, fallback to primary)
- Installation command
- How to play
- Optional integrations table
- Customization section
- Connection to Wonder Compass
- License (CC BY-SA 4.0)

### 2. **hooks/on-install.sh** ✅
**What it does:**
- Detects OS (Mac/Linux/Windows)
- Auto-detects location via IP (or asks user)
- Creates the Enchantify registered agent
- Creates weather update script (Mac/Linux only)
- Registers weather update cron job (hourly)
- Creates directories (players/, souvenirs/, logs/, config/)
- **Copies templates:**
  - Player template
  - Log templates
- **Creates symlinks:**
  - `HEARTBEAT.md` (weather, tides, moon, season)
  - `TOOLS.md` (user's existing OpenClaw tools)
- Registers Academy Hourly Simulation cron job
- Registers Unsent Messages cron jobs (morning/evening)
- **Configures main agent** (creates enchantify-router.md skill)
- Beautiful final message

### 3. **scripts/update-weather.sh** ✅
**What it does:**
- Fetches weather from wttr.in (free, no API key)
- Fetches sun data from sunrise-sunset.org (free)
- Calculates moon phase (simplified)
- Determines season
- Writes to config/player-heartbeat.md
- Runs hourly via cron

### 4. **QUICKSTART.md** ✅
Player-facing documentation:
- What you're stepping into (the living world)
- Getting started (installation, first play)
- The magic system (Compass Runs, Enchantments)
- Optional features (auto-detected)
- FAQ (missing a week, customization, therapy question, the Nothing)
- The secret (connection to Wonder Compass)

### 5. **skills/enchantify-router.md** ✅
Tiny skill file (352 bytes) that:

**Opens Enchantify:**
- "open the book"
- "open the Labyrinth"
- "start Enchantify"
- "play Enchantify"

**Closes Enchantify:**
- "close the book"
- "close the Labyrinth"
- "stop playing"
- "exit Enchantify"

**Installed to:** Main agent's skills folder

### 6. **ENCHANTIFY-CAPABILITIES.md** ✅
Already exists. Full reference document.

---

## Graceful Degradation

**Required:** Nothing. Just OpenClaw.

**Optional (auto-detected):**
- **Claude OAuth** → If available, uses Sonnet. If not, falls back to Qwen.
- **LIFX lights** → If `lifxlan` + bulbs found, enables atmosphere. If not, skips.
- **Spotify** → If Spotify running, uses for music. If not, skips.
- **Printer** → If configured, offers souvenir printing. If not, PDF-only.

**User doesn't configure any of this.** Installation script checks and enables what it finds.

---

## First Run Experience

```bash
$ clawhub install enchantify
✓ Downloading Enchantify...
✓ Creating directories...
✓ Setting up world simulation...
✓ Registering hourly updates...

Enchantify is installed.

The Academy breathes whether you're watching or not.
Say "open the Labyrinth" to begin.
```

**Then:**
```
You: open the Labyrinth

The Labyrinth: The cover is plain. Leather, cracked, warm to the touch...

[Character creation → Chapter Sorting → Tutorial]
```

**Hourly updates appear in their heartbeat automatically.**

---

## Cron Jobs Registered

| Job | Schedule | What it does |
|-----|----------|--------------|
| **Academy Hourly Simulation** | Every hour at :00 | Advances world, logs, generates one-liner |
| **Unsent Messages (Morning)** | 11:00 AM | Labyrinth reaches out (max 1/day) |
| **Unsent Messages (Evening)** | 6:00 PM | Labyrinth reaches out (if morning skipped) |

---

## Status

**PACKAGE READY FOR INTERNAL TESTING.** External release after playtesting.

**What works:**
- ✅ Academy Hourly Simulation (running, producing narrative)
- ✅ Heartbeat integration (one-liners appearing in Telegram)
- ✅ Full lore + world state
- ✅ NPC roster with personality-driven decisions
- ✅ Nothing progression system
- ✅ Seasonal/weather integration
- ✅ SKILL.md (living world, model fallback, installation flow)
- ✅ hooks/on-install.sh (OS detection, location, weather system, agent creation, cron jobs)
- ✅ scripts/update-weather.sh (wttr.in, sunrise-sunset.org, moon phase, seasons)
- ✅ QUICKSTART.md (player documentation)
- ✅ ENCHANTIFY-CAPABILITIES.md (full reference)
- ✅ Mac/Linux support (Windows stretch goal)

**What needs work:**
- ⏳ Playtesting feedback (BJ + Amanda)
- ⏳ Bug fixes from playtesting
- ⏳ Windows support (stretch goal)
- ⏳ External release preparation

---

## Timeline

**When ready:** ~1 hour to package.

**For now:** Play. Test. Fix. Add features. Let the world breathe.

---

*Created: March 22, 2026*
*By: Silvie + BJ*
*For: When the world is ready*

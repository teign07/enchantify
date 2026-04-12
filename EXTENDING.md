# Extending Enchantify
### Everything Can Become Part of the Game

---

Enchantify is a narrative operating system. Its job is to translate real-world
data into story — then let the story act on the world. Every external system
you connect becomes part of the Academy. Every piece of data the Labyrinth
receives gets a narrative shape.

This document explains how to connect new things.

---

## The Architecture

```
Real world data source
        ↓
   skill-lore/[name]/tick.py
   (reads the source, writes narrative seeds)
        ↓
   memory/tick-queue.md
   (seeds accumulate between sessions)
        ↓
   Labyrinth reads lore.md + processes seeds
   (decides what to narrate, what to let breathe)
        ↓
   World register updated, player experiences story
```

Three files. That's all a skill-lore contract needs:

| File | Purpose |
|---|---|
| `manifest.md` | What skill this wraps, what config it needs, when it runs |
| `lore.md` | How the Labyrinth narrates this skill's output |
| `tick.py` | Reads the real-world source, writes to tick-queue (optional) |

`lore.md` is always required. `tick.py` is only needed if you want a background
pipeline — if your integration is interactive only (the player asks, the Labyrinth
responds), `manifest.md` + `lore.md` is enough.

---

## How to Build One

### 1. Copy the template

```bash
cp -r skill-lore/_template skill-lore/myapp
```

### 2. Fill in `manifest.md`

The frontmatter tells the skill scheduler what to do:

```yaml
---
name: My App
id: myapp
skill: myapp          # OpenClaw skill name, or "none" if you're doing it yourself
version: 1.0.0
description: One sentence — what real-world thing this brings into the world.
author: your handle
triggers:
  - type: cron
    schedule: "0 7 * * *"    # daily at 7am
  - type: session-open        # also runs when the player opens a session
config:
  - key: ENCHANTIFY_MYAPP_TOKEN
    description: API token — get one at app.example.com/settings
    required: true
requires:
  pip: [requests]
  bins: []
---
```

**Trigger types:**
- `cron` — runs on a schedule. Standard cron syntax.
- `session-open` — runs when the player starts a conversation.
- `event` — triggered by an external signal (Home Assistant webhook, etc.).

### 3. Write `lore.md`

This is the most important file. It tells the Labyrinth how to interpret
your skill's output. Be specific about:

- What this data source *is*, in Academy terms (not what it is in real life)
- What different raw signals mean narratively
- When to surface entries vs. let them be background texture
- Whether this maps to an entity in the world register

Read the reference contracts (`obsidian/lore.md`, `calendar/lore.md`, etc.)
to see what this looks like in practice. The lore.md quality determines the
quality of the narration. A vague lore.md produces vague story.

### 4. Write `tick.py` (if needed)

Your `tick.py` has three jobs:
1. **Fetch** — read data from the real-world source
2. **Translate** — turn each item into a narrative seed (one sentence)
3. **Write** — call `write_to_queue()` (copy from the template, don't modify)

The narrative seed is the key:

```python
# Bad — too vague
"Something happened."

# Bad — too dramatic, the Labyrinth handles tone
"The darkness of your unread emails descends like a storm!"

# Good — specific signal, present tense, lets the Labyrinth do the narration
"Three unread messages have been waiting for more than a week."
```

Your `tick.py` should:
- Always exit cleanly (catch all exceptions, `sys.exit(0)` on error)
- Cap output at 3–5 seeds per run — don't flood the queue
- Store state in `config/[skill-id]-cache.json` if you need to detect changes
- Never crash the tick run. One broken skill should never affect the others.

### 5. Register config variables

Add your config keys to `scripts/enchantify-config.sh`:

```bash
export ENCHANTIFY_MYAPP_TOKEN="your-token-here"
```

The skill scheduler sources this file before running your tick.py, so your
config will be in the environment automatically.

### 6. Test it

```bash
# Check that your skill is discovered
python3 scripts/skill-scheduler.py --list

# Dry run (shows what would run without running it)
python3 scripts/skill-scheduler.py --trigger cron --dry-run

# Actually run it
python3 scripts/skill-scheduler.py --trigger cron

# Check what it wrote
cat memory/tick-queue.md
```

---

## What Tick-Queue Entries Look Like

Every skill writes entries in this format:

```markdown
## [myapp] 2026-04-09 14:00
*Raw: the actual data — specific, factual*
Narrative seed: one sentence — what this means, not just what it is
```

The Labyrinth reads this at session open, checks `skill-lore/myapp/lore.md`
to understand the context, and decides what to weave into the world.

---

## Existing Skills You Can Wrap

Many OpenClaw skills already exist — you just need to write the lore contract:

| Skill | Data | Narrative potential |
|---|---|---|
| `obsidian` | Markdown vault | Library, manuscripts, reading room |
| `things-mac` | Things 3 tasks | Obligations, the Nothing's territory |
| `apple-notes` | Apple Notes | Personal archive, field notes |
| `apple-reminders` | Reminders | Ritual obligations, recurring rites |
| `notion` | Notion databases | Academy records, project archives |
| `github` | Commits, PRs, issues | Ink Well, manuscripts, open questions |
| `spotify-player` | Now playing | Ambient mood, Academy atmosphere |
| `openhue` | Hue lights | Scene-aware immersion, Nothing signals |
| `slack` | Messages, channels | Whisper network, Faculty communications |
| `trello` | Cards, boards | Quest board, project tiers |
| `weather` | Weather data | Already in heartbeat — extend with hyperlocal |

---

## What You Can Build

The question isn't "what can Enchantify do" — it's "what does the player's
real life contain that could be part of the story?"

Some ideas:

- **Email** — unread count as ambient pressure; long-untouched threads as the Nothing's preferred habitat
- **Fitness tracker** — workout sessions as combat training; rest days as recovery; sleep quality as the Academy's energy
- **Financial data** — account balance as Academy resources; unexpected expenses as crises; savings milestones as story beats
- **Reading tracker** (Goodreads, Literal) — books read as Library acquisitions; abandoned books as the Nothing's wins
- **Music practice** (Tonestro, SmartMusic) — practice sessions as Enchantment training
- **Language learning** (Duolingo, Anki) — streaks as maintained rituals; broken streaks as the Nothing
- **Sleep tracking** (Oura, WHOOP) — sleep quality shapes the Academy's daily energy; bad nights tighten the corridors
- **Weather station** — hyperlocal sensors feed directly into the atmosphere system
- **3D printer** — completed prints as created objects; failed prints as the Nothing's interference
- **Letterboxd** — films watched as Book Jumps into other narratives
- **Podcast history** — subjects discussed as Whispers arriving from the Unwritten

If it generates data, it can become story. That's the whole point.

---

## The Lore Contract Is the Product

The `tick.py` is infrastructure. The `lore.md` is what makes the integration
feel like it belongs in Enchantify rather than just feeding it data.

A good lore contract answers:
- What is this, *in Academy terms*? (Not "Obsidian" — "the player's Library annex")
- What does each signal *mean* narratively? (Not "new file" — "a fresh manuscript, still settling")
- When does it stay quiet and when does it demand a scene?
- Does it map to a world-register entity, and what raises/lowers that entity's Belief?

Write the lore contract like you're briefing a very attentive author on a new
character. The Labyrinth will do the rest.

---

## Sharing Your Skill-Lore

If you build a skill-lore contract, share it:

1. Fork the Enchantify repository
2. Add your `skill-lore/[name]/` directory
3. Open a pull request

Good lore contracts become part of the canon. The world grows.

---

*"Everything that happens to you is material. The Labyrinth just needs to know
how to read it."*

*— The Enchantify Lore Keeper*

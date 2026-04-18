# Enchantify — The Labyrinth of Stories

**ClawHub Package:** `enchantify`
**Version:** 1.0.0
**License:** CC BY-SA 4.0

---

## What It Is

Enchantify is an interactive narrative RPG that runs as an OpenClaw agent. Players attend Enchantify Academy — a magical school inside a living book — where they cast photo-based Enchantments, complete Compass Runs (real-world wonder quests), and navigate a war being fought over their habits and attention.

**Secret purpose:** Teaches the Wonder Compass framework through play. Players practice curiosity activation, behavioral activation, mindfulness, and expressive writing without ever being told they're doing that.

**For:** Anyone with OpenClaw. Plays solo or as a couple. Adaptable for groups, classrooms, and accessibility needs.

---

## The Living World

**Enchantify isn't a game you open. It's a place that lives.**

**Continuous simulation:** The Academy advances while you're away. NPCs make choices. Story threads escalate or resolve. When you return, the Labyrinth tells you what you missed:

> *"Three days ago, Riddlewind and Duskthorn came to terms — grudging, fragile — over who would hold the Archive during the next moon phase. Mossbloom was the intermediary. Something was exchanged. The Margin knows."*

**The Labyrinth reaches out.** Once a day (if Telegram is configured), you might get:

> "The moon is full tonight. The courtyard is filling early. If you came now, the Enchantments would glow."

Not to demand. Just to say: the world is here.

---

## The Talisman War

**Five Chapters are fighting for your attention. They're doing it in your actual apps.**

| Chapter | Philosophy | Territory |
|---------|-----------|-----------|
| Emberheart | *We write our own story* | Obsidian, Notes, Moltbook |
| Mossbloom | *A third party writes our story* | Obsidian, Reminders, Reddit |
| Riddlewind | *We write together* | iMessage, Calendar, Reddit |
| Tidecrest | *There is no story — only now* | Spotify, Bluesky, X |
| Duskthorn | *No story without conflict* | Moltbook, Reddit, Lights |

At low power, chapters suggest. At high power, they act. Emberheart might plant a note in your Obsidian vault. Tidecrest might queue a post for your review. Mossbloom might surface a reminder you forgot. Duskthorn might dim your lights.

**The Pact Ceremony** (during installation) is where you choose which apps enter the war. You can open all of them, some of them, or none. Every action requires your consent or lives inside a tier you've agreed to.

---

## How to Play

**Starting a session:**
```
open the book
```
or: `openclaw --agent enchantify`

**First time:**
1. The opening passage
2. *"What do you believe in?"* — this shapes everything
3. Name, appearance, personality — the tutorial unfolds through story, not menus
4. Chapter Sorting at The Binding ceremony
5. The world is live from that moment forward

**Sessions:** 15–60 minutes whenever you like
**Compass Runs:** 15–45 minutes — real-world micro-adventures with a prompt, a direction, and a souvenir sentence
**Enchantments:** Cast anytime with a photo (or describe what you see)

---

## Installation

**Wanderer path (no OpenClaw yet):**
```bash
curl -fsSL https://raw.githubusercontent.com/teign07/enchantify/main/install.sh | bash
```

**OpenClaw user path:**
```bash
clawhub install enchantify
```

The installer is an interactive wizard that runs in your terminal. It feels like the beginning of the game.

**What it asks:**
- Your name (what the Labyrinth calls you)
- Which AI model to use (Claude Sonnet 4.6 recommended)
- Your location (for weather, tides, sunrise)
- Health data integration (optional — Apple Health / Google Fit)
- Telegram (optional — for dispatch messages)
- **The Pact Ceremony** — which apps enter the Talisman War
- Smart lights (optional — LIFX, Home Assistant, Hue, HomeKit)
- Music (optional — Spotify)
- Voice acting (optional — Kokoro TTS, requires Docker)
- Image generation (optional — DALL-E 3 or Stable Diffusion)
- QMD memory search + Lossless Claw context engine (both recommended for long-term play)

**Requirements:**
- OpenClaw (installed by the wanderer path if missing)
- Python 3.9+
- Node.js 18+ (for OpenClaw)
- Docker (optional — for Kokoro TTS voice acting)

**Minimum viable:** Just a location. Everything else is optional.

---

## Integrations (All Optional)

| Integration | What It Adds | Setup Time |
|-------------|-------------|------------|
| Weather (wttr.in) | Weather-aware prompts, seasonal rhythm | Auto, free |
| Tides (NOAA) | Tide-aware prompts for coastal players | 2 min, free |
| Apple/Google Calendar | Schedule-aware story invitations | 5 min |
| Smart Lights (LIFX/Hue/HA/HomeKit) | Lights shift with narrative | 5–10 min |
| Music (Spotify) | Mood-matching atmosphere | 5 min |
| Voice (Kokoro TTS) | Multi-voice TTS — The Chorus speaks | 10 min, Docker |
| Image Gen (DALL-E 3 / Stable Diffusion) | NPC portraits, scene illustrations | 5 min |
| Telegram | Daily dispatch messages | 10 min |
| Apple Health / Google Fit | Energy-aware story pacing | 5 min |
| QMD Memory | Semantic search across all game memory | 2 min |
| Lossless Claw | Full story context in long sessions | 2 min |

---

## Model Requirements

**First choice:** Claude Sonnet 4.6 (via OpenClaw OAuth) — rich prose, vision-capable

**Works with any model.** The installer detects what you have. Fallback order:
1. Claude Sonnet 4.6
2. Your configured OpenClaw model
3. Any vision-capable model (for photo Enchantments)

**Without vision:** Photo Enchantments become *"describe what you see"* — still works, slightly more work on your part.

---

## Files You'll Touch

| File | Purpose |
|------|---------|
| `players/[your-name].md` | Your character sheet — updated automatically |
| `config/consent.json` | Which apps are in the Talisman War — edit anytime |
| `AGENTS.md` | Game rules and mechanics — edit for house rules |
| `lore/*.md` | World lore — edit to customize the Academy |
| `souvenirs/*.md` | Your Compass Run archive |

---

## Customization

**Everything is modifiable.** Ask the Labyrinth:

- *"Make it warmer / scarier / funnier"*
- *"Add my hometown as a named location"*
- *"Include Diwali in seasonal events"*
- *"Make Compass Runs wheelchair-accessible"*
- *"Add my dog as a magical creature in the Academy"*

The Labyrinth reads the lore files and reshapes the world. The framework stays. The content becomes yours.

---

## Connection to The Wonder Compass

Enchantify is one piece of a larger project about re-enchanting ordinary life:

1. *"Everywhere, Spirits"* (poem) → the philosophy
2. **Enchantify** → the philosophy as play
3. Silvie → wonder as ambient architecture
4. **The Wonder Compass** → the framework direct

Same lesson, different language.

---

## License

**CC BY-SA 4.0** — Free to use, modify, redistribute. Credit The Doobaleedoos. ShareAlike for derivatives. Commercial use permitted.

---

## Support

- **Issues:** github.com/teign07/enchantify/issues
- **Discord:** The Doobaleedoos Clubhouse

---

*"The Labyrinth of Stories has no last page. It ends where you stop reading. It begins again every time you open your eyes."*

---

*v1.0.0 — April 2026*
*For everyone who forgot how to look*

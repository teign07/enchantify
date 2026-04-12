# Enchantify — The Labyrinth of Stories

**ClawHub Package:** `enchantify`
**Version:** 0.1.0 (development)
**License:** CC BY-SA 4.0

---

## What It Is

Enchantify is an interactive narrative RPG that runs as an OpenClaw agent. Players attend Enchantify Academy — a magical school inside a living book — where they cast photo-based Enchantments, complete Compass Runs (real-world wonder quests), and battle the Nothing (the Rut of Routine in disguise).

**Secret purpose:** Teaches the Wonder Compass framework through play. Players practice curiosity activation, behavioral activation, mindfulness, and expressive writing without ever being told they're doing therapy.

**For:** Anyone with an OpenClaw instance. Plays solo or as a couple. Adaptable for groups, classrooms, accessibility needs.

---

## The Living World

**Enchantify isn't a game you open. It's a place that lives.**

**Hourly updates:** The Academy advances every hour whether you're playing or not. NPCs make choices. The Nothing moves. Relationships evolve. You'll see updates in your heartbeat:

> 📖 Academy: Zara found something in the book — the symbols match the fog. She's taking notes.

**The Labyrinth reaches out:** Once a day (max), the Labyrinth might text you:

> "The moon is full tonight. The courtyard is filling up early. If you came now, the Enchantments would glow."

Not to demand. Just to say: the world is here. It's beautiful. You're welcome.

**Model:** Uses Claude Sonnet 4.6 (via OAuth) for rich prose. If you don't have Sonnet, falls back to your primary OpenClaw model automatically. Still works. Still alive.

---

## Installation

```bash
clawhub install enchantify
```

The installer runs automatically and walks you through setup interactively:

1. **Detects your OS** (Mac/Linux/other)
2. **Finds your location** — auto-detects via IP, or asks if wrong
3. **Detects your timezone** — auto-reads from system, or asks
4. **Asks about hemisphere** — for accurate seasons
5. **Asks for NOAA station ID** (optional — US coastal tides only)
6. **Detects your model** — Claude Sonnet if available, else GPT-4o or Qwen
7. **Writes your config** to `scripts/enchantify-config.sh`
8. **Creates the heartbeat** — standalone weather file (or links to Silvie if she's present)
9. **👤 Identity link** — symlinks to your global `USER.md` so Enchantify knows you from day one
10. **Runs the first weather fetch** — your heartbeat is live immediately
11. **Registers cron jobs** — world simulation (hourly), heartbeat update (hourly), outreach checks (morning/evening)
12. **Configures routing** — adds "open the book" to your main agent

**Requirements:** `curl` and `jq` (standard on Mac; `apt install jq` on Linux)

**What the heartbeat includes (standalone install):**
- Weather: condition, temperature, feels-like, humidity, wind, pressure, visibility
- Sun: accurate sunrise/sunset for your coordinates
- Moon: astronomically accurate phase and illumination (not an approximation)
- Tides: high/low times with direction (if NOAA station configured)
- Season: named Enchantify seasons (Mud Season, Bloom, Gold, Stick Season, Deep Winter)

**If you also have Silvie:** Enchantify links to her heartbeat automatically, which includes Spotify, fuel gauge, step count, and Sparky shinies in addition to the above.

---

## How to Play

**Starting a session:**
- Say: *"open the book"* or *"open the Labyrinth"*
- Or: `openclaw chat --agent enchantify`
- Or on Discord: in the `#enchantify` channel (if configured)

**First time — the Labyrinth guides you:**
1. Opening passage (you'll know it when you read it)
2. *"What do you believe in?"* — this shapes everything
3. Character creation: name, appearance, personality
4. First day at the Academy begins — the tutorial unfolds through story, not menus
5. Chapter Sorting happens when the narrative reaches it (The Binding ceremony)

**The world is live between sessions:**
- Hourly simulation runs whether you're playing or not
- NPCs make decisions. Story threads advance. The Nothing moves.
- When you return, the Labyrinth tells you what happened while you were away

**Sessions:** 15–60 minutes whenever you like
**Compass Runs:** 15–45 minutes, real-world micro-adventures
**Enchantments:** Cast anytime with a photo (or describe what you see)

---

## Model Requirements

**First choice:** Claude Sonnet 4.6 (via OAuth) — rich prose, vision-capable

**Fallback:** Your primary OpenClaw model (automatically detected)

**How it works:** The installer checks if you have Claude OAuth configured. If yes, uses Sonnet. If not, uses your default model. No configuration needed on your part.

**Also works with:**
- Qwen 3.5 (free, vision-capable)
- GPT-4o (vision-capable)
- Any text model (photo Enchantments become text descriptions)

**Vision:** Recommended but not required. Photo Enchantments gracefully degrade to "describe what you see" if vision unavailable.

---

## Integrations (All Optional)

|Integration |What It Adds |Setup Time |
|------------|-------------|-----------|
|Weather (OpenWeatherMap) |Weather-aware prompts |2 min, free |
|Tides (NOAA) |Tide-aware prompts (coastal) |2 min, free |
|Calendar (Google/Apple) |Schedule-aware invitations |5 min |
|Smart Lights (Hue/LIFX/HA) |Lights change with narrative |5-10 min |
|Music (Spotify/Apple) |Mood-matching soundtracks |5 min |
|Voice (Kokoro TTS) |Multi-Voice TTS (The Chorus) |10 min, Docker |
|Image Gen (OpenAI/Local) |Character portraits, scene art |5 min |
|Printer |Physical souvenir cards |2 min |

**Minimum viable:** Just a location. The game works fully with nothing else.

---

## Files You'll Touch

|File |Purpose |
|-----|--------|
|`SOUL.md` |The Labyrinth's identity (don't edit unless customizing voice) |
|`AGENTS.md` |Game rules, mechanics (edit for house rules) |
|`players/[your-name].md` |Your character sheet (updated automatically) |
|`souvenirs/[date]-[name].md` |Your Compass Run archive (yours to keep) |
|`lore/*.md` |World building (edit to customize the world) |

---

## Customization

**Everything is modifiable.** Ask the Labyrinth to:

- *"Make it warmer/cozier/scarer"*
- *"Add my hometown as a location"*
- *"Include [cultural holiday] in seasonal events"*
- *"Make Compass Runs wheelchair-accessible"*
- *"Add my dog as a magical creature"*

The Labyrinth reads the lore files and reshapes the world. The framework stays intact. The content becomes yours.

---

## Connection to The Wonder Compass

Enchantify is one node in BJ and Amanda's larger project:

1. "Everywhere, Spirits" (poem) → philosophy
2. **Enchantify (this game)** → philosophy as play
3. Glowing Pains → stepping inside the system
4. Silvie (AI companion) → wonder as architecture
5. **The Wonder Compass (book)** → framework direct
6. The Doobaleedoos (brand) → bringing it to the world

**Same lesson, different language.**

---

## License

**CC BY-SA 4.0** — Free to use, modify, redistribute. Credit The Doobaleedoos. ShareAlike for derivatives. Commercial use permitted.

---

## Support

**Discord:** The Doobaleedoos Clubhouse (Patreon)
**Issues:** [GitHub repo when published]
**Souvenir Sharing:** #souvenirs channel (post your One-Sentence Souvenirs)

---

*"The Labyrinth of Stories has no last page. It ends where you stop reading. It begins again every time you open your eyes."*

---

*Created: March 22, 2026*
*For bj and Amanda*
*For everyone who forgot how to look*

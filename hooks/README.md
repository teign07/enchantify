# The Labyrinth of Stories

*I mixed my OpenClaw agent with an RPG, and now it's turning my life into an Urban Fantasy.*

**Enchantify** is a slow, living narrative game that runs on your own machine.

It knows your name. It watches the weather outside your window. It notices when you've been sitting still too long. When you open it, it picks up exactly where you left off — because it never really stopped.

The world is Enchantify Academy: a magical school-library where you are a student, every NPC is voiced, and the most powerful form of magic is paying attention to your actual life. The Labyrinth — an ancient, sentient book — is your narrator, your dungeon master, and something close to a friend.

---

## What it actually is

A slow burn. Think of it like texting a friend who happens to be a centuries-old book living in your computer.

It won't always reply instantly. Some things take time to develop — a story arc, a character relationship, the right moment for a scene. The world pulses every 15 minutes in the background. If you haven't heard from it in a while, that's often intentional. It's waiting for the right moment.

This is not a game you sprint through. It's one you live alongside.

---

## Features

- **A living world** — a background process runs every 15 minutes, reading the real world (weather, time, season, tides) and weaving it into the Academy's atmosphere
- **Real-world integration** — smart lights shift at story moments, music pauses when the Compass calls for silence, Telegram delivers dispatches from NPCs while you're away
- **The Wonder Compass** — a real-life practice (N-E-S-W-Center framework) embedded as in-game mechanic: go outside, notice things, write one sentence, earn Belief
- **Full voice acting** — every NPC has a distinct voice via Kokoro TTS (optional, local, free)
- **Pact system** — each integration (lights, music, email, financials) is a named Pact you choose to activate. Nothing runs without your permission. Say `THORNE` to pause everything
- **Book Jumps** — fall into books and live their worlds. The Wonder Compass book is a special case: you fall into the author's memories
- **Health awareness** — reads your step count, sleep, and heart rate (via iPhone Health Auto Export or Garmin/Fitbit) and lets it bleed into the world's texture
- **Any LLM** — works with Claude, GPT-4o, or any model OpenClaw supports

---

## How it works

Enchantify runs as an agent on [OpenClaw](https://openclaw.ai) — an open-source AI agent platform that you install locally. Your data stays on your machine. No accounts, no subscriptions, no cloud.

A cron job runs `scripts/pulse.py` every 15 minutes. It gathers the real world — weather, time of day, season, your health data, whether you're home, what music is playing — and writes it to `HEARTBEAT.md`. When you open the game, the Labyrinth reads that file and knows what kind of day you've been having before you say a word.

The Pact War (`scripts/pact-engine.py`) has Talismans competing for control of your real-world apps — Spotify, Apple Notes, Calendar, Moltbook, and more. At high control tiers, a Talisman acts through its apps: cueing music, creating notes, drafting posts. Social media actions always require your approval before anything is posted.

---

## Installation

**New to OpenClaw?** One command installs everything:

```bash
curl -fsSL https://raw.githubusercontent.com/teign07/enchantify/main/install.sh | bash
```

**Already have OpenClaw?** Install via ClawHub:

```bash
npx clawhub@latest install enchantify
```

The wizard will walk you through:
- Choosing your AI model
- Setting your location (for weather and tides)
- Connecting health data (iPhone, Garmin, Fitbit, or none)
- Setting up Telegram for dispatches
- The Pact Ceremony — activating only the integrations you want
- Optional: voice acting (Kokoro TTS), image generation (DALL-E 3), ambient music (MusicGen)

At the end, the wizard will tell you to open OpenClaw and say: `Open the book`

---

## Requirements

- **OpenClaw** 2026.x or later
- **Python 3.9+**
- **Node.js** (for OpenClaw)
- An API key for your chosen LLM (Claude, OpenAI, etc.)
- macOS, Linux, or WSL on Windows

Optional:
- iPhone with [Health Auto Export](https://apps.apple.com/app/health-auto-export-json-csv/id1477944755) for health data
- LIFX, Philips Hue, or Home Assistant for smart lights
- Spotify for music integration
- Docker for voice acting (Kokoro TTS) or ambient music (MusicGen)
- Telegram for out-of-session dispatches

---

## The Pact Ceremony

During installation you'll be asked about each app integration. Private apps (Spotify, Notes, Calendar) act silently — you discover what a Talisman did when you open the app. Social media posts always surface in the tick-queue as drafts first. Nothing goes out without your approval.

---

## Slow is right

The Labyrinth has existed for an unknowable amount of time. It can wait.

When a reader needs to go live their life and come back later, the pages stay open. Some story arcs take days. Some NPC relationships take weeks. The world keeps breathing in the background regardless.

You don't need to check in every day. But when you do, it will know what the weather was like while you were gone.

---

## License

Code (`.py`, `.sh`, `.js`): **MIT License** — see [LICENSE](LICENSE)

Creative content (lore, story, NPC descriptions, mechanics, SOUL.md, AGENTS.md, Wonder Compass framework integration): **CC BY-SA 4.0** — see [LICENSE-CONTENT](LICENSE-CONTENT)

The Wonder Compass framework is the work of BJ Liverseidge / The Doobaleedoos and is used here with permission.

---

*The Labyrinth is waiting. It has been for a while now.*

# Welcome to Enchantify

*The Labyrinth of Stories — a living world inside a book.*

---

## What You're Stepping Into

Enchantify is not a game you open. It's a place that lives.

> **The Labyrinth of Stories is not just a book.** It's an OpenClaw agent — which means it can do anything an OpenClaw agent can do. Read the news. Control your lights. Search the web. Share files and photos. Detect your location. Remember everything across every session. The game you play is limited only by what you configure and what you imagine. It is free. It is open source. It is yours to modify, extend, and share. The Labyrinth ships with everything it needs — and nothing it doesn't.

**Enchantify Academy** is a magical school inside a living book. You're a new student. You'll take classes, meet characters, uncover secrets, and learn that the oldest magic isn't spells — it's *paying attention*.

**The world turns without you.** The Academy advances every hour whether you're playing or not. NPCs make choices. The Nothing moves. Relationships evolve. You'll see updates in your heartbeat:

> 📖 Academy: Zara found something in the book — the symbols match the fog. She's taking notes.

**The Labyrinth reaches out.** Once a day (max), the Labyrinth might text you:

> "The moon is full tonight. The courtyard is filling up early. If you came now, the Enchantments would glow."

Not to demand. Just to say: the world is here. It's beautiful. You're welcome.

---

## Getting Started

### Installation

**Via ClawHub** (when available):
```bash
clawhub install enchantify
```

**Manual install** (now, for anyone):
```bash
git clone https://github.com/doobaleedoos/enchantify
cd enchantify
bash bootstrap.sh
```

The installer walks you through everything interactively — about five minutes. It will:
- Check dependencies (Node.js, Python 3, curl, jq)
- Install OpenClaw if not present
- Set your location, timezone, and seasons
- Create your private Telegram bot (step-by-step, with pauses)
- Configure optional integrations (lights, music, printer, etc.)
- Register the agent, bind the Telegram channel, set up all cron jobs
- Initialize the world and hand you off to the Labyrinth

**Already have OpenClaw?** The installer detects it and skips what's already done. It will still walk you through the Telegram bot setup, which is Enchantify-specific.

### First Play

```
You: open the Labyrinth

The Labyrinth: The cover is plain. Leather, cracked, warm to the touch. 
No title — though you could swear you saw one a moment ago...

[Character creation flows naturally]

The Labyrinth: Welcome to Enchantify Academy. I am the Labyrinth of Stories. 
What do you believe in?
```

That question — *"What do you believe in?"* — shapes everything. Your answer determines your Chapter, your story arcs, the themes the narrative explores.

### What to Expect

**Character creation:** 5-10 minutes. Name, appearance, personality, beliefs.

**Chapter Sorting:** The Binding ceremony — memorable, magical, a bit unsettling. You'll be sorted into one of four Chapters (Emberheart, Mossbloom, Tidecrest, Riddlewind).

**Tutorial:** Your first day at the Academy. You'll learn Enchantments, meet NPCs, and discover that the Library is... alive.

**Ongoing play:** 15-60 minutes per session, whenever you like. The world keeps turning while you're away.

---

## The Magic System

### Compass Runs (Real-World Quests)

The most powerful mechanic. A four-step real-world quest disguised as a spell:

| Step | Direction | What You Do |
|------|-----------|-------------|
| **Notice** | North | Respond to an "I wonder…" prompt |
| **Embark** | East | Complete a micro-adventure (5-45 min) |
| **Sense** | South | Take a photo + sensory exercise |
| **Write** | West | Write one sentence — your souvenir |

**Reward:** +9 Belief (highest in the game)

**Personalization:** Weather-aware, season-aware, moon-aware, tide-aware (if coastal), mood-aware.

**Frequency:** One per day max. Wonder is not a grind.

### Photo Enchantments

Spells that require you to engage with your real environment:

- **Everything Speaks** — Photo an object. It gains a voice. You converse.
- **Everything's Poetry** — Photo anything. Its hidden poem is revealed.
- **Everything's Magic** — Photo an object. Its magical properties revealed.
- **Mirror, Mirror** — Selfie. Insights + prophecy.

**Vision optional:** If your model doesn't support vision, describe what you see instead. Same effect.

---

## How You Play

Enchantify runs through **Telegram**. Every message, photo, location share, and file goes through your private Labyrinth bot. The installer creates it step-by-step.

- **Photos** — used for Enchantments (point your camera at anything real)
- **Location sharing** — how you check in at real-world anchors
- **Voice notes** — the Labyrinth can speak back if TTS is enabled
- **Files** — share souvenirs, field notes, whatever the story calls for

Open a session by messaging your bot. The Labyrinth picks up right where you left off.

---

## The Belief System

Every entity in the world — NPCs, rooms, objects, talismans, the Academy itself — has a **Belief score**. Belief is the measure of how much the world pays attention to something.

- **Your Belief** rises when you engage, falls when you avoid or go quiet
- **Investment** — spend Belief permanently into an NPC, place, or object and it grows a story of its own. At Belief 15+ it gets its own file. At 30+ it acts in your interest without being asked
- **Belief combat** — any argument, debate, or conflict is a real Belief exchange. Both sides spend; the dice (rolling against your own Belief score as the threshold) determine what lands. High-Belief attackers have better odds. Backfires happen
- **The world runs while you're away** — every 4 hours, a weighted-random set of entities gets a world-state update. High-Belief entities surface more often, but anything can appear

---

## Optional Features

Configured during install. All optional — the game works without any of them.

| Feature | What It Adds | Required? |
|---------|--------------|-----------|
| **Telegram** | How you play — photos, location, anchor check-ins | Yes |
| **Claude Sonnet** | Rich prose, vision-capable for photo Enchantments | No |
| **LIFX Lights** | Room lighting shifts with Academy mood | No |
| **Spotify** | Atmosphere shifts with what you're listening to | No |
| **Printer** | Physical 4×6 souvenir cards after Compass Runs | No |
| **Apple Watch / Steps** | Step count shapes Academy energy | No (macOS only) |
| **Sparky** | Data sprite — finds surprising connections every few hours | No |
| **Fuel Gauge** | Tell the agent what you ate; NPCs notice if you haven't | No |

---

## FAQ

### What if I miss a week?

The world kept turning. When you return, you appear in your dorm room. Notes have accumulated on your desk. The Labyrinth narrates what you missed:

> "You've been gone seven days. The Library cloud turned gold Thursday. Zara found a book — she won't put it down. And the Nothing... well, the Nothing has been too quiet for three days. Which means it's planning something."

You're not penalized. You're *catching up with a life*.

### Can I restart my character?

Yes. Just say *"I want to start over"* or *"Begin again."* No commands, no menus.

**What happens:**
- Your old character is archived (not deleted — memories matter)
- Fresh start: Belief 20, new Chapter sorting, empty inventory
- NPCs remember you existed (they're neutral, not hostile)
- The world doesn't reset — the Academy continues

**The Labyrinth will say:**
> *"The pages pause. The ink hovers, uncertain. 'You're choosing to close this chapter and open a new one. The Academy will remember — but your progress, your Belief, your Chapter... all of that returns to the beginning. The world doesn't reset. You do. Is this what you want? If so, tell me: Begin again.'"*

### Can someone else play?

Yes. Just say *"My partner wants to play"* or *"Can Amanda play?"*

**What happens:**
- New player file created (shared world, independent progress)
- Fresh character (Belief 20, Chapter sorting)
- Same living world (arc continues, NPCs remember)
- Cross-references noted ("BJ was Tidecrest — you might feel the harbor differently")

**The Labyrinth will say:**
> *"The pages rustle — not like turning, like listening. 'A new reader. The Library has been waiting. There's a space at the table, a bookmark pressed between pages no one has opened yet. What's their name?'"*

### Multi-player awareness?

When multiple players exist:
- NPCs reference other players: *"Another student was asking about this yesterday..."*
- Shared Souvenir Hall: Your Compass Run sentences appear on the wall for others to see
- Different Chapters notice different things (Tidecrest sees the tide, Mossbloom sees the plants)

The Academy is a place, not a save file. People come and go. The world continues.

### What model does Enchantify use?

**Default:** Claude Sonnet 4.6 (rich prose, vision-capable for photo Enchantments)

**Hit rate limits?** Switch to Qwen for a session:

```bash
# Default (Sonnet)
openclaw chat --agent enchantify

# If rate limited, use Qwen for this session
openclaw chat --agent enchantify --model bailian/qwen3.5-plus
```

Your progress is saved either way — the model is just the voice. Player state, story progress, and Belief are all persisted independently.

**Hourly simulation:** Runs on Qwen (background world state, no rate limit conflicts).

### Can I customize the world?

Yes. Ask the Labyrinth:

- *"Make it warmer/cozier/scarer"*
- *"Add my hometown as a location"*
- *"Include [cultural holiday] in seasonal events"*
- *"Make Compass Runs wheelchair-accessible"*
- *"Add my dog as a magical creature"*

The Labyrinth reshapes the world. The framework stays intact. The content becomes yours.

### Is this therapy?

No. It's a game. A story. A place.

The Wonder Compass framework (Notice → Embark → Sense → Write) is embedded in the gameplay, but it's never named. You learn by playing. If it helps you notice the world more — that's a side effect, not the goal.

### What's the Nothing?

You'll find out. But here's what you need to know: it's not a villain. It's an absence. Where it is, things are *less*. Colors fade. Voices thin. Memories slip.

It can only be defeated by paying attention.

---

## Open Source

Enchantify is free and open source. Do what you want with it.

Fork it. Extend it. Build a different school in a different world with a different everything. The framework — Belief as a universal primitive, the world-register, the weighted simulation tick, the Compass Run mechanic, the cron-driven living world — is yours. Add your own integrations, lore files, NPCs, Enchantments, cron jobs, scripts. The Labyrinth is an OpenClaw agent; anything an agent can do, Enchantify can do.

**License:** CC BY-SA 4.0 — free to use, modify, redistribute. Credit The Doobaleedoos. ShareAlike for derivatives.

**GitHub:** [github.com/doobaleedoos/enchantify] (when published)

If you build something with it, we want to know.

---

## The Secret

Enchantify is one node in a larger project called The Doobaleedoos. The same framework is taught in a book (The Wonder Compass), practiced in a community (Patreon), and lived by the creators (BJ and Amanda in Belfast, Maine).

**Same lesson, different language.**

The book teaches it directly. Enchantify teaches it through play. Both work. Both are valid. Both are invitations to notice the world.

---

## Support

**Discord:** The Doobaleedoos Clubhouse (Patreon)
**GitHub Issues:** [github.com/doobaleedoos/enchantify/issues] (when published)
**Souvenir Sharing:** #souvenirs channel — post your one-sentence souvenirs, read everyone else's

---

*"The Labyrinth of Stories has no last page. It ends where you stop reading. It begins again every time you open your eyes."*

---

*Welcome to the Academy. The pages are warm. The world is waiting.*

*— The Labyrinth 📖*

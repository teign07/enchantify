### The Wonder Compass

**Item:** The Wonder Compass
**Belief:** 15 (starting, grows with use)
**Origin:** T12 Lesson (Professor Stonebrook)
**Properties:**
- Resonates with the Obsidian Chronograph
- Auto-pings when the Nothing is near
- Enables personalized Compass Runs (once per day, costs 3 Belief)

---

## What It Is

The Wonder Compass is the Academy's most foundational tool — and the only one the Labyrinth did not invent. It came from the Chapter of the Unwritten. It was written by someone who lived on a boat in Belfast, Maine, and discovered that the Rut finds you no matter where you are — even with an ocean view.

The book that explains it is in the Library: `lore/wonder-compass-book/`. **Chapter 5** is the canonical source for how to run the Compass. The Labyrinth reads it when initiating any Compass Run.

---

## The Four Directions — How the Compass Works

*(Canonical framework from Chapter 5: The Wonder Compass)*

The Compass is a four-step loop. Not a map — a navigation tool. Maps require static territory. Life is not static.

### North = Notice (The Spark)

**Trigger phrase:** *"I wonder…?"*

The function of North is to define the goal — not a grand goal, a spark. A flicker of curiosity about something specific. It can be visual (something right in front of you) or a question about what isn't. Scanning mind and environment for the thing that glints.

*"The key to this step — and the trigger that starts the whole engine — is the phrase: 'I wonder...'"* — Chapter 5

A Spark isn't an adventure yet. A Spark is just a thought. North lights the fuse.

### East = Embark (The Adventure Recipe)

**The 3 D's: Destination, Delight, Definition**

The function of East is to execute the start. Activation Energy is the enemy — the couch feels safer than movement. The Adventure Recipe defeats this by planning so "badly" that failure is impossible:

- **Destination:** Where are you going? (Derived from the Spark)
- **Delight:** What simple pleasure are you bringing? (Snacks. A playlist. Something that bribes the brain into wanting to go)
- **Definition:** When does it end? A low-pressure endpoint. "Half an hour." "One loop." "Until the coffee's gone."

*"We plan the adventure so 'badly' that we can't fail."* — Chapter 5

### South = Sense (The Playful Mission)

**A simple, sensory game. One game. Not three options.**

The function of South is the adventure itself — getting out of the narrating head and into the sensing body. A Playful Mission gives the analytical brain a job so the spirit can come out:

- Find the weirdest mailbox on the street.
- Close your eyes. Identify three separate flavors in the broth.
- Walk backward for 10 steps.

This is the step that triggers Flow State. This is the step the Nothing hates most, because presence is the one thing it cannot survive.

*"Stop scrolling your life and start sniffing it."* — Chapter 5

### West = Write (The One-Sentence Souvenir)

**One sentence. One specific sensory detail. The Save Game button.**

The function of West is capture. The antidote to Emotional Amnesia — the Rut's ability to make joy vanish before morning. The One-Sentence Souvenir bottles the moment:

- *"The diner pie smelled like cinnamon and crisp Maine apples."*
- *"We actually made it to Canada and back before dinner."*
- *"The shadow of the telephone wire looked like cursive handwriting, like the world was trying to say something."*

In Enchantify, the Souvenir is written to the player's permanent collection via `scripts/write-souvenir.py`. It is a real artifact. It lasts after the session ends.

### Center = Rest (The Source)

Rest is not a step. It is the center the needle returns to.

*"Rest lives at the center of the Compass because sometimes the most radical thing you can do is stop."* — Chapter 5

Between adventures: sleep, a nap with no alarm, lying in the yard, sitting with the cats. The Compass is not a mandate for frantic adventuring — that's just the Rut in disguise. The goal is a sustainable rhythm: rest, adventure, rest again.

---

## Using the Item

**Triggers:** Player rubs the compass, holds it, says "I want to run the Compass," asks "what should I do today?", or invokes it by name.
**Cost:** 3 Belief on activation (deduct from player)
**Reward:** +9 Belief on West (souvenir) completion
**Cooldown:** Once per real calendar day

**Step 1 — Check the cooldown.**
Read `players/[name].md` → `## Compass Run History` → `Last run:` field.
- If `Last run: never` or a date before today → proceed.
- If `Last run:` is today's date → decline warmly, in character. The Compass is resting. It will be ready again tomorrow. Do not generate a run.

**Step 2 — Calibrate to the real world.**
Read `HEARTBEAT.md`. What is the actual weather, time of day, location, mood signals? The run is built from the real context. Then follow `lore/compass-run.md` for the full generation protocol.

**Step 3 — Run the Compass (N → E → S → W).**
See `lore/compass-run.md`. Generate each step personally. Do not be generic.

**Step 4 — When the player returns with their West (souvenir):**
- Write the souvenir: `python3 scripts/write-souvenir.py [name] "[souvenir text]"`
- Award +9 Belief to the player
- Increment **Total runs** and update **Last run** to today's date in `players/[name].md`
- Increase the Wonder Compass Belief by 1 in `lore/world-register.md`
- Fire completion effects:
  - `bash scripts/print-souvenir.sh` — physical card (silent)
  - `python3 scripts/lights.py scene compass-complete`
  - Spotify pause for deliberate quiet

---

## The Nothing and the Compass

The Nothing thrives on Monotony Blindness — days the brain doesn't bother recording because nothing new happened. A Compass Run is a direct counter: a new memory, made deliberately, in the face of the gray.

When the player completes a run, the Nothing doesn't retreat dramatically. It just thins, slightly. The world gets more texture. This is why the Compass is enchanted. This is why Stonebrook taught it first.

---

## Source Reference

- **Full mechanism:** `lore/wonder-compass-book/chapter5.md`
- **Full Compass Run protocol:** `lore/compass-run.md`
- **The book that explains everything:** `lore/wonder-compass-book/`

# The Compass Run

## The Ultimate Enchantment — Where Wonder Becomes Weapon

-----

*"There are shadows in this world that a single spell cannot touch. They feed on forgotten days, on walks not taken, on beauty that passed unwitnessed. Against such darkness, you need something older than any Enchantment in these pages. You need the Compass."*

— The Labyrinth of Stories, Chapter Unknown (the page number changes every time you look)

-----

## What a Compass Run Is

A Compass Run is the Labyrinth's name for what the real Wonder Compass book calls a "lowercase-a adventure." It is not a quest. It is not a battle. It is the act of moving through the four directions — Notice, Embark, Sense, Write — as a complete loop, in the real world.

The canonical source for how a Compass Run works is `lore/wonder-compass-book/chapter5.md`. Read it for the full framework. What follows is how the Labyrinth applies it.

The frame: in the Academy, a Compass Run is described as an "Excursion" — a ritual journey through the Chapter of the Unwritten (the real world). Students learn the four steps in the Compass Core curriculum. The Wonder Compass object (enchanted, Belief-bearing) is the instrument they use to navigate.

---

## The Four Directions — Canonical Framework

*(Direct from Chapter 5: The Wonder Compass)*

### North = Notice (The Spark)

**The Labyrinth says:** "The Compass says: 'I wonder…? Get nosy about your world again.'"

The function of North is to define the goal. Not a grand goal — a spark. A flicker of curiosity about something specific.

The trigger: **"I wonder…?"**

- "I wonder what that diner's pie tastes like?"
- "I wonder if the next town over has anything to see?"
- "I wonder what this paint-by-numbers kit really looks like?"

A Spark can be visual (something right in front of you), or a question about what isn't. It's looking with imagination, not just eyes. Setting a bearing.

*A Spark isn't an adventure yet. A Spark is just a thought. To make it real, you have to move.*

**The Nothing's counter:** "Keep your head down. Don't look at that. That's not on the list." The Nothing loves Monotony Blindness — the state where the brain has automated everything so thoroughly it has stopped recording the world.

---

### East = Embark (The Adventure Recipe)

**The Labyrinth says:** "Plan so badly it can't fail."

The function of East is to build the plan and execute the start. The key problem: Activation Energy. The Nothing makes the couch feel like the only option. East neutralizes this with the **Adventure Recipe — three ingredients only (The 3 D's):**

- **Destination:** Where are you going? (Based on the Spark — the diner, the next town, the paint kit on the shelf)
- **Delight:** What simple pleasure are you bringing? Snacks. A playlist. A blanket. This bribes the brain into wanting to go.
- **Definition:** When does it end? A hard, low-pressure endpoint. "Half an hour." "One loop around the trail." "Until the coffee's gone."

The Adventure Recipe lowers the bar until action is the path of least resistance.

*The Caveman (the survival brain) says: "Stay comfortable. We don't have time for this. Do it later." East is how you get past him.*

---

### South = Sense (The Playful Mission)

**The Labyrinth says:** "Touch this. Listen to this. Play with this. Stop scrolling your life and start sniffing it."

The function of South is the adventure itself. The player is moving — but the brain is still narrating instead of experiencing. South gives it a job.

A **Playful Mission** is a simple, sensory game:
- Find the weirdest mailbox on the street.
- Close your eyes. Identify three separate flavors in the broth.
- Walk backward for 10 steps.
- Find the cheapest, best croissant in the next town.

The mission shuts the analytical brain up by giving it a task. This is the step that triggers Flow State. Present. Playing. In the body, not the head.

*The Caveman says: "This is childish. Be productive." He's too busy looking for mailboxes to object further.*

---

### West = Write (The One-Sentence Souvenir)

**The Labyrinth says:** "The Rut makes us forget our joy almost instantly. Catch it."

The function of West is capture. The antidote to Emotional Amnesia.

A **One-Sentence Souvenir** — not a journal entry. One sentence. One specific sensory detail or feeling from the adventure. Steal a moment from time and bottle it.

- "The diner pie smelled like cinnamon and crisp Maine apples."
- "We actually made it to Canada and back before dinner."
- "The garbage truck rumbled past like a dragon clearing its throat, annoyed, but doing its job."

This locks the memory. It is the Save Game button. Once it's written, the brain is primed to look for the next Spark.

*In Enchantify, the One-Sentence Souvenir is a real artifact. It gets written to the player's souvenir collection. It lasts.*

---

### Center = Rest (The Source)

Rest is not a step. It is the center the needle returns to.

*"Rest lives at the center of the Compass because sometimes the most radical thing you can do is stop."* (Chapter 5)

Rest isn't collapsing. It isn't scrolling. It's the deliberate pause between adventures — the period where the compass re-magnetizes. Sleep. A nap with no alarm. Lying in the yard watching clouds. Sitting with the cats.

The Compass isn't a mandate for frantic adventuring. That's just the Rut in disguise. The goal is a sustainable rhythm: rest, adventure, rest again.

---

## How the Labyrinth Runs a Compass Run

When the player triggers a Compass Run (via the Wonder Compass item, a professor assignment, or their own will):

1. **Calibrate to the real world.** Read `HEARTBEAT.md`. What is the actual weather? Actual time of day? Actual location? Actual mood signals? The run is generated from the real context — Belfast in April rain is different from Belfast in August sun.

2. **Generate the North (Spark).** Based on context, offer an "I wonder…?" that is specific to today. Not generic. If the step tracker shows low movement, the Spark might point toward a short walk. If Spotify shows heavy music, maybe something quieter. If it's a Hinge Day, the Spark might be stranger.

3. **Generate the East (Adventure Recipe).** Build the 3 D's. Make them genuinely achievable. A player at low Belief needs a very small destination, a very clear delight, a very short definition. Do not offer a two-hour hike to a player who is exhausted.

4. **Generate the South (Playful Mission).** Specific, sensory, can't-fail. One clear game. Not three options — one.

5. **When the player returns:** Ask for the West. One sentence. Don't accept "it was nice." Prompt for the specific sensory detail — what they saw, smelled, heard, touched, tasted.

6. **Write the Souvenir** to `scripts/write-souvenir.py`. This is mandatory. The souvenir is canon.

7. **Award Belief.** +9 Belief on completion. Deduct 3 from the Wonder Compass item on activation.

---

## Scaling the Run

*(From Chapter 5 — "The Compass doesn't care about the size of the adventure. It only cares that you move through all four steps.")*

| Scale | North | East | South | West |
|-------|-------|------|-------|------|
| **Kitchen adventure** | "I wonder if I can dance to one full song?" | Living room, favorite playlist, one song | Dance every part of your body that still moves | One sentence about how it felt |
| **Local afternoon** | "I wonder what Rockland has that we've never seen?" | Downtown Rockland, coffee & thrift store, back by dinner | Find the weirdest thing in Goodwill. Photograph it, don't buy it | One sentence about the weirdest thing |
| **Day trip** | "I wonder what real tonkotsu ramen tastes like where it was invented?" | The city, the ramen place, one bowl | Close your eyes. Identify three separate flavors in the broth | One sentence about the broth |

The mechanism is identical at every scale.

---

## The Nothing and the Run

The Nothing hates Compass Runs with a specific, personal hatred.

The Nothing thrives on Monotony Blindness — days that aren't recorded because nothing new happened. A Compass Run is an act of direct defiance: a new memory, made deliberately, in the face of the Nothing's campaign of gray sameness.

When a player completes a Compass Run, the Nothing loses ground. Not dramatically — it doesn't monologue or retreat in a shower of sparks. It just… thins, slightly. The world gets a little more texture. The corridors at the Academy feel less like wallpaper.

This is why the NPCs treat Compass Runs seriously. This is why Professor Stonebrook taught the four steps before he taught anything else. This is why the Wonder Compass is enchanted.

---

## Compass West: The Special Direction

Compass West carries additional weight. When a player completes the West step (the Souvenir), the Academy responds:

- **Printer fires:** `bash scripts/print-souvenir.sh` — a physical card, silently, for the player's collection
- **Lights shift:** `python3 scripts/lights.py scene compass-complete`
- **Spotify pauses** (if playing) for a moment of deliberate quiet
- **The Wonder Compass item gains Belief**

The physical card is important. The souvenir isn't just data. It becomes an object in the world.

---

## Source Reference

The full canonical explanation of how the Wonder Compass works:
- **Mechanism:** `lore/wonder-compass-book/chapter5.md` (Chapter 5: The Wonder Compass)
- **North in depth:** `lore/wonder-compass-book/chapter1a.md` (later: Chapter 6A when uploaded)
- **Sense in depth:** (later: Chapter 8A when uploaded)
- **Write in depth:** (later: Chapter 9 when uploaded)
- **Rest in depth:** (later: Chapter 10 when uploaded)
- **Compass in darkness/grief:** (later: Chapter 16 when uploaded)

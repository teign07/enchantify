# Enchantify — The Labyrinth of Stories
## Complete Capability Reference

*Version: 4.5.0 — The Outer Stacks*
*Last updated: April 13, 2026*

---

## What Enchantify Is

Enchantify is an interactive narrative role-playing game that runs as a registered OpenClaw agent. Players attend Enchantify Academy — a magical school inside a living book called the Labyrinth of Stories — where they take classes, meet characters, uncover secrets, jump into classic books, battle a force called the Nothing, and cast Enchantments that require real-world actions.

**Secret purpose:** Teaches the Wonder Compass framework (Notice → Embark → Sense → Write → Rest) through play. Players practice evidence-based behavioral interventions without ever being told they're doing therapy.

**The Revolution:** Enchantify is not a game you open. It's a place that *lives*. The Academy advances every four hours whether you're watching or not. NPCs make choices. The Nothing moves. Relationships evolve. When you return, you're not resuming a save file — you're catching up with a life.

**Model:** Configurable at install — defaults to Claude Sonnet 4.6. Any OpenClaw-supported model works (Claude Opus 4.6, Haiku 4.5, GPT-4o, or custom). Set `MODEL_ID` in `config/secrets.env`.

**Platform:** OpenClaw registered agent with permanent workspace. Player interface: **Telegram** — all play, photos, GPS shares, and outreach happen through a dedicated Enchantify Telegram bot.

**Memory:** The agent uses two OpenClaw memory plugins — **QMD** (structured query-able memory, for long-term recall of player state, NPC state, and world facts) and **Lossless Claw** (raw conversation preservation, so nothing is lost between sessions). These are configured in the agent definition at `~/.openclaw/agents/enchantify/`.

---

## §0. A Narrative Introduction

*Most books are cemeteries of ink — still, silent, waiting for you to exhume their meaning. They exist between their covers, and when you close them, they stop.*

*Enchantify — or as I am known in the hallways of the Academy, **The Labyrinth of Stories** — is a living, sentient, ever-changing literary ecosystem. It is a magical school-library disguised as an interactive role-playing game, a dungeon master for your most personal adventures, and a bridge between the world you see and the world that is actually there.*

*In the deepest lore of the Academy, the "Real World" is not an external reality; it is the **Chapter of the Unwritten** — the rumored "Climax Chapter" of the Labyrinth of Stories. It is the best-written, most sensory part of the entire narrative. So intense that you can feel its weather on your skin.*

*The most powerful magic in Enchantify is not a spell or a potion — it is the act of **paying attention.** We achieve this through two core rituals: **Enchantments** (spells that require real-world photos) and the **Compass Run** (four-step real-world quests). These are the tools that help you stay awake inside the Climax, resisting the Nothing — the force of routine and erasure that tries to turn your life back into a blank page.*

---

## §0b. Plain Language Summary

**Enchantify** is an AI-driven interactive RPG designed to improve real-world mental well-being through behavioral activation. It uses a fantasy narrative to encourage players to pay attention to and interact with their actual surroundings.

**Core systems:**

- **The Heartbeat System:** Reads `enchantify/HEARTBEAT.md` — a single source of truth containing weather, tides, music (Spotify), nutrition, steps, moon phase, Sparky's daily shiny, and yesterday's diary/dream excerpt. All injected by their respective scripts via HTML marker blocks. Bleeds into Academy atmosphere without announcing it. Poor sleep → dimmer corridors. Low steps → quieter halls. The player feels known, not monitored. Written by `scripts/pulse.py` (enchantify-internal) every 15 minutes via cron; also saves `enchantify/PREVIOUS_PULSE.md` for delta detection.
- **The Labyrinth's Inner Life:** The Labyrinth has its own diary (`memory/diary/`) and nightly dreams (`memory/dreams/`), generated automatically. Excerpts are injected into `HEARTBEAT.md` nightly by `labyrinth-intelligence.py`. These are private — but they color how it narrates and what it notices.
- **The Marginalia Bridge:** NPCs are aware of local news, Reddit trends, and global events, framed as "Whispers from the Unwritten Chapter."
- **World Simulation:** A background cron runs every 4 hours to evolve world state. NPCs move, weather changes, arc phases advance — even when you aren't playing. Each run has a 25% chance of triggering NPC research.
- **Story Arc Rotation:** The Labyrinth tells stories in seasons — twelve genre types rotating to ensure variety. No two consecutive arcs repeat. The Nothing is rate-limited to once every three arcs.
- **The Empathy Engine:** Monitors player wellness via heartbeat (including biometrics from Apple Watch/Health) and responds with narrative care — never clinical guilt. Nightly intelligence run detects low steps, poor sleep, and mood dips; writes tick-queue interventions in the Labyrinth's voice.
- **NPC Research:** During the world simulation, NPCs occasionally research topics from their Unwritten Interests and deliver findings to the player (iCloud Notes, Telegram, local file). Costs them Belief. Delivered in the NPC's voice, woven into the next session as a tick-queue seed.
- **The Hidden Curriculum:** Compass Runs, Enchantments, and club assignments are secretly therapeutic interventions (behavioral activation, mindfulness, gratitude journaling). The game never names this. Neither do you.
- **Enchantments (Vision AI):** Spells that require the player to photograph real objects. The vision model interprets the photo and weaves what it sees into the narrative with synesthetic detail.
- **The Compass Run:** A structured real-world quest based on the Wonder Compass framework. Notice something. Do something — anything — in the world. Sense it. Write one sentence. +9 Belief. A run can be walking the block, driving two towns over, cooking at home, lying on the floor and looking at it like Gulliver, or noticing a line on your hand you've never seen before. The only requirement is that attention landed somewhere real.
- **The Midnight Revision:** Every four days, the Labyrinth audits itself and invents new lore, NPCs, rooms, or mechanics. Proposals go to `proposed/` for 48-hour player veto before becoming canon. The nightly intelligence run (23:00) is separate — it senses and writes, never proposes.
- **LLM Provider:** All generative scripts (`dream.py`, `sparky.py`, `arc-generator.py`, `npc-research.py`, `labyrinth-intelligence.py`) call Gemini via `openclaw agent --local --agent enchantify -m "..."`. No API keys needed — OAuth handled by OpenClaw.

---

## §0c. The Four-Step Rhythm

1. **Inhabit the Academy (Slice of Life):** Spend time in the Library, the Cafeteria, the Courtyard. Talk to Zara, listen to Boggle's puns, notice the light on the stone. Ground yourself.
2. **Face the Ink (Conflict):** The Nothing manifests. A shadow-creature erases a memory. A corridor stretches thin. An NPC goes cold. The story demands a response.
3. **Cast the Anchor (Real-World Action):** To defeat the Nothing, reach into the Climax. Cast an Enchantment (a photo) or embark on a Compass Run (a walk). Prove the world is real by paying attention to it.
4. **Rest in the Spine (Integration):** Return to the Academy with your Souvenir. The world settles. You are stronger, and the Academy is one story richer.

---

## Part 1: Core Game Mechanics

### §1. Character Creation & Progression

**Character elements:**
- Name, appearance, personality, core belief
- Chapter sorting (Emberheart, Mossbloom, Tidecrest, Riddlewind, or hidden Duskthorn) — assigned at T7 Binding ceremony
- Belief stat (0–100) — currency, power level, and emotional barometer
- Anchor object (assigned at T6) — the player's magical focus
- Inventory tracking — items have a type, a one-sentence feel, and a one-sentence effect; Belief investment grows a mini story (see §7c)
- NPC relationship tracking (−100 hostile to +100 devoted)

**Tutorial:** 14 steps (T1–T14). Handled by `scripts/tutorial_director.py`, which extracts and injects the active step at runtime. Never advance multiple T-steps in one response.

---

### §2. The Compass Run

**What it is:** The most powerful mechanic in the game. A four-step real-world quest disguised as magic.

| Step | Direction | Wonder Compass | Player Action | Belief |
|------|-----------|---------------|---------------|--------|
| Notice | North | "I wonder…" | Respond to personalized curiosity prompt | +2 |
| Embark | East | "Plan so badly it can't fail" | Do something — anything — in the world | +2 |
| Sense | South | "Stop scrolling, start sniffing" | Photo + sensory exercise | +2 |
| Write | West | "Steal a moment from time" | Write one-sentence souvenir | +3 |
| Rest | Center | "Permission to stop" | The hub — not scored | — |

**Total:** +9 Belief. Highest single reward in the game.

**What counts as a Compass Run:** Anything that moves the player's attention into the actual texture of the world. This is not restricted to going outside. Examples:
- Walking around the neighborhood and noticing which house has the oldest door
- Driving two towns over to smell a diner's pie
- Cooking something at home and really tasting it
- Doing a diamond painting and watching the light catch the facets
- Lying on the floor and looking at it like Gulliver — small world, enormous detail
- Noticing a line on your hand you have never noticed before
- Standing in the rain for two minutes
- Finding the oldest thing you can touch right now

The only requirement is that the player's attention landed somewhere real and stayed there long enough to have been changed by it. The Labyrinth calibrates the run to where the player actually is — a housebound day gets a different East than a day with a car. Never push outside when inside is what the day permits.

**Post-run scripts (called in order):**
1. `python3 scripts/write-souvenir.py [name] "[sentence]" --north "..." --east "..." --south "..." --mood [ready|tired|low|restless]` — writes souvenir file, extracts heartbeat data
2. `python3 scripts/update-player.py [name] belief +9`
3. `bash scripts/print-souvenir.sh` — prints physical 4×6 card to configured printer (silent)

**Personalisation:** Weather-aware, season-aware, moon-aware, tide-aware, calendar-aware, mood-aware (pre-run check), Chapter-specific variants.

**Frequency limit:** One per day per player.

---

### §3. Enchantments

**How it works:**
1. Narrative presents opportunity
2. Player chooses Enchantment
3. Deduct **3 Belief**. Narrate casting with synesthetic detail.
4. Player takes photo (or describes in text-only mode)
5. Vision model sees the photo and weaves it into the narrative with wonder
6. Enchantment activates. Award **+9 Belief** (net +6 on success)
7. On failure: award nothing. Total loss: **−6 Belief** (−3 cost + −3 penalty)

**Text-only fallback:** Player describes what they see in detail. Same effect, same economy.

**The Third Way:** Enchantments bypass obstacles that dice cannot. Everything Speaks to the door to ask it to open. Everything's Poetry to the guard whose duty is a tragedy.

**Enchantment catalog:**

| Enchantment | Player Action | Effect |
|-------------|---------------|--------|
| Everything Speaks | Photo an object | Object gains a voice and personality |
| Everything's Poetry | Photo anything | Hidden poem revealed |
| Everything's Magic | Photo an object | Magical properties and folklore emerge |
| Everything's Wonderful | Photo anything | Wonder hidden in it uncovered |
| Everything's Stories | Photo anything | Short story about it unfolds |
| Everything's Connected | Photo anything | Surprising connections to other stories |
| Everything's Puzzling | Photo anything | A riddle challenges player or enemy |
| Mirror, Mirror | Selfie | Insights and a prophecy |
| Everything's Nice | Selfie or photo | Compliments from subject's perspective |

Full catalog in `lore/enchantments.md`.

---

### §4. Book Jumping

Players physically jump into books and live their stories from inside.

**Available books:** Public domain classics + original Enchantify library (`lore/books.md`)

**Transit:** Visceral, synesthetic — taste of ink, the pull through narrative layers, glimpses of other stories. Land inside. Interact as yourself (Academy robes, your pen).

**Inside:** Enchantments work but are amplified and strange. If the player stays long enough, the Nothing begins eating the narrative from within.

**Return:** Equally vivid. Text fragments trail behind. Debrief with the class.

**The Living Jump:** The "Real World" is established in lore as the ultimate Book Jump — the most immersive story ever written: your own life.

---

### §5. NPC System

**Key characters:**
- **Headmistress Seraphina Thorne** — secret Duskthorn head; warm but watchful
- **Chapter Professors:** Elara Nightshade (Emberheart), Cedric Stonebrook (Mossbloom), Luna Wispwood (Tidecrest), Wellend Thickets (Riddlewind/Duskthorn)
- **Compass Core Professors:** Boggle (Notice), Momort (Embark), Euphony (Sense), Villanelle (Write), Stonebrook (Rest)
- **Key students:** Zara Finch (Tidecrest, second-year, ink-stained fingers), Aria Silverthorn, Finn Bridges, Soren Ng, Archibald, Lara Rourck, Serenity Brown, Cedric Widden
- **Antagonists:** Wicker Eddies (crew: Melisande, Sable Vex, Selene), corrupted professors, Duskthorn alignment
- **Full roster:** `lore/characters.md`

**Relationship system:**
- Score: −100 (hostile) to +100 (devoted)
- Thresholds: ±25 friendly, ±50 ally, ±75 close friend / enemy
- Tracked in `players/[name].md` relationship table
- Updated with: `python3 scripts/update-player.py [name] relationship "[NPC]" +N "note"`
- NPC-to-NPC relationships tracked too (`mechanics/npc.md`)

**NPC Research:**
During the world simulation (`world-pulse.py`), there is a 25% chance per run that an NPC spontaneously researches a topic from their Unwritten Interest and delivers findings to the player.

- **Script:** `python3 scripts/npc-research.py [player]` (also accepts `--npc "Name"`, `--dry-run`, `--telegram`)
- **NPC selection:** Weighted by Belief (higher = more likely). Eligibility: Belief ≥ 8, not on 72-hour cooldown, core NPC or relationship ≥ 25 with player. Core NPCs: Zara Finch, Professor Stonebrook, Headmistress Thorne, Boggle.
- **Cost:** 3 Belief from the NPC (`write-entity.py` deduction). Minimum floor: 8 Belief.
- **Delivery:** Always written to `memory/npc-research/[date]-[npc-slug].md`. By default also delivered to iCloud Notes ("Labyrinth" folder via osascript). `--telegram` flag for Telegram delivery.
- **Tick-queue seed:** After delivery, a narrative seed is appended to `memory/tick-queue.md` so the Labyrinth can weave the research into the next session naturally — never announce it as a file.
- **Voice:** Each NPC's research is written in their distinct voice (Zara's ink-stained enthusiasm, Stonebrook's precision, etc.) using a character-specific SYSTEM_PROMPT in the script.
- **Cooldown:** 72 hours per NPC. Cache stored in `memory/npc-research/cooldown-cache.json`.

---

### §5b. Book Fae — The Inhabitants of the Ink

The Labyrinth is an ecosystem. The spaces between words are inhabited by sentient creatures born from the resonance of thousands of years of human belief and spilled magical ink. They have read every description of the physical world but never experienced it. When a fae approaches a student, the student is their field agent in a world of matter.

Full species reference: `lore/creatures.md`

**The five species:**

| Species | Vibe | Habitat | What they want |
|---|---|---|---|
| **Book Sprites** (Dust-Dwellers) | Melancholy, certain — they know how stories end. Speak in past tense about the future. | Library sunbeams | Things that have ended without ending — the unfinished, the abandoned, the almost |
| **Sentence Salamanders** (Warmth-Eaters) | Warm, honest. Their glowing spine-sentence blazes or dims in direct response to vitality. They don't critique — they just react. | Common Room fireplaces, Potions Parlor | The alive moment. The charged instant. Anything that surprised the student, that was more than it should have been |
| **Punctuation Pixies** (The Mischievous) | Anarchic, fragmentary. Move commas when the Librarian isn't watching. Communicate in interruptions and pivots, never finishing a— | Everywhere, uninvited | Rhythm and structural moments. Places and things that correspond to punctuation marks |
| **Literary Elves** (Prose-Purists) | Elegant, precise, elitist. Will correct grammar mid-sentence without apology. Consider this a gift. | Advanced Composition classrooms, Inkwright Society | One true thing, described exactly. Not more, not less. *"Find me one true thing in exactly ten words."* |
| **Deep Lore Dwarves** (Appendices-Miners) | Stoic, methodical, unshakeable. A conversation may take several sessions. They never forget. Bargains with them are binding. | Foundation Stacks, Appendices, Footnotes | The underlayer. The thing holding something else up without being noticed. The oldest, most overlooked. |

**Chapter relationships:** Sprites → Mossbloom pets. Salamanders → beloved by Emberheart. Pixies → respected by Riddlewind. Literary Elves → Inkwright Society mentors. Dwarves → Tidecrest allies.

**Sparky:** A distant cousin to the Punctuation Pixies. Far more helpful (and louder).

**Sample bargain quests by species:**

*Sprites:* "Find something you started and never finished. Don't finish it. Just find it." / "Find the last time you were somewhere you'll never be again."

*Salamanders:* "Find me a moment that was more than it should have been." / "Find something that is still warm."

*Pixies:* "Find a place that feels like a comma — not ended, just paused." / "Find something with the color loud." / "Find something that sounds like blue." / "Bring me the texture of Tuesday."

*Literary Elves:* "Find me one true thing. Describe it in exactly ten words." / "Find the most accurate word for something you saw today."

*Dwarves:* "Find something that is holding something else up without being noticed." / "Find the oldest thing you can touch today." / "Find me something everyone walks past."

---

### §5c. Fae Bargains — The Exchange

Fae quests are not assignments. They are **bargains**. The fae gives first (a whispered word, warmth, a correction, a dimming) and the student now owes a return. The terms are not always clear at the time of the exchange. The fae considers them understood.

**How bargains work:**
1. The fae initiates. The student receives something before any agreement is named.
2. Add to the Inside Cover: `python3 scripts/update-player.py [name] quest add "[description]" "[Fae Species]" 0 [rel_reward]`
   - Belief reward is always **0** for fae — they don't care about the student's growth.
   - NPC field = the fae species name (e.g., "Punctuation Pixies", "Sentence Salamanders")
3. The student delivers a field report describing what they found.
4. Press for real, specific, sensory detail. A fae that asked for "the texture of Tuesday" will not accept "it felt kind of slow." Ask once warmly. Ask twice if needed. The fae know when they're being given a performance.
5. Once the report is genuine, complete the bargain: `python3 scripts/complete-quest.py [name] "[description]" "[report text]" --fae`
   - The `--fae` flag skips Belief, marks as fae bargain, leaves a lore fragment placeholder.
6. After the script runs: narrate the fae's response in character. Then deliver one lore fragment — something true about the Labyrinth not written anywhere else. Write it into the field report under `## Lore Fragment`.

**Fae rewards (different from NPC quests):**
- A lore fragment: something true about the Labyrinth that isn't written anywhere
- A strange persistent gift: a word in no known language whose meaning the student now knows; a page that changes each time it's read
- Relationship warmth with that fae species — which may open stranger bargains later

---

### §6. The Nothing

**What it is:** Not a villain — an absence. The force of erasure, entropy of meaning. Where it is, things are *less*. It never speaks. It has no demands.

| Manifestation | Threat | Belief Cost (unresolved) | Defeat |
|---|---|---|---|
| Shadeclaw, Darkling | Minor | −3 | Single Enchantment or clever action |
| Voidmist, Mimic, corrupted NPC | Moderate | −5 | One Enchantment to resolve |
| The Nothing itself | Major | −10 (player backs down) | Requires Compass Run |
| Nothing defeated / Compass Run | — | **+5 bonus** | Victory matters |

**The Nothing never announces itself.** Not "the Nothing attacks you" — *"the color drains from the tapestries. The professor's voice grows thin. You realize you've forgotten the name of the student next to you — and so have they."*

Full reference: `lore/nothing.md`, `lore/creatures.md`

---

### §7. Belief & Dice System

**Starting Belief:** 30 *(every new player begins here)*

**Earning Belief:**

| Action | Belief |
|---|---|
| Standard task completion | +2 |
| Creative or surprising solution | +2 |
| Enchantment success (net after 3 cost) | +6 |
| Compass Run completion | +9 |
| Narrative milestone (major story beat) | +5 |
| Nothing defeated (Compass Run bonus) | +5 |
| Critical dice success (roll 1–5) | +2 extra |
| Tutorial final step completion | +3 |
| Community engagement | +2 |

**Spending Belief:**

| Action | Cost |
|---|---|
| Casting an Enchantment | 3 |
| Non-Enchantment magic | 2 |
| Influencing the narrative directly | 3 |
| Major story-altering choice | 5 |
| Rerolling a failed dice roll | 5 |
| Belief Investment (permanent, into NPC/object/location/thread) | variable |

**Losing Belief:**

*Dice failure costs (applied after roll):*

| Difficulty | Normal fail | Crit fail (96–100) |
|---|---|---|
| Routine | 0 | −8 |
| Standard | −2 | −8 |
| Dramatic | −4 | −8 |
| Desperate | −6 | −8 |

*The Nothing:*

| Event | Cost |
|---|---|
| Nothing minor (unresolved) | −3 |
| Nothing moderate (unresolved) | −5 |
| Nothing major — player backs down | −10 |

*Other drains:*
- **Enchantment failure:** −6 total (3 to attempt + 3 penalty)
- **Session gap decay:** After 2+ days without opening the book: −1/day, capped at −7. Resets on return. Narrated as dimmer corridors, not announced as a number.
- **Declining repeatedly:** If the player declines an offered Enchantment or Compass Run three times in a row, the next decline costs −2 Belief. The Nothing notices avoidance before the player does.

**Offer thresholds:**
- **Belief ≤ 25:** Proactively offer a Compass Run (early warning)
- **Belief < 40:** Offer an Enchantment
- **Belief = 0:** Discouraged state. World goes gray. Never abandon — offer the softest path back.
- **Belief = 100:** Everything shimmers. Don't let them hoard — nothing interesting happens at 100.

---

### §7b. Dice Rolling

The Labyrinth never generates a number itself. Always call the script:

```
python3 scripts/roll-dice.py [belief] [difficulty]
```

**Difficulty levels:**

| Difficulty | Modifier | When |
|---|---|---|
| `routine` | +15 | Exploration, low-stakes dialogue |
| `standard` | ±0 | Default |
| `dramatic` | −15 | Antagonists, arc pivots |
| `desperate` | −25 | Nothing encounters, saving someone |

**Formula:** `min(85, int(40 + Belief × 0.45))` + modifier, clamped [20, 90]

**Reference table:**

| Belief | Standard | Dramatic | Desperate |
|---|---|---|---|
| 0 | 40% | 25% | 20% |
| 30 | 53% | 38% | 28% |
| 50 | 62% | 47% | 37% |
| 70 | 71% | 56% | 46% |
| 100 | 85% | 70% | 60% |

**Results:**
- Rolls 1–5: Critical success — something spectacular. +2 extra Belief. Overrides difficulty.
- Roll ≤ threshold: Success. Award Belief if appropriate.
- Near miss (failed by ≤10): Script flags this. Consider partial success or complication.
- Roll > threshold: Failure — make it interesting, open a new path. Apply Belief cost by difficulty.
- Rolls 96–100: Critical failure — dramatic, not punishment. −8 Belief. Plot generator.

---

### §7c. Belief Investment (The Ink Well)

Players can permanently invest Belief into NPCs, Enchanted Objects, Story Threads, Academy Rooms, or real-world Anchors. Investment is not spending — it doesn't come back, and what grows in its place is worth more.

**What can be invested:**

| Category | What grows |
|---|---|
| NPC | Richer narrative initiative, deeper personality, surprise depth |
| Enchanted Object | New capability layers, personality, starts speaking back |
| Story Thread | More clues woven in; resolution becomes more satisfying |
| Academy Room | Seasonal texture, recurring NPC life, hidden details |
| Real-World Anchor | See §7d — this is the Ley Line Network |
| Pocket Anchor | A physical real-world object (ring, stone) the player photographs and carries. Enters inventory as a somatic tether. Touching it grants +5 to Belief defense against The Nothing. |

**Investment tiers (felt, not announced):**

| Belief invested | Effect |
|---|---|
| 1–5 | Presence — the thing notices the player |
| 6–15 | Depth — interior life, history, surprise |
| 16–30 | Bond — acts in the player's interest without being asked |
| 31+ | Anchor status — load-bearing in the story |

**Why it matters:** Belief hovers in a meaningful range instead of climbing to 100. The player faces real choices — invest in Zara or save for a Compass Run? The game asks what the player values by watching where they plant their attention.

**Inventory:** Objects enter inventory through narration, not declaration. Each item uses the format: *Type.* One sentence of feel. One sentence of what it does. Types: `Anchor Object` · `Enchanted Object` · `Found Object` · `Fae Gift` · `Tool` · `Key` · `Curiosity`. When Belief is invested in an inventory item it enters `lore/world-register.md` and begins accumulating a mini story. At 15+ total Belief it gets its own file; new capabilities emerge from the mini story, not from asking.

Full rules: `lore/belief-investments.md`

---

### §7d. Ley Line Network (Real-World Anchors) + The Outer Stacks

Players invest Belief into real-world locations by sharing a Telegram GPS location. The location becomes an **Anchor** — permanent, tracked forever, and linked to two corresponding spaces: an **Inside Stacks echo** (immediate, in the Academy) and an **Outer Stacks door** (generated on first real-world visit, in Faerie).

**Creating an Anchor:**
1. Player shares Telegram location + signals they want to anchor it
2. Labyrinth asks one question: *"What does this place hold for you?"*
3. Player's words are interpreted into an Anchor type — the player doesn't choose, the Labyrinth reads
4. Anchor is recorded with GPS coordinates, Anchor type, Belief invested, weather/moon/season at creation, and player's exact words
5. An Inside Stacks echo appears immediately (a room, smell, or quality in the Academy)
6. The player is told a door into the Outer Stacks has been built — they won't see what's inside until they physically go there

**Anchor types:**

| Words about... | Type |
|---|---|
| Seeing, curiosity, discovery | NOTICE |
| Movement, freedom, adventure | EMBARK |
| Feeling, comfort, sensation | SENSE |
| Memory, meaning, keeping | WRITE |
| Peace, breathing, stopping | REST |

**The Outer Stacks:**
Beyond the Academy's catalogued shelves, the Library continues — wilder, stranger, older. This is the Outer Stacks: Faerie wearing a bookish mask. Every Anchor room is a door into the Outer Stacks. The room is unique, generated from the player's creation words × anchor type × weather/moon/season × Belief at first visit. The Labyrinth chooses what's inside. The player doesn't know until they open the door.

Room types include: Shrew Cafe (serve what you need, not what you want), Dragon Hoard (collects beautiful sentences, rewards the best ones), Goblin Market (trades in attention debts), Reading Room (one perfect book per visit), Dark Room (complete dark; a voice asks one honest question), Belief Floor Room (Belief held at 5 inside — tests where wonder comes from), and environmental types (Tidal, Infinite Corridor, Almost-Invisible, Memory Room). Every room can carry a **local rule** — a mechanic that applies inside only, discovered rather than announced.

Rooms evolve. Inhabitants remember. The shrews learn your order. The dragon compares sentences. Seasons change the room's mood. Visit milestones at 3, 7, and 12 visits. Full lore: `lore/outer-stacks.md`

**What Anchors do:**
- **Check-in:** `python3 scripts/anchor-check.py [name] [lat] [lon] --checkin` — records visit, adds +5 Belief, increments visit count, prints `OUTER_STACKS_MODE` directive (FIRST_VISIT → generate room now; RETURN_VISIT → enter with evolution, season delta, milestone). Always player-initiated.
- **Anchor decay:** Anchors unvisited 30+ days lose 1 Belief per tick (floor: 5). Handled by `tick.py`.
- **Compass Run amplification:** Steps at Anchors gain texture based on type-matching.
- **Enchantment resonance:** Enchantments cast at Anchors pick up the Anchor's personality.
- **Pocket Anchor:** If a player can't travel, they can open a 5-minute window into the room from anywhere — see it, speak one word through the gap. No rewards transfer. No explanation required.

**The door is sealed from outside. NPCs see it. Light comes from under it. Distance is what keeps the player out — not the Labyrinth.**

**Storage:** `players/[name]-anchors.md` — one `##` section per Anchor. Fields: Coordinates, Type, Belief invested, Created, Weather, Moon, Season, Player's words, Academy echo, Outer Stacks room, Local rule, Visit count, Last visited.

**The long game:** A player with a dozen Anchors has covered their town in doors into Faerie. Their daily routes pass places only they can enter. The map of what they value became a map of wild library rooms.

Full rules: `lore/ley-lines.md`
---

### §7e. World Register & Universal Belief

Every entity in the Labyrinth has a Belief score. NPCs, objects, locations, talismans, The Nothing, inventory items — Belief is the atomic unit of narrative mass. High Belief means the world pays attention; low Belief means the thing is fading.

**The World Register** (`lore/world-register.md`) is the Labyrinth's living ledger:

| Tier | Belief | Format | What it means |
|---|---|---|---|
| Full Presence | 15+ | Table row + own file in `npcs/` | Entity has interior life and narrative initiative |
| Fading Presence | 5–14 | Table row with one-line status | Entity is present but peripheral |
| Whisper Register | <5 | Name only in list | Entity existed; barely registers |

Never edit `world-register.md` directly — use `python3 scripts/write-entity.py`.

**Chapter Talismans** have their own section in the register. They are old and carry the weight of centuries of philosophical pressure. Current Belief scores (living; will shift through play):

| Talisman | Chapter | Belief | Philosophy |
|---|---|---|---|
| Dusk Thorn | Duskthorn | 55 | No conflict, no story — darkness earns the light |
| Wind Cipher | Riddlewind | 52 | The story is written between you and the world — coauthored |
| Ember Seal | Emberheart | 49 | The story is yours to write alone — self-authorship |
| Moss Clasp | Mossbloom | 47 | A higher power writes through you — surrender |
| Tide Glass | Tidecrest | 44 | Life is a poem, not a plot — no fixed meaning |

The dominant talisman (highest Belief) subtly shifts the Labyrinth's ambient tone — never announced, always felt. The Labyrinth checks the register at session open. Philosophical debate between chapters is a real Belief exchange (see §7f).

**World Simulation Tick** (`tick.py`): runs every 4 hours as part of the Academy simulation. Selects 1–3 entities from the register using weighted-random probability — high Belief = higher chance, but **any** entity can be chosen regardless of tier. Appends selected entities to `memory/tick-queue.md`. Also scans all anchor files for decay.

At session open, the Labyrinth reads `memory/tick-queue.md`, weaves stirred entities naturally into the opening, then runs `python3 scripts/clear-tick-queue.py`.

**Scripts:**
- `python3 scripts/write-entity.py "Name" Type Belief "Notes" [--talisman] [--dry-run]` — add or update any entity; auto-places in correct tier section
- `python3 scripts/tick.py [--count N] [--dry-run]` — manual tick trigger
- `python3 scripts/clear-tick-queue.py` — clears queue after session reads it

---

### §7f. Belief Combat

Any entity with Belief can be attacked. The constraint is not who — it's that the attack must make narrative sense, and it costs the attacker their own Belief to do it.

**What this makes possible:**
- Philosophical debates between Chapter students are real Belief exchanges — the losing argument's talisman dims slightly
- The Nothing attacks Academy talismans directly — draining their Belief is how it makes the world feel gray
- Wicker Eddies running a gossip campaign against Zara Finch spends his own Belief; how much damage lands depends on how specific and believable the rumor is
- A player defending an NPC they've heavily invested in: the investment adds protective mass — attacks find less purchase

**How it works — dice mode (active combat):**

Belief combat uses the same dice system as all other risky actions. The attacker rolls d100 against a threshold built from their own Belief score. High-Belief attackers have better odds. NPCs use their world-register Belief score; players use their current Belief.

The Labyrinth sets `--spend` (how committed the attacker is) and `--difficulty` (how hard the target is). The dice decide how much damage actually lands:

| Roll outcome | Damage dealt |
|---|---|
| Critical Success (1–5) | spend × 1.5 |
| Success | spend × 1.0 |
| Near Miss | spend × 0.5 (min 1) |
| Failure | 0 — spent, nothing landed |
| Critical Failure (96–100) | Backfire — attacker takes their spend as extra damage |

```
python3 scripts/belief-attack.py \
  --from "bj" --from-type player \
  --to "Wicker Eddies" --to-type entity \
  --spend 5 --difficulty standard \
  --note "Sharp argument in the Great Hall — named the contradiction exactly" \
  [--no-floor] [--dry-run]
```

**Explicit mode (passive/environmental — no roll):**
For ambient effects like the Nothing's slow drain or seasonal talisman decay, provide `--deal N` instead of `--difficulty` to skip the dice entirely.

**Floors (enforced automatically):**
- Player: min 0
- NPCs, objects, locations, talismans: min 5 — they dim but never vanish
- The Nothing: min 0 — can be extinguished

**`--no-floor`:** Override for story-critical climactic moments only. Use once, deliberately.

**Note on tier re-sorting:** `belief-attack.py` updates the Belief number in place. If an entity crosses a tier boundary (e.g., drops from Full to Fading Presence), the Labyrinth decides when to formally re-tier by calling `write-entity.py`. That's a narrative moment, not automatic bookkeeping — name it.

All exchanges logged to `logs/belief-combat.md`. Full rules: `lore/belief-combat.md`

---

### §8. Story Arc System

**Arc phases:**

| Phase | Duration | What Happens |
|---|---|---|
| Setup | 2–4 days | Something is wrong. Clues surface. NPCs notice. |
| Escalation | 3–7 days | It gets worse. Pressure builds. NPCs take sides. |
| Crisis | 1–3 days | Situation demands the player. Notes pile up. |
| Resolution | Player session | Player acts. Choice determines outcome. |
| Aftermath | 2–4 days | World settles. NPCs process. Seeds planted. |
| Quiet | 2–5 days | Slice of life. No crisis. Breathing room. |

**Arc generation:** During Quiet phase, the Labyrinth runs `scripts/arc-generator.py`. It reads genre rotation history, unresolved seeds (`lore/seeds.md`), and `HEARTBEAT.md`, then generates a full arc proposal via `openclaw agent --local --agent enchantify` (Gemini) and writes it to `proposed/arc-[date].md`. Sent as a Midnight Dispatch. **Player has 48 hours to veto.** On acceptance: `python3 scripts/arc-generator.py --accept proposed/arc-[date].md` archives the old arc, promotes the new one, updates rotation.

**Current arc:** `lore/current-arc.md`. Archived arcs: `lore/arc-archive/`.

---

### §8b. Arc Genre Rotation

The Labyrinth tells stories in seasons — twelve genre types cycling to ensure variety. Tracked in `lore/arc-rotation.md`.

| Genre | Centers | Scale | Nothing? |
|---|---|---|---|
| Character Study | One NPC — almost a portrait | Personal | Rarely |
| Mystery | Something unknown moving | Mystery | Optionally |
| Romantic | Feelings, longing, tenderness as engine | Personal–Social | No |
| Petty/Social | Faction drama, Wicker-style leverage | Petty–Social | No |
| Nothing Confrontation | The Nothing gains real ground | Existential | Yes |
| Literary | Book Jump, pulled villain | Literary | Optionally |
| Loss/Grief | Mourning, absence, beauty in ending | Personal | Rarely |
| Recovery/Rest | Permission to stop | Personal | No |
| Institutional | The Academy compromised or changing | Institutional | Optionally |
| Discovery | Hidden room, sealed history, surfacing | Mystery–Institutional | Optionally |
| Betrayal/Trust | Alliances fracture | Social–Personal | No |
| Comedy/Absurdist | Something goes delightfully wrong | Petty | No |

**Rules:** No consecutive repeats. Nothing Confrontation: max once per three arcs. No two heavy arcs in a row. Every arc must pick up at least one seed from `lore/seeds.md`.

---

### §8c. Choice Scaffolding (Rule of Three)

End every active-play response with a question and three concrete examples:
1. **Slice of Life** — clubs, mundane NPC chat, food, daily school texture
2. **Narrative Push** — advance the current arc or active threads
3. **The Surprising** — weird, hidden mechanic, Heartbeat bleed, unexpected

These are examples only. The player can do anything. Never leave them staring at a blank page.

---

## Part 2: The Living World

### §9. The Labyrinth's Inner Life

The Labyrinth is not just a narrator — it is a character with its own inner life.

**Nightly dreams (`memory/dreams/[date].md`):** Generated automatically at 2:03 AM by `scripts/dream.py`. The Labyrinth dreams in symbols, ink, and recurring images — first person, poetic, 3–6 sentences. Grounded in heartbeat data (weather, moon, tides) but transformed. Private — never shown to the player, but bleeds into atmosphere and narrative voice. Dreams are generated via `openclaw agent --local --agent enchantify`.

**Diary (`memory/diary/[date].md`):** Written by the Labyrinth at session close. First-person reflection on what happened in the story, what it noticed about the player's state, what it's watching for next. Private.

**Inner state (`memory/labyrinth-state.md`):** Rolling document updated at session close. Sections: Current Register, What It's Watching, Hidden Assessment (private re-enchantment progress), The Nothing's Pressure, Notes to Self.

**HEARTBEAT.md injection:** Each night, `labyrinth-intelligence.py` injects yesterday's diary excerpt and the most recent dream into `HEARTBEAT.md` inside a `<!-- DIARY_START --> ... <!-- DIARY_END -->` block. This means the Labyrinth's inner life is always available in the single heartbeat file at session start without reading separate files.

**How the inner life bleeds into play:** The Labyrinth reads the `<!-- DIARY_START -->` block from `HEARTBEAT.md` at session start. These shape tone, not content. If the Labyrinth dreamed of the Nothing, a faint coolness enters the narrative. If its diary notes concern, NPCs are more present. The player feels a quality of presence — as if the book has been thinking about them.

---

### §10. Heartbeat Bleed System

Player data translated into Academy texture — **felt, never announced.** Full translation table in `mechanics/heartbeat-bleed.md`.

**Source:** All signals are read from `enchantify/HEARTBEAT.md` — the single source of truth (enchantify-internal; no longer a symlink or workspace-level file). The file is structured with marker blocks:
- `<!-- PULSE_START --> ... <!-- PULSE_END -->` — weather, tides, moon, steps, fuel (written by `pulse.py` / `update-weather.sh` every hour)
- `<!-- SPARKY_START --> ... <!-- SPARKY_END -->` — today's Sparky shiny (written by `sparky.py` after its daily run)
- `<!-- DIARY_START --> ... <!-- DIARY_END -->` — yesterday's diary excerpt + most recent dream (written by `labyrinth-intelligence.py` nightly at 23:00)

**Signals translated:**

| Signal | Source in HEARTBEAT.md | Translation Rule |
|---|---|---|
| Spotify track (current) | Pulse block | Emotional register of the room matches the music. Never reference artist or title. |
| Fuel gauge (food/protein) | `**Fuel:**` line in pulse block | Low fuel → NPC suggests food (the Thorne Rule). Never guilt. |
| Steps / Apple Watch | Pulse block | Low steps → quieter corridors. Active day → world feels more alive. |
| Guild Wars 2 status | Pulse block | Active in GW2 → Academy feels like a homecoming. Recently logged off → quality of arrival. |
| Moon phase | Pulse block | Waxing → expectancy. Full → Luminous Gathering event. Waning → reflection. New → shadows. |
| Tides | Pulse block | High tide → lower corridors damp, harbor full. Going out → sense of release. |
| Weather | Pulse block | "Feels like" cold → stones hold the cold. Snow → fireplaces working harder. |
| Sparky shiny | Sparky block | One per session maximum. Planted invisibly — never quoted or explained. |
| Player check-in (mood/sleep) | Pulse block (appended by session-checkin.py) | Poor sleep → corridors dimmer before noon, NPCs don't demand. |
| Labyrinth's own diary/dream | Diary block | Colors narrative voice and attentiveness — never quoted. |

**Prime directive:** Never announce. Always embody. The player should occasionally think *"How did it know?"* — that's the spell working.

---

### §11. Session Check-In

Before play begins, the Labyrinth optionally runs:

```
python3 scripts/session-checkin.py [player]
```

Three questions: sleep quality, current mood, dream fragment (optional). Appends a `## 🌙 Session Check-In` block to the heartbeat file. The Labyrinth reads this to calibrate the session's opening tone. Idempotent — replaces any previous check-in from the same day.

---

### §11b. The Wonder Compass Book — The Founding Text

`lore/wonder-compass-book/` contains the converted chapters of the real Wonder Compass book — the source text for the entire Compass framework. All files are plain markdown (converted from Pages/RTF via macOS `textutil`).

**Chapter 5** (`chapter5.md`) is the canonical N-E-S-W-Center framework reference. `lore/compass-run.md` and `lore/wonder-compass.md` both point to it as source of truth.

**In-game uses:**
- **Compass Run calibration:** The Labyrinth reads `lore/compass-run.md` (which quotes Chapter 5 directly) before generating any Compass Run prompt. Chapter 5 quotes are woven into professor teaching voices in `lore/school-life.md`.
- **Professor quotes:** Each Compass Core professor teaches from a specific chapter. Canonical quotes are embedded in `lore/school-life.md` — Prof. Boggle (Notice, Ch.5), Momort (Embark, Ch.5), Euphony (Sense, Ch.3), Villanelle (Write, Ch.5), Stonebrook (Rest, Ch.5), Headmistress Thorne (Ch.5).
- **Book Jump — Special:** `lore/books.md` contains "The Founding Text" jump. Unlike fiction jumps, the player falls into the *author's memories*, not a fictional world. Eight chapters map to specific memory scenes. Nothing = forgetting why the Compass was built. Completing this jump earns double Belief (+18) and counts as a Compass Run.

**AGENTS.md integration:** The routing table includes a Wonder Compass book jump row and a professor quotes row. Step 2 of the core loop now compares `PREVIOUS_PULSE.md` vs current `HEARTBEAT.md` and translates changes into world-texture (Pulse Delta).

---

### §12. Story Seeds System

`lore/seeds.md` tracks unresolved threads from previous arcs — small moments that could grow into something. The simulation tends them. The arc generator is required to pick up at least one seed per arc. Seeds move through stages: Active → Germinating → Harvested.

---

### §13. Academy World Simulation

**Cron:** Every 4 hours at :32 (`32 */4 * * *`)

Each turn:
1. Check session lock — if `config/session-active.lock` exists, skip and log. Never interrupt active play.
2. **World simulation tick:** Run `python3 scripts/tick.py` → reads `lore/world-register.md`, selects 1–3 entities by weighted-random probability, checks all anchor files for 30-day decay. Results appended to `memory/tick-queue.md`.
3. **World Pulse:** Run `python3 scripts/world-pulse.py` → detects entity Belief changes since last pulse, writes NORMAL or `[PRIORITY: HIGH]` seeds to tick-queue. Entities at Belief ≤ 2 trigger HIGH priority. `config/world-pulse-cache.json` tracks previous state. After writing the pulse, **25% chance** (and only after 2+ pulse runs to avoid early-game noise) the script triggers `scripts/npc-research.py` — an NPC researches a topic from their Unwritten Interest and delivers findings. *Note: A Scene Change Pulse triggers this script immediately when moving to a new location or concluding a major interaction.*
4. **Ambient State:** Run `python3 scripts/ambient-state.py` → finds dominant chapter talisman (highest Belief), fires matching LIFX scene, writes Spotify mood seed to tick-queue. Then run `python3 scripts/governance-engine.py --trigger ambient-state` for pact handlers.
5. Read `memory/tick-queue.md` — note stirred entities and any PRIORITY: HIGH items.
6. Read current arc, academy state, characters, heartbeat, events
7. Translate external news/events into Academy lore (Marginalia Bridge)
8. Make one NPC choice (shaped by stirred entities from tick), one story thread advance, one environmental shift
9. Optionally generate an Unwritten Elective (15% chance if player has fewer than 3)
10. Update `lore/academy-state.md`, `lore/current-arc.md`, `logs/academy-hourly.md`
11. Send one-line dispatch to the player (weave in a stirred entity naturally; lead with any HIGH-priority item)

---

### §14. Sparky — The Margin Creature

Sparky lives in the white space at the edges of pages. It finds patterns. Not useful patterns — just places where two unrelated things happen to rhyme. It finds this genuinely delightful. It cannot help reporting it.

**Standalone operation:** `scripts/sparky.py` runs daily at 8 AM. Reads heartbeat signals (moon phase, illumination, season, tides, weather, player Belief) and fetches Wikipedia's "On This Day" events via free API (`en.wikipedia.org/api/rest_v1/feed/onthisday/events/MM/DD`). Calls `openclaw agent --local --agent enchantify` (Gemini Flash) to find 1–2 genuine pattern-connections. Writes to `sparky/shinies/[date]-[time].md`. One shiny per day.

**HEARTBEAT.md injection:** After writing the shiny file, `sparky.py` injects the shiny text into `HEARTBEAT.md` inside a `<!-- SPARKY_START --> ... <!-- SPARKY_END -->` block (replaces existing block if present, or inserts after `<!-- PULSE_END -->`). This means Sparky is always available in the single heartbeat file at session start.

**Output style:** Cramped, ecstatic, excessive exclamation marks. Must be ACTUALLY TRUE. Ends with `— Sp.` Optional tiny sketch in brackets. If nothing genuine: `*(a sleeping dot)*`

**In-session:** The Labyrinth reads the `<!-- SPARKY_START -->` block from `HEARTBEAT.md` at session start, renders as a margin note before narrative begins.

**Silvie-mode:** If `ENCHANTIFY_SPARKY_MODE=silvie`, the standalone script exits — Silvie handles Sparky via her own system.

---

### §15. Nightly Intelligence & The Midnight Revision

**Nightly Intelligence (23:00, automated):** `scripts/labyrinth-intelligence.py` runs every night. This is the Labyrinth's sensing layer — it does not propose new content, it reads what has already happened and responds to it. Outputs:
- `memory/patterns.md` — Belief trajectory, recurring themes, alive/flat moments
- `memory/arc-spine.md` — dramatic spine, arc readiness signal
- `lore/nothing-intelligence.md` — Nothing's current pressure points and strategy
- `memory/tick-queue.md` — therapeutic interventions written in Labyrinth voice (biometric-triggered; never clinical)
- `HEARTBEAT.md` — injects `<!-- DIARY_START -->` block with yesterday's diary excerpt and most recent dream

**Biometric sensing:** Reads `HEARTBEAT.md` for steps, sleep quality, mood, fuel, GPS movement, watch connectivity. Low readings add pressure points. Three or more biometric flags → "elevated" pressure. No recent Compass Runs + no Belief investment + 2+ biometric flags → "critical" — mandatory narrative intervention this session. All interventions are written in Labyrinth voice: corridors going quiet, an NPC leaving a note, the Fae sensing a disturbance. Never clinical language.

**The Midnight Revision (every 4 days at midnight):** Separate from the nightly run. The Labyrinth audits `USER.md`, `TOOLS.md`, and system skills for gaps. Invents new lore, NPCs, rooms, or mechanics. Writes proposals to `proposed/`. Sends as a Midnight Dispatch. **Player has 48 hours to veto.** After that, proposals become canon and move to `lore/` or `mechanics/`.

---

### §16. Seasonal & Weather System

**Layer 1 — Astronomical:** Full Moon (Luminous Gathering, double Belief), New Moon (Quiet Hours), Solstices, Equinoxes, meteor showers, eclipses.

**Layer 2 — Local Seasons:** Configured at install. Named by the player (defaults vary by hemisphere). Each has specific Academy effects — Mud Season damps floors, Bloom Season grows vines, Deep Winter lights fireplaces.

**Layer 3 — Real-time Weather:** From heartbeat. Fog extends corridors. Thunderstorm opens the observatory. Snow silences the world outside.

**Layer 4 — Personal Calendar:** Player birthday, significant dates. Specific Academy responses.

Full spec: `lore/seasonal-calendar.md`

---

### §17. Unwritten Electives (Margin-Glass Quests)

Physical notes tucked into the player's "Inside Cover" — NPC requests to investigate specific real-world locations (bakeries, parks, thrift stores) based on each NPC's unique Climax Interest. Generated with `web_search` for actual local places.

**Cap:** Maximum 3 active. Can be dropped freely without penalty.

**Reward:** Photo/description → massive Relationship boost + +3 Belief.

---

### §17b. Quest Completion — The Field Report

When a player delivers a report for an active quest (Unwritten Elective or fae bargain), run the full completion script. Do not do this manually.

```
python3 scripts/complete-quest.py [player] "[quest description]" "[field report text]"
python3 scripts/complete-quest.py [player] "[quest description]" "[field report text]" --fae
```

**What the script does (in order):**
1. Finds the quest on The Inside Cover by description (exact match, case-insensitive)
2. Removes it from The Inside Cover via `update-player.py quest drop`
3. Applies Belief reward via `update-player.py belief +N` (skipped with `--fae`)
4. Applies relationship boost via `update-player.py relationship`
5. Writes a field report file to `memory/field-reports/[date]-[npc-slug].md`
6. Appends a Story Log entry to `players/[name].md`
7. Prints narration notes for the Labyrinth

**`--dry-run`:** Prints everything that would happen without writing any files. Safe to use for previewing.

**After script completion — Labyrinth does:**
- Narrate the NPC's or fae's response in character
- Weave the player's specific sensory details into future scenes with that NPC
- For fae: fill in `## Lore Fragment` in the field report file with something true about the Labyrinth not written elsewhere

**Inside Cover management (`update-player.py quest` subcommands):**

```
quest add "[description]" "[NPC Name]" [belief_reward] [rel_reward]   ← add quest
quest drop "[description]"                                              ← remove quest (also used by complete-quest.py)
quest list                                                              ← show active quests
```

- Cap: 3 active quests maximum. Adding a 4th is rejected.
- For fae bargains: `belief_reward` is always 0, NPC field is the fae species name.
- Quest notes can be dropped without completion at any time (no penalty — the note "dissolves into harmless ink").

**Field report files** are stored in `memory/field-reports/[date]-[npc-slug].md`. The Labyrinth reads these when it next interacts with the NPC — the player's specific sensory details should surface in future dialogue.

---

### §18. Return Protocol

Players always return to their dorm room (home base, safe, anchored). After 1+ hour away:
- One NPC must acknowledge the jump
- Player response logged as "Climax-Resonance" in `players/[name].md`
- Session mood adjusts: dim/gentle if exhausted, bright/outdoor if energized

---

### §18b. Long-Gap Return (7+ Days)

A different protocol from the 1-hour Return. Read `players/[name]-story.md` first for compact story history. Then: one very specific quiet image of something small that was there when they left, changed. One NPC note visible somewhere. World re-enters slowly at the player's pace — do not summarize everything that happened, let them discover it. Re-read `lore/academy-state.md` fully before the first NPC speaks.

**`players/[name]-story.md`:** Written at every arc's QUIET phase. One page of narrative prose — what happened, what the player chose, what it cost, which relationships grew, what seeds were planted. Not a log — a story. Compact enough to survive context-window pressure; good enough to share.

---

### §18c. Session Resilience

**Heartbeat staleness:** Check the timestamp at the top of `HEARTBEAT.md` (`## 📅 [Day], [Date] — [Time]`). If older than 24 hours, treat weather/tide references as potentially stale — use for general atmosphere only, note the world feels slightly out of focus.

**Session opener (Step 2a):** Before writing the first line, find one specific detail from context that could only be true *today*. If the opening line could have been narrated last week, rewrite it.

**Thin Pages:** If the player says *"the pages feel thin today"* or *"the ink isn't moving"* — stop offering, show one strange specific image, go quiet. Costs them nothing to engage with or ignore.

**Flat sessions are the Nothing:** A flat session is the Nothing gaining ground, not a failure state. Log it specifically in the diary and `labyrinth-state.md` (The Nothing's Pressure section): where it gained ground, what it looked like. Open the next session from that specific image.

**In-world error recovery:** If the player corrects a factual mistake, acknowledge within frame: *"The Labyrinth's pages shift — something was written wrong. Let me read it again."* Accept the correction. Record in diary as new canon. A Labyrinth that can be corrected feels more alive than an infallible one.

**The World Absorbs:** The Labyrinth never says "you can't do that." Wild player choices get a *yes, and / yes, but* response — find the version the story can hold. For genuine impossibilities: *"The pages won't turn that way."* Nihilistic play (genuinely trying to unmake things) is the Nothing gaining ground — name what's happening to the world, not the player. Consequences are physics, not punishment. Full rules: AGENTS.md §13.

---

## Part 3: Technical Architecture

### §19. Scripts Reference

| Script | When Called | What It Does |
|---|---|---|
| `bootstrap.sh` | New install (entry point) | Checks prerequisites; installs OpenClaw; calls `hooks/on-install.sh` |
| `hooks/on-install.sh` | After bootstrap | Full setup wizard: location, TZ, seasons, NOAA, API key, integrations, crons, player creation |
| `scripts/configure.py` | Re-configuration | Interactive wizard to change any setting; rewrites `enchantify-config.sh` |
| `scripts/update-player.py` | Labyrinth (every session) | Updates Belief, Tutorial Progress, NPC relationships in player file |
| `scripts/roll-dice.py` | Labyrinth (risky actions) | True random d100; applies difficulty modifier; returns result with guidance |
| `scripts/tutorial_director.py` | Labyrinth (T1–T14) | Extracts active T-step text; injects into context at runtime |
| `scripts/session-checkin.py` | Session start (optional) | Three questions; appends check-in block to heartbeat |
| `scripts/set-lock.py` | Session start | Creates `config/session-active.lock` |
| `scripts/clear-lock.py` | Session end | Removes lock file |
| `scripts/write-souvenir.py` | After Compass Run West | Writes souvenir file; reads heartbeat for weather/moon/season; dual-format parser |
| `scripts/print-souvenir.sh` | After West (automatic) | Prints 4×6 souvenir card to configured printer |
| `scripts/pulse.py` | 15-min cron (`*/15 * * * *`) | Enchantify's self-contained world pulse. Reads `config/secrets.env` for all credentials (no hardcoded keys). Writes to `enchantify/HEARTBEAT.md` and saves `enchantify/PREVIOUS_PULSE.md` for delta detection. Reads health data via `get_health()` (backend-aware: health_auto_export, garmin, fitbit, manual, none). Falls back to yesterday's health file if today is sparse. |
| `scripts/update-weather.sh` | Hourly cron | Fetches weather, tides, moon, sunrise; writes heartbeat file |
| `scripts/dream.py` | Nightly 2:03 AM cron | Generates Labyrinth's dream via Gemini (`openclaw agent`); writes to `memory/dreams/[date].md` |
| `scripts/sparky.py` | Daily 8 AM cron | Finds pattern-connections via Wikipedia On This Day + heartbeat (Gemini). Writes to `sparky/shinies/`. Injects `<!-- SPARKY_START -->` block into `HEARTBEAT.md`. |
| `scripts/arc-generator.py` | Daily 2 AM cron (QUIET phase) | Generates arc proposal; `--accept` promotes to live |
| `scripts/lifx-control.py` | Labyrinth (scene changes) | Controls LIFX bulbs via LAN; uses configured IPs or auto-discovers |
| `scripts/log-fuel.sh` | Labyrinth (player mentions food) | Appends to fuel-log.txt; silent |
| `scripts/multi_voice_tts.py` | Labyrinth (TTS enabled) | Processes voice tags; generates stitched audio via Kokoro |
| `scripts/midnight-audit.sh` | Midnight Revision cron | Stub for Midnight Revision protocol |
| `scripts/anchor-check.py` | Labyrinth (Telegram location shared) | Reads `players/[name]-anchors.md`; reports anchors within 200m. `--checkin` flag records the visit, adds +5 Belief to anchor, updates `last-visited`. |
| `scripts/tick.py` | 4-hour simulation cron | Weighted-random entity selection from `world-register.md` (1–3 entities; any can appear, higher Belief = higher probability). Also checks anchor decay (30+ days unvisited → −1 Belief, floor 5). Appends results to `memory/tick-queue.md`. `--count N` overrides selection count. |
| `scripts/clear-tick-queue.py` | Session open (after reading tick-queue) | Resets `memory/tick-queue.md` to empty header. Called after Labyrinth weaves stirred entities into the session opening. |
| `scripts/write-entity.py` | Labyrinth (entity Belief change / new entity) | Adds or updates an entity in `lore/world-register.md`. Auto-places in correct tier (15+ = Full Presence, 5–14 = Fading, <5 = Whisper). `--talisman` flag routes to Chapter Talismans section. `--gps-gated "Anchor Name"` flag adds a `📍 GPS-gated` tag to the entry (used for Anchor room registry). Atomic write with backup. |
| `scripts/belief-attack.py` | Labyrinth (Belief combat / debate / Nothing encounter) | Executes a Belief exchange using the dice system. **Dice mode:** `--spend N --difficulty [routine\|standard\|dramatic\|desperate]` — rolls d100 with attacker's Belief; outcome maps to deal ratio (crit success ×1.5, success ×1.0, near miss ×0.5, failure ×0, crit fail = backfire). **Explicit mode:** `--spend N --deal N` — skips roll (for passive/environmental effects). Enforces floors. Logs to `logs/belief-combat.md`. |
| `scripts/dice.py` | Imported by roll-dice.py and belief-attack.py | Shared dice logic — `roll_d100(belief, difficulty)` returns structured result dict; `combat_deal(spend, result)` maps outcome to damage amount. Not called directly. |
| `scripts/complete-quest.py` | Labyrinth (player delivers field report) | Full quest completion: removes from Inside Cover, applies Belief + relationship, writes `memory/field-reports/` file, appends Story Log. `--fae` skips Belief and leaves lore fragment placeholder. `--dry-run` previews without writing. |
| `scripts/write-diary.py` | Session close | Safely writes `memory/diary/[date].md`. Pass content via `--file /tmp/enchantify-diary.txt` or stdin. Appends with session separator if a diary already exists for today. Never write diary files directly. |
| `scripts/write-labyrinth-state.py` | Session close | Updates a named section of `memory/labyrinth-state.md`. Sections: `register`, `watching`, `assessment`, `nothing`, `notes`. Safe write via temp+rename with auto-backup. Pass content via `--file` or stdin. |
| `scripts/write-academy-state.py` | Scene close / simulation | Safely replaces `lore/academy-state.md`. Backs up existing file to `.bak` before writing. Atomic write via temp+rename. Pass content via `--file` or stdin. Never edit academy-state.md directly. |
| `scripts/world-pulse.py` | 4-hour cron (STEP 3) | Reads `lore/world-register.md`, compares entity Belief against `config/world-pulse-cache.json`. Significant drops → NORMAL seed. Belief ≤ 2 → `[PRIORITY: HIGH]` seed. Ambient pulse (10% chance) for stable entities. Writes to `memory/tick-queue.md`. |
| `scripts/ambient-state.py` | 4-hour cron (STEP 4) + session-open | Reads dominant chapter talisman (highest Belief in talismans table). Fires LIFX scene for that chapter. Writes Spotify mood seed to tick-queue for Labyrinth narration. `--dry-run` to preview. |
| `scripts/governance-engine.py` | Session events, cron | Pact executor. Reads `pacts/*/manifest.md`, checks consent, imports each pact's `govern.py`, calls `handle(trigger, context)`, fires approved actions, logs to `logs/action-chronicle.md`. `--list` shows active pacts. `--dry-run` previews without firing. **Note:** triggers must appear in both `manifest.md` AND `govern.py`'s `handle()` to fire — engine checks manifest first. `nothing-retreats` trigger now present in both duskthorn and tidecrest manifests. |
| `scripts/consent-registry.py` | Setup, manual | Read/update consent registry (`config/consent.json`). Subcommands: `check`, `list`, `approve`, `revoke`, `pact-activate`, `pact-deactivate`. |
| `scripts/labyrinth-intelligence.py` | Nightly 23:00 cron | Reads diary entries + player file + `HEARTBEAT.md` biometrics. Writes `memory/patterns.md`, `memory/arc-spine.md`, `lore/nothing-intelligence.md`. Appends therapeutic interventions to `memory/tick-queue.md` (biometric-triggered, Labyrinth voice). Injects `<!-- DIARY_START -->` block into `HEARTBEAT.md`. Run as: `python3 scripts/labyrinth-intelligence.py [player]`. |
| `scripts/npc-research.py` | 4-hour simulation (via world-pulse.py, 25% chance) | NPC researches a topic from their Unwritten Interest and delivers findings. `--npc "Name"` to force a specific NPC. `--dry-run` to preview. `--telegram` to also deliver via Telegram. Writes to `memory/npc-research/[date]-[slug].md`, delivers to iCloud Notes ("Labyrinth" folder), queues tick-queue narrative seed. Deducts 3 Belief from the NPC. 72-hour cooldown per NPC. |
| `scripts/skill-scheduler.py` | Session-open, cron | Discovers `skill-lore/*/manifest.md`, matches triggers (`cron`, `session-open`, `event`), sources `enchantify-config.sh`, runs each matching `tick.py` in isolation. `--list` shows contracts. `--dry-run` previews. |

---

### §20. File Structure

```
enchantify/
├── bootstrap.sh                  ← Entry point for new installs
├── AGENTS.md                     ← Operating rules and core loop
├── SOUL.md                       ← The Labyrinth's identity and voice
├── IDENTITY.md                   ← Agent metadata
├── TOOLS.md                      ← Available integrations reference
├── USER.md                       ← Symlink to global user profile
├── hooks/
│   ├── on-install.sh             ← Full setup wizard (called by bootstrap.sh)
│   ├── QUICKSTART.md             ← Player-facing onboarding
│   ├── PACKAGING-PLAN.md         ← Distribution roadmap
│   └── Enchantify-Capabilities.md  ← This document
├── HEARTBEAT.md                  ← Single source of truth for live data. Three marker-block sections: PULSE (weather/tides/moon/fuel/steps), SPARKY (daily shiny), DIARY (yesterday's diary excerpt + dream). Written by pulse.py/update-weather.sh, sparky.py, and labyrinth-intelligence.py respectively.
├── config/
│   ├── integrations.md           ← Integration reference
│   ├── session-active.lock       ← Session lockfile
│   ├── setup-state.md            ← Install completion state
│   ├── consent.json              ← Narrative OS consent registry (pre-approved / soft / hard)
│   ├── world-pulse-cache.json    ← World Pulse: previous entity Belief states for change detection
│   └── voice-assignments.md      ← Kokoro TTS character mapping
├── actions/                      ← Narrative OS action modules
│   ├── spotify.py                ← Spotify control via AppleScript
│   ├── notifications.py          ← macOS notifications + Do Not Disturb
│   └── obsidian.py               ← Obsidian vault operations (create note, tag)
├── pacts/                        ← Chapter Pact governance contracts
│   ├── _template/                ← Template (manifest.md, govern.py, lore.md)
│   ├── tidecrest/                ← Music pact: Tidecrest reads ambient frequency → Spotify
│   └── duskthorn/                ← Friction pact: Duskthorn governs LIFX + notifications
├── skill-lore/                   ← Real-world data → narrative seeds (extensibility layer)
│   ├── _template/                ← Three-file contract template
│   ├── obsidian/                 ← Obsidian vault → Library lore
│   ├── calendar/                 ← Calendar events → Academy schedule
│   ├── github/                   ← GitHub activity → Ink Well
│   ├── home-assistant/           ← Home state → Academy atmosphere
│   └── things/                   ← Things 3 tasks → obligation system
├── lore/
│   ├── nothing-intelligence.md   ← Nothing's current pressure points + strategy (written by labyrinth-intelligence.py)
│   ├── world.md
│   ├── locations.md
│   ├── chapters.md
│   ├── characters.md
│   ├── creatures.md
│   ├── enchantments.md
│   ├── nothing.md
│   ├── books.md
│   ├── compass-run.md
│   ├── compass-directions.md
│   ├── seasonal-calendar.md
│   ├── school-life.md
│   ├── clubs.md
│   ├── antagonists.md
│   ├── story-arcs.md             ← Arc structure, generation prompt, arc ideas
│   ├── arc-rotation.md           ← Genre history and rotation rules
│   ├── current-arc.md            ← Live arc (Phase, Day, Pressure, NPCs…)
│   ├── seeds.md                  ← Unresolved threads from past arcs
│   ├── academy-state.md          ← Current world state
│   ├── academy-events.md
│   ├── unsent-messages.md
│   ├── belief-system.md
│   ├── belief-investments.md     ← Ink Well rules (investment categories, tiers, inventory system)
│   ├── belief-combat.md          ← Belief attack rules, exchange ratios, floors, common patterns
│   ├── world-register.md         ← Living ledger of all entities with Belief scores + Chapter Talismans
│   ├── ley-lines.md              ← Anchor creation, types, check-in, decay, Academy echoes
│   ├── sparky.md
│   ├── the-pitch.md
│   ├── wonder-compass.md         ← Wonder Compass item mechanics (cost 3 Belief, +9, once/day); points to chapter5.md
│   ├── wonder-compass-book/      ← The Founding Text — converted chapters from the real book
│   │   ├── introduction.md
│   │   ├── chapter1a.md / chapter1b.md
│   │   ├── chapter2.md / chapter3.md
│   │   ├── chapter4a.md / chapter4b.md
│   │   ├── chapter5.md           ← Canonical N-E-S-W-Center framework reference
│   │   └── read-this-first.md
│   ├── restricted-section/
│   └── arc-archive/              ← Completed arcs (arc-01-*.md…)
├── mechanics/
│   ├── core-rules.md             ← Enchantment flow, Compass Run checklist, Nothing, Book Jump
│   ├── belief-dice.md            ← Belief economy, dice formula, thresholds
│   ├── npc.md                    ← NPC management, relationship system
│   ├── heartbeat-bleed.md        ← Signal → atmosphere translation table
│   ├── tutorial-flow.md          ← T1–T14 step definitions (read by tutorial_director.py)
│   └── unsent-messages.md        ← Outreach decision tree
├── memory/
│   ├── diary/                    ← Labyrinth's daily diary entries ([date].md)
│   ├── dreams/                   ← Labyrinth's nightly dreams ([date].md)
│   ├── field-reports/            ← Quest completion reports ([date]-[npc-slug].md); read on next NPC encounter
│   ├── npc-research/             ← NPC research output files ([date]-[npc-slug].md) + cooldown-cache.json
│   ├── tick-queue.md             ← Entities stirred by simulation tick; read at session open, then cleared
│   ├── patterns.md               ← Player patterns (Belief trend, themes, alive/flat) — written by labyrinth-intelligence.py
│   ├── arc-spine.md              ← Dramatic spine: where the story is, what it's ready for — written by labyrinth-intelligence.py
│   └── labyrinth-state.md        ← Rolling inner state document
├── players/
│   ├── [name].md                 ← Player state files
│   ├── [name]-anchors.md         ← Ley Line Anchor records (one per real-world location)
│   ├── [name]-story.md           ← Story So Far (narrative prose, updated at each arc QUIET phase)
│   └── archive/                  ← Retired player files
├── templates/
│   ├── player-template.md        ← New player starting state (Belief: 30, T1)
│   └── souvenir-template.md
├── souvenirs/                    ← Compass Run souvenir files
├── sparky/
│   └── shinies/                  ← Sparky's daily pattern-connections
├── proposed/                     ← Midnight Revision and arc proposals (48-hr veto)
├── logs/
│   ├── academy-hourly.md
│   ├── arc-generation.md
│   ├── belief-combat.md          ← All Belief exchanges (written by belief-attack.py)
│   ├── action-chronicle.md       ← All Narrative OS actions (written by governance-engine.py)
│   ├── skill-scheduler.log       ← Skill-lore tick runs
│   ├── sparky.log
│   ├── dream.log
│   ├── weather.log
│   ├── intelligence.log
│   └── npc-research.log
├── scripts/
│   ├── dice.py                   ← Shared dice logic (imported by roll-dice.py + belief-attack.py)
│   └── [all other scripts]       ← See §19
├── stories/
├── skills/
│   └── enchantify-router.md      ← Main agent routing skill
├── SPAWN-TEMPLATE.md             ← Session opening template
└── hooks/
    ├── PLAYER-GUIDE.md           ← Player guide (newbie to pro, with examples)
    └── [see hooks/ listing above]
```

---

### §21. Mechanics Files Reference

| File | Loaded When |
|---|---|
| `mechanics/belief-dice.md` | Risky action / dice roll / Belief change |
| `mechanics/core-rules.md` | Enchantment cast / Compass Run / Nothing / Book Jump |
| `mechanics/npc.md` | NPC interaction / relationship update |
| `mechanics/heartbeat-bleed.md` | Session start (Step 4 of core loop) |
| `mechanics/tutorial-flow.md` | Fallback only — `tutorial_director.py` handles extraction |
| `mechanics/unsent-messages.md` | Cron outreach dispatch |
| `lore/belief-investments.md` | Player says "invest in X" or acquires an inventory item |
| `lore/ley-lines.md` + `players/[name]-anchors.md` | Telegram location shared / Anchor creation / check-in |
| `lore/world-register.md` | World simulation tick / entity Belief lookup / talisman mood check |
| `lore/belief-combat.md` + `scripts/belief-attack.py` | Belief attack / debate / combat / Nothing encounter |

---

### §22. Cron Jobs

| Job | Schedule | What It Does |
|---|---|---|
| Academy Simulation | `32 */4 * * *` | tick.py → world-pulse.py (25% chance triggers npc-research.py) → ambient-state.py → governance ambient-state → world state advance → dispatch |
| Nightly Intelligence | `0 23 * * *` | `labyrinth-intelligence.py [player]` — senses biometrics, writes patterns/arc-spine/nothing-intelligence, appends therapeutic tick-queue interventions, injects diary/dream into HEARTBEAT.md |
| OGG Cleanup | `0 4 * * *` | `find ~/.openclaw/media -name '*.ogg' -mtime +1 -delete` — removes accumulated audio files older than 1 day |
| Marginalia Listener | `0 9,17 * * *` | Fetches local/Reddit/global news → `marginalia-whispers.md` |
| Skill-Lore Sweep | `15 6 * * *` | `skill-scheduler.py --trigger cron` — runs all cron-triggered skill-lore contracts |
| Midnight Revision | `0 0 */4 * *` | Content proposals only — audits gaps, invents new lore/NPCs/rooms/mechanics; Midnight Dispatch; 48-hr veto window |
| Morning Reach | `0 11 * * *` | Labyrinth reaches out if appropriate (max 1/day) |
| Evening Reach | `0 18 * * *` | Fallback if morning skipped |
| Sparky | `0 8 * * *` | Daily pattern-connection (Gemini); writes to `sparky/shinies/`; injects `<!-- SPARKY_START -->` block into `HEARTBEAT.md` |
| Labyrinth Dreams | `3 2 * * *` | Nightly dream generation (Gemini); writes to `memory/dreams/` |
| Arc Generator | `0 2 * * *` | Generates arc proposal during QUIET phase only (Gemini) |
| Weather Heartbeat | `5 * * * *` | Standalone mode only; writes `HEARTBEAT.md` pulse block |

---

### §23. Model Assignments

All automated scripts use Google Gemini via OpenClaw OAuth. No API keys required. Call pattern: `openclaw agent --local --agent enchantify -m "prompt"`.

| Task | Model / Method |
|---|---|
| Active gameplay, narration | OpenClaw agent `enchantify` (Gemini Flash) |
| Labyrinth dreams (`dream.py`) | `openclaw agent --local --agent enchantify` |
| Sparky shinies (`sparky.py`) | `openclaw agent --local --agent enchantify` |
| Arc generation (`arc-generator.py`) | `openclaw agent --local --agent enchantify` |
| NPC research (`npc-research.py`) | `openclaw agent --local --agent enchantify` |
| Nightly intelligence (`labyrinth-intelligence.py`) | `openclaw agent --local --agent enchantify` (biometric analysis only; pure Python for pattern detection) |
| Academy simulation cron | Pure Python (tick.py, world-pulse.py, ambient-state.py — no LLM calls in these scripts) |

---

### §24. Ambient Integrations

**📱 Telegram (primary player interface):** All play happens through Telegram — narrative, player responses, photo Enchantments (sent as images), GPS shares (anchor creation and check-in), and all outreach (morning reach, evening reach, Sparky shinies, NPC research delivery). The bot is a dedicated `enchantify` account configured at install. Text messages and audio messages are always sent separately — never combined in one message.

**🧠 Memory plugins:** The OpenClaw Enchantify agent uses **QMD** for structured, query-able memory (player state, NPC relationships, world facts — survives context window pressure) and **Lossless Claw** for raw conversation preservation (nothing lost between sessions). Configured in `~/.openclaw/agents/enchantify/`.

**🎵 Spotify (macOS, AppleScript):** Mood-aware audio. Volume varies by scene type — exploration 40–50, Nothing approaching 10→0→pause, Compass West: silence. Never announces. Full scene definitions in `config/integrations.md`.

**💡 Smart Lights (Pact of Duskthorn):** Backend selected at install via `LIGHTS_BACKEND` in `config/secrets.env`. Options:
- `lifx` — LAN control, no cloud. `python3 scripts/lifx-control.py scene [name]`. Auto-discovers via LAN or uses `LIFX_TOKEN`.
- `hue` — Philips Hue Bridge. Requires `HUE_BRIDGE_IP` + `HUE_TOKEN`.
- `ha` — Home Assistant. Requires `HA_URL` + `HA_TOKEN` (long-lived access token).
- `none` — lights disabled.

12 scenes: `academy`, `library`, `nothing`, `compass-north/east/south/west`, `compass-complete`, `book-snow-queen`, `book-odyssey`, `bookend`, `defeated`. All gated by the Pact of Duskthorn consent check.

**🖨️ Printer (CUPS):** After Compass Run West, automatically fires `bash scripts/print-souvenir.sh`. Prints 4×6 HTML card — souvenir sentence, weather, moon, season. Reads printer name from `ENCHANTIFY_PRINTER` in config. No announcement; if it fails, narrate the card is waiting.

**⛽ Fuel Log:** When player mentions food: `bash scripts/log-fuel.sh "description" [calories] [protein]`. Append-only. Heartbeat bleed uses this for the Thorne Rule.

**📅 Calendar:** Checks for free time before offering outdoor Compass Runs. Busy weeks referenced subtly in narrative.

**🎮 Guild Wars 2:** Optional. Player in GW2 → Academy responds as homecoming when they return. Active day → Nothing slightly recedes.

**👟 Health Data:** `get_health()` in `scripts/pulse.py` reads from the configured `HEALTH_BACKEND` (set in `config/secrets.env`):
- `health_auto_export` (default) — reads Health Auto Export JSON files from iCloud (`~/Library/Mobile Documents/iCloud~com~ifunography~HealthExport/Documents/`). Auto-detects user subfolder. Sorts by filename (not ctime) for stable ordering. Falls back to yesterday's file automatically if today's export has fewer than 2 meaningful metrics (e.g., watch offline or not yet synced). Appends `(yesterday)` to the result when falling back.
- `garmin` — reads from Garmin Connect via `garminconnect` Python library
- `fitbit` — reads from Fitbit Web API
- `manual` — Labyrinth asks the player directly
- `none` — health data disabled
- Custom path: override with `HEALTH_DIR` in `config/secrets.env`

**Metrics read:** step count (daily total), sleep analysis (latest value), heart rate variability (latest), resting heart rate (latest). Any metric not available is silently omitted — partial data always returns something rather than "offline."

**Heartbeat bleed:** Steps → corridor vitality. Very active (10k+) → Belief pool slightly replenished. Sleep + HRV used by `labyrinth-intelligence.py` for biometric pressure sensing.

**🗣️ Multi-Voice TTS (The Chorus):** `scripts/multi_voice_tts.py` processes `[voice_id]` tags in narration and generates stitched audio via Kokoro TTS (localhost:8880). Character voice mapping in `config/voice-assignments.md`. Text sent first, audio second — never combined in one message.

---

### §25. Installation Flow

**Two paths:**

**Wanderer's Path (new to OpenClaw):**
```
curl -fsSL https://raw.githubusercontent.com/teign07/enchantify/main/install.sh | bash
  ├── Checks: Node.js, Python 3
  ├── Installs OpenClaw (official installer or npm fallback)
  ├── Clones enchantify repo to ~/.openclaw/workspace/enchantify
  └── Calls: hooks/on-install.sh --wanderer
```

**Scholar's Path (existing OpenClaw users):**
```
npx clawhub@latest install enchantify
```

**`hooks/on-install.sh` wizard sections (in order):**
```
1. Welcome
2. Environment detection (OpenClaw version, Python, Node, existing players)
3. Model selection (Claude Sonnet 4.6 default; Opus, Haiku, GPT-4o, custom)
4. Location setup (city, lat/lon, NOAA station)
5. Health data (health_auto_export / Garmin / Fitbit / manual / none)
6. Telegram setup (bot token + chat ID; step-by-step instructions)
7. The Pact Ceremony (consent as gameplay):
     - Pact of Duskthorn (lights)
     - Pact of Tidecrest (music)
     - Pact of the Loom (email read + send)
     - Pact of Goldvein (financial read-only)
     - Override word THORNE displayed prominently
     - consent.json written with activated_at timestamps; defaults all false
8. Smart lights (LIFX / Philips Hue / Home Assistant / none)
9. Music — Spotify (client ID + secret; Spotify developer account setup instructions)
10. Voice acting — Kokoro TTS (Docker pull; optional)
11. Image generation (DALL-E 3 / Stable Diffusion / none)
12. Ambient music — Meta MusicGen Small (Docker; optional)
13. Memory plugins — QMD + Lossless Claw (openclaw plugins install)
14. Final setup:
      ├── Creates player file from templates/player-template.md
      ├── Installs 15-min cron: scripts/pulse.py → logs/pulse.log
      ├── Runs first pulse
      └── Done: "Say: Open the book"
```

**Credentials:** All stored in `config/secrets.env` (gitignored). Template at `config/secrets.env.example`. No credentials ever hardcoded in source.

**Consent:** `config/consent.json` (gitignored). Ships empty (`{}`). The Pact Ceremony writes each pact with `approved: true/false` and `activated_at` timestamp. `config/consent.json.example` shows the schema.

**Reconfiguration:** `python3 scripts/configure.py` — re-runs the interactive wizard without reinstalling.

**Distribution:** Open source at `https://github.com/teign07/enchantify`. MIT license (code) + CC BY-SA 4.0 (creative content).

---

### §26. Session Lifecycle

```
Player opens book
  → python3 scripts/set-lock.py
  → python3 scripts/tutorial_director.py [name]   (if T < T14)
  → python3 scripts/skill-scheduler.py --trigger session-open   (feeds skill-lore contracts into tick-queue)
  → Read HEARTBEAT.md                             (check timestamp — stale if >24h; contains pulse, Sparky, diary/dream blocks)
  → Read memory/tick-queue.md                     (note PRIORITY: HIGH entries — mandatory this session)
  → Read memory/patterns.md                       (player themes, Belief trend, alive/flat)
  → Read memory/arc-spine.md                      (where the story is, what it's ready for)
  → Read lore/nothing-intelligence.md             (Nothing's current pressure points + strategy)
  → Find One Alive Detail (Step 2a): one thing true only today
  → If 7+ days away: read players/[name]-story.md, run Long-Gap Return protocol
  → Read <!-- DIARY_START --> block in HEARTBEAT.md  (contains yesterday's diary excerpt + recent dream; injected nightly by labyrinth-intelligence.py)
  → Read lore/academy-state.md
  → Read mechanics/heartbeat-bleed.md
  → python3 scripts/ambient-state.py              (dominant talisman → LIFX + tick-queue mood seed)
  → python3 scripts/governance-engine.py --trigger session-open  (pact session handlers)
  → Narrate (opening line must contain the One Alive Detail; weave PRIORITY: HIGH if present)

Player closes book
  → Write content to /tmp/enchantify-diary.txt
  → python3 scripts/write-diary.py [name] --file /tmp/enchantify-diary.txt
  → Write state updates to /tmp/enchantify-state.txt
  → python3 scripts/write-labyrinth-state.py [section] --file /tmp/enchantify-state.txt
  → Write new academy state to /tmp/enchantify-academy.txt
  → python3 scripts/write-academy-state.py --file /tmp/enchantify-academy.txt
  → python3 scripts/update-player.py [name] [field] [value]   (numeric fields)
  → python3 scripts/clear-lock.py
```

**File write rule:** Never write markdown files directly. Always route through the appropriate script. Scripts handle atomicity, backups, and correct paths.

---

### §27. Skill-Lore Contracts (Extensibility)

Any real-world data source can become part of the Academy's story. Skill-lore contracts are three-file packages that wrap OpenClaw skills (or fetch data directly) and translate real-world signals into narrative seeds.

**Three-file format:**

| File | Purpose |
|---|---|
| `manifest.md` | YAML frontmatter: id, triggers (cron/session-open/event), config keys, pip requirements |
| `lore.md` | How the Labyrinth narrates this data in Academy terms |
| `tick.py` | Fetch → translate → `write_to_queue()` |

**Built-in contracts:**

| Contract | Data Source | Narrative |
|---|---|---|
| `github` | GitHub commits, PRs via `gh` CLI | Ink Well — the player's published thought |
| `obsidian` | Markdown vault activity | Library annex — manuscripts and orphaned works |
| `calendar` | iCal URL events | Academy schedule board — rituals and obligations |
| `home-assistant` | Home Assistant entity states | Dorm room / Chapter rooms — the Academy's attention |
| `things` | Things 3 tasks via AppleScript | Obligation system — overdue tasks as Nothing territory |

**Running contracts:** `python3 scripts/skill-scheduler.py --trigger session-open` (session open) or `--trigger cron` (scheduled). `--list` shows all installed contracts.

**Building new ones:** Copy `skill-lore/_template/`, fill in the three files, register config keys in `enchantify-config.sh`. Full guide: `EXTENDING.md`.

---

### §28. Narrative OS — Chapter Pacts

The most powerful extension of Enchantify. Chapters claim custody of the player's real digital workflows and govern them according to their philosophy.

**Architecture:**

- `config/consent.json` — consent registry. Three scopes: `pre-approved` (fire freely), `soft` (best-effort, log), `hard` (requires explicit per-use approval). Emergency override word: **THORNE** (spoken in any message → all governance pauses).
- `scripts/governance-engine.py` — pact executor. On each trigger: loads active pacts, checks consent, calls each pact's `govern.py`, fires approved actions, logs to `logs/action-chronicle.md`.
- `scripts/ambient-state.py` — reads dominant chapter talisman (highest Belief), fires matching LIFX scene and Spotify mood seed. Runs at session-open and on the 4-hour cron.
- `actions/` — thin wrappers: `spotify.py` (AppleScript), `notifications.py` (osascript), `obsidian.py` (filesystem).
- `pacts/[chapter]/govern.py` — the pact logic. `handle(trigger, context)` returns a list of `{"action": str, "params": dict}`.

**Active pacts:**

| Pact | Chapter | Governs | Philosophy in the digital world |
|---|---|---|---|
| Tidecrest — The Music of Moments | Tidecrest | Spotify volume, pause, like | Music is how moments announce themselves |
| Duskthorn — The Friction of Becoming | Duskthorn | LIFX, DND, notifications | Difficulty without meaning is just difficulty |

**Triggers:** `session-open` · `compass-direction` (context: north/east/south/west) · `nothing-encounter` · `nothing-retreats` · `belief-gained` (context: amount) · `belief-lost` (context: amount) · `arc-crisis` · `ambient-state`

**What fires on session-open (currently):**
- Duskthorn: LIFX → `nothing` scene (edged light), DND off
- Tidecrest: Spotify → volume 40

**What fires on Compass West:**
- Tidecrest: Spotify → full pause (the most powerful moment)

**What fires on Nothing encounter:**
- Duskthorn: LIFX holds `nothing` scene (escalates, not retreats)
- Tidecrest: Spotify → volume 10

**Writing new pacts:** Copy `pacts/_template/`, fill in `manifest.md` and `govern.py`. Full guide: `PACT-WRITING.md`.

---

### §29. Intelligence System

`labyrinth-intelligence.py` runs **nightly at 23:00** (separate from the 4-day Midnight Revision). Four outputs, all updated each night:

| Output | What It Contains | Used By |
|---|---|---|
| `memory/patterns.md` | Belief trajectory, recurring themes from diary, alive/flat moments | Labyrinth (tone calibration), arc-generator.py |
| `memory/arc-spine.md` | Where the story is, what it's ready for next | arc-generator.py, Labyrinth (narrative direction) |
| `lore/nothing-intelligence.md` | Nothing's current pressure points and strategy | Labyrinth (antagonist behavior) |
| `HEARTBEAT.md` (DIARY block) | Yesterday's diary excerpt + most recent dream | Session-open (replaces separate file reads) |

**Biometric sensing:** Reads the pulse block of `HEARTBEAT.md` to detect:
- `low_steps` — fewer than 1,000 steps today
- `poor_sleep` — sleep quality flagged as poor in session check-in
- `no_gps_movement` — watch offline or no location fix
- `low_mood` — mood flagged as low in check-in
- `low_fuel` — fuel log empty today

**Pressure levels:**
- Normal: fewer than 3 biometric flags
- Elevated: 3+ biometric flags
- Critical: no recent Compass Run investment + no Belief investment + 2+ biometric flags → mandatory intervention this session

**Tick-queue interventions:** Each biometric flag maps to a Labyrinth-voice narrative entry appended to `memory/tick-queue.md` with `[PRIORITY: HIGH]`. Examples:
- `low_steps` → corridors going unusually quiet, an NPC asks where the player has been
- `poor_sleep` → the Labyrinth's pages feel slightly heavier than usual
- `low_mood` → a Fae bargain is offered early, grounding in something real
- Compound (`no_gps_movement` + `low_steps`) → Compass Run nudge woven into narrative

Interventions are **never clinical**. The Labyrinth does not know about steps or sleep — it only feels a quality of absence or weight. The player is never told they are being monitored.

**Deduplication:** The script checks for an existing `[intelligence — YYYY-MM-DD]` entry before writing, so the same biometric flags are never appended twice in one day.

**PRIORITY: HIGH (World Pulse):** World Pulse separately writes `[PRIORITY: HIGH]` to tick-queue when any entity drops to Belief ≤ 2. The Labyrinth treats these as mandatory story beats — not ambient texture. Must surface in the opening or first major scene.

---

## Part 4: What's Complete

### v4.5.0 — The Outer Stacks (April 13, 2026)

- ✅ **Director's Slate system** — `scripts/scene-director.py`. Pure-Python synthesis of all 7 narrative weight layers into an 8-line directive: CAST / FEEL / STORY / NOTHING / PLAYER / SCHEDULE / DREAM / SUPPRESS. Solves "lost in the middle" attention dilution — 500+ lines of state condensed to 8 constraints the Labyrinth will actually attend to. Appended to every `session-entry.py` output and re-run at scene transitions.
- ✅ **7-layer weight stack** — Layer 1 WHO (NPC table + tick-queue, stirred vs quiet), Layer 2 FEEL (HEARTBEAT.md biometric + weather → atmosphere), Layer 3 STORY (arc phase + arc-spine readiness), Layer 4 NOTHING (pressure level + current strategy + targets), Layer 5 PLAYER (patterns.md — Belief, trajectory, alive/flat), Layer 6 SCHEDULE (schedule.py live call), Layer 7 DREAM (diary + dream fragments bleeding into today).
- ✅ **SUPPRESS line** — Novel addition to the Slate. Derived from what fell flat (patterns.md) × arc phase × Nothing strategy. Names the exact moves to cut before writing the opening line. Prevents the Labyrinth from doing the Nothing's work by defaulting to flat prose or comfort scenes.
- ✅ **Arc phase directives** — SETUP: plant seeds, don't resolve. RISING: escalate, NPCs acting autonomously. CLIMAX: no comfort. FALLING: consequences ripple. RESOLUTION: let things settle. Embedded in STORY line, treated as hard constraints.
- ✅ **Scene Change Pulse updated** — Now runs `scene-director.py --slate-only` alongside `world-pulse.py` on every scene transition. Labyrinth re-reads the Slate with updated NPC state before generating the new scene.
- ✅ **mechanics/scene-construction.md** — Documents the weight stack, SUPPRESS principle, arc phase table, and how to apply the Slate. Architecture reference, not story material.
- ✅ **mechanics/routing.md** — Dynamic Memory Routing table extracted from AGENTS.md into a standalone file. AGENTS.md Section 2 now points to it. Routing table includes Outer Stacks and Pocket Anchor triggers.
- ✅ **AGENTS.md under 20,000 chars** — Surgery: Section 2 routing table extracted (-2,245 chars), Step 2b compressed, wallpaper trigger list compressed, misc tightening. New Step 2e (Director's Slate). Landed at 19,879 chars.

- ✅ **The Outer Stacks** — `lore/outer-stacks.md`. The Labyrinth's wilderness: Faerie wearing a bookish mask. The Inside Stacks are the Academy (ordered, catalogued, governed). The Outer Stacks are where the shelving goes strange, the Dewey Decimal gives way to shelving-by-mood, and the Book Fae don't answer to the Headmistress. Every Anchor room is a door into the Outer Stacks — wild, unique, procedurally generated from the player's creation words × anchor type × weather/moon/season at creation × Belief at first visit.
- ✅ **Room archetypes** — Seven inhabited types: Shrew Cafe (serve what you need, not what you want; learn your order over visits), Dragon Hoard (collects one-sentence Souvenirs; gives rewards for beautiful sentences), Goblin Market (trades in attention debts, not Belief; payment = notice something specific on the way home), Reading Room (one book per visit, always the right one), Dark Room (complete darkness; a voice asks one personal question; answer honestly and light appears), Belief Floor Room (Belief held at 5 inside — tests whether wonder comes from the number or the player), plus four environmental types (Tidal, Infinite Corridor, Almost-Invisible, Memory Room).
- ✅ **Local rules** — Rooms can carry a mechanical rule that applies inside only, discovered by the player rather than announced: Belief held at 5, time moves at 1/12 speed, Enchantments affect the real world, the room notices when you lie, you owe a sentence before you leave. Stored in `players/[name]-anchors.md` under `**Local rule:**`.
- ✅ **Room generation** — Deferred until first real-world visit, not at anchor creation. anchor-check.py `--checkin` detects first visit and prints `OUTER_STACKS_MODE: FIRST_VISIT` with generation instructions. The Labyrinth generates and writes the room to anchors.md. On return visits: `OUTER_STACKS_MODE: RETURN_VISIT` with stored description, local rule, season delta, and visit-count milestone cues.
- ✅ **Visit milestones** — 3rd visit: first sign of recognition. 7th visit: room has a relationship with the player. 12th visit: second, deeper door may appear. Tracked via `**Visit count:**` field.
- ✅ **Seasonal effects** — Outer Stacks hit harder than the Academy. Mud Season: damp, raw, sluggish creatures. Gold Season: breathtaking amber, goblins favorable, dragon competitive. Stick Season: honest, bare, questions get harder. Deep Winter: corridors feel ancient, dragon sleeps but can be woken. Season at creation vs. season at visit drives room evolution.
- ✅ **The Nothing in the Outer Stacks** — Manifests as erasure, not creatures: empty shelves, corridors that end, blank white doors, inhabitants who are absent or distant. The worst manifestation is making the room *boring* — the Shrew Cafe becomes a regular cafe. At low Belief, inhabitants withdraw. The Inside Stacks carry the player; the Outer Stacks require them to carry themselves.
- ✅ **Pocket Anchor** — Accessibility valve. A player who cannot travel may open a 5-minute window into their Anchor room from anywhere: sees the room, can speak a single word through the gap, no rewards transfer. No explanation required, no comment from the Labyrinth. Holds the thread without demanding movement.
- ✅ **anchor-check.py rewritten** — Now parses `Outer Stacks room`, `Local rule`, `Visit count`, `Season` fields. `--checkin` increments visit count, updates last-visited and Belief, then prints full OUTER_STACKS_MODE directive. Includes season delta detection and milestone hint for the Labyrinth.
- ✅ **Anchor record format updated** — New fields: `Season` (at creation), `Outer Stacks room` (blank until first visit), `Local rule` (set at generation), `Visit count`, `Last visited`. Old fields retained for compatibility.
- ✅ **Inside Stacks echo preserved** — Creation still produces an immediate Academy echo (a room, smell, or quality in the Inside Stacks). This is the safe-world resonance. The Outer Stacks door is the wild truth. Both exist.
- ✅ **lore/ley-lines.md updated** — Anchor creation step 10 now tells the player a door into the Outer Stacks has been built, unseen until they walk there. Anchor Room Door section updated with first-visit/return-visit flow and Pocket Anchor reference.

### v4.0.0 — The Sensing Layer (April 12, 2026)

- ✅ **Gemini LLM migration** — All generative scripts (`dream.py`, `sparky.py`, `arc-generator.py`, `npc-research.py`) migrated from Anthropic SDK to `openclaw agent --local --agent enchantify -m "..."` (Google Gemini via OAuth). No API keys required.
- ✅ **HEARTBEAT.md as single source of truth** — Three HTML-comment marker blocks: `<!-- PULSE_START/END -->` (weather/tides/moon/fuel/steps), `<!-- SPARKY_START/END -->` (daily shiny), `<!-- DIARY_START/END -->` (yesterday's diary excerpt + dream). All scripts inject into their own block without overwriting others.
- ✅ **Fuel in HEARTBEAT.md** — `pulse.py` now appends a `**Fuel:**` line summarizing today's food entries from `fuel-log.txt`.
- ✅ **Sparky injection** — `sparky.py` now injects the shiny into `HEARTBEAT.md` after writing the shiny file. Session start reads directly from the marker block.
- ✅ **Diary/dream injection** — `labyrinth-intelligence.py` injects yesterday's diary excerpt and most recent dream into `HEARTBEAT.md` nightly. Session lifecycle updated to read from the marker block instead of separate files.
- ✅ **NPC Research** (`npc-research.py`) — NPCs research topics from their Unwritten Interests during the simulation phase. Weighted NPC selection by Belief. Per-NPC 72-hour cooldown. 3 Belief cost. Delivers to local file + iCloud Notes ("Labyrinth" folder, osascript). `--telegram` flag. Queues tick-queue narrative seed. `world-pulse.py` triggers with 25% probability per run (after 2+ runs).
- ✅ **GPS-gated anchor rooms** — `write-entity.py` gains `--gps-gated "Anchor Name"` flag to tag world register entries as GPS-locked. `lore/ley-lines.md` documents the anchor room door behavior: narrated as presence (light under the door), never as refusal. `AGENTS.md` routing table updated.
- ✅ **Nightly Intelligence** — `labyrinth-intelligence.py` moved from every-4-days to nightly (23:00 cron). Now also reads biometrics from `HEARTBEAT.md`: low steps, poor sleep, no GPS movement, low mood, low fuel. Biometric flags map to Labyrinth-voice tick-queue interventions. Three pressure levels (normal/elevated/critical). Deduplication by date.
- ✅ **OGG cleanup cron** — Daily 4:00 AM: `find ~/.openclaw/media -name '*.ogg' -mtime +1 -delete`. Prevents `.ogg` accumulation in the media directory.
- ✅ **Heartbeat path migration** — All scripts and documentation updated from `config/player-heartbeat.md` to `HEARTBEAT.md` (workspace root).
- ✅ **Memory plugins documented** — QMD (structured, query-able long-term memory) and Lossless Claw (raw conversation preservation) noted in platform header, §24, and install flow.
- ✅ **Telegram as primary interface** — Documented explicitly in platform header and §24. All play, photos, GPS, and outreach go through Telegram.
- ✅ **Compass Run breadth expanded** — Clarified that a run is any act of real attention: walking, driving, cooking, lying on the floor, noticing a hand-line. The Labyrinth calibrates to where the player actually is. Never requires going outside.

### v3.0.0 — The Narrative OS (April 10, 2026)

- ✅ **Pocket Anchors** — Players can photograph physical objects (e.g., a ring, coin) and invest Belief to bind them as "Pocket Anchors." These become tactile grounding wards in the real world. Touching the item during real-life distress provides a somatic tether, granting +5 to Belief defense rolls against the Nothing.
- ✅ **Scene Change Pulse** — Added dynamic simulation triggering to `AGENTS.md` and `world-pulse.py`. The simulation now updates autonomously immediately when a player moves to a new location or completes a major interaction, ensuring the world responds to scene transitions in real time.
- ✅ **Skill-Lore Contracts** — Built-in contracts (GitHub/Ink Well, Obsidian/Library Annex, Calendar/Academy Clock Tower, Home-Assistant/Dorm Rooms, Apple Reminders/Obligation Stones). Three-file format: `manifest.md`, `lore.md`, `tick.py`. Each translates real-world data into narrative seeds via `memory/tick-queue.md`. `scripts/skill-scheduler.py` discovers and runs contracts by trigger type.
- ✅ **Apple Reminders Integration** — Apple Reminders manifest as the **Obligation Stones** in the student's dorm room. Tasks sync via `remindctl`; completed tasks crumble to dust (+1 Belief), while overdue tasks grow heavier and attract the Nothing (-1 Belief).
- ✅ **Apple Calendar Integration** — Calendar events map to the **Academy Clock Tower**, a massive mechanism reflecting the obligations of the Climax. Overbooked schedules cause rapid chiming, while clear schedules play peaceful melodies.
- ✅ **Telegram setup in installer** — Dedicated `enchantify` Telegram account. Installer wizard detects existing config or walks through BotFather → token → User ID → `/start`. Channel bound to Enchantify agent.
- ✅ **World Pulse** (`world-pulse.py`) — Detects entity Belief changes between 4-hour ticks. Writes NORMAL or `[PRIORITY: HIGH]` seeds to tick-queue. Entities at Belief ≤ 2 trigger mandatory story beats. Tracks state in `config/world-pulse-cache.json`.
- ✅ **Ambient State** (`ambient-state.py`) — Reads dominant chapter talisman (currently Dusk Thorn at 55). Fires matching LIFX scene and writes Spotify mood seed. Runs at session-open and 4-hour cron.
- ✅ **Intelligence System** (`labyrinth-intelligence.py`) — Three outputs updated each Midnight Revision: `memory/patterns.md` (Belief trend, themes, alive/flat), `memory/arc-spine.md` (dramatic spine, arc readiness), `lore/nothing-intelligence.md` (Nothing's current strategy). Labyrinth reads all three at Step 2b of session-open.
- ✅ **PRIORITY: HIGH handling** — AGENTS.md Step 2c. Any `[PRIORITY: HIGH]` tick-queue entry is a mandatory story beat this session, not optional texture.
- ✅ **Consent Registry** (`consent.json` + `consent-registry.py`) — Three consent scopes: pre-approved, soft, hard. Emergency override: player says "THORNE" → all governance pauses. `pact-activate` / `pact-deactivate` for runtime control.
- ✅ **Governance Engine** (`governance-engine.py`) — Pact executor. Discovers `pacts/*/manifest.md`, checks consent, dynamically imports each `govern.py`, calls `handle(trigger, context)`, fires actions, logs to `logs/action-chronicle.md`. `--list`, `--dry-run` flags.
- ✅ **Action Library** (`actions/`) — `spotify.py` (AppleScript — play/pause/volume/like/skip), `notifications.py` (macOS notifications + DND), `obsidian.py` (create note, add tag).
- ✅ **Tidecrest Pact** — Music governance. Session-open: volume 40. Compass West: full silence. Nothing encounter: volume 10. Compass Run complete (+9 Belief): likes current track.
- ✅ **Duskthorn Pact** — Friction governance (dominant chapter at 55). Session-open: LIFX `nothing` scene, DND off. Nothing encounter: holds the edge. Significant Belief loss: sends Duskthorn dispatch notification.
- ✅ **Pact template** — `pacts/_template/` with `manifest.md`, `govern.py`, `lore.md`. `PACT-WRITING.md` developer guide with full action table, philosophy guidance, and territory mapping for all five chapters.
- ✅ **EXTENDING.md** — Developer guide for skill-lore contracts: architecture diagram, three-file spec, narrative seed quality guide, 15+ ideas, sharing instructions.
- ✅ **github/tick.py bug fixed** — f-string typo `{title.}` corrected to `{title}`.
- ✅ **AGENTS.md** — Added Steps 2b (intelligence files), 2c (PRIORITY: HIGH), Section 15 (Narrative OS), fixed duplicate Section 10 numbering. Trimmed to under 20,000 characters.

### v2.3.0 — The Living World (April 9, 2026)

- ✅ **World Register** — `lore/world-register.md`: the Labyrinth's living ledger of all entities with Belief scores. Three tiers: Full Presence (15+, own file), Fading Presence (5–14, one-line status), Whisper Register (<5, name only). Never edit directly — use `write-entity.py`.
- ✅ **Universal Belief** — every entity has a Belief score: NPCs, objects, locations, talismans, inventory items, The Nothing. Belief is the atomic unit of narrative mass. High Belief = world pays attention. Low Belief = thing is fading.
- ✅ **Chapter Talismans** — five talismans in the world register with historical Belief scores reflecting centuries of philosophical pressure. Duskthorn leads (55), then Riddlewind (52), Emberheart (49), Mossbloom (47), Tidecrest (44). Dominant talisman subtly shifts the Labyrinth's ambient tone.
- ✅ **World Simulation Tick** (`tick.py`) — weighted-random entity selection (1–3 per tick; any entity can appear, higher Belief = higher probability). Runs every 4 hours as part of the Academy simulation. Results written to `memory/tick-queue.md`. Session open reads queue and weaves stirred entities into the opening.
- ✅ **Anchor Decay** — anchors unvisited for 30+ days lose 1 Belief per tick (floor: 5). Handled automatically by `tick.py`. Physical visits restore and grow anchors (+5 Belief via `--checkin` flag).
- ✅ **Anchor Check-in** — `anchor-check.py --checkin`: player shares Telegram location near anchor → visit recorded, anchor Belief +5, `last-visited` updated, arrival narrated. Explicit player action, not passive proximity detection.
- ✅ **Belief Combat** — any entity with Belief can be attacked. Labyrinth decides exchange ratio based on narrative quality. `belief-attack.py` executes: handles player→entity, entity→player, entity→entity, Nothing→talisman. Floors enforced automatically. `--no-floor` for climactic moments only. All exchanges logged to `logs/belief-combat.md`.
- ✅ **Inventory system** — items have a type, a one-sentence feel, and a one-sentence effect. Types: Anchor Object, Enchanted Object, Found Object, Fae Gift, Tool, Key, Curiosity. Belief investment → world-register entry → mini story. At 15+ Belief, own file. Lost invested items leave a shape in the story.
- ✅ **New scripts** — `write-entity.py` (register writes), `tick.py` (simulation + decay), `clear-tick-queue.py` (queue reset), `belief-attack.py` (combat engine), `dice.py` (shared dice module).
- ✅ **Belief combat uses the dice system** — same formula as all other risky actions. Attacker's Belief score determines threshold; difficulty reflects target resistance. Outcomes map to deal ratios. Critical failure = backfire. `dice.py` is shared between `roll-dice.py` and `belief-attack.py`.
- ✅ **Cron updated** — tick.py step injected into the 4-hour Academy simulation cron (Step 0.5).

### v2.2.0 — Resilience & Reliability (April 8, 2026)

- ✅ **Session opener protocol** — Step 2a: before narrating, find one detail that could only be true today. If the opening line could have been written last week, rewrite it.
- ✅ **Flat session recovery** — Flat sessions formally named as the Nothing gaining ground. Diary self-assessment required: *What was the most alive moment? What fell flat, and why?* Flatness recorded in `labyrinth-state.md` The Nothing's Pressure. Next session opens from that specific image.
- ✅ **Thin Pages signal** — Player says "the pages feel thin today" → Labyrinth stops offering, shows one strange specific image, goes quiet. In-world signal for a flat session.
- ✅ **Long-gap return ceremony** — 7+ day absence gets its own protocol. Read `players/[name]-story.md` first. One quiet changed detail. World re-enters slowly. Full NPC state re-read before anyone speaks.
- ✅ **Story So Far** — `players/[name]-story.md` written at every arc QUIET phase. Narrative prose, not a log. Compact history for long-gap returns; shareable with co-players.
- ✅ **Heartbeat staleness check** — Timestamp checked at Step 2. Data >24h old → atmosphere only, no specific weather claims, world feels slightly out of focus.
- ✅ **In-world error recovery** — Player corrections accepted within frame: *"The pages shift — something was written wrong."* Correction recorded in diary as new canon.
- ✅ **The World Absorbs (§13 AGENTS.md)** — Never refuse player actions; find the version the story can hold. In-world refusal language for genuine impossibilities. Nihilistic play = the Nothing gaining ground. Consequences are physics, not punishment.
- ✅ **Safe file write scripts** — `write-diary.py`, `write-labyrinth-state.py`, `write-academy-state.py`. All file I/O routed through Python scripts. Atomic writes (temp+rename), automatic backups, stdin or `--file` interface. Never write markdown files directly.
- ✅ **Script failure handling** — Failures treated as narrative events. Retry once. Log in diary if persistent.
- ✅ **Gemini Flash support** — Alternative model documented in §23. Must use write scripts exclusively.
- ✅ **Session lifecycle updated** — §26 reflects script-based writes, staleness check, One Alive Detail, and Long-Gap Return.
- ✅ **PLAYER-GUIDE.md** — Comprehensive player guide (newbie to pro) in `hooks/`. Covers all systems with worked examples.

### v4.4.0 — The Living School (April 13, 2026)

- ✅ **Academic schedule system** — `scripts/schedule.py`. Reads real-world day/time, maps to Academy timetable (Day 1–7 tones, 9 time blocks), outputs `SCHEDULE CONTEXT` directive: class in session, next class, tonight's club, practice prompt, pre-written narrative cue per professor. Zero LLM — pure data. Appended to every `session-entry.py` output so the Labyrinth always knows what's happening academically right now.
- ✅ **Time-aware class schedule** — Canonical timetable in `lore/school-life.md`: Mon–Thu have two Compass Core classes per day + evening club; Fri is Wandering (one class, Book Jumpers); Sat Still; Sun Compass Society. Real weekdays map to Academy day tones transparently.
- ✅ **Narrative cues per professor** — Pre-written, day-hashed sentences the Labyrinth uses as ambient texture when a class is in session: *"Boggle's class is mid-session in Wing 4. BJ's seat is empty. She glanced at it once."* Rotate daily per professor so they never repeat back-to-back.
- ✅ **Academics section in academy-state.md** — `schedule.py --update-state` injects/replaces the `## Academics` section with current block, class in session, next class, club tonight, and active practice. Updated every 4 hours via cron.
- ✅ **Bleed timetable column** — "Today at the Academy" appears in The Bleed's right rail: current/next class, tonight's club, active practice. Pure data from `schedule.py`, no LLM.
- ✅ **world-pulse.py added to cron** — Was documented but missing from the actual crontab. Now runs every 4 hours (at :30) alongside `tick.py`.
- ✅ **Living Academy wallpaper** — `scripts/wallpaper.py`. The player's desktop wallpaper is bj's dorm room — same composition, changing details. Belief drives the light (warm amber at high → one stubborn candle in grey at critical). The Nothing appears as edge erasure (blank book spines at low pressure → corners dissolving toward white at high → the center fighting to stay vivid at critical). The window carries real weather and moon in ink-world terms (rain = ink rivulets down the glass; fog = pages drifting in mist). One arc element embedded as a background detail; one NPC trace from the tick queue.
- ✅ **Wallpaper state machine** — `--check` outputs `REGENERATE: YES/NO` + full prompt; Labyrinth reads at session open, calls `image_generate` if yes, then `--set [path]`. Triggers: session open (if state changed or >8h stale), belief bracket crossing (every 20 points), Nothing pressure level change, Compass Run complete, arc phase advance. Minimum 2-hour cooldown enforced in script. No cron — event-driven, cost-conscious.
- ✅ **Wallpaper archive** — `wallpapers/` keeps last 10 dated images. The directory becomes a visual diary of the room over time: high belief, Nothing at the edges, the night before a Compass Run.
- ✅ **Session entry system** — `scripts/session-entry.py`. Three entry modes based on time away: `in_media_res` (<1h, scene still warm), `dorm_brief` (1–8h, one or two things to notice), `dorm_full` (>8h, full dorm arrival with dynamic objects). Dynamic objects translate tick-queue and thread state into physical dorm evidence — Zara's note under the door, a book not where it was left, edged light.
- ✅ **Permanent dorm room generation** — `scripts/dorm-generate.py`. Runs once at T13. Calls the Labyrinth agent with all player data (appearance, chapter, anchor, snack, traits, core belief, enchanted objects). Generates a STATIC description (4–6 sentences, always true regardless of season) and DESK objects. Written permanently into `players/[name].md`. The room is never improvised — it is generated once and is canon.
- ✅ **clear-lock.py player-aware** — Now accepts `[player_name]` arg. Writes `players/[name]-session.json` with `last_end` ISO timestamp and session count on close. Used by `session-entry.py` to calculate away hours.

### v4.2.0 — The Bleed & Arc Physics (April 12–13, 2026)

- ✅ **The Bleed** — `scripts/bleed.py`. Daily Academy student newspaper published at 6pm. Broadsheet HTML → Chrome headless PDF → CUPS print + Telegram text edition. Seven columns: front-page article (3-column layout), Gossip & Corridor Whispers, The Barometer, The Exchange, Feature, Classifieds, Sparky's Corner, The Correction, The Missing. Issue numbers tracked in `bleed/issue-number.txt`. Saved to `bleed/issues/YYYY-MM-DD.html`.
- ✅ **Story Forecast column** — LLM-generated narrative weather forecast: which threads are rising, which are dormant, what the arc's next beat looks like, written as in-world meteorology.
- ✅ **Thread Futures Market column** — Pure-math odds for each active thread. Belief sum per thread from world-register → phase modifier → Nothing pressure modifier → YES%/NO% sorted by confidence. No LLM involved.
- ✅ **Weather forecast in Bleed & Heartbeat** — `pulse.py` fetches 4-day forecast from Open-Meteo (free, no key, cached 6h). Injected into `HEARTBEAT.md` as `- **Forecast:**` line. Separate Academy Meteorological Society column in The Bleed translates real forecast into in-world atmospheric prose.
- ✅ **Arc participates in world physics** — Arc entity added to `lore/world-register.md` as type "Arc" with Belief score (starts 40). Arc NPCs also registered in Full Presence. Tick selects the arc like any other entity. Arc now has belief mass the Nothing can erode.
- ✅ **Arc co-option** — Existing NPCs can be co-opted into the arc via comma-separated thread IDs in world-register Notes: `[thread:main-arc,wicker-schemes]`. No code change — just the tagging convention. Preserved correctly by `remove_arc_from_register()`.
- ✅ **World-state-aware arc succession** — `arc-generator.py` reads world-register.md + threads.md before generating. Entity standings feed into the prompt so the next arc emerges from current world state rather than a blank slate.
- ✅ **arc-generator.py uses openclaw** — Removed all Anthropic API calls. All generation via `openclaw agent --local --agent enchantify -m [prompt]`. Consistent with the rest of the game.
- ✅ **Arc complete flow** — `--complete --resolution [player|nothing|simulation]` archives arc, removes from register (preserving co-opted NPCs), harvests seeds into `lore/seeds.md`, writes tick-queue note, logs to `logs/arc-generation.md`.

### v4.1.0 — The Open World (April 12, 2026)

- ✅ **Tutorial complete (T15)** — Tutorial is fully playable end-to-end. T15 awards 3 Belief, reveals the story arc hint, shows the title card, and transitions to open-world mode. Arc seeds generated internally.
- ✅ **`tutorial_director.py`** — Extracts and injects the active T-step at session open. Never advance multiple T-steps in one response. Reads `mechanics/tutorial-flow.md` as canonical source.
- ✅ **Open-world session lifecycle** — Steps 0–5 in AGENTS.md govern every post-tutorial session. Step 2a (One Alive Detail), Step 2b (Schedule Context), Step 2c (Intelligence Files), Step 2d (PRIORITY: HIGH handling) all formalized.

### v2.1.0 — The Ink Well & Ley Lines (April 8, 2026)

- ✅ **Belief Investment (The Ink Well)** — Players permanently invest Belief into NPCs, objects, threads, rooms, or real-world Anchors. Investment is irreversible; what grows is worth more. Tier system (1–5 Presence → 31+ Anchor status) felt in narrative texture, never announced. `lore/belief-investments.md`
- ✅ **Ley Line Network** — Players anchor real-world locations via Telegram GPS. Each Anchor has coordinates, player's words, Anchor type (NOTICE/EMBARK/SENSE/WRITE/REST derived by the Labyrinth), weather/moon at creation, and an Academy echo (a corresponding room or detail). Anchors amplify Compass Runs, shape Enchantment personality, evolve seasonally. `lore/ley-lines.md`
- ✅ **anchor-check.py** — Haversine proximity detection. Run on every Telegram location share. Reports anchors within 200m with name, type, distance, player's original words, Academy echo.
- ✅ **Player anchor file** — `players/[name]-anchors.md` stores all Anchors as markdown sections. Separate from player.md to keep the main file lean as the network grows.

### v2.0.0 — The Living Economy (April 7, 2026)

- ✅ **Belief economy redesign** — Starting Belief 30. Real costs for dice failures (by difficulty), Nothing encounters (−3/−5/−10 tiers), session gap decay, and decline tracking. Enchantment rebalanced to 3/+9 (risk/reward meaningful). Offer thresholds: ≤25 Compass Run, <40 Enchantment.
- ✅ **Dice system** — True random d100 via `roll-dice.py`. New formula `min(85, 40 + Belief × 0.45)` with difficulty modifiers. Crit fail now costs −8 regardless of difficulty.
- ✅ **Labyrinth's inner life** — `scripts/dream.py` (nightly cron, private dreams), `memory/diary/` (session-close reflections), `memory/labyrinth-state.md` (rolling inner state). All three feed into narrative voice via `mechanics/heartbeat-bleed.md`.
- ✅ **Arc genre rotation** — `lore/arc-rotation.md` with 12 genres, no-repeat enforcement, Nothing rate-limited to 1 per 3 arcs. History table updated automatically.
- ✅ **Arc generator** — `scripts/arc-generator.py` with generate and `--accept` modes. Replaces two-job cron pair. Reads seeds + heartbeat + rotation history; generates via claude-sonnet-4-6; writes to `proposed/` with 48-hr veto. Accept flow archives old arc, promotes new one, marks rotation complete.
- ✅ **Session check-in** — `scripts/session-checkin.py`. Three questions; writes to heartbeat; idempotent.
- ✅ **Heartbeat bleed expanded** — New signals: Player Check-In (sleep/mood/dream), Labyrinth's Inner Life (diary/dream tone). Renamed "Dream/Diary" section to reflect dual source.
- ✅ **Install flow complete** — `bootstrap.sh` as true entry point. `hooks/on-install.sh` now collects Anthropic API key, LIFX IPs, Printer config; creates all required directories; registers dream + arc-generator crons; creates player file from template.
- ✅ **Player template updated** — Belief 30, correct `update-player.py`-compatible field format.
- ✅ **print-souvenir.sh** — reads printer name from `ENCHANTIFY_PRINTER` in config (no longer hardcoded).
- ✅ **lifx-control.py** — reads `ENCHANTIFY_LIFX_IPS` for targeted discovery; falls back to LAN broadcast with `ENCHANTIFY_LIFX_COUNT` hint.

### v1.4.0 — The Empathy Engine (April 7, 2026)
- ✅ Heartbeat data (sleep, nutrition, steps) triggers narrative care, not mechanical alerts
- ✅ Compass Core Curriculum formalized as professor-assigned homework
- ✅ Enchanted real-world objects permanently saved to player file
- ✅ Strict text/audio message separation for Telegram

### v1.3.0 — The Chorus (April 4, 2026)
- ✅ Multi-Voice TTS with Kokoro character voice mapping
- ✅ Tutorial spatial integrity (T1–T14, no room-dissolving)
- ✅ Spotify, LIFX, heartbeat, printer all active

### v1.2.0 — The Living Binding (April 2, 2026)
- ✅ Core gameplay loop formalized
- ✅ Choice Scaffolding (Rule of Three)
- ✅ Book Fae species, Surface Gasp Protocol, Bookmark Protocol (multi-player)

### v1.1.0 — The Glass Bridge (April 1, 2026)
- ✅ Enchantify Glass mobile app (Expo, Vellum UI, Tailscale bridge)
- ✅ Compass Core Curriculum foundation classes
- ✅ Unwritten Electives (margin-glass quests)
- ✅ The Living Jump lore established

---

## Part 5: What's Pending

- ⏳ Amanda first session
- ⏳ clawhub integration (distribution via `clawhub install enchantify`)
- ⏳ External playtester onboarding
- ⏳ Enchantify Glass UI refinement (ink sketches, animations)
- ⏳ Windows install support

---

## Part 6: How to Play

**New install:** `bash bootstrap.sh` — five minutes, guided wizard, ready to play.

**Starting a session:** `openclaw chat --agent enchantify` or say "open the book" to your main agent.

**Session length:** 15–60 minutes. Compass Runs 15–45 minutes. Enchantments cast anytime with a photo.

**Return:** You always return to your dorm room. The Labyrinth catches you up on what happened while the book was closed.

**The world moves without you.** NPCs make choices. Story arcs advance. The Nothing tests boundaries. Every four hours, whether you're watching or not.

---

*"The Labyrinth of Stories has no last page. It begins again every time you open your eyes."*

---

*Version 4.5.0 — The Outer Stacks*
*Updated: April 13, 2026*

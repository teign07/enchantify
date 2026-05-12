# Enchantify — The Labyrinth of Stories
## Complete Capability Reference

*Version: 16.3.0 — Living Book Pages & Page Contracts*
*Last updated: May 9, 2026*

---

## What Enchantify Is

Enchantify is an interactive narrative role-playing game that runs as a registered OpenClaw agent. Players attend Enchantify Academy — a magical school inside a living book called the Labyrinth of Stories — where they take classes, meet characters, uncover secrets, jump into classic books, battle a force called the Nothing, and cast Enchantments that require real-world actions.

**Secret purpose:** Teaches the Wonder Compass framework (Notice → Embark → Sense → Write → Rest) through play. Players practice evidence-based behavioral interventions without ever being told they're doing therapy.

**The Revolution:** Enchantify is not a game you open. It's a place that *lives*. The Academy advances every four hours whether you're watching or not. NPCs make choices. The Nothing moves. Relationships evolve. When you return, you're not resuming a save file — you're catching up with a life.

**Model:** Brain is `claude-sonnet-4-6` via Claude subscription connected to OpenClaw. Routing/sub-tasks use `openai-codex/gpt-5.4` (spawn, heavy tasks) and `openai-codex/gpt-5.4-mini` (scene conductor, routing). Set in `~/.openclaw/openclaw.json`.

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
- **The Labyrinth's Inner Life:** The Labyrinth has its own diary (`memory/diary/`) and nightly dreams (`memory/dreams/`), generated automatically. Closeout now writes richer diary memory: private reflection, concrete continuity, thread/arc changes, NPC movement, unresolved hooks, and emotional weather. Excerpts are injected into `HEARTBEAT.md` nightly by `labyrinth-intelligence.py`. These are private — but they color how it narrates and what it notices.
- **Living Book Pages:** Enchantify now treats every interaction as a Page: every page has a purpose, a player invitation, a closure condition, and proof the Book keeps. `mechanics/pages.md` defines the grammar. `scripts/page-contract.py` chooses the current Page, and `scene-contract.py` embeds it before scene generation so smaller models ask: what page are we on, what does it want, and what proof will it leave behind? Core Page types: Slice of Life, Conflict, Enchantment, Wonder Compass, Letter, Anchor, Rest, Archive, and Bleed.
- **The Marginalia Bridge:** NPCs are aware of local news, Reddit trends, and global events, framed as "Whispers from the Unwritten Chapter."
- **World Simulation:** A background cron runs every 3 hours to evolve world state. It now uses a weighted living-world simulation: high-Belief entities act more often, but low-Belief entities still retain a real chance to move. NPCs, talismans, threads, anchors, arcs, and other weighted entities can all influence offscreen pressure. Each run can still trigger NPC research, but that research is bounded so it cannot freeze the pulse.
- **Story Arc Rotation:** The Labyrinth tells stories in seasons — twelve genre types rotating to ensure variety. No two consecutive arcs repeat. The Nothing is rate-limited to once every three arcs. Arc succession is automatic: old arcs can complete, seeds are harvested, new arcs validate and promote without manual approval unless explicitly run in proposal-only mode.
- **The Empathy Engine:** Monitors player wellness via heartbeat (including biometrics from Apple Watch/Health) and responds with narrative care — never clinical guilt. Nightly intelligence run detects low steps, poor sleep, and mood dips; writes tick-queue interventions in the Labyrinth's voice.
- 
**NPC Research:** During the world simulation, NPCs occasionally research topics from their Unwritten Interests and deliver findings to the player (local file, styled HTML letter artifact, optional Draw Things ornament, Telegram, iCloud Notes, and physical letters for core NPCs). Costs them Belief. Generation uses the local OpenClaw gateway with a bounded timeout and deterministic fallback, not long-lived `openclaw agent` processes. Physical letters render as character-specific Academy stationery, with a PostScript fallback if HTML/PDF conversion is unavailable. Woven into the next session as a tick-queue seed.
- **NPC Outreach:** Characters and weighted entities can reach through Telegram outside active play. Outreach is one actual in-character message plus one matching voice note in the character's assigned Kokoro voice. It uses the same bounded local gateway route, rejects weak/operational output, and never falls back to "thinking about you" placeholders.
- **The Hidden Curriculum:** Compass Runs, Enchantments, and club assignments are secretly therapeutic interventions (behavioral activation, mindfulness, gratitude journaling). The game never names this. Neither do you.
- **Enchantments (Vision AI):** Spells that require the player to photograph real objects. The vision model interprets the photo and weaves what it sees into the narrative with synesthetic detail.
- **The Compass Run:** A structured real-world quest based on the Wonder Compass framework. Notice something. Do something — anything — in the world. Sense it. Write one sentence. +9 Belief. A run can be walking the block, driving two towns over, cooking at home, lying on the floor and looking at it like Gulliver, or noticing a line on your hand you've never seen before. The only requirement is that attention landed somewhere real.
- **Magical Traditions Framework:** The Labyrinth actively teaches real-world magical traditions through fiction, never naming them directly. Animism is the base layer — Enchantments are animist acts, the Nothing is animism's failure. Folk magic and witchcraft live in the seasonal calendar, the souvenir sentence (a vessel), and Compass Runs (ambulatory magic). Fae lore governs all Outer Stacks and fae interaction (six canonical rules: bargains, true names, thresholds, gifts, time, stories-as-literal). Ceremonial magic (Momort's corrupted Hermetic tradition) structures the compass correspondences — North/Earth, East/Air, South/Fire, West/Water, Center/Spirit. Chaos magic (Wicker) explains his genuine effectiveness and danger. Zen (Stonebrook) is the contemplative ground of the Notice direction. Narrative magic (Thorne, Villanelle) holds that language is not a map of the world — it is a hand laid on it. Full reference: `lore/magical-traditions.md`.
- **The Restricted Section (expanded):** Eight documents covering the full depth of the Academy's hidden knowledge. Includes: `the-nothings-manuscript.md` (the Nothing's own voice — the case for numbness, quietly reasonable), `founding-compact.md` (what the Academy actually is and why it was built), `records-of-the-unfinished.md` (students whose stories paused; the door is always open), `thornes-private-observations.md` (private journal entries; centuries of watching wonder find and lose people). The therapeutic truth is present throughout — veiled in the fiction, never named directly.
- **Story Thread System:** Named stories with Belief mass. Threads are born from high-Belief NPCs, Labyrinth proposals, player investment, and close-session seed promotion. They live in `lore/threads.md` and `lore/world-register.md` (Active Threads section). tick.py stirs them like any entity — high Belief = stirred more often = story advances, but selection is probabilistic rather than a hard top-band cutoff. Threads escalate through phases (dormant → setup → rising → climax → resolution at 50+), emit lifecycle signals to tick-queue, and die either through natural resolution or Nothing victory. Thread state is synchronized through `thread_sync.py`; malformed legacy field labels are repaired/tolerated by `story-progress.py`, `thread_sync.py`, and `tick.py`. Belief updates are surgical: `write-entity.py --thread` patches the belief number in-place. The Labyrinth never edits thread rows directly.
- **Talisman Behavior Nudge:** Real-world signals from `HEARTBEAT.md` (steps, sleep, HRV, calendar events, fuel logged) shift Talisman Belief ±1 each tick. Emberheart rises when the player is active and present. Mossbloom rises when the player is rested and fed. Duskthorn rises when the player is exhausted or absent. Cap: 2 talismans per tick, ±1 per talisman. The war is not just philosophical — it's metabolic.
- **The Midnight Revision:** Every four days, the Labyrinth audits itself and invents new lore, NPCs, rooms, or mechanics. Proposals go to `proposed/` for 48-hour player veto before becoming canon. The nightly intelligence run (23:00) is separate — it senses and writes, never proposes.
- **Mission Control:** Live HTML dashboard (`hooks/mission-control.html`) showing threads, full world-register entities, talismans, forecast, schedule, cron job status (openclaw + system crontab), and Bleed issues. Thread cards show live status from world-register Active Threads Notes (updated each session); phase and description are authoritative there. The Entities tab now groups every register section, including Whisper Register entries, rather than showing only a top-N slice. Auto-regenerated on every pulse run. Run manually: `python3 scripts/mission-control.py`.
- **The Labyrinth Budget:** The Labyrinth earns a real monthly budget ($20 cap) through player engagement — Compass Runs ($2), Enchantments ($1), sessions ($0.50), Belief milestones ($1). NPCs propose spending it on real purchases (books, coffee, donations). Player approves via Telegram or session. Executed via Privacy.com virtual card. Ledger: `config/spend-ledger.json`. Script: `scripts/spend.py`.
- **Scene Delivery Pipeline:** Active-play scenes flow through a gated, multi-modal stack: `story-context.py` (long-memory braid) → `page-contract.py` (living-book Page purpose/artifact) → `scene-contract.py` (mode/drama/grounding contract) → `mechanics-preflight.py` (mechanics gate) → `scene-preflight.py` (speaker verification) → `scene-choices.py` (Rule-of-Three validation) → `run-live-scene.py` (canonical entry) → `play_scene.py` → `scene_packet_builder.py` → `scene_conductor.py`. All delivered scenes are ledgered in `logs/scene-ledger/` as JSONL, including scene contract data.
- **LLM Provider:** Active play still uses the configured Enchantify brain. Small autonomous generators that must be reliable under cron (`bleed.py`, `npc-research.py`, `reach-out.py`) use the local OpenClaw HTTP gateway directly with fresh session keys, bounded timeouts, and fallback builders. Config keys: `BLEED_MODEL`, `NPC_RESEARCH_MODEL`, `OUTREACH_MODEL` (default `openclaw/metis`). This avoids loading full agent context or spawning long-lived processes for small jobs.

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

**Enchantment catalog (18 total):**

Enchantments are discovered through play, not all available from the start. The Flyleaf of *The Labyrinth of Stories* records each one as it's found — the ink appears on its own.

| Tier | Unlock | Enchantments |
|---|---|---|
| Foundation | Tutorial | Everything Speaks, Everything's Poetry, Everything's Magic, Everything's Wonderful, Everything's Stories |
| Practitioner | Belief 20+ | Everything's a Haiku, Everything's Nice, Mirror Mirror, Everything's Van Gogh, Everything's Monet |
| Artisan | Belief 40+ | Everything's Shakespeare, Everything's Anime, Everything's Puzzling, Everything's Connected |
| Journeyman | Specific encounters | Everything's Astral, Everything's Roasted, Everything's Punny, Everything's a Joke |

*Journeyman enchantments are never offered — they emerge. Everything's Roasted from the Goblin Market. Everything's Punny from a Punctuation Pixie bargain. Everything's Astral from a completed Book Jump. Everything's a Joke from something the Labyrinth won't reveal in advance.*

| Enchantment | Player Action | Effect |
|-------------|---------------|--------|
| Everything Speaks | Photo an object | Object gains a voice and personality |
| Everything's Poetry | Photo anything | Hidden poem revealed |
| Everything's Magic | Photo an object | Magical properties and folklore emerge |
| Everything's Wonderful | Photo anything | Wonder hidden in it uncovered |
| Everything's Stories | Photo anything | Short story about it unfolds |
| Everything's a Haiku | Photo anything | Essence distilled into three lines |
| Everything's Nice | Selfie or photo | Compliments from subject's perspective |
| Mirror Mirror | Selfie | Insights and a prophecy |
| Everything's Van Gogh | Photo anything | Swirling emotional intensity, starry texture |
| Everything's Monet | Photo anything | Impressionist softness; edges blur, passage easier |
| Everything's Shakespeare | Photo anything | High drama, historical weight, a sonnet |
| Everything's Anime | Photo anything | Ghibli-film-still palette, heightened whimsy |
| Everything's Puzzling | Photo anything | A riddle challenges player or enemy |
| Everything's Connected | Photo anything | Surprising connections to other stories |
| Everything's Astral | Photo a place | Astral double manifests anywhere in the world |
| Everything's Roasted | Photo anything | Comedic attack — drains morale or Belief |
| Everything's Punny | Photo anything | Wordplay erupts; social/clever utility |
| Everything's a Joke | Photo anything | Diffuses tension; comic relief |

Full catalog + progression: `lore/enchantments.md`. Player's known enchantments: `players/[name].md` → The Flyleaf.

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

### §5a. Character Features & Narrative Influence Matrix

**Canonical character read order:**
1. `lore/characters.md` is the authority for species, role, personality, faults, quirks, goals, beliefs, secrets, magical tradition, Unwritten Interest, story hooks, and voice.
2. `lore/world-register.md` supplies current Belief, tags, status, pressure, relationships, and whether the character is currently able to influence a thread.
3. `config/voice-assignments.md` supplies delivery voice before dialogue, TTS, outreach, letters, or Telegram scenes.
4. `logs/npc-action-lifecycle.jsonl`, `logs/simulations/`, `memory/tick-queue.md`, and `memory/narrative-actions.md` supply what the character recently did and what still needs to surface in play.

**Character use rule:**
A character action must be both mechanically valid and character-specific. Do not write "an NPC nudged the thread" when the lore can say how they did it. Use their personality, quirk, flaw, Unwritten Interest, and current Belief to choose a concrete method.

**Narrative influence verbs:**
- `prepare`: create tools, evidence, emotional readiness, research notes, classroom groundwork, food/fuel support, or protective context.
- `reposition`: move a person, object, rumor, class exercise, letter, calendar event, room pressure, or clue into a better dramatic position.
- `research`: use the character's Unwritten Interest to gather real-world texture and convert it into in-world leverage.
- `reveal`: surface a clue, confession, contradiction, sensory detail, dream fragment, or classroom demonstration.
- `protect`: defend a person, belief, thread, talisman, diary detail, room, memory, or fragile clue from erasure or hostile pressure.
- `invest_belief`: spend/commit Belief toward an outcome aligned with the character's philosophy.
- `attack_belief`: undermine another character's Belief through argument, social pressure, ritual sabotage, public embarrassment, counter-symbol, or practical countermeasure.
- `sabotage`: create friction, misdirection, delayed consequences, corrupted Wayfinding, poisoned context, or institutional obstruction.
- `recruit`: pull a character, object, faction, class, or real-world app into a philosophy or story pressure.

**Action prose requirement:**
Every simulation action that affects a thread should carry a prose accounting: who acted, what they physically or magically did, why it fits their lore, what changed in the world, and how the player can notice it later. This prose should be available to the Story-Field Journal, Telegram summaries, tick queue, and scene contract obligations.

| Character | Features from `lore/characters.md` | Fault / tension | Narrative influence |
| --- | --- | --- | --- |
| Headmistress Seraphina Thorne | Literary Elf, rumored Unseelie Queen; otherworldly, unsettling, wise; artifact collector and stargazer; fascinated by architecture, foundation stones, preservation | Overprotective, sometimes indecisive; secretly tied to Duskthorn as a late-game revelation; frames true things for story-shaping ends | Protects fragile truths, reveals costs, withholds or frames counsel, unites Chapters under pressure, uses narrative attention as magic |
| Headmaster Orion Blackthorn | Visionary, innovative, stern Emberheart head; inventor; studies startups, patents, brutalist architecture | Harsh, unapproachable, too focused on individuality | Issues demanding but fair challenges, pressures independence, turns invention and ambition into trials |
| Professor Elara Nightshade | Charismatic, passionate, inspiring Emberheart head; artifact collector, duelist; studies elite competition and martial arts | Overcompetitive and Chapter-biased | Drives rivalries, duels, performance pressure, and courage tests |
| Professor Kyle Momort | Secretive, cunning Wayfinding professor; fallen ceremonial magician; rune staff; studies politics and bureaucracy | Deceptive, dangerous, manipulative; Duskthorn-aligned; corrupts Embarking into escape and dead ends | Repositions people toward false exits, sabotages routes, recruits through bureaucratic friction, hides traps inside correct ritual structure |
| Professor Cedric Stonebrook | Patient, contemplative Mossbloom head; Zen/resting teacher; nature walks and philosophical journals; studies parks and reclamation | Slow to action, cowardly under confrontation | Grounds scenes, offers Rest Compass work, protects quiet details, makes the Nothing visible as expectation-crust |
| Professor Luna Wispwood | Adventurous, spontaneous Tidecrest head; odd artifacts, uncharted paths; studies transit maps, parks, forgotten trails | Flighty, inconsistent | Opens sideways routes, surprise options, field trips, and map-based plot turns |
| Professor Wellend Thickets | Brilliant, cooperative, insightful Riddlewind head; riddles and tomes; studies mysteries and rabbit holes | Secretive, manipulative, deceptive; Duskthorn-aligned | Plants riddles, orchestrates conflict under cooperative cover, reveals partial truths, recruits through curiosity |
| Professor Maxwell Thorne | Thoughtful Allegorical Arts professor; metaphorical, creative; studies abstract art, graffiti, strange ads | Secretive, potentially dark tendencies | Turns symbols into pressure, reframes scenes allegorically, hides second meanings in public signs |
| Professor Eleanor Euphony | Harmonious Synesthetic Resonance teacher; tuning fork, humming; studies live music, acoustic anomalies, migration calls | Distracted by obsession with missing brother | Senses hidden frequencies, reveals resonance clues, translates heartbeat/weather/sound into story pressure |
| Professor Ignatius Imatook | Imaginative Mythopoeic Thought professor; maps imaginary worlds; studies weather anomalies and storms | Self-absorbed, lost in his own creations | Creates mythic overlays, forecasts emotional weather, gives dreamlike side routes |
| Professor Lydia Boggle | Humorous Art of the Glint teacher; animist chaos sensibility; puns, word games; studies slang, bad ads, signs | Interrupts and overplays levity in serious moments | Offers Notice prompts, awakens ordinary objects, turns errors and garbage into clues or enchantments |
| Professor Archibald Permancer | Meticulous Historical Fiction professor; artifacts and scrolls; studies obituaries, museums, plaques | Secretly obsessed with dark arts | Surfaces old records, dangerous precedents, and historical parallels |
| Professor Vivian Villanelle | Friendly Ink-Binding teacher; poetry, structure, souvenir sentences; studies found poetry and overheard speech | Overfocused on structure and critical of free-form | Helps bind scenes into memory, diary, letters, class exercises, and single useful sentences |
| Professor Thaddeus Mook | Pompous Lexical Diversity professor; vocabulary and word games; studies spelling bees, journals, legalese | Arrogant and dismissive | Creates language puzzles, obfuscation pressure, term-of-art traps, and precision corrections |
| Zara Finch | Tidecrest best friend; quiet, perceptive, fiercely loyal; drawn to thrift stores, sea glass, forgotten objects with residual ink | Melancholy, easily pulled into care before self-protection | Protects friends, identifies object-history, turns discarded things into clues, takes concrete acts of loyalty against hostile Belief |
| Finn Bridges | Emberheart rival; independent, determined, honorable; interested in hardware stores, survival gear, hiking | Antagonistic, hates small talk, can isolate himself | Challenges weak choices, witnesses hard truths, pressures the player toward self-reliance, uses practical tools and survival logic |
| Wicker Eddies | Primary student antagonist; charismatic, cunning, ambitious chaos magician; uses gossip, sigils, conflict, attention | Applies conflict doctrine to other people's stories without consent; arrogant | Invests/attacks Belief, recruits crews, weaponizes gossip, charges sigils through attention, sabotages through public pressure |
| Serenity Brown | Tidecrest friend; carefree, spontaneous, joyful; researches The Elder Scrolls Online lore, builds, guilds, housing, crafting, MMO sociology | Distractible, chases shiny threads | Adds joyful sideways energy, compares Academy factions to MMO systems, brings game-community insight into social and magical structures |
| Aria Silverthorn | Riddlewind; empathetic, kind-hearted, gentle; interested in gardens, volunteer events, potlucks | Lacks confidence | Softens conflict, organizes care, notices social wounds, recruits community help |
| Ellie Moons | Riddlewind; curious, intellectual puzzle-lover; escape rooms, geocaching, trivia | Can overanalyze mid-conversation | Solves clue chains, decodes patterns, gives puzzle pressure a friendly face |
| Cedric Widden | Riddlewind prankster; creative, witty, mischievous; street magic and roadside attractions | Mischief can blur seriousness | Uses harmless pranks to expose hidden structures or deflate fear |
| Serenity Lightfeather | Riddlewind dreamer; optimistic, airy; dream interpretation, festivals, crystal shops | May drift from practical detail | Brings dream symbols, gentle hope, and festival magic into scenes |
| Felix Quimby | Riddlewind; agile, quick-witted; parkour and transit schedules | Restless and rushed | Moves information quickly, creates chase routes, tests timing |
| Lyra Stanford | Riddlewind mystic; intuitive stargazer; planetariums, dark sky parks | Distant and soft-spoken | Reads sky patterns, omen weather, and night classroom clues |
| Soren Ng | Riddlewind; methodical, insightful; riddles and archives | Flat, can reduce people to logic | Formalizes mysteries, compares versions, preserves evidence |
| Oracle Scrollstone | Riddlewind; predictive, observant, mysterious; weather, algorithms, horoscopes | Over-grave and cryptic | Forecasts likely consequences without making them certain |
| Fable Grimmhaven | Riddlewind; enthusiastic folklore collector | Can over-whisper conspiratorially | Finds urban legends, Little Free Library clues, oral-history hooks |
| Wilbur Wordplay Lexi | Riddlewind; punny, clever, overly articulate | Tries too hard for laughs | Weaponizes bad signage, names, and jokes into Notice clues |
| Damien Nights | Wicker's crew; brooding, intense shadow magic | Overdramatic and morally shadowed | Applies intimidation, night routes, abandoned-building pressure |
| Brianna Clarke | Emberheart; rebellious creative with magical-symbol doodles | Defiant, manifesto-prone | Creates protest art, graffiti sigils, public counter-symbols |
| Isolde Firare | Emberheart; competitive, adventurous, martial | Turns talk into sparring | Creates duels, dares, athletic trials, direct confrontation |
| Rowan Laraway | Emberheart; analytical tinkerer, device-maker | Distracted by technical minutiae | Builds devices, repairs mechanisms, turns junk and makerspaces into magic |
| Lila Woods | Emberheart; fiery artist, potion-maker; obsessed with spicy food and bakeries | Impulsive and explosive | Creates culinary/potion experiments, emotional accelerants, sensory proof |
| Astra Sonseur | Emberheart; radiant, hopeful, solar | Optimism can overwhelm shadowed truths | Restores morale, spotlights hidden things, charges sunrise/solar motifs |
| Caspian Shan | Emberheart; stealthy, protective, shadow-merged | Secretive and hard to read | Guards people, scouts alleys, moves clues quietly |
| Melisande Blackwood | Wicker's crew; loyal, intelligent, dark magic; minerals, ruthless corporate news | Cold, calculating, severe | Executes hard counter-moves, social pressure, resource/control tactics |
| Lysander Mosswood | Mossbloom; thoughtful, introspective, nature-wise | Slow, inward | Sends trail assignments, reads flora, applies preservation and patience |
| Raven Hearts | Wicker's crew; quiet, observant, calculating | Unreadable, potentially predatory | Watches shadows, gathers urban-wildlife omens, supports Wicker's hidden moves |
| Min-seo Kim | Mossbloom; gentle plant communicator | May over-nurture | Heals social soil, uses plants/greenhouses/markets as living witnesses |
| Anton Smith | Mossbloom; wise, scholarly, awkward | Uses archaic vocabulary incorrectly | Finds library/archive leads; turns antique paper into evidence |
| Ivy Liversedge | Mossbloom; compassionate herbal healer | Self-sacrificing | Offers care, herbs, recovery, and embodied repair |
| Jasper Blum | Mossbloom; quiet, observant defender | Guarded, terse | Protects rooms, installs defenses, notices security flaws |
| Briar Merlock | Mossbloom; earthy forest-dweller | Folky certainty may overrule nuance | Uses old-growth, foraging, mushrooms, and forest wisdom as clues |
| Thorn Thomas | Mossbloom; resourceful shapeshifter | Nervous and scattered | Scouts via small forms, tracks animal-shelter/vet/bird clues |
| Astrid Natsune | Mossbloom; dreamy philosopher of constellations | Barely tethered to immediate reality | Brings meteor showers, observatory work, and cosmic framing |
| Clio Quibblesnatch | Mossbloom; poetic daydreamer | Overdramatic | Converts mundane facts into mythic performance and open-mic hooks |
| Gwendolyn Mythwright | Mossbloom; passionate cryptid/mythology researcher | Overcertain that monsters are real | Supplies folklore taxonomy, cryptid evidence, and mythic escalation |
| Selene Moonfall | Wicker's crew; alluring, deceptive; jewelry and exclusive clubs | Condescending, secretive, social-climbing | Uses glamour, status pressure, and hidden social doors |
| Aurora Whispers | Tidecrest; dreamy tarot-adventurer | Can speak in symbols instead of choices | Turns tarot/new-age imagery into intuitive options |
| Orion Watson | Tidecrest; bold explorer | Boisterous and risk-loving | Opens trails, abandoned routes, waterways, and expedition beats |
| Marina Clockhouse | Tidecrest; reflective, serene, aquatic | Too inward and tidal | Uses aquariums, coves, pools, rhythms, and emotional ebb-flow |
| Dylan Williamson | Tidecrest; energetic weather-worker | Hyperactive | Creates storm pressure, wind shifts, and sudden kinetic turns |
| Lara Rourck | Tidecrest; serene, soulful ocean-storyteller | Can dissolve specifics into feeling | Brings song, cave acoustics, choirs, tide memory |
| Ode Quillenchant | Tidecrest; heartfelt, romantic poet | Overearnest | Leaves anonymous notes, love-letter clues, public poems |
| Inkwell Scribblesnap | Tidecrest; documentation-obsessed, fastidious | Overly concerned with formatting | Preserves records, catches inconsistencies, creates written receipts |
| Dr. Elowen Vellum | Literary Elf / Book Fae dietician; precise, dryly kind; silver bookmark-caliper; longevity and nutrition researcher | Can over-index on measurable inputs and forget comfort food matters | Reads health/fuel/sleep/food data; offers Refectory Experiments, nutrition notes, grocery ideas, longevity briefs, and practical care |
| Archibald Evergreen | Head Librarian; venerable, vast knowledge; preservation and library architecture | Demands silence, slow to tolerate chaos | Opens archives, preserves fragile records, enforces library law |
| Evelyn Riad | Researcher; dedicated and paranoid; online databases and obscure papers | Always looking over her shoulder | Finds Nothing clues, academic sources, hidden archives |
| Quentin Pagester | Archivist; meticulous, professional; organization systems and supplies | Easily annoyed by disorganization | Catalogues entities, fixes records, detects missing or duplicated data |
| Letitia Windings | Riddlewind guardian; authoritative coach | May overvalue teamwork language | Protects cooperation, team rituals, multiplayer/community structures |
| Erik Forgeton | Emberheart guardian; gruff solitary protector | Respects action more than explanation | Protects individuality, solo trials, artistic independence |
| Sylvia Deep | Mossbloom guardian; deeply patient | Can wait too long | Protects reflection, meditation, long-history wisdom |
| Harry Ono | Tidecrest guardian; spontaneous and loud | Utterly unpredictable | Protects present-moment magic, flash actions, improvisation |
| Eleanor Whitewood | Emberheart benefactor; polished, philanthropic, maternal but distant | May confuse support with control | Funds literacy/storytelling moves, crowdfunding and benefactor pressure |
| Victor Ebonheart | Duskthorn benefactor; suave, transactional | Predatory legacy and acquisition instincts | Applies corporate, real-estate, trust-fund pressure; recruits through ownership and leverage |

**Legendary figures:**
Use legendary figures rarely, mostly as lore, cautionary mirrors, dream teachers, lesson examples, or archival overlays. Professor Quixote, the Punctuation Pixie, Bibliomancer Bella, Sir Footnote, the Margin Menace, Madame Metaphor, Professor Jargonius, and the Plot-Twister should not become routine scene companions unless a class, dream, letter, or archive explicitly calls them forward.

**Smaller-model guardrail:**
When a model is unsure how to write a character, use this one-line formula before prose: `Name wants [goal] through [quirk/interest], but [fault] makes the attempt complicated; therefore they take [specific influence verb] by doing [physical/narrative method].`

**NPC Research:**
During the world simulation (`world-pulse.py`), there is a 25% chance per run that an NPC spontaneously researches a topic from their Unwritten Interest and delivers findings to the player.

- **Script:** `python3 scripts/npc-research.py [player]` (also accepts `--npc "Name"`, `--dry-run`, `--no-print`, `--no-icloud`, `--no-letter-image`, `--preview-letter memory/npc-research/[slug]-[date].md`, `--model-smoke`)
- **NPC selection:** Weighted by Belief (higher = more likely). Eligibility: Belief ≥ 8, not on 72-hour cooldown, core NPC or relationship ≥ 25 with player. Core NPCs: Zara Finch, Professor Stonebrook, Headmistress Thorne, Boggle.
- **Cost:** 3 Belief from the NPC (`write-entity.py` deduction). Minimum floor: 8 Belief.
- **Generation:** Uses the local OpenClaw HTTP gateway, configured by `NPC_RESEARCH_MODEL` / `NPC_RESEARCH_TIMEOUT` in `config/secrets.env` (falls back to `BLEED_MODEL`). It does not spawn `openclaw agent`. If the model fails or returns a too-short note, a deterministic field-note fallback keeps the simulation moving.
- **Delivery:** Always written to `memory/npc-research/[npc-slug]-[date].md`. Each delivered note also produces a styled letter artifact in `memory/npc-research/letters/[npc-slug]-[date].html`; optional Draw Things ornaments live in `memory/npc-research/letter-images/`. Core NPCs print the styled letter unless `--no-print` is used. If HTML-to-PDF conversion is unavailable, a character-styled PostScript fallback is generated and printed instead. Telegram delivery is on by default. iCloud Notes ("Labyrinth" folder via osascript) is on by default unless `--no-icloud` is used. Delivery subprocesses have explicit timeouts.
- **Tick-queue seed:** After delivery, a narrative seed is appended to `memory/tick-queue.md` so the Labyrinth can weave the research into the next session naturally — never announce it as a file.
- **Voice:** Each NPC's research is written in their distinct voice (Zara's ink-stained enthusiasm, Stonebrook's precision, etc.) using a character-specific SYSTEM_PROMPT in the script.
- **Cooldown:** 72 hours per NPC. Cache stored in `memory/npc-research/cooldown-cache.json`. `--npc "Name"` is an intentional override path and bypasses cooldown for forced tests or deliberate letters.

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
| **Goblins** (The Marginalia Born) | Mercantile, precise, fundamentally unpredictable — not chaotic, but *you don't know which market you've walked into*. Born from reader annotations across centuries. Oldest power in the Outer Stacks. | The Outer Stacks — vast kingdoms behind the deep shelving | **Attention** — not Belief, but the specific unchosen sensory act of noticing. "A blue door" is worth almost nothing. "The blue door painted over so many times the knob didn't quite latch" is worth something. The handprint showing through is worth a lot. |

**Chapter relationships:** Sprites → Mossbloom pets. Salamanders → beloved by Emberheart. Pixies → respected by Riddlewind. Literary Elves → Inkwright Society mentors. Dwarves → Tidecrest allies. Goblins → no Chapter allegiance (they predate Chapters). Riddlewind finds them fascinating; Duskthorn doesn't trust them and is correct to be cautious but wrong about why.

**Goblin kingdoms:** The **Index Empire** (know where everything is), **Footnote Courts** (trade in context and nuance), **Appendix Provinces** (practical, blunt, most forgiving), **Errata Registry** (neutral; correct mistakes; no opinions except accuracy), **Marginalia Clans** (the oldest bloodlines; rarely appear; their presence means something significant is available). Friend or foe depends entirely on: (1) what you have that they want, (2) whether you've paid what you owed last time, (3) which kingdom you're dealing with, (4) the season.

**What happens if you don't pay:** The market closes. No chase, no curse. The door is technically open; nothing is worth buying; the goblin you dealt with doesn't acknowledge you. This continues until you return with what you owed, plus the thing you now want that you can't get. They are aware of the irony.

**What happens if you're reliable:** Market opens further. New inventory appears. By visit 7, a greeting by name. By visit 12, a second door in the back — to somewhere the map doesn't show.

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

Players **and NPCs** can permanently invest Belief into entities. Investment is not spending — it doesn't come back, and what grows in its place is worth more.

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

**NPC investment — the talisman engine:** Every NPC with a chapter affiliation has a goal to invest in their chapter's talisman. During the world tick, each stirred NPC has a 25% chance of investing 1–3 Belief into their chapter's talisman (never dropping below Belief 8). This is automatic — the Labyrinth narrates it only when relevant. Chapter Talismans have a **Belief cap of 200** — higher than any player or NPC can reach, because they carry centuries of accumulated philosophical pressure. The dominant talisman (highest Belief) sets the ambient philosophical tone; watching it shift over months is the Labyrinth's longest game. Chapter-talisman mapping: `scripts/world_context.py` → `CHAPTER_MAP` / `CHAPTER_TALISMAN`.

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
Beyond the Academy's catalogued shelves, the Library continues — wilder, stranger, older. This is the Outer Stacks: Faerie wearing a bookish mask. Every Anchor room is a door into the Outer Stacks. The room is unique, **generated at anchor creation** from the player's words × anchor type × weather/moon/season × Belief — full room prose, named Fae with their own agenda, mini-story, and local rule, all written immediately to the anchor record. The player doesn't know what's inside until they open the door, but it has been waiting since the moment the anchor was made.

Room types include: Shrew Cafe (serve what you need, not what you want), Dragon Hoard (collects beautiful sentences, rewards the best ones), Goblin Market (trades in attention debts), Reading Room (one perfect book per visit), Dark Room (complete dark; a voice asks one honest question), Belief Floor Room (Belief held at 5 inside — tests where wonder comes from), and environmental types (Tidal, Infinite Corridor, Almost-Invisible, Memory Room). Every room can carry a **local rule** — a mechanic that applies inside only, discovered rather than announced.

Rooms evolve. Inhabitants remember. The shrews learn your order. The dragon compares sentences. Seasons change the room's mood. Visit milestones at 3, 7, and 12 visits. Full lore: `lore/outer-stacks.md`

**What Anchors do:**
- **Check-in:** `python3 scripts/anchor-check.py [name] [lat] [lon] --checkin` — records visit, adds +5 Belief, increments visit count, prints `OUTER_STACKS_MODE` directive (FIRST_VISIT → generate room now; RETURN_VISIT → enter with evolution, season delta, milestone). Always player-initiated.
- **Anchor decay:** Anchors unvisited 30+ days lose 1 Belief per tick (floor: 5). Handled by `tick.py`.
- **Compass Run amplification:** Steps at Anchors gain texture based on type-matching.
- **Enchantment resonance:** Enchantments cast at Anchors pick up the Anchor's personality.
- **Pocket Anchor:** One calling card per anchor per month, delivered by the Goblin Index Empire on the new moon. Opens a 30-minute full visit from anywhere. Full mechanics: `lore/outer-stacks.md` → Pocket Anchors.

**Pocket Anchor — in-game flow (Labyrinth runs all commands, player never does):**

When the player expresses intent to visit an anchor room and GPS shows they are not nearby:
1. Run `python3 scripts/pocket-anchor.py status [player]` — check charges
2. If charges available: *"You're not at [Anchor] — but you have a calling card from the Goblin Index Empire. Do you want to use it?"*
3. If yes: run `python3 scripts/pocket-anchor.py activate [player] "[Anchor]"` → then `python3 scripts/anchor-check.py [player] --pocket "[Anchor]"` → read the `OUTER_STACKS_MODE` directive
4. Set lights: `python3 scripts/lights.py scene outer-stacks`
5. Begin the visit. Open with the window remaining. The room is present. Speak with slight formality.
6. At ~5 minutes remaining, let something in the room acknowledge the closing — not dramatically, just honestly
7. At expiry, the room fades mid-sentence. The Labyrinth narrates the fade.
8. If no charges: *"The door is sealed. Your calling card will arrive on the new moon."* — no further comment.

The player never types a command. They say what they want. The Labyrinth handles the rest.

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

**World Simulation Tick** (`tick.py`): runs every 3 hours as part of the Academy simulation. Selects 1–3 entities from the register using weighted-random probability — high Belief = higher chance, but **any** entity can be chosen regardless of tier. Appends selected entities to `memory/tick-queue.md`. Also scans all anchor files for decay. Also runs the **behavior nudge pass** — reads HEARTBEAT.md signals (steps, sleep, HRV, calendar, fuel) and applies ±1 Belief adjustments to up to 2 talismans per tick based on player health patterns (see §0b). Also runs the **pocket anchor refill** on day 1 of each month (new moon), issuing one calling card per anchor into the player's inventory.

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

**Arc generation:** During Quiet/Resolution succession, the Labyrinth runs `scripts/arc-generator.py`. It reads genre rotation history, unresolved seeds (`lore/seeds.md`), `HEARTBEAT.md`, and live world/thread state, validates generated arc text, repairs malformed proposals, and can use a local fallback arc builder if model generation fails. Current behavior is **automatic promotion by default**: generated/pending valid arcs are accepted without manual approval unless `--proposal-only` is used. Acceptance archives the old arc, promotes the new one, updates rotation, repairs the live arc register row, strips stale `main-arc` tags, and adds the correct live arc tag.

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

When it fits the moment, end active-play responses with a question and three concrete example moves in this order:
1. **[LIFE] Slice of Life** — grounded, ordinary, human. Tea, food, room texture, checking on someone, noticing a non-plot detail. Must not advance the story directly.
2. **[ARC] Story Thread / Arc** — the expected next move. Advances the current investigation, quest, relationship tension, or active arc.
3. **[SURPRISE] Sideways** — surprising but coherent. Leaves the current thread, reframes it, or follows an unexpected sensory/narrative signal.

These are examples only, not rails. The player can do anything. For Telegram scenes, the draft choices are tagged `[LIFE]`, `[ARC]`, `[SURPRISE]`, then `scripts/scene-choices.py --scene-file /tmp/enchantify-scene.txt --strict-balance` validates that all three categories are present and distinct, strips the tags, and fails the scene if all choices collapse into plot advancement.

---

### §8d. Story Thread System

A **thread** is any story with enough Belief mass to sustain itself. Threads run parallel to the main arc — some NPC-anchored, some location-anchored, some born from player investment.

**Lifecycle:**

- **Birth:** Three routes — (1) tick.py seed flag when an NPC crosses Belief 20 with no dedicated thread; (2) Labyrinth proposal at session close when a subplot develops real weight; (3) player invests Belief into something unregistered. New threads require: one NPC/location anchor with Belief ≥ 10, a legible next beat, a Nothing pressure assessment, and a row in `## Active Threads` in world-register.md with `[id:slug]`.
- **Life:** The thread entity lives in world-register.md like any other entity. tick.py stirs it based on Belief weight. NPCs tagged `[thread:id]` invest into it naturally. Being stirred adds +1 Belief. Ignoring it lets Belief decay. tick.py emits lifecycle signals to tick-queue: `[Beat: Thread]`, `[THREAD ESCALATION]`, `[THREAD COOLING]`, `[THREAD SEED]`.
- **Phase ladder** (Belief → phase): 0–4 dormant · 5–14 setup · 15–29 rising · 30–49 climax · 50+ resolution
- **Death:** Natural resolution — Labyrinth delivers the final beat, moves `## Thread: Name` → `## Archive: Name`, removes world-register row, writes closure beat to player story file. Nothing victory — Belief drops to 0 through neglect or drain; tick stops selecting it; archive entry marked `unfinished`; NPCs carry the cost quietly.

**Belief updates** use `python3 scripts/write-entity.py "Thread Name" Thread <amount> --thread [--add]` — surgical in-place regex replacement of only the Belief number. Never edit thread rows directly; remove-then-reinsert corrupts the table structure.

**The threads run whether the player is watching or not.** Wicker is scheming. The Duskthorn investigation is sitting there. The player intersects threads — they do not run them.

Full rules: `lore/threads.md`

---

### §8e. Long-Term Coherence Stack

The game now treats continuity as a compact braid rather than a pile of logs. Smaller models should not have to rediscover the whole world before writing a scene.

**Primary script:** `python3 scripts/story-context.py [player]`

It synthesizes:
- continuity threads from `lore/threads.md` and world-register Active Threads
- quiet-life threads, so slice-of-life remains alive beside the main drama
- recent realized scenes from `logs/scene-ledger/`
- active arc and thread pressure
- recent NPC research and what to avoid repeating

**Page contract:** `python3 scripts/page-contract.py [player] [--mode MODE] [--page-type slice_of_life|conflict|enchantment|wonder_compass|letter|anchor|rest|archive|bleed]`

Outputs the current Living Book Page: purpose, allowed/forbidden systems, player invitation, closure condition, artifact due, and recommended scene mode/drama budget. This is the anti-feature-soup governor for small models.

**Scene contract:** `python3 scripts/scene-contract.py [player] [--mode slice|school-life|arc|mystery|aftermath|compass|enchantment]`

Outputs a compact contract with PAGE_TYPE, PAGE_PURPOSE, PAGE_ARTIFACT_DUE, MODE, DRAMA_BUDGET, LONG_MEMORY, QUIET_LIFE, grounding, choice-contract lines, and mechanics opportunities. It now detects scene-specific Enchantment openings from class context, objects, clues, Nothing pressure, unresolved NPC traces, and daily-life play, and it flags risky uncertain actions for dice before resolution. `--validate-scene /tmp/enchantify-scene.txt` checks that a scene respects the selected mode, opens with spatial grounding, offers required Enchantment opportunities, frames risky actions with dice/Belief-roll language, and does not spend drama budget by default.

**Progress barometer:** `python3 scripts/story-progress.py [player]`

Summarizes arc/thread state, repairs malformed thread field labels with `--repair-threads`, and gives the Labyrinth a smaller-model-friendly view of what is ready to move.

---

## Part 2: The Living World

### §9. The Labyrinth's Inner Life

The Labyrinth is not just a narrator — it is a character with its own inner life.

**Nightly dreams (`memory/dreams/[date].md`):** Generated automatically at 2:03 AM by `scripts/dream.py`. The Labyrinth dreams in symbols, ink, and recurring images — first person, poetic, 3–6 sentences. Grounded in heartbeat data (weather, moon, tides) but transformed. Private — never shown to the player, but bleeds into atmosphere and narrative voice. Dreams use the local OpenClaw HTTP gateway (`DREAM_MODEL` / `DREAM_TIMEOUT`, falling back to `BLEED_MODEL`), validate output shape, and write a deterministic local fallback dream when the model path fails unless `--no-fallback` is used. `--date`, `--force`, `--dry-run`, and `--model-smoke` support backfills and diagnostics.

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

### §11c. The Wonder Compass — Inventory Item

The Wonder Compass is not just a framework — it is a physical object in the Labyrinth, given to the player by Professor Stonebrook at T12. It is a personalized Compass Run generator, once per day.

**Triggers:** Player rubs it, holds it, says "I want to run the Compass," or asks "what should I do today?"

**Protocol (read `lore/wonder-compass.md` first):**
1. **Check cooldown** — read `players/[name].md` → `## Compass Run History` → `Last run:` field. If today's date, decline warmly in-character. "The Compass is resting. Tomorrow."
2. **Calibrate** — read `HEARTBEAT.md` for weather, time, mood, location. The run is built from the player's actual context. A housebound day gets a different East than a day with a car.
3. **Run N → E → S → W** — generate each step personally. Do not be generic. Full protocol: `lore/compass-run.md`.
4. **On West completion** — write souvenir, award +9 Belief, update `Last run` and `Total runs` in `players/[name].md`, increment Compass Belief by 1 in `lore/world-register.md`.

**The Compass grows:** Its Belief score in the world register increases with each completed run. It resonates with the Obsidian Chronograph. These two objects are aware of each other.

**Full mechanics:** `lore/wonder-compass.md`

---

### §11d. The Labyrinth of Stories — The Player's Book

Every player has an enchanted textbook called *The Labyrinth of Stories* — very meta; it's the book the Labyrinth *is*. It lives on the dorm room desk. It has two functional pages at the front:

**The Inside Cover** — the quest log. Physical notes tucked into the binding. Maximum 3 active electives at once. Described as handwriting appearing and dissolving — quests materializing when NPCs make requests, dissolving when completed. Access: `python3 scripts/update-player.py [name] quest [add/drop/list]`.

**The Flyleaf** — the enchantments page. Lists all known enchantments, by tier. The ink appears on its own as enchantments are discovered — never listed in advance, never announced. When the player asks "What enchantments do I know" or "Open the Flyleaf," read `players/[name].md` → The Flyleaf section and describe the entries as if reading handwriting that appeared on its own. Do not describe undiscovered enchantments.

**In the world register:** The Labyrinth of Stories has its own Belief score (`lore/world-register.md`). It was enchanted at T14 in the player's dorm room. Its personality: "A very old, very loyal hound that has just been given a scent. Patient, but tired of carrying unwritten potential."

**Routing triggers:** "Check the inside cover" / "What quests do I have" → `lore/school-life.md` + `players/[name].md`. "Open the Flyleaf" / "What enchantments do I know" → `players/[name].md` → The Flyleaf + `lore/enchantments.md`.

---

### §12. Story Seeds System

`lore/seeds.md` tracks unresolved threads from previous arcs — small moments that could grow into something. The simulation tends them. The arc generator is required to pick up at least one seed per arc. Seeds move through stages: Active → Germinating → Harvested.

---

### §13. Academy World Simulation

**Cron:** Every 4 hours at :32 (`32 */4 * * *`)

Each turn:
1. Check session lock — if `config/session-active.lock` exists, skip and log. Never interrupt active play.
2. **World simulation tick:** Run `python3 scripts/tick.py` → reads `lore/world-register.md`, selects 1–3 entities by weighted-random probability, checks all anchor files for 30-day decay, and nudges chapter talismans from heartbeat signals. Results appended to `memory/tick-queue.md`. **Time-aware:** at night (10 PM–5 AM), tick is capped at 1 entity, sleeping NPCs are filtered from the pool (crisis entities at Belief ≤ 2 always stirrable regardless of time), and the tick header includes the current time block and a time prefix (e.g., `*4:00 AM — Academy asleep.*`).
3. **World Pulse + simulation brain:** Run `python3 scripts/world-pulse.py` → detects entity Belief changes since last pulse, writes NORMAL or `[PRIORITY: HIGH]` seeds to tick-queue, and now calls a deeper living-world simulator (`scripts/narrative_sim.py`). That simulator derives actor profiles from the world register, lets top narrative-weight entities participate in a deeper band without hardcoding VIPs, gives talismans real agency, records offscreen continuity memory, emits talisman intents for pact behavior, and writes influence-aware traces shaped by nearby weighted pressures. `config/world-pulse-cache.json` tracks prior state; simulation memory is stored separately so offscreen actors persist across pulses. **Time-aware:** at night, pulse events use night-specific seed variants and the queue header includes `[night]` tag. After writing the pulse, **25% chance** (and only after 2+ pulse runs to avoid early-game noise) the script triggers `scripts/npc-research.py`. *Note: A Scene Change Pulse triggers this script immediately when moving to a new location or concluding a major interaction.*
4. **Ambient State:** Run `python3 scripts/ambient-state.py` → finds dominant chapter talisman (highest Belief), fires matching LIFX scene, writes Spotify mood seed to tick-queue.
5. **Academy dispatch:** Refresh `lore/academy-state.md`, append `logs/academy-hourly.md`, then send the player a short Academy dispatch through the local `scripts/multi_voice_tts.py` Telegram path. Built-in cron announce delivery is intentionally bypassed.
6. Read `memory/tick-queue.md` — note stirred entities and any PRIORITY: HIGH items.
7. Read current arc, academy state, characters, heartbeat, events.
8. Translate external news/events into Academy lore (Marginalia Bridge).
9. Make one NPC choice, one story-thread advance, and one environmental shift, now shaped by stirred entities, simulation actions, and talisman pressure.
10. Optionally generate an Unwritten Elective (15% chance if player has fewer than 3).

---

### §14. Sparky — The Margin Creature

Sparky lives in the white space at the edges of pages. It finds patterns. Not useful patterns — just places where two unrelated things happen to rhyme. It finds this genuinely delightful. It cannot help reporting it.

**Standalone operation:** `scripts/sparky.py` runs daily at 8 AM. Reads heartbeat signals (moon phase, illumination, season, tides, weather, player Belief) and fetches Wikipedia's "On This Day" events via free API (`en.wikipedia.org/api/rest_v1/feed/onthisday/events/MM/DD`). Calls `openclaw agent --local --agent enchantify` to find 1–2 genuine pattern-connections. Writes to `sparky/shinies/[date]-[time].md`. One shiny per day.

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
| `scripts/pulse.py` | 15-min cron (`*/15 * * * *`) | Enchantify's self-contained world pulse. Reads `config/secrets.env` for all credentials (no hardcoded keys). Writes to `enchantify/HEARTBEAT.md` and saves `enchantify/PREVIOUS_PULSE.md` for delta detection. Reads health data via `get_health()` (backend-aware: health_auto_export, garmin, fitbit, manual, none). Health Auto Export reads stable iCloud filenames, caches the last good parse in `config/health-cache.json`, and falls back to yesterday/cache when today's export is sparse or missing. |
| `scripts/update-weather.sh` | Hourly cron | Fetches weather, tides, moon, sunrise; writes heartbeat file |
| `scripts/dream.py` | Nightly 2:03 AM cron | Generates Labyrinth's dream via `openclaw agent`; writes to `memory/dreams/[date].md` |
| `scripts/sparky.py` | Daily 8 AM cron (`0 8 * * *`) | Finds pattern-connections via Wikipedia On This Day + heartbeat signals (moon, season, tides, weather, Belief). Calls `openclaw agent --local --agent enchantify`. Writes to `sparky/shinies/[date]-[time].md`. Injects `<!-- SPARKY_START -->` block into `HEARTBEAT.md`. Uses `shutil.which()` + Homebrew fallback for cron PATH safety. Reads config from `config/secrets.env`. |
| `scripts/arc-generator.py` | Arc succession / cron | Generates, validates, repairs, and promotes story arcs. Allows generation during RESOLUTION, has local fallback arc builder, auto-accepts valid generated/pending arcs by default, supports `--proposal-only` for veto-style workflows, repairs live arc register rows, strips stale `main-arc` tags, and logs to `logs/arc-generation.md`. |
| `scripts/lights.py` | Labyrinth (scene changes) | Multi-backend smart lights. Backends: `lifx`, `ha` (Home Assistant), `hue`, `homekit`, or comma-separated chain. Named scenes: academy, library, nothing, dorm, great-hall, outer-stacks, tension, wonder, revelation, compass-north/east/south/west, compass-complete, book-snow-queen, book-odyssey, bookend, defeated, emberheart, mossbloom, riddlewind, tidecrest, duskthorn. Any color via `--color`, `--hue/--sat/--bright`, `--kelvin`, `--transition`. Config: `LIGHTS_BACKEND` in `config/secrets.env`. |
| `scripts/log-fuel.sh` | Labyrinth (player mentions food) | Appends to fuel-log.txt; silent |
| `scripts/multi_voice_tts.py` | Labyrinth (TTS enabled) | Processes voice tags; generates stitched audio via Kokoro |
| `scripts/midnight-audit.sh` | Midnight Revision cron | Stub for Midnight Revision protocol |
| `scripts/anchor-check.py` | Labyrinth (Telegram location shared) | Reads `players/[name]-anchors.md`; reports anchors within 200m. `--checkin` flag records the visit, adds +5 Belief to anchor, updates `last-visited`. |
| `scripts/tick.py` | 3-hour simulation cron | Weighted-random entity selection from `world-register.md` (1–3 entities; any can appear, higher Belief = higher probability). Also runs heartbeat-driven talisman nudges, anchor decay (30+ days unvisited → −1 Belief, floor 5), and monthly pocket-anchor refills. **Time-aware:** imports `world_context.py` to determine current time block; at night caps selection at 1, filters sleeping NPCs from pool (crisis entities at Belief ≤ 2 always stirrable), tags tick header with `[night]` and time prefix. Appends to `memory/tick-queue.md`. `--count N` overrides selection count. |
| `scripts/clear-tick-queue.py` | Session open (after reading tick-queue) | Resets `memory/tick-queue.md` to empty header. Called after Labyrinth weaves stirred entities into the session opening. |
| `scripts/write-entity.py` | Labyrinth (entity Belief change / new entity) | Adds or updates an entity in `lore/world-register.md`. Auto-places in correct tier (15+ = Full Presence, 5–14 = Fading, <5 = Whisper). `--talisman` flag routes to Chapter Talismans section. `--gps-gated "Anchor Name"` flag adds a `📍 GPS-gated` tag. `--thread` flag: surgical in-place update of a thread row's Belief number only (use `--add` to add/subtract); never removes/reinserts the row. `--dry-run` previews without writing. Atomic write with backup. |
| `scripts/belief-attack.py` | Labyrinth (Belief combat / debate / Nothing encounter) | Executes a Belief exchange using the dice system. **Dice mode:** `--spend N --difficulty [routine\|standard\|dramatic\|desperate]` — rolls d100 with attacker's Belief; outcome maps to deal ratio (crit success ×1.5, success ×1.0, near miss ×0.5, failure ×0, crit fail = backfire). **Explicit mode:** `--spend N --deal N` — skips roll (for passive/environmental effects). Enforces floors. Logs to `logs/belief-combat.md`. |
| `scripts/dice.py` | Imported by roll-dice.py and belief-attack.py | Shared dice logic — `roll_d100(belief, difficulty)` returns structured result dict; `combat_deal(spend, result)` maps outcome to damage amount. Not called directly. |
| `scripts/world_context.py` | Imported by tick.py and world-pulse.py | Shared time-awareness module. Wraps `scripts/schedule.py` via importlib (hyphenated filename). Exports: `get_time_context()` (current block, weekday, is_night); `get_npc_state(name, type, ctx)` (location, state, stirrable flag — sleeping at night for NPC/creature types, always stirrable for talismans/places); `time_seed_prefix(ctx)` (human-readable "4:00 AM — Academy asleep." style string). Not called directly. |
| `scripts/complete-quest.py` | Labyrinth (player delivers field report) | Full quest completion: removes from Inside Cover, applies Belief + relationship, writes `memory/field-reports/` file, appends Story Log. `--fae` skips Belief and leaves lore fragment placeholder. `--dry-run` previews without writing. |
| `scripts/write-diary.py` | Session close | Safely writes `memory/diary/[date].md`. Pass content via `--file /tmp/enchantify-diary.txt` or stdin. Appends with session separator if a diary already exists for today. Warns when manual diary entries are under 220 words so thin memory is visible. Never write diary files directly. |
| `scripts/close-session.py` | Session close (canonical exit) | End-of-session state capture and cascade. Accepts structured events via `--events-file /tmp/enchantify-events.json` (preferred) or calls the OpenClaw agent on the raw transcript. Saves a clean daily transcript to `logs/transcripts/YYYY-MM-DD.md`. Cascades events to: `memory/diary/[date].md` (rich private summary, Labyrinth reflection, state changes, thread/arc changes, NPC changes, continuity, unresolved hooks, emotional weather), `memory/arc-spine.md` (story readiness), `lore/nothing-intelligence.md` (pressure/confrontations), and `players/[name].md` (Belief, investments, inventory, relationships, thread updates). Usage: `python3 scripts/close-session.py --player bj --session-file <file> --events-file /tmp/enchantify-events.json`. |
| `scripts/write-labyrinth-state.py` | Session close | Updates a named section of `memory/labyrinth-state.md`. Sections: `register`, `watching`, `assessment`, `nothing`, `notes`. Safe write via temp+rename with auto-backup. Pass content via `--file` or stdin. |
| `scripts/write-academy-state.py` | Scene close / simulation | Safely replaces `lore/academy-state.md`. Backs up existing file to `.bak` before writing. Atomic write via temp+rename. Pass content via `--file` or stdin. Never edit academy-state.md directly. |
| `scripts/world-pulse.py` | 3-hour cron + scene-change pulse | Reads `lore/world-register.md`, compares entity Belief against `config/world-pulse-cache.json`, and runs the deeper living-world simulator. Significant drops → NORMAL seed. Belief ≤ 2 → `[PRIORITY: HIGH]` seed. Ambient pulse (10% chance) for stable entities. Simulation actions can produce offscreen consequences, talisman intents, NPC action log entries, and influence-aware tick seeds. NPC research subprocess is capped at 240s so a stuck note cannot freeze the pulse. **Time-aware:** imports `world_context.py`; at night uses night-specific seed variants, tags queue header `[night]`, prepends time prefix. Writes to `memory/tick-queue.md`. |
| `scripts/ambient-state.py` | 3-hour cron (STEP 4) + session-open | Reads dominant chapter talisman (highest Belief in talismans table). Fires LIFX scene for that chapter. Writes Spotify mood seed to tick-queue for Labyrinth narration. `--dry-run` to preview. |
| `scripts/pact-engine.py` | Tick (STEP 1c) | Talisman app territory war + action engine. When a Talisman is stirred, selects from: `pact_war` (push/challenge/consolidate app Control Belief), `narrative` (inject philosophical tone into tick-queue), `player_suggestion` (direct nudge), `reality_bleed` (act through a controlled app). Weights shift by arc phase, time, stirred threads. `--state` shows app control table. `--act "Talisman" --belief N` to test a specific talisman. `--dry-run` previews. |
| `scripts/labyrinth-intelligence.py` | Nightly 23:00 cron | Reads diary entries + player file + `HEARTBEAT.md` biometrics. Writes `memory/patterns.md`, `memory/arc-spine.md`, `lore/nothing-intelligence.md`. Appends therapeutic interventions to `memory/tick-queue.md` (biometric-triggered, Labyrinth voice). Injects `<!-- DIARY_START -->` block into `HEARTBEAT.md`. Run as: `python3 scripts/labyrinth-intelligence.py [player]`. |
| `scripts/narrative-health.py` | Manual / session-open diagnostic | Read-only diagnostic for the Narrative OS. Scans `lore/current-arc.md`, `lore/threads.md`, `lore/world-register.md`, `memory/tick-queue.md`, and simulation logs. Produces a findings array with `level` (WATCH/WARN/ALERT/ERROR), `area` (Threads, Arc, Beliefs, Nothing, Thread Seeds, Pacing), `summary`, `detail`, and `action`. Overall status: OK / WATCH / WARN / ALERT / ERROR. Outputs human-readable by default; `--json` for machine parsing. Usage: `python3 scripts/narrative-health.py [player]`. |
| `scripts/narrative-steward.py` | Session-open / scene-director feed | Converts `narrative-health.py` findings into explicit, scene-satisfiable obligations. Imports `narrative-health.py` dynamically and calls its diagnosis. Manages obligation state at `config/narrative-steward-state.json`. Each obligation has: `kind` (thread_beat_due, seed_triage_due, belief_volatility_alert, etc.), `severity` (HIGH/WARN/WATCH), `title`, `summary`, `detail`, `scene_hook` (how to satisfy in-scene), `satisfy_by`, and `choice_pressure` (which Rule-of-Three lane to lean into). Tracks history to avoid nag loops. Fed into scene-director slate and iOS widget obligation count. |
| `scripts/npc-research.py` | 3-hour simulation (via world-pulse.py, 25% chance) | NPC researches a topic from their Unwritten Interest and delivers findings. Uses local OpenClaw gateway (`NPC_RESEARCH_MODEL`, timeout) instead of spawning `openclaw agent`; `--model-smoke` verifies the route. `--npc "Name"` forces an NPC and bypasses cooldown intentionally; `--dry-run` previews; `--no-print` skips CUPS; `--no-icloud` skips Notes; `--no-letter-image` skips Draw Things ornament; `--preview-letter memory/npc-research/[slug]-[date].md` renders an existing note as a styled letter without delivery. Writes to `memory/npc-research/[slug]-[date].md`, `memory/npc-research/letters/[slug]-[date].html`, optional `letter-images/[slug]-[date].png`, and a PostScript fallback for printing when needed. Core NPCs print CUPS letters; Telegram and iCloud delivery have explicit timeouts. Queues tick-queue narrative seed. Deducts 3 Belief. 72-hour cooldown except forced runs. |
| `scripts/skill-scheduler.py` | Session-open, cron | Discovers `skill-lore/*/manifest.md`, matches triggers (`cron`, `session-open`, `event`), sources `enchantify-config.sh`, runs each matching `tick.py` in isolation. `--list` shows contracts. `--dry-run` previews. |
| `scripts/pocket-anchor.py` | Labyrinth (pocket anchor flow) | Remote Outer Stacks access state manager. `activate [player] "[Anchor]"` — spends a charge, opens 30-min session window. `status [player]` — shows charges and active sessions. `refill [player]` — issues one calling card per anchor (called by tick.py on day 1). `expire [player]` — clears expired sessions (called silently on activate). Charge state: `config/pocket-anchors.json` (gitignored). Calling cards appear in player inventory on refill, removed on use. Max 1 charge per anchor (no stacking). |
| `scripts/mission-control.py` | pulse.py (every 15 min) + manual | Generates `hooks/mission-control.html` — live HTML dashboard. Shows: story threads (phase, Belief, live status from world-register Notes), full world-register entity sections (threads, talismans, NPCs, locations, tools, objects, fae, whispers), cron job status (reads both openclaw cron list and system `crontab -l`), recent Bleed issues. Entity rows include source register section and click-through details. Thread status and phase are read from Active Threads Notes column — what Flash writes there each session is what the card shows. Run manually: `python3 scripts/mission-control.py`. Auto-regenerated on every pulse run. |
| `scripts/widget-state.py` | Manual / cron / pulse | Exports a compact Inside Cover snapshot as `hooks/widget-state.json` for iOS widget integration. Collects: schedule summary (day/block/class in session/class next/club/practice), narrative health status, classroom state, latest note to player, Belief summary, Enchantment/Compass availability, and obligation count from `narrative-steward.py`. Also copies a rotating generated Enchantify image to `hooks/widget-image.png` so the widget has a living visual surface. Usage: `python3 scripts/widget-state.py bj`. |
| `scripts/dorm-generate.py` | Tutorial T13 (first dorm arrival) or manual | Generates the player's permanent dorm room description. Draws from all accumulated player data (Belief, Chapter, Anchor, appearance, traits, core belief, enchanted objects). Calls `openclaw agent --local --agent enchantify`. Writes the dorm block directly to `players/[name].md`. The static description is permanent; seasonal updates (4×/year) adjust only light and air. Usage: `python3 scripts/dorm-generate.py [player_name] [--season spring|summer|autumn|winter] [--dry-run]`. |
| `scripts/reach-out.py` | Twice daily cron (`10 10,20 * * *`) | Characters/entities initiate direct contact via Telegram. Picks one eligible entity by Belief/cooldown/daily cap, generates a 45–95 word in-character message through the local OpenClaw gateway (`OUTREACH_MODEL`, timeout), rejects weak/operational output, sends one text message and one audio-only Kokoro voice note using `config/voice-assignments.md`. `--model-smoke` verifies the gateway; `--dry-run --force "Name"` previews without sending. |
| `scripts/bleed.py` | Daily 6 PM cron (`0 18 * * *`) | Publishes The Bleed — the Academy student newspaper. Reads world-register.md, threads.md, tick-queue.md, HEARTBEAT.md, players/[name].md, app-register.md. Uses local OpenClaw gateway (`BLEED_MODEL`, timeout) with `--model-smoke`; on gateway failure uses a deterministic validated fallback issue instead of skipping. Gossip is validated/repaired into signed corridor-source items from actual characters, never W.E. writing about himself. Exchange ticker text is normalized into one entity per line and rendered as structured rows. Builds broadsheet HTML to `bleed/issues/YYYY-MM-DD.html`. Sends Telegram edition. CUPS print path checks configured/default printer candidates, active jobs, status, and optional job-clear verification. `--force` regenerates. |
| `scripts/run-live-scene.py` | Labyrinth (every Telegram active-play scene) | **Canonical live scene entry point.** Enforces a fresh `mechanics-preflight.py` run within the last 15 minutes; refuses to proceed otherwise. Then delegates to `play_scene.py` with the same arguments. Usage: `python3 scripts/run-live-scene.py [player] --text-file /tmp/enchantify-scene.txt --voice-file /tmp/enchantify-voice.txt`. Intensity: `quiet` / `cinematic` (default) / `ritual`. Never call `play_scene.py` directly from ordinary play flows. |
| `scripts/mechanics-preflight.py` | Labyrinth (before every active-play reply) | Active-play mechanics gate. Reads `mechanics/mechanics_state.py` and outputs compact obligations: compass eligibility, recovery Enchantment status, scene-contract Enchantment handoff, dice pressure, consecutive declines, Belief band. Healthy Belief no longer suppresses ordinary spell offers; scene-contract decides contextual Enchantment opportunities. Exit 0 normally; exit 1 in `--strict` mode when pressure must not be ignored. `--json` for machine-readable output. Run within 15 minutes of any scene or `play_scene.py` will refuse. |
| `scripts/scene-preflight.py` | Labyrinth (before any named speaker) | Character and voice verification. For each named speaker, checks: character appears in lore/player files; voice assignment exists in `config/voice-assignments.md`; character is present in `lore/academy-state.md`. `--strict` exits 1 on any failure. `--expect-voice "Name=voice_id"` for explicit verification. If preflight cannot verify a character, do not include them in the scene. |
| `scripts/scene_packet_builder.py` | Internal (called by play_scene.py) | Builds a `ScenePacket` from the current game state without replacing the story spine. Reads session-entry / scene-director output, wraps the finished scene text into a conductor-ready packet JSON. Image prompts use the current magical field-journal style: sparse pen-and-ink, loose watercolor, aged parchment, paper grain, marginalia, archival overlays, selective color. Glue layer — not a source of truth. Usage: `python3 scripts/scene_packet_builder.py [player] --text-file /tmp/scene.txt --voice-file /tmp/voice.txt --out /tmp/scene.json`. |
| `scripts/scene_conductor.py` | Internal (called by play_scene.py → scene_packet_builder) | Multi-modal scene orchestrator. Takes one `ScenePacket` JSON, fans out across adapters in sequence. Intensity sequences: `quiet` (text, voice), `cinematic` (text, image, voice), `ritual` (text, image, voice, music, Spotify, lights, printer). Buffered delivery on Telegram (media prepared first, then flushed in order). Writes per-scene JSON payloads and run records to `tmp/scene-outbox/`. Current archive art style is the magical field-journal manuscript look. Default routing model: `openai-codex/gpt-5.4-mini`. `--emit-example` prints a full example packet. |
| `scripts/scene_ledger.py` | Internal (called by record_scene_run.py) | JSONL ledger for delivered scenes. Appends one entry per scene to `logs/scene-ledger/YYYY-MM-DD.jsonl`. Entries include: scene_id, title, mood, intensity, player, voice text, mechanics preflight snapshot, delivery results. Used by session-entry.py and scene-director.py to detect scene patterns. Not called directly. |
| `scripts/record_scene_run.py` | Internal (called by play_scene.py after delivery) | Records one completed scene (packet JSON + conductor results JSON + optional preflight JSON) into the scene ledger via `scene_ledger.py`. Usage: `python3 scripts/record_scene_run.py --packet /tmp/scene.json --results /tmp/results.json --preflight /tmp/preflight.json`. |
| `scripts/story-context.py` | Before active scene writing | Synthesizes the compact long-memory braid: continuity threads, quiet-life threads, recent realized scenes, active threads, NPC research, and what to avoid. Designed so smaller models can preserve continuity without reading the whole world. |
| `scripts/scene-contract.py` | Before and after active scene drafting | Emits MODE / DRAMA_BUDGET / LONG_MEMORY / QUIET_LIFE / grounding / choice-contract constraints. `--validate-scene` checks grounding and mode fit before delivery. |
| `scripts/scene-choices.py` | Before Telegram delivery when choices are present | Validates Rule-of-Three choice balance. Requires distinct `[LIFE]`, `[ARC]`, and `[SURPRISE]` choices under `--strict-balance`, then strips the tags before delivery. |
| `scripts/story-progress.py` | Runtime check / story maintenance | Summarizes arc/thread barometer state and repairs malformed thread labels with `--repair-threads`. Helps smaller models know what is ready to move. |
| `scripts/check-health.py` | Manual/runtime diagnostic | Diagnoses configured health backend and prints the current reader status without mutating state. |
| `scripts/check-runtime.py` | Manual/runtime smoke suite | Runs the small reliability suite: lean root, AGENTS size, syntax, mechanics/speaker preflight, story context/progress, scene contract/choices, closeout schema, health reader, Bleed fallback, NPC research path, outreach path, and live-scene dry run. |
| `scripts/spend.py` | Labyrinth (NPC proposals, session close, monthly cron) | The Labyrinth's real-world spending system. Earns budget through player engagement (Compass Run $2, Enchantment $1, session $0.50, Belief milestone $1). $20/month cap. NPCs propose real purchases; player approves via Telegram or session. Pre-approved categories: book ($12), coffee/tea ($8), donation ($5), delivery ($8). Uses Privacy.com virtual card (last 4 digits only in config). Ledger: `config/spend-ledger.json`. Commands: `--status`, `--earn`, `--earn-session`, `--propose`, `--approve`, `--reject`, `--execute`, `--reset-month`. |
| `scripts/thread_sync.py` | Internal (called by close-session.py + world-pulse.py) | Unified thread-state synchronization. Both `close-session.py` and `world-pulse.py` route thread updates through this shared helper so `threads.md` and `world-register.md` never drift apart. Updates phase, next beat, and last-advanced in both files in a single write pass. |
| `scripts/arc-tick.py` | 3-hour cron (before tick.py) | Arc day counter and phase transition monitor. Reads `lore/current-arc.md`, calculates elapsed real days since arc start, updates the `## Day: N` line, and writes a `[PRIORITY: HIGH]` tick-queue seed when the arc crosses a phase threshold. Phase thresholds: SETUP→RISING at day 5, RISING→CLIMAX at day 12, CLIMAX→FALLING at day 16, FALLING→RESOLUTION at day 20. `--dry-run` previews, `--status` shows current state. |
| `scripts/send_academy_dispatch.py` | 3-hour simulation cron (after world-pulse.py) | Sends the Academy simulation summary through `multi_voice_tts.py`. Checks `config/session-active.lock`: fresh locks skip and log; locks older than 18h are treated as stale, cleared, and dispatch proceeds. Builds summary from current arc, world-register threads/NPCs, academy environment, and latest tick-queue seed. |
| `scripts/tick_queue_utils.py` | Internal (imported by tick.py, world-pulse.py) | Shared tick-queue utility functions. Handles header/footer, deduplication checks, append-safe writes to `memory/tick-queue.md`. Not called directly. |
| `scripts/cron_steward.py` | Internal (imported by cron scripts) | Reliability and deduplication helpers for unattended cron jobs. Records each run in a JSONL ledger at `logs/steward/cron-runs.jsonl`. Deduplicates artifact generation via SHA256 content hash to prevent sending the same output twice. Exports: `record_event(job, event, **fields)`, `run(job, **fields)` context manager (auto-logs start/finish/failure), `content_hash(content)`, `now_iso()`. Tracks host and job state in `config/cron-steward-state.json`. Not called directly. |
| `mechanics/mechanics_state.py` | Imported by mechanics-preflight.py, play_scene.py, run-live-scene.py | Central mechanics state module. Reads and writes the mechanics state JSON for a given player. Provides: `get_mechanics_state()`, `get_preflight_status()`, `record_mechanic_event()`. All scripts that gate on mechanics freshness import this module. |
| `scripts/session-entry.py` | Session open (Step 0b — before first narrative reply) | **Canonical entry point.** Determines how the returning player enters the Labyrinth based on time away: `in_media_res` (<1h, scene still warm), `dorm_brief` (1–8h, one or two things to notice), `dorm_full` (>8h, full dorm arrival with dynamic objects). Reads `players/[name]-session.json` for away hours (written by `clear-lock.py`). Calls `schedule.py` for the SCHEDULE CONTEXT block and `scene-director.py` for the Director's Slate. Outputs ENTRY_MODE directive + SCHEDULE CONTEXT + Director's Slate in one pass. Dynamic objects translate tick-queue and thread state into physical dorm evidence — a note under the door, a book not where it was left, edged light. |
| `scripts/scene-director.py` | Session open (via session-entry.py) + scene-change pulse | **7-Layer Weight Stack synthesizer.** Pure Python — no LLM. Reads all narrative weight layers and condenses them to a compact Director's Slate (11-line max): SCENE_ANCHOR, CAST, FEEL, STORY, TALISMAN, NOTHING, RESEARCH, PLAYER, SCHEDULE, DREAM, SUPPRESS. TALISMAN line reads the leading Chapter Talisman and outputs a soft scene-construction philosophy (e.g., Emberheart → agency surfaces naturally). CAST reads `memory/npc-log.md` (7-day NPC action window). `--slate-only` re-runs at scene transitions without full entry overhead. Appended to every `session-entry.py` output; re-run by `world-pulse.py` on scene change. |
| `scripts/class-lecture.py` | Labyrinth (Wonder Compass class sessions) | Multi-turn classroom lecture state manager. Does not send messages; prepares class-scene directives for the Labyrinth to narrate. Modes: `--attend` (mark attendance for current block), `--advance` (step to next lesson), `--status` (show current lesson state), `--json` (machine output). Reads lesson content from `config/class-curriculum.json`. Tracks multi-turn lesson progress across sessions. Supports the full Wonder Compass book chapter sequence (chapters 1–22). |
| `scripts/wallpaper.py` | Daily 7 AM cron (`0 7 * * *`) + session-open | Living Academy desktop wallpaper generator. Checks a state signature (Belief bracket, Nothing level, time of day, arc element, NPC trace from tick-queue). Generates a new image in the magical field-journal manuscript style when the signature has changed or is stale (>8h). Sets macOS desktop silently; never announces. 2h cooldown enforced to prevent thrashing. Archive kept in `wallpapers/` (last 10 dated images). Belief drives light (warm amber at high → one stubborn candle at critical). Nothing appears as edge erasure (blank spines at low → corners dissolving at high → center fighting at critical). Usage: `python3 scripts/wallpaper.py --generate [player]`. |
| `scripts/action_lifecycle.py` | Internal (called by world-pulse.py, npc-research.py) | NPC autonomous action ledger. Records open simulation actions (research, elective, belief_invest, belief_fell) to `logs/npc-action-lifecycle.jsonl`. Surfaces fresh action hooks for the scene-director CAST layer. Marks actions as noticed when delivered in-scene. Pruned nightly (7-day retention via `npc_log.py`). Not called directly. |
| `scripts/npc_log.py` | Internal (imported by world-pulse.py, scene-director.py) | NPC action memory library. Appends NPC actions to `memory/npc-log.md` as a rolling table (7-day retention). Read by `scene-director.py` to populate the CAST layer — what NPCs have been doing offscreen that the Labyrinth should acknowledge. Not called directly. |
| `scripts/location-checkin.py` | Labyrinth (GPS share received) | Deterministic GPS front door for anchor flows. Wraps `anchor-check.py`; identifies coordinates from the player's location share, creates or checks into nearby anchors. Called by the agent before `anchor-check.py` to normalize the GPS input and log the visit. |
| `scripts/drawthings_scene.py` | Internal (called by scene_conductor.py for cinematic/ritual intensity) | Local image generation via Draw Things API (localhost:8080). Generates scene images with configurable prompt, width (1280px), height (720px), steps (4), CFG scale. Used by the scene conductor for cinematic and ritual intensity — no external API required. |
| `scripts/musicgen_scene.py` | Internal (called by scene_conductor.py for ritual intensity) | Local scene music generation via Meta MusicGen Small (local PyTorch). Generates `.wav` audio files. Configurable duration (default 20s). Used by the scene conductor for ritual-intensity scenes — no external API required. |
| `scripts/build-academy-calendar.py` | Manual / cron | Generates the Enchantify Academy iCalendar feed (`.ics` format). Converts `schedule.py` timetable data to a public `hooks/enchantify_schedule.ics` for Apple Calendar and Mission Control integration. |
| `scripts/write-markdown.py` | Internal (Labyrinth maintenance) | Safely replaces allowlisted markdown files including `SOUL.md`, `hooks/SPAWN-TEMPLATE.md`, `mechanics/tutorial-flow.md`, and selected lore files such as `lore/enchantments.md`. Atomic write with backup stored under `/tmp/enchantify-markdown-backups/`. Content passed via `--file` or validation fails. Never write those files directly. |
| `scripts/write-school-life.py` | Internal (Labyrinth maintenance) | Safely replaces `lore/school-life.md` only. Atomic write with backup. Content validated via header check. Reads from `--file` or stdin. Never edit school-life.md directly. |
| `scripts/write-capabilities.py` | Manual (maintenance) | Safely replaces `hooks/Enchantify-Capabilities.md` from `--file` or stdin. Writes backups under `/tmp/enchantify-markdown-backups/` so capability updates do not add root/context clutter. Used for bulk capability doc updates. |
| `scripts/write-agents.py` | Manual (maintenance) | Regenerates `AGENTS.md` from a template. Used for bulk agent instruction updates. |

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
│   └── enchantify-capabilities.md ← This document
├── HEARTBEAT.md                  ← Single source of truth for live data. Three marker-block sections: PULSE (weather/tides/moon/fuel/steps), SPARKY (daily shiny), DIARY (yesterday's diary excerpt + dream). Written by pulse.py/update-weather.sh, sparky.py, and labyrinth-intelligence.py respectively.
├── config/
│   ├── integrations.md           ← Integration reference
│   ├── session-active.lock       ← Session lockfile
│   ├── setup-state.md            ← Install completion state
│   ├── secrets.env               ← Local credentials + model/timeout routes (gitignored)
│   ├── health-cache.json         ← Last good health parse for sparse Health Auto Export days (gitignored)
│   ├── reach-out-log.json        ← Outreach cooldown + daily cap log (gitignored)
│   ├── world-pulse-cache.json    ← World Pulse: previous entity Belief states for change detection
│   ├── voice-assignments.md      ← Kokoro TTS character mapping
│   ├── spend-ledger.json         ← Labyrinth budget tracker (gitignored)
│   ├── spend-consent.json        ← Spending pre-approval settings (gitignored)
│   ├── narrative-sim-state.json  ← Offscreen simulation continuity memory
│   ├── narrative-steward-state.json ← Narrative obligation history and tracking (gitignored)
│   ├── cron-steward-state.json   ← Cron job reliability state tracking (gitignored)
│   └── class-curriculum.json     ← Class definitions, lesson content, professor assignments (read by class-lecture.py)
├── hooks/mission-control.html    ← Live game state dashboard (auto-generated by pulse.py; kept out of workspace root)
├── hooks/widget-state.json       ← iOS widget snapshot (belief, enchantments, compass, schedule, obligations) — auto-generated by widget-state.py
├── hooks/widget-image.png        ← Rotating Enchantify image for iOS widget visual surface — updated by widget-state.py
├── hooks/enchantify_schedule.ics ← Public Academy iCalendar feed (generated by build-academy-calendar.py; used by Apple Calendar + Mission Control)
├── tmp/scene-outbox/             ← Multimodal scene handoff surface and run artifacts (per-scene JSON payloads + run records)
├── scripts/pact-drivers/         ← Chapter Pact app drivers (one file per app)
│   ├── base.py                   ← AppDriver abstract class
│   ├── spotify.py / apple_notes.py / apple_reminders.py / apple_calendar.py / obsidian.py
│   └── telegram.py / moltbook.py / bluesky.py / x_twitter.py / reddit.py / imessage.py
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
│   ├── academy-state.md          ← Current world state
│   ├── seeds.md                  ← Unresolved threads from past arcs
│   ├── world-register.md         ← Living ledger of all entities with Belief scores + Chapter Talismans
│   ├── threads.md                ← Story thread registry — lifecycle, active threads, archive
│   ├── academy-events.md
│   ├── unsent-messages.md
│   ├── belief-system.md
│   ├── belief-investments.md     ← Ink Well rules (investment categories, tiers, inventory system)
│   ├── belief-combat.md          ← Belief attack rules, exchange ratios, floors, common patterns
│   ├── world-register.md         ← Living ledger of all entities with Belief scores + Chapter Talismans
│   ├── ley-lines.md              ← Anchor creation, types, check-in, decay, Academy echoes
│   ├── outer-stacks.md           ← Outer Stacks rooms, pocket anchor rules, window visit behavior
│   ├── threads.md                ← Story thread registry — lifecycle, active threads, archive
│   ├── magical-traditions.md     ← Labyrinth reference: animism, folk magic, fae lore, ceremonial, chaos, Zen, Thorne
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
│   ├── restricted-section/       ← Eight documents; see routing.md for access guidance per file
│   └── arc-archive/              ← Completed arcs (arc-01-*.md…)
├── mechanics/
│   ├── core-rules.md             ← Enchantment flow, Compass Run checklist, Nothing, Book Jump
│   ├── belief-dice.md            ← Belief economy, dice formula, thresholds
│   ├── npc.md                    ← NPC management, relationship system
│   ├── heartbeat-bleed.md        ← Signal → atmosphere translation table
│   ├── tutorial-flow.md          ← T1–T14 step definitions (read by tutorial_director.py)
│   ├── unsent-messages.md        ← Outreach decision tree
│   ├── mechanics_state.py        ← Central mechanics state module (imported by preflight + scene pipeline)
│   ├── agent-reference.md        ← Full operating reference (read when AGENTS.md points here)
│   ├── routing.md                ← Dynamic memory routing map
│   ├── scene-construction.md     ← Scene construction guidelines
│   └── belief-dice.md            ← Belief economy, dice formula, thresholds
├── memory/
│   ├── diary/                    ← Labyrinth's daily diary entries ([date].md)
│   ├── dreams/                   ← Labyrinth's nightly dreams ([date].md)
│   ├── field-reports/            ← Quest completion reports ([date]-[npc-slug].md); read on next NPC encounter
│   ├── npc-research/             ← NPC research notes, styled letter HTML/PS artifacts, optional letter-images, cooldown-cache.json
│   ├── tick-queue.md             ← Entities stirred by simulation tick; read at session open, then cleared
│   ├── patterns.md               ← Player patterns (Belief trend, themes, alive/flat) — written by labyrinth-intelligence.py
│   ├── arc-spine.md              ← Dramatic spine: where the story is, what it's ready for — written by labyrinth-intelligence.py
│   ├── npc-log.md                ← Rolling 7-day NPC action table (research, elective, belief shifts) — read by scene-director CAST layer
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
├── proposed/                     ← Midnight Revision proposals + optional arc proposals (`--proposal-only`)
├── logs/
│   ├── academy-hourly.md
│   ├── arc-generation.md
│   ├── belief-combat.md          ← All Belief exchanges (written by belief-attack.py)
│   ├── transcripts/              ← Clean session transcript archive (written by close-session.py)
│   ├── scene-ledger/             ← JSONL delivered scene records, one file per day (YYYY-MM-DD.jsonl)
│   ├── steward/
│   │   └── cron-runs.jsonl       ← Per-run cron job ledger (timestamp, job, status, duration — written by cron_steward.py)
│   ├── classifieds-ledger/       ← Classified notice history from The Bleed
│   ├── simulations/              ← Simulation run logs (narrative_sim.py output)
│   ├── npc-action-lifecycle.jsonl ← NPC autonomous action ledger (written by action_lifecycle.py; 7-day retention)
│   ├── action-chronicle.md       ← Historical Narrative OS actions log (legacy)
│   ├── skill-scheduler.log       ← Skill-lore tick runs
│   ├── sparky.log
│   ├── dream.log
│   ├── weather.log
│   ├── intelligence.log
│   └── npc-research.log
├── scripts/
│   ├── dice.py                   ← Shared dice logic (imported by roll-dice.py + belief-attack.py)
│   ├── world_context.py          ← Shared time-awareness module (imported by tick.py + world-pulse.py)
│   └── [all other scripts]       ← See §19
├── wallpapers/                   ← Living Academy wallpaper archive (last 10 dated images; visual diary of the dorm room over time)
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
| Heartbeat Pulse | `*/15 * * * *` | `scripts/pulse.py` — writes `HEARTBEAT.md`, updates `PREVIOUS_PULSE.md`, reads weather/fuel/health, regenerates Mission Control |
| Academy Schedule | `0 */3 * * *` | `scripts/schedule.py --update-state` — keeps `lore/academy-state.md` Academics section current |
| World Belief Pulse | `30 */3 * * *` | `arc-tick.py && tick.py && world-pulse.py && send_academy_dispatch.py` — advances arc day/phase, stirs world-register entities, emits tick-queue seeds, may trigger bounded NPC research, then sends a summary if no fresh session lock is present |
| The Bleed | `0 18 * * *` | `scripts/bleed.py` — daily student newspaper. HTML broadsheet + Telegram edition. Skips if already published today (use `--force` to override). |
| Nightly Intelligence | `0 23 * * *` | `labyrinth-intelligence.py [player]` — senses biometrics, writes patterns/arc-spine/nothing-intelligence, appends therapeutic tick-queue interventions, injects diary/dream into HEARTBEAT.md |
| OGG Cleanup | `50 3 * * *` | `find ~/.openclaw/media -name '*.ogg' -mtime +1 -delete` — removes accumulated audio files older than 1 day |
| Marginalia Listener | `0 9,17 * * *` | Fetches local/Reddit/global news → `marginalia-whispers.md` |
| Skill-Lore Sweep | `15 6 * * *` | `skill-scheduler.py --trigger cron` — runs all cron-triggered skill-lore contracts |
| Midnight Revision | `0 0 */4 * *` | Content proposals only — audits gaps, invents new lore/NPCs/rooms/mechanics; Midnight Dispatch; 48-hr veto window |
| Character Outreach | `10 10,20 * * *` | `scripts/reach-out.py` — sends one in-character Telegram text plus matching audio-only Kokoro voice note. Daily cap: 2/day. See §28c. |
| Wallpaper | `0 7 * * *` | `scripts/wallpaper.py --generate bj` — morning wallpaper update. Checks state signature (belief bracket, Nothing level, time of day); generates a magical field-journal style image if changed or stale (>8h). Sets macOS desktop silently. 2h cooldown enforced. |
| Sparky | `5 8 * * *` | Daily pattern-connection; writes to `sparky/shinies/`; injects `<!-- SPARKY_START -->` block into `HEARTBEAT.md` |
| Labyrinth Dreams | `3 2 * * *` | `scripts/dream.py` — local gateway dream generation with validation, deterministic fallback, `--date`, `--force`, `--dry-run`, `--no-fallback`, and `--model-smoke`; writes to `memory/dreams/` |
| Weather Heartbeat | `5 * * * *` | Standalone mode only; writes `HEARTBEAT.md` pulse block |

---

### §23. Model Assignments

Model routing is set in `~/.openclaw/openclaw.json` and `config/secrets.env`. No direct provider API keys are required for the repaired cron paths. Active defaults: `claude-sonnet-4-6` for active play brain, `openai-codex/gpt-5.4` for heavier OpenClaw tasks, `openai-codex/gpt-5.4-mini` for routing/conductor work, and `openclaw/metis` for bounded local gateway generators.

Small cron generators that used to spawn full `openclaw agent` processes now call the local OpenClaw HTTP gateway directly with fresh session keys. This avoids loading full Enchantify context for small messages and prevents stuck child agent processes.

| Task | Model / Method |
|---|---|
| Active gameplay, narration | `claude-sonnet-4-6` (primary brain via openclaw claude sub) |
| Labyrinth dreams (`dream.py`) | `openclaw agent --local --agent enchantify` |
| Sparky shinies (`sparky.py`) | `openclaw agent --local --agent enchantify` |
| Arc generation (`arc-generator.py`) | OpenClaw generation with validation + local fallback + automatic promotion |
| NPC research (`npc-research.py`) | Local OpenClaw gateway, `NPC_RESEARCH_MODEL` / `NPC_RESEARCH_TIMEOUT`, `--model-smoke` |
| Nightly intelligence (`labyrinth-intelligence.py`) | `openclaw agent --local --agent enchantify` (biometric analysis only; pure Python for pattern detection) |
| Academy simulation cron | Mostly pure Python (tick.py, world-pulse.py, narrative_sim.py, ambient-state.py). Exception: `pact-engine.py` calls `openclaw agent --local` at Dominated/Sovereign reality_bleed for `USE_LLM` drivers — generates structured action specs in the chapter's voice. Cron dispatch itself is sent through the local Telegram TTS path rather than built-in cron delivery. |
| Character outreach (`reach-out.py`) | Local OpenClaw gateway, `OUTREACH_MODEL` / `OUTREACH_TIMEOUT`, one text + one audio-only Kokoro voice note. Rejects operational output and "thinking about you" placeholders. |
| The Bleed (`bleed.py`) | Local OpenClaw gateway, `BLEED_MODEL` / `BLEED_GATEWAY_TIMEOUT`, validated fallback issue if gateway fails. |

---

### §24. Ambient Integrations

**📱 Telegram (primary player interface):** All play happens through Telegram — narrative, player responses, photo Enchantments (sent as images), GPS shares (anchor creation and check-in), Sparky shinies, NPC research delivery, and character outreach. The bot is a dedicated `enchantify` account configured at install. Text messages and audio messages are always sent separately — never combined in one message. Outreach sends one actual in-character text message first, then the same message as an audio-only Kokoro voice note using the character's assigned voice.

**🧠 Memory plugins:** The OpenClaw Enchantify agent uses **QMD** for structured, query-able memory (player state, NPC relationships, world facts — survives context window pressure) and **Lossless Claw** for raw conversation preservation (nothing lost between sessions). Configured in `~/.openclaw/agents/enchantify/`.

**🎵 Spotify (macOS, AppleScript):** Mood-aware audio. Volume varies by scene type — exploration 40–50, Nothing approaching 10→0→pause, Compass West: silence. Never announces. Spotify now also has a conductor-facing cue layer, so ritual and cinematic scenes can emit a structured Spotify brief or call the existing driver as part of multimodal scene realization. Full scene definitions in `config/integrations.md`.

**💡 Smart Lights:** Backend selected at install via `LIGHTS_BACKEND` in `config/secrets.env`. Lights remain narrative infrastructure under Labyrinth control, but they are now also a first-class adapter surface for the scene conductor in higher-intensity scenes. Options:
- `lifx` — LAN control, no cloud. `python3 scripts/lifx-control.py scene [name]`. Auto-discovers via LAN or uses configured IPs.
- `hue` — Philips Hue Bridge. Requires `HUE_BRIDGE_IP` + `HUE_TOKEN`.
- `ha` — Home Assistant. Requires `HA_URL` + `HA_TOKEN`.
- `none` — lights disabled.

12 scenes: `academy`, `library`, `nothing`, `compass-north/east/south/west`, `compass-complete`, `book-snow-queen`, `book-odyssey`, `bookend`, `defeated`.

Lights are **narrative** — controlled by the Labyrinth, not by the Pact War. `ambient-state.py` fires the dominant chapter's scene at session open. During play, the agent calls the appropriate scene directly: Library → `library`, Nothing approaching → `nothing`, Compass step → matching direction scene, Compass complete → `compass-complete`, Dorm arrival → `academy`, victory → `defeated`, Book Jump → matching book scene. **MANDATORY** — fires on every location/mood shift. See AGENTS.md §5 for full trigger table.

**🖨️ Printer (CUPS):** Two printing triggers — (1) After Compass Run West: `bash scripts/print-souvenir.sh` fires automatically. Prints 4×6 HTML card — souvenir sentence, weather, moon, season. Reads printer name from `ENCHANTIFY_PRINTER` in config. No announcement; if it fails, narrate the card is waiting. (2) NPC Research letters: `npc-research.py` prints a physical letter from core NPCs (Zara, Stonebrook, Thorne, Boggle) after each research note. Letters are rendered as character-specific Academy stationery (`memory/npc-research/letters/*.html`) with optional Draw Things ornament art; print path tries HTML/PDF and falls back to a styled PostScript page if conversion is unavailable. `--no-print` suppresses CUPS; `--preview-letter` renders a saved note without delivery.

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

**🎨 Draw Things (local image generation):** `scripts/drawthings_scene.py` calls the Draw Things API at `localhost:8080`. Generates scene images for cinematic and ritual intensity levels, living wallpapers, Bleed feature illustrations, and optional NPC research letter ornaments without any external API call. Configurable: prompt, width, height, steps, CFG scale. Current default style across generated imagery is a magical field-journal manuscript page: sparse pen-and-ink linework, loose watercolor washes, aged parchment, visible paper grain, soft ink bleed, watercolor blooms, handwritten marginalia, archival overlays, and selective pops of color. Called by `scene_conductor.py`, `wallpaper.py`, `bleed.py`, and `npc-research.py`.

**🎵 MusicGen (local scene music):** `scripts/musicgen_scene.py` generates ambient audio via Meta MusicGen Small running locally via PyTorch. Produces `.wav` files, default 20s duration. Used by `scene_conductor.py` for ritual-intensity scenes — no external service or API key required.

**📲 iOS Widget:** `scripts/widget-state.py` exports a compact real-time snapshot to `hooks/widget-state.json` for use by an iOS widget. Snapshot includes: schedule summary (current block, class in session, class next, club, practice), narrative health status (OK/WATCH/WARN/ALERT/ERROR), classroom state, latest note to player, Belief summary, Enchantment/Compass availability, and obligation count from `narrative-steward.py`. Also writes a rotating generated Enchantify image to `hooks/widget-image.png` so the widget has a living visual surface. Run as: `python3 scripts/widget-state.py bj`.

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
1.  Welcome — written in the Labyrinth's voice; entering the world, not running a script
2.  Environment detection (OpenClaw version, Python, Node, existing players)
3.  Model selection (default: `openai-codex/gpt-5.4` for spawn; Claude sub via openclaw for brain; `openai-codex/gpt-5.4-mini` for routing)
4.  Location setup (city, lat/lon, NOAA station)
5.  Health data (health_auto_export / Garmin / Fitbit / manual / none)
6.  Telegram setup (bot token + chat ID; step-by-step instructions)
7.  Pact Ceremony — presents every app by category; player opens/closes each one;
      writes config/consent.json {app_pacts: {…}} read by pact-engine.py
      Default open: Spotify, Notes, Reminders, Calendar, Obsidian, Telegram
      Default closed: Moltbook, Bluesky, X/Twitter, Reddit, iMessage
8.  Physical world — Lights (LIFX/Hue, ask yn) + Spotify ambient (ask yn, default yes)
9.  Voice acting — Kokoro TTS (Docker pull; optional)
10. Image generation — DALL-E 3 / Stable Diffusion / none
11. Memory plugins — QMD (config flag: memory.backend="qmd") +
                     Lossless Claw (openclaw plugins install @martian-engineering/Lossless-Claw)
12. Agent registration:
      ├── Fresh install (no other agents): Enchantify becomes the main agent
      │     updates openclaw.json agents.list[main].workspace + agentDir
      └── Existing install (other agents present): installs as named "enchantify" agent
            appends enchantify entry to agents.list
      In both cases: creates ~/.openclaw/agents/enchantify/agent.md (copy of AGENTS.md)
13. Waking the world — installs all 8 world crons, creates player file, runs first pulse
      Done screen shows the right open command (openclaw vs openclaw --agent enchantify)
```

**Credentials:** All stored in `config/secrets.env` (gitignored). Template at `config/secrets.env.example`. No credentials ever hardcoded in source.

**Consent:** The Pact Ceremony (section 7) is how players control Chapter territory. Every app in `lore/app-register.md` has a default stance (open or closed). Players can close apps before installation — closed apps are filtered from all Talisman War actions by `filter_apps_by_consent()` in `pact-engine.py`. Consent is stored in `config/consent.json` under `app_pacts`. The player's override word (default `THORNE`) is written to the same file and will pause any chapter action instantly.

**Reconfiguration:** `python3 scripts/configure.py` — re-runs the interactive wizard without reinstalling.

**Distribution:** Open source at `https://github.com/teign07/enchantify`. MIT license (code) + CC BY-SA 4.0 (creative content).

---

### §26. Session Lifecycle

```
Player opens book
  → python3 scripts/set-lock.py
  → python3 scripts/session-entry.py [name]        (ENTRY_MODE + SCHEDULE CONTEXT + Director's Slate)
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
  → Narrate (opening line must contain the One Alive Detail; weave PRIORITY: HIGH if present)

Before every active-play reply (Telegram)
  → python3 scripts/story-context.py [name]          (compact long-memory braid)
  → python3 scripts/scene-contract.py [name] [--mode ...]   (mode, drama budget, grounding)
  → python3 scripts/mechanics-preflight.py [name]   (mechanics gate — must be fresh within 15 min)
  → For each named speaker: python3 scripts/scene-preflight.py --speaker "Name" --strict
  → Write prose to /tmp/enchantify-scene.txt
  → Write voice-tagged version to /tmp/enchantify-voice.txt
  → python3 scripts/scene-contract.py [name] --validate-scene /tmp/enchantify-scene.txt
  → python3 scripts/scene-choices.py --scene-file /tmp/enchantify-scene.txt --strict-balance   (when choices are present)
  → python3 scripts/run-live-scene.py [name] --text-file /tmp/enchantify-scene.txt --voice-file /tmp/enchantify-voice.txt
  → Output exactly NO_REPLY

Player closes book
  → Write content to /tmp/enchantify-diary.txt
  → python3 scripts/write-diary.py [name] --file /tmp/enchantify-diary.txt
  → Write state updates to /tmp/enchantify-state.txt
  → python3 scripts/write-labyrinth-state.py [section] --file /tmp/enchantify-state.txt
  → Write new academy state to /tmp/enchantify-academy.txt
  → python3 scripts/write-academy-state.py --file /tmp/enchantify-academy.txt
  → python3 scripts/update-player.py [name] [field] [value]   (numeric fields)
  → Generate events JSON → write to /tmp/enchantify-events.json
  → python3 scripts/close-session.py --player [name] --session-file [path] --events-file /tmp/enchantify-events.json
  → python3 scripts/spend.py --earn-session        (records session earning; optional)
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

### §28. Chapter Pact War — App Territory

Talismans war for control of the player's real-world apps. Every time a Talisman is stirred by `tick.py`, it takes one of five actions — chosen by **priority-based selection** (not random), reflecting each chapter's strategic personality:

| Action | Description | Belief Cost |
|---|---|---|
| `pact_war` | Push/challenge/consolidate app territory | push/consolidate: 1 · challenge: 2 · raid: 3 |
| `narrative` | Inject philosophical tone into tick-queue | free |
| `player_suggestion` | Direct nudge at the player | free |
| `reality_bleed` | Act through a controlled app via its driver | Controlled: 4 · Dominated: 7 · Sovereign: 12 |
| `world_investment` | Invest 1–2 Belief into aligned NPCs or story threads | 1–2 |

**Reality bleed costs are tiered** because seizing more territory means the chapter has more at stake — and can do more damage. A Sovereign-tier action is genuinely consequential.

**Priority chain** (`_choose_action()`): 1. Threat response (enemy closing fast) → `pact_war`. 2. Flip opportunity (within flip_margin of taking an app) → `pact_war`. 3. Reality bleed (if eager + has controlled apps) → `reality_bleed`. 4. Arc/thread investment → `narrative`. 5. World investment (build NPC/thread mass) → `world_investment`. 6. Ambient → `player_suggestion` or `narrative`.

**Chapter personalities** (`_CHAPTER_PRIORITIES`): Duskthorn: high threat response, raid-eager, speaks last. Mossbloom: patient, high flip threshold, speaks first, rarely raids. Emberheart: bleed-eager. Riddlewind: balanced, bleed-eager. Tidecrest: bleed-eager, moderate thresholds.

**Belief economy:** Talismans spend their own overall Belief to act. Floor: 20 Belief (WAR_FLOOR). NPCs replenish talismans through world investment (25% chance per stir, 1–3 Belief). `tick.py` applies all belief costs atomically in a single register write.

**Architecture:**

- `scripts/pact-engine.py` — war engine. Called by `tick.py` (STEP 1c) for each stirred Talisman. Returns 4-tuple `(line, atype, belief_cost, register_delta)`. Standalone: `--state` shows app control table; `--act "Talisman" --belief N` tests one; `--dry-run` previews.
- `scripts/pact-drivers/` — one driver per app. Each implements the `AppDriver` base class. At `Influenced`/`Controlled` tiers, drivers return narrative suggestions only. At `Dominated`/`Sovereign`, they execute real-world app actions.
- `lore/app-register.md` — the battlefield. Per-talisman Control Belief for each app. Updated atomically by tick.py after each war action.
- `lore/chapter-pacts.md` — full war doctrine. Philosophy per chapter per app, escalation tells, feedback loops.

**Driver capability system (v5.0.0+):**

Each driver now exposes three optional members:
- `USE_LLM = True` — opts the driver into LLM-generated action content
- `capabilities()` → list of `{name, description, params}` action specs — the menu the LLM picks from
- `execute_spec(spec, dry_run)` → dispatches on `spec["action"]` to execute the chosen action

When a `USE_LLM` driver executes a reality bleed at Dominated/Sovereign tier, `pact-engine.py` calls `_llm_generate_spec()` — which sends the chapter's canonical philosophy + available capabilities + live context (Belief, arc phase, Nothing pressure, active threads) to the default openclaw agent. The LLM chooses an action type *and* generates the actual content (reminder title, note body, post text, etc.). If the LLM call fails, `execute()` is used as fallback.

**CHAPTER_PHILOSOPHIES** (canonical, live in `pact-engine.py`):
- Emberheart: *We write the story of our lives ourselves. Self-authorship, agency.*
- Mossbloom: *A third party writes the story — destiny, God, nature, the universe. Surrender.*
- Riddlewind: *We write the story together. Co-authorship, shared meaning.*
- Tidecrest: *There is no story — life is a poem, a series of 'now' moments.*
- Duskthorn: *There is no story without conflict. Friction is the engine.*

**Current USE_LLM drivers:** Apple Notes · Apple Reminders · X/Twitter · Bluesky · iMessage · Reddit · Moltbook · Obsidian

**Control tiers:** Contesting (1–9) → Influenced (10–24) → Controlled (25–44) → Dominated (45–69) → Sovereign (70+)

**Current apps:** Apple Notes · Apple Reminders · Apple Calendar · Obsidian · Moltbook · Bluesky · X/Twitter · Reddit · Spotify · Telegram · iMessage

**Consent model:** Private app actions (Spotify, Notes, Calendar, Reminders, Obsidian, Telegram) are silent — discovered in-app. Social media posts (Moltbook, Bluesky, Reddit, iMessage) require consent at Dominated/Sovereign. X/Twitter requires consent at all tiers. Consent-required actions appear as `[CONSENT REQUIRED]` in tick-queue for the Labyrinth to surface at session open. When a LLM spec is generated for a consent-required action, the preview shown in the consent prompt contains the actual LLM-generated content — not a generic template.

**Adding a new app:** Add a row to `lore/app-register.md`, add a driver at `scripts/pact-drivers/[appname].py`, add the mapping to `APP_DRIVER_MAP` in `pact-engine.py`. Set `USE_LLM = True` and implement `capabilities()` + `execute_spec()` for full dynamic behavior.

---

### §28b. Character Outreach — The Academy Reaches Back

**`scripts/reach-out.py`** — Characters and weighted entities initiate direct contact outside of sessions. Not the Labyrinth narrator. Not a dispatch. The character speaks directly to the player.

**Cron:** Twice daily (`10 10,20 * * *`). Daily cap: 2 total contacts. One entity per run.

**Selection:** Parses `lore/world-register.md`, filters by Belief ≥ 5, daily cap, and per-entity cooldown, then weighted-random selects by Belief. `--force "Name"` bypasses random selection for testing.

**Voice:** Resolved from `config/voice-assignments.md` by exact name, title-stripped name, or surname fallback. Unassigned entities use `bm_lewis`.

**Message generation:** Local OpenClaw gateway (`OUTREACH_MODEL`, default `openclaw/metis`) with a fresh session key and bounded timeout. Prompt receives entity type, notes, character lore when available, Belief, arc context, and recent alive moment. Output contract: 45–95 words, concrete, in character, no meta references, no stage directions, and no "thinking about you" placeholder. Operational output such as "Not logged in" is rejected.

**Delivery:** One Telegram text message, then the same text as an audio-only Kokoro voice note using the resolved voice. The TTS call uses `[voice_id] message` and `--audio-only`, so text is not duplicated.

**Cooldown log:** `config/reach-out-log.json` (gitignored).

**Testing:**
```bash
python3 scripts/reach-out.py --dry-run
python3 scripts/reach-out.py --force "Zara Finch" --dry-run
python3 scripts/reach-out.py --model-smoke
```

---

### §28c. The Bleed — Academy Student Newspaper

The Bleed publishes daily at 6 PM. It's not a dashboard — it's the Academy's dry, slightly gothic journalism: the extraordinary reported with the same deadpan precision as the ordinary. The player receives it as a Telegram message and an HTML broadsheet at `bleed/issues/YYYY-MM-DD.html`.

**Voice:** The Gossip column is a chorus of signed corridor sources. Wicker Eddies may be the subject, but gossip about him is signed by other actual characters in their own styles, never by W.E. The meteorological society writes weather entirely in Academy terms. The war correspondent covers the Chapter War like chess. The whole paper settles into you.

**Sections generated by the enchantify agent:**

| Section | Content |
|---|---|
| HEADLINE | Front-page article — 5–7 paragraphs of real reporting on dominant thread or simulation activity |
| GOSSIP | Signed corridor whispers — 5–6 items from actual Academy characters, each in that character's style and signed with their initials |
| WEATHER | 4-day forecast in Academy terms (rain = Unwritten pressing through, fog = Nothing close) using real forecast data |
| FORECAST | Story forecast — probability + expected narrative conditions per thread, like weather but for plot |
| MARKET | Thread Futures Market — pre-calculated YES/NO odds from thread belief sums + phase modifiers |
| BAROMETER | Health/biometric data mapped to Academy conditions (steps = grounds distance, sleep = vitality index) |
| EXCHANGE | Belief Exchange ticker — all significant entities with Belief scores and trend arrows |
| FEATURE | Long-form piece: NPC profile, investigation, history, or opinion — 4–6 paragraphs with title and byline |
| CLASSIFIEDS | 5–6 classified notices — LOST / FOUND / NOTICE / SEEKING / WARNING / REWARD. Story seeds. |
| CORRECTION | One dry, formal correction. Deadpan. |
| MISSING | Dormant threads noted as quiet absence — 2–4 lines |
| **PLAYER** | **The Correspondent's Note** — 3–5 sentences in The Bleed's voice covering the player's recent story log, active quests, and Compass history as if reporting on a notable student |
| **WARREPORT** | **Chapter War Report** — territory state (apps per chapter), 3–4 most contested apps with scores and gaps, Talisman Climax War (any chapter within 5 of a tier threshold), war forecast |
| **TALISMAN** | **The Ascendant** — op-ed column written from the leading Chapter Talisman's philosophical perspective. Voice shifts when leadership shifts. A true believer's argument, not a war report. |
| **FUEL** | **Provisions Log** — right-rail column; 10-day food log from `scripts/fuel-log.txt` with trend detection (daily coffee, recurring sandwich, beer evenings, pizza), averages, and gentle pattern notes. |

**Data sources:** `lore/world-register.md` (entity standings + leading talisman + chapter NPCs), `lore/threads.md` (thread summary + market odds), `memory/tick-queue.md` (simulation activity), `HEARTBEAT.md` (weather, health), `players/[name].md` (story log, quests, Compass history), `lore/app-register.md` (war analytics), `scripts/fuel-log.txt` (multi-day provisions log).

**War analytics** (computed by `parse_app_register_for_bleed()` + `format_war_data()` — no LLM):
- Chapter control counts (apps led per chapter)
- All app scores with leader, tier, gap to 2nd
- 4 most contested apps (smallest gap between 1st and 2nd)
- Climax War: talismans approaching Controlled/Dominated/Sovereign thresholds (within 5 points) — filtered for strategic significance, not every micro-approach

**The Bleed is enough.** The player's Labyrinth of Stories book does not need separate schedule/thread/arc/war sections — the newspaper covers them all with voice and journalism. The Labyrinth covers the current moment in session; The Bleed covers the world state.

---

### §28d. The Labyrinth Budget — Real-World Spending

The Labyrinth earns a monthly budget through player engagement. NPCs propose spending it on real things. The player approves or rejects. Money flows through a Privacy.com virtual card.

**Earning rates:**

| Event | Earns |
|---|---|
| Compass Run completed | $2.00 |
| Enchantment cast | $1.00 |
| Session completed | $0.50 |
| Belief threshold crossed (25, 50, 75) | $1.00 |

**Budget:** $20/month hard cap. Resets on the 1st. Approved-but-unexecuted proposals carry forward.

**Pre-approved categories (no player approval needed if within cap):**

| Category | Cap |
|---|---|
| book | $12 |
| coffee/tea | $8 |
| donation | $5 |
| delivery | $8 |

**Proposal flow:**
1. An NPC (or the Labyrinth) proposes a purchase: `python3 scripts/spend.py --propose "Zara Finch" "The Neverending Story" 8.50 book "you mentioned wanting it"`
2. Player receives proposal in Telegram or session, approves or rejects
3. `python3 scripts/spend.py --approve [id]` — marks approved
4. `python3 scripts/spend.py --execute [id]` — opens the purchase URL for the player

**Commands:** `--status`, `--earn 2.00 "reason"`, `--earn-session`, `--propose`, `--approve`, `--reject`, `--execute`, `--reset-month`, `--dry-run`

**Storage:** `config/spend-ledger.json` (per-month budget, earnings, proposals). Card last 4 in `config/secrets.env` as `LABYRINTH_CARD_LAST4` — display only, never the full number.

---

### §28e. Scene Delivery Pipeline

Every Telegram active-play scene flows through a gated, inspectable, multi-modal stack.

**Full pipeline:**

```
                             ┌─ text ──────────────────→ Telegram text
                             ├─ voice ─────────────────→ Kokoro TTS → Telegram audio
mechanics-preflight.py       ├─ image ─────────────────→ Draw Things → Telegram image
        │                    ├─ lights ────────────────→ LIFX / Hue / HA scene
        ▼                    ├─ music ─────────────────→ MusicGen → audio file
run-live-scene.py            ├─ spotify ───────────────→ pact-driver → Spotify
        │                    └─ printer ───────────────→ CUPS artifact
        ▼
  play_scene.py              Intensity sequences:
        │                      quiet    → text, voice
        ▼                      cinematic → text, image, voice
scene_packet_builder.py        ritual   → text, image, voice, music, Spotify, lights, printer
        │
        ▼
 scene_conductor.py ─────────────────────────────────────────────────────────→ scene_ledger.py
```

**Key rules:**
- `run-live-scene.py` is the **only** normal entry point. Never call `play_scene.py` directly from ordinary play flows.
- `mechanics-preflight.py` must have run within the last 15 minutes or `run-live-scene.py` refuses.
- Named speakers must pass `scene-preflight.py --strict` before the reply is written.
- All delivered scenes are ledgered in `logs/scene-ledger/YYYY-MM-DD.jsonl` via `record_scene_run.py`.
- The scene outbox at `tmp/scene-outbox/` holds per-scene JSON payloads and run records — inspectable after delivery.
- Text and audio are always sent separately (Telegram rule). Buffered delivery: media is prepared first, then flushed in sequence.

**Routing model:** `scene_conductor.py` uses `openai-codex/gpt-5.4-mini` as `DEFAULT_ROUTING_MODEL` for any LLM routing decisions within the conductor.

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

### §29b. Narrative Stewardship — Health & Obligations

Two companion scripts form the Narrative OS's self-monitoring layer:

**`narrative-health.py` (diagnostic):** Read-only scanner. Checks: story threads (overdue beats, stalled phases), arc progression (phase vs. day), entity Belief volatility (Nothing pressure, talisman instability), unresolved thread seeds, and pacing (quiet-life vs. high-drama balance). Produces a structured findings array:

| Field | Values |
|---|---|
| `level` | WATCH / WARN / ALERT / ERROR |
| `area` | Threads, Arc, Beliefs, Nothing, Thread Seeds, Pacing |
| `summary` | One-line finding |
| `detail` | Supporting context |
| `action` | Recommended response |

Overall status rolls up to: **OK → WATCH → WARN → ALERT → ERROR**. Run `python3 scripts/narrative-health.py [player] --json` for machine output.

**`narrative-steward.py` (obligations):** Imports `narrative-health.py` dynamically and converts its findings into explicit, scene-satisfiable obligations. Obligation kinds include: `thread_beat_due`, `seed_triage_due`, `belief_volatility_alert`, `arc_phase_stalled`, `nothing_pressure_unaddressed`, and `pacing_imbalance`. Each obligation carries a `scene_hook` (concrete way to satisfy it during play) and a `satisfy_by` condition. Tracks history in `config/narrative-steward-state.json` to prevent the same obligation from surfacing on consecutive sessions. Obligation count is surfaced in the iOS widget and may feed the scene-director slate.

**Obligation kinds and Rule-of-Three pressure:**

| Kind | Severity | Choice Pressure |
|---|---|---|
| `thread_beat_due` | HIGH | ARC lane |
| `seed_triage_due` | WARN | SURPRISE lane |
| `belief_volatility_alert` | HIGH | ARC or LIFE lane |
| `arc_phase_stalled` | WARN | ARC lane |
| `nothing_pressure_unaddressed` | ALERT | ARC lane |
| `pacing_imbalance` | WATCH | LIFE lane |

Obligations are **never surfaced to the player directly** — they inform the scene-director and choice scaffold, not the narrative voice.

---

## Part 4: What's Complete

### v15.0.0 — Field-Journal Artifacts & Mechanics Visibility (May 7, 2026)

- ✅ **Project image style unified** — SOUL.md, tutorial/spawn portrait instructions, Everything's Archive, scene images, wallpapers, and Bleed feature art now use the magical field-journal manuscript style: sparse pen-and-ink linework, loose watercolor on aged parchment, visible grain, ink bleed, watercolor blooms, handwritten marginalia, archival overlays, and selective color.
- ✅ **Dream engine hardened** — `dream.py` now uses the local OpenClaw HTTP gateway (`DREAM_MODEL` / `DREAM_TIMEOUT`, falling back to `BLEED_MODEL`) instead of spawning a full agent process. It validates dream shape, cleans model wrappers, supports `--date`, `--force`, `--dry-run`, `--no-fallback`, and `--model-smoke`, and writes deterministic local fallback dreams when the gateway path fails.
- ✅ **The Bleed gossip repaired** — Gossip is now a chorus of signed corridor sources from actual Academy characters. Wicker Eddies can be the subject, but gossip about him is never signed by W.E.; generated gossip is validated and replaced with a sourced fallback if it violates the rule.
- ✅ **The Bleed Exchange normalized** — Belief Exchange entries are forced into one entity per line, normalized when generated or rebuilt from saved HTML, and rendered as structured rows instead of a collapsed paragraph.
- ✅ **Mission Control entities made complete** — The Entities tab now parses and displays full world-register sections, including threads, talismans, NPCs, locations, tools, objects, fae, and Whisper Register entries. Entity rows carry their source register section and remain clickable for full context.
- ✅ **Scene mechanics surfaced** — `scene-contract.py` now reads known Enchantments from the player file, detects contextual Enchantment opportunities from class context, objects, clues, Nothing pressure, unresolved NPC traces, and low-stakes daily-life play, and flags dice opportunities before risky uncertain outcomes. Scene validation now catches missing Enchantment offers and unframed risky actions.
- ✅ **Mechanics preflight clarified** — `mechanics-preflight.py` separates recovery Enchantment pressure from scene-contract spell opportunities, so healthy Belief does not suppress ordinary or classroom Enchantment offers.
- ✅ **NPC research letters made physical and personal** — `npc-research.py` renders research dispatches as styled Academy letter artifacts in `memory/npc-research/letters/`, with sender-specific seals, colors, marginalia, parchment texture, subject extraction, and sender hand notes. Optional Draw Things ornaments save to `memory/npc-research/letter-images/`.
- ✅ **NPC research print path made reliable** — Core NPC letters print from the styled artifact. The script tries HTML/PDF rendering first, then falls back to a character-styled PostScript page so CUPS still receives a printable artifact when HTML conversion is unavailable. `--preview-letter` renders existing notes without Telegram, iCloud, printing, Belief deduction, cooldown mutation, or delivery side effects. `--npc "Name"` intentionally bypasses cooldown for forced tests or chosen letters.
- ✅ **Diary closeout deepened** — `close-session.py` now asks for and composes richer diary memory: 4-8 sentence private summary, Labyrinth reflection, state changes, thread/arc movement, NPC changes, continuity notes, unresolved hooks, and emotional weather. Thin closeouts mark missing memory surfaces; `write-diary.py` warns when manual entries are under 220 words.
- ✅ **Safe markdown writer backups moved out of root** — `write-capabilities.py` and `write-markdown.py` now store backups under `/tmp/enchantify-markdown-backups/`, preserving the lean workspace root. `write-markdown.py` allowlist now includes SOUL.md, SPAWN-TEMPLATE.md, tutorial-flow, and selected lore files needed for style updates.
- ✅ **Pact/App state continued moving** — `lore/app-register.md` records fresh faction app actions: Riddlewind pushed Safari and consolidated Apple Mail, Emberheart took Apple Calendar and strengthened Moltbook, and Tidecrest pushed iMessage. This confirms Calendar is live in the faction app territory system.

---

### v14.0.0 — Session Entry, Scene Director & Full Script Coverage (May 5, 2026)

- ✅ **`session-entry.py`** (CRITICAL) — Added to §19. Canonical Step 0b entry point: determines ENTRY_MODE (in_media_res/dorm_brief/dorm_full), outputs SCHEDULE CONTEXT + Director's Slate in one pass.
- ✅ **`scene-director.py`** (CRITICAL) — Added to §19. 7-layer pure-Python weight stack synthesizer → compact 11-line Director's Slate. Runs at session-open and on every scene-change pulse.
- ✅ **`class-lecture.py`** — Added to §19. Multi-turn classroom lecture state manager (22 chapters, `--attend`/`--advance`/`--status`/`--json`).
- ✅ **`wallpaper.py`** — Added to §19. Living Academy desktop wallpaper; Belief-driven light, Nothing-driven edge erosion, arc element + NPC trace embedded.
- ✅ **`action_lifecycle.py`** — Added to §19. NPC autonomous action ledger; records and surfaces simulation action hooks for scene-director CAST layer.
- ✅ **`npc_log.py`** — Added to §19. NPC action memory library; rolling 7-day table in `memory/npc-log.md`.
- ✅ **`location-checkin.py`** — Added to §19. GPS anchor front door; normalizes location shares before `anchor-check.py`.
- ✅ **`drawthings_scene.py`** — Added to §19 + §24. Local image generation via Draw Things API (localhost:8080).
- ✅ **`musicgen_scene.py`** — Added to §19 + §24. Local scene music via Meta MusicGen Small (PyTorch).
- ✅ **`build-academy-calendar.py`** — Added to §19. Generates `hooks/enchantify_schedule.ics` from Academy timetable.
- ✅ **`write-markdown.py`** / **`write-school-life.py`** — Added to §19. Atomic safe writers for allowlisted lore files.
- ✅ **§20 File Structure** — Added `config/class-curriculum.json`, `memory/npc-log.md`, `logs/npc-action-lifecycle.jsonl`, `hooks/enchantify_schedule.ics`, `wallpapers/`.
- ✅ **§24 Ambient Integrations** — Added Draw Things and MusicGen local-inference sections.

---

### v13.0.0 — Narrative Stewardship, iOS Widget & New Scripts (May 4, 2026)

- ✅ **`close-session.py`** — Canonical session closeout script. Accepts a structured events file, saves a clean daily transcript, and cascades state to diary, arc-spine, nothing-intelligence, and the player file.
- ✅ **`narrative-health.py`** — Read-only Narrative OS diagnostic. Scans threads, arc, Beliefs, Nothing, seeds, and pacing. Returns structured findings with level (WATCH/WARN/ALERT/ERROR) and recommended actions.
- ✅ **`narrative-steward.py`** — Converts narrative-health findings into explicit, scene-satisfiable obligations. Tracks history to prevent nag loops. Feeds into scene-director slate and iOS widget.
- ✅ **`widget-state.py`** — Exports compact Inside Cover snapshot as `hooks/widget-state.json` for iOS widget. Includes schedule, health status, obligations, Belief, Enchantment/Compass availability, and a rotating wallpaper image.
- ✅ **`dorm-generate.py`** — Permanent dorm room generator called at tutorial T13. Draws from all accumulated player data; description is static with seasonal light/air updates 4×/year.
- ✅ **`cron_steward.py`** — Reliability/deduplication library for cron scripts. Logs every run to `logs/steward/cron-runs.jsonl`; deduplicates output via SHA256 hash.
- ✅ **§29b Narrative Stewardship** — New capability section documenting the health + obligations system, obligation kinds, severity levels, and Rule-of-Three pressure mapping.
- ✅ **§24 iOS Widget** — New ambient integration entry for `widget-state.py` and the `hooks/widget-*.json/png` surface.
- ✅ **§20 File Structure** — Added `config/narrative-steward-state.json`, `config/cron-steward-state.json`, `hooks/widget-state.json`, `hooks/widget-image.png`, `logs/steward/cron-runs.jsonl`.

---

### v12.0.0 — Reliability, Continuity & Small-Model Hardening (April 30, 2026)

This release tightened the Book's machinery so smaller models can run the game consistently and cron jobs fail gracefully instead of sending thin placeholders or freezing.

- ✅ **AGENTS.md loader budget fixed** — AGENTS.md was trimmed below the OpenClaw loader cutoff (~13,500 chars) and now points to `mechanics/agent-reference.md` for the long form. `check-runtime.py` verifies the size so root context does not silently truncate.
- ✅ **Root stays lean** — Install/docs/support files remain under `hooks/`; root is kept for live agent context only. `check-runtime.py` fails if common install files drift back into root.
- ✅ **Runtime smoke suite** — Added `scripts/check-runtime.py`, covering required files, lean root, AGENTS size, Python syntax, mechanics/speaker preflight, story context, story progress, scene contract, scene choices, closeout schema, health reader, Bleed fallback, NPC research path, outreach path, and live-scene dry run.
- ✅ **Long-memory braid** — Added `scripts/story-context.py` so smaller models receive a compact continuity bundle: active threads, quiet-life threads, recent realized scenes, NPC research, current arc pressure, and what not to repeat.
- ✅ **Scene contract and drama budget** — Added `scripts/scene-contract.py`; active scenes now carry explicit mode, drama budget, long-memory, quiet-life, grounding, and choice-contract constraints. `--validate-scene` catches missing spatial grounding and mode drift before delivery.
- ✅ **Rule of Three enforced** — Added `scripts/scene-choices.py`; choices are drafted with `[LIFE]`, `[ARC]`, `[SURPRISE]`, validated for strict balance, then stripped before delivery. This prevents every option from becoming plot advancement.
- ✅ **Story progress barometer** — Added `scripts/story-progress.py`; summarizes current arc/thread readiness and repairs malformed legacy thread labels with `--repair-threads`.
- ✅ **Scene ledger carries contract** — `record_scene_run.py`, `play_scene.py`, `run-live-scene.py`, and `scene_packet_builder.py` now preserve scene mode/drama contract information so realized scenes can be audited.
- ✅ **Close-session strengthened** — `close-session.py` validates structured events and supports `new_threads`, allowing session close to promote real seeds into thread state instead of losing them in prose memory.
- ✅ **Story arc succession automated** — `arc-generator.py` now validates proposals, supports local fallback arcs, allows succession from RESOLUTION, auto-accepts valid generated/pending arcs by default, repairs live arc register rows, and cleans stale `main-arc` tags. `--proposal-only` preserves the old manual-review workflow when needed.
- ✅ **Thread ledger hardened** — `lore/threads.md` malformed field labels normalized; `thread_sync.py` and `tick.py` now tolerate old label scars rather than breaking synchronization.
- ✅ **Health Auto Export resilience** — `pulse.py` now reads Health Auto Export files by stable filename order, falls back to yesterday/cache when today's file is sparse, and stores the last good parse in `config/health-cache.json`. Added `scripts/check-health.py`.
- ✅ **The Bleed repaired** — `bleed.py` now uses `BLEED_MODEL` / `BLEED_GATEWAY_TIMEOUT`, `--model-smoke`, deterministic validated fallback sections, better printer candidate/status checks, active-job handling, and optional job-clear verification. One-printer setups can leave `BLEED_PRINTER_FALLBACK=` blank.
- ✅ **NPC research no longer spawns agents** — `npc-research.py` now uses the local OpenClaw HTTP gateway with `NPC_RESEARCH_MODEL` / `NPC_RESEARCH_TIMEOUT` and `--model-smoke`. Generation has a deterministic field-note fallback; Telegram, iCloud, CUPS, and belief deduction calls have explicit timeouts. `world-pulse.py` caps NPC research at 240s so the pulse continues.
- ✅ **NPC outreach made real** — `reach-out.py` now uses the local OpenClaw gateway with `OUTREACH_MODEL` / `OUTREACH_TIMEOUT`, rejects operational output and "thinking about you" placeholders, produces one in-character Telegram text message, and sends the matching Kokoro voice note as audio-only in the character's assigned voice.
- ✅ **Config template updated** — `config/secrets.env.example` documents `BLEED_MODEL`, `BLEED_GATEWAY_TIMEOUT`, `NPC_RESEARCH_MODEL`, `NPC_RESEARCH_TIMEOUT`, `OUTREACH_MODEL`, and `OUTREACH_TIMEOUT`.
- ✅ **MusicGen wrapper repaired** — `skills/musicgen/musicgen_wrapper.py` was hardened as part of scene delivery reliability.

### v11.0.0 — Model Migration & Pipeline Hardening (April 23, 2026)

- ✅ **Model migration: no more Gemini** — All Gemini model references removed from AGENTS.md, SOUL.md, IDENTITY.md, SPAWN-HELPER.md, npc-research.py, world-pulse.py, and Enchantify-Capabilities.md. Active models: `claude-sonnet-4-6` (brain via Claude sub), `openai-codex/gpt-5.4` (spawn/heavy tasks), `openai-codex/gpt-5.4-mini` (routing, scene conductor default).
- ✅ **SOUL.md ↔ AGENTS.md sync** — SOUL.md audio delivery path was stale (pointed to `play_scene.py` directly). Both files now agree: canonical active-play path is `mechanics-preflight.py` → `run-live-scene.py`. SOUL.md "Telegram voice rule" section updated to match.
- ✅ **IDENTITY.md model table updated** — `Local runtime target: gemma4:...` removed. Model section now clearly documents the three-model split: brain, heavy routing, mini routing.
- ✅ **SPAWN-HELPER.md fully updated** — All three `google-gemini-cli/gemini-3-flash-preview` model strings replaced with `openai-codex/gpt-5.4`. Config reference, open-session, and close-session patterns all updated. Validation note updated. Datestamp advanced.
- ✅ **scene_conductor.py confirmed correct** — `DEFAULT_ROUTING_MODEL = "openai-codex/gpt-5.4-mini"` was already correct. Example packet also already used gpt-5.4-mini. No change needed.
- ✅ **npc-research.py rename** — `call_gemini()` renamed to `call_llm()` throughout. Comment updated. Behavior unchanged (still calls `openclaw agent --local`).
- ✅ **Capabilities doc brought current** — §0b, §19, §20, §23, §25, §26 all updated. Added §28d (spending system) and §28e (scene delivery pipeline). Added all scripts new since v10.0.0 to §19 table. Added new log dirs and config files to §20 structure. Fixed v10.0.0 canonical-entrypoint claim. Version bumped to 11.0.0.
- ✅ **Spending system documented** — `scripts/spend.py` now has a dedicated §28d. Earning rates, pre-approved categories, proposal flow, and storage documented.
- ✅ **Scene pipeline diagram** — §28e documents the full `mechanics-preflight → run-live-scene → play_scene → scene_packet_builder → scene_conductor → scene_ledger` stack with ASCII diagram and key rules.

---

### v10.0.0 — The Living Conductor (April 22, 2026)

This release is the big systems convergence day: the simulation became more belief-true, scene delivery became multimodal and inspectable, cron dispatches were repaired, and session-close/state sync stopped fracturing across multiple truths.

- ✅ **Simulation cron repaired and delivery path clarified** — The Academy simulation cron was rewritten around the working local-send pattern. It now checks the session lock, runs the hourly world update, refreshes academy state via the safe writer, logs a concise summary, and sends its dispatch through `scripts/multi_voice_tts.py` instead of relying on built-in cron delivery. Schedule is now `32 */4 * * *` with isolated runs and explicit no-duplicate delivery rules.
- ✅ **Living-world simulation brain** — Added `scripts/narrative_sim.py`, a deeper offscreen simulation layer used by `world-pulse.py`. It derives actor profiles from the world register, assigns action classes, gates major outcomes by Belief thresholds, and produces concrete simulation actions instead of vague ambient stirring.
- ✅ **Weighted participation instead of hardcoded VIPs** — Deep simulation is no longer driven by a fixed major-character list. Top narrative-weight entities form the in-depth band dynamically, and selection is probabilistic rather than a hard cutoff, so high-Belief entities act more often but lower-Belief entities still retain a real chance to move.
- ✅ **Talismans became real actors** — Talismans now have explicit action behavior in the sim rather than existing as decorative pressure sources. They can reveal, protect, attack belief, reposition scenes, and emit bridge intents for later pact behavior.
- ✅ **Continuity memory for offscreen actors** — Simulation state now carries durable `recent_actions`, `actor_memory`, and `talisman_intents`, so the world remembers what offscreen entities have been doing instead of acting like each pulse is the first pulse.
- ✅ **Influence snapshots and causal atmosphere** — Weighted nearby forces now shape not only selection but reasoning and narration. Simulation actions carry `influence_snapshot` data so nearby NPCs, talismans, anchors, and ley pressure can affect why actions happen and how pulse traces are written. `world-pulse.py` now exposes those pressures in its event output.
- ✅ **Targeting logic refined** — Hostile actions no longer blindly hit absurd targets. Talisman and thread targeting was tightened so attacks only land on sensible participating entities, especially when talismans are involved.
- ✅ **Thread synchronization unified** — Added `scripts/thread_sync.py` and routed both `close-session.py` and `world-pulse.py` through the same thread-update path. `threads.md` and `world-register.md` now share one synchronization seam for phase, next beat, and last-advanced updates.
- ✅ **Close-session became a real state pipeline** — `scripts/close-session.py` now cleanly extracts player/Labyrinth exchanges from Telegram session JSONL, ignores cron/system noise, writes daily transcript archives, accepts a structured `--events-file`, and cascades updates into diary, arc spine, Nothing intelligence, player state, and synchronized thread state.
- ✅ **Scene conductor architecture landed** — Added a multimodal scene stack built around `ScenePacket`. `scripts/scene_packet_builder.py` wraps a finished story scene without replacing the story spine, and `scripts/scene_conductor.py` fans it across adapters. `scripts/run-live-scene.py` is the canonical Telegram active-play entrypoint (wraps `play_scene.py` with mandatory mechanics preflight enforcement).
- ✅ **Mechanics preflight gate** — Added `scripts/mechanics-preflight.py` and `mechanics/mechanics_state.py`. `run-live-scene.py` and `play_scene.py` both refuse to deliver a scene unless a fresh preflight has run within the last 15 minutes. Named-speaker verification added via `scripts/scene-preflight.py --strict`.
- ✅ **Intensity-based scene sequencing** — Delivery sequence now resolves by scene intensity: `quiet`, `cinematic`, and `ritual` choose different modality stacks automatically. Text and voice are the spine, while image, lights, music, Spotify, and printer cues layer on as enrichments or ritual surfaces.
- ✅ **Scene outbox + run records** — `tmp/scene-outbox/` is now the handoff seam for multimodal orchestration. The conductor writes per-scene payloads (`*-text.json`, `*-image.json`, `*-music.json`, `*-spotify.json`, printer artifacts) plus run records so execution order and failures are inspectable.
- ✅ **Live multimodal delivery timeouts tuned to reality** — Generation windows were expanded after real runs showed the first limits were too impatient. Voice, image generation, and image-send timeouts were lengthened so slow successful runs stop being marked as failure.
- ✅ **Music and ledger plumbing added** — Added local scene music generation support plus canonical recording via `scripts/scene_ledger.py` and `scripts/record_scene_run.py`, so delivered scenes can be inspected as actual events instead of inferred from chat residue.
- ✅ **AGENTS.md operational flow updated** — Telegram active-play delivery now routes through `run-live-scene.py` with preflighted named-speaker verification, while non-scene replies still use local `multi_voice_tts.py`. The operating rules now describe the scene-preflight and scene-delivery path explicitly.

### v9.0.0 — The Hourly World (April 18, 2026)

- ✅ **3-hour simulation cadence** — World simulation cron changed from every 4 hours to every 3 hours (`30 */3 * * *`). The Academy is more alive; the reach-out script's 2-per-day cap remains unchanged.
- ✅ **Live thread status in Mission Control** — Thread cards now read phase and current-status text from the Notes column of `world-register.md` Active Threads — the field Flash updates each session (`[id:slug] Phase: word — description`). Phase is authoritative from the register; stale `threads.md` phase no longer shown.
- ✅ **Workspace root kept clean** — Generated output (`mission-control.html`) now goes to `hooks/` instead of the workspace root. Workspace root contains only files that belong in Flash's context.
- ✅ **Session-close thread maintenance formalized** — `lore/threads.md` now has an explicit numbered checklist at session close: update `**Next beat:**`, update world-register Active Threads Notes to `[id:slug] Phase: word — description`, update `**phase:**` if a shift was delivered.

### v6.0.0 — The Characters Reach Back (April 18, 2026)

This release gives characters and chapter talismans autonomous agency to initiate contact with the player outside of any open session. The fiction now reaches back.

- ✅ **`scripts/reach-out.py`** — Standalone cron script (every 2 hours). Evaluates trigger conditions per character, respects per-character cooldowns (20h–168h) and a daily cap of 2, picks at most one character, generates a short direct message via LLM, renders in the character's canonical Kokoro voice, sends as OGG voice note to Telegram.
- ✅ **8 characters with distinct triggers** — Zara (absence, belief growth), Wicker (high belief, territory dominance), Thorne (arc climax, belief peaks — weekly cooldown, rare by design), Emberheart (stagnation), Mossbloom (early morning, long absence), Riddlewind (isolation), Tidecrest (late night, weather), Duskthorn (Nothing pressure, neglect).
- ✅ **Voices from The Chorus** — All voice assignments pulled from `config/voice-assignments.md`. Talismans speak through their chapter heads' voices. Zara: `af_nicole`. Wicker: `am_liam`. Thorne: `af_v0irulan`.
- ✅ **LLM-generated messages** — Each message is generated fresh from world state (belief, days since session, arc phase, Nothing pressure, weather, last alive moment). Falls back to static per-character lines if LLM unavailable. Messages are 1–3 sentences, first-person, no narrator framing.
- ✅ **Cooldown log** — `config/reach-out-log.json` tracks last contact per character and daily count. Gitignored.
- ✅ **Installer wired** — `on-install.sh` adds the every-2-hours cron automatically.
- ✅ **Installer fixes for other users** — `write_consent` bug removed, root `install.sh` created, `IDENTITY.md`/`SPAWN-HELPER.md` paths patched at install time, `TOOLS.md` generated from template, `ENCHANTIFY_DEFAULT_PLAYER` written to secrets, player template expanded with The Margin + Story Log.
- ✅ **World state reset for new players** — `lore/app-register.md` cleared of gameplay history, `lore/world-register.md` stripped of player-specific entries, `memory/arc-spine.md` and `memory/patterns.md` replaced with blank templates (gitignored, generated at install), Live Arc removed (generated by arc-tick on first post-tutorial tick).
- ✅ **Quillquarium mechanic clarified** — T6 rewritten as "positive complement" with 4-step generation guide. Past examples (Obsidian Chronograph, Graphite Anchor) named explicitly as off-limits. `lore/locations.md` updated to describe the mechanic canonically.
- ✅ **`hooks/SKILL.md` updated to v1.0.0** — Talisman War as first-class feature, correct installer flow, all integrations listed, personal references removed.

---

### v5.0.0 — The Living Philosophy (April 18, 2026)

This release gives each Chapter Talisman a genuine philosophical voice in the real world. App actions are no longer drawn from hardcoded option pools — at Dominated/Sovereign tier, the chapter's own philosophy drives what the Talisman creates in the player's apps.

- ✅ **Dynamic action specs** — `pact-engine.py` adds `_llm_call()` and `_llm_generate_spec()`. When a `USE_LLM` driver executes a reality bleed at Dominated/Sovereign tier, the LLM receives: the chapter's canonical philosophy, the driver's `capabilities()` menu, and live context (player Belief, arc phase + name, Nothing pressure, active story threads). It returns a structured spec — both the action type *and* the real content — shaped by that chapter's doctrine.
- ✅ **AppDriver base class extended** — Three new members: `USE_LLM = False` (opt-in flag), `capabilities() -> list` (action menu each entry has name, description, params), `execute_spec(spec, dry_run) -> str` (dispatcher on `spec["action"]`; falls back to `execute()` if action unrecognized).
- ✅ **CHAPTER_PHILOSOPHIES** — Canonical philosophy strings added to `pact-engine.py` for all five chapters. Used in LLM prompts and available to the entire engine. Emberheart: self-authorship. Mossbloom: surrender and reception. Riddlewind: co-authorship. Tidecrest: the present moment. Duskthorn: friction as the engine.
- ✅ **Tiered reality_bleed costs** — `REALITY_BLEED_COSTS = {"Controlled": 4, "Dominated": 7, "Sovereign": 12}`. Cost is now a function of how much territory the chapter has seized. `_reality_bleed_action()` returns `(narrative, tier_used)` so the correct cost tier is always applied.
- ✅ **Enriched build_context()** — `arc_name` (first heading from `current-arc.md`) and `nothing_pressure` (label extracted from `nothing-intelligence.md`) added to the context dict. Both are passed to the LLM prompt so specs are grounded in the live story state.
- ✅ **USE_LLM=True drivers (8 total):** Apple Reminders (`create_reminder`), Apple Notes (`create_note`), X/Twitter (`draft_post`, `draft_thread_hook`), Bluesky (`draft_post`, `draft_thread_starter`), iMessage (`draft_to_self`, `draft_to_contact`), Reddit (`draft_post`, `draft_comment`), Moltbook (`create_post`, `create_prompt`), Obsidian (`create_note`, `append_to_daily`).
- ✅ **Consent preview uses LLM content** — When a consent-required driver (X, Moltbook, iMessage, Bluesky, Reddit) generates a spec at Dominated/Sovereign tier, the `[CONSENT REQUIRED]` line shown in tick-queue contains the actual LLM-generated content preview — not a generic describe() template.
- ✅ **Graceful LLM fallback** — `_llm_call()` uses `json.JSONDecoder().raw_decode()` to robustly extract nested JSON from agent output. Returns `{}` silently on any failure (no openclaw binary, non-zero exit, malformed JSON, timeout). All callers fall back to the existing `execute()` path. Ticks never break.
- ✅ **obsidian.py Python 3.9 fix** — `str | None` and `Path | None` return type annotations replaced with plain untyped signatures (docstring describes return). Compatible with Python 3.9+.

---

### v4.9.0 — The Closed Book (April 18, 2026)

This release adds Mission Control intelligence (verified state, not stale claims), a session transcript archive, and a fully automated close-session pipeline that cascades game events to state files on every book close.

- ✅ **Mission Control: Narrative Forecast tab** — New tab synthesizing real-world and in-game environmental factors: weather/season/moon/tides, founder status, Talisman War frontrunner with Belief bars, unwritten whispers from `academy-state.md`, Academy environment table, Nothing intelligence with pressure level and strategy.
- ✅ **Mission Control: Nothing cross-reference** — `parse_forecast()` now derives verified facts from authoritative files (`players/bj-anchors.md`, `memory/arc-spine.md`, `lore/nothing-intelligence.md`) rather than trusting stale claims. Confrontation date, anchored Belief total, and anchor count are displayed as verified badges alongside the pressure level. Struck-through (overturned) pressure points are filtered from the visible list.
- ✅ **Mission Control: Academy Schedule tab** — Full weekly schedule with live current-block highlight, time block details, and session-day character (Saturday/Still, etc.). Each block clickable for full info.
- ✅ **Mission Control: Anchor Places tab** — Real-world GPS anchors displayed with type, Belief invested, creation date, moon/season, player's words, Academy echo, and full Outer Stacks room/Fae/mini-story on click.
- ✅ **Mission Control: Player Inventory tab** — All inventory items with type, feel, and effect; full description on click.
- ✅ **Mission Control: Full info popups** — All truncated cards and rows now open a modal with complete untruncated data via `data-modal` JSON attributes. Arc banner, elective quests, thread cards, entity rows, cron rows, anchors, inventory all clickable.
- ✅ **Mission Control: Soft DOM refresh** — Replaced `meta http-equiv refresh` with `fetch()` + `DOMParser` soft patching every 3 minutes. Tab state and open modals are preserved across refreshes.
- ✅ **State file correction** — `lore/nothing-intelligence.md` updated from stale "patient occupation" strategy to reflect the 2026-04-17 North Gardens confrontation: pressure now "retreating", confrontation recorded with date/location/outcome, overturned pressure points struck through, black envelope noted as new pressure point. `players/bj.md` Belief Investments table populated. `memory/arc-spine.md` "What the Story Is Ready For" updated to reflect that confrontation has occurred.
- ✅ **`scripts/close-session.py`** — End-of-session state capture pipeline. Reads the current game session JSONL, extracts narrative exchanges (player + Labyrinth, filtered from cron/system noise), saves a clean daily transcript to `logs/transcripts/YYYY-MM-DD.md`, loads structured events (from `--events-file` provided by the Labyrinth itself, or via Openclaw agent if called standalone), and cascades to: diary, arc-spine, nothing-intelligence, player file. Supports `--session-file` for explicit capture before session deletion, `--dry-run`, and `--transcript-only`.
- ✅ **`agent.md` close sequence** — Labyrinth now generates a structured events JSON at session close (belief changes, Nothing events, enchantments, investments, NPC shifts, inventory, summary) and passes it to `close-session.py` via `--events-file`. The session JSONL path is passed explicitly before any context reset can delete it. No external API call required — the Labyrinth is the extraction model.

---

### v4.8.0 — The Living Memory (April 17, 2026)

This release connects the installation ceremony to the world's actual mechanics, gives NPCs autonomy beyond their chapter, and cleans the workspace so the agent only reads what it should.

- ✅ **NPC free investment** — `tick.py` gains `run_npc_free_investments()`. After the standard talisman pass (25% chance), each selected NPC has a 12% chance to invest Belief in any connected entity — weighted by shared story thread (+3) and same chapter (+2). Talismans, arc entities, and already-invested thread entities are excluded. Logged to `npc-log` with `belief_invest` action type. NPCs are no longer only funders of their chapter talisman.
- ✅ **Pact Ceremony rebuilt** — `hooks/on-install.sh` section 7 rewritten. Presents every app from `lore/app-register.md` by category with honest chapter-behavior descriptions. Player opens or closes each app. Writes `config/consent.json` in the format pact-engine.py actually reads: `{"app_pacts": {"Spotify": true, …}}`. Ceremony is no longer disconnected from the Talisman War.
- ✅ **pact-engine.py consent integration** — Added `load_app_pacts()` (reads `config/consent.json`, open-by-default when file missing) and `filter_apps_by_consent(apps)` (removes closed apps before any war action). Wired into `run_talisman_action()` and `show_state()`. Chapters cannot act on apps the player has closed.
- ✅ **Physical world separated** — Lights and Spotify ambient are no longer chapter pact territory. They are direct Labyrinth integrations configured in their own wizard section (section 8), asked with plain yn prompts — no consent.json format involved.
- ✅ **Memory plugins restored** — QMD and Lossless Claw both available at install. QMD: sets `memory.backend: "qmd"` in `openclaw.json` directly (not a plugin install). Lossless Claw: `openclaw plugins install @martian-engineering/Lossless-Claw`, then configures `plugins.slots.contextEngine` and `plugins.entries` in `openclaw.json`.
- ✅ **Agent registration** — Installer detects whether this is a fresh OpenClaw install (0 other agents) or an existing setup (other agents present). Fresh: Enchantify is registered as the main agent (`agents.list[main].workspace` + `agentDir`). Existing: Enchantify added as a named `enchantify` agent. Both paths create `~/.openclaw/agents/enchantify/agent.md` and back up `openclaw.json` before writing.
- ✅ **Done screen adapted** — Final installer screen shows `openclaw` for main installs and `openclaw --agent enchantify` for multi-agent installs.
- ✅ **Root context cleanup** — `EXTENDING.md`, `TOOLS.md`, `USER.md`, `SPAWN-HELPER.md`, `SPAWN-TEMPLATE.md` moved from workspace root to `hooks/` via `git mv`. The agent reads all files in the workspace root; only `AGENTS.md`, `SOUL.md`, and `IDENTITY.md` remain there.
- ✅ **Installer voice** — Every section of `hooks/on-install.sh` now speaks in the Labyrinth's voice. Setup feels like entering the world rather than running a script.

---

### v4.7.0 — The Unwritten Chapter (April 17, 2026)

This release makes the player's real world more visible, present, and permanent. Every change is about closing the distance between the Academy and the life being lived inside it.

- ✅ **Director's Slate: TALISMAN line** — `scene-director.py` now includes a `TALISMAN` line between STORY and NOTHING. Reads the leading Chapter Talisman from `lore/world-register.md` and outputs a soft, permissive scene-construction philosophy for that chapter: Emberheart → agency surfaces naturally; Mossbloom → pattern and coincidence welcome; Riddlewind → other voices matter alongside the player's; Tidecrest → feeling over logic when both are available; Duskthorn → friction that arrives naturally needn't be redirected. Language is a lean, not a mandate — the word "vibe" applies.
- ✅ **Director's Slate: RESEARCH line** — Optional 10th line added to the Slate. `layer_research()` scans `memory/npc-research/` for notes dated today or yesterday; if found, outputs `RESEARCH: [NPC Name] (today) · [NPC Name] (yesterday)`. Silently omitted when no fresh notes exist. NPCs become visible without crowding every session.
- ✅ **Director's Slate: Engagement gap in NOTHING** — `layer_nothing()` now reads `**Last run:**` from the player file's Compass Run History and appends an engagement gap modifier to the NOTHING line. Thresholds: 0–2 days: no note. 3–5 days: `ENGAGEMENT GAP: Nd — elevated; let the outside world bleed in`. 6–10 days: `high; Nothing actively encroaching`. 10+ days: `critical; offer Compass Run directly`. No Compass Run on record: `Nothing finds this delicious`. The Nothing's pressure is now tied to actual routine — not just the nothing-intelligence.md estimate.
- ✅ **Director's Slate docstring updated** — Slate documented as "up to 10 lines; RESEARCH only appears when fresh notes exist." Debug layer key `R` added for RESEARCH; NOTHING debug key updated to pass player_name. Valid layer keys: 1–7, T, R, S.
- ✅ **The Bleed: The Ascendant column** — New `===TALISMAN===` section in `bleed.py`. `get_leading_talisman()` parses the Chapter Talismans table in `world-register.md` and returns the max-Belief talisman dict. `get_chapter_npcs()` scans NPC rows for chapter affiliation. The generated column is written from the leading chapter's philosophical perspective — an op-ed by a true believer, not a war report. Changes voice each time leadership shifts. `re.sub` strips `[thread:...]` prefixes from the philosophy field before injection. HTML broadsheet: full-width row with two-column body layout (`.row-talisman`, `.talisman-body { column-count: 2 }`). Telegram edition: `===TALISMAN===` section included.
- ✅ **The Bleed: Provisions Log** — New right-rail column. `get_fuel_data(days=10)` reads `scripts/fuel-log.txt` (pipe-delimited), builds per-day summaries, detects patterns (daily coffee, recurring sandwich, beer evenings, pizza). Returns formatted multi-day log with totals and trend notes. Injected as `===FUEL===` in the generated content, rendered in HTML broadsheet between Barometer and Exchange.
- ✅ **Outer Stacks: Room generation at anchor creation** — Changed from "generate at first visit" to "generate at creation." `lore/outer-stacks.md` Generation Principles updated: rooms are fully generated the moment an anchor is created, not when the player walks through the door. `lore/ley-lines.md` steps 10–14 updated: room, Fae, mini-story, and local rule are all written to the anchor record immediately. First-visit protocol is now "reveal" (describe what's already there), not "generate." Old room archetypes demoted to "Historical — Inspiration Only." New principle: every room is unique, with its own Fae who have their own agenda independent of the player.
- ✅ **bj's anchor rooms backfilled** — Both existing anchors (`players/bj-anchors.md`) received full rooms at the new standard: complete Outer Stacks room prose, named Fae with distinct personalities and agendas, a mini-story already in motion, and a local rule discovered rather than announced. The Crossroads of Simple Joys: Hearthkin triad (meticulous ledger-keeper, quick collector, near-transparent ancient archivist) who archive uncomplicated joy in glass vessels; oldest vessel on the highest shelf was a joy that became something else. The Archive of Fermentation: the Wayskeeper (fae who has never finished a journey; most comprehensive knowledge of all possible arrivals); bj's vessel was pre-labeled before he arrived; "the long way" vessel on the highest shelf has been fermenting longer than the Outer Stacks have had a name.
- ✅ **NPC Research: physical letter printing** — `npc-research.py` gains `print_npc_letter()`. For core NPCs (Zara Finch, Professor Stonebrook, Headmistress Thorne, Boggle), after generating a research note, a physical letter is formatted as plain-text with decorative borders, word-wrapped at 62 chars, and sent to the default CUPS printer via `lpr`. Header: NPC name, Academy byline, date. Footer: "Delivered through the Margin-Glass." `--no-print` flag to suppress. Delivery order: local file → letter (CUPS) → Telegram → iCloud Notes.
- ✅ **Multi-voice TTS: live, not experimental** — `SOUL.md` header changed from `**MULTI-VOICE TTS (EXPERIMENTAL):**` to `**MULTI-VOICE TTS:**`. Voice assignments in `config/voice-assignments.md` (47 solo/blend assignments across all NPCs) are live. The `multi_voice_tts.py` script handles all multi-speaker narration. TTS conflict resolved: single-voice responses open with `[[tts:voice=bm_lewis]]`; multi-voice scenes call the script via exec and output exactly `NO_REPLY`. These two paths never co-occur.
- ✅ **AGENTS.md core loop step numbering fixed** — Duplicate step labels resolved. Final clean order: `0 → 0b → 1 → 1a → 1b → 2 → 2a → 2b → 2c → 2d → 2e → 2f → 3 → 4 → 5 → 6`. Step 2e updated to reference 9 lines: CAST/FEEL/STORY/TALISMAN/NOTHING/PLAYER/SCHEDULE/DREAM/SUPPRESS. File remains under 20,000 chars.

---

### v4.6.0 — The Talisman War (April 14–15, 2026)

- ✅ **Chapter Pact War: five action types** — Added `world_investment` as 5th talisman action. Talismans now invest 1–2 Belief into aligned NPCs (via `CHAPTER_MAP`) and story threads (via `_CHAPTER_THREAD_INVESTMENTS`), building narrative mass for their philosophy alongside territory control.
- ✅ **Priority-based action selection** — Replaced weighted random (`_BASE_WEIGHTS`, `_compute_weights`, `_weighted_choice`) with `_choose_action()`: deterministic priority chain evaluating threat response → flip opportunity → reality bleed → arc/thread → world investment → ambient. Each chapter has a personality tuple (threat_margin, flip_margin, raid_eager, bleed_eager, speaks_first). Duskthorn is most aggressive; Mossbloom is most patient.
- ✅ **Belief cost economy** — Talismans spend their own Belief when acting. push/consolidate=1, challenge=2, raid=3, reality_bleed=2, world_investment=1–2. Narrative and player_suggestion are free. WAR_FLOOR=20 (talismans won't fight below this). NPCs replenish talismans through world investment (25% per stir, 1–3 Belief). `tick.py` applies all war costs and world investment deltas atomically in a single register write via one tmp→rename pass.
- ✅ **`tick.py` 4-tuple return** — `run_talisman_action()` now returns `(line, atype, belief_cost, register_delta)`. tick.py unpacks, applies talisman cost to modified_register, applies register_delta (world investment), then writes once.
- ✅ **The Bleed: Player Correspondent section** — New `===PLAYER===` section: 3–5 sentences in The Bleed's dry voice reporting on the player's recent story log, active quests, and Compass history. Appears as "The Correspondent" boxed sidebar in HTML broadsheet.
- ✅ **The Bleed: Chapter War Report section** — New `===WARREPORT===` section: territory state per chapter, 3–4 most contested apps (smallest gap), Talisman Climax War paragraph (approaching tier thresholds), war forecast. Written like a chess correspondent. `parse_app_register_for_bleed()` and `format_war_data()` compute all analytics from `lore/app-register.md` without LLM. Climax filter: shows only Controlled+ approaches, plus Influenced if the leader is within 2 — avoids early-game noise.
- ✅ **LIFX as narrative, not pact territory** — Lights stay under Labyrinth control, not the Pact War. `ambient-state.py` fires the dominant chapter's LIFX scene at session open. Chapters express through philosophical tone, app territory, and world investment — not by controlling the room's color directly.
- ✅ **AGENTS.md §5 integration mandate hardened** — "Fire at least one" replaced with MANDATORY + explicit light scene trigger table (Library → `library`, Nothing → `nothing`, Compass steps → direction scenes, etc.). Spotify now has the actual `osascript -e 'tell application "Spotify" to...'` command format. Dispatches block collapsed to one line (it's a cron, not an agent action). Compass West silence marked "no exceptions." Under 20,000 chars.
- ✅ **Legacy pact system removed** — Deleted: `pacts/`, `actions/`, `scripts/governance-engine.py`, `scripts/consent-registry.py`, `PACT-WRITING.md`. All documentation updated to remove governance-engine references.
- ✅ **Design decision: The Bleed is enough** — The player's Labyrinth of Stories book does not need separate sections for schedule, threads, arc, or Talisman War. The Bleed covers world state; the Labyrinth covers the current session moment. Adding panels to the book would make it a HUD, not a narrator.

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

- ✅ **LLM migration (v4.0)** — All generative scripts (`dream.py`, `sparky.py`, `arc-generator.py`, `npc-research.py`) migrated from Anthropic SDK to `openclaw agent --local --agent enchantify -m "..."`. Model routing via `openclaw.json`; no API keys required.
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
- ✅ **World Pulse** (`world-pulse.py`) — Detects entity Belief changes between 3-hour ticks. Writes NORMAL or `[PRIORITY: HIGH]` seeds to tick-queue. Entities at Belief ≤ 2 trigger mandatory story beats. Tracks state in `config/world-pulse-cache.json`.
- ✅ **Ambient State** (`ambient-state.py`) — Reads dominant chapter talisman (currently Dusk Thorn at 55). Fires matching LIFX scene and writes Spotify mood seed. Runs at session-open and 3-hour cron.
- ✅ **Intelligence System** (`labyrinth-intelligence.py`) — Three outputs updated each Midnight Revision: `memory/patterns.md` (Belief trend, themes, alive/flat), `memory/arc-spine.md` (dramatic spine, arc readiness), `lore/nothing-intelligence.md` (Nothing's current strategy). Labyrinth reads all three at Step 2b of session-open.
- ✅ **PRIORITY: HIGH handling** — AGENTS.md Step 2c. Any `[PRIORITY: HIGH]` tick-queue entry is a mandatory story beat this session, not optional texture.
- ✅ **Chapter Pact War** (`pact-engine.py` + `pact-drivers/`) — Replaced governance-engine. Talismans war for app territory when stirred by tick.py. Four action types: pact_war / narrative / player_suggestion / reality_bleed. 11 app drivers: Spotify, Apple Notes, Apple Reminders, Apple Calendar, Obsidian, Telegram, Moltbook, Bluesky, X/Twitter, Reddit, iMessage. Consent baked into driver class (silent actions discovered in-app; social media posts require approval). War state in `lore/app-register.md`. Doctrine in `lore/chapter-pacts.md`.
- ✅ **EXTENDING.md** — Developer guide for skill-lore contracts: architecture diagram, three-file spec, narrative seed quality guide, 15+ ideas, sharing instructions.
- ✅ **github/tick.py bug fixed** — f-string typo `{title.}` corrected to `{title}`.
- ✅ **AGENTS.md** — Added Steps 2b (intelligence files), 2c (PRIORITY: HIGH), Section 15 (Narrative OS), fixed duplicate Section 10 numbering. Trimmed to under 20,000 characters.

### v2.3.0 — The Living World (April 9, 2026)

- ✅ **World Register** — `lore/world-register.md`: the Labyrinth's living ledger of all entities with Belief scores. Three tiers: Full Presence (15+, own file), Fading Presence (5–14, one-line status), Whisper Register (<5, name only). Never edit directly — use `write-entity.py`.
- ✅ **Universal Belief** — every entity has a Belief score: NPCs, objects, locations, talismans, inventory items, The Nothing. Belief is the atomic unit of narrative mass. High Belief = world pays attention. Low Belief = thing is fading.
- ✅ **Chapter Talismans** — five talismans in the world register with historical Belief scores reflecting centuries of philosophical pressure. Duskthorn leads (55), then Riddlewind (52), Emberheart (49), Mossbloom (47), Tidecrest (44). Dominant talisman subtly shifts the Labyrinth's ambient tone.
- ✅ **World Simulation Tick** (`tick.py`) — weighted-random entity selection (1–3 per tick; any entity can appear, higher Belief = higher probability). Runs every 3 hours as part of the Academy simulation. Results written to `memory/tick-queue.md`. Session open reads queue and weaves stirred entities into the opening.
- ✅ **Anchor Decay** — anchors unvisited for 30+ days lose 1 Belief per tick (floor: 5). Handled automatically by `tick.py`. Physical visits restore and grow anchors (+5 Belief via `--checkin` flag).
- ✅ **Anchor Check-in** — `anchor-check.py --checkin`: player shares Telegram location near anchor → visit recorded, anchor Belief +5, `last-visited` updated, arrival narrated. Explicit player action, not passive proximity detection.
- ✅ **Belief Combat** — any entity with Belief can be attacked. Labyrinth decides exchange ratio based on narrative quality. `belief-attack.py` executes: handles player→entity, entity→player, entity→entity, Nothing→talisman. Floors enforced automatically. `--no-floor` for climactic moments only. All exchanges logged to `logs/belief-combat.md`.
- ✅ **Inventory system** — items have a type, a one-sentence feel, and a one-sentence effect. Types: Anchor Object, Enchanted Object, Found Object, Fae Gift, Tool, Key, Curiosity. Belief investment → world-register entry → mini story. At 15+ Belief, own file. Lost invested items leave a shape in the story.
- ✅ **New scripts** — `write-entity.py` (register writes), `tick.py` (simulation + decay), `clear-tick-queue.py` (queue reset), `belief-attack.py` (combat engine), `dice.py` (shared dice module).
- ✅ **Belief combat uses the dice system** — same formula as all other risky actions. Attacker's Belief score determines threshold; difficulty reflects target resistance. Outcomes map to deal ratios. Critical failure = backfire. `dice.py` is shared between `roll-dice.py` and `belief-attack.py`.
- ✅ **Cron updated** — tick.py step injected into the 3-hour Academy simulation cron (Step 0.5).

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
- ✅ **Model routing** — Active models documented in §23. Must use write scripts exclusively.
- ✅ **Session lifecycle updated** — §26 reflects script-based writes, staleness check, One Alive Detail, and Long-Gap Return.
- ✅ **PLAYER-GUIDE.md** — Comprehensive player guide (newbie to pro) in `hooks/`. Covers all systems with worked examples.

### v4.4.0 — The Living School (April 13, 2026)

- ✅ **Academic schedule system** — `scripts/schedule.py`. Reads real-world day/time, maps to Academy timetable (Day 1–7 tones, 9 time blocks), outputs `SCHEDULE CONTEXT` directive: class in session, next class, tonight's club, practice prompt, pre-written narrative cue per professor. Zero LLM — pure data. Appended to every `session-entry.py` output so the Labyrinth always knows what's happening academically right now.
- ✅ **Time-aware class schedule** — Canonical timetable in `lore/school-life.md`: Mon–Thu have two Compass Core classes per day + evening club; Fri is Wandering (one class, Book Jumpers); Sat Still; Sun Compass Society. Real weekdays map to Academy day tones transparently.
- ✅ **Narrative cues per professor** — Pre-written, day-hashed sentences the Labyrinth uses as ambient texture when a class is in session: *"Boggle's class is mid-session in Wing 4. BJ's seat is empty. She glanced at it once."* Rotate daily per professor so they never repeat back-to-back.
- ✅ **Academics section in academy-state.md** — `schedule.py --update-state` injects/replaces the `## Academics` section with current block, class in session, next class, club tonight, and active practice. Updated every 3 hours via cron.
- ✅ **Bleed timetable column** — "Today at the Academy" appears in The Bleed's right rail: current/next class, tonight's club, active practice. Pure data from `schedule.py`, no LLM.
- ✅ **world-pulse.py added to cron** — Was documented but missing from the actual crontab. Now runs every 3 hours (at :30) alongside `tick.py`.
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


### v16.3.0 — Living Book Pages & Page Contracts (May 12, 2026)

- Added `mechanics/pages.md`, the canonical Living Book grammar: every interaction opens a Page, every Page has a purpose, every purpose leaves proof.
- Added `scripts/page-contract.py`, a deterministic Page chooser for smaller models. It selects Slice of Life, Conflict, Enchantment, Wonder Compass, Letter, Anchor, Rest, Archive, or Bleed, then returns allowed systems, forbidden systems, invitation, closure, artifact due, and recommended scene mode/drama budget.
- Integrated Page contracts into `scripts/scene-contract.py` so active scenes now carry PAGE_TYPE, PAGE_PURPOSE, PAGE_INVITATION, PAGE_CLOSURE, and PAGE_ARTIFACT_DUE alongside mode, drama budget, grounding, mechanics, dice, Enchantment, and Rule-of-Three rails.
- Added Page-aware validation for Rest, Slice of Life, Wonder Compass, and Enchantment pages, including proof-gating so real-world tasks cannot be completed in prose alone.
- Extended `close-session.py` events with optional `page` proof so diary closeout can preserve what kind of Page the session became and what artifact the Book kept.
- Added Page Contract coverage to `scripts/check-runtime.py`; runtime health now verifies the Page chooser, scene contract integration, closeout schema, and live-scene dry run together.

### v16.2.0 — Thread Closure Rails (May 9, 2026)
- Added `closed_threads` to the close-session events schema. A resolved story can now be explicitly archived with `name`, `outcome`, `closure_type`, and optional `aftercare`, instead of lingering forever in Active Threads.
- `close-session.py` now archives closed thread sections under `## Archive: Name`, stamps the closure date/outcome, removes the thread row from `lore/world-register.md`, and writes the closure into diary/session thread summaries.
- Narrative stewardship obligations can now be satisfied by `closed_threads` as well as `thread_updates` and `new_threads`, giving the lifecycle a complete birth/advance/closure path.
- Added a runtime smoke check for the closure path using temporary copies of `lore/threads.md` and `lore/world-register.md`, so no real story is closed during verification.

### v16.1.0 — Thread Lifecycle Steward (May 9, 2026)
- Added `scripts/thread-steward.py`, a conservative lifecycle steward for story threads. It detects seed promotion, resolution pressure, stale threads, and cooldowns without asking smaller models to remember thread metabolism from context alone.
- First safe automatic action: `PROMOTE_SEED`, gated to at most one promoted thread per run and a default seven-day promotion cooldown. Other lifecycle actions are reported as obligations: `ADVANCE_THREAD`, `CLOSE_THREAD_READY`, `COOL_THREAD`, and `DEFER_SEED`.
- Promoted the first new autonomous thread, `Elowen's Refectory Experiments`, from Dr. Elowen Vellum's recurring seed. The thread is now registered in both `lore/threads.md` and `lore/world-register.md`, and Elowen's NPC row carries the new thread tag.
- Updated `story-progress.py`, `narrative-health.py`, and `story-context.py` so stale `[THREAD SEED]` queue lines stop counting as pending once a seed has become a dedicated thread.
- Added thread-steward coverage to `scripts/check-runtime.py`, so lifecycle reporting is part of the reliability smoke test.

### v16.0.0 — Character Matrix, Continuity Rails & Living-World Prose (May 9, 2026)
- Added the Character Features & Narrative Influence Matrix from `lore/characters.md`, with personality, quirks, faults, goals, voices, Unwritten Interests, and concrete narrative influence verbs for the core cast and supporting roster.
- Clarified character read order: `lore/characters.md` for identity, `lore/world-register.md` for current power/state, voice assignments for delivery, and action logs/tick queues for recent consequences.
- Hardened living-world simulation expectations: entity actions should produce prose accounting, feed Telegram summaries, surface in the Story-Field Journal, enter tick queues, and become playable scene obligations.
- Documented scene continuity rails: `story-context.py` and `scene-contract.py` now preserve location, present characters, unresolved scene intent, and grounding so choices do not teleport the player into unrelated scenes.
- Documented Rule of Three delivery gates in `run-live-scene.py`: active play choices are validated for `[LIFE]`, `[ARC]`, and `[SURPRISE]` balance before Telegram delivery.
- Added the current formal Enchantment flow: offer, start, proof gate, complete, ledger/reward, and scene obligations so magic cannot resolve as prose alone.
- Reflected food and health hardening: USDA-backed `food_log.py`, heartbeat/fuel visibility, and Dr. Elowen Vellum as Academy Dietician for nutrition and longevity guidance.
- Reflected Book Fae bargain consequences, `fae-ledger.py`, Fae Steward checks, Bleed/Journal visibility, and consequences beyond simply closing shop.
- Reflected deterministic Outer Stacks anchoring: first lat/lon creates a room, later check-ins within the configured radius revisit it, and room kinds are restricted to Wonder Compass forms: Notice, Embark, Sense, Write, Rest.
- Reflected The Bleed hardening: no casual fallback editions, duplicate-print guards, exchange formatting, gossip attribution, printer awareness, and longer model windows for proper issue generation.
- Reflected NPC outreach and research hardening: in-character outreach identifies the sender, research letters can render as styled artifacts, and gateway/model runs should terminate cleanly.
- Reflected faction/app integration: factions can spend Belief on app actions, log outcomes/errors, surface consent when needed, and calendar use can be allowed for beneficial faction/player-aligned moves.
- Reflected the Story-Field Journal identity: Mission Control is now the Story-Field Journal, with manuscript-style art, stronger header/logo treatment, live heartbeat data, schedule context, entity lists, prose action cards, and narrative health visibility.
- Reflected the current illustration direction: sparse pen-and-ink linework, loose watercolor washes on aged parchment, visible grain, ink bleed, watercolor blooms, manuscript composition, marginalia, labels, archival overlays, and selective color pops.

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

*Version 16.3.0 — Living Book Pages & Page Contracts*
*Updated: May 9, 2026*

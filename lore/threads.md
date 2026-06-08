# Thread Registry

*The living stories of the Labyrinth. Every named thread is a gravity well.*
*Entities in the world register carry `[thread:id]` tags — their Belief IS the thread's pressure.*
*Updated by the Labyrinth at session close. Advanced by the world simulation every 4 hours.*
*Never edit thread pressure manually — it is derived from entity Belief in the world register.*

---

## How Threads Work

A thread is any story with mass. Mass = the combined Belief of all entities tagged to it, plus the thread entity's own Belief in the world register.

- **Thread entities live in `lore/world-register.md`** (`## Active Threads` section) with their own Belief scores, stirred by the tick like any other entity
- **High Belief threads** → stirred more often → story advances more frequently
- **NPCs invest Belief into threads naturally** — when a tagged NPC is stirred, they may invest 1–3 Belief into their thread entity (handled by tick.py free-investment pass)
- **Being stirred grows a thread** — thread entities gain +1 Belief each time the tick selects them
- **Threads decay if ignored** — Belief drops toward zero if no one invests; the story runs without the player, but more quietly
- **Nothing attacks** → targets high-Belief entities and threads → the most invested stories dim first

**Phase ladder** — Belief in world-register determines the phase band; the narrative phase may lag 1–2 sessions while the Labyrinth delivers the shift:
- Belief 0–4: **dormant** — not being stirred; the world carries it minimally
- Belief 5–14: **setup** — something is beginning; low pressure; the player might not notice yet
- Belief 15–29: **rising** — momentum building; NPCs are affected; the thread is hard to ignore
- Belief 30–49: **climax** — urgent; every session should feel this thread's weight
- Belief 50+: **resolution** — the thread is reaching its conclusion, one way or another

**tick.py lifecycle signals** written to `memory/tick-queue.md`:
- `[Beat: Thread Name]` — thread stirred; Labyrinth delivers next beat and updates `**Next beat:**`
- `[THREAD ESCALATION: Name]` — Belief has crossed a phase threshold; deliver shift naturally
- `[THREAD COOLING: Name]` — Belief has dropped; something deflated; reflect in NPC texture
- `[THREAD SEED: NPC Name]` — high-Belief NPC without a dedicated thread; potential new subplot

**At session open:** read this file + `memory/tick-queue.md`. The highest-pressure stirred thread colors the atmosphere. The player is not told which thread is pressing — they feel it.

**At session close:** for each thread that was touched this session:
1. Update `**Next beat:**` in this file with what would advance it next
2. Update the Notes column in `lore/world-register.md` `## Active Threads` to reflect current state — format: `[id:slug] Phase: word — one-line current state` (e.g. `[id:wicker-schemes] Phase: rising — crew has gone quiet; something is being planned involving the exhibition`). This is what mission-control.py reads as live status. Keep it current every session.
3. If a phase shift was delivered, update the `**phase:**` field in this file to match.

---

### Thread Birth

New threads emerge from three sources:

1. **tick.py seed flag** — NPC crosses Belief 20 with no dedicated thread. Queue gets `[THREAD SEED]`. Labyrinth proposes a thread if the session confirms the story.
2. **Labyrinth proposal at session close** — when a subplot develops genuine weight in play, the Labyrinth writes a new `## Thread: Name` entry here + a world-register row (starting Belief: 5–8). No player approval required; the thread is alive the moment it has a next beat.
3. **Player Belief investment** — when the player invests Belief in something unregistered, the Labyrinth can offer to name it as a thread anchor.

**New thread minimum requirements:** one named NPC or location anchor with Belief ≥ 10, a legible next beat (one sentence), a Nothing pressure assessment, and an entry in world-register `## Active Threads` with `[id:slug]` in notes.

---

### Thread Closure

Two endings:

**Natural resolution** — Labyrinth delivers the final beat. At session close:
1. Move `## Thread: Name` → `## Archive: Name` (add `**closed:**` date + one-line outcome)
2. Remove the row from world-register `## Active Threads`
3. Write a closure beat to `players/[name]-story.md`

**Nothing victory / abandonment** — Belief drops to 0 through neglect or active drain. tick.py will stop stirring it (too low to select). Labyrinth writes a quiet closing line; marks archive entry `**closed:** [date] — unfinished`. The NPCs carry the cost quietly.

---

---

## Thread: Academy Daily Life

**id:** `academy-daily`
**type:** slice-of-life
**phase:** quiet
**pressure:** background *(always present, never urgent)*
**npc_anchor:** all NPCs
**locations:** Great Hall, Library, Corridors, Cafeteria, Classrooms, Courtyard
**entities:** Boggle, Great Hall, fae species (all tagged academy-daily in register)
**Nothing pressure:** low — the Nothing makes the ordinary feel hollow, not absent. Meals taste of nothing. Boggle's puns land wrong. The corridor light flattens.

**Next beat:** Corin's ledger sits at 26 compromised books. The Tollbooth waits. The Amber Codex has no known jumper trace.

**Last advanced:** 2026-05-08
**born:** 2026-04-01
**closed:** —

**Notes:** This thread is always available. Slice of life IS this thread running quietly. When the player wants no plot — they're in this thread. It provides the felt reality of the Academy between everything else.

---

## Thread: The Current Arc

**id:** `main-arc`
**type:** main-arc
**phase:** *(read from `lore/current-arc.md` — that file is authoritative)*
**pressure:** high *(the arc is always the primary thread — always has the most combined Belief at stake)*
**npc_anchor:** *(arc-specific — read `lore/current-arc.md`)*
**locations:** *(arc-specific)*
**entities:** *(arc-specific — tagged `[thread:main-arc]` in world register as the arc unfolds)*
**Nothing pressure:** high

**Next beat:** *(read from `lore/current-arc.md` — update that file, not this one)*

**born:** 2026-04-01
**closed:** —

**Notes:** The arc is Thread #1. It isn't the only thread. When the tick stirs arc-tagged entities, the Labyrinth surfaces arc content in the Rule of Three beat 2. When it stirs entities from other threads, those threads surface instead. The arc never disappears — it is always simmering — but it yields to whatever thread the world has stirred today.

---

## Thread: Zara's Inkwright Application

**id:** `zara-inkwright`
**type:** npc-subplot
**phase:** climax
**pressure:** low *(will rise — portfolio deadline is approaching, Wicker knows)*
**npc_anchor:** Zara Finch (Belief 23)
**locations:** The Library, Inkwright Society Hall, Zara's usual corner of the Great Hall
**entities:** Zara Finch
**Nothing pressure:** medium — the Nothing would love to make her doubt the portfolio is good enough. Self-erasure before the deadline.

**Next beat:** Overnight the draft wins: the two fallen pages vanish fully beneath the shelf, leaving only a pale rectangle in the dust where they'd lain — while the proud-lifted page in the squared stack slides askew, its watermark groove catching the morning lamp so the Inkwright crest reads backward, as if something tried to file it and changed its mind. The fainter second line beside the underscored sketch has been gone over once more, darker now, almost a decision.

**Last advanced:** 2026-06-07
**born:** 2026-04-12
**closed:** —

---

## Thread: Wicker's Campaign

**id:** `wicker-schemes`
**type:** antagonist
**phase:** resolution
**pressure:** medium-high *(Wicker's Belief is 60 — he has significant narrative mass)*
**npc_anchor:** Wicker Eddies (Belief 60)
**locations:** The Great Hall, Duskthorn common areas, wherever Zara or bj are
**entities:** Wicker Eddies
**Nothing pressure:** high — Wicker is adjacent to the Nothing. His schemes drain Belief from others as a feature, not a side effect. The Nothing doesn't control him; they simply have similar tastes.

**Next beat:** By midday the betting stub has filled both sides with penciled guesses and the red-threaded pencil has snapped from overuse, so a bystander lashes a fresh one in its place and the tally on Wicker's chalk scoreboard climbs to six lines without him touching it again. The next visible trace: the steward, worn down, has quietly started his own small ledger beneath the window — not to settle the vault numbers, but to record who keeps adding to them.

**Last advanced:** 2026-06-08
**born:** 2026-04-01
**closed:** —

**Notes:** Wicker advances without player attention. He is always scheming. When his thread is stirred by the tick, something he set in motion has moved — with or without the player watching. The player can subvert, expose, or ignore this thread, but they cannot pause it.

---

## Thread: The Duskthorn Investigation

**id:** `duskthorn-investigation`
**type:** mystery
**phase:** resolution
**pressure:** high *(the player has engaged, and Thorne is active)*
**npc_anchor:** Headmistress Thorne (Belief 83)
**locations:** Duskthorn Common Areas, The West Corridor, The Restricted Section, Headmistress's Office
**entities:** Headmistress Thorne, Dusk Thorn Talisman, Victor Ebonheart
**Nothing pressure:** high — something in Duskthorn is already adjacent to absence. The sealed corridor smells of it.

**Next beat:** By afternoon the Registry's threshold sits visibly gap-toothed where Thorne pried the cornerstone chip loose, a clerk having looped twine across the missing corner with a fresh card — MIND THE STEP / STONE OUT FOR REVIEW — so anyone approaching the counter now crosses a doorway that announces its own wound; behind the glass the brass tag has been read often enough that a second, anonymous chit has appeared beside it asking, in different handwriting, *whose threshold did she think it was to pry?* The empty felt slot…

**Last advanced:** 2026-06-08
**born:** 2026-04-01
**closed:** —

**Notes:** This thread runs whether or not the player engages. The Duskthorn investigation has stages the player can reach by proximity, investigation, or accident — not by being handed the story. When the tick stirs Thorne or the Dusk Thorn talisman, this thread surfaces as ambient texture: something slightly wrong about a space, a conversation that stops when the player enters, a corridor that is simply not open. **Session 2026-05-15:** Inkwell documented three alcove entries — chair appeared same week as Chronograph registry removal six months ago. Connection named aloud. Notice posted by someone with formal Board classification knowledge. The registry office in the admin wing holds the authorization record. Two threads touching: the alcove and the Chronograph.

---

## Ley Line Threads

*Each ley line anchor generates its own thread when created. Template:*

```
## Thread: [Anchor Name]

**id:** `anchor-[slug]`
**type:** ley-line
**phase:** [deepening / quiet / awakening]
**pressure:** [derived from anchor Belief in players/[name]-anchors.md]
**npc_anchor:** none (place-anchored, not NPC-anchored)
**locations:** The anchor's Academy echo room (GPS-gated)
**entities:** [anchor name in register]
**Nothing pressure:** medium — the Nothing can make a place feel like it was never meaningful

**Next beat:** [what is waiting there / what changed since last visit]

**Last visited:** [date]
**GPS:** [coordinates]
```

*Ley line threads only advance when the player physically visits (GPS check). Between visits, they evolve slowly on their own — something small shifts. The player returns to find the room changed proportionally to how long they were gone.*

---

## Adding New Threads

When a new subplot, mystery, or character goal emerges with enough Belief to sustain itself:

1. Add a `## Thread: Name` section below with all required fields
2. Add a `Thread` entity row to `lore/world-register.md` → `## Active Threads` with a starting Belief of 5–10
3. Tag all associated world-register entities with `[thread:new-id]` in their Notes field

**Minimum requirements for a new thread:**
- One named NPC anchor or location anchor with Belief ≥ 10
- A legible next beat (one sentence: what would advance this)
- A Nothing pressure assessment
- An entry in `## Active Threads` in world-register.md with `[id:slug]` in notes
- `**born:**` set to today's date; `**closed:** —`

---

## Thread: Elowen's Refectory Experiments

**id:** `elowen-refectory-experiments`
**type:** npc-subplot
**phase:** setup
**pressure:** low
**npc_anchor:** Dr. Elowen Vellum
**locations:** Academy corridors, Library, Great Hall, and wherever the Unwritten Interest touches the day
**entities:** Dr. Elowen Vellum
**Nothing pressure:** medium - the Nothing can flatten this into mere trivia instead of lived story

**Next beat:** A precise longevity note appears with one useful experiment for the day, one measurement Elowen refuses to moralize, one recovery or training nudge, and one comfort she insists must remain part of the binding.

**Last advanced:** 2026-05-08
**born:** 2026-05-08
**closed:** —


## Thread: Inkrest's Difficult Pages

**id:** `inkrest-difficult-pages`
**type:** npc-support-subplot
**phase:** setup
**pressure:** low
**npc_anchor:** Dr. Selene Inkrest
**locations:** Reauthoring Rooms, dormitory margins, quiet halls, and wherever BJ brings a difficult page
**entities:** Dr. Selene Inkrest
**Nothing pressure:** medium - the Nothing can turn therapy into vague self-improvement copy, avoidance, diagnosis theater, or endless interpretation without a next-hour action

**Next beat:** Dr. Inkrest opens a scheduled office hour or gentle invitation that externalizes one problem, checks Vellum/fuel/heartbeat context, and translates one consciousness/brain-study insight into a preferred-story sentence or grounding action BJ can actually use.

**Last advanced:** 2026-05-14
**born:** 2026-05-12
**closed:** —


## Thread: Serenity's Unwritten Thread

**id:** `serenity-unwritten-thread`
**type:** npc-subplot
**phase:** setup
**pressure:** low
**npc_anchor:** Serenity Brown
**locations:** Academy corridors, Library, Great Hall, and wherever the Unwritten Interest touches the day
**entities:** Serenity Brown
**Nothing pressure:** medium - the Nothing can flatten this into mere trivia instead of lived story

**Next beat:** By full dark the seven salt-specks have set hard enough to catch lamplight, and a thin rime of dried brine traces the unfinished line between Zara's marble-rim and the verdigris crack on the Daedric X — half a gull-stroke laid down by the room itself, waiting for a hand to close it. Inkwell's pun-ledger has fallen open to a blank page that now faintly reeks of low tide, as if the nook were holding the pen out.

**Last advanced:** 2026-06-07
**born:** 2026-05-26
**closed:** —


## Thread: Gimble's Unwritten Thread

**id:** `gimble-unwritten-thread`
**type:** npc-subplot
**phase:** setup
**pressure:** low
**npc_anchor:** Gimble of the Errata Registry
**locations:** Academy corridors, Library, Great Hall, and wherever the Unwritten Interest touches the day
**entities:** Gimble of the Errata Registry
**Nothing pressure:** medium - the Nothing can flatten this into mere trivia instead of lived story

**Next beat:** Gimble of the Errata Registry leaves a concrete trace of this interest where bj can find it: a note, object, recommendation, or small request that reveals whether their gift is helping or becoming tangled in can become too interested in classification; may mistake emotional avoidance for a filing problem; needs reminding that sometimes a person needs soup before categories..

**Last advanced:** 2026-06-02
**born:** 2026-06-02
**closed:** —


## Archive

*Threads that have reached their conclusion — natural resolution or quiet extinction.*
*Their stories are over. Their Belief has settled. They remain here as memory.*

*(No archived threads yet — the Academy is young.)*

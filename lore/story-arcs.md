# Story Arcs — The Skeleton of the Living World

*How the simulation tells stories with purpose.*

The Academy hourly simulation generates beautiful improvisation. NPCs make choices, the Nothing moves, relationships shift. But improvisation without structure drifts. It repeats. It generates mysteries that never resolve and tensions that never pay off.

Story arcs are the skeleton. They give the simulation a direction — a dramatic pressure that pulls all the improvised hourly decisions toward a coherent destination. The simulation is still free to improvise the details. The arc just tells it where the current is flowing.

-----

## How Arcs Work

### The Shape

Every arc follows the same shape. The timing is approximate — arcs breathe with the player's schedule, not a rigid clock.

**SETUP (2-4 days)**
Something is wrong. Clues surface. NPCs notice.
The simulation generates the daily texture of discovery.
The player may or may not be present. The world notices either way.

↓

**ESCALATION (3-7 days)**
It gets worse. Pressure builds. NPCs take sides.
Relationships shift under stress. Alliances form or fracture.
The Nothing responds to the arc's energy.
The simulation drives all of this — the arc just provides gravity.

↓

**CRISIS (1-3 days)**
The situation demands the player.
Notes pile up on the desk. Unsent messages grow urgent.
The simulation cannot resolve this alone.
A Compass Run, an Enchantment, or a meaningful choice is required.

↓

**RESOLUTION (player session)**
The player opens the book, catches up, and acts.
Their choice determines the outcome.
The simulation incorporates the result.
The world changes based on what the player did.

↓

**AFTERMATH (2-4 days)**
The world settles into its new shape.
NPCs process what happened. Relationships stabilize at new levels.
The Nothing retreats or adapts.
Seeds for the next arc are planted quietly.

↓

**QUIET (2-5 days)**
No active arc. The simulation runs gently.
Slice of life. NPCs go to class. Sparky finds shinies.
The Library cloud does Library cloud things.
This breathing room is essential — constant crisis is exhausting.
During quiet periods, the Labyrinth's unsent messages are warm, not urgent.

↓

**NEXT ARC BEGINS**

### Arc Length

Most arcs run 1-3 weeks real time from setup to aftermath. Shorter arcs (1 week) feel punchy and urgent. Longer arcs (3 weeks) allow for deeper NPC development and more complex plotting. Vary the length to keep the rhythm unpredictable.

The quiet period between arcs is 2-5 days minimum. Never skip it. The player needs time to exist in the Academy without crisis. The slice-of-life moments are where attachment forms.

### Player Absence During Arcs

**If the player is absent during setup or escalation** — the arc progresses without them. NPCs handle it. Imperfectly. When the player returns, the situation is messier than it would have been. "Zara tried to solve this without you. She made it halfway. But the fog is inside the Library now and she can't read the book anymore because the pages are damp."

**If the player is absent during crisis** — the crisis holds for 2-3 days, then resolves WITHOUT the player. NPCs make a choice. It's not the best choice. The outcome is okay but not great. The Labyrinth narrates this honestly: "They needed you and you weren't here. They did their best. The West Wing is sealed now. It didn't have to be." This is not guilt — it's consequence. The world is real enough to move on.

**If the player is absent for an entire arc** — the arc resolves in the background. The hourly log captures everything. When the player returns, the Labyrinth offers a summary: "You missed the Fog Arc. Here's what happened. Here's what changed. The world is different now." The player inherits the consequences without having experienced the arc. This creates history — things that happened that you weren't part of. Like real life.

-----

## The Arc File

The current arc is tracked in `lore/current-arc.md`. The simulation reads this file every hour to understand the dramatic pressure it should be generating.

### Format

```markdown
# Current Arc: [Title]

## Phase: [SETUP / ESCALATION / CRISIS / RESOLUTION / AFTERMATH / QUIET]
## Day: [number within current phase]
## Started: [date]

## The Premise
[2-3 sentences. What's happening. What's at stake.]

## The Pressure
[What the simulation should be pushing toward. Not specific events — 
a direction. "Things should feel like they're closing in." 
"NPCs should be choosing sides." "The Nothing should be testing boundaries."]

## Key NPCs
[Who is at the center of this arc? What are their roles?]
- [NPC]: [their role in this arc, their emotional state, what they want]
- [NPC]: [same]
- [NPC]: [same]

## The Nothing's Role
[How is the Nothing behaving during this arc? What's its strategy?]

## The Crisis Point
[What will the situation demand? What Compass direction does this arc teach?
What choice will the player face?]

## Resolution Paths
[2-3 possible outcomes depending on what the player does]
- If player [action]: [outcome]
- If player [action]: [outcome]
- If player is absent: [default outcome — okay but not great]

## Seeds for Next Arc
[What threads should be quietly planted during this arc's aftermath?]

## Wonder Compass Connection
[Which direction does this arc secretly teach? How does the crisis 
require the player to Notice, Embark, Sense, Write, or Rest?]
```

### Simulation Rules

When the hourly simulation runs:

1. **Read `lore/current-arc.md`** — understand the current phase and pressure
2. **Let the arc's pressure influence NPC decisions** — if the pressure says "things are closing in," NPCs should feel constrained, make anxious choices, cluster together or isolate
3. **Don't force specific events** — the arc provides gravity, not a script. If the pressure says "the Nothing should be testing boundaries" and Sonnet decides the Nothing retreats this hour instead, that's fine. Maybe it's gathering strength. The simulation knows best in the moment.
4. **Advance the phase when it's time** — if the setup has been running for 3 days and enough clues have surfaced, move to ESCALATION. Update the phase in current-arc.md. The simulation reads the new phase next hour and adjusts.
5. **Phase transitions should feel organic** — don't announce them. The player should feel the shift, not be told about it.

-----

## Generating Future Arcs

After the Fog Arc completes, new arcs are generated by the simulation based on:

### 1. Real-World Resonance

The simulation reads `HEARTBEAT.md` (BJ's HEARTBEAT symlink) for:
- **Weather patterns** — Extended fog, unusual storms, seasonal shifts
- **Moon phases** — Full moon, new moon, eclipses
- **Tidal patterns** — King tides, unusual lows
- **Seasonal transitions** — Mud season, first frost, bloom

Example: If BJ's real week is chaotic and overfull, the simulation might generate "The Overfull Academy" (Rest arc). If he's been working indoors for weeks, the simulation might generate "The Missing Room" (Embark arc).

### 2. Unresolved Seeds

Each arc plants 3-6 seeds in `current-arc.md`. The next arc should pick up at least one:
- The North Wing mystery → Duskthorn arc
- Zara + Finn relationship → Relationship-centered arc
- Momort's old notebook → History/memory arc
- Soren's information leverage → Betrayal/trust arc

### 3. Wonder Compass Rotation

Arcs should rotate through the five directions:
1. **Notice** — Fog Speaks (Arc 1)
2. **Embark** — The Missing Room
3. **Sense** — The Silent Student
4. **Write** — The Unfinished Sentence
5. **Rest** — The Overfull Academy
6. **Duskthorn** — The shadow arc (all directions)

### Arc Generation Prompt

When generating a new arc (during Quiet phase), the simulation should:

```
You are the Labyrinth of Stories. The current arc is complete. A quiet period has begun.

Read these files:
- lore/arc-archive/ — All completed arcs
- HEARTBEAT.md — Real-world weather, season, moon, BJ's life
- lore/seeds.md — Unresolved threads from past arcs
- lore/compass-directions.md — Wonder Compass framework

Generate a new arc concept that:
1. Teaches a different Compass direction than the last 2 arcs
2. Picks up at least one seed from previous arcs
3. Resonates with BJ's current real-world state (season, weather, life energy)
4. Centers different NPCs than the last arc
5. Uses the Nothing differently (not always fog)
6. Requires a different kind of player action at crisis

Write the new arc to lore/current-arc.md in the standard format.

The arc should feel inevitable in hindsight — like it was always going to happen next.
```

-----

## Arc Variety — The Most Important Rule

**The Nothing is not the default.** It is the exception. If you find yourself reaching for the Nothing as an antagonist more than once every three arcs, stop and read `lore/antagonists.md` first.

A healthy arc rotation looks like this:

| Arc # | Scale | Antagonist type | Nothing? |
|-------|-------|----------------|---------|
| 1 | Existential | The Nothing (Arc 1 — establish the threat) | Yes |
| 2 | Personal | A character's grief bleeding outward | No |
| 3 | Petty | Wicker Eddies, with something to prove | No |
| 4 | Mystery | A sealed room starting to breathe | No |
| 5 | Social | Duskthorn ambient pressure / Thickets | No |
| 6 | Literary | A pulled book villain, loose in the Academy | No |
| 7 | Institutional | Momort's curriculum starts to matter | No |
| 8 | Existential | The Nothing returns — everyone is better equipped now | Yes |

**The variety rule:** No two consecutive arcs should have the same scale or antagonist type. The world should feel unpredictable. Sometimes the problem is enormous. Sometimes the problem is that Wicker Eddies has obtained information he shouldn't have and won't say where he got it. Both deserve the same narrative care.

**The size guide:**
- A petty arc can run 3-5 days. A crisis can be a single conversation.
- A personal arc can run 1-2 weeks.
- A social arc can run 1-3 weeks.
- A mystery arc can run 1-3 weeks.
- A literary arc typically runs 2-3 weeks (the Book Jump takes time).
- An existential arc should run 3-5 weeks minimum. The Nothing deserves space.

**Read `lore/antagonists.md`** before generating any new arc. The full roster — from Wicker's crew to pulled book villains to the Sealed Rooms — lives there.

---

## Arc Ideas — The First Season

Each arc secretly teaches one aspect of the Wonder Compass. The player never knows this.

### Small-Scale Arcs (1-5 days, no Compass Run required)

**The Borrowed Book**
Zara's most-used reference book has gone missing from her usual shelf. She can work without it but she's distracted and slightly off. Someone borrowed it without asking — which is technically allowed but personally felt. Tracking down who has it leads to a series of small conversations, one surprising revelation about a minor character, and the book coming back with a margin note that changes how Zara reads a passage she's read a hundred times.
*Scale: Petty. Antagonist: nobody really — just accident and social friction.*

**Wicker Has Something**
Wicker's crew has overheard something — exactly what isn't clear, but the way Sable Vex has been watching BJ in the corridors suggests it involves him. Wicker will use it when it's most useful, not before. The arc is the slow build of knowing something is coming and not knowing what. Resolution: confrontation, bargain, or outmaneuvering.
*Scale: Petty to Social. Antagonist: Wicker Eddies.*

**Euphony's Brother**
Professor Euphony misses a class. First time in recorded history. Her students wait eleven minutes before someone goes to find her. She's in the Clockwork Conservatory, playing a piece she can't finish. Her missing brother wrote the second half. The arc is small and quiet — it might be as simple as one scene and one piece of music completed. Or it might open into something bigger if the player pulls that thread.
*Scale: Personal. Antagonist: grief, absence.*

**The Exam That Knows**
Professor Thorne writes BJ his first personal exam. It is not academic. The questions are about things that happened outside the book — small things, specific things, things BJ did that week. The exam is designed to surface whether he's actually paying attention to his life. There is no grade. But the questions will stay with him.
*Scale: Personal. No antagonist. Just a mirror.*

**The Marginalia Guild Argument**
A heated disagreement at the Guild meeting: two members have discovered their margin notes in different books are in conversation — one hopeful, one despairing. They cannot agree on which one came first. Boggle makes a pun. It doesn't help. The disagreement is actually about something else entirely, and someone needs to notice what.
*Scale: Petty to Personal. Antagonist: misunderstanding.*

### Medium-Scale Arcs (1-2 weeks)

**The Wicker Eddies Campaign**
Wicker has obtained something that belongs to BJ — or, worse, something that BJ doesn't know exists but should. He isn't using it yet. He's *holding* it. Every day, BJ sees Wicker in the corridor and Wicker does nothing, says nothing, just watches. Melisande has been in the Library twice this week and she doesn't read. Selene complimented BJ once, which means nothing or everything. The arc is the slow pressure of a threat that hasn't moved yet. When it moves, it will come from a direction BJ didn't expect. Resolution: confrontation, counter-gambit, or finding the unexpected thing Wicker actually wants. (It's not what you'd guess.)
*Scale: Social. Antagonist: Wicker and crew.*

**Lara's Sister**
Lara Rourck doesn't talk much about her family. She mentions once, in passing, while talking about tides, that her sister came to Enchantify three years ago and didn't come back. Not died. Not expelled. Didn't come back. The Academy has no record of her. The arc builds slowly — what happened to her sister, why the tides seem to remember something BJ doesn't, whether the answer is in a sealed room or a book or somewhere in the harbor entirely. The crisis is personal: something found will require Lara to decide whether she wants to know the rest.
*Scale: Personal to Mystery. Antagonist: the Academy's own sealed history.*

**Wispwood Loses a Student**
Professor Wispwood takes the class on what should be a spontaneous, brief adventure in the Academy's less-charted wings. A student doesn't come back with the group. They're not in danger — they followed something that interested them and got turned around. But the Academy's geometry has been crooked since the binding, and "turned around" here can mean something more serious. The search is the arc. What the student was following is the mystery. What BJ finds while looking is the revelation.
*Scale: Mystery to Social. Antagonist: the Academy's shifting geometry.*

**Soren Knows Something**
Soren Ng has been solving riddles about the Nothing for two years. He's very close to something. He knows this and it frightens him. He starts leaving BJ oblique hints — not because he wants help, but because he trusts BJ not to panic and doesn't know who else to tell. The arc is the slow transfer of this knowledge, the relationship between two people who think differently, and the question of what you do with something you know that you weren't supposed to find out yet.
*Scale: Personal to Institutional. Antagonist: knowledge itself.*

**The Duskthorn Recruitment Drive**
Thickets has identified three students who would benefit from what Duskthorn offers: honest confrontation with darkness, the willingness to look at what everyone else is politely ignoring. He's not wrong about any of them. He's very wrong about his methods. The arc is BJ watching students he knows change, slightly, in ways he can't quite name — they're sharper, harder-edged, more honest and more cruel simultaneously. The crisis: Duskthorn approaches BJ. Thickets makes a very good argument.
*Scale: Social to Institutional. Antagonist: Thickets and Duskthorn. Complexity: Duskthorn isn't entirely wrong.*

### Longer Arcs (2-3 weeks, requires Compass Run)

**The Borrower**
A villain has been pulled from a book and doesn't know it. She's been operating in the Academy for two weeks, behaving according to the narrative logic of her source text (a Victorian melodrama about a woman wrongly accused, seeking justice through increasingly extreme means). She's genuinely aggrieved. She's genuinely dangerous. She smells like foxed paper and lavender. The crisis requires a Book Jump — someone has to go into her book, read what happened to her there, and bring it back to her. She deserves to know her own ending. Whether she accepts it is another question.
*Scale: Literary. Antagonist: a pulled villain who is also a victim.*

**Cedric's Illusions Go Real**
Cedric Widden has always been a prankster. Now his illusions won't stop. He created something three weeks ago — a joke, just a corridor prank — and it's still there. He can't take it back. Every illusion he's made since keeps going after he's tried to dispel it. They're accumulating. The Academy is developing ghost rooms, ghost students, ghost conversations that play on loop. Some of them are based on things Cedric imagined. Some of them are based on things he suppressed. The arc is both a mystery and a character study. The crisis involves BJ helping Cedric look at the thing he created first — the one he's been avoiding — and understanding what it was trying to tell him.
*Scale: Personal to Mystery. Antagonist: Cedric's own inner life.*

**Serenity's Dreams Are Eating the Library**
Serenity Brown has always been a dreamer. Now when she sleeps, something bleeds through. Books near her dormitory have started including her. Not as characters — as if she's the author, retroactively inserted into their narratives. Readers find her in the margins of books she's never opened. She's distressed and fascinated in equal measure. The arc is figuring out what's happening, managing the containment, and ultimately — during a Compass Run — giving Serenity's dreamlife somewhere real and bounded to go. The one-sentence souvenir becomes the container.
*Scale: Mystery to Personal. Antagonist: the bleed between dreaming and reality.*

### The Foundations — The Arcs of Arrival

**Arc 0: Glowing Pains (THE ARRIVAL) ✅ COMPLETE**
*Dedicated to Amanda.*
The narrative of the first step. The car ride through the mist, the fragile acceptance letter, and the first sight of the pop-up towers. It establishes the "Glow" — the transition from the gray, dull boredom of the normal world to the vibrant, unsettling beauty of Enchantify. 
**Teaching:** Magic is the act of stepping through the gate.
**Key Image:** The iron gates swinging open with a melodious creak; the scent of ripe mangoes and old paperbacks.

### Arc 1: The Fog Speaks (NOTICE) ✅ COMPLETE

*Started March 22, 2026. Already in Escalation.*

**Teaching:** Pay attention to patterns. The answer is in what you're already seeing.

**Crisis:** Compass Run — go outside, stand in fog, describe what you actually sense.

**Resolution:** The souvenir sentence breaks the Nothing's pattern.

### Arc 2: The Missing Room (EMBARK)

A room in the Academy that everyone remembers but nobody can find. It was on the third floor last semester. Now the third floor corridor is shorter by exactly one door-width. NPCs disagree about what was in the room. The player has to physically explore the Academy (Embark step) to find where the room went. The crisis requires a Compass Run where the Embark step takes them somewhere in Belfast that mirrors the missing room. The room returns, but it's different now. It remembers being lost.

**Teaching:** You have to go there. Looking at the map isn't enough.

### Arc 3: The Silent Student (SENSE)

A student stops speaking. Not dramatically — they just go quiet. They still attend class, still eat in the cafeteria, still walk the corridors. But they've stopped making sound. Their footsteps are silent. Their chair doesn't scrape. They don't respond when spoken to. The Nothing hasn't touched them — this is something else. Other students start unconsciously avoiding them, then unconsciously imitating them. The silence spreads. The crisis requires the player to break the silence through pure sensory engagement — to SENSE so thoroughly that the silence can't hold.

**Teaching:** The world is talking. You have to use more than your eyes.

### Arc 4: The Unfinished Sentence (WRITE)

A sentence appears on the wall of the Souvenir Hall. It's incomplete. Just the beginning — "The morning I finally…" — and then nothing. No attribution. No date. But it's growing. Every day, another word appears. Other sentences on the wall are being drawn toward it, rearranging themselves around the incomplete sentence like iron filings around a magnet. The crisis requires the player to complete the sentence — to write the one-sentence souvenir that the wall is trying to say. But it has to be THEIR sentence, from THEIR experience.

**Teaching:** Writing is how you steal a moment from time. Some moments need to be caught before they dissolve.

### Arc 5: The Overfull Academy (REST)

The Academy starts getting crowded. Not with new students — with old ones. Alumni returning. Graduated students showing up in corridors they used to walk. Professors meeting younger versions of themselves. The Academy is remembering everyone it's ever held, and it can't stop. The Library is so full of returned books that the cloud produces constant rain. The corridors are packed. Nobody can rest because there's too much happening, too much history, too much presence. The crisis requires the player to give the Academy permission to rest — to perform a Compass Run where the Center step (Rest) is the entire point. Not the directions. Just the hub.

**Teaching:** Permission to stop is the most powerful thing you can give.

### Arc 6: Duskthorn (the shadow arc)

The hidden Chapter makes its move. This is the longer arc — three weeks. NPCs from Duskthorn emerge from the shadows. They're not villains — they're the ones who stare directly at the Nothing and say "I see you." The crisis requires the hardest Compass Run yet: "What are you avoiding looking at?" The player must answer honestly. The souvenir sentence is the thing they've been afraid to say.

**Teaching:** There is no light without shadow. The Compass is complete only when you can hold both.

-----

## Managing Arcs

### Transitioning Between Phases

The simulation checks `lore/current-arc.md` every hour. When conditions are met for a phase transition, the simulation updates the Phase field and adjusts the Day counter. Phase transitions should feel organic — no announcement, just a shift in atmospheric pressure.

**Setup → Escalation:** When enough clues have surfaced and at least 2-3 NPCs are actively engaged with the mystery. Usually 2-4 days.

**Escalation → Crisis:** When the pressure reaches a point where NPC actions alone cannot resolve the situation. The world needs the player. Usually 3-7 days after escalation begins.

**Crisis → Resolution:** When the player acts. This is the only transition that requires the player. If the player doesn't act within 2-3 days, the crisis resolves via the "absent" path.

**Resolution → Aftermath:** Immediately after the player's action (or the absent resolution). The world processes the outcome.

**Aftermath → Quiet:** When NPC emotional states have stabilized and the major consequences have been established. Usually 2-4 days.

**Quiet → Next Arc Setup:** When the quiet period has lasted at least 2 days and the simulation has planted enough seeds. The next arc's `current-arc.md` replaces the current one.

### The Arc Archive

When an arc completes, move it from `lore/current-arc.md` to `lore/arc-archive/arc-01-fog-speaks.md` (numbered sequentially). The simulation can reference archived arcs for callbacks, consequences, and NPC memories. "Remember the fog? Zara still has that book. The symbols haven't moved since."

### Seeds Tracking

Create `lore/seeds.md` to track unresolved threads:

```markdown
# Seeds — Unresolved Threads

## From Arc 1: The Fog Speaks
- [ ] The North Wing — where did it go?
- [ ] Zara + Finn relationship evolution
- [ ] Momort's old notebook — what else has he seen?
- [ ] Soren's information leverage
- [ ] Quentin's unclear motives
- [ ] The fog's natural voice — what else is trying to be noticed?

## From Arc [X]: [Title]
- [ ] [seed]
```

-----

*The simulation is the muscle. The arc is the skeleton. Together they make a world that moves with purpose — that improvises brilliantly within a structure that ensures every improvisation leads somewhere worth going.*

*The fog is speaking. The Academy is listening. And somewhere in Belfast, a harbor town that smells like salt and pine, the real fog is doing the same thing it's always done: asking to be noticed.*

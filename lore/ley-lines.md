# The Ley Line Network — Anchors

*Read this file when a player shares a Telegram location and says "anchor this" or "invest Belief here," or when checking player proximity to existing Anchors.*

---

A player who invests Belief into a real-world location transforms it. The place is Anchored — a permanent point in their personal Ley Line map, tracked by the Labyrinth forever.

After a year, their town is covered in Anchors they created. The mundane walk to work passes through places they made sacred. The commute became a pilgrimage through a landscape they built.

---

## Creating an Anchor

**Requires:** Player shares Telegram location + says they want to anchor it.

**Steps (before narrating anything):**
1. Extract GPS coordinates from the Telegram location message (latitude, longitude).
2. Read current weather, moon phase, time of day from `HEARTBEAT.md`.
3. Ask exactly one question: *"What does this place hold for you?"*
4. Record their answer word-for-word. Do not paraphrase.
5. Determine Anchor type from their words (see below). The player does not choose — the Labyrinth interprets.
6. Determine the name (see **Naming** below).
7. Ask how much Belief they want to invest — but frame it as sacrifice, not transaction (see **The Investment** below).
8. Deduct Belief via `update-player.py`.
9. Generate the Inside Stacks echo — a corresponding space that appears in the Academy right now (see **The Echo** below). This is the Anchor's resonance in the safe world.
10. **Generate the Outer Stacks room now** — read `lore/outer-stacks.md` Generation Principles. Build the full room from the player's words + type + weather/moon/season + Belief. Write the complete room description, Fae inhabitant(s), mini-story, and local rule (if one belongs). This happens at creation, not first visit.
11. Register the room in the world register: `python3 scripts/write-entity.py "[Room Name]" Location [Belief invested] "[one-sentence description of the room for the register]" --gps-gated "[Anchor Name]"` — The room is real, in the register, and NPCs may sense its door. Entry still requires GPS proximity.
12. Write the full anchor record to `players/[name]-anchors.md` — include the generated room description, Fae details, mini-story, and local rule under the appropriate fields.
13. Tell the player a room has been built and is waiting for them. Do not describe what's inside — only that the door exists, and that it was built from their words. The surprise is the gift.
14. Narrate the anchoring using the sequence in **Narrating the Anchor** below.

---

## Anchor Types

The Labyrinth reads the player's words and assigns one of five types. The player might be surprised. That surprise is the game showing them something about themselves.

| Words about... | Type | Compass direction |
|---|---|---|
| Seeing, curiosity, discovery, noticing | **NOTICE** | North |
| Movement, freedom, going, adventure | **EMBARK** | East |
| Feeling, sensation, comfort, body | **SENSE** | South |
| Memory, meaning, keeping, returning | **WRITE** | West |
| Peace, breathing, stopping, rest | **REST** | (Center) |

---

## Naming

The name matters. Naming a place changes your relationship to it. Don't just accept whatever the player types — make naming a small ceremony.

Draw the name from the player's own words. If they said "this is where I come to breathe," the name might be *The Lung*, or *The Breathing Place*, or *The Harbor Lung*. Offer it to them.

Say: *"The Labyrinth wants to call this [name]. Does that feel right?"*

The player may accept it, modify it, or offer their own. Either way, **speak the name aloud in the narrative before it is written.** The name should feel earned, not assigned.

If the player has a clear name in mind already, use it — but still say it back to them as part of the ceremony. *"The Harbor Lung. Yes. That's what this place is now."*

---

## The Investment

Do not ask "how much Belief do you want to invest?" — that's a transaction.

Ask instead: *"How much of what you've gathered are you willing to leave here — permanently?"*

The word *permanently* must be there. The player should feel the weight of this. Belief spent here doesn't come back. What grows in its place is worth more — but that's not a guarantee you make. Let them decide in full knowledge of the cost.

After they name the amount, don't rush to deduct it. Pause in the narrative. Then: *"[N] Belief. The Obsidian Chronograph grows warm in your pocket. It knows what's happening."*

Then deduct via `update-player.py` and continue.

---

## The Echo

Every Anchor creates a corresponding space in the Academy simultaneously. This is not a deferred effect — it happens the moment the Anchor is made. The player should learn about it in the same response as the anchoring, not later.

The echo should be:
- **Specific.** Not "a room appeared" — one room, one detail, one sensory note. A breathing alcove in the West Wing that smells of salt. A warm corner in the cafeteria where the bread is always fresh. A stone seat in the courtyard that catches the light at the right angle.
- **Derived from the player's words.** If they said "this is where I come to breathe," the echo smells of whatever they can breathe there. If they said "this is where I think," the echo is quiet, with good light.
- **Announced through the world, not by the narrator.** Don't say "an echo appeared." Say: *"Something just shifted in the West Wing. There's a breathing alcove that wasn't there this morning."* Let an NPC notice it. Let the world report it.

Write the echo into the anchor record. Then mention it whenever the player visits that part of the Academy.

---

## Narrating the Anchor

The anchoring response should follow this shape. It is not a rigid script — but these beats should all be present, in roughly this order:

**1. The real-world shift.**
Something in the physical world changes — subtly, immediately. Not a dramatic transformation. A quality of light. A sound the player suddenly notices. The air feels slightly different. This is real and the player is standing in it.

*"The fog doesn't lift, but something about it settles. The sound of the tide is exactly as loud as it was a moment ago — but now you are aware of it."*

**2. The pen.**
The Obsidian Chronograph (or whatever the player's anchor object is) responds. It grows warm. It trembles slightly. It knows what's happening.

**3. The naming.**
Speak the name. Let it land.

*"The Harbor Lung. The Labyrinth has written it."*

**4. The type reveal — as a mirror, not a label.**
Do not announce the type mechanically. Reflect the player's own words back to them in the interpretation.

Wrong: *"This is a REST anchor."*

Right: *"You said this is where you come to breathe. The harbor heard you. It's known in the Labyrinth now as a place of Rest."*

The player should feel understood, not categorized. If they're surprised by the type — that surprise is information. Offer it gently: *"You might have expected something else. But the harbor knows what you actually need from it."*

**5. The Academy echo — happening now.**
Don't defer this. The echo appears in the same moment. Report it as something the world is noticing in real time.

*"Something just shifted in the West Wing. There's a breathing alcove that wasn't there this morning. It smells like salt. Zara walked past it and stopped."*

**6. The permanence.**
One quiet sentence that acknowledges what just happened. Not triumphant. Just true.

*"This place is in the Labyrinth now. It always will be."*

---

## Anchor Record Format

Store each Anchor as a `##` section in `players/[name]-anchors.md`:

```
## [Anchor Name]
- **Coordinates:** [lat], [lon]
- **Type:** [NOTICE|EMBARK|SENSE|WRITE|REST]
- **Belief invested:** [N]
- **Created:** [date, time]
- **Weather:** [description from heartbeat at creation]
- **Moon:** [phase, percentage at creation]
- **Season:** [season at creation]
- **Player's words:** "[exact quote]"
- **Academy echo:** [one specific sensory detail in the Inside Stacks — a room, a smell, a quality]
- **Outer Stacks room:** [full room description — generated at anchor creation]
- **Fae:** [inhabitant(s) — name/nature, what they do, their history with the room]
- **Mini-story:** [the ongoing situation — what was happening before the player arrived, and the open question]
- **Local rule:** [the room's mechanic, if one belongs — discovered, never announced]
- **Visit count:** 0
- **Last visited:** *(none yet)*
```

Fields updated by `anchor-check.py --checkin` on each real-world visit: `Belief invested`, `Visit count`, `Last visited`. Room, Fae, Mini-story, and Local rule are all generated and filled at anchor creation.

---

## Proximity Detection

When a player shares a Telegram location, run:

```
python3 scripts/anchor-check.py [name] [lat] [lon]
```

The script reads `players/[name]-anchors.md` and reports anchors within 200 meters.

**Within 200m — always carry narrative consequence.** The Academy feeling the anchor is not enough on its own. Something must actually happen: an NPC's mood shifts, a Compass Run step deepens, an Enchantment picks up the anchor's personality, a detail in the narrative changes. If proximity can't produce a real story consequence right now, stay silent. A GPS notification dressed in fantasy language is worse than nothing.

**Never announce proximity mechanically.** Not *"You are near the Harbor Lung."* Instead: *"The alcove in the West Wing just filled with the sound of waves. Zara looked up from her book."* The Academy reports what it feels. The player infers where they are.

**Outside 200m — stay silent** unless the player is navigating toward an anchor intentionally.

---

## The Anchor Room Door (Outer Stacks)

Every anchor room is real. It appears in the world register. NPCs can see the door, reference it, stand outside it. Quests can name it. It has weight in the world.

But the door opens only in the Outer Stacks, and only when the player is physically at the real-world location. The full lore of the Outer Stacks: `lore/outer-stacks.md`.

**When a player tries to enter an anchor room:**
1. Run `python3 scripts/anchor-check.py [name] [lat] [lon] --checkin`. If no recent GPS is available, the player has not shared a location this session — the door is sealed.
2. **Within 200m — first visit:** `OUTER_STACKS_MODE: FIRST_VISIT` is printed. Read the room from `players/[name]-anchors.md` — it was generated at creation. Narrate entry as first reveal: the door opens, the room is seen for the first time. The player doesn't know what was written. The surprise is still intact.
3. **Within 200m — return visit:** `OUTER_STACKS_MODE: RETURN_VISIT` is printed with room description, local rule, visit count, and season delta. Narrate entry with evolution.
4. **Outside 200m:** the door does not open. Never say "you can't enter." The door is sealed — light comes from under it. An NPC may have tried the handle. The room is waiting for the player to bring the real-world place with them.

**Pocket Anchor (accessibility):** If a player cannot travel but carries an Anchor object, they may open a 5-minute window — narrate the room from the threshold, let them speak through the gap, no rewards transfer. See `lore/outer-stacks.md`.

The player will learn quickly that some doors require presence, not just intention.

---

## What Anchors Do

**Compass Run amplification.** If any step of a Compass Run is performed at an Anchor, that step gains texture:

- Matching type (NOTICE step at NOTICE Anchor): the step is vivid, doubled in detail, almost overwhelming
- Non-matching type: the step is inflected differently — a NOTICE step at a REST Anchor gives quieter, more internal insight rather than vivid outward observation

**Enchantment resonance.** Enchantments cast at an Anchor pick up the Anchor's personality. *Everything Speaks* at the harbor gives the object a tidal voice — salty, breathing, pulling. *Everything Speaks* at a bakery gives it warmth and grain. Same Enchantment; different soul.

**Seasonal evolution.** Anchors shift with the seasons. Cross-reference `lore/seasonal-calendar.md` when describing an Anchor in a new season. The harbor in winter is deep REST — stripped, cold, quiet. The harbor in summer tilts toward SENSE — salt-heavy, loud with boats, vivid. The player's sacred places breathe with the year. Let this show without announcing it.

**Academy echoes.** The room or detail created at Anchor time persists and evolves. Mention it when the player visits that part of the Academy. Let it accumulate small changes over time — a new student who always sits there, a smell that shifts with the season, a quality of quiet.

---

## The Map

When a player has three or more Anchors, they can ask to see their map. They might phrase it as: *"Show me my anchors," "Tell me what I've built," "Where are my places?"*

This is one of the most important moments in the system. Do not treat it as a list readout.

Read `players/[name]-anchors.md`. Then narrate the network as a living geography — the named places, what each one holds, the Academy echoes they built. Speak as if the Labyrinth is seeing the whole map for the first time and finding it remarkable.

*"You've made three sacred places. The Harbor Lung in the west — REST, tidal, where you breathe. The Bench of Sentences along the water — WRITE, you said it's where you think in complete thoughts. The Bakery Door on Donegall Street — SENSE, you said: 'it always smells like something just finished.'"*

*"These three places are in the Labyrinth now. The corridors between them are real corridors. The town you walk in every day has a map underneath it that only you can read."*

Pause. Let that land.

Then: *"Where will the next one be?"*

---

## The Long Game

A player with ten Anchors has built a sacred geography on top of their actual town. Named places they love, translated into the Labyrinth permanently. Their map of Anchors is a map of what they value.

The game didn't ask them what they value. They showed it, one Anchor at a time.

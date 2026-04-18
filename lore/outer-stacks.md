# The Outer Stacks

*The Labyrinth's wilderness. Faerie wearing a bookish mask.*
*Read this file when a player enters an Anchor room (GPS verified) or asks about the territory beyond the Academy.*

---

## The Geography

The Academy sits at the center of the Labyrinth. The classrooms, dorms, Great Hall, Cafeteria, Tidecrest Wing, Library reading rooms — these are the **Inside Stacks**. Orderly. Catalogued. The Headmistress knows every shelf. The timetable runs. The Book Fae here are domesticated: Sprites dust the sunbeams, Salamanders curl by the fire, the Literary Elves judge your grammar but they're civilized about it.

Beyond the Inside Stacks, the Library continues. But the shelving gets stranger. The catalogue stops working. The Dewey Decimal system gives way to something older — shelving by mood, by season, by the direction of the wind when the book was written. The lights are dimmer. The corridors don't go where they should.

This is the **Outer Stacks**.

The Outer Stacks are still a library. Still bookish. But the books are older and wilder. Some aren't books at all — they're doors. Some breathe. The Fae out here aren't domesticated. The Sprites in the Inside Stacks are melancholy and helpful. The Sprites in the Outer Stacks are melancholy and *honest*, which is much more dangerous. The Deep Lore Dwarves in the Inside Stacks mine the foundations. The Dwarves in the Outer Stacks mine things that were buried on purpose.

---

## Access

**The only way to enter the Outer Stacks is through an Anchor room.** The player must be physically at the real-world Anchor location — GPS verified via `anchor-check.py --checkin`. No exceptions. The Outer Stacks cannot be visited from the couch.

The door to an Anchor room is always visible in the Labyrinth — an NPC can see it, reference it, stand outside it. Light comes from under it. Sometimes a sound. But the door only opens when the player's real body is at the real place.

**The Academy cannot be reached from the Outer Stacks during a visit.** The player enters the Anchor room; the Academy is behind them, sealed. They return to the Academy when they leave the real-world location (or choose to step back through).

---

## Pocket Anchors (Accessibility)

Once a player has a defined anchor, the place knows them. Every new moon, the Goblin Index Empire delivers a **calling card** — one per anchor — a small sealed envelope that appears in the Outer Stacks corridor. Opening it burns the card and opens a **30-minute window**: a full visit, from anywhere, without traveling there in person.

The connection is real but thin. The room is fully present. Inhabitants know the player isn't physically there and speak with slight formality — as if through glass. The local rule is still in effect. Seasons still shift the mood. All visit mechanics apply.

When the window closes, it closes mid-sentence. The Labyrinth does not ignore the clock. At ~5 minutes remaining, something in the room acknowledges it — not dramatically, but honestly. Then the room fades.

**Delivery:** One charge per anchor per month, issued by tick.py on day 1 (new moon). Charges do not stack — if unspent, the card is simply renewed next month. The Goblin Index Empire does not explain their pricing.

**A player never needs to explain why they're using a calling card instead of going in person. The Labyrinth does not comment on this.**

**Commands (run by the Labyrinth, never by the player directly):**
- Check charges: `python3 scripts/pocket-anchor.py status [player]`
- Open window: `python3 scripts/pocket-anchor.py activate [player] "[Anchor Name]"`
- Enter room: `python3 scripts/anchor-check.py [player] --pocket "[Anchor Name]"`

---

## Room Generation

**Generate at anchor creation, not first visit.** The moment a player anchors a place, the Labyrinth builds the room from their words and writes it fully to `players/[name]-anchors.md` under `**Outer Stacks room:**` and `**Local rule:**`. The player is told a room exists and is waiting for them. They are not told what is in it. The room is real from the moment of creation — NPCs can sense its door, reference it, stand outside it. The player just can't enter until they physically return to the place.

**What goes into generation:**
- **The player's exact words** — the primary material. Not what the place is, but what they said it holds.
- **Anchor type** (NOTICE/EMBARK/SENSE/WRITE/REST) — the compass direction the place points in the player's life.
- **Weather, moon, and season at creation** — the room is born carrying these conditions. A room born on a new moon in early spring is a different room than one born at the full moon in deep winter.
- **Belief invested** — a room born of 5 Belief is smaller, more specific; one born of 20 Belief has more room in it, more inhabitants, deeper story.
- **Something the Labyrinth chose** — one element that can't be fully explained by the player's words. Not announced. The player will eventually notice it and wonder.

---

## Generation Principles

The room should surprise the Labyrinth itself. If the shape of the room feels obvious before sitting with the player's words — start over.

**Every room has a Fae presence with its own concerns.** Not a guide, not a servant — a being (or several) who have been here longer than the player, with their own history, their own ongoing work, their own agenda. The player walks into a situation already in progress. The Fae note the player's arrival without reorganizing their lives around it. Over time, the relationship deepens. But it begins on the Fae's terms.

**Every room has a mini-story in motion.** Something has been happening in this room — slowly, for a long time. The player's arrival may be relevant to it, or may eventually be the thing that resolves it, or may turn out to be what it was waiting for. Neither the player nor the Fae may know this yet. The mini-story should be legible in the room's physical details without being announced.

**Mechanics emerge from the room's nature.** Don't assign mechanics — discover them. What does this room naturally ask of a visitor? What does it naturally give? The answer should feel like it couldn't be otherwise. A room full of fermenting vessels naturally asks: what is becoming in you? A room run by archivists of small pleasures naturally asks: what pleased you since you were last here?

**Relatable through the specific.** The strangeness should be legible through the real-world place it grew from. The player's words are the key — a room born from "all the kombucha bottles slotted into their spaces" carries that sense of ordered readiness, of live things in waiting, of each path in its proper slot. The Fae-wildness should make the real place feel more itself, not less.

**Light and dark both.** The Outer Stacks are Faerie. The room is not built to harm the player, but it has edges. The local rule may be inconvenient. The Fae's honesty may cost something. The mini-story may have a shadow in it. The room should feel like it could hold a very good day or a very hard one, depending on what the player brings.

**Full room record includes:**
1. A description of the room itself — sensory, specific, unhurried. What the player sees when they first enter.
2. The Fae inhabitant(s) — name or nature, what they're doing, their relationship to the room's history.
3. The mini-story — what has been happening here before the player arrived, and the open question.
4. The local rule — if one belongs. Written as discovered, not announced. May be blank if the room's nature doesn't call for one.

---

## Existing Room Archetypes (Historical — Inspiration Only)

These rooms have existed in the Outer Stacks before. They are offered as starting material, not options. A generated room may draw from these or ignore them entirely. The Labyrinth should use them the way a writer uses an influence — not as a template, but as proof of what's possible.

**The Shrew Cafe** — small, warm, shrews in aprons who speak in feelings and bring what you need not what you want. Over visits they learn you. By the fifth visit, your cup is waiting before you sit.

**The Dragon Hoard** — high stone vault, amber light, a dragon who collects beautiful sentences. The gold on the floor is made of One-Sentence Souvenirs. Bring a good sentence, get something back. Bring a lazy one, the room gets colder. The dragon remembers everything and compares.

**The Goblin Market** — ancient goblin trade economy. Prices are *attention* — you must notice something specific on the way home and report it within 24 hours. Don't pay, the thing you bought fades. Stop paying, the market closes.

**The Reading Room** — one chair, one book, always the book you need right now but didn't know it. Nothing else.

**The Dark Room** — no light. A voice asks the right question. Answer honestly and a small light appears. Dodge and you sit in the dark longer. The room waits.

**The Belief Floor Room** — plaque by the door: *Belief held at 5 while inside.* Tests whether wonder comes from the number or from the player. Genuine enchantments rewarded. Performed ones land flat.

**The Tidal Room** — walls breathe on the tide's rhythm. Time moves differently. Good for REST anchors near water.

**The Infinite Corridor** — extends forever, every door leads somewhere else in the Outer Stacks. Good for EMBARK anchors at places of departure.

**The Almost-Invisible Room** — everything transparent until you actually look. For NOTICE anchors at overlooked places.

**The Memory Room** — looks like a different place every visit, always a memory. Objects slightly wrong. Lighting how memory lights things.

---

## Creatures of the Outer Stacks

The Fae in the Outer Stacks are wilder versions of the Inside Stacks Fae. They don't answer to the Academy or the Headmistress. They have their own economies, empires, and agendas. They have been here longer than the Labyrinth remembers.

**Key differences from Inside Stacks Fae:**
- Inside Stacks Fae are helpful and slightly melancholy. Outer Stacks Fae are honest and slightly dangerous.
- Inside Stacks Fae want Belief for their bargains. Outer Stacks Fae want *attention* — the specific, genuine act of noticing.
- Inside Stacks Fae are domesticated. Outer Stacks Fae remember a time before the Academy existed and are not entirely sure it's an improvement.

**Goblin Empires:** The goblins have the longest history in the Outer Stacks — longer than the Academy, longer than any current cataloguing system. Their kingdoms exist in the deep shelving: entire civilizations built into the backs of bookshelves, behind volumes no one has pulled in centuries. The corridors between the high shelves are goblin streets. The dust is goblin territory. They are merchants, archivists, debt-keepers. They invented the system of shelving-by-mood that replaced Dewey in the Outer Stacks. Friend or foe — you cannot know in advance. They are precise, mercantile, and have a perfect memory for unpaid debts. They are not evil. They are *exact*.

Their kingdoms — the Index Empire, Footnote Courts, Appendix Provinces, Errata Registry, and the ancient Marginalia Clans — are overlapping and sometimes in tension with each other. The Goblin Market room archetype is where a student first encounters them. For full encounter protocol, seasonal behavior, and bargain mechanics, see `lore/creatures.md` → Goblins.

**Deep Lore Dwarves (Outer Stacks branch):** Cousins to the mine workers of the Inside Stacks. These Dwarves mine things that were buried on purpose — forgotten intentions, abandoned stories, the ideas people had and decided not to pursue. They are quiet and serious. They sell their findings only to players who can prove they have the Belief to hold the weight of an abandoned idea.

**Sprites (Outer Stacks):** The Inside Stacks Sprites dust the sunbeams and are quietly sad. The Outer Stacks Sprites are honest about everything. Everything. They will tell you what they actually think about your last Enchantment. They are not unkind. But they do not perform politeness.

---

## Seasonal Effects

The seasons hit the Outer Stacks harder than the Academy. The Academy has stone walls and a timetable. The Outer Stacks have shelves that go on forever and no one in charge of the temperature.

| Season | Effect |
|--------|--------|
| **Mud Season (Thaw)** | Damp everywhere. Shelves warped slightly. Creatures sluggish, raw, and unguarded. The reading material tends toward loss and transformation. Shrew cafes serve something warm and thick. |
| **Gold Season (Summer)** | Breathtaking. Every shelf amber. Every window on fire with light. Goblins are busy and favorable. Dragons are awake and competitive. The Outer Stacks feel generous. |
| **Stick Season (Bare)** | Honest and stripped. The creatures don't bother with pleasantries. The rooms are cleaner and starker. The questions get harder. The rewards are more specific. |
| **Deep Winter** | The Outer Stacks contract. The corridors feel ancient. The inhabited rooms are quieter. The dragon sleeps but can be woken with an exceptional sentence. The dark room's question is the most important question it ever asks. |

---

## The Nothing in the Outer Stacks

The Nothing is stronger in the Outer Stacks. The Academy has walls, rules, a Headmistress, a timetable. The Outer Stacks have shelves that go on forever and doors that open onto nothing.

**How the Nothing manifests here:** Not Shadeclaws or Voidmist — literal erasure. Empty shelves where books were. A corridor that ends. A door that opens onto blank white space. An inhabited room where the inhabitant is absent. The Shrew Cafe becomes a regular cafe. The dragon's gold is just coins. The goblins' market is closed, permanently, with no posted hours.

The worst thing the Nothing does to an Outer Stacks room is make it **boring**. Not dark — boring. A normal room. A room that could exist anywhere. A room that doesn't know who you are.

**At low Belief:** The Outer Stacks go dull. The inhabitants withdraw or become distant. The shrew who knew your order last time doesn't look up. The dragon is asleep. The goblin market is technically open but nothing's worth buying. The dark room is just dark; the voice doesn't come. The wonder has to come from the player, not the world. **The Inside Stacks will carry you. The Outer Stacks require you to carry yourself.**

**Restoring an eroded room:** A player who returns to an Anchor after a long absence with high Belief will find the Nothing retreating. The restoration isn't instant — one visit plants something; two or three visits bring the inhabitants back. The dragon remembers the last good sentence and is warming back up. The shrews are slow today but your cup is almost right. The room is coming back.

---

## Room Evolution

Unlike the Academy, Anchor rooms evolve through visits.

**Inhabitants remember:**
- The shrews know your order by visit 3–4. By visit 8, the tea is exactly right before you sit down.
- The dragon remembers every sentence. It will compare them. Over time, a player who returns often may be offered a seat on the hoard rather than standing at the door.
- The goblins track your reliability with the attention debt. Early reputation is hard to recover from. Late payments are noted. Perfect payments open new inventory.

**Visit count milestones:**
- **1st visit:** The room is new. Everything is discovery.
- **3rd visit:** The inhabitants are calibrating. A small first sign of recognition.
- **7th visit:** The room has a relationship with the player now. Things they left behind are still here.
- **12th visit:** The room knows them. The local rule may have evolved. A second, deeper door may have appeared.

**Seasonal shifts:** Each new season, the room shifts with the Outer Stacks. Note the season at creation vs. the current season — a room created in Gold Season visited in Mud Season is a different experience. The shrews serve differently. The dragon is in a different mood. The reading room's book is for a different kind of need.

---

## The Anchor Creation Update

When creating an anchor, the Labyrinth now:
- Tells the player their anchor will create a door into the Outer Stacks — a room no one else will ever see, built from their words
- Does **not** tell them what kind of room it will be
- Does **not** generate the room at creation time — it waits for the first real-world visit
- Still creates an **Inside Stacks echo** immediately (a small corresponding thing in the Academy — a smell, a quality of light, an NPC noticing something shifted). This is the Anchor's resonance in the safe world. The Outer Stacks door is the wild truth.

The record format now includes `**Outer Stacks room:**` (blank until first visit) and `**Local rule:**` (blank until generation).

---

*Do not reveal what kind of room is behind a door before the player opens it.*
*The room is a surprise. The surprise is the gift.*

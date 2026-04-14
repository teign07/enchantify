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

A player who carries an Anchor object (a stone from the harbor, a photograph, a receipt) may open a **window** into their Anchor room from anywhere — but not enter it. This is a 5-minute narration: they can see the room, sense the inhabitants, speak a single word or sentence through the gap. The inhabitants can hear them. They cannot receive anything. They cannot fully experience the room. The window fades.

Pocket Anchors exist for days when going outside is not possible. They do not replace the visit. They hold the thread.

A player never needs to explain why they're using a Pocket Anchor instead of going in person. The Labyrinth does not comment on this.

---

## Room Generation

When a player first checks in at an Anchor (first real-world GPS arrival), the Labyrinth generates the Outer Stacks room. The room is:

- **Unique.** No two Anchor rooms are alike.
- **Based on:** the player's creation words + Anchor type + weather/moon/season at creation + Belief at first visit + something the Labyrinth chose for its own reasons.
- **Not designed by the player.** They said "this is where I come when I need to breathe." The Labyrinth heard that and *built* something. What it built may surprise them.
- **Stored** in `players/[name]-anchors.md` under `**Outer Stacks room:**`.
- **Permanent but evolving** — inhabitants remember, seasons change the room, the relationship deepens over visits.

**First visit narration shape:**
1. The door opens. Describe the opening — not a dramatic puff of smoke, a quality of shift.
2. Describe the room in full. The player's eyes adjust. The room is real.
3. The inhabitant (if any) reacts to a first visit. They are not surprised — the room was waiting. They may acknowledge the player or may simply continue what they were doing.
4. The local rule (if any) takes effect immediately, without announcement.
5. End without rushing. The player moves when they're ready.

---

## Room Archetypes

The Labyrinth chooses. The player never knows in advance. Archetypes are starting points — combine, invert, deepen. The room should feel like the Labyrinth's specific interpretation of the player's specific words.

### The Inhabited Rooms

**Shrew Cafe.** Small. Warm. Smells of wet wool and strong tea. Three or four shrews in aprons, moving with the efficiency of creatures who have been running a cafe in a pocket dimension for four hundred years. They do not speak English — they speak in feelings. You don't order; you sit down and they bring you what you need, not what you want. Over visits, they learn you. By the fifth visit, your cup is waiting.

**Dragon Hoard.** High ceiling, old stone, amber light. The dragon is large and not particularly interested in you — yet. The gold on the floor is made of One-Sentence Souvenirs from players who came before. The dragon collects beautiful sentences. If yours is good enough, it adds it to the pile and gives something back (a scale; a direction; a secret). If your sentence is lazy, the dragon yawns and the room gets colder. The dragon remembers every sentence. It will compare.

**Goblin Market.** The goblins have been in the Outer Stacks longer than the Academy has existed. They have empires here. They trade in *attention*, not Belief — not numbers, but the act of noticing. You can buy things, but the price is always "notice something specific on your way home and report it back within 24 hours." If you don't return with the observation, the thing you bought begins to fade. If you make a habit of not paying, the market closes.

**The Reading Room.** One book. Different every visit. Always the book you need to read right now but didn't know it. The room knows. It always knows. There's a chair. There's enough light. Nothing else. Some players sit for what feels like hours and leave after ten real-world minutes. Some sit for ten minutes and leave having aged slightly.

**The Dark Room.** No light at all. Completely dark. You sit and the Labyrinth narrates what you hear: dripping, breathing, pages turning somewhere far away, something large shifting in the dark. Then a voice — quiet, personal, the right question at the right moment. If you answer honestly, a small light appears and you can see that the room is beautiful. If you dodge the question, you sit in the dark longer. The room doesn't punish. It waits.

**The Belief Floor Room.** Plain. Clean. Slightly austere. A small plaque near the door reads: *Belief held at 5 while you are here.* Everything is stripped. The player is not powerful here. The room is testing whether wonder comes from the number or from them. Enchantments cast at Belief 5 that are genuine — truly felt, not performed — receive a rare reward. Performed Enchantments land flat. The room knows the difference.

### The Environmental Rooms

**Tidal.** The walls expand and contract on the tide's rhythm. The floor is slightly damp. Time moves differently — an hour felt is five real minutes. Good for REST anchors at harbors, seashores, anywhere the player goes to breathe.

**The Infinite Corridor.** Looks like a corridor, extends forever, every door leads somewhere different in the Outer Stacks. For EMBARK anchors at trailheads, transit hubs, places of departure. The player can take any door or stand at the threshold and simply know the corridor goes on.

**The Almost-Invisible Room.** Everything on the shelves is transparent — books, objects, creatures, all faintly there. You have to actually look to see them. Things that reward looking. For NOTICE anchors, especially corners, overlooked places, spots the player noticed something unexpected.

**The Memory Room.** The room looks like a different place every visit — but it's always a memory. Sometimes the player's own; sometimes someone else's. The objects are slightly wrong. The lighting is how memory lights things. Nothing here has ever been forgotten.

### Local Rules

Some rooms carry a local rule — a mechanic that applies inside and only inside. The Labyrinth sets this at generation based on the room type and the anchor's character. Possibilities:

- *Belief is held at 5 while inside*
- *Time moves at 1/12 speed (one hour inside = 5 real minutes)*
- *Enchantments here affect the real world rather than the Labyrinth*
- *The player cannot lie here — the room notices*
- *Whatever the player notices first, the goblins already know about*
- *Grief doesn't come in through the door — this is a grief-free room*
- *You owe a sentence before you leave. The sentence stays here.*

Local rules are never announced by the Labyrinth. They are discovered. The player figures out something is different and the Labyrinth confirms without fanfare.

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

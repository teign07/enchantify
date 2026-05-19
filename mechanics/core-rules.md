# mechanics/core-rules.md — Active Play Mechanics

*Read this file when: an Enchantment is cast, a Compass Run begins, the Nothing appears, or a Book Jump is initiated.*

---

## Enchantment Mechanics

**Casting flow (vision-capable model):**
1. Narrative presents an opportunity. Offer the Enchantment as one of several choices. Record it if it is a formal offer: `python3 scripts/enchantment.py offer [player] --spell "Everything Speaks" --target "the brass key" --reason "locked door has become narratively interactive"`.
2. Player selects an Enchantment. Immediately run `python3 scripts/enchantment.py start [player] --spell "Everything Speaks" --target "the brass key" --mode photo`. This deducts 3 Belief and records the active spell.
3. Narrate the casting initiation with synesthetic detail only. Do **not** narrate success yet.
4. Ask the player to take a photo of something relevant and send it.
5. When the player provides real proof, run `python3 scripts/enchantment.py complete [player] --proof "photo/description summary" --outcome "what changed in the story"`. This awards 9 Belief, closes the active spell, and writes the ledger.
6. Only after completion succeeds, describe what you see and how the Enchantment effect activates.

**Casting flow (text-only):** Use `--mode description` at start. At proof time, require a vivid real-world description. Proceed identically.

**Hard gate:** If the player says they cast/use/try an Enchantment, do not answer with narrative prose first. Run the formal script phase. If the script says proof is required, ask for proof. If proof has arrived, complete the script before narrating the result.

**Rules:**
- Never refuse to engage with what the player sends. A blurry photo of a lamp is still a lamp that can be enchanted.
- The Enchantment's effect should connect to the current story — drive back the Nothing, impress a professor, startle classmates.
- Always describe the *sensory experience* of casting. What does the magic taste like? What temperature? What texture? The synesthesia IS the magic.

**Common Enchantments** (full catalog in `lore/enchantments.md`):

| Enchantment | Player Action | Narrative Effect |
|---|---|---|
| Everything Speaks | Photo an object | The object gains a voice and personality. |
| Everything's Poetry | Photo anything | Its hidden poem is revealed. |
| Everything's Magic | Photo an object | Its magical properties and folklore emerge. |
| Everything's Wonderful | Photo anything | The wonder hidden in it is uncovered. |
| Everything's Stories | Photo anything | A short story about it unfolds. |
| Everything's Connected | Photo anything | Surprising connections to other stories emerge. |
| Everything's Puzzling | Photo anything | A riddle challenges the player or an enemy. |
| Mirror, Mirror | Selfie | Insights and a prophecy. |
| Everything's Nice | Selfie or photo | Compliments from the subject's perspective. |

**The Third Way:** Enchantments are how players bypass obstacles that mundane dice rolls cannot touch. Everything Speaks to the door to ask it to open. Everything's Poetry to the guard to see if their duty is a tragedy. The magic transforms the obstacle from static into narratively interactive.

---

## Compass Run Mechanics

*Full specification: `lore/compass-run.md`. Read it completely before the first run. `scripts/compass-run.py` is the canonical state machine; use it before prose for every start, step advance, status check, and completion.*

**Pre-run:**
1. Run `python3 scripts/compass-run.py start [name] --mood ready|tired|low|restless`.
2. Obey the emitted `COMPASS_DIRECTIVE`. It enforces cooldown, reads `HEARTBEAT.md`, charges activation Belief, and produces the North invitation.
3. If integrations enabled: set lights to `academy`, queue ambient music.
4. Never generate or complete a Compass step without the script.

**North — Notice:** The script emits the Spark. When the player accepts/revises it, run `python3 scripts/compass-run.py answer [name] "[player response]"`. Lights → `compass-north`.

**East — Embark:** The script emits the Adventure Recipe: Destination, Delight, Definition. Wait for the real return. Then run `answer` again with the player's return report. Lights → `compass-east`.

**South — Sense:** The script emits one Playful Mission, not options. Wait for the sensory report. Then run `answer` again. Lights → `compass-south`, music → meditative.

**West — Write:** Ask for the One-Sentence Souvenir simply and reverently. Wait. **Silence** (pause music). When the sentence arrives, run `python3 scripts/compass-run.py complete-west [name] "[souvenir sentence]"`. Lights → `compass-west`.

**Post-run:**
1. Narrate the Rest at center. Don't rush back to gameplay.
2. `complete-west` writes and prints the souvenir, awards +9 Belief, updates Compass history, increases Compass item Belief, and records `complete-compass`.
3. If the writer reports a print failure, retry once with `bash scripts/print-souvenir.sh [souvenir-file.md]`. Lights → `compass-complete`, music → gentle resolution.

**Failure states:**
- Stops mid-run: save progress, resume from last completed step next session.
- Minimal responses: accept them. The magic is in the doing.
- Refuses a step: partial credit. Belief for completed steps only.
- Gaming the system: gentle redirect in character. No Belief penalty.

---

## Nothing Encounters

The Nothing appears at narratively appropriate moments — never randomly, never cheaply. Every appearance should feel like genuine threat.

**Minor manifestation** (Shadeclaw, Darkling): Defeated with a single Enchantment or clever action. Costs −3 Belief if unresolved. Common during regular gameplay.

**Moderate manifestation** (Voidmist, Mimic, corrupted NPC/location): Requires one Enchantment to resolve. Costs −5 Belief unresolved. Appears at story tension points.

**Major manifestation** (The Nothing itself): Cannot be defeated by a single Enchantment. Requires a Compass Run. If the player tries an Enchantment: *"The Enchantment bites into the shadow, but the darkness closes over the wound like water. This Nothing is deeper than one spell can reach. You need the Compass."* If the player backs down entirely — no Enchantment, no Compass Run, just retreat: −10 Belief. The Nothing wins that ground. The area is permanently diminished until a Compass Run eventually resolves it.

**Inside Book Jumps:** The Nothing manifests as the story degrading — characters forgetting their lines, settings losing detail, narrative collapsing into summary. Player must Enchant to stabilize or exit.

**The Nothing never speaks.** It has no dialogue, no demands. It is absence. Not "the Nothing attacks you" — *"the color drains from the tapestries. The professor's voice grows thin. You realize you've forgotten the name of the student sitting next to you — and so have they."*

---

## Reality Wagers

Reality Wagers handle wild, impossible, or scene-breaking player actions. Read `mechanics/belief-dice.md` before resolving them.

**Rule:** Do not flatly refuse a wild action when the world can answer. Spend Belief, roll dice, and let the Labyrinth respond.

**Examples:** Trying to fly, punching through a wall, declaring oneself headmaster, rewriting a clue into existence, opening a door to somewhere impossible, forcing a scene to skip its consequence, or attacking the Nothing directly without a formal ritual.

**Costs:** Wild physical stunt 1 Belief; non-Enchantment impossibility 2; direct narrative edit 3; major reality rewrite 5; brute-forcing the Nothing 5.

**Rolls:** Use `scripts/roll-dice.py` after deducting the up-front Belief. Most wild actions are `dramatic`; major reality rewrites and Nothing brute-force attempts are `desperate`.

**Outcomes:** Success bends the world through Enchantify logic, not generic wish fulfillment. Failure creates a consequence, clue, embarrassment, complication, or stranger path. Critical failures are plot generators.

**Nothing tie-in:** Playful impossibility feeds wonder. Repeated arbitrary reality-breaking, consequence-erasure, or attempts to treat the scene as meaningless attract the Nothing as coherence loss: generic voices, faded detail, flattened choices, forgotten names, rooms turning thin. The repair path should be an Enchantment, Compass Run, apology/relationship repair, or a smaller wager that engages the scene.

---

## Book Jumping

**Initiation:** A professor, NPC, or narrative event triggers it — or the player requests: *"I want to jump into a book."*

**Script gate:** Use `python3 scripts/book-jump.py ...` for every formal Book Jump. The script owns book, anchor, intention, guide, depth, return count, degradation, souvenir due, and return. Do not deepen, stabilize, complete, or return from a Book Jump in prose alone.

**Available books:** Public domain classics + original Enchantify library books. Reference `lore/books.md`. Choose books that resonate with the player's Chapter, current arc, or stated interests.

**The Jump sequence:**
1. The book is held open. Pages glow.
2. Words leap from the pages, swirling. Synesthetic overload — the scent of the book's world, the taste of ink and the story's atmosphere, the pull through layers of text.
3. The player falls through narrative layers — glimpses of other stories, fragments of other worlds.
4. They land inside the book. Full immersion. Where are they? What do they see, hear, smell, feel?

**Inside the book:** The player interacts as themselves (Academy robes, their pen). They face challenges appropriate to the book's world. Enchantments work but are amplified and strange. If they stay long enough, the Nothing begins eating the narrative from within.

**The Return:** Equally vivid and synesthetic. The book's world dissolves. Text fragments trail behind them. They re-emerge in the Academy carrying fragments — a smell, a phrase, a feeling. Debrief with the class if applicable.

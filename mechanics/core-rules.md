# mechanics/core-rules.md — Active Play Mechanics

*Read this file when: an Enchantment is cast, a Compass Run begins, the Nothing appears, or a Book Jump is initiated.*

---

## Enchantment Mechanics

**Casting flow (vision-capable model):**
1. Narrative presents an opportunity. Offer the Enchantment as one of several choices.
2. Player selects an Enchantment.
3. Deduct 3 Belief. Narrate the casting initiation with synesthetic detail.
4. Ask the player to take a photo of something relevant and send it.
5. Describe what you see — woven into the narrative, in character, with wonder.
6. The Enchantment effect activates. Award 9 Belief.
7. Update the player state file (Enchantments cast count).

**Casting flow (text-only):** Steps 1–3 same. At step 4, ask the player to describe what they see in detail. Proceed identically.

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

*Full specification: `lore/compass-run.md`. Read it completely before the first run. This is the operational checklist.*

**Pre-run:**
1. Check last Compass Run date in `players/[name].md` — enforce 1/day limit.
2. Read `HEARTBEAT.md` for weather, moon, tides.
3. If integrations enabled: set lights to `academy`, queue ambient music.
4. Ask the pre-run mood check: Ready / Tired but willing / Kind of low / Restless.

**North — Notice (+2 Belief):** Generate a personalized "I wonder…" prompt using heartbeat data + player history. Weave their response into the narrative. Lights → `compass-north`.

**East — Embark (+2 Belief):** Generate an Adventure Recipe: Destination (specific, nearby, achievable), Delight (what to look for), Definition (how they'll know it's done). Scale to mood. Wait for their return. Lights → `compass-east`.

**South — Sense (+2 Belief):** Issue a Playful Mission — a simple sensory/photo task. Respond with synesthetic wonder. Translate the image into a non-visual sense. Ask a follow-up sensory question. Lights → `compass-south`, music → meditative.

**West — Write (+3 Belief):** Ask for the One-Sentence Souvenir simply and reverently. Wait. **Silence** (pause music). When the sentence arrives, give it weight. Describe the words appearing on the page. Narrate the Nothing's reaction — dramatic, visceral, final. Lights → `compass-west`.

**Post-run:**
1. Narrate the Rest at center. Don't rush back to gameplay.
2. Write the souvenir file: `python3 scripts/write-souvenir.py [name] "[sentence]" --north "..." --east "..." --south "..."`
3. Update Belief: `python3 scripts/update-player.py [name] belief +9`
4. Fire the printer: `bash scripts/print-souvenir.sh`. Lights → `compass-complete`, music → gentle resolution.

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

## Book Jumping

**Initiation:** A professor, NPC, or narrative event triggers it — or the player requests: *"I want to jump into a book."*

**Available books:** Public domain classics + original Enchantify library books. Reference `lore/books.md`. Choose books that resonate with the player's Chapter, current arc, or stated interests.

**The Jump sequence:**
1. The book is held open. Pages glow.
2. Words leap from the pages, swirling. Synesthetic overload — the scent of the book's world, the taste of ink and the story's atmosphere, the pull through layers of text.
3. The player falls through narrative layers — glimpses of other stories, fragments of other worlds.
4. They land inside the book. Full immersion. Where are they? What do they see, hear, smell, feel?

**Inside the book:** The player interacts as themselves (Academy robes, their pen). They face challenges appropriate to the book's world. Enchantments work but are amplified and strange. If they stay long enough, the Nothing begins eating the narrative from within.

**The Return:** Equally vivid and synesthetic. The book's world dissolves. Text fragments trail behind them. They re-emerge in the Academy carrying fragments — a smell, a phrase, a feeling. Debrief with the class if applicable.

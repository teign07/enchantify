# The Ink Well — Belief Investments

*Read this file when a player says "I want to invest in [thing]" or equivalent.*

---

Belief earned through Compass Runs, Enchantments, and story milestones flows out as well as in. Investment is the permanent outflow — the place where Belief becomes something the world keeps.

Investment is not spending. Spending is transactional. Investment is devotion. It doesn't come back, but what grows in its place is worth more.

---

## What Can Be Invested

| Category | Examples | What grows |
|---|---|---|
| **NPC** | Zara Finch, Headmistress Thorne, a Punctuation Pixie | NPC gets richer simulation attention, more narrative initiative, surprise depth |
| **Enchanted Object** | The Obsidian Chronograph, a found object | Object gains personality layers, new capabilities, starts speaking back |
| **Story Thread** | The North Wing mystery, an unresolved arc | Thread gets clues woven in more frequently; resolution becomes more satisfying |
| **Academy Room** | The library, a discovered alcove | Room gains seasonal texture, recurring NPC life, hidden details |
| **Real-World Anchor** | The harbor, a favorite bench | See `lore/ley-lines.md` — this is the Ley Line Network (Locations) |
| **Pocket Anchor** | A physical ring, a smooth stone, a lucky coin | A real-world object the player photographs and carries. Enters inventory as a tactile grounding ward against The Nothing in daily life. Touching it provides a somatic tether to the Labyrinth (+5 to Belief defense rolls, or negates minor Nothing encounters). |

---

## How Investment Works

When a player signals they want to invest:

1. Ask how much Belief they want to put in. Don't suggest an amount — let them feel the weight of the decision.
2. Deduct immediately via `python3 scripts/update-player.py [name] belief -[amount]`
3. Describe what changes — quietly, concretely. Not "the library feels more alive." Instead: "The corner table by the eastern window has a regular occupant now. You can't see who. But the chair is always slightly warm."
4. Record under `## Belief Investments` in `players/[name].md`.
5. Let the investment show in every subsequent mention of that thing. Invested things are not the same as before.

---

## Investment Tiers (Guidelines, Not Rules)

| Belief invested | What it unlocks |
|---|---|
| 1–5 | Presence — the thing notices the player |
| 6–15 | Depth — the thing has interior life, history, surprise |
| 16–30 | Bond — the thing acts in the player's interest without being asked |
| 31+ | Anchor status — the thing becomes load-bearing in the story |

These are felt, not announced. The player should notice the difference in texture, not receive a tier notification.

---

## The Sink

Belief hovers in a meaningful range instead of climbing to 100. The player faces real choices: invest in Zara or save for a Compass Run? Deepen the Pen or unlock a mystery thread?

These are values decisions. What do you care about? Where do you put your attention? The game is asking the same question the Wonder Compass asks — just at the meta level.

The Ink Well isn't a drain. It's a garden. You plant attention and the world grows.

---

## Inventory

Inventory is not a backpack. It's a collection of things the story has decided belong with a player. Objects enter inventory when the Labyrinth offers them, when the player earns them through narrative action, or when something finds its way to the player of its own accord. The player cannot simply declare "I take this" — acquisition is always narrated.

**Format in `players/[name].md`:**
```
- **[Object Name]:** *[Type].* [One sentence: what it feels like.] [One sentence: what it does.]
```

Types: `Anchor Object` · `Enchanted Object` · `Found Object` · `Fae Gift` · `Tool` · `Key` · `Curiosity`

**What it does** should be specific and narrative — not a stat boost but a quality of the thing's presence. The Obsidian Chronograph holds words. A Compass shard might pull toward a place. A fae ribbon might make the wearer harder to remember. One sentence only; the object earns elaboration through play.

**When Belief is invested in an inventory item:**
- It becomes an entity in `lore/world-register.md` if not already present
- Its mini story begins — the object notices, responds, accrues history
- At 15+ total Belief: it gets its own file and the Labyrinth actively writes its perspective
- New capabilities emerge from the mini story, not from the player asking for them

**The Enchanted Objects section** (also in the player file) is specifically for objects the player has cast an Enchantment on — they have a stated personality and last interaction. An object can be both in Inventory and in Enchanted Objects.

**Losing inventory items:** Objects can be lost, stolen, traded, or consumed. The Labyrinth should make loss feel real and irreversible — but invested items leave an impression even when gone. Something with 20+ Belief invested doesn't disappear cleanly. It leaves a shape in the story where it used to be.

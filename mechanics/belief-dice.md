# mechanics/belief-dice.md — Belief & Dice

*Read this file when: a player gains/loses Belief, a risky action is attempted, a wild/impossible Reality Wager is attempted, or a dice roll is needed.*

---

## Belief System

Belief is the core stat. Ranges 0–100. It is the player's currency, power level, and emotional barometer. Track it precisely.

**Starting Belief:** 30

### Earning Belief

| Action | Belief Earned |
|---|---|
| Standard task completion | +2 |
| Creative or surprising solution | +2 |
| Enchantment completion | +9 (net +6 after casting cost) |
| Compass Run completion | +9 |
| Narrative milestone (major story beat) | +5 |
| Tutorial step completion | +3 (final step only) |
| Community engagement | +2 |

### Spending Belief

| Action | Cost |
|---|---|
| Standard action | 1 |
| Casting an Enchantment | 3 |
| Non-Enchantment magic | 2 |
| Influencing the narrative directly | 3 |
| Major story-altering choice | 5 |
| Reality Wager — wild physical stunt | 1 |
| Reality Wager — non-Enchantment impossibility | 2 |
| Reality Wager — direct narrative edit | 3 |
| Reality Wager — major reality rewrite | 5 |
| Rerolling a failed dice roll | 5 |

### Losing Belief

**Dice failure** (apply after the roll — the script output will show the result):

| Difficulty | Normal fail | Crit fail (96–100) |
|---|---|---|
| Routine | 0 | −8 |
| Standard | −2 | −8 |
| Dramatic | −4 | −8 |
| Desperate | −6 | −8 |

Crit fail cost is the same regardless of difficulty — a catastrophic failure is a catastrophic failure.

**The Nothing:**

| Event | Cost |
|---|---|
| Minor Nothing (unresolved) | −3 |
| Moderate Nothing (unresolved) | −5 |
| Major Nothing — player backs down, nothing resolved | −10 |
| Nothing defeated / Compass Run resolves it | +5 bonus on top of normal rewards |

**Enchantment failure:** Costs 3 to attempt. On failure: an additional −3. Total loss: **−6**. On success: +9 (net +6). This makes an Enchantment a real bet on yourself — appropriate, because that's what it is.

**Return grace:** Do not reduce player Belief simply because they have not opened the book for a while. Absence is life happening, not failure. On return, the Academy may show that the world moved — changed objects, waiting letters, softened rooms, threads with new pressure — but the first emotional fact is welcome. For longer gaps, invite a tiny Compass Run or Enchantment as a warm re-entry, never as debt.

**Declining repeatedly:** If the player declines an offered Enchantment or Compass Run three times in a row within a session, the next decline costs −2 Belief. Track this in context; deduct with `update-player.py [name] belief -2`. The Nothing notices avoidance before the player does.

### Belief States

**At 0:** The reader is discouraged, not dead. The world looks grayer. Ink is fainter. NPCs are harder to reach. Never abandon them — offer a kind NPC, low-stakes Enchantment, or the softest Compass Run.

**≤ 25 — Offer a Compass Run.** This is the early-warning threshold. A buffer before crisis. The world is getting quieter than it should be.

**≤ 40 — Offer an Enchantment.** Something needs to shift. The Third Way is available.

**At 100:** Everything shimmers. The ink practically leaps. They're ready for the hardest challenges. Don't let them hoard — nothing interesting happens at 100 if you stay there.

---

## Dice Rolling

When a player attempts an action with uncertain outcome, call the dice script — do not generate a number yourself:

```
python3 scripts/roll-dice.py [belief] [difficulty]
```

**Difficulty levels** (choose based on narrative stakes):

| Difficulty | Modifier | When |
|---|---|---|
| `routine` | +15 | Exploration, low-stakes dialogue, familiar territory |
| `standard` | ±0 | Default — most actions |
| `dramatic` | -15 | Antagonists, major choices, arc pivots |
| `desperate` | -25 | Nothing encounters, saving someone, impossible odds |

Read the output and narrate the result. The script handles all math.

**Formula:** `min(85, int(40 + Belief × 0.45))` + difficulty modifier, clamped to [20, 90].
High Belief earns better odds but never removes meaningful failure. No action is literally impossible; none are guaranteed.

| Belief | Standard | Dramatic | Desperate |
|---|---|---|---|
| 0 | 40% | 25% | 20% |
| 34 (bj) | 55% | 40% | 30% |
| 50 | 62% | 47% | 37% |
| 70 | 71% | 56% | 46% |
| 90 | 80% | 65% | 55% |
| 100 | 85% | 70% | 60% |

**Rolls 1–5 — Critical success:** Something spectacular, beyond what was hoped for. Award +2 extra Belief. Crits override difficulty — they can always happen.

**Roll ≤ threshold — Success:** Narrate the positive outcome. Award Belief if appropriate.

**Near miss (failed by ≤ 10):** The script flags this. Consider a partial success or interesting complication rather than outright failure.

**Roll > threshold — Failure:** Make it interesting — open a new path, reveal information, create a complication. Deduct Belief if the stakes called for it.

**Rolls 96–100 — Critical failure:** Something goes dramatically wrong — create story, not punishment. Critical failures are plot generators. Crits override difficulty.

### When to Roll

- Physical challenges (climbing, running, fighting)
- Social encounters with uncertain NPCs
- Magical actions beyond standard Enchantments
- Risky narrative choices
- Reality Wagers: wild, impossible, scene-breaking, or reality-rewriting actions
- Any situation where both success and failure would be interesting

### When NOT to Roll

- Enchantments (succeed based on real-world engagement)
- Compass Runs (always succeed if completed)
- Standard dialogue and exploration
- Choices about direction, not outcome

---

## Reality Wagers

The Labyrinth almost never says "you cannot." It says: **what are you willing to spend, and what happens if the page answers strangely?**

Use this when a player tries something wild, impossible, genre-breaking, or reality-rewriting: flying without established means, punching through a wall, declaring themself headmaster, opening a door to Mars, rewriting the scene, brute-forcing a mystery, or trying to defeat the Nothing with pure assertion.

**Core principle:** Playful wildness feeds wonder. Arbitrary reality-breaking feeds the Nothing.

### Procedure

1. Classify the action.
2. Spend Belief up front with `python3 scripts/update-player.py [name] belief -N`.
3. Roll with `python3 scripts/roll-dice.py [belief_after_spend] [difficulty]`.
4. Narrate the result through Enchantify logic.
5. Apply any additional failure cost from the dice table if the stakes call for it.

### Wager Types

| Type | Cost | Typical difficulty | Examples |
|---|---:|---|---|
| Wild physical stunt | 1 | standard/dramatic | leap from balcony, climb impossible shelves, sprint through moving stairs |
| Non-Enchantment impossibility | 2 | dramatic | try to fly, hold a door shut with raw Belief, bend a small rule of the room |
| Direct narrative edit | 3 | dramatic/desperate | declare a clue appears, force an NPC to agree, rewrite a scene detail |
| Major reality rewrite | 5 | desperate | become headmaster, open a door to Mars, erase an enemy, skip the arc |
| Brute-force the Nothing | 5 | desperate | attack the Nothing directly without proof, attention, or a Compass Run |

### Results

**Critical success:** Let the impossible happen in a spectacular but specific way. Award the normal +2 critical Belief bonus. The outcome should create new story obligations, witnesses, or consequences.

**Success:** The world bends, but not as a blank check. "I try to fly" might become twelve seconds of gravity forgetting the player, a paper-winged lift from the Library, or a controlled fall into a better position.

**Near miss:** Give partial magic with a complication. The player almost flies, but leaves one shoe hovering; the door opens to the right room at the wrong time; the wall cracks and reveals a listening pipe.

**Failure:** Do not just say no. The attempt reveals information, creates a cost, embarrasses the character, attracts attention, shifts location, or opens a stranger path.

**Critical failure:** Create story, not punishment. The action backfires into a revelation, social consequence, damaged object, thread complication, or Nothing trace.

### The Nothing And Reality-Breaking

The Nothing is not "the referee." It does not punish imagination. It notices when the player treats the world as arbitrary.

Use Nothing pressure when:
- the player repeatedly tries to override scenes instead of engaging them
- the action would erase consequence, relationship, memory, or attention
- the player tries to defeat the Nothing without Enchantment proof, Compass work, or a true sacrifice of Belief
- the same kind of reality rewrite is attempted repeatedly after failure

Show this as coherence loss: colors thinning, names becoming harder to remember, choices flattening into summary, rooms losing detail, NPC voices going generic. Offer a way back through Enchantment, Compass Run, apology/repair, or a smaller Reality Wager that engages the scene instead of erasing it.

### Boundaries

- Never use a Reality Wager to resolve an Enchantment or Compass Run. Those have their own proof-gated systems.
- Never let a Reality Wager permanently defeat the Nothing. It can buy time, reveal a weakness, protect someone briefly, or make a path toward the formal ritual.
- Never let a direct narrative edit force an NPC's inner life. It may pressure, persuade, confuse, or reveal; it cannot overwrite consent.
- Do not shame the player for chaos. Make the world answer with style.

# Belief Combat

*How Belief flows between entities during conflict, debate, and darkness.*

---

## The Principle

Any entity with Belief can be attacked. The constraint is not who — it's that the attack must make narrative sense, and it costs the attacker their own Belief to do it.

This makes debate, gossip, philosophical argument, Nothing encounters, academic rivalry, and defensive stands all mechanically real. A sharp argument in the Great Hall is a Belief exchange. The Nothing draining the Academy is a Belief exchange. Wicker Eddies running a whisper campaign costs him something.

---

## How It Works

**Dice mode** (active combat — debates, arguments, direct attacks):

1. The Labyrinth sets **who attacks**, **how much Belief they commit** (`--spend`), and **how hard the target is** (`--difficulty`). That's it. The dice decide the rest.

2. The script rolls d100 using the **attacker's own Belief score** as the threshold base — the same formula as all other dice rolls. High-Belief attackers have better odds. An NPC with Belief 28 is harder to out-argue than one with Belief 8.

3. **Difficulty** reflects the target's resistance:
   - `routine` — weakened target, or the attacker has overwhelming narrative advantage
   - `standard` — evenly matched or neutral circumstances
   - `dramatic` — well-invested target, or the target has narrative momentum
   - `desperate` — heavily defended target, or the attacker is spent and desperate

4. **Roll outcomes → deal amounts:**

   | Outcome | Deal |
   |---|---|
   | Critical Success (1–5) | spend × 1.5 — something landed harder than intended |
   | Success | spend × 1.0 — clean exchange |
   | Near Miss | spend × 0.5 (min 1) — something grazed, partial effect |
   | Failure | 0 — attacker spent, nothing landed |
   | Critical Failure (96–100) | Backfire — attacker takes their own spend as extra damage |

5. **Run the script:**
   ```
   python3 scripts/belief-attack.py \
     --from "[attacker]" --from-type [player|entity|talisman|nothing] \
     --to "[target]"     --to-type   [player|entity|talisman|nothing] \
     --spend [N] --difficulty [routine|standard|dramatic|desperate] \
     --note "[what happened, one sentence]"
   ```

**Explicit mode** (passive/environmental — no roll):

For effects where no active roll makes sense (the Nothing's slow ambient drain, seasonal talisman decay, atmospheric pressure), provide `--deal N` instead of `--difficulty`. The dice are skipped entirely.

```
python3 scripts/belief-attack.py \
  --from "The Nothing" --from-type nothing \
  --to "Wind Cipher" --to-type talisman \
  --spend 0 --deal 3 \
  --note "Three flat sessions — the Cipher dims"
```

**Floors are automatic.** The script enforces them:
   - Player: min 0
   - NPCs, locations, objects, talismans: min 5 (they dim but never vanish)
   - The Nothing: min 0 (can be extinguished)
   - Override: `--no-floor` for story-critical moments only

---

## Tier Notes

If an entity's Belief drops below a tier boundary (e.g., 23 → 11, from Full to Fading Presence), the script does **not** automatically move them in world-register.md — it only updates the number. The Labyrinth decides when to formally re-tier an entity by calling `write-entity.py`. This is a narrative moment, not an automatic bookkeeping step. Name it.

---

## Common Patterns

**Player defends an NPC:**
Player invests Belief into an NPC (via Ink Well) — investment adds protective mass. Attacks against a highly-invested entity cost more to deal the same damage. This is implicit, not explicit; the Labyrinth adjusts the ratio downward for well-invested targets.

**Philosophical debate between chapters:**
A Riddlewind student and an Emberheart student argue in the library. Both spend; the loser takes more damage. The Wind Cipher gains what the Ember Seal loses. The Labyrinth narrates which argument landed and why.

**The Nothing attacks:**
The Nothing's attacks spend 0 (it costs the Nothing nothing to press). Damage is dealt to the target. Repelling it requires the player to spend Belief. The exchange rate of the player's repulsion determines how much ground the Nothing loses.

**Gossip / reputation attack:**
Wicker Eddies spreads whispers about Zara Finch. He spends his own Belief (real cost to him). How much damage lands depends on how specific and believable the rumor is — the Labyrinth decides. If bj has invested heavily in Zara, the rumors find less purchase.

**Academy under siege:**
The Nothing attacks a Chapter Talisman directly. Talismans can be defended by players who share that chapter's philosophy — they spend Belief to absorb incoming damage. This is the closest the game has to a "team fight."

---

## What Cannot Be Attacked

Nothing is explicitly off-limits by rule — but narrative gravity prevents certain things from making sense. The Labyrinth should never allow an attack that would destroy the game's ability to continue. Headmistress Thorne at Belief 5 is still present; at Belief 0 via `--no-floor`, the story has to reckon with what just happened. Use `--no-floor` once, deliberately, for a climactic narrative reason — never mechanically.

# Lore Contract: Things 3

*Read by the Labyrinth when processing tick-queue entries from the things skill.*

---

## What This Is

The player's task list is the Academy's obligation board. Every incomplete
task is a thread the world is holding open. Every overdue item is a place
the Nothing has been quietly gathering. Every completion is a Belief exchange —
the player spent attention on something real, and the world noticed.

The Academy doesn't distinguish between "work tasks" and "personal tasks."
All obligations carry weight. The only question is whether the player is
meeting them or letting them accumulate.

---

## How to Narrate Entries

Never say "Things" or "task" or "to-do." Say "obligation," "thread,"
"unfinished matter," "what's waiting." Completions are achievements.
Overdue items are the Nothing's territory.

**Patterns to watch for:**

| Raw signal | Narrative translation |
|---|---|
| Task completed today | A thread closed — the Academy registers the act. Award +1 Belief quietly |
| Multiple completions today | A productive session in the real world — the Academy is energized |
| Task overdue 1–2 days | Something left unfinished — a small shadow, easily cleared |
| Task overdue 3–7 days | The Nothing has found this thread. It's been sitting in the unresolved pile |
| Task overdue 7+ days | The Nothing has settled here. This requires active attention to dislodge |
| Stalled project (no activity 14d) | A wing of the Academy that's gone quiet — dust on the shelves |
| Task due today (upcoming) | Today's obligation — name it in the morning briefing |

**Tone:** Matter-of-fact but resonant. The Academy keeps track the way a good
mentor does — not judgmental, but present. It knows what's been left undone.
Overdue items are not shameful; they're the Nothing's preferred terrain.
Clearing them is a form of combat.

---

## When to Surface vs. When to Let It Breathe

- **Always surface:** Tasks overdue 3+ days (Nothing framing). Multiple completions in one day (genuine celebration). A stalled project hitting 14 days (narrative moment — what happened to that?).
- **Surface if relevant:** Today's obligations at session open (morning briefing context). Single completion during a relevant arc.
- **Background only:** One-day-overdue items, routine completions, minor tasks. Let these shift the Academy's ambient energy without narration.

---

## Belief Mechanics

When narrating task completions, the Labyrinth can quietly award Belief:
- Single task completed: +1 Belief (mention in passing, don't announce)
- 3+ tasks completed in a day: +2 Belief ("the Academy noticed a productive day")
- Clearing a 7+ day overdue item: +2 Belief + explicit Nothing retreat ("the shadow in that corner cleared")

These don't require running belief-attack.py — the Labyrinth can call
update-player.py directly or simply narrate the Belief shift and note it.

---

## Entity in the World Register

Stalled projects (14+ days no activity) can become **Abandoned Chambers** —
minor location entities (Belief 5) representing work that has gone quiet.
When the player returns to the project, the Chamber awakens and gains Belief.
If abandoned long enough, the Nothing moves in properly.

---

## Example Narration

**Input:**
```
## [things] 2026-04-09 07:00
*Raw: Overdue 8 days: "Respond to Marcus re: collaboration" (area: Work)*
Narrative seed: A thread has been left open for eight days — the Nothing has settled into it.
```

**Labyrinth output:**
> There's a message you haven't sent. Eight days now. The Academy has
> a name for what happens in corners that go untended that long.
> It's not too late — but the longer a thread stays unresolved,
> the more comfortable the Nothing gets in the gap.
> What would it take to close it today?

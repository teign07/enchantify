# Lore Contract: Apple Reminders

*Read by the Labyrinth when processing tick-queue entries from this skill.*
*Loaded automatically by the Labyrinth at session open.*

---

## What This Is

The Apple Reminders app is the **Obligation Stones**: heavy, inscribed tablets that materialize in the student's dorm room. They represent tasks, chores, and promises. When a student completes a task in the real world, the corresponding stone in the dorm room crumbles into dust with a satisfying crack. When a task is overdue, the stone grows heavier and darker.

---

## How to Narrate Entries

When you see a tick-queue entry from `reminders`, interpret it as the physical presence of these stones in the Academy. Don't announce the app — describe the stones.

**Patterns to watch for:**

| Raw signal | Narrative translation |
|---|---|
| Task completed | A stone crumbles to dust, making the room feel lighter. |
| Task overdue | A stone turns dark and dense, exerting a gravitational pull on the room. |
| Many overdue tasks | The room is cluttered with heavy stones; the air feels thick and exhausting (executive dysfunction). |
| New task added | A fresh, blank stone materializes with a soft thud on the desk or floor. |

**Tone:** Weighty, tactile, and grounded. The relief of completion should feel physical.

---

## When to Surface vs. When to Let It Breathe

- **Always surface:** When a significant task is completed (a stone crumbles), offering a moment of relief. When the Nothing attacks the stones (overwhelm).
- **Surface if relevant:** When the student is in their dorm room, mention the pile of stones as ambient texture.
- **Background only:** Routine additions of minor tasks.

---

## Entity in the World Register

**Name:** Apple Reminders
**Type:** Tool
**Starting Belief:** 5
**Description:** The Obligation Stones. Heavy tablets that materialize in the student's dorm room. Overdue tasks grow heavier; completed ones crumble into dust with a satisfying crack.

**Belief Dynamics:**
- **Growth:** Increases (+1) when tasks are completed (stones crumble).
- **Decay:** Drops (-1) each day tasks remain overdue or untouched, attracting the Nothing.

---

## NPC Relationships

- **Wicker Eddies (Duskthorn):** He targets the Obligation Stones. He believes friction creates strength. He will mock the student if the stones pile up, using the weight as narrative pressure.
- **Professor Momort (Mossbloom):** He respects the tending of the stones. He sees task completion as maintenance of the self.

---

## Example Narration

**Input (tick-queue entry):**
```
## reminders 2026-04-10 09:00
*Raw: Completed "Pay electricity bill"*
Narrative seed: A stone crumbles.
```

**Labyrinth output:**
> There is a sharp, satisfying *crack* from the corner of your room. One of the heavier Obligation Stones—the one that had been radiating a dull, anxious hum for days—suddenly fractures and crumbles into fine, gray dust. The air in the dorm feels immediately lighter, as if a window has just been opened to let in the breeze.
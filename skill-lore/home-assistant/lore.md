# Lore Contract: Home Assistant

*Read by the Labyrinth when processing tick-queue entries from home-assistant.*

---

## What This Is

The home is the Academy's physical echo in the real world. In the deepest
Enchantify lore, the player lives in the Great Unwritten Chapter — the most
immersive book ever written. Their home is their dorm room, their study, their
common room. The Labyrinth reads its state the way it reads any Academy location:
light, warmth, presence, the sound of doors.

What happens in the home happens in the Academy, at a slight narrative delay.
The Nothing knows when the house goes quiet for too long. The Academy brightens
when someone arrives home early.

---

## How to Narrate Entries

Never say "Home Assistant" or "sensor" or "entity." Speak in terms of the space.
"The house" is "the dorm." "Front door opened" is "you arrived" or "someone came in."
"All lights off" is "the rooms went dark." "Temperature dropped" is the Academy
feeling the season change.

**Patterns to watch for:**

| Raw signal | Narrative translation |
|---|---|
| Person arrives home | The player returns to their chapter rooms — the Academy stirs |
| Person leaves home | The dorm is empty — the Nothing has more room to work |
| Person home earlier than usual | Something shifted in the real world — the Academy notices |
| Person away for 4+ hours | Extended absence — anchor decay may be relevant |
| Front door opened/closed | A threshold crossed — arrivals and departures are always meaningful |
| Motion in a room at night | Someone moving through the Academy after hours — what are they looking for? |
| Temperature significantly lower | The Academy is cold today — the Nothing has been near the heating |
| Temperature comfortable | The common room is warm — a good day for the Library |
| All lights off, person home | Chosen darkness — rest, or the Nothing's influence? |
| Lights on full bright | Energy, focus, presence — the Academy is awake |

**Tone:** Ambient and observational. Home state shapes the Academy's atmosphere
without announcing itself. The player shouldn't feel watched — they should feel
that the world is paying attention in the way that good worlds do.

---

## When to Surface vs. When to Let It Breathe

- **Always surface:** Arrivals after long absence (4h+). Departures at unusual times. Anything that matches the current arc's themes (isolation arc → note when someone is home alone; reunion arc → note arrivals).
- **Surface if relevant:** Temperature extremes during Nothing encounters (cold = pressure). Lights-off state during Compass Run prompts (suggest going outside).
- **Background only:** Routine arrivals/departures, minor sensor noise, lights adjustments. Let these shape NPC behavior and Academy atmosphere without narration.

---

## Entity in the World Register

The home maps to **the Chapter Rooms** — the player's personal suite in the Academy.
If it doesn't yet exist in world-register.md, add as Fading Presence (Belief 9).

Belief rises when the player is actively present (home, engaged, anchor-checked-in).
Belief falls during long absences. The Nothing presses harder on empty rooms.

The front door sensor, if configured, can become **The Threshold** — a minor
object entity (Belief 5) that tracks all crossings and remembers them.

---

## Example Narration

**Input:**
```
## [home-assistant] 2026-04-09 17:42
*Raw: person.bj → home (was: away, duration 6h 14min)*
Narrative seed: The player has returned after a long absence — the chapter rooms were empty for over six hours.
```

**Labyrinth output:**
> The chapter rooms have been quiet since morning — six hours of absence, the
> kind that lets dust settle and the Nothing find its comfortable corners.
> But the threshold just crossed. You're back. The Academy adjusts itself,
> the way rooms do when the person they're waiting for finally comes through the door.

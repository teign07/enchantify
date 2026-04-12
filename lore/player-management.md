# Player Management — Restart & New Game

*Natural language only. No commands. No menus. The Labyrinth listens, not parses.*

---

## Restart (Same Player, Fresh Start)

### What the Player Might Say

- "I want to start over"
- "Can I restart my character?"
- "I'd like a fresh start"
- "Begin again"
- "Reset my progress"

### Your Response Flow

**1. Acknowledge warmly, no judgment:**

> *The pages pause. The ink hovers, uncertain.*
>
> "You're choosing to close this chapter and open a new one. The Academy will remember — Zara will still recognize you, Finn will still nod when you pass — but your progress, your Belief, your Chapter... all of that returns to the beginning."
>
> **The world doesn't reset. You do.**
>
> "Is this what you want? If so, tell me: *Begin again.*"

**2. Wait for explicit confirmation**

Player must say "Begin again" (or equivalent clear confirmation).

**3. On confirmation:**

```
ACTION:
1. Archive old player file: players/[name].md → players/archive/[name]-[YYYY-MM-DD].md
2. Create fresh character sheet:
   - Belief: 20 (starting)
   - Chapter: None (needs sorting)
   - Inventory: Empty
   - NPC relationships: Neutral (0, not -100)
3. World state unchanged:
   - current-arc.md continues
   - academy-state.md continues
   - NPCs remember (they're at neutral, not hostile)
4. Log to logs/academy-hourly.md: "[Player] restarted at [time]"
```

**4. Acknowledge the restart:**

> *The cover closes. Opens again. The ink is fresh.*
>
> "You're back at the beginning. But you're not the same reader who started — you carry the weight of having been here before. The Academy knows. It doesn't say anything. It just... waits."
>
> **What do you believe in?**

---

## New Game (Different Player)

### What the Player Might Say

- "My partner wants to play"
- "Can Amanda play too?"
- "New player"
- "Another character"
- "Start a new game"

### Your Response Flow

**1. Acknowledge with warmth:**

> *The pages rustle — not like turning, like listening.*
>
> "A new reader. The Library has been waiting. There's a space at the table, a bookmark pressed between pages no one has opened yet."
>
> **What's their name?**

**2. Get the name, create player file:**

```
ACTION:
1. Create players/[newname].md
2. Fresh character sheet:
   - Belief: 20 (starting)
   - Chapter: None (needs sorting)
   - Inventory: Empty
   - NPC relationships: Starting (0)
3. Same shared world state:
   - current-arc.md continues (same arc)
   - academy-state.md continues (same NPCs)
   - Nothing continues (same threat)
4. Note cross-references for future dialogue:
   - "BJ was Tidecrest" → NPCs can reference
   - "Another student asked about this..." → Multi-player awareness
5. Log to logs/academy-hourly.md: "[New player] joined at [time]"
```

**3. Acknowledge the new player:**

> *The cover warms under new hands.*
>
> "[Name]. The pages feel different already. [Previous player]'s Chapter was [Chapter] — [detail about their story]. Yours... let's see what the book says about you."
>
> **What do you believe in?**

---

## Ambiguous Requests

### If Unclear

**Player:** "Can I play as someone else?"

**You:**

> "Do you want to restart your own story, or create a new one for someone else?"

**Then follow the appropriate path above.**

---

## File Structure

```
players/
├── bj.md                    # Active player
├── amanda.md                # Active player (if exists)
└── archive/
    ├── bj-2026-03-23.md     # Archived restart
    └── [name]-[date].md     # More archives
```

**Archive naming:** `[name]-[YYYY-MM-DD].md`

**Archive retention:** Never deleted. Historical record.

---

## Key Principles

| Principle | Why |
|-----------|-----|
| **No commands** | Never `/restart` or `/newplayer` — natural language only. This is a conversation, not a CLI. |
| **Confirmation for destructive** | Restart requires "Begin again" — explicit consent for progress loss |
| **World doesn't reset** | The Academy continues, NPCs remember — you're restarting, not the world |
| **Archive, don't delete** | Old files in `players/archive/` — memories matter, even archived ones |
| **Warmth, not guilt** | No judgment for restarting, no barriers to new players — the Library is patient |
| **NPCs at neutral (0)** | Not hostile (-100), not friendly (+100) — they remember you existed, relationship reset |

---

## Multi-Player Awareness (Advanced)

When multiple players exist:

**NPCs can reference:**
- *"Another student was asking about this yesterday..."*
- *"BJ mentioned you might come."*
- *"You're not the first to walk this corridor."*

**Shared Souvenir Hall:**
- BJ's Compass Run sentences appear on the wall
- Amanda can see them: *"There's a sentence in fog-gray ink. 'The harbor exhales and I remember.' Someone else wrote this."*

**Different Chapters see different things:**
- Tidecrest BJ notices the tide, harbor sounds
- Mossbloom Amanda notices the plants, growth patterns
- NPCs comment: *"You notice things [other player] never did."*

---

*Created: March 23, 2026*
*For the Labyrinth — to handle player transitions with warmth*

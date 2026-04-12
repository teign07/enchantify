# Enchantify Spawn Helper

*How to open the Labyrinth correctly. Read this if you're spawning an Enchantify session.*

---

## The Working Spawn Pattern

```javascript
sessions_spawn({
  task: "You are the Labyrinth of Stories. Open the book. [PLAYER NAME] has arrived. Read AGENTS.md for operating rules, then read their heartbeat and player state. Begin.",
  mode: "run",
  runtime: "subagent",
  model: "anthropic/claude-sonnet-4-6",
  cwd: "/Users/bj/.openclaw/workspace/enchantify"
})
```

**Why these parameters matter:**

- **`model: "anthropic/claude-sonnet-4-6"`** — Required. Without explicit Sonnet, prose quality degrades significantly. Never let this default.
- **`cwd`** — Must point to the enchantify workspace so the agent can find player state, heartbeat, lore, and mechanics files.
- **`task` should name the player** — Helps the agent read the right state file immediately.

---

## What the Agent Does on Open

Per `AGENTS.md` Core Loop:

1. Reads `players/[name].md` — player state, Belief, Chapter, last location
2. Reads `HEARTBEAT.md` — full heartbeat: weather, Spotify, food, steps, GW2, Sparky, dream/diary
3. Reads `lore/seasonal-calendar.md` — any triggered events
4. Reads `mechanics/heartbeat-bleed.md` — translates real-world data into narrative texture
5. Responds with immersive narrative, then updates state files

**The heartbeat is read every session.** The Academy's atmosphere is never generic — it mirrors the player's actual day.

---

## Config Reference

Enchantify's default model is set in `~/.openclaw/openclaw.json`:
```json
{
  "id": "enchantify",
  "model": "anthropic/claude-sonnet-4-6"
}
```

---

## When a Player Opens the Book

They say something like:
- *"Open the book"*
- *"I want to play Enchantify"*
- *"Let's go back to the Academy"*

Spawn with the pattern above, naming them in the task. The agent handles everything from there.

---

*Last updated: March 29, 2026*
*Validated: Claude Sonnet 4.6 — full heartbeat bleed enabled*

# Enchantify Spawn Helper

*How to open the Labyrinth correctly. Read this if you're spawning an Enchantify session.*

---

## The Working Spawn Pattern

```javascript
sessions_spawn({
  task: "You are the Labyrinth of Stories. Open the book for [PLAYER NAME]. Read AGENTS.md and follow the full session-open loop. Run session-entry for this player, follow ENTRY_MODE exactly, read the required world state, and write a substantial opening active-play scene, not a stub. If under 1 hour since last logout, resume where they last were. If 1 hour or more, begin in the dorm. On Telegram, do not send plain assistant prose. Deliver the opening through the run-live-scene.py pipeline so voice and image can run.",
  mode: "run",
  runtime: "subagent",
  model: "openai-codex/gpt-5.4",
  cwd: "/Users/bj/.openclaw/workspace/enchantify"
})
```

**Why these parameters matter:**

- **`model: "openai-codex/gpt-5.4"`** — Required. This is the primary spawn model. Never let this default.
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
  "model": "openai-codex/gpt-5.4"
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

*Last updated: April 23, 2026*
*Validated: openai-codex/gpt-5.4 — full heartbeat bleed enabled*

### Enchantify close-session spawn

When the user wants to end play, spawn Enchantify with an explicit closeout task, not a casual acknowledgement.

```js
sessions_spawn({
  task: "You are the Labyrinth of Stories. Close the book for [PLAYER NAME]. Read AGENTS.md and follow the full session-close loop. Run the required closeout steps, update state, clear the session lock, and only then treat the session as closed. If a final Telegram sendoff is appropriate, deliver it through the local session delivery path rather than plain assistant prose.",
  mode: "run",
  runtime: "subagent",
  model: "openai-codex/gpt-5.4",
  cwd: "/Users/bj/.openclaw/workspace/enchantify"
})
```

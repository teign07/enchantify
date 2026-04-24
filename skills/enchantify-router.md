# Enchantify Router

**When user says:**
- "open the book"
- "open the Labyrinth"
- "start Enchantify"
- "play Enchantify"

**Do this:**
```
sessions_spawn(
  agentId="enchantify",
  task="Open the book for the current player. Follow AGENTS.md session-open rules, run session-entry, obey ENTRY_MODE, write a substantial opening active-play scene, and on Telegram send it through the full scene pipeline with play_scene.py rather than as plain chat text."
)
```

**When user says:**
- "close the book"
- "close the Labyrinth"
- "stop playing"
- "exit Enchantify"

**Do this:**
```
sessions_spawn(
  agentId="enchantify",
  task="Close the book for the current player. Follow AGENTS.md session-close rules and run the real closeout ritual before treating the session as ended. Do the required close-session flow from mechanics/agent-reference.md, update state, clear the session lock, and if Telegram needs a final in-world sendoff, deliver it through the local session delivery path rather than plain chat prose."
)
```

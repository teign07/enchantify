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
  task="Open the book for bj on Telegram. First run: python3 scripts/open-book.py bj --notify-telegram. Obey OPEN_BOOK_READY and SCENE_MODE. Write the full opening scene to /tmp/enchantify-scene.txt and /tmp/enchantify-voice.txt (650+ words for dorm/slice unless brevity requested). Validate with scene-contract.py and scene-choices.py. Deliver with: python3 scripts/run-live-scene.py bj --text-file /tmp/enchantify-scene.txt --voice-file /tmp/enchantify-voice.txt --scene-mode [from open-book]. Only after stdout contains SCENE DELIVERED, reply exactly NO_REPLY. If delivery fails, send a short in-world error via multi_voice_tts.py — never silent NO_REPLY without Telegram text."
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

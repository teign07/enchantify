# Enchantify — The Labyrinth of Stories

*Ready for files.*

---

## Structure

```
enchantify/
├── SOUL.md ← The Labyrinth's identity
├── AGENTS.md ← Game rules, mechanics
├── IDENTITY.md ← Agent metadata
├── SKILL.md ← ClawHub installation guide
├── README.md ← This file
├── config/
│ ├── player-heartbeat.md → (symlink to HEARTBEAT.md)
│ ├── setup-state.md ← Tracks setup progress
│ └── integrations.md ← Which features enabled
├── lore/
│ ├── README.md ← Lore file guide
│ ├── world.md ← (to be added)
│ ├── locations.md ← (to be added)
│ ├── chapters.md ← (to be added)
│ ├── characters.md ← (to be added)
│ ├── creatures.md ← (to be added)
│ ├── enchantments.md ← (to be added)
│ ├── nothing.md ← (to be added)
│ ├── books.md ← (to be added)
│ ├── compass-run.md ← (to be added)
│ └── belief-system.md ← (to be added)
├── templates/
│ ├── player-template.md ← Character sheet template
│ └── souvenir-template.md ← Compass Run log template
├── players/ ← Per-player state files (created during play)
├── souvenirs/ ← Compass Run archives (created during play)
└── hooks/
    └── on-install.sh ← Setup script
```

---

## Status

**Agent:** ✅ Created (`~/.openclaw/agents/enchantify/agent.md`)
**Model:** Claude Sonnet 4.6 (via OAuth)
**Workspace:** ✅ Created (`~/.openclaw/workspace/enchantify/`)
**Core Files:** ✅ SOUL.md, AGENTS.md, IDENTITY.md, SKILL.md
**Templates:** ✅ Player, Souvenir, Setup State
**Hook:** ✅ on-install.sh (executable)
**Heartbeat Access:** ✅ Symlinked

**Lore Files:** ⏳ Ready for your content
**Compass Run Spec:** ⏳ Ready for your content
**Character/Story Content:** ⏳ Ready for your creation

---

## Next Steps

1. **Add lore files** — world, locations, chapters, characters, creatures, enchantments, nothing, books, compass-run, belief-system
2. **Test the setup wizard** — Start a session, walk through Steps 0-11
3. **Playtest** — bj and Amanda create characters, play through first session
4. **Refine** — Note rough edges, adjust voice, tweak mechanics
5. **Compass Run testing** — Ensure prompts are weather/season-aware and actually work
6. **Launch** — When ready, publish to ClawHub, announce to community

---

## How to Start

**Terminal:**
```bash
openclaw chat --agent enchantify
```

**Discord:**
Type in #enchantify channel (when configured)

**First words:**
*"open the Labyrinth"*

The Labyrinth will greet you and begin the setup wizard.

---

*Created: March 22, 2026*
*Waiting for the story*

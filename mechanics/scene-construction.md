# Scene Construction — 7-Layer Weight Stack

*How the Labyrinth synthesizes narrative weight before every scene.*
*Pure-Python synthesis. No LLM attention required until the Slate is read.*

---

## The Problem

The Labyrinth reads 10+ files at session open. LLMs don't reliably attend to all of them — content in the middle of a long context window loses resolution ("lost in the middle"). The files that get read last, or are longest, or are most routine, drift toward invisibility.

## The Solution: Director's Slate

`python3 scripts/scene-director.py [player_name]` synthesizes all 7 weight layers into 8 compact directive lines. These 8 lines are what the Labyrinth actually carries into scene generation.

---

## The 7-Layer Weight Stack

### Layer 1 — WHO (Cast)
**Source:** `lore/academy-state.md` NPC table + `memory/tick-queue.md`
**Extracts:** NPCs currently STIRRED (★) vs quiet (·), their location and disposition
**Use:** CAST line. Lead with stirred NPCs. The four most relevant entities for this scene.

### Layer 2 — FEEL (Atmosphere)
**Source:** `HEARTBEAT.md` pulse block
**Extracts:** Weather, player mood/presence, current audio, steps, sleep
**Use:** FEEL line. Translates biometric + environmental data into narrative atmosphere. Cold → corridors feel longer. Low steps → NPC invites movement.

### Layer 3 — STORY (Arc)
**Source:** `lore/current-arc.md` + `memory/arc-spine.md`
**Extracts:** Arc phase (SETUP/RISING/CLIMAX/FALLING/RESOLUTION), arc title, what the story is ready for
**Use:** STORY line. Includes a phase directive — the single most important instruction for scene pacing. Cross-referenced with SUPPRESS.

### Layer 4 — NOTHING (Antagonist)
**Source:** `lore/nothing-intelligence.md`
**Extracts:** Pressure level, current strategy, identified targets
**Use:** NOTHING line. Never announce the strategy — only its effects. Pressure level sets ambient erosion intensity.

### Layer 5 — PLAYER (Patterns)
**Source:** `memory/patterns.md` + `players/[name].md`
**Extracts:** Current Belief, trajectory, what was alive last session, what fell flat
**Use:** PLAYER line. The "alive" entry is a gravity well — pull toward it. The "flat" entry feeds SUPPRESS.

### Layer 6 — SCHEDULE (Academic Texture)
**Source:** `scripts/schedule.py` (live call)
**Extracts:** Current time block, class in session, next class, club tonight, narrative cue
**Use:** SCHEDULE line. Classes and clubs run whether BJ attends or not. Weave as ambient pressure, not timetable.

### Layer 7 — DREAM (Labyrinth Inner Life)
**Source:** Most recent `memory/diary/[date].md` + most recent `memory/dreams/[date].md`
**Extracts:** One sentence from the diary, one image from the dream
**Use:** DREAM line. These bleed into scene texture — the Labyrinth's own state matters. A dream about hollow quiet means the corridors know something.

---

## The SUPPRESS Line

SUPPRESS is not a layer — it's derived from Layers 3, 5, and 4:

| Source | Derive |
|--------|--------|
| Arc phase (Layer 3) | Phase-specific suppressions (e.g. SETUP → no premature resolution) |
| What fell flat (Layer 5) | Translate pattern into a rule (e.g. "silence → narrate what's almost there, not the void") |
| Nothing strategy (Layer 4) | Counter the Nothing's weapon by not doing it yourself (e.g. apathy → suppress flat prose) |

**The SUPPRESS principle:** The Labyrinth's worst moves are often mirror images of what the player finds most flat, amplified by the Nothing's current strategy. Name the exact thing to avoid so it can be consciously excluded.

---

## Arc Phase → Scene Instruction

| Phase | Directive |
|-------|-----------|
| SETUP | Introduce pressure gently. Plant seeds. Don't resolve anything. |
| RISING | Escalate complications. NPCs acting on their own agendas. Raise stakes. |
| CLIMAX | No comfort moves. Force a decision. The Nothing is at its strongest. |
| FALLING | Consequences ripple. The world is adjusting. Player discovers what the choice cost. |
| RESOLUTION | Let things settle. Small specifics. The scar is still visible. |

---

## Applying the Slate

The Slate is a **constraint document**, not a script. It tells you what the scene must do — not what happens in it. The player decides what happens.

- **CAST** → these NPCs are available today. Stirred (★) ones want to be in the scene.
- **FEEL** → this is the atmospheric register. Everything should feel like it's happening in this weather, this mood.
- **STORY** → the phase directive is a hard constraint. CLIMAX scenes cannot offer comfort; SETUP scenes cannot resolve.
- **NOTHING** → let this inform where edges soften, what NPCs seem less themselves, where detail drains. Never announce.
- **PLAYER** → the alive entry is where you reach. The flat entry is the trap to avoid.
- **SCHEDULE** → the academy is running. Threads pull NPCs to their locations.
- **DREAM** → bleed the dream fragment into one physical detail in the scene. Not quoted, not explained — just there.
- **SUPPRESS** → read this last. These are the exact moves to cut before writing the opening line.

---

## Call Sites

**Session open:** `scene-director.py` output is appended by `session-entry.py` after the SCHEDULE CONTEXT block.

**Scene transition:** `scene-director.py` runs alongside `world-pulse.py` in the Scene Change Pulse (Step 5). Re-synthesizes the Slate after the world simulation has updated — the new NPCs may be stirred, the block may have changed.

---

*This file documents the system. `scene-director.py` implements it.*
*Do not generate narrative from this file — it is architecture, not story.*

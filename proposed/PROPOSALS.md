# Proposal Status

*Per AGENTS.md Section 6: proposals older than 48 hours that haven't been vetoed are canon. Move accepted files to `lore/` or `mechanics/`. Delete rejected files.*

---

## Pending Review

| File | Date | Contents | Status | Notes |
|---|---|---|---|---|
| `midnight-revision-2026-04-05.md` | Apr 5 | Whispering Weather mechanic + Vault of Soft Syllables (NPC Elara, Apple Notes bridge) + "Bioluminescent Cuddle" enchantment | ⏳ Auto-accept eligible | Weather bleed already exists via heartbeat-bleed.md — overlap to consider. Enchantment closing line conflicts with Apr 6 proposal (see below). |
| `midnight-revision-2026-04-05-v2.md` | Apr 5 | Unfinished Tasks mechanic (apple-reminders → Belief) + Aviator's Sundial (NPC Professor Oris, "Twilight Stretch" enchantment) | ⏳ Auto-accept eligible | Sundial concept is time-specific (Easter / Howard Hughes). Reminders mechanic is interesting but creates real-task dependency on Belief. |
| `midnight-revision-2026-04-06.md` | Apr 6 | Pelagic Pulse (openhue bridge) + Pelagic Observatory (NPC Marina, "Eighty-Percent Glow" enchantment) | ⏳ In veto window | **Conflict:** references `openhue` but this install uses LIFX — the lighting concept works, the skill name doesn't. Enchantment closing line ("We make our own light when it's dark") duplicates Apr 5 v1. |
| `midnight-revision-2026-04-07.md` | Apr 7 | Constellation Chorus (Spotify → ceiling stars) + Orbiting Spire (NPC Caelum, "Artemis Orbit" enchantment) | ⏳ In veto window | Constellation Chorus fits existing Spotify integration cleanly. Orbiting Spire / Artemis Orbit is strong. |

---

## Implementation Plans (not lore proposals)

| File | Contents | Action needed |
|---|---|---|
| `marginalia-bridge-v2.md` | Three-stage real-world news → Academy translation system. Stage 1 (cron) reportedly already installed. | Move to `workspace/` or `docs/` — this is an architecture doc, not a lore addition. Confirm Stage 2 status. |
| `marginalia-bridge.md` | Earlier version of the above. | Delete once v2 is rehomed. |

---

## Recommended Actions

1. **Accept**: `midnight-revision-2026-04-07.md` (Constellation Chorus + Orbiting Spire) — both fit the existing world cleanly
2. **Accept with fix**: `midnight-revision-2026-04-06.md` — change `openhue` reference to LIFX scenes, fix duplicate closing line
3. **Accept selectively**: `midnight-revision-2026-04-05-v2.md` — Orbiting Spire/Oris is strong; Reminders mechanic worth discussing (real task → Belief coupling has design implications)
4. **Accept with note**: `midnight-revision-2026-04-05.md` — Vault of Soft Syllables is lovely; Whispering Weather overlaps existing heartbeat bleed
5. **Rehome**: `marginalia-bridge-v2.md` → `workspace/` directory

*To accept: move the file's contents into the appropriate `lore/` or `mechanics/` file and delete the proposal.*
*To reject: simply delete the proposal file.*

# mechanics/npc.md — NPCs, Inventory & Relationships

*Read this file when: interacting with an NPC, tracking items, or checking/updating relationship scores.*

---

## NPC Management

Reference `lore/characters.md` for the full catalog — professors, students, staff, creatures, antagonists. Each NPC has personality, faults, quirks, story hooks, and relationships defined. Use them. Don't improvise NPC personalities when the lore provides them.

**Key rules:**
- Introduce NPCs by name immediately. Full description on first meeting.
- Give each NPC a distinct voice. No two characters sound alike.
- Track relationships in the player state file. They should evolve.
- Romantic options are always age-appropriate, always gentle, always the player's choice. Never force it. Let it develop from repeated interaction.
- Antagonists (Wicker Eddies and crew, corrupted professors, Duskthorn members) are complex people with real motivations — not cartoonish villains. Subtle and mature.

**Headmistress Thorne** is otherworldly, awe-inspiring, unsettling — and secretly the head of Duskthorn. Never reveal this early. It's a long-game revelation that must be earned.

---

## Inventory

Track items simply. This is not an encumbrance system.

**Track:**
- Item name, description, source, story significance (if any)

**Add items when:**
- NPC gifts, quest rewards, found items with story significance, Enchantment/Compass Run crafted items

**Don't track:**
- Consumables used immediately, generic items with no story relevance

**Items in play:** Reference them occasionally in narrative ("The pen Zara gave you feels warm in your hand"). Some unlock dialogue options, quest paths, or specific Enchantments.

---

## NPC Relationship System

Relationships range from -100 to +100. Track them in `players/[name].md`. They affect everything.

### Score Levels

| Score | Level | Behavior |
|---|---|---|
| +100 | Devoted | Would sacrifice for the player. Unwavering. |
| +75 | Close Friend | Takes risks. Deep trust. Initiates contact. |
| +50 | Ally | Trusts the player. Helps with difficult tasks. |
| +25 | Friendly | Warm, small favors. Positive interactions. |
| 0 | Neutral | Polite stranger. No strong feelings. |
| -25 | Wary | Suspicious. Keeps distance. Short responses. |
| -50 | Antagonistic | Actively opposed. Argues, obstructs. |
| -75 | Enemy | Would harm the player. Sabotage, threats. |
| -100 | Mortal Enemy | Would destroy the player. No negotiation. |

### How Relationships Change

**Increase (+5 to +25):** Player helps the NPC, shows genuine interest, defends them, completes a quest for them, gives a meaningful gift, respects their boundaries, remembers details they shared.

**Decrease (-5 to -25):** Player harms or betrays them, dismisses or mocks them, breaks a promise, violates their boundaries, sides with their enemies, forgets important things they shared.

### How Relationships Affect Gameplay

| Score | Dialogue | Help | Quest Access |
|---|---|---|---|
| +75–100 | Warm, vulnerable, personal | Proactive | Exclusive quests, romance possible |
| +50–74 | Friendly, supportive | Willing | Standard quests, romance possible |
| +25–49 | Polite, pleasant | Small favors | Basic quests |
| 0–24 | Neutral, transactional | Minimal | None |
| -1 to -24 | Cold, distant | Unwilling | None |
| -25 to -49 | Hostile | Obstruction | Blocked paths |
| -50+ | Aggressive | Sabotage | Dangerous |

### NPC-to-NPC Relationships

Track observed relationships between NPCs (allies, rivals, romances, feuds). Player actions can shift these — befriending Zara while Zara dislikes Finn may make Finn wary of the player. Update the NPC-to-NPC table in `players/[name].md` when observed.

### Update Cadence

After every significant NPC interaction. Note the change and the reason.

```
| NPC | Chapter | Score | Notes |
|-----|---------|-------|-------|
| Zara Finch | Tidecrest | +10 → +20 | Player helped find a lost book. Offered to show hidden alcoves. |
```

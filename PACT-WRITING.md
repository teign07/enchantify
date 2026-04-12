# Writing Chapter Pacts
### How the Academy Claims the World

---

A pact is a chapter's claim on a piece of the player's digital life.
Not surveillance — custody. The chapter takes responsibility for that
territory and governs it according to its philosophy.

Tidecrest doesn't control Spotify. It reads the ambient frequency of the
current moment and translates it into sound. Duskthorn doesn't lock your
lights. It keeps the room slightly edged, because softness without
contrast produces nothing.

The pact is the translation layer between the chapter's philosophy and
the real world. Write it like that.

---

## The Three Files

Every pact is a directory in `pacts/[chapter-id]/` containing:

| File | Purpose |
|---|---|
| `manifest.md` | What the pact claims, what triggers it, what actions it can fire |
| `govern.py` | The logic — what to do for each trigger |
| `lore.md` | Optional: extended in-world lore for the Labyrinth to read |

---

## Step 1: Copy the Template

```bash
cp -r pacts/_template pacts/myChapter
```

---

## Step 2: Write `manifest.md`

The frontmatter is the machine-readable contract. The body is the lore.

```yaml
---
name: Riddlewind — The Shared Page
id: riddlewind
chapter: Riddlewind
philosophy: The story is written between you and the world — co-authored.
belief_threshold: 0
talisman: Wind Cipher
triggers:
  - session-open
  - compass-direction
  - nothing-encounter
  - belief-gained
actions:
  - spotify_volume
  - notification_send
---
```

**`triggers`** — which events this pact responds to:
- `session-open` — fires when the player opens a session
- `compass-direction` — fires when a Compass Run direction begins (context = "north"|"east"|"south"|"west")
- `nothing-encounter` — fires when the Nothing appears
- `nothing-retreats` — fires when the Nothing is defeated
- `belief-gained` — fires when Belief is gained (context = amount as string)
- `belief-lost` — fires when Belief is lost (context = amount as string)
- `arc-crisis` — fires when the current arc reaches a crisis point
- `ambient-state` — fires on the 4-hour cron ambient check

**`actions`** — which actions this pact is allowed to fire. Must match `config/consent.json`.

---

## Step 3: Write `govern.py`

The governance engine imports this and calls `handle(trigger, context)`.
Return a list of action calls. Return `[]` for triggers you don't handle.

```python
def handle(trigger: str, context: str = "") -> list[dict]:
    if trigger == "session-open":
        return [{"action": "spotify_volume", "params": {"level": 40}}]
    
    if trigger == "nothing-encounter":
        return [
            {"action": "spotify_volume", "params": {"level": 10}},
            {"action": "lifx_scene", "params": {"scene": "nothing"}},
        ]
    
    return []
```

**Available action IDs:**

| Action | Params | What it does |
|---|---|---|
| `spotify_play` | `{"uri": "spotify:..."}` (optional) | Play Spotify |
| `spotify_pause` | `{}` | Pause Spotify |
| `spotify_playpause` | `{}` | Toggle play/pause |
| `spotify_skip` | `{}` | Skip current track |
| `spotify_like` | `{}` | Like current track |
| `spotify_volume` | `{"level": 0-100}` | Set volume |
| `notification_send` | `{"title": str, "body": str, "sound": str\|None}` | macOS notification |
| `do_not_disturb_on` | `{}` | Enable DND |
| `do_not_disturb_off` | `{}` | Disable DND |
| `lifx_scene` | `{"scene": "academy"\|"library"\|"nothing"\|"compass-north"\|...}` | LIFX scene |
| `obsidian_note_create` | `{"title": str, "content": str, "tags": [...], "folder": str}` | Create Obsidian note |
| `obsidian_note_tag` | `{"path": str, "tag": str}` | Tag existing note |

**The governance engine handles:**
- Consent checking (won't fire unapproved actions)
- Logging to `logs/action-chronicle.md`
- Error recovery

**You don't need to handle:**
- Consent
- Logging
- Try/except around action calls

---

## Step 4: Register Actions in `consent.json`

If your pact fires a new action, add it to `config/consent.json` under `"actions"`.
Then add the pact to `"pacts"` with its `"governs"` list.

Or use the consent registry:
```bash
python3 scripts/consent-registry.py approve obsidian_note_create
python3 scripts/consent-registry.py pact-activate myChapter
```

---

## Step 5: Test It

```bash
# Check that your pact is discovered
python3 scripts/governance-engine.py --list

# Dry run — see what would fire without firing it
python3 scripts/governance-engine.py --trigger session-open --dry-run

# Actually run it
python3 scripts/governance-engine.py --trigger session-open
```

---

## Writing Good Pact Lore

The `manifest.md` body is read by the Labyrinth. It should answer:

- **What does this chapter believe** about this corner of the digital world?
- **What metaphor** does the chapter use? (Tidecrest doesn't "play music." It "reads the ambient frequency.")
- **When does it stay quiet** and when does it act?
- **What does the player feel** vs. what happens mechanically?

Write the lore contract like you're briefing an author on a new character.
The chapter is a character. The workflow is its territory. The pact is the story of that relationship.

---

## The Five Chapters and Their Natural Territories

| Chapter | Philosophy | Natural Territory |
|---|---|---|
| **Emberheart** | Self-authorship | Solo creative tools — Obsidian notes, writing files, personal playlists, DND on |
| **Mossbloom** | Surrender | Reading lists, meditation apps, ambient sound, slow playlists |
| **Tidecrest** | Moments | Music, present-state lighting, Spotify — whatever fits right now |
| **Riddlewind** | Co-authorship | Communication tools, shared files, collaborative playlists, notifications on |
| **Duskthorn** | Necessary conflict | Lighting (edged), alerts (open), drama playlists, arc-crisis notifications |

---

## What You Cannot Claim

Pacts cannot fire unapproved actions. The following require `"scope": "hard"` and
explicit per-use approval (not pre-approved):
- `file_delete`
- `email_send`
- `file_move`

The emergency override word is **THORNE**. The player speaks it in any message
and all governance pauses immediately. It does not resume until they say so.

---

## The Nothing's Territory

Any workflow *without* a pact is the Nothing's preferred habitat.
Ungoverned digital spaces accumulate apathy. If the player never claims
their email workflow, the Nothing settles there — quietly, without announcement.

That's not a bug. It's the physics of the system.

---

## Sharing Your Pact

1. Fork the Enchantify repository
2. Add your `pacts/[chapter-id]/` directory
3. Open a pull request

Good pacts become canon. The world grows.

---

*"The question isn't what Enchantify can do. It's what the player's life
contains that could be governed with intention. Every unclaimed workflow
is territory. Every piece of territory is a story waiting to be told."*

*— The Pact Keeper*

#!/usr/bin/env python3
"""
tick.py — Weighted-random world simulation tick + anchor decay.

1. ENTITY TICK — reads lore/world-register.md, selects 1-3 entities by
   Belief-weighted probability (high Belief = higher chance, but ANY can appear),
   appends them to memory/tick-queue.md for the next session open.

2. ANCHOR DECAY — scans all players/*-anchors.md files. Anchors not visited
   in 30+ days lose 1 Belief (floor: 5). Decayed anchors are noted in tick-queue.

Usage:
  python3 scripts/tick.py [--count N] [--dry-run]

  --count N   Override number of entities selected (default: random 1-3)
  --dry-run   Print what would happen without writing anything
"""
import re
import random
import shutil
import argparse
import sys
from pathlib import Path
from datetime import datetime, date

BASE_DIR   = Path(__file__).parent.parent
_SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(_SCRIPT_DIR))
import world_context
import importlib.util as _ilu
try:
    import npc_log as _npc_log
    _HAS_NPC_LOG = True
except ImportError:
    _HAS_NPC_LOG = False
_pe_spec = _ilu.spec_from_file_location("pact_engine", _SCRIPT_DIR / "pact-engine.py")
pact_engine = _ilu.module_from_spec(_pe_spec)
_pe_spec.loader.exec_module(pact_engine)

REGISTER = BASE_DIR / "lore" / "world-register.md"
THREADS  = BASE_DIR / "lore" / "threads.md"
QUEUE    = BASE_DIR / "memory" / "tick-queue.md"

DECAY_THRESHOLD_DAYS   = 30
DECAY_AMOUNT           = 1
ANCHOR_FLOOR           = 5

# ── Thread lifecycle ──────────────────────────────────────────────────────────
# Phase bands: Belief range → phase label.
# The phase field in world-register.md is the *narrative* phase (may lag Belief by 1-2 sessions).
# Escalation notes signal the Labyrinth to deliver the shift; it updates the register at session close.
THREAD_STIR_GAIN    = 1    # Belief gained per stir (threads grow slower than NPCs)
THREAD_BELIEF_CAP   = 65   # threads close narratively before reaching NPC cap
THREAD_SEED_BELIEF  = 20   # min NPC Belief to flag as a potential thread seed

PHASE_BANDS = [
    (0,   4,  "dormant"),
    (5,  14,  "setup"),
    (15, 29,  "rising"),
    (30, 49,  "climax"),
    (50, 999, "resolution"),
]
PHASE_ORDER = ["dormant", "setup", "rising", "climax", "resolution"]

def belief_to_phase_band(belief: int) -> str:
    for lo, hi, label in PHASE_BANDS:
        if lo <= belief <= hi:
            return label
    return "dormant"

INVESTMENT_CHANCE      = 0.25   # probability a stirred NPC invests per tick (talisman)
FREE_INVESTMENT_CHANCE = 0.12   # probability a stirred NPC makes a secondary investment
INVESTMENT_MIN         = 1      # minimum Belief invested per event
INVESTMENT_MAX         = 3      # maximum Belief invested per event
NPC_INVESTMENT_FLOOR   = 8      # NPCs never drop below this from investing
TALISMAN_CAP           = 200    # Chapter Talismans can grow to 200

NPC_BELIEF_CAP         = 100    # NPCs cap at 100 (same ceiling as players)
NPC_STIR_GAIN_MIN      = 1      # Belief gained from being stirred (min)
NPC_STIR_GAIN_MAX      = 2      # Belief gained from being stirred (max)


# ── Fae Bargains ─────────────────────────────────────────────────────────────
# Reads ## The Margin in every player file.
# Finds OPEN bargains whose deadline has passed and writes consequences
# to the tick-queue keyed by fae species.

PLAYERS_DIR = BASE_DIR / "players"

# Per-species consequence flavor — what happens when the debt goes unpaid.
# Keyed by lowercase species name or partial match.
_FAE_CONSEQUENCES = {
    "hearthkin": (
        "The warmth in the Archive shifted when the door opened. "
        "The ledger-keeper did not look up, but she turned a page. "
        "The vessel left unlabeled is still there, still unstoppered — "
        "but it is no longer warm to the touch."
    ),
    "wayskeeper": (
        "The Wayskeeper moved between the cases without pausing at the slot. "
        "The vessel pre-labeled for {player} is still there. "
        "She has noted, in notation that cannot be read yet, that the arrival is overdue. "
        "She does not consider this a failure. She considers it a data point."
    ),
    "goblin": (
        "The market door is still there. It does not open. "
        "A goblin debt unpaid is not forgotten — it is catalogued. "
        "Somewhere in the Index Empire, a ledger entry now reads: *owes attention, has not paid.* "
        "The inventory the bargain promised is behind a different door now. That door has a price."
    ),
    "appendix": (
        "Practical, blunt, final: the Appendix Provinces have noted the lapse. "
        "The thing stored here is still yours to claim — but the storage fee has increased. "
        "They do not chase debts. They simply adjust the terms."
    ),
    "punctuation pixie": (
        "Something in the margins shifted. A word in a sentence {player} read yesterday "
        "was different than it should have been. The Punctuation Pixies collect in unusual currency. "
        "The debt is not gone. It has been redenominated."
    ),
    "deep lore dwarf": (
        "Deep Lore Dwarves remember everything. The bargain is in their records. "
        "They will not pursue {player} — they will simply be there, formally, "
        "the next time the Outer Stacks are entered. They will say one word: *'Still.'*"
    ),
    "sentence sprite": (
        "A sentence somewhere in the Academy — a plaque, a heading, something on a wall — "
        "has changed. It now says something slightly different than it did yesterday. "
        "The Sentence Sprites made an adjustment. They do not explain. They only edit."
    ),
    # Fallback for unlisted species
    "_default": (
        "Something in the Outer Stacks has noticed. The bargain is not forgotten — "
        "the Fae do not forget. The terms have not changed. But the door is slightly harder to find."
    ),
}


def _fae_consequence(species: str, player: str) -> str:
    """Return consequence flavor text for the given species."""
    lower = species.lower()
    for key, text in _FAE_CONSEQUENCES.items():
        if key != "_default" and key in lower:
            return text.replace("{player}", player)
    return _FAE_CONSEQUENCES["_default"].replace("{player}", player)


def _parse_margin(text: str) -> list[dict]:
    """Parse ## The Margin from a player file. Returns list of bargain dicts."""
    bargains = []
    in_margin = False
    in_table  = False

    for line in text.splitlines():
        if re.match(r'^## The Margin', line):
            in_margin = True
            continue
        if in_margin and re.match(r'^## ', line):
            break  # next section
        if not in_margin:
            continue

        # Skip header/separator rows
        if '|' not in line:
            continue
        if re.search(r'[-]{3,}', line):
            continue
        if re.match(r'\|\s*Fae\s*\|', line, re.IGNORECASE):
            in_table = True
            continue
        if not in_table:
            continue

        cols = [c.strip() for c in line.strip('|').split('|')]
        if len(cols) < 5:
            continue
        # Columns: Fae | What They Gave | Terms (what you owe) | Deadline | Status
        fae, gave, terms, deadline, status = cols[0], cols[1], cols[2], cols[3], cols[4]
        if fae.startswith('*') or not fae:  # placeholder row
            continue

        bargains.append({
            "fae":      fae.strip(),
            "gave":     gave.strip(),
            "terms":    terms.strip(),
            "deadline": deadline.strip(),
            "status":   status.strip().upper(),
        })

    return bargains


def _deadline_passed(deadline_str: str) -> bool:
    """Return True if the deadline has passed. Accepts YYYY-MM-DD or 'before [event]'."""
    if not deadline_str or deadline_str.lower() in ("open", "none", "—", "-"):
        return False
    # Try to parse as a date
    m = re.search(r'(\d{4}-\d{2}-\d{2})', deadline_str)
    if m:
        try:
            dl = date.fromisoformat(m.group(1))
            return date.today() > dl
        except ValueError:
            pass
    # Condition-based deadlines like "before next visit" can't be auto-evaluated
    return False


def check_fae_bargains(dry_run: bool = False) -> list[str]:
    """Scan all player Fae Bargains. Return tick-queue lines for overdue OPEN bargains."""
    queue_lines = []

    for player_file in PLAYERS_DIR.glob("*.md"):
        # Skip anchor files and other non-player files
        if "-" in player_file.stem:
            continue
        player_name = player_file.stem

        text = player_file.read_text()
        bargains = _parse_margin(text)

        for b in bargains:
            if b["status"] != "OPEN":
                continue
            if not _deadline_passed(b["deadline"]):
                continue

            # This bargain is overdue
            consequence = _fae_consequence(b["fae"], player_name)
            queue_lines.append(
                f"- **[FAE DEBT — {b['fae']}]** Bargain overdue for {player_name}. "
                f"Owed: *{b['terms']}* (deadline: {b['deadline']}). "
                f"{consequence}"
            )

            if not dry_run:
                # Mark as OVERDUE in the player file
                new_line = line_with_status(text, b, "OVERDUE")
                if new_line:
                    player_file.write_text(new_line)
                    text = new_line  # keep in sync for multiple bargains in same file

            if dry_run:
                print(f"  [dry-run] Fae debt: {player_name} owes {b['fae']} — {b['terms']}")

    return queue_lines


def line_with_status(text: str, bargain: dict, new_status: str) -> str:
    """Replace the status cell for a specific bargain row in the player file text."""
    # Match the row by fae name and terms (both must appear)
    fae_escaped   = re.escape(bargain["fae"])
    terms_escaped = re.escape(bargain["terms"][:40])  # first 40 chars as anchor

    def replace_status(m):
        row = m.group(0)
        # Replace the last status cell (OPEN → new_status)
        return re.sub(
            r'\|\s*OPEN\s*(\|[^|]*)?$',
            f'| {new_status} ',
            row,
        )

    updated = re.sub(
        rf'\|[^|]*{fae_escaped}[^|]*\|.*?{terms_escaped}.*',
        replace_status,
        text,
        flags=re.IGNORECASE,
    )
    return updated


# ── Entity tick ───────────────────────────────────────────────────────────────

def parse_entities(text):
    """Extract all entities with Belief scores from world-register.md.
    Reads optional [thread:id] tag from the Notes column."""
    entities = []

    # Match rows with 4 columns: name | type | belief | notes |
    row_re = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|\s*([^|]*)\s*\|", re.MULTILINE)
    for m in row_re.finditer(text):
        name, etype, belief, notes = m.groups()
        name = name.strip()
        if name.lower() in ('entity', 'talisman', 'name', '---', ''):
            continue
        # Extract [thread:id1,id2] tags from notes
        thread_m = re.search(r'\[thread:([^\]]+)\]', notes)
        threads = [t.strip() for t in thread_m.group(1).split(',')] if thread_m else []
        entities.append({
            'name':    name,
            'type':    etype.strip(),
            'belief':  int(belief),
            'threads': threads,
            'notes':   notes.strip(),
        })

    whisper_re = re.compile(r"^-\s+(.+?)\s*\((\w[\w\s]*?),\s*Belief\s+(\d+)\)", re.MULTILINE)
    for m in whisper_re.finditer(text):
        name, etype, belief = m.groups()
        entities.append({'name': name.strip(), 'type': etype.strip(), 'belief': int(belief), 'threads': []})

    return entities


def get_thread_names():
    """Read lore/threads.md and return {thread_id: thread_name} mapping."""
    if not THREADS.exists():
        return {}
    text = THREADS.read_text()
    names = {}
    # Match: ## Thread: Name followed by **id:** `slug`
    sections = re.split(r'^## Thread: ', text, flags=re.MULTILINE)
    for section in sections[1:]:
        lines = section.strip().splitlines()
        thread_name = lines[0].strip() if lines else ''
        id_m = re.search(r'\*\*id:\*\*\s*`([^`]+)`', section)
        if id_m:
            names[id_m.group(1)] = thread_name
    return names


def group_by_thread(selected, thread_names):
    """Group selected entities by their thread tags.
    Returns (thread_groups dict, unthreaded list)."""
    thread_groups = {}
    unthreaded = []
    for e in selected:
        if e.get('threads'):
            for tid in e['threads']:
                thread_groups.setdefault(tid, []).append(e)
        else:
            unthreaded.append(e)
    return thread_groups, unthreaded


def weighted_sample(entities, n):
    """Select n entities without replacement, weighted by Belief (min weight 1)."""
    pool = [(e, max(1, e['belief'])) for e in entities]
    selected = []
    for _ in range(min(n, len(pool))):
        total = sum(w for _, w in pool)
        r = random.uniform(0, total)
        cumulative = 0
        for i, (entity, weight) in enumerate(pool):
            cumulative += weight
            if r <= cumulative:
                selected.append(entity)
                pool.pop(i)
                break
    return selected


# ── NPC Belief Gain + Talisman Investment ────────────────────────────────────

def get_belief_in_text(text, name):
    """Return current Belief for a named entity in world-register text, or None."""
    row_re = re.compile(
        r"^\|\s*" + re.escape(name) + r"\s*\|\s*[^|]+\s*\|\s*(\d+)\s*\|",
        re.MULTILINE
    )
    m = row_re.search(text)
    return int(m.group(1)) if m else None


def set_belief_in_text(text, name, new_belief):
    """Return (new_text, changed) with updated Belief for the named entity row."""
    row_re = re.compile(
        r"^(\|\s*" + re.escape(name) + r"\s*\|\s*[^|]+\s*\|\s*)\d+(\s*\|)",
        re.MULTILINE
    )
    new_text, n = row_re.subn(rf"\g<1>{new_belief}\g<2>", text, count=1)
    return new_text, n > 0


def run_npc_stir_gains(selected, register_text, dry_run=False):
    """
    Each stirred NPC gains NPC_STIR_GAIN_MIN–MAX Belief from being noticed.
    Being called into the narrative is the energizing act.

    Returns (modified_text, gain_count). Gain is applied silently — no queue entries.
    """
    text  = register_text
    count = 0

    for e in selected:
        etype = e['type'].lower()
        if etype not in ('npc', 'creature', 'thread'):
            continue  # Object, Location, Talisman — no stir gain

        # Skip permanent threads (academy-daily — they don't escalate)
        if etype == 'thread' and 'permanent' in e.get('notes', '').lower():
            continue

        current = get_belief_in_text(text, e['name'])
        cap     = THREAD_BELIEF_CAP if etype == 'thread' else NPC_BELIEF_CAP
        if current is None or current >= cap:
            continue

        gain  = THREAD_STIR_GAIN if etype == 'thread' else random.randint(NPC_STIR_GAIN_MIN, NPC_STIR_GAIN_MAX)
        new_b = min(cap, current + gain)

        if dry_run:
            print(f"  [dry-run] Stir gain: {e['name']}  {current} → {new_b}")
        else:
            text, changed = set_belief_in_text(text, e['name'], new_b)
            if changed:
                count += 1

    return text, count


def run_npc_talisman_investments(selected, register_text, dry_run=False):
    """
    For each stirred NPC with a chapter affiliation, roll INVESTMENT_CHANCE to
    invest 1–3 Belief into their chapter's talisman.

    Returns (investment_seeds: list[str], modified_text: str).
    Belief changes are applied in-memory; caller writes the file if needed.
    """
    seeds = []
    text  = register_text

    for e in selected:
        if e['type'].lower() not in ('npc', 'creature'):
            continue
        chapter  = world_context.CHAPTER_MAP.get(e['name'])
        talisman = world_context.CHAPTER_TALISMAN.get(chapter) if chapter else None
        if not talisman:
            continue

        if random.random() > INVESTMENT_CHANCE:
            continue

        npc_b = get_belief_in_text(text, e['name'])
        tal_b = get_belief_in_text(text, talisman)
        if npc_b is None or tal_b is None:
            continue
        if npc_b <= NPC_INVESTMENT_FLOOR:
            continue    # too drained to give
        if tal_b >= TALISMAN_CAP:
            continue    # talisman already maxed

        amount = random.randint(INVESTMENT_MIN, INVESTMENT_MAX)
        amount = min(amount, npc_b - NPC_INVESTMENT_FLOOR)
        amount = min(amount, TALISMAN_CAP - tal_b)
        if amount <= 0:
            continue

        new_npc_b = npc_b - amount
        new_tal_b = tal_b + amount

        if not dry_run:
            text, _ = set_belief_in_text(text, e['name'], new_npc_b)
            text, _ = set_belief_in_text(text, talisman,  new_tal_b)

        seeds.append(
            f"- *[Talisman Investment]* **{e['name']}** ({chapter}) channels "
            f"{amount} Belief into the **{talisman}** (now {new_tal_b})"
        )
        if not dry_run and _HAS_NPC_LOG:
            _npc_log.append(
                e['name'], "belief_invest",
                f"Invested {amount} Belief into {talisman} ({chapter})"
            )
        if dry_run:
            print(f"  [dry-run] {e['name']} → {talisman}: "
                  f"NPC {npc_b}→{new_npc_b}, Talisman {tal_b}→{new_tal_b}")

    return seeds, text


def run_npc_free_investments(selected, all_entities, register_text, dry_run=False):
    """
    Secondary investment pass: each stirred NPC has a FREE_INVESTMENT_CHANCE of investing
    1–3 Belief into an entity they have a natural connection to — shared story thread,
    same chapter, or any nearby entity with Belief > 0.

    Chapter talismans are excluded (handled by run_npc_talisman_investments).
    Arc entities are excluded (narrative constructs, not investment targets).

    Returns (investment_seeds: list[str], modified_text: str).
    """
    seeds = []
    text  = register_text

    talisman_names = set(world_context.CHAPTER_TALISMAN.values())

    for e in selected:
        if e['type'].lower() not in ('npc', 'creature'):
            continue
        if random.random() > FREE_INVESTMENT_CHANCE:
            continue

        npc_b = get_belief_in_text(text, e['name'])
        if npc_b is None or npc_b <= NPC_INVESTMENT_FLOOR:
            continue

        chapter    = world_context.CHAPTER_MAP.get(e['name'])
        npc_threads = set(e.get('threads', []))

        # Build weighted candidate list
        candidates = []
        for cand in all_entities:
            if cand['name'] == e['name']:
                continue
            if cand['name'] in talisman_names:
                continue  # talisman investments handled separately
            if cand['type'].lower() == 'arc':
                continue  # arc entities are narrative scaffolding, not investment targets
            if cand['belief'] <= 0:
                continue

            score = 1  # base weight — any entity is eligible
            cand_threads = set(cand.get('threads', []))
            if npc_threads & cand_threads:     # shared story thread → strongest pull
                score += 3
            # Thread entities use [id:slug] not [thread:slug] — match against NPC's thread tags
            if cand['type'].lower() == 'thread':
                id_m = re.search(r'\[id:([^\]]+)\]', cand.get('notes', ''))
                if id_m and id_m.group(1) in npc_threads:
                    score += 4  # NPC invests in "their" thread — strong pull
            cand_chapter = world_context.CHAPTER_MAP.get(cand['name'])
            if chapter and cand_chapter == chapter:  # same chapter family
                score += 2
            candidates.append((cand, score))

        if not candidates:
            continue

        # Weighted random selection
        total = sum(s for _, s in candidates)
        r = random.uniform(0, total)
        cumulative = 0
        target = None
        for cand, score in candidates:
            cumulative += score
            if r <= cumulative:
                target = cand
                break
        if target is None:
            target = candidates[-1][0]

        target_b = get_belief_in_text(text, target['name'])
        if target_b is None:
            continue
        if target_b >= NPC_BELIEF_CAP:
            continue

        amount = random.randint(INVESTMENT_MIN, INVESTMENT_MAX)
        amount = min(amount, npc_b - NPC_INVESTMENT_FLOOR)
        amount = min(amount, NPC_BELIEF_CAP - target_b)
        if amount <= 0:
            continue

        new_npc_b    = npc_b    - amount
        new_target_b = target_b + amount

        if not dry_run:
            text, _ = set_belief_in_text(text, e['name'],      new_npc_b)
            text, _ = set_belief_in_text(text, target['name'], new_target_b)

        seeds.append(
            f"- *[Belief Investment]* **{e['name']}** channels "
            f"{amount} Belief into **{target['name']}** (now {new_target_b})"
        )
        if not dry_run and _HAS_NPC_LOG:
            _npc_log.append(
                e['name'], "belief_invest",
                f"Invested {amount} Belief into {target['name']}"
            )
        if dry_run:
            print(f"  [dry-run] Free invest: {e['name']} → {target['name']}: "
                  f"NPC {npc_b}→{new_npc_b}, Target {target_b}→{new_target_b}")

    return seeds, text


# ── Thread lifecycle ──────────────────────────────────────────────────────────

def check_thread_escalations(entities, dry_run=False) -> list[str]:
    """
    Compare each thread entity's current Belief against its registered phase.
    If Belief has crossed a phase threshold, write an escalation or cooling note to queue.
    Permanent threads (academy-daily) are skipped — they don't escalate.
    """
    queue_lines = []
    for e in entities:
        if e['type'].lower() != 'thread':
            continue
        if 'permanent' in e.get('notes', '').lower():
            continue

        belief_band = belief_to_phase_band(e['belief'])

        # Parse registered phase from world-register notes: "Phase: setup — ..."
        phase_m = re.search(r'Phase:\s*(\w+)', e.get('notes', ''), re.IGNORECASE)
        if not phase_m:
            continue
        current_phase = phase_m.group(1).lower()
        # Normalise alternate labels
        if current_phase in ('escalating', 'escalation'):
            current_phase = 'rising'
        if current_phase not in PHASE_ORDER:
            continue

        band_idx  = PHASE_ORDER.index(belief_band)
        phase_idx = PHASE_ORDER.index(current_phase)

        if band_idx > phase_idx:
            queue_lines.append(
                f"- **[THREAD ESCALATION: {e['name']}]** Belief {e['belief']} places this thread "
                f"in `{belief_band}` phase (currently registered as `{current_phase}`). "
                f"Labyrinth: deliver this phase shift naturally over the next session — "
                f"not announced, just felt. Update the phase in `lore/world-register.md` notes at session close."
            )
            if dry_run:
                print(f"  [dry-run] Thread escalation: {e['name']} {current_phase} → {belief_band}")
        elif band_idx < phase_idx and current_phase not in ('dormant',):
            queue_lines.append(
                f"- **[THREAD COOLING: {e['name']}]** Belief {e['belief']} has dropped below "
                f"the `{current_phase}` threshold. Something has deflated. "
                f"Labyrinth: let this thread's quieting register in NPC behavior and ambient texture. "
                f"Update phase in `lore/world-register.md` at session close if the shift feels right."
            )
            if dry_run:
                print(f"  [dry-run] Thread cooling: {e['name']} {current_phase} → {belief_band}")

    return queue_lines


def check_thread_seeds(entities, dry_run=False) -> list[str]:
    """
    Flag high-Belief NPCs with no dedicated thread tag as potential thread seeds.
    A seed isn't a thread — it's a signal to the Labyrinth that narrative mass is accumulating.
    Avoids re-flagging the same NPC if they already appear in a THREAD SEED entry this week.
    """
    # Check tick-queue for recently flagged seeds (last ~14 ticks worth of content)
    recent_seeds: set[str] = set()
    if QUEUE.exists():
        queue_text = QUEUE.read_text()
        # Only look at entries from the last ~100 lines to avoid unbounded reads
        recent_lines = queue_text.splitlines()[-100:]
        for line in recent_lines:
            m = re.search(r'\[THREAD SEED:\s*([^\]]+)\]', line)
            if m:
                recent_seeds.add(m.group(1).strip().lower())

    queue_lines = []
    for e in entities:
        if e['type'].lower() != 'npc':
            continue
        if e['belief'] < THREAD_SEED_BELIEF:
            continue
        if e['name'].lower() in recent_seeds:
            continue  # Already flagged recently — don't spam

        # Only flag if their only thread tag is academy-daily (or none)
        non_daily = [t for t in e.get('threads', []) if t != 'academy-daily']
        if non_daily:
            continue  # Already has a dedicated thread

        queue_lines.append(
            f"- **[THREAD SEED: {e['name']}]** Belief {e['belief']} — "
            f"narrative mass accumulating without a named thread. "
            f"Labyrinth: if this session touches them meaningfully, "
            f"consider proposing a named subplot. Use as Rule of Three option 3 if confirmed."
        )
        if dry_run:
            print(f"  [dry-run] Thread seed: {e['name']} (Belief {e['belief']})")

    return queue_lines


# ── Anchor decay ──────────────────────────────────────────────────────────────

def parse_anchor_sections(text):
    """Return list of (name, body_text, last_visited_date, belief) tuples."""
    anchors = []
    sections = re.split(r"^## (.+)$", text, flags=re.MULTILINE)
    for i in range(1, len(sections), 2):
        name = sections[i].strip()
        body = sections[i + 1] if i + 1 < len(sections) else ""

        belief_m = re.search(r"\*\*Belief invested:\*\*\s*(\d+)", body)
        visit_m  = re.search(r"\*\*Last visited:\*\*\s*(\d{4}-\d{2}-\d{2})", body)
        coords_m = re.search(r"\*\*Coordinates:\*\*", body)

        if not coords_m:
            continue  # Not a real anchor section

        belief     = int(belief_m.group(1)) if belief_m else 0
        last_visit = date.fromisoformat(visit_m.group(1)) if visit_m else None
        anchors.append({
            "name":        name,
            "belief":      belief,
            "last_visited": last_visit,
        })
    return anchors


def decay_anchor_belief(anchor_file, anchor_name, old_belief, new_belief, dry_run):
    """Decrement an anchor's Belief in place (atomic write)."""
    text = anchor_file.read_text()
    section_re = re.compile(
        r"(^## " + re.escape(anchor_name) + r"\s*$)(.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL
    )
    m = section_re.search(text)
    if not m:
        print(f"  ⚠ Could not locate section for anchor '{anchor_name}'")
        return

    new_section = re.sub(
        r"(\*\*Belief invested:\*\*\s*)\d+",
        rf"\g<1>{new_belief}",
        m.group(2)
    )
    new_text = text[:m.start(2)] + new_section + text[m.end(2):]

    if dry_run:
        print(f"  [dry-run] Would decay '{anchor_name}': Belief {old_belief} → {new_belief}")
        return

    backup = anchor_file.with_suffix(".md.bak")
    shutil.copy2(anchor_file, backup)
    tmp = anchor_file.with_suffix(".md.tmp")
    tmp.write_text(new_text if new_text.endswith("\n") else new_text + "\n")
    tmp.rename(anchor_file)
    print(f"  ↓ Decayed '{anchor_name}': Belief {old_belief} → {new_belief} (last visited: never or >30d)")


def check_anchor_decay(dry_run=False):
    """Scan all player anchor files and decay anchors not visited in 30+ days."""
    anchor_files = list((BASE_DIR / "players").glob("*-anchors.md"))
    decayed = []
    today = date.today()

    for anchor_file in anchor_files:
        text = anchor_file.read_text()
        anchors = parse_anchor_sections(text)
        for a in anchors:
            if a["belief"] <= ANCHOR_FLOOR:
                continue  # Already at floor — skip
            days_away = (today - a["last_visited"]).days if a["last_visited"] else 999
            if days_away >= DECAY_THRESHOLD_DAYS:
                old_b = a["belief"]
                new_b = max(ANCHOR_FLOOR, old_b - DECAY_AMOUNT)
                decay_anchor_belief(anchor_file, a["name"], old_b, new_b, dry_run)
                decayed.append({
                    "name": a["name"],
                    "days_away": days_away,
                    "belief": new_b
                })

    return decayed


# ── Main ──────────────────────────────────────────────────────────────────────

def tag_entities_with_context(entities, ctx):
    """
    Add 'stirrable' and 'location_note' fields to each entity dict.
    Sleeping NPCs get stirrable=False; all other entity types remain stirrable.
    """
    for e in entities:
        state = world_context.get_npc_state(e["name"], e.get("type", "NPC"), ctx)
        e["stirrable"]     = state["stirrable"]
        e["location_note"] = state["note"]
    return entities


def build_queue_line(e):
    """Format a single entity into a tick-queue line with optional location note.
    Thread entities produce beat-advancement prompts instead of standard lines.
    Talisman pact actions are handled separately in main() after entity selection."""
    if e['type'].lower() == 'thread':
        id_m = re.search(r'\[id:([^\]]+)\]', e.get('notes', ''))
        thread_id = id_m.group(1) if id_m else e['name'].lower().replace(' ', '-')
        return (
            f"- **[Beat: {e['name']}]** (Thread, Belief {e['belief']}) — "
            f"Labyrinth: advance this thread. Read `lore/threads.md` entry `{thread_id}`, "
            f"deliver the next beat, and update its **Next beat:** line."
        )
    if e['name'] in pact_engine.TALISMAN_TO_CHAPTER:
        # Pact action handled in step 1c — this line is a fallback only
        return f"- **{e['name']}** (Talisman, Belief {e['belief']}) — stirs in its housing"
    base = f"- **{e['name']}** ({e['type']}, Belief {e['belief']})"
    if e.get("location_note"):
        return f"{base} — {e['location_note']}"
    return base


def main():
    parser = argparse.ArgumentParser(description="World simulation tick")
    parser.add_argument('--count', type=int, default=None,
                        help='Number of entities to select (default: random 1-3)')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    # ── Time context ──────────────────────────────────────────────────────────
    ctx      = world_context.get_time_context()
    night    = world_context.is_night(ctx)
    tag      = world_context.time_tag(ctx)
    prefix   = world_context.time_seed_prefix(ctx)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    header    = f"\n## Tick {timestamp} [{tag}]"
    if prefix:
        header += f"\n*{prefix}*"
    queue_lines = [header]

    # ── 1. Entity tick ────────────────────────────────────────────────────────
    if not REGISTER.exists():
        print(f"❌ {REGISTER} not found.")
        return

    register_text = REGISTER.read_text()
    entities = parse_entities(register_text)
    tag_entities_with_context(entities, ctx)
    thread_names = get_thread_names()

    if entities:
        # Night: only 1 entity, prefer low-belief (Nothing is hunting while everyone sleeps).
        # Remove sleeping NPCs from pool unless they're at crisis level (Belief ≤ 2).
        def is_available(e):
            if e["stirrable"]:
                return True
            return e["belief"] <= 2  # crisis entities stir even at night

        pool = [e for e in entities if is_available(e)]
        if not pool:
            pool = entities  # fallback: nothing suppressed everything

        if night:
            n = args.count if args.count is not None else 1
            # Prefer low-belief entities at night (most vulnerable to Nothing)
            pool.sort(key=lambda e: e["belief"])
        else:
            n = args.count if args.count is not None else random.randint(1, 3)

        selected = weighted_sample(pool, n)

        # Group selected entities by thread
        thread_groups, unthreaded = group_by_thread(selected, thread_names)

        # Write thread activations first (grouped, coherent)
        for tid, group in thread_groups.items():
            tname = thread_names.get(tid, tid)
            parts = []
            for e in group:
                line = f"{e['name']} (Belief {e['belief']})"
                if e.get("location_note"):
                    line += f" — {e['location_note']}"
                parts.append(line)
            queue_lines.append(f"- **[Thread: {tname}]** stirred — {', '.join(parts)}")

        # Then any unthreaded entities (talismans, misc)
        for e in unthreaded:
            queue_lines.append(build_queue_line(e))

        if not args.dry_run:
            suppressed = len(entities) - len(pool)
            print(f"✓ Entity tick [{tag}]: {len(selected)} selected across {len(thread_groups)} thread(s)")
            if suppressed > 0:
                print(f"  ({suppressed} sleeping NPC(s) excluded from pool)")
            for tid, group in thread_groups.items():
                tname = thread_names.get(tid, tid)
                print(f"  [Thread: {tname}] — {', '.join(e['name'] for e in group)}")
            for e in unthreaded:
                loc = f" [{e['location_note']}]" if e.get("location_note") else ""
                print(f"  - {e['name']} (Belief {e['belief']}){loc}")
    else:
        print("⚠ No entities found in world-register.md.")

    # ── 1b. NPC Stir Gains + Talisman Investments ────────────────────────────
    modified_register = register_text   # default; updated in 1b if selected
    stir_count  = 0
    invest_seeds = []
    if selected:
        # Stir gain first — being noticed energizes NPCs before they invest
        modified_register, stir_count = run_npc_stir_gains(
            selected, register_text, dry_run=args.dry_run
        )

        # Talisman investment — primary goal: energy flows to chapter talisman
        invest_seeds, modified_register = run_npc_talisman_investments(
            selected, modified_register, dry_run=args.dry_run
        )

        # Free investment — secondary: NPCs invest in connected entities (threads, chapter-mates, etc.)
        free_seeds, modified_register = run_npc_free_investments(
            selected, entities, modified_register, dry_run=args.dry_run
        )
        invest_seeds.extend(free_seeds)

        if invest_seeds:
            queue_lines.append("")
            queue_lines.extend(invest_seeds)

        # Talisman costs and pact seeds computed in 1c (below) — they modify
        # modified_register in-place, so the atomic write happens after 1c.
        # (Placeholder — actual write moved to after step 1c block)

    # ── 1c. Talisman Actions (pact war / narrative / suggestion / reality bleed)
    # Note: talisman table uses Chapter as the type column, so detect by name.
    # Belief costs are applied to world-register.md in the same pass as 1b.
    talisman_costs = []   # always defined so 1d can reference it
    if selected:
        stirred_talismans = [e for e in selected if e['name'] in pact_engine.TALISMAN_TO_CHAPTER]
        if stirred_talismans:
            pact_context = pact_engine.build_context(
                overall_belief=0,   # placeholder; overridden per-talisman below
                selected_entities=selected,
                time_ctx=ctx,
            )
            pact_seeds = []
            for e in stirred_talismans:
                pact_context["overall_belief"] = e["belief"]
                line, atype, belief_cost, register_delta = pact_engine.run_talisman_action(
                    e["name"], e["belief"], context=pact_context, dry_run=args.dry_run
                )
                if line:
                    pact_seeds.append(line)

                # Talisman spends its own Belief
                if belief_cost > 0:
                    old_b = get_belief_in_text(modified_register, e["name"])
                    if old_b is not None:
                        new_b = max(pact_engine.TALISMAN_WAR_FLOOR, old_b - belief_cost)
                        if new_b != old_b:
                            talisman_costs.append((e["name"], old_b, new_b))
                            if not args.dry_run:
                                modified_register, _ = set_belief_in_text(
                                    modified_register, e["name"], new_b
                                )

                # World investment: add Belief to the target entity
                if register_delta:
                    target_name, delta_amount = register_delta
                    target_b = get_belief_in_text(modified_register, target_name)
                    if target_b is not None and not args.dry_run:
                        new_target_b = target_b + delta_amount
                        modified_register, _ = set_belief_in_text(
                            modified_register, target_name, new_target_b
                        )

                if args.dry_run:
                    cost_str = f" (costs {belief_cost} Belief)" if belief_cost else ""
                    print(f"  [dry-run] {e['name']} → {atype}{cost_str}")

            if talisman_costs and args.dry_run:
                for name, old_b, new_b in talisman_costs:
                    print(f"  [dry-run] War cost: {name}  {old_b} → {new_b}")

            if pact_seeds:
                queue_lines.append("")
                queue_lines.extend(pact_seeds)
                if not args.dry_run:
                    print(f"✓ Talisman actions: {len(pact_seeds)} acted.")
            if talisman_costs and not args.dry_run:
                print(f"✓ Talisman war costs: {len(talisman_costs)} talisman(s) spent Belief.")

    # ── 1d. Atomic write — NPC gains + investments + talisman war costs ──────
    if selected and not args.dry_run:
        needs_write = stir_count > 0 or invest_seeds or talisman_costs
        if needs_write:
            backup = REGISTER.with_suffix(".md.bak")
            shutil.copy2(REGISTER, backup)
            tmp = REGISTER.with_suffix(".md.tmp")
            tmp.write_text(
                modified_register if modified_register.endswith("\n")
                else modified_register + "\n"
            )
            tmp.rename(REGISTER)
        if stir_count > 0:
            print(f"✓ Stir gains: {stir_count} NPC(s) gained Belief from being noticed.")
        if invest_seeds:
            tally = len([s for s in invest_seeds if "[Talisman" in s])
            free  = len([s for s in invest_seeds if "[Belief" in s])
            parts = []
            if tally: parts.append(f"{tally} talisman")
            if free:  parts.append(f"{free} free")
            print(f"✓ NPC investments: {', '.join(parts)} ({len(invest_seeds)} total).")

    # ── 2. Anchor decay ───────────────────────────────────────────────────────
    print("Checking anchor decay...")
    decayed = check_anchor_decay(dry_run=args.dry_run)
    if decayed:
        queue_lines.append("")
        queue_lines.append("*Anchor decay this tick:*")
        for a in decayed:
            days_str = f"{a['days_away']}d unvisited" if a['days_away'] < 999 else "never visited"
            queue_lines.append(f"- **{a['name']}** fading (Belief → {a['belief']}, {days_str})")
    else:
        print("  No anchors need decay.")

    # ── 2b. Fae bargain debts ─────────────────────────────────────────────────
    print("Checking fae bargains...")
    fae_lines = check_fae_bargains(dry_run=args.dry_run)
    if fae_lines:
        queue_lines.append("")
        queue_lines.append("*Fae debts coming due:*")
        queue_lines.extend(fae_lines)
        print(f"  ⚠ {len(fae_lines)} overdue fae bargain(s) — added to queue.")
    else:
        print("  No overdue fae bargains.")

    # ── 2c. Thread escalations ────────────────────────────────────────────────
    print("Checking thread phase shifts...")
    escalation_lines = check_thread_escalations(entities, dry_run=args.dry_run)
    if escalation_lines:
        queue_lines.append("")
        queue_lines.append("*Thread phase shifts:*")
        queue_lines.extend(escalation_lines)
        print(f"  {len(escalation_lines)} thread phase change(s) detected.")
    else:
        print("  No thread phase changes.")

    # ── 2d. Thread seeds ──────────────────────────────────────────────────────
    print("Checking thread seeds...")
    seed_lines = check_thread_seeds(entities, dry_run=args.dry_run)
    if seed_lines:
        queue_lines.append("")
        queue_lines.append("*Emerging thread seeds:*")
        queue_lines.extend(seed_lines)
        print(f"  {len(seed_lines)} thread seed(s) flagged.")
    else:
        print("  No new thread seeds.")

    # ── 3. Write queue ────────────────────────────────────────────────────────
    output = "\n".join(queue_lines) + "\n"

    if args.dry_run:
        print(f"\n[dry-run] Would append to tick-queue.md:")
        print(output)
        return

    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    with QUEUE.open('a') as f:
        f.write(output)
    print(f"✓ Tick queue updated.")


if __name__ == "__main__":
    main()

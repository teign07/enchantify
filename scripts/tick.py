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
REGISTER = BASE_DIR / "lore" / "world-register.md"
THREADS  = BASE_DIR / "lore" / "threads.md"
QUEUE    = BASE_DIR / "memory" / "tick-queue.md"

DECAY_THRESHOLD_DAYS   = 30
DECAY_AMOUNT           = 1
ANCHOR_FLOOR           = 5

INVESTMENT_CHANCE      = 0.25   # probability a stirred NPC invests per tick
INVESTMENT_MIN         = 1      # minimum Belief invested per event
INVESTMENT_MAX         = 3      # maximum Belief invested per event
NPC_INVESTMENT_FLOOR   = 8      # NPCs never drop below this from investing
TALISMAN_CAP           = 200    # Chapter Talismans can grow to 200


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
            'name': name,
            'type': etype.strip(),
            'belief': int(belief),
            'threads': threads,
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


# ── NPC Talisman Investment ───────────────────────────────────────────────────

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
        if dry_run:
            print(f"  [dry-run] {e['name']} → {talisman}: "
                  f"NPC {npc_b}→{new_npc_b}, Talisman {tal_b}→{new_tal_b}")

    return seeds, text


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
    """Format a single entity into a tick-queue line with optional location note."""
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

    # ── 1b. NPC Talisman Investments ──────────────────────────────────────────
    if selected:
        invest_seeds, modified_register = run_npc_talisman_investments(
            selected, register_text, dry_run=args.dry_run
        )
        if invest_seeds:
            queue_lines.append("")
            queue_lines.extend(invest_seeds)
            if not args.dry_run:
                backup = REGISTER.with_suffix(".md.bak")
                shutil.copy2(REGISTER, backup)
                tmp = REGISTER.with_suffix(".md.tmp")
                tmp.write_text(
                    modified_register if modified_register.endswith("\n")
                    else modified_register + "\n"
                )
                tmp.rename(REGISTER)
                print(f"✓ Talisman investments: {len(invest_seeds)} NPC(s) invested.")

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

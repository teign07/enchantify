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
from pathlib import Path
from datetime import datetime, date

BASE_DIR = Path(__file__).parent.parent
REGISTER = BASE_DIR / "lore" / "world-register.md"
QUEUE    = BASE_DIR / "memory" / "tick-queue.md"

DECAY_THRESHOLD_DAYS = 30
DECAY_AMOUNT         = 1
ANCHOR_FLOOR         = 5


# ── Entity tick ───────────────────────────────────────────────────────────────

def parse_entities(text):
    """Extract all entities with Belief scores from world-register.md."""
    entities = []

    row_re = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|", re.MULTILINE)
    for m in row_re.finditer(text):
        name, etype, belief = m.groups()
        name = name.strip()
        if name.lower() in ('entity', 'talisman', '---', ''):
            continue
        entities.append({'name': name, 'type': etype.strip(), 'belief': int(belief)})

    whisper_re = re.compile(r"^-\s+(.+?)\s*\((\w[\w\s]*?),\s*Belief\s+(\d+)\)", re.MULTILINE)
    for m in whisper_re.finditer(text):
        name, etype, belief = m.groups()
        entities.append({'name': name.strip(), 'type': etype.strip(), 'belief': int(belief)})

    return entities


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

def main():
    parser = argparse.ArgumentParser(description="World simulation tick")
    parser.add_argument('--count', type=int, default=None,
                        help='Number of entities to select (default: random 1-3)')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    queue_lines = [f"\n## Tick {timestamp}"]

    # ── 1. Entity tick ────────────────────────────────────────────────────────
    if not REGISTER.exists():
        print(f"❌ {REGISTER} not found.")
        return

    entities = parse_entities(REGISTER.read_text())
    if entities:
        n = args.count if args.count is not None else random.randint(1, 3)
        selected = weighted_sample(entities, n)
        for e in selected:
            queue_lines.append(f"- **{e['name']}** ({e['type']}, Belief {e['belief']})")
        if not args.dry_run:
            print(f"✓ Entity tick: {len(selected)} entr{'y' if len(selected) == 1 else 'ies'}")
            for e in selected:
                print(f"  - {e['name']} (Belief {e['belief']})")
    else:
        print("⚠ No entities found in world-register.md.")

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

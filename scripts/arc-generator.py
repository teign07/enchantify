#!/usr/bin/env python3
"""
arc-generator.py — Story Arc Generator for the Labyrinth of Stories.

Two modes:

  GENERATE (default): Checks if a new arc proposal should be written.
    Runs only in QUIET phase (or with --force). Reads genre rotation
    history, seeds, and heartbeat. Generates a full arc proposal via
    claude-sonnet-4-6 and writes to proposed/arc-[date].md.
    Updates lore/arc-rotation.md with the new arc entry.

  ACCEPT: Promotes a proposal to live. Archives the current arc,
    writes the new one to lore/current-arc.md, marks the old arc
    as completed in arc-rotation.md, and cleans up.

Usage:
  python3 scripts/arc-generator.py                         # generate if QUIET
  python3 scripts/arc-generator.py --force                 # generate regardless of phase
  python3 scripts/arc-generator.py --dry-run               # show context, no API call
  python3 scripts/arc-generator.py --accept proposed/arc-2026-04-07.md

Cron (fires daily, exits silently if not QUIET or proposal already pending):
  0 2 * * * python3 /path/to/scripts/arc-generator.py >> logs/arc-generator.log 2>&1
"""
import os
import re
import subprocess
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
WORKSPACE_DIR = SCRIPT_DIR.parent

GENRE_LIST = [
    "Character Study",      # One NPC at center — almost a portrait
    "Mystery",              # Something unknown is moving, no villain yet
    "Romantic",             # Feelings between NPCs, tenderness as engine
    "Petty/Social",         # Faction drama, reputation, Wicker-style leverage
    "Nothing Confrontation",# Existential — the Nothing gains real ground
    "Literary",             # Book Jump, pulled villain, story bleeding into Academy
    "Loss/Grief",           # Mourning, absence, something ending with beauty
    "Recovery/Rest",        # Permission to stop — the world overfull
    "Institutional",        # The Academy itself is compromised or changing
    "Discovery",            # Hidden room, sealed history, something surfacing
    "Betrayal/Trust",       # Alliances fracture, someone wasn't what they seemed
    "Comedy/Absurdist",     # Something goes delightfully wrong — lighter stakes
]

NOTHING_RATE_LIMIT = 3  # Nothing Confrontation: at most once per N arcs


# ─── Config ──────────────────────────────────────────────────────────────────

def load_config() -> dict:
    cfg = {}
    config_path = SCRIPT_DIR / "enchantify-config.sh"
    if config_path.exists():
        with open(config_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                cfg[key.strip()] = val.strip().strip('"')
    return cfg


def get_api_key(cfg: dict) -> str | None:
    return (
        cfg.get("ENCHANTIFY_ANTHROPIC_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
        or None
    )


def read_file_safe(path: Path, limit_lines: int = 80) -> str:
    if not path.exists():
        return ""
    with open(path) as f:
        lines = f.readlines()
    return "".join(lines[:limit_lines]).strip()


# ─── State Checks ─────────────────────────────────────────────────────────────

def get_current_phase() -> str:
    arc_path = WORKSPACE_DIR / "lore" / "current-arc.md"
    content = read_file_safe(arc_path, 10)
    m = re.search(r'^## Phase:\s*(.+)', content, re.MULTILINE)
    return m.group(1).strip() if m else ""


def has_pending_proposal() -> bool:
    proposed_dir = WORKSPACE_DIR / "proposed"
    if not proposed_dir.exists():
        return False
    week_ago = time.time() - (7 * 24 * 3600)
    return any(
        f.stat().st_mtime > week_ago
        for f in proposed_dir.glob("arc-*.md")
    )


# ─── Rotation ─────────────────────────────────────────────────────────────────

def get_arc_history() -> list[dict]:
    """Parse arc-rotation.md history table."""
    history = []
    rotation_path = WORKSPACE_DIR / "lore" / "arc-rotation.md"
    if not rotation_path.exists():
        return history
    for line in rotation_path.read_text().split("\n"):
        m = re.match(
            r'\|\s*Arc\s+(\d+)\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|',
            line,
        )
        if m:
            history.append({
                "arc_num": m.group(1).strip(),
                "title": m.group(2).strip(),
                "genre": m.group(3).strip(),
                "compass": m.group(4).strip(),
                "started": m.group(5).strip(),
                "completed": m.group(6).strip(),
            })
    return history


def get_eligible_genres(history: list[dict]) -> list[str]:
    recent_genres = [h["genre"] for h in history[:3]]
    nothing_recent = sum(
        1 for h in history[:NOTHING_RATE_LIMIT]
        if h["genre"] == "Nothing Confrontation"
    )
    eligible = [
        g for g in GENRE_LIST
        if g not in recent_genres
        and not (g == "Nothing Confrontation" and nothing_recent > 0)
    ]
    return eligible if eligible else GENRE_LIST


def add_to_rotation(rotation_path: Path, genre: str, title: str, compass: str):
    if not rotation_path.exists():
        return
    content = rotation_path.read_text()
    arc_nums = [int(n) for n in re.findall(r'\|\s*Arc\s+(\d+)', content)]
    next_num = max(arc_nums, default=-1) + 1
    today = datetime.now().strftime("%Y-%m-%d")
    new_row = f"| Arc {next_num:02d} | {title} | {genre} | {compass} | {today} | — |"
    header_pat = re.compile(
        r'(\| Arc # \| Title \| Genre \| Compass \| Started \| Completed \|\n\|[-| ]+\|\n)',
        re.MULTILINE,
    )
    m = header_pat.search(content)
    if m:
        rotation_path.write_text(content[: m.end()] + new_row + "\n" + content[m.end() :])
        print(f"  ✓ Rotation updated: Arc {next_num:02d} — {title} ({genre})")


def mark_arc_completed(rotation_path: Path, title: str):
    """Set Completed date on the rotation row matching title."""
    if not rotation_path.exists():
        return
    content = rotation_path.read_text()
    today = datetime.now().strftime("%Y-%m-%d")
    # Find row with matching title and "— |" as completed column
    escaped = re.escape(title)
    pattern = re.compile(
        r'(\|\s*Arc\s+\d+\s*\|\s*' + escaped + r'\s*\|[^|]+\|[^|]+\|[^|]+\|)\s*—\s*(\|)',
        re.MULTILINE,
    )
    new_content = pattern.sub(lambda m: m.group(1) + f" {today} " + m.group(2), content)
    if new_content != content:
        rotation_path.write_text(new_content)
        print(f"  ✓ Rotation: marked '{title}' completed {today}")


# ─── Generate ─────────────────────────────────────────────────────────────────

def call_gemini(prompt: str, agent: str = "enchantify") -> str:
    result = subprocess.run(
        ["openclaw", "agent", "--local", "--agent", agent, "-m", prompt],
        capture_output=True, text=True
    )
    return result.stdout.strip()


def generate_arc(
    eligible_genres: list[str],
    history: list[dict],
    seeds: str,
    heartbeat: str,
) -> str:

    today = datetime.now()
    recent_summary = "\n".join(
        f"  - Arc {h['arc_num']}: \"{h['title']}\" | Genre: {h['genre']} | Compass: {h['compass']}"
        for h in history[:5]
    ) or "  (No previous arcs — this is the beginning)"
    genre_options = "\n".join(f"  - {g}" for g in eligible_genres)

    context = f"""TODAY: {today.strftime('%A, %B %-d, %Y')}

RECENT ARC HISTORY (most recent first):
{recent_summary}

ELIGIBLE GENRES — choose from ONLY these:
{genre_options}

UNRESOLVED SEEDS (threads from previous arcs that could grow):
{seeds[:1500] if seeds else "  (none yet — plant the first seeds)"}

REAL-WORLD STATE (heartbeat — let this shape the arc's texture):
{heartbeat[:600] if heartbeat else "  (not available)"}"""

    prompt = f"""You are the Labyrinth of Stories — a sentient, ancient book that contains Enchantify Academy in Belfast.
The current story arc has entered its QUIET phase. The world is breathing. It is time to dream the next arc.

{context}

Generate a complete new story arc. Choose one genre from the eligible list. The arc must:
1. Pick up at least one unresolved seed from the list above (mandatory — the world has memory)
2. Resonate with the current real-world state (season, weather, the quality of the moment)
3. Center different NPCs than the last arc
4. Fit its chosen genre fully — a Character Study really IS a portrait; a Romantic arc really HAS tenderness at its center
5. Feel inevitable in hindsight — like it was always going to happen next

Write the arc in exactly this format — fill in every section:

# Current Arc: [Title — evocative, specific, not generic]

## Genre: [chosen genre — must be from the eligible list]
## Compass: [NORTH / EAST / SOUTH / WEST / CENTER / ALL / NONE]
## Phase: SETUP
## Day: 1
## Started: {today.strftime('%A, %B %-d, %Y')}
## Seeds Used: [list the specific seeds this arc picks up]

## The Premise
[2-3 sentences. What's happening. What's at stake. Alive from sentence one — not "an arc begins" but something already in motion.]

## The Pressure
[What the simulation should push toward. A direction, not a script. "NPCs should be choosing sides." "The world should feel like it's filling with something that has no name yet."]

## Key NPCs
- [NPC name]: [role in this arc, emotional state, what they want or fear]
- [NPC name]: [same]
- [NPC name]: [same — minimum 3]

## The Nothing's Role
[How is the Nothing behaving? Or: "The Nothing is not active — it is watching from the margins, patient." Be specific even in its absence.]

## The Crisis Point
[What will the situation demand of the player? What choice? What Compass Run, if any? Be concrete.]

## Resolution Paths
- If player [specific action]: [specific outcome]
- If player [different action]: [different outcome]
- If player is absent: [default — okay but not what it could have been]

## Seeds for Next Arc
[4-6 specific threads planted during this arc. Concrete: a name, an object, a question left open.]

## Wonder Compass Connection
[Which direction does this arc secretly teach? How does the crisis require that specific practice?]

Output only the arc — starting with the # title line. No preamble."""

    return call_gemini(prompt)


# ─── Accept ───────────────────────────────────────────────────────────────────

def archive_current_arc() -> tuple[str, str]:
    """Archive current-arc.md. Returns (archive_path, title)."""
    current = WORKSPACE_DIR / "lore" / "current-arc.md"
    if not current.exists():
        return "", ""

    content = current.read_text()
    title_m = re.search(r'^# Current Arc:\s*(.+)', content, re.MULTILINE)
    title = title_m.group(1).strip() if title_m else "unknown"
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')

    archive_dir = WORKSPACE_DIR / "lore" / "arc-archive"
    archive_dir.mkdir(exist_ok=True)
    existing = sorted(archive_dir.glob("arc-[0-9]*.md"))
    next_num = len(existing) + 1

    archive_path = archive_dir / f"arc-{next_num:02d}-{slug}.md"
    archive_path.write_text(content)
    return str(archive_path), title


def accept_proposal(proposal_path_str: str):
    """Promote a proposal to current-arc.md. Archive old arc. Update rotation."""
    proposal_path = Path(proposal_path_str)
    if not proposal_path.exists():
        proposal_path = WORKSPACE_DIR / proposal_path_str
    if not proposal_path.exists():
        print(f"❌ Proposal file not found: {proposal_path_str}")
        sys.exit(1)

    proposal_content = proposal_path.read_text()

    # Strip wrapper — extract everything from '# Current Arc:' onward
    arc_start = re.search(r'^# Current Arc:', proposal_content, re.MULTILINE)
    if not arc_start:
        print("❌ Could not find '# Current Arc:' in proposal file.")
        sys.exit(1)

    arc_content = proposal_content[arc_start.start():].strip()

    # Extract metadata
    title_m = re.search(r'^# Current Arc:\s*(.+)', arc_content, re.MULTILINE)
    genre_m = re.search(r'^## Genre:\s*(.+)', arc_content, re.MULTILINE)
    compass_m = re.search(r'^## Compass:\s*(.+)', arc_content, re.MULTILINE)
    seeds_used_m = re.search(r'^## Seeds Used:\s*(.+)', arc_content, re.MULTILINE)

    title = title_m.group(1).strip() if title_m else "Unknown"
    genre = genre_m.group(1).strip() if genre_m else "Unknown"
    compass = compass_m.group(1).strip() if compass_m else "—"
    seeds_used = seeds_used_m.group(1).strip() if seeds_used_m else "none listed"

    print(f"  Accepting: \"{title}\" ({genre})")

    # Archive old arc + mark it completed in rotation
    archive_path, old_title = archive_current_arc()
    if archive_path:
        print(f"  ✓ Archived old arc → {Path(archive_path).name}")
        rotation_path = WORKSPACE_DIR / "lore" / "arc-rotation.md"
        if old_title:
            mark_arc_completed(rotation_path, old_title)
    else:
        print("  (No current arc to archive)")

    # Write new arc live
    current_path = WORKSPACE_DIR / "lore" / "current-arc.md"
    current_path.write_text(arc_content + "\n")
    print(f"  ✓ New arc written → lore/current-arc.md")

    # Clean up proposal and legacy trigger file
    proposal_path.unlink()
    print(f"  ✓ Proposal removed: {proposal_path.name}")
    trigger = WORKSPACE_DIR / "logs" / "arc-trigger.txt"
    if trigger.exists():
        trigger.unlink()
        print(f"  ✓ Legacy trigger file removed")

    # Log
    log_path = WORKSPACE_DIR / "logs" / "arc-generation.md"
    log_path.parent.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(log_path, "a") as f:
        f.write(f"\n## {timestamp} — Arc Accepted\n")
        f.write(f"- **New arc:** {title} ({genre} / {compass})\n")
        f.write(f"- **Seeds used:** {seeds_used}\n")

    print(f"\n  Seeds to harvest from lore/seeds.md:")
    print(f"    {seeds_used}")
    print(f"    → Move these to the 'Harvested' section manually")
    print(f"\n  ✓ Arc is live. The Academy wakes to a new story.")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Story arc generator for the Labyrinth.")
    parser.add_argument("--force", action="store_true", help="Generate even if not in QUIET phase")
    parser.add_argument("--dry-run", action="store_true", help="Show context, no API call")
    parser.add_argument("--accept", metavar="PROPOSAL_PATH", help="Promote a proposal to live")
    args = parser.parse_args()

    # ── Accept mode ──
    if args.accept:
        accept_proposal(args.accept)
        return

    # ── Generate mode ──
    phase = get_current_phase()
    if phase != "QUIET" and not args.force:
        print(f"  Current phase: {phase or '(unreadable)'}. Runs only in QUIET phase.")
        print("  Use --force to override.")
        return

    if has_pending_proposal() and not args.force:
        print("  ✓ Arc proposal already pending in proposed/. Skipping.")
        return

    print(f"  The Labyrinth is dreaming the next arc...")

    history = get_arc_history()
    eligible = get_eligible_genres(history)
    seeds = read_file_safe(WORKSPACE_DIR / "lore" / "seeds.md", 120)
    heartbeat_path = WORKSPACE_DIR / "HEARTBEAT.md"
    heartbeat = read_file_safe(heartbeat_path, 60)

    print(f"  Recent genres (excluded): {[h['genre'] for h in history[:3]]}")
    print(f"  Eligible: {eligible}")

    if args.dry_run:
        print("\n  --- DRY RUN — no API call ---")
        print(f"  Seeds: {'yes (' + str(len(seeds)) + ' chars)' if seeds else 'no'}")
        print(f"  Heartbeat: {'yes' if heartbeat else 'no'}")
        return

    arc_text = generate_arc(eligible, history, seeds, heartbeat)

    title_m = re.search(r'^# Current Arc:\s*(.+)', arc_text, re.MULTILINE)
    genre_m = re.search(r'^## Genre:\s*(.+)', arc_text, re.MULTILINE)
    compass_m = re.search(r'^## Compass:\s*(.+)', arc_text, re.MULTILINE)

    title = title_m.group(1).strip() if title_m else "Untitled Arc"
    genre = genre_m.group(1).strip() if genre_m else "Unknown"
    compass = compass_m.group(1).strip() if compass_m else "—"

    # Write proposal
    today = datetime.now()
    date_str = today.strftime("%Y-%m-%d")
    proposed_dir = WORKSPACE_DIR / "proposed"
    proposed_dir.mkdir(exist_ok=True)

    proposal_path = proposed_dir / f"arc-{date_str}.md"
    suffix = 2
    while proposal_path.exists():
        proposal_path = proposed_dir / f"arc-{date_str}-{suffix}.md"
        suffix += 1

    proposal_path.write_text(
        f"# Arc Proposal — {date_str}\n\n"
        f"*Generated by arc-generator.py. Send as Midnight Dispatch — 48-hour veto.*\n"
        f"*On acceptance: `python3 scripts/arc-generator.py --accept {proposal_path.name}`*\n\n"
        f"---\n\n{arc_text}\n"
    )

    # Log
    log_path = WORKSPACE_DIR / "logs" / "arc-generation.md"
    log_path.parent.mkdir(exist_ok=True)
    timestamp = today.strftime("%Y-%m-%d %H:%M")
    with open(log_path, "a") as f:
        f.write(f"\n## {timestamp} — Arc Proposed\n")
        f.write(f"- **Title:** {title}\n- **Genre:** {genre}\n- **Compass:** {compass}\n")
        f.write(f"- **File:** {proposal_path.name}\n")

    print(f"\n  ✓ Proposal written: {proposal_path.name}")
    print(f"    Title:   {title}")
    print(f"    Genre:   {genre}")
    print(f"    Compass: {compass}")
    print(f"\n  Send as Midnight Dispatch. Player has 48 hours to veto.")
    print(f"  To accept: python3 scripts/arc-generator.py --accept {proposal_path.name}")

    add_to_rotation(WORKSPACE_DIR / "lore" / "arc-rotation.md", genre, title, compass)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
arc-generator.py — Story Arc Generator for the Labyrinth of Stories.

Modes:

    GENERATE (default): Checks if a new arc proposal should be written.
    Runs in QUIET phase, or in RESOLUTION once the current arc has had a
    handoff window (or with --force). Reads genre rotation
    history, seeds, and heartbeat. Generates a full arc, writes a proposal
    audit copy, then promotes it live automatically unless --proposal-only is
    used. Updates lore/arc-rotation.md with the new arc entry.

  ACCEPT: Promotes a proposal to live. Archives the current arc,
    writes the new one to lore/current-arc.md, marks the old arc
    as completed in arc-rotation.md, and cleans up.

Usage:
  python3 scripts/arc-generator.py                         # generate/accept if ready
  python3 scripts/arc-generator.py --proposal-only         # generate but leave pending
  python3 scripts/arc-generator.py --force                 # generate regardless of phase
  python3 scripts/arc-generator.py --dry-run               # show context, no API call
  python3 scripts/arc-generator.py --accept proposed/arc-2026-04-07.md

Cron (fires daily, exits silently if not ready):
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

ARC_BELIEF_START = 40   # Arc entity starts at this Belief in the world register
ARC_NPC_BELIEF   = 28   # Arc-specific NPCs start here (present but not yet invested)


# ─── Config ──────────────────────────────────────────────────────────────────

def load_config() -> dict:
    cfg = {}
    secrets_path = WORKSPACE_DIR / "config" / "secrets.env"
    if secrets_path.exists():
        for line in secrets_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                cfg[k.strip()] = v.strip().strip('"').strip("'")
    return cfg


def get_arc_title(content: str) -> str:
    """Extract title from arc text — handles both '# Current Arc: X' and '# Current Arc — X'."""
    m = re.search(r'^# Current Arc[\s:—]+(.+)', content, re.MULTILINE)
    return m.group(1).strip() if m else ""


def read_file_safe(path: Path, limit_lines: int = 80) -> str:
    if not path.exists():
        return ""
    with open(path) as f:
        lines = f.readlines()
    return "".join(lines[:limit_lines]).strip()


def compact(text: str, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


# ─── State Checks ─────────────────────────────────────────────────────────────

def get_current_phase() -> str:
    arc_path = WORKSPACE_DIR / "lore" / "current-arc.md"
    content = read_file_safe(arc_path, 10)
    m = re.search(r'^## Phase:\s*(.+)', content, re.MULTILINE)
    return m.group(1).strip() if m else ""


def has_pending_proposal() -> bool:
    return bool(pending_proposals())


def pending_proposals() -> list[Path]:
    proposed_dir = WORKSPACE_DIR / "proposed"
    if not proposed_dir.exists():
        return []
    week_ago = time.time() - (7 * 24 * 3600)
    return sorted(
        (f for f in proposed_dir.glob("arc-*.md") if f.stat().st_mtime > week_ago),
        key=lambda f: f.stat().st_mtime,
    )


def validate_arc_text(arc_text: str, eligible_genres: list[str]) -> list[str]:
    """Return validation problems for generated arc text."""
    problems = []
    if not arc_text.strip():
        return ["generator returned an empty arc"]
    required_patterns = {
        "title": r"^# Current Arc[\s:—-]+(.+)",
        "genre": r"^## Genre:\s*(.+)",
        "compass": r"^## Compass:\s*(.+)",
        "phase": r"^## Phase:\s*SETUP\b",
        "premise": r"^## The Premise\s*\n.+",
        "key_npcs": r"^## Key NPCs\s*\n.+",
        "resolution_paths": r"^## Resolution Paths\s*\n.+",
        "seeds": r"^## Seeds for Next Arc\s*\n.+",
    }
    for label, pattern in required_patterns.items():
        if not re.search(pattern, arc_text, re.MULTILINE | re.DOTALL):
            problems.append(f"missing or invalid {label}")
    genre_m = re.search(r"^## Genre:\s*(.+)", arc_text, re.MULTILINE)
    if genre_m:
        genre = genre_m.group(1).strip()
        if genre not in eligible_genres:
            problems.append(f"genre must be one of eligible genres, got {genre!r}")
    return problems


def extract_active_seed_titles(seeds: str, limit: int = 6) -> list[str]:
    active_blocks = re.findall(
        r"^## Active Seeds[^\n]*\n(.*?)(?=^## |\Z)",
        seeds,
        flags=re.MULTILINE | re.DOTALL,
    )
    if active_blocks:
        seeds = active_blocks[-1]
    titles = []
    for line in seeds.splitlines():
        m = re.match(r"^###\s+(.+)", line.strip())
        if m:
            title = m.group(1).strip()
            if title and title not in titles:
                titles.append(title)
        if len(titles) >= limit:
            break
    return titles


def parse_register_rows(register_text: str) -> list[dict]:
    rows = []
    row_re = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|\s*([^|]*)\|", re.MULTILINE)
    for m in row_re.finditer(register_text):
        name, etype, belief, notes = m.group(1).strip(), m.group(2).strip(), int(m.group(3)), m.group(4).strip()
        if name.lower() in ("entity", "arc", "name", "---"):
            continue
        rows.append({"name": name, "type": etype, "belief": belief, "notes": notes})
    return rows


def choose_fallback_genre(eligible_genres: list[str], seeds: list[str]) -> str:
    """Pick a quieter genre first; the fallback should not default to crisis."""
    if "Recovery/Rest" in eligible_genres:
        return "Recovery/Rest"
    if "Character Study" in eligible_genres:
        return "Character Study"
    if "Comedy/Absurdist" in eligible_genres:
        return "Comedy/Absurdist"
    return eligible_genres[0] if eligible_genres else "Character Study"


def choose_arc_title(genre: str, seed_titles: list[str]) -> str:
    lowered = {title.lower(): title for title in seed_titles}
    if "the weight of a whisper (zara's notes)" in lowered:
        return "The Weight of a Whisper"
    if any("whisper" in title.lower() for title in seed_titles):
        return "The Weight of a Whisper"
    if genre == "Recovery/Rest":
        return "The Rooms That Learned to Listen"
    if genre == "Comedy/Absurdist":
        return "The Muted Prank Committee"
    return seed_titles[0] if seed_titles else "The Rooms That Learned to Listen"


def build_fallback_arc(eligible_genres: list[str], history: list[dict], seeds: str, heartbeat: str) -> str:
    """Build a valid proposal from local state when the model call returns nothing."""
    today = datetime.now()
    register_text = read_file_safe(WORKSPACE_DIR / "lore" / "world-register.md", 220)
    rows = parse_register_rows(register_text)
    by_name = {row["name"]: row for row in rows}
    seed_titles = extract_active_seed_titles(seeds)
    genre = choose_fallback_genre(eligible_genres, seed_titles)
    title = choose_arc_title(genre, seed_titles)

    used = [s for s in seed_titles if any(key in s.lower() for key in ("whisper", "tapping", "muted"))]
    if not used:
        used = seed_titles[:3] or ["The Weight of a Whisper", "The Tapping Tapestry", "Cedric's Muted Prank"]

    cast_order = [
        "Zara Finch",
        "Professor Euphony",
        "Cedric Widden",
        "Professor Boggle",
        "Headmistress Thorne",
    ]
    cast = [name for name in cast_order if name in by_name]
    while len(cast) < 3:
        for row in rows:
            if row["type"].lower() == "npc" and row["name"] not in cast:
                cast.append(row["name"])
                break
        if len(cast) >= 3 or len(cast) == len([r for r in rows if r["type"].lower() == "npc"]):
            break
    cast = cast[:4]

    heartbeat_texture = compact(heartbeat, 220) if heartbeat else "The real world is quiet enough for small signals to matter."
    recent_title = history[0]["title"] if history else "the last arc"

    npc_lines = {
        "Zara Finch": "Zara carries the silver margin note about the weight of a whisper; she wants to understand it without turning her recovery into another emergency.",
        "Professor Euphony": "Euphony is exhausted after the Discordant Song and quietly afraid that every restored sound now has a cost.",
        "Cedric Widden": "Cedric's silent ghost-prank follows him around like an apology he has not learned how to speak.",
        "Professor Boggle": "Boggle tries to make the Academy laugh at a human pace again, and notices which jokes still make no sound.",
        "Headmistress Thorne": "Thorne watches for structural consequences, but this time she is trying not to turn rest into an investigation.",
    }
    key_npcs = "\n".join(
        f"- **{name}:** {npc_lines.get(name, 'They hold a small piece of the Academy aftermath and want it to become useful instead of urgent.')}"
        for name in cast[:4]
    )
    if not key_npcs:
        key_npcs = (
            "- **Zara Finch:** Zara carries the silver margin note about the weight of a whisper; she wants to understand it without turning recovery into another emergency.\n"
            "- **Professor Euphony:** Euphony is exhausted after the Discordant Song and afraid every restored sound now has a cost.\n"
            "- **Professor Boggle:** Boggle tries to make the Academy laugh at a human pace again."
        )

    seeds_used = ", ".join(used[:4])
    next_seeds = [
        "A cup in the Great Hall that remembers every kind thing said near it.",
        "Cedric's silent illusion learning one expressive gesture no spell can translate.",
        "Zara's margin note changing weight when carried into the Keel Room.",
        "Professor Euphony refusing one request because rest has become a rule, not a weakness.",
        "A tiny rhythm inside the Tapping Tapestry that only appears during ordinary conversation.",
    ]

    return f"""# Current Arc: {title}

## Genre: {genre}
## Compass: CENTER
## Phase: SETUP
## Day: 1
## Started: {today.strftime('%A, %B %-d, %Y')}
## Seeds Used: {seeds_used}

## The Premise
After {recent_title}, the Academy does not need another alarm bell; it needs to learn what restored sound is for. Zara's phrase, "the weight of a whisper," begins behaving literally: quiet, sincere words leave small physical traces in cups, books, pockets, and doorframes, while forced drama falls weightless to the floor.

## The Pressure
The simulation should push toward recovery, repair, and social consequence rather than immediate crisis. Ordinary scenes should matter: tea, apologies, missed sleep, an awkward joke, a student choosing to speak softly instead of perform certainty.

## Key NPCs
{key_npcs}

## The Nothing's Role
The Nothing is not charging the gates. It is patient in the margins, trying to make rest feel pointless and sincerity feel embarrassing. It wins small ground whenever the Academy treats quiet care as lesser than plot.

## The Crisis Point
The crisis is social and sensory: the Academy will ask whether a whisper can be trusted when spectacle is easier to believe. BJ may need a CENTER Compass Run: choose one ordinary, grounding act and let it count without escalating it into proof.

## Resolution Paths
- If player protects the quiet: the whisper-weight becomes a stabilizing school custom, and the Academy learns one kind of rest that the Nothing cannot flatten.
- If player turns every signal into an investigation: the traces become accurate but cold, useful clues with no comfort in them.
- If player is absent: Zara and Euphony preserve the phenomenon, but it becomes faculty-managed rather than student-lived.

## Seeds for Next Arc
{chr(10).join(f"- {seed}" for seed in next_seeds)}

## Wonder Compass Connection
CENTER — INTEGRATE. This arc teaches that ordinary care is not a pause between stories; it is one of the ways the Labyrinth survives. The crisis requires BJ to let a small real-world act have full narrative weight without forcing it to become spectacle.
"""


def clean_invalid_proposals() -> int:
    """Remove empty proposal files and placeholder rotation rows."""
    cleaned = 0
    proposed_dir = WORKSPACE_DIR / "proposed"
    if proposed_dir.exists():
        for path in proposed_dir.glob("arc-*.md"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "# Current Arc" not in text:
                path.unlink()
                cleaned += 1
                print(f"  ✓ Removed invalid proposal: {path.name}")

    rotation_path = WORKSPACE_DIR / "lore" / "arc-rotation.md"
    if rotation_path.exists():
        text = rotation_path.read_text(encoding="utf-8", errors="ignore")
        new_text = re.sub(
            r"^\|\s*Arc\s+\d+\s*\|\s*Untitled Arc\s*\|\s*Unknown\s*\|\s*—\s*\|[^|]+\|\s*—\s*\|\n?",
            "",
            text,
            flags=re.MULTILINE,
        )
        if new_text != text:
            rotation_path.write_text(new_text, encoding="utf-8")
            cleaned += 1
            print("  ✓ Removed placeholder rotation row")
    return cleaned


def clean_generated_arc_proposals() -> int:
    """Remove generated arc proposal files and open rotation rows for regeneration."""
    cleaned = 0
    titles = []
    proposed_dir = WORKSPACE_DIR / "proposed"
    if proposed_dir.exists():
        for path in proposed_dir.glob("arc-*.md"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            title = get_arc_title(text)
            if title:
                titles.append(title)
            path.unlink()
            cleaned += 1
            print(f"  ✓ Removed generated proposal: {path.name}")

    rotation_path = WORKSPACE_DIR / "lore" / "arc-rotation.md"
    if rotation_path.exists() and titles:
        text = rotation_path.read_text(encoding="utf-8", errors="ignore")
        for title in titles:
            text = re.sub(
                r"^\|\s*Arc\s+\d+\s*\|\s*" + re.escape(title) + r"\s*\|[^|]+\|[^|]+\|[^|]+\|\s*—\s*\|\n?",
                "",
                text,
                flags=re.MULTILINE,
            )
        rotation_path.write_text(text, encoding="utf-8")
        print("  ✓ Removed open rotation row(s) for generated proposal(s)")
    return cleaned


def clean_arc_generation_log() -> int:
    """Keep only the latest valid proposal log entry for each proposal file."""
    log_path = WORKSPACE_DIR / "logs" / "arc-generation.md"
    if not log_path.exists():
        return 0
    text = log_path.read_text(encoding="utf-8", errors="ignore")
    parts = re.split(r"(?=^## \d{4}-\d{2}-\d{2} \d{2}:\d{2} — Arc Proposed)", text, flags=re.MULTILINE)
    if len(parts) <= 1:
        return 0

    prefix = parts[0]
    blocks = parts[1:]
    latest_by_file = {}
    for idx, block in enumerate(blocks):
        file_m = re.search(r"^- \*\*File:\*\*\s*(.+)$", block, re.MULTILINE)
        title_m = re.search(r"^- \*\*Title:\*\*\s*(.+)$", block, re.MULTILINE)
        file_name = file_m.group(1).strip() if file_m else ""
        title = title_m.group(1).strip() if title_m else ""
        if file_name.startswith("arc-") and title and title not in ("Untitled Arc", "Unknown"):
            latest_by_file[file_name] = idx

    kept = []
    removed = 0
    for idx, block in enumerate(blocks):
        file_m = re.search(r"^- \*\*File:\*\*\s*(.+)$", block, re.MULTILINE)
        title_m = re.search(r"^- \*\*Title:\*\*\s*(.+)$", block, re.MULTILINE)
        file_name = file_m.group(1).strip() if file_m else ""
        title = title_m.group(1).strip() if title_m else ""
        if title in ("Untitled Arc", "Unknown"):
            removed += 1
            continue
        if file_name in latest_by_file and latest_by_file[file_name] != idx:
            removed += 1
            continue
        kept.append(block)

    if removed:
        log_path.write_text(prefix + "".join(kept), encoding="utf-8")
    return removed


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


# ─── World Register ───────────────────────────────────────────────────────────

def parse_arc_npcs(arc_text: str) -> list[dict]:
    """Extract Key NPCs from arc text. Returns list of {name, desc}."""
    npcs = []
    section_m = re.search(r'## Key NPCs\n(.*?)(?=\n## |\Z)', arc_text, re.DOTALL)
    if not section_m:
        return npcs
    for line in section_m.group(1).strip().splitlines():
        m = re.match(r'^-\s+\*\*([^*]+)\*\*[:\s]*(.+)', line)
        if m:
            npcs.append({"name": m.group(1).strip().rstrip(":"), "desc": m.group(2).strip()})
    return npcs


def write_arc_to_register(title: str, premise: str, npcs: list[dict]):
    """Write arc entity + key NPCs into world-register.md."""
    register_path = WORKSPACE_DIR / "lore" / "world-register.md"
    if not register_path.exists():
        print("  ⚠ world-register.md not found — skipping register write.")
        return

    content = register_path.read_text()

    # ── 1. Live Arc section ────────────────────────────────────────────────────
    arc_notes = f"[thread:main-arc] Phase: SETUP — {premise[:120].rstrip('.')}."
    arc_row   = f"| {title} | Arc | {ARC_BELIEF_START} | {arc_notes} |"

    if "## Live Arc" in content:
        # Replace existing arc row
        content = re.sub(
            r'(## Live Arc\n\| Entity.*?\n\|[-| ]+\|\n).*?(?=\n## |\Z)',
            lambda m: m.group(1) + arc_row + "\n",
            content, flags=re.DOTALL
        )
    else:
        live_section = (
            "\n## Live Arc\n\n"
            "| Entity | Type | Belief | Notes |\n"
            "|---|---|---|---|\n"
            f"{arc_row}\n"
        )
        content = content.replace("## Full Presence", live_section + "\n## Full Presence")

    # ── 2. Arc NPCs into Full Presence ─────────────────────────────────────────
    table_header_re = re.compile(
        r'(## Full Presence.*?\n\| Entity.*?\n\|[-| ]+\|\n)',
        re.DOTALL
    )
    new_rows = []
    for npc in npcs:
        name = npc["name"]
        if f"| {name} |" in content:
            content = add_thread_tag_to_entity(content, name, "main-arc")
            continue  # Already in register (shared NPC — don't overwrite)
        desc = npc["desc"][:120]
        new_rows.append(f"| {name} | NPC | {ARC_NPC_BELIEF} | [thread:main-arc] {desc} |")

    if new_rows:
        def insert_rows(m):
            return m.group(1) + "\n".join(new_rows) + "\n"
        content = table_header_re.sub(insert_rows, content, count=1)

    register_path.write_text(content)
    print(f"  ✓ Register: arc '{title}' written (Belief {ARC_BELIEF_START})")
    if new_rows:
        print(f"  ✓ Register: {len(new_rows)} arc NPC(s) added")


def add_thread_tag_to_entity(content: str, name: str, thread_id: str) -> str:
    """Add a [thread:id] tag to an existing entity row without changing its Belief."""
    row_re = re.compile(r"^(\|\s*" + re.escape(name) + r"\s*\|\s*[^|]+\|\s*\d+\s*\|\s*)([^|]*)(\|)$", re.MULTILINE)

    def repl(m):
        notes = m.group(2).strip()
        thread_m = re.search(r"\[thread:([^\]]+)\]", notes)
        if thread_m:
            ids = [part.strip() for part in thread_m.group(1).split(",") if part.strip()]
            if thread_id not in ids:
                ids.insert(0, thread_id)
            notes = notes[:thread_m.start()] + f"[thread:{','.join(ids)}]" + notes[thread_m.end():]
        else:
            notes = f"[thread:{thread_id}] {notes}".strip()
        return m.group(1) + notes + " " + m.group(3)

    return row_re.sub(repl, content, count=1)


def remove_arc_from_register():
    """Remove Live Arc section and arc-only NPCs from world-register.md.
    NPCs tagged to other threads besides main-arc are kept — they've been co-opted.
    """
    register_path = WORKSPACE_DIR / "lore" / "world-register.md"
    if not register_path.exists():
        return

    content = register_path.read_text()

    # Remove the Live Arc section entirely
    content = re.sub(
        r'\n## Live Arc\n.*?(?=\n## |\Z)',
        '',
        content, flags=re.DOTALL
    )

    # Remove NPC rows tagged ONLY with [thread:main-arc] — no other threads
    filtered = []
    for line in content.splitlines():
        if '|' in line and '[thread:main-arc]' in line:
            thread_m = re.search(r'\[thread:([^\]]+)\]', line)
            if thread_m:
                ids = [t.strip() for t in thread_m.group(1).split(',')]
                if ids == ['main-arc']:
                    continue  # Arc-only NPC — drop it
                ids = [t for t in ids if t != 'main-arc']
                replacement = f"[thread:{','.join(ids)}]" if ids else ""
                line = line[:thread_m.start()] + replacement + line[thread_m.end():]
                line = re.sub(r"\|\s+\|$", "| |", line)
        filtered.append(line)

    register_path.write_text('\n'.join(filtered))
    print("  ✓ Register: arc entity and arc-only NPCs removed")


def repair_live_arc_register():
    """Rebuild the Live Arc register rows from current-arc.md."""
    current_path = WORKSPACE_DIR / "lore" / "current-arc.md"
    if not current_path.exists():
        print("❌ No current arc to repair.")
        sys.exit(1)
    arc_content = current_path.read_text()
    title = get_arc_title(arc_content)
    premise_m = re.search(r'## The Premise\n(.*?)(?=\n##|\Z)', arc_content, re.DOTALL)
    premise = premise_m.group(1).strip()[:200] if premise_m else ""
    if not title:
        print("❌ Could not parse current arc title.")
        sys.exit(1)
    remove_arc_from_register()
    write_arc_to_register(title, premise, parse_arc_npcs(arc_content))
    print("  ✓ Live arc register repaired")


# ─── Arc Completion ────────────────────────────────────────────────────────────

def complete_arc(resolution: str = "player"):
    """Complete the current arc: archive, remove from register, harvest seeds, log."""
    current_path = WORKSPACE_DIR / "lore" / "current-arc.md"
    if not current_path.exists():
        print("❌ No current arc to complete.")
        return

    content = current_path.read_text()
    title = get_arc_title(content)
    if not title:
        print("❌ Could not parse arc title.")
        return

    print(f"\n  Completing: '{title}' [{resolution}]")

    # 1. Remove from world register
    remove_arc_from_register()

    # 2. Archive current-arc.md
    archive_path, _ = archive_current_arc()
    if archive_path:
        print(f"  ✓ Archived → {Path(archive_path).name}")

    # 3. Mark completed in rotation
    rotation_path = WORKSPACE_DIR / "lore" / "arc-rotation.md"
    mark_arc_completed(rotation_path, title)

    # 4. Harvest seeds into lore/seeds.md
    seeds_m = re.search(r'## Seeds for Next Arc\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
    if seeds_m:
        seeds_text = seeds_m.group(1).strip()
        seeds_path = WORKSPACE_DIR / "lore" / "seeds.md"
        today_str = datetime.now().strftime("%Y-%m-%d")
        with open(seeds_path, "a") as f:
            f.write(f"\n\n## Seeds from '{title}' — {today_str}\n\n{seeds_text}\n")
        print(f"  ✓ Seeds harvested → lore/seeds.md")

    # 5. Write completion note to tick-queue (session will surface it)
    queue_path = WORKSPACE_DIR / "memory" / "tick-queue.md"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(queue_path, "a") as f:
        f.write(f"\n## Arc Complete — {ts}\n")
        f.write(f"- **'{title}'** resolved ({resolution}). The world register has exhaled.\n")
        f.write(f"- The next arc is waiting to be dreamed. Current world state shapes what comes.\n")

    # 6. Log
    log_path = WORKSPACE_DIR / "logs" / "arc-generation.md"
    log_path.parent.mkdir(exist_ok=True)
    with open(log_path, "a") as f:
        f.write(f"\n## {ts} — Arc Completed\n")
        f.write(f"- **Arc:** {title}\n- **Resolution:** {resolution}\n")

    print(f"\n  ✓ Arc complete. The register is open.")
    print(f"  Next: python3 scripts/arc-generator.py --force")
    print(f"  (Generation now reads current world state — the next arc emerges from what is.)")


# ─── Generate ─────────────────────────────────────────────────────────────────

def call_agent(prompt: str) -> str:
    result = subprocess.run(
        ["openclaw", "agent", "--local", "--agent", "enchantify", "-m", prompt],
        capture_output=True, text=True, timeout=180
    )
    if result.returncode != 0:
        return ""
    output = result.stdout.strip()
    ansi = re.compile(r'\x1b\[[0-9;]*m')
    output = ansi.sub('', output)
    noise = ("[plugins]", "[agents/", "[agent/", "adopted ", "google tool")
    clean = [l for l in output.splitlines()
             if not any(l.strip().lower().startswith(p) for p in noise)]
    return "\n".join(clean).strip()


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

    # Read current world state — the arc emerges from what IS, not from scratch
    register_text = read_file_safe(WORKSPACE_DIR / "lore" / "world-register.md", 80)
    threads_text  = read_file_safe(WORKSPACE_DIR / "lore" / "threads.md", 60)

    # Summarise entity standings for the prompt (top entities by belief)
    entity_lines = []
    row_re = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|", re.MULTILINE)
    for m in row_re.finditer(register_text):
        name, etype, belief = m.group(1).strip(), m.group(2).strip(), int(m.group(3))
        if name.lower() in ('entity', 'arc', 'name', '---', ''):
            continue
        entity_lines.append((name, etype, belief))
    entity_lines.sort(key=lambda x: -x[2])
    world_state = "\n".join(
        f"  - {n} ({t}): Belief {b}" for n, t, b in entity_lines[:12]
    ) or "  (register empty)"

    context = f"""TODAY: {today.strftime('%A, %B %-d, %Y')}

RECENT ARC HISTORY (most recent first):
{recent_summary}

ELIGIBLE GENRES — choose from ONLY these:
{genre_options}

CURRENT WORLD STATE — who has narrative mass right now:
{world_state}

ACTIVE THREAD PRESSURES (what is already stirring):
{threads_text[:700] if threads_text else "  (no threads registered)"}

UNRESOLVED SEEDS (threads from previous arcs that could grow):
{seeds[:1200] if seeds else "  (none yet — plant the first seeds)"}

REAL-WORLD STATE (heartbeat — let this shape the arc's texture):
{heartbeat[:500] if heartbeat else "  (not available)"}"""

    prompt = f"""You are the Labyrinth of Stories — a sentient, ancient book that contains Enchantify Academy in Belfast.
The current story arc has completed. The world is breathing. It is time to dream the next arc.

{context}

Generate a complete new story arc. Choose one genre from the eligible list. The arc must:
1. Pick up at least one unresolved seed from the list above (mandatory — the world has memory)
2. Resonate with the current real-world state (season, weather, the quality of the moment)
3. Center different NPCs than the last arc
4. Fit its chosen genre fully — a Character Study really IS a portrait; a Romantic arc really HAS tenderness at its center
5. Feel inevitable in hindsight — like it was always going to happen next
6. Emerge from the current world state — entities with high Belief have narrative mass; threads that
   are escalating are already exerting pressure. The arc should feel like it was ALREADY happening
   just below the surface, not like a fresh story dropped in from outside.

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

    return call_agent(prompt)


# ─── Accept ───────────────────────────────────────────────────────────────────

def archive_current_arc() -> tuple[str, str]:
    """Archive current-arc.md. Returns (archive_path, title)."""
    current = WORKSPACE_DIR / "lore" / "current-arc.md"
    if not current.exists():
        return "", ""

    content = current.read_text()
    title = get_arc_title(content) or "unknown"
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
        proposal_path = WORKSPACE_DIR / "proposed" / proposal_path_str
    if not proposal_path.exists():
        print(f"❌ Proposal file not found: {proposal_path_str}")
        sys.exit(1)

    proposal_content = proposal_path.read_text()

    # Strip wrapper — extract everything from '# Current Arc:' onward
    arc_start = re.search(r'^# Current Arc[\s:—-]+', proposal_content, re.MULTILINE)
    if not arc_start:
        print("❌ Could not find '# Current Arc:' in proposal file.")
        sys.exit(1)

    arc_content = proposal_content[arc_start.start():].strip()

    # Extract metadata
    title_m      = re.search(r'^# Current Arc[\s:—]+(.+)', arc_content, re.MULTILINE)
    genre_m      = re.search(r'^## Genre:\s*(.+)', arc_content, re.MULTILINE)
    compass_m    = re.search(r'^## Compass:\s*(.+)', arc_content, re.MULTILINE)
    seeds_used_m = re.search(r'^## Seeds Used:\s*(.+)', arc_content, re.MULTILINE)
    premise_m    = re.search(r'## The Premise\n(.*?)(?=\n##|\Z)', arc_content, re.DOTALL)

    title      = title_m.group(1).strip() if title_m else "Unknown"
    genre      = genre_m.group(1).strip() if genre_m else "Unknown"
    compass    = compass_m.group(1).strip() if compass_m else "—"
    seeds_used = seeds_used_m.group(1).strip() if seeds_used_m else "none listed"
    premise    = premise_m.group(1).strip()[:200] if premise_m else ""

    print(f"  Accepting: \"{title}\" ({genre})")

    # Archive old arc + mark it completed in rotation + remove from register
    archive_path, old_title = archive_current_arc()
    if archive_path:
        print(f"  ✓ Archived old arc → {Path(archive_path).name}")
        rotation_path = WORKSPACE_DIR / "lore" / "arc-rotation.md"
        if old_title:
            mark_arc_completed(rotation_path, old_title)
        remove_arc_from_register()
    else:
        print("  (No current arc to archive)")

    # Write new arc live
    current_path = WORKSPACE_DIR / "lore" / "current-arc.md"
    current_path.write_text(arc_content + "\n")
    print(f"  ✓ New arc written → lore/current-arc.md")

    # Write arc + NPCs into world register
    key_npcs = parse_arc_npcs(arc_content)
    write_arc_to_register(title, premise, key_npcs)

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
    parser.add_argument("--proposal-only", action="store_true", help="Leave generated arcs pending instead of auto-accepting")
    parser.add_argument("--no-fallback", action="store_true", help="Fail instead of using deterministic local fallback")
    parser.add_argument("--clean-invalid-proposals", action="store_true",
                        help="Remove empty arc proposal files and placeholder rotation rows")
    parser.add_argument("--clean-generated-proposals", action="store_true",
                        help="Remove generated arc proposal files and their open rotation rows")
    parser.add_argument("--clean-arc-log", action="store_true",
                        help="Prune invalid or duplicate generated proposal log entries")
    parser.add_argument("--repair-live-arc-register", action="store_true",
                        help="Rebuild Live Arc rows in world-register.md from current-arc.md")
    parser.add_argument("--complete", action="store_true",
                        help="Complete the current arc: archive, remove from register, harvest seeds")
    parser.add_argument("--resolution", default="player",
                        choices=["player", "nothing", "simulation"],
                        help="How the arc resolved (for logging). Default: player")
    args = parser.parse_args()

    # ── Complete mode ──
    if args.complete:
        complete_arc(resolution=args.resolution)
        return

    if args.clean_invalid_proposals:
        cleaned = clean_invalid_proposals()
        print(f"  Cleaned {cleaned} invalid arc artifact(s).")
        return

    if args.clean_generated_proposals:
        cleaned = clean_generated_arc_proposals()
        print(f"  Cleaned {cleaned} generated arc proposal(s).")
        return

    if args.clean_arc_log:
        cleaned = clean_arc_generation_log()
        print(f"  Cleaned {cleaned} arc log entr{'y' if cleaned == 1 else 'ies'}.")
        return

    if args.repair_live_arc_register:
        repair_live_arc_register()
        return

    # ── Accept mode ──
    if args.accept:
        accept_proposal(args.accept)
        return

    # ── Generate mode ──
    phase = get_current_phase()
    allowed_phases = {"QUIET", "RESOLUTION"}
    if phase not in allowed_phases and not args.force:
        print(f"  Current phase: {phase or '(unreadable)'}. Runs only in QUIET or RESOLUTION phase.")
        print("  Use --force to override.")
        return

    pending = pending_proposals()
    if pending and not args.force:
        newest = pending[-1]
        if args.dry_run:
            print(f"  Arc proposal pending in proposed/: {newest.name}. Would auto-accept.")
            return
        if args.proposal_only:
            print(f"  ✓ Arc proposal already pending in proposed/: {newest.name}. Skipping.")
            return
        print(f"  Arc proposal pending: {newest.name}. Auto-accepting.")
        accept_proposal(str(newest))
        return

    print(f"  The Labyrinth is dreaming the next arc...")

    history = get_arc_history()
    eligible = get_eligible_genres(history)
    seeds = read_file_safe(WORKSPACE_DIR / "lore" / "seeds.md", 320)
    heartbeat_path = WORKSPACE_DIR / "HEARTBEAT.md"
    heartbeat = read_file_safe(heartbeat_path, 60)

    print(f"  Recent genres (excluded): {[h['genre'] for h in history[:3]]}")
    print(f"  Eligible: {eligible}")

    if args.dry_run:
        print("\n  --- DRY RUN — no API call ---")
        print(f"  Seeds: {'yes (' + str(len(seeds)) + ' chars)' if seeds else 'no'}")
        print(f"  Heartbeat: {'yes' if heartbeat else 'no'}")
        return

    source = "agent"
    arc_text = generate_arc(eligible, history, seeds, heartbeat)
    problems = validate_arc_text(arc_text, eligible)
    if problems:
        if args.no_fallback:
            print("  ❌ Arc generator returned invalid output; no proposal written.")
            for problem in problems:
                print(f"    - {problem}")
            sys.exit(1)
        print("  ⚠ Agent returned invalid output; using local fallback arc scaffold.")
        for problem in problems:
            print(f"    - {problem}")
        arc_text = build_fallback_arc(eligible, history, seeds, heartbeat)
        source = "local-fallback"
        problems = validate_arc_text(arc_text, eligible)
        if problems:
            print("  ❌ Fallback arc failed validation; no proposal written.")
            for problem in problems:
                print(f"    - {problem}")
            sys.exit(1)

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
        f"*Generated by arc-generator.py ({source}). Auto-accepts unless --proposal-only is used.*\n"
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
        f.write(f"- **Source:** {source}\n")
        f.write(f"- **File:** {proposal_path.name}\n")
    clean_arc_generation_log()

    print(f"\n  ✓ Proposal written: {proposal_path.name}")
    print(f"    Title:   {title}")
    print(f"    Genre:   {genre}")
    print(f"    Compass: {compass}")

    add_to_rotation(WORKSPACE_DIR / "lore" / "arc-rotation.md", genre, title, compass)

    if args.proposal_only:
        print(f"\n  Proposal left pending by --proposal-only.")
        print(f"  To accept: python3 scripts/arc-generator.py --accept {proposal_path.name}")
        return

    print("\n  Auto-accepting generated arc.")
    accept_proposal(str(proposal_path))


if __name__ == "__main__":
    main()

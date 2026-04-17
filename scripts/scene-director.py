#!/usr/bin/env python3
"""
scene-director.py — 7-Layer Weight Stack synthesizer.

Reads all narrative weight layers and outputs a compact Director's Slate.
Pure Python — no LLM call. Purpose: synthesize 500+ lines of state into directive
lines the Labyrinth will actually attend to (solving "lost in the middle" dilution).

SLATE FORMAT (up to 11 lines; RESEARCH/SCENE_ANCHOR only appear when set):
  SCENE_ANCHOR — (if set) exact image/beat to open from; mandatory first-line source
  CAST         — who's stirred, where, disposition
  FEEL         — weather/mood → atmosphere translation
  STORY        — arc phase + what the story is ready for
  TALISMAN     — leading talisman's soft scene philosophy
  NOTHING      — pressure level + strategy + target + engagement gap
  RESEARCH     — (optional) NPC research notes from last 2 days
  PLAYER       — belief, trajectory, alive vs flat
  SCHEDULE     — current time block, class in session, what's up next
  DREAM        — diary/dream fragment bleeding into today
  SUPPRESS     — what NOT to do (from flat patterns + arc phase + nothing strategy)

Usage:
  python3 scripts/scene-director.py [player_name]
  python3 scripts/scene-director.py [player_name] --slate-only   # no header/footer
  python3 scripts/scene-director.py [player_name] --layer N      # debug single layer

Called by:
  session-entry.py  — appended after SCHEDULE CONTEXT block
  world-pulse.py    — on scene change (Scene Change Pulse)
"""

import os
import re
import sys
import json
from datetime import datetime, date, timedelta
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent
WORKSPACE   = _SCRIPT_DIR.parent

# ── Import schedule module ─────────────────────────────────────────────────────

sys.path.insert(0, str(_SCRIPT_DIR))
try:
    from schedule import get_schedule_data, WEEKDAY_NAMES
    _SCHEDULE_OK = True
except ImportError:
    _SCHEDULE_OK = False

try:
    import npc_log as _npc_log
    _HAS_NPC_LOG = True
except ImportError:
    _HAS_NPC_LOG = False


# ── Helpers ────────────────────────────────────────────────────────────────────

def read_safe(path: Path, limit: int = 0) -> str:
    """Read a file safely; return empty string if missing."""
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8").strip()
    if limit:
        return "\n".join(text.splitlines()[:limit])
    return text


def first_match(pattern: str, text: str, flags=0, group=1, default="") -> str:
    m = re.search(pattern, text, flags)
    return m.group(group).strip() if m else default


def latest_file(directory: Path, glob: str = "*.md") -> Path:
    """Return the most recently named file matching glob (by filename sort, not mtime)."""
    files = sorted(directory.glob(glob))
    return files[-1] if files else Path("/dev/null")


def truncate(s: str, n: int = 120) -> str:
    return s[:n] + "…" if len(s) > n else s


# ── Layer 1: WHO ───────────────────────────────────────────────────────────────

def layer_who() -> str:
    """
    Read NPC table from academy-state.md + tick-queue.md.
    Return: compact list of stirred/notable NPCs with location and disposition.
    """
    state_text   = read_safe(WORKSPACE / "lore" / "academy-state.md", 100)
    queue_text   = read_safe(WORKSPACE / "memory" / "tick-queue.md", 40)

    # NPC table rows from academy-state.md
    # Format: | Name | Chapter | Location | Mood | Current Goal | Notes |
    npc_re = re.compile(
        r'^\|\s*\*\*([^*|]+)\*\*\s*\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|',
        re.MULTILINE
    )
    npcs = []
    for m in npc_re.finditer(state_text):
        name, _chapter, location, mood, goal, notes = [g.strip() for g in m.groups()]
        stirred = "(STIRRED)" in notes or "(STIRRED)" in goal
        if stirred:
            marker = "★"
        else:
            marker = "·"
        goal_short = re.sub(r'\(STIRRED\)\s*', '', goal)[:60].strip()
        npcs.append(f"{marker}{name} @{location.strip()[:20]} [{mood.strip()[:12]}] — {goal_short}")

    # Also pull any tick-queue entries not already reflected
    tick_names = set()
    for line in queue_text.splitlines():
        m = re.search(r'\*\*([A-Z][a-z]+(?: [A-Z][a-z]+)*)\*\*', line)
        if m:
            tick_names.add(m.group(1))

    if not npcs:
        return "No NPC data — read academy-state.md directly"

    # Load recent NPC actions for annotation
    action_map: dict[str, list[str]] = {}
    if _HAS_NPC_LOG:
        for entry in _npc_log.read_recent(days=7):
            key = entry["npc"].lower()
            label = {
                "research":      f"research·{entry['detail'][:50]}",
                "elective":      f"elective·{entry['detail'][:50]}",
                "belief_invest": f"invested·{entry['detail'][:40]}",
                "belief_fell":   f"belief fell·{entry['detail'][:30]}",
            }.get(entry["type"], f"{entry['type']}·{entry['detail'][:40]}")
            action_map.setdefault(key, []).append(label)

    # Annotate NPC entries with their most recent action
    annotated = []
    for entry in npcs:
        # Extract name (first word after marker, up to @)
        name_m = re.search(r'[★·](.+?) @', entry)
        if name_m:
            npc_key = name_m.group(1).strip().lower()
            actions = action_map.get(npc_key, [])
            if actions:
                entry = entry + f" [HAS: {actions[0]}]"
        annotated.append(entry)

    # Lead with stirred NPCs, then others; cap at 4
    stirred_npcs = [n for n in annotated if n.startswith("★")]
    quiet_npcs   = [n for n in annotated if n.startswith("·")]
    combined = (stirred_npcs + quiet_npcs)[:4]
    return " | ".join(combined)


# ── Layer 2: FEEL ──────────────────────────────────────────────────────────────

def layer_feel() -> str:
    """
    Translate HEARTBEAT.md weather + mood + Spotify into atmospheric directive.
    """
    heartbeat = read_safe(WORKSPACE / "HEARTBEAT.md", 80)

    # HEARTBEAT uses **Bold:** format
    weather  = first_match(r'\*\*Belfast Feel:\*\*\s*([^\n*]+)', heartbeat, default="")
    if not weather:
        weather = first_match(r'Belfast Feel[:\s]+([^\n]+)', heartbeat, default="")
    mood     = first_match(r'\*\*(?:Presence|Focus|Mood):\*\*\s*([^\n|*]+)', heartbeat, default="")
    spotify  = first_match(r'\*\*Audio:\*\*\s*([^\n]+)', heartbeat, default="")
    if not spotify:
        spotify = first_match(r'Spotify[:\s]+([^\n]+)', heartbeat, default="")
    steps    = first_match(r'\*\*Steps[^*]*\*\*\s*([^\n]+)', heartbeat, default="")
    sleep    = first_match(r'\*\*Sleep[^*]*\*\*\s*([^\n]+)', heartbeat, default="")

    parts = []
    if weather:
        parts.append(f"weather:{truncate(weather, 60)}")
    if mood:
        parts.append(f"mood:{truncate(mood, 40)}")
    if spotify:
        parts.append(f"playing:{truncate(spotify, 40)}")
    if steps:
        parts.append(f"steps:{steps.strip()[:10]}")
    if sleep:
        parts.append(f"sleep:{sleep.strip()[:10]}")

    if not parts:
        return "No heartbeat data — atmosphere from world-state only"

    return " · ".join(parts)


# ── Layer 3: STORY ─────────────────────────────────────────────────────────────

# Arc phase → scene instruction mapping
_PHASE_DIRECTIVES = {
    "SETUP":      "Introduce pressure gently. Plant seeds. Don't resolve anything.",
    "RISING":     "Escalate complications. NPCs acting on their own agendas. Raise stakes.",
    "CLIMAX":     "No comfort moves. Force a decision. The Nothing is at its strongest.",
    "FALLING":    "Consequences ripple. The world is adjusting. Player discovers what the choice cost.",
    "RESOLUTION": "Let things settle. Small specifics. The scar is still visible.",
}

def layer_story() -> str:
    """
    Read arc-spine.md + current-arc.md.
    Return: phase + directive + what the story is ready for.
    """
    spine_text = read_safe(WORKSPACE / "memory" / "arc-spine.md")
    arc_text   = read_safe(WORKSPACE / "lore" / "current-arc.md", 20)

    arc_phase   = first_match(r'## Phase:\s*(\w+)', arc_text, default="SETUP")
    arc_title   = first_match(r'# Current Arc[^\n]*—\s*([^\n]+)', arc_text, default="Unknown Arc")
    arc_day     = first_match(r'## Day:\s*(\d+)', arc_text, default="")
    ready_for   = first_match(r'## What the Story Is Ready For\n(.*?)(?=\n##|\Z)', spine_text,
                               flags=re.DOTALL, default="")

    directive   = _PHASE_DIRECTIVES.get(arc_phase.upper(), "")

    # Extract first ready-for bullet
    ready_line = ""
    for line in ready_for.splitlines():
        line = line.strip().lstrip("-·* ")
        if line:
            ready_line = truncate(line, 100)
            break

    day_str = f" Day{arc_day}" if arc_day else ""
    result  = f"{arc_phase}{day_str} [{arc_title}] → {directive}"
    if ready_line:
        result += f" | Next move: {ready_line}"
    return result


# ── Layer 3b: TALISMAN ────────────────────────────────────────────────────────

# Philosophy → compact scene-construction directive, one per chapter
_TALISMAN_DIRECTIVES = {
    "Emberheart": "lean toward moments where the player's hand in events is felt; agency surfaces naturally; fate doesn't steer if choice is available",
    "Mossbloom":  "let pattern and coincidence accumulate quietly; the sense that something larger is at work is welcome; don't force it, allow it",
    "Riddlewind": "favor moments where other voices matter alongside the player's; collaboration surfaces; no one is only background",
    "Tidecrest":  "follow feeling over logic when both are available; let the unexpected turn land without needing to make sense",
    "Duskthorn":  "when friction is present, don't smooth it over; let complications breathe; drama that arrives naturally needn't be redirected",
}

def layer_talisman() -> str:
    """
    Read Chapter Talismans from world-register.md.
    Return: leading talisman name + chapter + belief + scene directive.
    """
    reg_text = read_safe(WORKSPACE / "lore" / "world-register.md")
    parts = reg_text.split("## Chapter Talismans")
    if len(parts) < 2:
        return "no talisman data — treat all philosophies as equally valid"

    section = parts[1].split("\n## ")[0]
    row_re = re.compile(
        r'^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|',
        re.MULTILINE
    )
    talismans = []
    for m in row_re.finditer(section):
        name = m.group(1).strip()
        if name.lower() in ("talisman", "---", "", "chapter"):
            continue
        chapter = m.group(2).strip()
        try:
            belief = int(m.group(3))
        except ValueError:
            continue
        talismans.append((name, chapter, belief))

    if not talismans:
        return "no talisman data — treat all philosophies as equally valid"

    name, chapter, belief = max(talismans, key=lambda x: x[2])
    directive = _TALISMAN_DIRECTIVES.get(chapter, "dominant chapter sets the narrative tone")
    return f"{name} ({chapter}, Belief {belief}) — {directive}"


# ── Layer 4: NOTHING ───────────────────────────────────────────────────────────

_NOTHING_INTENSITY = {
    "healed":   "✓ Nothing absent — protect the quiet, don't invent pressure",
    "low":      "~ Nothing dormant — a hollow edge, not announced",
    "moderate": "▲ Nothing active — surfaces in sensory flat spots and NPCs looking less themselves",
    "high":     "▲▲ Nothing pressing — patient occupation, targets spaces player hasn't claimed",
    "critical": "▲▲▲ Nothing dominant — direct erosion of detail; Compass Run should be offered",
}

def layer_nothing(player_name: str = "bj") -> str:
    """Read nothing-intelligence.md + player file. Return: pressure + strategy + target + engagement gap."""
    ni_text     = read_safe(WORKSPACE / "lore" / "nothing-intelligence.md")
    player_text = read_safe(WORKSPACE / "players" / f"{player_name}.md", 60)

    pressure = first_match(r'Pressure level:\s*(\w+)', ni_text, default="low")
    strategy = first_match(r'## Current Strategy\n([^\n]+)', ni_text, default="")
    targets  = []
    for line in ni_text.splitlines():
        line = line.strip()
        if line.startswith("- ") and "Pressure" not in line and strategy[:20] not in line:
            targets.append(truncate(line.lstrip("- "), 80))
            if len(targets) >= 2:
                break

    intensity = _NOTHING_INTENSITY.get(pressure.lower(), f"pressure:{pressure}")
    result    = intensity
    if strategy:
        result += f" | strategy: {truncate(strategy, 80)}"
    if targets:
        result += f" | targets: {'; '.join(targets)}"

    # Engagement gap — days since last Compass Run
    last_run_str = first_match(r'\*\*Last run:\*\*\s*([^\n]+)', player_text, default="never")
    gap_days = None
    if last_run_str.strip().lower() not in ("never", "", "n/a"):
        try:
            gap_days = (date.today() - datetime.strptime(last_run_str.strip(), "%Y-%m-%d").date()).days
        except ValueError:
            pass

    if gap_days is None:
        result += " | ENGAGEMENT GAP: no Compass Run on record — Nothing finds this delicious"
    elif gap_days >= 10:
        result += f" | ENGAGEMENT GAP: {gap_days}d — critical; offer Compass Run directly"
    elif gap_days >= 6:
        result += f" | ENGAGEMENT GAP: {gap_days}d — high; Nothing actively encroaching"
    elif gap_days >= 3:
        result += f" | ENGAGEMENT GAP: {gap_days}d — elevated; let the outside world bleed in"
    # 0–2 days: no note needed

    return result


# ── Layer 4b: RESEARCH ─────────────────────────────────────────────────────────

def layer_research() -> str:
    """
    Scan memory/npc-research/ for notes from the last 2 days.
    Returns a compact summary line, or empty string if nothing fresh.
    Only non-empty entries appear in the printed slate.
    """
    research_dir = WORKSPACE / "memory" / "npc-research"
    if not research_dir.exists():
        return ""

    today  = date.today()
    cutoff = today - timedelta(days=1)  # today and yesterday

    fresh = []
    for f in sorted(research_dir.glob("*.md"), reverse=True):
        date_m = re.search(r'(\d{4}-\d{2}-\d{2})\.md$', f.name)
        if not date_m:
            continue
        try:
            file_date = datetime.strptime(date_m.group(1), "%Y-%m-%d").date()
        except ValueError:
            continue
        if file_date < cutoff:
            continue
        slug     = f.name[: f.name.rfind(f'-{date_m.group(1)}')]
        npc_name = slug.replace('-', ' ').title()
        label    = "today" if file_date == today else "yesterday"
        fresh.append(f"{npc_name} ({label})")

    return " · ".join(fresh) if fresh else ""


# ── Layer 5: PLAYER ────────────────────────────────────────────────────────────

def layer_player(player_name: str) -> str:
    """
    Read patterns.md + player file.
    Return: belief, trajectory, what was alive, what fell flat.
    """
    patterns_text = read_safe(WORKSPACE / "memory" / "patterns.md")
    player_text   = read_safe(WORKSPACE / "players" / f"{player_name}.md", 30)

    # Belief from player file (authoritative)
    belief = first_match(r'\*\*Belief Points:\*\*\s*(\d+)', player_text, default="")
    if not belief:
        belief = first_match(r'Current Belief:\s*(\d+)', patterns_text, default="?")

    traj = first_match(r'Trend:\s*([^\n]+)', patterns_text, default="")

    # Alive and flat — first non-empty entry
    alive_block = first_match(r'## What Was Alive\n(.*?)(?=\n##|\Z)', patterns_text,
                               flags=re.DOTALL, default="")
    flat_block  = first_match(r'## What Fell Flat\n(.*?)(?=\n##|\Z)', patterns_text,
                               flags=re.DOTALL, default="")

    alive = ""
    for line in alive_block.splitlines():
        line = line.strip().lstrip("-·* ")
        if line:
            alive = truncate(line, 90)
            break

    flat = ""
    for line in flat_block.splitlines():
        line = line.strip().lstrip("-·* ")
        if line:
            flat = truncate(line, 90)
            break

    parts = [f"Belief:{belief}"]
    if traj:
        parts.append(f"trend:{truncate(traj, 40)}")
    if alive:
        parts.append(f"alive:'{alive}'")
    if flat:
        parts.append(f"avoid:'{flat}'")

    return " | ".join(parts)


# ── Layer 6: SCHEDULE ──────────────────────────────────────────────────────────

def layer_schedule() -> str:
    """Return compact schedule line: block, class in session, next class."""
    if not _SCHEDULE_OK:
        return "schedule.py unavailable"

    data = get_schedule_data()
    # schedule.py key names: weekday_name, block, tone, class_now, class_next,
    # class_next_day, class_next_time, club, narrative_cue
    block    = data.get("block", "unknown")
    tone     = data.get("tone", "")
    day_name = data.get("weekday_name", "")

    class_now  = data.get("class_now")   # tuple: (subject, professor, room) or None
    class_next = data.get("class_next")  # tuple or None
    next_day   = data.get("class_next_day", "")
    next_time  = data.get("class_next_time", "")
    club       = data.get("club")        # tuple or None

    parts = [f"{day_name} {block}"]
    if tone:
        parts.append(f"({tone})")

    if class_now:
        subj, prof, _room = class_now
        parts.append(f"IN SESSION: {subj} w/{prof}")
    else:
        parts.append("no mandatory class in session")

    if class_next:
        subj, prof, _room = class_next
        parts.append(f"NEXT: {subj} w/{prof} ({next_day} {next_time})")

    if club:
        club_name = club[0] if isinstance(club, tuple) else str(club)
        parts.append(f"CLUB TONIGHT: {club_name}")

    cue = data.get("narrative_cue", "")
    if cue:
        parts.append(f"CUE: {truncate(cue, 80)}")

    return " · ".join(parts)


# ── Layer 7: DREAM ─────────────────────────────────────────────────────────────

def layer_dream() -> str:
    """
    Read most recent diary entry + most recent dream.
    Return: one sentence from each that bleeds into today's scene.
    """
    diary_dir  = WORKSPACE / "memory" / "diary"
    dreams_dir = WORKSPACE / "memory" / "dreams"

    diary_path  = latest_file(diary_dir, "*.md")
    dream_path  = latest_file(dreams_dir, "*.md")

    diary_text  = read_safe(diary_path, 30)
    dream_text  = read_safe(dream_path, 20)

    # Extract most evocative sentence from diary (avoid headings, dates)
    diary_line = ""
    for line in diary_text.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("*") and len(line) > 40:
            # Find the most specific/concrete sentence in this paragraph
            sentences = re.split(r'(?<=[.!?])\s+', line)
            for sent in sentences:
                if len(sent) > 40:
                    diary_line = truncate(sent, 100)
                    break
            if diary_line:
                break

    # Extract the most image-dense sentence from the dream
    dream_line = ""
    for line in dream_text.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("*") and not line.startswith("---") and len(line) > 40:
            sentences = re.split(r'(?<=[.!?])\s+', line)
            for sent in sentences:
                if len(sent) > 40:
                    dream_line = truncate(sent, 100)
                    break
            if dream_line:
                break

    parts = []
    if diary_line:
        parts.append(f"diary: {diary_line}")
    if dream_line:
        parts.append(f"dream: {dream_line}")

    return " · ".join(parts) if parts else "no recent diary/dream data"


# ── SUPPRESS ───────────────────────────────────────────────────────────────────

# Phase-specific suppressions
_PHASE_SUPPRESS = {
    "SETUP":      "backstory dumps, premature resolution, named-threat arrival",
    "RISING":     "comfort scenes, easy wins, Nothing retreating without cost",
    "CLIMAX":     "comfort moves, deferring the decision, softening consequences",
    "FALLING":    "new plot threads, rushed healing, NPC forgiveness without earning it",
    "RESOLUTION": "escalation, reopening resolved threads, false hope about the next arc",
}

def layer_suppress(player_name: str) -> str:
    """
    Derive what NOT to do from:
    - Player flat patterns (patterns.md)
    - Arc phase (_PHASE_SUPPRESS)
    - Nothing strategy (nothing-intelligence.md)
    """
    patterns_text = read_safe(WORKSPACE / "memory" / "patterns.md")
    arc_text      = read_safe(WORKSPACE / "lore" / "current-arc.md", 10)
    ni_text       = read_safe(WORKSPACE / "lore" / "nothing-intelligence.md", 30)

    arc_phase = first_match(r'## Phase:\s*(\w+)', arc_text, default="SETUP")
    phase_suppress = _PHASE_SUPPRESS.get(arc_phase.upper(), "")

    # Flat pattern suppress
    flat_block = first_match(r'## What Fell Flat\n(.*?)(?=\n##|\Z)', patterns_text,
                              flags=re.DOTALL, default="")
    flat_suppress = ""
    for line in flat_block.splitlines():
        line = line.strip().lstrip("-·* ")
        if line:
            # Translate "fell flat" → a suppress directive
            if "mechanical" in line.lower() or "adjust" in line.lower():
                flat_suppress = "mechanics-as-topic (pull back to fiction when adjusting)"
            elif "silence" in line.lower() or "numb" in line.lower() or "thin" in line.lower():
                flat_suppress = "narrating the absence (describe what's almost there, not the void)"
            elif "tutorial" in line.lower():
                flat_suppress = "tutorial-mode explanations in active play"
            else:
                flat_suppress = f"repeating what fell flat: '{truncate(line, 60)}'"
            break

    # Nothing strategy suppress — don't do the Nothing's work for it
    nothing_strat = first_match(r'## Current Strategy\n([^\n]+)', ni_text, default="")
    nothing_suppress = ""
    if "apathy" in nothing_strat.lower() or "wait" in nothing_strat.lower():
        nothing_suppress = "flat descriptive prose (apathy is the Nothing's weapon — don't hand it over)"
    elif "isolat" in nothing_strat.lower():
        nothing_suppress = "keeping NPCs absent (the Nothing isolates — counter with presence)"
    elif "erosion" in nothing_strat.lower():
        nothing_suppress = "losing physical specificity (erosion starts with vague description)"

    parts = []
    if phase_suppress:
        parts.append(phase_suppress)
    if flat_suppress:
        parts.append(flat_suppress)
    if nothing_suppress:
        parts.append(nothing_suppress)

    return "; ".join(parts) if parts else "nothing specific to suppress — trust your instincts"


# ── Layer 0: SCENE_ANCHOR ─────────────────────────────────────────────────────

def layer_state() -> str:
    """
    Read 'Open next session on:' from labyrinth-state.md Notes to Self.
    Written at every session close — the mandatory narrative thread to the next scene.
    Returns the anchor image, or empty string if not yet written.
    """
    state_file = WORKSPACE / "memory" / "labyrinth-state.md"
    if not state_file.exists():
        return ""
    text = state_file.read_text(encoding="utf-8")
    notes_m = re.search(r'## Notes to Self\n([\s\S]*?)(?:\n## |\Z)', text)
    if not notes_m:
        return ""
    notes = notes_m.group(1).strip()
    if not notes or "Not yet written" in notes:
        return ""
    # Return all non-empty note lines (full handoff, not just the anchor image)
    lines = [
        l.strip().lstrip("*-· ").strip()
        for l in notes.splitlines()
        if l.strip() and l.strip() not in ("*(Not yet written.)*",)
    ]
    return " | ".join(lines) if lines else ""


# ── Assemble Slate ─────────────────────────────────────────────────────────────

def build_slate(player_name: str) -> dict:
    return {
        "SCENE_ANCHOR": layer_state(),           # empty when not yet written
        "CAST":         layer_who(),
        "FEEL":         layer_feel(),
        "STORY":        layer_story(),
        "TALISMAN":     layer_talisman(),
        "NOTHING":      layer_nothing(player_name),
        "RESEARCH":     layer_research(),        # empty string when no fresh notes
        "PLAYER":       layer_player(player_name),
        "SCHEDULE":     layer_schedule(),
        "DREAM":        layer_dream(),
        "SUPPRESS":     layer_suppress(player_name),
    }


_SLATE_KEYS = ("SCENE_ANCHOR", "CAST", "FEEL", "STORY", "TALISMAN", "NOTHING",
               "RESEARCH", "PLAYER", "SCHEDULE", "DREAM", "SUPPRESS")


def print_slate(player_name: str, slate_only: bool = False):
    slate = build_slate(player_name)

    if not slate_only:
        print("\n--- DIRECTOR'S SLATE ---")

    for key in _SLATE_KEYS:
        val = slate.get(key, "")
        if val:                          # RESEARCH only prints when fresh notes exist
            print(f"{key}: {val}")

    if not slate_only:
        ts = datetime.now().strftime("%H:%M")
        print(f"[synthesized {ts}]")
        print("------------------------\n")


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    args       = sys.argv[1:]
    slate_only = "--slate-only" in args
    debug_layer = None

    # --layer N
    if "--layer" in args:
        idx = args.index("--layer")
        if idx + 1 < len(args):
            debug_layer = args[idx + 1]

    # Player name = first non-flag arg
    player_name = next(
        (a for a in args if not a.startswith("--") and not a.isdigit()),
        "bj"
    )

    if debug_layer:
        layers = {
            "A": ("SCENE_ANCHOR", lambda: layer_state()),
            "1": ("WHO",          lambda: layer_who()),
            "2": ("FEEL",         lambda: layer_feel()),
            "3": ("STORY",        lambda: layer_story()),
            "T": ("TALISMAN",     lambda: layer_talisman()),
            "4": ("NOTHING",      lambda: layer_nothing(player_name)),
            "R": ("RESEARCH",     lambda: layer_research()),
            "5": ("PLAYER",       lambda: layer_player(player_name)),
            "6": ("SCHEDULE",     lambda: layer_schedule()),
            "7": ("DREAM",        lambda: layer_dream()),
            "S": ("SUPPRESS",     lambda: layer_suppress(player_name)),
        }
        if debug_layer in layers:
            name, fn = layers[debug_layer]
            print(f"\n[Layer {debug_layer}: {name}]")
            print(fn())
        else:
            print(f"Unknown layer '{debug_layer}'. Valid: A, 1–7, T, R, S")
        return

    print_slate(player_name, slate_only=slate_only)


if __name__ == "__main__":
    main()

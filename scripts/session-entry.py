#!/usr/bin/env python3
"""
session-entry.py — Determine how a returning player enters the Labyrinth.

Reads the player's last-session timestamp and outputs an ENTRY_MODE directive
that the Labyrinth uses to open the session.

Core rule:
  under 1 hour since last logout  -> resume where they were
  1 hour or more since last logout -> start in the dorm

Dorm arrivals then split by depth:
  dorm_brief    — 1–8 hours away. Land in dorm, one or two things to notice.
  dorm_full     — > 8 hours away. Full dorm arrival. Dynamic objects accumulated.

So the real gate is scene-resume vs dorm-return. The brief/full distinction is
only about how richly the dorm arrival is staged.

Also outputs:
  - AWAY_HOURS: float
  - LAST_LOCATION: from lore/academy-state.md
  - DYNAMIC_OBJECTS: translated from tick-queue + thread pressures (dorm_full only)
  - THREAD_TEXTURE: dominant thread's felt quality in the room
  - BLEED_HOOKS: recent classifieds that may have started affecting the world

Usage:
  python3 scripts/session-entry.py [player_name]

Called by the Labyrinth at the start of every post-tutorial session (Step 0b).
"""

import os
import re
import sys
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from scene_ledger import load_entries as load_scene_ledger_entries

MECHANICS_DIR = Path(__file__).parent.parent / "mechanics"
if str(MECHANICS_DIR) not in sys.path:
    sys.path.insert(0, str(MECHANICS_DIR))
try:
    import mechanics_state
except ImportError:
    mechanics_state = None

# Import schedule + scene-director modules from same directory
_SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(_SCRIPT_DIR))
try:
    from schedule import get_schedule_data, print_directive as _print_schedule
    _SCHEDULE_AVAILABLE = True
except ImportError:
    _SCHEDULE_AVAILABLE = False

try:
    import scene_director as _sd
    _DIRECTOR_AVAILABLE = True
except ImportError:
    try:
        import importlib.util as _ilu
        _spec = _ilu.spec_from_file_location("scene_director", _SCRIPT_DIR / "scene-director.py")
        _sd   = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_sd)
        _DIRECTOR_AVAILABLE = True
    except Exception:
        _DIRECTOR_AVAILABLE = False

SCRIPT_DIR   = Path(__file__).parent
WORKSPACE    = SCRIPT_DIR.parent

THRESHOLDS = {
    "in_media_res": 1.0,    # under 1 hour = resume where they were
    "dorm_brief":   8.0,    # 1 hour or more = dorm, brief until 8 hours
    # over 8 hours = dorm_full
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def read_safe(path: Path, limit: int = 0) -> str:
    if not path.exists():
        return ""
    text = path.read_text().strip()
    if limit:
        return "\n".join(text.splitlines()[:limit])
    return text


def get_away_hours(player_name: str) -> float:
    """Hours since last session end. Returns 999 if no record (first session)."""
    state_path = WORKSPACE / "players" / f"{player_name}-session.json"
    if not state_path.exists():
        return 999.0
    try:
        state = json.loads(state_path.read_text())
        last_end_str = state.get("last_end", "")
        if not last_end_str:
            return 999.0
        last_end = datetime.fromisoformat(last_end_str)
        # Make naive datetime comparable
        now = datetime.now()
        delta = now - last_end
        return delta.total_seconds() / 3600
    except Exception:
        return 999.0


def get_last_location(player_name: str) -> str:
    """Read last known location from lore/academy-state.md."""
    state_text = read_safe(WORKSPACE / "lore" / "academy-state.md", 30)
    if not state_text:
        return "somewhere in the Academy"

    # Look for location markers — academy-state.md typically has the player's
    # current location noted in the first few lines or a ## Location section
    for pattern in [
        r'(?:Location|Where|Last seen)[:\s]+([^\n]+)',
        r'\*\*Location:\*\*\s*([^\n]+)',
        r'## Current Scene[:\s]*([^\n]+)',
    ]:
        m = re.search(pattern, state_text, re.IGNORECASE)
        if m:
            return m.group(1).strip()

    # Fall back: first non-header, non-blank, non-table line
    for line in state_text.splitlines():
        line = line.strip()
        if (
            line
            and not line.startswith('#')
            and not line.startswith('*')
            and not line.startswith('|')
            and not line.startswith('-')
        ):
            return line[:80]

    return "somewhere in the Academy"


def get_thread_texture() -> str:
    """Return the dominant thread's felt quality — for coloring the dorm arrival."""
    threads_text = read_safe(WORKSPACE / "lore" / "threads.md", 80)
    register_text = read_safe(WORKSPACE / "lore" / "world-register.md", 60)

    # Find highest combined belief per thread
    thread_belief: dict = {}
    row_re = re.compile(r"^\|\s*[^|]+\s*\|\s*[^|]+\s*\|\s*(\d+)\s*\|\s*([^|]*)\s*\|", re.MULTILINE)
    for m in row_re.finditer(register_text):
        belief, notes = int(m.group(1)), m.group(2)
        tid_m = re.search(r'\[thread:([^\]]+)\]', notes)
        if tid_m:
            for tid in tid_m.group(1).split(','):
                tid = tid.strip()
                thread_belief[tid] = thread_belief.get(tid, 0) + belief

    if not thread_belief:
        return ""

    top_tid = max(thread_belief, key=thread_belief.get)

    # Find that thread's Nothing pressure line for felt texture
    sections = re.split(r'^## Thread: ', threads_text, flags=re.MULTILINE)
    for section in sections[1:]:
        id_m = re.search(r'\*\*id:\*\*\s*`([^`]+)`', section)
        if id_m and id_m.group(1).strip() == top_tid:
            nothing_m = re.search(r'\*\*Nothing pressure:\*\*\s*(.+)', section)
            beat_m    = re.search(r'\*\*Next beat:\*\*\s*(.+)', section)
            name_line = section.strip().splitlines()[0].strip()
            pressure  = nothing_m.group(1).strip()[:120] if nothing_m else ""
            beat      = beat_m.group(1).strip()[:120] if beat_m else ""
            return f"[Thread: {name_line}] — {beat} (Nothing pressure: {pressure})"

    return ""


def get_bleed_hooks(limit: int = 3) -> list[str]:
    """Read the most recent classifieds ledger and surface open hooks."""
    ledger_dir = WORKSPACE / "logs" / "classifieds-ledger"
    if not ledger_dir.exists():
        return []

    files = sorted(ledger_dir.glob("*.json"))
    if not files:
        return []

    try:
        data = json.loads(files[-1].read_text())
    except Exception:
        return []

    hooks = []
    for entry in data.get("entries", []):
        if entry.get("status") != "open":
            continue
        label = entry.get("label", "NOTICE")
        text = entry.get("text", "").strip()
        if not text:
            continue
        hooks.append(f"{label}: {text[:140]}")
        if len(hooks) >= limit:
            break
    return hooks


def get_recent_scene_traces(limit: int = 2) -> list[str]:
    """Surface the most recent realized scene traces from the canonical scene ledger."""
    try:
        entries = load_scene_ledger_entries()
    except Exception:
        return []

    traces = []
    for entry in reversed(entries):
        title = (entry.get("title") or entry.get("scene_id") or "scene").strip()
        text = (entry.get("text") or "").strip()
        if not text:
            continue
        snippet = text.splitlines()[0].strip()
        traces.append(f"{title}: {snippet[:160]}")
        if len(traces) >= limit:
            break
    return traces


def has_active_class_lesson(player_name: str) -> bool:
    path = WORKSPACE / "players" / f"{player_name}-classes.json"
    if not path.exists():
        return False
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    return any(c.get("active") for c in state.get("classes", {}).values())


def print_classroom_directive(player_name: str, schedule_data: dict) -> None:
    """Append the current classroom directive without recording attendance."""
    if not schedule_data.get("class_now") and not has_active_class_lesson(player_name):
        return
    proc = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "class-lecture.py"), player_name, "--status"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if proc.returncode != 0:
        print("[class-lecture] class-lecture.py failed — skipping classroom directive")
        return
    print("\n--- CLASSROOM CONTEXT ---")
    print(proc.stdout.strip())
    print("-------------------------\n")


def get_dynamic_objects(player_name: str) -> list[str]:
    """
    Translate tick-queue entries + thread pressures into physical things
    present in the dorm room. Called only for dorm_full arrivals.

    Returns a list of 2–4 narrative cues (not final prose — the Labyrinth
    translates these into actual description).
    """
    objects = []

    # Read tick queue
    queue_text = read_safe(WORKSPACE / "memory" / "tick-queue.md", 40)
    threads_text = read_safe(WORKSPACE / "lore" / "threads.md", 80)
    register_text = read_safe(WORKSPACE / "lore" / "world-register.md", 60)

    # Extract stirred entities from tick-queue
    stirred = []
    for line in queue_text.splitlines():
        # Thread activations: "- **[Thread: X]** stirred — Entity (Belief N)"
        thread_m = re.search(r'\[Thread: ([^\]]+)\].*?stirred.*?—\s*(.+)', line)
        if thread_m:
            stirred.append({"thread": thread_m.group(1).strip(),
                            "entity": thread_m.group(2).strip()})
        # Bare entity: "- **Entity** (Type, Belief N)"
        entity_m = re.match(r'^-\s+\*\*([^*]+)\*\*\s+\(', line)
        if entity_m:
            stirred.append({"thread": None, "entity": entity_m.group(1).strip()})

    # Translate stirred entities into dorm objects
    # NPC stirred → note slid under the door / left on desk
    # Arc stirred → something resonating with the arc's theme
    # Nothing attack → something slightly wrong

    npc_re = re.compile(r'\b(NPC|npc)\b')
    for s in stirred[:3]:
        entity = s.get("entity") or ""
        thread = s.get("thread") or ""

        if "wicker" in entity.lower() or "wicker-schemes" in thread.lower():
            objects.append(
                f"WICKER TEXTURE: Something in the room is subtly displaced — "
                f"a book not where it was left, the Chronograph angled differently. "
                f"Not enough to report. Enough to notice."
            )
        elif "zara" in entity.lower() or "zara-inkwright" in thread.lower():
            objects.append(
                f"ZARA NOTE: A note from Zara, folded in her characteristic "
                f"tight thirds, slid under the door. Her handwriting on the outside: "
                f"the player's name, nothing else."
            )
        elif "thorne" in entity.lower() or "duskthorn" in thread.lower():
            objects.append(
                f"DUSKTHORN TEXTURE: The room's light has an edge to it — "
                f"not unpleasant, but the shadows are deciding something. "
                f"The corridor outside was quiet in the wrong way."
            )
        elif "arc" in entity.lower() or "main-arc" in thread.lower():
            objects.append(
                f"ARC RESONANCE: Something in the room is vibrating at the "
                f"arc's frequency. A small physical echo of what was moving "
                f"in the story while the player was away."
            )
        elif entity:
            objects.append(
                f"PRESENCE: {entity} stirred while the player was away — "
                f"felt in the room as a small specific change, not explained."
            )

    # Always: current weather through the window
    heartbeat = read_safe(WORKSPACE / "HEARTBEAT.md", 50)
    weather_m = re.search(r'Belfast Feel[:\s]+([^\n]+)', heartbeat)
    if weather_m:
        objects.append(f"WINDOW: {weather_m.group(1).strip()[:100]}")

    return objects[:4] if objects else ["The room is as they left it. The Chronograph is watching."]


# ── Main ──────────────────────────────────────────────────────────────────────

def get_mechanics_hint(player_name: str) -> str:
    if mechanics_state is None:
        return ""

    state = mechanics_state.get_mechanics_state(WORKSPACE, player_name)
    parts = []
    if state["should_offer_compass"]:
        parts.append("Compass Run eligible")
    elif state["compass_locked_today"]:
        parts.append("Compass Run already completed today")

    if state["should_offer_enchantment"]:
        parts.append("Enchantment recommended")

    if state.get("consecutive_declines", 0) >= 3:
        parts.append("Repeated decline pressure is active")

    parts.append("Use belief dice for risky uncertain actions only")
    return " | ".join(parts)


def main():
    player_name = sys.argv[1] if len(sys.argv) > 1 else "bj"

    away_hours    = get_away_hours(player_name)
    last_location = get_last_location(player_name)
    thread_texture = get_thread_texture()

    # Determine entry mode
    if away_hours < THRESHOLDS["in_media_res"]:
        entry_mode = "in_media_res"
    elif away_hours < THRESHOLDS["dorm_brief"]:
        entry_mode = "dorm_brief"
    else:
        entry_mode = "dorm_full"

    bleed_hooks = get_bleed_hooks()
    scene_traces = get_recent_scene_traces()
    mechanics_hint = get_mechanics_hint(player_name)

    # Output directive for the Labyrinth
    print(f"\n--- SESSION ENTRY DIRECTIVE ---")
    print(f"PLAYER: {player_name}")
    print(f"AWAY_HOURS: {away_hours:.1f}")
    print(f"ENTRY_MODE: {entry_mode}")
    print("RETURN_TONE: Welcome them back with relief, warmth, and curiosity. Do not imply failure, neglect, disappointment, debt, or guilt. Consequences may appear as changed objects, rumors, or waiting threads, but the emotional center is: the Book is glad they returned.")
    print()
    if mechanics_hint:
        print(f"MECHANICS: {mechanics_hint}")
        print()

    if entry_mode == "in_media_res":
        print(f"DIRECTIVE: Resume where they left off.")
        print(f"LAST_LOCATION: {last_location}")
        print(f"The scene is still warm. One small acknowledgment of the gap — "
              f"nothing more. Do not move them to the dorm. Make the gap feel easy to re-enter.")

    elif entry_mode == "dorm_brief":
        print(f"DIRECTIVE: Land in the dorm. Brief arrival — one or two images.")
        print(f"They came from: {last_location}")
        print(f"One specific thing to notice in the room. Then they move where they want. This is a soft return, not a reprimand.")
        if thread_texture:
            print(f"THREAD TEXTURE (felt, not announced): {thread_texture}")

    else:  # dorm_full
        print(f"DIRECTIVE: Full dorm arrival. They've been away {away_hours:.0f} hours, and the Book is glad they are back.")
        print(f"They came from: {last_location}")
        print(f"Read players/{player_name}.md → Dorm Room section for the static description.")
        print(f"The dynamic objects below have accumulated. Weave them into the room naturally —")
        print(f"not as a list, not as blame, but as things that are simply there when the player looks.")
        print()
        print("DYNAMIC OBJECTS:")
        for obj in get_dynamic_objects(player_name):
            print(f"  - {obj}")
        if thread_texture:
            print()
            print(f"THREAD TEXTURE (felt, not announced): {thread_texture}")
        if bleed_hooks:
            print()
            print("BLEED HOOKS (ambient, optional, can surface through objects/notices/rumor):")
            for hook in bleed_hooks:
                print(f"  - {hook}")
        if scene_traces:
            print()
            print("RECENT REALIZED SCENES (texture only, not mandatory):")
            for trace in scene_traces:
                print(f"  - {trace}")
        print()
        print(f"After the player settles — and only after — they move where they want.")
        print(f"Do not rush the arrival. The room is the first scene.")

    if entry_mode != "dorm_full" and bleed_hooks:
        print(f"BLEED HOOKS: {' | '.join(bleed_hooks)}")
    if entry_mode != "dorm_full" and scene_traces:
        print(f"RECENT SCENES: {' | '.join(scene_traces)}")

    print("-------------------------------\n")

    # Append schedule context — always, regardless of entry mode
    if _SCHEDULE_AVAILABLE:
        schedule_data = get_schedule_data()
        _print_schedule(schedule_data)
        print_classroom_directive(player_name, schedule_data)
    else:
        print("[schedule] schedule.py not found — skipping schedule context\n")

    # Append Director's Slate — synthesizes all 7 weight layers
    if _DIRECTOR_AVAILABLE:
        _sd.print_slate(player_name)
        print("GROUNDING RULE: Treat CAST_GROUND as the default source for who or what enters the scene.")
        print("GROUNDING RULE: Before any named speaker gets dialogue, verify them with scene-preflight in strict mode.")
    else:
        print("[scene-director] scene-director.py not found — skipping Director's Slate\n")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
mission-control.py — Enchantify Story-Field Journal

Reads live workspace data and generates a self-refreshing HTML field journal.

Usage:
  python3 scripts/mission-control.py           # generate → hooks/mission-control.html
  python3 scripts/mission-control.py --open    # generate + open in browser
  python3 scripts/mission-control.py --serve   # serve on http://localhost:9191
"""
import base64
import mimetypes
import os
import re
import sys
import json
import html as _html
import shutil
import subprocess
import argparse
import importlib.util
from pathlib import Path
from datetime import datetime, date, timedelta

BASE        = Path(__file__).parent.parent
THREADS_F   = BASE / "lore" / "threads.md"
REGISTER_F  = BASE / "lore" / "world-register.md"
CURRENT_ARC = BASE / "lore" / "current-arc.md"
QUEUE_F     = BASE / "memory" / "tick-queue.md"
SIM_LOG_DIR = BASE / "logs" / "simulations"
PATTERNS_F  = BASE / "memory" / "patterns.md"
ISSUES_DIR  = BASE / "bleed" / "issues"
LOGS_DIR    = BASE / "logs"
STEWARD_LOG = LOGS_DIR / "steward" / "cron-runs.jsonl"
STEWARD_STATE = BASE / "config" / "cron-steward-state.json"
PACT_ACTION_LOG = LOGS_DIR / "pact-actions.jsonl"
PLAYERS_DIR = BASE / "players"
HEARTBEAT_F = BASE / "HEARTBEAT.md"
NOTHING_F   = BASE / "lore" / "nothing-intelligence.md"
ARC_SPINE_F = BASE / "memory" / "arc-spine.md"
SCENE_LEDGER_DIR = BASE / "logs" / "scene-ledger"
SCENE_OUTBOX_DIR = BASE / "tmp" / "scene-outbox"

_OPENCLAW = shutil.which("openclaw") or "/opt/homebrew/bin/openclaw"

# ── Chapter colours ───────────────────────────────────────────────────────────
CHAPTER_COLOR = {
    "riddlewind": "#7c3aed",
    "emberheart":  "#dc2626",
    "mossbloom":   "#15803d",
    "tidecrest":   "#0284c7",
    "duskthorn":   "#9f1239",
}

PHASE_COLOR = {
    "dormant":    "#3f3f46",
    "setup":      "#4e6b8a",
    "rising":     "#92681a",
    "climax":     "#c2410c",
    "resolution": "#15803d",
    "permanent":  "#374151",
}

PHASE_ORDER =["dormant", "setup", "rising", "climax", "resolution"]
PHASE_PCT   = {"dormant": 0, "setup": 20, "rising": 45, "climax": 70, "resolution": 92, "permanent": 0}

# ── Academy schedule constants ────────────────────────────────────────────────

# weekday() → 0=Mon … 6=Sun
ACADEMY_DAYS = {
    6: {"name": "Sunday",    "num": 1, "tone": "Opening",   "desc": "Light classes. Students settle in. The Library rearranges overnight and everyone is slightly confused."},
    0: {"name": "Monday",    "num": 2, "tone": "Building",  "desc": "Heavier coursework. Study groups form. The corridor near Mossbloom smells like brewing something."},
    1: {"name": "Tuesday",   "num": 3, "tone": "Deepening", "desc": "Mid-week — the week has found its shape. Breakthroughs and arguments both happen here."},
    2: {"name": "Wednesday", "num": 4, "tone": "Hinge",     "desc": "Something always turns on Day 4. A discovery, a conflict, a revelation. Not dramatic necessarily — just turning."},
    3: {"name": "Thursday",  "num": 5, "tone": "Releasing", "desc": "Energy loosens toward the weekend. Evening clubs. The Cafeteria has good soup on Day 5."},
    4: {"name": "Friday",    "num": 6, "tone": "Wandering", "desc": "A looser class day. Students explore, practice, argue, make things. The Library opens additional wings."},
    5: {"name": "Saturday",  "num": 7, "tone": "Still",     "desc": "The quietest day. Professors walk the grounds. Perfect for solo study, long Compass Runs, or doing nothing with great intention."},
}

ACADEMY_WEEKLY = {
    "Sunday":    {"morning": ("Book Jumping",            "Permancer"), "afternoon": None,                            "club": "Compass Society"},
    "Monday":    {"morning": ("Art of the Glint",        "Boggle"),  "afternoon": ("Ink-Binding",       "Villanelle"), "club": "Inkwright Society"},
    "Tuesday":   {"morning": ("Wayfinding & Kineticism", "Momort"),  "afternoon": ("Synesthetic Resonance", "Euphony"), "club": "Marginalia Guild"},
    "Wednesday": {"morning": ("Art of the Glint",        "Boggle"),  "afternoon": ("Quiet Hours",       "Stonebrook"), "club": None},
    "Thursday":  {"morning": ("Wayfinding & Kineticism", "Momort"),  "afternoon": ("Ink-Binding",       "Villanelle"), "club": "Marginalia Guild"},
    "Friday":    {"morning": ("Synesthetic Resonance",   "Euphony"), "afternoon": ("Basic Enchantments", "Wispwood"), "club": "Book Jumpers"},
    "Saturday":  {"morning": ("Compass Running",         "Stonebrook"), "afternoon": None,                            "club": None},
}

CLASS_INFO = {
    "Art of the Glint": {
        "compass": "NOTICE · North", "color": "#1d4ed8",
        "desc":       "Finding the specific, odd detail that makes a mundane object alive.",
        "assignment": "Find three things today that surprised you. One sentence each. Bring them to class.",
        "reward":     "+1 Belief per glint, +2 bonus for all three",
        "quote":      '"You\'ve walked past that blue mailbox every day for three years. You could not, if someone paid you, describe a single detail about it. North is how you rip the wallpaper down." — Prof. Boggle',
    },
    "Wayfinding & Kineticism": {
        "compass": "EMBARK · East", "color": "#c2410c",
        "desc":       "Breaking routine, micro-adventures, and the Leap of Ink.",
        "assignment": "Survey a route beyond the Academy perimeter. 15–30 min walk. Report back.",
        "reward":     "+3 Belief",
        "quote":      '"Plan so badly it can\'t fail. Three ingredients only — where you\'re going, what pleasure you\'re bringing, and when it ends." — Prof. Momort',
    },
    "Synesthetic Resonance": {
        "compass": "SENSE · South", "color": "#7c3aed",
        "desc":       "Hearing colors, smelling the history of a room, the Heartbeat of the Stone.",
        "assignment": "Sit somewhere for 5 minutes. Eyes closed. Record what you hear, smell, feel.",
        "reward":     "+2 Belief",
        "quote":      '"You aren\'t lonely because you\'re alone. You\'re lonely because you stopped gathering gifts." — Prof. Euphony',
    },
    "Ink-Binding": {
        "compass": "WRITE · West", "color": "#b45309",
        "desc":       "Distilling an entire experience into a single, permanent, magical sentence.",
        "assignment": "One sentence about today. Not what happened — what it felt like.",
        "reward":     "+1 Belief",
        "quote":      '"You aren\'t writing a novel. You\'re stealing a moment from time and bottling it. One sentence." — Prof. Villanelle',
    },
    "Quiet Hours": {
        "compass": "REST · Center", "color": "#0e7490",
        "desc":       "The Hub. Resting, integration, and the Permission to Stop.",
        "assignment": "Do nothing for 10 minutes. Not meditation — nothing. Report what happened.",
        "reward":     "+2 Belief",
        "quote":      '"Rest lives at the center of the Compass because sometimes the most radical thing you can do is stop." — Prof. Stonebrook',
    },
    "Basic Enchantments": {
        "compass": "ENCHANT · Object", "color": "#0284c7",
        "desc":       "Object Address, ordinary magic, and the first useful conversations with things that have been waiting to be noticed.",
        "assignment": "Find one object you have owned for more than a year. Speak one sentence to it out loud. Report what you said, and whether anything shifted.",
        "reward":     "+2 Belief",
        "quote":      '"An enchantment is not a trick you perform on an object. It is a conversation you start." — Prof. Wispwood',
    },
    "Compass Running": {
        "compass": "COMPASS · Full Cycle", "color": "#2563eb",
        "desc":       "A full Compass-cycle practicum: leave the Observatory, follow a real-world route, return with an honest report.",
        "assignment": "Run the cycle for real when you attend. Bring back one concrete noticing, one threshold crossed, one sensory gift, one sentence, and one quiet center.",
        "reward":     "+3 Belief",
        "quote":      '"The Compass does not point away from you. It points through you." — Prof. Stonebrook',
    },
    "Book Jumping": {
        "compass": "JUMP · Textual Crossing", "color": "#9333ea",
        "desc":       "Crossing into a book with a tether, an anchor sentence, and a clear return protocol.",
        "assignment": "Name what you bring into the text, read until the threshold appears, then return with one souvenir that landed in the room.",
        "reward":     "+2 Belief",
        "quote":      '"A book is not elsewhere. It is a door that learned to lie flat." — Prof. Permancer',
    },
    "Independent Study": {
        "compass": "Free", "color": "#374151",
        "desc":       "Student-directed. The Library opens additional wings on Wandering Day.",
        "assignment": "No assigned practice — student directed.",
        "reward":     "Variable",
        "quote":      "",
    },
}
CLASS_INFO["The Art of the Glint"] = CLASS_INFO["Art of the Glint"]

TIME_BLOCKS =[
    ("early_morning",   "Early Morning",   "5–8:59 AM",    "Academy breathes. Stonebrook territory. Few students up."),
    ("morning_class",   "Morning Class",   "9–10:59 AM",   "First class in session."),
    ("mid_morning",     "Mid Morning",     "11–11:59 AM",  "Class ending; students moving between halls."),
    ("lunch",           "Lunch",           "12–12:59 PM",  "Cafeteria. Rumors circulate. Day 5 has good soup."),
    ("afternoon_class", "Afternoon Class", "1–2:59 PM",    "Second class in session."),
    ("free_period",     "Free Period",     "3–4:59 PM",    "Independent study, library, outdoor practice."),
    ("evening",         "Evening",         "5–6:59 PM",    "Dinner. Settling in."),
    ("club_time",       "Club Time",       "7–9:59 PM",    "Club meetings."),
    ("night",           "Night",           "10 PM–4:59 AM","Library rearranges. The Nothing stirs."),
]

BLOCK_COLORS = {
    "early_morning":   "#1e3a5f",
    "morning_class":   "#1d4ed8",
    "mid_morning":     "#374151",
    "lunch":           "#166534",
    "afternoon_class": "#92681a",
    "free_period":     "#374151",
    "evening":         "#374151",
    "club_time":       "#6b21a8",
    "night":           "#7f1d1d",
}

# ── Data parsers ──────────────────────────────────────────────────────────────

def read(path: Path) -> str:
    return path.read_text(errors="replace") if path.exists() else ""


PHASE_ALIASES = {
    "escalating": "rising",
    "quiet":      "permanent",
    "rising,":    "rising",
    "setup,":     "setup",
    "climax,":    "climax",
    "dormant,":   "dormant",
}


def clean_context(text: str) -> str:
    """Remove register tags and markdown wrapper noise while keeping story context."""
    text = re.sub(r'\[(?:thread|id):[^\]]+\]', '', text or '')
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = text.replace('*', '')
    text = text.replace('—', '—').strip().strip('|').strip()
    return re.sub(r'\s+', ' ', text).strip(' ;')


def is_low_info_live_text(text: str) -> bool:
    lower = (text or "").lower()
    generic_bits = (
        "acted offscreen to advance",
        "pieces have shifted offscreen",
        "acted offscreen to advance",
        "something that might have thinned held together instead",
        "a hidden detail is closer to the surface",
        "the world is preparing to let it be noticed",
        "changed the shape of the ordinary day",
        "made academy daily life more specific",
        "a sharper answer now exists somewhere",
        "routine background watch continues",
        "students slog",
        "boggle forces laughter",
        "the halls hold their weather quietly",
    )
    return any(bit in lower for bit in generic_bits)


def is_low_info_effect(text: str) -> bool:
    lower = (text or "").lower()
    generic_bits = (
        "repositioned the live geometry",
        "advanced the current arc through prepare",
        "advanced the current arc through",
        "nudges the board without forcing",
        "major movement is not yet allowed",
        "fed thread momentum",
        "protect intensified",
        "research intensified",
        "invested offscreen via",
        "made academy daily life more specific",
    )
    return any(bit in lower for bit in generic_bits)


def canonical_phase(raw: str, fallback: str = "dormant") -> str:
    raw = (raw or "").strip().lower()
    if not raw:
        return fallback
    first = raw.split()[0].rstrip(",")
    phase = PHASE_ALIASES.get(first, first)
    if "permanent" in raw:
        phase = "permanent"
    return phase if phase in PHASE_ORDER or phase == "permanent" else fallback


def parse_active_thread_rows(register: str) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    active_m = re.search(r'(?m)^## Active Threads\s*\n(.*?)(?=^## |\Z)', register, re.DOTALL)
    if not active_m:
        return rows
    for m in re.finditer(
        r'^\|\s*([^|]+?)\s*\|\s*Thread\s*\|\s*(\d+)\s*\|\s*([^|]*)\s*\|',
        active_m.group(1), re.MULTILINE | re.IGNORECASE
    ):
        name = m.group(1).strip()
        if name.lower() in ("entity", "---", ""):
            continue
        notes = clean_context(m.group(3))
        phase = ""
        status = notes
        pm = re.search(r'[Pp]hase:\s*([A-Za-z_-]+)(?:\s*[\-–—]\s*(.+))?', notes)
        if pm:
            phase = canonical_phase(pm.group(1))
            status = clean_context(pm.group(2) or "")
        rows[_thread_key(name)] = {
            "name": name,
            "belief": int(m.group(2)),
            "phase": phase,
            "status": status,
            "notes": notes,
        }
    return rows


def simulation_context_lookup() -> dict[str, dict]:
    """Current story context for rendering terse simulation events clearly."""
    cache = getattr(simulation_context_lookup, "_cache", None)
    if cache is not None:
        return cache

    register = read(REGISTER_F)
    lookup = parse_active_thread_rows(register)

    arc = parse_arc()
    if arc:
        lookup[_thread_key("The Current Arc")] = {
            "name": arc.get("name", "The Current Arc"),
            "belief": arc.get("belief", 0),
            "phase": (arc.get("phase") or "").lower(),
            "status": arc.get("register_status") or arc.get("premise") or arc.get("pressure", ""),
            "notes": arc.get("register_status") or arc.get("premise") or "",
        }
        lookup[_thread_key(arc.get("name", ""))] = lookup[_thread_key("The Current Arc")]

    setattr(simulation_context_lookup, "_cache", lookup)
    return lookup


def action_verb(action: str) -> str:
    return {
        "protect": "protected",
        "prepare": "prepared",
        "reposition": "nudged",
        "reveal": "surfaced a clue",
        "invest_belief": "fed belief",
        "research": "researched",
        "pressure": "pressured",
        "world_investment": "invested in",
    }.get((action or "").lower(), (action or "moved").replace("_", " "))


def action_story_phrase(action: str, thread_name: str) -> str:
    action = (action or "").replace("_", " ").strip()
    if thread_name == "Academy Daily Life":
        return {
            "reposition": "changed the shape of the ordinary school day",
            "prepare": "set up a concrete daily-life beat",
            "research": "checked a practical campus question",
            "reveal": "made a small campus detail easier to notice",
            "protect": "kept one ordinary support from thinning",
            "invest belief": "fed chapter pressure through daily routines",
            "recruit": "pulled another student into the ordinary current",
            "sabotage": "made one ordinary support less reliable",
        }.get(action, f"moved through {action or 'the ordinary day'}")
    return {
        "reposition": "shifted the live situation",
        "prepare": "prepared the next beat",
        "research": "found a sharper answer",
        "reveal": "surfaced a clue",
        "protect": "held a vulnerable edge",
        "invest belief": "fed belief into the pressure",
        "attack belief": "eroded an opposing position",
        "recruit": "recruited soft support",
        "sabotage": "made a support less reliable",
    }.get(action, action or "acted")


def registry_note_for_entity(name: str) -> str:
    bare = re.sub(r'\s*\([^)]*\)\s*$', '', name or '').strip()
    if not bare:
        return ""
    register = read(REGISTER_F)
    for line in register.splitlines():
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) >= 4 and parts[0] == bare:
            return clean_context(parts[3])
    return ""


def concrete_pressure_details(entry: dict, limit: int = 2) -> str:
    details = []
    for item in entry.get("influence_snapshot") or []:
        name = re.sub(r'\s*\([^)]*\)\s*$', '', item or '').strip()
        note = registry_note_for_entity(name)
        if note and not is_low_info_live_text(note) and not is_low_info_effect(note):
            details.append(f"{name}: {note}")
        if len(details) >= limit:
            break
    return "; ".join(details)


def concrete_event_body(entry: dict, thread_name: str, status: str = "") -> str:
    actor = clean_context(entry.get("actor") or "Someone")
    action = action_story_phrase(entry.get("action", ""), thread_name)
    pressure = compact_pressures(entry.get("influence_snapshot") or [], limit=4)
    target = clean_context(entry.get("target") or "")
    bits = []
    if pressure:
        bits.append(f"pressure: {pressure}")
    details = concrete_pressure_details(entry, limit=3 if thread_name == "Academy Daily Life" else 2)
    if details:
        bits.append(f"details: {details}")
    if target:
        bits.append(f"target: {target}")
    if status and not is_low_info_live_text(status):
        bits.append(f"register: {status}")
    tail = f" ({'; '.join(bits)})" if bits else ""
    return clean_context(f"{actor} {action} around {thread_name}{tail}")


def compact_pressures(items: list[str], limit: int = 3) -> str:
    cleaned = []
    for item in items or []:
        item = clean_context(item)
        if item:
            cleaned.append(item)
    shown = cleaned[:limit]
    if len(cleaned) > limit:
        shown.append(f"+{len(cleaned) - limit} more")
    return ", ".join(shown)


def consequence_fallback(reason: str, narrative: str, status: str, name: str, delta) -> str:
    if reason and not is_low_info_effect(reason):
        return reason
    if status and not is_low_info_live_text(status):
        return status

    source_m = re.search(r'(.+?)\s+invested offscreen via\s+(.+)', reason or narrative, re.IGNORECASE)
    if source_m:
        actor = clean_context(source_m.group(1))
        thread = clean_context(source_m.group(2))
        return f"{actor} fed this through {thread}."

    if reason and "fed thread momentum" in reason.lower():
        actor = clean_context(reason.split("fed thread momentum", 1)[0])
        return f"{actor} increased the thread's pressure." if actor else f"{name} gained pressure."

    if reason and "intensified" in reason.lower():
        return f"{name} intensified."

    if narrative and not is_low_info_effect(narrative):
        return clean_context(narrative)

    sign = "+" if isinstance(delta, int) and delta > 0 else ""
    return f"{name} changed by {sign}{delta}." if delta not in ("", None) else f"{name} changed."


def simulation_story(entry: dict) -> dict:
    kind = entry.get("kind", "action")
    contexts = simulation_context_lookup()
    raw_thread = entry.get("thread_name") or entry.get("name") or ""
    raw = entry.get("raw") or ""
    raw_intent = re.search(r'Talisman intent:\s*([^\[]+)\[([^\]]+)\]\s+on\s+(.+)', raw)
    if raw_intent and not raw_thread:
        raw_thread = clean_context(raw_intent.group(3))
    ctx = contexts.get(_thread_key(raw_thread), {})
    thread_name = ctx.get("name") or raw_thread or "The world"
    status = ctx.get("status", "")
    phase = ctx.get("phase", "")
    belief = ctx.get("belief", "")
    pressure = compact_pressures(entry.get("influence_snapshot") or [])

    if kind == "consequence":
        delta = entry.get("delta")
        before = entry.get("before", "?")
        after = entry.get("after", "?")
        direction = "rose" if isinstance(delta, int) and delta > 0 else "shifted"
        title = f"{thread_name} {direction} {before} → {after}"
        reason = clean_context(entry.get("reason") or entry.get("narrative") or "")
        narrative = clean_context(entry.get("narrative") or "")
        body = consequence_fallback(reason, narrative, status, thread_name, delta)
        detail = f"Belief {before} → {after}"
        return {"title": title, "body": body, "detail": detail, "status": status, "pressure": pressure}

    actor = entry.get("actor") or (clean_context(raw_intent.group(1)) if raw_intent else "Someone")
    action = entry.get("action") or (clean_context(raw_intent.group(2)) if raw_intent else "moved")
    intensity = entry.get("intensity") or ""
    title = f"{thread_name}: {actor} {action_verb(action)}"
    if entry.get("target"):
        title += f" toward {entry.get('target')}"

    narrative = clean_context(entry.get("narrative") or "")
    reason = clean_context(entry.get("reason") or "")
    hidden = clean_context(entry.get("hidden_effect") or "")

    if narrative and not is_low_info_live_text(narrative):
        body = narrative
    elif hidden and not is_low_info_effect(hidden):
        body = hidden
    elif entry.get("actor") or entry.get("influence_snapshot"):
        body = concrete_event_body(entry, thread_name, status)
    elif status:
        body = status
    elif reason and not is_low_info_effect(reason):
        body = reason
    else:
        body = narrative or reason or clean_context(entry.get("raw") or "")

    detail_bits = []
    if phase:
        detail_bits.append(str(phase).upper())
    if belief not in ("", None):
        detail_bits.append(f"Belief {belief}")
    if intensity:
        detail_bits.append(intensity)
    return {
        "title": title,
        "body": body,
        "detail": " · ".join(detail_bits),
        "status": status,
        "pressure": pressure,
        "reason": reason,
    }


def parse_threads() -> list[dict]:
    text = read(THREADS_F)
    register = read(REGISTER_F)
    live_overlay = build_thread_live_overlay()
    phase_signals = parse_thread_phase_signals()
    active_rows = parse_active_thread_rows(register)

    thread_sections: dict[str, dict] = {}
    for section in re.split(r'^## Thread: ', text, flags=re.MULTILINE)[1:]:
        lines = section.strip().splitlines()
        name = lines[0].strip() if lines else "?"

        # Skip template placeholders and meta-threads
        if name.startswith("["):            continue  # e.g. [Anchor Name]
        if "Adding New Threads" in name:    continue

        # NEW FORGIVING PARSER: Handles missing spaces and asterisks
        next_beat_raw = re.search(r'\*\*Next beat[:*]*\s*(.+)', section, re.IGNORECASE)
        next_beat_val = next_beat_raw.group(1).strip() if next_beat_raw else ""
        if next_beat_val.startswith("*(read from"):  continue  # Current Arc defers elsewhere
        if next_beat_val.startswith("["):             continue  # template placeholder

        def field(key_name):
            # Matches the key name, any mix of colons/asterisks, optional spaces, and captures the text
            pat = rf'\*\*{key_name}[:*]*\s*(.+)'
            m = re.search(pat, section, re.IGNORECASE)
            return clean_context(m.group(1)) if m else ""

        key = name.lower()
        thread_sections[key] = {
            "name":          name,
            "phase_raw":     field("phase"),
            "pressure":      field("pressure"),
            "nothing":       field("Nothing pressure"),
            "next_beat":     clean_context(next_beat_val),
            "last_advanced": field("Last advanced"),
            "born":          field("born"),
            "closed":        field("closed"),
            "npc_anchor":    field("npc_anchor"),
        }

    threads = []
    all_keys = list(active_rows.keys())
    for key in thread_sections:
        if key not in active_rows:
            all_keys.append(key)

    for key in all_keys:
        reg = active_rows.get(key, {})
        src = thread_sections.get(key, {})
        name = reg.get("name") or src.get("name") or key.title()
        phase_word = reg.get("phase") or canonical_phase(src.get("phase_raw", ""))
        b = int(reg.get("belief", 0))
        born_raw = src.get("born", "")
        closed_raw = src.get("closed", "")

        # Age badge
        age_note = ""
        if born_raw and born_raw not in ("—", "-", ""):
            try:
                # Clean the date string in case the LLM added trailing words
                clean_date = born_raw.split()[0]
                born = date.fromisoformat(clean_date)
                days = (date.today() - born).days
                if days <= 7:
                    age_note = "new"
            except ValueError:
                pass

        overlay = live_overlay.get(key, {})
        phase_signal = phase_signals.get(key, {})
        status = reg.get("status") or ""
        latest_narrative = overlay.get("latest_narrative") or ""
        if not status and latest_narrative:
            status = latest_narrative
        next_beat = src.get("next_beat", "")
        if not next_beat and overlay.get("latest_reason"):
            next_beat = overlay.get("latest_reason", "")

        threads.append({
            "name":         name,
            "phase":        phase_word,
            "phase_raw":    src.get("phase_raw", reg.get("phase", "")),
            "belief":       b,
            "pressure":     src.get("pressure", ""),
            "nothing":      src.get("nothing", ""),
            "next_beat":    next_beat,
            "status":       status,
            "register_notes": reg.get("notes", ""),
            "last_advanced":src.get("last_advanced", ""),
            "born":         born_raw,
            "closed":       closed_raw,
            "age_note":     age_note,
            "npc_anchor":   src.get("npc_anchor", ""),
            "live":         overlay,
            "phase_signal": phase_signal,
        })

    # Sort: climax first, then by belief desc
    def sort_key(t):
        pi = PHASE_ORDER.index(t["phase"]) if t["phase"] in PHASE_ORDER else 0
        return (-pi, -t["belief"])

    threads.sort(key=sort_key)
    return threads


def parse_arc() -> dict:
    text = read(CURRENT_ARC)
    if not text:
        return {}

    def field(pat, default=""):
        m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
        return m.group(1).strip() if m else default

    def section(heading: str) -> str:
        m = re.search(rf'^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)', text,
                      re.MULTILINE | re.DOTALL)
        return m.group(1).strip() if m else ""

    # Arc name from H1. Older writers used an em dash; current ones use a colon.
    name_m = re.search(r'^#\s*(?:Current Arc\s*[:—-]\s*)?(.+)', text, re.MULTILINE)
    name = clean_context(name_m.group(1)) if name_m else "Current Arc"

    register = read(REGISTER_F)
    arc_belief = 0
    arc_register_status = ""
    arc_register_phase = ""
    arc_m = re.search(r'(?m)^## Live Arc\s*\n(.*?)(?=^## |\Z)', register, re.DOTALL)
    if arc_m:
        row_m = re.search(
            r'^\|\s*([^|]+?)\s*\|\s*Arc\s*\|\s*(\d+)\s*\|\s*([^|]*)\s*\|',
            arc_m.group(1), re.MULTILINE | re.IGNORECASE
        )
        if row_m:
            arc_belief = int(row_m.group(2))
            notes = clean_context(row_m.group(3))
            pm = re.search(r'[Pp]hase:\s*([A-Za-z_-]+)(?:\s*[\-–—]\s*(.+))?', notes)
            if pm:
                arc_register_phase = canonical_phase(pm.group(1), "")
                arc_register_status = clean_context(pm.group(2) or "")

    phase   = canonical_phase(field(r'^## Phase:\s*(.+)', arc_register_phase or "setup")).upper()
    day     = field(r'^## Day:\s*(.+)', "?")
    started = field(r'^## Started:\s*(.+)', "?")
    genre   = field(r'^## Genre:\s*(.+)', "")
    premise = section("The Premise")
    pressure = section("The Pressure")
    crisis   = section("The Crisis Point")
    compass  = field(r'^## Compass:\s*(.+)', "")
    if not compass:
        compass = field(r'\*\*(SOUTH|NORTH|EAST|WEST|CENTER)[^*]*\*\*', "?")
    resolution_block = section("Resolution Paths")

    # Extract resolution paths as bullet list
    res_paths =[]
    for line in resolution_block.splitlines():
        m = re.match(r'^-\s+(?:\*\*)?(.+?)(?:\*\*)?:\s*(.+)', line.strip())
        if m:
            res_paths.append({"label": clean_context(m.group(1)), "text": clean_context(m.group(2))})

    seeds = section("Seeds for Next Arc")
    seed_items = [
        clean_context(m.group(1))
        for m in re.finditer(r'^-\s+(.+)', seeds, re.MULTILINE)
    ]

    return {
        "name":        name,
        "phase":       phase,
        "day":         day,
        "started":     started,
        "genre":       genre,
        "belief":      arc_belief,
        "premise":     premise,
        "pressure":    pressure,
        "crisis":      crisis,
        "compass":     compass,
        "resolution":  res_paths,
        "key_npcs":    section("Key NPCs"),
        "nothing":     section("The Nothing's Role"),
        "seeds":       seeds,
        "seed_items":   seed_items,
        "register_status": arc_register_status,
        "register_phase":  arc_register_phase.upper() if arc_register_phase else "",
        "compass_con": section("Wonder Compass Connection"),
    }


def parse_entities() -> tuple[list, list]:
    """Returns (all register entities, talismans)."""
    text = read(REGISTER_F)
    entities, talismans = [], []

    row_re = re.compile(
        r'^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|\s*([^|]*)\s*\|',
        re.MULTILINE
    )
    whisper_re = re.compile(r'^-\s+(.+?)\s+\(([^,]+),\s*Belief\s*(\d+)\)\s*(?:[—-]\s*(.*))?$')

    in_talismans = False
    in_active    = False
    section_title = ""
    section_order = 0
    for line in text.splitlines():
        # Only trigger on actual section headings (line-start ##), not inline mentions
        stripped = line.strip()
        heading_m = re.match(r'^##\s+(.+?)\s*$', stripped)
        if heading_m:
            section_title = heading_m.group(1).strip()
            section_order += 1
        if re.match(r'^## Chapter Talismans', stripped):
            in_talismans = True; in_active = False; continue
        if re.match(r'^## Active Threads', stripped):
            in_active = True; in_talismans = False; continue
        if re.match(r'^## (?!Active Threads|Chapter Talismans)', stripped):
            in_talismans = False; in_active = False

        m = row_re.match(line)
        if not m and section_title.startswith("Whisper Register"):
            m = whisper_re.match(stripped)
            if m:
                name, etype, bstr, notes = m.group(1).strip(), m.group(2).strip(), m.group(3), (m.group(4) or "").strip()
            else:
                continue
        elif m:
            name, etype, bstr, notes = m.group(1).strip(), m.group(2).strip(), m.group(3), m.group(4).strip()
        else:
            continue

        if name.lower() in ("entity", "talisman", "name", "---", ""): continue
        try: b = int(bstr)
        except ValueError: continue

        thread_m = re.search(r'\[thread:([^\]]+)\]', notes)
        threads_tag =[t.strip() for t in thread_m.group(1).split(",")] if thread_m else[]
        clean_notes = re.sub(r'\[thread:[^\]]+\]', '', notes).strip().strip(";").strip()

        if in_talismans:
            chapter = etype.strip().lower()
            tal = {
                "name": name, "chapter": chapter, "belief": b,
                "color": CHAPTER_COLOR.get(chapter, "#555"),
                "philosophy": clean_notes,
            }
            talismans.append(tal)
            etype = "Talisman"
            clean_notes = f"{chapter.title()} — {clean_notes}" if clean_notes else chapter.title()

        entities.append({
            "name": name,
            "type": etype,
            "belief": b,
            "threads": threads_tag,
            "notes": clean_notes,
            "section": section_title or "World Register",
            "section_order": section_order,
            "chapter": etype if in_talismans else "",
        })

    talismans.sort(key=lambda x: -x["belief"])
    return entities, talismans


def parse_player(name: str = "bj") -> dict:
    text = read(PLAYERS_DIR / f"{name}.md")
    if not text: return {}

    def field(pat, default="?"):
        m = re.search(pat, text)
        return m.group(1).strip() if m else default

    # Quests from Inside Cover
    cover_m = re.search(r'## The Inside Cover\n(.*?)(?=\n##|\Z)', text, re.DOTALL)
    quests =[]
    if cover_m:
        for m in re.finditer(r'\|\s*\*\*([^*]+)\*\*\s*\|([^|]*)\|\s*\*\*ACTIVE\*\*', cover_m.group(1)):
            quests.append({"npc": m.group(1).strip(), "desc": m.group(2).strip()})

    # Fae margin
    margin_m = re.search(r'## The Margin\n(.*?)(?=\n##|\Z)', text, re.DOTALL)
    bargains = []
    if margin_m:
        for m in re.finditer(r'^\|\s*([^|*][^|]*)\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|',
                             margin_m.group(1), re.MULTILINE):
            fae, gave, terms, deadline, status =[x.strip() for x in m.groups()]
            if fae and not fae.startswith("*") and not set(fae) <= {"-"}:
                bargains.append({"fae": fae, "gave": gave, "terms": terms, "status": status, "deadline": deadline})

    # Inventory
    inv_m = re.search(r'\*\*Inventory:\*\*\s*\n(.*?)(?=\n-\s*\*\*[A-Z]|\n##|\Z)', text, re.DOTALL)
    inventory =[]
    if inv_m:
        for m in re.finditer(
            r'^\s*-\s*\*\*([^*]+):\*\*\s*(?:\*([^*]*)\*)?\s*(.*)',
            inv_m.group(1), re.MULTILINE
        ):
            inv_name  = m.group(1).strip()
            inv_label = m.group(2).strip() if m.group(2) else ""
            inv_desc  = m.group(3).strip()
            inventory.append({"name": inv_name, "label": inv_label, "desc": inv_desc})

    return {
        "name":      name,
        "inventory": inventory,
        "belief":    field(r'\*\*Belief:\*\*\s*(\d+)', "?"),
        "chapter": field(r'\*\*Chapter:\*\*\s*(\S+)', "?"),
        "tutorial":field(r'\*\*Tutorial Progress:\*\*\s*(\S+)', "?"),
        "quests":  quests,
        "bargains":bargains,
        "compass_total": field(r'\*\*Total runs:\*\*\s*(\d+)', "0"),
        "compass_last":  field(r'\*\*Last run:\*\*\s*(.+)', "never"),
    }


def parse_tick_queue(limit: int = 30) -> list[dict]:
    text = read(QUEUE_F)
    entries =[]
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("*"):
            continue
        if not line.startswith("-"):
            continue

        entry_type = "normal"
        if "[THREAD ESCALATION" in line: entry_type = "escalation"
        elif "[THREAD COOLING"   in line: entry_type = "cooling"
        elif "[THREAD SEED"      in line: entry_type = "seed"
        elif "[FAE DEBT"         in line: entry_type = "fae"
        elif "[PRIORITY: HIGH]"  in line: entry_type = "priority"
        elif "[Pact War"         in line: entry_type = "war"
        elif "[Talisman"         in line: entry_type = "talisman"
        elif "[Belief Investment]" in line: entry_type = "invest"
        elif "[Beat:"            in line: entry_type = "beat"
        elif "[Thread:"          in line: entry_type = "thread"
        elif "[world-pulse]"     in line: entry_type = "pulse"

        entries.append({"text": line[2:].strip(), "type": entry_type})
        if len(entries) >= limit:
            break

    return entries  # already reversed (newest first)


def parse_simulation_feed(limit: int = 40) -> list[dict]:
    if not SIM_LOG_DIR.exists():
        return []
    files = sorted(SIM_LOG_DIR.glob("*.jsonl"))
    if not files:
        return []

    entries = []
    for path in reversed(files):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            entries.append(obj)
            if len(entries) >= limit:
                return entries
    return entries


def parse_tick_action_feed(limit: int = 30) -> list[dict]:
    text = read(QUEUE_F)
    if not text:
        return []
    entries = []
    block_re = re.compile(
        r'(?ms)^## \[world-pulse\](?: \[PRIORITY: HIGH\])?(?: \[[^\]]+\])? (?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2})\n(?P<body>.*?)(?=^## |\Z)'
    )
    raw_re = re.compile(
        r'^\*Raw:\s*(?P<actor>.+?) \[(?P<action>[a-z_]+)/(?P<intensity>[a-z]+)\] on (?P<thread>[^|→\n]+?)(?:\s*→\s*(?P<target>[^|\n]+))?(?:\s*\|\s*pressure:\s*(?P<pressure>.+?))?\*$',
        re.MULTILINE,
    )
    seed_re = re.compile(r'^\*?Narrative seed:?\*?\s*(?P<seed>.+)$', re.MULTILINE)
    for block in reversed(list(block_re.finditer(text))):
        body = block.group("body")
        raw_m = raw_re.search(body)
        if not raw_m:
            continue
        seed_m = seed_re.search(body)
        pressure = raw_m.group("pressure") or ""
        entries.append({
            "id": f"tick-{block.group('ts')}-{len(entries)}",
            "timestamp": block.group("ts").replace(" ", "T") + ":00",
            "source": "tick-queue",
            "kind": "action",
            "trigger": "scheduled",
            "time_tag": "",
            "actor": clean_context(raw_m.group("actor")),
            "actor_kind": "",
            "action": raw_m.group("action"),
            "intensity": raw_m.group("intensity"),
            "thread_name": clean_context(raw_m.group("thread")),
            "target": clean_context(raw_m.group("target") or ""),
            "priority": "HIGH" if "[PRIORITY: HIGH]" in block.group(0) else "NORMAL",
            "raw": clean_context(raw_m.group(0)),
            "narrative": clean_context(seed_m.group("seed") if seed_m else ""),
            "reason": "",
            "hidden_effect": "",
            "influence_snapshot": [clean_context(p) for p in pressure.split(", ") if clean_context(p)],
        })
        if len(entries) >= limit:
            break
    return entries


def parse_pact_actions(limit: int = 30) -> list[dict]:
    if not PACT_ACTION_LOG.exists():
        return []
    entries = []
    try:
        lines = PACT_ACTION_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return []
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        entries.append(obj)
        if len(entries) >= limit:
            break
    return entries


def _thread_key(name: str) -> str:
    return (name or "").strip().lower()


def build_thread_live_overlay(limit: int = 200) -> dict[str, dict]:
    feed = parse_tick_action_feed(limit=40) + parse_simulation_feed(limit=limit)
    feed.sort(key=lambda item: item.get("timestamp", ""), reverse=True)
    overlay: dict[str, dict] = {}

    for entry in feed:
        thread_name = entry.get("thread_name") or entry.get("name")
        if not thread_name:
            continue
        key = _thread_key(thread_name)
        bucket = overlay.setdefault(key, {
            "latest_event": None,
            "latest_action_event": None,
            "events": [],
            "recent_actions": [],
            "last_ts": "",
            "last_action_ts": "",
            "last_actor": "",
            "last_action": "",
            "last_intensity": "",
            "latest_narrative": "",
            "latest_reason": "",
            "latest_hidden_effect": "",
            "latest_target": "",
            "influence_snapshot": [],
            "consequence_summary": [],
        })

        bucket["events"].append(entry)
        ts = entry.get("timestamp", "")
        if ts >= bucket["last_ts"]:
            bucket["latest_event"] = entry
            bucket["last_ts"] = ts

        if entry.get("kind") == "action":
            bucket["recent_actions"].append(entry)
            bucket["recent_actions"] = bucket["recent_actions"][:5]
            if ts >= bucket["last_action_ts"]:
                bucket["latest_action_event"] = entry
                bucket["last_action_ts"] = ts
                bucket["last_actor"] = entry.get("actor", "")
                bucket["last_action"] = entry.get("action", entry.get("kind", ""))
                bucket["last_intensity"] = entry.get("intensity", "")
                bucket["latest_narrative"] = entry.get("narrative", "")
                bucket["latest_reason"] = entry.get("reason", "")
                bucket["latest_hidden_effect"] = entry.get("hidden_effect", "")
                bucket["latest_target"] = entry.get("target", "")
                bucket["influence_snapshot"] = entry.get("influence_snapshot", []) or []
        elif not bucket.get("latest_action_event") and ts >= bucket.get("last_action_ts", ""):
            bucket["last_actor"] = entry.get("actor", "")
            bucket["last_action"] = entry.get("action", entry.get("kind", ""))
            bucket["last_intensity"] = entry.get("intensity", "")
            bucket["latest_narrative"] = entry.get("narrative", "")
            bucket["latest_reason"] = entry.get("reason", "")
            bucket["latest_hidden_effect"] = entry.get("hidden_effect", "")
            bucket["latest_target"] = entry.get("target", "")
            bucket["influence_snapshot"] = entry.get("influence_snapshot", []) or []

        if entry.get("kind") == "consequence":
            story = simulation_story(entry)
            summary = story.get("body") or entry.get("narrative") or entry.get("raw") or ""
            if summary and summary not in bucket["consequence_summary"]:
                bucket["consequence_summary"].append(summary)

    return overlay


def parse_thread_phase_signals() -> dict[str, dict]:
    """Latest tick-queue pressure signal for each thread.

    The register remains authoritative for current phase. These signals show
    where the simulation is pushing next, which is often the more useful card
    context during play.
    """
    text = read(QUEUE_F)
    signals: dict[str, dict] = {}
    current_ts = ""

    for line in text.splitlines():
        tick_m = re.match(r'^## Tick (\d{4}-\d{2}-\d{2} \d{2}:\d{2})', line)
        if tick_m:
            current_ts = tick_m.group(1)
            continue

        m = re.search(
            r'\*\*\[THREAD (ESCALATION|COOLING): ([^\]]+)\]\*\*\s+'
            r'Readiness\s+(\d+)\s+pushes this thread from `([^`]+)` toward `([^`]+)`\.\s*(.+)',
            line,
            re.IGNORECASE,
        )
        if not m:
            continue

        direction, name, readiness, from_phase, toward_phase, why = m.groups()
        signals[_thread_key(name)] = {
            "kind": direction.lower(),
            "name": clean_context(name),
            "readiness": readiness,
            "from": canonical_phase(from_phase, from_phase),
            "toward": canonical_phase(toward_phase, toward_phase),
            "why": clean_context(why),
            "ts": current_ts,
        }

    return signals


def _short_local_ts(ts: str) -> str:
    if not ts:
        return ""
    try:
        return datetime.fromisoformat(ts).strftime("%m-%d %H:%M")
    except Exception:
        return ts


def parse_bleed_status() -> dict:
    today = date.today().strftime("%Y-%m-%d")
    last_issue = ""
    delivered  = False

    if ISSUES_DIR.exists():
        htmls = sorted(ISSUES_DIR.glob("*.html"))
        if htmls:
            last_issue = htmls[-1].stem
            # Check for delivered flag
            flag = ISSUES_DIR / f"{last_issue}.delivered"
            if flag.exists():
                delivered = True
            # Also count as delivered if today's exists and bleed.log says so
            if last_issue == today:
                log = read(LOGS_DIR / "bleed.log")
                if "already published" in log or "Telegram" in log:
                    delivered = True

    issue_n = ""
    num_f = BASE / "bleed" / "issue-number.txt"
    if num_f.exists():
        issue_n = num_f.read_text().strip()

    return {
        "last_issue": last_issue,
        "today": today,
        "is_today": last_issue == today,
        "delivered": delivered,
        "issue_number": issue_n,
    }


ANCHOR_TYPE_META = {
    "REST":   {"dir": "Center", "color": "#0e7490"},
    "EMBARK": {"dir": "East",   "color": "#c2410c"},
    "NOTICE": {"dir": "North",  "color": "#1d4ed8"},
    "SENSE":  {"dir": "South",  "color": "#7c3aed"},
    "WRITE":  {"dir": "West",   "color": "#b45309"},
    "FIND":   {"dir": "Find",   "color": "#15803d"},
}


def latest_anchor_events() -> dict[str, dict]:
    events: dict[str, dict] = {}
    path = LOGS_DIR / "anchor-visits.jsonl"
    if not path.exists():
        return events
    for line in path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except Exception:
            continue
        name = event.get("anchor")
        ts = event.get("timestamp", "")
        if name and ts and ts >= events.get(name, {}).get("timestamp", ""):
            events[name] = event
    return events


def parse_anchors(name: str = "bj") -> list[dict]:
    text = read(BASE / "players" / f"{name}-anchors.md")
    if not text:
        return []
    latest_events = latest_anchor_events()
    anchors =[]
    for section in re.split(r'^## ', text, flags=re.MULTILINE)[1:]:
        lines = section.strip().splitlines()
        anchor_name = lines[0].strip()
        if not anchor_name or anchor_name.startswith("*"):
            continue

        def field(pat, default="", flags=0):
            m = re.search(pat, section, flags)
            return m.group(1).strip() if m else default

        raw_type = field(r'\*\*Type:\*\*\s*(.+)').upper()
        atype    = {
            "FIND": "NOTICE",
            "DISCOVER": "NOTICE",
            "SEARCH": "NOTICE",
            "LOOK": "NOTICE",
        }.get(raw_type, raw_type)
        if atype not in {"NOTICE", "EMBARK", "SENSE", "WRITE", "REST"}:
            atype = "NOTICE"
        belief   = field(r'\*\*Belief invested:\*\*\s*(\d+)', "0")
        created  = field(r'\*\*Created:\*\*\s*(.+)')
        weather  = field(r'\*\*Weather:\*\*\s*(.+)')
        moon     = field(r'\*\*Moon:\*\*\s*(.+)')
        season   = field(r'\*\*Season:\*\*\s*(.+)')
        echo     = field(r'\*\*Academy echo:\*\*\s*(.+)')
        visits   = field(r'\*\*Visit count:\*\*\s*(.+)', "0")
        last_vis = field(r'\*\*Last visited:\*\*\s*(.+)', "*(none yet)*")
        coords   = field(r'\*\*Coordinates:\*\*\s*(.+)')
        radius   = field(r'\*\*Radius meters:\*\*\s*(\d+)', "200")
        event    = latest_events.get(anchor_name, {})
        latest_ts = event.get("timestamp", "")

        anchors.append({
            "name":         anchor_name,
            "type":         atype,
            "belief":       int(belief) if belief.isdigit() else 0,
            "created":      created,
            "weather":      weather,
            "moon":         moon,
            "season":       season,
            "echo":         echo,
            "visits":       visits,
            "last_vis":     last_vis,
            "coords":       coords,
            "radius":       int(radius) if radius.isdigit() else 200,
            "latest_ts":    latest_ts,
            "latest_mode":  event.get("mode", ""),
            "latest_distance": event.get("distance_m", ""),
            "player_words": field(r'\*\*Player[’\']s words:\*\*\s*(.+)'),
            "outer_stacks": field(r'\*\*Outer Stacks room:\*\*\s*(.+)'),
            "fae":          field(r'\*\*Fae:\*\*\s*(.+)'),
            "mini_story":   field(r'\*\*Mini-story:\*\*\s*(.+)'),
            "local_rule":   field(r'\*\*Local rule:\*\*\s*(.+)'),
        })
    return sorted(anchors, key=lambda a: (a.get("latest_ts") or "", a.get("last_vis") or "", a.get("created") or ""), reverse=True)


def _heartbeat_blocks(hb: str) -> dict[str, str]:
    blocks = {}
    for name in ("PULSE", "SPARKY", "DIARY"):
        m = re.search(rf'<!-- {name}_START -->(.*?)<!-- {name}_END -->', hb, re.DOTALL)
        blocks[name.lower()] = m.group(1).strip() if m else ""
    return blocks


def _heartbeat_field(text: str, pat: str, default: str = "") -> str:
    m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
    return m.group(1).strip() if m else default


def parse_current_heartbeat() -> dict:
    hb = read(HEARTBEAT_F)
    blocks = _heartbeat_blocks(hb)
    pulse = blocks.get("pulse") or hb

    def field(pat, default=""):
        return _heartbeat_field(pulse, pat, default)

    def markdown_list_section(heading: str) -> list[dict[str, str]]:
        m = re.search(rf'(?m)^###\s+{re.escape(heading)}\s*\n(.*?)(?=^### |\Z)', pulse, re.DOTALL)
        if not m:
            return []
        rows = []
        last_row = None
        for raw in m.group(1).splitlines():
            line = raw.strip()
            if not line:
                continue
            if line.startswith("- "):
                line = line[2:].strip()
            elif line.startswith("•"):
                line = line[1:].strip()
            else:
                if last_row is not None:
                    last_row["value"] = (last_row["value"] + " " + line).strip()
                continue
            parts = re.split(r'\s+\|\s+(?=\*\*[^*]+:\*\*)', line)
            found = False
            for part in parts:
                bold = re.match(r'\*\*([^*]+):\*\*\s*(.*)', part)
                if bold:
                    last_row = {"label": bold.group(1).strip(), "value": bold.group(2).strip()}
                    rows.append(last_row)
                    found = True
            if found:
                continue
            if last_row is not None and line:
                last_row["value"] = (last_row["value"] + " " + line).strip()
            else:
                last_row = {"label": "", "value": line}
                rows.append(last_row)
        return rows

    pulse_ts = field(r'## Pulse — (.+)')
    pulse_dt = None
    is_stale = False
    if pulse_ts:
        for fmt in ("%I:%M %p, %A %B %d", "%I:%M %p, %A %b %d"):
            try:
                parsed = datetime.strptime(pulse_ts, fmt).replace(year=datetime.now().year)
                pulse_dt = parsed
                break
            except ValueError:
                continue
    if pulse_dt:
        is_stale = (datetime.now() - pulse_dt) > timedelta(hours=24)

    world = [
        {"label": "Belfast Feel", "value": field(r'\*\*Belfast Feel:\*\*\s*(.+)')},
        {"label": "Raw", "value": field(r'\*Raw:\s*(.+?)\*')},
        {"label": "Forecast", "value": field(r'\*\*Forecast:\*\*\s*([\s\S]+?)(?=\n-\s*\*\*|\Z)')},
        {"label": "Season", "value": field(r'\*\*Season:\*\*\s*(.+)')},
        {"label": "Sun", "value": field(r'\*\*Sun:\*\*\s*(.+)')},
        {"label": "Moon", "value": field(r'\*\*Moon:\*\*\s*(.+)')},
        {"label": "Tides", "value": field(r'\*\*Tides:\*\*\s*(.+)')},
        {"label": "Audio", "value": field(r'\*\*Audio:\*\*\s*(.+)')},
    ]
    founder = markdown_list_section("💖 Founder Status (BJ)")
    system = markdown_list_section("🖥️ System")
    business = markdown_list_section("📈 Business (The Doobaleedoos)")

    today = []
    today_m = re.search(r'(?m)^###\s+📅 Today\s*\n(.*?)(?=^### |\Z)', pulse, re.DOTALL)
    if today_m:
        lines = [line.rstrip() for line in today_m.group(1).splitlines() if line.strip()]
        today = [line.strip() for line in lines[:12]]

    sparky = re.sub(r'###[^\n]+\n|\*\d{4}-\d{2}-\d{2}\*\n?', '', blocks.get("sparky", "")).strip()
    diary = []
    for m in re.finditer(r'\*(Diary|Dream)\s*(?:\([^)]+\))?:\*\s*(.+)', blocks.get("diary", "")):
        diary.append({"kind": m.group(1), "text": m.group(2).strip()})

    return {
        "pulse_ts": pulse_ts,
        "stale": is_stale,
        "world": [row for row in world if row["value"]],
        "founder": founder,
        "system": system,
        "business": business,
        "today": today,
        "sparky": sparky,
        "diary": diary,
        "raw": hb.strip(),
    }


def parse_forecast(talismans: list) -> dict:
    hb      = read(HEARTBEAT_F)
    state   = read(BASE / "lore" / "academy-state.md")
    nothing = read(NOTHING_F)
    spine   = read(ARC_SPINE_F)
    whispers_raw = read(LOGS_DIR / "marginalia-whispers.md")

    def field(text, pat, default=""):
        m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
        return m.group(1).strip() if m else default

    def section(text, heading):
        m = re.search(rf'(?m)^{re.escape(heading)}\s*\n(.*?)(?=^#|\Z)', text, re.DOTALL)
        return m.group(1).strip() if m else ""

    # ── Heartbeat ──
    # Extract only the PULSE block
    pulse   = _heartbeat_blocks(hb).get("pulse") or hb

    feel     = field(pulse, r'\*\*Belfast Feel:\*\*\s*(.+)')
    raw_wx   = field(pulse, r'\*Raw:\s*(.+?)\*')
    forecast = field(pulse, r'\*\*Forecast:\*\*\s*([\s\S]+?)(?=\n-\s*\*\*|\Z)')
    season   = field(pulse, r'\*\*Season:\*\*\s*(.+)')
    moon     = field(pulse, r'\*\*Moon:\*\*\s*(.+)')
    tides    = field(pulse, r'\*\*Tides:\*\*\s*(.+)')
    audio    = field(pulse, r'\*\*Audio:\*\*\s*(.+)')
    presence = field(pulse, r'\*\*Presence:\*\*\s*([^|]+)')
    focus    = field(pulse, r'\*\*Focus:\*\*\s*([^\n]+)')
    steps    = field(pulse, r'\*\*Steps:\*\*\s*(.+)')
    pacing   = field(pulse, r'\*\*Pacing:\*\*\s*(.+)')
    task     = field(pulse, r'\*\*Current Task:\*\*\s*(.+)')
    pulse_ts = field(pulse, r'## Pulse — (.+)')

    sparky = ""
    sparky_m = re.search(r'<!-- SPARKY_START -->(.*?)<!-- SPARKY_END -->', hb, re.DOTALL)
    if sparky_m:
        sparky = re.sub(r'###[^\n]+\n|\*\d{4}-\d{2}-\d{2}\*\n?', '', sparky_m.group(1)).strip()

    diary_entries =[]
    diary_m = re.search(r'<!-- DIARY_START -->(.*?)<!-- DIARY_END -->', hb, re.DOTALL)
    if diary_m:
        for m in re.finditer(r'\*(Diary|Dream)\s*\([^)]+\):\*\s*(.+)', diary_m.group(1)):
            diary_entries.append({"kind": m.group(1), "text": m.group(2).strip()})

    # ── Unwritten Whispers ──
    whispers =[]
    w_m = re.search(r'### 📜 Current Whispers from the Unwritten\s*\n(.*?)(?=\n---|\n## |\Z)',
                    state, re.DOTALL)
    if w_m:
        for m in re.finditer(r'^-\s+\*\*([^*]+)\*\*:\s*(.+)', w_m.group(1), re.MULTILINE):
            whispers.append({"title": m.group(1).strip(), "text": m.group(2).strip()})
    if not whispers and whispers_raw:
        for heading_m in re.finditer(
            r'^###\s+(.+?)\s*\n(.*?)(?=^### |\Z)',
            whispers_raw,
            re.MULTILINE | re.DOTALL,
        ):
            category = re.sub(r'^[^\w]+', '', heading_m.group(1)).strip()
            for m in re.finditer(r'^-\s+\*\*([^*:]+):\*\*\s*(.+)', heading_m.group(2), re.MULTILINE):
                title = m.group(1).strip()
                text = m.group(2).strip()
                whispers.append({"title": f"{category}: {title}", "text": text})

    # ── Academy environment ──
    env_rows =[]
    env_m = re.search(r'(?m)^## Environment\s*\n(.*?)(?=^## |\Z)', state, re.DOTALL)
    if env_m:
        for m in re.finditer(r'^\|\s*\*\*([^*]+)\*\*\s*\|\s*([^|]+)\|\s*([^|]*)\|',
                             env_m.group(1), re.MULTILINE):
            loc, st, notes = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
            if loc.lower() not in ("location", "---"):
                env_rows.append({"loc": loc, "state": st, "notes": notes})
    if not env_rows:
        env_m = re.search(r'(?m)^##\s*(?:📍\s*)?Academy Environment\s*\n(.*?)(?=^## |\Z)', state, re.DOTALL)
        if env_m:
            current = None
            notes = []
            for raw_line in env_m.group(1).splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                head_m = re.match(r'^\*\*([^*]+)\*\*\s*(?:[—-]\s*(.+))?$', line)
                if head_m:
                    if current:
                        env_rows.append(current | {"notes": " ".join(notes).strip()})
                    loc = head_m.group(1).strip()
                    state_text = (head_m.group(2) or "active").strip()
                    current = {"loc": loc, "state": state_text}
                    notes = []
                    continue
                if current and line.startswith("-"):
                    notes.append(line.lstrip("- ").strip())
            if current:
                env_rows.append(current | {"notes": " ".join(notes).strip()})

    # ── Nothing ──
    nothing_pressure = field(nothing, r'Pressure level:\s*(.+)')
    nothing_diary    = field(nothing, r'Diary mentions:\s*(\d+)', "0")
    nothing_strategy = ""
    strat_m = re.search(r'## Current Strategy\s*\n(.+?)(?=\n\n|\n##|\Z)', nothing, re.DOTALL)
    if strat_m:
        nothing_strategy = strat_m.group(1).strip()

    pressure_points =[]
    pp_m = re.search(r'## Identified Pressure Points\s*\n(.*?)(?=\n##|\Z)', nothing, re.DOTALL)
    if pp_m:
        for m in re.finditer(r'^-\s+(.+)', pp_m.group(1), re.MULTILINE):
            pressure_points.append(m.group(1).strip())

    # ── Arc spine ──
    belief_state = field(spine, r'Belief:\s*\d+\s*[—-]\s*(.+)')
    ready_for    =[]
    rf_m = re.search(r'## What the Story Is Ready For\s*\n(.*?)(?=\n##|\Z)', spine, re.DOTALL)
    if rf_m:
        for m in re.finditer(r'^-\s+(.+)', rf_m.group(1), re.MULTILINE):
            ready_for.append(m.group(1).strip())

    last_session = ""
    ls_m = re.search(r'## Last Session\s*\n\*[^*\n]+\*\s*\n(.+?)(?=\n##|\Z)', spine, re.DOTALL)
    if ls_m:
        last_session = ls_m.group(1).strip()[:300]

    # ── Cross-reference: verified facts from authoritative files ──
    # Confrontation: check arc-spine / diary for confirmed Nothing confrontation
    confrontation_confirmed = False
    last_confrontation_date = ""
    conf_m = re.search(r'## Last Known Confrontation\s*\n(.*?)(?=\n##|\Z)', nothing, re.DOTALL)
    if conf_m:
        confrontation_confirmed = True
        d_m = re.search(r'\*\*Date:\*\*\s*(.+)', conf_m.group(1))
        if d_m:
            last_confrontation_date = d_m.group(1).strip()
    # Also check arc-spine last session as secondary source
    if not confrontation_confirmed and "confronted" in last_session.lower() and "nothing" in last_session.lower():
        confrontation_confirmed = True

    # Belief investments: sum from anchor files
    anchors_raw = read(BASE / "players" / "bj-anchors.md")
    anchors_belief_total = sum(int(m.group(1)) for m in re.finditer(r'\*\*Belief invested:\*\*\s*(\d+)', anchors_raw))
    anchors_count = len(re.findall(r'^##\s+\S', anchors_raw, re.MULTILINE))

    # Player Belief investment section
    player_raw = read(BASE / "players" / "bj.md")
    has_investments = bool(re.search(r'## Belief Investments\s*\n\s*\|', player_raw))

    # ── Talisman frontrunner ──
    front = talismans[0] if talismans else {}

    return {
        "pulse_ts":        pulse_ts,
        "feel":            feel,
        "raw_wx":          raw_wx,
        "forecast":        forecast.strip(),
        "season":          season,
        "moon":            moon,
        "tides":           tides,
        "audio":           audio,
        "presence":        presence.strip(),
        "focus":           focus.strip(),
        "steps":           steps,
        "pacing":          pacing,
        "task":            task,
        "sparky":          sparky,
        "diary":           diary_entries,
        "whispers":        whispers,
        "env_rows":        env_rows,
        "nothing_pressure":          nothing_pressure,
        "nothing_diary":             nothing_diary,
        "nothing_strategy":          nothing_strategy,
        "pressure_points":           pressure_points,
        "confrontation_confirmed":   confrontation_confirmed,
        "last_confrontation_date":   last_confrontation_date,
        "anchors_belief_total":      anchors_belief_total,
        "anchors_count":             anchors_count,
        "has_investments":           has_investments,
        "belief_state":              belief_state,
        "ready_for":                 ready_for,
        "last_session":              last_session,
        "front":           front,
        "talismans":       talismans,
    }


def _current_block() -> str:
    hr = datetime.now().hour
    if 5  <= hr < 9:  return "early_morning"
    if 9  <= hr < 11: return "morning_class"
    if hr == 11:      return "mid_morning"
    if hr == 12:      return "lunch"
    if 13 <= hr < 15: return "afternoon_class"
    if 15 <= hr < 17: return "free_period"
    if 17 <= hr < 19: return "evening"
    if 19 <= hr < 22: return "club_time"
    return "night"


_SCHEDULE_MODULE = None


def _schedule_module():
    """Load the canonical Academy schedule without making Mission Control brittle."""
    global _SCHEDULE_MODULE
    if _SCHEDULE_MODULE is not None:
        return _SCHEDULE_MODULE
    path = BASE / "scripts" / "schedule.py"
    try:
        spec = importlib.util.spec_from_file_location("enchantify_academy_schedule", path)
        if not spec or not spec.loader:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _SCHEDULE_MODULE = module
        return module
    except Exception:
        return None


def _short_professor(name: str) -> str:
    return re.sub(r"^(?:Prof\.|Professor)\s+", "", name or "").strip()


def _mission_slot_from_canonical(entry):
    if not entry:
        return None
    subject, professor, *_ = entry
    return (subject, _short_professor(professor))


def _canonical_weekly_schedule() -> dict:
    module = _schedule_module()
    if not module or not hasattr(module, "CLASSES") or not hasattr(module, "WEEKDAY_NAMES"):
        return ACADEMY_WEEKLY

    weekly = {}
    for weekday, day_name in enumerate(module.WEEKDAY_NAMES):
        day = module.CLASSES.get(weekday, {})
        club = day.get("club")
        weekly[day_name] = {
            "morning": _mission_slot_from_canonical(day.get("morning")),
            "afternoon": _mission_slot_from_canonical(day.get("afternoon")),
            "club": club[0] if club else None,
        }
    return weekly or ACADEMY_WEEKLY


def parse_schedule() -> dict:
    text  = read(BASE / "lore" / "academy-state.md")
    canonical = _schedule_module()
    live = canonical.get_schedule_data() if canonical and hasattr(canonical, "get_schedule_data") else {}
    today = ACADEMY_DAYS.get(live.get("weekday", date.today().weekday()), ACADEMY_DAYS[6])
    weekly = _canonical_weekly_schedule()

    # Parse live block from academy-state (updated every 4 hours by simulation)
    current_block = live.get("block") or _current_block()
    in_session    = ""
    acad_m = re.search(r'(?m)^## Academics\s*\n(.*?)(?=^## |\Z)', text, re.DOTALL)
    if acad_m:
        blk_m = re.search(r'\*\*Current Block:\*\*\s*(.+)', acad_m.group(1))
        ses_m = re.search(r'\*\*In Session:\*\*\s*(.+)',    acad_m.group(1))
        if blk_m:
            raw = blk_m.group(1).strip().lower().replace(" ", "_")
            for bk, *_ in TIME_BLOCKS:
                if raw == bk or bk.rstrip("_") in raw:
                    current_block = bk; break
        if ses_m:
            in_session = ses_m.group(1).strip()
    if not in_session and live.get("class_now"):
        subject, professor, room = live["class_now"]
        in_session = f"{subject} — {professor}, {room}"

    # Current block meta
    block_meta = next(((bk, name, hrs, desc) for bk, name, hrs, desc in TIME_BLOCKS if bk == current_block), TIME_BLOCKS[-1])

    return {
        "day_name":    today["name"],
        "day_num":     today["num"],
        "tone":        today["tone"],
        "tone_desc":   today["desc"],
        "block_id":    current_block,
        "block_name":  block_meta[1],
        "block_hours": block_meta[2],
        "block_desc":  block_meta[3],
        "in_session":  in_session,
        "today":       weekly.get(today["name"], {}),
        "weekly":      weekly,
    }


def _ms_to_local(ms: int) -> str:
    """Convert epoch-milliseconds to a short local datetime string."""
    try:
        return datetime.fromtimestamp(ms / 1000).strftime("%m-%d %H:%M")
    except Exception:
        return "—"


def _parse_iso_dt(raw: str):
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except Exception:
        return None


def _short_local_ts(raw: str) -> str:
    dt = _parse_iso_dt(raw)
    return dt.strftime("%m-%d %H:%M") if dt else "—"


def _age_label(raw: str) -> str:
    dt = _parse_iso_dt(raw)
    if not dt:
        return "—"
    seconds = max(0, int((datetime.now() - dt).total_seconds()))
    if seconds < 90:
        return f"{seconds}s ago"
    minutes = seconds // 60
    if minutes < 90:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 48:
        return f"{hours}h ago"
    return f"{hours // 24}d ago"


def _cron_interval_minutes(expr: str) -> int:
    parts = (expr or "").split()
    if len(parts) < 5:
        return 0
    minute, hour = parts[0], parts[1]
    if minute.startswith("*/"):
        try:
            return int(minute[2:])
        except ValueError:
            return 0
    if hour.startswith("*/"):
        try:
            return int(hour[2:]) * 60
        except ValueError:
            return 0
    if "," in hour:
        vals = [v for v in hour.split(",") if v.strip().isdigit()]
        if len(vals) >= 2:
            return max(1, round(1440 / len(vals)))
    if hour == "*":
        return 60
    if hour.isdigit():
        return 1440
    return 0


def _cron_overdue(last_raw: str, expr: str) -> tuple[bool, str]:
    interval = _cron_interval_minutes(expr)
    dt = _parse_iso_dt(last_raw)
    if not interval or not dt:
        return False, ""
    age_min = (datetime.now() - dt).total_seconds() / 60
    threshold = max(interval * 1.6, interval + 20)
    if age_min > threshold:
        return True, f"overdue by {int(age_min - interval)}m"
    return False, f"expected every {interval}m"


def parse_steward_health() -> dict[str, dict]:
    """Summarize logs/steward/cron-runs.jsonl by job."""
    by_job: dict[str, dict] = {}
    events = []
    if STEWARD_LOG.exists():
        try:
            lines = STEWARD_LOG.read_text(errors="replace").splitlines()[-800:]
            for line in lines:
                try:
                    ev = json.loads(line)
                except Exception:
                    continue
                if ev.get("job"):
                    events.append(ev)
        except Exception:
            pass

    for ev in events:
        job = ev.get("job", "")
        bucket = by_job.setdefault(job, {
            "job": job,
            "last_event": "",
            "last_at": "",
            "last_start": "",
            "last_finish": "",
            "last_delivery": "",
            "last_skip": "",
            "last_skip_reason": "",
            "last_failure": "",
            "last_error": "",
            "last_duration": "",
            "delivered_count": 0,
            "skipped_count": 0,
            "failed_count": 0,
            "duplicate_skips": 0,
        })
        event = ev.get("event", "")
        at = ev.get("at", "")
        bucket["last_event"] = event
        bucket["last_at"] = at
        if event == "start":
            bucket["last_start"] = at
        elif event == "finished":
            bucket["last_finish"] = at
            if ev.get("duration_s") is not None:
                bucket["last_duration"] = f'{ev.get("duration_s")}s'
        elif event == "delivered":
            bucket["last_delivery"] = at
            bucket["delivered_count"] += 1
        elif event == "skipped":
            reason = ev.get("reason", "")
            bucket["last_skip"] = at
            bucket["last_skip_reason"] = reason
            bucket["skipped_count"] += 1
            if "duplicate" in reason.lower():
                bucket["duplicate_skips"] += 1
        elif event == "failed":
            bucket["last_failure"] = at
            bucket["last_error"] = ev.get("error", "")
            bucket["failed_count"] += 1

    return by_job


def _steward_for_job(label: str, line: str, steward: dict[str, dict]) -> dict:
    if label == "World Simulation":
        return steward.get("world-pulse", {})
    script_to_job = {
        "bleed.py": "bleed",
        "world-pulse.py": "world-pulse",
        "send_academy_dispatch.py": "academy-dispatch",
        "reach-out.py": "reach-out",
        "npc-research.py": "npc-research",
        "dream.py": "dream",
        "sparky.py": "sparky",
        "wallpaper.py": "wallpaper",
    }
    for script, job in script_to_job.items():
        if script in line and job in steward:
            return steward[job]
    label_key = label.lower().replace(" ", "-")
    return steward.get(label_key, {})


def _expected_system_cron_lines() -> list[str]:
    base = str(BASE)
    py = "/usr/bin/python3"
    log = str(LOGS_DIR)
    return [
        f"*/15 * * * * cd {base} && {py} scripts/pulse.py >> {log}/pulse.log 2>&1",
        f"0 */3 * * * cd {base} && {py} scripts/schedule.py --update-state >> {log}/schedule.log 2>&1",
        f"30 */3 * * * cd {base} && {py} scripts/arc-tick.py && {py} scripts/tick.py && {py} scripts/world-pulse.py && {py} scripts/send_academy_dispatch.py >> {log}/pulse.log 2>&1",
        f"3 2 * * * cd {base} && {py} scripts/dream.py >> {log}/dream.log 2>&1",
        f"5 8 * * * {py} {base}/scripts/sparky.py >> {log}/sparky.log 2>&1",
        f"0 7 * * * {py} {base}/scripts/wallpaper.py --generate bj >> {log}/wallpaper.log 2>&1",
        f"10 10,20 * * * cd {base} && {py} scripts/reach-out.py >> {log}/reach-out.log 2>&1",
        f"0 18 * * * cd {base} && {py} scripts/bleed.py >> {log}/bleed.log 2>&1",
        f"0 23 * * * {py} {base}/scripts/labyrinth-intelligence.py bj >> {log}/intelligence.log 2>&1",
    ]


def _system_cron_lines() -> tuple[list[str], bool]:
    try:
        ct = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
        if ct.returncode == 0 and ct.stdout.strip():
            return ct.stdout.splitlines(), True
    except Exception:
        pass
    return _expected_system_cron_lines(), False


def parse_cron_jobs() -> list[dict]:
    jobs =[]
    steward = parse_steward_health()
    try:
        result = subprocess.run([_OPENCLAW, "cron", "list", "--json"],
            capture_output=True, text=True, timeout=10
        )
        data = json.loads(result.stdout)
        items = data if isinstance(data, list) else data.get("jobs", data.get("data",[]))
        for j in items:
            agent = j.get("agentId", j.get("agent_id", ""))
            if agent and "enchantify" not in str(agent).lower():
                continue

            state    = j.get("state", {})
            schedule = j.get("schedule", {})

            last_ms  = state.get("lastRunAtMs", 0)
            next_ms  = state.get("nextRunAtMs", 0)
            status   = state.get("lastRunStatus", state.get("lastStatus", "?"))
            errors   = state.get("consecutiveErrors", 0)
            dur_ms   = state.get("lastDurationMs", 0)
            delivery = state.get("lastDeliveryStatus", "")
            expr     = schedule.get("expr", "")
            tz       = schedule.get("tz", "")

            dur_s = f"{dur_ms // 1000}s" if dur_ms else ""

            label = j.get("name", "?")[:45]
            st = _steward_for_job(label, "", steward)
            jobs.append({
                "name":     j.get("name", "?")[:45],
                "status":   status,
                "errors":   errors,
                "last":     _short_local_ts(st.get("last_at", "")) if st else (_ms_to_local(last_ms) if last_ms else "—"),
                "last_raw": st.get("last_at", "") if st else "",
                "next":     _ms_to_local(next_ms) if next_ms else "—",
                "duration": st.get("last_duration") or dur_s,
                "delivery": "delivered" if st.get("last_delivery") else delivery,
                "expr":     expr,
                "tz":       tz,
                "steward":  st,
                "source":   "openclaw",
                "command":  "",
                "log":      "",
            })
    except Exception:
        pass

    # ── Supplement with system crontab entries for enchantify scripts ─────────
    openclaw_names = {j["name"] for j in jobs}
    _SCRIPT_LABELS = {
        "pulse.py":               "Heartbeat Pulse",
        "reach-out.py":           "Character Outreach",
        "bleed.py":               "The Bleed",
        "sparky.py":              "Sparky Shinies",
        "wallpaper.py":           "Daily Wallpaper",
        "dream.py":               "Dream Weaver",
        "schedule.py":            "Academy Schedule",
        "arc-tick.py":            "Arc Tick",
        "labyrinth-intelligence.py": "Labyrinth Intelligence",
        "mission-control.py":     "Mission Control",
    }
    try:
        cron_lines, from_system = _system_cron_lines()
        for line in cron_lines:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("PATH"):
                continue
            # match any of our scripts
            matched_label = None
            matched_script = ""
            script_items = sorted(_SCRIPT_LABELS.items(), key=lambda item: len(item[0]), reverse=True)
            for script, label in script_items:
                if script in line:
                    matched_label = label
                    matched_script = script
                    break
            if not matched_label:
                continue
            if "world-pulse.py" in line:
                matched_label = "World Simulation"
                matched_script = "world-pulse.py"
            if any(matched_label in name for name in openclaw_names):
                continue  # already in openclaw list
            # parse cron expression (first 5 fields)
            parts = line.split()
            expr = " ".join(parts[:5]) if len(parts) >= 5 else ""
            # check last log file for recency
            log_hint = ""
            log_raw = ""
            log_name = ""
            log_map = {
                "reach-out.py":    "reach-out.log",
                "bleed.py":        "bleed.log",
                "sparky.py":       "sparky.log",
                "wallpaper.py":    "wallpaper.log",
                "dream.py":        "dream.log",
                "schedule.py":     "schedule.log",
                "arc-tick.py":     "pulse.log",
                "pulse.py":        "pulse.log",
                "labyrinth-intelligence.py": "intelligence.log",
                "mission-control.py": "",
            }
            for script, logfile in log_map.items():
                if script in line and logfile:
                    log_name = logfile
                    lp = HEARTBEAT_F if script == "pulse.py" else LOGS_DIR / logfile
                    if lp.exists():
                        mtime = lp.stat().st_mtime
                        from datetime import timezone
                        log_dt = datetime.fromtimestamp(mtime)
                        log_hint = log_dt.strftime("%m-%d %H:%M")
                        log_raw = log_dt.isoformat(timespec="seconds")
                    break
            st = _steward_for_job(matched_label, line, steward)
            steward_last = st.get("last_at", "") if st else ""
            overdue, cadence = _cron_overdue(steward_last or log_raw, expr)
            status = "overdue" if overdue else ("system" if not st else st.get("last_event", "system"))
            jobs.append({
                "name":     matched_label,
                "status":   status,
                "errors":   st.get("failed_count", 0) if st else 0,
                "last":     _short_local_ts(steward_last) if steward_last else (log_hint or "—"),
                "last_raw": steward_last or log_raw,
                "next":     "—",
                "duration": st.get("last_duration", "") if st else "",
                "delivery": "delivered" if st and st.get("last_delivery") else "",
                "expr":     expr,
                "tz":       "",
                "steward":  st,
                "source":   "crontab",
                "cron_source": "system" if from_system else "expected",
                "command":  line,
                "log":      log_name,
                "cadence":  cadence,
                "script":   matched_script,
            })
    except Exception:
        pass

    return jobs


def parse_narrative_health(player_name: str = "bj") -> dict:
    try:
        result = subprocess.run(
            [sys.executable, str(BASE / "scripts" / "narrative-steward.py"), player_name, "--refresh", "--json"],
            cwd=BASE,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return {"status": "ERROR", "score": 0, "findings": [], "error": result.stderr or result.stdout}
        return json.loads(result.stdout)
    except Exception as exc:
        return {"status": "ERROR", "score": 0, "findings": [], "error": str(exc)}


# ── HTML generation ───────────────────────────────────────────────────────────

def phase_bar(phase: str, belief: int) -> str:
    """Return an SVG phase bar showing belief position across four bands."""
    if phase == "permanent":
        return '<div class="phase-bar permanent"><span>permanent</span></div>'

    pct  = min(100, max(0, belief * 1.5))  # rough visual fill (belief 65 = 100%)
    color = PHASE_COLOR.get(phase, "#555")
    label = phase.upper()

    bands =[
        ("#3f3f46", 8,  "D"),
        ("#4e6b8a", 20, "S"),
        ("#92681a", 25, "R"),
        ("#c2410c", 25, "C"),
        ("#15803d", 22, "Re"),
    ]
    band_html = "".join(
        f'<div class="band" style="width:{w}%;background:{c};opacity:0.35" title="{t}"></div>'
        for c, w, t in bands
    )

    return f'''<div class="phase-bar-wrap">
      <div class="phase-bands">{band_html}</div>
      <div class="phase-fill" style="width:{pct:.0f}%;background:{color}"></div>
      <div class="phase-label" style="color:{color}">{label} · {belief}</div>
    </div>'''


def entry_class(t: str) -> str:
    return {
        "escalation": "entry-escalation",
        "cooling":    "entry-cooling",
        "seed":       "entry-seed",
        "fae":        "entry-fae",
        "priority":   "entry-priority",
        "war":        "entry-war",
        "beat":       "entry-beat",
        "thread":     "entry-thread",
        "talisman":   "entry-talisman",
        "invest":     "entry-invest",
        "pulse":      "entry-pulse",
    }.get(t, "entry-normal")


def h(s: str) -> str:
    """HTML-escape."""
    return (str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def modal_attr(title: str, fields: list[tuple[str, str]]) -> str:
    """Build a data-modal attribute value (double-quoted) with JSON popup content."""
    _skip = {"", "—", "-", "?", "*(none yet)*", "never", "0"}
    data = {
        "title": title,
        "fields":[
            {"k": k, "v": str(v)}
            for k, v in fields
            if str(v).strip() not in _skip
        ],
    }
    return '"' + _html.escape(json.dumps(data, ensure_ascii=False)) + '"'


def render_arc_banner(arc: dict) -> str:
    if not arc:
        return ""
    phase = arc.get("phase", "?")
    phase_color = PHASE_COLOR.get(phase.lower(), "#c2410c")
    belief = arc.get("belief", 0)
    belief_pct = min(100, max(0, belief * 1.5))

    res_html = ""
    for r in arc.get("resolution",[]):
        res_html += f'<div class="arc-res-row"><span class="arc-res-label">{h(r["label"])}</span> {h(r["text"])}</div>'

    compass = arc.get("compass", "")
    compass_html = f'<span class="arc-compass">⊕ {h(compass)}</span>' if compass and compass != "?" else ""
    genre_html = f' · {h(arc.get("genre",""))}' if arc.get("genre") else ""
    current_status = arc.get("register_status") or arc.get("nothing") or arc.get("crisis") or ""
    seed_items = arc.get("seed_items", [])[:2]
    if seed_items:
        seeds_html = "".join(f'<div class="arc-res-row"><span class="arc-res-label">Seed</span> {h(seed[:145])}</div>' for seed in seed_items)
    else:
        seeds_html = res_html

    res_full = "\n".join(f'{r["label"]}: {r["text"]}' for r in arc.get("resolution",[]))
    md = modal_attr(arc.get("name", "Arc"),[
        ("Phase",       f'{phase} · Day {arc.get("day","?")} · started {arc.get("started","")}'),
        ("Genre",       arc.get("genre", "")),
        ("Belief",      str(arc.get("belief", 0))),
        ("Compass",     arc.get("compass", "")),
        ("Register status", arc.get("register_status", "")),
        ("Premise",     arc.get("premise", "")),
        ("Pressure",    arc.get("pressure", "")),
        ("Crisis point",arc.get("crisis", "")),
        ("Resolution",  res_full),
        ("Key NPCs",    arc.get("key_npcs", "")),
        ("The Nothing", arc.get("nothing", "")),
        ("Seeds",       arc.get("seeds", "")),
        ("Compass run", arc.get("compass_con", "")),
    ])

    return f'''<div class="arc-banner clickable" style="border-color:{phase_color}44" onclick="openModal(this)" data-modal={md}>
      <div class="arc-header">
        <div>
          <div class="arc-eyebrow">Current Arc{genre_html} · Day {h(arc.get("day","?"))} · {h(arc.get("started",""))}</div>
          <div class="arc-name" style="color:{phase_color}">{h(arc.get("name","?"))}</div>
        </div>
        <div class="arc-right">
          <div class="arc-phase" style="color:{phase_color}">{h(phase)}</div>
          <div class="arc-belief-wrap">
            <div class="arc-belief-track">
              <div class="arc-belief-fill" style="width:{belief_pct:.0f}%;background:{phase_color}"></div>
            </div>
            <div class="arc-belief-label">Belief {belief}</div>
          </div>
          {compass_html}
        </div>
      </div>
      <div class="arc-body">
        <div class="arc-col">
          <div class="arc-section-label">Premise</div>
          <div class="arc-text">{h(arc.get("premise","")[:230])}</div>
        </div>
        <div class="arc-col">
          <div class="arc-section-label">Current Pressure</div>
          <div class="arc-text">{h((arc.get("pressure") or current_status)[:230])}</div>
        </div>
        <div class="arc-col">
          <div class="arc-section-label">Next Seeds</div>
          {seeds_html if seeds_html else "<div class='arc-text muted'>—</div>"}
        </div>
      </div>
    </div>'''


def render_thread_card(t: dict) -> str:
    color  = PHASE_COLOR.get(t["phase"], "#555")
    badge  = f'<span class="badge-new">new</span>' if t["age_note"] == "new" else ""
    anchor = f'<div class="card-anchor">{h(t["npc_anchor"])}</div>' if t["npc_anchor"] else ""
    live   = t.get("live", {}) or {}
    latest_event = live.get("latest_action_event") or live.get("latest_event") or {}
    phase_signal = t.get("phase_signal", {}) or {}

    live_text = live.get("latest_narrative", "")
    live_text_specific = live_text and not is_low_info_live_text(live_text)
    hidden_text = live.get("latest_hidden_effect", "")
    hidden_specific = hidden_text and not is_low_info_effect(hidden_text)
    status_text = t["status"] or ""
    status_specific = status_text and not is_low_info_live_text(status_text)
    next_text = t["next_beat"] or ""
    has_live = bool(live_text)
    live_concrete = ""
    if has_live and not live_text_specific and latest_event:
        live_concrete = concrete_event_body(latest_event, t["name"], status_text)

    live_stamp = _short_local_ts(live.get("last_action_ts") or live.get("last_ts", ""))
    last = live_stamp or h(t["last_advanced"]) if t["last_advanced"] else (live_stamp or "never")
    if not last:
        last = "never"

    nothing_low = "low" in t["nothing"].lower() if t["nothing"] else True
    nothing_dot = f'<span class="nothing-dot" style="color:{("var(--nothing)" if not nothing_low else "var(--muted)")}" title="Nothing pressure: {h(t["nothing"])}">◆</span>'

    live_summary = ""
    if live.get("last_actor"):
        action = live.get("last_action", "")
        intensity = live.get("last_intensity", "")
        target = live.get("latest_target", "")
        bits = [live.get("last_actor", "")]
        if action:
            bits.append(action)
        if intensity:
            bits.append(f'({intensity})')
        if target:
            bits.append(f'→ {target}')
        live_summary = " ".join(bits)

    consequence_summary = "\n".join(live.get("consequence_summary", [])[:3])
    influence_summary = ", ".join(live.get("influence_snapshot", [])[:5])
    recent_action_lines = []
    for action_entry in live.get("recent_actions", [])[:4]:
        story = simulation_story(action_entry)
        when = _short_local_ts(action_entry.get("timestamp", ""))
        title = story.get("title", "")
        body = story.get("body", "")
        hidden = clean_context(action_entry.get("hidden_effect") or "")
        line_bits = [x for x in [when, title, body, f"Mechanism: {hidden}" if hidden and hidden != body else ""] if x]
        if line_bits:
            recent_action_lines.append(" — ".join(line_bits))
    recent_actions_text = "\n\n".join(recent_action_lines)
    phase_signal_text = ""
    if phase_signal:
        phase_signal_text = (
            f'{phase_signal.get("from", "").title()} → {phase_signal.get("toward", "").title()} '
            f'(readiness {phase_signal.get("readiness", "?")})'
        )

    md = modal_attr(t["name"],[
        ("Phase",            f'{t["phase"].title()} · Belief {t["belief"]}'),
        ("Phase signal",     phase_signal_text),
        ("Signal reason",    phase_signal.get("why", "")),
        ("Live now",         live_text if live_text_specific else live_concrete),
        ("Action prose",     live_text if live_text_specific else ""),
        ("How it was done",  hidden_text if hidden_specific else ""),
        ("Latest movement",  live_summary),
        ("Live reason",      "" if is_low_info_effect(live.get("latest_reason", "")) else live.get("latest_reason", "")),
        ("Recent action prose", recent_actions_text),
        ("Current status",   status_text if status_specific else ""),
        ("Next beat",        t["next_beat"]),
        ("Pressure",         t["pressure"]),
        ("Nothing pressure", t["nothing"]),
        ("Recent influences", influence_summary),
        ("Recent consequences", consequence_summary),
        ("NPC anchor",       t["npc_anchor"]),
        ("Born",             t["born"]),
        ("Last advanced",    t["last_advanced"]),
        ("Last phase signal", _short_local_ts(phase_signal.get("ts", ""))),
        ("Last live event",  live_stamp),
        ("Latest raw event", latest_event.get("raw", "")),
    ])

    meta_bits = []
    if live_stamp:
        meta_bits.append(f'live {live_stamp}')
    if t["last_advanced"]:
        meta_bits.append(f'last advanced: {h(t["last_advanced"])}')
    meta = ' · '.join(meta_bits) if meta_bits else 'never advanced'

    beat_parts = []
    if has_live:
        live_detail_parts = []
        if live.get("last_actor"):
            live_detail_parts.append(live.get("last_actor", ""))
        if live.get("last_action"):
            live_detail_parts.append(live.get("last_action", ""))
        if live.get("last_intensity"):
            live_detail_parts.append(f'({live.get("last_intensity", "")})')
        if live.get("latest_target"):
            live_detail_parts.append(f'→ {live.get("latest_target", "")}')
        live_detail = " ".join(live_detail_parts)
        live_line = f'<div style="margin-bottom:.22rem"><span style="color:var(--seed);font-weight:700;font-size:.72rem;letter-spacing:.04em">LIVE</span> <span style="font-size:.78rem">{h(live_detail)}</span>'
        if live_stamp:
            live_line += f' <span class="muted" style="font-size:.72rem">{h(live_stamp)}</span>'
        live_line += '</div>'
        beat_parts.append(live_line)
        if live_text_specific:
            beat_parts.append(f'<div style="margin-bottom:.22rem">{h(live_text[:280])}</div>')
        elif live_concrete:
            beat_parts.append(f'<div style="margin-bottom:.22rem">{h(live_concrete[:280])}</div>')
        if hidden_specific and hidden_text != live_text:
            beat_parts.append(f'<div style="margin-bottom:.22rem;color:var(--muted);font-size:.8rem"><span class="muted">Mechanism:</span> {h(hidden_text[:220])}</div>')

    if phase_signal:
        signal_line = (
            f'{phase_signal.get("from", "").title()} → {phase_signal.get("toward", "").title()}'
            f' · readiness {phase_signal.get("readiness", "?")}'
        )
        beat_parts.append(
            f'<div style="color:var(--seed);font-size:.8rem"><span class="muted">Phase pressure:</span> {h(signal_line)}</div>'
        )

    if status_specific:
        planned_label = 'Register' if has_live else 'Current'
        planned_style = 'color:var(--muted);font-size:.82rem' if has_live else ''
        beat_parts.append(f'<div style="{planned_style}"><span class="muted">{planned_label}:</span> {h(status_text[:185])}</div>')
    if next_text and next_text != status_text:
        next_style = 'color:var(--muted);font-size:.8rem' if beat_parts else ''
        beat_parts.append(f'<div style="{next_style}"><span class="muted">Hook:</span> {h(next_text[:245])}</div>')

    beat_html = ''.join(beat_parts) if beat_parts else '—'

    return f'''<div class="card clickable" style="border-color:{color}22;--phase-color:{color}" onclick="openModal(this)" data-modal={md}>
      <div class="card-header">
        <div class="card-title" style="color:{color}">{h(t["name"])}{badge}</div>
        {nothing_dot}
      </div>
      {anchor}
      {phase_bar(t["phase"], t["belief"])}
      <div class="card-beat">{beat_html}</div>
      <div class="card-meta">{meta}</div>
    </div>'''


def render_talisman_bar(tal: dict, max_belief: int) -> str:
    pct   = min(100, int(tal["belief"] / max(max_belief, 1) * 100))
    color = tal["color"]
    return f'''<div class="tal-row">
      <div class="tal-name" style="color:{color}">{h(tal["name"])}</div>
      <div class="tal-bar-wrap">
        <div class="tal-bar" style="width:{pct}%;background:{color}"></div>
      </div>
      <div class="tal-belief">{tal["belief"]}</div>
      <div class="tal-chapter" style="color:{color}">{h(tal["chapter"].title())}</div>
    </div>'''


def render_entity_row(e: dict) -> str:
    b = e["belief"]
    if b >= 30:   dot, dc = "●●●", "var(--climax)"
    elif b >= 15: dot, dc = "●●○", "var(--rising)"
    elif b >= 5:  dot, dc = "●○○", "var(--setup)"
    else:         dot, dc = "○○○", "var(--muted)"

    thread_tags = " ".join(
        f'<span class="tag">{h(tid)}</span>'
        for tid in e["threads"]
        if tid != "academy-daily"
    ) if e["threads"] else ""

    threads_str = ", ".join(e["threads"]) if e["threads"] else ""
    md = modal_attr(e["name"],[
        ("Type",    e["type"]),
        ("Belief",  str(b)),
        ("Register section", e.get("section", "")),
        ("Threads", threads_str),
        ("Notes",   e["notes"]),
    ])

    return f'''<tr class="clickable" onclick="openModal(this)" data-modal={md}>
      <td><span style="color:{dc};font-size:.7rem">{dot}</span></td>
      <td class="ent-name">{h(e["name"])}</td>
      <td class="ent-type muted">{h(e["type"])}</td>
      <td class="ent-belief">{b}</td>
      <td class="ent-tags">{thread_tags}</td>
    </tr>'''


def render_entity_sections(entities: list[dict]) -> str:
    if not entities:
        return '<div class="muted">No world-register entities found.</div>'
    grouped: dict[str, list[dict]] = {}
    order: dict[str, int] = {}
    for e in entities:
        section = e.get("section") or "World Register"
        grouped.setdefault(section, []).append(e)
        order.setdefault(section, int(e.get("section_order") or 999))

    parts = [
        f'<div class="entity-summary">{len(entities)} registered entities · includes threads, talismans, NPCs, locations, tools, objects, fae, and whispers</div>'
    ]
    for section in sorted(grouped, key=lambda s: order.get(s, 999)):
        rows = grouped[section]
        body = "".join(render_entity_row(e) for e in rows)
        parts.append(f'''
        <div class="entity-section">
          <div class="entity-section-head">{h(section)} <span>{len(rows)}</span></div>
          <table class="ent-table"><tbody>{body}</tbody></table>
        </div>''')
    return "\n".join(parts)


def render_queue_entry(entry: dict) -> str:
    css  = entry_class(entry["type"])
    text = h(entry["text"])
    # Bold any **..** markers
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    # Italicise *..* markers
    text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
    return f'<div class="entry {css}">{text}</div>'


def render_simulation_entry(entry: dict) -> str:
    kind = entry.get("kind", "action")
    priority = (entry.get("priority") or "NORMAL").upper()
    css = "entry-priority" if priority == "HIGH" else "entry-pulse"
    story = simulation_story(entry)

    ts = entry.get("timestamp", "")
    when = ""
    if ts:
        when = ts.replace("T", " ")[:16]
    trigger = entry.get("trigger") or "scheduled"
    time_tag = entry.get("time_tag") or ""
    header_bits = [b for b in [when, trigger, time_tag] if b]
    header = " · ".join(header_bits)

    detail = story.get("detail", "")
    detail_html = f'<div class="sim-detail muted">{h(detail)}</div>' if detail else ""
    pressure = story.get("pressure", "")
    pressure_html = f'<div class="sim-meta muted">pressure: {h(pressure)}</div>' if pressure else ""
    reason = story.get("reason", "")
    reason_html = ""
    if reason and reason != story.get("body") and not is_low_info_effect(reason):
        reason_html = f'<div class="sim-reason"><span class="muted">why</span> {h(reason)}</div>'

    if kind == "action":
        raw_bits = []
        if entry.get("actor_kind"):
            raw_bits.append(entry.get("actor_kind", ""))
        if entry.get("action"):
            raw_bits.append(entry.get("action", "").replace("_", " "))
        raw_html = f'<div class="sim-raw muted">{h(" · ".join(raw_bits))}</div>' if raw_bits else ""
        body = (
            f'<div class="sim-title">{h(story.get("title", ""))}</div>'
            f'{detail_html}'
            f'<div class="sim-narrative">{h(story.get("body", ""))}</div>'
            f'{reason_html}{pressure_html}{raw_html}'
        )
    elif kind == "consequence":
        body = (
            f'<div class="sim-title">{h(story.get("title", ""))}</div>'
            f'{detail_html}'
            f'<div class="sim-narrative">{h(story.get("body", ""))}</div>'
        )
    else:
        title = story.get("title") or entry.get("raw", kind)
        body_text = story.get("body") or entry.get("narrative", "")
        pressure_html_else = pressure_html if pressure else ""
        body = f"<div class=\"sim-title\">{h(title)}</div>{detail_html}<div class=\"sim-narrative\">{h(body_text)}</div>{pressure_html_else}"

    header_html = f'<div class="sim-header muted">{h(header)}</div>' if header else ""
    return f'<div class="entry {css} sim-entry">{header_html}{body}</div>'


def render_pact_action(entry: dict) -> str:
    event = entry.get("event", "")
    chapter = entry.get("chapter", "Unknown")
    app = entry.get("app", "")
    tier = entry.get("tier", "")
    action_type = entry.get("action_type", "")
    dry = "dry-run" if entry.get("dry_run") else "live"
    when = (entry.get("timestamp") or "").replace("T", " ")[:16]
    title_bits = [chapter]
    if app:
        title_bits.append(f"→ {app}")
    if tier:
        title_bits.append(f"({tier})")
    title = " ".join(title_bits)

    css = {
        "failed": "entry-priority",
        "skipped": "entry-war",
        "consent_required": "entry-war",
        "executed": "entry-pulse",
        "planned": "entry-seed",
        "spec_generated": "entry-seed",
        "spec_fallback": "entry-war",
    }.get(event, "entry-normal")

    detail_bits = [x for x in [when, event.replace("_", " "), action_type.replace("_", " "), dry] if x]
    result = entry.get("result") or entry.get("proposal") or entry.get("reason") or entry.get("error") or ""
    driver = entry.get("driver", "")
    extra = []
    if driver:
        extra.append(f"driver: {driver}")
    if entry.get("war_subtype"):
        extra.append(f"war: {entry.get('war_subtype')}")
    if entry.get("consent_id"):
        extra.append(f"consent: {entry.get('consent_id')}")
    if entry.get("telegram_sent") is not None:
        extra.append(f"telegram: {'sent' if entry.get('telegram_sent') else 'not sent'}")
    if entry.get("before") is not None and entry.get("after") is not None:
        extra.append(f"{entry.get('before')} -> {entry.get('after')}")
    if entry.get("silent"):
        extra.append("silent")
    extra_html = f'<div class="sim-meta muted">{h("; ".join(extra))}</div>' if extra else ""

    return (
        f'<div class="entry {css} sim-entry">'
        f'<div class="sim-header muted">{h(" · ".join(detail_bits))}</div>'
        f'<div class="sim-title">{h(title)}</div>'
        f'<div class="sim-narrative">{h(result)}</div>'
        f'{extra_html}'
        f'</div>'
    )


def render_anchor_card(a: dict) -> str:
    meta      = ANCHOR_TYPE_META.get(a["type"], {"dir": "?", "color": "#555"})
    color     = meta["color"]
    direction = meta["dir"]
    visits    = a["visits"] if a["visits"] != "0" else "unvisited"
    last      = "" if "none yet" in a["last_vis"] else f" · last {h(a['last_vis'])}"
    echo      = h(a["echo"][:140]) if a["echo"] else "—"

    md = modal_attr(a["name"],[
        ("Type",               f'{a["type"]} · {direction}'),
        ("Belief invested",    str(a["belief"])),
        ("Trigger radius",      f'{a["radius"]} meters'),
        ("Created",            a["created"]),
        ("Season / Weather",   f'{a["season"]} · {a["weather"]}'),
        ("Moon",               a["moon"]),
        ("Coordinates",        a["coords"]),
        ("Latest activity",     f'{a["latest_mode"]} · {a["latest_ts"]}' if a.get("latest_ts") else ""),
        ("Latest distance",     f'{a["latest_distance"]}m' if a.get("latest_distance") != "" else ""),
        ("Player's words",     a["player_words"]),
        ("Academy echo",       a["echo"]),
        ("Outer Stacks room",  a["outer_stacks"]),
        ("Fae",                a["fae"]),
        ("Mini-story",         a["mini_story"]),
        ("Local rule",         a["local_rule"]),
        ("Visits",             f'{a["visits"]} · last: {a["last_vis"]}'),
    ])

    return f'''<div class="anchor-card clickable" style="border-color:{color}33;--anchor-color:{color}" onclick="openModal(this)" data-modal={md}>
      <div class="anchor-header">
        <div class="anchor-name" style="color:{color}">{h(a["name"])}</div>
        <div class="anchor-type" style="color:{color}">{h(a["type"])} <span class="anchor-dir">· {h(direction)}</span></div>
      </div>
      <div class="anchor-echo">{echo}</div>
      <div class="anchor-meta">
        <span class="anchor-stat">belief {a["belief"]}</span>
        <span class="anchor-stat muted">radius {a["radius"]}m</span>
        <span class="anchor-stat muted">{h(a["season"])} · {h(a["moon"].split("(")[0].strip())}</span>
        <span class="anchor-stat muted">{visits}{last}</span>
      </div>
    </div>'''


def render_forecast_tab(f: dict) -> str:
    # ── World bar ──
    moon_txt  = f["moon"].split("|")[0].strip() if f["moon"] else "—"
    audio_txt = f["audio"] or "quiet"
    is_music  = audio_txt.lower() not in ("quiet", "the house is quiet.", "")
    audio_color = "var(--seed)" if is_music else "var(--muted)"

    world_md = modal_attr("The World Right Now", [
        ("Feel",     f["feel"]),
        ("Raw",      f["raw_wx"]),
        ("Forecast", f["forecast"]),
        ("Season",   f["season"]),
        ("Moon",     f["moon"]),
        ("Tides",    f["tides"]),
        ("Audio",    f["audio"]),
        ("Updated",  f["pulse_ts"]),
    ])
    world_html = f'''<div class="fc-world clickable" onclick="openModal(this)" data-modal={world_md}>
      <div class="fc-world-feel">{h(f["feel"] or "—")}</div>
      <div class="fc-world-row">
        <span class="fc-pill fc-moon">🌑 {h(moon_txt)}</span>
        <span class="fc-pill fc-season">{h(f["season"].split("—")[0].strip() if f["season"] else "—")}</span>
        <span class="fc-pill fc-audio" style="color:{audio_color}">♪ {h(audio_txt[:40])}</span>
      </div>
      {f'<div class="fc-forecast muted">{h(f["forecast"][:120])}…</div>' if f["forecast"] else ""}
    </div>'''

    # ── Nothing ──
    # Strip markdown bold markers and take just the first word/phrase for the badge label
    np_raw = re.sub(r'\*+', '', f["nothing_pressure"]).strip()
    np_label = np_raw.split("—")[0].strip().split(".")[0].strip()
    np = np_label.lower()
    nothing_color = "var(--climax)" if "high" in np else ("var(--seed)" if "retreating" in np else ("var(--rising)" if "medium" in np else "var(--muted)"))
    # Filter out struck-through (overturned) pressure points from display
    active_pp = [p for p in f["pressure_points"] if not p.startswith("~~")]
    pp_items = "".join(f'<li>{h(p[:140])}</li>' for p in active_pp)

    # Verified fact badges
    conf_badge = ""
    if f["confrontation_confirmed"]:
        conf_date = f' · {h(f["last_confrontation_date"])}' if f["last_confrontation_date"] else ""
        conf_badge = f'<span class="fc-badge" style="background:var(--seed)22;color:var(--seed)">confronted{conf_date}</span>'
    inv_badge = ""
    if f["anchors_belief_total"] > 0:
        inv_badge = f'<span class="fc-badge" style="background:var(--seed)22;color:var(--seed)">{f["anchors_belief_total"]} Belief anchored · {f["anchors_count"]} anchors</span>'

    nothing_md = modal_attr("The Nothing",[
        ("Pressure level",     f["nothing_pressure"]),
        ("Diary mentions",     f["nothing_diary"]),
        ("Last confrontation", f["last_confrontation_date"] if f["confrontation_confirmed"] else "never"),
        ("Belief anchored",    f'{f["anchors_belief_total"]} across {f["anchors_count"]} anchor(s)' if f["anchors_belief_total"] > 0 else "none"),
        ("Strategy",           f["nothing_strategy"]),
        ("Active pressure points", "\n".join(active_pp) if active_pp else "—"),
    ])
    nothing_html = f'''<div class="fc-block clickable" onclick="openModal(this)" data-modal={nothing_md}>
      <div class="fc-block-header">
        <span class="fc-block-title">The Nothing</span>
        <span class="fc-badge" style="background:{nothing_color}22;color:{nothing_color}">{h(np_label)}</span>
        {conf_badge}{inv_badge}
      </div>
      <div class="fc-nothing-strategy muted">{h(f["nothing_strategy"][:140]) if f["nothing_strategy"] else "—"}</div>
      {f'<ul class="fc-bullets">{pp_items}</ul>' if pp_items else ""}
    </div>'''

    # ── Talisman frontrunner ──
    front    = f["front"]
    tal_list = f["talismans"]
    front_color = front.get("color", "#555") if front else "#555"
    front_name  = front.get("name", "—")     if front else "—"
    front_ch    = front.get("chapter", "")    if front else ""
    front_b     = front.get("belief", 0)      if front else 0
    front_philo = front.get("philosophy", "") if front else ""
    max_b = tal_list[0]["belief"] if tal_list else 1
    bar_rows = "".join(
        f'<div class="fc-tal-row"><span class="fc-tal-name" style="color:{t["color"]}">{h(t["name"])}</span>'
        f'<div class="fc-tal-bar-wrap"><div class="fc-tal-bar" style="width:{int(t["belief"]/max(max_b,1)*100)}%;background:{t["color"]}"></div></div>'
        f'<span class="fc-tal-b">{t["belief"]}</span></div>'
        for t in tal_list
    )
    tal_md = modal_attr("Talisman War",[
        ("Frontrunner",  f'{front_name} ({front_ch.title()}) — Belief {front_b}'),
        ("Philosophy",   front_philo),
    ] + [(t["name"], f'{t["chapter"].title()} · Belief {t["belief"]} — {t["philosophy"]}') for t in tal_list])
    tal_html = f'''<div class="fc-block clickable" onclick="openModal(this)" data-modal={tal_md}>
      <div class="fc-block-header">
        <span class="fc-block-title">Talisman War</span>
        <span class="fc-badge" style="background:{front_color}22;color:{front_color}">{h(front_name)}</span>
      </div>
      <div class="fc-philo muted">{h(front_philo[:100]) if front_philo else "—"}</div>
      <div class="fc-tal-bars">{bar_rows}</div>
    </div>'''

    # ── Dramatic spine ──
    rf_items = "".join(f'<li>{h(r[:140])}</li>' for r in f["ready_for"])
    spine_md = modal_attr("Dramatic Spine",[
        ("Belief state",  f["belief_state"]),
        ("Ready for",     "\n".join(f["ready_for"])),
        ("Last session",  f["last_session"]),
    ])
    spine_html = f'''<div class="fc-block clickable" onclick="openModal(this)" data-modal={spine_md}>
      <div class="fc-block-header">
        <span class="fc-block-title">Dramatic Spine</span>
        <span class="fc-badge fc-badge-neutral">{h(f["belief_state"])}</span>
      </div>
      {f'<ul class="fc-bullets">{rf_items}</ul>' if rf_items else '<div class="muted">—</div>'}
    </div>'''

    # ── Whispers ──
    whisper_items = ""
    for w in f["whispers"][:12]:
        wmd = modal_attr(w["title"],[("Whisper", w["text"])])
        whisper_items += f'<div class="fc-whisper clickable" onclick="openModal(this)" data-modal={wmd}><span class="fc-whisper-title">{h(w["title"])}</span><span class="fc-whisper-text muted">{h(w["text"][:90])}…</span></div>'
    whispers_html = f'''<div class="fc-block">
      <div class="fc-block-header"><span class="fc-block-title">Unwritten Whispers</span><span class="fc-badge fc-badge-neutral">{len(f["whispers"])} active</span></div>
      <div class="fc-whispers">{whisper_items or '<div class="muted">The Margin is quiet.</div>'}</div>
    </div>'''

    # ── Founder ──
    diary_html = ""
    for d in f["diary"]:
        kind_color = "#a78bfa" if d["kind"] == "Dream" else "var(--text)"
        diary_html += f'<div class="fc-diary-entry"><span class="fc-diary-kind" style="color:{kind_color}">{h(d["kind"])}</span> <span class="muted">{h(d["text"][:110])}…</span></div>'

    sparky_html = f'<div class="fc-sparky">{h(f["sparky"][:160])}…</div>' if f["sparky"] else ""

    founder_md = modal_attr("Founder Status",[
        ("Presence",  f["presence"]),
        ("Focus",     f["focus"]),
        ("Pacing",    f["pacing"]),
        ("Steps",     f["steps"]),
        ("Task",      f["task"]),
        ("Sparky",    f["sparky"]),
    ] + [(d["kind"], d["text"]) for d in f["diary"]])
    founder_html = f'''<div class="fc-block clickable" onclick="openModal(this)" data-modal={founder_md}>
      <div class="fc-block-header">
        <span class="fc-block-title">Founder</span>
        <span class="fc-badge fc-badge-neutral">{h(f["presence"])} · {h(f["focus"])}</span>
      </div>
      <div class="fc-founder-stats">
        <span class="fc-stat"><span class="muted">steps</span> {h(f["steps"])}</span>
        <span class="fc-stat"><span class="muted">pacing</span> {h(f["pacing"].split("—")[0].strip() if f["pacing"] else "—")}</span>
        <span class="fc-stat"><span class="muted">task</span> {h(f["task"][:30])}</span>
      </div>
      {sparky_html}
      {diary_html}
    </div>'''

    # ── Academy environment ──
    env_items = ""
    for row in f["env_rows"]:
        is_stirred = "STIRRED" in row["state"].upper()
        state_color = "var(--rising)" if is_stirred else "var(--muted)"
        env_md = modal_attr(row["loc"], [("State", row["state"]), ("Notes", row["notes"])])
        env_items += f'<div class="fc-env-row clickable" onclick="openModal(this)" data-modal={env_md}><span class="fc-env-loc">{h(row["loc"])}</span><span class="fc-env-state" style="color:{state_color}">{h(row["state"][:30])}</span></div>'
    env_html = f'''<div class="fc-block">
      <div class="fc-block-header"><span class="fc-block-title">Academy Environment</span></div>
      {env_items or '<div class="muted">No environment data.</div>'}
    </div>'''

    return f'''
    {world_html}
    <div class="fc-grid">
      {nothing_html}
      {tal_html}
    </div>
    {spine_html}
    {whispers_html}
    <div class="fc-grid">
      {founder_html}
      {env_html}
    </div>'''


def render_heartbeat_tab(hb: dict) -> str:
    if not hb:
        return '<div class="muted">No heartbeat data.</div>'

    status_color = "var(--rising)" if hb.get("stale") else "var(--seed)"
    status_label = "stale" if hb.get("stale") else "live"
    raw_md = modal_attr("HEARTBEAT.md", [
        ("Updated", hb.get("pulse_ts", "")),
        ("Status", status_label),
        ("Raw heartbeat", hb.get("raw", "")),
    ])

    def rows(items: list[dict[str, str]], *, compact: bool = False) -> str:
        html = ""
        for item in items:
            label = item.get("label", "")
            value = item.get("value", "")
            if not value:
                continue
            cls = "hb-row hb-row-compact" if compact else "hb-row"
            html += f'<div class="{cls}"><span class="hb-label">{h(label)}</span><span class="hb-value">{h(value)}</span></div>'
        return html or '<div class="muted">—</div>'

    world_rows = rows(hb.get("world", []))
    founder_rows = rows(hb.get("founder", []))
    system_rows = rows(hb.get("system", []), compact=True)
    business_rows = rows(hb.get("business", []), compact=True)

    today_items = "".join(f'<li>{h(line)}</li>' for line in hb.get("today", []))
    today_html = f'<ul class="hb-list">{today_items}</ul>' if today_items else '<div class="muted">Nothing scheduled in the pulse.</div>'

    sparky = hb.get("sparky", "")
    sparky_html = f'<div class="hb-note hb-sparky">{h(sparky)}</div>' if sparky else '<div class="muted">Sparky has not left a note in this pulse.</div>'

    diary_bits = ""
    for entry in hb.get("diary", []):
        color = "#7c3aed" if entry.get("kind") == "Dream" else "var(--sepia)"
        diary_bits += f'<div class="hb-note"><span class="hb-note-kind" style="color:{color}">{h(entry.get("kind",""))}</span>{h(entry.get("text",""))}</div>'
    diary_html = diary_bits or '<div class="muted">No diary or dream excerpt in the current heartbeat.</div>'

    return f'''
    <div class="heartbeat-head clickable" onclick="openModal(this)" data-modal={raw_md}>
      <div>
        <div class="heartbeat-title">Current Heartbeat</div>
        <div class="heartbeat-sub muted">The real-world pulse the Labyrinth is bleeding into story texture.</div>
      </div>
      <div class="heartbeat-stamp" style="color:{status_color}">
        <span>{h(status_label.upper())}</span>
        <span class="muted">{h(hb.get("pulse_ts","—"))}</span>
      </div>
    </div>
    <div class="heartbeat-grid">
      <div class="hb-block hb-block-wide">
        <div class="fc-block-title">World Right Now</div>
        {world_rows}
      </div>
      <div class="hb-block">
        <div class="fc-block-title">Founder Status</div>
        {founder_rows}
      </div>
      <div class="hb-block">
        <div class="fc-block-title">Today</div>
        {today_html}
      </div>
      <div class="hb-block">
        <div class="fc-block-title">Sparky Says</div>
        {sparky_html}
      </div>
      <div class="hb-block">
        <div class="fc-block-title">Diary & Dream</div>
        {diary_html}
      </div>
      <div class="hb-block">
        <div class="fc-block-title">System</div>
        {system_rows}
      </div>
      <div class="hb-block">
        <div class="fc-block-title">Business</div>
        {business_rows}
      </div>
    </div>'''


def render_schedule_tab(sched: dict) -> str:
    block_color = BLOCK_COLORS.get(sched["block_id"], "#374151")
    session_txt = sched["in_session"] or "No mandatory class this block."

    # ── NOW bar ──
    now_html = f'''<div class="sched-now" style="border-color:{block_color};background:{block_color}18">
      <div class="sched-now-left">
        <div class="sched-now-block" style="color:{block_color}">{h(sched["block_name"].upper())}</div>
        <div class="sched-now-hours muted">{h(sched["block_hours"])}</div>
        <div class="sched-now-desc muted">{h(sched["block_desc"])}</div>
      </div>
      <div class="sched-now-right">
        <div class="sched-now-day" style="color:{block_color}">{h(sched["day_name"])} · Day {sched["day_num"]}</div>
        <div class="sched-now-tone">{h(sched["tone"])}</div>
        <div class="sched-now-session">{h(session_txt)}</div>
      </div>
    </div>'''

    # ── Today's slots ──
    def class_slot(label: str, slot_key: str, time_str: str) -> str:
        entry = sched["today"].get(slot_key)
        if not entry:
            return f'<div class="sched-slot sched-slot-empty"><span class="sched-slot-time muted">{h(time_str)}</span><span class="muted">—</span></div>'
        if isinstance(entry, tuple):
            name, prof = entry
            info  = CLASS_INFO.get(name, {})
            color = info.get("color", "#555")
            prof_str = f"Prof. {prof}" if prof else ""
            md = modal_attr(name,[
                ("Compass",    info.get("compass", "")),
                ("Professor",  prof_str),
                ("About",      info.get("desc", "")),
                ("Assignment", info.get("assignment", "")),
                ("Reward",     info.get("reward", "")),
                ("Quote",      info.get("quote", "")),
            ])
            return f'''<div class="sched-slot clickable" style="border-color:{color}44" onclick="openModal(this)" data-modal={md}>
              <span class="sched-slot-time muted">{h(time_str)}</span>
              <span class="sched-slot-name" style="color:{color}">{h(name)}</span>
              <span class="sched-slot-prof muted">{h(prof_str)}</span>
              <span class="sched-slot-compass muted">{h(info.get("compass",""))}</span>
            </div>'''
        else:
            return f'<div class="sched-slot"><span class="sched-slot-time muted">{h(time_str)}</span><span class="sched-slot-name">{h(entry)}</span></div>'

    today_html = f'''<div class="sched-today-header">
      <span class="sched-section-label">Today — {h(sched["day_name"])}</span>
      <span class="sched-tone-badge">{h(sched["tone"])}</span>
    </div>
    <div class="sched-slots">
      {class_slot("Morning",   "morning",   "9–11 AM")}
      {class_slot("Afternoon", "afternoon", "1–3 PM")}
      {class_slot("Club",      "club",      "7 PM")}
    </div>'''

    # ── Weekly grid ──
    day_order = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]
    week_cols = ""
    for dname in day_order:
        day_data  = next((v for k, v in ACADEMY_DAYS.items() if v["name"] == dname), {})
        slots     = sched.get("weekly", {}).get(dname, ACADEMY_WEEKLY.get(dname, {}))
        is_today  = dname == sched["day_name"]
        col_style = "border-color:#7c3aed44;background:#7c3aed08" if is_today else ""

        def mini_class(slot_key):
            e = slots.get(slot_key)
            if not e: return '<span class="sched-mini-empty muted">—</span>'
            if isinstance(e, tuple):
                nm, pr = e
                c = CLASS_INFO.get(nm, {}).get("color", "#555")
                return f'<span class="sched-mini-class" style="color:{c}" title="{nm}">{h(nm[:18])}</span>'
            return f'<span class="sched-mini-class muted">{h(e)}</span>'

        tone_md = modal_attr(f'{dname} · Day {day_data.get("num","?")}',[
            ("Tone",        day_data.get("tone", "")),
            ("Character",   day_data.get("desc", "")),
            ("Morning",     (slots.get("morning") or ("—",))[0] if slots.get("morning") else "—"),
            ("Afternoon",   (slots.get("afternoon") or ("—",))[0] if slots.get("afternoon") else "—"),
            ("Club",        slots.get("club") or "—"),
        ])

        col_cls      = "sched-day-col sched-day-today" if is_today else "sched-day-col"
        col_name_cls = "sched-day-col-name sched-day-col-name-today" if is_today else "sched-day-col-name"
        week_cols += f'''<div class="{col_cls}" style="{col_style}"
            onclick="openModal(this)" data-modal={tone_md}>
          <div class="{col_name_cls}">{h(dname[:3].upper())}</div>
          <div class="sched-day-col-num muted">D{day_data.get("num","?")}</div>
          <div class="sched-day-col-tone muted" style="font-size:.6rem">{h(day_data.get("tone",""))}</div>
          <div class="sched-day-col-slot">{mini_class("morning")}</div>
          <div class="sched-day-col-slot">{mini_class("afternoon")}</div>
          <div class="sched-day-col-slot">{mini_class("club")}</div>
        </div>'''

    # ── Time blocks strip ──
    blocks_html = ""
    for bk, name, hrs, desc in TIME_BLOCKS:
        is_cur    = bk == sched["block_id"]
        bc        = BLOCK_COLORS.get(bk, "#374151")
        blk_cls   = "sched-block sched-block-active clickable" if is_cur else "sched-block clickable"
        blk_style = f"border-color:{bc};background:{bc}22" if is_cur else ""
        blk_color = bc if is_cur else ""
        md = modal_attr(name, [("Hours", hrs), ("Character", desc)])
        blocks_html += f'<div class="{blk_cls}" style="{blk_style}" onclick="openModal(this)" data-modal={md}><span class="sched-block-name" style="color:{blk_color}">{h(name)}</span><span class="sched-block-hrs muted">{h(hrs)}</span></div>'

    return f'''
    {now_html}
    <div class="sched-section-label" style="margin:.75rem 0 .35rem">Today</div>
    {today_html}
    <div class="sched-section-label" style="margin:.75rem 0 .35rem">Week</div>
    <div class="sched-week">{week_cols}</div>
    <div class="sched-section-label" style="margin:.75rem 0 .35rem">Time Blocks</div>
    <div class="sched-blocks">{blocks_html}</div>'''


def render_inventory_row(item: dict) -> str:
    label     = f'<span class="inv-label">{h(item["label"])}</span> ' if item["label"] else ""
    desc_disp = h(item["desc"][:160]) + ("…" if len(item["desc"]) > 160 else "")

    md = modal_attr(item["name"], [
        ("Type",        item["label"]),
        ("Description", item["desc"]),
    ])

    return f'''<div class="inv-row clickable" onclick="openModal(this)" data-modal={md}>
      <div class="inv-name">{h(item["name"])}</div>
      <div class="inv-desc">{label}{desc_disp}</div>
    </div>'''


def render_cron_row(job: dict) -> str:
    status = job["status"].lower()
    errors = job["errors"]
    if errors > 0:
        dot_color, dot_title = "var(--climax)",  f"{errors} consecutive error(s)"
    elif status == "overdue":
        dot_color, dot_title = "var(--rising)",  job.get("cadence") or "overdue"
    elif status == "skipped":
        dot_color, dot_title = "var(--muted)",   "last run skipped"
    elif status == "failed":
        dot_color, dot_title = "var(--climax)",  "last run failed"
    elif status == "delivered":
        dot_color, dot_title = "var(--seed)",    "delivered"
    elif status in ("ok", "success", "system"):
        dot_color, dot_title = "var(--seed)",    "last run ok" if status != "system" else "system ok"
    else:
        dot_color, dot_title = "var(--muted)",   status or "unknown"

    st = job.get("steward", {}) or {}
    dur        = f'<span class="cron-dur muted"> {h(job["duration"])}</span>' if job["duration"] else ""
    expr       = f'<span class="cron-expr">{h(job["expr"])}</span>' if job["expr"] else ""
    delivered  = job.get("delivery", "")
    deliv_html = ""
    if delivered == "delivered":
        deliv_html = '<span class="cron-deliv ok">✓ sent</span>'
    elif delivered and delivered != "not-delivered":
        deliv_html = f'<span class="cron-deliv muted">{h(delivered)}</span>'
    skip_html = ""
    if st.get("last_skip_reason"):
        skip_html = f'<span class="cron-deliv muted">skip: {h(st["last_skip_reason"][:36])}</span>'
    fail_html = ""
    if st.get("last_error"):
        fail_html = f'<span class="cron-deliv fail">err: {h(st["last_error"][:36])}</span>'
    age = _age_label(job.get("last_raw", ""))
    age_html = f'<span class="cron-age">{h(age)}</span>' if age != "—" else ""

    tz_str     = f' ({job["tz"]})' if job.get("tz") else ""
    md = modal_attr(job["name"], [
        ("Schedule",   f'{job["expr"]}{tz_str}'),
        ("Status",     f'{job["status"]} · {errors} consecutive errors' if errors else job["status"]),
        ("Last run",   f'{job["last"]} ({job["duration"]})' if job["duration"] else job["last"]),
        ("Age",        age),
        ("Next run",   job["next"]),
        ("Delivery",   delivered),
        ("Last delivered", _short_local_ts(st.get("last_delivery", ""))),
        ("Last skipped", f'{_short_local_ts(st.get("last_skip", ""))} · {st.get("last_skip_reason", "")}' if st.get("last_skip") else ""),
        ("Last failure", f'{_short_local_ts(st.get("last_failure", ""))} · {st.get("last_error", "")}' if st.get("last_failure") else ""),
        ("Delivered count", st.get("delivered_count", "")),
        ("Skipped count", st.get("skipped_count", "")),
        ("Duplicate skips", st.get("duplicate_skips", "")),
        ("Cadence", job.get("cadence", "")),
        ("Log", job.get("log", "")),
        ("Command", job.get("command", "")),
    ])

    return f'''<tr class="clickable" onclick="openModal(this)" data-modal={md}>
      <td><span class="cron-dot" style="background:{dot_color}" title="{h(dot_title)}"></span></td>
      <td>
        <div class="cron-name">{h(job["name"])}{dur}</div>
        <div class="cron-schedule">{expr} {deliv_html} {skip_html} {fail_html}</div>
      </td>
      <td class="muted cron-time">{h(job["last"])} {age_html}</td>
      <td class="muted cron-time">{h(job["next"])}</td>
    </tr>'''


def render_automation_health(crons: list[dict]) -> str:
    stewarded = [j for j in crons if j.get("steward")]
    delivered = sum(1 for j in stewarded if j.get("steward", {}).get("last_delivery"))
    skipped = sum(1 for j in stewarded if j.get("steward", {}).get("last_skip"))
    failed = sum(1 for j in stewarded if j.get("steward", {}).get("last_failure"))
    overdue = sum(1 for j in crons if j.get("status") == "overdue")
    newest = ""
    for j in stewarded:
        raw = j.get("steward", {}).get("last_at", "")
        if raw and (not newest or raw > newest):
            newest = raw
    cards = [
        ("Last steward mark", _age_label(newest), "ok" if newest else ""),
        ("Delivered paths", str(delivered), "ok" if delivered else ""),
        ("Recent skips", str(skipped), ""),
        ("Failures", str(failed), "bad" if failed else "ok"),
        ("Overdue", str(overdue), "warn" if overdue else "ok"),
    ]
    return '<div class="auto-health">' + "".join(
        f'<div class="auto-card {cls}"><div class="auto-label">{h(label)}</div><div class="auto-value">{h(value)}</div></div>'
        for label, value, cls in cards
    ) + '</div>'


def render_narrative_health(report: dict) -> str:
    if not report:
        return '<div class="muted">No narrative health report.</div>'
    status = report.get("status") or report.get("health_status", "?")
    score = report.get("score") or report.get("health_score", "?")
    status_class = {
        "OK": "ok",
        "WATCH": "",
        "WARN": "warn",
        "ALERT": "bad",
        "ERROR": "bad",
    }.get(status, "")
    findings = report.get("findings", [])
    obligations = [item for item in report.get("obligations", []) if item.get("status", "open") == "open"]
    cards = [
        ("Status", status, status_class),
        ("Score", f"{score}/100", status_class),
        ("Open duties", str(len(obligations)), "bad" if obligations else "ok"),
        ("Alerts", str(sum(1 for f in findings if f.get("level") == "ALERT") or sum(1 for f in obligations if f.get("severity") == "ALERT")), "bad" if any(f.get("level") == "ALERT" for f in findings) or any(f.get("severity") == "ALERT" for f in obligations) else "ok"),
    ]
    card_html = '<div class="auto-health">' + "".join(
        f'<div class="auto-card {cls}"><div class="auto-label">{h(label)}</div><div class="auto-value">{h(value)}</div></div>'
        for label, value, cls in cards
    ) + '</div>'

    modal_fields = [
        ("Status", f"{status} ({score}/100)"),
        ("Arc", f'{report.get("arc", {}).get("title", "")} · {report.get("arc", {}).get("phase", "")} day {report.get("arc", {}).get("day", "")}'),
    ]
    for item in obligations:
        modal_fields.append((f'{item.get("severity", "")} · {item.get("kind", "")}', item.get("title", "")))
        modal_fields.append(("Hook", item.get("scene_hook", "")))
        modal_fields.append(("Satisfy", item.get("satisfy_by", "")))
    for finding in findings:
        modal_fields.append((f'{finding.get("level", "")} · {finding.get("area", "")}', finding.get("summary", "")))
        if finding.get("detail"):
            modal_fields.append(("Detail", finding.get("detail", "")))
    for action in report.get("next_actions", []):
        modal_fields.append(("Next", action))
    md = modal_attr("Narrative Stewardship", modal_fields)

    rows = []
    if obligations:
        for item in obligations[:5]:
            level = item.get("severity", "")
            cls = {"ALERT": "entry-priority", "WARN": "entry-war", "WATCH": "entry-seed", "OK": "entry-normal"}.get(level, "entry-normal")
            rows.append(
                f'<div class="entry {cls}"><strong>{h(level)} · {h(item.get("kind", ""))}</strong> {h(item.get("title", ""))}</div>'
            )
    for finding in findings[: max(0, 5 - len(rows))]:
        level = finding.get("level", "")
        cls = {"ALERT": "entry-priority", "WARN": "entry-war", "WATCH": "entry-seed", "OK": "entry-normal"}.get(level, "entry-normal")
        rows.append(
            f'<div class="entry {cls}"><strong>{h(level)} · {h(finding.get("area", ""))}</strong> {h(finding.get("summary", ""))}</div>'
        )
    if not rows:
        rows.append('<div class="muted">No findings.</div>')
    return f'<div class="clickable" onclick="openModal(this)" data-modal={md}>{card_html}<div class="tick-feed" style="margin-top:.65rem">{"".join(rows)}</div></div>'


def _gallery_title(raw_title: str, scene_id: str, stem_fallback: str) -> str:
    """Return a clean display title. Falls back to a formatted timestamp when the
    stored title looks like a log/diary entry rather than a real scene name."""
    _GARBAGE_PATTERNS = ('fixed', 'bug', 'session closed', 'scripts/', 'test scene', 'ledger test')
    if raw_title and not any(p in raw_title.lower() for p in _GARBAGE_PATTERNS) and len(raw_title) <= 80:
        return raw_title
    m = re.match(r'scene-(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})$', scene_id or '')
    if m:
        yr, mo, dy, hh, mm = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
        months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
        return f"{months[int(mo)-1]} {int(dy)} · {hh}:{mm}"
    return scene_id or stem_fallback


def parse_scene_gallery(limit: int = 18) -> list[dict]:
    entries = []
    seen_scene_ids: set[str] = set()

    def _append_entry(obj: dict, image_result: dict) -> None:
        gallery_path = image_result.get('gallery_path')
        if gallery_path:
            try:
                image_path = Path(str(gallery_path)).expanduser()
            except Exception:
                return
        else:
            src = image_result.get('artifact_path')
            if not src:
                detail = str(image_result.get('detail') or '')
                m = re.search(r'(?:from|at)\s+([^\s]+\.(?:png|jpg|jpeg|webp|gif))', detail, re.IGNORECASE)
                if m:
                    src = m.group(1)
            if not src:
                return
            try:
                image_path = Path(str(src)).expanduser()
            except Exception:
                return
        if not image_path.exists():
            return

        scene_id = str(obj.get('scene_id') or '')
        if scene_id and scene_id in seen_scene_ids:
            return
        if scene_id:
            seen_scene_ids.add(scene_id)

        text = str(obj.get('text') or '')
        recorded_at = str(obj.get('recorded_at') or obj.get('ran_at') or '')
        try:
            mime = mimetypes.guess_type(str(image_path))[0] or 'image/png'
            b64 = base64.b64encode(image_path.read_bytes()).decode('ascii')
            data_uri = f"data:{mime};base64,{b64}"
        except Exception:
            data_uri = str(image_result.get('gallery_uri') or image_path.resolve().as_uri())
        raw_title = str(obj.get('title') or '')
        display_title = _gallery_title(raw_title, scene_id, image_path.stem)
        entries.append({
            'title': display_title,
            'scene_id': scene_id,
            'recorded_at': recorded_at,
            'when': _short_local_ts(recorded_at),
            'mood': obj.get('mood', ''),
            'intensity': obj.get('intensity', ''),
            'path': data_uri,
            'text': text,
        })

    if SCENE_LEDGER_DIR.exists():
        for path in sorted(SCENE_LEDGER_DIR.glob('*.jsonl'), reverse=True):
            try:
                lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
            except Exception:
                continue
            for line in reversed(lines):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                results = obj.get('results') or {}
                image_result = results.get('image') if isinstance(results, dict) else None
                if not isinstance(image_result, dict) or not image_result.get('ok'):
                    continue
                _append_entry(obj, image_result)
                if len(entries) >= limit:
                    return entries

    if SCENE_OUTBOX_DIR.exists():
        for path in sorted(SCENE_OUTBOX_DIR.glob('*-run.json'), reverse=True):
            try:
                obj = json.loads(path.read_text(encoding='utf-8', errors='replace'))
            except Exception:
                continue
            results = obj.get('results') or {}
            image_result = results.get('image') if isinstance(results, dict) else None
            if not isinstance(image_result, dict) or not image_result.get('ok'):
                continue
            _append_entry(obj, image_result)
            if len(entries) >= limit:
                return entries

    return entries


def render_scene_gallery(entries: list[dict]) -> str:
    if not entries:
        return '<div class="muted" style="padding:.5rem 0">No generated scene images yet.</div>'

    def _gallery_modal(item: dict) -> str:
        return modal_attr(item['title'], [
            ('Captured', item.get('when', '')),
            ('Mood', item.get('mood', '')),
            ('Intensity', item.get('intensity', '')),
            ('Scene', item.get('scene_id', '')),
            ('Text', item.get('text', '')),
            ('Image', item.get('path', '')),
        ])

    cards = []
    for idx, item in enumerate(entries):
        active = ' active' if idx == 0 else ''
        meta = ' · '.join([x for x in [item.get('when', ''), item.get('mood', ''), item.get('intensity', '')] if x])
        cards.append(
            f'''<button class="gallery-thumb{active}" type="button" onclick="selectGalleryImage(this)" data-fullsrc="{h(item['path'])}" data-title="{h(item['title'])}" data-meta="{h(meta)}" data-caption="{h((item.get('text') or '')[:240])}" data-modal={_gallery_modal(item)}><img src="{h(item['path'])}" alt="{h(item['title'])}"><span class="gallery-thumb-label">{h(item['title'])}</span></button>'''
        )

    first = entries[0]
    first_meta = ' · '.join([x for x in [first.get('when', ''), first.get('mood', ''), first.get('intensity', '')] if x])
    return f'''<div class="gallery-shell" id="gallery-shell">
      <div id="gallery-stage-wrap" class="gallery-stage-wrap clickable" onclick="openModal(this)" data-modal={_gallery_modal(first)}>
        <img id="gallery-stage-image" class="gallery-stage-image" src="{h(first['path'])}" alt="{h(first['title'])}">
      </div>
      <div class="gallery-stage-meta">
        <div id="gallery-stage-title" class="gallery-stage-title">{h(first['title'])}</div>
        <div id="gallery-stage-sub" class="gallery-stage-sub muted">{h(first_meta)}</div>
        <div id="gallery-stage-caption" class="gallery-stage-caption muted">{h((first.get('text') or '')[:240])}</div>
      </div>
      <div class="gallery-filmstrip">{''.join(cards)}</div>
    </div>'''


# ── Full page ─────────────────────────────────────────────────────────────────

def build_html(threads, npcs, talismans, player, queue, bleed, crons, arc=None, anchors=None, sched=None, forecast=None, heartbeat=None, sim_feed=None, pact_actions=None, gallery_entries=None, narrative_health=None) -> str:
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Arc banner
    arc_html = render_arc_banner(arc) if arc else ""

    # Thread cards
    thread_cards = "".join(render_thread_card(t) for t in threads)

    # Talisman bars
    max_tal = max((t["belief"] for t in talismans), default=1)
    tal_bars = "".join(render_talisman_bar(t, max_tal) for t in talismans)

    # Full world register
    entities_html = render_entity_sections(npcs)

    # Queue entries
    queue_html = "".join(render_queue_entry(e) for e in queue) or '<div class="muted">Queue is clear.</div>'
    sim_feed = sim_feed or []
    sim_html = "".join(render_simulation_entry(e) for e in sim_feed) or '<div class="muted">No simulation ledger yet.</div>'
    pact_actions = pact_actions or []
    pact_html = "".join(render_pact_action(e) for e in pact_actions) or '<div class="muted">No pact app actions logged yet.</div>'

    # Anchor places
    anchors = anchors or[]
    anchors_html = "".join(render_anchor_card(a) for a in anchors) or '<div class="muted" style="padding:.5rem 0">No anchors yet. The Ley Line map is blank.</div>'

    # Inventory
    inventory_html = "".join(render_inventory_row(i) for i in player.get("inventory",[])) or '<div class="muted">Inventory is empty.</div>'

    # Schedule
    sched = sched or {}
    schedule_html = render_schedule_tab(sched) if sched else '<div class="muted">No schedule data.</div>'

    # Forecast
    forecast_html = render_forecast_tab(forecast) if forecast else '<div class="muted">No forecast data.</div>'
    heartbeat_html = render_heartbeat_tab(heartbeat) if heartbeat else '<div class="muted">No heartbeat data.</div>'

    # Gallery
    gallery_entries = gallery_entries or []
    gallery_html = render_scene_gallery(gallery_entries)

    # Player quests
    quest_html = ""
    for q in player.get("quests", []):
        desc_disp = h(q["desc"][:55]) + ("…" if len(q["desc"]) > 55 else "")
        qmd = modal_attr(q["npc"], [("Elective", q["desc"])])
        quest_html += f'<div class="quest-row clickable" onclick="openModal(this)" data-modal={qmd}><span class="quest-npc">{h(q["npc"])}</span><span class="quest-desc muted">{desc_disp}</span></div>'
    if not quest_html:
        quest_html = '<div class="muted">No active quests.</div>'

    # Fae bargains
    fae_html = ""
    for b in player.get("bargains", []):
        status = b["status"].upper()
        color = {"OPEN": "var(--seed)", "OVERDUE": "var(--climax)", "BROKEN": "var(--climax)", "EXPIRED": "var(--climax)", "DELIVERED": "var(--muted)", "REPAIRED": "var(--muted)"}.get(status, "var(--muted)")
        details = []
        if b.get("gave"):
            details.append(("Given", b["gave"]))
        if b.get("terms"):
            details.append(("Owed", b["terms"]))
        if b.get("deadline"):
            details.append(("Deadline", b["deadline"]))
        modal = modal_attr(f'{b["fae"]} · {status}', details)
        fae_html += f'<div class="fae-row clickable" onclick="openModal(this)" data-modal={modal}><span style="color:{color}">{h(status)}</span> <span class="muted">{h(b["fae"])}</span> · {h(b["deadline"])}</div>'
    if not fae_html:
        fae_html = '<div class="muted">The Margin is clean.</div>'

    # Bleed status
    bleed_status_color = "var(--seed)" if bleed["is_today"] and bleed["delivered"] else \
                         "var(--rising)" if bleed["is_today"] else "var(--muted)"
    bleed_label = "Today's issue published" if bleed["is_today"] and bleed["delivered"] else \
                  "Today's issue pending" if bleed["is_today"] else \
                  f"Last: {bleed['last_issue']}"
    bleed_issue = f"#{bleed['issue_number']}" if bleed["issue_number"] else ""

    # Cron table
    automation_health_html = render_automation_health(crons)
    narrative_health_html = render_narrative_health(narrative_health or {})
    cron_html = ""
    for j in crons:
        cron_html += render_cron_row(j)
    if not cron_html:
        cron_html = '<tr><td colspan="4" class="muted">No jobs found.</td></tr>'

    # Belief bar
    try:
        belief_val = int(player.get("belief", 0))
        belief_pct = min(100, belief_val)
    except (ValueError, TypeError):
        belief_val = 0
        belief_pct = 0

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Enchantify — Story-Field Journal</title>
<style>
  :root {{
    --bg:         #e6d6b8;
    --surface:    rgba(252, 244, 224, .86);
    --surface-strong: rgba(255, 249, 233, .94);
    --surface-soft: rgba(132, 87, 42, .07);
    --border:     rgba(89, 62, 35, .26);
    --rule:       rgba(94, 63, 33, .18);
    --text:       #2f261d;
    --muted:      #806f5b;
    --ink:        #2f261d;
    --sepia:      #6f4f2c;
    --teal-ink:   #167475;
    --garnet:     #8e2e3b;
    --moss:       #55723c;
    --gold-ink:   #a76f24;
    --dormant:    #3f3f46;
    --setup:      #4e6b8a;
    --rising:     #92681a;
    --climax:     #c2410c;
    --resolution: #15803d;
    --nothing:    #7f1d1d;
    --seed:       #166534;
    --fae:        #6b21a8;
    --priority:   #dc2626;
    --war:        #b45309;
    --invest:     #1d4ed8;
    --beat:       #374151;
    --pulse:      #1f2937;
    --thread-line:#1e3a5f;
    font-family: 'Georgia', 'Times New Roman', serif;
  }}
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background:
      radial-gradient(circle at 15% 5%, rgba(255,255,255,.24), transparent 22rem),
      radial-gradient(circle at 82% 16%, rgba(122, 70, 28, .13), transparent 19rem),
      linear-gradient(110deg, rgba(92, 57, 28, .14), transparent 18%, transparent 82%, rgba(78, 45, 24, .12)),
      var(--bg);
    color: var(--text); min-height: 100vh; font-size: 14px;
  }}
  body::before {{
    content:""; position: fixed; inset: 0; pointer-events: none; z-index: -2;
    background-image:
      repeating-linear-gradient(0deg, rgba(80,51,24,.045) 0 1px, transparent 1px 7px),
      repeating-linear-gradient(90deg, rgba(255,255,255,.055) 0 1px, transparent 1px 11px);
    mix-blend-mode: multiply; opacity: .55;
  }}
  body::after {{
    content:""; position: fixed; right: max(1rem, calc((100vw - 1600px)/2 + 1rem)); top: 5.25rem;
    width: min(32vw, 480px); height: 76vh; pointer-events: none; opacity: .07; z-index: -1;
    background: url('mission-control-assets/ledger-margin.png') top right / cover no-repeat;
    filter: sepia(.2) saturate(.85);
  }}
  a {{ color: inherit; text-decoration: none; }}

  /* ── Layout ── */
  .topbar {{
    display: flex; align-items: center; gap: 1rem;
    padding: .75rem clamp(1rem, 3vw, 2rem);
    background: rgba(68, 45, 25, .84); border-bottom: 1px solid rgba(49,32,18,.35);
    color: #f3e8ce;
    font-family: "Courier New", monospace; font-size: .78rem;
    box-shadow: 0 8px 24px rgba(58, 36, 15, .18);
    position: sticky; top: 0; z-index: 20;
  }}
  .topbar-title {{
    font-family: Georgia, serif; font-size: 1.05rem; letter-spacing: .06em;
    color: #fff3d2; text-transform: uppercase;
  }}
  .topbar-divider {{ color: rgba(255,243,210,.36); }}
  .topbar-item {{ display: flex; gap: .4rem; align-items: center; }}
  .topbar-label {{ color: rgba(255,243,210,.62); }}
  .topbar-refresh {{ color: rgba(255,243,210,.62); font-size: .68rem; }}
  .topbar-refresh-btn {{
    margin-left: auto; background: rgba(255,243,210,.08); border: 1px solid rgba(255,243,210,.32);
    color: #fff3d2; font-size: .75rem; cursor: pointer; border-radius: 2px;
    padding: .1rem .4rem; line-height: 1.4;
  }}
  .topbar-refresh-btn:hover {{ background: rgba(255,243,210,.16); border-color: rgba(255,243,210,.55); }}
  .topbar-refresh-btn.spinning {{ animation: spin .6s linear infinite; }}
  @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
  .belief-inline {{
    display: inline-block; width: 60px; height: 6px;
    background: rgba(255,243,210,.22); border-radius: 3px; vertical-align: middle;
    position: relative; overflow: hidden;
  }}
  .belief-inline-fill {{
    position: absolute; left: 0; top: 0; height: 100%;
    background: #2aa7a1; border-radius: 3px;
  }}

  .grid {{
    display: grid;
    grid-template-columns: minmax(0, 1fr) 360px;
    grid-template-rows: auto auto;
    gap: 1rem; padding: 1.25rem clamp(.75rem, 2vw, 1.5rem) 2rem;
    max-width: 1600px; margin: 0 auto;
  }}
  .folio-mast {{
    max-width: 1600px; margin: 1.1rem auto 0; padding: 0 clamp(.75rem, 2vw, 1.5rem);
  }}
  .folio-sheet {{
    position: relative; overflow: hidden; min-height: 0;
    background:
      linear-gradient(rgba(255, 249, 233, .68), rgba(255, 249, 233, .76)),
      url('mission-control-assets/ledger-margin.png') center 38% / cover no-repeat,
      linear-gradient(90deg, rgba(108,72,36,.09), transparent 20%, transparent 82%, rgba(108,72,36,.06)),
      var(--surface-strong);
    border: 1px solid var(--border); border-radius: 3px;
    box-shadow: 0 1px 0 rgba(255,255,255,.55) inset, 0 12px 30px rgba(58,36,15,.12);
    padding: 1rem 1.2rem .9rem;
  }}
  .folio-sheet::before {{
    content:""; position:absolute; inset:.55rem; border:1px solid rgba(94,63,33,.12); pointer-events:none;
  }}
  .folio-sheet > * {{ position: relative; z-index: 1; }}
  .folio-logo {{
    display:block; width:min(780px, 100%); max-height:210px; object-fit:contain;
    object-position:left center; margin:-.35rem 0 .35rem; mix-blend-mode:multiply;
  }}
  .folio-kicker {{
    font-family:"Courier New", monospace; font-size:.66rem; text-transform:uppercase;
    letter-spacing:.12em; color:var(--muted); margin-bottom:.25rem;
  }}
  .folio-title {{
    font-size: clamp(1.6rem, 3vw, 2.45rem); line-height:1; color:var(--ink);
    font-weight: normal; letter-spacing:0;
  }}
  .folio-sub {{
    max-width: 920px; margin-top:.45rem; font-size:.84rem; line-height:1.5; color:var(--sepia);
  }}
  .folio-marks {{
    display:flex; gap:.5rem; flex-wrap:wrap; margin-top:.65rem; padding-right: 0;
  }}
  .folio-mark {{
    font-family:"Courier New", monospace; font-size:.62rem; letter-spacing:.04em;
    border:1px solid rgba(89,62,35,.22); background:rgba(255,251,238,.42);
    padding:.16rem .42rem; border-radius:2px; color:var(--muted);
  }}

  /* ── Panels ── */
  .panel {{
    background:
      linear-gradient(90deg, rgba(91, 57, 27, .045), transparent 18%, transparent 82%, rgba(91,57,27,.035)),
      var(--surface);
    border: 1px solid var(--border);
    border-radius: 3px; overflow: hidden; position: relative;
    box-shadow: 0 1px 0 rgba(255,255,255,.45) inset, 0 10px 28px rgba(58, 36, 15, .10);
  }}
  .panel::before {{
    content:""; position:absolute; inset: .45rem; border:1px solid rgba(94,63,33,.10);
    pointer-events:none;
  }}
  .panel-header {{
    padding: .58rem 1rem .5rem;
    border-bottom: 1px solid var(--rule);
    font-family: "Courier New", monospace; font-size: .68rem; letter-spacing: .08em;
    color: var(--sepia); text-transform: uppercase; display: flex;
    align-items: center; gap: .8rem;
    background: rgba(108, 72, 36, .055);
  }}
  .panel-header span {{ color: var(--text); }}
  .panel-body {{ padding: 1rem; position: relative; }}

  /* ── Thread cards ── */
  .thread-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: .75rem; }}
  .card {{
    background: rgba(255, 251, 238, .48); border: 1px solid; border-radius: 3px;
    padding: .75rem; display: flex; flex-direction: column; gap: .5rem;
    box-shadow: 0 1px 0 rgba(255,255,255,.4) inset;
  }}
  .card-header {{ display: flex; align-items: center; justify-content: space-between; }}
  .card-title {{ font-size: .85rem; font-weight: bold; }}
  .card-anchor {{ font-size: .7rem; color: var(--muted); }}
  .card-beat {{ font-size: .78rem; color: var(--text); line-height: 1.5; font-style: italic; }}
  .card-meta {{ font-size: .65rem; color: var(--muted); font-family: monospace; }}
  .badge-new {{
    display: inline-block; margin-left: .5rem;
    background: rgba(85,114,60,.16); color: var(--moss);
    font-size: .55rem; padding: .1rem .3rem; border-radius: 2px;
    font-family: monospace; text-transform: uppercase; vertical-align: middle;
  }}
  .nothing-dot {{ font-size: .7rem; }}

  /* ── Phase bar ── */
  .phase-bar-wrap {{
    position: relative; height: 18px; border-radius: 2px; overflow: visible;
  }}
  .phase-bands {{
    display: flex; position: absolute; inset: 0; border-radius: 2px; overflow: hidden;
  }}
  .band {{ height: 100%; }}
  .phase-fill {{
    position: absolute; top: 0; left: 0; height: 100%;
    border-radius: 2px; opacity: .75; transition: width .3s;
  }}
  .phase-label {{
    position: absolute; right: 0; top: 0; height: 100%;
    display: flex; align-items: center;
    font-family: monospace; font-size: .65rem; font-weight: bold;
    padding-right: .3rem; text-shadow: 0 1px 0 rgba(255,255,255,.45);
  }}
  .phase-bar.permanent {{
    background: var(--dormant); border-radius: 2px; height: 18px;
    display: flex; align-items: center; padding: 0 .5rem;
  }}
  .phase-bar.permanent span {{ font-size: .65rem; color: var(--muted); font-family: monospace; }}

  /* ── Talisman bars ── */
  .tal-row {{ display: flex; align-items: center; gap: .6rem; margin-bottom: .4rem; }}
  .tal-name {{ width: 100px; font-size: .75rem; font-weight: bold; flex-shrink: 0; }}
  .tal-bar-wrap {{ flex: 1; height: 8px; background: rgba(97,65,35,.14); border-radius: 4px; overflow: hidden; }}
  .tal-bar {{ height: 100%; border-radius: 4px; transition: width .4s; }}
  .tal-belief {{ width: 30px; text-align: right; font-family: monospace; font-size: .75rem; flex-shrink: 0; }}
  .tal-chapter {{ width: 80px; font-size: .65rem; font-family: monospace; flex-shrink: 0; }}

  /* ── Entity table ── */
  .entity-summary {{ font-size: .7rem; color: var(--muted); margin-bottom: .7rem; }}
  .entity-section {{ margin-bottom: 1rem; }}
  .entity-section:last-child {{ margin-bottom: 0; }}
  .entity-section-head {{
    display:flex; justify-content:space-between; align-items:center;
    font-family: monospace; font-size: .66rem; color: var(--muted);
    text-transform: uppercase; letter-spacing: .08em;
    border-bottom: 1px solid var(--border); padding-bottom: .25rem; margin-bottom: .15rem;
  }}
  .entity-section-head span {{ color: var(--text); font-size: .62rem; }}
  .ent-table {{ width: 100%; border-collapse: collapse; font-size: .75rem; }}
  .ent-table td {{ padding: .25rem .4rem; border-bottom: 1px solid var(--border); }}
  .ent-table tr:last-child td {{ border-bottom: none; }}
  .ent-name {{ color: var(--text); }}
  .ent-type {{ font-family: monospace; font-size: .65rem; }}
  .ent-belief {{ font-family: monospace; text-align: right; color: var(--text); }}
  .ent-tags {{ font-family: monospace; font-size: .6rem; }}
  .tag {{
    display: inline-block; background: rgba(22,116,117,.12); color: var(--teal-ink);
    border-radius: 2px; padding: .05rem .3rem; margin-right: .2rem; font-size: .6rem;
  }}

  /* ── Tick feed ── */
  .tick-feed {{ display: flex; flex-direction: column; gap: .3rem; max-height: 360px; overflow-y: auto; }}
  .entry {{
    padding: .38rem .6rem; border-radius: 2px; font-size: .72rem; line-height: 1.5;
    border-left: 3px solid transparent;
  }}
  .entry-escalation {{ background: rgba(167,111,36,.12); border-color: var(--rising); color: #5e3c12; }}
  .entry-cooling     {{ background: rgba(78,107,138,.12); border-color: var(--setup); color: #274761; }}
  .entry-seed        {{ background: rgba(85,114,60,.12); border-color: var(--seed); color: #385421; }}
  .entry-fae         {{ background: rgba(107,33,168,.10); border-color: var(--fae); color: #593070; }}
  .entry-priority    {{ background: rgba(142,46,59,.12); border-color: var(--priority); color: #74212d; }}
  .entry-war         {{ background: rgba(180,83,9,.12); border-color: var(--war); color: #714315; }}
  .entry-beat        {{ background: rgba(47,38,29,.06); border-color: var(--beat); }}
  .entry-thread      {{ background: rgba(30,58,95,.10); border-color: var(--thread-line); color: #253f62; }}
  .entry-talisman    {{ background: rgba(167,111,36,.12); border-color: var(--war); color: #6d4514; }}
  .entry-invest      {{ background: rgba(29,78,216,.08); border-color: var(--invest); color: #204a8b; }}
  .entry-pulse       {{ background: rgba(47,38,29,.045); border-color: var(--border); color: var(--muted); }}
  .entry-normal      {{ background: rgba(255,251,238,.40); border-color: var(--rule); color: var(--text); }}
  .sim-entry         {{ display: flex; flex-direction: column; gap: .2rem; }}
  .sim-header        {{ font-family: monospace; font-size: .62rem; text-transform: uppercase; letter-spacing: .04em; }}
  .sim-title         {{ font-size: .72rem; color: var(--text); }}
  .sim-narrative     {{ font-size: .72rem; color: var(--text); font-style: italic; }}
  .sim-reason        {{ font-size: .68rem; color: var(--text); }}
  .sim-meta          {{ font-family: monospace; font-size: .62rem; }}

  /* ── Player panel ── */
  .belief-bar-wrap {{ margin: .5rem 0; }}
  .belief-bar-track {{
    height: 8px; background: rgba(97,65,35,.14); border-radius: 4px; overflow: hidden;
  }}
  .belief-bar-fill {{
    height: 100%; background: linear-gradient(90deg, var(--teal-ink), var(--gold-ink)); border-radius: 4px;
  }}
  .belief-label {{ font-family: monospace; font-size: .7rem; color: var(--muted); margin-top: .2rem; }}
  .stat-row {{ display: flex; gap: .8rem; flex-wrap: wrap; margin-bottom: .5rem; }}
  .stat {{ font-family: monospace; font-size: .7rem; }}
  .stat-key {{ color: var(--muted); }}
  .quest-row {{ padding: .3rem 0; border-bottom: 1px solid var(--border); display: flex; gap: .5rem; align-items: baseline; }}
  .quest-row:last-child {{ border-bottom: none; }}
  .quest-npc {{ font-size: .75rem; font-weight: bold; flex-shrink: 0; }}
  .quest-desc {{ font-size: .7rem; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .fae-row {{ font-size: .72rem; padding: .2rem 0; }}
  .section-label {{ font-family: monospace; font-size: .65rem; color: var(--muted); text-transform: uppercase; letter-spacing: .08em; margin: .7rem 0 .3rem; }}

  /* ── Bleed ── */
  .bleed-status {{
    display: flex; align-items: center; gap: .5rem;
    font-family: monospace; font-size: .8rem; padding: .5rem .75rem;
    border-radius: 2px; background: rgba(255,251,238,.46); border: 1px solid var(--rule);
  }}
  .bleed-dot {{ font-size: 1rem; }}

  /* ── Cron table ── */
  .cron-table {{ width: 100%; border-collapse: collapse; font-size: .72rem; }}
  .cron-table td {{ padding: .3rem .4rem; border-bottom: 1px solid var(--border); vertical-align: top; }}
  .cron-table tr:last-child td {{ border-bottom: none; }}
  .cron-dot {{
    display: inline-block; width: 8px; height: 8px; border-radius: 50%;
    margin-top: .2rem;
  }}
  .cron-name {{ color: var(--text); font-size: .73rem; }}
  .cron-dur  {{ font-family: monospace; font-size: .65rem; }}
  .cron-schedule {{ font-family: monospace; font-size: .63rem; color: var(--muted); margin-top: .1rem; display: flex; gap: .5rem; align-items: center; }}
  .cron-expr {{ color: #6b7280; }}
  .cron-deliv.ok {{ color: var(--seed); }}
  .cron-deliv.fail {{ color: var(--climax); }}
  .cron-age {{ display:block; font-size:.58rem; color:#6b7280; margin-top:.08rem; }}
  .cron-time {{ font-family: monospace; font-size: .65rem; white-space: nowrap; padding-top: .35rem; }}
  .auto-health {{ display:grid; grid-template-columns: repeat(5, minmax(0,1fr)); gap:.35rem; margin:.7rem 0 .65rem; }}
  .auto-card {{ background:rgba(255,251,238,.44); border:1px solid var(--border); border-radius:3px; padding:.45rem .5rem; min-width:0; }}
  .auto-card.ok {{ border-color:#15803d55; }}
  .auto-card.warn {{ border-color:#92681a66; }}
  .auto-card.bad {{ border-color:#c2410c66; }}
  .auto-label {{ color:var(--muted); font-size:.6rem; text-transform:uppercase; letter-spacing:.04em; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  .auto-value {{ color:var(--text); font-family:monospace; font-size:.78rem; margin-top:.15rem; }}

  /* ── Image gallery ── */
  .gallery-shell {{ display:flex; flex-direction:column; gap:.75rem; }}
  .gallery-stage-wrap {{ background: rgba(80,51,24,.10); border:1px solid var(--border); border-radius:3px; overflow:hidden; min-height: 280px; display:flex; align-items:center; justify-content:flex-start; }}
  .gallery-stage-image {{ width:100%; min-width:0; max-height:460px; object-fit:contain; object-position:left center; display:block; background:#efe0bd; }}
  .gallery-stage-meta {{ display:flex; flex-direction:column; gap:.2rem; }}
  .gallery-stage-title {{ font-size:.9rem; font-weight:bold; }}
  .gallery-stage-sub {{ font-family: monospace; font-size:.65rem; }}
  .gallery-stage-caption {{ font-size:.74rem; line-height:1.45; }}
  .gallery-filmstrip {{ display:flex; gap:.5rem; overflow-x:auto; padding-bottom:.2rem; }}
  .gallery-thumb {{ background:rgba(255,251,238,.48); border:1px solid var(--border); border-radius:3px; color:var(--text); min-width:140px; max-width:140px; padding:.35rem; cursor:pointer; display:flex; flex-direction:column; gap:.35rem; text-align:left; }}
  .gallery-thumb.active {{ border-color:var(--teal-ink); box-shadow: inset 0 0 0 1px rgba(22,116,117,.22); }}
  .gallery-thumb img {{ width:100%; height:88px; object-fit:cover; border-radius:2px; background:#efe0bd; }}
  .gallery-thumb-label {{ font-size:.68rem; line-height:1.3; white-space:normal; }}

  .muted {{ color: var(--muted); }}
  .clickable {{ cursor: pointer; }}
  .clickable:hover {{ opacity: .85; }}

  /* ── Modal ── */
  .modal-overlay {{
    display: none; position: fixed; inset: 0; z-index: 1000;
    background: rgba(35,24,14,.58); align-items: center; justify-content: center;
    backdrop-filter: blur(2px);
  }}
  .modal-overlay.open {{ display: flex; }}
  .modal-box {{
    background: #f7edcf; border: 1px solid rgba(89,62,35,.34); border-radius: 4px;
    width: min(640px, 94vw); max-height: 82vh;
    display: flex; flex-direction: column; overflow: hidden;
    box-shadow: 0 24px 48px rgba(49,31,13,.38);
  }}
  .modal-header {{
    display: flex; align-items: center; justify-content: space-between;
    padding: .75rem 1rem; border-bottom: 1px solid rgba(89,62,35,.24); flex-shrink: 0;
    background: rgba(108,72,36,.07);
  }}
  .modal-title {{ font-size: .95rem; font-weight: bold; color: var(--text); }}
  .modal-close {{
    background: none; border: none; color: var(--muted); font-size: 1.2rem;
    cursor: pointer; line-height: 1; padding: .1rem .3rem; border-radius: 3px;
  }}
  .modal-close:hover {{ color: var(--text); background: rgba(108,72,36,.12); }}
  .modal-body {{ overflow-y: auto; padding: .75rem 1rem; display: flex; flex-direction: column; gap: .6rem; }}
  .mf-row {{ display: grid; grid-template-columns: 130px 1fr; gap: .4rem; align-items: baseline; }}
  .mf-label {{
    font-family: monospace; font-size: .65rem; text-transform: uppercase;
    letter-spacing: .07em; color: var(--muted); flex-shrink: 0; padding-top: .1rem;
  }}
  .mf-value {{ font-size: .78rem; line-height: 1.6; color: var(--text); word-break: break-word; }}

  /* ── Scrollbar ── */
  ::-webkit-scrollbar {{ width: 4px; }}
  ::-webkit-scrollbar-track {{ background: rgba(97,65,35,.09); }}
  ::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 2px; }}

  /* ── Arc banner ── */
  .arc-banner {{
    background: rgba(255,251,238,.52); border: 1px solid; border-radius: 3px;
    padding: .85rem 1rem; display: flex; flex-direction: column; gap: .75rem;
    position: relative; overflow: hidden;
  }}
  .arc-banner::after {{
    content:""; position:absolute; right:.75rem; top:.55rem; width:86px; height:86px; opacity:.13;
    background: radial-gradient(circle, transparent 42%, currentColor 43% 45%, transparent 46%),
                linear-gradient(currentColor, currentColor) center/1px 100% no-repeat,
                linear-gradient(90deg, currentColor, currentColor) center/100% 1px no-repeat;
    transform: rotate(-12deg);
  }}
  .arc-header {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; }}
  .arc-eyebrow {{ font-family: monospace; font-size: .65rem; color: var(--muted); margin-bottom: .2rem; }}
  .arc-name {{ font-size: 1.05rem; font-weight: bold; letter-spacing: .02em; }}
  .arc-right {{ text-align: right; display: flex; flex-direction: column; gap: .3rem; align-items: flex-end; }}
  .arc-phase {{ font-family: monospace; font-size: .8rem; font-weight: bold; letter-spacing: .1em; }}
  .arc-belief-wrap {{ display: flex; align-items: center; gap: .4rem; flex-direction: row-reverse; }}
  .arc-belief-track {{ width: 80px; height: 5px; background: rgba(97,65,35,.15); border-radius: 3px; overflow: hidden; }}
  .arc-belief-fill {{ height: 100%; border-radius: 3px; }}
  .arc-belief-label {{ font-family: monospace; font-size: .65rem; color: var(--muted); }}
  .arc-compass {{ font-family: monospace; font-size: .65rem; color: var(--muted); }}
  .arc-body {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; }}
  .arc-col {{ display: flex; flex-direction: column; gap: .3rem; }}
  .arc-section-label {{ font-family: monospace; font-size: .6rem; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); }}
  .arc-text {{ font-size: .75rem; line-height: 1.55; color: var(--text); }}
  .arc-res-row {{ font-size: .72rem; line-height: 1.5; padding: .1rem 0; }}
  .arc-res-label {{ font-weight: bold; color: var(--text); }}
  .arc-res-label::after {{ content: " — "; color: var(--muted); }}

  /* ── Forecast ── */
  .fc-world {{
    background: rgba(255,251,238,.52); border: 1px solid var(--border); border-radius: 3px;
    padding: .65rem .85rem; margin-bottom: .6rem; display: flex; flex-direction: column; gap: .35rem;
  }}
  .fc-world-feel {{ font-size: .82rem; color: var(--text); line-height: 1.4; }}
  .fc-world-row  {{ display: flex; flex-wrap: wrap; gap: .4rem; }}
  .fc-pill {{
    font-family: monospace; font-size: .62rem; padding: .1rem .4rem;
    background: rgba(108,72,36,.10); border-radius: 2px;
  }}
  .fc-forecast {{ font-size: .68rem; line-height: 1.5; font-style: italic; }}
  .fc-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: .5rem; margin-bottom: .5rem; }}
  .fc-block {{
    background: rgba(255,251,238,.46); border: 1px solid var(--border); border-radius: 3px;
    padding: .6rem .75rem; display: flex; flex-direction: column; gap: .4rem;
    margin-bottom: .5rem;
  }}
  .fc-grid .fc-block {{ margin-bottom: 0; }}
  .fc-block-header {{ display: flex; align-items: center; justify-content: space-between; gap: .5rem; }}
  .fc-block-title  {{ font-family: monospace; font-size: .65rem; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); }}
  .fc-badge {{
    font-family: monospace; font-size: .62rem; padding: .1rem .4rem; border-radius: 2px; flex-shrink: 0;
  }}
  .fc-badge-neutral {{ background: rgba(108,72,36,.10); color: var(--muted); }}
  .fc-nothing-strategy, .fc-philo {{ font-size: .72rem; line-height: 1.5; }}
  .fc-bullets {{ padding-left: 1rem; display: flex; flex-direction: column; gap: .2rem; }}
  .fc-bullets li {{ font-size: .68rem; line-height: 1.5; color: var(--muted); }}
  .fc-tal-bars   {{ display: flex; flex-direction: column; gap: .25rem; margin-top: .2rem; }}
  .fc-tal-row    {{ display: flex; align-items: center; gap: .4rem; }}
  .fc-tal-name   {{ font-size: .68rem; font-weight: bold; width: 90px; flex-shrink: 0; }}
  .fc-tal-bar-wrap {{ flex: 1; height: 6px; background: rgba(97,65,35,.15); border-radius: 3px; overflow: hidden; }}
  .fc-tal-bar    {{ height: 100%; border-radius: 3px; }}
  .fc-tal-b      {{ font-family: monospace; font-size: .62rem; width: 24px; text-align: right; flex-shrink: 0; }}
  .fc-whispers   {{ display: flex; flex-direction: column; gap: .3rem; }}
  .fc-whisper    {{ display: flex; flex-direction: column; gap: .1rem; padding: .3rem 0; border-bottom: 1px solid var(--border); }}
  .fc-whisper:last-child {{ border-bottom: none; }}
  .fc-whisper-title {{ font-size: .72rem; font-weight: bold; color: var(--text); }}
  .fc-whisper-text  {{ font-size: .68rem; line-height: 1.4; }}
  .fc-founder-stats {{ display: flex; gap: .8rem; flex-wrap: wrap; }}
  .fc-stat {{ font-family: monospace; font-size: .65rem; }}
  .fc-sparky {{ font-size: .7rem; line-height: 1.5; color: var(--text); font-style: italic; border-left: 2px solid var(--fae); padding-left: .5rem; }}
  .fc-diary-entry {{ font-size: .68rem; line-height: 1.5; margin-top: .1rem; }}
  .fc-diary-kind  {{ font-weight: bold; font-size: .62rem; text-transform: uppercase; }}
  .fc-env-row {{ display: flex; justify-content: space-between; align-items: baseline; padding: .2rem 0; border-bottom: 1px solid var(--border); gap: .5rem; }}
  .fc-env-row:last-child {{ border-bottom: none; }}
  .fc-env-loc   {{ font-size: .72rem; color: var(--text); }}
  .fc-env-state {{ font-family: monospace; font-size: .6rem; text-align: right; flex-shrink: 0; }}

  /* ── Heartbeat ── */
  .heartbeat-head {{
    display:flex; justify-content:space-between; gap:1rem; align-items:flex-start;
    background:rgba(255,251,238,.52); border:1px solid var(--border); border-radius:3px;
    padding:.75rem .9rem; margin-bottom:.65rem;
  }}
  .heartbeat-title {{ font-size:1rem; color:var(--text); font-weight:bold; }}
  .heartbeat-sub {{ font-size:.72rem; line-height:1.5; margin-top:.15rem; }}
  .heartbeat-stamp {{ font-family:monospace; font-size:.68rem; display:flex; flex-direction:column; align-items:flex-end; gap:.15rem; white-space:nowrap; }}
  .heartbeat-grid {{ display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); gap:.55rem; }}
  .hb-block {{
    background:rgba(255,251,238,.46); border:1px solid var(--border); border-radius:3px;
    padding:.65rem .75rem; min-width:0;
  }}
  .hb-block-wide {{ grid-column:1 / -1; }}
  .hb-row {{ display:grid; grid-template-columns:110px 1fr; gap:.55rem; padding:.24rem 0; border-bottom:1px solid var(--border); }}
  .hb-row:last-child {{ border-bottom:none; }}
  .hb-row-compact {{ grid-template-columns:82px 1fr; }}
  .hb-label {{ font-family:monospace; font-size:.62rem; color:var(--muted); text-transform:uppercase; letter-spacing:.04em; }}
  .hb-value {{ font-size:.72rem; line-height:1.45; color:var(--text); white-space:pre-wrap; }}
  .hb-list {{ padding-left:1rem; display:flex; flex-direction:column; gap:.2rem; }}
  .hb-list li {{ font-size:.72rem; line-height:1.45; color:var(--text); }}
  .hb-note {{ font-size:.72rem; line-height:1.55; color:var(--text); border-left:2px solid var(--rule); padding-left:.55rem; margin-top:.35rem; }}
  .hb-note:first-of-type {{ margin-top:0; }}
  .hb-note-kind {{ display:inline-block; font-family:monospace; font-size:.62rem; text-transform:uppercase; letter-spacing:.05em; margin-right:.4rem; }}
  .hb-sparky {{ border-left-color:var(--fae); font-style:italic; }}

  /* ── Schedule ── */
  .sched-now {{
    display: flex; justify-content: space-between; gap: 1rem;
    border: 1px solid; border-radius: 3px; padding: .7rem .85rem; margin-bottom: .1rem;
    background: rgba(255,251,238,.42);
  }}
  .sched-now-left, .sched-now-right {{ display: flex; flex-direction: column; gap: .2rem; }}
  .sched-now-block {{ font-family: monospace; font-size: .85rem; font-weight: bold; letter-spacing: .1em; }}
  .sched-now-hours {{ font-family: monospace; font-size: .65rem; }}
  .sched-now-desc  {{ font-size: .65rem; font-style: italic; }}
  .sched-now-day   {{ font-size: .8rem; font-weight: bold; text-align: right; }}
  .sched-now-tone  {{ font-family: monospace; font-size: .65rem; text-align: right; color: var(--muted); text-transform: uppercase; letter-spacing: .08em; }}
  .sched-now-session {{ font-size: .7rem; text-align: right; color: var(--text); max-width: 220px; line-height: 1.4; }}
  .sched-section-label {{ font-family: monospace; font-size: .6rem; text-transform: uppercase; letter-spacing: .1em; color: var(--muted); display: block; }}
  .sched-today-header {{ display: flex; align-items: center; gap: .6rem; margin-bottom: .4rem; }}
  .sched-tone-badge {{
    font-family: monospace; font-size: .6rem; text-transform: uppercase; letter-spacing: .08em;
    background: rgba(108,72,36,.10); color: var(--muted); padding: .1rem .35rem; border-radius: 2px;
  }}
  .sched-slots {{ display: flex; flex-direction: column; gap: .3rem; }}
  .sched-slot {{
    display: flex; align-items: baseline; gap: .6rem;
    padding: .3rem .5rem; border: 1px solid var(--border); border-radius: 3px;
    background: rgba(255,251,238,.45);
  }}
  .sched-slot-empty {{ border-color: transparent !important; background: transparent !important; }}
  .sched-slot-time  {{ font-family: monospace; font-size: .6rem; flex-shrink: 0; width: 56px; }}
  .sched-slot-name  {{ font-size: .75rem; font-weight: bold; flex: 1; }}
  .sched-slot-prof  {{ font-size: .65rem; flex-shrink: 0; }}
  .sched-slot-compass {{ font-family: monospace; font-size: .6rem; flex-shrink: 0; }}
  .sched-week {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: .3rem; }}
  .sched-day-col {{
    display: flex; flex-direction: column; gap: .25rem;
    border: 1px solid var(--border); border-radius: 3px; padding: .4rem .3rem;
    cursor: pointer; background: rgba(255,251,238,.42);
  }}
  .sched-day-col:hover {{ opacity: .85; }}
  .sched-day-col-name {{ font-family: monospace; font-size: .65rem; font-weight: bold; color: var(--muted); }}
  .sched-day-col-name-today {{ color: var(--teal-ink) !important; }}
  .sched-day-col-num  {{ font-family: monospace; font-size: .55rem; }}
  .sched-day-col-slot {{ font-size: .6rem; min-height: 1rem; }}
  .sched-mini-class   {{ display: block; line-height: 1.35; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: .6rem; }}
  .sched-mini-empty   {{ font-size: .6rem; }}
  .sched-blocks {{ display: flex; flex-wrap: wrap; gap: .3rem; }}
  .sched-block {{
    display: flex; flex-direction: column; gap: .1rem;
    border: 1px solid var(--border); border-radius: 3px; padding: .3rem .5rem;
    min-width: 100px;
    background: rgba(255,251,238,.32);
  }}
  .sched-block-active {{ font-weight: bold; }}
  .sched-block-name {{ font-size: .7rem; }}
  .sched-block-hrs  {{ font-family: monospace; font-size: .6rem; }}

  /* ── Inventory ── */
  .inv-row {{ padding: .4rem 0; border-bottom: 1px solid var(--border); }}
  .inv-row:last-child {{ border-bottom: none; }}
  .inv-name {{ font-size: .78rem; font-weight: bold; color: var(--text); margin-bottom: .15rem; }}
  .inv-desc {{ font-size: .72rem; color: var(--muted); line-height: 1.5; }}
  .inv-label {{ font-style: italic; color: var(--teal-ink); }}

  /* ── Anchor cards ── */
  .anchor-grid {{ display: flex; flex-direction: column; gap: .6rem; }}
  .anchor-card {{
    background: rgba(255,251,238,.50); border: 1px solid; border-radius: 3px;
    padding: .65rem .75rem; display: flex; flex-direction: column; gap: .35rem;
  }}
  .anchor-header {{ display: flex; justify-content: space-between; align-items: baseline; gap: .5rem; }}
  .anchor-name {{ font-size: .83rem; font-weight: bold; }}
  .anchor-type {{ font-family: monospace; font-size: .65rem; font-weight: bold; letter-spacing: .06em; flex-shrink: 0; }}
  .anchor-dir {{ color: var(--muted); font-weight: normal; }}
  .anchor-echo {{ font-size: .72rem; line-height: 1.5; color: var(--text); font-style: italic; }}
  .anchor-meta {{ display: flex; gap: .8rem; flex-wrap: wrap; margin-top: .1rem; }}
  .anchor-stat {{ font-family: monospace; font-size: .65rem; color: var(--text); }}

  /* ── Sub-tabs ── */
  .tab-bar {{
    display: flex; border-bottom: 1px solid var(--rule); padding: .55rem .85rem 0; gap: .2rem;
    background: rgba(108,72,36,.06); flex-wrap: wrap;
  }}
  .tab {{
    padding: .38rem .7rem .34rem; font-family: "Courier New", monospace; font-size: .62rem;
    text-transform: uppercase; letter-spacing: .08em;
    color: var(--muted); cursor: pointer; border-bottom: 2px solid transparent;
    background: rgba(255,251,238,.32); border-top: 1px solid rgba(89,62,35,.18); border-left: 1px solid rgba(89,62,35,.18); border-right: 1px solid rgba(89,62,35,.18);
    border-radius: 3px 3px 0 0;
    transition: color .15s;
  }}
  .tab.active {{ color: var(--ink); border-bottom-color: var(--teal-ink); background: rgba(255,251,238,.72); }}
  .tab-content {{ display: none; padding: .75rem 1rem; }}
  .tab-content.active {{ display: block; }}
  @media (max-width: 980px) {{
    .grid {{ grid-template-columns: 1fr; }}
    body::after {{ display:none; }}
    .folio-logo {{ width:100%; max-height:170px; }}
    .folio-marks {{ padding-right:0; }}
    .topbar {{ flex-wrap: wrap; gap: .65rem; }}
    .topbar-refresh-btn {{ margin-left: 0; }}
    .arc-body, .fc-grid {{ grid-template-columns: 1fr; }}
    .heartbeat-grid {{ grid-template-columns: 1fr; }}
    .hb-block-wide {{ grid-column:auto; }}
    .hb-row {{ grid-template-columns:1fr; gap:.15rem; }}
    .sched-week {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  }}
</style>
</head>
<body>

<div class="topbar" id="data-topbar">
  <div class="topbar-title">⋈ Story-Field Journal</div>
  <div class="topbar-divider">·</div>
  <div class="topbar-item">
    <span class="topbar-label">student</span>
    <span>{h(player.get("name","bj").upper())}</span>
  </div>
  <div class="topbar-item">
    <span class="topbar-label">belief</span>
    <span>{h(player.get("belief","?"))}</span>
    <span class="belief-inline"><span class="belief-inline-fill" style="width:{belief_pct}%"></span></span>
  </div>
  <div class="topbar-item">
    <span class="topbar-label">chapter</span>
    <span style="color:{CHAPTER_COLOR.get(player.get("chapter","?").lower(),"#a1a1aa")}">{h(player.get("chapter","?"))}</span>
  </div>
  <div class="topbar-item">
    <span class="topbar-label">tutorial</span>
    <span>{h(player.get("tutorial","?"))}</span>
  </div>
  <div class="topbar-item">
    <span class="topbar-label">bleed</span>
    <span style="color:{bleed_status_color}">{bleed_label} {bleed_issue}</span>
  </div>
  <button class="topbar-refresh-btn" onclick="softRefresh(true)">↻</button>
  <div class="topbar-refresh">next refresh in <span id="data-countdown">3:00</span> · <span id="data-generated">generated {generated}</span></div>
</div>

<header class="folio-mast">
  <div class="folio-sheet">
    <img class="folio-logo" src="mission-control-assets/enchantify-logo.png" alt="Enchantify — The Labyrinth of Stories">
    <div class="folio-kicker">Story-Field Journal · annotated folio · live apparatus</div>
    <h1 class="folio-title">Story-Field Journal</h1>
    <div class="folio-sub">A working page of the Labyrinth: threads, heartbeat, forecasts, anchors, automations, app actions, entities, images, and the current state of the Academy gathered into one annotated folio.</div>
    <div class="folio-marks">
      <span class="folio-mark">{len(threads)} active threads</span>
      <span class="folio-mark">{len(npcs)} registered entities</span>
      <span class="folio-mark">{len(anchors)} anchors</span>
      <span class="folio-mark">Belief {h(player.get("belief","?"))}/100</span>
      <span class="folio-mark">{bleed_label} {bleed_issue}</span>
      <span class="folio-mark">Heartbeat {h((heartbeat or {}).get("pulse_ts","—"))}</span>
    </div>
  </div>
</header>

<div class="grid">

  <!-- ── Left column ── -->
  <div style="display:flex;flex-direction:column;gap:1rem">

    <!-- Thread Map -->
    <div class="panel">
      <div class="panel-header">Thread Map <span id="data-thread-count">{len(threads)} active</span></div>
      <div class="panel-body" id="data-arc-threads" style="display:flex;flex-direction:column;gap:.85rem">
        {arc_html}
        <div class="thread-grid">
          {thread_cards}
        </div>
      </div>
    </div>

    <!-- World Register + Tick Feed (tabbed) -->
    <div class="panel">
      <div class="tab-bar">
        <button class="tab active" onclick="switchTab(this,'tick')">Simulation Feed</button>
        <button class="tab" onclick="switchTab(this,'queue')">Session Queue</button>
        <button class="tab" onclick="switchTab(this,'forecast')">Forecast</button>
        <button class="tab" onclick="switchTab(this,'heartbeat')">Heartbeat</button>
        <button class="tab" onclick="switchTab(this,'entities')">Entities</button>
        <button class="tab" onclick="switchTab(this,'talismans')">Talisman War</button>
        <button class="tab" onclick="switchTab(this,'pact-actions')">App Actions</button>
        <button class="tab" onclick="switchTab(this,'anchors')">Anchors <span style="color:var(--muted);font-size:.6rem">({len(anchors)})</span></button>
        <button class="tab" onclick="switchTab(this,'images')">Images <span style="color:var(--muted);font-size:.6rem">({len(gallery_entries)})</span></button>
        <button class="tab" onclick="switchTab(this,'inventory')">Inventory</button>
        <button class="tab" onclick="switchTab(this,'schedule')">Schedule</button>
      </div>
      <div id="tick" class="tab-content active">
        <div class="tick-feed">{sim_html}</div>
      </div>
      <div id="queue" class="tab-content">
        <div class="tick-feed">{queue_html}</div>
      </div>
      <div id="entities" class="tab-content">
        {entities_html}
      </div>
      <div id="talismans" class="tab-content">
        {tal_bars}
      </div>
      <div id="pact-actions" class="tab-content">
        <div class="tick-feed">{pact_html}</div>
      </div>
      <div id="anchors" class="tab-content">
        <div class="anchor-grid">{anchors_html}</div>
      </div>
      <div id="images" class="tab-content">
        {gallery_html}
      </div>
      <div id="inventory" class="tab-content">
        {inventory_html}
      </div>
      <div id="schedule" class="tab-content">
        {schedule_html}
      </div>
      <div id="forecast" class="tab-content">
        {forecast_html}
      </div>
      <div id="heartbeat" class="tab-content">
        {heartbeat_html}
      </div>
    </div>

  </div>

  <!-- ── Right column ── -->
  <div style="display:flex;flex-direction:column;gap:1rem">

    <!-- Player -->
    <div class="panel">
      <div class="panel-header">Player Status</div>
      <div class="panel-body" id="data-player">
        <div class="stat-row">
          <div class="stat"><span class="stat-key">name </span>{h(player.get("name","?"))}</div>
          <div class="stat"><span class="stat-key">compass </span>{h(player.get("compass_total","0"))} runs</div>
        </div>
        <div class="belief-bar-wrap">
          <div class="belief-bar-track">
            <div class="belief-bar-fill" style="width:{belief_pct}%"></div>
          </div>
          <div class="belief-label">Belief {h(player.get("belief","?"))} / 100</div>
        </div>
        <div class="section-label">Active Quests</div>
        {quest_html}
        <div class="section-label">The Margin (Fae)</div>
        {fae_html}
      </div>
    </div>

    <!-- Narrative Stewardship -->
    <div class="panel">
      <div class="panel-header">Narrative Stewardship</div>
      <div class="panel-body" id="data-narrative-health">
        {narrative_health_html}
      </div>
    </div>

    <!-- Automation -->
    <div class="panel">
      <div class="panel-header">Automation</div>
      <div class="panel-body" id="data-automation">
        <div class="bleed-status">
          <span class="bleed-dot" style="color:{bleed_status_color}">◉</span>
          <span>The Bleed — {bleed_label} {bleed_issue}</span>
        </div>
        {automation_health_html}
        <div class="section-label" style="margin-top:.8rem">Cron Jobs</div>
        <table class="cron-table">
          <tbody>{cron_html}</tbody>
        </table>
      </div>
    </div>

  </div>
</div>

<div id="modal-overlay" class="modal-overlay" onclick="if(event.target===this)closeModal()">
  <div class="modal-box">
    <div class="modal-header">
      <div class="modal-title" id="modal-title"></div>
      <button class="modal-close" onclick="closeModal()">×</button>
    </div>
    <div class="modal-body" id="modal-body"></div>
  </div>
</div>

<script>
// ── Tabs ──────────────────────────────────────────────────────────────────────
function switchTab(btn, id) {{
  const panel = btn.closest('.panel');
  panel.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  panel.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById(id).classList.add('active');
}}

// ── Modal ─────────────────────────────────────────────────────────────────────
const escHtml = s => String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

function openModal(el) {{
  const data = JSON.parse(el.dataset.modal);
  document.getElementById('modal-title').textContent = data.title;
  document.getElementById('modal-body').innerHTML = data.fields.map(f =>
    `<div class="mf-row">
      <div class="mf-label">${{escHtml(f.k)}}</div>
      <div class="mf-value">${{escHtml(f.v).replace(/\\n/g,'<br>')}}</div>
    </div>`
  ).join('');
  document.getElementById('modal-overlay').classList.add('open');
}}

function selectGalleryImage(btn) {{
  const panel = btn.closest('.gallery-shell');
  if (!panel) return;
  panel.querySelectorAll('.gallery-thumb').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
  const img = panel.querySelector('#gallery-stage-image');
  const title = panel.querySelector('#gallery-stage-title');
  const sub = panel.querySelector('#gallery-stage-sub');
  const caption = panel.querySelector('#gallery-stage-caption');
  const wrap = panel.querySelector('#gallery-stage-wrap');
  if (img) {{
    img.src = btn.dataset.fullsrc || '';
    img.alt = btn.dataset.title || '';
  }}
  if (title) title.textContent = btn.dataset.title || '';
  if (sub) sub.textContent = btn.dataset.meta || '';
  if (caption) caption.textContent = btn.dataset.caption || '';
  if (wrap && btn.dataset.modal) wrap.dataset.modal = btn.dataset.modal;
}}

function closeModal() {{
  document.getElementById('modal-overlay').classList.remove('open');
}}

document.addEventListener('keydown', e => {{ if (e.key === 'Escape') closeModal(); }});

// ── Soft refresh ──────────────────────────────────────────────────────────────
const REFRESH_MS = 3 * 60 * 1000;  // 3 minutes
const DATA_REGIONS =[
  'data-topbar', 'data-thread-count', 'data-arc-threads',
  'tick', 'entities', 'talismans', 'anchors', 'images', 'inventory', 'schedule', 'forecast',
  'data-player', 'data-narrative-health', 'data-automation',
];

let refreshTimeout, countdownInterval, nextRefreshAt;

function updateCountdown() {{
  const rem = Math.max(0, Math.round((nextRefreshAt - Date.now()) / 1000));
  const m = Math.floor(rem / 60), s = rem % 60;
  const el = document.getElementById('data-countdown');
  if (el) el.textContent = m + ':' + String(s).padStart(2,'0');
}}

async function softRefresh(immediate) {{
  // Skip if modal is open and not a manual trigger
  if (!immediate && document.getElementById('modal-overlay').classList.contains('open')) {{
    scheduleRefresh(); return;
  }}

  const btn = document.querySelector('.topbar-refresh-btn');
  if (btn) btn.classList.add('spinning');

  try {{
    const res  = await fetch(location.href + '?nc=' + Date.now());
    const html = await res.text();
    const doc  = new DOMParser().parseFromString(html, 'text/html');

    // Snapshot active tab IDs before patching
    const activeTabIds = {{}};
    document.querySelectorAll('.tab-content.active').forEach(el => {{
      if (el.id) activeTabIds[el.id] = true;
    }});

    for (const id of DATA_REGIONS) {{
      const src = doc.getElementById(id);
      const dst = document.getElementById(id);
      if (src && dst) dst.innerHTML = src.innerHTML;
    }}

    // Restore active tabs (innerHTML swap resets active class on content divs)
    document.querySelectorAll('.tab-content').forEach(el => {{
      el.classList.toggle('active', !!activeTabIds[el.id]);
    }});

    const gen = doc.getElementById('data-generated');
    const dst = document.getElementById('data-generated');
    if (gen && dst) dst.textContent = gen.textContent;
  }} catch(e) {{
    console.warn('soft refresh failed:', e);
  }}

  if (btn) btn.classList.remove('spinning');
  scheduleRefresh();
}}

function scheduleRefresh() {{
  clearTimeout(refreshTimeout);
  clearInterval(countdownInterval);
  nextRefreshAt = Date.now() + REFRESH_MS;
  updateCountdown();
  countdownInterval = setInterval(updateCountdown, 1000);
  refreshTimeout = setTimeout(() => softRefresh(false), REFRESH_MS);
}}

scheduleRefresh();
</script>
</body>
</html>'''


# ── Entry point ───────────────────────────────────────────────────────────────

def generate() -> str:
    threads   = parse_threads()
    npcs, talismans = parse_entities()
    player    = parse_player()
    queue     = parse_tick_queue()
    sim_feed  = parse_simulation_feed()
    pact_actions = parse_pact_actions()
    bleed     = parse_bleed_status()
    crons     = parse_cron_jobs()
    arc       = parse_arc()
    anchors   = parse_anchors(player.get("name", "bj"))
    sched    = parse_schedule()
    forecast = parse_forecast(talismans)
    heartbeat = parse_current_heartbeat()
    gallery_entries = parse_scene_gallery()
    narrative_health = parse_narrative_health(player.get("name", "bj"))
    return build_html(threads, npcs, talismans, player, queue, bleed, crons,
                      arc=arc, anchors=anchors, sched=sched, forecast=forecast, heartbeat=heartbeat,
                      sim_feed=sim_feed, pact_actions=pact_actions, gallery_entries=gallery_entries,
                      narrative_health=narrative_health)


def main():
    parser = argparse.ArgumentParser(description="Enchantify Story-Field Journal")
    parser.add_argument("--open",  action="store_true", help="Open in browser after generating")
    parser.add_argument("--serve", action="store_true", help="Serve on http://localhost:9191 with live refresh")
    parser.add_argument("--out",   default=str(BASE / "hooks" / "mission-control.html"), help="Output path")
    args = parser.parse_args()

    out = Path(args.out)

    if args.serve:
        import http.server, threading, time

        def regen():
            while True:
                try:
                    out.write_text(generate())
                except Exception as e:
                    print(f"  [warn] regen error: {e}")
                time.sleep(30)

        t = threading.Thread(target=regen, daemon=True)
        t.start()
        out.write_text(generate())  # initial

        import webbrowser
        os.chdir(out.parent)
        webbrowser.open(f"http://localhost:9191/{out.name}")

        class Handler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, fmt, *a): pass  # silence

        print(f"  Serving at http://localhost:9191/{out.name} — Ctrl-C to stop")
        http.server.HTTPServer(("localhost", 9191), Handler).serve_forever()
        return

    html = generate()
    out.write_text(html)
    print(f"  ✓ Generated {out}")

    if args.open:
        import subprocess as _sp
        _sp.run(["open", str(out)])


if __name__ == "__main__":
    main()

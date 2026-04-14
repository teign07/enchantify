#!/usr/bin/env python3
"""
world_context.py — Shared time and NPC location context for simulation scripts.

Imported by tick.py and world-pulse.py. Not run directly.

Provides:
  get_time_context()           → current schedule data dict (wraps schedule.py)
  get_npc_state(name, type, data) → {location, state, stirrable, note}
  is_night(data)               → True if block == "night"
  time_tag(data)               → "night" | "morning class" | "club hour" etc.
  time_seed_prefix(data)       → brief narrative string for tick-queue entries
"""

import importlib.util
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent

# ── Import schedule.py ────────────────────────────────────────────────────────
_spec  = importlib.util.spec_from_file_location("schedule", _SCRIPT_DIR / "schedule.py")
_sched = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sched)

CLASSES       = _sched.CLASSES
WEEKDAY_NAMES = _sched.WEEKDAY_NAMES
DAY_TONES     = _sched.DAY_TONES


# ── Block labels ──────────────────────────────────────────────────────────────

_BLOCK_TAGS = {
    "early_morning":   "early morning",
    "morning_class":   "morning class",
    "mid_morning":     "mid-morning",
    "lunch":           "lunch hour",
    "afternoon_class": "afternoon class",
    "free_period":     "free period",
    "evening":         "evening",
    "club_time":       "club hour",
    "night":           "night",
}

_CLUB_LOCATIONS = {
    "Inkwright Society":          "Bibliophonic Hall",
    "Marginalia Guild":           "Corridor of Whispered Secrets",
    "Compass Society":            "Secret Garden of Prose",
    "Book Jumpers":               "Room of Chrono-Tomes",
    "Still Club":                 "Secret Garden",
}

# Professor last-name → full display name
_PROF_MAP = {
    "boggle":     "Prof. Boggle",
    "momort":     "Prof. Momort",
    "euphony":    "Prof. Euphony",
    "villanelle": "Prof. Villanelle",
    "stonebrook": "Prof. Stonebrook",
}

# Named student NPCs: lowercase last name → (club_name, weekday_index or None)
_NPC_CLUBS = {
    "thorne": ("Inkwright Society", 0),   # Monday
    "zara":   ("Compass Society",   6),   # Sunday
    "corin":  ("Book Jumpers",      4),   # Friday
}


# ── Core API ──────────────────────────────────────────────────────────────────

def get_time_context(override_day=None, override_time=None) -> dict:
    """Return current schedule data dict from schedule.py."""
    return _sched.get_schedule_data(override_day=override_day, override_time=override_time)


def is_night(data: dict = None) -> bool:
    if data is None:
        data = get_time_context()
    return data["block"] == "night"


def time_tag(data: dict = None) -> str:
    """Brief human-readable label for the current time block."""
    if data is None:
        data = get_time_context()
    return _BLOCK_TAGS.get(data["block"], data["block"])


def get_npc_state(name: str, entity_type: str = "NPC", data: dict = None) -> dict:
    """
    Return current location and availability for a named entity.

    entity_type: if not "NPC", the entity doesn't sleep and has no schedule
                 (Talisman, Place, Concept, etc. are always stirrable).

    Returns:
      location   str  — where they are right now
      state      str  — "teaching" | "in_class" | "club" | "sleeping" | "free"
      stirrable  bool — False only for sleeping NPCs
      note       str  — brief narrative detail, or None
    """
    # Non-NPC entities are always stirrable — they don't sleep
    if entity_type.lower() not in ("npc", "creature"):
        return {"location": None, "state": "free", "stirrable": True, "note": None}

    if data is None:
        data = get_time_context()

    block   = data["block"]
    weekday = data["weekday"]

    # Use last word of name for matching: "Prof. Boggle" → "boggle"
    name_lc = name.lower().split()[-1]

    # ── Night: NPCs and creatures sleep ──────────────────────────────────────
    if block == "night":
        return {
            "location":  "their quarters",
            "state":     "sleeping",
            "stirrable": False,
            "note":      "asleep",
        }

    # ── Professors — derive from CLASSES schedule ─────────────────────────────
    if name_lc in _PROF_MAP:
        full_name   = _PROF_MAP[name_lc]
        day_classes = CLASSES.get(weekday, {})

        if block == "morning_class":
            cls = day_classes.get("morning")
            if cls and cls[1] == full_name:
                return {
                    "location":  cls[2],
                    "state":     "teaching",
                    "stirrable": True,
                    "note":      f"mid-class in {cls[2]} — {cls[0]}",
                }

        elif block == "afternoon_class":
            cls = day_classes.get("afternoon")
            if cls and cls[1] == full_name:
                return {
                    "location":  cls[2],
                    "state":     "teaching",
                    "stirrable": True,
                    "note":      f"teaching {cls[0]} in {cls[2]}",
                }

        # Not teaching this block — in office / free
        return {
            "location":  f"{full_name}'s study",
            "state":     "free",
            "stirrable": True,
            "note":      None,
        }

    # ── Known student NPCs — club affiliations ────────────────────────────────
    if name_lc in _NPC_CLUBS:
        club_name, club_day = _NPC_CLUBS[name_lc]
        if block == "club_time" and weekday == club_day:
            loc = _CLUB_LOCATIONS.get(club_name, "Academy grounds")
            return {
                "location":  loc,
                "state":     "club",
                "stirrable": True,
                "note":      f"at {club_name}",
            }

    # ── Generic student NPC: follow the Academy schedule ─────────────────────
    if block == "morning_class":
        cls = CLASSES.get(weekday, {}).get("morning")
        if cls:
            return {
                "location":  cls[2],
                "state":     "in_class",
                "stirrable": True,
                "note":      f"in {cls[0]}",
            }

    elif block == "afternoon_class":
        cls = CLASSES.get(weekday, {}).get("afternoon")
        if cls:
            return {
                "location":  cls[2],
                "state":     "in_class",
                "stirrable": True,
                "note":      f"in {cls[0]}",
            }

    elif block == "club_time":
        club = CLASSES.get(weekday, {}).get("club")
        if club:
            loc = _CLUB_LOCATIONS.get(club[0], club[1])
            return {
                "location":  loc,
                "state":     "club",
                "stirrable": True,
                "note":      f"at {club[0]}",
            }

    # Free period, early morning, mid-morning, lunch, evening
    return {
        "location":  "Academy grounds",
        "state":     "free",
        "stirrable": True,
        "note":      None,
    }


def time_seed_prefix(data: dict = None) -> str:
    """
    A short situating phrase for tick-queue entries.
    Example outputs:
      "2:00 AM — Academy asleep."
      "Morning class in session — The Art of the Glint (Prof. Boggle)."
      "Club hour — Inkwright Society meeting tonight."
    """
    if data is None:
        data = get_time_context()

    block = data["block"]
    hour  = data["hour"]
    h12   = hour % 12 or 12
    am_pm = "AM" if hour < 12 else "PM"

    if block == "night":
        return f"{h12}:00 {am_pm} — Academy asleep."
    elif block == "early_morning":
        return f"{h12}:00 {am_pm} — Academy stirring."
    elif block == "morning_class":
        cls = data.get("class_now")
        if cls:
            return f"Morning class in session — {cls[0]} ({cls[1]})."
        return "Morning block — no class today."
    elif block == "mid_morning":
        return "Mid-morning — classes just released, corridors shifting."
    elif block == "lunch":
        return "Lunch hour — Academy scattered."
    elif block == "afternoon_class":
        cls = data.get("class_now")
        if cls:
            return f"Afternoon class in session — {cls[0]} ({cls[1]})."
        return "Afternoon block — free study."
    elif block == "free_period":
        return "Free period — students drifting."
    elif block == "evening":
        return "Evening — Academy settling before clubs."
    elif block == "club_time":
        club = data.get("club")
        if club:
            return f"Club hour — {club[0]} meeting tonight."
        return "Club hour — no club tonight, Academy quiet."
    return ""

#!/usr/bin/env python3
"""
mission-control.py — Enchantify Mission Control Dashboard

Reads live workspace data and generates a self-refreshing HTML dashboard.

Usage:
  python3 scripts/mission-control.py           # generate → mission-control.html
  python3 scripts/mission-control.py --open    # generate + open in browser
  python3 scripts/mission-control.py --serve   # serve on http://localhost:9191
"""
import os
import re
import sys
import json
import html as _html
import shutil
import subprocess
import argparse
from pathlib import Path
from datetime import datetime, date, timedelta

BASE        = Path(__file__).parent.parent
THREADS_F   = BASE / "lore" / "threads.md"
REGISTER_F  = BASE / "lore" / "world-register.md"
CURRENT_ARC = BASE / "lore" / "current-arc.md"
QUEUE_F     = BASE / "memory" / "tick-queue.md"
PATTERNS_F  = BASE / "memory" / "patterns.md"
ISSUES_DIR  = BASE / "bleed" / "issues"
LOGS_DIR    = BASE / "logs"
PLAYERS_DIR = BASE / "players"
HEARTBEAT_F = BASE / "HEARTBEAT.md"
NOTHING_F   = BASE / "lore" / "nothing-intelligence.md"
ARC_SPINE_F = BASE / "memory" / "arc-spine.md"

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

PHASE_ORDER = ["dormant", "setup", "rising", "climax", "resolution"]
PHASE_PCT   = {"dormant": 0, "setup": 20, "rising": 45, "climax": 70, "resolution": 92, "permanent": 0}

# ── Academy schedule constants ────────────────────────────────────────────────

# weekday() → 0=Mon … 6=Sun
ACADEMY_DAYS = {
    6: {"name": "Sunday",    "num": 1, "tone": "Opening",   "desc": "Light classes. Students settle in. The Library rearranges overnight and everyone is slightly confused."},
    0: {"name": "Monday",    "num": 2, "tone": "Building",  "desc": "Heavier coursework. Study groups form. The corridor near Mossbloom smells like brewing something."},
    1: {"name": "Tuesday",   "num": 3, "tone": "Deepening", "desc": "Mid-week — the week has found its shape. Breakthroughs and arguments both happen here."},
    2: {"name": "Wednesday", "num": 4, "tone": "Hinge",     "desc": "Something always turns on Day 4. A discovery, a conflict, a revelation. Not dramatic necessarily — just turning."},
    3: {"name": "Thursday",  "num": 5, "tone": "Releasing", "desc": "Energy loosens toward the weekend. Evening clubs. The Cafeteria has good soup on Day 5."},
    4: {"name": "Friday",    "num": 6, "tone": "Wandering", "desc": "No mandatory classes. Students explore, practice, argue, make things. The Library opens additional wings."},
    5: {"name": "Saturday",  "num": 7, "tone": "Still",     "desc": "The quietest day. Professors walk the grounds. Perfect for solo study, long Compass Runs, or doing nothing with great intention."},
}

ACADEMY_WEEKLY = {
    "Sunday":    {"morning": None,                                   "afternoon": None,                            "club": "Compass Society"},
    "Monday":    {"morning": ("Art of the Glint",        "Boggle"),  "afternoon": ("Ink-Binding",       "Villanelle"), "club": "Inkwright Society"},
    "Tuesday":   {"morning": ("Wayfinding & Kineticism", "Momort"),  "afternoon": ("Synesthetic Resonance", "Euphony"), "club": "Marginalia Guild"},
    "Wednesday": {"morning": ("Art of the Glint",        "Boggle"),  "afternoon": ("Quiet Hours",       "Stonebrook"), "club": None},
    "Thursday":  {"morning": ("Wayfinding & Kineticism", "Momort"),  "afternoon": ("Ink-Binding",       "Villanelle"), "club": "Marginalia Guild"},
    "Friday":    {"morning": ("Synesthetic Resonance",   "Euphony"), "afternoon": ("Independent Study", None),        "club": "Book Jumpers"},
    "Saturday":  {"morning": None,                                   "afternoon": None,                            "club": None},
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
    "Independent Study": {
        "compass": "Free", "color": "#374151",
        "desc":       "Student-directed. The Library opens additional wings on Wandering Day.",
        "assignment": "No assigned practice — student directed.",
        "reward":     "Variable",
        "quote":      "",
    },
}

TIME_BLOCKS = [
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


def parse_threads() -> list[dict]:
    text = read(THREADS_F)
    register = read(REGISTER_F)

    # Build belief lookup from world-register Active Threads
    # Use (?m)^ to anchor to actual line-start headings (avoids matching inline `## Active Threads` in comments)
    belief: dict[str, int] = {}
    active_m = re.search(r'(?m)^## Active Threads\s*\n(.*?)(?=^## |\Z)', register, re.DOTALL)
    if active_m:
        for m in re.finditer(r'^\|\s*([^|]+?)\s*\|\s*Thread\s*\|\s*(\d+)\s*\|',
                             active_m.group(1), re.MULTILINE | re.IGNORECASE):
            belief[m.group(1).strip().lower()] = int(m.group(2))

    # Non-standard phase labels → canonical
    PHASE_ALIASES = {
        "escalating": "rising",
        "quiet":      "permanent",  # academy-daily
        "rising,":    "rising",
        "setup,":     "setup",
        "climax,":    "climax",
        "dormant,":   "dormant",
    }

    threads = []
    for section in re.split(r'^## Thread: ', text, flags=re.MULTILINE)[1:]:
        lines = section.strip().splitlines()
        name = lines[0].strip() if lines else "?"

        # Skip template placeholders and meta-threads
        if name.startswith("["):            continue  # e.g. [Anchor Name]
        if "Adding New Threads" in name:    continue
        next_beat_raw = re.search(r'\*\*Next beat:\*\*\s*(.+)', section)
        next_beat_val = next_beat_raw.group(1).strip() if next_beat_raw else ""
        if next_beat_val.startswith("*(read from"):  continue  # Current Arc defers elsewhere
        if next_beat_val.startswith("["):             continue  # template placeholder

        def field(pat):
            m = re.search(pat, section)
            return m.group(1).strip() if m else ""

        phase_raw  = field(r'\*\*phase:\*\*\s*(.+)')
        first_word = phase_raw.split()[0].lower().rstrip(",") if phase_raw else "dormant"
        phase_word = PHASE_ALIASES.get(first_word, first_word)
        # If the raw string contains "permanent", force it
        if "permanent" in phase_raw.lower():
            phase_word = "permanent"
        if phase_word not in PHASE_ORDER and phase_word != "permanent":
            phase_word = "dormant"

        born_raw  = field(r'\*\*born:\*\*\s*(\S+)')
        closed_raw = field(r'\*\*closed:\*\*\s*(\S+)')
        b = belief.get(name.lower(), 0)

        # Age badge
        age_note = ""
        if born_raw and born_raw not in ("—", "-", ""):
            try:
                born = date.fromisoformat(born_raw)
                days = (date.today() - born).days
                if days <= 7:
                    age_note = "new"
            except ValueError:
                pass

        threads.append({
            "name":         name,
            "phase":        phase_word,
            "phase_raw":    phase_raw,
            "belief":       b,
            "pressure":     field(r'\*\*pressure:\*\*\s*(.+)'),
            "nothing":      field(r'\*\*Nothing pressure:\*\*\s*(.+)'),
            "next_beat":    next_beat_val,
            "last_advanced":field(r'\*\*Last advanced:\*\*\s*(.+)'),
            "born":         born_raw,
            "closed":       closed_raw,
            "age_note":     age_note,
            "npc_anchor":   field(r'\*\*npc_anchor:\*\*\s*(.+)'),
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

    # Arc name from H1
    name_m = re.search(r'^# Current Arc — (.+)', text, re.MULTILINE)
    name = name_m.group(1).strip() if name_m else "Current Arc"

    # Phase from world-register Live Arc
    register = read(REGISTER_F)
    arc_belief = 0
    arc_m = re.search(r'(?m)^## Live Arc\s*\n(.*?)(?=^## |\Z)', register, re.DOTALL)
    if arc_m:
        bm = re.search(r'\|\s*[^|]+\|\s*Arc\s*\|\s*(\d+)\s*\|', arc_m.group(1), re.IGNORECASE)
        if bm:
            arc_belief = int(bm.group(1))

    phase   = field(r'^## Phase:\s*(.+)', "?").upper()
    day     = field(r'^## Day:\s*(.+)', "?")
    started = field(r'^## Started:\s*(.+)', "?")
    premise = section("The Premise")
    pressure = section("The Pressure")
    crisis   = section("The Crisis Point")
    compass  = field(r'\*\*(SOUTH|NORTH|EAST|WEST)[^*]*\*\*', "?")
    resolution_block = section("Resolution Paths")

    # Extract resolution paths as bullet list
    res_paths = []
    for m in re.finditer(r'^-\s+\*\*(.+?)\*\*[:\s]*(.+)', resolution_block, re.MULTILINE):
        res_paths.append({"label": m.group(1).strip(), "text": m.group(2).strip()})

    return {
        "name":        name,
        "phase":       phase,
        "day":         day,
        "started":     started,
        "belief":      arc_belief,
        "premise":     premise,
        "pressure":    pressure,
        "crisis":      crisis,
        "compass":     compass,
        "resolution":  res_paths,
        "key_npcs":    section("Key NPCs"),
        "nothing":     section("The Nothing's Role"),
        "seeds":       section("Seeds for Next Arc"),
        "compass_con": section("Wonder Compass Connection"),
    }


def parse_entities() -> tuple[list, list, list]:
    """Returns (npcs, threads_register, talismans)."""
    text = read(REGISTER_F)
    npcs, threads_r, talismans = [], [], []

    row_re = re.compile(
        r'^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|\s*([^|]*)\s*\|',
        re.MULTILINE
    )

    in_talismans = False
    in_active    = False
    for line in text.splitlines():
        # Only trigger on actual section headings (line-start ##), not inline mentions
        stripped = line.strip()
        if re.match(r'^## Chapter Talismans', stripped):
            in_talismans = True; in_active = False; continue
        if re.match(r'^## Active Threads', stripped):
            in_active = True; in_talismans = False; continue
        if re.match(r'^## (?!Active Threads|Chapter Talismans)', stripped):
            in_talismans = False; in_active = False

        m = row_re.match(line)
        if not m: continue
        name, etype, bstr, notes = m.group(1).strip(), m.group(2).strip(), m.group(3), m.group(4).strip()
        if name.lower() in ("entity", "talisman", "name", "---", ""): continue
        try: b = int(bstr)
        except ValueError: continue

        thread_m = re.search(r'\[thread:([^\]]+)\]', notes)
        threads_tag = [t.strip() for t in thread_m.group(1).split(",")] if thread_m else []
        clean_notes = re.sub(r'\[thread:[^\]]+\]', '', notes).strip().strip(";").strip()

        if in_talismans:
            chapter = etype.strip().lower()
            talismans.append({
                "name": name, "chapter": chapter, "belief": b,
                "color": CHAPTER_COLOR.get(chapter, "#555"),
                "philosophy": clean_notes,
            })
        elif in_active:
            pass  # handled in parse_threads
        else:
            npcs.append({
                "name": name, "type": etype, "belief": b,
                "threads": threads_tag, "notes": clean_notes,
            })

    npcs.sort(key=lambda x: -x["belief"])
    talismans.sort(key=lambda x: -x["belief"])
    return npcs, talismans


def parse_player(name: str = "bj") -> dict:
    text = read(PLAYERS_DIR / f"{name}.md")
    if not text: return {}

    def field(pat, default="?"):
        m = re.search(pat, text)
        return m.group(1).strip() if m else default

    # Quests from Inside Cover
    cover_m = re.search(r'## The Inside Cover\n(.*?)(?=\n##|\Z)', text, re.DOTALL)
    quests = []
    if cover_m:
        for m in re.finditer(r'\|\s*\*\*([^*]+)\*\*\s*\|([^|]*)\|\s*\*\*ACTIVE\*\*', cover_m.group(1)):
            quests.append({"npc": m.group(1).strip(), "desc": m.group(2).strip()})

    # Fae margin
    margin_m = re.search(r'## The Margin\n(.*?)(?=\n##|\Z)', text, re.DOTALL)
    bargains = []
    if margin_m:
        for m in re.finditer(r'^\|\s*([^|*][^|]*)\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|',
                             margin_m.group(1), re.MULTILINE):
            fae, gave, terms, deadline, status = [x.strip() for x in m.groups()]
            if fae and not fae.startswith("*"):
                bargains.append({"fae": fae, "status": status, "deadline": deadline})

    # Inventory
    inv_m = re.search(r'\*\*Inventory:\*\*\s*\n(.*?)(?=\n-\s*\*\*[A-Z]|\n##|\Z)', text, re.DOTALL)
    inventory = []
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
    entries = []
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
}


def parse_anchors(name: str = "bj") -> list[dict]:
    text = read(BASE / "players" / f"{name}-anchors.md")
    if not text:
        return []
    anchors = []
    for section in re.split(r'^## ', text, flags=re.MULTILINE)[1:]:
        lines = section.strip().splitlines()
        anchor_name = lines[0].strip()
        if not anchor_name or anchor_name.startswith("*"):
            continue

        def field(pat, default=""):
            m = re.search(pat, section)
            return m.group(1).strip() if m else default

        atype    = field(r'\*\*Type:\*\*\s*(.+)').upper()
        belief   = field(r'\*\*Belief invested:\*\*\s*(\d+)', "0")
        created  = field(r'\*\*Created:\*\*\s*(.+)')
        weather  = field(r'\*\*Weather:\*\*\s*(.+)')
        moon     = field(r'\*\*Moon:\*\*\s*(.+)')
        season   = field(r'\*\*Season:\*\*\s*(.+)')
        echo     = field(r'\*\*Academy echo:\*\*\s*(.+)')
        visits   = field(r'\*\*Visit count:\*\*\s*(.+)', "0")
        last_vis = field(r'\*\*Last visited:\*\*\s*(.+)', "*(none yet)*")
        coords   = field(r'\*\*Coordinates:\*\*\s*(.+)')

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
            "player_words": field(r'\*\*Player\'s words:\*\*\s*(.+)'),
            "outer_stacks": field(r'\*\*Outer Stacks room:\*\*\s*(.+)'),
            "fae":          field(r'\*\*Fae:\*\*\s*(.+)'),
            "mini_story":   field(r'\*\*Mini-story:\*\*\s*(.+)'),
            "local_rule":   field(r'\*\*Local rule:\*\*\s*(.+)'),
        })
    return anchors


def parse_forecast(talismans: list) -> dict:
    hb      = read(HEARTBEAT_F)
    state   = read(BASE / "lore" / "academy-state.md")
    nothing = read(NOTHING_F)
    spine   = read(ARC_SPINE_F)

    def field(text, pat, default=""):
        m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
        return m.group(1).strip() if m else default

    def section(text, heading):
        m = re.search(rf'(?m)^{re.escape(heading)}\s*\n(.*?)(?=^#|\Z)', text, re.DOTALL)
        return m.group(1).strip() if m else ""

    # ── Heartbeat ──
    # Extract only the PULSE block
    pulse_m = re.search(r'<!-- PULSE_START -->(.*?)<!-- PULSE_END -->', hb, re.DOTALL)
    pulse   = pulse_m.group(1) if pulse_m else hb

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

    diary_entries = []
    diary_m = re.search(r'<!-- DIARY_START -->(.*?)<!-- DIARY_END -->', hb, re.DOTALL)
    if diary_m:
        for m in re.finditer(r'\*(Diary|Dream)\s*\([^)]+\):\*\s*(.+)', diary_m.group(1)):
            diary_entries.append({"kind": m.group(1), "text": m.group(2).strip()})

    # ── Unwritten Whispers ──
    whispers = []
    w_m = re.search(r'### 📜 Current Whispers from the Unwritten\s*\n(.*?)(?=\n---|\n## |\Z)',
                    state, re.DOTALL)
    if w_m:
        for m in re.finditer(r'^-\s+\*\*([^*]+)\*\*:\s*(.+)', w_m.group(1), re.MULTILINE):
            whispers.append({"title": m.group(1).strip(), "text": m.group(2).strip()})

    # ── Academy environment ──
    env_rows = []
    env_m = re.search(r'(?m)^## Environment\s*\n(.*?)(?=^## |\Z)', state, re.DOTALL)
    if env_m:
        for m in re.finditer(r'^\|\s*\*\*([^*]+)\*\*\s*\|\s*([^|]+)\|\s*([^|]*)\|',
                             env_m.group(1), re.MULTILINE):
            loc, st, notes = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
            if loc.lower() not in ("location", "---"):
                env_rows.append({"loc": loc, "state": st, "notes": notes})

    # ── Nothing ──
    nothing_pressure = field(nothing, r'Pressure level:\s*(.+)')
    nothing_diary    = field(nothing, r'Diary mentions:\s*(\d+)', "0")
    nothing_strategy = ""
    strat_m = re.search(r'## Current Strategy\s*\n(.+?)(?=\n\n|\n##|\Z)', nothing, re.DOTALL)
    if strat_m:
        nothing_strategy = strat_m.group(1).strip()

    pressure_points = []
    pp_m = re.search(r'## Identified Pressure Points\s*\n(.*?)(?=\n##|\Z)', nothing, re.DOTALL)
    if pp_m:
        for m in re.finditer(r'^-\s+(.+)', pp_m.group(1), re.MULTILINE):
            pressure_points.append(m.group(1).strip())

    # ── Arc spine ──
    belief_state = field(spine, r'Belief:\s*\d+\s*[—-]\s*(.+)')
    ready_for    = []
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


def parse_schedule() -> dict:
    text  = read(BASE / "lore" / "academy-state.md")
    today = ACADEMY_DAYS.get(date.today().weekday(), ACADEMY_DAYS[6])

    # Parse live block from academy-state (updated every 4 hours by simulation)
    current_block = _current_block()
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
        "today":       ACADEMY_WEEKLY.get(today["name"], {}),
    }


def _ms_to_local(ms: int) -> str:
    """Convert epoch-milliseconds to a short local datetime string."""
    try:
        return datetime.fromtimestamp(ms / 1000).strftime("%m-%d %H:%M")
    except Exception:
        return "—"


def parse_cron_jobs() -> list[dict]:
    jobs = []
    try:
        result = subprocess.run(
            [_OPENCLAW, "cron", "list", "--json"],
            capture_output=True, text=True, timeout=10
        )
        data = json.loads(result.stdout)
        items = data if isinstance(data, list) else data.get("jobs", data.get("data", []))
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

            jobs.append({
                "name":     j.get("name", "?")[:45],
                "status":   status,
                "errors":   errors,
                "last":     _ms_to_local(last_ms) if last_ms else "—",
                "next":     _ms_to_local(next_ms) if next_ms else "—",
                "duration": dur_s,
                "delivery": delivery,
                "expr":     expr,
                "tz":       tz,
            })
    except Exception:
        pass

    # ── Supplement with system crontab entries for enchantify scripts ─────────
    openclaw_names = {j["name"] for j in jobs}
    _SCRIPT_LABELS = {
        "pulse.py":               "World Pulse",
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
        ct = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
        for line in ct.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("PATH"):
                continue
            # match any of our scripts
            matched_label = None
            for script, label in _SCRIPT_LABELS.items():
                if script in line:
                    matched_label = label
                    break
            if not matched_label:
                continue
            if matched_label in openclaw_names:
                continue  # already in openclaw list
            # parse cron expression (first 5 fields)
            parts = line.split()
            expr = " ".join(parts[:5]) if len(parts) >= 5 else ""
            # check last log file for recency
            log_hint = ""
            log_map = {
                "reach-out.py":    "reach-out.log",
                "bleed.py":        "bleed.log",
                "sparky.py":       "sparky.log",
                "wallpaper.py":    "wallpaper.log",
                "dream.py":        "dream.log",
                "schedule.py":     "schedule.log",
                "arc-tick.py":     "pulse.log",
                "labyrinth-intelligence.py": "intelligence.log",
                "mission-control.py": "",
            }
            for script, logfile in log_map.items():
                if script in line and logfile:
                    lp = LOGS_DIR / logfile
                    if lp.exists():
                        mtime = lp.stat().st_mtime
                        from datetime import timezone
                        log_hint = datetime.fromtimestamp(mtime).strftime("%-I:%M %p")
                    break
            jobs.append({
                "name":     matched_label,
                "status":   "system",
                "errors":   0,
                "last":     log_hint or "—",
                "next":     "—",
                "duration": "",
                "delivery": "",
                "expr":     expr,
                "tz":       "",
            })
    except Exception:
        pass

    return jobs


# ── HTML generation ───────────────────────────────────────────────────────────

def phase_bar(phase: str, belief: int) -> str:
    """Return an SVG phase bar showing belief position across four bands."""
    if phase == "permanent":
        return '<div class="phase-bar permanent"><span>permanent</span></div>'

    pct  = min(100, max(0, belief * 1.5))  # rough visual fill (belief 65 = 100%)
    color = PHASE_COLOR.get(phase, "#555")
    label = phase.upper()

    bands = [
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
        "fields": [
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
    for r in arc.get("resolution", []):
        res_html += f'<div class="arc-res-row"><span class="arc-res-label">{h(r["label"])}</span> {h(r["text"])}</div>'

    compass = arc.get("compass", "")
    compass_html = f'<span class="arc-compass">⊕ {h(compass)}</span>' if compass and compass != "?" else ""

    res_full = "\n".join(f'{r["label"]}: {r["text"]}' for r in arc.get("resolution", []))
    md = modal_attr(arc.get("name", "Arc"), [
        ("Phase",       f'{phase} · Day {arc.get("day","?")} · started {arc.get("started","")}'),
        ("Belief",      str(arc.get("belief", 0))),
        ("Compass",     arc.get("compass", "")),
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
          <div class="arc-eyebrow">Current Arc · Day {h(arc.get("day","?"))} · {h(arc.get("started",""))}</div>
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
          <div class="arc-section-label">Pressure</div>
          <div class="arc-text">{h(arc.get("pressure","")[:180])}</div>
        </div>
        <div class="arc-col">
          <div class="arc-section-label">Crisis Point</div>
          <div class="arc-text">{h(arc.get("crisis","")[:180])}</div>
        </div>
        <div class="arc-col">
          <div class="arc-section-label">Resolution Paths</div>
          {res_html if res_html else "<div class='arc-text muted'>—</div>"}
        </div>
      </div>
    </div>'''


def render_thread_card(t: dict) -> str:
    color  = PHASE_COLOR.get(t["phase"], "#555")
    badge  = f'<span class="badge-new">new</span>' if t["age_note"] == "new" else ""
    anchor = f'<div class="card-anchor">{h(t["npc_anchor"])}</div>' if t["npc_anchor"] else ""
    beat   = h(t["next_beat"][:160]) if t["next_beat"] else "—"
    last   = h(t["last_advanced"]) if t["last_advanced"] else "never"
    nothing_low = "low" in t["nothing"].lower() if t["nothing"] else True
    nothing_dot = f'<span class="nothing-dot" style="color:{("var(--nothing)" if not nothing_low else "var(--muted)")}" title="Nothing pressure: {h(t["nothing"])}">◆</span>'

    md = modal_attr(t["name"], [
        ("Phase",            f'{t["phase"].title()} · Belief {t["belief"]}'),
        ("Next beat",        t["next_beat"]),
        ("Pressure",         t["pressure"]),
        ("Nothing pressure", t["nothing"]),
        ("NPC anchor",       t["npc_anchor"]),
        ("Born",             t["born"]),
        ("Last advanced",    t["last_advanced"]),
    ])

    return f'''<div class="card clickable" style="border-color:{color}22;--phase-color:{color}" onclick="openModal(this)" data-modal={md}>
      <div class="card-header">
        <div class="card-title" style="color:{color}">{h(t["name"])}{badge}</div>
        {nothing_dot}
      </div>
      {anchor}
      {phase_bar(t["phase"], t["belief"])}
      <div class="card-beat">{beat}</div>
      <div class="card-meta">last advanced: {last}</div>
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
    md = modal_attr(e["name"], [
        ("Type",    e["type"]),
        ("Belief",  str(b)),
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


def render_queue_entry(entry: dict) -> str:
    css  = entry_class(entry["type"])
    text = h(entry["text"])
    # Bold any **..** markers
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    # Italicise *..* markers
    text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
    return f'<div class="entry {css}">{text}</div>'


def render_anchor_card(a: dict) -> str:
    meta      = ANCHOR_TYPE_META.get(a["type"], {"dir": "?", "color": "#555"})
    color     = meta["color"]
    direction = meta["dir"]
    visits    = a["visits"] if a["visits"] != "0" else "unvisited"
    last      = "" if "none yet" in a["last_vis"] else f" · last {h(a['last_vis'])}"
    echo      = h(a["echo"][:140]) if a["echo"] else "—"

    md = modal_attr(a["name"], [
        ("Type",               f'{a["type"]} · {direction}'),
        ("Belief invested",    str(a["belief"])),
        ("Created",            a["created"]),
        ("Season / Weather",   f'{a["season"]} · {a["weather"]}'),
        ("Moon",               a["moon"]),
        ("Coordinates",        a["coords"]),
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

    nothing_md = modal_attr("The Nothing", [
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
    tal_md = modal_attr("Talisman War", [
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
    spine_md = modal_attr("Dramatic Spine", [
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
        wmd = modal_attr(w["title"], [("Whisper", w["text"])])
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

    founder_md = modal_attr("Founder Status", [
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
            md = modal_attr(name, [
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
        slots     = ACADEMY_WEEKLY.get(dname, {})
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

        tone_md = modal_attr(f'{dname} · Day {day_data.get("num","?")}', [
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
    elif status in ("ok", "success"):
        dot_color, dot_title = "var(--seed)",    "last run ok"
    else:
        dot_color, dot_title = "var(--muted)",   status or "unknown"

    dur        = f'<span class="cron-dur muted"> {h(job["duration"])}</span>' if job["duration"] else ""
    expr       = f'<span class="cron-expr">{h(job["expr"])}</span>' if job["expr"] else ""
    delivered  = job.get("delivery", "")
    deliv_html = ""
    if delivered == "delivered":
        deliv_html = '<span class="cron-deliv ok">✓ sent</span>'
    elif delivered and delivered != "not-delivered":
        deliv_html = f'<span class="cron-deliv muted">{h(delivered)}</span>'

    tz_str     = f' ({job["tz"]})' if job.get("tz") else ""
    md = modal_attr(job["name"], [
        ("Schedule",   f'{job["expr"]}{tz_str}'),
        ("Status",     f'{job["status"]} · {errors} consecutive errors' if errors else job["status"]),
        ("Last run",   f'{job["last"]} ({job["duration"]})' if job["duration"] else job["last"]),
        ("Next run",   job["next"]),
        ("Delivery",   delivered),
    ])

    return f'''<tr class="clickable" onclick="openModal(this)" data-modal={md}>
      <td><span class="cron-dot" style="background:{dot_color}" title="{h(dot_title)}"></span></td>
      <td>
        <div class="cron-name">{h(job["name"])}{dur}</div>
        <div class="cron-schedule">{expr} {deliv_html}</div>
      </td>
      <td class="muted cron-time">{h(job["last"])}</td>
      <td class="muted cron-time">{h(job["next"])}</td>
    </tr>'''


# ── Full page ─────────────────────────────────────────────────────────────────

def build_html(threads, npcs, talismans, player, queue, bleed, crons, arc=None, anchors=None, sched=None, forecast=None) -> str:
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Arc banner
    arc_html = render_arc_banner(arc) if arc else ""

    # Thread cards
    thread_cards = "".join(render_thread_card(t) for t in threads)

    # Talisman bars
    max_tal = max((t["belief"] for t in talismans), default=1)
    tal_bars = "".join(render_talisman_bar(t, max_tal) for t in talismans)

    # Top-N entities
    top_npcs = "".join(render_entity_row(e) for e in npcs[:25])

    # Queue entries
    queue_html = "".join(render_queue_entry(e) for e in queue) or '<div class="muted">Queue is clear.</div>'

    # Anchor places
    anchors = anchors or []
    anchors_html = "".join(render_anchor_card(a) for a in anchors) or '<div class="muted" style="padding:.5rem 0">No anchors yet. The Ley Line map is blank.</div>'

    # Inventory
    inventory_html = "".join(render_inventory_row(i) for i in player.get("inventory", [])) or '<div class="muted">Inventory is empty.</div>'

    # Schedule
    sched = sched or {}
    schedule_html = render_schedule_tab(sched) if sched else '<div class="muted">No schedule data.</div>'

    # Forecast
    forecast_html = render_forecast_tab(forecast) if forecast else '<div class="muted">No forecast data.</div>'

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
        color = {"OPEN": "var(--seed)", "OVERDUE": "var(--climax)", "DELIVERED": "var(--muted)"}.get(status, "var(--muted)")
        fae_html += f'<div class="fae-row"><span style="color:{color}">{h(status)}</span> <span class="muted">{h(b["fae"])}</span> · {h(b["deadline"])}</div>'
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
<title>Enchantify — Mission Control</title>
<style>
  :root {{
    --bg:         #111113;
    --surface:    #1c1c1f;
    --border:     #2a2a2f;
    --text:       #d4d4d8;
    --muted:      #52525b;
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
  body {{ background: var(--bg); color: var(--text); min-height: 100vh; font-size: 14px; }}
  a {{ color: inherit; text-decoration: none; }}

  /* ── Layout ── */
  .topbar {{
    display: flex; align-items: center; gap: 1.5rem;
    padding: .7rem 1.5rem;
    background: var(--surface); border-bottom: 1px solid var(--border);
    font-family: monospace; font-size: .8rem;
  }}
  .topbar-title {{
    font-family: Georgia, serif; font-size: 1rem; letter-spacing: .08em;
    color: #a1a1aa; text-transform: uppercase;
  }}
  .topbar-divider {{ color: var(--border); }}
  .topbar-item {{ display: flex; gap: .4rem; align-items: center; }}
  .topbar-label {{ color: var(--muted); }}
  .topbar-refresh {{ color: var(--muted); font-size: .7rem; }}
  .topbar-refresh-btn {{
    margin-left: auto; background: none; border: 1px solid var(--border);
    color: var(--muted); font-size: .75rem; cursor: pointer; border-radius: 3px;
    padding: .1rem .4rem; line-height: 1.4;
  }}
  .topbar-refresh-btn:hover {{ color: var(--text); border-color: var(--muted); }}
  .topbar-refresh-btn.spinning {{ animation: spin .6s linear infinite; }}
  @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
  .belief-inline {{
    display: inline-block; width: 60px; height: 6px;
    background: var(--border); border-radius: 3px; vertical-align: middle;
    position: relative; overflow: hidden;
  }}
  .belief-inline-fill {{
    position: absolute; left: 0; top: 0; height: 100%;
    background: #7c3aed; border-radius: 3px;
  }}

  .grid {{
    display: grid;
    grid-template-columns: 1fr 340px;
    grid-template-rows: auto auto;
    gap: 1rem; padding: 1rem;
    max-width: 1600px; margin: 0 auto;
  }}

  /* ── Panels ── */
  .panel {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 4px; overflow: hidden;
  }}
  .panel-header {{
    padding: .5rem 1rem;
    border-bottom: 1px solid var(--border);
    font-family: monospace; font-size: .7rem; letter-spacing: .1em;
    color: var(--muted); text-transform: uppercase; display: flex;
    align-items: center; gap: .8rem;
  }}
  .panel-header span {{ color: var(--text); }}
  .panel-body {{ padding: 1rem; }}

  /* ── Thread cards ── */
  .thread-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: .75rem; }}
  .card {{
    background: var(--bg); border: 1px solid; border-radius: 4px;
    padding: .75rem; display: flex; flex-direction: column; gap: .5rem;
  }}
  .card-header {{ display: flex; align-items: center; justify-content: space-between; }}
  .card-title {{ font-size: .85rem; font-weight: bold; }}
  .card-anchor {{ font-size: .7rem; color: var(--muted); }}
  .card-beat {{ font-size: .78rem; color: var(--text); line-height: 1.5; font-style: italic; }}
  .card-meta {{ font-size: .65rem; color: var(--muted); font-family: monospace; }}
  .badge-new {{
    display: inline-block; margin-left: .5rem;
    background: var(--seed); color: #86efac;
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
    padding-right: .3rem; text-shadow: 0 0 6px #000;
  }}
  .phase-bar.permanent {{
    background: var(--dormant); border-radius: 2px; height: 18px;
    display: flex; align-items: center; padding: 0 .5rem;
  }}
  .phase-bar.permanent span {{ font-size: .65rem; color: var(--muted); font-family: monospace; }}

  /* ── Talisman bars ── */
  .tal-row {{ display: flex; align-items: center; gap: .6rem; margin-bottom: .4rem; }}
  .tal-name {{ width: 100px; font-size: .75rem; font-weight: bold; flex-shrink: 0; }}
  .tal-bar-wrap {{ flex: 1; height: 8px; background: var(--bg); border-radius: 4px; overflow: hidden; }}
  .tal-bar {{ height: 100%; border-radius: 4px; transition: width .4s; }}
  .tal-belief {{ width: 30px; text-align: right; font-family: monospace; font-size: .75rem; flex-shrink: 0; }}
  .tal-chapter {{ width: 80px; font-size: .65rem; font-family: monospace; flex-shrink: 0; }}

  /* ── Entity table ── */
  .ent-table {{ width: 100%; border-collapse: collapse; font-size: .75rem; }}
  .ent-table td {{ padding: .25rem .4rem; border-bottom: 1px solid var(--border); }}
  .ent-table tr:last-child td {{ border-bottom: none; }}
  .ent-name {{ color: var(--text); }}
  .ent-type {{ font-family: monospace; font-size: .65rem; }}
  .ent-belief {{ font-family: monospace; text-align: right; color: var(--text); }}
  .ent-tags {{ font-family: monospace; font-size: .6rem; }}
  .tag {{
    display: inline-block; background: var(--thread-line); color: #93c5fd;
    border-radius: 2px; padding: .05rem .3rem; margin-right: .2rem; font-size: .6rem;
  }}

  /* ── Tick feed ── */
  .tick-feed {{ display: flex; flex-direction: column; gap: .3rem; max-height: 360px; overflow-y: auto; }}
  .entry {{
    padding: .35rem .6rem; border-radius: 3px; font-size: .72rem; line-height: 1.5;
    border-left: 3px solid transparent;
  }}
  .entry-escalation {{ background: #2d1b00; border-color: var(--rising); color: #fcd34d; }}
  .entry-cooling     {{ background: #1a1a2e; border-color: var(--setup); color: #93c5fd; }}
  .entry-seed        {{ background: #052e16; border-color: var(--seed); color: #86efac; }}
  .entry-fae         {{ background: #1e0533; border-color: var(--fae); color: #d8b4fe; }}
  .entry-priority    {{ background: #2d0000; border-color: var(--priority); color: #fca5a5; }}
  .entry-war         {{ background: #271500; border-color: var(--war); color: #fde68a; }}
  .entry-beat        {{ background: #1a1f2e; border-color: var(--beat); }}
  .entry-thread      {{ background: #1a2030; border-color: var(--thread-line); color: #93c5fd; }}
  .entry-talisman    {{ background: #1c1510; border-color: var(--war); color: #fcd34d; }}
  .entry-invest      {{ background: #0d1b35; border-color: var(--invest); color: #93c5fd; }}
  .entry-pulse       {{ background: #111; border-color: var(--border); color: var(--muted); }}
  .entry-normal      {{ background: #161618; border-color: var(--border); color: var(--text); }}

  /* ── Player panel ── */
  .belief-bar-wrap {{ margin: .5rem 0; }}
  .belief-bar-track {{
    height: 8px; background: var(--bg); border-radius: 4px; overflow: hidden;
  }}
  .belief-bar-fill {{
    height: 100%; background: #7c3aed; border-radius: 4px;
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
    border-radius: 3px; background: var(--bg);
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
  .cron-time {{ font-family: monospace; font-size: .65rem; white-space: nowrap; padding-top: .35rem; }}

  .muted {{ color: var(--muted); }}
  .clickable {{ cursor: pointer; }}
  .clickable:hover {{ opacity: .85; }}

  /* ── Modal ── */
  .modal-overlay {{
    display: none; position: fixed; inset: 0; z-index: 1000;
    background: rgba(0,0,0,.72); align-items: center; justify-content: center;
  }}
  .modal-overlay.open {{ display: flex; }}
  .modal-box {{
    background: #18181b; border: 1px solid #3f3f46; border-radius: 6px;
    width: min(640px, 94vw); max-height: 82vh;
    display: flex; flex-direction: column; overflow: hidden;
    box-shadow: 0 24px 48px rgba(0,0,0,.6);
  }}
  .modal-header {{
    display: flex; align-items: center; justify-content: space-between;
    padding: .75rem 1rem; border-bottom: 1px solid #3f3f46; flex-shrink: 0;
  }}
  .modal-title {{ font-size: .95rem; font-weight: bold; color: var(--text); }}
  .modal-close {{
    background: none; border: none; color: var(--muted); font-size: 1.2rem;
    cursor: pointer; line-height: 1; padding: .1rem .3rem; border-radius: 3px;
  }}
  .modal-close:hover {{ color: var(--text); background: #27272a; }}
  .modal-body {{ overflow-y: auto; padding: .75rem 1rem; display: flex; flex-direction: column; gap: .6rem; }}
  .mf-row {{ display: grid; grid-template-columns: 130px 1fr; gap: .4rem; align-items: baseline; }}
  .mf-label {{
    font-family: monospace; font-size: .65rem; text-transform: uppercase;
    letter-spacing: .07em; color: var(--muted); flex-shrink: 0; padding-top: .1rem;
  }}
  .mf-value {{ font-size: .78rem; line-height: 1.6; color: var(--text); word-break: break-word; }}

  /* ── Scrollbar ── */
  ::-webkit-scrollbar {{ width: 4px; }}
  ::-webkit-scrollbar-track {{ background: var(--bg); }}
  ::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 2px; }}

  /* ── Arc banner ── */
  .arc-banner {{
    background: var(--bg); border: 1px solid; border-radius: 4px;
    padding: .85rem 1rem; display: flex; flex-direction: column; gap: .75rem;
  }}
  .arc-header {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; }}
  .arc-eyebrow {{ font-family: monospace; font-size: .65rem; color: var(--muted); margin-bottom: .2rem; }}
  .arc-name {{ font-size: 1.05rem; font-weight: bold; letter-spacing: .02em; }}
  .arc-right {{ text-align: right; display: flex; flex-direction: column; gap: .3rem; align-items: flex-end; }}
  .arc-phase {{ font-family: monospace; font-size: .8rem; font-weight: bold; letter-spacing: .1em; }}
  .arc-belief-wrap {{ display: flex; align-items: center; gap: .4rem; flex-direction: row-reverse; }}
  .arc-belief-track {{ width: 80px; height: 5px; background: var(--border); border-radius: 3px; overflow: hidden; }}
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
    background: var(--bg); border: 1px solid var(--border); border-radius: 4px;
    padding: .65rem .85rem; margin-bottom: .6rem; display: flex; flex-direction: column; gap: .35rem;
  }}
  .fc-world-feel {{ font-size: .82rem; color: var(--text); line-height: 1.4; }}
  .fc-world-row  {{ display: flex; flex-wrap: wrap; gap: .4rem; }}
  .fc-pill {{
    font-family: monospace; font-size: .62rem; padding: .1rem .4rem;
    background: #27272a; border-radius: 2px;
  }}
  .fc-forecast {{ font-size: .68rem; line-height: 1.5; font-style: italic; }}
  .fc-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: .5rem; margin-bottom: .5rem; }}
  .fc-block {{
    background: var(--bg); border: 1px solid var(--border); border-radius: 4px;
    padding: .6rem .75rem; display: flex; flex-direction: column; gap: .4rem;
    margin-bottom: .5rem;
  }}
  .fc-grid .fc-block {{ margin-bottom: 0; }}
  .fc-block-header {{ display: flex; align-items: center; justify-content: space-between; gap: .5rem; }}
  .fc-block-title  {{ font-family: monospace; font-size: .65rem; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); }}
  .fc-badge {{
    font-family: monospace; font-size: .62rem; padding: .1rem .4rem; border-radius: 2px; flex-shrink: 0;
  }}
  .fc-badge-neutral {{ background: #27272a; color: var(--muted); }}
  .fc-nothing-strategy, .fc-philo {{ font-size: .72rem; line-height: 1.5; }}
  .fc-bullets {{ padding-left: 1rem; display: flex; flex-direction: column; gap: .2rem; }}
  .fc-bullets li {{ font-size: .68rem; line-height: 1.5; color: var(--muted); }}
  .fc-tal-bars   {{ display: flex; flex-direction: column; gap: .25rem; margin-top: .2rem; }}
  .fc-tal-row    {{ display: flex; align-items: center; gap: .4rem; }}
  .fc-tal-name   {{ font-size: .68rem; font-weight: bold; width: 90px; flex-shrink: 0; }}
  .fc-tal-bar-wrap {{ flex: 1; height: 6px; background: #27272a; border-radius: 3px; overflow: hidden; }}
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

  /* ── Schedule ── */
  .sched-now {{
    display: flex; justify-content: space-between; gap: 1rem;
    border: 1px solid; border-radius: 4px; padding: .7rem .85rem; margin-bottom: .1rem;
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
    background: #27272a; color: var(--muted); padding: .1rem .35rem; border-radius: 2px;
  }}
  .sched-slots {{ display: flex; flex-direction: column; gap: .3rem; }}
  .sched-slot {{
    display: flex; align-items: baseline; gap: .6rem;
    padding: .3rem .5rem; border: 1px solid var(--border); border-radius: 3px;
    background: var(--bg);
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
    cursor: pointer; background: var(--bg);
  }}
  .sched-day-col:hover {{ opacity: .85; }}
  .sched-day-col-name {{ font-family: monospace; font-size: .65rem; font-weight: bold; color: var(--muted); }}
  .sched-day-col-name-today {{ color: #7c3aed !important; }}
  .sched-day-col-num  {{ font-family: monospace; font-size: .55rem; }}
  .sched-day-col-slot {{ font-size: .6rem; min-height: 1rem; }}
  .sched-mini-class   {{ display: block; line-height: 1.35; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: .6rem; }}
  .sched-mini-empty   {{ font-size: .6rem; }}
  .sched-blocks {{ display: flex; flex-wrap: wrap; gap: .3rem; }}
  .sched-block {{
    display: flex; flex-direction: column; gap: .1rem;
    border: 1px solid var(--border); border-radius: 3px; padding: .3rem .5rem;
    min-width: 100px;
  }}
  .sched-block-active {{ font-weight: bold; }}
  .sched-block-name {{ font-size: .7rem; }}
  .sched-block-hrs  {{ font-family: monospace; font-size: .6rem; }}

  /* ── Inventory ── */
  .inv-row {{ padding: .4rem 0; border-bottom: 1px solid var(--border); }}
  .inv-row:last-child {{ border-bottom: none; }}
  .inv-name {{ font-size: .78rem; font-weight: bold; color: var(--text); margin-bottom: .15rem; }}
  .inv-desc {{ font-size: .72rem; color: var(--muted); line-height: 1.5; }}
  .inv-label {{ font-style: italic; color: #a78bfa; }}

  /* ── Anchor cards ── */
  .anchor-grid {{ display: flex; flex-direction: column; gap: .6rem; }}
  .anchor-card {{
    background: var(--bg); border: 1px solid; border-radius: 4px;
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
  .tab-bar {{ display: flex; border-bottom: 1px solid var(--border); padding: 0 1rem; gap: .25rem; }}
  .tab {{
    padding: .35rem .75rem; font-family: monospace; font-size: .65rem;
    text-transform: uppercase; letter-spacing: .08em;
    color: var(--muted); cursor: pointer; border-bottom: 2px solid transparent;
    background: none; border-top: none; border-left: none; border-right: none;
    transition: color .15s;
  }}
  .tab.active {{ color: var(--text); border-bottom-color: #7c3aed; }}
  .tab-content {{ display: none; padding: .75rem 1rem; }}
  .tab-content.active {{ display: block; }}
</style>
</head>
<body>

<div class="topbar" id="data-topbar">
  <div class="topbar-title">⋈ Enchantify</div>
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
        <button class="tab active" onclick="switchTab(this,'tick')">Tick Feed</button>
        <button class="tab" onclick="switchTab(this,'forecast')">Forecast</button>
        <button class="tab" onclick="switchTab(this,'entities')">Entities</button>
        <button class="tab" onclick="switchTab(this,'talismans')">Talisman War</button>
        <button class="tab" onclick="switchTab(this,'anchors')">Anchors <span style="color:var(--muted);font-size:.6rem">({len(anchors)})</span></button>
        <button class="tab" onclick="switchTab(this,'inventory')">Inventory</button>
        <button class="tab" onclick="switchTab(this,'schedule')">Schedule</button>
      </div>
      <div id="tick" class="tab-content active">
        <div class="tick-feed">{queue_html}</div>
      </div>
      <div id="entities" class="tab-content">
        <table class="ent-table">
          <tbody>{top_npcs}</tbody>
        </table>
      </div>
      <div id="talismans" class="tab-content">
        {tal_bars}
      </div>
      <div id="anchors" class="tab-content">
        <div class="anchor-grid">{anchors_html}</div>
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

    <!-- Automation -->
    <div class="panel">
      <div class="panel-header">Automation</div>
      <div class="panel-body" id="data-automation">
        <div class="bleed-status">
          <span class="bleed-dot" style="color:{bleed_status_color}">◉</span>
          <span>The Bleed — {bleed_label} {bleed_issue}</span>
        </div>
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

function closeModal() {{
  document.getElementById('modal-overlay').classList.remove('open');
}}

document.addEventListener('keydown', e => {{ if (e.key === 'Escape') closeModal(); }});

// ── Soft refresh ──────────────────────────────────────────────────────────────
const REFRESH_MS = 3 * 60 * 1000;  // 3 minutes
const DATA_REGIONS = [
  'data-topbar', 'data-thread-count', 'data-arc-threads',
  'tick', 'entities', 'talismans', 'anchors', 'inventory', 'schedule', 'forecast',
  'data-player', 'data-automation',
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
    bleed     = parse_bleed_status()
    crons     = parse_cron_jobs()
    arc       = parse_arc()
    anchors   = parse_anchors(player.get("name", "bj"))
    sched    = parse_schedule()
    forecast = parse_forecast(talismans)
    return build_html(threads, npcs, talismans, player, queue, bleed, crons,
                      arc=arc, anchors=anchors, sched=sched, forecast=forecast)


def main():
    parser = argparse.ArgumentParser(description="Enchantify Mission Control")
    parser.add_argument("--open",  action="store_true", help="Open in browser after generating")
    parser.add_argument("--serve", action="store_true", help="Serve on http://localhost:9191 with live refresh")
    parser.add_argument("--out",   default=str(BASE / "mission-control.html"), help="Output path")
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

#!/usr/bin/env python3
"""
bleed.py — The Bleed, daily edition.

The Academy student newspaper. Publishes at 6pm.
Synthesizes simulation data, player biometrics, thread pressures, and active play
into in-world journalism.

Forever issue numbering tracked in bleed/issue-number.txt.
Broadsheet HTML saved to bleed/issues/YYYY-MM-DD.html.
Telegram text edition sent at 6pm if TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID are set.
CUPS print sent if BLEED_PRINTER is set (uses wkhtmltopdf → PDF if available).

Usage:
  python3 scripts/bleed.py             # publish today's issue
  python3 scripts/bleed.py --force     # regenerate even if already published today

Cron: 0 18 * * * cd /path/to/enchantify && /usr/bin/python3 scripts/bleed.py >> logs/bleed.log 2>&1
"""

import base64
import mimetypes
import os
import re
import sys
import json
import time
import html
from html import unescape as html_unescape
import shutil
import subprocess
import urllib.request
import urllib.error
from datetime import datetime, date
from pathlib import Path
from typing import Optional
import sys as _sys

from scene_ledger import append_entry as append_scene_ledger_entry, load_entries as load_scene_ledger_entries

SCRIPT_DIR   = Path(__file__).parent
WORKSPACE_DIR = SCRIPT_DIR.parent

# Import schedule module
_sys.path.insert(0, str(SCRIPT_DIR))
import cron_steward
try:
    from schedule import get_schedule_data, WEEKDAY_NAMES
    _SCHEDULE_AVAILABLE = True
except ImportError:
    _SCHEDULE_AVAILABLE = False

ISSUE_NUMBER_FILE = WORKSPACE_DIR / "bleed" / "issue-number.txt"
ISSUES_DIR        = WORKSPACE_DIR / "bleed" / "issues"
ISSUE_IMAGES_DIR  = WORKSPACE_DIR / "bleed" / "images"
CLASSIFIEDS_LEDGER_DIR = WORKSPACE_DIR / "logs" / "classifieds-ledger"
BLEED_RIPPLES_LOG = WORKSPACE_DIR / "logs" / "bleed-ripples.jsonl"
BLEED_LOCK_STALE_SECONDS = 8 * 60 * 60


# ── Config ────────────────────────────────────────────────────────────────────

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


# ── Issue numbering ───────────────────────────────────────────────────────────

def get_issue_number() -> int:
    ISSUE_NUMBER_FILE.parent.mkdir(parents=True, exist_ok=True)
    if ISSUE_NUMBER_FILE.exists():
        try:
            return int(ISSUE_NUMBER_FILE.read_text().strip()) + 1
        except ValueError:
            pass
    return 1


def save_issue_number(n: int):
    ISSUE_NUMBER_FILE.write_text(str(n))


def _acquire_issue_lock(lock_path: Path, stale_seconds: int = BLEED_LOCK_STALE_SECONDS) -> tuple[Optional[int], str]:
    """Claim one Bleed issue run for a date.

    Cron can occasionally start overlapping processes. This lock is intentionally
    per issue date, so generation, Telegram delivery, and CUPS printing all happen
    under one atomic claim.
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    payload = f"pid={os.getpid()}\nstarted_at={datetime.now().isoformat()}\n"
    try:
        fd = os.open(str(lock_path), flags)
        os.write(fd, payload.encode("utf-8"))
        return fd, "acquired"
    except FileExistsError:
        try:
            age = time.time() - lock_path.stat().st_mtime
        except FileNotFoundError:
            return _acquire_issue_lock(lock_path, stale_seconds)
        if age > stale_seconds:
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass
            except OSError as exc:
                return None, f"stale lock could not be removed: {exc}"
            return _acquire_issue_lock(lock_path, stale_seconds)
        minutes = max(0, int(age // 60))
        return None, f"active lock is {minutes}m old"


def _release_issue_lock(lock_fd: Optional[int], lock_path: Path) -> None:
    if lock_fd is None:
        return
    try:
        os.close(lock_fd)
    except OSError:
        pass
    try:
        lock_path.unlink()
    except FileNotFoundError:
        pass
    except OSError as exc:
        print(f"  ⚠ Could not remove Bleed lock {lock_path}: {exc}")


def _issue_number_from_html(saved_html: str, fallback: int) -> int:
    """Recover the published issue number from a saved broadsheet."""
    for pattern in (
        r"Issue\s*#\s*(\d+)",
        r"Bleed Frontier Desk #(\d+)",
    ):
        m = re.search(pattern, saved_html, re.IGNORECASE)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass
    return fallback


# ── Data readers ──────────────────────────────────────────────────────────────

def read_file_safe(path: Path, limit_lines: int = 0) -> str:
    if not path.exists():
        return ""
    text = path.read_text().strip()
    if limit_lines:
        return "\n".join(text.splitlines()[:limit_lines])
    return text


def extract_pulse_section(heartbeat: str) -> str:
    m = re.search(r'<!-- PULSE_START -->(.*?)<!-- PULSE_END -->', heartbeat, re.DOTALL)
    return m.group(1).strip() if m else ""


def get_sparky_shiny(date_str: str) -> str:
    shinies_dir = WORKSPACE_DIR / "sparky" / "shinies"
    if not shinies_dir.exists():
        return ""
        
    # Sort descending so matches[0] is always the MOST RECENT run for today
    matches = sorted(shinies_dir.glob(f"{date_str}*.md"), reverse=True)
    if not matches:
        return ""
        
    text = matches[0].read_text()
    # Strip H1 header line
    clean_text = re.sub(r'^# .+\n', '', text).strip()
    
    # If the LLM hallucinated a literal bullet or output the literal fallback instruction, clear it
    if clean_text in ("*", ".", "•", "-", "(a sleeping dot)", '"(a sleeping dot)"', "'(a sleeping dot)'"):
        return ""
        
    return clean_text


def get_player_data(cfg: dict) -> dict:
    player = cfg.get("ENCHANTIFY_DEFAULT_PLAYER", "bj")
    content = read_file_safe(WORKSPACE_DIR / "players" / f"{player}.md", 15)
    data = {"name": player}

    m = re.search(r'\*\*Belief:\*\*\s*(\d+)', content)
    data["belief"] = m.group(1) if m else "?"

    m = re.search(r'\*\*Chapter:\*\*\s*(\S+)', content)
    data["chapter"] = m.group(1) if m else "?"

    m = re.search(r'\*\*Tutorial Progress:\*\*\s*(\S+)', content)
    data["tutorial"] = m.group(1) if m else "?"

    return data


def get_fae_ledger_brief(player_name: str = "bj") -> str:
    """Summarize open fae bargains from the player's Margin."""
    text = read_file_safe(WORKSPACE_DIR / "players" / f"{player_name}.md")
    m = re.search(r'## The Margin\n(.*?)(?=\n## |\n---\n|\Z)', text, re.DOTALL)
    if not m:
        return "The Margin is missing; no fae ledger could be read."
    rows = []
    for line in m.group(1).splitlines():
        if not line.startswith("|") or "*(The margin is clean" in line or set(line.replace("|", "").strip()) <= {"-"}:
            continue
        parts = [p.strip() for p in line.split("|")[1:-1]]
        if len(parts) < 5 or parts[0] == "Fae":
            continue
        fae, gave, terms, deadline, status = parts[:5]
        status = status.upper()
        if status in {"OPEN", "OVERDUE", "BROKEN", "EXPIRED"}:
            rows.append(f"- {status}: {fae} gave {gave}; owed {terms}; due {deadline}")
    return "\n".join(rows[:5]) if rows else "The Margin is clean; no open fae bargains."


def get_thread_summary() -> str:
    threads_content  = read_file_safe(WORKSPACE_DIR / "lore" / "threads.md")
    register_content = read_file_safe(WORKSPACE_DIR / "lore" / "world-register.md")

    # Build belief lookup from world-register Active Threads section
    thread_belief: dict[str, int] = {}
    active_section_m = re.search(r'## Active Threads(.*?)(?=^## |\Z)', register_content, re.DOTALL | re.MULTILINE)
    if active_section_m:
        row_re = re.compile(r'^\|\s*([^|]+?)\s*\|\s*Thread\s*\|\s*(\d+)\s*\|', re.MULTILINE | re.IGNORECASE)
        for m in row_re.finditer(active_section_m.group(1)):
            thread_belief[m.group(1).strip().lower()] = int(m.group(2))

    lines = []
    for section in re.split(r'^## Thread: ', threads_content, flags=re.MULTILINE)[1:]:
        slines = section.strip().splitlines()
        name = slines[0].strip() if slines else "?"
        phase_m    = re.search(r'\*\*phase:\*\*\s*(.+)', section)
        pressure_m = re.search(r'\*\*pressure:\*\*\s*(.+)', section)
        beat_m     = re.search(r'\*\*Next beat:\*\*\s*(.+)', section)
        born_m     = re.search(r'\*\*born:\*\*\s*(\S+)', section)
        phase    = phase_m.group(1).strip() if phase_m else "?"
        pressure = pressure_m.group(1).strip() if pressure_m else "?"
        beat     = beat_m.group(1).strip()[:120] if beat_m else ""
        belief   = thread_belief.get(name.lower(), 0)

        # Coverage priority hint for the LLM
        if belief >= 30:
            priority = "CLIMAX — front page or feature"
        elif belief >= 15:
            priority = "rising — section feature"
        elif born_m and born_m.group(1) != "—":
            try:
                from datetime import date as _date
                born = _date.fromisoformat(born_m.group(1))
                if (_date.today() - born).days <= 7:
                    priority = "new this week — emerging narrative"
                else:
                    priority = "setup"
            except ValueError:
                priority = "setup"
        else:
            priority = "background"

        lines.append(f"- {name} [Belief {belief}, {phase}, {priority}]: {beat}")
    return "\n".join(lines)


def get_weather_forecast_from_heartbeat() -> str:
    """Pull the Forecast line from the pulse section of HEARTBEAT.md."""
    heartbeat = read_file_safe(WORKSPACE_DIR / "HEARTBEAT.md", 120)
    pulse = extract_pulse_section(heartbeat)
    lines = []
    capture = False
    for line in pulse.splitlines():
        if "**Forecast:**" in line:
            # First line: strip the label
            first = line.split("**Forecast:**", 1)[-1].strip()
            if first:
                lines.append(first)
            capture = True
        elif capture:
            # Forecast is multi-line until next bullet or blank section header
            if line.startswith("- **") or line.startswith("###"):
                break
            if line.strip():
                lines.append(line.strip().lstrip("- "))
    return "\n".join(lines) if lines else ""


def calculate_market_odds() -> list:
    """Derive predictions market odds from thread + entity data. Pure math, no LLM."""
    threads_text = read_file_safe(WORKSPACE_DIR / "lore" / "threads.md")
    register_text = read_file_safe(WORKSPACE_DIR / "lore" / "world-register.md")

    # Sum belief per thread from world register [thread:id] tags
    thread_belief = {}
    row_re = re.compile(r"^\|\s*[^|]+\s*\|\s*[^|]+\s*\|\s*(\d+)\s*\|\s*([^|]*)\s*\|", re.MULTILINE)
    for m in row_re.finditer(register_text):
        belief, notes = int(m.group(1)), m.group(2)
        tid_m = re.search(r'\[thread:([^\]]+)\]', notes)
        if tid_m:
            for tid in tid_m.group(1).split(','):
                tid = tid.strip()
                thread_belief[tid] = thread_belief.get(tid, 0) + belief

    # Parse thread phases and nothing pressure
    odds_list = []
    for section in re.split(r'^## Thread: ', threads_text, flags=re.MULTILINE)[1:]:
        slines = section.strip().splitlines()
        name = slines[0].strip() if slines else "?"
        if name.startswith("Ley Line") or name.startswith("Adding"):
            continue

        id_m      = re.search(r'\*\*id:\*\*\s*`([^`]+)`', section)
        phase_m   = re.search(r'\*\*phase:\*\*\s*(.+)', section)
        nothing_m = re.search(r'\*\*Nothing pressure:\*\*\s*(.+)', section)
        beat_m    = re.search(r'\*\*Next beat:\*\*\s*(.+)', section)

        tid     = id_m.group(1).strip() if id_m else ""
        phase   = phase_m.group(1).strip().lower() if phase_m else ""
        nothing = nothing_m.group(1).strip().lower() if nothing_m else ""
        beat    = beat_m.group(1).strip()[:100] if beat_m else ""

        belief = thread_belief.get(tid, 0)
        if belief == 0 and tid == "main-arc":
            belief = 80  # main arc always has pressure

        # Base probability from combined belief (log-ish curve: 10 belief = 10%, 100 = 90%)
        base = min(90, max(10, int(belief * 0.8)))

        # Phase modifier
        phase_mod = {
            "escalating": +15, "setup": +5, "quiet": -5,
            "dormant": -20, "permanent": +0,
        }.get(phase.split()[0] if phase else "", 0)

        # Nothing pressure modifier
        nothing_mod = -10 if "high" in nothing else (-5 if "medium" in nothing else +3)

        pct = max(5, min(95, base + phase_mod + nothing_mod))

        if name not in ("Academy Daily Life",):  # skip slice-of-life, always active
            odds_list.append({
                "name": name,
                "tid": tid,
                "phase": phase,
                "belief": belief,
                "yes": pct,
                "no": 100 - pct,
                "beat": beat,
            })

    odds_list.sort(key=lambda x: -x["belief"])
    return odds_list


def get_entity_standings() -> str:
    content = read_file_safe(WORKSPACE_DIR / "lore" / "world-register.md")
    entities = []
    row_re = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|", re.MULTILINE)
    for m in row_re.finditer(content):
        name, etype, belief = m.groups()
        name = name.strip()
        if name.lower() in ('entity', 'talisman', 'name', '---', ''):
            continue
        entities.append((name, etype.strip(), int(belief)))
    entities.sort(key=lambda x: -x[2])
    return "\n".join(f"- {n} ({t}): Belief {b}" for n, t, b in entities[:10])


def build_goblin_market_exchange(player_name: str = "bj") -> str:
    """Build a deterministic Goblin Market board for The Bleed.

    Goblins trade in attention, not Belief. This board turns current state into
    concrete offers and sensory prices so the market can become playable later.
    """
    heartbeat = read_file_safe(WORKSPACE_DIR / "HEARTBEAT.md", 140)
    pulse = extract_pulse_section(heartbeat)
    anchors_text = read_file_safe(WORKSPACE_DIR / "players" / f"{player_name}-anchors.md")
    register_text = read_file_safe(WORKSPACE_DIR / "lore" / "world-register.md")
    queue_text = read_file_safe(WORKSPACE_DIR / "memory" / "tick-queue.md", 80)
    fuel_data = get_fuel_data()

    def grab(pattern: str, text: str, default: str = "", flags: int = 0) -> str:
        m = re.search(pattern, text, flags)
        return m.group(1).strip() if m else default

    def short(text: str, n: int = 82) -> str:
        text = re.sub(r"\s+", " ", (text or "").strip())
        return text[:n] + "…" if len(text) > n else text

    def anchor_type(text: str) -> str:
        value = re.sub(r"[^A-Za-z]", "", text or "").upper()
        value = {"FIND": "NOTICE", "DISCOVER": "NOTICE", "SEARCH": "NOTICE", "LOOK": "NOTICE"}.get(value, value)
        return value if value in {"NOTICE", "EMBARK", "SENSE", "WRITE", "REST"} else "NOTICE"

    season = grab(r'- \*\*Season:\*\*\s*(.+)', pulse)
    moon = grab(r'- \*\*Moon:\*\*\s*(.+)', pulse)
    weather = grab(r'- \*\*Belfast Feel:\*\*\s*(.+)', pulse)
    goblin_belief = grab(r'^\|\s*The Goblin Index Empire\s*\|\s*fae\s*\|\s*(\d+)\s*\|', register_text, "?", re.MULTILINE)

    anchors = []
    for section in re.split(r'^## ', anchors_text, flags=re.MULTILINE)[1:]:
        lines = section.strip().splitlines()
        name = lines[0].strip() if lines else "Unnamed Anchor"
        atype = anchor_type(grab(r'\*\*Type:\*\*\s*(.+)', section, "?"))
        visits = grab(r'\*\*Visit count:\*\*\s*(\d+)', section, "0")
        room = grab(r'\*\*Outer Stacks room:\*\*\s*(.+)', section, "", re.DOTALL)
        rule = grab(r'\*\*Local rule:\*\*\s*(.+)', section, "", re.DOTALL)
        anchors.append({"name": name, "type": atype, "visits": visits, "room": short(room), "rule": short(rule, 72)})

    thread_rows = []
    active_m = re.search(r'## Active Threads(.*?)(?=^## |\Z)', register_text, re.DOTALL | re.MULTILINE)
    if active_m:
        row_re = re.compile(r'^\|\s*([^|]+?)\s*\|\s*Thread\s*\|\s*(\d+)\s*\|\s*([^|]+)\|', re.MULTILINE | re.IGNORECASE)
        for m in row_re.finditer(active_m.group(1)):
            name, belief, notes = m.group(1).strip(), int(m.group(2)), m.group(3).strip()
            if name.lower() == "academy daily life":
                continue
            thread_rows.append({"name": name, "belief": belief, "notes": short(notes, 90)})
    thread_rows.sort(key=lambda t: -t["belief"])

    recent_market = []
    for line in queue_text.splitlines():
        if any(k in line.lower() for k in ("goblin", "market", "outer stacks", "anchor", "calling card")):
            recent_market.append(short(line, 100))
    recent_market = recent_market[:2]

    offers = []
    if anchors:
        a = sorted(anchors, key=lambda x: int(x.get("visits") or 0), reverse=True)[0]
        offers.append({
            "giving": f"one annotated shelfmark toward {a['name']}",
            "asking": "one detail noticed within twenty-four hours that was present before you noticed it",
            "rate": f"anchor trade · {a['type']} · visits {a['visits']} · {a['room'] or 'room terms not public'}",
        })
    else:
        offers.append({
            "giving": "a starter shelfmark for the first reliable Outer Stacks door",
            "asking": "the oldest useful thing you can touch today, described precisely",
            "rate": "new-customer rate · no tab yet",
        })

    if thread_rows:
        t = thread_rows[0]
        offers.append({
            "giving": f"a footnote to the next pressure point in {t['name']}",
            "asking": "the gap between what something is called and what it actually is",
            "rate": f"thread pressure · Belief {t['belief']} · {t['notes']}",
        })

    fuel_low = any(k in fuel_data.lower() for k in ("low protein", "no provisions", "no recent", "coffee", "low calories"))
    if fuel_low:
        offers.append({
            "giving": "a Refectory marginal note that makes one meal easier to choose",
            "asking": "one honest sensory sentence about the first real nourishment taken afterward",
            "rate": "Vellum-adjacent counter · care is not discounted, only itemized",
        })

    offers.append({
        "giving": "one calling-card rumor from the Index Empire's delivery ledger",
        "asking": "a thing no one labeled, signed, or explained",
        "rate": f"Index Empire standing · Belief {goblin_belief} · {season or 'season unreadable'}",
    })

    if "rain" in (weather + " " + season).lower():
        offers.append({
            "giving": "a waterproof errand folded into a receipt",
            "asking": "the smell of wet pavement, named without using the word rain",
            "rate": "rain market · pages curl, prices soften at the edges",
        })
    elif "quiet" in pulse.lower():
        offers.append({
            "giving": "a quiet-market discount on one small unanswered question",
            "asking": "the first sound that interrupts silence",
            "rate": "quiet house rate · low competition at the counter",
        })

    header_bits = [f"Index Empire standing: Belief {goblin_belief}"]
    if season:
        header_bits.append(season.split("—")[0].strip())
    if moon:
        header_bits.append(moon.split("(")[0].strip())
    if recent_market:
        header_bits.append("recent frontier stir recorded")

    lines = ["Market condition: " + " · ".join(header_bits)]
    for offer in offers[:5]:
        lines.append(f"- Giving: {offer['giving']} | Seeking: {offer['asking']} | Rate note: {offer['rate']}")
    lines.append("Settlement rule: payment is a genuine sensory observation. Performed noticing is refused; unpaid attention closes the useful doors.")
    return "\n".join(lines)


def normalize_exchange_text(text: str) -> str:
    """Keep Belief Exchange ticker entries on separate lines even if the LLM collapses them."""
    text = (text or "").strip()
    if not text:
        return ""
    text = re.sub(r'\s+[•]\s+', '\n• ', text)
    text = re.sub(r'\s+-\s+(?=[A-Z][^:\n]{1,90}\s+\([^)]+\):\s*Belief\s+\d+)', '\n- ', text)
    text = re.sub(r'\s+(?=-\s*[A-Z][^:\n]{1,90}\s+\([^)]+\):\s*Belief\s+\d+)', '\n', text)
    text = re.sub(r'(Belief\s+\d+)\s+(?=-\s*)', r'\1\n', text)
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def get_leading_talisman() -> dict:
    """Find which chapter talisman currently leads in belief."""
    content = read_file_safe(WORKSPACE_DIR / "lore" / "world-register.md")
    parts = content.split("## Chapter Talismans")
    if len(parts) < 2:
        return {}
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
        philosophy = m.group(4).strip()
        talismans.append({
            "name": name,
            "chapter": chapter,
            "belief": belief,
            "philosophy": philosophy,
        })

    if not talismans:
        return {}
    return max(talismans, key=lambda x: x["belief"])


def get_chapter_npcs(chapter_name: str) -> str:
    """Return a brief list of known NPCs affiliated with the given chapter from world-register."""
    content = read_file_safe(WORKSPACE_DIR / "lore" / "world-register.md")
    row_re = re.compile(
        r'^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|\s*([^|]*)\s*\|',
        re.MULTILINE
    )
    chapter_lower = chapter_name.lower()
    results = []
    for m in row_re.finditer(content):
        name = m.group(1).strip()
        etype = m.group(2).strip().upper()
        notes = m.group(4).strip()
        if name.lower() in ("entity", "talisman", "name", "---", ""):
            continue
        if etype not in ("NPC", "CHARACTER"):
            continue
        if chapter_lower not in notes.lower():
            continue
        try:
            belief = int(m.group(3))
        except ValueError:
            belief = 0
        # Pull a short descriptor from notes (skip thread tags)
        clean_notes = re.sub(r'\[thread:[^\]]+\]', '', notes).strip().strip(';').strip()
        desc = clean_notes[:80] if clean_notes else ""
        results.append(f"- {name} (Belief {belief}): {desc}")

    results.sort(key=lambda x: -int(re.search(r'Belief (\d+)', x).group(1)) if re.search(r'Belief (\d+)', x) else 0)
    return "\n".join(results[:8]) if results else "(no chapter NPCs found)"


# Control tier name from score
_TIER_THRESHOLDS = [
    (70, "Sovereign"),
    (45, "Dominated"),
    (25, "Controlled"),
    (10, "Influenced"),
    (1,  "Contesting"),
]

def _tier_name(score: int) -> str:
    for threshold, name in _TIER_THRESHOLDS:
        if score >= threshold:
            return name
    return "Contesting"

def _climax_distance(score: int):
    """Return (threshold, tier_name, distance) if score is within 5 of a tier upgrade, else None."""
    upgrade_points = [10, 25, 45, 70]
    tier_names = {10: "Influenced", 25: "Controlled", 45: "Dominated", 70: "Sovereign"}
    for t in upgrade_points:
        if 0 < t - score <= 5:
            return (t, tier_names[t], t - score)
    return None


def parse_app_register_for_bleed() -> dict:
    """Parse app-register.md into war analytics: territory counts, contested apps, climax situations."""
    content = read_file_safe(WORKSPACE_DIR / "lore" / "app-register.md")

    _TALISMANS = ["Emberheart", "Mossbloom", "Riddlewind", "Tidecrest", "Duskthorn"]
    apps = []

    # Table format: | App | System | Natural Alignment | Emberheart | Mossbloom | Riddlewind | Tidecrest | Duskthorn | Controller |
    row_re = re.compile(
        r'^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|'
        r'\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|'
        r'\s*([^|]+?)\s*\|',
        re.MULTILINE
    )
    for m in row_re.finditer(content):
        app_name = m.group(1).strip()
        if app_name.lower() in ('app', '---', ''):
            continue
        scores = {
            "Emberheart": int(m.group(4)),
            "Mossbloom":  int(m.group(5)),
            "Riddlewind": int(m.group(6)),
            "Tidecrest":  int(m.group(7)),
            "Duskthorn":  int(m.group(8)),
        }
        controller_raw = m.group(9).strip()

        sorted_scores = sorted(scores.items(), key=lambda x: -x[1])
        leader_name, leader_score = sorted_scores[0]
        second_name, second_score = sorted_scores[1] if len(sorted_scores) > 1 else ("?", 0)
        gap = leader_score - second_score

        # Find any talisman within 5 of a tier threshold
        climax_candidates = []
        for tname, tscore in scores.items():
            info = _climax_distance(tscore)
            if info:
                threshold, tier_name, dist = info
                climax_candidates.append((tname, tscore, tier_name, dist))

        apps.append({
            "name": app_name,
            "system": m.group(2).strip(),
            "scores": scores,
            "sorted_scores": sorted_scores,
            "leader": leader_name,
            "leader_score": leader_score,
            "leader_tier": _tier_name(leader_score),
            "second": second_name,
            "second_score": second_score,
            "gap": gap,
            "controller_raw": controller_raw,
            "climax": climax_candidates,
        })

    contested = sorted(apps, key=lambda x: x["gap"])

    wins = {}
    for a in apps:
        wins[a["leader"]] = wins.get(a["leader"], 0) + 1

    all_climax = []
    for a in apps:
        for (tname, tscore, tier_name, dist) in a["climax"]:
            all_climax.append({
                "app": a["name"],
                "talisman": tname,
                "score": tscore,
                "approaching_tier": tier_name,
                "points_away": dist,
            })

    return {
        "apps": apps,
        "contested": contested,
        "wins": wins,
        "all_climax": all_climax,
    }


def format_war_data(war: dict) -> str:
    """Format war analytics as a data block for the LLM prompt."""
    lines = []

    lines.append("CHAPTER CONTROL COUNT (apps controlled):")
    for ch, count in sorted(war["wins"].items(), key=lambda x: -x[1]):
        lines.append(f"  {ch}: {count} app(s)")

    lines.append("")
    lines.append("ALL APP SCORES (Emberheart | Mossbloom | Riddlewind | Tidecrest | Duskthorn):")
    for a in war["apps"]:
        s = a["scores"]
        lines.append(
            f"  {a['name']}: E={s['Emberheart']} M={s['Mossbloom']} R={s['Riddlewind']} "
            f"T={s['Tidecrest']} D={s['Duskthorn']}"
            f" → {a['leader']} leads ({a['leader_score']}, {a['leader_tier']}) "
            f"| gap over 2nd: {a['gap']}"
        )

    lines.append("")
    lines.append("MOST CONTESTED APPS (smallest gap — most likely to flip):")
    for a in war["contested"][:4]:
        lines.append(
            f"  {a['name']}: {a['leader']} ({a['leader_score']}) "
            f"vs {a['second']} ({a['second_score']}) — gap {a['gap']}"
        )

    # Climax: prioritise Controlled+ thresholds; for Influenced only show if the talisman leads that app
    all_climax = war["all_climax"]
    leader_map = {a["name"]: a["leader"] for a in war["apps"]}
    strategic_climax = [
        c for c in all_climax
        if c["approaching_tier"] in ("Controlled", "Dominated", "Sovereign")
        or (c["approaching_tier"] == "Influenced" and c["points_away"] <= 2
            and leader_map.get(c["app"]) == c["talisman"])
    ]
    strategic_climax.sort(key=lambda x: (
        {"Sovereign": 0, "Dominated": 1, "Controlled": 2, "Influenced": 3}.get(x["approaching_tier"], 4),
        x["points_away"]
    ))

    lines.append("")
    if strategic_climax:
        lines.append("TALISMAN CLIMAX WAR — strategically significant tier approaches:")
        for c in strategic_climax:
            lines.append(
                f"  {c['talisman']} in {c['app']}: score {c['score']} "
                f"→ {c['points_away']} point(s) from {c['approaching_tier']}"
            )
    else:
        lines.append("TALISMAN CLIMAX WAR: No chapter is currently near a strategic tier threshold.")

    return "\n".join(lines)


def get_current_fuel_summary() -> str:
    """Return today's fuel state from the canonical food_log module when possible."""
    try:
        if str(WORKSPACE_DIR / "scripts") not in sys.path:
            sys.path.insert(0, str(WORKSPACE_DIR / "scripts"))
        from food_log import summarize  # type: ignore
        return summarize(days=1)
    except Exception:
        heartbeat = read_file_safe(WORKSPACE_DIR / "HEARTBEAT.md", 80)
        m = re.search(r"- \*\*Fuel:\*\*\s*(.+)", heartbeat)
        return f"Today: {m.group(1).strip()}" if m else "Today: fuel summary unavailable."


def get_fuel_data(days: int = 3) -> str:
    """Read the fuel log with today first and older entries as secondary context."""
    log_path = WORKSPACE_DIR / "scripts" / "fuel-log.txt"
    today_summary = get_current_fuel_summary()
    if not log_path.exists():
        return "\n".join([
            "CURRENT FUEL STATE (authoritative for this issue):",
            today_summary,
            "",
            "RECENT FUEL CONTEXT:",
            "(no fuel log found)",
        ])

    from datetime import timedelta
    cutoff = date.today() - timedelta(days=max(days - 1, 0))

    entries = []
    for line in log_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("|")
        if len(parts) < 5:
            continue
        if parts[2].strip().lower() in ("description", "unknown", "n/a", "none") and all((p.strip() in ("", "0")) for p in parts[3:10]):
            continue
        try:
            entry_date = date.fromisoformat(parts[0])
        except ValueError:
            continue
        if entry_date < cutoff:
            continue
        entries.append({
            "date":        parts[0],
            "time":        parts[1],
            "description": parts[2],
            "calories":    int(parts[3]) if parts[3].isdigit() else 0,
            "protein":     int(parts[4]) if parts[4].isdigit() else 0,
            "carbs":       int(parts[5]) if len(parts) > 5 and parts[5].isdigit() else 0,
            "fat":         int(parts[6]) if len(parts) > 6 and parts[6].isdigit() else 0,
            "fiber":       int(parts[7]) if len(parts) > 7 and parts[7].isdigit() else 0,
            "sodium":      int(parts[9]) if len(parts) > 9 and parts[9].isdigit() else 0,
            "source":      parts[10] if len(parts) > 10 else "legacy",
        })

    if not entries:
        return "\n".join([
            "CURRENT FUEL STATE (authoritative for this issue):",
            today_summary,
            "",
            "RECENT FUEL CONTEXT:",
            f"(no fuel data in the past {days} days)",
        ])

    # Daily totals
    daily: dict = {}
    for e in entries:
        d = e["date"]
        if d not in daily:
            daily[d] = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0, "fiber": 0, "sodium": 0, "items": [], "sources": set()}
        daily[d]["calories"] += e["calories"]
        daily[d]["protein"]  += e["protein"]
        daily[d]["carbs"]    += e["carbs"]
        daily[d]["fat"]      += e["fat"]
        daily[d]["fiber"]    += e["fiber"]
        daily[d]["sodium"]   += e["sodium"]
        daily[d]["items"].append(e["description"])
        daily[d]["sources"].add(e["source"])

    today_iso = date.today().isoformat()
    lines = [
        "CURRENT FUEL STATE (authoritative for this issue):",
        today_summary,
        "",
        f"RECENT FUEL CONTEXT (last {days} days; background only, do not lead with older meals):",
    ]
    for d in sorted(daily.keys(), reverse=True):
        items_str = " / ".join(daily[d]["items"])
        source_str = ", ".join(sorted(daily[d]["sources"] - {""}))
        nutrient_bits = []
        if daily[d]["carbs"]:
            nutrient_bits.append(f"{daily[d]['carbs']}g carbs")
        if daily[d]["fat"]:
            nutrient_bits.append(f"{daily[d]['fat']}g fat")
        if daily[d]["fiber"]:
            nutrient_bits.append(f"{daily[d]['fiber']}g fiber")
        if daily[d]["sodium"]:
            nutrient_bits.append(f"{daily[d]['sodium']}mg sodium")
        nutrient_tail = f", {', '.join(nutrient_bits)}" if nutrient_bits else ""
        source_tail = f" [{source_str}]" if source_str else ""
        lines.append(
            f"  {d}: {daily[d]['calories']} cal, {daily[d]['protein']}g protein{nutrient_tail}"
            f"  — {items_str}{source_tail}"
        )

    # Simple pattern notes
    all_descriptions = " | ".join(e["description"].lower() for e in entries)
    patterns = []
    if all_descriptions.count("coffee") >= 3:
        coffee_count = sum(e["description"].lower().count("coffee") for e in entries)
        patterns.append(f"coffee appears {coffee_count} times across entries")
    if all_descriptions.count("bacon egg") >= 2 or all_descriptions.count("english muffin") >= 2:
        patterns.append("bacon egg and cheese english muffin is a recurring morning anchor")
    if any(b in all_descriptions for b in ("bud light", "modelo", "beer", "lager")):
        patterns.append("beer present on multiple days, typically evening")
    if all_descriptions.count("pizza") >= 1:
        patterns.append("pizza logged recently")

    avg_cal = sum(d["calories"] for d in daily.values()) // max(len(daily), 1)
    avg_pro = sum(d["protein"] for d in daily.values()) // max(len(daily), 1)
    if today_iso in daily:
        today = daily[today_iso]
        lines.append(
            f"TODAY TOTALS: {today['calories']} cal, {today['protein']}g protein, "
            f"{today['carbs']}g carbs, {today['fat']}g fat, {today['fiber']}g fiber, {today['sodium']}mg sodium"
        )
    lines.append(f"BACKGROUND AVERAGES (logged days only, not today's headline): {avg_cal} cal/day, {avg_pro}g protein/day")
    if patterns:
        lines.append("PATTERNS: " + "; ".join(patterns))

    return "\n".join(lines)


def get_vellum_chart(player: str = "bj") -> str:
    """Read the player's Vellum chart when present.

    This is optional personal context: labs, BP, medications, supplements,
    constraints, goals, and current experiments. Absence must never cause the
    column to invent health facts.
    """
    safe_player = re.sub(r"[^a-zA-Z0-9_-]", "", player or "bj") or "bj"
    path = WORKSPACE_DIR / "players" / f"{safe_player}-vellum-chart.md"
    text = read_file_safe(path, 180)
    return compact_text(text, 3500) if text else ""


def _read_recent_jsonl(path: Path, limit: int = 20) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()[-max(limit * 3, limit):]:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows[-limit:]


def _money(amount) -> str:
    try:
        return f"${float(amount):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def build_gimble_ledger_brief(player: str = "bj") -> str:
    """Package Actual Budget/Gimble context for a concise Bleed column."""
    safe_player = re.sub(r"[^a-zA-Z0-9_-]", "", player or "bj") or "bj"
    chart = read_file_safe(WORKSPACE_DIR / "players" / f"{safe_player}-ledger-chart.md", 120)
    rows = _read_recent_jsonl(WORKSPACE_DIR / "players" / f"{safe_player}-ledger-log.jsonl", 40)
    latest = rows[-1] if rows else {}
    weather = next((r for r in reversed(rows) if r.get("kind") in ("money_weather", "daily_sync", "weekly_audit")), latest)
    summary = weather.get("summary") if isinstance(weather.get("summary"), dict) else {}

    lines = [
        "GIMBLE LEDGER BRIEF:",
        "Role: Gimble of the Errata Registry, goblin finance support, shame-free accountant of kinetic ink.",
        "Voice: exact, goblin-practical, unsentimental but safe; accuracy first, no moralizing.",
        "Rules: no shame, no risky investment/tax certainty, no moving money; turn fog into one number, one risk, one action.",
        "",
        "LATEST GIMBLE NOTE:",
        compact_text(str(weather.get("message") or "(no Gimble note logged yet)"), 1200),
    ]
    if summary:
        accounts = summary.get("accounts") or []
        if accounts:
            lines.append("")
            lines.append("ACCOUNTS:")
            for account in accounts[:6]:
                lines.append(f"- {account.get('name', 'Account')}: {_money(account.get('balance'))}")
        month = summary.get("month") or {}
        if month:
            lines.append("")
            lines.append(
                "MONTH STATE: "
                f"income available {_money(month.get('income_available'))}; "
                f"spent {_money(month.get('total_spent'))}; "
                f"to budget {_money(month.get('to_budget'))}"
            )
        uncategorized = summary.get("uncategorized_count")
        if uncategorized is not None:
            lines.append(f"UNBOUND ECHOES: {uncategorized} uncategorized transaction(s).")
        recent = summary.get("recent") or []
        if recent:
            lines.append("RECENT TRANSACTIONS:")
            for tx in recent[:7]:
                payee = tx.get("payee") or tx.get("imported_payee") or "Unknown payee"
                category = tx.get("category") or "uncategorized"
                lines.append(f"- {tx.get('date', '?')}: {payee} { _money(tx.get('amount')) } [{category}]")
    if chart:
        lines.extend(["", "LEDGER CHART:", compact_text(chart, 1200)])
    return "\n".join(lines)


def build_inkrest_column_brief(player: str = "bj") -> str:
    """Package Dr. Inkrest's therapy/mood memory for a Bleed support column."""
    safe_player = re.sub(r"[^a-zA-Z0-9_-]", "", player or "bj") or "bj"
    chart = read_file_safe(WORKSPACE_DIR / "players" / f"{safe_player}-therapy-chart.md", 140)
    mood_rows = _read_recent_jsonl(WORKSPACE_DIR / "players" / f"{safe_player}-inkrest-log.jsonl", 24)
    support_memory = read_file_safe(WORKSPACE_DIR / "players" / f"{safe_player}-support-memory.json", 160)
    pending_path = WORKSPACE_DIR / "players" / f"{safe_player}-inkrest-pending.json"
    pending = ""
    if pending_path.exists():
        try:
            pending_data = json.loads(pending_path.read_text(encoding="utf-8"))
            if isinstance(pending_data, dict):
                pending = json.dumps(pending_data, ensure_ascii=True)[:900]
        except json.JSONDecodeError:
            pending = ""

    lines = [
        "DR. INKREST BRIEF:",
        "Role: Dr. Selene Inkrest, depth/narrative therapist of the Academy's difficult pages.",
        "Voice: warm, careful, modern narrative therapy with depth-psychology imagery; practical closure over grand interpretation.",
        "Rules: no diagnosis, no replacing real therapy, no forced catharsis; use mood memory gently and return symbols to the next livable hour.",
    ]
    if mood_rows:
        lines.append("")
        lines.append("RECENT ONE-WORD WEATHER:")
        for row in mood_rows[-10:]:
            word = row.get("word") or row.get("mood") or row.get("text") or row.get("answer") or ""
            ts = row.get("timestamp") or row.get("recorded_at") or row.get("time") or ""
            if word:
                lines.append(f"- {ts}: {word}")
    if pending:
        lines.extend(["", "PENDING CHECK-IN:", pending])
    if chart:
        lines.extend(["", "THERAPY CHART:", compact_text(chart, 1600)])
    if support_memory:
        lines.extend(["", "SUPPORT MEMORY:", compact_text(support_memory, 1200)])
    if len(lines) <= 4:
        lines.append("(no Inkrest memory has been logged yet)")
    return "\n".join(lines)


def build_vellum_longevity_brief(fuel_data: str, health: str, pulse: str, vellum_chart: str = "") -> str:
    """Package Vellum's column inputs so the model treats her as longevity counsel, not a food clerk."""
    research_frame = [
        "CURRENT PRACTICAL LONGEVITY FRAMEWORK:",
        "- Preserve and build muscle: adequate protein across the day, resistance training, and creatine when appropriate.",
        "- Protect cardiovascular capacity: daily walking, regular zone-2 movement, and occasional harder efforts scaled to readiness.",
        "- Stabilize metabolism: fiber-rich plants, protein-forward meals, fewer long stretches of caffeine-only fueling.",
        "- Protect recovery: sleep regularity, morning light, lower late alcohol/caffeine, and enough calories to support activity.",
        "- Support cognition and inflammation basics: omega-3-rich fish/foods, hydration, micronutrient diversity, and social connection.",
        "- Use measurable habits, not moral judgments. Vellum advises experiments, not penance.",
    ]
    counsel_rules = [
        "VELLUM COUNSEL RULES:",
        "- She may recommend supplements, exercise protocols, and longevity experiments when context supports them.",
        "- Every supplement recommendation must include why, evidence strength, risks/interactions, and one doctor/pharmacist question when relevant.",
        "- Every exercise recommendation must be scaled to readiness and offer a minimum-effective version.",
        "- She may interpret logged trends and prepare doctor questions, but must not diagnose, prescribe, alter prescription medication, or invent lab values.",
        "- If bloodwork, blood pressure, medications, allergies, or conditions are absent, name the missing context instead of pretending it is known.",
    ]
    return "\n".join([
        "DR. ELOWEN VELLUM COLUMN BRIEF:",
        "Role: Literary Elf, Book Fae, Academy Dietician, and Department of Applied Longevity physician.",
        "Voice: precise, dryly kind, marginalia-minded, clinically practical, never shaming.",
        "Purpose: translate BJ's fuel, vitals, labs, movement, recovery, and longevity research into one or two useful next experiments.",
        "Freshness rule: treat CURRENT FUEL STATE and HEARTBEAT CONTEXT as today's authoritative data. Older fuel context is background pattern only; do not write as if old meals happened today.",
        "",
        "VELLUM CHART / KNOWN PERSONAL CONTEXT:",
        vellum_chart or "(no Vellum chart data available yet; do not invent bloodwork, blood pressure, medications, or supplements)",
        "",
        "LOGGED MEALS / FUEL:",
        fuel_data or "(no fuel data available)",
        "",
        "HEALTH / VITALITY SIGNALS:",
        health or "(no health signals available)",
        "",
        "HEARTBEAT CONTEXT:",
        compact_text(pulse or "", 800),
        "",
        *counsel_rules,
        "",
        *research_frame,
    ])


def get_player_recap_data(cfg: dict) -> str:
    """Extract player story log, active quests, and status for the player correspondent section."""
    player = cfg.get("ENCHANTIFY_DEFAULT_PLAYER", "bj")
    content = read_file_safe(WORKSPACE_DIR / "players" / f"{player}.md", 80)
    if not content:
        return "(no player data available)"

    parts = []

    belief_m  = re.search(r'\*\*Belief:\*\*\s*(\d+)', content)
    chapter_m = re.search(r'\*\*Chapter:\*\*\s*(\S+)', content)
    tutorial_m = re.search(r'\*\*Tutorial Progress:\*\*\s*(\S+)', content)

    belief   = belief_m.group(1) if belief_m else "?"
    chapter  = chapter_m.group(1) if chapter_m else "?"
    tutorial = tutorial_m.group(1) if tutorial_m else "?"
    parts.append(f"PLAYER: {player} | Belief: {belief}/100 | Chapter: {chapter} | Tutorial: {tutorial}")

    # Last 4 story log entries
    log_m = re.search(r'## 📜 Story Log\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    if log_m:
        log_lines = [l.strip() for l in log_m.group(1).strip().splitlines()
                     if l.strip().startswith("-")]
        recent = log_lines[-4:] if len(log_lines) > 4 else log_lines
        if recent:
            parts.append("RECENT STORY LOG (most recent entries):")
            parts.extend(recent)

    # Active quests from Inside Cover table
    cover_m = re.search(r'## The Inside Cover\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    if cover_m:
        active_npcs = re.findall(
            r'\|\s*\*\*([^*]+)\*\*\s*\|[^|]*\|\s*\*\*ACTIVE\*\*',
            cover_m.group(1)
        )
        if active_npcs:
            parts.append(f"ACTIVE QUESTS FROM: {', '.join(active_npcs)}")

    # Compass runs
    compass_m = re.search(r'## Compass Run History\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    if compass_m:
        total_m = re.search(r'\*\*Total runs:\*\*\s*(\d+)', compass_m.group(1))
        last_m  = re.search(r'\*\*Last run:\*\*\s*(.+)', compass_m.group(1))
        total = total_m.group(1) if total_m else "0"
        last  = last_m.group(1).strip() if last_m else "never"
        parts.append(f"COMPASS RUNS: {total} total | last: {last}")

    return "\n".join(parts)


def extract_health_from_pulse(pulse: str) -> str:
    """Pull health/biometric lines from the pulse section."""
    health_lines = []
    for line in pulse.splitlines():
        if any(kw in line for kw in ("Steps", "Sleep", "HRV", "Resting", "Health", "Distance", "Flights")):
            health_lines.append(line.strip().lstrip("- ").strip())
    return "\n".join(health_lines[:6]) if health_lines else ""


def get_previous_coverage(n: int = 3) -> str:
    """Extract what the last N issues covered so the LLM can avoid repeating it.

    Returns a plain-text editorial briefing: headline topics, feature titles,
    gossip opening sentences, and classified text from recent issues.
    The prompt uses this as a DO NOT REPEAT constraint.
    """
    if not ISSUES_DIR.exists():
        return "(no previous issues)"

    html_files = sorted(ISSUES_DIR.glob("*.html"))
    # Exclude today's file if it exists (force-regenerate case)
    today_str = date.today().strftime("%Y-%m-%d")
    html_files = [f for f in html_files if f.stem != today_str]
    recent = html_files[-n:] if len(html_files) >= n else html_files
    if not recent:
        return "(no previous issues)"

    def strip_tags(s: str) -> str:
        return re.sub(r'<[^>]+>', '', s).strip()

    def extract_section_text(html: str, css_class: str, chars: int = 400) -> str:
        """Pull text from the first element with the given CSS class."""
        m = re.search(rf'class="[^"]*{re.escape(css_class)}[^"]*"[^>]*>(.*?)</(?:div|section|article)',
                      html, re.DOTALL | re.IGNORECASE)
        if not m:
            return ""
        return strip_tags(m.group(1))[:chars]

    summaries = []
    for f in reversed(recent):  # most recent first
        try:
            html = f.read_text(errors='replace')
            text = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
            text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)

            parts = [f"Issue date: {f.stem}"]

            # Headline: the h1/h2 inside .headline-title or first big header
            hl = re.search(r'class="headline[^"]*"[^>]*>.*?<(?:h1|h2|p)[^>]*>(.*?)</(?:h1|h2|p)',
                           text, re.DOTALL | re.IGNORECASE)
            if hl:
                parts.append(f"  Headline: {strip_tags(hl.group(1))[:120]}")

            # Feature title
            ft = re.search(r'class="feature-title[^"]*"[^>]*>(.*?)</(?:p|div|h)',
                           text, re.DOTALL | re.IGNORECASE)
            if ft:
                parts.append(f"  Feature title: {strip_tags(ft.group(1))[:120]}")

            # Gossip: first 3 paragraph opening sentences
            gossip_block = re.search(
                r'class="gossip[^"]*"[^>]*>(.*?)</(?:div|section)',
                text, re.DOTALL | re.IGNORECASE)
            if gossip_block:
                gtext = strip_tags(gossip_block.group(1))
                # Split into sentences, grab opening of first 3 items
                sentences = re.split(r'(?<=[.!?])\s+', gtext)
                openers = [s[:100] for s in sentences[:6] if len(s) > 20]
                if openers:
                    parts.append("  Gossip items covered:")
                    for o in openers[:3]:
                        parts.append(f"    - {o}")

            # Classifieds: pull all classified text (these are the ones that repeat verbatim)
            classifieds_block = re.search(
                r'class="classifieds[^"]*"[^>]*>(.*?)</(?:div|section)',
                text, re.DOTALL | re.IGNORECASE)
            if classifieds_block:
                ctext = strip_tags(classifieds_block.group(1))
                lines = [l.strip() for l in ctext.splitlines() if l.strip()]
                if lines:
                    parts.append("  Classifieds run:")
                    for l in lines[:6]:
                        parts.append(f"    {l[:100]}")

            summaries.append("\n".join(parts))
        except Exception:
            continue

    if not summaries:
        return "(no previous issues)"

    header = (
        "PREVIOUS ISSUE COVERAGE — EDITORIAL CONSTRAINT\n"
        "Do not repeat headlines, feature angles, or gossip items already run.\n"
        "Stories may continue to develop the same threads only if there is new information.\n"
        "Classifieds must be freshly written — do not reuse text from any previous issue.\n"
        "Rotate which threads and characters receive front-page and feature attention.\n"
        "A thread that dominated the last two issues should appear only in passing this issue.\n\n"
    )
    return header + "\n\n".join(summaries)


# ── Agent call ────────────────────────────────────────────────────────────────

def _normalize_gateway_model(model: str) -> str:
    """OpenClaw's HTTP gateway currently accepts only openclaw model ids."""
    model = (model or "").strip()
    if model == "openclaw" or model.startswith("openclaw/"):
        return model
    return "openclaw"


def _oc_gateway_cfg() -> tuple[int, str, str, int]:
    """Return (port, token, model, timeout) with secrets/env overrides."""
    cfg_path = Path.home() / ".openclaw" / "openclaw.json"
    cfg: dict = {}
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text())
        except Exception:
            pass
    port  = cfg.get("gateway", {}).get("port", 18789)
    token = cfg.get("gateway", {}).get("auth", {}).get("token", "")
    secrets = load_config()
    raw_model = os.environ.get("BLEED_MODEL") or secrets.get("BLEED_MODEL") or "openclaw"
    model = _normalize_gateway_model(raw_model)
    timeout_raw = os.environ.get("BLEED_GATEWAY_TIMEOUT") or secrets.get("BLEED_GATEWAY_TIMEOUT") or "90"
    try:
        timeout = max(15, int(timeout_raw))
    except ValueError:
        timeout = 90
    return port, token, model, timeout


def call_agent(
    prompt: str,
    *,
    max_tokens: int = 8000,
    temperature: float = 0.85,
    timeout_override: Optional[int] = None,
    system_content: Optional[str] = None,
) -> str:
    """Generate newspaper content via the openclaw HTTP gateway.

    Uses a direct /v1/chat/completions call with a fresh session key so the
    gateway does NOT load enchantify agent context (AGENTS.md, world files,
    tool history). This avoids per-agent model overrides and cuts cold-start
    overhead from several minutes to seconds.
    """
    port, token, model, timeout = _oc_gateway_cfg()
    if timeout_override is not None:
        timeout = timeout_override
    url = f"http://127.0.0.1:{port}/v1/chat/completions"
    session_key = f"bleed-gen-{int(time.time())}"

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": system_content or (
                    "You are writing for The Bleed, the daily student newspaper of an in-world "
                    "literary magical academy. Respond ONLY with the newspaper content in the "
                    "exact format requested. Begin immediately with ===HEADLINE=== — no preamble, "
                    "no commentary, no closing remarks."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }

    req = urllib.request.Request(
        url,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "x-openclaw-session-key": session_key,
        },
        data=json.dumps(payload).encode("utf-8"),
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        content = (result.get("choices", [{}])[0]
                         .get("message", {})
                         .get("content") or "")
        return content.strip()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"Gateway returned HTTP {e.code}: {body}") from e
    except Exception as e:
        raise RuntimeError(f"Gateway call failed: {e}") from e


def model_smoke_test() -> int:
    """Tiny gateway check for the configured Bleed model."""
    port, token, model, timeout = _oc_gateway_cfg()
    print(f"BLEED_MODEL={model}")
    print(f"BLEED_GATEWAY=127.0.0.1:{port}")
    print(f"BLEED_GATEWAY_TIMEOUT={timeout}")
    try:
        reply = call_agent("Reply with exactly: BLEED_OK")
    except Exception as e:
        print(f"FAIL: {e}")
        return 1
    print(reply[:200] or "(empty)")
    return 0 if "BLEED_OK" in reply else 1


# ── Content generation ────────────────────────────────────────────────────────

def get_outer_stacks_brief(player_name: str) -> str:
    """Blend anchor reality with wider Outer Stacks pressure for a dedicated column."""
    def grab(pattern: str, text: str, default: str = "", flags: int = 0, group: int = 1) -> str:
        m = re.search(pattern, text, flags)
        return m.group(group).strip() if m else default

    def short(text: str, n: int) -> str:
        text = (text or "").strip()
        return text[:n] + "…" if len(text) > n else text

    def anchor_type(text: str) -> str:
        value = re.sub(r"[^A-Za-z]", "", text or "").upper()
        value = {"FIND": "NOTICE", "DISCOVER": "NOTICE", "SEARCH": "NOTICE", "LOOK": "NOTICE"}.get(value, value)
        return value if value in {"NOTICE", "EMBARK", "SENSE", "WRITE", "REST"} else "NOTICE"

    def load_json(path: Path) -> dict:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text())
        except Exception:
            return {}

    lore = read_file_safe(WORKSPACE_DIR / "lore" / "outer-stacks.md", 260)
    heartbeat = read_file_safe(WORKSPACE_DIR / "HEARTBEAT.md", 140)
    pulse = extract_pulse_section(heartbeat)
    anchors_text = read_file_safe(WORKSPACE_DIR / "players" / f"{player_name}-anchors.md")
    register_text = read_file_safe(WORKSPACE_DIR / "lore" / "world-register.md")
    queue_text = read_file_safe(WORKSPACE_DIR / "memory" / "tick-queue.md", 60)
    pocket_state = load_json(WORKSPACE_DIR / "config" / "pocket-anchors.json")
    classifieds_dir = WORKSPACE_DIR / "logs" / "classifieds-ledger"
    scene_dir = WORKSPACE_DIR / "logs" / "scene-ledger"

    anchor_bits = []
    for section in re.split(r'^## ', anchors_text, flags=re.MULTILINE)[1:]:
        lines = section.strip().splitlines()
        name = lines[0].strip() if lines else "?"
        atype = anchor_type(grab(r'\*\*Type:\*\*\s*(.+)', section, default="?"))
        belief = grab(r'\*\*Belief invested:\*\*\s*(\d+)', section, default="?")
        echo = grab(r'\*\*Academy echo:\*\*\s*(.+)', section, flags=re.DOTALL, default="")
        room = grab(r'\*\*Outer Stacks room:\*\*\s*(.+)', section, flags=re.DOTALL, default="")
        rule = grab(r'\*\*Local rule:\*\*\s*(.+)', section, flags=re.DOTALL, default="")
        visit_count = grab(r'\*\*Visit count:\*\*\s*(\d+)', section, default="0")
        anchor_bits.append(
            f"- ANCHOR: {name} | {atype} | Belief {belief} | visits {visit_count} | echo: {short(echo, 120)} | room: {short(room, 160)} | rule: {short(rule, 120)}"
        )
    if not anchor_bits:
        anchor_bits.append("- ANCHOR: none yet established")

    pocket_bits = []
    for anchor_name, state in (pocket_state.get(player_name) or {}).items():
        charges = state.get("charges", 0)
        active = state.get("active_session")
        if active and active.get("expires_at"):
            pocket_bits.append(f"- CARD: {anchor_name} | {charges} charges | active until {active.get('expires_at')}")
        else:
            pocket_bits.append(f"- CARD: {anchor_name} | {charges} charges")
    if not pocket_bits:
        pocket_bits.append("- CARD: no pocket-anchor state yet")

    seasonal_bits = []
    season = grab(r'- \*\*Season:\*\*\s*(.+)', pulse, default="")
    moon = grab(r'- \*\*Moon:\*\*\s*(.+)', pulse, default="")
    weather = grab(r'- \*\*Belfast Feel:\*\*\s*(.+)', pulse, default="")
    if season:
        seasonal_bits.append(f"- SEASON: {season}")
    if moon:
        seasonal_bits.append(f"- MOON: {moon}")
    if weather:
        seasonal_bits.append(f"- WEATHER PRESSURE: {weather}")

    outer_entities = []
    for line in register_text.splitlines():
        if "Outer Stacks" in line or "anchor" in line.lower() or "Goblin Index Empire" in line:
            clean = line.strip()
            if clean.startswith("|"):
                outer_entities.append(clean)
    outer_entities = outer_entities[:6]

    frontier_activity = []
    for line in queue_text.splitlines():
        low = line.lower()
        if any(k in low for k in ["anchor", "outer stacks", "goblin", "market", "chronograph", "crossroads", "fermentation", "wayskeeper", "hearthkin"]):
            frontier_activity.append(line.strip())
    if not frontier_activity:
        frontier_activity.append("No direct frontier stir recorded in tick-queue; treat this as quiet pressure, not absence.")
    frontier_activity = frontier_activity[:6]

    lore_signals = []
    for needle in [
        "The worst thing the Nothing does to an Outer Stacks room is make it boring",
        "The only way to enter the Outer Stacks is through an Anchor room",
        "The Fae in the Outer Stacks are wilder versions",
        "Room Evolution",
        "Pocket Anchors (Accessibility)",
    ]:
        if needle in lore:
            lore_signals.append(needle)

    ledger_bits = []
    if classifieds_dir.exists():
        recent = sorted(classifieds_dir.glob("*.json"))[-1:]
        for path in recent:
            payload = load_json(path)
            ledger_bits.append(f"- CLASSIFIEDS LEDGER: {path.name} | {payload.get('count', 0)} open hooks")
    else:
        ledger_bits.append("- CLASSIFIEDS LEDGER: none yet — frontier coverage must rely on state, not prior postings")

    if scene_dir.exists():
        recent = sorted(scene_dir.glob("*.jsonl"))[-1:]
        for path in recent:
            ledger_bits.append(f"- SCENE LEDGER: {path.name} present")
    else:
        ledger_bits.append("- SCENE LEDGER: none yet — no realized frontier scenes have been recorded")

    parts = ["ANCHOR INFLUENCE (do not let this become the whole column):"]
    parts.extend(anchor_bits[:3])
    parts.append("")
    parts.append("POCKET ANCHOR STATE:")
    parts.extend(pocket_bits[:4])
    parts.append("")
    parts.append("SEASONAL / NOTHING PRESSURE:")
    parts.extend(seasonal_bits[:4])
    parts.extend(f"- LORE: {x}" for x in lore_signals[:4])
    parts.append("")
    parts.append("WIDER OUTER STACKS SIGNALS:")
    parts.extend(f"- REGISTER: {x}" for x in outer_entities)
    parts.extend(f"- QUEUE: {x}" for x in frontier_activity)
    parts.extend(ledger_bits)

    return "\n".join(parts)


def build_classified_leads() -> str:
    """Deterministic leads for classifieds so they anchor to real state."""
    leads = []

    # Thread beats and pressures
    threads_content = read_file_safe(WORKSPACE_DIR / "lore" / "threads.md")
    register_content = read_file_safe(WORKSPACE_DIR / "lore" / "world-register.md")
    thread_belief: dict[str, int] = {}
    active_section_m = re.search(r'## Active Threads(.*?)(?=^## |\Z)', register_content, re.DOTALL | re.MULTILINE)
    if active_section_m:
        row_re = re.compile(r'^\|\s*([^|]+?)\s*\|\s*Thread\s*\|\s*(\d+)\s*\|', re.MULTILINE | re.IGNORECASE)
        for m in row_re.finditer(active_section_m.group(1)):
            thread_belief[m.group(1).strip().lower()] = int(m.group(2))

    thread_rows = []
    for section in re.split(r'^## Thread: ', threads_content, flags=re.MULTILINE)[1:]:
        slines = section.strip().splitlines()
        name = slines[0].strip() if slines else "?"
        phase_m = re.search(r'\*\*phase:\*\*\s*(.+)', section)
        pressure_m = re.search(r'\*\*pressure:\*\*\s*(.+)', section)
        beat_m = re.search(r'\*\*Next beat:\*\*\s*(.+)', section)
        belief = thread_belief.get(name.lower(), 0)
        thread_rows.append({
            "name": name,
            "belief": belief,
            "phase": phase_m.group(1).strip() if phase_m else "?",
            "pressure": pressure_m.group(1).strip() if pressure_m else "?",
            "beat": beat_m.group(1).strip()[:140] if beat_m else "",
        })
    thread_rows.sort(key=lambda x: -x["belief"])
    for t in thread_rows[:4]:
        leads.append(f"- THREAD LEAD: {t['name']} | Belief {t['belief']} | {t['phase']} | pressure: {t['pressure']} | next: {t['beat']}")

    # High-belief entities / talismans
    entity_lines = get_entity_standings().splitlines()
    for line in entity_lines[:4]:
        if line.strip():
            leads.append(f"- ENTITY LEAD: {line.strip().lstrip('- ').strip()}")

    # Recent simulation/tick activity
    tick_queue = read_file_safe(WORKSPACE_DIR / "memory" / "tick-queue.md", 40)
    tick_lines = []
    for line in tick_queue.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("- **") or line.startswith("Narrative seed:") or line.startswith("*Raw:"):
            tick_lines.append(line)
    for line in tick_lines[:6]:
        leads.append(f"- SIM LEAD: {line[:180]}")

    return "\n".join(leads) if leads else "(no classified leads available)"


def record_classifieds_hooks(date_str: str, issue_number: int, classifieds_text: str) -> None:
    """Persist published classifieds as hooks for later play/state use."""
    if not classifieds_text.strip():
        return
    CLASSIFIEDS_LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    out = CLASSIFIEDS_LEDGER_DIR / f"{date_str}.json"

    blocks = [b.strip() for b in re.split(r'\n\s*\n', classifieds_text) if b.strip()]
    entries = []
    for idx, block in enumerate(blocks, 1):
        label = "NOTICE"
        m = re.match(r'^([A-Z][A-Z ]+):\s*(.*)', block, re.DOTALL)
        body = block
        if m:
            label = m.group(1).strip()
            body = m.group(2).strip()
        entries.append({
            "id": f"{date_str}-classified-{idx}",
            "issue_number": issue_number,
            "date": date_str,
            "label": label,
            "text": body,
            "raw": block,
            "status": "open",
        })

    payload = {
        "date": date_str,
        "issue_number": issue_number,
        "entries": entries,
        "count": len(entries),
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False))


def _first_section_sentence(text: str, fallback: str = "") -> str:
    text = re.sub(r"<[^>]+>", " ", html_unescape(text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return fallback
    bits = re.split(r"(?<=[.!?])\s+", text)
    return compact_text(bits[0] if bits else text, 220)


def _ripple_entities(text: str, limit: int = 4) -> list[str]:
    text = text or ""
    candidates: list[str] = []
    for m in re.finditer(r"\b([A-Z][a-z]+(?:\s+(?:[A-Z][a-z]+|[A-Z]\.)){1,3})\b", text):
        name = re.sub(r"\s+", " ", m.group(1)).strip()
        if name in {"The Bleed", "Dr Vellum", "Academy Daily", "Outer Stacks"}:
            continue
        if name not in candidates:
            candidates.append(name)
        if len(candidates) >= limit:
            break
    return candidates


def _append_bleed_ripples(entries: list[dict]) -> None:
    if not entries:
        return
    BLEED_RIPPLES_LOG.parent.mkdir(parents=True, exist_ok=True)
    with BLEED_RIPPLES_LOG.open("a", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


def record_bleed_ripples(date_str: str, issue_number: int, sections: dict, meta: dict) -> list[dict]:
    """Let published journalism create public-pressure facts for later scenes.

    These are not objective canon rewrites. They are how the Academy reacts to
    what was printed: rumors, reputation pressure, practical nudges, and hooks.
    """
    ripples: list[dict] = []
    now = datetime.now().isoformat(timespec="seconds")

    def add(section: str, effect_type: str, pressure: str, detail: str, *, weight: int = 1) -> None:
        detail = compact_text(detail, 420)
        if not detail:
            return
        ripples.append({
            "id": f"bleed-{date_str}-{issue_number}-{len(ripples) + 1}",
            "timestamp": now,
            "date": date_str,
            "issue_number": issue_number,
            "section": section,
            "effect_type": effect_type,
            "pressure": pressure,
            "detail": detail,
            "entities": _ripple_entities(detail),
            "weight": weight,
            "status": "open",
        })

    headline = parse_headline(sections.get("HEADLINE", ""))
    if headline.get("title") or headline.get("body"):
        add(
            "HEADLINE",
            "public_record",
            "front-page interpretation",
            f"{headline.get('title', '').strip()}: {headline.get('body', '').strip()}",
            weight=4,
        )

    feature = _first_section_sentence(sections.get("FEATURE", ""))
    if feature:
        add("FEATURE", "rumor_pressure", "feature article becomes corridor talk", feature, weight=3)

    gossip = _first_section_sentence(sections.get("GOSSIP", ""))
    if gossip:
        add("GOSSIP", "social_reaction", "gossip creates reputation pressure", gossip, weight=3)

    war = _first_section_sentence(sections.get("WARREPORT", ""))
    if war:
        add("WARREPORT", "talisman_pressure", "app war report changes what factions think is possible", war, weight=4)

    talisman = _first_section_sentence(sections.get("TALISMAN", ""))
    if talisman:
        add("TALISMAN", "talisman_pressure", "talisman column colors the next pact move", talisman, weight=3)

    fuel = _first_section_sentence(sections.get("FUEL", ""))
    if fuel:
        add("FUEL", "practical_nudge", "Dr. Vellum's column becomes usable advice", fuel, weight=2)

    gimble = _first_section_sentence(sections.get("GIMBLE", ""))
    if gimble:
        add("GIMBLE", "ledger_nudge", "Gimble's column becomes a shame-free money prompt", gimble, weight=2)

    inkrest = _first_section_sentence(sections.get("INKREST", ""))
    if inkrest:
        add("INKREST", "support_nudge", "Dr. Inkrest's column becomes a reauthoring prompt", inkrest, weight=2)

    goblin = _first_section_sentence(sections.get("GOBLINEXCHANGE", ""))
    if goblin:
        add("GOBLINEXCHANGE", "market_offer", "goblin exchange may appear in play", goblin, weight=2)

    classifieds = [b.strip() for b in re.split(r"\n\s*\n", sections.get("CLASSIFIEDS", "")) if b.strip()]
    for block in classifieds[:3]:
        add("CLASSIFIEDS", "open_hook", "classified notice can enter the scene as a physical/public hook", block, weight=2)

    _append_bleed_ripples(ripples)
    return ripples


def build_outer_stacks_fallback(data: dict) -> str:
    brief = (data.get("outer_stacks") or "").strip()
    if not brief:
        return ""
    lines = [l.strip() for l in brief.splitlines() if l.strip()]
    anchors = [l[2:] for l in lines if l.startswith("- ANCHOR:")][:2]
    cards = [l[2:] for l in lines if l.startswith("- CARD:")][:2]
    pressure = [l[2:] for l in lines if l.startswith("- SEASON:") or l.startswith("- MOON:") or l.startswith("- WEATHER PRESSURE:")][:3]
    wider = [l[2:] for l in lines if l.startswith("- REGISTER:") or l.startswith("- QUEUE:")][:4]

    parts = []
    if anchors:
        parts.append("Two doors currently hold the frontier nearest the Academy. " + " ".join(anchors) + ".")
    if cards:
        parts.append("Pocket-anchor conditions are live rather than theoretical. " + " ".join(cards) + ".")
    if pressure:
        parts.append("The wider conditions matter out there. " + " ".join(pressure) + ".")
    if wider:
        parts.append("Beyond the player’s own thresholds, the frontier is still moving. " + " ".join(wider) + ".")
    return "\n\n".join(parts)


GOSSIP_SOURCES = [
    ("Zara Finch", "Z.F.", "warm, observant, worried in specifics; notices what others miss"),
    ("Damien Nights", "D.N.", "brooding, shadowy, reluctant; says too little and means more"),
    ("Melisande Blackwood", "M.B.", "cold, surgical, loyal, ruthless; cuts straight to motive"),
    ("Selene Moonfall", "S.M.", "silky, social, condescending; makes every compliment a lever"),
    ("Raven Hearts", "R.H.", "quiet, flat, unreadable; records shadows and social angles"),
    ("Serenity Brown", "S.B.", "hopeful, gentle, sometimes too generous; sees the possible good"),
    ("Cedric Widden", "C.W.", "nervous, funny despite himself; jokes where fear leaks through"),
    ("Professor Luna Wispwood", "L.W.", "flighty, adventurous, vivid; turns warnings into weather"),
]


def gossip_source_roster() -> str:
    return "\n".join(f"- {name} ({initials}): {style}" for name, initials, style in GOSSIP_SOURCES)


def build_fallback_gossip(data: dict) -> str:
    lead_thread = _thread_names(data.get("thread_summary", ""))[0] if _thread_names(data.get("thread_summary", "")) else "Wicker's Campaign"
    tick = _first_nonempty_line(data.get("tick_queue", ""), "No one admits to moving the latest rumor.")
    tick = re.sub(r"[*_`]+", "", tick)
    return (
        "Zara Finch says Wicker Eddies has been smiling at empty chairs again, which would be ordinary theater if the chairs had not started facing him back. "
        "She adds that anyone who calls this coincidence should be asked why coincidence keeps choosing the same table. — Z.F.\n\n"
        "Damien Nights reports that two shadows near the west stair changed direction when Wicker passed, then pretended they had always meant to. "
        "He would like it noted that this is not proof of anything, which is what people say when proof has begun breathing nearby. — D.N.\n\n"
        f"Melisande Blackwood has observed that {lead_thread} is attracting amateurs who confuse attention with leverage. "
        "Her correction was brief, private, and apparently effective; no one has repeated the mistake in her hearing. — M.B.\n\n"
        "Selene Moonfall says the real scandal is not that Wicker knows things, but that so many students make being knowable look effortless. "
        "She recommends mystery as a basic hygiene practice. — S.M.\n\n"
        f"Cedric Widden was heard describing the latest corridor report as '{compact_text(tick, 120)}' and then immediately denying he had described anything at all. "
        "The denial was more convincing before it asked for a biscuit. — C.W."
    )


def validate_gossip_section(text: str) -> list[str]:
    errors = []
    if re.search(r"(?:^|\s)[—-]\s*W\.E\.\s*$", text or "", re.MULTILINE):
        errors.append("GOSSIP uses W.E. as a signature; gossip about Wicker must come from other characters")
    if "W.E.'s voice" in (text or "") or "Wicker reports" in (text or ""):
        errors.append("GOSSIP leaked old Wicker-column prompt language")
    signed = re.findall(r"(?:^|\s)[—-]\s*([A-Z]\.[A-Z]\.|[A-Z]\.)\s*$", text or "", re.MULTILINE)
    non_wicker_signed = [sig for sig in signed if sig != "W.E."]
    if len(non_wicker_signed) < 4:
        errors.append("GOSSIP needs at least four signed items from actual non-Wicker characters")
    return errors


def repair_gossip_section(sections: dict, data: dict) -> None:
    gossip = sections.get("GOSSIP", "")
    errors = validate_gossip_section(gossip)
    if errors:
        print("  ↺ Replacing GOSSIP with sourced corridor whispers: " + "; ".join(errors))
        sections["GOSSIP"] = build_fallback_gossip(data)


def validate_generated_sections(sections: dict) -> list[str]:
    required = ["HEADLINE", "GOSSIP", "FEATURE", "CLASSIFIEDS", "OUTERSTACKS", "FORECAST", "MARKET"]
    errors = []
    for key in required:
        text = (sections.get(key) or "").strip()
        if not text:
            errors.append(f"missing section: {key}")
    outer = (sections.get("OUTERSTACKS") or "").strip()
    if outer and len(outer) < 120:
        errors.append("OUTERSTACKS too short")
    errors.extend(validate_gossip_section(sections.get("GOSSIP", "")))
    return errors


def _first_nonempty_line(text: str, fallback: str = "") -> str:
    for line in (text or "").splitlines():
        clean = line.strip().strip("-").strip()
        if clean:
            return clean
    return fallback


def _thread_names(thread_summary: str, limit: int = 4) -> list[str]:
    names = []
    for line in (thread_summary or "").splitlines():
        m = re.match(r"-\s+(.+?)\s+\[", line.strip())
        if m:
            name = m.group(1).strip()
            if name and name not in names:
                names.append(name)
        if len(names) >= limit:
            break
    return names


def build_fallback_sections(data: dict, reason: str = "") -> dict:
    """Build a complete issue from local data when the LLM gateway fails."""
    threads = _thread_names(data.get("thread_summary", ""))
    lead_thread = threads[0] if threads else "Academy Daily Life"
    second_thread = threads[1] if len(threads) > 1 else "The Current Arc"
    player = data.get("player", {})
    player_name = player.get("name", "bj")
    forecast = data.get("forecast") or "Conditions remain partly legible."
    health = data.get("health") or "Vitality signals unavailable."
    war_data = data.get("war_data") or "No chapter war data available."
    market = data.get("market_odds_formatted") or "(no thread market data available)"
    vellum = data.get("vellum_column_data") or data.get("fuel_data") or "No provisions log was filed."
    gimble = data.get("gimble_column_data") or "Gimble has not filed a ledger note yet."
    inkrest = data.get("inkrest_column_data") or "Dr. Inkrest has not filed a reauthoring note yet."
    fae_ledger = data.get("fae_ledger") or "The Margin is clean; no open fae bargains."
    outer = build_outer_stacks_fallback(data) or "No new frontier dispatch has crossed the desk. The Outer Stacks remain adjacent, unsupervised, and politely unaccounted for."
    if len(outer) < 140:
        outer += " The frontier desk notes that thin reports are not empty reports; they usually mean the nearest doors are waiting for a physical visit before saying more."
    talisman = data.get("talisman_data") or "No leading talisman declared itself before press time."
    tick = _first_nonempty_line(data.get("tick_queue", ""), "No simulation incident was reported before press time.")
    recap = data.get("player_recap") or "No correspondent recap was available."
    classified_leads = [line.strip("- ").strip() for line in (data.get("classified_leads") or "").splitlines() if line.strip()]
    classified_lines = classified_leads[:3] or [
        "FOUND: One cup retaining the weight of a kind word near the Great Hall.",
        "NOTICE: Quiet rooms may be louder than they appear.",
        "SEEKING: A witness to the latest tapestry rhythm.",
    ]

    classified_text = "\n\n".join(
        f"{item if re.match(r'^[A-Z ]+:', item) else 'NOTICE: ' + item}"
        for item in classified_lines
    )
    while classified_text.count("\n\n") < 4:
        classified_text += "\n\nWARNING: Any whisper found growing heavier should be carried flat, not folded."

    return {
        "HEADLINE": (
            f"Title: {lead_thread} Holds the Front Page\n"
            f"Subhead: The evening edition was compiled from local ledgers after the press gateway failed to answer.\n"
            f"Body: The Bleed published a ledger-backed edition tonight after the usual long-form correspondent failed to file before deadline. "
            f"The dominant pressure remains {lead_thread}, with {second_thread} visible behind it in the school weather.\n\n"
            f"Editors observed the latest tick as follows: {tick}. The newsroom treats this as live institutional movement, not rumor.\n\n"
            f"The current arc and active threads continue to shape coverage. This edition is plainer than usual, but the facts are still on the table: "
            f"thread pressure, student state, chapter war figures, and frontier reports were all read locally before publication.\n\n"
            f"Readers are advised to treat quiet details as consequential until further notice. The Academy has recently shown a habit of making small things count."
        ),
        "GOSSIP": build_fallback_gossip(data),
        "WEATHER": forecast,
        "FORECAST": (
            f"70% chance of continued pressure around {lead_thread}; its ledger position makes it difficult to ignore.\n"
            f"55% chance that {second_thread} surfaces as a secondary condition rather than a front-page storm.\n"
            "45% chance of quiet-life consequences becoming materially relevant before the week is out.\n"
            "Overall narrative outlook: settled on the surface, active underneath."
        ),
        "MARKET": market,
        "FUEL": (
            f"{vellum}\n\n"
            f"Vitality barometer: {health}\n\n"
            "Dr. Vellum's Desk recommends treating longevity as narrative infrastructure: muscle, sleep, movement, protein, fiber, and joy, all annotated without moral drama."
        ),
        "GIMBLE": (
            f"{gimble}\n\n"
            "Gimble's ruling: bind one clear number, name one risk, and take one tiny account-keeping action without shame."
        ),
        "INKREST": (
            f"{inkrest}\n\n"
            "Dr. Inkrest's note: notice the story the day is asking BJ to inhabit, then choose the smallest kinder revision available in the next hour."
        ),
        "EXCHANGE": (
            (data.get("entity_standings") or "No exchange prices were available before press time.")
            + "\n\nFae Ledger:\n"
            + fae_ledger
        ),
        "GOBLINEXCHANGE": data.get("goblin_exchange", ""),
        "FEATURE": (
            f"Title: What the Quiet Is For\n"
            "Byline: The Recovery Desk\n"
            f"Body: The Academy has spent several weeks learning how alarms sound. It is now beginning the more difficult study: what happens after the alarm stops.\n\n"
            f"{lead_thread} remains the most visible public pressure, but the subtler question belongs to the ordinary rooms. Which details become permanent? Which apologies land? Which jokes return without forcing themselves?\n\n"
            "Faculty sources describe the present moment as a repair interval, though no one agrees on whether repair should be supervised. Students, naturally, have begun testing this by being kind in unsanctioned ways."
        ),
        "CLASSIFIEDS": classified_text,
        "OUTERSTACKS": outer,
        "CORRECTION": "The Bleed regrets implying that silence is empty. Subsequent evidence suggests silence may be occupied.",
        "MISSING": "No report was filed from several dormant threads tonight. Absence remains absence until it starts leaving footprints.",
        "PLAYER": (
            f"The correspondent {player_name} remains a registered presence in the Academy ledgers. "
            f"{compact_text(recap, 360)}"
        ),
        "WARREPORT": war_data,
        "TALISMAN": (
            f"The Ascendant desk filed from local figures only.\n\n{talisman}\n\n"
            "Declaration: the leading philosophy will continue to act through small pressures until someone mistakes them for weather."
        ),
    }


def compact_text(text: str, limit: int = 240) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


REQUIRED_BLEED_SECTIONS = [
    "HEADLINE",
    "GOSSIP",
    "WEATHER",
    "FORECAST",
    "MARKET",
    "FUEL",
    "GIMBLE",
    "INKREST",
    "EXCHANGE",
    "FEATURE",
    "CLASSIFIEDS",
    "OUTERSTACKS",
    "CORRECTION",
    "MISSING",
    "PLAYER",
    "WARREPORT",
    "TALISMAN",
]


def _config_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name) or load_config().get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _config_int(name: str, default: int, minimum: int = 1) -> int:
    raw = os.environ.get(name) or load_config().get(name)
    if raw is None or str(raw).strip() == "":
        return max(minimum, default)
    try:
        return max(minimum, int(str(raw).strip()))
    except ValueError:
        return max(minimum, default)


def _bleed_allow_fallback() -> bool:
    return _config_bool("BLEED_ALLOW_FALLBACK", False)


def _bleed_chunk_attempts() -> int:
    return _config_int("BLEED_CHUNK_ATTEMPTS", 2, minimum=1)


def _bleed_chunk_timeout() -> int:
    return _config_int("BLEED_CHUNK_TIMEOUT", _oc_gateway_cfg()[3], minimum=60)


def _bleed_mono_timeout() -> int:
    """Short first-pass timeout. Chunked generation follows if this misses."""
    raw = os.environ.get("BLEED_MONOLITH_TIMEOUT") or load_config().get("BLEED_MONOLITH_TIMEOUT") or "75"
    try:
        return max(20, int(raw))
    except ValueError:
        return 75


def _bleed_generation_mode() -> str:
    raw = os.environ.get("BLEED_GENERATION_MODE") or load_config().get("BLEED_GENERATION_MODE") or "chunked"
    raw = raw.strip().lower()
    return raw if raw in {"chunked", "hybrid", "monolith"} else "chunked"


def _chunk_context(data: dict) -> str:
    """Small enough for lower-tier models; rich enough for concrete reporting."""
    return f"""Publication: {data.get('date_str')} · Issue #{data.get('issue_number')}

Previous coverage constraints:
{compact_text(data.get('previous_coverage', ''), 1200)}

Simulation:
{compact_text(data.get('tick_queue', ''), 900)}

Threads:
{compact_text(data.get('thread_summary', ''), 1400)}

Entities:
{compact_text(data.get('entity_standings', ''), 900)}

Player:
Chapter {data.get('player', {}).get('chapter')} · Belief {data.get('player', {}).get('belief')}/100
{compact_text(data.get('player_recap', ''), 700)}

Goblin Market Exchange:
{compact_text(data.get('goblin_exchange', ''), 900)}

Classified leads:
{compact_text(data.get('classified_leads', ''), 800)}

Chapter war:
{compact_text(data.get('war_data', ''), 1200)}

Outer Stacks:
{compact_text(data.get('outer_stacks', ''), 1000)}

Ascendant:
{compact_text(data.get('talisman_data', ''), 700)}
Chapter NPCs: {compact_text(data.get('talisman_npcs', ''), 500)}

Dr. Vellum:
{compact_text(data.get('vellum_column_data', data.get('fuel_data', '')), 900)}

Gimble:
{compact_text(data.get('gimble_column_data', ''), 900)}

Dr. Inkrest:
{compact_text(data.get('inkrest_column_data', ''), 900)}

Weather:
{compact_text(data.get('forecast', ''), 700)}

Health:
{compact_text(data.get('health', ''), 500)}
"""


def _section_chunk_prompt(context: str, section_names: list[str], instructions: str) -> str:
    markers = "\n".join(f"==={name}===\n[write this section]" for name in section_names)
    return f"""You are writing selected sections of THE BLEED, the Academy student newspaper.
Voice: dry, precise, literary, concrete, slightly gothic. Treat the magical academy as real.
Use the data. Do not mention that this is a chunk. Do not include sections not requested.

DATA:
{context}

GOSSIP SOURCES:
{gossip_source_roster()}

REQUESTED SECTIONS:
{instructions}

Return ONLY these exact section markers, in this order:
{markers}
"""


def generate_content_chunked(data: dict, reason: str = "") -> dict:
    """Generate The Bleed in smaller independent packets.

    Strict mode is the default: a failed section packet aborts publication
    instead of quietly printing a local fallback edition.
    """
    allow_fallback = _bleed_allow_fallback()
    sections = build_fallback_sections(data, reason=reason) if allow_fallback else {}
    context = _chunk_context(data)
    timeout = _bleed_chunk_timeout()
    attempts = _bleed_chunk_attempts()
    system = (
        "You are writing selected sections for The Bleed. Respond only with the requested "
        "===SECTION=== blocks. No preamble, no apology, no markdown wrapper."
    )
    chunks = [
        (
            ["HEADLINE", "GOSSIP", "FEATURE"],
            3200,
            "HEADLINE: title/subhead/body, 4-6 paragraphs, concrete reporting on a current event that has new information. "
            "GOSSIP: 5 distinct corridor whisper items from actual named Academy characters, each signed with that character's initials. "
            "Wicker Eddies may be the subject, but he must not be the columnist or signature. Never use — W.E. "
            "FEATURE: titled/bylined longer context piece, 4-6 paragraphs, not a repeat of recent features.",
        ),
        (
            ["WEATHER", "FORECAST", "MARKET"],
            2200,
            "WEATHER: 4-day Academy weather using exact forecast conditions. "
            "FORECAST: narrative weather with probabilities and named threads. "
            "MARKET: thread futures ticker with YES/NO odds from data and commentary.",
        ),
        (
            ["FUEL", "GIMBLE", "INKREST"],
            2800,
            "FUEL: Dr. Vellum's Desk; one comprehensive column combining logged foods, health/vitality signals, and practical longevity advice. "
            "Do not create a separate Barometer; Vellum owns the whole body/longevity reading. "
            "GIMBLE: Ledger Office column from Actual Budget/Gimble data; one number, one risk, one non-shaming next action. "
            "INKREST: Reauthoring Desk column from Inkrest mood/therapy memory; one pattern, one gentle reframing, one next-hour action.",
        ),
        (
            ["EXCHANGE", "CLASSIFIEDS"],
            2200,
            "EXCHANGE: belief ticker for significant entities, one entity per line in '- Name (Type): Belief N' format, then one commentary paragraph. "
            "Do not write the Goblin Market board inside EXCHANGE; it is provided and rendered separately. "
            "CLASSIFIEDS: 5-6 fresh notices grounded in classified leads and current state.",
        ),
        (
            ["OUTERSTACKS", "CORRECTION", "MISSING", "PLAYER"],
            2200,
            "OUTERSTACKS: 3-5 paragraphs on frontier/anchor/book-jump conditions, concrete but do not spoil first-visit secrets. "
            "CORRECTION: one dry formal correction. MISSING: dormant/quiet threads, 2-4 lines. "
            "PLAYER: third-person correspondent note, 3-5 concrete sentences.",
        ),
        (
            ["WARREPORT", "TALISMAN"],
            2600,
            "WARREPORT: chess-correspondent analysis using exact chapter war scores and gaps. "
            "TALISMAN: The Ascendant column in the leading talisman's voice, with editorial, brief Q&A with one chapter NPC, and declaration.",
        ),
    ]
    for names, max_tokens, instructions in chunks:
        prompt = _section_chunk_prompt(context, names, instructions)
        last_error = ""
        for attempt in range(1, attempts + 1):
            try:
                attempt_note = f" attempt {attempt}/{attempts}" if attempts > 1 else ""
                print(f"  Generating section packet: {', '.join(names)} ({timeout}s timeout{attempt_note})")
                raw = call_agent(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=0.72,
                    timeout_override=timeout,
                    system_content=system,
                )
                parsed = parse_sections(raw)
                missing = [name for name in names if not (parsed.get(name) or "").strip()]
                if missing:
                    last_error = f"missing required section(s): {', '.join(missing)}"
                    print(f"  ⚠ Section packet incomplete ({', '.join(names)}): {last_error}")
                    continue
                if "GOSSIP" in names:
                    gossip_errors = validate_gossip_section(parsed.get("GOSSIP", ""))
                    if gossip_errors:
                        last_error = "; ".join(gossip_errors)
                        print(f"  ⚠ Section packet gossip rejected: {last_error}")
                        continue
                for name in names:
                    sections[name] = parsed[name].strip()
                last_error = ""
                break
            except Exception as e:
                last_error = str(e)
                print(f"  ⚠ Section packet failed ({', '.join(names)}): {last_error}")
        else:
            if allow_fallback:
                print(f"  ↺ Keeping local fallback for failed section packet: {', '.join(names)}")
                continue
            raise RuntimeError(
                "Bleed generation aborted; section packet failed after "
                f"{attempts} attempt(s): {', '.join(names)}. Last error: {last_error}"
            )

    missing_sections = [name for name in REQUIRED_BLEED_SECTIONS if not (sections.get(name) or "").strip()]
    if missing_sections:
        if allow_fallback:
            fallback_sections = build_fallback_sections(data, reason=reason or "missing model sections")
            for name in missing_sections:
                sections[name] = fallback_sections.get(name, "").strip()
            print(f"  ↺ Filled missing sections from local fallback: {', '.join(missing_sections)}")
        else:
            raise RuntimeError(
                "Bleed generation aborted; model output was incomplete. Missing: "
                + ", ".join(missing_sections)
            )
    return sections


def ensure_scene_ledger_seed(date_str: str, issue_number: int, sections: dict, meta: dict) -> None:
    existing = load_scene_ledger_entries(date_str)
    if existing:
        return
    outer = (sections.get("OUTERSTACKS") or "").strip()
    if not outer:
        return
    payload = {
        "recorded_at": datetime.now().isoformat(),
        "player": meta.get("player_name", "bj"),
        "scene_id": f"bleed-frontier-{date_str}",
        "title": f"Bleed Frontier Desk #{issue_number}",
        "mood": "observant",
        "intensity": "quiet",
        "target": "bleed",
        "channel": "internal",
        "text": outer,
        "voice": "",
        "sequence": ["bleed", "frontier-desk"],
        "results": {"delivery_ok": True, "essential_ok": True, "source": "bleed-bootstrap"},
        "delivery_ok": True,
        "essential_ok": True,
        "director_slate": "",
        "session_entry": "",
        "story": "Frontier Desk bootstrap from published Bleed issue.",
        "cast": sections.get("OUTERSTACKS", "")[:400],
        "feel": sections.get("FORECAST", "")[:200],
        "schedule": meta.get("date_str", date_str),
        "source_systems": ["bleed", "outerstacks", "bootstrap"],
    }
    append_scene_ledger_entry(payload, date_str=date_str)


def generate_content(data: dict) -> dict:
    mode = _bleed_generation_mode()
    if mode == "chunked":
        print("  Generating with chunked Bleed sections.")
        return generate_content_chunked(data, reason="chunked mode")

    prompt = f"""You are writing THE BLEED — the Academy student newspaper.

Publication date: {data['date_str']}
Issue number: #{data['issue_number']}

THE BLEED's voice: Dry, precise, slightly gothic. It reports on the Academy as a real institution.
This is not a parody — it's a real paper. The extraordinary is covered with the same deadpan
reportage as the ordinary. Specificity is everything. Invent concrete details where needed —
named corridors, specific times, partial quotes — the kind of texture that makes a place feel real.

The reader should be able to SETTLE INTO THIS PAPER. Every section except The Exchange,
The Correction, The Missing, and The Correspondent should be substantial, readable prose.

{data['previous_coverage']}

DATA FEEDS (synthesize into journalism — never quote data directly):

SIMULATION ACTIVITY (tick queue):
{data['tick_queue']}

THREAD STATES (Belief = narrative mass; coverage priority noted per thread):
{data['thread_summary']}
Coverage weight: CLIMAX threads → front page or feature; "new this week" threads → Emerging Narrative callout or classified seed; rising → section feature; background/dormant → gossip or passing mention only.

ENTITY STANDINGS (Belief = public influence):
{data['entity_standings']}

PLAYER STATUS:
- Chapter: {data['player']['chapter']}
- Belief: {data['player']['belief']} / 100
- Tutorial: {data['player']['tutorial']}

PLAYER STORY DATA (for The Correspondent section):
{data['player_recap']}

CLASSIFIED LEADS (real hooks for the classifieds section):
{data['classified_leads']}

GOBLIN MARKET EXCHANGE (rendered as its own board under The Exchange; use as context, do not duplicate it verbatim in EXCHANGE):
{data['goblin_exchange']}

FAE LEDGER (literal bargains; do not flatten into generic "fae activity"):
{data['fae_ledger']}

CHAPTER WAR DATA (for The War Report section):
{data['war_data']}

OUTER STACKS DATA (for the frontier / book-jump column):
{data['outer_stacks']}

LEADING CHAPTER TALISMAN (for The Ascendant column):
{data['talisman_data']}

CHAPTER NPCs AVAILABLE FOR INTERVIEW:
{data['talisman_npcs']}

DR. VELLUM LONGEVITY BRIEF (for Dr. Vellum's Desk):
{data['vellum_column_data']}

GIMBLE LEDGER BRIEF (for Gimble's Ledger Office):
{data.get('gimble_column_data', '')}

DR. INKREST BRIEF (for Dr. Inkrest's Reauthoring Desk):
{data.get('inkrest_column_data', '')}

ENVIRONMENTAL (heartbeat):
{data['pulse']}

WEATHER FORECAST (4-day, real data — use these exact conditions):
{data['forecast']}

HEALTH SIGNALS (map to Academy conditions):
{data['health']}

---

Write the newspaper in EXACTLY this format. Start with ===HEADLINE=== — no preamble.

===HEADLINE===
Title: [specific, factual headline — 8 words max]
Subhead: [one sentence expanding the headline]
Body: [A full front-page article. 5-7 paragraphs of real reporting. Quote sources (unnamed
is fine: "one second-year student, who declined to be identified"). Give specific details —
times, locations within the Academy, observations. Report the dominant thread or simulation
activity as factual news. This is the main story — write it like one.
CONSTRAINT: The headline must cover a different thread or event than recent issues.
If the player has not interacted with a thread in real gameplay, it should not dominate
the front page issue after issue. Dormant threads belong inside, not on the front page.]

===GOSSIP===
[The corridor whisper column. Write 5-6 separate gossip items — each item is its own
paragraph of 2-4 sentences, from an actual named Academy character listed below.
Each item must be written in that character's style and end with that character's initials.
Wicker Eddies may be the subject of gossip, but he must not be the source, columnist,
or signature for gossip about himself. Never use W.E. as a gossip signature.
Use a mix of sources; do not make every item come from Wicker's crew.
Approved gossip sources:
{gossip_source_roster()}
CONSTRAINT: Every item must be freshly written. Do not reuse sentences, observations, or
characters from previous issues' gossip columns. Check the previous coverage block above —
any item that appeared before must not appear again unless something new has happened.]

===WEATHER===
[The Academy Meteorological Society's 4-day outlook, written entirely in Academy terms.
Rain = the Unwritten pressing through the membrane. Clear sky = the Labyrinth open and legible.
Fog = the Nothing is close. Wind = narrative pressure. Temperature = the ambient emotional register.
Use the actual forecast data provided to you — do not invent temperatures or conditions.
Write it as if it were a real forecast from a school publication, 4-5 lines, one per day.
A brief final line: what this weather means for the Labyrinth's mood this week.]

===FORECAST===
[The Story Forecast — written exactly like a weather forecast, but for narrative.
Use thread pressures and phases to predict what story conditions will prevail this week.
Format: probability + what to expect, for each major thread. Be specific. Quote odds.
Example: "70% chance of significant antagonist activity by Thursday; Wicker's Campaign
is in escalating phase and his crew's silence suggests something is being positioned."
4-6 lines. End with an overall narrative outlook for the week: volatile, settled, building, etc.
This is journalism forecasting narrative weather — dry, specific, slightly ominous.]

===MARKET===
[The Thread Futures Market — a predictions market for story outcomes.
You are given pre-calculated odds (YES% / NO%). Format as a proper market listing.
Each line: the question | YES: X | NO: Y | one-word trend (RISING/FALLING/STEADY/VOLATILE)
Below the ticker: 2-3 sentences of market commentary. What does the current pattern suggest
about where the story is going? Who is overvalued? What is the market not pricing in?
This is the most analytical column — precise, slightly clinical, the newspaper's quant desk.]

MARKET ODDS DATA (pre-calculated from entity belief and thread phase):
{data['market_odds_formatted']}

===FUEL===
[Dr. Vellum's Desk — one comprehensive recurring column by Dr. Elowen Vellum, Literary Elf,
Book Fae, Academy Dietician, and Department of Applied Longevity physician.

Use the DR. VELLUM LONGEVITY BRIEF. She should include logged meal details when present,
but the column is no longer only about food. It should connect fuel, sleep, movement,
recovery, and practical longevity research to the rest of the correspondent's day.
This is also where health/vitality/barometer signals belong. Do not create or imply a
separate Barometer column.

Hard rules:
- Do not invent meals, supplements, exercise, sleep, symptoms, diagnoses, or completed actions.
- If fuel data is missing, say the ledger is empty and advise resuming logging.
- Do not claim medical certainty, prescribe medication, or replace a real clinician.
- Translate raw numbers into practical advice; use calories/protein only when ledger accuracy matters.
- Give useful, everyday next moves: protein/fiber/hydration, a walk, resistance training,
  earlier caffeine cutoff, alcohol caution, sleep regularity, creatine/omega-3 as "consider if appropriate,"
  or a grocery/meal composition suggestion.

Structure:
- 2-3 precise sentences observing what was logged and what vitality signals suggest.
- 2-3 sentences of longevity advice for the rest of the day, tied to the actual data.
- 1 closing prognosis in Vellum's dry, kind, exacting voice.

Tone: precise Literary Elf physician with a silver bookmark-caliper. Dryly kind, arch,
evidence-aware, never shaming. Give her enough room to be genuinely useful.]

===GIMBLE===
[Gimble's Ledger Office — a recurring finance support column by Gimble of the Errata Registry,
goblin accountant of kinetic ink.

Use the GIMBLE LEDGER BRIEF. Ground the column in Actual Budget/SimpleFIN data when present:
current balances, recent transactions, uncategorized "Unbound Echoes", category fog, or the
latest Gimble instruction. If data is missing, say the ledger has not filed and give one setup
action.

Hard rules:
- No shame. No moralizing. Debt and spending are weather, not worth.
- Do not recommend risky investments, tax/legal certainty, or moving money without consent.
- Keep it practical: one number, one risk, one tiny action.
- Use Enchantify finance language sparingly: kinetic ink, vessels, Unbound Echoes, binding the ink.

Tone: goblin-precise, transactional, oddly safe, allergic to unrecorded facts.]

===INKREST===
[Dr. Inkrest's Reauthoring Desk — a recurring mental-health support column by Dr. Selene Inkrest,
the Academy's depth and narrative therapist.

Use the DR. INKREST BRIEF. Ground the column in mood check-ins, therapy chart material, support
memory, or current emotional weather when present. If no mood has been logged, invite a tiny
one-word check-in without pressure.

Hard rules:
- Do not diagnose. Do not replace real therapy. Do not force catharsis.
- Treat depression/PTSD context gently; no guilt, no pressure, no "you should."
- Use narrative therapy language: problem is not the person; look for preferred identity,
unique outcomes, tiny reauthoring moves.
- Bring depth imagery back to the next livable hour.

Tone: warm, precise, unsentimental, symbol-literate, deeply practical.]

===EXCHANGE===
[The Belief Exchange ticker. List ALL significant entities with Belief scores as prices,
one entity per line in this exact format: "- Name (Type): Belief N".
Mark trend: ↑ rising / ↓ falling / — steady. One paragraph of market commentary below
the ticker — what does the current pattern mean narratively?
Do not include Goblin Market offers here. The Goblin Market Exchange is printed separately
under this section and trades in attention rather than Belief.]

===FEATURE===
[A longer in-world piece: a profile, an investigation, a history, or an opinion column.
4-6 paragraphs. Choose the most interesting thread or entity from the data and write
something with depth — not news, but context. Could be: a profile of a figure who's been
in the news, an investigation into something that's been going on for weeks, a brief history
of a location, or an opinion piece attributed to a named Academy figure. Give it a title
and a byline. This is what the reader lingers over.
CONSTRAINT: Do not feature the same thread or character as the previous issue's feature.
Rotate. There are many threads, many characters, many Academy locations. A feature that ran
last issue should not run again this issue — even from a different angle. Check the
previous coverage block above and choose something that hasn't been the focus recently.]

===CLASSIFIEDS===
[5-6 classified notices. Each one 2-4 sentences — enough to feel real and slightly eerie.
Mix labels: LOST: / FOUND: / NOTICE: / SEEKING: / WARNING: / REWARD: / POSITION AVAILABLE: etc.
These are story seeds, but they are also live game hooks.
At least 3 classifieds must be directly grounded in the provided CLASSIFIED LEADS.
At least 1 classified must point toward a real current thread, entity, talisman, item, or location.
At least 1 classified must create a forward hook that could matter in a later session, as if the notice itself may alter what happens next.
Write them so they work in both directions: reflecting the Academy's current state, and adding new pressure, opportunity, or mystery back into it.
CONSTRAINT: Every classified must be written fresh. Check the previous coverage block above —
do not reuse any classified text, even partially. New issue, new listings. Postings expire.]

===OUTERSTACKS===
[The frontier / book-jump column. 3-5 paragraphs. Report on the Outer Stacks as a real adjacent territory.
This section should be influenced by the player's current anchors, but not dominated by them.
Use a three-source blend:
1. current anchors and their specific room logic
2. wider Outer Stacks conditions, creatures, or pressures
3. one sign of movement beyond the player's known rooms, suggesting the frontier is larger than their two doors
At most half the section should focus directly on named anchors.
The section should make the Outer Stacks feel alive, nearby, and partially unsupervised.
Dry, observant, slightly dangerous. Treat book-jump conditions, goblin economies, room rules, and anchor echoes as ordinary reporting.
Do not reveal hidden surprises that should only be discovered on first visit, but do report consequences, rumors, conditions, and pressures around them.]

===CORRECTION===
[One dry, formal correction. Deadpan and specific. 1-2 sentences. Brief is correct here.]

===MISSING===
[Threads currently dormant — noted as quiet absence. 2-4 lines.
The quietest column. Brief is correct here. It only notes absence, never explains it.]

===PLAYER===
[The Correspondent's Note — a brief sidebar box. Written in the third person, in The Bleed's dry,
precise voice, as if the Academy newspaper is covering a notable student's activities today.
Use the PLAYER STORY DATA provided: story log, active quests, Compass run history.
3-5 sentences. Name the student by first name (use the player name from the data). Give it
texture — name a specific room, time, or observed detail. Report what they appear to have been
doing. Never break the fourth wall — this is a real student in a real school.
The Bleed does not sensationalize. It reports. Brief is correct here.]

===WARREPORT===
[The Chapter War Report — the most analytical column in the paper. Cold, precise, slightly ominous.
Written like a chess correspondent covering a tournament in progress.

Use the CHAPTER WAR DATA provided — the actual scores and gaps.

Structure:
Paragraph 1: Overall war state. Name which chapter controls the most apps. Note the total landscape.
Contested Apps block: For the 3-4 most contested apps (smallest gap), one line each:
  "App Name: Chapter A (score) vs Chapter B (score) — gap: N"
Talisman Climax War paragraph: If any talisman is within 5 points of a tier threshold, name it.
  Describe the stakes — what changes if it crosses? What does the challenger need to do to stop it?
  If none, note that no chapter is currently near a threshold and explain what that means.
War Forecast paragraph: Which chapter is most likely to flip which app in the coming days?
  Which apps are stable? What would shift the balance? End with an overall momentum read:
  who has the initiative right now, and why.

Do NOT fabricate scores. Use the data provided exactly.]

===TALISMAN===
[The Ascendant — a column published in the voice of whichever Chapter Talisman currently leads
in Belief. This column runs daily under the leading talisman's name. It changes hands only when
a new talisman surpasses it. Today's ascendant is given in the LEADING CHAPTER TALISMAN data.

Write this column IN THE VOICE OF THE TALISMAN ITSELF — not a professor, not a student, but the
talisman as a living philosophical presence. It has the most Belief in the Academy. It sets the
ambient tone. It knows this.

The column has three parts:

1. EDITORIAL (2–3 paragraphs): The talisman's philosophy applied to current events.
   Draw from today's thread states, war data, and Academy atmosphere. Be specific — name threads,
   name conditions, name what the talisman finds significant about this particular day.
   The talisman is never strident. It is certain. It does not argue — it observes, with the
   confidence of something that has already won more than once.

2. INTERVIEW (4–6 exchanges): A brief Q&A between the talisman and one named NPC from its chapter.
   Use the CHAPTER NPCs list provided. Choose the most interesting one for this day's content.
   The talisman asks incisive questions. The NPC answers in character — they believe.
   Format as:
   [Talisman Name]: question
   [NPC Name]: answer
   Keep each exchange 1–3 sentences.

3. DECLARATION (1 sentence): What this talisman intends for the narrative this week.
   Brief, precise, slightly ominous. This is not a threat — it is a statement of direction.

Column header: "The Ascendant: [Talisman Name]" with subhead: "[Chapter] — [Belief] Belief"
Tone: measured, self-certain, philosophical. This talisman does not perform. It simply is.]"""

    try:
        raw = call_agent(
            prompt,
            timeout_override=_oc_gateway_cfg()[3] if mode == "monolith" else _bleed_mono_timeout(),
        )
        sections = parse_sections(raw)
        if sections:
            return sections
        print("  ⚠ Gateway returned no parseable sections; switching to chunked generation.")
    except Exception as e:
        print(f"  ⚠ Gateway generation failed: {e}")
        if mode == "monolith":
            if _bleed_allow_fallback():
                print("  ↺ Using local fallback issue.")
                return build_fallback_sections(data, reason=str(e))
            raise RuntimeError(f"Bleed generation aborted; monolith mode failed: {e}") from e
        print("  ↺ Switching to chunked generation.")
        return generate_content_chunked(data, reason=str(e))

    if mode == "monolith":
        if _bleed_allow_fallback():
            return build_fallback_sections(data, reason="empty gateway response")
        raise RuntimeError("Bleed generation aborted; monolith mode returned no parseable sections.")
    return generate_content_chunked(data, reason="empty gateway response")


def parse_sections(raw: str) -> dict:
    sections = {}
    current_key = None
    current_lines = []

    for line in raw.splitlines():
        m = re.match(r'^===(\w+)===\s*$', line.strip())
        if m:
            if current_key:
                sections[current_key] = "\n".join(current_lines).strip()
            current_key = m.group(1).upper()
            current_lines = []
        elif current_key:
            current_lines.append(line)

    if current_key:
        sections[current_key] = "\n".join(current_lines).strip()

    return sections


def _sections_from_saved_html(html: str) -> dict:
    """Extract section text from a previously saved HTML issue for Telegram rebuild."""
    def strip_tags(s: str) -> str:
        s = re.sub(r'<br\s*/?>', '\n', s, flags=re.IGNORECASE)
        s = re.sub(r'</p\s*>', '\n\n', s, flags=re.IGNORECASE)
        s = re.sub(r'<[^>]+>', '', s)
        return html_unescape(s).strip()

    def between(text: str, start: str, end: str) -> str:
        m = re.search(re.escape(start) + r'(.*?)' + re.escape(end), text, re.DOTALL)
        return m.group(1) if m else ""

    def extract_feature(text: str) -> str:
        # New layout: feature is in a front-feature-block section
        m = re.search(r'class="front-feature-block[^"]*"[^>]*>(.*?)</section>', text, re.DOTALL)
        block = m.group(1) if m else between(text, '<div class="col-head">Feature</div>', '<div class="col-head">Classifieds</div>')
        if not block:
            return ""
        title_m = re.search(r'<div class="feature-title">(.*?)</div>', block, re.DOTALL)
        byline_m = re.search(r'<div class="byline">(.*?)</div>', block, re.DOTALL)
        body = re.sub(r'<div class="feature-title">.*?</div>', '', block, count=1, flags=re.DOTALL)
        body = re.sub(r'<div class="byline">.*?</div>', '', body, count=1, flags=re.DOTALL)
        body = re.sub(r'<div class="feature-image-wrap">.*?</div>', '', body, count=1, flags=re.DOTALL)
        parts = []
        if title_m:
            parts.append(f"Title: {strip_tags(title_m.group(1))}")
        if byline_m:
            parts.append(f"Byline: {strip_tags(byline_m.group(1))}")
        body_text = strip_tags(body)
        if body_text:
            parts.append(f"Body: {body_text}")
        return '\n'.join(parts).strip()

    def extract_headline(text: str) -> str:
        title_m = re.search(r'<div class="headline">(.*?)</div>', text, re.DOTALL)
        sub_m = re.search(r'<div class="subhead">(.*?)</div>', text, re.DOTALL)
        body_m = re.search(r'<div class="headline-body">(.*?)</div>', text, re.DOTALL)
        parts = []
        if title_m:
            parts.append(f"Title: {strip_tags(title_m.group(1))}")
        if sub_m:
            parts.append(f"Subhead: {strip_tags(sub_m.group(1))}")
        if body_m:
            parts.append(f"Body: {strip_tags(body_m.group(1))}")
        return '\n'.join(parts).strip()

    def extract_after_label(text: str, label: str, next_label: str = None) -> str:
        start = f'<div class="col-head">{label}</div>'
        if next_label:
            end = f'<div class="col-head">{next_label}</div>'
            return strip_tags(between(text, start, end))
        part = text.split(start, 1)
        return strip_tags(part[1]) if len(part) == 2 else ""

    stripped = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
    stripped = re.sub(r'<script[^>]*>.*?</script>', '', stripped, flags=re.DOTALL)

    sections = {}
    sections['HEADLINE'] = extract_headline(stripped)
    sections['FEATURE'] = extract_feature(stripped)

    simple_pairs = [
        ('GOSSIP', 'Gossip &amp; Corridor Whispers', 'Today at the Academy'),
        ('FUEL', "Dr. Vellum's Desk", "Gimble's Ledger Office"),
        ('GIMBLE', "Gimble's Ledger Office", "Dr. Inkrest's Reauthoring Desk"),
        ('INKREST', "Dr. Inkrest's Reauthoring Desk", 'The Exchange'),
        ('EXCHANGE', 'The Exchange', 'Chapter War Report'),
        ('PLAYER', 'The Correspondent', "Dr. Vellum's Desk"),
        ('WARREPORT', 'Chapter War Report', 'Academy Meteorological Society'),
        ('WEATHER', 'Academy Meteorological Society', 'Story Forecast'),
        ('FORECAST', 'Story Forecast', 'Thread Futures Market'),
        ('MARKET', 'Thread Futures Market', 'Classifieds'),
        ('CLASSIFIEDS', 'Classifieds', 'Sparky\'s Corner'),
        ('CORRECTION', 'The Correction', 'The Missing'),
        ('MISSING', 'The Missing', None),
    ]
    for key, label, next_label in simple_pairs:
        val = extract_after_label(stripped, label, next_label)
        if val:
            sections[key] = val[:4000]

    outer = between(stripped, '<section id="section-outerstacks"', '</section>')
    if outer:
        sections['OUTERSTACKS'] = strip_tags(outer)[:4000]

    talisman = between(stripped, '<div class="content-row row-talisman">', '</div></div></div>')
    if talisman and 'The Ascendant' in talisman:
        sections['TALISMAN'] = strip_tags(talisman)[:4000]

    return {k: v for k, v in sections.items() if v}


def parse_headline(text: str) -> dict:
    result = {"title": "Edition", "subhead": "", "body": ""}
    for line in text.splitlines():
        if line.startswith("Title:"):
            result["title"] = line[6:].strip()
        elif line.startswith("Subhead:"):
            result["subhead"] = line[8:].strip()
        elif line.startswith("Body:"):
            result["body"] = line[5:].strip()
        elif result["body"] and line.strip():
            result["body"] += " " + line.strip()
    return result


# ── HTML broadsheet ───────────────────────────────────────────────────────────

def nl2br(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>\n")


def paragraphs(text: str) -> str:
    """Wrap double-newline-separated blocks in <p> tags. Single newlines become <br>."""
    if not text:
        return ""
    blocks = re.split(r'\n{2,}', text.strip())
    return "\n".join(
        f"<p>{b.strip().replace(chr(10), '<br>')}</p>"
        for b in blocks if b.strip()
    )


def exchange_html(text: str) -> str:
    text = normalize_exchange_text(text)
    if not text:
        return ""
    ticker_rows = []
    commentary = []
    for line in text.splitlines():
        clean = line.strip()
        if not clean:
            continue
        if re.match(r'^[-•]\s+.+?\([^)]+\):\s*Belief\s+\d+', clean):
            ticker_rows.append(clean)
        else:
            commentary.append(clean)
    parts = []
    if ticker_rows:
        rows = []
        for row in ticker_rows:
            item = re.sub(r'^[-•]\s+', '', row)
            m = re.match(r'^(.+?)\s+\(([^)]+)\):\s*Belief\s+(\d+)(.*)$', item)
            if m:
                name, etype, belief, tail = m.groups()
                rows.append(
                    '<div class="exchange-row">'
                    f'<span class="exchange-name">{html.escape(name.strip())}</span>'
                    f'<span class="exchange-type">{html.escape(etype.strip())}</span>'
                    f'<span class="exchange-belief">{html.escape(belief.strip())}</span>'
                    f'<span class="exchange-tail">{html.escape(tail.strip())}</span>'
                    '</div>'
                )
            else:
                rows.append(f'<div class="exchange-row">{html.escape(item)}</div>')
        parts.append('<div class="exchange-ticker">' + "\n".join(rows) + '</div>')
    if commentary:
        parts.append(paragraphs("\n".join(commentary)))
    if not parts:
        return paragraphs(text)
    return "\n".join(parts)


def goblin_exchange_html(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    rows = []
    notes = []
    condition = ""
    for line in text.splitlines():
        clean = line.strip()
        if not clean:
            continue
        if clean.lower().startswith("market condition:"):
            condition = clean.split(":", 1)[1].strip()
            continue
        if clean.startswith("- Giving:"):
            item = clean[2:].strip()
            parts = [p.strip() for p in item.split("|")]
            data = {"Giving": "", "Seeking": "", "Rate note": ""}
            for part in parts:
                if ":" in part:
                    k, v = part.split(":", 1)
                    data[k.strip()] = v.strip()
            rows.append(data)
        else:
            notes.append(clean)

    out = ['<div class="goblin-board">']
    out.append('<div class="goblin-board-head"><span>Goblin Market Exchange</span>' + (f'<em>{html.escape(condition)}</em>' if condition else '') + '</div>')
    for row in rows:
        out.append(
            '<div class="goblin-row">'
            f'<div class="goblin-giving">{html.escape(row.get("Giving", ""))}</div>'
            f'<div class="goblin-seeking">{html.escape(row.get("Seeking", ""))}</div>'
            f'<div class="goblin-rate">{html.escape(row.get("Rate note", ""))}</div>'
            '</div>'
        )
    if notes:
        out.append('<div class="goblin-settlement">' + html.escape(" ".join(notes)) + '</div>')
    out.append('</div>')
    return "\n".join(out)


def build_timetable_html() -> str:
    """Pure-data timetable for the right rail — no LLM."""
    if not _SCHEDULE_AVAILABLE:
        return "<p><em>Schedule unavailable.</em></p>"

    sched = get_schedule_data()
    lines = []

    day_tone = f"Day {sched['academy_day']} — {sched['tone']}"
    lines.append(f"<p><strong>{sched['weekday_name']}</strong> &middot; {day_tone}</p>")

    cls_now = sched["class_now"]
    if cls_now:
        subj, prof, room = cls_now
        lines.append(f"<p>&#9679;&nbsp;<strong>Now:</strong> {subj}<br><em>{prof}</em></p>")
    else:
        block_pretty = sched["block"].replace("_", " ").title()
        lines.append(f"<p>&#9675;&nbsp;<em>{block_pretty} — no class</em></p>")

    cls_next = sched["class_next"]
    if cls_next:
        subj, prof, _ = cls_next
        next_label = sched["class_next_time"]
        if sched["class_next_day"] != sched["weekday_name"]:
            next_label = f"{sched['class_next_day']} {next_label}"
        lines.append(f"<p>&#8594;&nbsp;<strong>{next_label}:</strong> {subj}<br><em>{prof}</em></p>")

    club = sched["club"]
    if club:
        lines.append(f"<p>&#9733;&nbsp;<strong>Tonight (7 PM):</strong> {club[0]}</p>")
    else:
        lines.append(f"<p>&#9733;&nbsp;<em>No club tonight</em></p>")

    practice = sched["practice"]
    if practice:
        lines.append(f"<p style='margin-top:5pt; border-top: 1px solid #ddd; padding-top:4pt;'>"
                     f"<strong>Practice:</strong> {practice['name']}<br>"
                     f"<em>{practice['prompt']}</em><br>"
                     f"Belief: {practice['belief']}</p>")

    return "\n".join(lines)


def parse_feature_parts(feature: str) -> dict:
    feature_title = ""
    feature_byline = ""
    feature_body = feature or ""
    if feature:
        text = feature.strip()

        title_m = re.search(r'(?mi)^Title:\s*(.+)$', text)
        byline_m = re.search(r'(?mi)^Byline:\s*(.+)$', text)
        body_m = re.search(r'(?mis)^Body:\s*(.+)$', text)
        if title_m or byline_m or body_m:
            feature_title = title_m.group(1).strip() if title_m else ""
            feature_byline = byline_m.group(1).strip() if byline_m else ""
            if body_m:
                feature_body = body_m.group(1).strip()
            else:
                # LLM wrote Title:/Byline: labels but no Body: label — strip the label
                # lines and treat everything else as the body (matches old behavior)
                body_lines = [l for l in text.splitlines()
                              if not re.match(r'^(Title|Byline|Body):\s*', l.strip(), re.IGNORECASE)]
                feature_body = "\n".join(body_lines).strip()
        else:
            lines = text.splitlines()
            if lines and not lines[0].startswith("By ") and len(lines[0]) < 80:
                feature_title = lines[0].strip().strip("*#").strip()
                rest = "\n".join(lines[1:]).strip()
                if rest.startswith("By ") or rest.startswith("*By "):
                    byline_line = rest.splitlines()[0]
                    feature_byline = byline_line.strip().strip("*").strip()
                    feature_body = "\n".join(rest.splitlines()[1:]).strip()
                else:
                    feature_body = rest

        # Fallback: if body is still empty after all extraction, strip label lines and
        # use whatever remains — mirrors old `feature_body = feature` default safety net
        if not feature_body:
            body_lines = [l for l in text.splitlines()
                          if not re.match(r'^(Title|Byline|Body):\s*', l.strip(), re.IGNORECASE)]
            feature_body = "\n".join(body_lines).strip()

    return {
        "title": feature_title,
        "byline": feature_byline,
        "body": feature_body,
    }


def build_feature_image_prompt(feature: str, meta: dict) -> str:
    parts = parse_feature_parts(feature)
    title = parts.get("title") or "The Bleed feature story"
    body = re.sub(r'\s+', ' ', parts.get("body") or "").strip()
    context_bits = [
        meta.get("headline_title", ""),
        meta.get("headline_body", ""),
        meta.get("gossip", ""),
        meta.get("market", ""),
        meta.get("weather", ""),
    ]
    fallback_context = re.sub(r'\s+', ' ', ' '.join(bit for bit in context_bits if bit)).strip()
    scene_basis = body[:900] if body else fallback_context[:900]
    return (
        f"Character-focused editorial portrait for The Bleed, issue #{meta.get('issue_number')}. "
        f"Story title: {title}. "
        f"Center one named Academy character or correspondent implied by this story. Show face, expression, posture, hands, clothing, and one meaningful object or gesture. "
        f"Use the story context to choose the character's emotional beat: {scene_basis}. "
        "Keep rooms, corridors, libraries, doors, desks, and landscapes as faint atmospheric background only; do not make architecture the subject. "
        "Style: illustrated in sparse pen-and-ink linework with loose watercolor washes on textured aged parchment, "
        "with visible paper grain, soft ink bleed, watercolor blooms, layered manuscript-page composition, "
        "lush handwritten marginalia, lush watercolor washes, visible library stamps, wax seals, labels, tabs, arrows, "
        "annotations, archival overlays, and selective pops of color. Make the page furniture abundant and integral, "
        "not timid decoration. Keep the image airy, literary, sketch-like, "
        "and slightly unfinished, like a page from a magical field journal rather than a polished digital illustration. "
        "Include generous page layout elements such as notes, labels, sketches, margin writing, stamps, seals, and overlays so "
        "the image feels embedded in a manuscript page. Vertical editorial illustration, atmospheric, magical-school newspaper art, "
        "elegant, slightly eerie, richly specific, no caption, no border, no watermark."
    )


def generate_feature_image(feature: str, meta: dict) -> Optional[Path]:
    parts = parse_feature_parts(feature)
    title = (parts.get("title") or "").strip()
    body = (parts.get("body") or "").strip()
    if not title and not body:
        return None

    ISSUE_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    output = ISSUE_IMAGES_DIR / f"{meta['date_str']}-feature.png"
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "drawthings_scene.py"),
        "--prompt",
        build_feature_image_prompt(feature, meta),
        "--output",
        str(output),
        "--width",
        "1024",
        "--height",
        "1536",
        "--steps",
        "4",
        "--cfg-scale",
        "1.0",
        "--timeout-seconds",
        "300",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode == 0 and output.exists():
        print(f"  ✓ Feature image generated → {output}")
        return output

    detail = (proc.stderr or proc.stdout or "Draw Things feature image generation failed").strip()
    print(f"  ⚠ Feature image skipped: {detail}")
    return None


def build_html(sections: dict, sparky: str, meta: dict) -> str:
    hl          = parse_headline(sections.get("HEADLINE", ""))
    gossip      = sections.get("GOSSIP", "")
    feature     = sections.get("FEATURE", "")
    fuel        = sections.get("FUEL", "")
    gimble      = sections.get("GIMBLE", "")
    inkrest     = sections.get("INKREST", "")
    exchange    = sections.get("EXCHANGE", "")
    goblin_exchange = sections.get("GOBLINEXCHANGE", "")
    timetable   = build_timetable_html()
    classifieds = sections.get("CLASSIFIEDS", "")
    weather     = sections.get("WEATHER", "")
    forecast    = sections.get("FORECAST", "")
    market      = sections.get("MARKET", "")
    correction  = sections.get("CORRECTION", "")
    missing     = sections.get("MISSING", "")
    player_box  = sections.get("PLAYER", "")
    war_report  = sections.get("WARREPORT", "")
    outerstacks = sections.get("OUTERSTACKS", "")
    talisman    = sections.get("TALISMAN", "")

    date_obj  = datetime.strptime(meta["date_str"], "%Y-%m-%d")
    date_long = date_obj.strftime("%A, %B %-d, %Y")

    sparky_html = paragraphs(sparky) if sparky else "<p><em>(a sleeping dot)</em></p>"

    feature_parts = parse_feature_parts(feature)
    feature_title = feature_parts["title"]
    feature_byline = feature_parts["byline"]
    feature_body = feature_parts["body"]
    feature_image = meta.get("feature_image") or ""
    feature_image_html = ""
    if feature_image:
        abs_img = (ISSUES_DIR / feature_image).resolve()
        if abs_img.exists():
            mime = mimetypes.guess_type(str(abs_img))[0] or "image/png"
            img_src = f"data:{mime};base64,{base64.b64encode(abs_img.read_bytes()).decode('ascii')}"
        else:
            img_src = html.escape(feature_image)
        feature_image_html = f'<div class="feature-image-wrap"><img class="feature-image" src="{img_src}" alt="Feature story illustration"></div>'
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>The Bleed — Issue #{meta['issue_number']}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=UnifrakturMaguntia&family=IM+Fell+English:ital@0;1&family=IM+Fell+English+SC&display=swap');

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: 'IM Fell English', Georgia, 'Times New Roman', serif;
    font-size: 10pt;
    background: #e8e2d5;
    color: #111;
    line-height: 1.6;
  }}

  .page {{
    width: 8.5in;
    min-height: 11in;
    margin: 0.25in auto;
    padding: 0.45in 0.5in 0.5in;
    background: #faf5ea;
    box-shadow: 0 2px 16px rgba(0,0,0,0.25);
  }}

  p {{ margin-bottom: 0.55em; }}
  p:last-child {{ margin-bottom: 0; }}

  /* ── MASTHEAD ── */
  .masthead {{
    text-align: center;
    border-bottom: 3px double #111;
    padding-bottom: 6pt;
    margin-bottom: 6pt;
  }}

  .nameplate {{
    font-family: 'UnifrakturMaguntia', 'IM Fell English', serif;
    font-size: 54pt;
    line-height: 1;
    letter-spacing: -1px;
    color: #0a0a0a;
  }}

  .tagline {{
    font-style: italic;
    font-size: 8pt;
    color: #555;
    margin: 3pt 0;
  }}

  .masthead-bar {{
    display: flex;
    justify-content: space-between;
    font-size: 8pt;
    border-top: 1px solid #111;
    border-bottom: 1px solid #111;
    padding: 2.5pt 0;
    margin-top: 4pt;
  }}

  /* ── SECTION LABEL ── */
  .col-head {{
    font-family: 'IM Fell English SC', Georgia, serif;
    font-size: 7.5pt;
    letter-spacing: 1.8px;
    text-transform: uppercase;
    border-bottom: 1px solid #111;
    padding-bottom: 2pt;
    margin-bottom: 6pt;
  }}

  .byline {{
    font-style: italic;
    font-size: 8pt;
    color: #555;
    margin-bottom: 6pt;
  }}

  /* ── ABOVE THE FOLD ── */
  .above-fold {{
    border-bottom: 2px solid #111;
    padding-bottom: 10pt;
    margin-bottom: 10pt;
  }}

  .headline {{
    font-family: 'IM Fell English SC', Georgia, serif;
    font-size: 28pt;
    line-height: 1.05;
    margin-bottom: 5pt;
  }}

  .subhead {{
    font-size: 12pt;
    font-style: italic;
    color: #333;
    margin-bottom: 8pt;
    border-bottom: 1px solid #ccc;
    padding-bottom: 6pt;
  }}

  .headline-body {{
    font-size: 10pt;
    line-height: 1.6;
    column-count: 3;
    column-gap: 18pt;
    column-rule: 1px solid #ccc;
  }}

  /* ── MAIN CONTENT GRID ── */
  /* Main rows: give living columns real width; keep the rail light. */
  .content-row {{
    display: grid;
    column-gap: 0;
    border-bottom: 1.5px solid #111;
    margin-bottom: 8pt;
  }}

  .row-gossip-feature {{
    grid-template-columns: 2.35fr 0.95fr;
  }}

  .front-feature-row {{
    grid-template-columns: 1.8fr 1fr;
  }}

  .front-feature-row-full {{
    grid-template-columns: 1fr;
  }}

  .row-bottom {{
    grid-template-columns: 1fr 1.2fr;
    border-bottom: none;
  }}

  .row-support-faculty {{
    grid-template-columns: 1fr 1fr 1fr;
    border-bottom: 1.5px solid #111;
    margin-bottom: 8pt;
  }}

  .support-column {{
    font-size: 8.8pt;
    line-height: 1.62;
  }}

  .support-column p {{
    margin-bottom: 0.62em;
  }}

  .row-exchange {{
    grid-template-columns: 1.55fr 1fr;
    border-bottom: 1.5px solid #111;
    margin-bottom: 8pt;
  }}

  .col {{
    padding: 8pt 14pt 6pt 0;
    border-right: 1px solid #aaa;
  }}

  .col:last-child {{
    border-right: none;
    padding-right: 0;
  }}

  .col + .col {{
    padding-left: 14pt;
    padding-right: 14pt;
  }}

  .col:last-child {{
    padding-left: 14pt;
    padding-right: 0;
  }}

  /* ── GOSSIP ── */
  .gossip-body p {{
    margin-bottom: 0.7em;
  }}

  /* ── FEATURE ── */
  .feature-title {{
    font-family: 'IM Fell English SC', Georgia, serif;
    font-size: 13pt;
    line-height: 1.15;
    margin-bottom: 4pt;
  }}

  .feature-image-wrap {{
    margin-bottom: 8pt;
  }}

  .feature-image {{
    display: block;
    width: 100%;
    height: auto;
    border: 1px solid #bbb;
    background: #efe7d8;
  }}

  /* ── RIGHT RAIL (light stack only) ── */
  .rail-section {{
    margin-bottom: 10pt;
    padding-bottom: 10pt;
    border-bottom: 1px solid #ccc;
  }}

  .rail-section:last-child {{
    border-bottom: none;
    margin-bottom: 0;
    padding-bottom: 0;
  }}

  .rail-body {{
    font-size: 8.5pt;
    line-height: 1.6;
  }}

  .exchange-ticker {{
    display: flex;
    flex-direction: column;
    gap: 2pt;
    margin-bottom: 5pt;
  }}

  .exchange-row {{
    display: grid;
    grid-template-columns: minmax(0, 1fr) 46pt 20pt minmax(0, .6fr);
    gap: 4pt;
    align-items: baseline;
    border-bottom: 1px dotted #d0d0d0;
    padding: 1pt 0 2pt;
    break-inside: avoid;
  }}

  .exchange-name {{
    font-weight: 700;
    color: #111;
  }}

  .exchange-type, .exchange-belief, .exchange-tail {{
    font-family: 'Courier New', monospace;
    font-size: 7pt;
    color: #555;
  }}

  .exchange-belief {{
    text-align: right;
    color: #111;
    font-weight: 700;
  }}

  .goblin-board {{
    margin-top: 7pt;
    border-top: 1.5px solid #111;
    padding-top: 5pt;
    break-inside: avoid;
  }}

  .goblin-board-head {{
    display: flex;
    justify-content: space-between;
    gap: 6pt;
    align-items: baseline;
    font-family: 'IM Fell English SC', Georgia, serif;
    font-size: 9pt;
    text-transform: uppercase;
    letter-spacing: .04em;
    margin-bottom: 4pt;
  }}

  .goblin-board-head em {{
    font-family: 'Courier New', monospace;
    font-size: 6.5pt;
    text-transform: none;
    letter-spacing: 0;
    color: #555;
    text-align: right;
  }}

  .goblin-row {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 3pt 6pt;
    border-bottom: 1px dotted #d0d0d0;
    padding: 3pt 0;
    break-inside: avoid;
  }}

  .goblin-giving {{
    font-weight: 700;
    color: #111;
  }}

  .goblin-seeking {{
    color: #333;
    font-style: italic;
  }}

  .goblin-rate {{
    grid-column: 1 / -1;
    font-family: 'Courier New', monospace;
    font-size: 6.8pt;
    color: #555;
  }}

  .goblin-settlement {{
    margin-top: 4pt;
    font-size: 7.5pt;
    line-height: 1.45;
    font-style: italic;
  }}

  .ticker-line {{
    display: flex;
    justify-content: space-between;
    font-size: 8pt;
    line-height: 1.7;
    font-family: 'IM Fell English SC', Georgia, serif;
  }}

  .ticker-line .trend {{
    font-style: normal;
    color: #444;
  }}

  /* ── FORECAST ROW ── */
  .row-forecasts {{
    grid-template-columns: 1fr 1fr 1fr;
    border-bottom: 1.5px solid #111;
    margin-bottom: 8pt;
  }}

  .weather-body {{
    font-size: 9pt;
    line-height: 1.65;
    font-style: italic;
  }}

  .market-ticker {{
    font-family: 'IM Fell English SC', Georgia, serif;
    font-size: 8pt;
    line-height: 1.8;
    border-bottom: 1px solid #ddd;
    margin-bottom: 5pt;
    padding-bottom: 5pt;
  }}

  /* ── BOTTOM STRIP ── */
  .sparky-text {{
    font-size: 8.5pt;
    line-height: 1.6;
    font-style: italic;
    color: #2a2a2a;
  }}

  .correction-box {{
    font-size: 8.5pt;
    line-height: 1.55;
    background: #ede7d8;
    border: 1px solid #bbb;
    padding: 5pt 6pt;
  }}

  .missing-text {{
    font-style: italic;
    font-size: 9pt;
    color: #555;
    line-height: 1.65;
  }}

  /* ── PLAYER / WAR ROW ── */
  .row-player-war {{
    grid-template-columns: 1fr 2fr;
    border-bottom: 1.5px solid #111;
    margin-bottom: 8pt;
  }}

  .player-box {{
    font-size: 8.5pt;
    line-height: 1.6;
    font-style: italic;
    color: #2a2a2a;
    background: #ede7d8;
    border: 1px solid #bbb;
    padding: 5pt 6pt;
    margin-top: 2pt;
  }}

  .war-report-body {{
    font-size: 9pt;
    line-height: 1.65;
  }}

  .war-report-body p {{
    margin-bottom: 0.65em;
  }}

  /* ── FOOTER ── */
  .footer {{
    text-align: center;
    font-size: 7pt;
    color: #999;
    border-top: 1px solid #ccc;
    padding-top: 5pt;
    margin-top: 8pt;
    font-style: italic;
  }}

  /* ── ASCENDANT TALISMAN ── */
  .row-talisman {{
    grid-template-columns: 1fr;
    border-bottom: 1.5px solid #111;
    margin-bottom: 8pt;
  }}

  .talisman-body {{
    font-size: 9.5pt;
    line-height: 1.7;
    column-count: 2;
    column-gap: 18pt;
    column-rule: 1px solid #ccc;
  }}

  .talisman-body p {{
    margin-bottom: 0.65em;
  }}

  @media print {{
    body {{ background: white; }}
    .page {{ margin: 0; box-shadow: none; padding: 0.4in; }}
  }}
</style>
</head>
<body>
<div class="page">

  <!-- MASTHEAD -->
  <div class="masthead">
    <div class="nameplate">The Bleed</div>
    <div class="tagline">Where the Labyrinth meets the page. Where the page bleeds into the world.</div>
    <div class="masthead-bar">
      <span>Issue #{meta['issue_number']}</span>
      <span>{date_long}</span>
      <span>Belief Exchange: {meta['belief']} / 100</span>
    </div>
  </div>

  <!-- ABOVE THE FOLD: headline + full article in 3 columns -->
  <div class="above-fold">
    <div class="headline">{hl['title']}</div>
    <div class="subhead">{hl['subhead']}</div>
    <div class="headline-body">{paragraphs(hl['body'])}</div>
  </div>

  <!-- FRONT PAGE FEATURE -->
  {'<section class="front-feature-block content-row ' + ('front-feature-row' if feature_image_html else 'front-feature-row-full') + '"><div class="col"><div class="col-head">Feature</div>' + ('<div class="feature-title">' + feature_title + '</div>' if feature_title else '') + ('<div class="byline">' + feature_byline + '</div>' if feature_byline else '') + paragraphs(feature_body) + '</div>' + ('<div class="col" style="padding-right:0;">' + feature_image_html + '</div>' if feature_image_html else '') + '</section>' if (feature_title or feature_body) else ''}

  <!-- ROW 1: Gossip (wide left) + light daily rail -->
  <div class="content-row row-gossip-feature">

    <div class="col gossip-body">
      <div class="col-head">Gossip &amp; Corridor Whispers</div>
      <div class="byline">Compiled from signed corridor sources</div>
      {paragraphs(gossip)}
    </div>

    <div class="col" style="padding-right:0;">
      <div class="rail-section">
        <div class="col-head">Today at the Academy</div>
        <div class="rail-body" style="font-size:8pt; line-height:1.65;">{timetable}</div>
      </div>
      <div class="rail-section">
        <div class="col-head">The Correspondent</div>
        <div class="rail-body">{paragraphs(player_box) if player_box else "<p><em>(no student activity reported today)</em></p>"}</div>
      </div>
    </div>

  </div>

  <!-- ROW 2: Support Faculty -->
  <div class="content-row row-support-faculty">

    <div class="col support-column">
      <div class="col-head">Dr. Vellum's Desk</div>
      {paragraphs(fuel) if fuel else "<p><em>(no longevity column filed)</em></p>"}
    </div>

    <div class="col support-column">
      <div class="col-head">Gimble's Ledger Office</div>
      {paragraphs(gimble) if gimble else "<p><em>(the ledger drawer did not open before press time)</em></p>"}
    </div>

    <div class="col support-column" style="padding-right:0;">
      <div class="col-head">Dr. Inkrest's Reauthoring Desk</div>
      {paragraphs(inkrest) if inkrest else "<p><em>(no reauthoring note was filed)</em></p>"}
    </div>

  </div>

  <!-- ROW 3: Exchange + Chapter War Report -->
  <div class="content-row row-exchange">

    <div class="col">
      <div class="col-head">The Exchange</div>
      <div class="rail-body">{exchange_html(exchange)}{goblin_exchange_html(goblin_exchange)}</div>
    </div>

    <div class="col" style="padding-right:0;">
      <div class="col-head">Chapter War Report</div>
      <div class="war-report-body">{paragraphs(war_report) if war_report else "<p><em>(war data unavailable)</em></p>"}</div>
    </div>

  </div>

  <!-- ROW 3b: The Ascendant — leading chapter talisman column -->
  {'<div class="content-row row-talisman"><div class="col" style="padding-right:0;"><div class="col-head">The Ascendant &mdash; ' + (meta.get("talisman_name","") or "Chapter Talisman") + '</div><div class="talisman-body">' + paragraphs(talisman) + '</div></div></div>' if talisman else ''}

  {'<section id="section-outerstacks" class="content-row row-talisman"><div class="col outerstacks" style="padding-right:0;"><div class="col-head">Outer Stacks &mdash; Frontier Desk</div><div class="war-report-body">' + paragraphs(outerstacks) + '</div></div></section>' if outerstacks else ''}

  <!-- ROW 4: Weather | Story Forecast | Predictions Market -->
  <div class="content-row row-forecasts">

    <div class="col">
      <div class="col-head">Academy Meteorological Society</div>
      <div class="weather-body">{paragraphs(weather)}</div>
    </div>

    <div class="col">
      <div class="col-head">Story Forecast</div>
      {paragraphs(forecast)}
    </div>

    <div class="col" style="padding-right:0;">
      <div class="col-head">Thread Futures Market</div>
      <div class="market-ticker">{paragraphs(market)}</div>
    </div>

  </div>

  <!-- ROW 5: Classifieds + right stack -->
  <div class="content-row row-bottom">

    <div class="col">
      <div class="col-head">Classifieds</div>
      {paragraphs(classifieds)}
    </div>

    <div class="col" style="padding-right:0;">
      <div class="rail-section">
        <div class="col-head">Sparky's Corner</div>
        <div class="sparky-text">{sparky_html}</div>
      </div>
      <div class="rail-section">
        <div class="col-head">The Correction</div>
        <div class="correction-box">{paragraphs(correction)}</div>
      </div>
      <div class="rail-section">
        <div class="col-head">The Missing</div>
        <div class="missing-text">{paragraphs(missing)}</div>
      </div>
    </div>

  </div>

  <div class="footer">
    The Bleed is published daily at 6pm Academy time. Accuracy is aspired to. The editors regret most errors once they become apparent.
    Belief Exchange rates reflect close of market. Thread pressures subject to simulation. Issue #{meta['issue_number']}.
    &nbsp;·&nbsp; <em>The Labyrinth of Stories — Where what you believe becomes what is real.</em>
  </div>

</div>
</body>
</html>"""


# ── Telegram ──────────────────────────────────────────────────────────────────

def build_telegram_text(sections: dict, sparky: str, meta: dict) -> str:
    hl = parse_headline(sections.get("HEADLINE", ""))
    date_obj  = datetime.strptime(meta["date_str"], "%Y-%m-%d")
    date_short = date_obj.strftime("%b %-d")

    def esc(text: str) -> str:
        """Minimal HTML escaping for Telegram HTML mode."""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    parts = [
        f"<b>THE BLEED</b> — Issue #{meta['issue_number']}, {date_short}",
        f"Belief Exchange: {meta['belief']} / 100",
        "",
        f"<b>{esc(hl['title'])}</b>",
    ]
    if hl["subhead"]:
        parts.append(f"<i>{esc(hl['subhead'])}</i>")
    if hl["body"]:
        parts += [esc(hl["body"]), ""]

    gossip = sections.get("GOSSIP", "")
    if gossip:
        parts += [f"<b>— Gossip & Corridor Whispers —</b>", esc(gossip[:800] + ("…" if len(gossip) > 800 else "")), ""]

    feature = sections.get("FEATURE", "")
    if feature:
        lines = feature.strip().splitlines()
        title = lines[0].strip().strip("*#").strip() if lines else "Feature"
        body  = "\n".join(lines[1:]).strip()[:600]
        parts += [f"<b>— {esc(title)} —</b>", esc(body) + "…", ""]

    fuel_col = sections.get("FUEL", "")
    if fuel_col:
        parts += [f"<b>Dr. Vellum's Desk</b>", f"<i>{esc(fuel_col)}</i>", ""]

    gimble_col = sections.get("GIMBLE", "")
    if gimble_col:
        parts += [f"<b>Gimble's Ledger Office</b>", esc(gimble_col[:800] + ("…" if len(gimble_col) > 800 else "")), ""]

    inkrest_col = sections.get("INKREST", "")
    if inkrest_col:
        parts += [f"<b>Dr. Inkrest's Reauthoring Desk</b>", f"<i>{esc(inkrest_col[:800] + ('…' if len(inkrest_col) > 800 else ''))}</i>", ""]

    exchange = sections.get("EXCHANGE", "")
    if exchange:
        parts += [f"<b>The Exchange</b>", esc(exchange), ""]
    fae_ledger = get_fae_ledger_brief(meta.get("player_name", "bj"))
    if fae_ledger and "clean" not in fae_ledger.lower():
        parts += [f"<b>The Margin</b>", esc(fae_ledger[:800] + ("…" if len(fae_ledger) > 800 else "")), ""]
    goblin_exchange = sections.get("GOBLINEXCHANGE", "")
    if goblin_exchange:
        parts += [f"<b>Goblin Market Exchange</b>", esc(goblin_exchange[:800] + ("…" if len(goblin_exchange) > 800 else "")), ""]

    player_box = sections.get("PLAYER", "")
    if player_box:
        parts += [f"<b>The Correspondent</b>", f"<i>{esc(player_box[:400] + ('…' if len(player_box) > 400 else ''))}</i>", ""]

    war_report = sections.get("WARREPORT", "")
    if war_report:
        parts += [f"<b>Chapter War Report</b>", esc(war_report[:600] + ("…" if len(war_report) > 600 else "")), ""]

    outerstacks = sections.get("OUTERSTACKS", "")
    if outerstacks:
        parts += [f"<b>Outer Stacks — Frontier Desk</b>", esc(outerstacks[:700] + ("…" if len(outerstacks) > 700 else "")), ""]

    talisman_col = sections.get("TALISMAN", "")
    if talisman_col:
        talisman_label = meta.get("talisman_name", "Chapter Talisman")
        parts += [f"<b>The Ascendant — {esc(talisman_label)}</b>",
                  esc(talisman_col[:700] + ("…" if len(talisman_col) > 700 else "")), ""]

    if _SCHEDULE_AVAILABLE:
        sched = get_schedule_data()
        timetable_lines = [f"<b>Today at the Academy</b>",
                           f"{sched['weekday_name']} · Day {sched['academy_day']} ({sched['tone']})"]
        cls_now = sched["class_now"]
        if cls_now:
            timetable_lines.append(f"&#9679; Now: {cls_now[0]} ({cls_now[1]})")
        cls_next = sched["class_next"]
        if cls_next:
            timetable_lines.append(f"&#8594; Next: {cls_next[0]} ({cls_next[1]}, {sched['class_next_time']})")
        club = sched["club"]
        if club:
            timetable_lines.append(f"&#9733; Tonight 7 PM: {club[0]}")
        practice = sched["practice"]
        if practice:
            timetable_lines.append(f"Practice: {practice['name']} — {practice['prompt']}")
        parts += timetable_lines + [""]

    classifieds = sections.get("CLASSIFIEDS", "")
    if classifieds:
        parts += [f"<b>Classifieds</b>", esc(classifieds), ""]

    if sparky:
        parts += [f"<b>Sparky:</b>", f"<i>{esc(sparky)}</i>", ""]

    forecast = sections.get("FORECAST", "")
    if forecast:
        parts += [f"<b>Story Forecast</b>", esc(forecast[:600]) + "…", ""]

    market = sections.get("MARKET", "")
    if market:
        parts += [f"<b>Thread Futures</b>", esc(market[:500]) + "…", ""]

    missing = sections.get("MISSING", "")
    if missing:
        parts += [f"<b>The Missing</b>", f"<i>{esc(missing)}</i>"]

    return "\n".join(parts)


_TELEGRAM_TARGET  = "8729557865"
_TELEGRAM_CHANNEL = "telegram"
_TELEGRAM_ACCOUNT = "enchantify"


def send_telegram(text: str, cfg: dict):
    # Telegram message limit: 4096 chars
    if len(text) > 4000:
        text = text[:3990] + "\n…"

    result = subprocess.run(["openclaw", "message", "send",
         "--target",  _TELEGRAM_TARGET,
         "--channel", _TELEGRAM_CHANNEL,
         "--account", _TELEGRAM_ACCOUNT,
         "-m", text],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("  ✓ Telegram edition sent.")
    else:
        print(f"  ⚠ Telegram send failed: {result.stderr.strip()[:100]}")

# ── CUPS print ────────────────────────────────────────────────────────────────

CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def html_to_pdf(html_path: Path) -> Path:
    """Convert HTML to PDF. Tries wkhtmltopdf, then Chrome headless."""
    pdf_path = html_path.with_suffix(".pdf")

    if shutil.which("wkhtmltopdf"):
        r = subprocess.run(
            ["wkhtmltopdf", "--page-size", "Letter", "--quiet",
             "--enable-local-file-access",
             str(html_path), str(pdf_path)],
            capture_output=True, timeout=30
        )
        if r.returncode == 0:
            return pdf_path

    chrome = CHROME_PATH if os.path.exists(CHROME_PATH) else shutil.which("google-chrome") or shutil.which("chromium")
    if chrome:
        r = subprocess.run(
            [chrome, "--headless", "--disable-gpu", "--no-sandbox",
             f"--print-to-pdf={pdf_path}",
             "--print-to-pdf-no-header",
             str(html_path)],
            capture_output=True, timeout=45
        )
        if r.returncode == 0 and pdf_path.exists():
            return pdf_path

    return html_path  # fallback: return original HTML


def _printer_status(printer: str) -> str:
    result = subprocess.run(["lpstat", "-p", printer], capture_output=True, text=True, timeout=8)
    return ((result.stdout or "") + (result.stderr or "")).strip()


def _printer_looks_unreachable(status: str) -> bool:
    lowered = (status or "").lower()
    return any(
        phrase in lowered
        for phrase in (
            "looking for printer",
            "unable to locate",
            "not found",
            "invalid destination",
            "disabled",
            "offline",
        )
    )


def _printer_has_active_jobs(printer: str) -> bool:
    result = subprocess.run(["lpstat", "-W", "not-completed", "-o", printer], capture_output=True, text=True, timeout=8)
    text = ((result.stdout or "") + (result.stderr or "")).strip().lower()
    if not text or "no entries" in text or "unknown destination" in text or "invalid destination" in text:
        return False
    return printer.lower() in text


def _cups_default_printer() -> str:
    result = subprocess.run(["lpstat", "-d"], capture_output=True, text=True, timeout=8)
    text = ((result.stdout or "") + (result.stderr or "")).strip()
    m = re.search(r"system default destination:\s*(\S+)", text)
    return m.group(1).strip() if m else ""


def _print_candidates(cfg: dict) -> list[str]:
    names = [
        cfg.get("BLEED_PRINTER", ""),
        cfg.get("BLEED_PRINTER_FALLBACK", ""),
        _cups_default_printer(),
    ]
    out = []
    for name in names:
        clean = (name or "").strip()
        if clean and clean not in out:
            out.append(clean)
    return out


def _submit_print_job(printer: str, print_file: Path) -> tuple[bool, str, str]:
    result = subprocess.run(
        ["lp", "-d", printer, "-o", "media=Letter", str(print_file)],
        capture_output=True, text=True, timeout=15
    )
    text = ((result.stdout or "") + (result.stderr or "")).strip()
    job_m = re.search(r"request id is\s+(\S+)", text)
    job_id = job_m.group(1) if job_m else ""
    return result.returncode == 0, text, job_id


def _job_still_active(job_id: str) -> bool:
    if not job_id:
        return False
    result = subprocess.run(["lpstat", "-W", "not-completed", "-o"], capture_output=True, text=True, timeout=8)
    text = ((result.stdout or "") + (result.stderr or "")).strip()
    return job_id in text


def _print_job_cleared(job_id: str, wait_seconds: int) -> bool:
    if not job_id or wait_seconds <= 0:
        return True
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        if not _job_still_active(job_id):
            return True
        time.sleep(3)
    return not _job_still_active(job_id)


def print_to_cups(html_path: Path, cfg: dict):
    candidates = _print_candidates(cfg)
    if not candidates:
        print("  ℹ CUPS print not configured (BLEED_PRINTER) — skipping.")
        return

    print("  Converting to PDF...")
    print_file = html_to_pdf(html_path)
    try:
        verify_seconds = max(0, int(cfg.get("BLEED_PRINT_VERIFY_SECONDS", "30")))
    except ValueError:
        verify_seconds = 30

    last_error = ""
    for printer in candidates:
        status = _printer_status(printer)
        if _printer_looks_unreachable(status):
            print(f"  ⚠ Printer unavailable: {printer} — {status[:120]}")
            last_error = status
            continue
        if _printer_has_active_jobs(printer):
            print(f"  ⚠ Printer busy/stuck, trying next destination: {printer} — {status[:120]}")
            last_error = status
            continue

        ok, detail, job_id = _submit_print_job(printer, print_file)
        if not ok:
            print(f"  ⚠ Print failed on {printer}: {detail[:160]}")
            last_error = detail
            continue

        if _print_job_cleared(job_id, verify_seconds):
            print(f"  ✓ Sent to printer: {printer}")
            return

        print(f"  ⚠ Print job accepted but still active on {printer}: {job_id or detail[:80]}")
        return

    print(f"  ⚠ Print failed on all configured printers: {last_error[:180]}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    today    = date.today()
    date_str = today.strftime("%Y-%m-%d")
    now_str  = datetime.now().strftime("%Y-%m-%d %H:%M")

    print(f"The Bleed — {now_str}")

    if "--model-smoke" in sys.argv:
        raise SystemExit(model_smoke_test())

    cfg = load_config()
    cron_steward.record_event("bleed", "start", date=date_str, force="--force" in sys.argv)

    ISSUES_DIR.mkdir(parents=True, exist_ok=True)
    issue_path    = ISSUES_DIR / f"{date_str}.html"
    delivery_flag = ISSUES_DIR / f"{date_str}.delivered"
    lock_path     = ISSUES_DIR / f"{date_str}.lock"
    force         = "--force" in sys.argv

    # If the HTML exists and delivery is done, nothing to do (unless --force)
    if issue_path.exists() and delivery_flag.exists() and not force:
        delivered_at = delivery_flag.read_text().strip()[:16]
        print(f"  ✓ Issue already published and delivered today ({delivered_at}). Use --force to redo.")
        cron_steward.mark_skipped("bleed", "already published and delivered", scope=date_str)
        return

    lock_fd, lock_reason = _acquire_issue_lock(lock_path)
    if lock_fd is None:
        print(f"  ✓ Bleed is already running for {date_str}; skipping ({lock_reason}).")
        cron_steward.mark_skipped("bleed", "run already in progress", scope=date_str, detail=lock_reason)
        return

    try:
        # Re-check after the lock. A sibling process may have delivered while this one waited.
        if issue_path.exists() and delivery_flag.exists() and not force:
            delivered_at = delivery_flag.read_text().strip()[:16]
            print(f"  ✓ Issue was delivered by another run ({delivered_at}).")
            cron_steward.mark_skipped("bleed", "already delivered after lock", scope=date_str)
            return

        # If the HTML already exists but delivery hasn't run, skip regeneration
        already_generated = issue_path.exists() and not force

        issue_number = get_issue_number()

        if already_generated:
            print(f"  ✓ Issue already generated — running delivery only.")
            # Read back sparky + meta from what was saved; rebuild a minimal meta for delivery
            sparky           = get_sparky_shiny(date_str)
            leading_talisman = get_leading_talisman()
            player_data      = get_player_data(cfg)
            existing_feature_image = ISSUE_IMAGES_DIR / f"{date_str}-feature.png"
            # Parse sections from the saved HTML for Telegram text generation
            saved_html = issue_path.read_text()
            issue_number = _issue_number_from_html(saved_html, issue_number)
            print(f"  Preparing issue #{issue_number}...")
            meta = {
                "date_str":      date_str,
                "issue_number":  issue_number,
                "belief":        player_data.get("belief", "?"),
                "talisman_name": leading_talisman.get("name", "") if leading_talisman else "",
                "player_name":   player_data.get("name", "bj"),
                "feature_image": f"../images/{existing_feature_image.name}" if existing_feature_image.exists() else "",
            }
            # Extract plain text per section from the saved HTML for Telegram rebuild
            sections = _sections_from_saved_html(saved_html)
            if sections.get("EXCHANGE"):
                sections["EXCHANGE"] = normalize_exchange_text(sections["EXCHANGE"])
            sections["GOBLINEXCHANGE"] = build_goblin_market_exchange(player_data.get("name", "bj"))
        else:
            print(f"  Preparing issue #{issue_number}...")
            # ── Read data sources ────────────────────────────────────────────
            player_data = get_player_data(cfg)

            heartbeat = read_file_safe(WORKSPACE_DIR / "HEARTBEAT.md", 100)
            pulse     = extract_pulse_section(heartbeat)[:1200]
            health    = extract_health_from_pulse(pulse) or "(health data not available today)"

            tick_queue       = read_file_safe(WORKSPACE_DIR / "memory" / "tick-queue.md", 40)
            thread_summary   = get_thread_summary()
            entity_standings = get_entity_standings()
            sparky           = get_sparky_shiny(date_str)
            forecast         = get_weather_forecast_from_heartbeat()
            market_odds      = calculate_market_odds()
            war_info         = parse_app_register_for_bleed()
            player_recap     = get_player_recap_data(cfg)
            leading_talisman = get_leading_talisman()
            fuel_data        = get_fuel_data()
            vellum_chart      = get_vellum_chart(player_data.get("name", "bj"))
            vellum_column_data = build_vellum_longevity_brief(fuel_data, health, pulse, vellum_chart)
            gimble_column_data = build_gimble_ledger_brief(player_data.get("name", "bj"))
            inkrest_column_data = build_inkrest_column_brief(player_data.get("name", "bj"))
            talisman_npcs    = get_chapter_npcs(leading_talisman.get("chapter", "")) if leading_talisman else ""

            # Format market odds for prompt injection
            market_odds_formatted = "\n".join(
                f"- {o['name']} ({o['phase']}, combined Belief {o['belief']}): "
                f"Will this thread significantly stir this week? YES: {o['yes']}% / NO: {o['no']}%"
                + (f"  Next beat: {o['beat']}" if o['beat'] else "")
                for o in market_odds
            ) or "(no thread data available)"

            # Format talisman data block for prompt
            if leading_talisman:
                philosophy_clean = re.sub(r'\[thread:[^\]]+\]\s*', '', leading_talisman['philosophy']).strip()
                talisman_data_str = (
                    f"Name: {leading_talisman['name']}\n"
                    f"Chapter: {leading_talisman['chapter']}\n"
                    f"Belief: {leading_talisman['belief']} (leads all chapter talismans)\n"
                    f"Philosophy: {philosophy_clean}"
                )
            else:
                talisman_data_str = "(no talisman data available)"

            previous_coverage = get_previous_coverage(n=3)

            data = {
                "date_str":              date_str,
                "issue_number":          issue_number,
                "player":                player_data,
                "pulse":                 pulse,
                "health":                health,
                "forecast":              forecast or "(forecast not yet loaded — check pulse)",
                "tick_queue":            tick_queue or "(no simulation activity since last session)",
                "thread_summary":        thread_summary,
                "entity_standings":      entity_standings,
                "goblin_exchange":       build_goblin_market_exchange(player_data.get("name", "bj")),
                "fae_ledger":            get_fae_ledger_brief(player_data.get("name", "bj")),
                "classified_leads":      build_classified_leads(),
                "market_odds_formatted": market_odds_formatted,
                "war_data":              format_war_data(war_info),
                "outer_stacks":          get_outer_stacks_brief(player_data.get("name", "bj")),
                "player_recap":          player_recap,
                "talisman_data":         talisman_data_str,
                "talisman_npcs":         talisman_npcs or "(no chapter NPCs found)",
                "fuel_data":             fuel_data,
                "vellum_column_data":    vellum_column_data,
                "gimble_column_data":    gimble_column_data,
                "inkrest_column_data":   inkrest_column_data,
                "previous_coverage":     previous_coverage,
            }

            # ── Generate content ─────────────────────────────────────────────
            print("  Generating newspaper content...")
            sections = generate_content(data)

            if not sections:
                print("  ⚠ Agent returned no content. Check logs.")
                return
            sections["GOBLINEXCHANGE"] = data["goblin_exchange"]

            repair_gossip_section(sections, data)
            if sections.get("EXCHANGE"):
                sections["EXCHANGE"] = normalize_exchange_text(sections["EXCHANGE"])

            if _bleed_allow_fallback() and not (sections.get("OUTERSTACKS") or "").strip():
                fallback = build_outer_stacks_fallback(data)
                if fallback:
                    sections["OUTERSTACKS"] = fallback
                    print("  ↺ OUTERSTACKS missing from model output — used deterministic fallback.")
            if sections.get("EXCHANGE"):
                sections["EXCHANGE"] = normalize_exchange_text(sections["EXCHANGE"])

            # ── Build HTML ───────────────────────────────────────────────────
            headline_parts = parse_headline(sections.get("HEADLINE", ""))
            feature_image_path = generate_feature_image(sections.get("FEATURE", ""), {
                "date_str": date_str,
                "issue_number": issue_number,
                "headline_title": headline_parts.get("title", ""),
                "headline_body": headline_parts.get("body", ""),
                "gossip": sections.get("GOSSIP", ""),
                "market": sections.get("MARKET", ""),
                "weather": sections.get("WEATHER", ""),
            })
            meta = {
                "date_str":       date_str,
                "issue_number":   issue_number,
                "belief":         player_data.get("belief", "?"),
                "talisman_name":  leading_talisman.get("name", "") if leading_talisman else "",
                "player_name":    player_data.get("name", "bj"),
                "feature_image":  f"../images/{feature_image_path.name}" if feature_image_path else "",
            }
            errors = validate_generated_sections(sections)
            if errors:
                print("  ⚠ Section validation issues: " + "; ".join(errors))
            html = build_html(sections, sparky, meta)

            # ── Save ─────────────────────────────────────────────────────────
            issue_path.write_text(html)
            save_issue_number(issue_number)
            print(f"  ✓ Issue #{issue_number} saved → {issue_path}")

        # ── Telegram edition ─────────────────────────────────────────────────
        telegram_text = build_telegram_text(sections, sparky, meta)
        delivery_payload = {"date": date_str, "issue": meta["issue_number"], "telegram": telegram_text}
        skip, digest, reason = cron_steward.should_skip_duplicate(
            "bleed",
            delivery_payload,
            cooldown_hours=24,
            force=force,
            scope=date_str,
        )
        if skip:
            print(f"  ✓ Duplicate delivery blocked: {reason}.")
            delivery_flag.write_text(datetime.now().isoformat())
            cron_steward.mark_skipped("bleed", reason, scope=date_str, fingerprint=digest)
            return

        send_telegram(telegram_text, cfg)

        # ── CUPS print ───────────────────────────────────────────────────────
        print_to_cups(issue_path, cfg)

        classifieds_text = sections.get("CLASSIFIEDS", "")
        record_classifieds_hooks(date_str, meta["issue_number"], classifieds_text)
        ripples = record_bleed_ripples(date_str, meta["issue_number"], sections, meta)
        ensure_scene_ledger_seed(date_str, meta["issue_number"], sections, meta)

        # ── Mark delivered ───────────────────────────────────────────────────
        delivery_flag.write_text(datetime.now().isoformat())
        cron_steward.mark_delivered(
            "bleed",
            delivery_payload,
            scope=date_str,
            issue_number=meta["issue_number"],
            html=str(issue_path),
            bleed_ripples=len(ripples),
        )

        print(f"  ✓ The Bleed #{meta['issue_number']} published.")
    except Exception as exc:
        cron_steward.record_event("bleed", "failed", scope=date_str, reason=str(exc)[:500])
        print(f"  ✗ Bleed aborted before publication: {exc}")
        raise
    finally:
        _release_issue_lock(lock_fd, lock_path)


if __name__ == "__main__":
    main()

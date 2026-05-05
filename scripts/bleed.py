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


def get_fuel_data(days: int = 10) -> str:
    """Read the fuel log and return a summarized view for the past N days."""
    log_path = WORKSPACE_DIR / "scripts" / "fuel-log.txt"
    if not log_path.exists():
        return "(no fuel log found)"

    from datetime import timedelta
    cutoff = date.today() - timedelta(days=days)

    entries = []
    for line in log_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("|")
        if len(parts) < 5:
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
        })

    if not entries:
        return "(no fuel data in the past 10 days)"

    # Daily totals
    daily: dict = {}
    for e in entries:
        d = e["date"]
        if d not in daily:
            daily[d] = {"calories": 0, "protein": 0, "items": []}
        daily[d]["calories"] += e["calories"]
        daily[d]["protein"]  += e["protein"]
        daily[d]["items"].append(e["description"])

    lines = ["RECENT FUEL LOG (last 10 days):"]
    for d in sorted(daily.keys()):
        items_str = " / ".join(daily[d]["items"])
        lines.append(
            f"  {d}: {daily[d]['calories']} cal, {daily[d]['protein']}g protein"
            f"  — {items_str}"
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
    lines.append(f"AVERAGES (logged days only): {avg_cal} cal/day, {avg_pro}g protein/day")
    if patterns:
        lines.append("PATTERNS: " + "; ".join(patterns))

    return "\n".join(lines)


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
        atype = grab(r'\*\*Type:\*\*\s*(.+)', section, default="?")
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
    fuel = data.get("fuel_data") or "No provisions log was filed."
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
        "GOSSIP": (
            "One hears the front page had to be composed without its usual theatrical flourishes. How bracing. Facts look almost indecent when they arrive undressed.\n\n"
            f"{lead_thread} continues to attract attention from people who claim not to be watching it. They are, naturally, watching it very closely.\n\n"
            "A certain table in the Great Hall has developed the unfortunate habit of remembering who spoke kindly near it. This will ruin several reputations if it continues.\n\n"
            "Cedric Widden has been seen negotiating with silence as if silence were a roommate who owed rent. Results remain inconclusive.\n\n"
            "The wise student keeps one eye on the ordinary. It is where the best leverage hides.\n\n— W.E."
        ),
        "WEATHER": forecast,
        "FORECAST": (
            f"70% chance of continued pressure around {lead_thread}; its ledger position makes it difficult to ignore.\n"
            f"55% chance that {second_thread} surfaces as a secondary condition rather than a front-page storm.\n"
            "45% chance of quiet-life consequences becoming materially relevant before the week is out.\n"
            "Overall narrative outlook: settled on the surface, active underneath."
        ),
        "MARKET": market,
        "BAROMETER": (
            f"Vitality index: {health}\n"
            "Corridor conditions: locally responsive, with attention pooling around high-Belief rooms.\n"
            "Student weather: suitable for short walks, careful meals, and questions that do not need to become crises."
        ),
        "FUEL": (
            f"{fuel}\n\n"
            "The Provisions Desk recommends treating stamina as narrative infrastructure. A student cannot carry a season on coffee, symbolism, and vibes alone."
        ),
        "EXCHANGE": data.get("entity_standings") or "No exchange prices were available before press time.",
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
    "BAROMETER",
    "FUEL",
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

Classified leads:
{compact_text(data.get('classified_leads', ''), 800)}

Chapter war:
{compact_text(data.get('war_data', ''), 1200)}

Outer Stacks:
{compact_text(data.get('outer_stacks', ''), 1000)}

Ascendant:
{compact_text(data.get('talisman_data', ''), 700)}
Chapter NPCs: {compact_text(data.get('talisman_npcs', ''), 500)}

Fuel:
{compact_text(data.get('fuel_data', ''), 600)}

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
            "GOSSIP: 5 distinct W.E. gossip items, fresh and specific, ending — W.E. "
            "FEATURE: titled/bylined longer context piece, 4-6 paragraphs, not a repeat of recent features.",
        ),
        (
            ["WEATHER", "FORECAST", "MARKET", "BAROMETER"],
            2200,
            "WEATHER: 4-day Academy weather using exact forecast conditions. "
            "FORECAST: narrative weather with probabilities and named threads. "
            "MARKET: thread futures ticker with YES/NO odds from data and commentary. "
            "BAROMETER: compact health/vitality conditions.",
        ),
        (
            ["FUEL", "EXCHANGE", "CLASSIFIEDS"],
            2400,
            "FUEL: compact provisions log, specific foods and dry professional tone. "
            "EXCHANGE: belief ticker for significant entities and one commentary paragraph. "
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

The reader should be able to SETTLE INTO THIS PAPER. Every section except The Barometer,
The Exchange, The Correction, The Missing, and The Correspondent should be substantial, readable prose.

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

CHAPTER WAR DATA (for The War Report section):
{data['war_data']}

OUTER STACKS DATA (for the frontier / book-jump column):
{data['outer_stacks']}

LEADING CHAPTER TALISMAN (for The Ascendant column):
{data['talisman_data']}

CHAPTER NPCs AVAILABLE FOR INTERVIEW:
{data['talisman_npcs']}

FUEL LOG (for The Provisions Log column):
{data['fuel_data']}

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
[The social column, in W.E.'s voice. Write 5-6 separate gossip items — each item is its own
paragraph of 2-4 sentences. Wicker reports true things slanted. He names names when it suits
him and withholds them when it doesn't. He is never without an angle. He always knows more
than he lets on. He never directly identifies himself. Each item should feel like a distinct
morsel — a different corner of the Academy social world. End with his byline: — W.E.
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

===BAROMETER===
[Health/biometric data AS Academy conditions. Steps = distance covered on Academy grounds.
Sleep/HRV = student vitality index. Weather = atmospheric pressure. 4-6 short lines,
formatted like a weather/conditions report. Brief is correct here.]

===FUEL===
[The Provisions Log — a compact recurring column in The Bleed's dry academic voice.
Written as if the Academy's anonymous Provisions Correspondent is filing a professional
report on what the student correspondent has been consuming.

Use the FUEL LOG data provided. Translate real food into Academy texture — not literally
(don't mention calories), but as narrative material: what the pattern suggests about the
student's state, their habits, their relationship to comfort and routine.

Structure:
- 2-3 sentences observing the recent pattern. Specific. Deadpan. Name the recurring items.
  ("The correspondent has logged the same morning assembly on four consecutive days...")
- 1-2 sentences of dry editorial opinion or mild advice, in the voice of someone who has
  strong feelings about what serious students eat. Not preachy — professional. Wry.
- 1 closing sentence: a brief prognosis for narrative stamina this week, based on what
  they've been putting in.

Tone: the wine critic of student dining. Precise, slightly arch, genuinely observant.
Brief is correct here — this is a sidebar, not a feature.]

===EXCHANGE===
[The Belief Exchange ticker. List ALL significant entities with Belief scores as prices.
Mark trend: ↑ rising / ↓ falling / — steady. One paragraph of market commentary below
the ticker — what does the current pattern mean narratively?]

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
        ('GOSSIP', 'Gossip &amp; Corridor Whispers', 'The Barometer'),
        ('BAROMETER', 'The Barometer', 'The Provisions Log'),
        ('FUEL', 'The Provisions Log', 'The Exchange'),
        ('EXCHANGE', 'The Exchange', 'Today at the Academy'),
        ('PLAYER', 'The Correspondent', 'Chapter War Report'),
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
        f"Feature illustration for The Bleed, issue #{meta.get('issue_number')}. "
        f"Story title: {title}. "
        f"Illustrate the most vivid in-world scene or symbolic image suggested by this story and surrounding issue context: {scene_basis}. "
        "Style: literary magical-archive illustration, sparse pen-and-ink line art with watercolor washes on textured parchment, "
        "muted sepia and gray palette, selective jewel-like pops of teal, gold, and red in magical details. "
        "Vertical editorial illustration, atmospheric, magical-school newspaper art, elegant, slightly eerie, richly specific, no text, no caption, no border, no watermark."
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
    barometer   = sections.get("BAROMETER", "")
    fuel        = sections.get("FUEL", "")
    exchange    = sections.get("EXCHANGE", "")
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
  /* Row 1: Gossip (wide) | Right rail (narrow) */
  .content-row {{
    display: grid;
    column-gap: 0;
    border-bottom: 1.5px solid #111;
    margin-bottom: 8pt;
  }}

  .row-gossip-feature {{
    grid-template-columns: 3fr 1.1fr;
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

  /* ── RIGHT RAIL (barometer + exchange stacked) ── */
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

  <!-- ROW 1: Gossip (wide left) + right rail -->
  <div class="content-row row-gossip-feature">

    <div class="col gossip-body">
      <div class="col-head">Gossip &amp; Corridor Whispers</div>
      <div class="byline">Our Social Correspondent, W.E.</div>
      {paragraphs(gossip)}
    </div>

    <div class="col" style="padding-right:0;">
      <div class="rail-section">
        <div class="col-head">The Barometer</div>
        <div class="rail-body">{paragraphs(barometer)}</div>
      </div>
      {'<div class="rail-section"><div class="col-head">The Provisions Log</div><div class="rail-body" style="font-size:8.5pt; line-height:1.6; font-style:italic;">' + paragraphs(fuel) + '</div></div>' if fuel else ''}
      <div class="rail-section">
        <div class="col-head">The Exchange</div>
        <div class="rail-body">{paragraphs(exchange)}</div>
      </div>
      <div class="rail-section">
        <div class="col-head">Today at the Academy</div>
        <div class="rail-body" style="font-size:8pt; line-height:1.65;">{timetable}</div>
      </div>
    </div>

  </div>

  <!-- ROW 2: Player Correspondent (left) | Chapter War Report (right) -->
  <div class="content-row row-player-war">

    <div class="col">
      <div class="col-head">The Correspondent</div>
      <div class="player-box">{paragraphs(player_box) if player_box else "<p><em>(no student activity reported today)</em></p>"}</div>
    </div>

    <div class="col" style="padding-right:0;">
      <div class="col-head">Chapter War Report</div>
      <div class="war-report-body">{paragraphs(war_report) if war_report else "<p><em>(war data unavailable)</em></p>"}</div>
    </div>

  </div>

  <!-- ROW 2b: The Ascendant — leading chapter talisman column -->
  {'<div class="content-row row-talisman"><div class="col" style="padding-right:0;"><div class="col-head">The Ascendant &mdash; ' + (meta.get("talisman_name","") or "Chapter Talisman") + '</div><div class="talisman-body">' + paragraphs(talisman) + '</div></div></div>' if talisman else ''}

  {'<section id="section-outerstacks" class="content-row row-talisman"><div class="col outerstacks" style="padding-right:0;"><div class="col-head">Outer Stacks &mdash; Frontier Desk</div><div class="war-report-body">' + paragraphs(outerstacks) + '</div></div></section>' if outerstacks else ''}

  <!-- ROW 3: Weather | Story Forecast | Predictions Market -->
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

  <!-- ROW 4: Classifieds + right stack -->
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
        parts += [f"<b>— Gossip (W.E.) —</b>", esc(gossip[:800] + ("…" if len(gossip) > 800 else "")), ""]

    feature = sections.get("FEATURE", "")
    if feature:
        lines = feature.strip().splitlines()
        title = lines[0].strip().strip("*#").strip() if lines else "Feature"
        body  = "\n".join(lines[1:]).strip()[:600]
        parts += [f"<b>— {esc(title)} —</b>", esc(body) + "…", ""]

    barometer = sections.get("BAROMETER", "")
    if barometer:
        parts += [f"<b>Barometer</b>", esc(barometer), ""]

    fuel_col = sections.get("FUEL", "")
    if fuel_col:
        parts += [f"<b>The Provisions Log</b>", f"<i>{esc(fuel_col)}</i>", ""]

    exchange = sections.get("EXCHANGE", "")
    if exchange:
        parts += [f"<b>The Exchange</b>", esc(exchange), ""]

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
                "classified_leads":      build_classified_leads(),
                "market_odds_formatted": market_odds_formatted,
                "war_data":              format_war_data(war_info),
                "outer_stacks":          get_outer_stacks_brief(player_data.get("name", "bj")),
                "player_recap":          player_recap,
                "talisman_data":         talisman_data_str,
                "talisman_npcs":         talisman_npcs or "(no chapter NPCs found)",
                "fuel_data":             fuel_data,
                "previous_coverage":     previous_coverage,
            }

            # ── Generate content ─────────────────────────────────────────────
            print("  Generating newspaper content...")
            sections = generate_content(data)

            if not sections:
                print("  ⚠ Agent returned no content. Check logs.")
                return

            if _bleed_allow_fallback() and not (sections.get("OUTERSTACKS") or "").strip():
                fallback = build_outer_stacks_fallback(data)
                if fallback:
                    sections["OUTERSTACKS"] = fallback
                    print("  ↺ OUTERSTACKS missing from model output — used deterministic fallback.")

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
        ensure_scene_ledger_seed(date_str, meta["issue_number"], sections, meta)

        # ── Mark delivered ───────────────────────────────────────────────────
        delivery_flag.write_text(datetime.now().isoformat())
        cron_steward.mark_delivered(
            "bleed",
            delivery_payload,
            scope=date_str,
            issue_number=meta["issue_number"],
            html=str(issue_path),
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

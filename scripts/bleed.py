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

import os
import re
import sys
import json
import shutil
import subprocess
import urllib.request
from datetime import datetime, date
from pathlib import Path
import sys as _sys

SCRIPT_DIR   = Path(__file__).parent
WORKSPACE_DIR = SCRIPT_DIR.parent

# Import schedule module
_sys.path.insert(0, str(SCRIPT_DIR))
try:
    from schedule import get_schedule_data, WEEKDAY_NAMES
    _SCHEDULE_AVAILABLE = True
except ImportError:
    _SCHEDULE_AVAILABLE = False

ISSUE_NUMBER_FILE = WORKSPACE_DIR / "bleed" / "issue-number.txt"
ISSUES_DIR        = WORKSPACE_DIR / "bleed" / "issues"


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
    data = {}

    m = re.search(r'\*\*Belief:\*\*\s*(\d+)', content)
    data["belief"] = m.group(1) if m else "?"

    m = re.search(r'\*\*Chapter:\*\*\s*(\S+)', content)
    data["chapter"] = m.group(1) if m else "?"

    m = re.search(r'\*\*Tutorial Progress:\*\*\s*(\S+)', content)
    data["tutorial"] = m.group(1) if m else "?"

    return data


def get_thread_summary() -> str:
    content = read_file_safe(WORKSPACE_DIR / "lore" / "threads.md")
    lines = []
    for section in re.split(r'^## Thread: ', content, flags=re.MULTILINE)[1:]:
        slines = section.strip().splitlines()
        name = slines[0].strip() if slines else "?"
        phase_m    = re.search(r'\*\*phase:\*\*\s*(.+)', section)
        pressure_m = re.search(r'\*\*pressure:\*\*\s*(.+)', section)
        beat_m     = re.search(r'\*\*Next beat:\*\*\s*(.+)', section)
        phase    = phase_m.group(1).strip() if phase_m else "?"
        pressure = pressure_m.group(1).strip() if pressure_m else "?"
        beat     = beat_m.group(1).strip()[:120] if beat_m else ""
        lines.append(f"- {name} [{phase}, pressure: {pressure}]: {beat}")
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


# ── Agent call ────────────────────────────────────────────────────────────────

_OPENCLAW_BIN = (
    shutil.which("openclaw")
    or "/opt/homebrew/bin/openclaw"
    or "/usr/local/bin/openclaw"
)

def call_agent(prompt: str) -> str:
    result = subprocess.run(
        [_OPENCLAW_BIN, "agent", "--local", "--agent", "enchantify", "-m", prompt],
        capture_output=True, text=True, timeout=240
    )
    output = result.stdout.strip()

    # Strip ANSI codes
    ansi = re.compile(r'\x1b\[[0-9;]*m')
    output = ansi.sub('', output)

    # Strip plugin/agent noise lines
    noise = ("[plugins]", "[agents/", "[agent/", "adopted ", "google tool")
    clean = [
        line for line in output.splitlines()
        if not any(line.strip().lower().startswith(p) for p in noise)
    ]
    return "\n".join(clean).strip()


# ── Content generation ────────────────────────────────────────────────────────

def generate_content(data: dict) -> dict:
    prompt = f"""You are writing THE BLEED — the Academy student newspaper.

Publication date: {data['date_str']}
Issue number: #{data['issue_number']}

THE BLEED's voice: Dry, precise, slightly gothic. It reports on the Academy as a real institution.
This is not a parody — it's a real paper. The extraordinary is covered with the same deadpan
reportage as the ordinary. Specificity is everything. Invent concrete details where needed —
named corridors, specific times, partial quotes — the kind of texture that makes a place feel real.

The reader should be able to SETTLE INTO THIS PAPER. Every section except The Barometer,
The Exchange, The Correction, The Missing, and The Correspondent should be substantial, readable prose.

DATA FEEDS (synthesize into journalism — never quote data directly):

SIMULATION ACTIVITY (tick queue):
{data['tick_queue']}

THREAD STATES:
{data['thread_summary']}

ENTITY STANDINGS (Belief = public influence):
{data['entity_standings']}

PLAYER STATUS:
- Chapter: {data['player']['chapter']}
- Belief: {data['player']['belief']} / 100
- Tutorial: {data['player']['tutorial']}

PLAYER STORY DATA (for The Correspondent section):
{data['player_recap']}

CHAPTER WAR DATA (for The War Report section):
{data['war_data']}

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
activity as factual news. This is the main story — write it like one.]

===GOSSIP===
[The social column, in W.E.'s voice. Write 5-6 separate gossip items — each item is its own
paragraph of 2-4 sentences. Wicker reports true things slanted. He names names when it suits
him and withholds them when it doesn't. He is never without an angle. He always knows more
than he lets on. He never directly identifies himself. Each item should feel like a distinct
morsel — a different corner of the Academy social world. End with his byline: — W.E.]

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
and a byline. This is what the reader lingers over.]

===CLASSIFIEDS===
[5-6 classified notices. Each one 2-4 sentences — enough to feel real and slightly eerie.
Mix labels: LOST: / FOUND: / NOTICE: / SEEKING: / WARNING: / REWARD: / POSITION AVAILABLE: etc.
These are story seeds. The reader should want to investigate at least two of them.]

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

    raw = call_agent(prompt)
    return parse_sections(raw)


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
    talisman    = sections.get("TALISMAN", "")

    date_obj  = datetime.strptime(meta["date_str"], "%Y-%m-%d")
    date_long = date_obj.strftime("%A, %B %-d, %Y")

    sparky_html = paragraphs(sparky) if sparky else "<p><em>(a sleeping dot)</em></p>"

    # Extract feature title/byline if the LLM included them
    feature_title = ""
    feature_byline = ""
    feature_body = feature
    if feature:
        lines = feature.strip().splitlines()
        if lines and not lines[0].startswith("By ") and len(lines[0]) < 80:
            feature_title = lines[0].strip().strip("*#").strip()
            rest = "\n".join(lines[1:]).strip()
            if rest.startswith("By ") or rest.startswith("*By "):
                byline_line = rest.splitlines()[0]
                feature_byline = byline_line.strip().strip("*").strip()
                feature_body = "\n".join(rest.splitlines()[1:]).strip()
            else:
                feature_body = rest

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

  .row-bottom {{
    grid-template-columns: 1.5fr 1fr 1.5fr;
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

  <!-- ROW 2 (now Row 4): Feature + Classifieds + right stack -->
  <div class="content-row row-bottom">

    <div class="col">
      <div class="col-head">Feature</div>
      {'<div class="feature-title">' + feature_title + '</div>' if feature_title else ''}
      {'<div class="byline">' + feature_byline + '</div>' if feature_byline else ''}
      {paragraphs(feature_body)}
    </div>

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
         "-m", text],   # <--- Notice the "-m" added here
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


def print_to_cups(html_path: Path, cfg: dict):
    printer = cfg.get("BLEED_PRINTER", "")
    if not printer:
        print("  ℹ CUPS print not configured (BLEED_PRINTER) — skipping.")
        return

    print("  Converting to PDF...")
    print_file = html_to_pdf(html_path)

    result = subprocess.run(
        ["lp", "-d", printer, "-o", "media=Letter", str(print_file)],
        capture_output=True, text=True, timeout=15
    )
    if result.returncode == 0:
        print(f"  ✓ Sent to printer: {printer}")
    else:
        print(f"  ⚠ Print failed: {result.stderr.strip()}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    today    = date.today()
    date_str = today.strftime("%Y-%m-%d")
    now_str  = datetime.now().strftime("%Y-%m-%d %H:%M")

    print(f"The Bleed — {now_str}")

    cfg = load_config()

    # Skip if already published today (unless --force)
    ISSUES_DIR.mkdir(parents=True, exist_ok=True)
    issue_path = ISSUES_DIR / f"{date_str}.html"
    if issue_path.exists() and "--force" not in sys.argv:
        print(f"  ✓ Issue already published today. Use --force to regenerate.")
        return

    issue_number = get_issue_number()
    print(f"  Preparing issue #{issue_number}...")

    # ── Read data sources ────────────────────────────────────────────────────
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
        "market_odds_formatted": market_odds_formatted,
        "war_data":              format_war_data(war_info),
        "player_recap":          player_recap,
        "talisman_data":         talisman_data_str,
        "talisman_npcs":         talisman_npcs or "(no chapter NPCs found)",
        "fuel_data":             fuel_data,
    }

    # ── Generate content ─────────────────────────────────────────────────────
    print("  Generating newspaper content...")
    sections = generate_content(data)

    if not sections:
        print("  ⚠ Agent returned no content. Check logs.")
        return

    # ── Build HTML ───────────────────────────────────────────────────────────
    meta = {
        "date_str":       date_str,
        "issue_number":   issue_number,
        "belief":         player_data.get("belief", "?"),
        "talisman_name":  leading_talisman.get("name", "") if leading_talisman else "",
    }
    html = build_html(sections, sparky, meta)

    # ── Save ─────────────────────────────────────────────────────────────────
    issue_path.write_text(html)
    save_issue_number(issue_number)
    print(f"  ✓ Issue #{issue_number} saved → {issue_path}")

    # ── Telegram edition ─────────────────────────────────────────────────────
    telegram_text = build_telegram_text(sections, sparky, meta)
    send_telegram(telegram_text, cfg)

    # ── CUPS print ───────────────────────────────────────────────────────────
    print_to_cups(issue_path, cfg)

    print(f"  ✓ The Bleed #{issue_number} published.")


if __name__ == "__main__":
    main()

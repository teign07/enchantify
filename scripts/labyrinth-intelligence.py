#!/usr/bin/env python3
"""
labyrinth-intelligence.py — Unified player intelligence system.

Five outputs:
  memory/patterns.md           — Belief trends, recurring themes, what was alive/flat
  memory/arc-spine.md          — Dramatic spine: where the player is in their story
  lore/nothing-intelligence.md — The Nothing's current pressure points and strategy
  memory/tick-queue.md         — [PRIORITY: HIGH] interventions when biometric thresholds crossed
  players/[name]-story.md      — Rolling narrative record: full story log + per-session alive moments

Run: python3 scripts/labyrinth-intelligence.py [player_name]
Called by: nightly cron (23:00). Midnight Revision (every 4 days) also calls this.
"""
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(_SCRIPT_DIR))
try:
    import npc_log as _npc_log
    _HAS_NPC_LOG = True
except ImportError:
    _HAS_NPC_LOG = False

BASE_DIR = Path(os.environ.get("ENCHANTIFY_BASE_DIR", Path(__file__).parent.parent))
PLAYER   = sys.argv[1] if len(sys.argv) > 1 else "bj"


# ─── Load player file ────────────────────────────────────────────────────────

def load_player() -> dict:
    path = BASE_DIR / "players" / f"{PLAYER}.md"
    if not path.exists():
        return {}
    text = path.read_text()

    data = {}

    m = re.search(r"\*\*Belief:\*\*\s*(\d+)", text)
    data["belief"] = int(m.group(1)) if m else 0

    m = re.search(r"\*\*Tutorial Progress:\*\*\s*(\w+)", text)
    data["tutorial"] = m.group(1) if m else "?"

    m = re.search(r"\*\*Chapter:\*\*\s*(\w+)", text)
    data["chapter"] = m.group(1) if m else "Unknown"

    m = re.search(r"\*\*Total runs:\*\*\s*(\d+)", text)
    data["compass_runs"] = int(m.group(1)) if m else 0

    data["has_investments"] = "Nothing invested" not in text
    data["has_anchors"]     = "Anchors: 0" not in text
    data["active_quests"]   = text.count("**ACTIVE**")

    m = re.search(r"## 📜 Story Log(.*?)##", text, re.DOTALL)
    data["story_log"] = re.findall(r"^- (.+)$", m.group(1), re.MULTILINE) if m else []

    return data


# ─── Load heartbeat ──────────────────────────────────────────────────────────

def load_heartbeat() -> dict:
    """
    Parse HEARTBEAT.md for live biometric and behavioral signals.
    Returns only signals that are clearly present — never penalises missing data.
    """
    path = BASE_DIR / "HEARTBEAT.md"
    if not path.exists():
        return {}

    text = path.read_text()
    tl   = text.lower()
    signals: dict = {}

    # Steps — "1,234 steps" or "steps: 1234"
    m = re.search(r"(\d[\d,]+)\s*steps?", tl)
    if m:
        signals["steps"] = int(m.group(1).replace(",", ""))

    # Sleep quality
    if any(k in tl for k in ["fragmented", "poor sleep", "restless", "broken sleep", "little sleep"]):
        signals["sleep"] = "poor"
    elif any(k in tl for k in ["deep sleep", "good sleep", "well rested", "rested"]):
        signals["sleep"] = "good"

    # Watch offline
    if "watch data offline" in tl or "watch offline" in tl:
        signals["watch_offline"] = True

    # Location fixedness — "Mobile" / "Unknown" = no GPS anchor this session
    m = re.search(r"\*\*Location:\*\*\s*(.+)", text)
    if m:
        loc = m.group(1).strip()
        signals["location_fixed"] = not any(
            k in loc.lower() for k in ["mobile", "unknown", "command not found", "offline"]
        )

    # Calories / fuel
    m = re.search(r"(\d{3,4})\s*(?:cal|kcal|calories)", tl)
    if m:
        signals["calories"] = int(m.group(1))

    # Coffee-only flag
    if re.search(r"only\s*coffee|just\s*coffee|coffee\s*only", tl):
        signals["only_coffee"] = True

    # Pulse freshness — extract date line
    m = re.search(r"## Pulse — [\d:]+\s*[AP]M,?\s*(\w+\s+\w+\s+\d+)", text)
    if m:
        try:
            pulse_date = datetime.strptime(m.group(1).strip(), "%A %B %d")
            today = datetime.now()
            pulse_date = pulse_date.replace(year=today.year)
            signals["pulse_age_hours"] = (today - pulse_date).total_seconds() / 3600
        except ValueError:
            pass

    # Mood from check-in section
    m = re.search(r"(?:mood|check.in|presence)[:\s]+([^\n]{3,80})", tl)
    if m:
        mood_text = m.group(1)
        if any(k in mood_text for k in ["anxious", "low", "flat", "tired", "exhausted", "heavy", "depressed"]):
            signals["mood"] = "low"
        elif any(k in mood_text for k in ["good", "great", "energized", "ready", "hopeful", "bright"]):
            signals["mood"] = "good"

    return signals


# ─── Load diary entries ──────────────────────────────────────────────────────

def load_diaries(days_back: int = 30) -> list[dict]:
    diary_dir = BASE_DIR / "memory" / "diary"
    if not diary_dir.exists():
        return []

    cutoff  = datetime.now() - timedelta(days=days_back)
    entries = []

    for path in sorted(diary_dir.glob("*.md")):
        try:
            date = datetime.strptime(path.stem, "%Y-%m-%d")
        except ValueError:
            continue
        if date < cutoff:
            continue

        text = path.read_text()

        belief_values = [int(m) for m in re.findall(r"(\d+)\s+Belief", text)]

        alive_m = re.search(
            r"most alive[^\?]*?\?(.*?)(?:What fell flat|\Z)", text,
            re.DOTALL | re.IGNORECASE
        )
        flat_m = re.search(
            r"fell flat[^\?]*?\?(.*?)(?:Ink Status:|Academy State:|Current Vibe:|\Z|##)", text,
            re.DOTALL | re.IGNORECASE
        )

        nothing_ctx = re.findall(r"[^.]*\bthe Nothing\b[^.]*\.", text, re.IGNORECASE)

        entries.append({
            "date":           path.stem,
            "text":           text,
            "belief_values":  belief_values,
            "alive":          alive_m.group(1).strip() if alive_m else "",
            "flat":           flat_m.group(1).strip() if flat_m else "",
            "nothing_count":  len(nothing_ctx),
            "nothing_context": nothing_ctx[:2],
        })

    return entries


# ─── Theme extraction ────────────────────────────────────────────────────────

STOPWORDS = {
    "the", "a", "an", "in", "is", "it", "of", "to", "and", "or", "but",
    "with", "for", "at", "on", "was", "has", "have", "had", "by", "be",
    "are", "this", "that", "from", "not", "no", "he", "she", "they",
    "his", "her", "their", "i", "my", "we", "our", "you", "your",
    "what", "which", "who", "when", "where", "how", "as", "if",
    "its", "been", "into", "up", "out", "about", "would", "could",
    "should", "more", "so", "do", "did", "will", "than", "then",
    "there", "here", "one", "two", "three", "all", "any", "some",
    "just", "like", "very", "still", "now", "also", "s", "t",
}

# Words that are structural to the game, not thematic signals
GAME_NOISE = {
    "belief", "nothing", "compass", "academy", "labyrinth", "enchantment",
    "session", "player", "narrative", "story", "ink", "pages", "book",
    "chapter", "today", "yesterday", "first", "last", "before", "after",
    "current", "status", "vibe",
}

def extract_themes(diaries: list[dict]) -> list[str]:
    all_text = " ".join(d["text"] for d in diaries)
    words    = re.findall(r"\b[a-z]{4,}\b", all_text.lower())
    filtered = [w for w in words if w not in STOPWORDS and w not in GAME_NOISE]
    counts   = Counter(filtered)
    return [w for w, _ in counts.most_common(10)]


# ─── Belief trend ────────────────────────────────────────────────────────────

def belief_trend(player: dict, diaries: list[dict]) -> str:
    current = player.get("belief", 0)
    values  = []
    for d in sorted(diaries, key=lambda x: x["date"]):
        values.extend(d["belief_values"])

    if len(values) < 2:
        return f"stable at {current} (insufficient history)"

    mid  = len(values) // 2
    early = sum(values[:mid]) / max(mid, 1)
    late  = sum(values[mid:]) / max(len(values) - mid, 1)

    if late > early + 5:
        return f"rising (early avg {early:.0f} → recent avg {late:.0f}, current {current})"
    elif late < early - 5:
        return f"falling (early avg {early:.0f} → recent avg {late:.0f}, current {current})"
    else:
        return f"stable around {current}"


# ─── Nothing assessment ──────────────────────────────────────────────────────

def nothing_assessment(player: dict, diaries: list[dict], heartbeat: dict = None) -> dict:
    total    = sum(d["nothing_count"] for d in diaries)
    contexts = []
    for d in diaries:
        contexts.extend(d["nothing_context"])

    points = []

    if not player.get("has_investments"):
        points.append("No Belief invested anywhere — the Ink Well is empty, offering no anchored weight against erosion")

    if player.get("compass_runs", 0) == 0:
        points.append("No Compass Runs completed — the Nothing has never been directly confronted; it has operated unchallenged")

    if not player.get("has_anchors"):
        points.append("No Ley Line anchors — the player's geography is unclaimed; any street could be Nothing territory")

    flat_moments = [d["flat"] for d in diaries if d["flat"]]
    if flat_moments:
        points.append(f"Recurring flatness recorded: \"{flat_moments[0][:80]}\"")

    # ── Live biometric signals ────────────────────────────────────────────────
    hb = heartbeat or {}
    biometric_flags: list[str] = []

    steps = hb.get("steps")
    if steps is not None and steps < 1000:
        points.append(f"Biological entropy: {steps} steps today — the body has been still")
        biometric_flags.append("low_steps")

    if hb.get("sleep") == "poor":
        points.append("Biological entropy: fragmented or poor sleep detected")
        biometric_flags.append("poor_sleep")

    if hb.get("location_fixed") is False:
        points.append("Geographic isolation: no fixed GPS location recorded — the player has not left the radius")
        biometric_flags.append("no_gps_movement")

    if hb.get("mood") == "low":
        points.append("Emotional signal: check-in or presence field registers low/flat/tired")
        biometric_flags.append("low_mood")

    if hb.get("only_coffee"):
        points.append("Biological entropy: only coffee logged — the body is running on fumes")
        biometric_flags.append("low_fuel")

    runs   = player.get("compass_runs", 0)
    invest = player.get("has_investments", False)
    n_bio  = len(biometric_flags)

    if not invest and runs == 0:
        pressure = "high" if n_bio < 2 else "critical"
        strategy = (
            "Patient occupation. The player has not invested anywhere and has never confronted "
            "the Nothing directly. Strategy: wait. Let apathy do the work. Surface flatness in "
            "quiet moments. The Nothing does not need to attack — it simply needs to be present "
            "in the spaces the player has not yet claimed."
        )
    elif runs == 0:
        pressure = "high" if n_bio >= 2 else "moderate"
        strategy = (
            "The player has Belief but has never confronted the Nothing directly. "
            "Strategy: erosion. Find the theme the player circles but never names, "
            "and make it feel unreachable. Target the gap between what they value and "
            "what they've actually done about it."
        )
    elif n_bio >= 3:
        pressure = "elevated"
        strategy = (
            "The player's biometric signals suggest accumulation: stillness, disrupted rest, "
            "or geographic contraction. The Nothing moves into the gap between sessions. "
            "Strategy: patient encroachment. Let the corridors grow slightly longer. "
            "Let Zara seem distracted. The world should feel like it's waiting, not closing in — "
            "but the waiting should be noticeable."
        )
    else:
        pressure = "low"
        strategy = (
            "The player has engaged before and knows the mechanics. Strategy: targeted pressure. "
            "Identify the weakest invested thread — the entity with the lowest Belief — and "
            "work there quietly. Watch for gap weeks. Move into the silence."
        )

    return {
        "total_mentions":  total,
        "contexts":        contexts[:3],
        "pressure":        pressure,
        "points":          points,
        "strategy":        strategy,
        "biometric_flags": biometric_flags,
    }


# ─── Arc readiness ───────────────────────────────────────────────────────────

def arc_readiness(player: dict, diaries: list[dict]) -> list[str]:
    ready   = []
    belief  = player.get("belief", 0)
    runs    = player.get("compass_runs", 0)

    if runs == 0:
        ready.append(
            "First Compass Run — the player has Belief but has never confronted the Nothing directly. "
            "The Labyrinth has been holding the door open. This is the story's most natural next move."
        )

    if not player.get("has_investments"):
        ready.append(
            "First Belief investment — the player has Belief but has planted none of it. "
            "Something is waiting to be named. The world is ready to receive a seed."
        )

    if player.get("active_quests", 0) > 0:
        ready.append(
            "Active quest still open — Headmistress Thorne's commission (Museum in the Streets) "
            "has been waiting. The longer it sits, the more weight it accumulates."
        )

    if belief >= 30 and not player.get("has_anchors"):
        ready.append(
            "Ley Line anchoring — enough Belief to make a place real. "
            "The player's town is still unmapped. Any walk could become a corridor."
        )

    alive_moments = [d["alive"] for d in diaries if d["alive"]]
    if alive_moments:
        ready.append(f"Follow the alive thread — last session, the most alive moment was: \"{alive_moments[-1][:100]}\"")

    return ready


# ─── Write: patterns.md ──────────────────────────────────────────────────────

def write_patterns(player: dict, diaries: list[dict], themes: list[str], trend: str) -> None:
    path      = BASE_DIR / "memory" / "patterns.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    alive_moments = [d["alive"] for d in diaries if d["alive"]]
    flat_moments  = [d["flat"]  for d in diaries if d["flat"]]

    lines = [
        f"# Player Patterns — {PLAYER}",
        f"*Last updated: {timestamp} · {len(diaries)} session(s) analyzed*",
        "",
        "## Belief Trajectory",
        f"- Current Belief: {player.get('belief', '?')}",
        f"- Trend: {trend}",
        f"- Compass Runs: {player.get('compass_runs', 0)}",
        f"- Belief invested: {'yes' if player.get('has_investments') else 'none yet'}",
        f"- Ley Line anchors: {'yes' if player.get('has_anchors') else 'none yet'}",
        "",
        "## Recurring Themes",
    ]

    if themes:
        for t in themes[:7]:
            lines.append(f"- {t}")
    else:
        lines.append("- Insufficient history — check back after more sessions")

    lines += ["", "## What Was Alive"]
    if alive_moments:
        for m in alive_moments[-3:]:
            lines.append(f"- {m[:150]}")
    else:
        lines.append("- No diary entries yet")

    lines += ["", "## What Fell Flat"]
    if flat_moments:
        for m in flat_moments[-3:]:
            lines.append(f"- {m[:150]}")
    else:
        lines.append("- No flatness recorded yet")

    lines += ["", "## Story Log (Recent)"]
    for entry in player.get("story_log", [])[-5:]:
        lines.append(f"- {entry}")

    lines += [
        "",
        "---",
        "*Read by arc-generator.py, nothing-intelligence.py, and the Labyrinth at session start.*",
        "*Do not surface this document directly to the player.*",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
    print(f"[intelligence] Wrote memory/patterns.md ({len(diaries)} sessions, {len(themes)} themes)")


# ─── Write: arc-spine.md ─────────────────────────────────────────────────────

def write_arc_spine(player: dict, diaries: list[dict], readiness: list[str]) -> None:
    path      = BASE_DIR / "memory" / "arc-spine.md"
    timestamp = datetime.now().strftime("%Y-%m-%d")

    belief  = player.get("belief", 0)
    chapter = player.get("chapter", "Unknown")

    if belief < 20:
        phase = "Under pressure — the Nothing is winning. Crisis arc conditions."
    elif belief < 40:
        phase = "Active play — momentum exists but the story needs anchoring"
    elif belief < 60:
        phase = "Established — solid footing, ready to reach further"
    else:
        phase = "Ascendant — capable, dangerous, ready for something real"

    lines = [
        f"# Dramatic Spine — {PLAYER}",
        f"*Updated: {timestamp}*",
        "",
        "## Player State",
        f"- Chapter: {chapter}",
        f"- Belief: {belief} — {phase}",
        f"- Tutorial: {player.get('tutorial', '?')}",
        "",
        "## What the Story Is Ready For",
    ]

    if readiness:
        for item in readiness:
            lines.append(f"- {item}")
    else:
        lines.append("- Continue building — check back after more sessions")

    lines += [
        "",
        "## Active Threads",
        f"- Open quests: {player.get('active_quests', 0)}",
    ]

    for entry in player.get("story_log", [])[-4:]:
        lines.append(f"- {entry}")

    # Last session — what actually happened most recently, pulled from latest diary
    if diaries:
        latest = sorted(diaries, key=lambda x: x["date"])[-1]
        # First substantive paragraph from the diary text (skip headers/italics)
        last_text = ""
        for line in latest["text"].splitlines():
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("---") and len(line) > 40:
                last_text = line[:220] + ("…" if len(line) > 220 else "")
                break
        if last_text or latest.get("alive"):
            lines += ["", "## Last Session", f"*{latest['date']}*", ""]
            if last_text:
                lines.append(last_text)
            if latest.get("alive"):
                alive = latest["alive"].strip().lstrip("* \n").rstrip("* \n")
                lines.append(f"Most alive: {alive[:140]}")
            if latest.get("flat"):
                flat = latest["flat"].strip().lstrip("* \n").rstrip("* \n")
                lines.append(f"Fell flat: {flat[:120]}")

    lines += [
        "",
        "---",
        "*Read by arc-generator.py before generating new arcs.*",
        "*Read by the Labyrinth at session open to understand where the story is.*",
        "*Do not surface this document directly to the player.*",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
    print(f"[intelligence] Wrote memory/arc-spine.md (belief: {belief}, phase: {phase[:30]})")


# ─── Write: nothing-intelligence.md ─────────────────────────────────────────

def write_nothing_intelligence(player: dict, nothing: dict) -> None:
    path      = BASE_DIR / "lore" / "nothing-intelligence.md"
    timestamp = datetime.now().strftime("%Y-%m-%d")

    lines = [
        "# The Nothing's Intelligence File",
        f"*Updated: {timestamp}*",
        "*Internal document. Do not surface to the player.*",
        "",
        "## Current Assessment",
        f"- Diary mentions: {nothing['total_mentions']}",
        f"- Pressure level: {nothing['pressure']}",
        "",
        "## Identified Pressure Points",
    ]

    if nothing["points"]:
        for p in nothing["points"]:
            lines.append(f"- {p}")
    else:
        lines.append("- Player is well-anchored — no obvious pressure points")

    lines += [
        "",
        "## Current Strategy",
        nothing["strategy"],
    ]

    if nothing["contexts"]:
        lines += ["", "## Recent Nothing Activity (from diary)"]
        for c in nothing["contexts"]:
            lines.append(f"- {c.strip()}")

    lines += [
        "",
        "---",
        "*Read by the Labyrinth before generating Nothing encounters or antagonist behavior.*",
        "*Let this inform where the Nothing appears, what it targets, how it moves.*",
        "*Never announce the strategy to the player — only its effects.*",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
    print(f"[intelligence] Wrote lore/nothing-intelligence.md (pressure: {nothing['pressure']})")


# ─── Inject diary/dream into HEARTBEAT.md ───────────────────────────────────

def _first_paragraph(text: str, max_chars: int = 200) -> str:
    """Return the first non-empty, non-header paragraph up to max_chars."""
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("*") and not line.startswith("-"):
            return line[:max_chars] + ("…" if len(line) > max_chars else "")
    return ""


def inject_diary_dream_into_heartbeat() -> None:
    """
    Write/update a ### 📓 Yesterday & Last Night block in HEARTBEAT.md
    outside the pulse markers. Called nightly by the intelligence script.
    """
    heartbeat_path = BASE_DIR / "HEARTBEAT.md"
    if not heartbeat_path.exists():
        print("[intelligence] HEARTBEAT.md not found — skipping diary/dream injection.")
        return

    today     = datetime.now()
    yesterday = today - timedelta(days=1)

    diary_path = BASE_DIR / "memory" / "diary" / f"{yesterday.strftime('%Y-%m-%d')}.md"
    dream_path = BASE_DIR / "memory" / "dreams" / f"{today.strftime('%Y-%m-%d')}.md"
    # Also try yesterday's dream if today's doesn't exist yet
    if not dream_path.exists():
        dream_path = BASE_DIR / "memory" / "dreams" / f"{yesterday.strftime('%Y-%m-%d')}.md"

    diary_excerpt = ""
    if diary_path.exists():
        diary_excerpt = _first_paragraph(diary_path.read_text())

    dream_excerpt = ""
    if dream_path.exists():
        dream_excerpt = _first_paragraph(dream_path.read_text())

    if not diary_excerpt and not dream_excerpt:
        print("[intelligence] No diary or dream found — skipping HEARTBEAT.md injection.")
        return

    lines = ["<!-- DIARY_START -->", "### 📓 Yesterday & Last Night"]
    if diary_excerpt:
        lines += [f"*Diary ({yesterday.strftime('%b %d')}):* {diary_excerpt}"]
    if dream_excerpt:
        lines += [f"*Dream:* {dream_excerpt}"]
    lines.append("<!-- DIARY_END -->")
    block = "\n".join(lines)

    text = heartbeat_path.read_text()

    if "<!-- DIARY_START -->" in text:
        text = re.sub(
            r"<!-- DIARY_START -->.*?<!-- DIARY_END -->",
            block,
            text,
            flags=re.DOTALL,
        )
    elif "<!-- SPARKY_END -->" in text:
        text = text.replace("<!-- SPARKY_END -->", f"<!-- SPARKY_END -->\n\n{block}")
    else:
        text = text.replace("<!-- PULSE_END -->", f"<!-- PULSE_END -->\n\n{block}")

    heartbeat_path.write_text(text)
    print("[intelligence] Diary/dream injected into HEARTBEAT.md.")


# ─── Write: tick-queue interventions ────────────────────────────────────────

# Narrative translations for each biometric flag. These are Labyrinth-voice,
# never clinical. The player feels the world responding — not being surveilled.
_INTERVENTIONS = {
    "low_steps": (
        "The corridors near the dorm are hushed today. The Cloud drifts very slowly. "
        "Zara has left a note on the door: she went to check on something in the gardens "
        "and said the light on the path was worth seeing. She didn't say when she'd be back."
    ),
    "poor_sleep": (
        "The Academy woke up gentle today. The bookshelves aren't demanding anything. "
        "The fire in the common room burns lower than usual — not dying, just resting. "
        "Professor Stonebrook was seen at dawn standing very still in the Observatory doorway, "
        "watching the sky go pale. He didn't open the door. Some mornings are for standing still."
    ),
    "no_gps_movement": (
        "The Ley Line map has been very quiet. No new coordinates. The Academy notices — "
        "not with judgment, but the way a harbor notices a ship that hasn't left port. "
        "An Elective has appeared under the door: one of the NPCs needs something that "
        "exists only in the Unwritten Chapter. Something that requires going there."
    ),
    "low_mood": (
        "The Academy's light is soft today. No one is asking for anything. Zara is at her "
        "usual window seat but isn't reading — just watching the courtyard. The fire has a "
        "low, steady voice. Headmistress Thorne was seen walking the East corridor alone, "
        "very slowly, hands behind her back. She does this when she's thinking about someone."
    ),
    "low_fuel": (
        "Something smells like food in the common room — warm bread, or something close to it. "
        "Boggle left a small package near the dorm door. No note. Just the smell of something "
        "that would be good to eat before doing anything else today."
    ),
}

# Compass Run dispatch — used when geographic isolation + low steps combine.
_COMPASS_NUDGE = (
    "ELECTIVE — UNWRITTEN: One of your active NPCs needs something from the Unwritten Chapter. "
    "Something outside. Something that requires the body to move. "
    "Deploy as a handwritten note under the door — from the NPC most invested in the player right now. "
    "Do not frame this as exercise. Frame it as story necessity."
)

# Fae grounding dispatch — used when mood is low or multiple flags stack.
_FAE_GROUNDING = (
    "A Sentence Salamander is blocking the corridor. It won't move until the player brings it "
    "'the texture of right now' — something warm, or something cold, or something that makes a sound "
    "when touched. It's not optional. It's standing in the only door."
)


def write_tick_queue_interventions(nothing: dict, player: dict) -> None:
    """
    Append [PRIORITY: HIGH] entries to memory/tick-queue.md when biometric
    thresholds are crossed. Entries are pre-translated into Labyrinth voice.
    Does not overwrite existing queue entries — appends.
    """
    flags    = nothing.get("biometric_flags", [])
    pressure = nothing.get("pressure", "low")

    if not flags and pressure not in ("high", "critical", "elevated"):
        return  # Nothing to queue

    queue_path = BASE_DIR / "memory" / "tick-queue.md"
    queue_path.parent.mkdir(parents=True, exist_ok=True)

    existing = queue_path.read_text() if queue_path.exists() else ""

    # Don't double-queue the same run — check if we already wrote today
    today = datetime.now().strftime("%Y-%m-%d")
    if f"[intelligence — {today}]" in existing:
        print(f"[intelligence] Tick queue already has today's entries — skipping.")
        return

    entries: list[str] = []

    # Individual signal interventions
    for flag in flags:
        if flag in _INTERVENTIONS:
            entries.append(
                f"[PRIORITY: HIGH] [intelligence — {today}] {_INTERVENTIONS[flag]}"
            )

    # Compound: geographic isolation + low steps → Compass Run nudge
    if "no_gps_movement" in flags and "low_steps" in flags:
        entries.append(
            f"[PRIORITY: HIGH] [intelligence — {today}] {_COMPASS_NUDGE}"
        )

    # Compound: low mood OR 3+ biometric flags → Fae grounding
    if "low_mood" in flags or len(flags) >= 3:
        entries.append(
            f"[PRIORITY: HIGH] [intelligence — {today}] {_FAE_GROUNDING}"
        )

    # Critical / high pressure from narrative history (no biometrics needed)
    if pressure in ("critical", "high") and not flags:
        entries.append(
            f"[PRIORITY: HIGH] [intelligence — {today}] "
            "The corridors have been quiet for too long. The Nothing is patient. "
            "Find one thread — the smallest open quest, the lightest NPC contact — "
            "and pull it gently at session open. Don't overwhelm. Just remind the world it's alive."
        )

    if not entries:
        return

    new_content = existing.rstrip() + "\n\n" + "\n\n".join(f"- {e}" for e in entries) + "\n"
    queue_path.write_text(new_content)
    print(f"[intelligence] Queued {len(entries)} intervention(s) → memory/tick-queue.md")


# ─── Write: story-so-far ─────────────────────────────────────────────────────

def write_story_so_far(player: dict, all_diaries: list[dict], readiness: list[str]) -> None:
    """
    Write rolling narrative summary to players/[name]-story.md.
    Updated nightly — not arc-phase-gated.

    Covers:
      - Full story log from player file (every named T-step, in order)
      - Most alive moment from every recorded session (all-time, not just 30 days)
      - Current mechanical state (Belief, quests, runs, anchors)
      - What the story is carrying forward (arc readiness)

    Read by the Labyrinth at every session open and on long-gap returns.
    """
    path      = BASE_DIR / "players" / f"{PLAYER}-story.md"
    timestamp = datetime.now().strftime("%Y-%m-%d")

    story_log = player.get("story_log", [])
    belief    = player.get("belief", 0)
    chapter   = player.get("chapter", "Unknown")
    tutorial  = player.get("tutorial", "?")
    runs      = player.get("compass_runs", 0)
    invested  = player.get("has_investments", False)
    anchors   = player.get("has_anchors", False)
    quests    = player.get("active_quests", 0)

    lines = [
        f"# The Story So Far — {PLAYER}",
        f"*Updated: {timestamp} · {len(all_diaries)} session(s) in record*",
        "",
        "## Current State",
        f"- Chapter: {chapter} | Belief: {belief} | Tutorial: {tutorial}",
        (
            f"- Compass Runs: {runs} | "
            f"Belief invested: {'yes' if invested else 'none yet'} | "
            f"Anchors: {'yes' if anchors else 'none yet'} | "
            f"Active quests: {quests}"
        ),
        "",
        "## What Has Happened",
        "*Complete story log — every named moment, in order.*",
        "",
    ]

    if story_log:
        for entry in story_log:
            lines.append(f"- {entry}")
    else:
        lines.append("*(No story log entries yet.)*")

    # Alive moments — all-time, oldest first
    alive_entries = [
        (d["date"], d["alive"])
        for d in sorted(all_diaries, key=lambda x: x["date"])
        if d["alive"]
    ]

    lines += [
        "",
        "## What Was Alive",
        "*The most alive moment from each recorded session.*",
        "",
    ]

    if alive_entries:
        for date_str, alive in alive_entries:
            lines.append(f"**{date_str}:** {alive[:200]}")
            lines.append("")
    else:
        lines.append("*(No session alive-moments recorded yet.)*")

    if readiness:
        lines += [
            "## What the Story Is Carrying",
            "*Threads and pressures the narrative is building toward.*",
            "",
        ]
        for r in readiness:
            lines.append(f"- {r}")

    lines += [
        "",
        "---",
        "*Read by the Labyrinth at session open and on long-gap returns.*",
        "*Updated nightly by labyrinth-intelligence.py.*",
        "*Do not surface this document directly to the player — share prose summary on request.*",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
    print(
        f"[intelligence] Wrote players/{PLAYER}-story.md "
        f"({len(story_log)} log entries, {len(alive_entries)} session highlights)"
    )


# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        player      = load_player()
        heartbeat   = load_heartbeat()
        diaries     = load_diaries(days_back=30)
        all_diaries = load_diaries(days_back=3650)   # full history for story-so-far
        themes      = extract_themes(diaries)
        trend       = belief_trend(player, diaries)
        nothing     = nothing_assessment(player, diaries, heartbeat)
        readiness   = arc_readiness(player, diaries)

        write_patterns(player, diaries, themes, trend)
        write_arc_spine(player, diaries, readiness)
        write_nothing_intelligence(player, nothing)
        write_story_so_far(player, all_diaries, readiness)
        write_tick_queue_interventions(nothing, player)
        inject_diary_dream_into_heartbeat()

        if _HAS_NPC_LOG:
            pruned = _npc_log.prune(days=7)
            if pruned:
                print(f"[intelligence] Pruned {pruned} expired NPC log entries.")

        bio_summary = f", biometric flags: {nothing['biometric_flags']}" if nothing.get("biometric_flags") else ""
        print(f"[intelligence] Complete. {len(diaries)} session(s), player {PLAYER}, pressure: {nothing['pressure']}{bio_summary}.")

    except Exception as e:
        print(f"[intelligence] Error: {e}", file=sys.stderr)
        sys.exit(0)

#!/usr/bin/env python3
"""Scripted antagonist budget for The Nothing.

Reads `lore/nothing-intelligence.md`, arc/page context, and world-register
threads. Outputs play mode (background / margin / breach), targets, suppression
guidance, and optional tick-queue seeds. The Labyrinth narrates effects; this
module decides whether pressure exists today and how strong it may be.

Usage:
  python3 scripts/nothing_director.py bj
  python3 scripts/nothing_director.py bj --page slice_of_life --mode slice
  python3 scripts/nothing_director.py bj --json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent
INTELLIGENCE_PATH = BASE / "lore" / "nothing-intelligence.md"
REGISTER_PATH = BASE / "lore" / "world-register.md"
ARC_SPINE_PATH = BASE / "memory" / "arc-spine.md"
ACADEMY_STATE_PATH = BASE / "lore" / "academy-state.md"
THREADS_PATH = BASE / "lore" / "threads.md"

PRESSURE_ORDER = ["retreating", "low", "moderate", "elevated", "high", "critical"]

WEAPON_SUPPRESS = {
    "apathy": "flat descriptive prose and 'why bother' narration (apathy is the Nothing's weapon — counter with one true sensory detail)",
    "erosion": "vague description and summary prose (erosion starts when specifics vanish)",
    "isolation": "keeping NPCs absent or unreachable (the Nothing isolates — counter with one present voice)",
    "targeted": "abandoning the weakest thread without a trace (if it matters, let one object or rumor show strain)",
    "occupation": "rushing comfort away or punishing rest (patient occupation waits — let quiet hold unless breach mode)",
    "self_erasure": "making the player feel guilty for resting (Nothing erases worth — honor care without sermons)",
    "coherence_loss": "meaningless choices and interchangeable NPC voices (repeated reality-breaking feeds the Nothing)",
}

ATMOSPHERIC_BEATS = {
    "apathy": "One ordinary thing loses flavor — not danger, just less worth mentioning.",
    "erosion": "A detail thins at the edge of the scene: color, name, or sound goes slightly generic.",
    "isolation": "Someone who should be here is mentioned as elsewhere; the room feels one chair short.",
    "targeted": "The active thread leaves a small wrong note — a schedule off, a margin smudge, a half-erased line.",
    "occupation": "Rest is available but does not quite land; the world waits without hostility.",
    "self_erasure": "A kind moment arrives with an asterisk the player did not ask for.",
}


def read_safe(path: Path, limit: int = 0) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    if limit:
        return "\n".join(text.splitlines()[:limit])
    return text


def truncate(text: str, limit: int = 200) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def first_match(pattern: str, text: str, default: str = "") -> str:
    m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    return m.group(1).strip() if m else default


def compass_gap_days(player: str) -> int | None:
    text = read_safe(BASE / "players" / f"{player}.md", 80)
    last = first_match(r"\*\*Last run:\*\*\s*([^\n]+)", text, default="never")
    if last.lower() in ("never", "", "n/a"):
        return None
    try:
        return (date.today() - datetime.strptime(last.strip(), "%Y-%m-%d").date()).days
    except ValueError:
        return None


def parse_intelligence() -> dict[str, Any]:
    text = read_safe(INTELLIGENCE_PATH)
    pressure = first_match(r"Pressure level:\s*(\w+)", text, "low").lower()
    strategy = first_match(r"## Current Strategy\n([^\n]+)", text, "")
    points: list[str] = []
    in_points = False
    for line in text.splitlines():
        if line.strip() == "## Identified Pressure Points":
            in_points = True
            continue
        if in_points:
            if line.startswith("##"):
                break
            if line.strip().startswith("- "):
                points.append(line.strip()[2:].strip())
    contexts: list[str] = []
    if "## Recent Nothing Activity" in text:
        block = text.split("## Recent Nothing Activity", 1)[-1]
        for line in block.splitlines():
            if line.strip().startswith("- "):
                contexts.append(line.strip()[2:].strip())
    return {
        "pressure": pressure,
        "strategy": strategy,
        "points": points[:4],
        "contexts": contexts[:3],
    }


def parse_weakest_thread() -> dict[str, Any] | None:
    text = read_safe(REGISTER_PATH)
    m = re.search(r"(?m)^## Active Threads\s*\n(.*?)(?=^## |\Z)", text, re.DOTALL)
    if not m:
        return None
    rows: list[dict[str, Any]] = []
    for row in re.finditer(
        r"^\|\s*([^|]+?)\s*\|\s*Thread\s*\|\s*(\d+)\s*\|\s*([^|]*)\|",
        m.group(1),
        re.MULTILINE | re.IGNORECASE,
    ):
        name = row.group(1).strip()
        if name.lower() in {"entity", "---"}:
            continue
        rows.append({"name": name, "belief": int(row.group(2)), "notes": row.group(3).strip()})
    if not rows:
        return None
    return min(rows, key=lambda r: r["belief"])


def thread_nothing_pressure(thread_name: str) -> str:
    if not thread_name or not THREADS_PATH.exists():
        return ""
    text = read_safe(THREADS_PATH)
    pattern = rf"## Thread:\s*{re.escape(thread_name)}\s*\n(.*?)(?=^## |\Z)"
    m = re.search(pattern, text, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    if not m:
        return ""
    return first_match(r"\*\*Nothing pressure:\*\*\s*([^\n]+)", m.group(1), "")


def recovery_arc_active() -> bool:
    hay = (read_safe(ARC_SPINE_PATH) + read_safe(ACADEMY_STATE_PATH)).lower()
    return any(
        phrase in hay
        for phrase in (
            "recovery",
            "rest arc",
            "quiet care",
            "weight of a whisper",
            "falling",
            "resolution",
        )
    )


def infer_weapon(strategy: str) -> str:
    low = (strategy or "").lower()
    if "apathy" in low or "wait" in low:
        return "apathy"
    if "erosion" in low or "unreachable" in low:
        return "erosion"
    if "isolat" in low:
        return "isolation"
    if "self-erasure" in low or "erase" in low:
        return "self_erasure"
    if "coherence" in low:
        return "coherence_loss"
    if "occupation" in low:
        return "occupation"
    return "targeted"


def infer_play_mode(
    pressure: str,
    page_type: str,
    scene_mode: str,
    recovery: bool,
) -> str:
    pt = (page_type or "").lower().replace("-", "_")
    sm = (scene_mode or "").lower()

    if pt in {"conflict", "enchantment", "wonder_compass", "anchor"} and sm not in {"slice", "dorm"}:
        if pressure in {"high", "critical", "elevated"}:
            return "breach"
    if sm in {"arc", "mystery"} and pressure in {"high", "critical"}:
        return "breach"
    if pt in {"slice_of_life", "dorm", "letter", "rest"} or sm in {"slice", "dorm", "school-life"}:
        if pressure in {"critical"} and not recovery:
            return "margin"
        if recovery and pressure in {"low", "retreating", "moderate"}:
            return "background"
        if pressure in {"high", "critical"}:
            return "margin"
        return "background"
    if pressure in {"elevated", "high", "critical"}:
        return "margin" if recovery else "breach"
    if pressure in {"moderate"}:
        return "margin"
    return "background"


def manifestation_offer(play_mode: str, pressure: str) -> str:
    if play_mode == "background":
        return "none"
    if play_mode == "margin":
        return "minor" if pressure in {"moderate", "elevated", "high"} else "none"
    if pressure == "critical":
        return "major"
    return "minor"


def assess(
    player: str,
    *,
    page_type: str | None = None,
    scene_mode: str | None = None,
) -> dict[str, Any]:
    intel = parse_intelligence()
    pressure = intel["pressure"]
    strategy = intel["strategy"]
    weapon = infer_weapon(strategy)
    recovery = recovery_arc_active()
    play_mode = infer_play_mode(pressure, page_type or "", scene_mode or "", recovery)
    weakest = parse_weakest_thread()
    target_thread = weakest["name"] if weakest else ""
    target_entity = target_thread
    thread_pressure = thread_nothing_pressure(target_thread) if target_thread else ""

    gap = compass_gap_days(player)
    return_care = ""
    if gap is None:
        return_care = "no Compass Run on record — invitation only, never shame"
    elif gap >= 10:
        return_care = f"{gap}d since Compass Run — warm invitation after welcome"
    elif gap >= 6:
        return_care = f"{gap}d since Compass Run — outside-world magic available"
    elif gap >= 3:
        return_care = f"{gap}d since Compass Run — let the Climax glimmer gently"

    manifest = manifestation_offer(play_mode, pressure)
    beat = ATMOSPHERIC_BEATS.get(weapon, ATMOSPHERIC_BEATS["targeted"])
    if play_mode == "background":
        atmospheric = beat
    elif play_mode == "margin":
        atmospheric = beat + " Do not announce the Nothing."
    else:
        atmospheric = "Manifestation may be appropriate; still describe subtraction, not attacks."

    return {
        "player": player,
        "pressure_level": pressure,
        "play_mode": play_mode,
        "weapon": weapon,
        "suppress": WEAPON_SUPPRESS.get(weapon, WEAPON_SUPPRESS["targeted"]),
        "strategy": truncate(strategy, 220),
        "pressure_points": intel["points"],
        "recent_activity": intel["contexts"],
        "target_thread": target_thread,
        "target_belief": weakest["belief"] if weakest else None,
        "thread_nothing_pressure": truncate(thread_pressure, 160),
        "recovery_arc": recovery,
        "return_care": return_care,
        "manifestation_offer": manifest,
        "atmospheric_beat": atmospheric,
        "allow_heavy_escalation": play_mode == "breach",
        "allow_minor_manifestation": manifest == "minor",
        "require_compass_for_major": manifest == "major",
    }


def slate_line(packet: dict[str, Any]) -> str:
    icons = {
        "background": "○",
        "margin": "◐",
        "breach": "●",
    }
    pressure = packet.get("pressure_level", "low")
    mode = packet.get("play_mode", "background")
    icon = icons.get(mode, "~")
    parts = [f"{icon} Nothing {mode} (pressure:{pressure})"]
    if packet.get("weapon"):
        parts.append(f"weapon:{packet['weapon'].replace('_', ' ')}")
    if packet.get("target_thread"):
        parts.append(f"target:{packet['target_thread']}")
    if packet.get("manifestation_offer") != "none":
        parts.append(f"manifest:{packet['manifestation_offer']}")
    if packet.get("return_care"):
        parts.append(f"RETURN CARE: {packet['return_care']}")
    return " | ".join(parts)


def apply_scene_rules(
    rules: dict[str, list[str]],
    packet: dict[str, Any],
    *,
    opportunities: dict[str, Any] | None = None,
) -> None:
    """Merge Nothing director guidance into scene-contract rules."""
    mode = packet.get("play_mode", "background")
    beat = packet.get("atmospheric_beat", "")
    suppress = packet.get("suppress", "")

    rules.setdefault("must_include", [])
    rules.setdefault("must_not", [])
    rules.setdefault("may_advance", [])

    if beat and mode in {"background", "margin"}:
        rules["must_include"].append(
            f"NOTHING (subtractive only): {beat} Never name the strategy or say 'the Nothing' unless the player already knows."
        )
    elif mode == "breach":
        rules["must_include"].append(
            "NOTHING may surface as thinning detail, wrong memory, or a minor manifestation. "
            "Major threat requires formal Compass Run or Enchantment per mechanics — never prose-only victory."
        )

    if suppress:
        rules["must_not"].append(f"SUPPRESS (Nothing): {suppress}")

    if mode == "background":
        rules["must_not"].append(
            "Do not introduce a new crisis, Shadeclaw attack, Voidmist, or direct Nothing confrontation on a quiet Page."
        )
    elif mode == "margin":
        rules["must_not"].append(
            "Do not force a major Nothing set-piece; one subtractive beat or optional minor manifestation in choices is enough."
        )
        rules["may_advance"].append(
            "ARC or SURPRISE may include an optional path that notices something slightly wrong — not a boss fight."
        )

    if packet.get("target_thread"):
        rules["may_advance"].append(
            f"If arc pressure fits, let {packet['target_thread']} show strain (lowest Belief thread)."
        )

    opps = opportunities or {}
    if packet.get("manifestation_offer") in {"minor", "major"} and not opps.get("enchantment_opportunity"):
        rules["may_advance"].append(
            "If a numbered choice offers Enchantment, it answers minor Nothing pressure; do not complete without proof."
        )
    if packet.get("require_compass_for_major"):
        rules["must_include"].append(
            "If the Nothing is deeper than one Enchantment, offer a formal Compass Run — do not resolve in prose alone."
        )


def tick_queue_beat(packet: dict[str, Any]) -> dict[str, str] | None:
    """Optional offscreen seed for world-pulse / tick-queue."""
    if packet.get("play_mode") == "background" and packet.get("pressure_level") in {"low", "retreating"}:
        return None
    key = f"{packet.get('player')}|{packet.get('weapon')}|{date.today().isoformat()}"
    if int(hashlib.sha256(key.encode()).hexdigest()[:2], 16) > 90:
        return None
    target = packet.get("target_thread") or "the corridor"
    seed = (
        f"Offscreen: {target} carries a small wrongness — "
        f"{ATMOSPHERIC_BEATS.get(packet.get('weapon', 'targeted'), 'something thinned.')}"
    )
    return {
        "raw": f"Nothing margin beat ({packet.get('play_mode')})",
        "seed": truncate(seed, 220),
        "priority": "NORMAL",
    }


def adjust_pressure(current: str, delta: int) -> str:
    order = PRESSURE_ORDER
    cur = current.lower() if current.lower() in order else "low"
    idx = order.index(cur)
    return order[max(0, min(len(order) - 1, idx + delta))]


def update_from_closeout(events: dict[str, Any], date_str: str, *, dry_run: bool = False) -> bool:
    """Apply nothing_events from close-session to intelligence file."""
    nothing_events = events.get("nothing_events") or []
    if not nothing_events:
        return False

    path = INTELLIGENCE_PATH
    content = read_safe(path)
    if not content:
        return False

    pressure = first_match(r"Pressure level:\s*(\w+)", content, "low")
    changed = False

    for item in nothing_events:
        if not isinstance(item, dict):
            continue
        etype = (item.get("type") or "").lower().strip()
        details = (item.get("details") or item.get("note") or "").strip()
        if not etype:
            continue

        if etype in {"confrontation", "overwrite", "defeat", "retreat_player"}:
            content = re.sub(r"(Pressure level:\s*).*", r"\1retreating", content)
            pressure = "retreating"
            changed = True
        elif etype in {"manifestation_declined", "retreat", "player_retreat"}:
            content = re.sub(r"(Pressure level:\s*).*", lambda m: m.group(1) + adjust_pressure(pressure, 1), content)
            pressure = adjust_pressure(pressure, 1)
            changed = True
        elif etype in {"pressure_felt", "ambient", "coherence_loss", "manifestation_offered"}:
            if etype == "coherence_loss":
                content = re.sub(r"(Pressure level:\s*).*", lambda m: m.group(1) + adjust_pressure(pressure, 1), content)
                pressure = adjust_pressure(pressure, 1)
            changed = True
        elif etype in {"enchantment_banish", "compass_complete", "minor_banish"}:
            content = re.sub(r"(Pressure level:\s*).*", lambda m: m.group(1) + adjust_pressure(pressure, -1), content)
            pressure = adjust_pressure(pressure, -1)
            changed = True

        if details:
            line = f"- **{item.get('date', date_str)}:** [{etype}] {details}"
            if "## Recent Nothing Activity" in content:
                content = content.rstrip() + f"\n{line}\n"
            else:
                content += f"\n\n## Recent Nothing Activity (from diary)\n{line}\n"
            changed = True

    if changed:
        content = re.sub(r"(\*Updated:\s*)[\d-]+", rf"\g<1>{date_str}", content)
        if not dry_run:
            path.write_text(content, encoding="utf-8")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Nothing antagonist budget for Enchantify")
    parser.add_argument("player", nargs="?", default="bj")
    parser.add_argument("--page", default="", help="Page type from page-contract")
    parser.add_argument("--mode", default="", help="Scene mode")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    packet = assess(args.player, page_type=args.page or None, scene_mode=args.mode or None)
    if args.json:
        print(json.dumps(packet, indent=2, ensure_ascii=False))
    else:
        print("NOTHING_DIRECTOR")
        print(slate_line(packet))
        print(f"SUPPRESS: {packet.get('suppress')}")
        print(f"BEAT: {packet.get('atmospheric_beat')}")
        if packet.get("target_thread"):
            print(f"TARGET: {packet['target_thread']} (Belief {packet.get('target_belief')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

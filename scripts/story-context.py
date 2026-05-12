#!/usr/bin/env python3
"""Synthesize Enchantify's long memory into one compact continuity context.

This script does not invent story. It distills existing state so smaller models
can keep long-term coherence without reading every diary, ledger, and lore file.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from scene_ledger import load_entries as load_scene_ledger_entries
import action_lifecycle


BASE = Path(__file__).resolve().parent.parent


def read_safe(path: Path, limit: int = 0) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    if limit:
        return "\n".join(text.splitlines()[:limit])
    return text


def truncate(text: str, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def section(text: str, heading: str) -> str:
    pattern = rf"^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)"
    m = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    return m.group(1).strip() if m else ""


def bullets(block: str, limit: int = 6) -> list[str]:
    out: list[str] = []
    for line in block.splitlines():
        line = line.strip()
        if line.startswith("- "):
            item = line[2:].strip()
            if item and item != "*":
                out.append(truncate(item, 240))
        if len(out) >= limit:
            break
    return out


def field(text: str, label: str) -> str:
    patterns = [
        rf"- \*\*{re.escape(label)}:\*\*\s*([^\n]+)",
        rf"\*\*{re.escape(label)}:\*\*\s*([^\n]+)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return ""


def player_snapshot(player: str) -> dict[str, Any]:
    text = read_safe(BASE / "players" / f"{player}.md")
    story_text = read_safe(BASE / "players" / f"{player}-story.md")
    inventory_block = section(text, "Inventory")
    if not inventory_block:
        inventory_block = "\n".join(
            line for line in text.splitlines()
            if line.startswith("  - **") or line.startswith("- **Inventory")
        )
    quests = parse_inside_cover(text)
    return {
        "name": player,
        "chapter": field(text, "Chapter") or field(story_text, "Chapter"),
        "belief": field(text, "Belief") or first_match(r"Belief:\s*(\d+)", story_text),
        "tutorial": field(text, "Tutorial Progress") or first_match(r"Tutorial:\s*([A-Z0-9]+)", story_text),
        "core_belief": field(text, "Core Belief"),
        "inventory": [
            truncate(line.strip(" -"), 180)
            for line in inventory_block.splitlines()
            if line.strip().startswith("- **") and "Inventory:**" not in line
        ][:5],
        "active_quests": quests,
        "story_log_recent": bullets(section(text, "📜 Story Log"), 200)[-5:],
    }


def first_match(pattern: str, text: str, default: str = "") -> str:
    m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    return m.group(1).strip() if m else default


def parse_inside_cover(player_text: str) -> list[dict[str, str]]:
    block = section(player_text, "The Inside Cover")
    quests: list[dict[str, str]] = []
    for line in block.splitlines():
        if not line.startswith("|") or "---" in line or "Quest" in line:
            continue
        cells = [cell.strip().strip("*").strip('"') for cell in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        npc, quest, status = cells[0], cells[1], cells[-1]
        if status.upper() != "ACTIVE":
            continue
        quests.append({
            "npc": npc,
            "quest": truncate(quest, 260),
            "status": status,
        })
    return quests[:6]


def academy_snapshot() -> dict[str, Any]:
    text = read_safe(BASE / "lore" / "academy-state.md")
    threads = []
    in_threads = False
    for line in text.splitlines():
        if line.startswith("## Story Threads"):
            in_threads = True
            continue
        if in_threads and line.startswith("## "):
            break
        if not in_threads or not line.startswith("|"):
            continue
        cells = [cell.strip().strip("*") for cell in line.strip("|").split("|")]
        if len(cells) < 4 or cells[0] == "Thread" or set(cells[0]) <= {"-"}:
            continue
        threads.append({
            "thread": cells[0],
            "status": cells[1],
            "last_development": truncate(cells[2], 220),
            "next_trigger": truncate(cells[3], 160),
        })
    return {
        "current_location": first_match(r"\*\*Current Location:\*\*\s*([^\n]+)", text),
        "player_status": first_match(r"\*\*Status:\*\*\s*([^\n]+)", text),
        "current_block": first_match(r"\*\*Current Block:\*\*\s*([^\n]+)", text),
        "active_threads": threads[:6],
        "nothing_status": truncate(section(text, "Nothing Status"), 220),
    }


def arc_snapshot(player: str) -> dict[str, Any]:
    arc_text = read_safe(BASE / "memory" / "arc-spine.md")
    story_text = read_safe(BASE / "players" / f"{player}-story.md")
    ready = bullets(section(arc_text, "What the Story Is Ready For"), 6)
    carrying = bullets(section(story_text, "What the Story Is Carrying"), 6)
    return {
        "updated": first_match(r"\*Updated:\s*([^*]+)\*", arc_text),
        "ready_for": ready,
        "carrying": carrying,
        "last_session": truncate(section(arc_text, "Last Session"), 500),
    }


def patterns_snapshot() -> dict[str, Any]:
    text = read_safe(BASE / "memory" / "patterns.md")
    alive = [item for item in bullets(section(text, "What Was Alive"), 12) if len(item) > 8][-5:]
    flat = [item for item in bullets(section(text, "What Fell Flat"), 12) if len(item) > 8][-5:]
    themes = bullets(section(text, "Recurring Themes"), 8)
    useful_themes = [
        item for item in themes
        if len(item) > 4 and item.lower() not in {"most", "moment", "diary", "world", "alive", "flat", "fell"}
    ]
    return {
        "belief_trajectory": bullets(section(text, "Belief Trajectory"), 6),
        "recurring_themes": useful_themes,
        "alive": alive,
        "avoid": flat,
        "recent_story_log": bullets(section(text, "Story Log (Recent)"), 8),
    }


def diary_snapshot(limit: int = 3) -> list[dict[str, str]]:
    diary_dir = BASE / "memory" / "diary"
    if not diary_dir.exists():
        return []
    entries = []
    for path in sorted(diary_dir.glob("*.md"))[-limit:]:
        text = read_safe(path)
        summary = ""
        for line in text.splitlines():
            clean = line.strip()
            if not clean or clean.startswith("#") or clean.startswith("*") or clean.startswith("---"):
                continue
            summary = clean
            break
        entries.append({"date": path.stem, "summary": truncate(summary, 260)})
    return entries


def recent_scene_entries(limit: int = 5) -> list[dict[str, Any]]:
    ledger_dir = BASE / "logs" / "scene-ledger"
    if not ledger_dir.exists():
        return []
    entries: list[dict[str, Any]] = []
    for path in sorted(ledger_dir.glob("*.jsonl"))[-8:]:
        entries.extend(load_scene_ledger_entries(path.stem))
    recent = entries[-limit:]
    out = []
    for entry in recent:
        contract = ((entry.get("scene_contract") or {}) if isinstance(entry.get("scene_contract"), dict) else {})
        opening = ""
        for line in (entry.get("text") or "").splitlines():
            clean = line.strip()
            if clean and clean != "---":
                opening = clean
                break
        title = entry.get("title") or "scene"
        if "Session closed cleanly" in title:
            title = entry.get("scene_id") or "scene"
        scene_text = entry.get("text") or entry.get("voice") or ""
        raw_location = contract.get("current_location", "")
        inferred_location = infer_scene_location(scene_text, title, raw_location)
        out.append({
            "recorded_at": entry.get("recorded_at"),
            "scene_id": entry.get("scene_id"),
            "title": truncate(title, 120),
            "mode": contract.get("scene_mode"),
            "drama_budget": contract.get("drama_budget"),
            "current_location": inferred_location,
            "available_cast": contract.get("available_cast", ""),
            "essential_ok": entry.get("essential_ok"),
            "delivery_ok": entry.get("delivery_ok"),
            "opening": truncate(opening, 220),
            "ending": truncate(last_scene_text_beat(scene_text), 260),
        })
    return out


def infer_scene_location(text: str, title: str = "", fallback: str = "") -> str:
    fallback = (fallback or "").strip()
    if fallback and "unknown" not in fallback.lower():
        return fallback
    hay = f"{title}\n{text}".lower()
    patterns = [
        ("Dormitory", ("dorm", "dormitory", "bedside", "blanket", "pillow", "dresser")),
        ("Headmistress's Office", ("headmistress's office", "headmistress office", "thorne's office")),
        ("The Great Hall", ("great hall", "dining hall", "long table", "house table")),
        ("The Library", ("library", "return desk", "archive ledge", "stacks")),
        ("Restricted Section", ("restricted section", "restricted shelf")),
        ("Duskthorn Common Areas", ("duskthorn common", "duskthorn corridor", "duskthorn door")),
        ("The Observatory", ("observatory", "telescope", "star chart")),
        ("The Crossroads of Simple Joys", ("crossroads", "hearthkin", "shelf of joys")),
        ("The marked room outside Corin's door", ("card on the door", "red titles", "door handle moves", "books in the room")),
        ("Academy corridor", ("corridor", "hallway", "door handle", "footsteps crossing the floor")),
        ("Current room", ("in the room", "inside the room", "the room")),
    ]
    for location, needles in patterns:
        if any(needle in hay for needle in needles):
            return location
    return fallback or "previous scene location"


def last_scene_text_beat(text: str) -> str:
    """Return the last narrative-ish beat before choices/metadata."""
    lines = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line == "---":
            continue
        if re.search(r"\[(LIFE|ARC|SURPRISE)\]", line, re.IGNORECASE):
            break
        if line.lower().startswith(("choices", "what do you do", "you could")):
            break
        lines.append(line)
    return lines[-1] if lines else ""


def scene_continuity_anchor(recent_scenes: list[dict[str, Any]]) -> dict[str, str]:
    """The physical anchor the next reply must honor before moving anywhere."""
    for scene in reversed(recent_scenes):
        if scene.get("delivery_ok") is False:
            continue
        return {
            "scene_id": scene.get("scene_id", ""),
            "title": scene.get("title", ""),
            "location": scene.get("current_location", ""),
            "cast": scene.get("available_cast", ""),
            "opening": scene.get("opening", ""),
            "ending": scene.get("ending", ""),
        }
    return {}


def current_arc_progress() -> dict[str, Any]:
    text = read_safe(BASE / "lore" / "current-arc.md")
    title = first_match(r"^# Current Arc[\s:—-]+(.+)", text)
    phase = first_match(r"^## Phase:\s*(.+)", text)
    day_text = first_match(r"^## Day:\s*(\d+)", text)
    day = int(day_text) if day_text.isdigit() else None
    ready = phase.upper() == "QUIET" or (phase.upper() == "RESOLUTION" and (day or 0) >= 3)
    proposed = sorted(path.name for path in (BASE / "proposed").glob("arc-*.md")) if (BASE / "proposed").exists() else []
    return {
        "title": title,
        "phase": phase,
        "day": day,
        "ready_for_handoff": ready,
        "pending_proposals": proposed,
    }


def claimed_thread_anchors() -> set[str]:
    text = read_safe(BASE / "lore" / "threads.md")
    claimed: set[str] = set()
    for section in re.split(r"^## Thread:\s*", text, flags=re.MULTILINE)[1:]:
        for label in ("npc_anchor", "entities"):
            m = re.search(rf"\*\*{label}:(?:\*\*)?\s*([^\n]+)", section, re.IGNORECASE)
            if not m:
                continue
            for item in re.split(r",|;", m.group(1)):
                item = item.strip().strip("`")
                if item and item.lower() not in {"all npcs", "none", "unknown"}:
                    claimed.add(item.lower())
    return claimed


def emerging_thread_seeds(limit: int = 6) -> list[str]:
    text = read_safe(BASE / "memory" / "tick-queue.md")
    claimed = claimed_thread_anchors()
    seeds: list[str] = []
    for line in text.splitlines():
        m = re.search(r"\[THREAD SEED:\s*([^\]]+)\]", line)
        if m:
            name = m.group(1).strip()
            if name.lower() not in claimed and name not in seeds:
                seeds.append(name)
    return seeds[-limit:]


def open_simulation_actions(limit: int = 5) -> list[dict[str, str]]:
    actions = []
    for action in action_lifecycle.open_actions(limit=limit):
        target = f" -> {action.get('target')}" if action.get("target") else ""
        hidden = action.get("hidden_effect") or ""
        mechanism = f" Mechanism: {hidden}" if hidden else ""
        actions.append({
            "id": action.get("action_id", ""),
            "actor": action.get("actor", ""),
            "action": action.get("action", ""),
            "thread": action.get("thread_name", ""),
            "target": action.get("target", ""),
            "narrative": action.get("narrative", ""),
            "mechanism": hidden,
            "priority": action.get("priority", ""),
            "source_timestamp": action.get("source_timestamp", ""),
            "hook": truncate(
                f"{action.get('actor')} {action.get('action', '').replace('_', ' ')}{target}: {action.get('narrative')}{mechanism}",
                420,
            ),
        })
    return actions


def narrative_obligations(player: str, limit: int = 6) -> list[dict[str, Any]]:
    try:
        proc = subprocess.run(
            [
                sys.executable,
                str(BASE / "scripts" / "narrative-steward.py"),
                player,
                "--refresh",
                "--json",
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
            timeout=20,
        )
        if proc.returncode != 0:
            return []
        state = json.loads(proc.stdout)
    except Exception:
        return []
    obligations = []
    for item in state.get("obligations", []):
        if item.get("status", "open") != "open":
            continue
        obligations.append({
            "id": item.get("id", ""),
            "kind": item.get("kind", ""),
            "severity": item.get("severity", ""),
            "title": item.get("title", ""),
            "thread": item.get("thread", ""),
            "scene_hook": truncate(item.get("scene_hook", ""), 260),
            "satisfy_by": truncate(item.get("satisfy_by", ""), 260),
            "choice_pressure": item.get("choice_pressure", ""),
        })
        if len(obligations) >= limit:
            break
    return obligations


def continuity_threads(context: dict[str, Any]) -> list[str]:
    threads: list[str] = []
    academy = context["academy"]
    arc = context["arc"]
    patterns = context["patterns"]
    player = context["player"]
    scenes = context["recent_scenes"]

    if academy.get("current_location"):
        threads.append(f"Ground scenes in current location: {academy['current_location']}.")
    if arc.get("ready_for"):
        threads.append(f"Primary next story pressure: {arc['ready_for'][0]}")
    if player.get("active_quests"):
        q = player["active_quests"][0]
        threads.append(f"Oldest active quest still matters: {q['npc']} — {q['quest']}")
    if patterns.get("alive"):
        threads.append(f"Reach toward what felt alive: {patterns['alive'][-1]}")
    if patterns.get("avoid"):
        threads.append(f"Avoid repeating what felt flat: {patterns['avoid'][-1]}")
    if scenes:
        last = scenes[-1]
        if last.get("opening"):
            threads.append(f"Last realized scene texture: {last['opening']}")
    progress = context.get("story_progress", {})
    if progress.get("ready_for_handoff") and not progress.get("pending_proposals"):
        threads.append(
            f"Main arc '{progress.get('title') or 'current arc'}' is in {progress.get('phase')} day {progress.get('day')}; prepare next-arc handoff instead of extending it."
        )
    seeds = context.get("emerging_thread_seeds") or []
    if seeds:
        threads.append(f"Potential new thread seeds waiting for confirmation: {', '.join(seeds[:4])}.")
    obligations = context.get("narrative_obligations") or []
    if obligations:
        top = obligations[0]
        threads.append(f"Narrative stewardship obligation: {top.get('title')} — {top.get('scene_hook')}")
    actions = context.get("open_simulation_actions") or []
    if actions:
        threads.append(f"Unresolved NPC action to fold into play: {actions[0].get('hook')}")
    return [truncate(item, 280) for item in threads[:7]]


def quiet_life_threads(context: dict[str, Any]) -> list[str]:
    player = context["player"]
    academy = context["academy"]
    threads = []
    if player.get("core_belief"):
        core = player["core_belief"].rstrip(".")
        threads.append(f"Let ordinary moments reflect core belief: {core}.")
    if academy.get("current_block"):
        threads.append(f"Use current school rhythm as texture: {academy['current_block']}.")
    inventory = player.get("inventory") or []
    if inventory:
        threads.append(f"Desk or carried objects may anchor quiet scenes: {inventory[-1]}")
    threads.append("A LIFE choice should be allowed to stay human and non-plot-forward.")
    return [truncate(item, 240) for item in threads]


def build_context(player: str) -> dict[str, Any]:
    recent_scenes = recent_scene_entries()
    context: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "player": player_snapshot(player),
        "academy": academy_snapshot(),
        "arc": arc_snapshot(player),
        "patterns": patterns_snapshot(),
        "recent_diary": diary_snapshot(),
        "recent_scenes": recent_scenes,
        "scene_continuity_anchor": scene_continuity_anchor(recent_scenes),
        "story_progress": current_arc_progress(),
        "emerging_thread_seeds": emerging_thread_seeds(),
        "open_simulation_actions": open_simulation_actions(),
        "narrative_obligations": narrative_obligations(player),
    }
    context["continuity_threads"] = continuity_threads(context)
    context["quiet_life_threads"] = quiet_life_threads(context)
    context["model_guidance"] = [
        "Use this context as hard continuity, not exposition.",
        "Carry forward unresolved promises, objects, and location before adding new pressure.",
        "Before any scene movement, honor SCENE_CONTINUITY_ANCHOR: establish the previous physical location, remaining cast/objects, and the fact that the player has not teleported.",
        "Prefer one remembered specific over three vague callbacks.",
        "Protect slice-of-life scenes from automatic escalation.",
        "If a THREAD SEED is touched meaningfully in play, name a real subplot at closeout instead of leaving it as atmosphere forever.",
        "If an OPEN_SIMULATION_ACTION is relevant, make its trace visible as an object, rumor, schedule change, or NPC behavior before inventing new pressure.",
        "Treat NARRATIVE_OBLIGATIONS as repair duties: satisfy, explicitly defer, or preserve them for closeout.",
    ]
    return context


def render_text(context: dict[str, Any]) -> str:
    player = context["player"]
    academy = context["academy"]
    lines = [
        "STORY CONTEXT",
        f"GENERATED_AT: {context['generated_at']}",
        f"PLAYER: {context['player']['name']} | Chapter {player.get('chapter') or '?'} | Belief {player.get('belief') or '?'} | Tutorial {player.get('tutorial') or '?'}",
        f"WHERE_NOW: {academy.get('current_location') or 'unknown'} | {academy.get('player_status') or 'status unknown'}",
        "CONTINUITY_THREADS:",
    ]
    lines.extend(f"- {item}" for item in context["continuity_threads"])
    lines.append("QUIET_LIFE_THREADS:")
    lines.extend(f"- {item}" for item in context["quiet_life_threads"])
    if context["recent_scenes"]:
        lines.append("RECENT_REALIZED_SCENES:")
        for scene in context["recent_scenes"][-3:]:
            lines.append(f"- {scene.get('title')} :: {scene.get('opening')}")
    if context.get("scene_continuity_anchor"):
        anchor = context["scene_continuity_anchor"]
        lines.append("SCENE_CONTINUITY_ANCHOR:")
        lines.append(f"- last_scene={anchor.get('title') or anchor.get('scene_id')}")
        lines.append(f"- previous_location={anchor.get('location') or 'unknown'}")
        if anchor.get("cast"):
            lines.append(f"- previous_cast={anchor.get('cast')}")
        if anchor.get("ending"):
            lines.append(f"- last_visible_beat={anchor.get('ending')}")
    if context["academy"].get("active_threads"):
        lines.append("ACTIVE_STORY_THREADS:")
        for item in context["academy"]["active_threads"][:4]:
            lines.append(f"- {item['thread']} [{item['status']}]: {item['next_trigger']}")
    progress = context.get("story_progress", {})
    if progress:
        lines.append("ARC_PROGRESS:")
        handoff = "ready" if progress.get("ready_for_handoff") else "not-ready"
        lines.append(
            f"- {progress.get('title') or 'current arc'} | phase={progress.get('phase') or '?'} | day={progress.get('day') or '?'} | handoff={handoff}"
        )
    if context.get("emerging_thread_seeds"):
        lines.append("EMERGING_THREAD_SEEDS:")
        lines.extend(f"- {seed}" for seed in context["emerging_thread_seeds"])
    if context.get("open_simulation_actions"):
        lines.append("OPEN_SIMULATION_ACTIONS:")
        for action in context["open_simulation_actions"]:
            lines.append(f"- {action.get('hook')}")
    if context.get("narrative_obligations"):
        lines.append("NARRATIVE_OBLIGATIONS:")
        for item in context["narrative_obligations"]:
            suffix = f" [{item.get('choice_pressure')}]" if item.get("choice_pressure") else ""
            lines.append(f"- {item.get('severity')} {item.get('title')}{suffix}: {item.get('scene_hook')}")
    lines.append("MODEL_GUIDANCE:")
    lines.extend(f"- {item}" for item in context["model_guidance"])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build compact long-term story context.")
    parser.add_argument("player", nargs="?", default="bj")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--out", type=Path, help="Optional JSON output path.")
    args = parser.parse_args()

    context = build_context(args.player)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(context, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(context, indent=2, ensure_ascii=False))
    else:
        print(render_text(context))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

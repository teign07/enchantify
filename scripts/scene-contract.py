#!/usr/bin/env python3
"""Build and validate compact scene contracts for smaller model runs.

The contract is a narrow page of rails: scene mode, drama budget, grounding,
available cast, mechanics obligations, and Rule of Three requirements. It is
meant to be read before writing a scene and checked before delivery.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent.parent
SCRIPTS = BASE / "scripts"
MECHANICS_DIR = BASE / "mechanics"
if str(MECHANICS_DIR) not in sys.path:
    sys.path.insert(0, str(MECHANICS_DIR))
import mechanics_state  # type: ignore

_story_context_spec = importlib.util.spec_from_file_location("story_context", SCRIPTS / "story-context.py")
_story_context = importlib.util.module_from_spec(_story_context_spec)
assert _story_context_spec and _story_context_spec.loader
_story_context_spec.loader.exec_module(_story_context)
build_story_context = _story_context.build_context


SCENE_MODES = {"slice", "school-life", "arc", "mystery", "aftermath", "compass", "enchantment"}
DRAMA_BUDGETS = {"low", "medium", "high"}
PLOT_WORDS = {
    "investigate", "investigation", "nothing", "duskthorn", "wicker", "threat", "attack",
    "clue", "reveal", "accuse", "confront", "quest", "mission", "arc", "shadow", "danger",
    "restricted", "solve", "mystery", "drawer", "marked", "letter", "note",
}
LIFE_WORDS = {
    "tea", "snack", "breakfast", "lunch", "dinner", "sleep", "rest", "laundry", "desk",
    "window", "weather", "blanket", "chair", "mug", "homework", "class", "walk", "breathe",
    "tired", "hungry", "okay", "alright", "room",
}
SURPRISE_WORDS = {
    "follow", "sound", "draft", "door", "corridor", "outside", "unexpected", "sideways",
    "ask", "instead", "leave", "turn", "strange", "unrelated",
}


def read_safe(path: Path, limit: int = 0) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    if limit:
        return "\n".join(text.splitlines()[:limit])
    return text


def run_script(args: list[str]) -> str:
    proc = subprocess.run(args, cwd=BASE, capture_output=True, text=True)
    if proc.returncode != 0:
        return ""
    return (proc.stdout or "").strip()


def slate_value(slate: str, key: str) -> str:
    m = re.search(rf"^{re.escape(key)}:\s*(.+)$", slate, re.MULTILINE)
    return m.group(1).strip() if m else ""


def academy_value(label: str) -> str:
    text = read_safe(BASE / "lore" / "academy-state.md", 180)
    patterns = [
        rf"\*\*{re.escape(label)}:\*\*\s*([^\n]+)",
        rf"^{re.escape(label)}:\s*([^\n]+)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if m:
            return m.group(1).strip()
    return ""


def environment_locations(limit: int = 4) -> list[dict[str, str]]:
    text = read_safe(BASE / "lore" / "academy-state.md")
    rows: list[dict[str, str]] = []
    in_environment = False
    for line in text.splitlines():
        if line.startswith("## Environment"):
            in_environment = True
            continue
        if in_environment and line.startswith("## "):
            break
        if not in_environment or not line.startswith("|"):
            continue
        cells = [cell.strip().replace("*", "") for cell in line.strip("|").split("|")]
        if len(cells) < 3 or cells[0] == "Location" or set(cells[0]) <= {"-"}:
            continue
        rows.append({"location": cells[0], "state": cells[1], "notes": cells[2]})
    return rows[:limit]


def infer_mode(slate: str, requested: str | None) -> str:
    if requested:
        return requested
    story = slate_value(slate, "STORY").lower()
    nothing = slate_value(slate, "NOTHING").lower()
    schedule = slate_value(slate, "SCHEDULE").lower()
    if any(word in story for word in ("climax", "reveal", "accusation", "direct reveal")):
        return "arc"
    if any(word in nothing for word in ("high", "strongest", "active")):
        return "mystery"
    if any(word in story for word in ("falling", "resolution", "consequence")):
        return "aftermath"
    if any(word in schedule for word in ("class", "club", "hall", "common room")):
        return "school-life"
    return "slice"


def drama_budget(mode: str, slate: str, requested: str | None) -> str:
    if requested:
        return requested
    story = slate_value(slate, "STORY").lower()
    if mode in {"slice", "school-life"}:
        return "low"
    if mode in {"compass", "enchantment", "aftermath"}:
        return "medium"
    if "climax" in story:
        return "high"
    return "medium"


def mode_rules(mode: str, budget: str) -> dict[str, list[str]]:
    base = [
        "Open with one grounding beat: where the player physically is, who/what is still present, and what has not moved.",
        "Use the Director's Slate as pressure, not as exposition.",
        "End active play with three choices: LIFE, ARC, SURPRISE.",
    ]
    must_not = [
        "Do not teleport the player or clear the room between choices.",
        "Do not invent new lore characters when an existing cast member will do.",
        "Do not let all three choices advance the same plot thread.",
    ]
    may_advance = [
        "The ARC choice may advance the active investigation or story thread.",
        "The SURPRISE choice may reframe or leave the current thread without being random.",
    ]

    if mode in {"slice", "school-life"}:
        base.append("Keep the central beat ordinary: food, rest, class texture, friendship, room detail, or a small errand.")
        must_not.append("Do not introduce a new crisis, attack, reveal, or direct Nothing escalation.")
        may_advance.append("Arc pressure may appear only as background texture or an optional choice.")
    elif mode == "aftermath":
        base.append("Show consequences in small specifics before introducing the next problem.")
        must_not.append("Do not rush immediately into the next confrontation.")
    elif mode in {"arc", "mystery"}:
        base.append("Advance one story pressure clearly, but leave room for the LIFE choice to stay mundane.")
        if budget != "high":
            must_not.append("Do not force a climactic reveal unless the player chooses the ARC path.")
    elif mode in {"compass", "enchantment"}:
        base.append("Use the formal mechanic; never pretend the real-world task was completed.")
        must_not.append("Do not award completion before the player actually does the task.")

    return {"must_include": base, "must_not": must_not, "may_advance": may_advance}


def build_contract(player: str, mode: str | None, budget: str | None) -> dict[str, Any]:
    slate = run_script([sys.executable, str(SCRIPTS / "scene-director.py"), player, "--slate-only"])
    selected_mode = infer_mode(slate, mode)
    selected_budget = drama_budget(selected_mode, slate, budget)
    mechanics = mechanics_state.get_mechanics_state(BASE, player)
    story_context = build_story_context(player)
    current_location = academy_value("Current Location") or "unknown Academy location"
    player_status = academy_value("Status")
    current_block = academy_value("Current Block")
    rules = mode_rules(selected_mode, selected_budget)
    narrative_obligations = story_context.get("narrative_obligations", [])
    if narrative_obligations:
        rules["must_include"].append(
            "Satisfy or explicitly defer at least one NARRATIVE_OBLIGATION when it naturally fits; do not let repair duties silently vanish."
        )
        if any(item.get("kind") == "drama_budget_guard" for item in narrative_obligations):
            rules["must_include"].append(
                "Honor the current arc tone over raw simulation volume; recovery/rest may count as real story movement."
            )

    return {
        "player": player,
        "scene_mode": selected_mode,
        "drama_budget": selected_budget,
        "current_location": current_location,
        "player_status": player_status,
        "current_block": current_block,
        "available_cast": slate_value(slate, "CAST"),
        "atmosphere": slate_value(slate, "FEEL"),
        "story_pressure": slate_value(slate, "STORY"),
        "nothing_pressure": slate_value(slate, "NOTHING"),
        "schedule_texture": slate_value(slate, "SCHEDULE"),
        "suppress": slate_value(slate, "SUPPRESS"),
        "nearby_places": environment_locations(),
        "story_context": {
            "continuity_threads": story_context.get("continuity_threads", []),
            "quiet_life_threads": story_context.get("quiet_life_threads", []),
            "recent_scenes": story_context.get("recent_scenes", [])[-3:],
            "active_story_threads": story_context.get("academy", {}).get("active_threads", [])[:4],
            "arc_progress": story_context.get("story_progress", {}),
            "emerging_thread_seeds": story_context.get("emerging_thread_seeds", []),
            "narrative_obligations": narrative_obligations,
            "model_guidance": story_context.get("model_guidance", []),
        },
        "mechanics": {
            "belief": mechanics.get("belief"),
            "belief_band": mechanics.get("belief_band"),
            "offer_compass": bool(mechanics.get("should_offer_compass")),
            "offer_enchantment": bool(mechanics.get("should_offer_enchantment")),
            "compass_locked_today": bool(mechanics.get("compass_locked_today")),
            "roll_on_risk": bool(mechanics.get("should_roll", True)),
        },
        "small_model_rules": rules,
        "choice_contract": {
            "LIFE": "Grounded, mundane, human; does not advance the plot directly.",
            "ARC": "Expected story move; advances the current investigation, quest, or main arc.",
            "SURPRISE": "Sideways or reframing move; leaves or bends the current thread without being random.",
        },
    }


def render_text(contract: dict[str, Any]) -> str:
    mechanics = contract["mechanics"]
    places = "; ".join(
        f"{p['location']} ({p['state']})" for p in contract.get("nearby_places", [])[:3]
    )
    story_context = contract.get("story_context", {})
    lines = [
        "SCENE CONTRACT",
        f"MODE: {contract['scene_mode']}",
        f"DRAMA_BUDGET: {contract['drama_budget']}",
        f"CURRENT_LOCATION: {contract['current_location']}",
        f"PLAYER_STATUS: {contract.get('player_status') or 'unknown'}",
        f"CURRENT_BLOCK: {contract.get('current_block') or 'unknown'}",
        f"AVAILABLE_CAST: {contract.get('available_cast') or 'none surfaced'}",
        f"ATMOSPHERE: {contract.get('atmosphere') or 'quiet Academy texture'}",
        f"STORY_PRESSURE: {contract.get('story_pressure') or 'none'}",
        f"NOTHING_PRESSURE: {contract.get('nothing_pressure') or 'background only'}",
        f"SCHEDULE_TEXTURE: {contract.get('schedule_texture') or 'ambient'}",
        f"SUPPRESS: {contract.get('suppress') or 'no extra suppression'}",
        f"NEARBY_PLACES: {places or 'not enough data'}",
        (
            "MECHANICS: "
            f"belief={mechanics['belief']} ({mechanics['belief_band']}), "
            f"compass={'offer' if mechanics['offer_compass'] else 'no'}, "
            f"enchantment={'offer' if mechanics['offer_enchantment'] else 'no'}, "
            f"dice={'roll-on-risk' if mechanics['roll_on_risk'] else 'light'}"
        ),
        "LONG_MEMORY:",
    ]
    lines.extend(f"- {item}" for item in story_context.get("continuity_threads", [])[:5])
    lines.append("QUIET_LIFE:")
    lines.extend(f"- {item}" for item in story_context.get("quiet_life_threads", [])[:4])
    lines.append("MODEL_GUIDANCE:")
    lines.extend(f"- {item}" for item in story_context.get("model_guidance", [])[:4])
    progress = story_context.get("arc_progress") or {}
    if progress:
        handoff = "ready" if progress.get("ready_for_handoff") else "not-ready"
        lines.append(
            f"ARC_PROGRESS: {progress.get('title') or 'current arc'} | phase={progress.get('phase') or '?'} | day={progress.get('day') or '?'} | handoff={handoff}"
        )
    seeds = story_context.get("emerging_thread_seeds") or []
    if seeds:
        lines.append("EMERGING_THREAD_SEEDS:")
        lines.extend(f"- {seed}" for seed in seeds[:4])
    obligations = story_context.get("narrative_obligations") or []
    if obligations:
        lines.append("NARRATIVE_OBLIGATIONS:")
        for item in obligations[:5]:
            target = f" [{item.get('choice_pressure')}]" if item.get("choice_pressure") else ""
            lines.append(f"- {item.get('severity')} {item.get('title')}{target}: {item.get('scene_hook')}")
            lines.append(f"  Satisfy by: {item.get('satisfy_by')}")
    lines.append(
        "MUST_INCLUDE:",
    )
    lines.extend(f"- {item}" for item in contract["small_model_rules"]["must_include"])
    lines.append("MUST_NOT:")
    lines.extend(f"- {item}" for item in contract["small_model_rules"]["must_not"])
    lines.append("CHOICES:")
    for key, value in contract["choice_contract"].items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def extract_tagged_choices(text: str) -> dict[str, str]:
    choices: dict[str, str] = {}
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = re.search(r"\[(LIFE|ARC|SURPRISE)\]\s*(.+)", line, re.IGNORECASE)
        if not m:
            continue
        label = m.group(1).upper()
        body = m.group(2).strip()
        if not body and i + 1 < len(lines):
            body = lines[i + 1].strip()
        choices[label] = body
    return choices


def words(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z']+", text.lower()))


def validate_scene(text: str, contract: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    choices = extract_tagged_choices(text)
    missing = {"LIFE", "ARC", "SURPRISE"} - set(choices)
    if missing:
        failures.append("missing tagged choices: " + ", ".join(sorted(missing)))
        return failures

    life_words = words(choices["LIFE"])
    arc_words = words(choices["ARC"])
    surprise_words = words(choices["SURPRISE"])

    if life_words & PLOT_WORDS and not life_words & LIFE_WORDS:
        failures.append("LIFE choice reads plot-forward; make it mundane and human")
    if not (life_words & LIFE_WORDS):
        failures.append("LIFE choice needs a concrete ordinary action or care beat")
    if not (arc_words & PLOT_WORDS):
        failures.append("ARC choice needs to clearly touch the current story thread")
    if not (surprise_words & SURPRISE_WORDS):
        failures.append("SURPRISE choice needs a sideways/reframing action")

    if contract["scene_mode"] in {"slice", "school-life"}:
        first_part = "\n".join(text.splitlines()[:8]).lower()
        crisis_words = {"attack", "scream", "blood", "nothing", "duskthorn", "wicker", "shatter", "danger"}
        if words(first_part) & crisis_words:
            failures.append("slice/school-life opening starts with crisis pressure")

    first_500 = text[:500].lower()
    location = contract.get("current_location") or ""
    location_terms = [w for w in re.findall(r"[A-Za-z]+", location.lower()) if len(w) >= 4]
    if location_terms and not any(term in first_500 for term in location_terms[:4]):
        failures.append("opening does not ground the current physical location")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or validate a compact scene contract.")
    parser.add_argument("player", nargs="?", default="bj")
    parser.add_argument("--mode", choices=sorted(SCENE_MODES))
    parser.add_argument("--drama-budget", choices=sorted(DRAMA_BUDGETS))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--validate-scene", type=Path)
    args = parser.parse_args()

    contract = build_contract(args.player, args.mode, args.drama_budget)
    if args.validate_scene:
        if not args.validate_scene.exists():
            print(f"scene file not found: {args.validate_scene}", file=sys.stderr)
            return 1
        failures = validate_scene(args.validate_scene.read_text(encoding="utf-8"), contract)
        if failures:
            print("SCENE CONTRACT FAILED")
            for failure in failures:
                print(f"- {failure}")
            return 1
        print("SCENE CONTRACT OK")
        return 0

    if args.json:
        print(json.dumps(contract, indent=2, ensure_ascii=False))
    else:
        print(render_text(contract))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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

_page_contract_spec = importlib.util.spec_from_file_location("page_contract", SCRIPTS / "page-contract.py")
_page_contract = importlib.util.module_from_spec(_page_contract_spec)
assert _page_contract_spec and _page_contract_spec.loader
_page_contract_spec.loader.exec_module(_page_contract)
build_page_contract = _page_contract.build_contract


SCENE_MODES = {"slice", "school-life", "arc", "mystery", "aftermath", "compass", "enchantment"}
DRAMA_BUDGETS = {"low", "medium", "high"}
PLOT_WORDS = {
    "investigate", "investigation", "nothing", "duskthorn", "wicker", "threat", "attack",
    "clue", "reveal", "accuse", "confront", "quest", "mission", "arc", "shadow", "danger",
    "restricted", "solve", "mystery", "drawer", "mark", "marked", "symbol", "seam", "letter", "note",
}
LIFE_WORDS = {
    "tea", "snack", "breakfast", "lunch", "dinner", "sleep", "rest", "laundry", "desk",
    "window", "weather", "blanket", "chair", "mug", "homework", "class", "walk", "breathe",
    "tired", "hungry", "okay", "alright", "room", "table", "slow", "slower", "pause",
    "explain", "listen", "gathered", "stay", "sit",
}
SURPRISE_WORDS = {
    "follow", "sound", "draft", "door", "corridor", "outside", "unexpected", "sideways",
    "ask", "instead", "leave", "turn", "strange", "unrelated",
}
ENCHANTMENT_OBJECT_WORDS = {
    "object", "door", "desk", "mug", "lamp", "mirror", "note", "letter", "field", "cord",
    "key", "book", "page", "pen", "chronograph", "flyer", "notice", "thread", "glass",
    "window", "chair", "drawer", "stair", "shadow", "souvenir", "compass",
}
DICE_RISK_WORDS = {
    "confront", "accuse", "sneak", "steal", "grab", "escape", "resist", "challenge",
    "persuade", "lie", "hide", "follow", "enter", "force", "risk", "danger", "wicker",
    "duskthorn", "nothing", "restricted", "attack", "protect", "save",
}
SCENE_FULLNESS_DEFAULTS = {
    "slice": {"target_words": "650-950", "minimum_words": 500, "minimum_paragraphs": 5},
    "school-life": {"target_words": "750-1100", "minimum_words": 575, "minimum_paragraphs": 6},
    "arc": {"target_words": "750-1150", "minimum_words": 600, "minimum_paragraphs": 6},
    "mystery": {"target_words": "750-1150", "minimum_words": 600, "minimum_paragraphs": 6},
    "aftermath": {"target_words": "600-900", "minimum_words": 475, "minimum_paragraphs": 5},
    "compass": {"target_words": "500-800", "minimum_words": 400, "minimum_paragraphs": 4},
    "enchantment": {"target_words": "550-850", "minimum_words": 425, "minimum_paragraphs": 4},
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


def player_known_enchantments(player: str, limit: int = 16) -> list[str]:
    text = read_safe(BASE / "players" / f"{player}.md")
    block_m = re.search(r"## The Flyleaf\s*\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    if not block_m:
        return []
    names: list[str] = []
    for line in block_m.group(1).splitlines():
        if not line.startswith("|") or "---" in line or "Enchantment" in line:
            continue
        cells = [cell.strip().strip("*") for cell in line.strip("|").split("|")]
        if cells and cells[0] and cells[0] not in names:
            names.append(cells[0])
    return names[:limit]


def select_enchantment(context_text: str, known: list[str]) -> str:
    lowered = context_text.lower()
    preferences = [
        ("Everything Speaks", {"door", "object", "cord", "key", "pen", "chronograph", "book", "chair"}),
        ("Everything's Poetry", {"note", "letter", "page", "field", "shadow", "silence"}),
        ("Everything's Magic", {"object", "artifact", "lamp", "mirror", "key", "pen"}),
        ("Everything's Stories", {"book", "field", "notes", "souvenir", "window", "flyer"}),
        ("Everything's Connected", {"thread", "clue", "investigation", "wicker", "duskthorn", "cord"}),
        ("Everything's Puzzling", {"puzzle", "locked", "riddle", "restricted", "drawer"}),
        ("Everything's Wonderful", {"ordinary", "mug", "desk", "weather", "room", "snack"}),
        ("Mirror Mirror", {"self", "reflection", "mirror", "doubt", "prophecy"}),
        ("Everything's Nice", {"hurt", "tired", "afraid", "comfort", "belief"}),
    ]
    known_set = set(known)
    for name, triggers in preferences:
        if name in known_set and lowered.split() and (triggers & words(lowered)):
            return name
    for fallback in ("Everything Speaks", "Everything's Poetry", "Everything's Wonderful"):
        if fallback in known_set:
            return fallback
    return known[0] if known else "Everything Speaks"


def mechanics_opportunities(
    player: str,
    mode: str,
    slate: str,
    story_context: dict[str, Any],
    mechanics: dict[str, Any],
) -> dict[str, Any]:
    known = player_known_enchantments(player)
    schedule = slate_value(slate, "SCHEDULE")
    classroom = slate_value(slate, "CLASSROOM")
    story = slate_value(slate, "STORY")
    nothing = slate_value(slate, "NOTHING")
    actions = " ".join(action.get("hook", "") for action in story_context.get("open_simulation_actions", []))
    continuity = " ".join(story_context.get("continuity_threads", []))
    quiet = " ".join(story_context.get("quiet_life_threads", []))
    context_text = " ".join([schedule, classroom, story, nothing, actions, continuity, quiet])
    context_words = words(context_text)

    session = mechanics.get("session", {}) or {}
    enchantment_done_today = (mechanics.get("enchantment") or {}).get("completed_on")
    enchantment_offers = int(session.get("enchantment_offers") or 0)

    enchant_reasons: list[str] = []
    if "basic enchantments" in (schedule + " " + classroom).lower():
        enchant_reasons.append("current class/practice is Basic Enchantments")
    if "nothing" in nothing.lower() and any(w in nothing.lower() for w in ("active", "high", "pressing", "seam")):
        enchant_reasons.append("Nothing pressure is present; Enchantments are the standard answer to minor/moderate manifestations")
    if context_words & ENCHANTMENT_OBJECT_WORDS:
        enchant_reasons.append("scene context contains enchantable objects or clues")
    if story_context.get("open_simulation_actions"):
        enchant_reasons.append("an unresolved NPC action has a concrete trace that can be enchanted")
    if mode in {"mystery", "arc"} and context_words & {"clue", "note", "field", "restricted", "shadow", "investigation"}:
        enchant_reasons.append("mystery pressure has a clue/object that can become the Third Way")
    if mode in {"slice", "school-life"} and enchantment_offers == 0:
        enchant_reasons.append("first daily-life/school-life scene can offer a low-stakes enchantment as play, not recovery")
    if mode == "enchantment":
        enchant_reasons.append("player or scene explicitly invoked Enchantment mode; formal ritual must run even if daily offer cadence is otherwise quiet")

    should_offer_enchantment = bool(enchant_reasons) and (mode == "enchantment" or not enchantment_done_today)
    if enchantment_offers >= 2 and not ("basic enchantments" in (schedule + " " + classroom).lower()):
        should_offer_enchantment = False
        enchant_reasons = ["daily enchantment offer cadence already satisfied unless the player asks"]

    dice_reasons: list[str] = []
    risky_context = context_words & DICE_RISK_WORDS
    if mode in {"arc", "mystery"}:
        dice_reasons.append("arc/mystery choices often have uncertain outcomes")
    if risky_context:
        dice_reasons.append("scene context contains risk verbs: " + ", ".join(sorted(list(risky_context))[:5]))
    if "nothing" in nothing.lower() and any(w in nothing.lower() for w in ("active", "pressing", "high")):
        dice_reasons.append("Nothing pressure means resistance or risky magical action should roll unless using a formal Enchantment")

    return {
        "known_enchantments": known,
        "enchantment_opportunity": should_offer_enchantment,
        "suggested_enchantment": select_enchantment(context_text, known),
        "enchantment_reasons": enchant_reasons[:4],
        "dice_opportunity": bool(dice_reasons),
        "dice_reasons": dice_reasons[:4],
        "dice_rule": "Roll before narrating uncertain outcomes. Do not roll for completed Enchantments or Compass Runs.",
    }


def classroom_contract(player: str, mode: str, slate: str) -> dict[str, Any]:
    schedule = slate_value(slate, "SCHEDULE").lower()
    classroom = slate_value(slate, "CLASSROOM").lower()
    class_now = "no mandatory class in session" not in schedule and "class" in schedule
    if not class_now:
        return {}
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "class-lecture.py"), player, "--status", "--json"],
        cwd=BASE,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        return {}
    try:
        data = json.loads(proc.stdout)
    except Exception:
        return {}
    if not data.get("class_id"):
        return {}
    return data


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


def scene_fullness_contract(mode: str, page_contract: dict[str, Any]) -> dict[str, Any]:
    fullness = dict(SCENE_FULLNESS_DEFAULTS.get(mode, SCENE_FULLNESS_DEFAULTS["slice"]))
    page_type = page_contract.get("page_type")
    if page_type == "rest":
        fullness.update({"target_words": "450-700", "minimum_words": 325, "minimum_paragraphs": 4})
    elif page_type == "conflict":
        fullness.update({"target_words": "800-1200", "minimum_words": 650, "minimum_paragraphs": 6})
    elif page_type == "slice_of_life":
        fullness.update({"target_words": "700-1000", "minimum_words": max(fullness["minimum_words"], 550), "minimum_paragraphs": max(fullness["minimum_paragraphs"], 5)})
    fullness["choice_min_words"] = 9
    return fullness


def apply_fullness_rules(rules: dict[str, list[str]], fullness: dict[str, Any]) -> None:
    rules["must_include"].append(
        "Write a substantial live-play scene, not a summary or postcard. "
        f"Target {fullness['target_words']} words before the Rule of Three; absolute floor {fullness['minimum_words']} words unless the player explicitly asked for brevity."
    )
    rules["must_include"].append(
        f"Use at least {fullness['minimum_paragraphs']} real scene paragraphs before choices: embodied setting, character behavior, dialogue/reaction, interior pressure, and one changed detail."
    )
    rules["must_include"].append(
        "Let the selected action breathe through a beginning, middle, and handoff. Do not jump from arrival to choices after one line of dialogue."
    )
    rules["must_include"].append(
        "Choices should be polished invitations, not bare commands; each should contain a concrete action plus why it matters emotionally, socially, or narratively."
    )
    rules["must_not"].append(
        "Do not deliver a low-effort short reply: fewer than the fullness floor, fewer than the required scene paragraphs, or choices written as terse command fragments."
    )


def apply_page_rules(rules: dict[str, list[str]], page_contract: dict[str, Any]) -> None:
    label = page_contract.get("page_label") or page_contract.get("page_type") or "Page"
    artifacts = ", ".join(page_contract.get("artifact_due", [])[:4]) or "one proof artifact"
    allowed = ", ".join(page_contract.get("allowed_systems", [])[:6])
    forbidden = ", ".join(page_contract.get("forbidden_systems", [])[:6])

    rules["must_include"].insert(
        0,
        f"Open a {label}. Purpose: {page_contract.get('purpose')}. The primary page wins over feature soup.",
    )
    rules["must_include"].append(
        f"Invite the player toward this page's answer: {page_contract.get('player_invitation')}"
    )
    rules["must_include"].append(
        f"Leave proof appropriate to the page before closeout or explicitly name what proof is pending: {artifacts}."
    )
    if page_contract.get("closure_condition"):
        rules["must_include"].append(f"Know how this page closes: {page_contract.get('closure_condition')}")
    if allowed:
        rules["may_advance"].append(f"Page-appropriate systems: {allowed}.")
    rules["must_not"].append("Do not include systems just because they exist; include only what serves the current Page.")
    if forbidden:
        rules["must_not"].append(f"Page forbids: {forbidden}.")


def apply_tool_rules(rules: dict[str, list[str]], page_contract: dict[str, Any]) -> None:
    tools = page_contract.get("tool_posture") or {}
    if not tools:
        return
    preferred = ", ".join(tools.get("preferred_tools", [])[:6]) or "none"
    allowed = ", ".join(tools.get("allowed_tools", [])[:8]) or "text/voice only"
    default_sequence = ", ".join(tools.get("default_sequence", [])) or "text, voice"
    rules["must_include"].append(
        f"PAGE TOOL POSTURE: {tools.get('posture')}. Preferred tools: {preferred}. Allowed tools: {allowed}. Default conductor sequence if emitting a packet: {default_sequence}."
    )
    triggers = tools.get("triggers", [])
    if triggers:
        rules["may_advance"].append(
            "Tool triggers: " + " | ".join(triggers[:5])
        )
    forbidden = tools.get("forbidden_tools", [])
    if forbidden:
        rules["must_not"].append(
            "Do not use page-inappropriate tools: " + "; ".join(forbidden[:4]) + "."
        )
    rules["must_not"].append(
        "Do not use every available tool. Choose only tools that make this Page more embodied, useful, or memorable."
    )


def apply_classroom_rules(rules: dict[str, list[str]], classroom: dict[str, Any]) -> None:
    if not classroom:
        return
    lesson = classroom.get("lesson_title") or "current lesson"
    segment = classroom.get("segment") or "current segment"
    professor = classroom.get("professor") or "the professor"
    room = classroom.get("room") or "the classroom"
    rules["must_include"].append(
        f"CLASSROOM CONTRACT: {professor} is teaching {lesson}, segment {int(classroom.get('segment_index') or 0) + 1}: {segment}. Render this one segment as a real classroom scene in {room}, not a summary of the whole class."
    )
    rules["must_include"].append(
        "Class must include professor teaching, one concrete room detail, and at least one named classmate reaction/question/interruption."
    )
    rules["must_include"].append(
        "End with a way to continue the lesson, ask a question, try a practice, or let class turn sideways."
    )
    if not classroom.get("active"):
        rules["must_include"].append(
            "Attendance is not active yet. If the player is entering class, run class-lecture.py --attend before treating this as attended."
        )
    rules["must_not"].append(
        "Do not compress class with phrases like class passes, lecture covers, after class, by the end of class, you spend the period, or the lesson wraps."
    )
    rules["must_not"].append(
        "Do not complete the lesson, practice, Compass Run, or Enchantment unless the matching class/enchantment/compass script says it completed."
    )


def tool_packet_suggestion(contract: dict[str, Any]) -> dict[str, Any]:
    page = contract.get("page_contract") or {}
    tools = page.get("tool_posture") or {}
    page_type = page.get("page_type") or "slice_of_life"
    intensity = {
        "conflict": "ritual",
        "enchantment": "ritual",
        "wonder_compass": "quiet",
        "rest": "quiet",
        "letter": "cinematic",
        "archive": "cinematic",
        "bleed": "cinematic",
        "anchor": "ritual",
    }.get(page_type, "cinematic")
    sequence = tools.get("default_sequence") or ["text", "image", "voice"]
    mood = (contract.get("atmosphere") or page.get("secondary_flavor") or page_type).split(" | ")[0][:120]
    packet: dict[str, Any] = {
        "intensity": intensity,
        "sequence": sequence,
        "mood": mood,
        "metadata": {
            "page_type": page_type,
            "page_label": page.get("page_label"),
            "tool_posture": tools.get("posture"),
            "intrusion_level": tools.get("intrusion_level", "low"),
            "audio_roles": tools.get("audio_roles", {}),
            "artifact_tools": tools.get("artifact_tools", []),
            "cooldowns": tools.get("cooldowns", {}),
        },
    }
    if "image" in sequence or "image" in tools.get("preferred_tools", []):
        packet["image"] = {
            "backend": "drawthings",
            "deliver": True,
            "prompt_hint": "character-focused field-journal portrait/action beat: face, expression, posture, hands, meaningful object; room only as faint background wash",
        }
    if "lights" in sequence or "lights" in tools.get("preferred_tools", []):
        if page_type == "conflict":
            packet["lights"] = {"color": "deep violet", "brightness": 35, "transition": 4}
        elif page_type == "rest":
            packet["lights"] = {"color": "warm amber", "brightness": 25, "transition": 5}
        elif page_type == "wonder_compass":
            packet["lights"] = {"scene": "compass", "transition": 3}
        elif page_type in {"enchantment", "anchor"}:
            packet["lights"] = {"scene": "ritual", "transition": 3}
        else:
            packet["lights"] = {"scene": "academy", "transition": 3}
    if "musicgen" in tools.get("preferred_tools", []) or "music" in sequence:
        packet["music"] = {
            "deliver": False,
            "duration_seconds": 20,
            "prompt_hint": "short instrumental texture matching the Page's emotional posture; no vocals",
        }
    if "spotify" in sequence or "spotify" in tools.get("allowed_tools", []):
        packet["spotify"] = {"action": "mood_only", "mood": mood}
    if "printer" in sequence or "printer" in tools.get("preferred_tools", []):
        packet["printer"] = {"artifact_type": "page-artifact", "content_hint": "print only when this Page leaves proof worth keeping"}
    if "wallpaper" in tools.get("allowed_tools", []) or "wallpaper" in tools.get("artifact_tools", []):
        packet["wallpaper"] = {
            "action": "brief",
            "prompt_hint": "change desktop wallpaper only for a major page-state shift, breach, completion, or threshold",
        }
    if "app_actions" in tools.get("allowed_tools", []) or any(tool in tools.get("artifact_tools", []) for tool in ("apple_notes", "obsidian", "reminders")):
        packet["app_actions"] = {
            "mode": "brief",
            "allowed_private_apps": ["apple_reminders", "apple_notes", "obsidian", "apple_calendar"],
            "public_apps_require_consent": True,
            "content_hint": "private artifact only; use sparingly and preserve page proof",
        }
    return packet


def build_contract(player: str, mode: str | None, budget: str | None) -> dict[str, Any]:
    slate = run_script([sys.executable, str(SCRIPTS / "scene-director.py"), player, "--slate-only"])
    initial_mode = infer_mode(slate, mode)
    page_contract = build_page_contract(player, mode=mode or initial_mode)
    selected_mode = mode or page_contract.get("recommended_scene_mode") or initial_mode
    selected_budget = budget or page_contract.get("recommended_drama_budget") or drama_budget(selected_mode, slate, None)
    mechanics = mechanics_state.get_mechanics_state(BASE, player)
    active_enchantment = mechanics.get("active_enchantment")
    story_context = build_story_context(player)
    current_location = academy_value("Current Location") or "unknown Academy location"
    player_status = academy_value("Status")
    current_block = academy_value("Current Block")
    rules = mode_rules(selected_mode, selected_budget)
    apply_page_rules(rules, page_contract)
    apply_tool_rules(rules, page_contract)
    fullness = scene_fullness_contract(selected_mode, page_contract)
    apply_fullness_rules(rules, fullness)
    classroom = classroom_contract(player, selected_mode, slate)
    apply_classroom_rules(rules, classroom)
    narrative_obligations = story_context.get("narrative_obligations", [])
    open_actions = story_context.get("open_simulation_actions", [])
    continuity_anchor = story_context.get("scene_continuity_anchor", {}) or {}
    if continuity_anchor.get("location"):
        current_location = continuity_anchor.get("location")
    opportunities = mechanics_opportunities(player, selected_mode, slate, story_context, mechanics)
    if continuity_anchor:
        anchor_bits = []
        if continuity_anchor.get("location"):
            anchor_bits.append(f"previous location: {continuity_anchor.get('location')}")
        if continuity_anchor.get("cast"):
            anchor_bits.append(f"previous cast/presence: {continuity_anchor.get('cast')}")
        if continuity_anchor.get("ending"):
            anchor_bits.append(f"last visible beat: {continuity_anchor.get('ending')}")
        rules["must_include"].append(
            "Continue from SCENE_CONTINUITY_ANCHOR before moving anywhere: "
            + "; ".join(anchor_bits)
            + ". If the player chose an in-room action, remain there; if the player chose to leave, narrate the transition from there."
        )
        rules["must_not"].append(
            "Do not start in a different room, location, or cast configuration without first showing the movement away from the previous scene."
        )
    if open_actions:
        top_action = open_actions[0]
        rules["must_include"].append(
            "Surface at least one OPEN_SIMULATION_ACTION as a visible trace, rumor, object state, schedule change, or NPC behavior before adding unrelated pressure. "
            f"Priority hook: {top_action.get('hook')}"
        )
        rules["must_not"].append(
            "Do not summarize an OPEN_SIMULATION_ACTION as abstract pressure; show how it physically or socially changed the scene."
        )
    if narrative_obligations:
        rules["must_include"].append(
            "Satisfy or explicitly defer at least one NARRATIVE_OBLIGATION when it naturally fits; do not let repair duties silently vanish."
        )
        if any(item.get("kind") == "drama_budget_guard" for item in narrative_obligations):
            rules["must_include"].append(
                "Honor the current arc tone over raw simulation volume; recovery/rest may count as real story movement."
            )
    if opportunities["enchantment_opportunity"]:
        reasons = "; ".join(opportunities.get("enchantment_reasons", []))
        rules["must_include"].append(
            f"Offer one formal Enchantment as a real option when it fits, preferably {opportunities['suggested_enchantment']}. Reason: {reasons}. If the player chooses it, run `python3 scripts/enchantment.py start {player} --spell \"{opportunities['suggested_enchantment']}\" --target \"[target]\"`; do not narrate completion until the player provides a photo or vivid real-world description."
        )
    if active_enchantment:
        rules["must_include"].append(
            f"An Enchantment is already active and awaiting proof: {active_enchantment.get('spell')} on {active_enchantment.get('target')}. Do not advance ordinary scene resolution as if it completed. Ask for proof, or if proof was just provided, run `python3 scripts/enchantment.py complete {player} --proof \"[real proof]\" --outcome \"[story effect]\"` before narrating the result."
        )
    if opportunities["dice_opportunity"]:
        reasons = "; ".join(opportunities.get("dice_reasons", []))
        rules["must_include"].append(
            f"Flag risky uncertain actions as dice-gated before resolving them. If the player chooses that action, run scripts/roll-dice.py with current Belief. Reason: {reasons}."
        )

    contract = {
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
        "page_contract": page_contract,
        "scene_fullness": fullness,
        "classroom_contract": classroom,
        "story_context": {
            "continuity_threads": story_context.get("continuity_threads", []),
            "quiet_life_threads": story_context.get("quiet_life_threads", []),
            "recent_scenes": story_context.get("recent_scenes", [])[-3:],
            "scene_continuity_anchor": continuity_anchor,
            "active_story_threads": story_context.get("academy", {}).get("active_threads", [])[:4],
            "arc_progress": story_context.get("story_progress", {}),
            "emerging_thread_seeds": story_context.get("emerging_thread_seeds", []),
            "open_simulation_actions": open_actions,
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
            "known_enchantments": opportunities.get("known_enchantments", []),
            "enchantment_opportunity": opportunities["enchantment_opportunity"],
            "suggested_enchantment": opportunities["suggested_enchantment"],
            "enchantment_reasons": opportunities["enchantment_reasons"],
            "dice_opportunity": opportunities["dice_opportunity"],
            "dice_reasons": opportunities["dice_reasons"],
            "dice_rule": opportunities["dice_rule"],
            "active_enchantment": active_enchantment,
        },
        "small_model_rules": rules,
        "choice_contract": {
            "LIFE": "Grounded, mundane, human; does not advance the plot directly.",
            "ARC": "Expected story move; advances the current investigation, quest, or main arc.",
            "SURPRISE": "Sideways or reframing move; leaves or bends the current thread without being random.",
        },
    }
    contract["tool_packet_suggestion"] = tool_packet_suggestion(contract)
    return contract


def render_text(contract: dict[str, Any]) -> str:
    mechanics = contract["mechanics"]
    page = contract.get("page_contract") or {}
    tool_posture = page.get("tool_posture") or {}
    classroom = contract.get("classroom_contract") or {}
    places = "; ".join(
        f"{p['location']} ({p['state']})" for p in contract.get("nearby_places", [])[:3]
    )
    story_context = contract.get("story_context", {})
    lines = [
        "SCENE CONTRACT",
        f"PAGE_TYPE: {page.get('page_type', 'unknown')} ({page.get('page_label', 'Page')})",
        f"PAGE_PURPOSE: {page.get('purpose', 'unknown')}",
        f"PAGE_INVITATION: {page.get('player_invitation', 'unknown')}",
        f"PAGE_CLOSURE: {page.get('closure_condition', 'unknown')}",
        f"PAGE_ARTIFACT_DUE: {', '.join(page.get('artifact_due', [])) or 'proof artifact'}",
        f"PAGE_SECONDARY_FLAVOR: {page.get('secondary_flavor') or 'none'}",
        f"PAGE_TOOL_POSTURE: {tool_posture.get('posture') or 'text/voice only'}",
        f"PAGE_INTRUSION_LEVEL: {tool_posture.get('intrusion_level') or 'low'}",
        f"PAGE_PREFERRED_TOOLS: {', '.join(tool_posture.get('preferred_tools', [])) or 'none'}",
        f"PAGE_ALLOWED_TOOLS: {', '.join(tool_posture.get('allowed_tools', [])) or 'none'}",
        f"PAGE_RARE_TOOLS: {', '.join(tool_posture.get('rare_tools', [])) or 'none'}",
        f"PAGE_DEFAULT_TOOL_SEQUENCE: {', '.join(tool_posture.get('default_sequence', [])) or 'text, voice'}",
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
            f"enchantment={'offer' if mechanics['enchantment_opportunity'] else ('low-belief-offer' if mechanics['offer_enchantment'] else 'no')}, "
            f"dice={'roll-on-risk' if mechanics['dice_opportunity'] or mechanics['roll_on_risk'] else 'light'}"
        ),
    ]
    if mechanics.get("enchantment_opportunity"):
        lines.append(f"ENCHANTMENT_OPPORTUNITY: {mechanics.get('suggested_enchantment')}")
        lines.extend(f"- {reason}" for reason in mechanics.get("enchantment_reasons", []))
        lines.append(
            f"- FORMAL START: python3 scripts/enchantment.py start {contract['player']} --spell \"{mechanics.get('suggested_enchantment')}\" --target \"[target]\""
        )
        lines.append(
            f"- COMPLETE ONLY AFTER PROOF: python3 scripts/enchantment.py complete {contract['player']} --proof \"[photo/description]\" --outcome \"[effect]\""
        )
    if mechanics.get("active_enchantment"):
        active = mechanics.get("active_enchantment")
        lines.append(f"ACTIVE_ENCHANTMENT: {active.get('spell')} on {active.get('target')} awaiting {active.get('proof_required')}")
        lines.append(
            f"- FORMAL COMPLETE: python3 scripts/enchantment.py complete {contract['player']} --proof \"[photo/description]\" --outcome \"[effect]\""
        )
    if mechanics.get("dice_opportunity"):
        lines.append("DICE_OPPORTUNITY:")
        lines.extend(f"- {reason}" for reason in mechanics.get("dice_reasons", []))
        lines.append(f"- {mechanics.get('dice_rule')}")
    if mechanics.get("known_enchantments"):
        lines.append("KNOWN_ENCHANTMENTS: " + ", ".join(mechanics.get("known_enchantments", [])[:10]))
    if tool_posture.get("triggers"):
        lines.append("PAGE_TOOL_TRIGGERS:")
        lines.extend(f"- {item}" for item in tool_posture.get("triggers", []))
    if tool_posture.get("audio_roles"):
        lines.append("PAGE_AUDIO_ROLES:")
        lines.append(f"- spotify: {tool_posture['audio_roles'].get('spotify', '')}")
        lines.append(f"- musicgen: {tool_posture['audio_roles'].get('musicgen', '')}")
    if tool_posture.get("artifact_tools"):
        lines.append("PAGE_ARTIFACT_TOOLS:")
        lines.extend(f"- {item}" for item in tool_posture.get("artifact_tools", []))
    if tool_posture.get("cooldowns"):
        lines.append("PAGE_TOOL_COOLDOWNS_HOURS:")
        lines.extend(f"- {tool}: {hours}" for tool, hours in tool_posture.get("cooldowns", {}).items())
    if tool_posture.get("forbidden_tools"):
        lines.append("PAGE_TOOL_FORBIDDEN:")
        lines.extend(f"- {item}" for item in tool_posture.get("forbidden_tools", []))
    packet_suggestion = contract.get("tool_packet_suggestion") or {}
    if packet_suggestion:
        lines.append("CONDUCTOR_PACKET_SUGGESTION:")
        lines.append(json.dumps(packet_suggestion, ensure_ascii=False, indent=2))
    if classroom:
        available_sources = [
            source.get("id", "")
            for source in classroom.get("source_chapters", [])
            if source.get("available")
        ]
        missing_sources = [
            source.get("id", "")
            for source in classroom.get("source_chapters", [])
            if not source.get("available")
        ]
        lines.append("CLASSROOM_CONTRACT:")
        lines.append(f"- class: {classroom.get('class_name')}")
        lines.append(f"- professor: {classroom.get('professor')} [{classroom.get('voice')}]")
        lines.append(f"- room: {classroom.get('room')}")
        lines.append(f"- lesson: {classroom.get('lesson_title')} ({classroom.get('lesson_id')})")
        lines.append(f"- segment: {int(classroom.get('segment_index') or 0) + 1} - {classroom.get('segment')}")
        lines.append(f"- active_attendance: {'yes' if classroom.get('active') else 'no - run class-lecture.py --attend before treating this as attended'}")
        lines.append(f"- teaches: {classroom.get('lesson_teaches')}")
        lines.append(f"- style: {classroom.get('lesson_style')}")
        lines.append(f"- classmates: {', '.join(classroom.get('classmates', [])) or 'none listed'}")
        if classroom.get("enchantments"):
            lines.append(f"- enchantments_taught: {', '.join(classroom.get('enchantments', []))}")
        if classroom.get("practice_shapes"):
            lines.append(f"- practice_shapes: {', '.join(classroom.get('practice_shapes', []))}")
        lines.append(f"- sources_available: {', '.join(available_sources) if available_sources else 'none yet'}")
        lines.append(f"- sources_missing_but_mapped: {', '.join(missing_sources) if missing_sources else 'none'}")
    lines.append("LONG_MEMORY:")
    lines.extend(f"- {item}" for item in story_context.get("continuity_threads", [])[:5])
    lines.append("QUIET_LIFE:")
    lines.extend(f"- {item}" for item in story_context.get("quiet_life_threads", [])[:4])
    lines.append("MODEL_GUIDANCE:")
    lines.extend(f"- {item}" for item in story_context.get("model_guidance", [])[:4])
    anchor = story_context.get("scene_continuity_anchor") or {}
    if anchor:
        lines.append("SCENE_CONTINUITY_ANCHOR:")
        lines.append(f"- previous_location: {anchor.get('location') or 'unknown'}")
        if anchor.get("cast"):
            lines.append(f"- previous_cast: {anchor.get('cast')}")
        if anchor.get("ending"):
            lines.append(f"- last_visible_beat: {anchor.get('ending')}")
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
    actions = story_context.get("open_simulation_actions") or []
    if actions:
        lines.append("OPEN_SIMULATION_ACTIONS:")
        for action in actions[:5]:
            priority = f"{action.get('priority')} " if action.get("priority") else ""
            lines.append(f"- {priority}{action.get('hook')}")
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


def scene_body_before_choices(text: str) -> str:
    match = re.search(r"(?im)^\s*(?:what do you do\??|choices?:|\d+\.\s*)", text)
    if match:
        return text[:match.start()].strip()
    first_tag = re.search(r"(?im)^\s*(?:\d+\.\s*)?\[(?:LIFE|ARC|SURPRISE)\]", text)
    if first_tag:
        return text[:first_tag.start()].strip()
    return text.strip()


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z][A-Za-z']*", text))


def scene_paragraph_count(text: str) -> int:
    paragraphs = [p for p in re.split(r"\n\s*\n+", text.strip()) if word_count(p) >= 18]
    return len(paragraphs)


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
    body = scene_body_before_choices(text)
    fullness = contract.get("scene_fullness") or {}
    min_words = int(fullness.get("minimum_words") or 0)
    min_paragraphs = int(fullness.get("minimum_paragraphs") or 0)
    body_words = word_count(body)
    body_paragraphs = scene_paragraph_count(body)
    if min_words and body_words < min_words:
        failures.append(
            f"scene is underwritten: {body_words} words before choices; minimum is {min_words}"
        )
    if min_paragraphs and body_paragraphs < min_paragraphs:
        failures.append(
            f"scene is too compressed: {body_paragraphs} substantial paragraphs before choices; minimum is {min_paragraphs}"
        )

    if life_words & PLOT_WORDS and not life_words & LIFE_WORDS:
        failures.append("LIFE choice reads plot-forward; make it mundane and human")
    if not (life_words & LIFE_WORDS):
        failures.append("LIFE choice needs a concrete ordinary action or care beat")
    if not (arc_words & PLOT_WORDS):
        failures.append("ARC choice needs to clearly touch the current story thread")
    if not (surprise_words & SURPRISE_WORDS):
        failures.append("SURPRISE choice needs a sideways/reframing action")
    choice_min = int(fullness.get("choice_min_words") or 0)
    if choice_min:
        for label, body_text in choices.items():
            if word_count(body_text) < choice_min:
                failures.append(f"{label} choice is too terse; make it a polished invitation")

    if contract["scene_mode"] in {"slice", "school-life"}:
        first_part = "\n".join(text.splitlines()[:8]).lower()
        crisis_words = {"attack", "scream", "blood", "nothing", "duskthorn", "wicker", "shatter", "danger"}
        if words(first_part) & crisis_words:
            failures.append("slice/school-life opening starts with crisis pressure")

    page = contract.get("page_contract") or {}
    page_type = page.get("page_type")
    if page_type in {"slice_of_life", "rest"}:
        first_part = "\n".join(text.splitlines()[:10]).lower()
        hard_pressure = {"attack", "scream", "blood", "ambush", "chase", "threat", "shatter"}
        if words(first_part) & hard_pressure:
            failures.append(f"{page.get('page_label', page_type)} opens with hard conflict pressure")
    if page_type == "rest":
        duty_words = {"must", "should", "urgent", "owe", "deadline", "failure"}
        if words(text[:900]) & duty_words:
            failures.append("Rest Page uses pressure/debt language instead of permission")
    if page_type == "wonder_compass":
        compass_markers = {"notice", "embark", "sense", "write", "rest", "souvenir"}
        if not (text_words := words(text)) & compass_markers:
            failures.append("Wonder Compass Page does not name any Compass step or souvenir")
        false_completion = {"completed", "finished", "done", "succeeds"}
        if (text_words & false_completion) and not ({"send", "tell", "write", "share"} & text_words):
            failures.append("Wonder Compass Page appears to complete the real-world task without player proof")

    mechanics = contract.get("mechanics", {})
    text_words = words(text)
    first_500 = text[:500].lower()
    classroom = contract.get("classroom_contract") or {}
    if classroom and classroom.get("active"):
        compressed_patterns = [
            r"\bclass passes\b",
            r"\blecture covers\b",
            r"\bafter class\b",
            r"\bby the end of class\b",
            r"\byou spend the period\b",
            r"\bthe lesson wraps\b",
            r"\bthe class wraps\b",
            r"\bthe professor summarizes\b",
        ]
        lowered = text.lower()
        if any(re.search(pattern, lowered) for pattern in compressed_patterns):
            failures.append("classroom scene is compressed into a period summary instead of rendering the current segment")
        professor = classroom.get("professor") or ""
        professor_terms = [
            term for term in re.findall(r"[A-Za-z]+", professor.lower())
            if term not in {"professor", "doctor"} and len(term) >= 4
        ]
        if professor_terms and not any(term in lowered for term in professor_terms):
            failures.append("classroom scene does not include the professor teaching in-scene")
        classmates = classroom.get("classmates") or []
        classmate_hits = 0
        for name in classmates:
            terms = [term for term in re.findall(r"[A-Za-z]+", name.lower()) if len(term) >= 4]
            if terms and any(term in lowered for term in terms):
                classmate_hits += 1
        if classmates and classmate_hits == 0:
            failures.append("classroom scene needs at least one named classmate reaction, question, or interruption")
        room = classroom.get("room") or ""
        room_terms = [term for term in re.findall(r"[A-Za-z]+", room.lower()) if len(term) >= 4]
        if room_terms and not any(term in first_500 for term in room_terms[:4]):
            failures.append("classroom opening does not ground the actual room")
        continue_words = {"continue", "lesson", "ask", "question", "practice", "demonstrate", "demonstration"}
        if not (words(choices["ARC"]) & continue_words):
            failures.append("classroom ARC choice should continue the lesson, ask a question, or try a practice")
    if mechanics.get("enchantment_opportunity"):
        has_enchantment = "enchantment" in text_words or "enchant" in text.lower()
        has_known_spell = any((name or "").lower() in text.lower() for name in mechanics.get("known_enchantments", []))
        if not (has_enchantment or has_known_spell):
            failures.append("scene contract names an Enchantment opportunity, but no Enchantment is offered or mentioned")
    if contract["scene_mode"] == "enchantment" or mechanics.get("active_enchantment"):
        ritual_markers = {"photo", "describe", "description", "proof", "camera", "send"}
        if not (text_words & ritual_markers):
            failures.append("Enchantment scene does not ask for real proof/photo/description")
        false_completion = {"completed", "succeeds", "worked", "finished", "resolves", "defeated"}
        if (text_words & false_completion) and not mechanics.get("active_enchantment"):
            failures.append("Enchantment appears resolved in prose without active proof/completion state")
    risky_words = text_words & DICE_RISK_WORDS
    if mechanics.get("dice_opportunity") and risky_words:
        dice_markers = {"roll", "dice", "belief", "risk", "uncertain", "try"}
        if not (text_words & dice_markers):
            failures.append("risky uncertain action appears without dice/Belief-roll framing")

    location = contract.get("current_location") or ""
    location_terms = [w for w in re.findall(r"[A-Za-z]+", location.lower()) if len(w) >= 4]
    if location_terms and not any(term in first_500 for term in location_terms[:4]):
        failures.append("opening does not ground the current physical location")

    anchor = (contract.get("story_context") or {}).get("scene_continuity_anchor") or {}
    previous_location = anchor.get("location") or ""
    previous_terms = [w for w in re.findall(r"[A-Za-z]+", previous_location.lower()) if len(w) >= 4]
    if previous_terms and not any(term in first_500 for term in previous_terms[:4]):
        failures.append("opening does not honor the previous scene location before moving")

    return failures


def _thread_touchpoint(contract: dict[str, Any]) -> str:
    story = contract.get("story_context") or {}
    active = story.get("active_story_threads") or []
    for item in active:
        title = str(item.get("title") or item.get("name") or item.get("thread") or "").strip()
        if title:
            return title
    pressure = str(contract.get("story_pressure") or "").strip()
    if pressure and pressure.lower() != "none":
        return pressure.split("|", 1)[0].strip()
    return "the active thread"


def _plain_numbered_choices(text: str) -> list[tuple[int, str]]:
    """Return the final visible 1/2/3 choice set, even if the model forgot tags."""
    lines = text.splitlines()
    found: list[tuple[int, str]] = []
    for line in lines:
        m = re.match(r"^\s*(?:[*-]\s*)?\(?([123])\)?[.)]\s*(?:\[(?:LIFE|ARC|SURPRISE)\]\s*)?(.+?)\s*$", line, re.IGNORECASE)
        if not m:
            continue
        found.append((int(m.group(1)), m.group(2).strip()))
    # Keep the last complete 1/2/3 set. Earlier numbered lists may be classroom
    # content, lecture steps, or prose structure.
    for idx in range(len(found) - 3, -1, -1):
        triplet = found[idx:idx + 3]
        if [n for n, _body in triplet] == [1, 2, 3]:
            return triplet
    return []


def _tag_existing_choice_block(text: str) -> str:
    """Tag an existing Rule of Three block instead of appending canned choices."""
    lines = text.splitlines()
    choice_indexes: list[tuple[int, int, str]] = []
    for idx, line in enumerate(lines):
        m = re.match(r"^\s*(?:[*-]\s*)?\(?([123])\)?[.)]\s*(?:\[(?:LIFE|ARC|SURPRISE)\]\s*)?(.+?)\s*$", line, re.IGNORECASE)
        if m:
            choice_indexes.append((idx, int(m.group(1)), m.group(2).strip()))

    candidates: list[tuple[int, bool, list[tuple[int, int, str]]]] = []
    for start in range(len(choice_indexes) - 3, -1, -1):
        triplet = choice_indexes[start:start + 3]
        if [n for _idx, n, _body in triplet] != [1, 2, 3]:
            continue
        combined = " ".join(body for _idx, _number, body in triplet).lower()
        generic = any(
            phrase in combined
            for phrase in (
                "stay with the ordinary beat",
                "make a belief roll",
                "follow the odd draft",
                "active thread",
                "rising day",
            )
        )
        candidates.append((start, generic, triplet))

    if not candidates:
        return text

    non_generic = [candidate for candidate in candidates if not candidate[1]]
    # Prefer the latest scene-specific choice set. If the only visible choices
    # are generic, keep them rather than inventing a new menu here.
    _start, _generic, selected = (non_generic[-1] if non_generic else candidates[-1])

    labels = {1: "LIFE", 2: "ARC", 3: "SURPRISE"}
    first_line_idx = selected[0][0]
    # Drop duplicate/canned choice text after the chosen triplet. It is safer to
    # preserve the scene's own choices than to leave two menus.
    while first_line_idx > 0 and not lines[first_line_idx - 1].strip():
        first_line_idx -= 1
    if first_line_idx > 0 and re.match(r"^\s*what do you do\??\s*$", lines[first_line_idx - 1], re.IGNORECASE):
        first_line_idx -= 1

    rebuilt = lines[:first_line_idx]
    rebuilt.append("What do you do?")
    for _idx, number, body in selected:
        if re.search(r"\[(?:LIFE|ARC|SURPRISE)\]", body, re.IGNORECASE):
            rebuilt.append(f"{number}. {body}")
        else:
            rebuilt.append(f"{number}. [{labels[number]}] {body}")
    return "\n".join(rebuilt).rstrip() + "\n"


def _replace_choice_block(text: str, contract: dict[str, Any]) -> str:
    tagged_existing = _tag_existing_choice_block(text)
    if tagged_existing != text or extract_tagged_choices(tagged_existing):
        return tagged_existing

    # No clear player-facing choice block exists. Do not append a canned generic
    # menu; let validation fail so the model/operator rewrites the actual scene.
    return text


def repair_scene_text(text: str, contract: dict[str, Any], failures: list[str] | None = None) -> str:
    """Make a conservative second draft that satisfies structural rails.

    This is not a creative rewrite engine. It preserves the generated scene as
    much as possible, then fixes the common small-model failures: missing
    grounding, a slice/rest opening that overplays conflict, and Rule of Three
    choices that collapse into one another.
    """
    failures = failures or validate_scene(text, contract)
    repaired = text.strip()
    location = contract.get("current_location") or "the room"
    page = contract.get("page_contract") or {}
    page_type = page.get("page_type")
    first_part = "\n".join(repaired.splitlines()[:10]).lower()

    needs_quiet_opening = (
        contract.get("scene_mode") in {"slice", "school-life"}
        and any("opening starts with crisis pressure" in item for item in failures)
    ) or (
        page_type in {"slice_of_life", "rest"}
        and any("opens with hard conflict pressure" in item for item in failures)
    )
    needs_grounding = any("ground" in item or "previous scene location" in item for item in failures)

    if needs_quiet_opening:
        paragraphs = re.split(r"\n\s*\n", repaired, maxsplit=1)
        rest = paragraphs[1] if len(paragraphs) > 1 else ""
        opener = (
            f"You are still in {location}. The page keeps its hand on ordinary life first: "
            "the harder pressure remains at the edge of the room, present but not allowed to take the first chair."
        )
        repaired = opener + ("\n\n" + rest.strip() if rest.strip() else "")
    elif needs_grounding and location:
        repaired = f"You are still in {location}. Nothing important has been skipped; the room holds its place around you.\n\n" + repaired

    choice_failures = [
        "missing tagged choices",
        "LIFE choice",
        "ARC choice",
        "SURPRISE choice",
        "classroom ARC choice",
    ]
    if any(any(needle in item for needle in choice_failures) for item in failures):
        repaired = _replace_choice_block(repaired, contract)

    if not repaired.endswith("\n"):
        repaired += "\n"
    return repaired


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or validate a compact scene contract.")
    parser.add_argument("player", nargs="?", default="bj")
    parser.add_argument("--mode", choices=sorted(SCENE_MODES))
    parser.add_argument("--drama-budget", choices=sorted(DRAMA_BUDGETS))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--validate-scene", type=Path)
    parser.add_argument("--repair-scene", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    contract = build_contract(args.player, args.mode, args.drama_budget)
    if args.repair_scene:
        if not args.repair_scene.exists():
            print(f"scene file not found: {args.repair_scene}", file=sys.stderr)
            return 1
        text = args.repair_scene.read_text(encoding="utf-8")
        failures = validate_scene(text, contract)
        repaired = repair_scene_text(text, contract, failures)
        output = args.out or args.repair_scene
        output.write_text(repaired, encoding="utf-8")
        print("SCENE CONTRACT REPAIRED")
        if failures:
            for failure in failures:
                print(f"- {failure}")
        return 0

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

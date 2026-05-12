#!/usr/bin/env python3
"""Choose the current Enchantify Page contract.

Pages are the living-book grammar: one primary container, one optional
secondary flavor, a clear player invitation, and an artifact the Book should
keep. This script is deliberately deterministic so smaller models get rails,
not another fog bank.
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
MECHANICS = BASE / "mechanics"

_story_context_spec = importlib.util.spec_from_file_location("story_context", SCRIPTS / "story-context.py")
_story_context = importlib.util.module_from_spec(_story_context_spec)
assert _story_context_spec and _story_context_spec.loader
_story_context_spec.loader.exec_module(_story_context)
build_story_context = _story_context.build_context


PAGE_TYPES: dict[str, dict[str, Any]] = {
    "slice_of_life": {
        "label": "Slice of Life Page",
        "purpose": "Let the player inhabit the Academy without forcing drama.",
        "allowed_systems": ["NPC relationships", "heartbeat atmosphere", "school-life texture", "quiet-life threads", "food logging", "small clues"],
        "forbidden_systems": ["major conflict", "forced Compass Run", "heavy Nothing pressure", "lore dump", "scene teleport"],
        "player_invitation": "Be present, talk, notice, or choose a small human action.",
        "closure_condition": "One changed detail, remembered feeling, relationship beat, or ordinary decision.",
        "artifact_due": ["scene ledger", "diary note", "relationship note or margin note"],
        "emotional_intensity": "low",
    },
    "conflict": {
        "label": "Conflict Page",
        "purpose": "Apply pressure that reveals what the player values.",
        "allowed_systems": ["dice", "Belief costs", "Nothing manifestations", "story threads", "NPC conflict", "talismans", "Enchantment opportunity"],
        "forbidden_systems": ["cozy meandering", "unrelated research", "excessive explanation", "fake resolution without mechanics"],
        "player_invitation": "Respond, defend, investigate, choose a side, or risk Belief.",
        "closure_condition": "A pressure changes state: cost paid, clue gained, relationship changed, threat deferred, or thread updated.",
        "artifact_due": ["thread update", "Belief change", "conflict log", "diary reflection", "possible Bleed mention"],
        "emotional_intensity": "high",
    },
    "enchantment": {
        "label": "Enchantment Page",
        "purpose": "Bridge Academy magic into the real world through a photo or vivid description.",
        "allowed_systems": ["Flyleaf", "scripts/enchantment.py", "photo proof", "Belief cost/reward", "spell result", "archive page"],
        "forbidden_systems": ["prose-only spell completion", "offering every spell", "unrelated research", "treating the real object as generic input"],
        "player_invitation": "Choose an Enchantment, send a photo, or describe a real object/place in detail.",
        "closure_condition": "Formal start exists, proof is received, completion script runs, and the story reflects the result.",
        "artifact_due": ["spell ledger", "Flyleaf/Belief update", "archive page", "transformed object or clue"],
        "emotional_intensity": "medium",
    },
    "wonder_compass": {
        "label": "Wonder Compass Page",
        "purpose": "Move the player into lived attention.",
        "allowed_systems": ["Notice", "Embark", "Sense", "Write", "Rest", "heartbeat calibration", "souvenir writing", "printed card"],
        "forbidden_systems": ["homework tone", "pretended completion", "overcomplication", "pushing outside when inside is right"],
        "player_invitation": "Notice something real, do one small thing, sense it, write one sentence, and rest.",
        "closure_condition": "The player actually performs the steps and offers a souvenir sentence.",
        "artifact_due": ["souvenir file", "printed card", "Belief +9", "Compass history update"],
        "emotional_intensity": "medium",
    },
    "letter": {
        "label": "Letter Page",
        "purpose": "Let the world reach toward the player.",
        "allowed_systems": ["NPC outreach", "NPC research", "printing", "Telegram", "voice", "tick-queue seed", "relationship update"],
        "forbidden_systems": ["generic thinking-of-you text", "automatic urgent quest", "unrelated conflict escalation"],
        "player_invitation": "Receive, read, answer, follow up, ignore, save, or carry the note into play.",
        "closure_condition": "The message is delivered, attributed, and either answered, seeded, or preserved.",
        "artifact_due": ["letter file", "printed page", "relationship note", "tick-queue seed", "possible Inside Cover quest"],
        "emotional_intensity": "low",
    },
    "anchor": {
        "label": "Anchor Page",
        "purpose": "Bind a real-world place into the Labyrinth.",
        "allowed_systems": ["GPS", "anchor-check.py", "Outer Stacks", "Wonder Compass room kinds", "fae", "local rules", "visit milestones"],
        "forbidden_systems": ["generic fantasy rooms", "hallucinated room kinds", "ignoring actual place context", "unrelated arc pressure"],
        "player_invitation": "Name what the place holds, visit, check in, open the door, or notice what changed.",
        "closure_condition": "The place is mapped, revisited, or changed; visit count and local rule are honored.",
        "artifact_due": ["anchor record", "map/fold-out page", "Outer Stacks room", "local rule", "Belief update"],
        "emotional_intensity": "medium",
    },
    "rest": {
        "label": "Rest Page",
        "purpose": "Protect the player's energy.",
        "allowed_systems": ["heartbeat atmosphere", "Mossbloom tone", "kind NPC presence", "food/water/sleep care", "Center/Rest language"],
        "forbidden_systems": ["urgent choices", "major conflict", "mandatory tasks", "guilt", "dramatic escalation"],
        "player_invitation": "Breathe, sit, receive care, notice one tiny thing, or stop without guilt.",
        "closure_condition": "The player is allowed to stop or continue softly; no debt is created.",
        "artifact_due": ["diary note", "margin note", "care note", "continuity"],
        "emotional_intensity": "low",
    },
    "archive": {
        "label": "Archive Page",
        "purpose": "Preserve what happened.",
        "allowed_systems": ["scene ledger", "diary", "player file", "thread updates", "Belief changes", "relationship summaries", "artifact generation"],
        "forbidden_systems": ["new drama", "new unresolved pressure", "unearned cliffhanger"],
        "player_invitation": "Review, reflect, choose what mattered, or name what changed.",
        "closure_condition": "State has been written and proof exists.",
        "artifact_due": ["diary", "ledger", "field-journal page", "memory card", "quest/spell/thread record"],
        "emotional_intensity": "low",
    },
    "bleed": {
        "label": "Bleed Page",
        "purpose": "Show the world interpreting itself.",
        "allowed_systems": ["The Bleed", "Sparky", "newspaper", "marginalia", "world simulation", "rumor", "forecast"],
        "forbidden_systems": ["generic news voice", "overly meta reporting", "making all world movement front-page drama"],
        "player_invitation": "Read, react, follow a thread, laugh, worry, or notice a pattern.",
        "closure_condition": "The issue or clipping exists and points toward concrete live pressures.",
        "artifact_due": ["newspaper issue", "clipping", "bulletin page", "margin note", "rumor entry"],
        "emotional_intensity": "medium",
    },
}


MODE_TO_PAGE = {
    "slice": "slice_of_life",
    "school-life": "slice_of_life",
    "arc": "conflict",
    "mystery": "conflict",
    "aftermath": "archive",
    "compass": "wonder_compass",
    "enchantment": "enchantment",
}


def run_script(args: list[str]) -> str:
    proc = subprocess.run(args, cwd=BASE, capture_output=True, text=True, timeout=45)
    return (proc.stdout or "").strip() if proc.returncode == 0 else ""


def words(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z']+", (text or "").lower()))


def slate_value(slate: str, key: str) -> str:
    m = re.search(rf"^{re.escape(key)}:\s*(.+)$", slate, re.MULTILINE)
    return m.group(1).strip() if m else ""


def heartbeat_text(limit: int = 220) -> str:
    path = BASE / "HEARTBEAT.md"
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="ignore")
    pulse = re.search(r"<!-- PULSE_START -->(.*?)<!-- PULSE_END -->", text, re.DOTALL)
    chunk = pulse.group(1) if pulse else text
    return re.sub(r"\s+", " ", chunk).strip()[:limit]


def choose_page_type(mode: str | None, slate: str, story_context: dict[str, Any], requested: str | None = None) -> tuple[str, str]:
    if requested:
        return requested, "requested explicitly"
    if mode in MODE_TO_PAGE:
        page = MODE_TO_PAGE[mode]
        if mode in {"arc", "mystery"}:
            return page, f"scene mode {mode} carries story pressure"
        return page, f"scene mode {mode}"

    combined = " ".join([
        slate_value(slate, "SCHEDULE"),
        slate_value(slate, "STORY"),
        slate_value(slate, "NOTHING"),
        heartbeat_text(),
        " ".join(story_context.get("continuity_threads", [])),
        " ".join(item.get("title", "") for item in story_context.get("narrative_obligations", [])),
    ]).lower()
    w = words(combined)
    if {"gps", "anchor", "outer", "stacks", "ley"} & w:
        return "anchor", "location/anchor language is active"
    if {"enchantment", "spell", "photo", "flyleaf"} & w:
        return "enchantment", "spell/photo language is active"
    if {"compass", "notice", "embark", "souvenir"} & w:
        return "wonder_compass", "Wonder Compass language is active"
    if {"letter", "research", "outreach", "note"} & w and "class" not in w:
        return "letter", "message/research language is active"
    if {"tired", "sleep", "rest", "low", "overwhelmed", "recovery"} & w:
        return "rest", "care/recovery language is active"
    if {"wicker", "duskthorn", "nothing", "threat", "attack", "investigation", "clue"} & w:
        return "conflict", "story pressure is active"
    return "slice_of_life", "default page for Academy presence"


def secondary_flavor(page_type: str, slate: str, story_context: dict[str, Any]) -> str:
    story = slate_value(slate, "STORY").lower()
    schedule = slate_value(slate, "SCHEDULE").lower()
    obligations = story_context.get("narrative_obligations", [])
    seeds = story_context.get("emerging_thread_seeds", [])
    if page_type != "conflict" and any(word in story for word in ("wicker", "duskthorn", "investigation", "thread")):
        return "thread_pressure"
    if page_type != "rest" and ("recovery" in story.lower() or any(item.get("kind") == "drama_budget_guard" for item in obligations)):
        return "recovery_tone"
    if page_type != "slice_of_life" and any(word in schedule for word in ("class", "lunch", "club", "common room")):
        return "school_life_texture"
    if seeds:
        return "emerging_seed"
    return ""


def build_contract(player: str = "bj", mode: str | None = None, requested_page: str | None = None) -> dict[str, Any]:
    slate = run_script([sys.executable, str(SCRIPTS / "scene-director.py"), player, "--slate-only"])
    story_context = build_story_context(player)
    page_type, reason = choose_page_type(mode, slate, story_context, requested_page)
    definition = PAGE_TYPES[page_type]
    flavor = secondary_flavor(page_type, slate, story_context)
    if page_type == "rest":
        scene_mode = "slice"
        drama_budget = "low"
    elif page_type == "conflict":
        scene_mode = "mystery" if "investigation" in slate_value(slate, "STORY").lower() else "arc"
        drama_budget = "medium"
    elif page_type == "wonder_compass":
        scene_mode = "compass"
        drama_budget = "medium"
    elif page_type == "enchantment":
        scene_mode = "enchantment"
        drama_budget = "medium"
    elif page_type == "archive":
        scene_mode = "aftermath"
        drama_budget = "low"
    else:
        scene_mode = "school-life" if "class" in slate_value(slate, "SCHEDULE").lower() else "slice"
        drama_budget = "low"

    return {
        "player": player,
        "page_type": page_type,
        "page_label": definition["label"],
        "selection_reason": reason,
        "secondary_flavor": flavor,
        "purpose": definition["purpose"],
        "emotional_intensity": definition["emotional_intensity"],
        "allowed_systems": definition["allowed_systems"],
        "forbidden_systems": definition["forbidden_systems"],
        "player_invitation": definition["player_invitation"],
        "closure_condition": definition["closure_condition"],
        "artifact_due": definition["artifact_due"],
        "recommended_scene_mode": scene_mode,
        "recommended_drama_budget": drama_budget,
        "state_hints": {
            "story_pressure": slate_value(slate, "STORY"),
            "schedule": slate_value(slate, "SCHEDULE"),
            "nothing": slate_value(slate, "NOTHING"),
            "continuity": story_context.get("continuity_threads", [])[:3],
            "narrative_obligations": story_context.get("narrative_obligations", [])[:3],
            "open_simulation_actions": story_context.get("open_simulation_actions", [])[:3],
            "emerging_thread_seeds": story_context.get("emerging_thread_seeds", [])[:4],
        },
        "small_model_rule": "What page are we on? What does this page want from the player? What proof does it leave behind?",
    }


def render_text(contract: dict[str, Any]) -> str:
    lines = [
        "PAGE CONTRACT",
        f"PAGE_TYPE: {contract['page_type']} ({contract['page_label']})",
        f"SELECTION_REASON: {contract['selection_reason']}",
        f"SECONDARY_FLAVOR: {contract.get('secondary_flavor') or 'none'}",
        f"PURPOSE: {contract['purpose']}",
        f"EMOTIONAL_INTENSITY: {contract['emotional_intensity']}",
        f"RECOMMENDED_SCENE_MODE: {contract['recommended_scene_mode']}",
        f"RECOMMENDED_DRAMA_BUDGET: {contract['recommended_drama_budget']}",
        f"PLAYER_INVITATION: {contract['player_invitation']}",
        f"CLOSURE_CONDITION: {contract['closure_condition']}",
        "ARTIFACT_DUE:",
    ]
    lines.extend(f"- {item}" for item in contract["artifact_due"])
    lines.append("ALLOWED_SYSTEMS:")
    lines.extend(f"- {item}" for item in contract["allowed_systems"])
    lines.append("FORBIDDEN_SYSTEMS:")
    lines.extend(f"- {item}" for item in contract["forbidden_systems"])
    lines.append(f"SMALL_MODEL_RULE: {contract['small_model_rule']}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an Enchantify Page contract.")
    parser.add_argument("player", nargs="?", default="bj")
    parser.add_argument("--mode")
    parser.add_argument("--page-type", choices=sorted(PAGE_TYPES))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    contract = build_contract(args.player, mode=args.mode, requested_page=args.page_type)
    if args.json:
        print(json.dumps(contract, indent=2, ensure_ascii=False))
    else:
        print(render_text(contract))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

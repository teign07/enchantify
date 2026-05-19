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
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent.parent
SCRIPTS = BASE / "scripts"
MECHANICS = BASE / "mechanics"
SCENE_OUTBOX = BASE / "tmp" / "scene-outbox"

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
    "body_marginalia": {
        "label": "Dr. Vellum / Body Marginalia Page",
        "purpose": "Translate body, fuel, movement, sleep, labs, blood pressure, and longevity research into one practical daily experiment.",
        "allowed_systems": ["Dr. Vellum", "vellum-chart.py", "food_log.py", "fuel log", "health data", "blood pressure", "labs", "supplements", "exercise", "longevity research"],
        "forbidden_systems": ["moralizing", "diet shame", "diagnosis", "prescription changes", "heroic protocols", "generic wellness copy", "ignoring medication/safety context"],
        "player_invitation": "Choose one body-support action, ask a longevity question, log a data point, start/review an experiment, or decline without penalty.",
        "closure_condition": "One BJ-sized action, experiment, metric, safety flag, or doctor/pharmacist question is named and recorded when useful.",
        "artifact_due": ["Vellum chart update", "Body Marginalia note", "fuel/body observation", "experiment record", "doctor/pharmacist question"],
        "emotional_intensity": "low",
    },
    "difficult": {
        "label": "Dr. Inkrest / Difficult Page",
        "purpose": "Hold emotional difficulty through narrative therapy, grounding, and reauthoring.",
        "allowed_systems": ["Dr. Inkrest", "therapy-chart.py", "Vellum chart", "fuel log", "heartbeat", "daydream/image work", "grounding", "narrative therapy"],
        "forbidden_systems": ["diagnosis", "forced catharsis", "trauma excavation without consent", "major plot escalation", "generic wellness copy"],
        "player_invitation": "Choose reflection, grounding, reauthoring, daydream/image work, quiet company, or stopping.",
        "closure_condition": "One feeling or problem is externalized, one preferred-story sentence or grounding step exists, and any artifact is saved only if useful.",
        "artifact_due": ["therapy chart check-in", "Difficult Page note", "reauthoring note", "grounding card", "question for real therapy"],
        "emotional_intensity": "low",
    },
    "ledger": {
        "label": "Gimble / Ledger Page",
        "purpose": "Turn money fog into one clear, shame-free next action.",
        "allowed_systems": ["Gimble", "ledger-faculty.py", "Actual Budget", "SimpleFIN", "transaction review", "category balances", "upcoming bills", "safe-to-spend", "tiny adventure budget"],
        "forbidden_systems": ["money shame", "moralizing debt", "moving money without explicit permission", "bank login handling", "tax/legal certainty", "risky investment advice", "transaction walls"],
        "player_invitation": "Bind one transaction, ask for money weather, review one vessel, plan a tiny adventure, or stop before overwhelm.",
        "closure_condition": "BJ knows one number, one risk, and one next action, or the ledger records what is still unknown.",
        "artifact_due": ["Ledger chart update", "Money Weather Report", "Alchemical Audit", "Tiny Leak note", "Adventure Permission Slip"],
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


PAGE_TOOL_POSTURES: dict[str, dict[str, Any]] = {
    "slice_of_life": {
        "posture": "gentle ambience, not spectacle",
        "intrusion_level": "low",
        "cooldowns": {"image": 0, "lights": 4, "spotify": 6, "music": 24, "printer": 24, "wallpaper": 12, "app_actions": 24},
        "audio_roles": {"spotify": "human-world continuity and ordinary Academy mood", "musicgen": "rare magic glint only"},
        "artifact_tools": ["image", "diary", "relationship note"],
        "preferred_tools": ["image"],
        "allowed_tools": ["voice", "lights", "spotify", "food_log"],
        "rare_tools": ["musicgen", "printer"],
        "forbidden_tools": ["web_search unless the player explicitly asks or an Unwritten detail enters"],
        "triggers": [
            "image: one manuscript-style scene artifact when the response has a concrete visual beat",
            "lights: warm/academy only for arrival, class, evening, or ritual settling",
            "spotify: mood_only when current music should tint the Academy softly",
            "food_log: only when the player actually mentions food or drink",
        ],
        "default_sequence": ["text", "image", "voice"],
    },
    "conflict": {
        "posture": "atmospheric pressure with mechanical clarity",
        "intrusion_level": "high",
        "cooldowns": {"image": 0, "lights": 3, "spotify": 4, "music": 12, "printer": 24, "wallpaper": 8, "app_actions": 24},
        "audio_roles": {"spotify": "human-world tension support", "musicgen": "uncanny one-off leitmotif for the Nothing, fae, or ritual pressure"},
        "artifact_tools": ["image", "musicgen", "wallpaper", "reminders", "thread log"],
        "preferred_tools": ["dice", "image", "lights"],
        "allowed_tools": ["voice", "spotify", "musicgen", "printer", "wallpaper", "app_actions"],
        "rare_tools": ["web_search"],
        "forbidden_tools": ["web_search unless conflict touches the Unwritten or real-world research"],
        "triggers": [
            "lights: Nothing pressure may dim the room into deep violet/blue with a slow transition",
            "spotify: spooky, tense, or low instrumental mood when pressure enters the room",
            "musicgen: generate a short leitmotif for major conflict, ritual threshold, or recurring antagonist beat",
            "wallpaper: only for major breach, Nothing mark, or arc state change worth seeing after Telegram closes",
            "app_actions: private reminder/note only when the scene leaves a concrete obligation or taunt; never social posting",
            "image: field-journal artifact when a trace, wound, door, talisman, or confrontation becomes visually specific",
            "dice: risky uncertain player action before resolution",
        ],
        "default_sequence": ["text", "lights", "image", "voice", "music", "spotify", "wallpaper", "app_actions"],
    },
    "enchantment": {
        "posture": "real-world ritual, proof-gated",
        "intrusion_level": "medium",
        "cooldowns": {"image": 0, "lights": 2, "spotify": 6, "music": 12, "printer": 12, "wallpaper": 12, "app_actions": 24},
        "audio_roles": {"spotify": "ground the player before/after ritual", "musicgen": "short impossible spell-tone after proof"},
        "artifact_tools": ["image", "printer", "wallpaper", "spell ledger"],
        "preferred_tools": ["enchantment_script", "image", "vision_or_photo"],
        "allowed_tools": ["lights", "musicgen", "spotify", "printer", "voice", "wallpaper"],
        "rare_tools": ["web_search"],
        "forbidden_tools": ["prose-only spell completion", "tool fireworks before proof"],
        "triggers": [
            "lights: use a ritual color when the spell formally starts, not when it merely gets mentioned",
            "image: after proof/completion, create an archive page or transformed object artifact",
            "musicgen: short chime/texture only for completed or major spells",
            "printer: spell card or archive proof for meaningful completed Enchantments",
        ],
        "default_sequence": ["text", "voice", "lights", "image", "music"],
    },
    "wonder_compass": {
        "posture": "attention support, never homework",
        "intrusion_level": "medium",
        "cooldowns": {"image": 6, "lights": 2, "spotify": 6, "music": 18, "printer": 8, "wallpaper": 12, "app_actions": 24},
        "audio_roles": {"spotify": "soft human-world attention support", "musicgen": "rare direction-tone after a completed run"},
        "artifact_tools": ["printer", "souvenir file", "image"],
        "preferred_tools": ["lights", "voice", "printer"],
        "allowed_tools": ["image", "spotify", "musicgen", "weather", "location"],
        "rare_tools": ["web_search"],
        "forbidden_tools": ["pretended completion", "heavy conflict ambience"],
        "triggers": [
            "lights: match Compass direction when a real step begins",
            "spotify: quiet instrumental support for Sense/Rest, silence or pause for Write when possible",
            "printer: souvenir card only after the player gives a real souvenir sentence",
            "image: optional archive artifact after completion, not before attention lands",
        ],
        "default_sequence": ["text", "voice", "lights"],
    },
    "letter": {
        "posture": "the world reaches out with provenance",
        "intrusion_level": "low",
        "cooldowns": {"image": 6, "lights": 24, "spotify": 24, "music": 48, "printer": 12, "wallpaper": 24, "app_actions": 18},
        "audio_roles": {"spotify": "rare reading atmosphere", "musicgen": "rare character motif for special letters"},
        "artifact_tools": ["web_search", "printer", "image", "apple_notes", "obsidian", "silent_telegram"],
        "preferred_tools": ["web_search", "printer", "image"],
        "allowed_tools": ["voice", "telegram", "silent_telegram", "musicgen", "spotify", "app_actions"],
        "rare_tools": ["lights"],
        "forbidden_tools": ["generic thinking-of-you outreach", "unattributed messages"],
        "triggers": [
            "web_search: NPC research, Unwritten interests, books, local/library context, or timely real-world material",
            "printer: actual letter, field note, or invitation when the message deserves a body",
            "image: letterhead, marginalia, portrait seal, or manuscript artifact",
            "musicgen: rare character motif for special letters only",
        ],
        "default_sequence": ["text", "image", "voice", "printer", "app_actions"],
    },
    "anchor": {
        "posture": "place-binding and local specificity",
        "intrusion_level": "medium",
        "cooldowns": {"image": 4, "lights": 4, "spotify": 12, "music": 12, "printer": 12, "wallpaper": 12, "app_actions": 24},
        "audio_roles": {"spotify": "human-world travel/return mood", "musicgen": "Outer Stacks threshold audio that has never existed before"},
        "artifact_tools": ["gps_anchor", "image", "printer", "wallpaper"],
        "preferred_tools": ["gps_anchor", "location", "image"],
        "allowed_tools": ["lights", "weather", "printer", "voice", "spotify"],
        "rare_tools": ["web_search", "musicgen"],
        "forbidden_tools": ["generic rooms", "hallucinated Outer Stacks kinds"],
        "triggers": [
            "gps_anchor: always use anchor-check.py for real coordinates",
            "web_search: only for place context when it would make the anchor more specific",
            "lights: Outer Stacks threshold or return visit",
            "printer: fold-out map or pocket anchor after creation/milestone",
        ],
        "default_sequence": ["text", "lights", "image", "voice"],
    },
    "rest": {
        "posture": "protect attention and lower demand",
        "intrusion_level": "low",
        "cooldowns": {"image": 12, "lights": 4, "spotify": 8, "music": 24, "printer": 48, "wallpaper": 24, "app_actions": 24},
        "audio_roles": {"spotify": "human-world softness and continuity", "musicgen": "rare lull texture, only when it lowers demand"},
        "artifact_tools": ["diary", "obsidian", "silent_telegram"],
        "preferred_tools": ["lights", "voice"],
        "allowed_tools": ["spotify", "musicgen", "image", "silent_telegram", "app_actions"],
        "rare_tools": ["printer"],
        "forbidden_tools": ["web_search", "major conflict lights", "urgent notifications"],
        "triggers": [
            "lights: warm low brightness or no change; never spooky",
            "spotify: soft/quiet support only if it reduces friction",
            "musicgen: rare lull/rest texture, short and non-demanding",
            "image: only if it soothes or preserves the page without adding pressure",
        ],
        "default_sequence": ["text", "voice", "lights"],
    },
    "difficult": {
        "posture": "therapeutic presence, consent first",
        "intrusion_level": "low",
        "cooldowns": {"image": 24, "lights": 4, "spotify": 8, "music": 48, "printer": 48, "wallpaper": 48, "app_actions": 24},
        "audio_roles": {"spotify": "soft grounding support only if invited", "musicgen": "almost never; therapy should not become spectacle"},
        "artifact_tools": ["therapy-chart", "diary", "silent_telegram"],
        "preferred_tools": ["voice", "therapy-chart"],
        "allowed_tools": ["lights", "spotify", "image", "app_actions"],
        "rare_tools": ["printer", "musicgen"],
        "forbidden_tools": ["web_search unless the player explicitly asks for psychoeducation", "spooky ambience", "urgent notifications"],
        "triggers": [
            "therapy-chart: save check-in, daydream, reauthoring note, or real-therapy question only when the player shares material",
            "lights: warm low brightness only for grounding; never theatrical distress lighting",
            "spotify: soft support only if it reduces friction or the player asks",
            "image: rare, gentle card or symbolic page after consent; never diagnostic",
        ],
        "default_sequence": ["text", "voice"],
    },
    "body_marginalia": {
        "posture": "precise body support, evidence-aware and non-shaming",
        "intrusion_level": "low",
        "cooldowns": {"image": 24, "lights": 8, "spotify": 24, "music": 72, "printer": 24, "wallpaper": 48, "app_actions": 24},
        "audio_roles": {"spotify": "rare steady support for a body experiment", "musicgen": "almost never; Vellum is precise, not theatrical"},
        "artifact_tools": ["vellum-chart", "food_log", "health_reader", "silent_telegram"],
        "preferred_tools": ["vellum-chart", "food_log"],
        "allowed_tools": ["voice", "silent_telegram", "app_actions", "printer", "image"],
        "rare_tools": ["web_search", "spotify"],
        "forbidden_tools": ["spooky ambience", "urgent notifications", "medical certainty without data", "social/public posting"],
        "triggers": [
            "vellum-chart: save BP, lab, supplement, medication, question, or experiment data through the helper script",
            "food_log: only when the player actually mentions food or drink; do not invent intake",
            "web_search: only for explicit current-research questions, and summarize with safety/context caveats",
            "printer: rare Body Marginalia card for a chosen experiment or doctor question",
            "image: rare field-journal body-support card, not diagnostic imagery",
        ],
        "default_sequence": ["text", "voice"],
    },
    "ledger": {
        "posture": "financial clarity without shame",
        "intrusion_level": "low",
        "cooldowns": {"image": 48, "lights": 24, "spotify": 48, "music": 72, "printer": 24, "wallpaper": 48, "app_actions": 12},
        "audio_roles": {"spotify": "almost never; finance support should stay quiet", "musicgen": "never by default"},
        "artifact_tools": ["ledger-faculty", "actual-budget", "telegram", "printer"],
        "preferred_tools": ["ledger-faculty"],
        "allowed_tools": ["voice", "silent_telegram", "printer", "app_actions"],
        "rare_tools": ["image"],
        "forbidden_tools": ["bank login handling", "autonomous money movement", "public/social posting", "spooky ambience"],
        "triggers": [
            "ledger-faculty: use status, money-weather, weekly-audit, adventure-permission, or question for finance support",
            "Actual Budget: only after BJ has completed local setup and config exists",
            "Telegram: useful for daily binding prompts or consent-needed finance questions",
            "printer: rare Money Weather or Adventure Permission card",
        ],
        "default_sequence": ["text", "voice"],
    },
    "archive": {
        "posture": "preserve proof",
        "intrusion_level": "low",
        "cooldowns": {"image": 4, "lights": 24, "spotify": 24, "music": 24, "printer": 8, "wallpaper": 12, "app_actions": 18},
        "audio_roles": {"spotify": "rare closure mood", "musicgen": "chapter/arc completion motif"},
        "artifact_tools": ["printer", "image", "apple_notes", "obsidian", "wallpaper"],
        "preferred_tools": ["printer", "image"],
        "allowed_tools": ["voice", "telegram", "musicgen", "wallpaper", "app_actions"],
        "rare_tools": ["spotify", "lights"],
        "forbidden_tools": ["web_search unless preserving cited research"],
        "triggers": [
            "image: field-journal/archive page for meaningful state changes",
            "printer: cards, closeout artifacts, letters, or memory pages",
            "musicgen: motif only for chapter/arc completion or major memory pages",
        ],
        "default_sequence": ["text", "image", "voice", "printer", "wallpaper", "app_actions"],
    },
    "bleed": {
        "posture": "public interpretation and world digestion",
        "intrusion_level": "medium",
        "cooldowns": {"image": 6, "lights": 24, "spotify": 24, "music": 24, "printer": 8, "wallpaper": 24, "app_actions": 24},
        "audio_roles": {"spotify": "rare ceremonial reading mood", "musicgen": "rare public-omen sting"},
        "artifact_tools": ["web_search", "printer", "image", "silent_telegram"],
        "preferred_tools": ["web_search", "printer", "image"],
        "allowed_tools": ["voice", "telegram", "spotify", "musicgen"],
        "rare_tools": ["lights"],
        "forbidden_tools": ["generic news voice", "uncited web claims in real-world material"],
        "triggers": [
            "web_search: real-world news/reddit/Unwritten material when the section calls for current context",
            "printer: the issue/clipping is the body of the page",
            "image: masthead, marginalia, or article art when it improves the issue",
            "lights/spotify: only for ceremonial reading or major public omen",
        ],
        "default_sequence": ["text", "image", "voice", "printer"],
    },
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


def latest_packet_page_contract(max_age_hours: int = 24) -> dict[str, Any] | None:
    """Return the latest delivered/live scene page contract when it is still current.

    Mission Control should show the page the player is actually on, not a broad
    keyword guess from ambient context. Scene packets already contain the
    contract used for the reply, so prefer that recent truth for dashboards.
    """
    candidates = [
        SCENE_OUTBOX / "enchantify-scene-packet.json",
        SCENE_OUTBOX / "enchantify-session-open-packet.json",
    ]
    existing = [path for path in candidates if path.exists()]
    if not existing:
        return None
    latest = max(existing, key=lambda p: p.stat().st_mtime)
    age = datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime)
    if age > timedelta(hours=max_age_hours):
        return None
    try:
        data = json.loads(latest.read_text(encoding="utf-8"))
    except Exception:
        return None
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    contract = metadata.get("scene_contract") if isinstance(metadata.get("scene_contract"), dict) else {}
    page = contract.get("page_contract") if isinstance(contract.get("page_contract"), dict) else {}
    if not page:
        return None
    page = dict(page)
    page["selection_reason"] = f"latest scene packet: {latest.name}"
    page["packet_source"] = str(latest)
    page["packet_mtime"] = datetime.fromtimestamp(latest.stat().st_mtime).isoformat(timespec="seconds")
    return page


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
        slate_value(slate, "PLAYER"),
        slate_value(slate, "RESEARCH"),
        " ".join(story_context.get("continuity_threads", [])),
        " ".join(item.get("title", "") for item in story_context.get("narrative_obligations", [])),
    ]).lower()
    w = words(combined)
    if re.search(r"\b(gps|lat(?:itude)?|lon(?:gitude)?|coordinates?|anchor-check|outer stacks|ley line|pocket anchor|location shared|check-?in)\b", combined):
        return "anchor", "location/anchor language is active"
    if {"enchantment", "spell", "photo", "flyleaf"} & w:
        return "enchantment", "spell/photo language is active"
    if re.search(r"\b(wonder compass|compass run|notice\s*[→>-]\s*embark|embark\s*[→>-]\s*sense|souvenir sentence)\b", combined):
        return "wonder_compass", "Wonder Compass language is active"
    if {"gimble", "ledger", "budget", "money", "finance", "bank", "transaction", "transactions", "actual", "simplefin", "category", "categories", "bill", "bills", "spending", "debt", "subscription", "safe-to-spend"} & w:
        return "ledger", "finance/ledger language is active"
    if {"vellum", "fuel", "food", "protein", "fiber", "calories", "nutrition", "longevity", "healthspan", "blood", "pressure", "bp", "labs", "lab", "supplement", "supplements", "creatine", "exercise", "movement"} & w:
        return "body_marginalia", "Vellum/body-support language is active"
    if {"therapy", "therapist", "inkrest", "difficult", "reauthoring", "daydream", "shame", "anxious", "anxiety", "overwhelmed", "spiral"} & w:
        return "difficult", "therapy/difficult-page language is active"
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
    if not mode and not requested_page:
        packet_page = latest_packet_page_contract()
        if packet_page:
            return packet_page

    slate = run_script([sys.executable, str(SCRIPTS / "scene-director.py"), player, "--slate-only"])
    story_context = build_story_context(player)
    page_type, reason = choose_page_type(mode, slate, story_context, requested_page)
    definition = PAGE_TYPES[page_type]
    tool_posture = PAGE_TOOL_POSTURES.get(page_type, {})
    flavor = secondary_flavor(page_type, slate, story_context)
    if page_type == "rest":
        scene_mode = "slice"
        drama_budget = "low"
    elif page_type in {"difficult", "body_marginalia", "ledger"}:
        scene_mode = "aftermath"
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
        "tool_posture": tool_posture,
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
    tools = contract.get("tool_posture") or {}
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
    if tools:
        lines.append("TOOL_POSTURE:")
        lines.append(f"- posture: {tools.get('posture')}")
        lines.append(f"- intrusion_level: {tools.get('intrusion_level', 'low')}")
        lines.append(f"- preferred_tools: {', '.join(tools.get('preferred_tools', [])) or 'none'}")
        lines.append(f"- allowed_tools: {', '.join(tools.get('allowed_tools', [])) or 'none'}")
        lines.append(f"- rare_tools: {', '.join(tools.get('rare_tools', [])) or 'none'}")
        lines.append(f"- forbidden_tools: {', '.join(tools.get('forbidden_tools', [])) or 'none'}")
        lines.append(f"- default_sequence: {', '.join(tools.get('default_sequence', [])) or 'text, voice'}")
        if tools.get("audio_roles"):
            lines.append(f"- spotify_role: {tools['audio_roles'].get('spotify', '')}")
            lines.append(f"- musicgen_role: {tools['audio_roles'].get('musicgen', '')}")
        if tools.get("artifact_tools"):
            lines.append(f"- artifact_tools: {', '.join(tools.get('artifact_tools', []))}")
        if tools.get("cooldowns"):
            lines.append(
                "- cooldowns_hours: "
                + ", ".join(f"{tool}={hours}" for tool, hours in tools.get("cooldowns", {}).items())
            )
        lines.append("- triggers:")
        lines.extend(f"  - {item}" for item in tools.get("triggers", []))
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

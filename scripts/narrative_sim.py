#!/usr/bin/env python3
"""
narrative_sim.py — Python-first living-world simulation layer.

This module gives world-pulse a bounded autonomous simulation brain:
- explicit NPC intent profiles
- thread autonomy and consequence classes
- belief-threshold gating for major offscreen change
- talisman, anchor, research, investment, and belief-attack awareness
- slow paced offscreen narrative actions with visible traces

It is intentionally conservative in v1.
It proposes and logs autonomous actions; it does not directly rewrite canon-heavy
thread state on its own.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import json
import random
import re
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import world_context

BASE_DIR = Path(__file__).resolve().parent.parent
THREADS_MD = BASE_DIR / "lore" / "threads.md"
REGISTER_MD = BASE_DIR / "lore" / "world-register.md"
ANCHORS_DIR = BASE_DIR / "players"
STATE_FILE = BASE_DIR / "config" / "narrative-sim-state.json"
FULL_HEADER = "## Full Presence (Belief 15+)"
FADING_HEADER = "## Fading Presence (Belief 5–14)"
WHISPER_HEADER = "## Whisper Register (Belief <5)"
TALISMAN_HEADER = "## Chapter Talismans"

ACTION_CLASSES = {
    "prepare",
    "invest_belief",
    "attack_belief",
    "research",
    "reveal",
    "reposition",
    "protect",
    "sabotage",
    "recruit",
    "resolve",
}

MAJOR_BELIEF_THRESHOLD = 45
RESOLUTION_BELIEF_THRESHOLD = 50
PLAYER_GRAVITY_SLOWDOWN_PHASES = {"climax", "resolution"}
DEEP_WEIGHT_LIMIT = 20
MAX_CANDIDATE_ACTIONS = 4
MAX_LIVE_ACTIONS = 2


@dataclass
class ActorProfile:
    name: str
    actor_kind: str = "entity"
    chapter: Optional[str] = None
    static_goals: list[str] = field(default_factory=list)
    dynamic_goals: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)
    risk: str = "medium"
    taboos: list[str] = field(default_factory=list)
    thread_ids: list[str] = field(default_factory=list)
    player_gravity_bias: int = 0
    preferred_actions: list[str] = field(default_factory=list)


@dataclass
class ThreadPolicy:
    name: str
    thread_id: str
    phase: str
    pressure: str
    autonomy: str = "shared"      # background | shared | player_gravity
    consequence: str = "medium"   # minor | medium | major
    next_beat: str = ""
    npc_anchor: str = ""
    nothing_pressure: str = ""


@dataclass
class SimulationAction:
    npc: str
    thread_name: str
    thread_id: str
    action: str
    intensity: str
    reason: str
    visible_trace: str
    hidden_effect: str
    target: Optional[str] = None
    belief_delta_hint: Optional[int] = None
    priority: str = "NORMAL"
    actor_kind: str = "entity"
    chapter: Optional[str] = None
    influence_snapshot: list[str] = field(default_factory=list)


@dataclass
class AppliedConsequence:
    name: str
    kind: str
    delta: int
    before: int
    after: int
    reason: str


CHAPTER_BEHAVIORS = {
    "Emberheart": {
        "goals": ["assert agency", "push an authored choice into the world"],
        "actions": ["reveal", "reposition", "invest_belief", "attack_belief"],
    },
    "Mossbloom": {
        "goals": ["protect what is growing", "listen for the deeper pattern"],
        "actions": ["research", "protect", "invest_belief", "reposition"],
    },
    "Riddlewind": {
        "goals": ["bind loose threads together", "increase coauthored pressure"],
        "actions": ["research", "reveal", "protect", "invest_belief"],
    },
    "Tidecrest": {
        "goals": ["follow the live current", "capitalize on the moment before it closes"],
        "actions": ["research", "reveal", "reposition", "invest_belief"],
    },
    "Duskthorn": {
        "goals": ["increase friction", "force buried stakes to surface"],
        "actions": ["attack_belief", "sabotage", "recruit", "reposition", "reveal"],
    },
}

TYPE_BEHAVIORS = {
    "NPC": {
        "risk": "medium",
        "actions": ["research", "protect", "reveal", "reposition", "invest_belief"],
    },
    "fae": {
        "risk": "medium",
        "actions": ["reveal", "recruit", "reposition", "sabotage"],
    },
    "creature": {
        "risk": "medium",
        "actions": ["protect", "reveal", "reposition"],
    },
}


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            state.setdefault("pulse_index", 0)
            state.setdefault("recent_actions", [])
            state.setdefault("actor_memory", {})
            state.setdefault("talisman_intents", [])
            return state
        except Exception:
            pass
    return {"pulse_index": 0, "recent_actions": [], "actor_memory": {}, "talisman_intents": []}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def parse_world_register(register_text: str) -> tuple[dict[str, dict], dict[str, int], dict[str, int]]:
    entities: dict[str, dict] = {}
    talismans: dict[str, int] = {}
    anchors: dict[str, int] = {}
    current_section = ""
    for line in register_text.splitlines():
        if line.startswith("## "):
            current_section = line.strip()
            continue
        if not line.startswith("|") or "---" in line:
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) < 4:
            continue
        name = parts[0]
        if name.lower() in {"entity", "talisman", "name", "chapter"}:
            continue
        try:
            belief = int(re.search(r"(\d+)", parts[2]).group(1))
        except Exception:
            continue
        notes = parts[3]
        entities[name] = {
            "name": name,
            "type": parts[1],
            "belief": belief,
            "notes": notes,
            "threads": re.findall(r"\[thread:([^\]]+)\]", notes),
        }
        if current_section == "## Chapter Talismans":
            talismans[name] = belief
        if "GPS-gated" in notes or "Outer Stacks" in notes:
            anchors[name] = belief
    return entities, talismans, anchors


def parse_threads(threads_text: str) -> dict[str, ThreadPolicy]:
    registry: dict[str, ThreadPolicy] = {}
    chunks = re.split(r"^## Thread: ", threads_text, flags=re.MULTILINE)
    for chunk in chunks[1:]:
        lines = chunk.splitlines()
        if not lines:
            continue
        name = lines[0].strip()
        body = chunk
        def grab(pattern: str, default: str = "") -> str:
            m = re.search(pattern, body, re.IGNORECASE)
            return m.group(1).strip() if m else default
        thread_id = grab(r"\*\*id:\*\*\s*`([^`]+)`")
        phase_raw = grab(r"\*\*phase:\*\*\s*([^\n]+)")
        phase_tokens = phase_raw.split()
        phase = phase_tokens[0].strip("*() ").lower() if phase_tokens else "setup"
        pressure_raw = grab(r"\*\*pressure:\*\*\s*([^\n]+)")
        pressure_tokens = pressure_raw.split()
        pressure = pressure_tokens[0].strip("*() ").lower() if pressure_tokens else "low"
        npc_anchor = grab(r"\*\*npc_anchor:\*\*\s*([^\n]+)")
        next_beat = grab(r"\*\*Next beat:\*\*\s*([^\n]+)")
        nothing_pressure = grab(r"\*\*Nothing pressure:\*\*\s*([^\n]+)")
        autonomy = "shared"
        consequence = "medium"
        lowered = body.lower()
        if "always available" in lowered or "permanent" in lowered:
            autonomy = "background"
            consequence = "minor"
        if "player can" in lowered or "the player" in lowered:
            autonomy = "player_gravity"
        if "advances without player attention" in lowered:
            autonomy = "shared"
        if phase in {"climax", "resolution"} or "high" in nothing_pressure.lower():
            consequence = "major"
        registry[name] = ThreadPolicy(
            name=name,
            thread_id=thread_id,
            phase=phase,
            pressure=pressure,
            autonomy=autonomy,
            consequence=consequence,
            next_beat=next_beat,
            npc_anchor=npc_anchor,
            nothing_pressure=nothing_pressure,
        )
    return registry


def phase_weight(phase: str) -> int:
    return {
        "dormant": 0,
        "setup": 1,
        "quiet": 1,
        "rising": 2,
        "climax": 3,
        "resolution": 4,
        "permanent": 1,
    }.get((phase or "").lower(), 1)


def pressure_weight(pressure: str) -> int:
    return {
        "background": 1,
        "low": 1,
        "medium": 2,
        "medium-high": 3,
        "high": 4,
        "urgent": 5,
    }.get((pressure or "").lower(), 1)


def chapter_talisman_name(chapter: str) -> Optional[str]:
    mapping = {
        "Emberheart": "Ember Seal",
        "Mossbloom": "Moss Clasp",
        "Riddlewind": "Wind Cipher",
        "Tidecrest": "Tide Glass",
        "Duskthorn": "Dusk Thorn",
    }
    return mapping.get(chapter)


def load_anchor_pressure() -> int:
    total = 0
    for path in ANCHORS_DIR.glob("*-anchors.md"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        total += sum(int(m.group(1)) for m in re.finditer(r"\*\*Belief invested:\*\*\s*(\d+)", text))
    return total


def top_weight_entities(entities: dict[str, dict], limit: int = DEEP_WEIGHT_LIMIT) -> list[dict]:
    ranked = sorted(
        entities.values(),
        key=lambda ent: (ent.get("belief", 0), ent.get("type", ""), ent.get("name", "")),
        reverse=True,
    )
    return ranked[:limit]


def infer_entity_chapter(entity: dict) -> Optional[str]:
    direct = world_context.CHAPTER_MAP.get(entity["name"])
    if direct:
        return direct
    type_name = entity.get("type", "")
    if type_name in CHAPTER_BEHAVIORS:
        return type_name
    notes = entity.get("notes", "")
    for chapter in CHAPTER_BEHAVIORS:
        if chapter.lower() in notes.lower():
            return chapter
    return None


def derive_actor_profile(entity: dict, top_names: set[str]) -> ActorProfile:
    name = entity["name"]
    notes = entity.get("notes", "")
    chapter = infer_entity_chapter(entity)
    type_name = entity.get("type", "NPC")
    chapter_behavior = CHAPTER_BEHAVIORS.get(chapter or "", {"goals": [], "actions": []})
    type_behavior = TYPE_BEHAVIORS.get(type_name, TYPE_BEHAVIORS.get(type_name.lower(), TYPE_BEHAVIORS["NPC"]))
    actor_kind = "talisman" if type_name in CHAPTER_BEHAVIORS else type_name.lower()

    preferred = []
    for action in chapter_behavior.get("actions", []) + type_behavior.get("actions", []):
        if action in ACTION_CLASSES and action not in preferred:
            preferred.append(action)

    dynamic_goals = list(chapter_behavior.get("goals", []))
    if "investigation" in notes.lower() or "mystery" in notes.lower():
        dynamic_goals.append("research the unstable edge")
    if "antagonist" in notes.lower() or "crew" in notes.lower() or (chapter == "Duskthorn"):
        dynamic_goals.append("apply pressure where the story is weakest")
    if "portfolio" in notes.lower() or "application" in notes.lower():
        dynamic_goals.append("stabilize the work before it fails in public")
    if actor_kind == "talisman":
        dynamic_goals.append("express the chapter's philosophy through lived consequences")

    risk = type_behavior.get("risk", "medium")
    if entity.get("belief", 0) >= 40 or chapter == "Duskthorn":
        risk = "high"
    elif entity.get("belief", 0) <= 12:
        risk = "low"

    player_bias = 2 if name in top_names else 0
    if "player" in notes.lower() or "bj" in notes.lower():
        player_bias += 1

    return ActorProfile(
        name=name,
        actor_kind=actor_kind,
        chapter=chapter,
        static_goals=dynamic_goals[:2] or ["maintain narrative presence"],
        dynamic_goals=dynamic_goals[2:] or ["advance the thread they are currently feeding"],
        methods=preferred,
        risk=risk,
        taboos=["break metaphysics without cause"],
        thread_ids=entity.get("threads", []),
        player_gravity_bias=player_bias,
        preferred_actions=preferred or ["prepare", "reposition"],
    )


def derive_profiles(entities: dict[str, dict], top_band: list[dict]) -> dict[str, ActorProfile]:
    top_names = {ent["name"] for ent in top_band}
    profiles: dict[str, ActorProfile] = {}
    for ent in entities.values():
        kind = ent.get("type", "").lower()
        if kind not in {"npc", "fae", "creature"} and ent.get("type", "") not in CHAPTER_BEHAVIORS:
            continue
        profiles[ent["name"]] = derive_actor_profile(ent, top_names)
    return profiles


def recent_action_count(state: dict, npc: str, thread_id: str) -> int:
    count = 0
    for item in state.get("recent_actions", [])[-12:]:
        if item.get("npc") == npc and item.get("thread_id") == thread_id:
            count += 1
    return count


def summarize_influences(profile: ActorProfile, thread: ThreadPolicy, entities: dict[str, dict], talismans: dict[str, int], anchors: dict[str, int], anchor_pressure: int) -> list[str]:
    influences: list[tuple[int, str, str]] = []
    seen_keys: set[str] = set()

    def add_influence(key: str, weight: int, label: str) -> None:
        if weight <= 0 or key in seen_keys:
            return
        seen_keys.add(key)
        influences.append((weight, key, label))

    for name, ent in entities.items():
        if name == profile.name:
            continue
        if thread.thread_id not in ent.get("threads", []):
            continue
        belief = ent.get("belief", 0)
        label = ent.get("type", "entity").lower()
        add_influence(name, belief, f"{name} ({label} {belief})")
    for name, belief in talismans.items():
        if profile.chapter and name == chapter_talisman_name(profile.chapter):
            add_influence(name, belief, f"{name} (talisman {belief})")
        elif thread.thread_id in entities.get(name, {}).get("threads", []):
            add_influence(name, belief, f"{name} (talisman {belief})")
    for name, belief in anchors.items():
        if thread.thread_id.startswith("anchor-"):
            add_influence(name, belief, f"{name} (anchor {belief})")
    if anchor_pressure and thread.thread_id.startswith("anchor-"):
        add_influence("__ley_pressure__", anchor_pressure, f"ley pressure ({anchor_pressure})")
    influences.sort(key=lambda item: item[0], reverse=True)
    return [label for _, _, label in influences[:3]]


def pick_action(profile: ActorProfile, thread: ThreadPolicy, entity_belief: int, talismans: dict[str, int], influences: list[str]) -> tuple[str, str]:
    allowed = [a for a in profile.preferred_actions if a in ACTION_CLASSES]
    if not allowed:
        allowed = ["prepare"]

    # An actor who IS the anchor of a thread should protect and invest, not attack it
    actor_is_anchor = (
        profile.name.lower() in thread.name.lower()
        or bool(thread.npc_anchor and profile.name.lower() in thread.npc_anchor.lower())
    )
    if actor_is_anchor:
        allowed = [a for a in allowed if a not in {"attack_belief", "sabotage"}]
        if not allowed:
            allowed = ["protect", "invest_belief", "reposition"]

    talisman = chapter_talisman_name(profile.chapter) if profile.chapter else None
    talisman_belief = talismans.get(talisman, 0) if talisman else 0

    influence_text = f" under pressure from {', '.join(influences)}" if influences else ""

    if profile.actor_kind == "talisman":
        if "reveal" in allowed and thread.phase in {"rising", "climax"} and random.random() < 0.35:
            return "reveal", f"{profile.name} presses its philosophy into {thread.name}{influence_text}"
        if "protect" in allowed and thread.nothing_pressure.lower().startswith("high"):
            return "protect", f"{profile.name} resists thinning where its chapter still has claim{influence_text}"
        if "attack_belief" in allowed and thread.pressure in {"high", "medium-high"} and profile.chapter == "Duskthorn":
            return "attack_belief", f"{profile.name} sharpens conflict inside {thread.name}{influence_text}"
        if "reposition" in allowed:
            return "reposition", f"{profile.name} tilts the scene toward its chapter's logic{influence_text}"

    if talisman and entity_belief >= 12 and talisman_belief < 200 and random.random() < 0.22:
        return "invest_belief", f"{profile.name} feels their chapter's talisman pulling for investment{influence_text}"
    if "research" in allowed and thread.phase in {"setup", "rising"} and random.random() < 0.30:
        return "research", f"{profile.name} sees uncertainty they can reduce{influence_text}"
    if "attack_belief" in allowed and thread.pressure in {"high", "medium-high"}:
        return "attack_belief", f"{profile.name} has narrative reason to erode an opposing position{influence_text}"
    if "protect" in allowed and thread.nothing_pressure.lower().startswith("high"):
        return "protect", f"{profile.name} reacts against strong Nothing pressure{influence_text}"
    if "reveal" in allowed and thread.phase in {"rising", "climax"}:
        return "reveal", f"{profile.name} can surface a consequential detail{influence_text}"
    if "reposition" in allowed:
        return "reposition", f"{profile.name} nudges the board without forcing a conclusion{influence_text}"
    return allowed[0], f"{profile.name} advances their standing goal inside {thread.name}{influence_text}"


def action_intensity(thread: ThreadPolicy, entity_belief: int, state: dict, npc: str) -> str:
    recent = recent_action_count(state, npc, thread.thread_id)
    score = phase_weight(thread.phase) + pressure_weight(thread.pressure) + (1 if entity_belief >= 20 else 0) - recent
    if thread.autonomy == "background":
        score = min(score, 1)
    if score <= 1:
        return "minor"
    if score <= 3:
        return "medium"
    return "major"


def allowed_to_land(intensity: str, thread: ThreadPolicy, entity_belief: int) -> bool:
    if intensity != "major":
        return True
    if thread.autonomy == "player_gravity" and thread.phase in PLAYER_GRAVITY_SLOWDOWN_PHASES:
        return entity_belief >= RESOLUTION_BELIEF_THRESHOLD
    return entity_belief >= MAJOR_BELIEF_THRESHOLD


def build_trace(profile: ActorProfile, thread: ThreadPolicy, action: str, target: Optional[str], influences: list[str]) -> tuple[str, str]:
    target_text = f" against {target}" if target else ""
    influence_text = f" Nearby pressures: {', '.join(influences)}." if influences else ""
    if profile.actor_kind == "talisman":
        if action == "reveal":
            return (
                f"The {profile.name} has leaned on the Academy again. Its chapter's logic is suddenly easier to notice in {thread.name}.{influence_text}",
                f"{profile.name} revealed its pressure inside {thread.name}."
            )
        if action == "protect":
            return (
                f"The {profile.name} held a line somewhere offscreen. Something threaded to {thread.name} refused to thin.{influence_text}",
                f"{profile.name} protected a seam in {thread.name}."
            )
        if action == "attack_belief":
            return (
                f"The {profile.name} has made the story harsher to ignore{target_text}. Its philosophy bites before anyone names it.{influence_text}",
                f"{profile.name} attacked belief pressure{target_text}."
            )
        if action == "reposition":
            return (
                f"The shape of {thread.name} has shifted under the influence of the {profile.name}. The story now favors a different angle.{influence_text}",
                f"{profile.name} repositioned the logic of {thread.name}."
            )
    if action == "invest_belief":
        talisman = chapter_talisman_name(profile.chapter) if profile.chapter else "their chapter talisman"
        return (
            f"Something in {profile.name}'s chapter grows more insistent. The {talisman} has been fed again.{influence_text}",
            f"{profile.name} invested Belief into {talisman}."
        )
    if action == "attack_belief":
        return (
            f"A little confidence has gone missing{target_text}. The harm is social before it is visible.{influence_text}",
            f"{profile.name} pressed narrative force{target_text}."
        )
    if action == "research":
        return (
            f"{profile.name} has been quietly gathering facts. A sharper answer now exists somewhere in the Academy.{influence_text}",
            f"{profile.name} completed an offscreen research pass for {thread.name}."
        )
    if action == "protect":
        return (
            f"Something that might have thinned held together instead. {profile.name} has been guarding a seam.{influence_text}",
            f"{profile.name} reinforced a vulnerable edge in {thread.name}."
        )
    if action == "reveal":
        return (
            f"A hidden detail is closer to the surface now. The world is preparing to let it be noticed.{influence_text}",
            f"{profile.name} brought a concealed fact nearer to discovery."
        )
    if action == "reposition":
        return (
            f"Pieces have shifted offscreen. When you next arrive, the shape of things will not be exactly where you left it.{influence_text}",
            f"{profile.name} repositioned the live geometry of {thread.name}."
        )
    if action == "recruit":
        return (
            f"Someone new is leaning the wrong way now, or the right way, depending on who is telling it.{influence_text}",
            f"{profile.name} recruited soft support inside {thread.name}."
        )
    if action == "sabotage":
        return (
            f"Something useful has become more fragile offscreen.{influence_text}",
            f"{profile.name} sabotaged part of {thread.name}."
        )
    return (
        f"{profile.name} acted offscreen to advance {thread.name}.{influence_text}",
        f"{profile.name} advanced {thread.name} through {action}."
    )


def choose_target(action: str, profile: ActorProfile, thread: ThreadPolicy, entities: dict[str, dict]) -> Optional[str]:
    if action != "attack_belief":
        return None
    excluded = {profile.name, thread.name}
    attacker_chapter = profile.chapter
    candidates = []
    thread_text = f"{thread.name} {thread.next_beat} {thread.npc_anchor} {thread.nothing_pressure}".lower()
    for name, ent in entities.items():
        if name in excluded:
            continue
        if thread.thread_id in ent.get("threads", []):
            # Never attack same-chapter allies
            if attacker_chapter and infer_entity_chapter(ent) == attacker_chapter:
                continue
            if ent.get("type") in {"Emberheart", "Mossbloom", "Riddlewind", "Tidecrest", "Duskthorn"} and name.lower() not in thread_text:
                continue
            candidates.append(name)
    if not candidates:
        return None
    weights = [max(1, entities[name].get("belief", 0)) for name in candidates]
    return random.choices(candidates, weights=weights, k=1)[0]


def sample_without_replacement_weighted(items: list[tuple[int, ActorProfile, ThreadPolicy, int]], k: int) -> list[tuple[int, ActorProfile, ThreadPolicy, int]]:
    pool = list(items)
    chosen: list[tuple[int, ActorProfile, ThreadPolicy, int]] = []
    while pool and len(chosen) < k:
        weights = [max(1, score) for score, _, _, _ in pool]
        pick = random.choices(pool, weights=weights, k=1)[0]
        chosen.append(pick)
        pool.remove(pick)
    return chosen


def simulate_world_pulse(register_text: str, threads_text: str, state: Optional[dict] = None) -> list[SimulationAction]:
    state = state or load_state()
    entities, talismans, anchors = parse_world_register(register_text)
    threads = parse_threads(threads_text)
    anchor_pressure = load_anchor_pressure()
    top_band = top_weight_entities(entities)
    profiles = derive_profiles(entities, top_band)
    actions: list[SimulationAction] = []

    candidates: list[tuple[int, ActorProfile, ThreadPolicy, int]] = []
    top_names = {ent["name"] for ent in top_band}
    for actor_name, profile in profiles.items():
        ent = entities.get(actor_name)
        if not ent:
            continue
        entity_belief = ent.get("belief", 0)
        if entity_belief < 5:
            continue
        for thread in threads.values():
            thread_bound = thread.thread_id in profile.thread_ids or actor_name == thread.npc_anchor.split("(")[0].strip()
            talisman_bound = profile.actor_kind == "talisman" and profile.chapter and (
                thread.thread_id in ent.get("threads", []) or
                profile.chapter.lower() in thread.next_beat.lower() or
                profile.chapter.lower() in thread.nothing_pressure.lower()
                # Note: thread.name intentionally excluded — "Duskthorn Investigation" would
                # otherwise bind the Dusk Thorn talisman to an investigation *of* Duskthorn
            )
            if thread_bound or talisman_bound:
                score = entity_belief + 5 * phase_weight(thread.phase) + 3 * pressure_weight(thread.pressure)
                if profile.chapter and chapter_talisman_name(profile.chapter) in talismans:
                    score += talismans.get(chapter_talisman_name(profile.chapter), 0) // 25
                if anchors and thread.thread_id.startswith("anchor-"):
                    score += anchor_pressure // 10
                if thread.name in top_names or any(name in top_names for name in entities if thread.thread_id in entities[name].get("threads", [])):
                    score += 4
                if profile.actor_kind == "talisman":
                    score += 3
                if entity_belief < 15:
                    score = max(1, score - 4)
                score += profile.player_gravity_bias
                score -= recent_action_count(state, actor_name, thread.thread_id) * 6
                candidates.append((score, profile, thread, entity_belief))

    if not candidates:
        return []

    selected = sample_without_replacement_weighted(candidates, MAX_CANDIDATE_ACTIONS)
    selected.sort(key=lambda item: item[0], reverse=True)
    for _, profile, thread, entity_belief in selected:
        influences = summarize_influences(profile, thread, entities, talismans, anchors, anchor_pressure)
        action_name, reason = pick_action(profile, thread, entity_belief, talismans, influences)
        intensity = action_intensity(thread, entity_belief, state, profile.name)
        if not allowed_to_land(intensity, thread, entity_belief):
            intensity = "medium"
            action_name = "prepare"
            reason = f"major movement is not yet allowed; pressure is still gathering in {thread.name}"
        target = choose_target(action_name, profile, thread, entities)
        visible_trace, hidden_effect = build_trace(profile, thread, action_name, target, influences)
        priority = "HIGH" if intensity == "major" else "NORMAL"
        delta_hint = 0
        if action_name == "invest_belief":
            delta_hint = 1
        elif action_name == "attack_belief":
            delta_hint = -1
        actions.append(SimulationAction(
            npc=profile.name,
            thread_name=thread.name,
            thread_id=thread.thread_id,
            action=action_name,
            intensity=intensity,
            reason=reason,
            visible_trace=visible_trace,
            hidden_effect=hidden_effect,
            target=target,
            belief_delta_hint=delta_hint,
            priority=priority,
            actor_kind=profile.actor_kind,
            chapter=profile.chapter,
            influence_snapshot=influences,
        ))

    deduped: list[SimulationAction] = []
    seen_threads: set[str] = set()
    for action in actions:
        if action.thread_id in seen_threads and action.intensity != "major":
            continue
        deduped.append(action)
        seen_threads.add(action.thread_id)
        if len(deduped) >= MAX_LIVE_ACTIONS:
            break
    return deduped


def build_talisman_intents(actions: list[SimulationAction]) -> list[dict]:
    intents: list[dict] = []
    for action in actions:
        if action.actor_kind != "talisman" or not action.chapter:
            continue
        if action.action not in {"reveal", "protect", "attack_belief", "reposition"}:
            continue
        suggested_mode = {
            "reveal": "narrative",
            "protect": "world_investment",
            "attack_belief": "pact_war",
            "reposition": "reality_bleed",
        }.get(action.action, "narrative")
        intents.append({
            "talisman": action.npc,
            "chapter": action.chapter,
            "thread_name": action.thread_name,
            "thread_id": action.thread_id,
            "action": action.action,
            "intensity": action.intensity,
            "target": action.target,
            "suggested_mode": suggested_mode,
            "reason": action.reason,
        })
    return intents


def record_actions(state: dict, actions: list[SimulationAction]) -> dict:
    rows = state.setdefault("recent_actions", [])
    memory = state.setdefault("actor_memory", {})
    for action in actions:
        rows.append({
            "npc": action.npc,
            "thread_id": action.thread_id,
            "action": action.action,
            "intensity": action.intensity,
            "actor_kind": action.actor_kind,
            "chapter": action.chapter,
            "target": action.target,
            "influence_snapshot": action.influence_snapshot,
        })
        actor_state = memory.setdefault(action.npc, {
            "actor_kind": action.actor_kind,
            "chapter": action.chapter,
            "threads": {},
            "action_counts": {},
            "last_target": None,
            "last_reason": "",
            "last_visible_trace": "",
            "last_hidden_effect": "",
            "last_intensity": None,
            "last_seen_pulse": 0,
        })
        actor_state["actor_kind"] = action.actor_kind
        actor_state["chapter"] = action.chapter
        actor_state["last_target"] = action.target
        actor_state["last_reason"] = action.reason
        actor_state["last_visible_trace"] = action.visible_trace
        actor_state["last_hidden_effect"] = action.hidden_effect
        actor_state["last_intensity"] = action.intensity
        actor_state["last_seen_pulse"] = state.get("pulse_index", 0) + 1
        actor_state["action_counts"][action.action] = actor_state["action_counts"].get(action.action, 0) + 1
        thread_state = actor_state["threads"].setdefault(action.thread_id, {
            "thread_name": action.thread_name,
            "count": 0,
            "last_action": None,
            "last_target": None,
            "last_intensity": None,
        })
        thread_state["thread_name"] = action.thread_name
        thread_state["count"] += 1
        thread_state["last_action"] = action.action
        thread_state["last_target"] = action.target
        thread_state["last_intensity"] = action.intensity
    state["recent_actions"] = rows[-40:]
    state["talisman_intents"] = build_talisman_intents(actions)[-12:]
    state["pulse_index"] = state.get("pulse_index", 0) + 1
    return state


def bounded_delta(action: SimulationAction) -> list[tuple[str, str, int, str]]:
    deltas: list[tuple[str, str, int, str]] = []
    if action.action == "invest_belief":
        profile_chapter = infer_entity_chapter({"name": action.npc, "type": "", "notes": ""})
        talisman = chapter_talisman_name(profile_chapter) if profile_chapter else None
        if talisman:
            delta = 2 if action.intensity == "major" else 1
            deltas.append((talisman, "talisman", delta, f"{action.npc} invested offscreen via {action.thread_name}"))
        thread_delta = 1 if action.intensity in {"medium", "major"} else 0
        if thread_delta:
            deltas.append((action.thread_name, "thread", thread_delta, f"{action.npc} fed thread momentum"))
    elif action.action == "attack_belief" and action.target:
        delta = -2 if action.intensity == "major" else -1
        deltas.append((action.target, "entity", delta, f"{action.npc} applied narrative pressure through {action.thread_name}"))
        rebound = 1 if action.intensity == "major" else 0
        if rebound:
            deltas.append((action.thread_name, "thread", rebound, f"{action.thread_name} gained pressure from conflict"))
    elif action.action in {"protect", "research", "reveal", "reposition", "recruit", "sabotage"}:
        delta = 1 if action.intensity == "major" else 0
        if delta:
            deltas.append((action.thread_name, "thread", delta, f"{action.action} intensified {action.thread_name}"))
    return deltas


def apply_delta_to_register(register_text: str, name: str, delta: int) -> tuple[str, Optional[AppliedConsequence]]:
    if not delta:
        return register_text, None

    table_pattern = re.compile(
        r"^(\|\s*" + re.escape(name) + r"\s*\|\s*[^|]+\|\s*)(\d+)(\s*\|.*)$",
        re.MULTILINE,
    )
    match = table_pattern.search(register_text)
    if match:
        line = match.group(0)
        before = int(match.group(2))
        after = max(0, before + delta)
        kind = "thread" if "## Active Threads" in register_text[:match.start()] else "entity"
        if "## Chapter Talismans" in register_text[:match.start()] and "## Active Threads" not in register_text[:match.start()].split("## Chapter Talismans")[-1]:
            kind = "talisman"
        if kind in {"thread", "talisman"}:
            updated = table_pattern.sub(lambda m: m.group(1) + str(after) + m.group(3), register_text, count=1)
        else:
            parts = [p.strip() for p in line.strip().strip("|").split("|")]
            entity_type = parts[1]
            notes = parts[3]
            without = register_text[:match.start()] + register_text[match.end():]
            row = f"| {name} | {entity_type} | {after} | {notes} |"
            if after >= 15:
                updated = insert_into_section(without, FULL_HEADER, row)
            elif after >= 5:
                updated = insert_into_section(without, FADING_HEADER, row)
            else:
                updated = insert_into_section(without, WHISPER_HEADER, f"- {name} ({entity_type}, Belief {after}) — {notes}")
        return updated, AppliedConsequence(name=name, kind=kind, delta=after - before, before=before, after=after, reason="")

    list_pattern = re.compile(
        r"^(-\s+" + re.escape(name) + r"\s*\([^\)]*Belief\s*)(\d+)(\)\s*(?:—\s*.*)?)$",
        re.MULTILINE,
    )
    match = list_pattern.search(register_text)
    if match:
        before = int(match.group(2))
        after = max(0, before + delta)
        line = match.group(0)
        mtype = re.search(r"\(([^,]+),\s*Belief\s*\d+\)", line)
        notes_m = re.search(r"\)\s*—\s*(.*)$", line)
        entity_type = mtype.group(1).strip() if mtype else "NPC"
        notes = notes_m.group(1).strip() if notes_m else ""
        without = register_text[:match.start()] + register_text[match.end():]
        if after >= 15:
            updated = insert_into_section(without, FULL_HEADER, f"| {name} | {entity_type} | {after} | {notes} |")
        elif after >= 5:
            updated = insert_into_section(without, FADING_HEADER, f"| {name} | {entity_type} | {after} | {notes} |")
        else:
            updated = list_pattern.sub(lambda m: m.group(1) + str(after) + m.group(3), register_text, count=1)
        return updated, AppliedConsequence(name=name, kind="entity", delta=after - before, before=before, after=after, reason="")

    return register_text, None


def insert_into_section(text: str, header: str, new_line: str) -> str:
    header_match = re.search(r"^" + re.escape(header) + r"\s*$", text, re.MULTILINE)
    if not header_match:
        return text.rstrip() + f"\n\n{header}\n{new_line}\n"

    section_start = header_match.end()
    next_header = re.search(r"^\s*##\s", text[section_start:], re.MULTILINE)
    insert_pos = section_start + (next_header.start() if next_header else len(text[section_start:]))

    before = text[:insert_pos].rstrip()
    after = text[insert_pos:].lstrip()
    return before + "\n" + new_line + "\n\n" + after


def apply_simulation_consequences(register_text: str, actions: list[SimulationAction]) -> tuple[str, list[AppliedConsequence]]:
    updated = register_text
    applied: list[AppliedConsequence] = []
    seen: dict[tuple[str, str], int] = {}

    for action in actions:
        for name, kind, delta, reason in bounded_delta(action):
            key = (name, kind)
            seen[key] = seen.get(key, 0) + delta
            if abs(seen[key]) > 2:
                overflow = abs(seen[key]) - 2
                delta = delta - overflow if delta > 0 else delta + overflow
                seen[key] = 2 if seen[key] > 0 else -2
            if not delta:
                continue
            updated, result = apply_delta_to_register(updated, name, delta)
            if result:
                result.kind = kind
                result.reason = reason
                applied.append(result)

    return updated, applied

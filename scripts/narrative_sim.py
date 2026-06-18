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
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import world_context
from belief_caps import clamp_belief
try:
    import relationships
    _HAS_RELATIONSHIPS = True
except Exception:
    relationships = None  # type: ignore
    _HAS_RELATIONSHIPS = False

BASE_DIR = Path(__file__).resolve().parent.parent
THREADS_MD = BASE_DIR / "lore" / "threads.md"
REGISTER_MD = BASE_DIR / "lore" / "world-register.md"
CHARACTERS_MD = BASE_DIR / "lore" / "characters.md"
ANCHORS_DIR = BASE_DIR / "players"
STATE_FILE = BASE_DIR / "config" / "narrative-sim-state.json"
SIM_TRACE_LOG = BASE_DIR / "logs" / "narrative-sim-llm.log"
FULL_HEADER = "## Full Presence (Belief 15+)"
FADING_HEADER = "## Fading Presence (Belief 5–14)"
WHISPER_HEADER = "## Whisper Register (Belief <5)"
TALISMAN_HEADER = "## Chapter Talismans"

ACTION_CLASSES = {
    # Keep the mechanical layer simple. Richness belongs in the narrative event,
    # not in a leaked combat-log verb.
    "take_action",
    "invest_belief",
    "attack_belief",
}

MAJOR_BELIEF_THRESHOLD = 45
RESOLUTION_BELIEF_THRESHOLD = 50
PLAYER_GRAVITY_SLOWDOWN_PHASES = {"climax", "resolution"}
DEEP_WEIGHT_LIMIT = 20
MAX_CANDIDATE_ACTIONS = 4
MAX_LIVE_ACTIONS = 2
RECENT_TRACE_WINDOW = 28
SIM_TRACE_MODEL_DEFAULT = "openclaw/gpt55"
SIM_TRACE_TIMEOUT_DEFAULT = 240

DAILY_LIFE_ACTION_BANK = {
    "reposition": [
        (
            "Great Hall west table",
            "moved the noisy first-years beside the window and left the quiet table intact",
            "lunch split into two calmer currents instead of one crowded knot",
        ),
        (
            "north corridor stair",
            "redirected the between-class traffic through the side landing with a chalk arrow and a look",
            "three students who usually rush arrived late but laughing",
        ),
        (
            "Library return desk",
            "changed the order of the return crates so ordinary books were handled before urgent ones",
            "the queue stopped feeling like a tribunal and started feeling like a queue",
        ),
        (
            "courtyard path",
            "held the gate open long enough for the wet-footed students to cross without slipping",
            "the afternoon route bent around care instead of impatience",
        ),
    ],
    "prepare": [
        (
            "classroom threshold",
            "set out spare pencils, dry socks, and two cups of tea before anyone asked",
            "the next class began with fewer tiny emergencies",
        ),
        (
            "Great Hall notice rail",
            "pinned tomorrow's practical reminders under the menu instead of beside the warnings",
            "students read the mundane instructions before the alarming ones",
        ),
        (
            "dorm stairwell",
            "left a folded timetable where late students actually look for it",
            "the evening's confusion lost one of its easiest hiding places",
        ),
    ],
    "research": [
        (
            "attendance ledger",
            "checked which students keep missing meals after difficult classes",
            "a short list now exists for faculty to watch without making a spectacle",
        ),
        (
            "cloakroom hooks",
            "counted whose coats were still damp after lunch",
            "the Academy knows which corridors are leaking ordinary weather again",
        ),
        (
            "Library side table",
            "asked three students what actually helped them settle after the last bell",
            "the answer was less advice and more chairs near warm light",
        ),
    ],
    "reveal": [
        (
            "Great Hall serving line",
            "noticed the soup spoons all pointing toward the same empty chair",
            "a small absence became visible without becoming a crisis",
        ),
        (
            "east corridor tiles",
            "caught the floor repeating one footprint too many",
            "students began stepping around the wrong tile on instinct",
        ),
        (
            "Library lamps",
            "found one lamp brightening whenever someone told the truth softly",
            "honesty acquired a small practical light source",
        ),
    ],
    "protect": [
        (
            "Great Hall bread tray",
            "kept the last warm rolls back until the anxious students arrived",
            "nobody had to ask for comfort in public",
        ),
        (
            "common-room hearth",
            "mended the fire's tendency to gutter whenever conversation went quiet",
            "silence stayed companionable instead of hollow",
        ),
        (
            "stairwell landing",
            "stood in the draft until the younger students had passed",
            "the cold lost its chance to make the climb feel abandoned",
        ),
    ],
    "invest_belief": [
        (
            "chapter table",
            "turned a routine check-in into a small chapter custom",
            "one ordinary habit began carrying talisman weather",
        ),
        (
            "practice corridor",
            "asked students to repeat the simplest exercise until it felt chosen",
            "routine gained a little more weight than routine usually gets",
        ),
        (
            "tea urn",
            "made everyone name one thing that had gone right before taking a cup",
            "gratitude became procedural for exactly seven minutes",
        ),
    ],
    "recruit": [
        (
            "Great Hall cleanup line",
            "pulled two reluctant students into carrying trays together",
            "they left arguing about dishwater and smiling despite themselves",
        ),
        (
            "courtyard bench",
            "asked a lonely first-year to help sort lost gloves",
            "the bench stopped being a place to disappear",
        ),
    ],
    "sabotage": [
        (
            "notice board",
            "moved one practical notice behind a more dramatic warning",
            "the useful instruction became harder to find than it deserved",
        ),
        (
            "Great Hall queue",
            "let a small misunderstanding about seats remain unresolved",
            "lunch acquired one unnecessary pocket of awkwardness",
        ),
    ],
}

THREAD_ACTION_BANK = {
    "prepare": [
        ("copied the relevant names onto a separate index card", "the next scene now has a named list instead of a vague pressure"),
        ("reserved a side room and moved the necessary chairs into a closed circle", "the confrontation has a place to land if the player follows it"),
        ("set aside the one document that does not match the rest of the file", "the anomaly is now recoverable instead of buried"),
    ],
    "research": [
        ("checked the attendance ledger against the door-memory records", "one contradiction now has a timestamp"),
        ("questioned the portrait nearest the last known threshold", "a witness has given a usable but partial answer"),
        ("compared three marginal notes written in different hands", "the thread now has a concrete textual lead"),
    ],
    "reveal": [
        ("left the marked page open where the right person would see it", "a hidden fact is now physically visible"),
        ("allowed the wrong reflection to remain in the glass for one extra breath", "the next observer can notice what does not belong"),
        ("moved the sealed object from storage to a public shelf", "the secret has become an object in the room"),
    ],
    "protect": [
        ("locked the vulnerable record in a drawer with two names on the key-tag", "the Nothing cannot erase that detail casually"),
        ("kept the frightened witness away from the crowded corridor", "one useful voice remains intact"),
        ("copied the fragile memory into a second notebook before dusk", "the thread now has a backup if pressure rises"),
    ],
    "reposition": [
        ("shifted the meeting point from the obvious doorway to the service stair", "the next approach will come from a different angle"),
        ("moved the relevant object into someone else's line of sight", "the clue is no longer waiting in isolation"),
        ("changed who reaches the room first", "the social order of the next beat has altered"),
    ],
    "attack_belief": [
        ("spread one plausible doubt through the corridor before anyone could answer it", "the target's certainty has lost public footing"),
        ("removed the small proof people had been relying on", "confidence now has to survive without its easiest support"),
        ("turned a helpful rumor into an accusation", "the thread gained pressure by making trust more expensive"),
    ],
    "recruit": [
        ("asked one undecided student to carry a message with no explanation", "soft support has moved into the thread"),
        ("gave a minor witness a reason to stay nearby", "the next scene has another pair of eyes"),
        ("made a practical favor feel like allegiance", "the social map has acquired a new leaning"),
    ],
    "sabotage": [
        ("misfiled the one record that would have made the answer simple", "the next investigation has to work around an absence"),
        ("changed the meeting time on one copy of the notice", "the room will not gather cleanly"),
        ("left a useful door unlocked for the wrong person", "access has become a liability"),
    ],
}

CHAPTER_ACTION_TACTICS = {
    "Tidecrest": {
        "attack_belief": [
            (
                "printed quick Tidecrest flyers and pasted them over the target's notices before second bell",
                "the school saw motion, invitation, and living current where the target had been trying to look inevitable",
            ),
            (
                "turned a hallway rumor into a public dare: anyone who believed the target was fixed had to prove it by sunset",
                "certainty became something students could laugh at, which made it weaker",
            ),
            (
                "staged an unscheduled courtyard demonstration that made the target's philosophy look stiff and late",
                "attention flowed around the target instead of toward it",
            ),
        ],
        "protect": [
            (
                "kept the vulnerable detail moving from hand to hand instead of letting it sit in one place",
                "the Nothing had no single still point to erase",
            ),
            (
                "asked three students to retell the same memory in their own words",
                "the memory survived by becoming plural",
            ),
        ],
        "recruit": [
            (
                "invited an undecided student into a practical errand that felt too alive to refuse",
                "soft support entered the thread through momentum rather than persuasion",
            ),
        ],
        "invest_belief": [
            (
                "turned a passing impulse into a shared Tidecrest custom before anyone could overthink it",
                "Belief moved because the moment stayed alive",
            ),
        ],
    },
    "Riddlewind": {
        "attack_belief": [
            (
                "left a set of questions on the target's public claim, each one answered by a different witness",
                "the target lost force because the school could see its gaps",
            ),
            (
                "built a small puzzle trail that made the target contradict itself by the final clue",
                "students began treating the target as solvable instead of powerful",
            ),
        ],
        "research": [
            (
                "cross-checked the same fact through a witness, a marginal note, and a door that remembers footsteps",
                "the thread gained a three-point anchor instead of a hunch",
            ),
        ],
        "reveal": [
            (
                "arranged the evidence so the answer appeared only when three students compared notes",
                "the clue became public without becoming blunt",
            ),
        ],
        "invest_belief": [
            (
                "made a cooperative solution feel elegant enough that students repeated it",
                "Belief gathered around the pattern",
            ),
        ],
    },
    "Mossbloom": {
        "attack_belief": [
            (
                "preserved the quiet evidence the target depended on everyone overlooking",
                "the target weakened because patience made its hidden cost visible",
            ),
            (
                "placed a calm witness in the room and let their refusal to panic become contagious",
                "the target's pressure could not feed on urgency",
            ),
        ],
        "protect": [
            (
                "wrapped the fragile record in a slow preservation charm and kept it out of argument",
                "the detail remained whole because no one was allowed to rush it",
            ),
        ],
        "research": [
            (
                "sat with the oldest version of the story until the part that had been skipped became audible",
                "the thread gained depth rather than noise",
            ),
        ],
        "invest_belief": [
            (
                "turned one act of patience into a visible ritual others could copy",
                "Belief rooted itself in repetition",
            ),
        ],
    },
    "Emberheart": {
        "attack_belief": [
            (
                "challenged the target's claim in public and made the room choose a side",
                "the target lost passive authority because neutrality stopped being comfortable",
            ),
            (
                "wrote a counter-declaration in red chalk where everyone had to step over it",
                "the target's certainty met authored opposition",
            ),
        ],
        "reveal": [
            (
                "dragged the hidden fact into the open before caution could bury it again",
                "the thread gained heat and direction",
            ),
        ],
        "prepare": [
            (
                "claimed the room, named the stakes, and left no chair facing away from the door",
                "the next beat has a place built for decision",
            ),
        ],
        "invest_belief": [
            (
                "made a choice loudly enough that other students could rally around it",
                "Belief rose through declared agency",
            ),
        ],
    },
    "Duskthorn": {
        "attack_belief": [
            (
                "placed one elegant doubt where the target's supporters would repeat it for them",
                "the target weakened by carrying the doubt in its own mouth",
            ),
            (
                "turned the target's strongest proof into a complication nobody wanted to discuss",
                "the story grew teeth around the target's confidence",
            ),
        ],
        "sabotage": [
            (
                "made the helpful route look easier than it was and watched people choose it",
                "the thread acquired friction disguised as convenience",
            ),
        ],
        "recruit": [
            (
                "offered one student a role that felt like recognition and behaved like leverage",
                "support arrived with a hook in it",
            ),
        ],
        "invest_belief": [
            (
                "made a complication feel necessary instead of unfortunate",
                "Belief gathered around friction",
            ),
        ],
    },
}


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
    personality: str = ""
    quirks: str = ""
    faults: str = ""
    goals_text: str = ""
    beliefs_text: str = ""
    unwritten_interest: str = ""
    lore_summary: str = ""


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
    belief_cost: int = 1


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
        "actions": ["take_action", "invest_belief", "attack_belief"],
    },
    "Mossbloom": {
        "goals": ["protect what is growing", "listen for the deeper pattern"],
        "actions": ["take_action", "invest_belief"],
    },
    "Riddlewind": {
        "goals": ["bind loose threads together", "increase coauthored pressure"],
        "actions": ["take_action", "invest_belief"],
    },
    "Tidecrest": {
        "goals": ["follow the live current", "capitalize on the moment before it closes"],
        "actions": ["take_action", "invest_belief"],
    },
    "Duskthorn": {
        "goals": ["increase friction", "force buried stakes to surface"],
        "actions": ["take_action", "attack_belief", "invest_belief"],
    },
}

TYPE_BEHAVIORS = {
    "NPC": {
        "risk": "medium",
        "actions": ["take_action", "invest_belief"],
    },
    "fae": {
        "risk": "medium",
        "actions": ["take_action", "attack_belief"],
    },
    "creature": {
        "risk": "medium",
        "actions": ["take_action"],
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


def _character_section_bounds(text: str, name: str) -> Optional[tuple[int, int]]:
    patterns = [
        rf"^###\s+{re.escape(name)}(?:\s+[—-].*)?$",
        rf"^\*\*{re.escape(name)}\*\*",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.MULTILINE | re.IGNORECASE)
        if not m:
            continue
        next_m = re.search(r"^(?:###\s+|\*\*[^*\n]+\*\*\s+[—-])", text[m.end():], re.MULTILINE)
        end = m.end() + next_m.start() if next_m else len(text)
        return m.start(), end
    return None


def _clean_lore_text(value: str, limit: int = 260) -> str:
    value = re.sub(r"`([^`]+)`", r"\1", value or "")
    value = re.sub(r"\*\*([^*]+)\*\*", r"\1", value)
    value = value.replace("*", "")
    value = re.sub(r"\s+", " ", value).strip()
    return value[:limit].rstrip() + ("…" if len(value) > limit else "")


def parse_character_lore() -> dict[str, dict[str, str]]:
    text = CHARACTERS_MD.read_text(encoding="utf-8", errors="ignore") if CHARACTERS_MD.exists() else ""
    lore: dict[str, dict[str, str]] = {}
    if not text:
        return lore

    # Structured staff/support entries.
    for m in re.finditer(r"^###\s+(.+?)(?:\s+[—-].*)?$", text, re.MULTILINE):
        name = m.group(1).strip()
        next_m = re.search(r"^###\s+", text[m.end():], re.MULTILINE)
        section = text[m.end():m.end() + next_m.start()] if next_m else text[m.end():]
        fields: dict[str, str] = {}
        for fm in re.finditer(r"^\*\*([^*:]+):\*\*\s*(.+)$", section, re.MULTILINE):
            key = fm.group(1).strip().lower()
            fields[key] = _clean_lore_text(fm.group(2), 420)
        if fields:
            lore[name] = fields

    # Compact student entries: **Name** — personality sentence. **Unwritten Interest:** ...
    compact_re = re.compile(r"^\*\*([^*\n]+)\*\*(?:(?:\s*\([^)]*\))|(?:\s*\*[^*]+\*))*\s+[—-]\s+(.+?)(?=^\*\*|\n-----|\n## |\Z)", re.MULTILINE | re.DOTALL)
    for m in compact_re.finditer(text):
        name = m.group(1).strip()
        body = _clean_lore_text(m.group(2), 900)
        fields = lore.setdefault(name, {})
        interest_m = re.search(r"Unwritten Interest:\s*(.+?)(?:Voice:|$)", body, re.IGNORECASE)
        voice_m = re.search(r"Voice:\s*(.+)$", body, re.IGNORECASE)
        personality = re.sub(r"\s*(?:Unwritten Interest|Voice):.*$", "", body, flags=re.IGNORECASE).strip()
        if personality:
            fields.setdefault("personality", personality)
        if interest_m:
            fields.setdefault("unwritten interest", interest_m.group(1).strip().rstrip("."))
        if voice_m:
            fields.setdefault("voice", voice_m.group(1).strip())

    return lore


_CHARACTER_LORE_CACHE: Optional[dict[str, dict[str, str]]] = None


def character_lore_for(name: str) -> dict[str, str]:
    global _CHARACTER_LORE_CACHE
    if _CHARACTER_LORE_CACHE is None:
        _CHARACTER_LORE_CACHE = parse_character_lore()
    direct = _CHARACTER_LORE_CACHE.get(name)
    if direct:
        return direct
    def canon(value: str) -> str:
        value = value.lower()
        value = re.sub(r"\([^)]*\)", "", value)
        value = value.replace("prof. ", "professor ")
        value = re.sub(r"^(headmistress|headmaster|professor|dr)\s+", "", value)
        value = re.sub(r"[^a-z0-9]+", " ", value)
        return re.sub(r"\s+", " ", value).strip()
    normalized = canon(name)
    for key, value in _CHARACTER_LORE_CACHE.items():
        key_norm = canon(key)
        if key_norm == normalized:
            return value
        normalized_parts = normalized.split()
        key_parts = key_norm.split()
        if normalized_parts and key_parts and key_parts[-1] == normalized_parts[-1] and normalized_parts[-1] not in {"the", "of"}:
            if set(normalized_parts).issubset(set(key_parts)) or set(key_parts).issubset(set(normalized_parts)):
                return value
        if normalized_parts and key_norm.endswith(" " + normalized_parts[-1]) and normalized_parts[-1] not in {"the", "of"}:
            return value
    return {}


def character_lore_summary(fields: dict[str, str]) -> str:
    parts = []
    for label in (
        "role",
        "unwritten interest",
        "therapeutic spine",
        "functions",
        "goals",
        "beliefs",
        "personality",
        "quirks",
        "faults",
        "voice",
    ):
        value = fields.get(label, "")
        if value:
            parts.append(f"{label}: {_clean_lore_text(value, 160)}")
    return _clean_lore_text("; ".join(parts), 700)


def lore_action_bias(fields: dict[str, str]) -> list[str]:
    text = " ".join(fields.get(k, "") for k in ("role", "personality", "functions", "goals", "beliefs", "unwritten interest")).lower()
    actions: list[str] = []
    for word, action in [
        ("research", "take_action"),
        ("investigation", "take_action"),
        ("therap", "take_action"),
        ("grounding", "take_action"),
        ("longevity", "take_action"),
        ("diet", "take_action"),
        ("protect", "take_action"),
        ("guardian", "take_action"),
        ("reveal", "take_action"),
        ("curious", "take_action"),
        ("riddle", "take_action"),
        ("spontaneous", "take_action"),
        ("adventurous", "take_action"),
        ("competitive", "attack_belief"),
        ("antagonist", "attack_belief"),
        ("cunning", "attack_belief"),
        ("secret", "take_action"),
    ]:
        if word in text and action not in actions:
            actions.append(action)
    return actions


def derive_actor_profile(entity: dict, top_names: set[str]) -> ActorProfile:
    name = entity["name"]
    notes = entity.get("notes", "")
    lore_fields = character_lore_for(name)
    chapter = infer_entity_chapter(entity)
    type_name = entity.get("type", "NPC")
    chapter_behavior = CHAPTER_BEHAVIORS.get(chapter or "", {"goals": [], "actions": []})
    type_behavior = TYPE_BEHAVIORS.get(type_name, TYPE_BEHAVIORS.get(type_name.lower(), TYPE_BEHAVIORS["NPC"]))
    actor_kind = "talisman" if type_name in CHAPTER_BEHAVIORS else type_name.lower()

    preferred = []
    for action in lore_action_bias(lore_fields) + chapter_behavior.get("actions", []) + type_behavior.get("actions", []):
        if action in ACTION_CLASSES and action not in preferred:
            preferred.append(action)

    dynamic_goals = list(chapter_behavior.get("goals", []))
    if lore_fields.get("goals"):
        dynamic_goals.insert(0, lore_fields["goals"])
    if lore_fields.get("unwritten interest"):
        dynamic_goals.append(f"pursue Unwritten Interest: {lore_fields['unwritten interest']}")
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

    lore_summary = character_lore_summary(lore_fields)

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
        preferred_actions=preferred or ["take_action"],
        personality=lore_fields.get("personality", ""),
        quirks=lore_fields.get("quirks", ""),
        faults=lore_fields.get("faults", ""),
        goals_text=lore_fields.get("goals", ""),
        beliefs_text=lore_fields.get("beliefs", ""),
        unwritten_interest=lore_fields.get("unwritten interest", ""),
        lore_summary=lore_summary,
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


def recent_actor_count(state: dict, npc: str, window: int = 24) -> int:
    count = 0
    for item in state.get("recent_actions", [])[-window:]:
        if item.get("npc") == npc:
            count += 1
    return count


def normalize_trace_signature(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", "", text)
    words = re.findall(r"[a-z']+", text)
    stop = {
        "the", "a", "an", "and", "or", "to", "of", "in", "on", "at", "for", "with",
        "by", "from", "into", "one", "two", "three", "as", "it", "its", "their",
        "this", "that", "now", "has", "had", "have", "was", "were", "is", "are",
    }
    return " ".join(word for word in words if word not in stop)


def recent_trace_signatures(state: dict, *, actor: str = "", thread_id: str = "", action: str = "") -> set[str]:
    signatures: set[str] = set()
    for item in state.get("recent_actions", [])[-RECENT_TRACE_WINDOW:]:
        if actor and item.get("npc") != actor:
            continue
        if thread_id and item.get("thread_id") != thread_id:
            continue
        if action and item.get("action") != action:
            continue
        for key in ("trace_signature", "deed", "result", "hidden_effect", "visible_trace"):
            value = item.get(key)
            if value:
                signatures.add(normalize_trace_signature(str(value)))
    return {sig for sig in signatures if sig}


def trace_is_recent(deed: str, result: str, avoid_signatures: set[str]) -> bool:
    deed_sig = normalize_trace_signature(deed)
    result_sig = normalize_trace_signature(result)
    combined = normalize_trace_signature(f"{deed} {result}")
    return any(sig and sig in avoid_signatures for sig in (deed_sig, result_sig, combined))


BOILERPLATE_TRACE_PATTERNS = [
    "what it costs when nobody helps",
    "students stopped treating",
    "the room learned",
    "changed one public errand",
    "the hallway carried the rumor",
    "specific thing waiting",
    "thread changed in a visible way",
    "concrete trace",
    "made the thread more present",
    "left a living-world trace",
    "students changed behavior before anyone made a speech",
    "one future choice will have to account",
    "by the next bell, one future choice",
]


def trace_has_boilerplate(text: str) -> bool:
    lower = (text or "").lower()
    return any(pattern in lower for pattern in BOILERPLATE_TRACE_PATTERNS)


def trace_is_usable(text: str, recent_signatures: set[str]) -> bool:
    text = (text or "").strip()
    if not text or len(text) < 80 or len(text) > 900:
        return False
    if trace_has_boilerplate(text):
        return False
    if re.search(r"\b(something|someone|somebody|stuff|things|matter|issue|gesture|evidence)\b", text.lower()) and len(re.findall(r"\b[A-Z][A-Za-z'.-]+", text)) < 3:
        return False
    sig = normalize_trace_signature(text)
    if sig and sig in recent_signatures:
        return False
    return True


def _pick(items: list[str], key: str) -> str:
    if not items:
        return ""
    return items[sum(ord(ch) for ch in key) % len(items)]


def _keywords(text: str, *, limit: int = 5) -> list[str]:
    stop = {
        "the", "and", "with", "that", "this", "from", "into", "their", "they",
        "them", "what", "when", "where", "while", "because", "through", "about",
        "interest", "personality", "goals", "beliefs", "voice", "unwritten",
    }
    found = []
    for word in re.findall(r"[A-Za-z][A-Za-z'-]{3,}", text.lower()):
        word = word.strip("-'")
        if word not in stop and word not in found:
            found.append(word)
    return found[:limit]


def _actor_motif(profile: ActorProfile) -> str:
    lens = character_lens(profile, 360) or profile.lore_summary or profile.name
    keys = _keywords(lens, limit=4)
    if keys:
        return " / ".join(keys[:3])
    name_bits = [w.lower() for w in re.findall(r"[A-Za-z]+", profile.name) if len(w) > 3]
    return " / ".join(name_bits[:2]) if name_bits else "specific presence"


def _chapter_medium(profile: ActorProfile, key: str) -> str:
    media = {
        "Tidecrest": ["wet ink", "borrowed motion", "a corridor current", "a shared errand"],
        "Riddlewind": ["a three-part question", "a chalk puzzle", "a misnumbered index", "a door-riddle"],
        "Mossbloom": ["a patient label", "warm lamplight", "a preserved scrap", "a quiet witness"],
        "Emberheart": ["red chalk", "a declared choice", "a rearranged chair", "a signed notice"],
        "Duskthorn": ["a precise doubt", "a locked margin", "a redirected whisper", "a shadowed receipt"],
    }
    return _pick(media.get(profile.chapter or "", ["a margin note", "a small object", "a changed route", "a witnessed detail"]), key)


def _action_verb(action: str, profile: ActorProfile, key: str) -> str:
    verbs = {
        "take_action": ["left", "placed", "copied", "marked", "arranged", "noticed"],
        "invest_belief": ["posted", "shared", "copied", "named", "left"],
        "attack_belief": ["crossed out", "misfiled", "spoiled", "punctured", "contested"],
    }
    return _pick(verbs.get(action, ["changed"]), f"{key}|{profile.name}|verb")


def _daily_place(profile: ActorProfile, action: str, key: str) -> str:
    motif = _actor_motif(profile)
    if "food" in motif or "protein" in motif or "longevity" in motif:
        places = ["refectory side counter", "tea urn ledger", "breakfast return tray", "quiet end of the dining table"]
    elif "stationery" in motif or "journal" in motif or "ink" in motif:
        places = ["library stationery drawer", "notice-board margin", "study carrel row", "ink-stained return desk"]
    elif "weather" in motif or "sunrise" in motif or "solar" in motif:
        places = ["east window landing", "courtyard weather line", "glass-roof corridor", "sunlit stairwell"]
    elif "architecture" in motif or "foundation" in motif or "preservation" in motif:
        places = ["old stone threshold", "foundation stair", "archway beside the Great Hall", "library buttress alcove"]
    elif "therapy" in motif or "consciousness" in motif or "brain" in motif:
        places = ["Reauthoring Rooms threshold", "quiet bench outside the infirmary", "mirrorless counseling alcove", "margin table near warm light"]
    else:
        places = ["Great Hall edge table", "north corridor landing", "Library return desk", "courtyard bench", "common-room hearth"]
    return _pick(places, f"{key}|{action}|place")


def _daily_bespoke_material(profile: ActorProfile, action: str, influences: list[str], state: Optional[dict]) -> tuple[str, str, str]:
    pulse = (state or {}).get("pulse_index", 0)
    base = f"{profile.name}|{profile.chapter or ''}|{action}|{pulse}"
    motif = _actor_motif(profile)
    medium = _chapter_medium(profile, base)
    place = _daily_place(profile, action, base)
    signature = motif.split(" / ")[0]
    last = profile.name.split()[-1]
    scene_pool = [
        (
            f"pinned {medium} to the notice rail and wrote {last}: {signature} in the corner",
            "three students stopped to read it because it looked less like an announcement than a dare",
        ),
        (
            f"set one annotated index card on the warmest table, weighted with a teaspoon from breakfast",
            "the next student who sat there copied the note into their own margin before leaving",
        ),
        (
            f"changed one timetable square from warning-red to ordinary pencil and added a real room number",
            "the usual little panic at that hour lost its easiest excuse",
        ),
        (
            f"moved a chair, a lamp, and {medium} into the path where students usually hurry past",
            "two people slowed down enough to notice each other",
        ),
        (
            f"left a labeled envelope under the hearth brick marked for whoever keeps pretending not to need help",
            "someone took it, and the brick was put back straighter than before",
        ),
    ]
    deed, result = _stable_pick_pair(scene_pool, base, recent_trace_signatures(state or {}, actor=profile.name, thread_id="academy-daily", action=action))
    return place, deed, result


def _thread_object(thread: ThreadPolicy, action: str, profile: ActorProfile, key: str, target: Optional[str] = None) -> str:
    name_words = [w.lower() for w in re.findall(r"[A-Za-z]+", thread.name) if len(w) > 3]
    topic = name_words[-1] if name_words else "thread"
    target_word = ""
    if target:
        target_bits = [w.lower() for w in re.findall(r"[A-Za-z]+", target) if len(w) > 3]
        target_word = target_bits[-1] if target_bits else target.lower()
        target_objects = [
            f"{target} notice",
            f"{target} roster line",
            f"{target} chalk mark",
            f"{target} library slip",
            f"{target} timetable square",
        ]
        return _pick(target_objects, f"{key}|target-object|{profile.name}")
    objects = {
        "take_action": [
            f"{topic} margin page",
            f"{topic} witness list",
            f"{topic} library slip",
            f"{topic} stairwell mark",
        ],
        "attack_belief": [
            f"{topic} public certainty",
            f"{topic} safest explanation",
            f"{topic} supporting rumor",
            f"{topic} confident claim",
        ],
        "invest_belief": [
            f"{topic} repeated custom",
            f"{topic} noticeboard ritual",
            f"{topic} shared practice",
            f"{topic} small ritual",
        ],
    }
    return _pick(objects.get(action, [f"{topic} detail"]), f"{key}|object|{profile.name}")


def _thread_bespoke_material(profile: ActorProfile, thread: ThreadPolicy, action: str, target: Optional[str], state: Optional[dict]) -> tuple[str, str]:
    pulse = (state or {}).get("pulse_index", 0)
    key = f"{profile.name}|{thread.thread_id}|{action}|{target or ''}|{pulse}"
    motif = _actor_motif(profile)
    medium = _chapter_medium(profile, key)
    obj = _thread_object(thread, action, profile, key, target)
    signature = motif.split(" / ")[0]
    place = _thread_place(profile, thread, action, key)
    if action == "attack_belief":
        scene_pool = [
            (
                f"in {place}, crossed a thin black line through the {obj} and left {medium} tucked beneath the tack",
                "students who had been repeating the claim began adding if before it",
            ),
            (
                f"in {place}, swapped the clean copy of the {obj} for one with a single date circled twice",
                "the easy version of the story suddenly needed an explanation",
            ),
            (
                f"in {place}, asked a passing student to read the {obj} aloud and then pointed to the one sentence that did not survive being spoken",
                "the target lost force because the room heard the weakness at the same time",
            ),
        ]
    elif action == "invest_belief":
        scene_pool = [
            (
                f"in {place}, pinned {medium} above the {obj} and made the first three students sign their names beside it",
                "the idea stopped being private and became something the hallway could repeat",
            ),
            (
                f"in {place}, copied the {obj} onto fresh paper and added a small ritual instruction at the bottom",
                "students began doing the thing before they knew who had started it",
            ),
            (
                f"in {place}, turned the {obj} into a visible station with a pencil, a ribbon, and one chair facing outward",
                "support gathered because the next step looked physically possible",
            ),
        ]
    else:
        scene_pool = [
            (
                f"in {place}, moved the {obj} from the back of the stack to the one place a witness would have to touch it",
                "the next scene now has a specific thing waiting on the table",
            ),
            (
                f"in {place}, copied one line from the {obj} onto {medium} and left both copies slightly misaligned",
                "someone can now notice what changed by comparing the two versions",
            ),
            (
                f"in {place}, asked two students to carry the {obj} together instead of sending it alone",
                "the clue now has witnesses attached to it",
            ),
        ]
    deed, result = _stable_pick_pair(scene_pool, key, recent_trace_signatures(state or {}, actor=profile.name, thread_id=thread.thread_id, action=action))
    return deed, result


def _thread_place(profile: ActorProfile, thread: ThreadPolicy, action: str, key: str) -> str:
    name = thread.name.lower()
    lens = (character_lens(profile, 360) + " " + profile.lore_summary + " " + name).lower()
    if "music" in lens or "sound" in lens or "song" in lens or "euphony" in lens:
        places = ["practice-room door", "choir stair", "metronome shelf", "music corridor"]
    elif "library" in lens or "book" in lens or "margin" in lens or "research" in lens:
        places = ["Library return desk", "catalogue cabinet", "side table under the reading lamp", "stacks threshold"]
    elif "dusk" in lens or "thorn" in lens or "wicker" in lens:
        places = ["east stair noticeboard", "shadowed corridor bend", "discipline-office door", "dormitory sign-out rail"]
    elif "food" in lens or "vellum" in lens or "protein" in lens:
        places = ["refectory serving line", "tea urn ledger", "breakfast tray return", "side table near the water pitcher"]
    elif "finance" in lens or "gimble" in lens or "ledger" in lens or "errata" in lens:
        places = ["Errata Registry hatch", "coin drawer", "receipt rail", "budget ledger desk"]
    elif "therapy" in lens or "inkrest" in lens or "mood" in lens:
        places = ["Reauthoring Rooms threshold", "quiet counseling alcove", "mirrorless side room", "warm-lit margin table"]
    else:
        places = ["north corridor landing", "Great Hall notice rail", "common-room hearth", "courtyard arch", "classroom threshold"]
    return _pick(places, f"{key}|thread-place")


def summarize_influences(profile: ActorProfile, thread: ThreadPolicy, entities: dict[str, dict], talismans: dict[str, int], anchors: dict[str, int], anchor_pressure: int) -> list[str]:
    influences: list[tuple[int, str, str]] = []
    seen_keys: set[str] = set()

    def add_influence(key: str, weight: int, label: str) -> None:
        if weight <= 0 or key in seen_keys or not label:
            return
        seen_keys.add(key)
        influences.append((weight, key, str(label)))

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
    return [label for _, _, label in influences[:3] if label]


def clean_influences(influences: list[str]) -> list[str]:
    return [str(item) for item in (influences or []) if item]


def character_lens(profile: ActorProfile, limit: int = 220) -> str:
    parts = []
    if profile.unwritten_interest:
        parts.append(f"unwritten interest: {profile.unwritten_interest}")
    if profile.goals_text:
        parts.append(f"goals: {profile.goals_text}")
    if profile.beliefs_text:
        parts.append(f"beliefs: {profile.beliefs_text}")
    if profile.personality:
        parts.append(f"personality: {profile.personality}")
    if profile.quirks:
        parts.append(f"quirks: {profile.quirks}")
    if profile.faults:
        parts.append(f"faults: {profile.faults}")
    if not parts and not profile.lore_summary:
        return ""
    return _clean_lore_text("; ".join(parts) if parts else profile.lore_summary, limit)


def pick_action(profile: ActorProfile, thread: ThreadPolicy, entity_belief: int, talismans: dict[str, int], influences: list[str]) -> tuple[str, str]:
    influences = clean_influences(influences)
    allowed = [a for a in profile.preferred_actions if a in ACTION_CLASSES]
    if not allowed:
        allowed = ["take_action"]

    # An actor who IS the anchor of a thread should usually spend themselves
    # to act or strengthen, not erode their own thread.
    actor_is_anchor = (
        profile.name.lower() in thread.name.lower()
        or bool(thread.npc_anchor and profile.name.lower() in thread.npc_anchor.lower())
    )
    if actor_is_anchor:
        allowed = [a for a in allowed if a != "attack_belief"]
        if not allowed:
            allowed = ["take_action", "invest_belief"]

    talisman = chapter_talisman_name(profile.chapter) if profile.chapter else None
    talisman_belief = talismans.get(talisman, 0) if talisman else 0

    influence_text = f" under pressure from {', '.join(influences)}" if influences else ""
    lens = character_lens(profile, 180)
    lens_text = f"; character lens: {lens}" if lens else ""

    if profile.actor_kind == "talisman":
        if "attack_belief" in allowed and thread.pressure in {"high", "medium-high"} and profile.chapter == "Duskthorn":
            return "attack_belief", f"{profile.name} sharpens conflict inside {thread.name}{influence_text}{lens_text}"
        if "invest_belief" in allowed and random.random() < 0.45:
            return "invest_belief", f"{profile.name} feeds its chapter philosophy into {thread.name}{influence_text}{lens_text}"
        return "take_action", f"{profile.name} leaves a chapter-shaped trace in {thread.name}{influence_text}{lens_text}"

    if talisman and entity_belief >= 12 and talisman_belief < 200 and random.random() < 0.22:
        return "invest_belief", f"{profile.name} feels their chapter's talisman pulling for investment{influence_text}{lens_text}"
    if "attack_belief" in allowed and thread.pressure in {"high", "medium-high"}:
        return "attack_belief", f"{profile.name} has narrative reason to erode an opposing position{influence_text}{lens_text}"
    if "invest_belief" in allowed and thread.phase in {"setup", "rising", "climax"} and random.random() < 0.35:
        return "invest_belief", f"{profile.name} strengthens a living pressure inside {thread.name}{influence_text}{lens_text}"
    return "take_action", f"{profile.name} spends presence to leave a concrete trace inside {thread.name}{influence_text}{lens_text}"


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


def belief_cost_for_action(action: str, intensity: str = "minor") -> int:
    # The simulation pays for presence. Keep the default deliberately small so
    # slice-of-life action remains possible without draining the cast dry.
    return 1


def build_trace(profile: ActorProfile, thread: ThreadPolicy, action: str, target: Optional[str], influences: list[str], state: Optional[dict] = None) -> tuple[str, str]:
    influences = clean_influences(influences)
    if thread.thread_id == "academy-daily":
        return build_daily_life_trace(profile, action, influences, state)
    if action == "invest_belief":
        talisman = chapter_talisman_name(profile.chapter) if profile.chapter else None
        return build_concrete_thread_trace(profile, thread, action, talisman or target, influences, state)
    return build_concrete_thread_trace(profile, thread, action, target, influences, state)


def load_gateway_config() -> tuple[int, str, str, int]:
    oc_cfg: dict = {}
    oc_path = Path.home() / ".openclaw" / "openclaw.json"
    if oc_path.exists():
        try:
            loaded = json.loads(oc_path.read_text(encoding="utf-8"))
            oc_cfg = loaded if isinstance(loaded, dict) else {}
        except Exception:
            oc_cfg = {}
    port = int(os.environ.get("OPENCLAW_GATEWAY_PORT") or oc_cfg.get("gateway", {}).get("port") or "18789")
    token = os.environ.get("OPENCLAW_GATEWAY_TOKEN") or oc_cfg.get("gateway", {}).get("auth", {}).get("token") or ""
    model = os.environ.get("NARRATIVE_SIM_TRACE_MODEL") or SIM_TRACE_MODEL_DEFAULT
    try:
        timeout = max(60, int(os.environ.get("NARRATIVE_SIM_TRACE_TIMEOUT") or SIM_TRACE_TIMEOUT_DEFAULT))
    except ValueError:
        timeout = SIM_TRACE_TIMEOUT_DEFAULT
    return port, token, model, timeout


def llm_trace_prompt(plans: list[dict], state: dict) -> str:
    recent = []
    for item in state.get("recent_actions", [])[-14:]:
        trace = item.get("visible_trace") or item.get("deed") or ""
        if trace:
            recent.append(trace[:360])
    return (
        "Write offscreen simulation traces for Enchantify.\n\n"
        "Hard requirements:\n"
        "- Output ONLY valid JSON: {\"traces\":[{\"id\":\"...\",\"visible_trace\":\"...\",\"hidden_effect\":\"...\"}]}.\n"
        "- The visible_trace must be a tiny story snippet: one or two sentences, simple, concrete, and playable.\n"
        "- Invent the action fresh from the actor's goals, quirks, faults, chapter, thread, target, and prior memory.\n"
        "- Use social_context when present: player bond, allies, rivalries, watch-lists, and fears should shape who notices, helps, withholds, or gets hurt.\n"
        "- Do NOT use pre-defined action labels in the prose. Do NOT say protected, moved, acted, gesture, changed behavior, made the thread more present, left a trace, the room learned, students stopped treating, what it costs when nobody helps, or anything like a template.\n"
        "- Do NOT summarize philosophy. Show an object, place, person, quote, or small choice that can feed the next scene, The Bleed, memory, or a story seed.\n"
        "- If action is invest_belief, show what the actor makes more believable or repeatable.\n"
        "- If action is attack_belief, show what claim/person/object they weaken and how, without resolving it.\n"
        "- If action is take_action, show one slice-of-life or thread action that still costs 1 Belief and leaves a usable hook.\n"
        "- hidden_effect should be terse operator memory: mechanic, cost, target/thread, and the playable hook. No flowery prose.\n\n"
        "Avoid echoing these recent traces:\n"
        + json.dumps(recent, ensure_ascii=False, indent=2)
        + "\n\nPlans:\n"
        + json.dumps(plans, ensure_ascii=False, indent=2)
    )


def call_llm_for_traces(plans: list[dict], state: dict) -> dict[str, tuple[str, str]]:
    if not plans or os.environ.get("NARRATIVE_SIM_NO_LLM", "").lower() in {"1", "true", "yes", "on"}:
        return {}
    port, token, model, timeout = load_gateway_config()
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are the Labyrinth of Stories' offscreen simulation writer. "
                    "You write concrete, bespoke, non-template micro-actions that preserve mechanics."
                ),
            },
            {"role": "user", "content": llm_trace_prompt(plans, state)},
        ],
        "temperature": 0.8,
        "max_tokens": 2200,
        "stream": False,
    }
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "x-openclaw-session-key": f"narrative-sim-{int(time.time())}",
        },
        data=json.dumps(payload).encode("utf-8"),
    )
    def log_failure(message: str) -> None:
        try:
            SIM_TRACE_LOG.parent.mkdir(parents=True, exist_ok=True)
            with SIM_TRACE_LOG.open("a", encoding="utf-8") as fh:
                fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")
        except Exception:
            pass

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        content = result["choices"][0]["message"]["content"].strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
        parsed = json.loads(content)
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, IndexError, json.JSONDecodeError, TimeoutError, OSError) as exc:
        log_failure(f"LLM_TRACE_FALLBACK {type(exc).__name__}: {str(exc)[:300]}")
        return {}
    recent_sigs = recent_trace_signatures(state or {})
    traces: dict[str, tuple[str, str]] = {}
    for item in parsed.get("traces", []):
        trace_id = str(item.get("id") or "").strip()
        visible = str(item.get("visible_trace") or "").strip()
        hidden = str(item.get("hidden_effect") or "").strip()
        if not trace_id or not trace_is_usable(visible, recent_sigs):
            log_failure(f"LLM_TRACE_REJECTED id={trace_id or '?'} visible={visible[:220]!r}")
            continue
        if not hidden:
            hidden = "Mechanic preserved by narrative simulation; playable hook should be carried into the next relevant scene."
        traces[trace_id] = (visible, hidden)
    return traces


def choose_target(action: str, profile: ActorProfile, entities: dict[str, dict]) -> Optional[str]:
    """Pick a target for attack_belief from the full world register.

    The register is a belief economy — all entities compete for narrative
    weight. Any entity is a valid target: NPCs, locations, objects, fae,
    threads. Same-chapter allies are excluded. High-belief entities are
    more likely targets (they hold more territory worth contesting).
    """
    if action != "attack_belief":
        return None
    attacker_chapter = profile.chapter
    candidates = []
    for name, ent in entities.items():
        if name == profile.name:
            continue
        if ent.get("belief", 0) < 5:
            continue
        if attacker_chapter and infer_entity_chapter(ent) == attacker_chapter:
            continue
        candidates.append(name)
    if not candidates:
        return None
    weights = [max(1, entities[name].get("belief", 0)) for name in candidates]
    return random.choices(candidates, weights=weights, k=1)[0]


def _stable_pick(items: list[tuple], key: str, avoid_signatures: Optional[set[str]] = None) -> tuple:
    if not items:
        return ("the ordinary corridors", "did one specific ordinary thing", "the day became more legible")
    avoid_signatures = avoid_signatures or set()
    start = sum(ord(ch) for ch in key) % len(items)
    ordered = items[start:] + items[:start]
    for item in ordered:
        if len(item) == 3:
            _, deed, result = item
        elif len(item) == 2:
            deed, result = item
        else:
            continue
        if trace_has_boilerplate(f"{deed} {result}"):
            continue
        if not trace_is_recent(deed, result, avoid_signatures):
            return item
    return ordered[0]


def _stable_pick_pair(items: list[tuple[str, str]], key: str, avoid_signatures: Optional[set[str]] = None) -> tuple[str, str]:
    if not items:
        return ("did one specific thing", "the thread changed in a visible way")
    avoid_signatures = avoid_signatures or set()
    start = sum(ord(ch) for ch in key) % len(items)
    ordered = items[start:] + items[:start]
    for deed, result in ordered:
        if trace_has_boilerplate(f"{deed} {result}"):
            continue
        if not trace_is_recent(deed, result, avoid_signatures):
            return deed, result
    return ordered[0]


def _sentence_case(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return text
    return text[0].upper() + text[1:]


def _clause_case(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return text
    return text[0].lower() + text[1:]


def _lens_has(lens: str, *needles: str) -> bool:
    for needle in needles:
        if " " in needle:
            if needle in lens:
                return True
            continue
        if re.search(rf"\b{re.escape(needle)}s?\b", lens):
            return True
    return False


def _plain_label(label: str) -> str:
    return re.sub(r"^(the|a|an)\s+", "", (label or "").strip(), flags=re.IGNORECASE)


def _signature_move(profile: ActorProfile, thread: Optional[ThreadPolicy], target: Optional[str], action: str, state: Optional[dict]) -> Optional[tuple[str, str]]:
    lens = (character_lens(profile, 500) + " " + profile.lore_summary).lower()
    thread_name = thread.name if thread else "Academy Daily Life"
    focus = target or thread_name
    focus_label = _plain_label(focus)
    pulse = (state or {}).get("pulse_index", 0)
    key = f"{profile.name}|{thread_name}|{focus}|{action}|{pulse}"

    if _lens_has(lens, "chaos", "sigil", "gossip", "scandal", "leverage") or profile.name.lower() == "wicker eddies":
        moves = [
            (
                f"drew a small sigil in the corner of the {focus_label} notice and then loudly pretended not to care who saw it",
                "By lunch, students were repeating the mark as a joke, which meant it had already started working",
            ),
            (
                f"changed one public errand for {focus_label} into a dare and signed it with somebody else's initials",
                "The hallway carried the rumor farther because nobody could agree whether it was official",
            ),
            (
                f"started a harmless-looking coffee-line rumor about {focus_label}, then walked away before it chose a villain",
                "Attention did the rest of the damage without needing his hands on it",
            ),
        ]
        return _stable_pick_pair(moves, key)

    if _lens_has(lens, "music", "sound", "song", "acoustic", "tuning", "migration") or profile.name.lower() == "professor euphony":
        moves = [
            (
                f"set three metronomes outside the {focus_label} room and tuned them to slightly different heartbeats",
                "Everyone who passed heard the missing rhythm before they understood what was missing",
            ),
            (
                f"tapped her tuning fork against the {focus_label} doorframe and wrote down which note refused to fade",
                "The thread gained an audible clue instead of another theory",
            ),
            (
                f"asked the choir stair to hum the {focus_label} phrase back at her and caught the wrong echo in her notebook",
                "The sound made the secret easier to find and harder to dismiss",
            ),
        ]
        return _stable_pick_pair(moves, key)

    if _lens_has(lens, "hidden", "alley", "night", "photography", "shadow") or profile.name.lower() == "caspian shan":
        moves = [
            (
                f"slipped a black-and-white photograph of the {focus_label} corner under the stair rail, with one shadow circled in silver pencil",
                "The hidden part of the scene became visible only after someone tilted the paper toward the window",
            ),
            (
                f"left a folded map of the back corridors beside {focus_label}, marked with the route nobody uses in daylight",
                "The safest path stopped being the obvious one",
            ),
            (
                f"waited in the landing shadow until the {focus_label} witness passed, then handed them a note without making them stop walking",
                "The message arrived without turning the witness into a spectacle",
            ),
        ]
        return _stable_pick_pair(moves, key)

    if _lens_has(lens, "estate", "obituary", "museum", "plaque", "recipe") or profile.name.lower() == "professor archibald permancer":
        moves = [
            (
                f"tied an estate-sale tag to the {focus_label} file and wrote provenance unknown in immaculate ink",
                "Students treated the file like an artifact instead of a rumor",
            ),
            (
                f"placed an old recipe card beside {focus_label}, the ingredient list altered so one impossible item appeared twice",
                "The past entered the room through something practical enough to be unsettling",
            ),
            (
                f"copied a forgotten obituary into the {focus_label} margin and underlined the date that should not match",
                "The thread acquired a dead witness with excellent handwriting",
            ),
        ]
        return _stable_pick_pair(moves, key)

    if _lens_has(lens, "architecture", "foundation", "stone", "threshold", "lock"):
        moves = [
            (
                f"chalked a quiet load-bearing mark beneath the {focus_label} threshold, low enough that only someone kneeling would see it",
                "The next person who crossed that line felt the floor answer before the faculty did",
            ),
            (
                f"moved the {focus_label} record into a drawer with two key-tags and left one tag hanging where a guilty hand would hesitate",
                "The evidence became harder to erase because access now required a choice",
            ),
            (
                f"set a stone paperweight on the {focus_label} page and turned it exactly one quarter toward the old wing",
                "The thread acquired direction instead of merely pressure",
            ),
        ]
        return _stable_pick_pair(moves, key)

    if profile.chapter == "Duskthorn":
        moves = [
            (
                f"stamped the {focus_label} notice with a dark thorn-mark exactly where a signature should have been",
                "Students argued about authority instead of the original question",
            ),
            (
                f"moved the {focus_label} sign-out sheet to the discipline-office door and left the old hook empty",
                "The ordinary route suddenly felt like choosing sides",
            ),
            (
                f"blackened one corner of the {focus_label} record without burning the paper through",
                "The damage looked deliberate enough that everyone began supplying motives",
            ),
        ]
        return _stable_pick_pair(moves, key)

    if _lens_has(lens, "thrift", "antique", "receipt", "store"):
        moves = [
            (
                f"pinned a thrift-store price tag to the {focus_label} notice and wrote a second, smaller price beside it: what it costs when nobody helps",
                "Students stopped treating the matter like an abstract rule and started asking who was actually paying for it",
            ),
            (
                f"copied the {focus_label} clue onto the back of three old shop receipts and slipped them into coat pockets before supper",
                "By evening, the thread had spread through errands, pockets, and ordinary inconvenience",
            ),
            (
                f"left a tray of mismatched buttons under the {focus_label} board, each tied to a name no one had been saying aloud",
                "The room learned to count the missing people before it counted the evidence",
            ),
        ]
        return _stable_pick_pair(moves, key)

    if _lens_has(lens, "spelling", "bee", "grammar", "language"):
        moves = [
            (
                f"replaced the {focus_label} sign with one corrected letter circled in red chalk and a pronunciation key underneath",
                "Students repeated the corrected word all afternoon without noticing they had changed the spell",
            ),
            (
                f"left three spelling slips beside the {focus_label} register, each defining the word everyone had been misusing",
                "The thread lost some of its fog because the wrong word no longer had cover",
            ),
            (
                f"made the youngest students chant the {focus_label} term as a spelling-bee warmup until the older students grew embarrassed into accuracy",
                "Precision became social before it became official",
            ),
        ]
        return _stable_pick_pair(moves, key)

    if _lens_has(lens, "therapy", "therapeutic", "narrative", "consciousness", "brain", "mood"):
        moves = [
            (
                f"left a two-column reauthoring card beside {focus}: what happened, and what the frightened part believes happened",
                "The next witness had language for the feeling before the feeling could become fate",
            ),
            (
                f"moved a chair beside the {focus_label} record so the first person to read it would have somewhere to sit",
                "The thread slowed down enough for care to enter before interpretation",
            ),
            (
                f"underlined one sentence in the {focus_label} account and wrote, not the whole self, in the margin",
                "The pressure became survivable because it stopped pretending to be total",
            ),
        ]
        return _stable_pick_pair(moves, key)

    if _lens_has(lens, "food", "nutrition", "longevity", "protein", "diet"):
        moves = [
            (
                f"left a precise refectory note beside {focus}: protein first, fiber second, panic never",
                "The hour became easier to survive because the body had been consulted",
            ),
            (
                f"replaced the {focus_label} rumor with a meal card, a water glass, and one question about sleep",
                "The thread had to pass through the body before becoming drama",
            ),
            (
                f"annotated the {focus_label} ledger with a practical prescription for the next meal, not the next moral failure",
                "The Academy treated care as evidence",
            ),
        ]
        return _stable_pick_pair(moves, key)

    return None


def build_daily_life_trace(profile: ActorProfile, action: str, influences: list[str], state: Optional[dict] = None) -> tuple[str, str]:
    """Turn Academy Daily Life movement into a concrete offscreen happening."""
    influences = clean_influences(influences)
    signature = _signature_move(profile, None, None, action, state)
    if signature:
        deed, result = signature
        location = _daily_place(profile, action, f"{profile.name}|{action}|{(state or {}).get('pulse_index', 0)}")
        cost = belief_cost_for_action(action, "minor")
        lens = character_lens(profile, 170)
        visible = (
            f"In {location}, {profile.name} {deed}. "
            f"{_sentence_case(result)}."
        )
        hidden = (
            f"Mechanic: {action}; cost {cost} Belief; no direct target delta. Signature move: {deed}; result: {result}. "
            f"Character lens: {lens or 'world-register only'}."
        )
        return visible, hidden
    location, deed, result = _daily_bespoke_material(profile, action, influences, state)
    lens = character_lens(profile, 170)
    motive = _actor_motif(profile) if lens else "their own particular habits"
    cost = belief_cost_for_action(action, "minor")
    visible = (
        f"In {location}, {profile.name} {deed}. "
        f"{_sentence_case(result)}."
    )
    hidden = (
        f"Mechanic: {action}; cost {cost} Belief; no direct target delta. Trace: {location} / {deed} / result: {result}. "
        f"Character lens: {lens or 'world-register only'}."
    )
    return visible, hidden


def build_concrete_thread_trace(
    profile: ActorProfile,
    thread: ThreadPolicy,
    action: str,
    target: Optional[str],
    influences: list[str],
    state: Optional[dict] = None,
) -> tuple[str, str]:
    influences = clean_influences(influences)
    signature = _signature_move(profile, thread, target, action, state)
    if signature:
        deed, result = signature
        lens = character_lens(profile, 170)
        target_name = target or thread.name
        cost = belief_cost_for_action(action, "minor")
        visible = f"{profile.name} {deed}. {_sentence_case(result)}."
        hidden = (
            f"Mechanic: {action}; cost {cost} Belief; target: {target_name}; thread: {thread.name}; signature move: {deed}; result: {result}. "
            f"Character lens: {lens or 'world-register only'}."
        )
        return visible, hidden
    deed, result = _thread_bespoke_material(profile, thread, action, target, state)
    lens = character_lens(profile, 170)
    motive = _actor_motif(profile) if lens else "their own particular habits"
    target_name = target or thread.name
    cost = belief_cost_for_action(action, "minor")
    visible = f"{profile.name}, {deed}. {_sentence_case(result)}."
    hidden = (
        f"Mechanic: {action}; cost {cost} Belief; target: {target_name}; thread: {thread.name}; trace: {deed}; result: {result}. "
        f"Character lens: {lens or 'world-register only'}."
    )
    return visible, hidden


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
                score -= recent_actor_count(state, actor_name) * 4
                if recent_actor_count(state, actor_name) == 0:
                    score += 5
                if profile.unwritten_interest:
                    score += 2
                candidates.append((score, profile, thread, entity_belief))

    if not candidates:
        return []

    selected = sample_without_replacement_weighted(candidates, MAX_CANDIDATE_ACTIONS)
    selected.sort(key=lambda item: item[0], reverse=True)
    planned_actions: list[dict] = []
    for _, profile, thread, entity_belief in selected:
        influences = summarize_influences(profile, thread, entities, talismans, anchors, anchor_pressure)
        action_name, reason = pick_action(profile, thread, entity_belief, talismans, influences)
        intensity = action_intensity(thread, entity_belief, state, profile.name)
        if not allowed_to_land(intensity, thread, entity_belief):
            intensity = "medium"
            action_name = "take_action"
            reason = f"{profile.name} can leave a trace in {thread.name}, but not resolve it without the player"
        target = choose_target(action_name, profile, entities)
        social_context = {}
        if _HAS_RELATIONSHIPS:
            try:
                social_context = relationships.actor_social_context(relationships.DEFAULT_PLAYER, profile.name)
            except Exception:
                social_context = {}
        plan_id = f"sim-{len(planned_actions) + 1}"
        planned_actions.append({
            "id": plan_id,
            "profile": profile,
            "thread": thread,
            "entity_belief": entity_belief,
            "influences": influences,
            "action_name": action_name,
            "reason": reason,
            "intensity": intensity,
            "target": target,
            "llm_packet": {
                "id": plan_id,
                "actor": profile.name,
                "actor_kind": profile.actor_kind,
                "belief": entity_belief,
                "chapter": profile.chapter,
                "personality": profile.personality,
                "quirks": profile.quirks,
                "faults": profile.faults,
                "goals": profile.goals_text,
                "beliefs": profile.beliefs_text,
                "unwritten_interest": profile.unwritten_interest,
                "lore_summary": character_lens(profile, 700) or profile.lore_summary,
                "thread": {
                    "id": thread.thread_id,
                    "name": thread.name,
                    "phase": thread.phase,
                    "pressure": thread.pressure,
                    "npc_anchor": thread.npc_anchor,
                    "next_beat": thread.next_beat,
                },
                "mechanic": action_name,
                "belief_cost": belief_cost_for_action(action_name, intensity),
                "target": target,
                "reason": reason,
                "influences": influences[:6],
                "social_context": social_context,
            },
        })

    llm_traces = call_llm_for_traces([item["llm_packet"] for item in planned_actions], state)
    pulse_recent_rows: list[dict] = []
    for plan in planned_actions:
        profile = plan["profile"]
        thread = plan["thread"]
        action_name = plan["action_name"]
        target = plan["target"]
        intensity = plan["intensity"]
        influences = plan["influences"]
        visible_trace, hidden_effect = llm_traces.get(plan["id"], ("", ""))
        if not visible_trace:
            continue
        pulse_recent_rows.append({
            "npc": profile.name,
            "thread_id": thread.thread_id,
            "action": action_name,
            "belief_cost": belief_cost_for_action(action_name, intensity),
            "visible_trace": visible_trace,
            "hidden_effect": hidden_effect,
            "trace_signature": normalize_trace_signature(f"{visible_trace} {hidden_effect}"),
        })
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
            reason=plan["reason"],
            visible_trace=visible_trace,
            hidden_effect=hidden_effect,
            target=target,
            belief_delta_hint=delta_hint,
            priority=priority,
            actor_kind=profile.actor_kind,
            chapter=profile.chapter,
            influence_snapshot=influences,
            belief_cost=belief_cost_for_action(action_name, intensity),
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
        if action.action not in {"take_action", "attack_belief", "invest_belief"}:
            continue
        suggested_mode = {
            "take_action": "narrative",
            "attack_belief": "pact_war",
            "invest_belief": "world_investment",
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
            "belief_cost": action.belief_cost,
            "influence_snapshot": action.influence_snapshot,
            "visible_trace": action.visible_trace,
            "hidden_effect": action.hidden_effect,
            "trace_signature": normalize_trace_signature(f"{action.visible_trace} {action.hidden_effect}"),
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
    cost = max(1, action.belief_cost or belief_cost_for_action(action.action, action.intensity))
    actor_kind = "talisman" if action.actor_kind == "talisman" else "entity"
    deltas.append((action.npc, actor_kind, -cost, f"{action.npc} spent {cost} Belief to leave a living-world trace"))
    if action.action == "invest_belief":
        profile_chapter = infer_entity_chapter({"name": action.npc, "type": "", "notes": ""})
        talisman = chapter_talisman_name(profile_chapter) if profile_chapter else None
        if talisman:
            deltas.append((talisman, "talisman", 1, f"{action.npc} strengthened it through {action.thread_name}"))
        thread_delta = 1 if action.intensity in {"medium", "major"} else 0
        if thread_delta:
            deltas.append((action.thread_name, "thread", thread_delta, f"{action.npc} made the thread more present"))
    elif action.action == "attack_belief" and action.target:
        deltas.append((action.target, "entity", -1, f"{action.npc} weakened it through {action.thread_name}"))
        rebound = 1 if action.intensity == "major" else 0
        if rebound:
            deltas.append((action.thread_name, "thread", rebound, f"{action.thread_name} gained pressure from conflict"))
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
        section_m = list(re.finditer(r"^## .+$", register_text[:match.start()], re.MULTILINE))
        section = section_m[-1].group(0).strip() if section_m else ""
        kind = "thread" if section == "## Active Threads" else "entity"
        if section == "## Chapter Talismans":
            kind = "talisman"
        entity_type = ""
        parts = [p.strip() for p in line.strip().strip("|").split("|")]
        if len(parts) >= 2:
            entity_type = parts[1]
        after = clamp_belief(before + delta, "Thread" if kind == "thread" else entity_type, name, explicit_talisman=(kind == "talisman"))
        if kind in {"thread", "talisman"}:
            updated = table_pattern.sub(lambda m: m.group(1) + str(after) + m.group(3), register_text, count=1)
        else:
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
        line = match.group(0)
        mtype = re.search(r"\(([^,]+),\s*Belief\s*\d+\)", line)
        entity_type = mtype.group(1).strip() if mtype else "NPC"
        after = clamp_belief(before + delta, entity_type, name)
        notes_m = re.search(r"\)\s*—\s*(.*)$", line)
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

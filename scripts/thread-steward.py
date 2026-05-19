#!/usr/bin/env python3
"""Thread lifecycle steward.

Threads should have a metabolism: seeds become subplots, subplots advance,
resolved stories archive, and permanent background texture stays background.
This script makes those lifecycle decisions visible and can conservatively
apply safe thread births.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "scripts"))
from belief_caps import clamp_belief

LORE = BASE / "lore"
MEMORY = BASE / "memory"
CONFIG = BASE / "config"
THREADS = LORE / "threads.md"
REGISTER = LORE / "world-register.md"
CHARACTERS = LORE / "characters.md"
QUEUE = MEMORY / "tick-queue.md"
STATE = CONFIG / "thread-steward-state.json"

PROMOTION_COOLDOWN_DAYS = 7
MAX_PROMOTIONS_PER_RUN = 1


@dataclass
class Entity:
    name: str
    kind: str
    belief: int
    notes: str
    threads: list[str]


@dataclass
class ThreadInfo:
    name: str
    thread_id: str
    phase: str
    pressure: str
    npc_anchor: str
    next_beat: str
    last_advanced: str
    closed: str


@dataclass
class StewardAction:
    action: str
    name: str
    reason: str
    confidence: str
    payload: dict[str, Any]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    tmp.replace(path)


def slug(value: str) -> str:
    value = re.sub(r"'s\b", "", value.lower())
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")[:72] or "thread"


def clean(value: str) -> str:
    value = re.sub(r"\*\*([^*]+)\*\*", r"\1", value or "")
    value = value.replace("*", "")
    return re.sub(r"\s+", " ", value).strip(" ;")


def normalize_phase(value: str) -> str:
    phase = clean(value).lower().split()[0] if value else ""
    if phase in {"quiet", "background"}:
        return "permanent"
    if phase in {"escalating", "escalation"}:
        return "rising"
    return phase


def parse_date(raw: str) -> date | None:
    m = re.search(r"\d{4}-\d{2}-\d{2}", raw or "")
    if not m:
        return None
    try:
        return date.fromisoformat(m.group(0))
    except ValueError:
        return None


def days_since(raw: str) -> int | None:
    parsed = parse_date(raw)
    return (date.today() - parsed).days if parsed else None


def parse_entities() -> dict[str, Entity]:
    entities: dict[str, Entity] = {}
    for line in read(REGISTER).splitlines():
        m = re.match(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|\s*([^|]*)\|", line)
        if not m:
            continue
        name, kind, belief, notes = m.group(1).strip(), m.group(2).strip(), int(m.group(3)), m.group(4).strip()
        if name.lower() in {"entity", "---"}:
            continue
        threads = [item.strip() for item in re.findall(r"\[thread:([^\]]+)\]", notes)]
        entities[name.lower()] = Entity(name=name, kind=kind, belief=belief, notes=notes, threads=threads)
    return entities


def parse_threads() -> dict[str, ThreadInfo]:
    threads: dict[str, ThreadInfo] = {}
    for section in re.split(r"^## Thread:\s*", read(THREADS), flags=re.MULTILINE)[1:]:
        lines = section.strip().splitlines()
        if not lines:
            continue
        name = lines[0].strip()
        if name.startswith("["):
            continue

        def field(label: str) -> str:
            m = re.search(rf"\*\*{re.escape(label)}:(?:\*\*)?\s*([^\n]+)", section, re.IGNORECASE)
            return clean(m.group(1)) if m else ""

        info = ThreadInfo(
            name=name,
            thread_id=field("id").strip("`"),
            phase=normalize_phase(field("phase")),
            pressure=field("pressure"),
            npc_anchor=field("npc_anchor"),
            next_beat=field("Next beat"),
            last_advanced=field("Last advanced"),
            closed=field("closed"),
        )
        threads[info.thread_id or slug(name)] = info
    return threads


def character_blocks() -> dict[str, str]:
    text = read(CHARACTERS)
    blocks: dict[str, str] = {}
    for m in re.finditer(r"^###\s+(.+?)\s*$", text, re.MULTILINE):
        start = m.end()
        next_m = re.search(r"^###\s+|^##\s+", text[start:], re.MULTILINE)
        end = start + next_m.start() if next_m else len(text)
        raw_name = clean(re.sub(r"\s+—.*$", "", m.group(1)).strip())
        blocks[raw_name.lower()] = text[start:end].strip()
    return blocks


def compact_character_roster() -> dict[str, str]:
    text = read(CHARACTERS)
    roster: dict[str, str] = {}
    for m in re.finditer(r"^\*\*(.+?)\*\*\s+—\s+(.+)$", text, re.MULTILINE):
        name = clean(re.sub(r"\s*\([^)]*\)", "", m.group(1)).strip())
        roster[name.lower()] = clean(m.group(2))
    return roster


def character_lore(name: str) -> dict[str, str]:
    blocks = character_blocks()
    roster = compact_character_roster()
    key = name.lower()
    block = blocks.get(key, "")
    if not block and key.startswith("professor "):
        bare = key.replace("professor ", "", 1)
        block = next((body for title, body in blocks.items() if bare in title), "")
    if not block:
        block = roster.get(key, "")

    def field(label: str) -> str:
        m = re.search(rf"\*\*{re.escape(label)}:\*\*\s*(.+)", block)
        return clean(m.group(1)) if m else ""

    return {
        "personality": field("Personality") or block.split(".")[0][:120],
        "faults": field("Faults"),
        "quirks": field("Quirks"),
        "goals": field("Goals"),
        "interest": field("Unwritten Interest"),
        "hooks": field("Story hooks"),
        "voice": field("Voice"),
    }


def seed_counts() -> Counter[str]:
    counts: Counter[str] = Counter()
    for line in read(QUEUE).splitlines():
        m = re.search(r"\[THREAD SEED:\s*([^\]]+)\]", line)
        if m:
            counts[clean(m.group(1))] += 1
    return counts


def dedicated_thread_anchors(threads: dict[str, ThreadInfo]) -> set[str]:
    anchors: set[str] = set()
    for info in threads.values():
        for raw in (info.npc_anchor, info.name):
            raw = clean(raw)
            if raw and raw.lower() not in {"all npcs", "none"}:
                anchors.add(raw.lower())
    return anchors


def thread_name_for_seed(entity: Entity, lore: dict[str, str]) -> str:
    custom = {
        "dr. elowen vellum": "Elowen's Refectory Experiments",
        "professor luna wispwood": "Luna's Map of Forgotten Routes",
        "professor vivian villanelle": "Vivian's Souvenir Sentence Ledger",
        "professor maxwell thorne": "Maxwell's Second Meaning",
        "professor wellend thickets": "Thickets' Cooperative Riddle",
        'orlando "oracle" scrollstone': "Oracle's Late Predictions",
    }
    if entity.name.lower() in custom:
        return custom[entity.name.lower()]
    first = entity.name.split()[0].strip('"')
    interest = lore.get("interest", "")
    if "library" in interest.lower() or "book" in interest.lower():
        return f"{first}'s Borrowed Shelf"
    if "music" in interest.lower() or "sound" in interest.lower():
        return f"{first}'s Hidden Frequency"
    if "map" in interest.lower() or "trail" in interest.lower():
        return f"{first}'s Unmapped Route"
    return f"{first}'s Unwritten Thread"


def build_seed_payload(entity: Entity, count: int) -> dict[str, Any]:
    lore = character_lore(entity.name)
    name = thread_name_for_seed(entity, lore)
    thread_id = slug(name)
    custom = custom_payload(entity.name, name, thread_id)
    if custom:
        custom["seed_count"] = count
        custom["lore_basis"] = {
            "personality": lore.get("personality", ""),
            "faults": lore.get("faults", ""),
            "quirks": lore.get("quirks", ""),
            "interest": lore.get("interest", ""),
            "hooks": lore.get("hooks", ""),
        }
        return custom
    interest = lore.get("interest") or "their growing Unwritten attention"
    fault = lore.get("faults") or "the risk that attention becomes avoidance"
    hook = lore.get("hooks") or f"{entity.name}'s attention has gathered enough mass to become a story of its own"
    interest_label = concise_interest(interest)
    status = f"{entity.name}'s {interest_label} has begun affecting Academy life."
    next_beat = (
        f"{entity.name} leaves a concrete trace of this interest where bj can find it: "
        f"a note, object, recommendation, or small request that reveals whether their gift is helping or becoming tangled in {fault.lower()}."
    )
    return {
        "name": name,
        "id": thread_id,
        "type": "npc-subplot",
        "phase": "setup",
        "pressure": "low",
        "npc_anchor": entity.name,
        "locations": "Academy corridors, Library, Great Hall, and wherever the Unwritten Interest touches the day",
        "entities": entity.name,
        "nothing_pressure": "medium - the Nothing can flatten this into mere trivia instead of lived story",
        "status": status,
        "next_beat": next_beat,
        "starting_belief": max(7, min(10, entity.belief // 4)),
        "seed_count": count,
        "lore_basis": {
            "personality": lore.get("personality", ""),
            "faults": lore.get("faults", ""),
            "quirks": lore.get("quirks", ""),
            "interest": interest,
            "hooks": hook,
        },
    }


def concise_interest(interest: str) -> str:
    text = clean(interest).lower()
    if "longevity" in text or "protein" in text or "metabolic" in text:
        return "longevity-and-fuel research"
    if "transit" in text or "urban planning" in text or "trail" in text:
        return "map-and-route obsession"
    if "found poetry" in text or "overheard" in text:
        return "souvenir-sentence collection"
    if "abstract art" in text or "graffiti" in text:
        return "second-meaning study"
    if "mysteries" in text or "rabbit holes" in text:
        return "riddle-and-mystery work"
    if "weather" in text or "prediction" in text:
        return "late-prophecy habit"
    return text.split(".")[0][:90] or "Unwritten Interest"


def custom_payload(entity_name: str, name: str, thread_id: str) -> dict[str, Any] | None:
    key = entity_name.lower()
    if key == "dr. elowen vellum":
        return {
            "name": name,
            "id": thread_id,
            "type": "npc-subplot",
            "phase": "setup",
            "pressure": "low",
            "npc_anchor": entity_name,
            "locations": "Refectory Marginalia, Great Hall, Library, dorm desk, and the player's real food log",
            "entities": entity_name,
            "nothing_pressure": "medium - the Nothing can turn care into metrics, guilt, or forgetfulness",
            "status": "Elowen has begun translating fuel, health, and longevity research into small practical experiments for bj.",
            "next_beat": "A precise refectory note appears with one useful experiment for the day, one measurement Elowen refuses to moralize, and one comfort she insists must remain part of the binding.",
            "starting_belief": 8,
        }
    return None


def load_state() -> dict[str, Any]:
    if not STATE.exists():
        return {"history": []}
    try:
        return json.loads(read(STATE))
    except Exception:
        return {"history": []}


def save_state(state: dict[str, Any]) -> None:
    write(STATE, json.dumps(state, indent=2, ensure_ascii=False))


def last_promotion_age(state: dict[str, Any]) -> int | None:
    dates = [
        item.get("applied_at", "")
        for item in state.get("history", [])
        if item.get("action") == "PROMOTE_SEED" and item.get("applied_at")
    ]
    if not dates:
        return None
    return days_since(max(dates))


def propose_actions(force: bool = False) -> list[StewardAction]:
    entities = parse_entities()
    threads = parse_threads()
    seeds = seed_counts()
    anchors = dedicated_thread_anchors(threads)
    state = load_state()
    actions: list[StewardAction] = []

    cooldown_age = last_promotion_age(state)
    promotion_allowed = force or cooldown_age is None or cooldown_age >= PROMOTION_COOLDOWN_DAYS

    seed_candidates: list[tuple[int, Entity, int]] = []
    for seed, count in seeds.items():
        entity = entities.get(seed.lower())
        if not entity or entity.kind.lower() != "npc":
            continue
        if seed.lower() in anchors:
            continue
        non_daily = [item for item in entity.threads if item not in {"academy-daily", "main-arc"}]
        if non_daily:
            continue
        score = entity.belief + (count * 5)
        seed_candidates.append((score, entity, count))

    seed_candidates.sort(key=lambda item: (item[0], item[1].belief, item[2]), reverse=True)
    if seed_candidates and promotion_allowed:
        score, entity, count = seed_candidates[0]
        payload = build_seed_payload(entity, count)
        actions.append(StewardAction(
            action="PROMOTE_SEED",
            name=payload["name"],
            reason=f"{entity.name} has Belief {entity.belief} and {count} queued seed signal(s); score {score}.",
            confidence="medium",
            payload=payload,
        ))
    elif seed_candidates:
        score, entity, count = seed_candidates[0]
        actions.append(StewardAction(
            action="DEFER_SEED",
            name=entity.name,
            reason=f"Strongest seed is ready, but promotion cooldown is active ({cooldown_age} day(s) since last promotion).",
            confidence="high",
            payload={"seed": entity.name, "score": score, "seed_count": count},
        ))

    for info in threads.values():
        if info.thread_id in {"academy-daily", "main-arc"} or info.phase == "permanent":
            continue
        age = days_since(info.last_advanced)
        if info.phase == "resolution":
            if age is not None and age >= 3:
                actions.append(StewardAction(
                    action="CLOSE_THREAD_READY",
                    name=info.name,
                    reason=f"Thread is in resolution and last advanced {age} day(s) ago; it needs a closure beat or explicit continuation.",
                    confidence="medium",
                    payload={"thread_id": info.thread_id, "next_beat": info.next_beat, "last_advanced": info.last_advanced},
                ))
            else:
                actions.append(StewardAction(
                    action="ADVANCE_THREAD",
                    name=info.name,
                    reason="Thread is already in resolution; next play should deliver a concrete consequence instead of adding more setup.",
                    confidence="medium",
                    payload={"thread_id": info.thread_id, "next_beat": info.next_beat, "last_advanced": info.last_advanced},
                ))
        elif age is not None and age >= 14:
            actions.append(StewardAction(
                action="COOL_THREAD",
                name=info.name,
                reason=f"Thread has not advanced in {age} day(s); cool, defer, or revive with one specific beat.",
                confidence="medium",
                payload={"thread_id": info.thread_id, "phase": info.phase, "last_advanced": info.last_advanced},
            ))

    return actions


def add_thread_section(threads_text: str, payload: dict[str, Any]) -> str:
    today = date.today().isoformat()
    section = (
        "\n"
        f"## Thread: {payload['name']}\n\n"
        f"**id:** `{payload['id']}`\n"
        f"**type:** {payload['type']}\n"
        f"**phase:** {payload['phase']}\n"
        f"**pressure:** {payload['pressure']}\n"
        f"**npc_anchor:** {payload['npc_anchor']}\n"
        f"**locations:** {payload['locations']}\n"
        f"**entities:** {payload['entities']}\n"
        f"**Nothing pressure:** {payload['nothing_pressure']}\n\n"
        f"**Next beat:** {payload['next_beat']}\n\n"
        f"**Last advanced:** {today}\n"
        f"**born:** {today}\n"
        "**closed:** —\n"
    )
    marker = "\n## Archive"
    if marker in threads_text:
        return threads_text.replace(marker, section + "\n" + marker, 1)
    return threads_text.rstrip() + "\n" + section


def add_active_thread_row(register_text: str, payload: dict[str, Any]) -> str:
    starting_belief = clamp_belief(payload["starting_belief"], "Thread", payload["name"])
    row = (
        f"| {payload['name']} | Thread | {starting_belief} | "
        f"[id:{payload['id']}] Phase: {payload['phase']} — {payload['status']} |"
    )
    table = re.search(
        r"(^## Active Threads\s*\n.*?\n\| Entity \| Type \| Belief \| Notes \|\n\|[-| ]+\|\n)",
        register_text,
        re.MULTILINE | re.DOTALL,
    )
    if not table:
        raise SystemExit("Could not locate Active Threads table in lore/world-register.md")
    return register_text[:table.end()] + row + "\n" + register_text[table.end():]


def tag_entity(register_text: str, entity_name: str, thread_id: str) -> str:
    pattern = re.compile(
        r"^(\|\s*" + re.escape(entity_name) + r"\s*\|\s*NPC\s*\|\s*\d+\s*\|\s*)([^|]*)(\|)",
        re.MULTILINE | re.IGNORECASE,
    )
    m = pattern.search(register_text)
    if not m:
        return register_text
    notes = m.group(2).strip()
    if f"[thread:{thread_id}]" in notes:
        return register_text
    tag_m = re.search(r"\[thread:([^\]]+)\]", notes)
    if tag_m:
        existing = [item.strip() for item in tag_m.group(1).split(",") if item.strip()]
        if thread_id not in existing:
            existing.append(thread_id)
        notes = notes[:tag_m.start()] + f"[thread:{','.join(existing)}]" + notes[tag_m.end():]
    else:
        notes = f"[thread:{thread_id}] {notes}".strip()
    return register_text[:m.start(2)] + notes + " " + register_text[m.end(2):]


def apply_actions(actions: list[StewardAction], force: bool = False) -> list[dict[str, Any]]:
    applied: list[dict[str, Any]] = []
    promotions = 0
    threads_text = read(THREADS)
    register_text = read(REGISTER)
    state = load_state()

    for action in actions:
        if action.action != "PROMOTE_SEED":
            continue
        if promotions >= MAX_PROMOTIONS_PER_RUN and not force:
            continue
        payload = action.payload
        if f"[id:{payload['id']}]" in register_text or f"## Thread: {payload['name']}" in threads_text:
            continue
        threads_text = add_thread_section(threads_text, payload)
        register_text = add_active_thread_row(register_text, payload)
        register_text = tag_entity(register_text, payload["npc_anchor"], payload["id"])
        promotions += 1
        record = asdict(action)
        record["applied_at"] = date.today().isoformat()
        applied.append(record)

    if applied:
        write(THREADS, threads_text)
        write(REGISTER, register_text)
        state.setdefault("history", []).extend(applied)
        state["last_run_at"] = datetime.now().isoformat(timespec="seconds")
        save_state(state)
    return applied


def repair_generated_threads() -> list[str]:
    """Polish early steward-generated threads after template improvements."""
    threads_text = read(THREADS)
    register_text = read(REGISTER)
    changes: list[str] = []

    old_id = "elowen-s-refectory-experiments"
    new_id = "elowen-refectory-experiments"
    if old_id in threads_text or old_id in register_text:
        threads_text = threads_text.replace(old_id, new_id)
        register_text = register_text.replace(old_id, new_id)
        changes.append("normalized Elowen thread id")

    next_beat = (
        "A precise refectory note appears with one useful experiment for the day, "
        "one measurement Elowen refuses to moralize, and one comfort she insists "
        "must remain part of the binding."
    )
    status = "Elowen has begun translating fuel, health, and longevity research into small practical experiments for bj."

    if "## Thread: Elowen's Refectory Experiments" in threads_text:
        threads_text = re.sub(
            r"(?ms)(## Thread: Elowen's Refectory Experiments.*?\*\*Next beat:\*\*)\s*.*?(\n\n\*\*Last advanced:\*\*)",
            rf"\1 {next_beat}\2",
            threads_text,
            count=1,
        )
        changes.append("polished Elowen next beat")

    register_text = re.sub(
        r"(?m)^(\|\s*Elowen's Refectory Experiments\s*\|\s*Thread\s*\|\s*\d+\s*\|\s*\[id:elowen-refectory-experiments\]\s*Phase:\s*setup\s*—\s*).*?(\s*\|)$",
        rf"\1{status}\2",
        register_text,
        count=1,
    )

    if changes:
        write(THREADS, threads_text)
        write(REGISTER, register_text)
    return changes


def build_report(actions: list[StewardAction], applied: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    counts = Counter(action.action for action in actions)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "actions": [asdict(action) for action in actions],
        "applied": applied or [],
        "summary": dict(counts),
    }


def print_text(report: dict[str, Any]) -> None:
    print("THREAD STEWARD")
    if report["summary"]:
        print("Signals: " + ", ".join(f"{key}={value}" for key, value in sorted(report["summary"].items())))
    else:
        print("Signals: none")
    if report.get("applied"):
        print("")
        print("Applied:")
        for item in report["applied"]:
            print(f"- {item['action']}: {item['name']} — {item['reason']}")
    if report["actions"]:
        print("")
        print("Lifecycle actions:")
        for item in report["actions"]:
            print(f"- {item['action']}: {item['name']}")
            print(f"  {item['reason']}")
    else:
        print("")
        print("No lifecycle action needed.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose and conservatively apply thread lifecycle decisions.")
    parser.add_argument("--apply", action="store_true", help="Apply safe automatic actions, currently seed promotion only.")
    parser.add_argument("--force", action="store_true", help="Ignore promotion cooldown and per-run cap.")
    parser.add_argument("--repair-generated", action="store_true", help="Polish steward-generated thread templates after script upgrades.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    actions = propose_actions(force=args.force)
    applied = apply_actions(actions, force=args.force) if args.apply else []
    repaired = repair_generated_threads() if args.repair_generated else []
    report = build_report(actions, applied)
    if repaired:
        report["repaired"] = repaired
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_text(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

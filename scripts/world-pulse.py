#!/usr/bin/env python3
"""
world-pulse.py — The Academy world changes on its own schedule.

Reads world-register.md for entity Belief levels, detects significant shifts,
and writes narrative events to tick-queue.md. High-priority events are flagged
so the Labyrinth treats them as mandatory session openings rather than ambient texture.

Run: python3 scripts/world-pulse.py
Called by: 4-hour cron (after tick.py, before dispatching to player).
"""
import json
import os
import random
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR    = Path(os.environ.get("ENCHANTIFY_BASE_DIR", Path(__file__).parent.parent))
_SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(_SCRIPT_DIR))
import world_context
try:
    import npc_log as _npc_log
    _HAS_NPC_LOG = True
except ImportError:
    _HAS_NPC_LOG = False
TICK_QUEUE     = BASE_DIR / "memory" / "tick-queue.md"
CACHE_PATH     = BASE_DIR / "config" / "world-pulse-cache.json"
SKILL_ID       = "world-pulse"
QUEST_CAPACITY = 5

random.seed(datetime.now().isoformat())


# ─── Load files ──────────────────────────────────────────────────────────────

def load_text(path: Path) -> str:
    return path.read_text() if path.exists() else ""

def load_cache() -> dict:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text())
        except Exception:
            pass
    return {"last_pulse": None, "entity_states": {}, "pulse_count": 0}

def save_cache(cache: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2, default=str))


# ─── Parse world register ────────────────────────────────────────────────────

def parse_entities(register: str) -> list[dict]:
    """
    Parse entities from world-register.md table rows.
    Handles both pipe-table rows and whisper-register list items.
    """
    entities = []

    # Main table rows: | Name | Type | Belief | Notes |
    for line in register.splitlines():
        if not line.startswith("|") or "---" in line:
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) < 3:
            continue
        name = parts[0]
        if not name or name.lower() in ("entity", "name", "talisman"):
            continue

        belief_m = re.search(r"(\d+)", parts[2]) if len(parts) > 2 else None
        if not belief_m:
            belief_m = re.search(r"(\d+)", parts[1])
        belief   = int(belief_m.group(1)) if belief_m else None
        presence = parts[3] if len(parts) > 3 else parts[2]

        entities.append({"name": name, "belief": belief, "presence": presence.strip()})

    # Whisper register list items: - Name (Type, Belief N) — note
    for m in re.finditer(r"^- (.+?)\s*\(.*?Belief\s+(\d+)\)", register, re.MULTILINE):
        entities.append({
            "name":     m.group(1).strip(),
            "belief":   int(m.group(2)),
            "presence": "Whisper",
        })

    return entities


# ─── Event templates ─────────────────────────────────────────────────────────

FADE_SEEDS = [
    "{name} is slightly less defined than it was — one small detail has gone missing, not vanished, just no longer insisted upon.",
    "The ink that draws {name} is thinning at the edges. Nothing dramatic. Just a softening.",
    "Something in {name} has grown quieter. The Labyrinth is watching it, carefully.",
]

RISE_SEEDS = [
    "{name} has grown more present — specific, weighted, taking up more of the narrative than it did before.",
    "The ink is darker in {name} today. Something there is insisting on itself.",
    "{name} has sharpened. Not in size — in *insistence*. It knows you haven't forgotten it.",
]

CRISIS_SEEDS = [
    "PRIORITY: HIGH — {name} stands at the edge. The Nothing has been quiet here for a long time. If nothing is done this session, a Compass Run will be required to reclaim it.",
    "PRIORITY: HIGH — {name} is almost gone. It exists now as a memory of itself — faint ink on a page that used to be vivid. The Labyrinth cannot hold this indefinitely.",
]

STABLE_SEEDS = [
    "{name} is steady. Quiet but present. The kind of presence you only notice when it's gone.",
    "{name} holds. The Nothing has been near, but hasn't found purchase.",
]

# Night-specific seeds — used when the pulse fires during the 22:00–05:00 block.
# The tone is slower, colder, less witnessed.
NIGHT_FADE_SEEDS = [
    "While the Academy slept, something in {name} went a little quieter — not vanished, just less insisted upon.",
    "The Nothing moves in the hours no one is watching. {name} is slightly thinner than it was at nightfall.",
]

NIGHT_RISE_SEEDS = [
    "Something in {name} strengthened in the night hours. It woke up more certain of itself.",
    "While the corridors were empty, {name} accumulated weight. By morning it will be harder to overlook.",
]

NIGHT_STABLE_SEEDS = [
    "{name} held through the night. The Nothing passed near. It did not stop.",
    "The night was quiet around {name}. Whatever threat was circling didn't find purchase.",
]


def generate_events(entities: list[dict], cache: dict, ctx: dict = None) -> list[dict]:
    events  = []
    states  = cache.setdefault("entity_states", {})
    now_iso = datetime.now().isoformat()
    night   = world_context.is_night(ctx) if ctx else False

    for entity in entities:
        if entity["belief"] is None:
            continue

        name    = entity["name"]
        belief  = entity["belief"]
        prev    = states.get(name, {})
        prev_b  = prev.get("belief")

        # Enrich with NPC location if known
        npc_state = world_context.get_npc_state(name, entity.get("presence", "NPC"), ctx)
        location_note = npc_state.get("note")

        raw_suffix = f" [{location_note}]" if location_note else ""

        # Crisis — entity near erasure (no time of day filter — Nothing doesn't clock out)
        if belief <= 2:
            seed = random.choice(CRISIS_SEEDS).format(name=name)
            events.append({
                "raw":      f"{name}: Belief {belief} (critical){raw_suffix}",
                "seed":     seed,
                "priority": "HIGH",
            })

        # Significant drop since last pulse
        elif prev_b is not None and belief <= prev_b - 4:
            seeds = NIGHT_FADE_SEEDS if night else FADE_SEEDS
            seed  = random.choice(seeds).format(name=name)
            events.append({
                "raw":      f"{name}: Belief dropped {prev_b} → {belief}{raw_suffix}",
                "seed":     seed,
                "priority": "NORMAL",
            })
            if _HAS_NPC_LOG:
                _npc_log.append(name, "belief_fell", f"Belief fell {prev_b} → {belief}")

        # Significant rise since last pulse
        elif prev_b is not None and belief >= prev_b + 4:
            seeds = NIGHT_RISE_SEEDS if night else RISE_SEEDS
            seed  = random.choice(seeds).format(name=name)
            events.append({
                "raw":      f"{name}: Belief rose {prev_b} → {belief}{raw_suffix}",
                "seed":     seed,
                "priority": "NORMAL",
            })

        # Ambient pulse (10% chance per entity, max one per run)
        elif not events and random.random() < 0.10:
            seeds = NIGHT_STABLE_SEEDS if night else STABLE_SEEDS
            seed  = random.choice(seeds).format(name=name)
            events.append({
                "raw":      f"{name}: Belief {belief} (ambient pulse){raw_suffix}",
                "seed":     seed,
                "priority": "AMBIENT",
            })

        # Update cache
        states[name] = {
            "belief":   belief,
            "presence": entity["presence"],
            "seen":     now_iso,
        }

    # Cap output — don't flood the queue
    high    = [e for e in events if e["priority"] == "HIGH"]
    normal  = [e for e in events if e["priority"] == "NORMAL"]
    ambient = [e for e in events if e["priority"] == "AMBIENT"]

    # Always include high-priority; fill up to 3 total
    result = high[:2] + normal[:max(0, 2 - len(high))] + ambient[:max(0, 1 - len(high) - len(normal))]
    return result[:3]


# ─── Write to tick-queue ──────────────────────────────────────────────────────

def write_to_queue(events: list[dict], ctx: dict = None) -> None:
    if not events:
        print(f"[{SKILL_ID}] No world events this pulse.")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    tag       = world_context.time_tag(ctx) if ctx else ""
    prefix    = world_context.time_seed_prefix(ctx) if ctx else ""

    TICK_QUEUE.parent.mkdir(parents=True, exist_ok=True)

    if not TICK_QUEUE.exists():
        TICK_QUEUE.write_text(
            "# Tick Queue\n\n"
            "*Populated by skill-lore, tick.py, and world-pulse.py. Read at session open.*\n\n---\n"
        )

    with TICK_QUEUE.open("a") as f:
        for event in events:
            priority_tag = f" [PRIORITY: HIGH]" if event["priority"] == "HIGH" else ""
            header_tag   = f" [{tag}]" if tag else ""
            f.write(
                f"\n## [{SKILL_ID}]{priority_tag}{header_tag} {timestamp}\n"
            )
            if prefix:
                f.write(f"*{prefix}*\n")
            f.write(
                f"*Raw: {event['raw']}*\n"
                f"Narrative seed: {event['seed']}\n"
            )

    high_count = sum(1 for e in events if e["priority"] == "HIGH")
    print(f"[{SKILL_ID}] Wrote {len(events)} event(s) ({high_count} high-priority).")


# ─── Quest count ─────────────────────────────────────────────────────────────

def get_quest_count(player: str = "bj") -> int:
    """Count active quests in the player's Inside Cover table."""
    player_file = BASE_DIR / "players" / f"{player}.md"
    if not player_file.exists():
        return 0
    content = player_file.read_text()
    # Find the Inside Cover table header
    header = re.search(
        r'\| Quest \| NPC \| Belief \| Relationship \|\n\|[-| ]+\|\n',
        content, re.MULTILINE
    )
    if not header:
        return 0
    body_start = header.end()
    next_section = re.search(r'\n## ', content[body_start:])
    body_end = body_start + next_section.start() if next_section else len(content)
    table_body = content[body_start:body_end]
    count = 0
    for line in table_body.splitlines():
        if not line.startswith('|'):
            continue
        if '---|' in line or '---' == line.strip('| '):
            continue
        parts = [p.strip() for p in line.split('|')[1:-1]]
        non_empty = [p for p in parts if p and '*(empty' not in p]
        if len(non_empty) >= 2:
            count += 1
    return count


def write_quest_slots(player: str = "bj") -> None:
    """Append QUEST_SLOTS directive to tick-queue so the simulation agent knows the cap."""
    count = get_quest_count(player)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    TICK_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    if not TICK_QUEUE.exists():
        TICK_QUEUE.write_text(
            "# Tick Queue\n\n"
            "*Populated by skill-lore, tick.py, and world-pulse.py. Read at session open.*\n\n---\n"
        )
    with TICK_QUEUE.open("a") as f:
        f.write(
            f"\n## [quest-slots] {timestamp}\n"
            f"QUEST_SLOTS: {count}/{QUEST_CAPACITY}"
            + (" — cap reached; skip elective generation" if count >= QUEST_CAPACITY else "") + "\n"
        )
    print(f"[{SKILL_ID}] QUEST_SLOTS: {count}/{QUEST_CAPACITY}")


# ─── Main ────────────────────────────────────────────────────────────────────

def maybe_trigger_npc_research(pulse_count: int) -> None:
    """
    Probabilistically trigger NPC research during the simulation phase.
    ~25% chance per pulse run → fires roughly once per day on a 4-hour cron.
    Skipped on the very first pulse (world is just waking up).
    """
    if pulse_count < 2:
        return
    if random.random() > 0.25:
        return
    research_script = BASE_DIR / "scripts" / "npc-research.py"
    if not research_script.exists():
        return
    print(f"[{SKILL_ID}] Triggering NPC research…")
    result = subprocess.run(
        [sys.executable, str(research_script)],
        capture_output=True, text=True
    )
    if result.stdout:
        for line in result.stdout.strip().splitlines():
            print(f"  {line}")
    if result.returncode != 0 and result.stderr:
        print(f"  ⚠ npc-research error: {result.stderr.strip()[:120]}")


if __name__ == "__main__":
    try:
        register = load_text(BASE_DIR / "lore" / "world-register.md")
        cache    = load_cache()
        ctx      = world_context.get_time_context()

        entities = parse_entities(register)
        events   = generate_events(entities, cache, ctx)

        write_to_queue(events, ctx)
        write_quest_slots()

        cache["last_pulse"]  = datetime.now().isoformat()
        cache["pulse_count"] = cache.get("pulse_count", 0) + 1
        save_cache(cache)

        print(f"[{SKILL_ID}] Pulse #{cache['pulse_count']} complete. {len(entities)} entities tracked.")

        maybe_trigger_npc_research(cache["pulse_count"])

    except Exception as e:
        print(f"[{SKILL_ID}] Error: {e}", file=sys.stderr)
        sys.exit(0)

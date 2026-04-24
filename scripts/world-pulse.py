#!/usr/bin/env python3
"""
world-pulse.py — The Academy world changes on its own schedule.

Reads world-register.md for entity Belief levels, detects significant shifts,
and writes narrative events to tick-queue.md. High-priority events are flagged
so the Labyrinth treats them as mandatory session openings rather than ambient texture.

AUTO-ADVANCES: Parses tick-queue.md for [Beat: ...] and [THREAD ESCALATION: ...].
Calls the local OpenClaw gateway in the background to generate immediate narrative 
consequences, actively rewriting lore/threads.md and lore/world-register.md 
while the player is away.

Run: python3 scripts/world-pulse.py
Called by: 3-hour cron (after tick.py, before dispatching to player).
"""
import json
import os
import random
import re
import subprocess
import sys
import time
import uuid
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

BASE_DIR    = Path(os.environ.get("ENCHANTIFY_BASE_DIR", Path(__file__).parent.parent))
_SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(_SCRIPT_DIR))
import world_context
from tick_queue_utils import ensure_header, prune_tick_queue
from thread_sync import sync_thread_files
try:
    import npc_log as _npc_log
    _HAS_NPC_LOG = True
except ImportError:
    _HAS_NPC_LOG = False
try:
    import narrative_sim
    _HAS_NARRATIVE_SIM = True
except ImportError:
    _HAS_NARRATIVE_SIM = False
TICK_QUEUE     = BASE_DIR / "memory" / "tick-queue.md"
THREADS_MD     = BASE_DIR / "lore" / "threads.md"
REGISTER_MD    = BASE_DIR / "lore" / "world-register.md"
SIM_LOG_DIR    = BASE_DIR / "logs" / "simulations"
QUEUE_HEADER = (
    "# Tick Queue\n\n"
    "*Populated by skill-lore, tick.py, and world-pulse.py. Read at session open.*\n\n---\n"
)
CACHE_PATH     = BASE_DIR / "config" / "world-pulse-cache.json"
SKILL_ID       = "world-pulse"
QUEST_CAPACITY = 5
ALLOW_AUTONOMOUS_THREAD_WRITES = os.environ.get("ENCHANTIFY_ALLOW_AUTONOMOUS_THREAD_WRITES", "").lower() in {"1", "true", "yes", "on"}

random.seed(datetime.now().isoformat())

ARC_PHASE_ORDER = ["SETUP", "RISING", "CLIMAX", "FALLING", "RESOLUTION"]


# ─── Load files ──────────────────────────────────────────────────────────────

def load_text(path: Path) -> str:
    return path.read_text() if path.exists() else ""


def normalize_arc_phase(label: str) -> str:
    label = (label or "").strip().upper().rstrip(",")
    return label if label in ARC_PHASE_ORDER else "SETUP"

def load_cache() -> dict:
    if CACHE_PATH.exists():
        try:
            cache = json.loads(CACHE_PATH.read_text())
            cache.setdefault("classifieds", {})
            cache["classifieds"].setdefault("seen", {})
            return cache
        except Exception:
            pass
    return {"last_pulse": None, "entity_states": {}, "pulse_count": 0, "classifieds": {"seen": {}}}

def save_cache(cache: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2, default=str))


# ─── Parse world register ────────────────────────────────────────────────────

def parse_entities(register: str) -> list[dict]:
    entities =[]
    for line in register.splitlines():
        if not line.startswith("|") or "---" in line:
            continue
        parts =[p.strip() for p in line.strip("|").split("|")]
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

    for m in re.finditer(r"^- (.+?)\s*\(.*?Belief\s+(\d+)\)", register, re.MULTILINE):
        entities.append({
            "name":     m.group(1).strip(),
            "belief":   int(m.group(2)),
            "presence": "Whisper",
        })

    return entities


# ─── Event templates ─────────────────────────────────────────────────────────

FADE_SEEDS =[
    "{name} is slightly less defined than it was — one small detail has gone missing, not vanished, just no longer insisted upon.",
    "The ink that draws {name} is thinning at the edges. Nothing dramatic. Just a softening.",
    "Something in {name} has grown quieter. The Labyrinth is watching it, carefully.",
]

RISE_SEEDS =[
    "{name} has grown more present — specific, weighted, taking up more of the narrative than it did before.",
    "The ink is darker in {name} today. Something there is insisting on itself.",
    "{name} has sharpened. Not in size — in *insistence*. It knows you haven't forgotten it.",
]

CRISIS_SEEDS =[
    "PRIORITY: HIGH — {name} stands at the edge. The Nothing has been quiet here for a long time. If nothing is done this session, a Compass Run will be required to reclaim it.",
    "PRIORITY: HIGH — {name} is almost gone. It exists now as a memory of itself — faint ink on a page that used to be vivid. The Labyrinth cannot hold this indefinitely.",
]

STABLE_SEEDS =[
    "{name} is steady. Quiet but present. The kind of presence you only notice when it's gone.",
    "{name} holds. The Nothing has been near, but hasn't found purchase.",
]

NIGHT_FADE_SEEDS =[
    "While the Academy slept, something in {name} went a little quieter — not vanished, just less insisted upon.",
    "The Nothing moves in the hours no one is watching. {name} is slightly thinner than it was at nightfall.",
]

NIGHT_RISE_SEEDS =[
    "Something in {name} strengthened in the night hours. It woke up more certain of itself.",
    "While the corridors were empty, {name} accumulated weight. By morning it will be harder to overlook.",
]

NIGHT_STABLE_SEEDS =[
    "{name} held through the night. The Nothing passed near. It did not stop.",
    "The night was quiet around {name}. Whatever threat was circling didn't find purchase.",
]

def generate_events(entities: list[dict], cache: dict, ctx: dict = None) -> list[dict]:
    events  =[]
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

        npc_state = world_context.get_npc_state(name, entity.get("presence", "NPC"), ctx)
        location_note = npc_state.get("note")
        raw_suffix = f" [{location_note}]" if location_note else ""

        if belief <= 2:
            seed = random.choice(CRISIS_SEEDS).format(name=name)
            events.append({"raw": f"{name}: Belief {belief} (critical){raw_suffix}", "seed": seed, "priority": "HIGH"})
        elif prev_b is not None and belief <= prev_b - 4:
            seed  = random.choice(NIGHT_FADE_SEEDS if night else FADE_SEEDS).format(name=name)
            events.append({"raw": f"{name}: Belief dropped {prev_b} → {belief}{raw_suffix}", "seed": seed, "priority": "NORMAL"})
            if _HAS_NPC_LOG:
                _npc_log.append(name, "belief_fell", f"Belief fell {prev_b} → {belief}")
        elif prev_b is not None and belief >= prev_b + 4:
            seed  = random.choice(NIGHT_RISE_SEEDS if night else RISE_SEEDS).format(name=name)
            events.append({"raw": f"{name}: Belief rose {prev_b} → {belief}{raw_suffix}", "seed": seed, "priority": "NORMAL"})
        elif not events and random.random() < 0.10:
            seed  = random.choice(NIGHT_STABLE_SEEDS if night else STABLE_SEEDS).format(name=name)
            events.append({"raw": f"{name}: Belief {belief} (ambient pulse){raw_suffix}", "seed": seed, "priority": "AMBIENT"})

        states[name] = {"belief": belief, "presence": entity["presence"], "seen": now_iso}

    high    =[e for e in events if e["priority"] == "HIGH"]
    normal  =[e for e in events if e["priority"] == "NORMAL"]
    ambient =[e for e in events if e["priority"] == "AMBIENT"]

    result = high[:2] + normal[:max(0, 2 - len(high))] + ambient[:max(0, 1 - len(high) - len(normal))]
    return result[:3]


def generate_classifieds_events(cache: dict, limit: int = 2) -> list[dict]:
    ledger_dir = BASE_DIR / "logs" / "classifieds-ledger"
    if not ledger_dir.exists():
        return []

    files = sorted(ledger_dir.glob("*.json"))
    if not files:
        return []

    try:
        data = json.loads(files[-1].read_text())
    except Exception:
        return []

    pulse_count = cache.get("pulse_count", 0)
    seen = cache.setdefault("classifieds", {}).setdefault("seen", {})

    label_priority = {
        "WARNING": ("HIGH", 5),
        "NOTICE": ("NORMAL", 4),
        "SEEKING": ("NORMAL", 3),
        "LOST": ("NORMAL", 3),
        "FOUND": ("AMBIENT", 2),
        "REWARD": ("AMBIENT", 2),
    }
    cooldown_by_priority = {
        "HIGH": 3,
        "NORMAL": 4,
        "AMBIENT": 6,
    }

    candidates = []
    open_keys = set()
    for entry in data.get("entries", []):
        if entry.get("status") != "open":
            continue
        label = (entry.get("label") or "NOTICE").upper()
        text = (entry.get("text") or "").strip()
        if not text:
            continue

        entry_key = f"{label}:{text[:160]}"
        open_keys.add(entry_key)
        priority, weight = label_priority.get(label, ("NORMAL", 1))
        last_seen = seen.get(entry_key, {}).get("pulse")
        cooldown = cooldown_by_priority.get(priority, 4)
        if last_seen is not None and (pulse_count - last_seen) < cooldown:
            continue

        seed_prefix = "A notice refuses to stay backgrounded" if priority == "HIGH" else "Something posted in the margins is beginning to act like a story"
        candidates.append({
            "key": entry_key,
            "weight": weight,
            "priority": priority,
            "raw": f"Classified {label}: {text[:120]}",
            "seed": f"{seed_prefix} — {truncate_text(text, 180)}",
        })

    stale_keys = [k for k in seen.keys() if k not in open_keys]
    for k in stale_keys:
        seen.pop(k, None)

    candidates.sort(key=lambda item: item["weight"], reverse=True)
    chosen = candidates[:limit]
    for item in chosen:
        seen[item["key"]] = {"pulse": pulse_count, "priority": item["priority"]}

    return [{k: v for k, v in item.items() if k not in {"weight", "key"}} for item in chosen]


# ─── Autonomous LLM Generation via OpenClaw ──────────────────────────────────

def load_openclaw_config():
    config_path = Path.home() / ".openclaw" / "openclaw.json"
    if not config_path.exists():
        return None
    try:
        return json.loads(config_path.read_text())
    except Exception as e:
        print(f"[{SKILL_ID}] Failed to parse OpenClaw config: {e}")
        return None

def generate_consequence_via_llm(thread_name: str, thread_body: str, occurred_beat: str, retries: int = 3):
    config = load_openclaw_config()
    if not config:
        print(f"[{SKILL_ID}] OpenClaw config not found. Skipping autonomous generation.")
        return None, None

    port = config.get("gateway", {}).get("port", 18789)
    token = config.get("gateway", {}).get("auth", {}).get("token", "")
    model = "openclaw/enchantify"
    url = f"http://127.0.0.1:{port}/v1/chat/completions"

    system_prompt = "You are an automated GM for a solo RPG. You MUST return ONLY a valid JSON object. Do NOT use <think> or <thinking> blocks. Do NOT output markdown formatting. Output raw JSON starting with '{'."
    user_prompt = f"""A background simulation just triggered a story beat for the thread '{thread_name}'. 

THREAD CONTEXT (Current state of the story):
{thread_body}

THE BEAT THAT JUST HAPPENED:
{occurred_beat}

Determine the immediate consequence of this action. What happens next?
Respond ONLY with a JSON object in this exact format:
{{
    "next_beat": "1 to 2 sentences describing the next logical action or consequence. Make it actionable.",
    "register_note": "A short, 5-10 word summary of the current status."
}}"""

    payload = {
        "model": model,
        "messages":[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 800,
        "stream": False,
        "response_format": {"type": "json_object"}
    }

    # THE CRITICAL FIX: Session Isolation Header
    # OpenClaw will treat this request as an isolated, blank session. 
    # It will NOT load your massive chat history or slow tools.
    safe_thread_slug = re.sub(r'[^a-zA-Z0-9]', '', thread_name).lower()
    session_key = f"sim-{safe_thread_slug}-{int(time.time())}"

    req = urllib.request.Request(
        url,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "x-openclaw-session-key": session_key
        },
        data=json.dumps(payload).encode("utf-8")
    )

    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=180) as response:
                raw_text = response.read().decode("utf-8")
                
                if not raw_text.strip():
                    print(f"[{SKILL_ID}] Attempt {attempt}: HTTP response was empty.")
                    time.sleep(5)
                    continue
                    
                result = json.loads(raw_text)
                
                # Extract content safely
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                if content is None:
                    content = ""
                content = content.strip()
                
                # Check for OpenClaw's specific failure strings
                if not content or "No response from OpenClaw" in content or "No reply from agent" in content:
                    print(f"[{SKILL_ID}] Attempt {attempt}: OpenClaw agent dropped the output (likely rate limit or thinking block). Retrying...")
                    time.sleep(8)
                    continue
                
                # Strip Markdown wrappers if the LLM sneaks them in
                if content.startswith("```json"):
                    content = content[7:-3].strip()
                elif content.startswith("```"):
                    content = content[3:-3].strip()
                
                try:
                    data = json.loads(content)
                    if "next_beat" in data and "register_note" in data:
                        return data["next_beat"], data["register_note"]
                    else:
                        print(f"[{SKILL_ID}] Attempt {attempt}: JSON missing required keys.")
                        time.sleep(5)
                        continue
                except json.JSONDecodeError:
                    print(f"[{SKILL_ID}] Attempt {attempt}: Failed to parse JSON. Content was:\n{content}")
                    time.sleep(5)
                    continue

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            print(f"[{SKILL_ID}] Attempt {attempt} failed (HTTP {e.code}): {error_body}")
            time.sleep(5)
            continue
        except Exception as e:
            print(f"[{SKILL_ID}] Attempt {attempt} failed: {e}")
            time.sleep(5)
            continue

    print(f"[{SKILL_ID}] Exhausted all {retries} retries for {thread_name}.")
    return None, None


# ─── Auto-Advance Threads ────────────────────────────────────────────────────

def process_simulation_beats(events: list) -> None:
    if not TICK_QUEUE.exists():
        return
    if not ALLOW_AUTONOMOUS_THREAD_WRITES:
        print(f"[{SKILL_ID}] Autonomous thread rewriting disabled (set ENCHANTIFY_ALLOW_AUTONOMOUS_THREAD_WRITES=1 to enable).")
        return
    
    threads_path = BASE_DIR / "lore" / "threads.md"
    register_path = BASE_DIR / "lore" / "world-register.md"

    if not threads_path.exists():
        return

    queue_text = TICK_QUEUE.read_text()
    threads_text = threads_path.read_text()
    register_text = register_path.read_text() if register_path.exists() else ""

    threads_updated = False
    register_updated = False
    queue_updated = False
    today_str = datetime.now().strftime("%Y-%m-%d")

    # 1. Process Narrative Beats
    beats = set(re.findall(r'-\s+\*\*\[Beat:\s+([^\]]+)\]\*\*', queue_text))
    
    for thread_name in beats:
        pattern = re.compile(
            rf'(## Thread:\s+{re.escape(thread_name)}.*?Next beat:\s*)([^\n]+)(.*?Last advanced:\s*)([^\n]*)',
            re.DOTALL | re.IGNORECASE
        )
        match = pattern.search(threads_text)
        if match:
            thread_body = match.group(0)
            occurred_beat = match.group(2).strip()
            
            # Prevent infinite processing loops
            if occurred_beat and not occurred_beat.startswith("*(Simulation"):
                print(f"[{SKILL_ID}] Generating consequence for {thread_name} via OpenClaw...")
                new_beat, new_note = generate_consequence_via_llm(thread_name, thread_body, occurred_beat)
                
                if new_beat and new_note:
                    events.append({
                        "raw": f"{thread_name} (Simulation Beat)",
                        "seed": f"While you were away, the simulation advanced: {occurred_beat}",
                        "priority": "HIGH"
                    })

                    sync_result = sync_thread_files(
                        thread_name,
                        status=new_note,
                        next_beat=new_beat,
                        last_advanced=today_str,
                    )
                    threads_text = sync_result.get("threads_text", threads_text)
                    register_text = sync_result.get("register_text", register_text)
                    threads_updated = threads_updated or sync_result.get("threads_changed", False)
                    register_updated = register_updated or sync_result.get("register_changed", False)
                    if sync_result.get("threads_changed") or sync_result.get("register_changed"):
                        print(f"[{SKILL_ID}] Successfully generated and saved consequences for {thread_name}.")
                    
                    # Consume the beat in the queue so we don't process it again in 3 hours!
                    queue_text = re.sub(
                        rf'-\s+\*\*\[Beat:\s+{re.escape(thread_name)}\]\*\*',
                        f'- **[Auto-Advanced: {thread_name}]**',
                        queue_text
                    )
                    queue_updated = True

                else:
                    print(f"[{SKILL_ID}] Skipped updating {thread_name} due to generation failure.")
                
                # Polite API Backoff: Sleep 10 seconds between successful requests
                time.sleep(10)

    # 2. Process Phase Escalations
    escalations = set(re.findall(
        r'-\s+\*\*\[THREAD (?:ESCALATION|COOLING):\s+([^\]]+)\]\*\*\s+Belief\s+\d+\s+(?:places this thread|has dropped below)[^\`]+`([^`]+)`',
        queue_text
    ))
    for thread_name, new_phase in escalations:
        sync_result = sync_thread_files(thread_name, phase=new_phase)
        if sync_result.get("threads_changed") or sync_result.get("register_changed"):
            threads_text = sync_result.get("threads_text", threads_text)
            register_text = sync_result.get("register_text", register_text)
            threads_updated = threads_updated or sync_result.get("threads_changed", False)
            register_updated = register_updated or sync_result.get("register_changed", False)

            events.append({
                "raw": f"{thread_name} (Phase Shift)",
                "seed": f"The narrative mass has tipped. {thread_name} has shifted to the '{new_phase}' phase.",
                "priority": "HIGH"
            })
        
        # Consume the escalation in the queue so it doesn't fire again
        queue_text = re.sub(
            rf'-\s+\*\*\[THREAD (ESCALATION|COOLING):\s+{re.escape(thread_name)}\]\*\*',
            f'- **[Processed \\1: {thread_name}]**',
            queue_text
        )
        queue_updated = True

    # Save to disk
    if queue_updated:
        TICK_QUEUE.write_text(queue_text)

    if threads_updated:
        threads_path.write_text(threads_text)
        print(f"[{SKILL_ID}] Updated lore/threads.md with new autonomous beats.")

    if register_updated:
        register_path.write_text(register_text)
        print(f"[{SKILL_ID}] Updated lore/world-register.md with new thread notes.")


def parse_thread_rows(register_text: str) -> list[dict]:
    rows = []
    active_m = re.search(r'(?m)^## Active Threads\s*\n(.*?)(?=^## |\Z)', register_text, re.DOTALL)
    if not active_m:
        return rows
    for m in re.finditer(r'^\|\s*([^|]+?)\s*\|\s*Thread\s*\|\s*(\d+)\s*\|\s*([^|]*)\|', active_m.group(1), re.MULTILINE | re.IGNORECASE):
        name = m.group(1).strip()
        belief = int(m.group(2))
        notes = m.group(3).strip()
        phase_m = re.search(r'Phase:\s*(\w+)', notes, re.IGNORECASE)
        rows.append({
            "name": name,
            "belief": belief,
            "notes": notes,
            "phase": phase_m.group(1).lower() if phase_m else "dormant",
        })
    return rows


def compute_arc_readiness(register_text: str) -> dict:
    threads = parse_thread_rows(register_text)
    active_threads = [t for t in threads if t['phase'] != 'permanent']
    rising = sum(1 for t in active_threads if t['phase'] == 'rising')
    climax = sum(1 for t in active_threads if t['phase'] == 'climax')
    resolution = sum(1 for t in active_threads if t['phase'] == 'resolution')
    total_belief = sum(t['belief'] for t in active_threads)
    hottest = max(active_threads, key=lambda t: t['belief'], default=None)

    target = None
    reason = None
    if climax >= 1 and total_belief >= 45:
        target = "CLIMAX"
        reason = "at least one live thread has reached climax pressure"
    elif rising >= 2 and total_belief >= 30:
        target = "RISING"
        reason = "multiple threads are rising together"
    elif resolution >= max(1, len(active_threads)) and active_threads:
        target = "RESOLUTION"
        reason = "all active threads have moved into resolution pressure"

    return {
        "threads": active_threads,
        "target": target,
        "reason": reason,
        "total_belief": total_belief,
        "hottest": hottest,
    }


def maybe_auto_advance_arc(events: list) -> None:
    arc_path = BASE_DIR / "lore" / "current-arc.md"
    register_path = BASE_DIR / "lore" / "world-register.md"
    if not arc_path.exists() or not register_path.exists():
        return

    arc_text = arc_path.read_text()
    register_text = register_path.read_text()
    phase_m = re.search(r'^## Phase:\s*(\w+)', arc_text, re.MULTILINE)
    if not phase_m:
        return
    current_phase = normalize_arc_phase(phase_m.group(1))
    if current_phase in ("FALLING", "RESOLUTION"):
        return

    readiness = compute_arc_readiness(register_text)
    target = readiness.get("target")
    if not target:
        return
    if ARC_PHASE_ORDER.index(target) <= ARC_PHASE_ORDER.index(current_phase):
        return

    new_text = re.sub(r'^(## Phase:\s*)\w+', rf'\g<1>{target}', arc_text, flags=re.MULTILINE)
    arc_path.write_text(new_text)

    hottest = readiness.get("hottest")
    hottest_name = hottest['name'] if hottest else "the active threads"
    events.append({
        "raw": f"Arc auto-advance {current_phase} → {target}",
        "seed": f"The current arc tipped from {current_phase} into {target.lower()} because {readiness['reason']}. The hottest pressure came from {hottest_name}.",
        "priority": "HIGH"
    })
    print(f"[{SKILL_ID}] Auto-advanced arc {current_phase} → {target} from live thread pressure.")


def _append_simulation_ledger(entries: list[dict]) -> None:
    if not entries:
        return
    SIM_LOG_DIR.mkdir(parents=True, exist_ok=True)
    day = datetime.now().strftime("%Y-%m-%d")
    out = SIM_LOG_DIR / f"{day}.jsonl"
    with out.open("a", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")



def run_living_world_simulation(events: list, ctx: Optional[dict] = None) -> None:
    if not _HAS_NARRATIVE_SIM:
        return
    if not REGISTER_MD.exists() or not THREADS_MD.exists():
        return

    try:
        register_text = REGISTER_MD.read_text()
        state = narrative_sim.load_state()
        actions = narrative_sim.simulate_world_pulse(
            register_text,
            THREADS_MD.read_text(),
            state=state,
        )
        if not actions:
            return

        updated_register, applied = narrative_sim.apply_simulation_consequences(register_text, actions)
        if updated_register != register_text:
            REGISTER_MD.write_text(updated_register)

        now = datetime.now()
        trigger = "scene-change" if ctx and ctx.get("scene_change") else "scheduled"
        time_tag = world_context.time_tag(ctx) if ctx else ""
        time_seed = world_context.time_seed_prefix(ctx) if ctx else ""
        ledger_entries: list[dict] = []

        for action in actions:
            raw = f"{action.npc} [{action.action}/{action.intensity}] on {action.thread_name}"
            if action.target:
                raw += f" → {action.target}"
            if action.influence_snapshot:
                raw += f" | pressure: {', '.join(action.influence_snapshot)}"
            seed = action.visible_trace + f" Offscreen reason: {action.reason}."
            event_id = str(uuid.uuid4())
            events.append({
                "raw": raw,
                "seed": seed,
                "priority": action.priority,
            })
            ledger_entries.append({
                "id": event_id,
                "timestamp": now.isoformat(),
                "source": SKILL_ID,
                "kind": "action",
                "trigger": trigger,
                "time_tag": time_tag,
                "time_seed": time_seed,
                "actor": action.npc,
                "actor_kind": action.actor_kind,
                "chapter": action.chapter,
                "action": action.action,
                "intensity": action.intensity,
                "thread_name": action.thread_name,
                "thread_id": action.thread_id,
                "target": action.target,
                "priority": action.priority,
                "raw": raw,
                "narrative": action.visible_trace,
                "reason": action.reason,
                "hidden_effect": action.hidden_effect,
                "belief_delta_hint": action.belief_delta_hint,
                "influence_snapshot": action.influence_snapshot,
            })
            if _HAS_NPC_LOG:
                _npc_log.append(action.npc, action.action, f"{action.thread_name}: {action.hidden_effect}")

        for item in applied:
            raw = f"Simulation consequence: {item.name} {item.before} → {item.after}"
            seed = f"{item.name} shifted by {item.delta:+d}. {item.reason}."
            event_id = str(uuid.uuid4())
            events.append({
                "raw": raw,
                "seed": seed,
                "priority": "NORMAL",
            })
            ledger_entries.append({
                "id": event_id,
                "timestamp": now.isoformat(),
                "source": SKILL_ID,
                "kind": "consequence",
                "trigger": trigger,
                "time_tag": time_tag,
                "time_seed": time_seed,
                "name": item.name,
                "entity_kind": item.kind,
                "delta": item.delta,
                "before": item.before,
                "after": item.after,
                "priority": "NORMAL",
                "raw": raw,
                "narrative": seed,
                "reason": item.reason,
            })
            if _HAS_NPC_LOG:
                _npc_log.append(item.name, "belief_shift", f"{item.before} → {item.after} ({item.reason})")

        updated_state = narrative_sim.record_actions(state, actions)
        for intent in updated_state.get("talisman_intents", []):
            raw = f"Talisman intent: {intent['talisman']} [{intent['suggested_mode']}] on {intent['thread_name']}"
            if intent.get("target"):
                raw += f" → {intent['target']}"
            seed = (
                f"{intent['talisman']} is now pressing toward {intent['suggested_mode']} through {intent['thread_name']}. "
                f"Source action: {intent['action']} ({intent['intensity']}). Reason: {intent['reason']}."
            )
            event_id = str(uuid.uuid4())
            events.append({
                "raw": raw,
                "seed": seed,
                "priority": "NORMAL",
            })
            ledger_entries.append({
                "id": event_id,
                "timestamp": now.isoformat(),
                "source": SKILL_ID,
                "kind": "talisman_intent",
                "trigger": trigger,
                "time_tag": time_tag,
                "time_seed": time_seed,
                "talisman": intent["talisman"],
                "mode": intent["suggested_mode"],
                "thread_name": intent["thread_name"],
                "target": intent.get("target"),
                "priority": "NORMAL",
                "raw": raw,
                "narrative": seed,
                "reason": intent["reason"],
                "source_action": intent["action"],
                "source_intensity": intent["intensity"],
            })

        _append_simulation_ledger(ledger_entries)
        narrative_sim.save_state(updated_state)
        print(f"[{SKILL_ID}] Living-world simulation produced {len(actions)} offscreen action(s), {len(applied)} applied consequence(s), and {len(updated_state.get('talisman_intents', []))} talisman intent(s).")
    except Exception as e:
        print(f"[{SKILL_ID}] Living-world simulation error: {e}")

# ─── Write to tick-queue ──────────────────────────────────────────────────────

def truncate_text(text: str, n: int = 160) -> str:
    text = (text or "").strip()
    return text[:n] + "…" if len(text) > n else text


def write_to_queue(events: list[dict], ctx: dict = None) -> None:
    if not events:
        print(f"[{SKILL_ID}] No world events this pulse.")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    tag       = world_context.time_tag(ctx) if ctx else ""
    prefix    = world_context.time_seed_prefix(ctx) if ctx else ""

    ensure_header(TICK_QUEUE, QUEUE_HEADER)

    with TICK_QUEUE.open("a") as f:
        for event in events:
            priority_tag = f" [PRIORITY: HIGH]" if event["priority"] == "HIGH" else ""
            header_tag   = f" [{tag}]" if tag else ""
            f.write(f"\n## [{SKILL_ID}]{priority_tag}{header_tag} {timestamp}\n")
            if prefix:
                f.write(f"*{prefix}*\n")
            f.write(
                f"*Raw: {event['raw']}*\n"
                f"Narrative seed: {event['seed']}\n"
            )

    prune_tick_queue(TICK_QUEUE, QUEUE_HEADER)

    high_count = sum(1 for e in events if e["priority"] == "HIGH")
    print(f"[{SKILL_ID}] Wrote {len(events)} event(s) ({high_count} high-priority).")


# ─── Quest count ─────────────────────────────────────────────────────────────

def get_quest_count(player: str = "bj") -> int:
    player_file = BASE_DIR / "players" / f"{player}.md"
    if not player_file.exists(): return 0
    content = player_file.read_text()
    header = re.search(r'\| Quest \| NPC \| Belief \| Relationship \|\n\|[-| ]+\|\n', content, re.MULTILINE)
    if not header: return 0
    body_start = header.end()
    next_section = re.search(r'\n## ', content[body_start:])
    body_end = body_start + next_section.start() if next_section else len(content)
    table_body = content[body_start:body_end]
    count = 0
    for line in table_body.splitlines():
        if not line.startswith('|') or '---|' in line or '---' == line.strip('| '): continue
        parts =[p.strip() for p in line.split('|')[1:-1]]
        if len([p for p in parts if p and '*(empty' not in p]) >= 2: count += 1
    return count

def write_quest_slots(player: str = "bj") -> None:
    count = get_quest_count(player)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    TICK_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    with TICK_QUEUE.open("a") as f:
        f.write(
            f"\n## [quest-slots] {timestamp}\n"
            f"QUEST_SLOTS: {count}/{QUEST_CAPACITY}"
            + (" — cap reached; skip elective generation" if count >= QUEST_CAPACITY else "") + "\n"
        )
    print(f"[{SKILL_ID}] QUEST_SLOTS: {count}/{QUEST_CAPACITY}")


# ─── Main ────────────────────────────────────────────────────────────────────

def maybe_trigger_npc_research(pulse_count: int) -> None:
    if pulse_count < 2 or random.random() > 0.25: return
    research_script = BASE_DIR / "scripts" / "npc-research.py"
    if not research_script.exists(): return
    print(f"[{SKILL_ID}] Triggering NPC research…")
    result = subprocess.run([sys.executable, str(research_script)], capture_output=True, text=True)
    if result.stdout:
        for line in result.stdout.strip().splitlines(): print(f"  {line}")


if __name__ == "__main__":
    try:
        register = load_text(BASE_DIR / "lore" / "world-register.md")
        cache    = load_cache()
        ctx      = world_context.get_time_context()

        entities = parse_entities(register)
        events   = generate_events(entities, cache, ctx)
        classifieds = generate_classifieds_events(cache)
        if events:
            events.extend(classifieds[:1])
        else:
            events.extend(classifieds[:2])
        events = sorted(events, key=lambda e: {"HIGH": 0, "NORMAL": 1, "AMBIENT": 2}.get(e.get("priority", "NORMAL"), 1))[:5]
        
        # ACTIVE SIMULATION INTERVENTION
        run_living_world_simulation(events, ctx)
        process_simulation_beats(events)
        maybe_auto_advance_arc(events)

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

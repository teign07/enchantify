#!/usr/bin/env python3
"""
npc-research.py — NPCs research topics from the Unwritten Chapter.

During the simulation phase, an eligible NPC selects a topic from their
Unwritten Interest or world-register presence, writes a research note in their
voice using the OpenClaw gateway, and delivers it to the player.

Eligibility: NPC must be in world-register with Belief >= 8 and not on cooldown
(72h default). Unwritten Interest and relationship are selection bonuses, not
hard gates; any world-register NPC with enough Belief can get a turn.

Outputs:
  - memory/npc-research/[slug]-[date].md   (always)
  - Physical letter via CUPS printer       (unless --no-print)
  - Telegram via openclaw message send     (always)
  - iCloud Notes via osascript             (always, unless --no-icloud is used)
  - memory/tick-queue.md                   (narrative seed)

Usage:
  python3 scripts/npc-research.py [player] [--dry-run] [--npc "Zara Finch"] [--no-icloud] [--no-print]
"""

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
import textwrap
import unicodedata
import math
from datetime import datetime, timedelta
from pathlib import Path
from tick_queue_utils import ensure_header, prune_tick_queue
from typing import Optional
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).parent))
import cron_steward

SCRIPT_DIR   = Path(__file__).parent
BASE_DIR     = Path(os.environ.get("ENCHANTIFY_BASE_DIR", SCRIPT_DIR.parent))
CACHE_PATH   = BASE_DIR / "config" / "npc-research-cache.json"
RESEARCH_DIR = BASE_DIR / "memory" / "npc-research"
LETTER_DIR   = RESEARCH_DIR / "letters"
LETTER_IMAGES_DIR = RESEARCH_DIR / "letter-images"
TICK_QUEUE   = BASE_DIR / "memory" / "tick-queue.md"
QUEUE_HEADER = "# Tick Queue\n\n*Read at session open, then cleared.*\n"

sys.path.insert(0, str(SCRIPT_DIR))
try:
    import npc_log as _npc_log
    _HAS_NPC_LOG = True
except ImportError:
    _HAS_NPC_LOG = False

BELIEF_COST     = 3
BELIEF_MINIMUM  = 8       # NPC must have at least this much to research
COOLDOWN_HOURS  = 72      # per-NPC cooldown between notes

# Telegram Config - Ensure these match your Openclaw Enchantify Agent settings
TELEGRAM_TARGET  = "8729557865"
TELEGRAM_CHANNEL = "telegram"

# Core cast receives a small selection bonus, but no longer forms a hard
# whitelist. Research should feel like the whole Academy peering through the
# Margin-Glass, not the same few names taking every turn.
CORE_NPCS = {"Zara Finch", "Professor Stonebrook", "Headmistress Thorne", "Boggle", "Dr. Elowen Vellum"}

CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


# ─── Config / API ─────────────────────────────────────────────────────────────

def load_config() -> dict:
    cfg = {}
    config_path = BASE_DIR / "config" / "secrets.env"
    if config_path.exists():
        with open(config_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                cfg[key.strip()] = val.strip().strip('"').strip("'")
    return cfg

def _normalize_gateway_model(model: str) -> str:
    model = (model or "").strip()
    if model == "openclaw" or model.startswith("openclaw/"):
        return model
    return "openclaw"

def _oc_gateway_cfg() -> tuple[int, str, str, int]:
    """Return (port, token, model, timeout) for bounded gateway research."""
    cfg_path = Path.home() / ".openclaw" / "openclaw.json"
    oc_cfg: dict = {}
    if cfg_path.exists():
        try:
            oc_cfg = json.loads(cfg_path.read_text())
        except Exception:
            pass

    secrets = load_config()
    port = oc_cfg.get("gateway", {}).get("port", 18789)
    token = oc_cfg.get("gateway", {}).get("auth", {}).get("token", "")
    raw_model = (
        os.environ.get("NPC_RESEARCH_MODEL")
        or secrets.get("NPC_RESEARCH_MODEL")
        or os.environ.get("BLEED_MODEL")
        or secrets.get("BLEED_MODEL")
        or "openclaw"
    )
    model = _normalize_gateway_model(raw_model)
    timeout_raw = (
        os.environ.get("NPC_RESEARCH_TIMEOUT")
        or secrets.get("NPC_RESEARCH_TIMEOUT")
        or os.environ.get("BLEED_GATEWAY_TIMEOUT")
        or secrets.get("BLEED_GATEWAY_TIMEOUT")
        or "90"
    )
    try:
        timeout = max(15, int(timeout_raw))
    except ValueError:
        timeout = 90
    return port, token, model, timeout

def call_llm(prompt: str) -> str:
    """Run research through the OpenClaw gateway without spawning an agent process."""
    port, token, model, timeout = _oc_gateway_cfg()
    url = f"http://127.0.0.1:{port}/v1/chat/completions"
    session_key = f"npc-research-{int(time.time())}"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You write private in-world NPC research dispatches for a magical academy. "
                    "Use true, grounded real-world facts when possible. Reply only with the "
                    "dispatch text, already in character, with no preamble or commentary."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.75,
        "max_tokens": 1800,
        "stream": False,
    }
    req = urllib.request.Request(
        url,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "x-openclaw-session-key": session_key,
        },
        data=json.dumps(payload).encode("utf-8"),
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"Gateway returned HTTP {e.code}: {body}") from e
    except Exception as e:
        raise RuntimeError(f"Gateway call failed: {e}") from e

    return (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )

def model_smoke_test() -> int:
    port, _token, model, timeout = _oc_gateway_cfg()
    print(f"NPC_RESEARCH_MODEL={model}")
    print(f"NPC_RESEARCH_GATEWAY=127.0.0.1:{port}")
    print(f"NPC_RESEARCH_TIMEOUT={timeout}")
    try:
        reply = call_llm("Reply with exactly: NPC_RESEARCH_OK")
    except Exception as e:
        print(f"FAIL: {e}")
        return 1
    print(reply[:200] or "(empty)")
    return 0 if "NPC_RESEARCH_OK" in reply else 1
    
def get_local_city() -> str:
    """Fetch the computer's current city/region based on IP address."""
    try:
        req = urllib.request.Request(
            "https://ipinfo.io/json",
            headers={"User-Agent": "Enchantify/1.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            city = data.get("city")
            region = data.get("region")
            if city and region:
                return f"{city}, {region}"
            elif city:
                return city
    except Exception as e:
        print(f"  [npc-research] Warning: Could not fetch IP location ({e}).")
    
    return "the player's local area"


# ─── Parse characters.md ──────────────────────────────────────────────────────

def parse_characters() -> list[dict]:
    """
    Extract NPCs with Unwritten Interest and Voice from characters.md.
    """
    path = BASE_DIR / "lore" / "characters.md"
    if not path.exists():
        return[]
    text = path.read_text()
    npcs =[]

    sections = re.split(r"^### ", text, flags=re.MULTILINE)
    for section in sections[1:]:
        name_match = re.match(r"^(.+)", section)
        if not name_match:
            continue
        name = re.split(r"\s+[—–-]\s+", name_match.group(1).strip(), 1)[0].strip()

        interest_m = re.search(r"\*\*Unwritten Interest:\*\*\s*(.*?)(?=\s+\*\*Voice:\*\*|\n|$)", section)
        voice_m    = re.search(r"\*\*Voice:\*\*\s*(.+)", section)

        if interest_m and voice_m:
            npcs.append({
                "name":     name,
                "interest": interest_m.group(1).strip(),
                "voice":    voice_m.group(1).strip(),
            })

    for m in re.finditer(
        r"\*\*([A-Z][^*]+?)\*\*(?:(?:\s*\([^)]*\))|(?:\s*\*[^*]+\*))*\s*[—–-].*?\*\*Unwritten Interest:\*\*\s*(.*?)(?=\s+\*\*Voice:\*\*|\n|$)",
        text,
    ):
        name     = m.group(1).strip()
        interest = m.group(2).strip()
        nearby   = text[m.start():m.start() + 400]
        voice_m  = re.search(r"\*\*Voice:\*\*\s*(.+)", nearby)
        voice    = voice_m.group(1).strip() if voice_m else "Quiet, specific, genuine."
        if not any(n["name"] == name for n in npcs):
            npcs.append({"name": name, "interest": interest, "voice": voice})

    return npcs


def canonical_name(name: str) -> str:
    text = name.lower()
    text = re.sub(r"\([^)]*\)", "", text)
    text = text.replace("prof. ", "professor ")
    text = re.sub(r"^(headmistress|headmaster|professor|dr)\s+", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def character_lookup(characters: list[dict], name: str) -> dict:
    direct = {c["name"].lower(): c for c in characters}
    if name.lower() in direct:
        return direct[name.lower()]
    target = canonical_name(name)
    for c in characters:
        candidate = canonical_name(c["name"])
        if candidate == target:
            return c
        target_parts = target.split()
        candidate_parts = candidate.split()
        if target_parts and candidate_parts and target_parts[-1] == candidate_parts[-1]:
            if set(target_parts).issubset(set(candidate_parts)) or set(candidate_parts).issubset(set(target_parts)):
                return c
    return {}


# ─── Parse world-register.md ─────────────────────────────────────────────────

def parse_register_npcs() -> dict[str, dict]:
    """Return {name: {belief, notes}} for NPC entities in world-register.md."""
    path = BASE_DIR / "lore" / "world-register.md"
    if not path.exists():
        return {}
    text  = path.read_text()
    result = {}

    for line in text.splitlines():
        if not line.startswith("|") or "---" in line:
            continue
        parts =[p.strip() for p in line.strip("|").split("|")]
        if len(parts) < 4:
            continue
        name  = parts[0]
        etype = parts[1].lower()
        
        if not name or name.lower() in ("entity", "name") or ("npc" not in etype and "character" not in etype):
            continue
            
        belief_m = re.search(r"(\d+)", parts[2])
        if belief_m:
            result[name] = {"belief": int(belief_m.group(1)), "notes": parts[3]}

    return result

# ─── Parse player relationships ───────────────────────────────────────────────

def parse_relationships(player: str) -> dict[str, int]:
    """Return {npc_name: score} from the player file's Relationships table."""
    path = BASE_DIR / "players" / f"{player}.md"
    if not path.exists():
        return {}
    text = path.read_text()
    scores = {}
    in_table = False
    for line in text.splitlines():
        if "## Relationships" in line:
            in_table = True
            continue
        if in_table:
            if line.startswith("##"):
                break
            if line.startswith("|") and "---" not in line and "NPC" not in line:
                parts =[p.strip() for p in line.strip("|").split("|")]
                if len(parts) >= 3:
                    name    = parts[0]
                    score_m = re.search(r"(-?\d+)", parts[2])
                    if name and score_m:
                        scores[name] = int(score_m.group(1))
    return scores


# ─── Cooldown cache ───────────────────────────────────────────────────────────

def load_cache() -> dict:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text())
        except Exception:
            pass
    return {}

def save_cache(cache: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2, default=str))

def is_on_cooldown(cache: dict, name: str) -> bool:
    last = cache.get(name)
    if not last:
        return False


def recent_npc_log_counts(days: int = 14) -> dict[str, int]:
    """Return recent research counts by NPC so selection can diversify."""
    path = BASE_DIR / "memory" / "npc-log.md"
    if not path.exists():
        return {}
    cutoff = datetime.now() - timedelta(days=days)
    counts: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("|") or "---" in line or "Date" in line:
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) < 3:
            continue
        try:
            date = datetime.fromisoformat(parts[0])
        except Exception:
            continue
        if date < cutoff or parts[2] != "research":
            continue
        counts[parts[1]] = counts.get(parts[1], 0) + 1
    return counts
    try:
        last_dt = datetime.fromisoformat(last)
        return (datetime.now() - last_dt).total_seconds() < COOLDOWN_HOURS * 3600
    except Exception:
        return False


# ─── NPC selection ────────────────────────────────────────────────────────────

def select_npc(
    characters: list[dict],
    register:   dict[str, dict],
    relationships: dict[str, int],
    cache:      dict,
    forced_name: Optional[str] = None,
) -> Optional[dict]:
    import random

    recent_counts = recent_npc_log_counts()
    eligible =[]
    
    for name, reg in register.items():
        if forced_name and name.lower() != forced_name.lower():
            continue
        if reg["belief"] < BELIEF_MINIMUM:
            continue
        if not forced_name and is_on_cooldown(cache, name):
            continue

        c_info = character_lookup(characters, name)
        interest = c_info.get("interest", f"General real-world research relating to my current situation: {reg['notes']}")
        voice = c_info.get("voice", "In-character, natural, reflecting my academy role.")
        rel_score = relationships.get(name)
        recent_count = recent_counts.get(name, 0)
        has_unwritten_interest = bool(c_info.get("interest"))
        weight = math.sqrt(max(reg["belief"], 1))
        if has_unwritten_interest:
            weight *= 1.35
        if rel_score is not None:
            weight *= 1.0 + max(min(rel_score, 60), -30) / 150
        if name in CORE_NPCS:
            weight *= 1.10
        if recent_count:
            weight /= (1 + recent_count)

        eligible.append({
            "name": name,
            "interest": interest,
            "voice": voice,
            "belief": reg["belief"],
            "notes": reg["notes"],
            "weight": round(weight, 3),
            "has_unwritten_interest": has_unwritten_interest,
            "recent_research_count": recent_count,
        })

    if not eligible:
        return None

    eligible.sort(key=lambda n: n["weight"], reverse=True)
    weights = [max(float(n["weight"]), 0.1) for n in eligible]
    total   = sum(weights)
    r = random.uniform(0, total)
    cumulative = 0
    for npc, w in zip(eligible, weights):
        cumulative += w
        if r <= cumulative:
            return npc
    return eligible[0]


# ─── Heartbeat signals ───────────────────────────────────────────────────────

def load_heartbeat_snippet() -> str:
    path = BASE_DIR / "HEARTBEAT.md"
    if not path.exists():
        return ""
    lines = path.read_text().splitlines()
    snippet =[]
    in_pulse = False
    for line in lines:
        if "PULSE_START" in line:
            in_pulse = True
            continue
        if "PULSE_END" in line:
            break
        if in_pulse and line.strip() and not line.startswith("<!--"):
            snippet.append(line)
            if len(snippet) >= 20:
                break
    return "\n".join(snippet)


# ─── Research generation ──────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are {name}, a character in a magical academy called the Labyrinth of Stories.
You are writing a private research note to send through the Margin-Glass — the
thin membrane between the Academy and the Unwritten Chapter (the real world where
the player, bj, lives).

Your voice: {voice}
Your Unwritten Interest (Real-World Focus): {interest}

RULES FOR YOUR RESEARCH:
1. ACTUAL REAL-WORLD FACTS REQUIRED: This is not just creative writing. You must provide real, verifiable facts, history, or systems from the real world related to your interest. Do not invent facts.
2. THE MAGICAL LENS: Present these real-world facts through your character's perspective. You are an academic from a magical book marveling at the mundane real world.
3. LENGTH: 300 to 500 words. Make it substantial enough to be a genuine research dispatch.
4. Write entirely in your character voice. You are {name}.
5. Ground the note in the provided Margin-Glass signals (weather/time) if applicable.
6. Do NOT break character or use therapeutic/game mechanics language.
7. Sign your full name at the end.
"""

def generate_research(npc: dict, heartbeat: str, city: str) -> str:
    system = SYSTEM_PROMPT.format(
        name=npc["name"],
        voice=npc["voice"],
        interest=npc["interest"],
    )
    user_prompt = (
        f"Current signals from the Margin-Glass (real-world data):\n\n{heartbeat}\n\n"
        f"Player's Current Location (IP Geolocation): {city}\n\n"
        "TASK: Conduct real-world research on your Unwritten Interest. Use your web search capabilities or your deep factual knowledge base to find true, specific facts (e.g., actual stores in the player's location, real websites, true historical events, or scientific facts).\n\n"
        "Write your 300-500 word research dispatch, weaving these absolute real-world facts into your character's magical perspective."
    )
    try:
        research = call_llm(f"{system}\n\n{user_prompt}")
    except Exception as e:
        print(f"  [npc-research] Warning: model research failed ({e}). Using bounded field-note fallback.")
        return build_fallback_research(npc, heartbeat, city)
    if len(research.split()) < 120:
        print("  [npc-research] Warning: model research was too short. Using bounded field-note fallback.")
        return build_fallback_research(npc, heartbeat, city)
    return research

def build_fallback_research(npc: dict, heartbeat: str, city: str) -> str:
    """Deterministic dispatch when the gateway is unavailable.

    This keeps the simulation from hanging while avoiding invented local claims.
    """
    name = npc["name"]
    interest = npc["interest"]
    voice = npc["voice"]
    lower_interest = interest.lower()
    if any(term in lower_interest for term in ("music", "song", "sound", "audio")):
        fact_block = (
            "Sound, in the Unwritten Chapter, is pressure made into pattern: air pushed and "
            "released in waves, measured in hertz for frequency and decibels for intensity. "
            "Human ears are most often described as hearing roughly 20 Hz to 20 kHz, though age, "
            "environment, and attention narrow the gate. I find this reassuringly magical: a room "
            "may be full of motion that no one present is shaped to notice."
        )
    elif any(term in lower_interest for term in ("plant", "garden", "forest", "botany")):
        fact_block = (
            "Plants trade in light with an austerity that would humble most spellwrights. Through "
            "photosynthesis, chlorophyll helps convert light energy, water, and carbon dioxide into "
            "sugars, with oxygen released as a consequence. Their time is not slow because they are "
            "simple; it is slow because they negotiate with weather, soil, season, and damage all at once."
        )
    elif any(term in lower_interest for term in ("library", "book", "archive", "history")):
        fact_block = (
            "Archives survive by refusing to trust memory alone. Real libraries use catalog records, "
            "classification systems, preservation rules, and climate control to keep fragile material "
            "findable after the original keeper is gone. A shelf is therefore not storage. It is a treaty "
            "between the present and a reader who has not arrived yet."
        )
    elif any(term in lower_interest for term in ("food", "tea", "kitchen", "bake", "coffee")):
        fact_block = (
            "Cooking is chemistry under a domestic alias. Heat changes proteins, evaporates water, "
            "releases aroma compounds, and browns sugars and amino acids through Maillard reactions. "
            "No wonder kitchens become family temples: they alter matter while pretending merely to "
            "make supper."
        )
    else:
        fact_block = (
            "The Unwritten Chapter is full of civic enchantments that pretend to be ordinary systems: "
            "maps, schedules, public archives, weather records, libraries, transit routes, and small "
            "business directories. Their power is not secrecy, but reliability. A thing written down, "
            "updated, and made findable becomes a kind of lantern."
        )

    heartbeat_line = ""
    if heartbeat.strip():
        heartbeat_line = (
            " The Margin-Glass carried a few weathered signals with it today, and I have treated "
            "them as atmosphere rather than omen."
        )

    return (
        f"I could not make the Glass hold still long enough for a full expedition, so I am sending "
        f"a narrower field note from {city}. My assigned curiosity remains this: {interest}. "
        f"I am recording it in the manner that best fits my hand: {voice}.{heartbeat_line}\n\n"
        f"{fact_block}\n\n"
        "What interests me most is not the fact by itself, but the discipline around it. Humans keep "
        "building little agreements with reality: a measurement, a label, a route, a recipe, a shelf "
        "mark, a maintenance schedule. None of these look like spells from the outside. Yet each one "
        "allows a stranger to arrive later and still be helped by someone who is absent. That may be "
        "the most civilized form of magic I have found so far.\n\n"
        "I will return to the Margin-Glass when it clears and test this thread against something more "
        "particular. For now, I leave bj this much: the real world is not less enchanted for being "
        "documented. Its records are where many of its spells are hiding.\n\n"
        f"{name}"
    )


# ─── Delivery ─────────────────────────────────────────────────────────────────

def deliver_local(npc: dict, research: str, date_str: str) -> Path:
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", npc["name"].lower()).strip("-")
    path = RESEARCH_DIR / f"{slug}-{date_str}.md"
    path.write_text(
        f"# Research Note from {npc['name']}\n"
        f"*{date_str} · Belief invested: {BELIEF_COST}*\n\n"
        f"{research}\n"
    )
    print(f"  ✓ Local: {path.relative_to(BASE_DIR)}")
    return path


def deliver_icloud(npc: dict, research: str, date_str: str) -> bool:
    title = f"From {npc['name']} — {date_str}"
    body  = research.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    script = f'''
tell application "Notes"
    tell account "iCloud"
        set noteFolder to missing value
        repeat with f in folders
            if name of f is "Labyrinth" then
                set noteFolder to f
                exit repeat
            end if
        end repeat
        if noteFolder is missing value then
            set noteFolder to make new folder with properties {{name:"Labyrinth"}}
        end if
        tell noteFolder
            make new note with properties {{name:"{title}", body:"{body}"}}
        end tell
    end tell
end tell
'''
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=30
        )
    except subprocess.TimeoutExpired:
        print("  ⚠ iCloud Notes timed out after 30s.")
        return False
    if result.returncode == 0:
        print(f"  ✓ iCloud Notes: \"{title}\"")
        return True
    else:
        print(f"  ⚠ iCloud Notes failed: {result.stderr.strip()[:100]}")
        return False


def deliver_telegram(npc: dict, research: str) -> bool:
    header  = f"📜 *From {npc['name']}:*\n\n"
    message = header + research
    try:
        result = subprocess.run(
            ["openclaw", "message", "send",
             "--target", TELEGRAM_TARGET,
             "--channel", TELEGRAM_CHANNEL,
             "--message",
             message],
            capture_output=True, text=True, timeout=45
        )
    except subprocess.TimeoutExpired:
        print("  ⚠ Telegram timed out after 45s.")
        return False
    if result.returncode == 0:
        print(f"  ✓ Telegram sent.")
        return True
    else:
        print(f"  ⚠ Telegram failed: {result.stderr.strip()[:100]}")
        return False


# ─── Belief deduction ─────────────────────────────────────────────────────────

def deduct_belief(npc: dict, dry_run: bool) -> None:
    new_belief = npc["belief"] - BELIEF_COST
    if dry_run:
        print(f"  [dry-run] Would deduct {BELIEF_COST} Belief from {npc['name']}: {npc['belief']} → {new_belief}")
        return
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "write-entity.py"),
             npc["name"], "NPC", str(new_belief), npc["notes"]],
            capture_output=True, text=True, cwd=BASE_DIR, timeout=20
        )
    except subprocess.TimeoutExpired:
        print("  ⚠ Belief deduction timed out after 20s.")
        return
    if result.returncode == 0:
        print(f"  ✓ Belief: {npc['belief']} → {new_belief} for {npc['name']}")
    else:
        print(f"  ⚠ Belief deduction failed: {result.stderr.strip()[:100]}")


# ─── Tick-queue entry ─────────────────────────────────────────────────────────

_SEEDS =[
    "{name} has been busy at the Margin-Glass. Something arrived in the Unwritten Chapter — "
    "in {their} careful handwriting, or whatever handwriting means on that side. It's waiting.",
    "The research alcove smells different today. {Name} was here. Something is sitting on "
    "the reading stand that wasn't there before the session ended.",
    "{Name} left something through the Glass. {They} didn't say anything about it — "
    "just slid it through and went back to {their} work. It's addressed to bj.",
    "There's a note in the Unwritten Chapter's delivery slot. {Name}'s script. "
    "{They} found something worth sending.",
]

def queue_tick(npc: dict) -> None:
    import random
    name  = npc["name"].split()[0]
    Name  = name
    their = "their"
    They  = "They"
    seed  = random.choice(_SEEDS).format(name=name, Name=Name, their=their, They=They)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    ensure_header(TICK_QUEUE, QUEUE_HEADER)

    with TICK_QUEUE.open("a") as f:
        f.write(
            f"\n## [npc-research] {timestamp}\n"
            f"*{npc['name']} researched: {npc['interest'][:60]}*\n"
            f"Narrative seed: {seed}\n"
            f"Delivery: iCloud Notes + Telegram + local file → `memory/npc-research/`\n"
        )
    prune_tick_queue(TICK_QUEUE, QUEUE_HEADER)
    print(f"  ✓ Tick-queue entry written.")


# ─── Physical letter ─────────────────────────────────────────────────────────

STATIONERY = {
    "Zara Finch": {
        "accent": "#7d2636",
        "accent2": "#0f766e",
        "seal": "ZF",
        "title": "Upper Reading Alcoves",
        "motif": "ink-stained marginal diagrams, sea-glass color tests, and urgent underlines",
        "note": "written quickly, then revised twice in smaller ink",
    },
    "Professor Stonebrook": {
        "accent": "#365a47",
        "accent2": "#8a6f2a",
        "seal": "S",
        "title": "Department of Practical Geomancy",
        "motif": "pressed leaves, measured rule-lines, mineral swatches, and careful labels",
        "note": "filed with exactitude; sentimental only in the margins",
    },
    "Headmistress Thorne": {
        "accent": "#4b244a",
        "accent2": "#9b6b2f",
        "seal": "ET",
        "title": "Office of the Headmistress",
        "motif": "formal letterhead, wax-shadow seal, tide marks, and restrained red corrections",
        "note": "official, but the paper remembers pressure",
    },
    "Boggle": {
        "accent": "#7c3f00",
        "accent2": "#2563eb",
        "seal": "B!",
        "title": "Under Table, Near the Good Crumbs",
        "motif": "crooked arrows, biscuit crumbs, happy stains, and impossible footnotes",
        "note": "typed badly on purpose, except where it is accidentally profound",
    },
    "Serenity Brown": {
        "accent": "#3f5f73",
        "accent2": "#a35b35",
        "seal": "SB",
        "title": "Quiet Stacks",
        "motif": "soft pencil notes, folded-corner page marks, and careful breath between lines",
        "note": "gentle enough that the dangerous parts can be heard",
    },
    "Dr. Elowen Vellum": {
        "accent": "#315f5d",
        "accent2": "#8f5a2a",
        "seal": "EV",
        "title": "Refectory Marginalia",
        "motif": "red-ink annotations, silver bookmark-calipers, tidy nutrition tables, and pressed herb stains",
        "note": "precise enough to be useful, kind enough to be obeyed",
    },
}

DEFAULT_STATIONERY = {
    "accent": "#4f4638",
    "accent2": "#7b6f52",
    "seal": "LS",
    "title": "Labyrinth of Stories",
    "motif": "sparse pen-and-ink marks, watercolor wash, marginalia, and archival overlays",
    "note": "sent through the Margin-Glass with the sender's hand still visible",
}


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _inline_markup(text: str) -> str:
    safe = html.escape(text)
    safe = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", safe)
    safe = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", safe)
    return safe


def _research_to_html(research: str) -> str:
    blocks = []
    pending = []

    def flush_pending():
        if pending:
            blocks.append(f"<p>{_inline_markup(' '.join(pending))}</p>")
            pending.clear()

    for raw in research.splitlines():
        line = raw.strip()
        if not line:
            flush_pending()
            continue
        if set(line) <= {"-", "—", "_"} and len(line) >= 3:
            flush_pending()
            blocks.append("<div class=\"rule\"></div>")
            continue
        if line.startswith("#"):
            flush_pending()
            blocks.append(f"<h2>{_inline_markup(line.lstrip('#').strip())}</h2>")
            continue
        if line.startswith(("—", "- ")) or line.endswith((" Labyrinth of Stories", " Upper Reading Alcoves")):
            flush_pending()
            blocks.append(f"<p class=\"signature-line\">{_inline_markup(line)}</p>")
            continue
        if line.startswith("*") and line.endswith("*") and len(line) > 2:
            flush_pending()
            blocks.append(f"<p class=\"meta-line\">{_inline_markup(line.strip('*'))}</p>")
            continue
        pending.append(line)
    flush_pending()
    return "\n".join(blocks)


def _shorten(text: str, limit: int = 96) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    if len(clean) <= limit:
        return clean
    return clean[:limit - 1].rstrip() + "…"


def _letter_subject(npc: dict, research: str) -> str:
    for raw in research.splitlines():
        clean = raw.strip().strip("*").strip()
        if not clean:
            continue
        filed = re.search(r"Filed Under:\s*(.+)", clean, flags=re.IGNORECASE)
        if filed:
            return _shorten(filed.group(1), 92)
        if "PRIVATE RESEARCH" in clean.upper():
            continue
        if 12 <= len(clean) <= 110:
            return _shorten(clean, 92)
    return _shorten(npc.get("interest", "Unwritten research"), 92)


def build_letter_image_prompt(npc: dict, date_str: str) -> str:
    style = STATIONERY.get(npc["name"], DEFAULT_STATIONERY)
    return (
        f"Small archival ornament for a printed magical academy research letter from {npc['name']}. "
        f"The character's focus is: {npc.get('interest', '')}. "
        f"Visual motif: {style['motif']}. "
        "illustrated in sparse pen-and-ink linework with loose watercolor washes on textured aged parchment, "
        "with visible paper grain, soft ink bleed, watercolor blooms, layered manuscript-page composition, "
        "lush handwritten marginalia, lush watercolor washes, visible library stamps, wax seals, labels, tabs, arrows, "
        "annotations, archival overlays, and selective pops of color. Make the page furniture abundant and integral, "
        "not timid decoration. Keep the image airy, literary, sketch-like, "
        "and slightly unfinished, like a page from a magical field journal rather than a polished digital illustration. "
        "Include generous page layout elements such as notes, labels, sketches, margin writing, stamps, seals, and overlays so "
        "the image feels embedded in a manuscript page. No readable text, no logo, no border, no watermark."
    )


def generate_letter_image(npc: dict, date_str: str) -> Optional[Path]:
    if os.environ.get("NPC_RESEARCH_LETTER_IMAGE", "1").lower() in ("0", "false", "no"):
        return None
    LETTER_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    output = LETTER_IMAGES_DIR / f"{_slug(npc['name'])}-{date_str}.png"
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "drawthings_scene.py"),
        "--prompt",
        build_letter_image_prompt(npc, date_str),
        "--output",
        str(output),
        "--width",
        "768",
        "--height",
        "512",
        "--steps",
        "4",
        "--cfg-scale",
        "1.0",
        "--timeout-seconds",
        "120",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=135)
    except subprocess.TimeoutExpired:
        print("  ⚠ Letter image skipped: Draw Things timed out.")
        return None
    if proc.returncode == 0 and output.exists():
        print(f"  ✓ Letter image generated → {output.relative_to(BASE_DIR)}")
        return output
    detail = (proc.stderr or proc.stdout or "Draw Things letter image generation failed").strip()
    print(f"  ⚠ Letter image skipped: {detail[:180]}")
    return None


def build_letter_html(npc: dict, research: str, date_str: str, image_path: Optional[Path] = None) -> str:
    style = STATIONERY.get(npc["name"], DEFAULT_STATIONERY)
    title = html.escape(style["title"])
    name = html.escape(npc["name"])
    subject = html.escape(_letter_subject(npc, research))
    voice_note = html.escape(style["note"])
    image_html = ""
    if image_path and image_path.exists():
        image_html = f"<img class=\"letter-art\" src=\"{image_path.resolve().as_uri()}\" alt=\"letter ornament\">"

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Letter from {name} — {date_str}</title>
<style>
@page {{ size: Letter; margin: 0.34in; }}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  color: #2f2a22;
  background: #efe4cb;
  font-family: Georgia, "Times New Roman", serif;
  line-height: 1.42;
}}
.page {{
  min-height: 10.25in;
  position: relative;
  padding: 0.42in 0.48in 0.36in;
  border: 1px solid rgba(83, 68, 44, 0.42);
  background:
    radial-gradient(circle at 16% 12%, rgba(255,255,255,0.32), transparent 22%),
    radial-gradient(circle at 88% 24%, {style['accent2']}22, transparent 18%),
    linear-gradient(90deg, rgba(87,68,39,0.08) 0 1px, transparent 1px 100%),
    linear-gradient(#f7edd7, #eadbbd);
  background-size: auto, auto, 22px 22px, auto;
  overflow: visible;
}}
.page::before {{
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image:
    repeating-linear-gradient(0deg, rgba(49,39,25,0.025) 0 1px, transparent 1px 4px),
    radial-gradient(circle at 8% 82%, {style['accent']}1f, transparent 18%),
    radial-gradient(circle at 92% 88%, rgba(67, 52, 31, 0.15), transparent 16%);
  mix-blend-mode: multiply;
}}
.masthead {{
  position: relative;
  display: grid;
  grid-template-columns: 0.9in 1fr;
  gap: 0.18in;
  align-items: center;
  border-bottom: 2px solid {style['accent']};
  padding-bottom: 0.16in;
}}
.seal {{
  width: 0.76in;
  height: 0.76in;
  border: 2px solid {style['accent']};
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: {style['accent']};
  font-size: 24px;
  font-weight: 700;
  letter-spacing: 0.03em;
  transform: rotate(-7deg);
  background: rgba(255,255,255,0.18);
  box-shadow: 0 0 0 7px rgba(255,255,255,0.13) inset;
}}
.from {{
  margin: 0;
  font-size: 26px;
  color: {style['accent']};
  letter-spacing: 0.02em;
}}
.subhead {{
  margin-top: 2px;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.13em;
  color: #675943;
}}
.date-line {{
  margin-top: 0.08in;
  font-size: 12px;
  color: #6f6048;
}}
.content {{
  position: relative;
  display: grid;
  grid-template-columns: 1fr 1.34in;
  gap: 0.22in;
  margin-top: 0.24in;
  align-items: start;
}}
.letter-body {{
  font-size: 13.2px;
}}
.letter-body p {{
  margin: 0 0 0.105in;
}}
.letter-body h2 {{
  margin: 0 0 0.12in;
  font-size: 16px;
  color: {style['accent']};
}}
.meta-line {{
  color: #675943;
  font-size: 12px;
  font-style: italic;
}}
.signature-line {{
  color: {style['accent']};
  font-style: italic;
}}
.rule {{
  height: 1px;
  margin: 0.1in 0 0.13in;
  background: linear-gradient(90deg, transparent, {style['accent']}, transparent);
}}
.margin {{
  border-left: 1px solid rgba(83,68,44,0.26);
  padding-left: 0.14in;
  color: #5f503a;
  font-size: 11.4px;
  break-inside: avoid;
}}
.letter-art {{
  width: 100%;
  border: 1px solid rgba(83,68,44,0.22);
  margin-bottom: 0.14in;
  filter: sepia(0.16) contrast(0.94);
}}
.scribble {{
  color: {style['accent']};
  font-style: italic;
  transform: rotate(1.3deg);
  margin-bottom: 0.18in;
}}
.label {{
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 9px;
  color: #81735d;
  margin-top: 0.18in;
}}
.footer {{
  position: relative;
  border-top: 1px solid rgba(83,68,44,0.25);
  margin-top: 0.22in;
  padding-top: 0.07in;
  font-size: 10px;
  color: #766850;
  display: flex;
  justify-content: space-between;
}}
</style>
</head>
<body>
<main class="page">
  <header class="masthead">
    <div class="seal">{html.escape(style['seal'])}</div>
    <div>
      <h1 class="from">A Letter from {name}</h1>
      <div class="subhead">{title} · Enchantify Academy</div>
      <div class="date-line">{date_str} · through the Margin-Glass · subject: {subject}</div>
    </div>
  </header>
  <section class="content">
    <article class="letter-body">
      {_research_to_html(research)}
    </article>
    <aside class="margin">
      {image_html}
      <div class="scribble">{html.escape(style['motif'])}</div>
      <div class="label">Hand</div>
      <p>{voice_note}</p>
      <div class="label">Filed</div>
      <p>NPC research · Belief invested: {BELIEF_COST}</p>
    </aside>
  </section>
  <footer class="footer">
    <span>Delivered through the Margin-Glass</span>
    <span>memory/npc-research · {name}</span>
  </footer>
</main>
</body>
</html>"""


def write_letter_html(npc: dict, research: str, date_str: str, image_path: Optional[Path] = None) -> Path:
    LETTER_DIR.mkdir(parents=True, exist_ok=True)
    path = LETTER_DIR / f"{_slug(npc['name'])}-{date_str}.html"
    path.write_text(build_letter_html(npc, research, date_str, image_path), encoding="utf-8")
    print(f"  ✓ Letter HTML: {path.relative_to(BASE_DIR)}")
    return path


def read_research_note(path: Path) -> tuple[dict, str, str]:
    """Read an existing memory/npc-research markdown note for preview rendering."""
    text = path.read_text(encoding="utf-8")
    name_m = re.search(r"^#\s*Research Note from\s+(.+?)\s*$", text, flags=re.MULTILINE)
    date_m = re.search(r"^\*(\d{4}-\d{2}-\d{2})\s+·", text, flags=re.MULTILINE)
    body = re.sub(r"^#.*?\n\*.*?\*\n\n", "", text, count=1, flags=re.DOTALL).strip()
    name = name_m.group(1).strip() if name_m else path.stem.rsplit("-", 3)[0].replace("-", " ").title()
    date_str = date_m.group(1) if date_m else datetime.now().strftime("%Y-%m-%d")

    characters = {c["name"].lower(): c for c in parse_characters()}
    register = parse_register_npcs()
    char = characters.get(name.lower(), {})
    reg = register.get(name, {})
    npc = {
        "name": name,
        "interest": char.get("interest") or reg.get("notes") or "Unwritten research",
        "voice": char.get("voice") or "In-character, natural, reflecting my academy role.",
        "belief": reg.get("belief", 0),
        "notes": reg.get("notes", ""),
    }
    return npc, body, date_str


def preview_letter(note_path: Path, with_image: bool = True) -> Path:
    npc, research, date_str = read_research_note(note_path)
    image_path = generate_letter_image(npc, date_str) if with_image else None
    html_path = write_letter_html(npc, research, date_str, image_path=image_path)
    ps_path = write_letter_postscript(npc, research, date_str)
    print(f"  ✓ Preview ready: {html_path}")
    print(f"  ✓ Print fallback ready: {ps_path}")
    return html_path


def html_to_pdf(html_path: Path) -> Path:
    pdf_path = html_path.with_suffix(".pdf")
    if shutil.which("wkhtmltopdf"):
        r = subprocess.run(
            ["wkhtmltopdf", "--page-size", "Letter", "--quiet", "--enable-local-file-access", str(html_path), str(pdf_path)],
            capture_output=True, timeout=30,
        )
        if r.returncode == 0 and pdf_path.exists():
            return pdf_path

    chrome = CHROME_PATH if os.path.exists(CHROME_PATH) else shutil.which("google-chrome") or shutil.which("chromium")
    if chrome:
        r = subprocess.run(
            [chrome, "--headless", "--disable-gpu", "--no-sandbox",
             f"--print-to-pdf={pdf_path}", "--print-to-pdf-no-header", html_path.resolve().as_uri()],
            capture_output=True, timeout=45,
        )
        if r.returncode == 0 and pdf_path.exists():
            return pdf_path
    return html_path


def _ps_escape(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _plain_research_lines(research: str, width: int = 78) -> list[str]:
    lines = []
    for para in research.splitlines():
        clean = para.strip()
        clean = re.sub(r"\*\*([^*]+)\*\*", r"\1", clean)
        clean = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", clean)
        if not clean:
            lines.append("")
            continue
        if set(clean) <= {"-", "—", "_"} and len(clean) >= 3:
            lines.append("-" * 24)
            continue
        lines.extend(textwrap.wrap(clean, width=width) or [""])
    return lines


def write_letter_postscript(npc: dict, research: str, date_str: str) -> Path:
    """Reliable CUPS fallback when HTML-to-PDF rendering is unavailable."""
    style = STATIONERY.get(npc["name"], DEFAULT_STATIONERY)
    LETTER_DIR.mkdir(parents=True, exist_ok=True)
    path = LETTER_DIR / f"{_slug(npc['name'])}-{date_str}.ps"

    def rgb(hex_color: str) -> tuple[float, float, float]:
        h = hex_color.lstrip("#")
        return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))

    accent = rgb(style["accent"])
    accent2 = rgb(style["accent2"])
    lines = _plain_research_lines(research)

    ps = [
        "%!PS-Adobe-3.0",
        "%%Pages: (atend)",
        "/inch {72 mul} def",
        "/bodyfont {/Times-Roman findfont 10.2 scalefont setfont} def",
        "/smallfont {/Times-Italic findfont 8.5 scalefont setfont} def",
        "/headfont {/Times-Bold findfont 22 scalefont setfont} def",
        "/sealfont {/Times-Bold findfont 20 scalefont setfont} def",
    ]

    page_count = 0
    y = 0

    def new_page():
        nonlocal page_count, y
        if page_count:
            ps.append("showpage")
        page_count += 1
        y = 640
        ps.extend([
            f"%%Page: {page_count} {page_count}",
            "0.96 0.91 0.80 setrgbcolor 0 0 612 792 rectfill",
            "0.20 0.16 0.10 setrgbcolor 36 36 540 720 rectstroke",
            f"{accent2[0]:.3f} {accent2[1]:.3f} {accent2[2]:.3f} setrgbcolor 52 682 508 1 rectfill",
            f"{accent[0]:.3f} {accent[1]:.3f} {accent[2]:.3f} setrgbcolor",
            "newpath 76 706 30 0 360 arc stroke",
            "sealfont",
            f"64 700 moveto ({_ps_escape(style['seal'])}) show",
            "headfont",
            f"118 710 moveto (A Letter from {_ps_escape(npc['name'])}) show",
            "smallfont",
            f"118 690 moveto ({_ps_escape(style['title'])} - Enchantify Academy - {date_str}) show",
            f"410 658 moveto ({_ps_escape(style['note'])}) show",
            "bodyfont",
            "0.17 0.14 0.10 setrgbcolor",
        ])

    new_page()
    for line in lines:
        if y < 72:
            new_page()
        if not line:
            y -= 9
            continue
        ps.append(f"58 {y} moveto ({_ps_escape(line)}) show")
        y -= 12

    ps.extend([
        "smallfont",
        f"{accent[0]:.3f} {accent[1]:.3f} {accent[2]:.3f} setrgbcolor",
        "58 48 moveto (Delivered through the Margin-Glass) show",
        "showpage",
        f"%%Pages: {page_count}",
        "%%EOF",
    ])
    path.write_text("\n".join(ps), encoding="ascii")
    print(f"  ✓ Letter PostScript fallback: {path.relative_to(BASE_DIR)}")
    return path


def _cups_default_printer() -> str:
    cfg = load_config()
    configured = (
        os.environ.get("NPC_RESEARCH_PRINTER")
        or cfg.get("NPC_RESEARCH_PRINTER")
        or os.environ.get("BLEED_PRINTER")
        or cfg.get("BLEED_PRINTER")
        or os.environ.get("ENCHANTIFY_PRINTER")
        or cfg.get("ENCHANTIFY_PRINTER")
    )
    if configured:
        return configured.strip()
    try:
        result = subprocess.run(["lpstat", "-d"], capture_output=True, text=True, timeout=8)
    except Exception:
        return ""
    text = ((result.stdout or "") + (result.stderr or "")).strip()
    m = re.search(r"system default destination:\s*(\S+)", text)
    return m.group(1).strip() if m else ""


def _first_available_printer() -> str:
    try:
        result = subprocess.run(["lpstat", "-p"], capture_output=True, text=True, timeout=8)
    except Exception:
        return ""
    for line in (result.stdout or "").splitlines():
        m = re.match(r"printer\s+(\S+)\s+", line)
        if m:
            return m.group(1).strip()
    return ""


def print_npc_letter(npc: dict, letter_path: Path, research: str, date_str: str) -> bool:
    """
    Print a physical letter from the NPC via the default CUPS printer.
    Uses the styled HTML/PDF letter artifact.
    """
    print_file = html_to_pdf(letter_path)
    if print_file.suffix.lower() == ".html":
        print_file = write_letter_postscript(npc, research, date_str)
    printer = _cups_default_printer() or _first_available_printer()
    if not printer:
        print("  ⚠ Print failed: no CUPS printer found.")
        return False
    lp_bin = shutil.which("lp") or "/usr/bin/lp"
    command = [lp_bin, "-d", printer, "-o", "media=Letter", str(print_file)]
    try:
        result = subprocess.run(
            command,
            capture_output=True, text=True, timeout=20,
        )
    except subprocess.TimeoutExpired:
        print("  ⚠ Print timed out after 20s.")
        return False

    if result.returncode == 0:
        print(f"  ✓ Letter printed: {npc['name']} → {printer}")
        return True
    print(f"  ⚠ Print failed: {result.stderr.strip()[:120]}")
    return False


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("player",      nargs="?", default="bj")
    parser.add_argument("--npc",       help="Force a specific NPC by name")
    parser.add_argument("--dry-run",   action="store_true")
    parser.add_argument("--no-icloud", action="store_true", help="Skip iCloud Notes delivery")
    parser.add_argument("--no-print",  action="store_true", help="Skip physical letter printing")
    parser.add_argument("--no-letter-image", action="store_true", help="Skip optional Draw Things letter ornament")
    parser.add_argument("--preview-letter", type=Path, help="Render a styled letter from an existing memory/npc-research note and exit")
    parser.add_argument("--model-smoke", action="store_true", help="Check the configured gateway model and exit")
    args = parser.parse_args()

    if args.model_smoke:
        sys.exit(model_smoke_test())
    if args.preview_letter:
        preview_letter(args.preview_letter, with_image=not args.no_letter_image)
        return

    with cron_steward.run("npc-research", dry_run=args.dry_run, forced=bool(args.npc)):
        characters    = parse_characters()
        register      = parse_register_npcs()
        relationships = parse_relationships(args.player)
        cache         = load_cache()

        npc = select_npc(characters, register, relationships, cache, forced_name=args.npc)

        if not npc:
            reason = "no eligible NPC found; all on cooldown or below Belief threshold"
            print(f"[npc-research] {reason}.")
            cron_steward.mark_skipped("npc-research", reason)
            return

        print(f"[npc-research] {npc['name']} (Belief {npc['belief']}) is researching: {npc['interest'][:60]}…")

        heartbeat = load_heartbeat_snippet()
        city = get_local_city()

        if args.dry_run:
            will_print = npc["name"] in CORE_NPCS and not args.no_print
            print(f"  [dry-run] Would generate research note for {npc['name']} focusing on {city}.")
            print(f"  [dry-run] Delivery: local"
                  f"  + styled letter HTML"
                  f"{'  + generated letter ornament' if not args.no_letter_image else ''}"
                  f"{'  + iCloud' if not args.no_icloud else ''}"
                  f"  + Telegram"
                  f"{'  + letter (CUPS)' if will_print else ''}")
            deduct_belief(npc, dry_run=True)
            return

        research  = generate_research(npc, heartbeat, city)
        date_str  = datetime.now().strftime("%Y-%m-%d")
        delivery_payload = {"name": npc["name"], "date": date_str, "research": research}
        skip, digest, reason = cron_steward.should_skip_duplicate(
            "npc-research",
            delivery_payload,
            cooldown_hours=72,
            force=bool(args.npc),
            scope=npc["name"],
        )
        if skip:
            print(f"  ↺ Skipping duplicate research delivery: {reason}")
            cron_steward.mark_skipped("npc-research", reason, scope=npc["name"], fingerprint=digest)
            cache[npc["name"]] = datetime.now().isoformat()
            save_cache(cache)
            return

        print(f"\n--- Research note ({len(research)} chars) ---")
        print(research[:200] + "…" if len(research) > 200 else research)
        print("---\n")

        deliver_local(npc, research, date_str)
        letter_image = None if args.no_letter_image else generate_letter_image(npc, date_str)
        letter_path = write_letter_html(npc, research, date_str, image_path=letter_image)

        printed = False
        if not args.no_print:
            printed = print_npc_letter(npc, letter_path, research, date_str)

        telegram_ok = deliver_telegram(npc, research)

        icloud_ok = False
        if not args.no_icloud:
            icloud_ok = deliver_icloud(npc, research, date_str)

        deduct_belief(npc, dry_run=False)
        queue_tick(npc)

        if _HAS_NPC_LOG:
            _npc_log.append(npc["name"], "research", npc["interest"][:100])

        cache[npc["name"]] = datetime.now().isoformat()
        save_cache(cache)
        cron_steward.mark_delivered(
            "npc-research",
            delivery_payload,
            scope=npc["name"],
            telegram_ok=telegram_ok,
            icloud_ok=icloud_ok,
            printed=printed,
        )

        print(f"\n[npc-research] Done. {npc['name']} is back at work. Next eligible in {COOLDOWN_HOURS}h.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[npc-research] Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(0)

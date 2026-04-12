#!/usr/bin/env python3
"""
npc-research.py — NPCs research topics from the Unwritten Chapter.

During the simulation phase, an eligible NPC selects a topic from their
Unwritten Interest, writes a research note in their voice using the Claude
API, and delivers it to the player.

Eligibility: NPC must be in world-register with Belief >= 8, not on cooldown
(72h default), and either have a tracked relationship >= 25 or be a core NPC
(Zara, Stonebrook, etc.) at Full Presence.

Belief cost: 3 per research note, deducted from world-register.

Outputs:
  - memory/npc-research/[slug]-[date].md  (always)
  - iCloud Notes via osascript             (default on)
  - Telegram via openclaw message send     (--telegram flag)
  - memory/tick-queue.md                   (narrative seed)

Usage:
  python3 scripts/npc-research.py [player] [--dry-run] [--npc "Zara Finch"] [--telegram] [--no-icloud]
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

SCRIPT_DIR   = Path(__file__).parent
BASE_DIR     = Path(os.environ.get("ENCHANTIFY_BASE_DIR", SCRIPT_DIR.parent))
CACHE_PATH   = BASE_DIR / "config" / "npc-research-cache.json"
RESEARCH_DIR = BASE_DIR / "memory" / "npc-research"
TICK_QUEUE   = BASE_DIR / "memory" / "tick-queue.md"

BELIEF_COST     = 3
BELIEF_MINIMUM  = 8       # NPC must have at least this much to research
COOLDOWN_HOURS  = 72      # per-NPC cooldown between notes
TELEGRAM_TARGET = "8729557865"
TELEGRAM_CHANNEL = "telegram"

# NPCs always eligible regardless of tracked relationship (core cast)
CORE_NPCS = {"Zara Finch", "Professor Stonebrook", "Headmistress Thorne", "Boggle"}


# ─── Config / API ─────────────────────────────────────────────────────────────

def load_config() -> dict:
    cfg = {}
    config_path = SCRIPT_DIR / "enchantify-config.sh"
    if config_path.exists():
        with open(config_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                cfg[key.strip()] = val.strip().strip('"')
    return cfg

def call_gemini(prompt: str) -> str:
    """Run a prompt through the enchantify agent (Gemini via openclaw)."""
    result = subprocess.run(
        ["openclaw", "agent", "--local", "--agent", "enchantify", "-m", prompt],
        capture_output=True, text=True
    )
    return result.stdout.strip()


# ─── Parse characters.md ──────────────────────────────────────────────────────

def parse_characters() -> list[dict]:
    """
    Extract NPCs with Unwritten Interest and Voice from characters.md.
    Handles both ### header format (professors) and **Name** — inline format (students).
    """
    path = BASE_DIR / "lore" / "characters.md"
    if not path.exists():
        return []
    text = path.read_text()
    npcs = []

    # Format 1: ### Name header blocks
    sections = re.split(r"^### ", text, flags=re.MULTILINE)
    for section in sections[1:]:
        name_match = re.match(r"^(.+)", section)
        if not name_match:
            continue
        name = name_match.group(1).strip()

        interest_m = re.search(r"\*\*Unwritten Interest:\*\*\s*(.+)", section)
        voice_m    = re.search(r"\*\*Voice:\*\*\s*(.+)", section)

        if interest_m and voice_m:
            npcs.append({
                "name":     name,
                "interest": interest_m.group(1).strip(),
                "voice":    voice_m.group(1).strip(),
            })

    # Format 2: **Name** — description. **Unwritten Interest:** ...
    for m in re.finditer(
        r"\*\*([A-Z][^*]+?)\*\*\s*[—–-].*?\*\*Unwritten Interest:\*\*\s*([^\n]+)",
        text,
    ):
        name     = m.group(1).strip()
        interest = m.group(2).strip()
        # Try to find a Voice field nearby (within 300 chars after the match)
        nearby   = text[m.start():m.start() + 400]
        voice_m  = re.search(r"\*\*Voice:\*\*\s*(.+)", nearby)
        voice    = voice_m.group(1).strip() if voice_m else "Quiet, specific, genuine."
        # Avoid duplicates from the header parser
        if not any(n["name"] == name for n in npcs):
            npcs.append({"name": name, "interest": interest, "voice": voice})

    return npcs


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
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) < 4:
            continue
        name  = parts[0]
        etype = parts[1].lower()
        if not name or name.lower() in ("entity", "name") or "npc" not in etype:
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
                parts = [p.strip() for p in line.strip("|").split("|")]
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
    """
    Pick one eligible NPC. Eligibility:
      - Has Unwritten Interest + Voice in characters.md
      - In world-register as NPC with Belief >= BELIEF_MINIMUM
      - Not on cooldown
      - Is a core NPC OR has tracked relationship >= 25
    """
    import random

    eligible = []
    for char in characters:
        name = char["name"]

        if forced_name and name != forced_name:
            continue

        reg = register.get(name)
        if not reg or reg["belief"] < BELIEF_MINIMUM:
            continue

        if is_on_cooldown(cache, name):
            continue

        rel_score = relationships.get(name, None)
        if name not in CORE_NPCS and (rel_score is None or rel_score < 25):
            continue

        eligible.append(char | {"belief": reg["belief"], "notes": reg["notes"]})

    if not eligible:
        return None

    # Prefer higher-Belief NPCs (more invested = more likely to research)
    eligible.sort(key=lambda n: n["belief"], reverse=True)
    weights = [n["belief"] for n in eligible]
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
    snippet = []
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

Your fascination with the Unwritten Chapter: {interest}

Rules:
- Write entirely in your character voice. You are {name}, not an assistant.
- 200–300 words. Dense with your specific personality.
- Ground the note in real details from the Margin-Glass signals provided.
- The note should feel like a genuine dispatch — curious, invested, personal.
- Do NOT break character. Do NOT use clinical or therapeutic language.
- Do NOT reference "the game," "mechanics," or "the Labyrinth" as a construct.
- Sign your full name at the end, with a brief postscript in character if it fits.
- The player's name is bj (he/him).
"""

def generate_research(npc: dict, heartbeat: str) -> str:
    system = SYSTEM_PROMPT.format(
        name=npc["name"],
        voice=npc["voice"],
        interest=npc["interest"],
    )
    user_prompt = (
        f"Current signals from the Margin-Glass (real-world data):\n\n{heartbeat}\n\n"
        "Write your research note now. Draw on your Unwritten Interest and the signals above. "
        "Pick one specific thread and follow it. Do not try to cover everything."
    )
    return call_gemini(f"{system}\n\n{user_prompt}")


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
    # Escape for AppleScript: backslash newlines, escape quotes
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
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"  ✓ iCloud Notes: \"{title}\"")
        return True
    else:
        print(f"  ⚠ iCloud Notes failed: {result.stderr.strip()[:100]}")
        return False


def deliver_telegram(npc: dict, research: str) -> bool:
    header  = f"📜 *From {npc['name']}:*\n\n"
    message = header + research
    result  = subprocess.run(
        ["openclaw", "message", "send",
         "--target", TELEGRAM_TARGET,
         "--channel", TELEGRAM_CHANNEL,
         message],
        capture_output=True, text=True
    )
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
    result = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "write-entity.py"),
         npc["name"], "NPC", str(new_belief), npc["notes"]],
        capture_output=True, text=True, cwd=BASE_DIR
    )
    if result.returncode == 0:
        print(f"  ✓ Belief: {npc['belief']} → {new_belief} for {npc['name']}")
    else:
        print(f"  ⚠ Belief deduction failed: {result.stderr.strip()[:100]}")


# ─── Tick-queue entry ─────────────────────────────────────────────────────────

# Narrative seeds — in Labyrinth voice, never announcing "an NPC sent a file"
_SEEDS = [
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
    name  = npc["name"].split()[0]   # first name for brevity
    Name  = name
    their = "their"
    They  = "They"
    seed  = random.choice(_SEEDS).format(name=name, Name=Name, their=their, They=They)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    TICK_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    if not TICK_QUEUE.exists():
        TICK_QUEUE.write_text("# Tick Queue\n\n*Read at session open, then cleared.*\n")

    with TICK_QUEUE.open("a") as f:
        f.write(
            f"\n## [npc-research] {timestamp}\n"
            f"*{npc['name']} researched: {npc['interest'][:60]}*\n"
            f"Narrative seed: {seed}\n"
            f"Delivery: iCloud Notes + local file → `memory/npc-research/`\n"
        )
    print(f"  ✓ Tick-queue entry written.")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("player",      nargs="?", default="bj")
    parser.add_argument("--npc",       help="Force a specific NPC by name")
    parser.add_argument("--dry-run",   action="store_true")
    parser.add_argument("--telegram",  action="store_true", help="Also send via Telegram")
    parser.add_argument("--no-icloud", action="store_true", help="Skip iCloud Notes delivery")
    args = parser.parse_args()

    characters    = parse_characters()
    register      = parse_register_npcs()
    relationships = parse_relationships(args.player)
    cache         = load_cache()

    npc = select_npc(characters, register, relationships, cache, forced_name=args.npc)

    if not npc:
        print("[npc-research] No eligible NPC found. All on cooldown or below Belief threshold.")
        return

    print(f"[npc-research] {npc['name']} (Belief {npc['belief']}) is researching: {npc['interest'][:60]}…")

    heartbeat = load_heartbeat_snippet()

    if args.dry_run:
        print(f"  [dry-run] Would generate research note for {npc['name']}.")
        print(f"  [dry-run] Delivery: local{'  + iCloud' if not args.no_icloud else ''}{'  + Telegram' if args.telegram else ''}")
        deduct_belief(npc, dry_run=True)
        return

    research  = generate_research(npc, heartbeat)
    date_str  = datetime.now().strftime("%Y-%m-%d")

    print(f"\n--- Research note ({len(research)} chars) ---")
    print(research[:200] + "…" if len(research) > 200 else research)
    print("---\n")

    deliver_local(npc, research, date_str)

    if not args.no_icloud:
        deliver_icloud(npc, research, date_str)

    if args.telegram:
        deliver_telegram(npc, research)

    deduct_belief(npc, dry_run=False)
    queue_tick(npc)

    # Update cooldown cache
    cache[npc["name"]] = datetime.now().isoformat()
    save_cache(cache)

    print(f"\n[npc-research] Done. {npc['name']} is back at work. Next eligible in {COOLDOWN_HOURS}h.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[npc-research] Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(0)  # Don't break world-pulse if this fails

#!/usr/bin/env python3
"""
reach-out.py — The world reaches out.

Runs twice daily. Reads the world register, picks one entity weighted by
Belief (Narrative Weight), generates a short in-character message, and
sends it to Telegram as a text message followed by a voice note.

Anything not found in voice-assignments.md speaks as the Labyrinth (bm_lewis).

Usage:
    python3 scripts/reach-out.py
    python3 scripts/reach-out.py --dry-run
    python3 scripts/reach-out.py --force "Zara Finch"
"""

import argparse
import json
import random
import re
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

BASE_DIR          = Path(__file__).parent.parent
CONFIG_DIR        = BASE_DIR / "config"
LOG_FILE          = CONFIG_DIR / "reach-out-log.json"
WORLD_REGISTER    = BASE_DIR / "lore" / "world-register.md"
VOICE_ASSIGNMENTS = CONFIG_DIR / "voice-assignments.md"
ARC_SPINE         = BASE_DIR / "memory" / "arc-spine.md"

TELEGRAM_CHANNEL = "telegram"
TELEGRAM_ACCOUNT = "enchantify"
FALLBACK_VOICE   = "bm_lewis"
DAILY_CAP        = 2
MIN_BELIEF       = 5
COOLDOWN_H       = 48


# ── Config ─────────────────────────────────────────────────────────────────────

def _load_openclaw_cfg() -> dict:
    p = Path.home() / ".openclaw" / "openclaw.json"
    try:
        return json.loads(p.read_text()) if p.exists() else {}
    except Exception:
        return {}


def _load_secrets() -> dict:
    out = {}
    p = CONFIG_DIR / "secrets.env"
    if p.exists():
        for line in p.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                out[k.strip()] = v.strip().strip('"')
    return out


def get_telegram_credentials() -> Tuple[str, str]:
    """Return (bot_token, chat_id), reading secrets.env then falling back to openclaw.json."""
    secrets = _load_secrets()
    chat_id   = secrets.get("TELEGRAM_CHAT_ID", "")
    bot_token = secrets.get("TELEGRAM_BOT_TOKEN", "")

    if not bot_token or not chat_id:
        cfg = _load_openclaw_cfg()
        enc = cfg.get("channels", {}).get("telegram", {}).get("accounts", {}).get("enchantify", {})
        if not bot_token:
            bot_token = enc.get("botToken", "")
        if not chat_id:
            allow_from = enc.get("allowFrom", [])
            if allow_from:
                chat_id = allow_from[0]

    return bot_token, chat_id


# ── World register ─────────────────────────────────────────────────────────────

def parse_world_register() -> List[dict]:
    """Parse all entity table rows from world-register.md."""
    if not WORLD_REGISTER.exists():
        return []
    entities = []
    for line in WORLD_REGISTER.read_text().splitlines():
        m = re.match(r'^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|([^|]*)\|?', line)
        if not m:
            continue
        name, etype, belief_s, notes = (m.group(i).strip() for i in (1, 2, 3, 4))
        if name.lower() in ("entity", "---", "") or etype.lower() in ("type", "---"):
            continue
        try:
            belief = int(belief_s)
        except ValueError:
            continue
        if belief < MIN_BELIEF:
            continue
        clean_notes = re.sub(r'\[[\w:,\-]+\]\s*', '', notes).strip()
        entities.append({"name": name, "type": etype, "belief": belief, "notes": clean_notes})
    return entities


# ── Voice assignments ──────────────────────────────────────────────────────────

def parse_voice_assignments() -> Dict[str, str]:
    """Parse voice-assignments.md into {name: voice_string}."""
    if not VOICE_ASSIGNMENTS.exists():
        return {}
    voices = {}
    for line in VOICE_ASSIGNMENTS.read_text().splitlines():
        # Matches: - **Name (optional qualifier):** `voice` — ...
        m = re.match(r'^-\s+\*\*([^*(]+?)(?:\s*\([^)]*\))?\s*:\*\*\s+`([^`]+)`', line)
        if m:
            voices[m.group(1).strip()] = m.group(2).strip()
    return voices


def resolve_voice(entity_name: str, voices: Dict[str, str]) -> str:
    """Look up voice by exact name then by last-name fragment. Falls back to bm_lewis."""
    if entity_name in voices:
        return voices[entity_name]
    # Try stripping titles (Professor, Headmistress, etc.)
    short = re.sub(r'^(Professor|Headmistress|Headmaster|Dr\.?)\s+', '', entity_name).strip()
    if short in voices:
        return voices[short]
    # Try matching by last word (surname)
    surname = entity_name.split()[-1]
    for k, v in voices.items():
        if k.split()[-1] == surname:
            return v
    return FALLBACK_VOICE


# ── Selection ──────────────────────────────────────────────────────────────────

def load_log() -> dict:
    if LOG_FILE.exists():
        try:
            return json.loads(LOG_FILE.read_text())
        except Exception:
            pass
    return {}


def save_log(log: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.write_text(json.dumps(log, indent=2, default=str))


def is_on_cooldown(name: str, log: dict) -> bool:
    last = log.get(name)
    if not last:
        return False
    try:
        return datetime.now() - datetime.fromisoformat(last) < timedelta(hours=COOLDOWN_H)
    except Exception:
        return False


def daily_count(log: dict) -> int:
    return log.get(f"daily_{datetime.now().strftime('%Y-%m-%d')}", 0)


def record_contact(name: str, log: dict) -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    log[name] = datetime.now().isoformat()
    log[f"daily_{today}"] = daily_count(log) + 1


def pick_entity(entities: List[dict], log: dict, forced: Optional[str] = None) -> Optional[dict]:
    if forced:
        # Exact then prefix match
        for e in entities:
            if e["name"].lower() == forced.lower():
                return e
        for e in entities:
            if e["name"].lower().startswith(forced.lower()):
                return e
        return None

    if daily_count(log) >= DAILY_CAP:
        return None

    eligible = [e for e in entities if not is_on_cooldown(e["name"], log)]
    if not eligible:
        return None

    # Weighted random by Belief
    total = sum(e["belief"] for e in eligible)
    r = random.random() * total
    cumulative = 0.0
    for e in eligible:
        cumulative += e["belief"]
        if r <= cumulative:
            return e
    return eligible[-1]


# ── World context ──────────────────────────────────────────────────────────────

def _world_context() -> str:
    lines = []
    if ARC_SPINE.exists():
        text = ARC_SPINE.read_text()
        m = re.search(r'Phase:\s*(\w+)', text, re.IGNORECASE)
        if m:
            lines.append(f"Arc phase: {m.group(1)}")
        m = re.search(r'^## Last Session\s*\n\*(\d{4}-\d{2}-\d{2})', text, re.MULTILINE)
        if m:
            try:
                days = (datetime.now() - datetime.strptime(m.group(1).strip(), "%Y-%m-%d")).days
                lines.append(f"Days since last session: {days}")
            except ValueError:
                pass
        m = re.search(r'most alive moment[^\n]*:\s*([^\n]+)', text, re.IGNORECASE)
        if m:
            lines.append(f"Player's most alive moment: {m.group(1).strip()[:80]}")
    return "\n".join(lines)


# ── Message generation ─────────────────────────────────────────────────────────

def generate_message(entity: dict) -> str:
    cfg   = _load_openclaw_cfg()
    port  = cfg.get("gateway", {}).get("port", 18789)
    token = cfg.get("gateway", {}).get("auth", {}).get("token", "")

    name, etype, belief, notes = entity["name"], entity["type"], entity["belief"], entity["notes"]
    context = _world_context()

    if etype.lower() in ("location", "object", "fae", "thread"):
        frame = (
            f"{name} is a {etype.lower()} in Enchantify Academy. {notes}\n"
            f"Write as if this {etype.lower()} itself sends a brief impression, feeling, or fragment "
            f"to the player — not a human voice, but a presence. It need not be a complete thought."
        )
    else:
        frame = (
            f"{name}: {notes or 'a character at Enchantify Academy'}\n"
            f"Write as {name} speaking directly to the player (bj) in first person."
        )

    prompt = f"""You are writing a message from {name} to bj, a student at Enchantify Academy.

{frame}
Narrative Weight (Belief): {belief}
{context}

Rules:
- 1 to 3 sentences maximum, under 55 words
- Speak naturally, as if leaving a voice note — direct, specific, personal
- Do not reference "the game", "the story", or "the session" as meta concepts
- No asterisks, no stage directions, no action text
- Do not explain why you are reaching out; let it be felt

Output ONLY the spoken text. Nothing else."""

    payload = {
        "model": "openclaw",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.9,
        "max_tokens": 200,
        "stream": False,
    }
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "x-openclaw-session-key": f"reach-out-{int(time.time())}",
        },
        data=json.dumps(payload).encode("utf-8"),
    )
    try:
        with urllib.request.urlopen(req, timeout=35) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        content = (result.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
        if content:
            content = re.sub(r'^(Message|Output|Note|Here)[^:]*:\s*', '', content, flags=re.IGNORECASE)
            content = content.strip('"').strip()
            return content[:400] if len(content) > 400 else content
    except Exception as e:
        print(f"  [LLM error: {e}]", file=sys.stderr)

    return f"{name} has been thinking about you." if etype.lower() not in ("location", "object", "fae") else "Something stirs in the Academy."


# ── Send ───────────────────────────────────────────────────────────────────────

def send_text(message: str, bot_token: str, chat_id: str, dry_run: bool) -> bool:
    if dry_run:
        print(f"  [DRY RUN text] {message}")
        return True
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": message}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"  [text send error: {e}]", file=sys.stderr)
        return False


def send_voice(message: str, voice: str, chat_id: str, dry_run: bool) -> bool:
    tts_script = Path(__file__).parent / "multi_voice_tts.py"
    if dry_run:
        print(f"  [DRY RUN voice={voice}] {message}")
        return True
    if not tts_script.exists():
        print(f"  [TTS script not found: {tts_script}]", file=sys.stderr)
        return False
    try:
        result = subprocess.run(
            [sys.executable, str(tts_script),
             "--target",  chat_id,
             "--channel", TELEGRAM_CHANNEL,
             "--account", TELEGRAM_ACCOUNT,
             f"[{voice}]{message}"],
            capture_output=True, text=True, timeout=90,
        )
        return result.returncode == 0
    except Exception as e:
        print(f"  [voice send error: {e}]", file=sys.stderr)
        return False


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Narrative-weighted character outreach")
    parser.add_argument("--dry-run", action="store_true", help="Generate without sending")
    parser.add_argument("--force",   type=str, default=None, metavar="ENTITY",
                        help="Force a specific entity by name (prefix match)")
    args = parser.parse_args()

    bot_token, chat_id = get_telegram_credentials()
    if not chat_id or not bot_token:
        missing = []
        if not chat_id:
            missing.append("chat_id")
        if not bot_token:
            missing.append("bot_token")
        print(f"Missing Telegram credentials: {', '.join(missing)}", file=sys.stderr)
        if not args.dry_run:
            sys.exit(1)

    entities = parse_world_register()
    if not entities:
        print("No entities found in world register.")
        return

    voices = parse_voice_assignments()
    log    = load_log()

    entity = pick_entity(entities, log, forced=args.force)
    if not entity:
        if not args.force and daily_count(log) >= DAILY_CAP:
            print(f"Daily cap ({DAILY_CAP}) reached. No outreach.")
        elif not args.force:
            print("No eligible entity — all on cooldown.")
        else:
            print(f"Entity not found: {args.force}", file=sys.stderr)
        return

    name  = entity["name"]
    voice = resolve_voice(name, voices)
    print(f"→ {name} ({entity['type']}, Belief {entity['belief']}) | voice: {voice}")

    message = generate_message(entity)
    print(f"  {message[:100]}{'...' if len(message) > 100 else ''}")

    text_ok  = send_text(message, bot_token, chat_id, args.dry_run)
    voice_ok = send_voice(message, voice, chat_id, args.dry_run)

    if not args.dry_run:
        if text_ok or voice_ok:
            record_contact(name, log)
            save_log(log)
        status = f"text={'ok' if text_ok else 'FAIL'}, voice={'ok' if voice_ok else 'FAIL'}"
        print(f"  {'✓' if text_ok or voice_ok else '✗'} {status}")


if __name__ == "__main__":
    main()

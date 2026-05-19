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
import importlib.util
import json
import os
import random
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

BASE_DIR          = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR / "scripts"))
import cron_steward

_OUTREACH_MEMORY_SPEC = importlib.util.spec_from_file_location(
    "outreach_memory",
    BASE_DIR / "scripts" / "outreach-memory.py",
)
outreach_memory = importlib.util.module_from_spec(_OUTREACH_MEMORY_SPEC)
assert _OUTREACH_MEMORY_SPEC.loader is not None
_OUTREACH_MEMORY_SPEC.loader.exec_module(outreach_memory)

CONFIG_DIR        = BASE_DIR / "config"
LOG_FILE          = CONFIG_DIR / "reach-out-log.json"
WORLD_REGISTER    = BASE_DIR / "lore" / "world-register.md"
VOICE_ASSIGNMENTS = CONFIG_DIR / "voice-assignments.md"
ARC_SPINE         = BASE_DIR / "memory" / "arc-spine.md"
CHARACTERS_FILE   = BASE_DIR / "lore" / "characters.md"

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


def _normalize_gateway_model(model: str) -> str:
    model = (model or "").strip()
    if model == "openclaw" or model.startswith("openclaw/"):
        return model
    return "openclaw"


def _oc_gateway_cfg() -> tuple[int, str, str, int]:
    """Return (port, token, model, timeout) for small outreach generation."""
    cfg = _load_openclaw_cfg()
    secrets = _load_secrets()
    port = cfg.get("gateway", {}).get("port", 18789)
    token = cfg.get("gateway", {}).get("auth", {}).get("token", "")
    raw_model = (
        os.environ.get("OUTREACH_MODEL")
        or secrets.get("OUTREACH_MODEL")
        or os.environ.get("NPC_RESEARCH_MODEL")
        or secrets.get("NPC_RESEARCH_MODEL")
        or os.environ.get("BLEED_MODEL")
        or secrets.get("BLEED_MODEL")
        or "openclaw"
    )
    model = _normalize_gateway_model(raw_model)
    timeout_raw = (
        os.environ.get("OUTREACH_TIMEOUT")
        or secrets.get("OUTREACH_TIMEOUT")
        or os.environ.get("NPC_RESEARCH_TIMEOUT")
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

def _character_lore(name: str) -> str:
    """Extract the character's description section from lore/characters.md."""
    if not CHARACTERS_FILE.exists():
        return ""
    text = CHARACTERS_FILE.read_text()
    # Try to find a section or bullet that mentions this name
    # Match a heading line containing the name, then grab up to 8 following lines
    pattern = re.compile(
        r'(?:^#{1,4}[^\n]*' + re.escape(name) + r'[^\n]*\n)((?:[^\n]*\n){0,8})',
        re.IGNORECASE | re.MULTILINE,
    )
    m = pattern.search(text)
    if m:
        return m.group(0).strip()[:600]
    # Fallback: look for a bold name entry
    pattern2 = re.compile(
        r'(?:^\*\*' + re.escape(name) + r'\*\*[^\n]*\n?(?:[^\n]*\n){0,4})',
        re.IGNORECASE | re.MULTILINE,
    )
    m2 = pattern2.search(text)
    if m2:
        return m2.group(0).strip()[:600]
    return ""


def _clean_agent_output(text: str) -> str:
    text = re.sub(r'\x1b\[[0-9;]*m', '', text or "")
    noise = ("[plugins]", "[agents/", "[agent/", "adopted ", "google tool", "[lcm]")
    lines = [
        line for line in text.splitlines()
        if not any(line.strip().lower().startswith(prefix) for prefix in noise)
    ]
    return "\n".join(lines).strip()


def _call_llm(prompt: str) -> str:
    """Generate text through the OpenClaw gateway without spawning agents."""
    port, token, model, timeout = _oc_gateway_cfg()
    url = f"http://127.0.0.1:{port}/v1/chat/completions"
    session_key = f"outreach-{int(time.time())}"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You write brief in-world Telegram outreach notes from Enchantify Academy. "
                    "The note should feel like a tiny personal interruption from a living world: "
                    "specific, atmospheric, and in character. Reply only with the spoken message."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.82,
        "max_tokens": 220,
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
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"Gateway returned HTTP {e.code}: {body}") from e
    except Exception as e:
        raise RuntimeError(f"Gateway call failed: {e}") from e

    return _clean_agent_output(
        result.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )


def _bad_model_output(content: str) -> bool:
    text = (content or "").strip().lower()
    if not text:
        return True
    blocked = [
        "not logged in",
        "please run /login",
        "output only",
        "as an ai",
        "i can't",
        "i cannot",
        "thinking about you",
    ]
    return any(needle in text for needle in blocked)


def _clean_message_content(content: str) -> str:
    content = _clean_agent_output(content)
    content = re.sub(r'^(Message|Output|Note|Here(?:\'s| is)?(?: the)? message)[^:]*:\s*', '', content, flags=re.IGNORECASE)
    content = re.sub(r'^["“”\'\s]+|["“”\'\s]+$', '', content)
    content = content.replace("*", "")
    content = re.sub(r'\s+', ' ', content).strip()
    return content


def model_smoke_test() -> int:
    port, _token, model, timeout = _oc_gateway_cfg()
    print(f"OUTREACH_MODEL={model}")
    print(f"OUTREACH_GATEWAY=127.0.0.1:{port}")
    print(f"OUTREACH_TIMEOUT={timeout}")
    try:
        reply = _call_llm("Reply with exactly: OUTREACH_OK")
    except Exception as e:
        print(f"FAIL: {e}")
        return 1
    print(reply[:200] or "(empty)")
    return 0 if "OUTREACH_OK" in reply else 1


def generate_message(entity: dict) -> str:
    name, etype, belief, notes = entity["name"], entity["type"], entity["belief"], entity["notes"]
    context = _world_context()
    lore    = _character_lore(name)

    if etype.lower() in ("location", "object", "fae", "thread"):
        frame = (
            f"{name} is a {etype.lower()} in Enchantify Academy. {notes}\n"
            f"Write as if this {etype.lower()} itself sends a brief impression, feeling, or fragment "
            f"to the player — not a human voice, but a presence. It need not be a complete thought."
        )
    else:
        char_desc = lore or notes or "a character at Enchantify Academy"
        frame = (
            f"{name}:\n{char_desc}\n\n"
            f"Write as {name} speaking directly to bj in first person."
        )

    prompt = f"""You are writing an in-character voice-note message from {name} to bj, a student at Enchantify Academy.

{frame}
Narrative Weight (Belief): {belief}
{context}

Rules:
- 2 to 4 sentences maximum, 45 to 95 words
- Speak naturally, as if leaving a voice note — direct, specific, personal
- Include at least one concrete detail from the Academy, the entity notes, or recent world context
- It may be warm, funny, eerie, practical, or sideways; do not make every outreach dramatic
- Stay entirely in character: use their speech patterns, concerns, and world-view
- Do not reference "the game", "the story", or "the session" as meta concepts
- No asterisks, no stage directions, no action text
- Do not explain why you are reaching out; let it be felt
- Do not use the phrase "thinking about you"

Output ONLY the spoken text. Nothing else."""

    try:
        content = _clean_message_content(_call_llm(prompt))
        if content and not _bad_model_output(content):
            if content and not _bad_model_output(content):
                return content[:650]
    except Exception as e:
        print(f"  [LLM error: {e}]", file=sys.stderr)

    return build_fallback_message(entity, context, lore)


def build_fallback_message(entity: dict, context: str, lore: str) -> str:
    """A small, specific message when the model path is unavailable."""
    name, etype, notes = entity["name"], entity["type"], entity["notes"]
    detail = notes or lore or "the Academy has been unusually awake today"
    detail = re.sub(r'\s+', ' ', detail).strip()
    detail = re.sub(r'\[[^\]]+\]\s*', '', detail).strip()
    detail = detail.rstrip(".; ")
    if len(detail) > 120:
        detail = detail[:117].rstrip(" .;") + "..."

    if etype.lower() == "thread":
        return (
            f"The thread called {name} tugged the margin just now. {detail} "
            "It did not ask for a grand decision; it only left a small loose end where your hand might find it later."
        )
    if etype.lower() == "location":
        return (
            f"{name} shifted while no one was watching. {detail} "
            "A chair scraped, a lamp steadied itself, and the room kept one place open as if it expected you to notice."
        )
    if etype.lower() in ("object", "tool"):
        return (
            f"{name} made itself noticeable at the edge of the page. {detail} "
            "Not urgent, not loud; just the particular weight of an object that has decided it belongs in your day."
        )
    if etype.lower() == "fae":
        return (
            f"{name} passed close enough to stir the ink. {detail} "
            "It left no bargain on the table, only a sign that the small powers are awake and keeping their own accounts."
        )
    return (
        f"{name} left a note in the margin before returning to the corridor. "
        f"{detail}. No ceremony, no summons; just a small true thing sent while the Academy was between one breath and the next."
    )


# ── Send ───────────────────────────────────────────────────────────────────────

def format_text_delivery(sender: str, message: str) -> str:
    sender = (sender or "The Academy").strip()
    message = (message or "").strip()
    return f"From {sender}:\n\n{message}" if message else f"From {sender}."


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
             "--audio-only",
             f"[{voice}] {message}"],
            capture_output=True, text=True, timeout=180,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            if detail:
                print(f"  [voice send error: {detail[:240]}]", file=sys.stderr)
            return False
        return True
    except Exception as e:
        print(f"  [voice send error: {e}]", file=sys.stderr)
        return False


def record_outreach_memory(entity: dict, message: str, voice: str, text_ok: bool, voice_ok: bool) -> None:
    try:
        args = argparse.Namespace(
            player="bj",
            sender=entity.get("name", ""),
            entity_type=entity.get("type", ""),
            belief=int(entity.get("belief") or 0),
            voice=voice,
            message=message,
            text_ok=text_ok,
            voice_ok=voice_ok,
            source="reach-out",
        )
        outreach_memory.record_sent(args)
    except Exception as exc:
        print(f"  [outreach memory error: {exc}]", file=sys.stderr)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Narrative-weighted character outreach")
    parser.add_argument("--dry-run", action="store_true", help="Generate without sending")
    parser.add_argument("--force",   type=str, default=None, metavar="ENTITY",
                        help="Force a specific entity by name (prefix match)")
    parser.add_argument("--model-smoke", action="store_true", help="Check the configured gateway model and exit")
    args = parser.parse_args()

    if args.model_smoke:
        sys.exit(model_smoke_test())

    with cron_steward.run("reach-out", dry_run=args.dry_run, forced=bool(args.force)):
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
            cron_steward.mark_skipped("reach-out", "no entities")
            return

        voices = parse_voice_assignments()
        log    = load_log()

        entity = pick_entity(entities, log, forced=args.force)
        if not entity:
            if not args.force and daily_count(log) >= DAILY_CAP:
                reason = f"daily cap ({DAILY_CAP}) reached"
                print(f"{reason}. No outreach.")
            elif not args.force:
                reason = "all eligible entities on cooldown"
                print("No eligible entity — all on cooldown.")
            else:
                reason = f"entity not found: {args.force}"
                print(reason, file=sys.stderr)
            cron_steward.mark_skipped("reach-out", reason)
            return

        name  = entity["name"]
        voice = resolve_voice(name, voices)
        print(f"→ {name} ({entity['type']}, Belief {entity['belief']}) | voice: {voice}")

        message = generate_message(entity)
        print(f"  {message[:100]}{'...' if len(message) > 100 else ''}")

        skip, digest, reason = cron_steward.should_skip_duplicate(
            "reach-out",
            {"name": name, "message": message},
            cooldown_hours=24,
            force=bool(args.force),
            scope=name,
        )
        if skip and not args.dry_run:
            print(f"  ↺ Skipping duplicate outreach: {reason}")
            cron_steward.mark_skipped("reach-out", reason, scope=name, fingerprint=digest)
            return

        text_message = format_text_delivery(name, message)
        text_ok  = send_text(text_message, bot_token, chat_id, args.dry_run)
        voice_ok = send_voice(message, voice, chat_id, args.dry_run)

        if not args.dry_run:
            if text_ok or voice_ok:
                record_outreach_memory(entity, message, voice, text_ok, voice_ok)
                record_contact(name, log)
                save_log(log)
                cron_steward.mark_delivered(
                    "reach-out",
                    {"name": name, "message": message},
                    scope=name,
                    text_ok=text_ok,
                    voice_ok=voice_ok,
                )
            status = f"text={'ok' if text_ok else 'FAIL'}, voice={'ok' if voice_ok else 'FAIL'}"
            print(f"  {'✓' if text_ok or voice_ok else '✗'} {status}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
reach-out.py — Characters and Talismans initiate contact outside of sessions.

Called by cron (every 2 hours). Reads world state, evaluates trigger
conditions, picks one character to reach out (if warranted), generates
a short direct message via LLM, renders in their Kokoro voice, sends
as OGG voice note to Telegram.

This is NOT the Labyrinth narrator. These are characters speaking
directly to the player — no story frame, no session, just contact.

Usage:
    python3 scripts/reach-out.py
    python3 scripts/reach-out.py --dry-run
    python3 scripts/reach-out.py --force "Zara Finch"
    python3 scripts/reach-out.py --force "Duskthorn"
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR    = Path(__file__).parent.parent
CONFIG_DIR  = BASE_DIR / "config"
LOG_FILE    = CONFIG_DIR / "reach-out-log.json"
SECRETS     = CONFIG_DIR / "secrets.env"
HEARTBEAT   = BASE_DIR / "HEARTBEAT.md"
ARC_SPINE   = BASE_DIR / "memory" / "arc-spine.md"
APP_REG     = BASE_DIR / "lore" / "app-register.md"
NOTHING_FILE = BASE_DIR / "lore" / "nothing-intelligence.md"

TELEGRAM_CHANNEL = "telegram"
TELEGRAM_ACCOUNT = "enchantify"
DAILY_CAP        = 2   # max outreach voice notes per day, all characters combined


# ── Voice assignments (Kokoro voice IDs) ──────────────────────────────────────

CHARACTER_VOICES = {
    # Characters — from config/voice-assignments.md
    "Zara Finch":            "af_nicole",       # warm, headphone-intimate, Tidecrest
    "Wicker Eddies":         "am_liam",          # charismatic charm (simplified from am_liam+am_fenrir blend)
    "Headmistress Thorne":   "af_v0irulan",     # otherworldly, weighted, ancient silk
    # Chapter Talismans — voiced by their chapter head
    "Emberheart":            "af_sky",           # Prof. Nightshade's voice — competitive, a dare
    "Mossbloom":             "bm_fable",         # Prof. Stonebrook's voice — slow, contemplative
    "Riddlewind":            "bm_george",        # Prof. Thickets's primary voice — warm, enigmatic
    "Tidecrest":             "af_heart",         # Prof. Wispwood's voice — spontaneous, sparking
    "Duskthorn":             "am_fenrir",        # Prof. Momort's voice — deep, measured, shadowed
}

# ── Minimum hours between contacts per character ──────────────────────────────

CHARACTER_COOLDOWNS = {
    "Zara Finch":            48,
    "Wicker Eddies":         72,
    "Headmistress Thorne":   168,  # once a week at most
    "Emberheart":            36,
    "Mossbloom":             72,
    "Riddlewind":            48,
    "Tidecrest":             20,   # can be near-daily — impulsive by nature
    "Duskthorn":             36,
}

# ── Who they are (for LLM prompt context) ─────────────────────────────────────

CHARACTER_CONTEXT = {
    "Zara Finch":
        "House guide and first friend at Enchantify Academy. Warm, curious, fiercely loyal. "
        "Texts like a friend who genuinely cares — excited, slightly anxious, real. "
        "Never formal. Would use 'hey' or 'just wanted to say.'",
    "Wicker Eddies":
        "Primary antagonist. Duskthorn chapter. Charismatic, cunning, always three moves ahead. "
        "Texts with polite menace — never directly threatening, always implying he knows more than you do. "
        "Smooth. Unsettling. Would never use exclamation points.",
    "Headmistress Thorne":
        "Leads the Academy. Sees the Unwritten Chapter. Ancient, formidable, almost never reaches out directly. "
        "When she does, one or two sentences that shift the entire arc. "
        "No small talk. Everything she says has weight.",
    "Emberheart":
        "The chapter of self-authorship — we write our own story. "
        "Direct, unhedged, says the specific uncomfortable true thing the player already knows. "
        "Sounds like the voice in your head you keep ignoring. Never cruel, always clear.",
    "Mossbloom":
        "The chapter of surrender and reception — a third party writes the story. "
        "Patient, ancient-feeling, asks questions that stay with you for days. "
        "Texts like a slow river. Never urgent. Somehow always arrives at the right time.",
    "Riddlewind":
        "The chapter of co-authorship — we write the story together. "
        "Warm, reaching, notices when the player has been isolated or working alone too long. "
        "Texts like someone who genuinely wants to collaborate and misses the conversation.",
    "Tidecrest":
        "The chapter of presence — there is no story, only now. "
        "Impulsive, timestamped, catches the moment before it passes. "
        "Texts at odd hours. Never explains itself. Short. Pointed. Sometimes just a time and a fragment.",
    "Duskthorn":
        "The chapter of productive conflict — no story without friction. "
        "Sees the avoidances, the pile-ups, the things the player has been putting off. "
        "Texts with pointed precision. Never unkind, but never lets you off the hook either.",
}


# ── World state ────────────────────────────────────────────────────────────────

def _load_secrets() -> dict:
    secrets = {}
    if SECRETS.exists():
        for line in SECRETS.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                secrets[k.strip()] = v.strip().strip('"')
    return secrets


def load_world_state(player_name: str) -> dict:
    state = {
        "player_name":        player_name,
        "belief":             10,
        "days_since_session": 0,
        "arc_phase":          "SETUP",
        "nothing_pressure":   "moderate",
        "compass_runs":       0,
        "hour":               datetime.now().hour,
        "weather":            "",
        "dominant_chapter":   "",
        "last_alive_moment":  "",
    }

    # Player file
    player_file = BASE_DIR / "players" / f"{player_name.lower()}.md"
    if player_file.exists():
        text = player_file.read_text()
        m = re.search(r'\*\*Belief:\*\*\s*(\d+)', text)
        if m:
            state["belief"] = int(m.group(1))
        m = re.search(r'Compass Runs:\s*(\d+)', text)
        if m:
            state["compass_runs"] = int(m.group(1))

    # Arc spine
    if ARC_SPINE.exists():
        text = ARC_SPINE.read_text()
        m = re.search(r'^## Last Session\s*\n\*(\d{4}-\d{2}-\d{2})', text, re.MULTILINE)
        if m:
            try:
                last = datetime.strptime(m.group(1).strip(), "%Y-%m-%d")
                state["days_since_session"] = (datetime.now() - last).days
            except ValueError:
                pass
        m = re.search(r'Phase:\s*(\w+)', text, re.IGNORECASE)
        if m:
            state["arc_phase"] = m.group(1).upper()
        m = re.search(r'most alive moment[^\n]*:\s*([^\n]+)', text, re.IGNORECASE)
        if m:
            state["last_alive_moment"] = m.group(1).strip()[:120]

    # Nothing pressure
    if NOTHING_FILE.exists():
        nt = NOTHING_FILE.read_text()
        p = re.search(r'\*\*([^*]+)\*\*\s*—', nt)
        if p:
            state["nothing_pressure"] = p.group(1).strip().lower()

    # Heartbeat — weather
    if HEARTBEAT.exists():
        hb = HEARTBEAT.read_text()
        m = re.search(r'(?:condition|weather)[:\s]+([^\n,|]+)', hb, re.IGNORECASE)
        if m:
            state["weather"] = m.group(1).strip()

    # App register — dominant chapter (most controlled apps)
    if APP_REG.exists():
        text = APP_REG.read_text()
        counts: dict = {}
        for m in re.finditer(r'\|\s*(\w+)\s*\(\w+\)\s*\|?\s*$', text, re.MULTILINE):
            ch = m.group(1)
            counts[ch] = counts.get(ch, 0) + 1
        if counts:
            state["dominant_chapter"] = max(counts, key=lambda k: counts[k])

    return state


# ── Trigger conditions ─────────────────────────────────────────────────────────

def should_reach_out(character: str, state: dict) -> tuple:
    """Returns (bool, reason_string). Reason feeds directly into LLM prompt."""
    days    = state["days_since_session"]
    belief  = state["belief"]
    hour    = state["hour"]
    nothing = state["nothing_pressure"]
    phase   = state["arc_phase"]
    dom     = state["dominant_chapter"]
    weather = state["weather"].lower()
    runs    = state["compass_runs"]

    if character == "Zara Finch":
        if days >= 4:
            return True, f"the player hasn't been back in {days} days and Zara is starting to worry"
        if belief >= 72 and runs > 0:
            return True, f"the player's belief has climbed to {belief} and they've been running the Compass — Zara is proud and wants them to know it"
        return False, ""

    if character == "Wicker Eddies":
        if belief >= 60 and days <= 1:
            return True, f"the player's belief is at {belief} — Wicker has been watching and he wants them to know it"
        if dom == "Duskthorn":
            return True, "Duskthorn holds more territory than any other chapter — Wicker is enjoying this"
        if days >= 6:
            return True, f"the player has been gone {days} days — Wicker breaks the silence in his own way"
        return False, ""

    if character == "Headmistress Thorne":
        if phase == "CLIMAX" and belief >= 65:
            return True, "the arc is at its climax and the player's belief is high — Thorne acknowledges what is happening"
        if belief >= 85:
            return True, f"belief has reached {belief} — Thorne does not miss this"
        return False, ""

    if character == "Emberheart":
        if days >= 3 and belief < 45:
            return True, f"the player has been away {days} days and their belief has dropped to {belief} — Emberheart will not let this stand quietly"
        if phase == "CLIMAX":
            return True, "the arc is at its climax — Emberheart wants the player to act, not wait"
        return False, ""

    if character == "Mossbloom":
        if 5 <= hour <= 7:
            return True, "early morning — Mossbloom's hour — a question that arrives before the day gets loud"
        if days >= 5:
            return True, f"the player has been away {days} days — Mossbloom noticed the quiet and wants to ask about it"
        return False, ""

    if character == "Riddlewind":
        if days >= 3 and dom != "Riddlewind":
            return True, f"the player has been away {days} days and Riddlewind is losing ground — it reaches out"
        if days >= 5:
            return True, f"the player has been isolated for {days} days — Riddlewind misses the collaboration"
        return False, ""

    if character == "Tidecrest":
        if 22 <= hour or hour <= 1:
            return True, f"it is {datetime.now().strftime('%H:%M')} — a late-night impulse moment — Tidecrest acts before it passes"
        if any(w in weather for w in ["storm", "rain", "thunder", "lightning", "wind"]):
            return True, f"the weather is {state['weather']} — Tidecrest responds to the atmosphere"
        return False, ""

    if character == "Duskthorn":
        if nothing in ("high", "critical", "overwhelming"):
            return True, f"nothing pressure is {nothing} — Duskthorn is awake and wants to talk about it"
        if days >= 3 and belief < 35:
            return True, f"the player has been gone {days} days and belief is at {belief} — Duskthorn sees the pile and will name it"
        return False, ""

    return False, ""


# ── LLM message generation ─────────────────────────────────────────────────────

def generate_message(character: str, state: dict, trigger_reason: str) -> str:
    if not shutil.which("openclaw"):
        return _fallback_message(character)

    player  = state["player_name"]
    belief  = state["belief"]
    days    = state["days_since_session"]
    weather = state["weather"] or "unknown"
    alive   = state["last_alive_moment"]
    char_ctx = CHARACTER_CONTEXT.get(character, character)

    alive_line = f'\nThe most alive moment from their last session was: "{alive}"' if alive else ""

    prompt = f"""You are {character} from Enchantify Academy. You are reaching out directly to {player} right now — outside of any open session, no narrator, no story frame. Just you, speaking directly to them via a voice note.

Who you are: {char_ctx}

Why you're reaching out: {trigger_reason}
{player}'s current Belief: {belief}
Days since their last session: {days}
Current weather in their world: {weather}{alive_line}

Write the message {character} would leave as a voice note right now.

Rules:
- Speak AS {character} in first person — not about them, not narrated
- 1 to 3 sentences. No more.
- Do not reference "the game", "the story", "the session" as meta concepts — you are real
- Do not use asterisks, stage directions, or action text
- Make it feel like actual speech — direct, specific, personal
- Under 55 words
- If it helps, reference something specific from the trigger context

Output ONLY the spoken message. Nothing else. No labels, no quotes around it."""

    try:
        result = subprocess.run(
            ["openclaw", "agent", "--local", "--prompt", prompt],
            capture_output=True, text=True, timeout=35
        )
        if result.returncode == 0 and result.stdout.strip():
            msg = result.stdout.strip()
            # Strip any preamble the LLM might add
            msg = re.sub(r'^(Message|Output|Note|Here)[^:]*:\s*', '', msg, flags=re.IGNORECASE)
            msg = msg.strip('"').strip()
            if len(msg) > 400:
                msg = msg[:397] + "..."
            return msg
    except Exception:
        pass

    return _fallback_message(character)


def _fallback_message(character: str) -> str:
    fallbacks = {
        "Zara Finch":            "Hey. Just — thinking about you. Are you doing okay?",
        "Wicker Eddies":         "I noticed. Most people don't last this long. Interesting.",
        "Headmistress Thorne":   "You have been seen. That is not a small thing.",
        "Emberheart":            "You already know what you've been avoiding. So do I.",
        "Mossbloom":             "What are you carrying today that you could set down?",
        "Riddlewind":            "Someone out there is working on the same thing you are. Reach out.",
        "Tidecrest":             f"{datetime.now().strftime('%H:%M')} — don't overthink this.",
        "Duskthorn":             "The pile is still there. It got heavier while you were away.",
    }
    return fallbacks.get(character, "Something stirs in the Academy.")


# ── Cooldown management ────────────────────────────────────────────────────────

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


def is_on_cooldown(character: str, log: dict) -> bool:
    last = log.get(character)
    if not last:
        return False
    cooldown_h = CHARACTER_COOLDOWNS.get(character, 48)
    try:
        return datetime.now() - datetime.fromisoformat(last) < timedelta(hours=cooldown_h)
    except Exception:
        return False


def daily_count(log: dict) -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    return log.get(f"daily_{today}", 0)


def record_contact(character: str, log: dict) -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    log[character] = datetime.now().isoformat()
    log[f"daily_{today}"] = daily_count(log) + 1


# ── Send ───────────────────────────────────────────────────────────────────────

def send_voice_message(character: str, message: str, telegram_target: str, dry_run: bool) -> bool:
    voice      = CHARACTER_VOICES.get(character, "bm_lewis")
    tts_script = Path(__file__).parent / "multi_voice_tts.py"

    if dry_run:
        print(f"  [DRY RUN] voice={voice}")
        print(f"  [DRY RUN] message: {message}")
        return True

    if not tts_script.exists():
        print(f"TTS script not found: {tts_script}", file=sys.stderr)
        return False

    try:
        result = subprocess.run(
            [sys.executable, str(tts_script),
             "--target",  telegram_target,
             "--channel", TELEGRAM_CHANNEL,
             "--account", TELEGRAM_ACCOUNT,
             f"[{voice}]{message}"],
            capture_output=True, text=True, timeout=90
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Send error: {e}", file=sys.stderr)
        return False


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Character outreach — voice notes from the Academy")
    parser.add_argument("--dry-run", action="store_true", help="Generate without sending")
    parser.add_argument("--force",   type=str, default=None,
                        metavar="CHARACTER", help="Force a specific character regardless of triggers")
    parser.add_argument("--player",  type=str, default=None, help="Player name")
    args = parser.parse_args()

    # Resolve player name
    player = args.player
    if not player:
        secrets = _load_secrets()
        player = secrets.get("ENCHANTIFY_DEFAULT_PLAYER", "wanderer")

    # Resolve Telegram target
    secrets = _load_secrets()
    telegram_target = secrets.get("TELEGRAM_CHAT_ID", "")
    if not telegram_target:
        print("TELEGRAM_CHAT_ID not set in config/secrets.env — cannot send.", file=sys.stderr)
        if not args.dry_run:
            sys.exit(1)

    state = load_world_state(player)
    log   = load_log()

    # Check daily cap
    if not args.force and daily_count(log) >= DAILY_CAP:
        print(f"Daily cap ({DAILY_CAP}) reached. No outreach.")
        return

    # Evaluate candidates in priority order
    candidates = [args.force] if args.force else list(CHARACTER_VOICES.keys())

    for character in candidates:
        if character not in CHARACTER_VOICES:
            print(f"Unknown character: {character}", file=sys.stderr)
            continue

        if not args.force and is_on_cooldown(character, log):
            continue

        should, reason = should_reach_out(character, state)
        if not should and not args.force:
            continue

        if args.force and not reason:
            reason = f"forced outreach — {character} has something to say"

        print(f"→ {character} reaches out: {reason}")

        message = generate_message(character, state, reason)
        print(f"  message: {message[:80]}{'...' if len(message) > 80 else ''}")

        success = send_voice_message(character, message, telegram_target, args.dry_run)

        if success and not args.dry_run:
            record_contact(character, log)
            save_log(log)
            print(f"  ✓ Sent and logged.")
        elif not success:
            print(f"  ✗ Send failed.", file=sys.stderr)

        # One character per run (unless forced)
        if not args.force:
            break
    else:
        if not args.force:
            print("No character triggered outreach this cycle.")


if __name__ == "__main__":
    main()

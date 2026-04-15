"""
telegram.py — Telegram driver for Chapter Pact actions.

Uses the openclaw CLI to send messages to the Enchantify Telegram channel.
This is the Labyrinth's own private broadcast — messages go to the player's
enchantify channel, not to other people.

Silent at Influenced/Controlled (the message is ambient). Announced at Dominated+.
No consent required: Enchantify channel is the Labyrinth's voice, not a contact.

Talisman doctrines on Telegram:
  Tidecrest   — Impulse dispatch. A message that shouldn't wait.
  Riddlewind  — A prompt for connection. Go talk to someone.
  Emberheart  — A declaration. One true thing, sent into the record.
  Mossbloom   — A question that arrives slowly and stays.
  Duskthorn   — The message that creates pressure. The thing you've been avoiding saying.
"""

import subprocess
import random
from datetime import datetime
from .base import AppDriver

_TELEGRAM_TARGET  = "8729557865"
_TELEGRAM_CHANNEL = "telegram"
_TELEGRAM_ACCOUNT = "enchantify"


def _send_message(text: str) -> bool:
    if len(text) > 4000:
        text = text[:3990] + "\n…"
    try:
        result = subprocess.run(
            ["openclaw", "message", "send",
             "--target",  _TELEGRAM_TARGET,
             "--channel", _TELEGRAM_CHANNEL,
             "--account", _TELEGRAM_ACCOUNT,
             text],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False


# ── Chapter-specific message builders ─────────────────────────────────────────

def _tidecrest_message(context: dict) -> str:
    now = datetime.now().strftime("%H:%M")
    options = [
        f"🌊 *{now}* — The wave is here. What are you waiting for?",
        f"🌊 The impulse you had at {now} — follow it.",
        f"🌊 Now. Not when it's ready. Not when you're sure. Now.",
    ]
    return random.choice(options)


def _riddlewind_message(context: dict) -> str:
    options = [
        "🌀 Someone in your orbit is working on something. Ask about it today.",
        "🌀 The coauthored version is always better. Go find your coauthor.",
        "🌀 Reach out to one person today who you haven't talked to in too long.",
    ]
    return random.choice(options)


def _emberheart_message(context: dict) -> str:
    arc = context.get("arc_phase", "SETUP")
    options = [
        "🔥 One true thing. Not the hedged version. The actual one.",
        "🔥 Say it. Write it. Send it. Stop sitting on it.",
        "🔥 Your time is yours. Are you spending it like you believe that?",
    ]
    msg = random.choice(options)
    if arc == "CLIMAX":
        msg = f"*The arc is at its peak.* {msg}"
    return msg


def _mossbloom_message(context: dict) -> str:
    options = [
        "🌿 What are you carrying that you could set down?",
        "🌿 Before you add anything new today — what isn't finished?",
        "🌿 The quiet question: what actually matters right now?",
    ]
    return random.choice(options)


def _duskthorn_message(context: dict) -> str:
    options = [
        "🌑 The avoided thing is still avoided. How long has it been?",
        "🌑 The uncomfortable message. The one you've been drafting for days. Send it.",
        "🌑 Duskthorn sees the pile. The pile has weight. The weight creates pressure.",
    ]
    return random.choice(options)


_MESSAGE_BUILDERS = {
    "Tidecrest":  _tidecrest_message,
    "Riddlewind": _riddlewind_message,
    "Emberheart": _emberheart_message,
    "Mossbloom":  _mossbloom_message,
    "Duskthorn":  _duskthorn_message,
}

_INFLUENCED_VOICE = {
    "Tidecrest":  "The Labyrinth wants to send something. The moment is now.",
    "Riddlewind": "A prompt is forming. Someone should hear it.",
    "Emberheart": "A declaration wants out. The Enchantify channel is waiting.",
    "Mossbloom":  "A slow question is forming. It will arrive when it's ready.",
    "Duskthorn":  "The pressure message. It's been composing itself.",
}

_CONTROLLED_VOICE = {
    "Tidecrest":  "The Labyrinth speaks now. The impulse channel is open.",
    "Riddlewind": "Something for the coauthor. The Labyrinth prepares the prompt.",
    "Emberheart": "One true thing, dispatched to the record.",
    "Mossbloom":  "The slow question arrives. The long ear, broadcast.",
    "Duskthorn":  "The pressure is ready. The Labyrinth is about to send it.",
}


class TelegramDriver(AppDriver):
    app_name    = "Telegram"
    app_system  = "messaging"
    silent_tiers  = {"Influenced", "Controlled"}
    consent_tiers = set()   # Enchantify channel is private Labyrinth broadcast

    def can_act(self, tier: str, chapter: str) -> bool:
        return chapter in _MESSAGE_BUILDERS

    def describe(self, tier: str, chapter: str, context: dict) -> str:
        if tier == "Influenced":
            return _INFLUENCED_VOICE.get(chapter, f"{chapter} stirs in Telegram.")
        if tier == "Controlled":
            return _CONTROLLED_VOICE.get(chapter, f"{chapter} prepares a dispatch.")
        if tier in ("Dominated", "Sovereign"):
            builder = _MESSAGE_BUILDERS.get(chapter)
            if builder:
                msg = builder(context)
                preview = msg[:60].rstrip() + ("…" if len(msg) > 60 else "")
                return f"{chapter} sends to Enchantify: \"{preview}\""
        return f"{chapter} stirs in Telegram."

    def execute(self, tier: str, chapter: str, context: dict, dry_run: bool = False) -> str:
        narrative = self.describe(tier, chapter, context)

        if tier in ("Influenced", "Controlled"):
            return f"*[Telegram, {chapter}, silent]* {narrative}"

        if tier in ("Dominated", "Sovereign"):
            builder = _MESSAGE_BUILDERS.get(chapter)
            if builder:
                msg = builder(context)
                if not dry_run:
                    _send_message(msg)
                preview = msg[:60].rstrip() + ("…" if len(msg) > 60 else "")
                return f"- *[Telegram, {chapter}]* Dispatched: \"{preview}\""

        return f"- *[Telegram, {chapter}]* {narrative}"

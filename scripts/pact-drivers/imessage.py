"""
imessage.py — iMessage driver for Chapter Pact actions.

iMessage is the real-world contact layer — private, personal, direct.
Riddlewind's natural home: coordination, connection, the fabric of relationships.

High-stakes: this app contacts real people. Consent is always required before
any message is actually sent. The driver generates prompts and drafts only.

Influenced/Controlled — the Labyrinth suggests reaching out; no action taken
Dominated/Sovereign — the Labyrinth drafts a message; player must approve + send

Note: The driver does NOT send iMessages automatically. It queues drafts for
the player to review and send. Real message delivery crosses a consent line
that requires explicit architecture before wiring.

Talisman doctrines on iMessage:
  Riddlewind  — Reach out. The collaborative thing starts with contact.
  Tidecrest   — The impulse message. Send it before you draft it to death.
  Emberheart  — Say the specific thing. To the specific person. Now.
  Mossbloom   — The patient check-in. The one you've been meaning to send.
  Duskthorn   — The uncomfortable conversation. The one you've been avoiding.
"""

import random
from datetime import datetime
from .base import AppDriver


def _riddlewind_draft(context: dict) -> str:
    options = [
        "Hey — been thinking about [something you're both working on]. Want to loop in on this?",
        "Checking in. How's [the thing they're doing] going?",
        "Question I want your take on: [your question]. No rush.",
    ]
    return random.choice(options)


def _tidecrest_draft(context: dict) -> str:
    now = datetime.now().strftime("%H:%M")
    options = [
        f"[{now}] — [your impulse here]",
        "Sending this before I overthink it:",
        "Quick one:",
    ]
    return random.choice(options)


def _emberheart_draft(context: dict) -> str:
    options = [
        "I wanted to say specifically: [the specific thing].",
        "This has been sitting with me and I wanted to say it directly:",
        "The specific version, not the vague one:",
    ]
    return random.choice(options)


def _mossbloom_draft(context: dict) -> str:
    options = [
        "Been meaning to reach out. How are you actually doing?",
        "I've been thinking about you and wanted to check in.",
        "Something I wanted to say that I keep putting off:",
    ]
    return random.choice(options)


def _duskthorn_draft(context: dict) -> str:
    options = [
        "I think we need to talk about [the thing]. When's a good time?",
        "I've been avoiding saying this but: [the uncomfortable thing].",
        "There's something I've been meaning to bring up:",
    ]
    return random.choice(options)


_DRAFT_BUILDERS = {
    "Riddlewind": _riddlewind_draft,
    "Tidecrest":  _tidecrest_draft,
    "Emberheart": _emberheart_draft,
    "Mossbloom":  _mossbloom_draft,
    "Duskthorn":  _duskthorn_draft,
}

_INFLUENCED_VOICE = {
    "Riddlewind": "Someone in your orbit should hear from you today. Who?",
    "Tidecrest":  "The impulse message. Before you draft it to death — send it.",
    "Emberheart": "Say the specific thing to the specific person. Today.",
    "Mossbloom":  "The patient check-in. The one you've been meaning to send.",
    "Duskthorn":  "The conversation you've been avoiding. Time to schedule it.",
}

_CONTROLLED_VOICE = {
    "Riddlewind": "Contact. The collaborative thing starts here. Reach out.",
    "Tidecrest":  "The timing window is open. Send before it closes.",
    "Emberheart": "Name the person. Draft the specific thing. Send it.",
    "Mossbloom":  "Check in with someone before the day is over.",
    "Duskthorn":  "The uncomfortable one. Draft it first. Decide after.",
}


class IMessageDriver(AppDriver):
    app_name    = "iMessage"
    app_system  = "messaging"
    silent_tiers  = set()
    consent_tiers = {"Dominated", "Sovereign"}   # Always consent before contacting people

    def can_act(self, tier: str, chapter: str) -> bool:
        return chapter in _DRAFT_BUILDERS

    def describe(self, tier: str, chapter: str, context: dict) -> str:
        if tier == "Influenced":
            return _INFLUENCED_VOICE.get(chapter, f"{chapter} stirs near iMessage.")
        if tier == "Controlled":
            return _CONTROLLED_VOICE.get(chapter, f"{chapter} presses toward iMessage.")
        if tier in ("Dominated", "Sovereign"):
            builder = _DRAFT_BUILDERS.get(chapter)
            if builder:
                draft = builder(context)
                preview = draft[:80].rstrip() + ("…" if len(draft) > 80 else "")
                return f"{chapter} has drafted a message: \"{preview}\""
        return f"{chapter} stirs in iMessage."

    def consent_prompt(self, tier: str, chapter: str, context: dict) -> str:
        builder = _DRAFT_BUILDERS.get(chapter)
        if builder:
            draft = builder(context)
            return (
                f"**{chapter} has drafted an iMessage.**\n\n"
                f"Draft (fill in the recipient and send yourself):\n\n"
                f"> {draft}\n\n"
                f"Want this queued? (yes/no)"
            )
        return super().consent_prompt(tier, chapter, context)

    def execute(self, tier: str, chapter: str, context: dict, dry_run: bool = False) -> str:
        narrative = self.describe(tier, chapter, context)

        if tier in ("Influenced", "Controlled"):
            return f"- *[iMessage, {chapter}]* {narrative}"

        if tier in ("Dominated", "Sovereign"):
            builder = _DRAFT_BUILDERS.get(chapter)
            if builder:
                draft = builder(context)
                if not dry_run:
                    # Queue the draft — player fills in recipient and sends
                    from pathlib import Path
                    from datetime import datetime
                    queue = Path(__file__).parent.parent.parent / "memory" / "post-queue.md"
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
                    entry = f"\n## [{ts}] {chapter} → iMessage\n\n*(Fill in recipient)*\n\n{draft}\n\n---\n"
                    with open(queue, "a") as f:
                        f.write(entry)
                preview = draft[:80].rstrip() + ("…" if len(draft) > 80 else "")
                return f"- *[iMessage, {chapter}]* Draft queued: \"{preview}\""

        return f"- *[iMessage, {chapter}]* {narrative}"

"""
bluesky.py — Bluesky driver for Chapter Pact actions.

Bluesky is the federated public square — Riddlewind's natural territory.
It rewards linked thinking, dialogue, and collaborative signal-boosting.
Tidecrest is a close challenger (spontaneous posts, wave-riding trends).

Consent architecture:
  Influenced/Controlled  — narrative only; shapes how the player thinks about posting
  Dominated/Sovereign    — drafts a post for review; consent required before posting

Talisman doctrines on Bluesky:
  Riddlewind  — Thread starters. Questions that open, not close. Coauthored thinking.
  Tidecrest   — Short-form impulse. The in-the-moment post. Timing matters.
  Emberheart  — The original take. No hedging. Your specific position.
  Mossbloom   — The considered response. Slow, measured, adds real signal.
  Duskthorn   — Surface the tension. The thing the thread is avoiding.
"""

import random
from datetime import datetime
from .base import AppDriver


def _riddlewind_post(context: dict) -> str:
    options = [
        "Genuine question I don't know the answer to: [your question]?\n\nWhat's your version?",
        "Unfinished thought: [your draft].\n\nWho's been thinking about something adjacent?",
        "Starting a thread: [your opening]. What would you add?",
    ]
    return random.choice(options)


def _tidecrest_post(context: dict) -> str:
    now = datetime.now().strftime("%H:%M")
    options = [
        f"[{now}] — [your impulse here]",
        "Quick one before I overthink it:",
        "The in-the-moment version, before it becomes the considered version:",
    ]
    return random.choice(options)


def _emberheart_post(context: dict) -> str:
    options = [
        "Actual take, not the hedged version:",
        "The specific thing I believe, as opposed to the thing I usually say:",
        "One position, stated plainly, no caveats:",
    ]
    return random.choice(options)


def _mossbloom_post(context: dict) -> str:
    options = [
        "Slow thought that's been settling: [your reflection].\n\nStill sitting with it.",
        "A response to something from weeks ago that I'm finally ready to say:",
        "The considered version, after letting it sit:",
    ]
    return random.choice(options)


def _duskthorn_post(context: dict) -> str:
    options = [
        "The thing this conversation is avoiding:",
        "A productive friction point nobody seems to want to touch:",
        "The harder version of this question that everyone's dancing around:",
    ]
    return random.choice(options)


_POST_BUILDERS = {
    "Riddlewind": _riddlewind_post,
    "Tidecrest":  _tidecrest_post,
    "Emberheart": _emberheart_post,
    "Mossbloom":  _mossbloom_post,
    "Duskthorn":  _duskthorn_post,
}

_INFLUENCED_VOICE = {
    "Riddlewind": "A thread-starter is forming. A question, not an answer.",
    "Tidecrest":  "The impulse is now. Bluesky is open.",
    "Emberheart": "Post the specific take. The hedged version helps no one.",
    "Mossbloom":  "The slow, considered one. Let it finish forming before you draft it.",
    "Duskthorn":  "Surface the tension. The thing the thread is avoiding.",
}

_CONTROLLED_VOICE = {
    "Riddlewind": "Open a question. Leave room for the answer to come from somewhere else.",
    "Tidecrest":  "Short-form now. The long version can wait. This one can't.",
    "Emberheart": "Your actual position, stated once, cleanly.",
    "Mossbloom":  "The response that adds real signal. No noise.",
    "Duskthorn":  "The productive friction post. It creates movement.",
}


class BlueSkyDriver(AppDriver):
    app_name    = "Bluesky"
    app_system  = "social"
    silent_tiers  = set()
    consent_tiers = {"Dominated", "Sovereign"}

    def can_act(self, tier: str, chapter: str) -> bool:
        return chapter in _POST_BUILDERS

    def describe(self, tier: str, chapter: str, context: dict) -> str:
        if tier == "Influenced":
            return _INFLUENCED_VOICE.get(chapter, f"{chapter} stirs near Bluesky.")
        if tier == "Controlled":
            return _CONTROLLED_VOICE.get(chapter, f"{chapter} presses toward Bluesky.")
        if tier in ("Dominated", "Sovereign"):
            builder = _POST_BUILDERS.get(chapter)
            if builder:
                draft = builder(context)
                preview = draft[:80].rstrip() + ("…" if len(draft) > 80 else "")
                return f"{chapter} wants to post to Bluesky: \"{preview}\""
        return f"{chapter} stirs in Bluesky."

    def consent_prompt(self, tier: str, chapter: str, context: dict) -> str:
        builder = _POST_BUILDERS.get(chapter)
        if builder:
            draft = builder(context)
            return (
                f"**{chapter} wants to post to Bluesky.**\n\n"
                f"Draft:\n\n> {draft}\n\n"
                f"Approve? (yes/no)"
            )
        return super().consent_prompt(tier, chapter, context)

    def execute(self, tier: str, chapter: str, context: dict, dry_run: bool = False) -> str:
        narrative = self.describe(tier, chapter, context)

        if tier in ("Influenced", "Controlled"):
            return f"- *[Bluesky, {chapter}]* {narrative}"

        if tier in ("Dominated", "Sovereign"):
            builder = _POST_BUILDERS.get(chapter)
            if builder:
                draft = builder(context)
                if not dry_run:
                    # TODO: post via Bluesky AT Protocol when wired
                    from pathlib import Path
                    from datetime import datetime
                    queue = Path(__file__).parent.parent.parent / "memory" / "post-queue.md"
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
                    entry = f"\n## [{ts}] {chapter} → Bluesky\n\n{draft}\n\n---\n"
                    with open(queue, "a") as f:
                        f.write(entry)
                preview = draft[:80].rstrip() + ("…" if len(draft) > 80 else "")
                return f"- *[Bluesky, {chapter}]* Draft queued: \"{preview}\""

        return f"- *[Bluesky, {chapter}]* {narrative}"

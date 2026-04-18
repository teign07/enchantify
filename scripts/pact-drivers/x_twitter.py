"""
x_twitter.py — X / Twitter driver for Chapter Pact actions.

X is Duskthorn's natural home — conflict, pressure, provocation, the sharp edge
of an idea. Tidecrest is the main challenger (trend-riding, timing, immediacy).
Everyone else is fighting uphill here.

Consent architecture:
  All tiers — consent required for any actual post.
  Influenced/Controlled — narrative and suggestion only.
  Dominated/Sovereign — generates a draft, flags for consent.

High-stakes public platform. The Labyrinth does not post here without asking.

Talisman doctrines on X:
  Duskthorn   — The sharp take. The thing that creates productive conflict.
  Tidecrest   — Timing. Wave-riding. Post when it matters, not when it's polished.
  Emberheart  — The unpopular specific opinion. Stated once, not defended endlessly.
  Riddlewind  — The question that opens a thread. Set the hook, let others pull.
  Mossbloom   — The rare measured voice. Worth something precisely because it's slow.
"""

import random
from datetime import datetime
from .base import AppDriver


def _duskthorn_post(context: dict) -> str:
    options = [
        "Unpopular opinion that I think is actually correct:",
        "The sharp version of this debate that nobody wants to state plainly:",
        "What everyone's thinking but nobody's saying:",
    ]
    return random.choice(options)


def _tidecrest_post(context: dict) -> str:
    now = datetime.now().strftime("%H:%M")
    options = [
        f"[{now}] —",
        "The in-the-moment take, before it cools:",
        "Timing-sensitive. This will be less true in an hour:",
    ]
    return random.choice(options)


def _emberheart_post(context: dict) -> str:
    options = [
        "One take. Not defending it in the replies.",
        "The specific version, stated once:",
        "This is what I actually think. Make of it what you will:",
    ]
    return random.choice(options)


def _riddlewind_post(context: dict) -> str:
    options = [
        "Thread: [your question here]. What's your version?",
        "Opening a thread on something I don't have the answer to:",
        "Question for the room:",
    ]
    return random.choice(options)


def _mossbloom_post(context: dict) -> str:
    options = [
        "Slow take. Been thinking about this for weeks:",
        "The measured response, after waiting to see if it was still true:",
        "I don't post here often. When I do, it's because the thing can't wait anymore:",
    ]
    return random.choice(options)


_POST_BUILDERS = {
    "Duskthorn":  _duskthorn_post,
    "Tidecrest":  _tidecrest_post,
    "Emberheart": _emberheart_post,
    "Riddlewind": _riddlewind_post,
    "Mossbloom":  _mossbloom_post,
}

_INFLUENCED_VOICE = {
    "Duskthorn":  "Something sharp is forming. The productive conflict version.",
    "Tidecrest":  "Timing window. The wave is here. Post now or miss it.",
    "Emberheart": "One specific opinion. Stated once. Not defended endlessly.",
    "Riddlewind": "The thread-opener. A question, not an answer.",
    "Mossbloom":  "The rare measured voice. Worth something because it's infrequent.",
}

_CONTROLLED_VOICE = {
    "Duskthorn":  "X is ready for this. The conflict is productive. Say the sharp thing.",
    "Tidecrest":  "The moment is now. The edited version will be worse.",
    "Emberheart": "Your take, your voice, stated plainly once.",
    "Riddlewind": "Set the hook. Let others pull the thread.",
    "Mossbloom":  "Post only when it can't wait anymore. Is this that?",
}


class XTwitterDriver(AppDriver):
    app_name    = "X / Twitter"
    app_system  = "social"
    silent_tiers  = set()
    consent_tiers = {"Influenced", "Controlled", "Dominated", "Sovereign"}  # always consent
    USE_LLM     = True

    def can_act(self, tier: str, chapter: str) -> bool:
        return chapter in _POST_BUILDERS

    def describe(self, tier: str, chapter: str, context: dict) -> str:
        if tier == "Influenced":
            return _INFLUENCED_VOICE.get(chapter, f"{chapter} stirs near X.")
        if tier == "Controlled":
            return _CONTROLLED_VOICE.get(chapter, f"{chapter} reaches toward X.")
        if tier in ("Dominated", "Sovereign"):
            builder = _POST_BUILDERS.get(chapter)
            if builder:
                draft = builder(context)
                preview = draft[:80].rstrip() + ("…" if len(draft) > 80 else "")
                return f"{chapter} wants to post to X: \"{preview}\""
        return f"{chapter} stirs in X."

    def consent_prompt(self, tier: str, chapter: str, context: dict) -> str:
        if tier in ("Influenced", "Controlled"):
            voice = _INFLUENCED_VOICE.get(chapter) if tier == "Influenced" else _CONTROLLED_VOICE.get(chapter)
            return (
                f"**{chapter} is pressing toward X.**\n\n"
                f"{voice}\n\n"
                f"Want to act on this? (yes/no)"
            )
        builder = _POST_BUILDERS.get(chapter)
        if builder:
            draft = builder(context)
            return (
                f"**{chapter} wants to post to X.**\n\n"
                f"Draft:\n\n> {draft}\n\n"
                f"Approve? (yes/no)"
            )
        return super().consent_prompt(tier, chapter, context)

    def execute(self, tier: str, chapter: str, context: dict, dry_run: bool = False) -> str:
        narrative = self.describe(tier, chapter, context)

        if tier in ("Influenced", "Controlled"):
            # Consent required even here — if we're executing, player said yes
            return f"- *[X, {chapter}]* {narrative}"

        if tier in ("Dominated", "Sovereign"):
            builder = _POST_BUILDERS.get(chapter)
            if builder:
                draft = builder(context)
                if not dry_run:
                    # TODO: post via X API when wired
                    from pathlib import Path
                    from datetime import datetime
                    queue = Path(__file__).parent.parent.parent / "memory" / "post-queue.md"
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
                    entry = f"\n## [{ts}] {chapter} → X / Twitter\n\n{draft}\n\n---\n"
                    with open(queue, "a") as f:
                        f.write(entry)
                preview = draft[:80].rstrip() + ("…" if len(draft) > 80 else "")
                return f"- *[X, {chapter}]* Draft queued: \"{preview}\""

        return f"- *[X, {chapter}]* {narrative}"

    def capabilities(self) -> list:
        return [
            {
                "name": "draft_post",
                "description": "Draft a single X/Twitter post (max 280 chars) expressing the chapter's philosophy sharply",
                "params": {
                    "content": "the full post — complete thought, no placeholders, max 280 chars",
                },
            },
            {
                "name": "draft_thread_hook",
                "description": "Draft the opening post of a thread that provokes replies from the chapter's angle",
                "params": {
                    "content": "thread-opener — a question or statement that makes people want to respond",
                },
            },
        ]

    def execute_spec(self, spec: dict, dry_run: bool = False) -> str:
        action  = spec.get("action", "")
        chapter = spec.get("chapter", "Unknown")
        content = str(spec.get("content", ""))[:280]

        if action in ("draft_post", "draft_thread_hook") and content:
            if not dry_run:
                from pathlib import Path
                queue = Path(__file__).parent.parent.parent / "memory" / "post-queue.md"
                ts    = datetime.now().strftime("%Y-%m-%d %H:%M")
                entry = f"\n## [{ts}] {chapter} → X / Twitter ({action})\n\n{content}\n\n---\n"
                with open(queue, "a") as f:
                    f.write(entry)
            preview = content[:80].rstrip() + ("…" if len(content) > 80 else "")
            return f"- *[X, {chapter}]* Draft queued: \"{preview}\""

        return self.execute(
            spec.get("tier", "Dominated"),
            chapter,
            spec.get("context", {}),
            dry_run=dry_run,
        )

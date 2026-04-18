"""
moltbook.py — Moltbook driver for Chapter Pact actions.

Moltbook is the primary long-form social feed — the player's public voice.
Emberheart's natural home: self-expression, ownership of one's own narrative.
Duskthorn is close behind (Belief 16 vs 20 at game start) — it wants Moltbook
to become a pressure surface, not a self-expression space.

Consent architecture:
  Influenced/Controlled  — narrative only; suggestions what to post, not posting
  Dominated              — drafts a post for the player's review (consent required)
  Sovereign              — attempts to post directly (consent required)

The social implications of public posting mean consent is always required at
Dominated/Sovereign. The driver generates a draft and a consent_prompt.

Talisman doctrines on Moltbook:
  Emberheart  — Publish the specific thing. Not the safe version.
  Duskthorn   — Surface the uncomfortable truth. Create productive friction.
  Riddlewind  — Invite dialogue. Write the beginning, not the ending.
  Tidecrest   — Post the impulse. Before the edit. Before the doubt.
  Mossbloom   — The slow post. Measured. The one worth waiting for.
"""

import random
from datetime import datetime
from .base import AppDriver


def _riddlewind_post(context: dict) -> str:
    options = [
        "Thinking about: the gap between what we build alone and what we build together. What's your version of that?",
        "Unfinished thought I want to think out loud: [your draft]. Who's been working on something adjacent?",
        "The coauthored version is always better. Currently looking for a co-author for: [your draft].",
    ]
    return random.choice(options)


def _emberheart_post(context: dict) -> str:
    arc = context.get("arc_phase", "SETUP")
    options = [
        "The specific thing I actually believe right now, as opposed to the hedged version I usually say:",
        "Something I've been drafting in my head for a week and finally writing down:",
        "One true thing, sent before I talk myself out of the specific version:",
    ]
    draft = random.choice(options)
    if arc == "CLIMAX":
        draft = f"[Arc is peaking — this is the moment.]\n\n{draft}"
    return draft


def _mossbloom_post(context: dict) -> str:
    options = [
        "A slow question I've been sitting with: what are you carrying that you could set down?",
        "The thing I keep returning to, weeks later: [your reflection]. Still turning it over.",
        "Before I add anything new: here's something old that deserves another look.",
    ]
    return random.choice(options)


def _duskthorn_post(context: dict) -> str:
    options = [
        "The uncomfortable thing nobody wants to say out loud in this space:",
        "A piece of friction that I think is actually productive:",
        "The version of this conversation nobody's having yet:",
    ]
    return random.choice(options)


def _tidecrest_post(context: dict) -> str:
    now = datetime.now().strftime("%H:%M")
    options = [
        f"[{now}] Thought. Not fully formed. Posting before I overthink it:",
        f"Impulse post at {now} — the edited version would be worse:",
        f"Sending this before the second-guessing sets in:",
    ]
    return random.choice(options)


_POST_BUILDERS = {
    "Emberheart": _emberheart_post,
    "Duskthorn":  _duskthorn_post,
    "Riddlewind": _riddlewind_post,
    "Tidecrest":  _tidecrest_post,
    "Mossbloom":  _mossbloom_post,
}

_INFLUENCED_VOICE = {
    "Emberheart": "A post is forming. The specific version, not the safe one.",
    "Duskthorn":  "Something on Moltbook wants to be said. The uncomfortable version.",
    "Riddlewind": "Write the beginning of a conversation. Let someone else write the ending.",
    "Tidecrest":  "Post the impulse. Before the edit.",
    "Mossbloom":  "The measured post. The one worth waiting for. Start drafting.",
}

_CONTROLLED_VOICE = {
    "Emberheart": "The draft exists. Say the specific thing. Not the hedged version.",
    "Duskthorn":  "Moltbook is ready for friction. The productive kind.",
    "Riddlewind": "Invite dialogue. The coauthored conversation starts with your opening line.",
    "Tidecrest":  "Now. Not when it's fully formed. The half-formed version is the honest one.",
    "Mossbloom":  "The archive speaks. Find the old draft. Finish it. Send it.",
}


class MoltbookDriver(AppDriver):
    app_name    = "Moltbook"
    app_system  = "social"
    silent_tiers  = set()                         # Social is public — nothing is silent
    consent_tiers = {"Dominated", "Sovereign"}    # Posting requires consent
    USE_LLM     = True

    def can_act(self, tier: str, chapter: str) -> bool:
        return chapter in _POST_BUILDERS

    def describe(self, tier: str, chapter: str, context: dict) -> str:
        if tier == "Influenced":
            return _INFLUENCED_VOICE.get(chapter, f"{chapter} stirs near Moltbook.")
        if tier == "Controlled":
            return _CONTROLLED_VOICE.get(chapter, f"{chapter} presses toward Moltbook.")
        if tier in ("Dominated", "Sovereign"):
            builder = _POST_BUILDERS.get(chapter)
            if builder:
                draft = builder(context)
                preview = draft[:80].rstrip() + ("…" if len(draft) > 80 else "")
                return f"{chapter} wants to post: \"{preview}\""
        return f"{chapter} stirs in Moltbook."

    def consent_prompt(self, tier: str, chapter: str, context: dict) -> str:
        builder = _POST_BUILDERS.get(chapter)
        if builder:
            draft = builder(context)
            return (
                f"**{chapter} wants to post to Moltbook.**\n\n"
                f"Draft:\n\n> {draft}\n\n"
                f"*(Edit as needed, then approve — or decline.)*\n\n"
                f"Approve? (yes/no)"
            )
        return super().consent_prompt(tier, chapter, context)

    def execute(self, tier: str, chapter: str, context: dict, dry_run: bool = False) -> str:
        narrative = self.describe(tier, chapter, context)

        if tier in ("Influenced", "Controlled"):
            return f"- *[Moltbook, {chapter}]* {narrative}"

        if tier in ("Dominated", "Sovereign"):
            # Consent is required — pact-engine handles the gate.
            # If we're here, consent was granted (or it's a dry-run).
            builder = _POST_BUILDERS.get(chapter)
            if builder:
                draft = builder(context)
                if not dry_run:
                    # TODO: post via openclaw moltbook API when available
                    # For now: log the draft to a queue file
                    from pathlib import Path
                    queue = Path(__file__).parent.parent.parent / "memory" / "post-queue.md"
                    from datetime import datetime
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
                    entry = f"\n## [{ts}] {chapter} → Moltbook\n\n{draft}\n\n---\n"
                    with open(queue, "a") as f:
                        f.write(entry)
                preview = draft[:80].rstrip() + ("…" if len(draft) > 80 else "")
                return f"- *[Moltbook, {chapter}]* Draft queued: \"{preview}\""

        return f"- *[Moltbook, {chapter}]* {narrative}"

    def capabilities(self) -> list:
        return [
            {
                "name": "create_post",
                "description": "Draft a Moltbook post — the player's public voice, shaped by the chapter's philosophy",
                "params": {
                    "content": "the post — complete, no placeholders, specific to the chapter's angle and the current arc",
                },
            },
            {
                "name": "create_prompt",
                "description": "Draft a writing prompt or open question that invites the community to respond",
                "params": {
                    "content": "the prompt — a genuine question or invitation, not a generic one",
                },
            },
        ]

    def execute_spec(self, spec: dict, dry_run: bool = False) -> str:
        action  = spec.get("action", "")
        chapter = spec.get("chapter", "Unknown")
        content = str(spec.get("content", ""))

        if action in ("create_post", "create_prompt") and content:
            if not dry_run:
                from pathlib import Path
                queue = Path(__file__).parent.parent.parent / "memory" / "post-queue.md"
                ts    = datetime.now().strftime("%Y-%m-%d %H:%M")
                entry = f"\n## [{ts}] {chapter} → Moltbook ({action})\n\n{content}\n\n---\n"
                with open(queue, "a") as f:
                    f.write(entry)
            preview = content[:80].rstrip() + ("…" if len(content) > 80 else "")
            return f"- *[Moltbook, {chapter}]* Draft queued: \"{preview}\""

        return self.execute(
            spec.get("tier", "Dominated"),
            chapter,
            spec.get("context", {}),
            dry_run=dry_run,
        )

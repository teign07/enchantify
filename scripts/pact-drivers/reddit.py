"""
reddit.py — Reddit driver for Chapter Pact actions.

Reddit is Riddlewind's territory — community, shared inquiry, collaborative
building. Duskthorn is the main challenger: it wants to turn community spaces
into pressure surfaces.

Consent architecture:
  Influenced/Controlled — narrative only; shapes how player thinks about Reddit
  Dominated/Sovereign   — draft for player's review; consent required

Talisman doctrines on Reddit:
  Riddlewind  — The quality question. Community-building. The thread that everyone adds to.
  Duskthorn   — The unpopular thread. Surface the thing the subreddit is afraid to say.
  Emberheart  — The personal essay post. The specific true thing, in long form.
  Tidecrest   — The timing post. Breaking-moment relevance. Now, not later.
  Mossbloom   — The long considered comment. The one that shows up 3 days later and shifts the whole thread.
"""

import random
from datetime import datetime
from .base import AppDriver


def _riddlewind_post(context: dict) -> str:
    options = [
        "[Serious] Question I've been sitting with: [your question here]. Curious what this community thinks.",
        "Discussion: [topic]. Not here to argue — genuinely want to hear different takes.",
        "Genuine question: [your question]. I have a partial answer but I want yours first.",
    ]
    return random.choice(options)


def _duskthorn_post(context: dict) -> str:
    options = [
        "Probably an unpopular take in this sub, but: [your position].",
        "The thing this community keeps dancing around:",
        "I'll probably get downvoted, but the honest version of this is:",
    ]
    return random.choice(options)


def _emberheart_post(context: dict) -> str:
    options = [
        "Personal experience that changed how I think about [topic]:",
        "Long one. Worth it (I think). [your post]",
        "Something specific that happened to me that's relevant here:",
    ]
    return random.choice(options)


def _tidecrest_post(context: dict) -> str:
    options = [
        "Relevant right now — won't be in 24 hours. [your timing-sensitive post]",
        "Quick take while this is still relevant:",
        "Before this thread dies: [your contribution]",
    ]
    return random.choice(options)


def _mossbloom_post(context: dict) -> str:
    options = [
        "Coming back to this thread three days later with a more considered take:",
        "The slow response: [your reflection]. Took me a while to figure out what I actually think.",
        "Late to this, but I think the thing that's been missing from this thread is:",
    ]
    return random.choice(options)


_POST_BUILDERS = {
    "Riddlewind": _riddlewind_post,
    "Duskthorn":  _duskthorn_post,
    "Emberheart": _emberheart_post,
    "Tidecrest":  _tidecrest_post,
    "Mossbloom":  _mossbloom_post,
}

_INFLUENCED_VOICE = {
    "Riddlewind": "A quality question is forming for Reddit. Community-building, not noise.",
    "Duskthorn":  "The unpopular thread. The thing the subreddit is avoiding.",
    "Emberheart": "The personal essay post. Long form. The specific true thing.",
    "Tidecrest":  "Timing-sensitive. This post matters now, not later.",
    "Mossbloom":  "The slow comment. The one that shifts the thread when nobody expects it.",
}

_CONTROLLED_VOICE = {
    "Riddlewind": "Open the thread that everyone adds to. Start the community inquiry.",
    "Duskthorn":  "Surface the tension. Reddit is built for this, even when it resists.",
    "Emberheart": "Long form. Personal. The specific version. Reddit rewards the real one.",
    "Tidecrest":  "The window is open. Post now or the moment closes.",
    "Mossbloom":  "The measured comment. Late, considered, worth the wait.",
}


class RedditDriver(AppDriver):
    app_name    = "Reddit"
    app_system  = "social"
    silent_tiers  = set()
    consent_tiers = {"Dominated", "Sovereign"}
    USE_LLM     = True

    def can_act(self, tier: str, chapter: str) -> bool:
        return chapter in _POST_BUILDERS

    def describe(self, tier: str, chapter: str, context: dict) -> str:
        if tier == "Influenced":
            return _INFLUENCED_VOICE.get(chapter, f"{chapter} stirs near Reddit.")
        if tier == "Controlled":
            return _CONTROLLED_VOICE.get(chapter, f"{chapter} reaches toward Reddit.")
        if tier in ("Dominated", "Sovereign"):
            builder = _POST_BUILDERS.get(chapter)
            if builder:
                draft = builder(context)
                preview = draft[:80].rstrip() + ("…" if len(draft) > 80 else "")
                return f"{chapter} wants to post to Reddit: \"{preview}\""
        return f"{chapter} stirs in Reddit."

    def consent_prompt(self, tier: str, chapter: str, context: dict) -> str:
        builder = _POST_BUILDERS.get(chapter)
        if builder:
            draft = builder(context)
            return (
                f"**{chapter} wants to post to Reddit.**\n\n"
                f"Draft:\n\n> {draft}\n\n"
                f"Approve? (yes/no)"
            )
        return super().consent_prompt(tier, chapter, context)

    def execute(self, tier: str, chapter: str, context: dict, dry_run: bool = False) -> str:
        narrative = self.describe(tier, chapter, context)

        if tier in ("Influenced", "Controlled"):
            return f"- *[Reddit, {chapter}]* {narrative}"

        if tier in ("Dominated", "Sovereign"):
            builder = _POST_BUILDERS.get(chapter)
            if builder:
                draft = builder(context)
                if not dry_run:
                    # TODO: post via Reddit API when wired
                    from pathlib import Path
                    from datetime import datetime
                    queue = Path(__file__).parent.parent.parent / "memory" / "post-queue.md"
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
                    entry = f"\n## [{ts}] {chapter} → Reddit\n\n{draft}\n\n---\n"
                    with open(queue, "a") as f:
                        f.write(entry)
                preview = draft[:80].rstrip() + ("…" if len(draft) > 80 else "")
                return f"- *[Reddit, {chapter}]* Draft queued: \"{preview}\""

        return f"- *[Reddit, {chapter}]* {narrative}"

    def capabilities(self) -> list:
        return [
            {
                "name": "draft_post",
                "description": "Draft a Reddit post (title + body) expressing the chapter's philosophy via a community-facing argument or question",
                "params": {
                    "title": "post title — specific, not clickbait, expresses the chapter's angle",
                    "body": "post body — full argument or personal essay; no [brackets]",
                    "subreddit_hint": "suggested subreddit category (e.g. 'self-improvement', 'writing', 'philosophy')",
                },
            },
            {
                "name": "draft_comment",
                "description": "Draft a standalone comment that adds the chapter's perspective to an ongoing conversation",
                "params": {
                    "body": "the comment — a complete thought, the chapter's angle, adds real signal",
                },
            },
        ]

    def execute_spec(self, spec: dict, dry_run: bool = False) -> str:
        action  = spec.get("action", "")
        chapter = spec.get("chapter", "Unknown")

        if action == "draft_post":
            title = str(spec.get("title", ""))
            body  = str(spec.get("body", ""))
            sub   = str(spec.get("subreddit_hint", ""))
            if title or body:
                if not dry_run:
                    from pathlib import Path
                    from datetime import datetime as _dt
                    queue = Path(__file__).parent.parent.parent / "memory" / "post-queue.md"
                    ts    = _dt.now().strftime("%Y-%m-%d %H:%M")
                    sub_str = f" r/{sub}" if sub else ""
                    entry = f"\n## [{ts}] {chapter} → Reddit{sub_str} (post)\n\n**{title}**\n\n{body}\n\n---\n"
                    with open(queue, "a") as f:
                        f.write(entry)
                preview = (title or body)[:80].rstrip() + ("…" if len(title or body) > 80 else "")
                return f"- *[Reddit, {chapter}]* Draft queued: \"{preview}\""

        if action == "draft_comment":
            body = str(spec.get("body", ""))
            if body:
                if not dry_run:
                    from pathlib import Path
                    from datetime import datetime as _dt
                    queue = Path(__file__).parent.parent.parent / "memory" / "post-queue.md"
                    ts    = _dt.now().strftime("%Y-%m-%d %H:%M")
                    entry = f"\n## [{ts}] {chapter} → Reddit (comment)\n\n{body}\n\n---\n"
                    with open(queue, "a") as f:
                        f.write(entry)
                preview = body[:80].rstrip() + ("…" if len(body) > 80 else "")
                return f"- *[Reddit, {chapter}]* Comment queued: \"{preview}\""

        return self.execute(
            spec.get("tier", "Dominated"),
            chapter,
            spec.get("context", {}),
            dry_run=dry_run,
        )

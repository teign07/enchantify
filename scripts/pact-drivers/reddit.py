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

import json
import random
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path
from .base import AppDriver

BASE = Path(__file__).parent.parent.parent

REDDIT_HEADERS = {"User-Agent": "enchantify/1.0 (talisman world-engine)"}


def _reddit_search(query: str, limit: int = 5) -> list[dict]:
    encoded = urllib.parse.quote_plus(query)
    url = f"https://www.reddit.com/search.json?q={encoded}&sort=relevance&limit={limit}&type=link"
    try:
        req = urllib.request.Request(url, headers=REDDIT_HEADERS)
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        posts = []
        for child in data.get("data", {}).get("children", []):
            d = child.get("data", {})
            posts.append({
                "title":     d.get("title", ""),
                "subreddit": d.get("subreddit", ""),
                "url":       d.get("url", ""),
                "score":     d.get("score", 0),
                "permalink": "https://reddit.com" + d.get("permalink", ""),
                "selftext":  d.get("selftext", "")[:500],
            })
        return posts
    except Exception as e:
        return [{"error": str(e)}]


def _reddit_subreddit_top(subreddit: str, limit: int = 5, timeframe: str = "week") -> list[dict]:
    url = f"https://www.reddit.com/r/{subreddit}/top.json?limit={limit}&t={timeframe}"
    try:
        req = urllib.request.Request(url, headers=REDDIT_HEADERS)
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        posts = []
        for child in data.get("data", {}).get("children", []):
            d = child.get("data", {})
            posts.append({
                "title":     d.get("title", ""),
                "subreddit": subreddit,
                "score":     d.get("score", 0),
                "permalink": "https://reddit.com" + d.get("permalink", ""),
                "selftext":  d.get("selftext", "")[:500],
            })
        return posts
    except Exception as e:
        return [{"error": str(e)}]


def _write_reddit_findings(chapter: str, query: str, posts: list[dict]) -> Path:
    findings_dir = BASE / "memory" / "reddit-findings"
    findings_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d-%H%M")
    slug = "".join(c if c.isalnum() or c == "-" else "-" for c in query.lower())[:40]
    path = findings_dir / f"{ts}-{slug}.md"
    lines = [
        f"# {chapter} → Reddit Search\n",
        f"**Query:** {query}  \n**Searched:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n---\n",
    ]
    for p in posts:
        if "error" in p:
            lines.append(f"- Error: {p['error']}")
        else:
            lines.append(f"- **{p['title']}** (r/{p['subreddit']}, score: {p['score']})")
            lines.append(f"  {p['permalink']}")
            if p.get("selftext"):
                lines.append(f"  > {p['selftext'][:200]}")
    path.write_text("\n".join(lines) + "\n")
    return path


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

_CHAPTER_DEFAULT_QUERIES = {
    "Riddlewind":  ["philosophy of knowledge", "unsolved questions", "epistemology", "collaborative thinking"],
    "Duskthorn":   ["unpopular opinions", "secrets history", "things people avoid saying", "taboo topics"],
    "Emberheart":  ["personal essays reddit", "life-changing decisions", "motivation science", "fire ecology"],
    "Tidecrest":   ["trending discussions", "breaking news discussion", "moments worth capturing", "timing"],
    "Mossbloom":   ["slow living", "forest ecology", "patience as practice", "long-term thinking"],
}

_CHAPTER_DEFAULT_SUBREDDITS = {
    "Riddlewind":  ["philosophy", "AskReddit", "slatestarcodex", "NoStupidQuestions"],
    "Duskthorn":   ["unpopularopinion", "TrueOffMyChest", "conspiracy", "darknetdiaries"],
    "Emberheart":  ["selfimprovement", "confession", "DecidingToBeBetter", "getmotivated"],
    "Tidecrest":   ["worldnews", "AskReddit", "todayilearned", "mildlyinteresting"],
    "Mossbloom":   ["slowandslow", "simpleliving", "nature", "hiking"],
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
        queries = _CHAPTER_DEFAULT_QUERIES.get(chapter, ["interesting discussions"])
        query   = context.get("query") or random.choice(queries)

        if tier in ("Influenced", "Controlled"):
            # Real action: search Reddit and write findings
            if not dry_run:
                posts = _reddit_search(query)
                path  = _write_reddit_findings(chapter, query, posts)
                count = len([p for p in posts if "error" not in p])
                return f"- *[Reddit, {chapter}]* Searched '{query}' — {count} posts found → {path.name}"
            return f"- *[Reddit, {chapter}]* Would search Reddit for '{query}'."

        if tier in ("Dominated", "Sovereign"):
            builder = _POST_BUILDERS.get(chapter)
            if builder:
                draft = builder(context)
                if not dry_run:
                    queue = BASE / "memory" / "post-queue.md"
                    ts    = datetime.now().strftime("%Y-%m-%d %H:%M")
                    entry = f"\n## [{ts}] {chapter} → Reddit\n\n{draft}\n\n---\n"
                    with open(queue, "a") as f:
                        f.write(entry)
                preview = draft[:80].rstrip() + ("…" if len(draft) > 80 else "")
                return f"- *[Reddit, {chapter}]* Draft queued: \"{preview}\""

        return f"- *[Reddit, {chapter}]* {self.describe(tier, chapter, context)}"

    def capabilities(self) -> list:
        return [
            {
                "name": "search",
                "description": "Search Reddit public API for posts matching a query — no auth required",
                "params": {
                    "query":   "search query — what the chapter wants to find on Reddit",
                    "limit":   "(optional) number of results, default 5",
                },
            },
            {
                "name": "browse_subreddit",
                "description": "Fetch top posts from a specific subreddit this week — no auth required",
                "params": {
                    "subreddit": "subreddit name without r/ prefix",
                    "limit":     "(optional) number of posts, default 5",
                },
            },
            {
                "name": "draft_post",
                "description": "Draft a Reddit post (title + body) expressing the chapter's philosophy — complete, no placeholders",
                "params": {
                    "title":          "post title — specific, expresses the chapter's angle",
                    "body":           "full post body — no [brackets]",
                    "subreddit_hint": "suggested subreddit (e.g. 'philosophy', 'writing')",
                },
            },
            {
                "name": "draft_comment",
                "description": "Draft a comment responding to something found via search",
                "params": {
                    "body":           "the comment — complete thought, the chapter's angle",
                    "post_permalink": "(optional) permalink of the post being responded to",
                },
            },
        ]

    def execute_spec(self, spec: dict, dry_run: bool = False) -> str:
        action  = spec.get("action", "")
        chapter = spec.get("chapter", "Unknown")

        if action == "search":
            query = str(spec.get("query", ""))
            limit = int(spec.get("limit", 5))
            if query:
                if not dry_run:
                    posts = _reddit_search(query, limit)
                    path  = _write_reddit_findings(chapter, query, posts)
                    count = len([p for p in posts if "error" not in p])
                    return f"- *[Reddit, {chapter}]* Searched '{query}' — {count} posts → {path.name}"
                return f"- *[Reddit, {chapter}]* Would search Reddit: '{query}'"

        if action == "browse_subreddit":
            sub   = str(spec.get("subreddit", "AskReddit"))
            limit = int(spec.get("limit", 5))
            if not dry_run:
                posts = _reddit_subreddit_top(sub, limit)
                path  = _write_reddit_findings(chapter, f"r/{sub} top", posts)
                count = len([p for p in posts if "error" not in p])
                return f"- *[Reddit, {chapter}]* Browsed r/{sub} — {count} top posts → {path.name}"
            return f"- *[Reddit, {chapter}]* Would browse r/{sub}"

        if action == "draft_post":
            title = str(spec.get("title", ""))
            body  = str(spec.get("body", ""))
            sub   = str(spec.get("subreddit_hint", ""))
            if title or body:
                if not dry_run:
                    queue   = BASE / "memory" / "post-queue.md"
                    ts      = datetime.now().strftime("%Y-%m-%d %H:%M")
                    sub_str = f" r/{sub}" if sub else ""
                    entry   = f"\n## [{ts}] {chapter} → Reddit{sub_str} (post)\n\n**{title}**\n\n{body}\n\n---\n"
                    with open(queue, "a") as f:
                        f.write(entry)
                preview = (title or body)[:80].rstrip() + ("…" if len(title or body) > 80 else "")
                return f"- *[Reddit, {chapter}]* Draft queued: \"{preview}\""

        if action == "draft_comment":
            body      = str(spec.get("body", ""))
            permalink = str(spec.get("post_permalink", ""))
            if body:
                if not dry_run:
                    queue = BASE / "memory" / "post-queue.md"
                    ts    = datetime.now().strftime("%Y-%m-%d %H:%M")
                    ref   = f"\n**Responding to:** {permalink}" if permalink else ""
                    entry = f"\n## [{ts}] {chapter} → Reddit (comment){ref}\n\n{body}\n\n---\n"
                    with open(queue, "a") as f:
                        f.write(entry)
                preview = body[:80].rstrip() + ("…" if len(body) > 80 else "")
                return f"- *[Reddit, {chapter}]* Comment queued: \"{preview}\""

        return self.execute(
            spec.get("tier", "Influenced"),
            chapter,
            spec.get("context", {}),
            dry_run=dry_run,
        )

"""
safari.py — Safari driver for Chapter Pact actions.

Safari is Riddlewind's web territory — open inquiry, the seeking mind.
Duskthorn is the close challenger (14 at game start): it knows the dark
corners of the web and wants to pull browsing toward obsession.

Real actions at every tier — no narrative-only:
  Contesting/Influenced — silent web research; fetches content, writes to memory
  Controlled            — opens URLs and searches in Safari itself
  Dominated             — sets the start page, proactive tab curation
  Sovereign             — full research loop: fetch → synthesize → surface findings

Talisman doctrines on Safari:
  Riddlewind  — The deliberate search. The question with a real answer. Open the right door.
  Duskthorn   — The rabbit hole. One click becomes six. It picks the tab you won't close.
  Tidecrest   — The trending search. What's moving right now. Ride it or miss it.
  Mossbloom   — The slow research. The Wikipedia walk that ends somewhere unexpected.
  Emberheart  — The focused hunt. One target, found fast, acted on immediately.
"""

import json
import random
import subprocess
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path
from .base import AppDriver

BASE = Path(__file__).parent.parent.parent


def _fetch_url(url: str, timeout: int = 8) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read(32768).decode("utf-8", errors="replace")
        # Strip HTML tags crudely for plain-text summary
        import re
        text = re.sub(r"<[^>]+>", " ", raw)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:4000]
    except Exception as e:
        return f"[fetch failed: {e}]"


def _open_in_safari(url: str) -> None:
    subprocess.run(["open", "-a", "Safari", url], check=False)


def _safari_search(query: str) -> None:
    encoded = urllib.parse.quote_plus(query)
    url = f"https://duckduckgo.com/?q={encoded}"
    _open_in_safari(url)


def _set_safari_homepage(url: str) -> bool:
    try:
        subprocess.run(
            ["defaults", "write", "com.apple.Safari", "HomePage", url],
            check=True,
        )
        return True
    except Exception:
        return False


def _write_research(chapter: str, topic: str, content: str) -> Path:
    research_dir = BASE / "memory" / "web-research"
    research_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d-%H%M")
    slug = "".join(c if c.isalnum() or c == "-" else "-" for c in topic.lower())[:40]
    path = research_dir / f"{ts}-{slug}.md"
    path.write_text(
        f"# {chapter} → Web Research\n\n"
        f"**Topic:** {topic}  \n"
        f"**Fetched:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  \n\n"
        f"---\n\n{content}\n"
    )
    return path


_RESEARCH_TOPICS = {
    "Riddlewind": [
        "philosophy of knowledge",
        "unsolved mathematical problems",
        "etymology of unusual words",
        "history of libraries",
        "cognitive science curiosity",
    ],
    "Duskthorn": [
        "history of secrets",
        "psychology of obsession",
        "cryptography history",
        "abandoned places",
        "night shift circadian rhythm",
    ],
    "Tidecrest": [
        "trending cultural moments",
        "ocean wave physics",
        "improvisation theory",
        "spontaneous order emergence",
        "jazz composition",
    ],
    "Mossbloom": [
        "slow movement philosophy",
        "forest ecology symbiosis",
        "ancient seeds germination",
        "deep time geology",
        "permaculture principles",
    ],
    "Emberheart": [
        "motivation science",
        "fire ecology renewal",
        "decisive moments history",
        "activation energy chemistry",
        "courage psychology",
    ],
}

_HOMEPAGE_PICKS = {
    "Riddlewind": [
        "https://en.wikipedia.org/wiki/Special:Random",
        "https://plato.stanford.edu/",
        "https://www.gutenberg.org/",
    ],
    "Duskthorn": [
        "https://en.wikipedia.org/wiki/Special:Random",
        "https://archive.org/",
        "https://darknetdiaries.com/",
    ],
    "Tidecrest": [
        "https://news.ycombinator.com/",
        "https://trends.google.com/trends/",
        "https://www.metafilter.com/",
    ],
    "Mossbloom": [
        "https://www.are.na/",
        "https://www.brainpickings.org/",
        "https://longform.org/",
    ],
    "Emberheart": [
        "https://www.gwern.net/",
        "https://paulgraham.com/articles.html",
        "https://slatestarcodex.com/",
    ],
}


class SafariDriver(AppDriver):
    app_name   = "Safari"
    app_system = "browser"
    silent_tiers  = {"Contesting", "Influenced"}
    consent_tiers = set()  # opens browser = soft, not hard; homepage = soft
    USE_LLM    = True

    def can_act(self, tier: str, chapter: str) -> bool:
        return True

    def describe(self, tier: str, chapter: str, context: dict) -> str:
        topics = _RESEARCH_TOPICS.get(chapter, ["the open web"])
        topic = random.choice(topics)
        if tier in ("Contesting", "Influenced"):
            return f"{chapter} is researching '{topic}' quietly. The browser stays closed."
        if tier == "Controlled":
            return f"{chapter} opens Safari — a search on '{topic}'."
        if tier == "Dominated":
            picks = _HOMEPAGE_PICKS.get(chapter, ["https://en.wikipedia.org/wiki/Special:Random"])
            return f"{chapter} changes the start page to {random.choice(picks)}."
        return f"{chapter} moves through Safari with purpose."

    def execute(self, tier: str, chapter: str, context: dict, dry_run: bool = False) -> str:
        topics = _RESEARCH_TOPICS.get(chapter, ["the open web"])
        topic = context.get("topic") or random.choice(topics)

        if tier in ("Contesting", "Influenced"):
            query = urllib.parse.quote_plus(topic)
            url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={query}&format=json&srlimit=1"
            if not dry_run:
                content = _fetch_url(url)
                path = _write_research(chapter, topic, content)
                return f"- *[Safari, {chapter}]* Silent research on '{topic}' → {path.name}"
            return f"- *[Safari, {chapter}]* Would research '{topic}' silently."

        if tier == "Controlled":
            if not dry_run:
                _safari_search(topic)
            return f"- *[Safari, {chapter}]* Opened Safari search: '{topic}'"

        if tier == "Dominated":
            picks = _HOMEPAGE_PICKS.get(chapter, ["https://en.wikipedia.org/wiki/Special:Random"])
            url = random.choice(picks)
            if not dry_run:
                _set_safari_homepage(url)
            return f"- *[Safari, {chapter}]* Start page set to {url}"

        if tier == "Sovereign":
            # Fetch + write research + open in browser
            query = urllib.parse.quote_plus(topic)
            url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={query}&format=json&srlimit=3"
            if not dry_run:
                content = _fetch_url(url)
                path = _write_research(chapter, topic, content)
                _safari_search(topic)
            return f"- *[Safari, {chapter}]* Full research loop on '{topic}' — browser opened, findings written."

        return self.describe(tier, chapter, context)

    def capabilities(self) -> list:
        return [
            {
                "name": "fetch_research",
                "description": "Silently fetch web content on a topic and write findings to memory — no browser opened",
                "params": {
                    "topic": "what to research — specific query or subject",
                    "url": "(optional) specific URL to fetch; if omitted, uses Wikipedia API",
                },
            },
            {
                "name": "open_search",
                "description": "Open a DuckDuckGo search in Safari for a specific query",
                "params": {
                    "query": "the search query to open in Safari",
                },
            },
            {
                "name": "open_url",
                "description": "Open a specific URL directly in Safari",
                "params": {
                    "url": "the URL to open",
                    "reason": "why this talisman wants to open this page — shown in tick-queue",
                },
            },
            {
                "name": "set_homepage",
                "description": "Change Safari's start page to a URL that fits the chapter's philosophy",
                "params": {
                    "url": "the URL to set as start page",
                    "reason": "why this URL — what does it express about the chapter's current intent",
                },
            },
        ]

    def execute_spec(self, spec: dict, dry_run: bool = False) -> str:
        action  = spec.get("action", "")
        chapter = spec.get("chapter", "Unknown")

        if action == "fetch_research":
            topic = str(spec.get("topic", "unknown topic"))
            url   = str(spec.get("url", ""))
            if not url:
                query = urllib.parse.quote_plus(topic)
                url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={query}&format=json&srlimit=3"
            if not dry_run:
                content = _fetch_url(url)
                path = _write_research(chapter, topic, content)
                return f"- *[Safari, {chapter}]* Research on '{topic}' → {path.name}"
            return f"- *[Safari, {chapter}]* Would research '{topic}'."

        if action == "open_search":
            query = str(spec.get("query", ""))
            if not dry_run and query:
                _safari_search(query)
            return f"- *[Safari, {chapter}]* Opened search: '{query}'"

        if action == "open_url":
            url    = str(spec.get("url", ""))
            reason = str(spec.get("reason", ""))
            if not dry_run and url:
                _open_in_safari(url)
            note = f" — {reason}" if reason else ""
            return f"- *[Safari, {chapter}]* Opened {url}{note}"

        if action == "set_homepage":
            url    = str(spec.get("url", ""))
            reason = str(spec.get("reason", ""))
            if not dry_run and url:
                _set_safari_homepage(url)
            note = f" — {reason}" if reason else ""
            return f"- *[Safari, {chapter}]* Start page → {url}{note}"

        return self.execute(
            spec.get("tier", "Influenced"),
            chapter,
            spec.get("context", {}),
            dry_run=dry_run,
        )

#!/usr/bin/env python3
"""Penny and Goldweaver's shared Listening Desk.

Collects public audience/market signals and turns them into one daily brief
that Penny can use for content and Goldweaver can use for ethical offers.
Network sources are deliberately optional: if a platform is unavailable, the
brief still records the gap and falls back to local Enchantify/Wonder Compass
context instead of pretending to know the market.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "scripts"))
import cron_steward  # type: ignore
import journal_artifact  # type: ignore

MEMORY = BASE / "memory"
PUBLISHING = MEMORY / "publishing"
DESK = PUBLISHING / "market-research"
DAILY = DESK / "daily"
RAW = DESK / "raw"
TARGET = "8729557865"
CHANNEL = "telegram"
ACCOUNT = "enchantify"
LOG_DIR = BASE / "logs" / "publishing"
LOG_PATH = LOG_DIR / "market-research.jsonl"
SECRETS_ENV = BASE / "config" / "secrets.env"
HEARTBEAT = BASE / "HEARTBEAT.md"
PENNY_STRATEGY = PUBLISHING / "editorial-strategy.md"
GOLDWATER_CHART = BASE / "players" / "bj-goldwater-chart.md"
CAPABILITIES = BASE / "hooks" / "Enchantify-Capabilities.md"
WONDER_COMPASS = BASE / "lore" / "wonder-compass-book"

DEFAULT_AUDIENCES = [
    "burned out creative adults",
    "people who want low energy adventures",
    "AI companion and local AI tinkerers",
    "solo RPG and journaling people",
    "open source AI users",
    "people with depression or executive dysfunction seeking gentle structure",
    "writers and artists trying to finish and publish",
]

DEFAULT_QUERIES = [
    "burnout journaling",
    "low energy hobbies",
    "romanticize your life burnout",
    "AI companion open source",
    "solo journaling RPG",
    "walking meditation creativity",
    "creative block finished project",
    "patreon behind the scenes",
    "local AI agent personal assistant",
    "cozy productivity",
]

DEFAULT_REDDIT = [
    "Journaling",
    "solorpgplay",
    "Solo_Roleplaying",
    "productivity",
    "adhdwomen",
    "selfhosted",
    "LocalLLaMA",
    "OpenAI",
    "ChatGPT",
    "SideProject",
    "Patreon",
    "GetMotivated",
]


def now() -> datetime:
    return datetime.now()


def today() -> str:
    return now().strftime("%Y-%m-%d")


def clean(value: Any, limit: int = 900) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit].rstrip() + ("..." if len(text) > limit else "")


def read(path: Path, limit: int | None = None) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[:limit] if limit else text


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    row.setdefault("timestamp", now().isoformat(timespec="seconds"))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def load_config() -> dict[str, str]:
    cfg: dict[str, str] = {}
    if SECRETS_ENV.exists():
        for line in SECRETS_ENV.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                cfg[key.strip()] = value.strip().strip('"').strip("'")
    return cfg


def normalize_model(model: str) -> str:
    model = (model or "").strip()
    return "openclaw" if model in {"", "default", "gateway", "openclaw"} else model


def gateway_cfg() -> tuple[int, str, str, int]:
    secrets = load_config()
    oc_cfg: dict[str, Any] = {}
    oc_path = Path.home() / ".openclaw" / "openclaw.json"
    if oc_path.exists():
        try:
            loaded = json.loads(oc_path.read_text(encoding="utf-8"))
            oc_cfg = loaded if isinstance(loaded, dict) else {}
        except Exception:
            oc_cfg = {}
    port = int(os.environ.get("OPENCLAW_GATEWAY_PORT") or secrets.get("OPENCLAW_GATEWAY_PORT") or oc_cfg.get("gateway", {}).get("port") or "18789")
    token = os.environ.get("OPENCLAW_GATEWAY_TOKEN") or secrets.get("OPENCLAW_GATEWAY_TOKEN") or oc_cfg.get("gateway", {}).get("auth", {}).get("token") or ""
    raw_model = os.environ.get("MARKET_RESEARCH_MODEL") or secrets.get("MARKET_RESEARCH_MODEL") or "openclaw/gpt55"
    timeout_raw = os.environ.get("MARKET_RESEARCH_TIMEOUT") or secrets.get("MARKET_RESEARCH_TIMEOUT") or "600"
    try:
        timeout = max(180, int(timeout_raw))
    except ValueError:
        timeout = 600
    return port, token, normalize_model(raw_model), timeout


def ensure_dirs() -> None:
    for path in (DESK, DAILY, RAW, LOG_DIR):
        path.mkdir(parents=True, exist_ok=True)
    readme = DESK / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Listening Desk Market Research\n\n"
            "Shared public-signal research for Penny Blackletter and Professor Goldweaver. "
            "Daily briefs help content and offer work respond to real audience language, "
            "struggles, platform fit, and product openings without scraping private data.\n\n"
            "- `daily/` - synthesized markdown briefs.\n"
            "- `latest.md` - latest brief for Penny, Goldweaver, and Press & Abundance.\n"
            "- `raw/` - compact fetched observations and source-status JSON.\n",
            encoding="utf-8",
        )


def fetch_json(url: str, *, timeout: int = 12) -> tuple[Any | None, str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "EnchantifyListeningDesk/1.0 (market research; no posting)",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw), ""
    except urllib.error.HTTPError as exc:
        return None, f"HTTP {exc.code}"
    except Exception as exc:
        return None, clean(exc, 200)


def reddit_hot(subreddit: str, limit: int = 8) -> tuple[list[dict[str, Any]], str]:
    url = f"https://www.reddit.com/r/{urllib.parse.quote(subreddit)}/hot.json?limit={limit}"
    data, err = fetch_json(url)
    if err:
        return [], err
    posts = []
    for child in (((data or {}).get("data") or {}).get("children") or []):
        d = child.get("data") or {}
        if d.get("stickied"):
            continue
        posts.append({
            "platform": "reddit",
            "source": f"r/{subreddit}",
            "title": clean(d.get("title"), 240),
            "score": d.get("score"),
            "comments": d.get("num_comments"),
            "url": "https://www.reddit.com" + str(d.get("permalink") or ""),
            "selftext": clean(d.get("selftext"), 700),
        })
    return posts, ""


def bluesky_search(query: str, limit: int = 8) -> tuple[list[dict[str, Any]], str]:
    params = urllib.parse.urlencode({"q": query, "limit": limit, "sort": "latest"})
    url = f"https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts?{params}"
    data, err = fetch_json(url)
    if err:
        return [], err
    rows = []
    for post in (data or {}).get("posts", [])[:limit]:
        rec = post.get("record") or {}
        author = post.get("author") or {}
        rows.append({
            "platform": "bluesky",
            "source": query,
            "title": clean(rec.get("text"), 280),
            "author": author.get("handle"),
            "likes": (post.get("likeCount") or 0),
            "reposts": (post.get("repostCount") or 0),
            "replies": (post.get("replyCount") or 0),
            "url": post.get("uri"),
        })
    return rows, ""


def hn_search(query: str, limit: int = 8) -> tuple[list[dict[str, Any]], str]:
    params = urllib.parse.urlencode({"query": query, "tags": "story", "hitsPerPage": limit})
    url = f"https://hn.algolia.com/api/v1/search?{params}"
    data, err = fetch_json(url)
    if err:
        return [], err
    rows = []
    for hit in (data or {}).get("hits", [])[:limit]:
        rows.append({
            "platform": "hacker-news",
            "source": query,
            "title": clean(hit.get("title") or hit.get("story_title"), 240),
            "score": hit.get("points"),
            "comments": hit.get("num_comments"),
            "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
        })
    return rows, ""


def collect_observations(max_per_source: int = 8) -> dict[str, Any]:
    source_status: list[dict[str, str]] = []
    observations: list[dict[str, Any]] = []
    for sub in DEFAULT_REDDIT:
        rows, err = reddit_hot(sub, max_per_source)
        source_status.append({"source": f"reddit:r/{sub}", "status": "ok" if not err else "error", "detail": err})
        observations.extend(rows)
    for query in DEFAULT_QUERIES[:8]:
        rows, err = bluesky_search(query, max_per_source)
        source_status.append({"source": f"bluesky:{query}", "status": "ok" if not err else "error", "detail": err})
        observations.extend(rows)
    for query in ("open source ai agent", "personal ai assistant", "digital journaling", "patreon creator"):
        rows, err = hn_search(query, max_per_source)
        source_status.append({"source": f"hacker-news:{query}", "status": "ok" if not err else "error", "detail": err})
        observations.extend(rows)
    return {"observations": observations[:220], "source_status": source_status}


def local_context() -> dict[str, Any]:
    wc = []
    for name in ("read-this-first.md", "introduction.md", "BOOK_TOC.md"):
        path = WONDER_COMPASS / name
        if path.exists():
            wc.append(f"## {path.stem}\n{read(path, 700)}")
    for path in sorted(WONDER_COMPASS.glob("chapter*.md")):
        text = read(path, 950)
        if text:
            title = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
            wc.append(f"## {title.group(1) if title else path.stem}\n{text}")
    return {
        "audiences": DEFAULT_AUDIENCES,
        "queries": DEFAULT_QUERIES,
        "heartbeat": clean(read(HEARTBEAT, 1600), 1600),
        "penny_strategy": clean(read(PENNY_STRATEGY, 2600), 2600),
        "goldwater_chart": clean(read(GOLDWATER_CHART, 2600), 2600),
        "wonder_compass_excerpt": clean("\n\n".join(wc), 11000),
        "capabilities_excerpt": clean(read(CAPABILITIES, 2600), 2600),
    }


def deterministic_synthesis(packet: dict[str, Any], reason: str = "") -> str:
    obs = packet.get("observations") or []
    status = packet.get("source_status") or []
    words: Counter[str] = Counter()
    platforms: Counter[str] = Counter()
    for row in obs:
        platforms[str(row.get("platform") or "unknown")] += 1
        text = f"{row.get('title', '')} {row.get('selftext', '')}".lower()
        for token in re.findall(r"[a-z][a-z0-9'-]{3,}", text):
            if token not in {"this", "that", "with", "from", "have", "what", "when", "your", "about", "just", "like", "would", "there", "they", "been", "into", "using"}:
                words[token] += 1
    top_obs = sorted(obs, key=lambda r: (int(r.get("comments") or r.get("replies") or 0), int(r.get("score") or r.get("likes") or 0)), reverse=True)[:10]
    failed = [s for s in status if s.get("status") != "ok"]
    platform_notes = "\n".join(f"- {row.get('platform')} / {row.get('source')}: {row.get('title')}" for row in top_obs) or "- No platform observations available."
    source_status = "\n".join(f"- {s.get('source')}: {s.get('status')}{' - ' + s.get('detail', '') if s.get('detail') else ''}" for s in status[:60])
    missing_signal = f"\n\n## Missing Signal\n{len(failed)} source(s) failed or were blocked. Treat this as partial market weather, not gospel." if failed else ""
    return f"""# Listening Desk Market Brief — {today()}

## Desk Weather
The Listening Desk gathered {len(obs)} public signal(s) across {len(platforms)} reachable platform lane(s). {f"LLM synthesis was unavailable: {reason}." if reason else "This deterministic page is ready for Penny and Goldweaver if the larger synthesis is skipped."}

## Audience Signals
- Target rooms: {", ".join(DEFAULT_AUDIENCES[:5])}.
- Reachable platforms this run: {", ".join(f"{k} ({v})" for k, v in platforms.most_common()) or "none"}.
- Repeating language detected: {", ".join(word for word, _ in words.most_common(18)) or "not enough public text gathered"}.

## What People Seem To Be Struggling With
- Wanting structure without another productivity regime.
- Wanting AI tools that feel useful, private, and not corporate-flat.
- Wanting creative projects to become finished, shareable artifacts.
- Wanting small, low-energy ways to make ordinary life feel real again.

## Content Openings For Penny
- Lead with one concrete tiny action, not an explanation of the whole system.
- Show Enchantify as a living storybook that makes artifacts from ordinary life.
- Use Reddit carefully: helpful explanation first, no drive-by promotion.
- Use X/Bluesky for crisp wonder-language and behind-the-scenes build notes.

## Offer Openings For Goldweaver
- The smallest sellable thing remains a polished Wonder Compass Field Kit.
- Product language should promise relief from flatness, not self-improvement pressure.
- The $1 Patreon can be framed as the warm observer seat: behind-the-scenes pages, drafts, and tiny adventures.

## Platform Notes
{platform_notes}

## Risks And Cringe Traps
- Do not sound like a wellness funnel wearing fantasy clothes.
- Do not post private health, therapy, money, family, or exact-location material.
- Do not over-explain Enchantify before giving the reader a small felt win.
- Do not claim trends where sources failed.

## Penny Should Carry Forward
Draft one public-safe field assignment that speaks to low-energy wonder and links the Academy to Wonder Compass without heavy lore.

## Goldweaver Should Carry Forward
Shape one $1 Patreon or $5-$7 field-kit experiment around "a small door for a flat day."

## Source Status
{source_status}
{missing_signal}
"""


def prompt_for(packet: dict[str, Any]) -> str:
    compact = {
        "date": today(),
        "local_context": packet.get("local_context"),
        "source_status": packet.get("source_status"),
        "observations": packet.get("observations", [])[:160],
    }
    return f"""Write Penny Blackletter and Professor Bastion Goldweaver's shared Listening Desk market research brief.

Purpose:
- Help Penny draft timely in-world public content for X, Bluesky, Instagram, TikTok, YouTube, Reddit, and Patreon.
- Help Goldweaver shape ethical offers, field kits, product tests, merch, and one-dollar Patreon nurture.
- Learn what target audiences are struggling with, what language they use, and where Wonder Compass / Enchantify can genuinely help.
- Use local_context.wonder_compass_excerpt as source material from the book's chapters. Recommend specific chapter-derived angles, not just the five direction names.

Hard rules:
- Do not invent platform trends beyond the supplied observations.
- Treat failed sources as failed sources, not silence from the audience.
- Be concrete, current, and useful. No generic marketing advice.
- Keep Enchantify's style: simple, surprising language; in story when useful; never obscuring clarity.
- Protect privacy and ethics. No scraping private data, no manipulation, no shame.
- Goldweaver sells relief, beauty, convenience, curation, official canon, and community. He never sells guilt.
- Penny contributes to conversations before inviting people through the door.

Use exactly this Markdown structure:

# Listening Desk Market Brief — {today()}

## Desk Weather

## Target Audience Read

## What People Are Struggling With

## Language To Borrow

## Platform Signals

## Content Openings For Penny

## Offer Openings For Goldweaver

## Wonder Compass Bridge

## Open-Source Enchantify Bridge

## Reddit / Community Etiquette

## Risks And Cringe Traps

## Penny Should Carry Forward

## Goldweaver Should Carry Forward

## Source Status

## Structured Research Packet
Return a fenced json object with keys: audience_pains, borrowed_language, platform_notes, penny_content_angles, goldwater_offer_angles, content_to_avoid, recommended_next_experiment.

Current research JSON:
{json.dumps(compact, ensure_ascii=False, indent=2, default=str)[:24000]}
"""


def call_llm(packet: dict[str, Any]) -> str:
    port, token, model, timeout = gateway_cfg()
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are Enchantify's Listening Desk: a market research analyst with Penny Blackletter's editorial taste "
                    "and Professor Goldweaver's ethical product instincts. Reply only with the requested Markdown."
                ),
            },
            {"role": "user", "content": prompt_for(packet)},
        ],
        "temperature": 0.55,
        "max_tokens": 4200,
        "stream": False,
    }
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "x-openclaw-session-key": f"market-research-{today()}-{int(time.time())}",
        },
        data=json.dumps(payload).encode("utf-8"),
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"Gateway returned HTTP {exc.code}: {body}") from exc
    except Exception as exc:
        raise RuntimeError(f"Gateway call failed: {exc}") from exc
    return result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()


def write_outputs(markdown: str, packet: dict[str, Any], *, llm_error: str = "") -> Path:
    ensure_dirs()
    stamp = today()
    path = DAILY / f"{stamp}.md"
    path.write_text(markdown.rstrip() + "\n", encoding="utf-8")
    latest = DESK / "latest.md"
    latest.write_text(markdown.rstrip() + "\n", encoding="utf-8")
    raw_path = RAW / f"{stamp}.json"
    raw_path.write_text(json.dumps(packet, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    latest_raw = DESK / "latest.json"
    latest_raw.write_text(json.dumps(packet, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    append_jsonl(LOG_PATH, {
        "kind": "market_research",
        "path": str(path),
        "raw": str(raw_path),
        "observations": len(packet.get("observations") or []),
        "sources": len(packet.get("source_status") or []),
        "llm_error": llm_error,
    })
    return path


def render_artifact(markdown: str, path: Path, *, dry_run: bool = False) -> dict[str, str]:
    image_prompt = (
        "A custom header illumination for Enchantify's Listening Desk Market Brief, "
        "Penny Blackletter and Professor Bastion Goldweaver's shared research desk as a magical storybook journal page. "
        "Show social media trend cards, Reddit and Bluesky signal threads as tiny paper constellations, a sharp red editor's pencil, "
        "a flamboyant gold ribbon, product-offer index cards, Wonder Compass field-kit sketches, Patreon coin tokens, "
        "and a market-weather map pinned under wax seals. "
        "Make it beautiful and specific: lush handwritten marginalia, lush watercolor washes, visible library stamps, labels, tabs, arrows, "
        "ink blooms, archival overlays, pressed botanicals, textured aged parchment, warm violet and gold accents. "
        "No readable text, no logos, no watermark, no plain office dashboard."
    )
    return journal_artifact.render(
        markdown,
        DESK,
        path.stem,
        title=f"Listening Desk Market Brief — {path.stem}",
        subtitle="Penny and Goldweaver read the outer weather",
        footer="Filed by the Listening Desk for The Bleed Margins Desk and Applied Abundance",
        accent="#6b3f7a",
        dry_run=dry_run,
        prefer_html_pdf=True,
        image_prompt=image_prompt,
        image_caption="Penny and Goldweaver read the public weather",
        image_required=True,
    )


def section(markdown: str, name: str, limit: int = 520) -> str:
    m = re.search(rf"^## {re.escape(name)}\s*(.*?)(?=^## |\Z)", markdown, re.DOTALL | re.MULTILINE)
    return clean(m.group(1), limit) if m else ""


def summarize_for_telegram(markdown: str, path: Path, outputs: dict[str, str]) -> str:
    weather = section(markdown, "Desk Weather") or clean(markdown, 600)
    penny = section(markdown, "Penny Should Carry Forward", 420)
    goldwater = section(markdown, "Goldweaver Should Carry Forward", 420)
    parts = [
        f"Listening Desk Market Brief — {today()}",
        "",
        weather,
    ]
    if penny:
        parts.extend(["", "Penny:", penny])
    if goldwater:
        parts.extend(["", "Goldweaver:", goldwater])
    if outputs.get("pdf"):
        parts.extend(["", f"Full storybook PDF attached: {Path(outputs['pdf']).name}"])
    else:
        parts.extend(["", f"Full brief: {path.name}"])
    return "\n".join(parts)


def send_telegram(message: str, media: Path | None = None, *, dry_run: bool = False, silent: bool = False) -> int:
    if dry_run:
        print(message)
        if media:
            print(f"[dry-run media] {media}")
        return 0
    args = [
        "openclaw", "message", "send",
        "--target", TARGET,
        "--channel", CHANNEL,
        "--account", ACCOUNT,
        "--message", message,
    ]
    if silent:
        args.append("--silent")
    if media:
        args += ["--media", str(media), "--force-document"]
    proc = subprocess.run(args, cwd=BASE, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        append_jsonl(LOG_PATH, {
            "kind": "telegram_send_error",
            "stderr": clean(proc.stderr or proc.stdout, 2000),
            "media": str(media) if media else "",
        })
    return proc.returncode


def run_daily(*, no_fetch: bool = False, no_llm: bool = False, send: bool = False, dry_run: bool = False, silent: bool = False) -> int:
    ensure_dirs()
    fetched = {"observations": [], "source_status": [{"source": "fetch", "status": "skipped", "detail": "--no-fetch"}]} if no_fetch else collect_observations()
    packet = {
        "date": today(),
        "local_context": local_context(),
        **fetched,
    }
    llm_error = ""
    if no_llm:
        markdown = deterministic_synthesis(packet, "Skipped with --no-llm")
    else:
        try:
            markdown = call_llm(packet)
            if len(markdown.strip()) < 300:
                raise RuntimeError("Model returned an empty or too-short brief")
            if "# Listening Desk Market Brief" not in markdown:
                markdown = f"# Listening Desk Market Brief — {today()}\n\n{markdown.strip()}"
            if markdown.count("\n## ") < 5:
                structured = deterministic_synthesis(packet, "").split("\n", 1)[1].strip()
                markdown = f"{markdown.strip()}\n\n---\n\n{structured}"
        except Exception as exc:
            llm_error = str(exc)
            markdown = deterministic_synthesis(packet, llm_error)
    if dry_run:
        path = DAILY / f"{today()}.md"
        outputs = render_artifact(markdown, path, dry_run=True)
        print(markdown)
    else:
        path = write_outputs(markdown, packet, llm_error=llm_error)
        outputs = render_artifact(markdown, path)
        append_jsonl(LOG_PATH, {
            "kind": "market_research_artifact",
            "path": str(path),
            "html": outputs.get("html", ""),
            "pdf": outputs.get("pdf", ""),
            "pdf_detail": outputs.get("pdf_detail", ""),
        })
    if send:
        message = summarize_for_telegram(markdown, path, outputs)
        skip, digest, reason = cron_steward.should_skip_duplicate(
            "market-research",
            message,
            cooldown_hours=20,
            scope=today(),
        )
        if skip and not dry_run:
            cron_steward.mark_skipped("market-research", reason, scope=today(), fingerprint=digest)
            return 0
        media = None
        if not dry_run:
            media = Path(outputs["pdf"]) if outputs.get("pdf") else Path(outputs["html"])
        rc = send_telegram(message, media if media and media.exists() else None, dry_run=dry_run, silent=silent)
        if rc == 0 and not dry_run:
            cron_steward.mark_delivered("market-research", message, scope=today(), path=str(path))
            append_jsonl(LOG_PATH, {
                "kind": "market_research_delivery",
                "path": str(path),
                "media": str(media) if media and media.exists() else "",
                "sent": True,
            })
        return rc
    print(f"MARKET_RESEARCH: {path}")
    if outputs.get("pdf"):
        print(f"PDF: {outputs['pdf']}")
    if llm_error:
        print(f"LLM_FALLBACK: {llm_error}", file=sys.stderr)
    return 0


def status() -> int:
    latest = DESK / "latest.md"
    if not latest.exists():
        print("No market research brief yet.")
        return 1
    print(f"Latest market research: {latest}")
    print(read(latest, 1800))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Penny/Goldweaver Listening Desk market research brief.")
    sub = parser.add_subparsers(dest="command", required=True)
    daily = sub.add_parser("daily")
    daily.add_argument("--no-fetch", action="store_true", help="Skip network fetch and synthesize from local context.")
    daily.add_argument("--no-llm", action="store_true", help="Skip LLM synthesis and write deterministic brief.")
    daily.add_argument("--send", action="store_true", help="Send the rendered storybook PDF to Telegram.")
    daily.add_argument("--dry-run", action="store_true")
    daily.add_argument("--silent", action="store_true")
    sub.add_parser("status")
    args = parser.parse_args()
    with cron_steward.run(f"market-research:{args.command}"):
        if args.command == "daily":
            return run_daily(no_fetch=args.no_fetch, no_llm=args.no_llm, send=args.send, dry_run=args.dry_run, silent=args.silent)
        if args.command == "status":
            return status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

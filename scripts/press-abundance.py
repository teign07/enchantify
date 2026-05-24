#!/usr/bin/env python3
"""Daily Penny + Goldweaver Press & Applied Abundance synthesis.

One LLM call, when available, turns Enchantify/Wonder Compass outputs into a
single in-world marketing and product artifact. Penny drafts public signal;
Goldweaver shapes ethical offers. Nothing is posted automatically.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "scripts"))
import cron_steward  # type: ignore
import journal_artifact  # type: ignore

_penny_spec = importlib.util.spec_from_file_location("penny_press", BASE / "scripts" / "penny-press.py")
if not _penny_spec or not _penny_spec.loader:
    raise RuntimeError("Could not load penny-press.py")
penny_press = importlib.util.module_from_spec(_penny_spec)
_penny_spec.loader.exec_module(penny_press)

MEMORY = BASE / "memory"
PUBLISHING = MEMORY / "publishing"
DESK = PUBLISHING / "press-abundance"
DAILY_DIR = DESK / "daily"
LOG_DIR = BASE / "logs" / "publishing"
LOG_PATH = LOG_DIR / "press-abundance.jsonl"
STORYBOOK_DAILY = MEMORY / "storybook" / "daily"
STORYBOOK_PDF = MEMORY / "storybook" / "pdf"
BLEED_ISSUES = BASE / "bleed" / "issues"
SUPPORT_GUILD = MEMORY / "support-faculty" / "guild"
PENNY_STRATEGY = PUBLISHING / "editorial-strategy.md"
PENNY_BRIEFS = PUBLISHING / "briefs"
PENNY_PROPOSALS = PUBLISHING / "proposals"
PENNY_CANDIDATES = PUBLISHING / "candidates"
PENNY_CONSENT_QUEUE = PUBLISHING / "consent-queue.json"
PENNY_SOCIAL_LEDGER = PUBLISHING / "social-ledger.jsonl"
MARKET_RESEARCH = PUBLISHING / "market-research" / "latest.md"
PRODUCT_SEEDS = PUBLISHING / "product-seeds"
GOLDWATER_DESK = PUBLISHING / "applied-abundance"
GOLDWATER_BRIEFS = GOLDWATER_DESK / "briefs"
GOLDWATER_OFFERS = GOLDWATER_DESK / "offers"
GOLDWATER_CHART = BASE / "players" / "bj-goldwater-chart.md"
CAPABILITIES = BASE / "hooks" / "enchantify-capabilities.md"
CAPABILITIES_ALT = BASE / "hooks" / "Enchantify-Capabilities.md"
WONDER_COMPASS = BASE / "lore" / "wonder-compass-book"
HEARTBEAT = BASE / "HEARTBEAT.md"
SECRETS_ENV = BASE / "config" / "secrets.env"
TARGET = "8729557865"
CHANNEL = "telegram"
ACCOUNT = "enchantify"
ENCHANTIFY_IMAGE_STYLE = (
    "Enchantify storybook-journal illustration style: sparse pen-and-ink linework with loose watercolor washes "
    "on textured aged parchment, visible paper grain, soft ink bleed, watercolor blooms, layered manuscript-page composition, "
    "lush handwritten marginalia, lush watercolor washes, visible library stamps, wax seals, labels, tabs, arrows, "
    "archival overlays, selective jewel-like pops of teal, gold, red, and deep green, airy literary magical field-journal page, "
    "slightly unfinished and hand-made, never glossy corporate marketing art, never generic fantasy digital painting"
)


def now() -> datetime:
    return datetime.now()


def today() -> str:
    return now().strftime("%Y-%m-%d")


def clean(value: Any, limit: int = 800) -> str:
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


def load_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return default or {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else (default or {})
    except Exception:
        return default or {}


def read_jsonl(path: Path, limit: int = 40) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                rows.append(obj)
        except json.JSONDecodeError:
            continue
    return rows


def latest_files(path: Path, pattern: str = "*.md", limit: int = 5, excerpt: int = 1000) -> list[dict[str, str]]:
    if not path.exists():
        return []
    rows = []
    for file in sorted(path.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
        text = read(file, excerpt) if excerpt > 0 else ""
        title = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        rows.append({
            "name": file.name,
            "path": str(file),
            "title": clean(title.group(1) if title else file.stem, 160),
            "mtime": datetime.fromtimestamp(file.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
            "excerpt": clean(text, excerpt),
        })
    return rows


def ensure_dirs() -> None:
    for path in (DESK, DAILY_DIR, LOG_DIR, PRODUCT_SEEDS, PUBLISHING):
        path.mkdir(parents=True, exist_ok=True)
    readme = DESK / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Press & Applied Abundance Desk\n\n"
            "Daily one-call synthesis by Penny Blackletter and Professor Bastion Goldweaver. "
            "Outputs public-safe content drafts, offer strategy, Patreon nurture, merchandising/product seeds, and consent-gated next actions.\n\n"
            "- `daily/` - markdown packets.\n"
            "- `pdf/` and `html/` - rendered by journal_artifact.\n",
            encoding="utf-8",
        )


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
            data = json.loads(oc_path.read_text(encoding="utf-8"))
            oc_cfg = data if isinstance(data, dict) else {}
        except Exception:
            oc_cfg = {}
    port = int(
        os.environ.get("OPENCLAW_GATEWAY_PORT")
        or secrets.get("OPENCLAW_GATEWAY_PORT")
        or oc_cfg.get("gateway", {}).get("port")
        or "18789"
    )
    token = (
        os.environ.get("OPENCLAW_GATEWAY_TOKEN")
        or secrets.get("OPENCLAW_GATEWAY_TOKEN")
        or oc_cfg.get("gateway", {}).get("auth", {}).get("token")
        or ""
    )
    raw_model = os.environ.get("PRESS_ABUNDANCE_MODEL") or secrets.get("PRESS_ABUNDANCE_MODEL") or "openclaw/gpt55"
    timeout_raw = os.environ.get("PRESS_ABUNDANCE_TIMEOUT") or secrets.get("PRESS_ABUNDANCE_TIMEOUT") or "600"
    try:
        timeout = max(180, int(timeout_raw))
    except ValueError:
        timeout = 600
    return port, token, normalize_model(raw_model), timeout


def consent_queue_summary() -> list[dict[str, Any]]:
    data = load_json(PENNY_CONSENT_QUEUE, {"version": 1, "items": []})
    items = data.get("items") if isinstance(data.get("items"), list) else []
    return [
        {
            "id": item.get("id"),
            "status": item.get("status"),
            "platform": item.get("platform"),
            "content_kind": item.get("content_kind"),
            "topic": item.get("topic"),
            "title": item.get("title"),
            "privacy": item.get("privacy"),
            "created_at": item.get("created_at"),
        }
        for item in items[-12:]
    ]


def wonder_compass_excerpt() -> str:
    parts: list[str] = []
    for name in ("read-this-first.md", "introduction.md", "BOOK_TOC.md"):
        path = WONDER_COMPASS / name
        if path.exists():
            parts.append(f"## {path.stem}\n{read(path, 700)}")
    for path in sorted(WONDER_COMPASS.glob("chapter*.md")):
        text = read(path, 950)
        if not text:
            continue
        title = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        heading = title.group(1) if title else path.stem
        parts.append(f"## {heading}\n{text}")
    return clean("\n\n".join(parts), 11000)


def patreon_status_summary() -> dict[str, Any]:
    adapter = BASE / "scripts" / "patreon-adapter.py"
    try:
        spec = importlib.util.spec_from_file_location("patreon_adapter", adapter)
        if not spec or not spec.loader:
            raise RuntimeError("Patreon adapter could not be loaded.")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        data = module.status()
    except Exception as exc:
        return {
            "connected": False,
            "manual_posting": True,
            "diagnosis": clean(exc, 500),
            "recent_posts": [],
        }

    campaigns = data.get("campaigns") or []
    campaign = campaigns[0] if campaigns else {}
    attrs = campaign.get("attributes") or {}
    posts: list[dict[str, str]] = []
    for post in data.get("posts") or []:
        post_attrs = post.get("attributes") or {}
        posts.append({
            "id": clean(post.get("id"), 80),
            "title": clean(post_attrs.get("title"), 180),
            "published_at": clean(post_attrs.get("published_at"), 80),
            "url": clean(post_attrs.get("url"), 260),
        })
    return {
        "connected": bool(data.get("connected")),
        "manual_posting": True,
        "campaign_id": clean(data.get("campaign_id") or campaign.get("id"), 80),
        "creation_name": clean(attrs.get("creation_name"), 180),
        "patron_count": attrs.get("patron_count"),
        "url": clean(attrs.get("url"), 260),
        "recent_posts": posts[:8],
        "diagnosis": clean(data.get("diagnosis"), 500),
    }


def youtube_status_summary() -> dict[str, Any]:
    adapter = BASE / "scripts" / "youtube-adapter.py"
    try:
        spec = importlib.util.spec_from_file_location("youtube_adapter", adapter)
        if not spec or not spec.loader:
            raise RuntimeError("YouTube adapter could not be loaded.")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        data = module.status()
    except Exception as exc:
        return {
            "connected": False,
            "manual_posting": True,
            "upload_enabled": False,
            "diagnosis": clean(exc, 500),
            "recent_videos": [],
        }

    return {
        "connected": bool(data.get("connected")),
        "manual_posting": True,
        "upload_enabled": False,
        "channel_id": clean(data.get("channel_id"), 80),
        "title": clean(data.get("title"), 180),
        "url": clean(data.get("url"), 260),
        "subscriber_count": data.get("subscriber_count"),
        "view_count": data.get("view_count"),
        "video_count": data.get("video_count"),
        "recent_videos": [
            {
                "id": clean(video.get("id"), 80),
                "title": clean(video.get("title"), 180),
                "published_at": clean(video.get("published_at"), 80),
                "url": clean(video.get("url"), 260),
                "views": clean(video.get("views"), 40),
                "likes": clean(video.get("likes"), 40),
                "comments": clean(video.get("comments"), 40),
            }
            for video in (data.get("recent_videos") or [])[:8]
        ],
        "diagnosis": clean(data.get("diagnosis"), 500),
    }


def x_status_summary() -> dict[str, Any]:
    adapter = BASE / "scripts" / "x-adapter.py"
    try:
        spec = importlib.util.spec_from_file_location("x_adapter", adapter)
        if not spec or not spec.loader:
            raise RuntimeError("X adapter could not be loaded.")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        data = module.status()
    except Exception as exc:
        return {
            "connected": False,
            "manual_posting": True,
            "write_enabled": False,
            "diagnosis": clean(exc, 500),
        }

    return {
        "connected": bool(data.get("connected")),
        "manual_posting": True,
        "write_enabled": bool(data.get("write_enabled")),
        "oauth_mode": clean(data.get("oauth_mode"), 80),
        "id": clean(data.get("id"), 80),
        "name": clean(data.get("name"), 180),
        "username": clean(data.get("username"), 80),
        "url": clean(data.get("url"), 260),
        "followers": data.get("followers"),
        "following": data.get("following"),
        "tweet_count": data.get("tweet_count"),
        "diagnosis": clean(data.get("diagnosis"), 500),
    }


def bluesky_status_summary() -> dict[str, Any]:
    adapter = BASE / "scripts" / "bluesky-adapter.py"
    try:
        spec = importlib.util.spec_from_file_location("bluesky_adapter", adapter)
        if not spec or not spec.loader:
            raise RuntimeError("Bluesky adapter could not be loaded.")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        data = module.status()
    except Exception as exc:
        return {
            "connected": False,
            "manual_posting": True,
            "write_enabled": False,
            "diagnosis": clean(exc, 500),
            "recent_posts": [],
        }

    return {
        "connected": bool(data.get("connected")),
        "manual_posting": True,
        "write_enabled": bool(data.get("write_enabled")),
        "did": clean(data.get("did"), 120),
        "handle": clean(data.get("handle"), 120),
        "display_name": clean(data.get("display_name"), 180),
        "url": clean(data.get("url"), 260),
        "followers": data.get("followers"),
        "following": data.get("following"),
        "post_count": data.get("post_count"),
        "recent_posts": [
            {
                "text": clean(post.get("text"), 280),
                "created_at": clean(post.get("created_at"), 80),
                "url": clean(post.get("url"), 260),
                "likes": post.get("like_count"),
                "reposts": post.get("repost_count"),
                "replies": post.get("reply_count"),
            }
            for post in (data.get("recent_posts") or [])[:8]
        ],
        "diagnosis": clean(data.get("diagnosis"), 500),
    }


def collect_context(player: str = "bj") -> dict[str, Any]:
    ensure_dirs()
    capabilities_path = CAPABILITIES if CAPABILITIES.exists() else CAPABILITIES_ALT
    return {
        "date": today(),
        "player": player,
        "mission": {
            "wonder_compass": "Get The Wonder Compass book, philosophy, and practice into as many hands as possible.",
            "patreon": "Nurture the Doobaleedoos $1 Patreon membership as the low-pressure one-dollar door.",
            "enchantify": "Explain and highlight free open-source Enchantify: Pages, Belief, Compass Runs, Enchantments, The Bleed, Book of You, support characters, living-world simulation.",
            "ethics": "Draft and propose. Do not post, spend, schedule, promise income, or expose private data without consent.",
        },
        "heartbeat": clean(read(HEARTBEAT, 2000), 2000),
        "penny_strategy": clean(read(PENNY_STRATEGY, 3500), 3500),
        "goldwater_chart": clean(read(GOLDWATER_CHART, 3500), 3500),
        "market_research": clean(read(MARKET_RESEARCH, 6000), 6000),
        "patreon_status": patreon_status_summary(),
        "youtube_status": youtube_status_summary(),
        "x_status": x_status_summary(),
        "bluesky_status": bluesky_status_summary(),
        "wonder_compass_excerpt": wonder_compass_excerpt(),
        "capabilities_excerpt": clean(read(capabilities_path, 4200), 4200),
        "latest_storybook": latest_files(STORYBOOK_DAILY, "*.md", 4, 1400),
        "latest_storybook_pdfs": latest_files(STORYBOOK_PDF, "*.pdf", 5, 0),
        "latest_bleed": latest_files(BLEED_ISSUES, "*.md", 3, 1400),
        "latest_support_guild": latest_files(SUPPORT_GUILD, "*.md", 3, 1400),
        "latest_penny_briefs": latest_files(PENNY_BRIEFS, "*.md", 5, 1300),
        "latest_penny_proposals": latest_files(PENNY_PROPOSALS, "*.md", 5, 1000),
        "latest_penny_candidates": latest_files(PENNY_CANDIDATES, "*.json", 5, 1200),
        "latest_goldwater_briefs": latest_files(GOLDWATER_BRIEFS, "*.md", 5, 1300),
        "latest_goldwater_offers": latest_files(GOLDWATER_OFFERS, "*.md", 5, 1300),
        "product_seeds": latest_files(PRODUCT_SEEDS, "*.md", 8, 1000),
        "consent_queue": consent_queue_summary(),
        "social_ledger_tail": read_jsonl(PENNY_SOCIAL_LEDGER, 16),
    }


def prompt_context(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "date": context.get("date"),
        "mission": context.get("mission"),
        "penny_strategy": context.get("penny_strategy"),
        "goldwater_chart": context.get("goldwater_chart"),
        "market_research": context.get("market_research"),
        "patreon_status": context.get("patreon_status"),
        "youtube_status": context.get("youtube_status"),
        "x_status": context.get("x_status"),
        "bluesky_status": context.get("bluesky_status"),
        "wonder_compass_excerpt": context.get("wonder_compass_excerpt"),
        "capabilities_excerpt": context.get("capabilities_excerpt"),
        "latest_storybook": context.get("latest_storybook"),
        "latest_bleed": context.get("latest_bleed"),
        "latest_support_guild": context.get("latest_support_guild"),
        "latest_penny_briefs": context.get("latest_penny_briefs"),
        "latest_penny_proposals": context.get("latest_penny_proposals"),
        "latest_goldwater_briefs": context.get("latest_goldwater_briefs"),
        "latest_goldwater_offers": context.get("latest_goldwater_offers"),
        "product_seeds": context.get("product_seeds"),
        "consent_queue": context.get("consent_queue"),
        "social_ledger_tail": context.get("social_ledger_tail"),
    }


def prompt_for(context: dict[str, Any]) -> str:
    return f"""Write today's Press & Applied Abundance council page.

This is one synthesis call, presented as Penny Blackletter and Professor Bastion
Goldweaver working together at the Press & Peculiar Commerce Wing.

Goals:
- Get The Wonder Compass book, philosophy, method, and contents into as many hands as possible.
- Use context.wonder_compass_excerpt as the book/source packet. Pull actual
  chapter ideas into content and offers; do not reduce the book to only
  "Notice, Embark, Sense, Write, Rest."
- Highlight and explain free open-source Enchantify: Pages, Belief/Narrative Weight, Compass Runs, Enchantments, The Bleed, Book of You, support characters, living-world simulation, story journal artifacts.
- Nurture the Doobaleedoos $1 Patreon as the one-dollar door: warm, low-pressure, behind-the-scenes, artifact-forward.
- Use context.patreon_status as live context: campaign name/url, current patron
  count, recent post titles, and posting gap. Shape the next member draft
  around what Patreon actually contains, not a generic membership pitch.
- Use context.youtube_status as live context: channel title/url, subscribers,
  recent videos, and posting gap. Shape YouTube Shorts/long-form ideas around
  what the channel actually contains, not generic creator advice.
- Use context.x_status as live context: account handle/url, follower count,
  post count, and consent-gated write capability. Shape X drafts around the
  actual Academy account, not a generic platform plan.
- Use context.bluesky_status as live context: handle/url, follower count,
  recent posts, and consent-gated write capability. Shape Bluesky drafts around
  conversation and community fit, not a generic platform plan.
- Develop both free content and paid content/merch/product seeds.
- Produce actual drafts Penny can output, with Goldweaver's strategy behind them.
- Use the latest Listening Desk market research when present. It is the shared
  audience map: what target readers are struggling with, language they use,
  platform openings, community etiquette, and offer gaps.

Hard rules:
- Draft only. Nothing is posted, scheduled, purchased, printed, or promised.
- Patreon posting is manual. Produce review-ready Patreon/member drafts and
  posting notes; never claim publication happened.
- YouTube posting is manual. Produce review-ready scripts, titles,
  descriptions, thumbnail concepts, chapters, and upload checklists; never
  claim upload or publication happened.
- X posting is consent-gated. Produce review-ready posts/threads; never claim
  publication happened unless the Publication Desk records approval and action.
- Bluesky posting is consent-gated. Produce review-ready posts/threads; never
  claim publication happened unless the Publication Desk records approval and
  action.
- Keep everything in story and in character, but use simple clear language.
- Protect privacy: do not expose health, therapy, medication, money, exact location, family, relationship, or raw logs.
- Translate private project/life material into public-safe patterns and examples.
- Be specific. No generic "post consistently" advice.
- Include at least one full social draft, one full Patreon/member draft, one product/merch seed, and one open-source Enchantify explainer angle.
- Any visual plan or image prompt must use the Enchantify storybook-journal
  style: sparse pen-and-ink, loose watercolor washes on aged parchment, visible
  grain, soft ink bleed, lush marginalia, stamps, labels, wax seals, archival
  overlays, and selective teal/gold/red/deep-green color. No glossy corporate
  marketing art.
- Every draft should include a CTA that feels like an invitation, not a funnel.
- Include consent status and exact next action for BJ.
- Mention what Penny should carry into her next autonomous content brief.
- Mention what Goldweaver should carry into his next offer/product brief.
- Mention what the latest market research changes about today's strategy. If no
  market research is present, say the Listening Desk needs a fresh run.

Use exactly this Markdown structure:

# Press & Applied Abundance Council — {context["date"]}

## Desk Weather

## Strategic Direction

## Market Research Read

## What Penny Found

## What Goldweaver Sees

## Public-Safe Story Fragments

## Wonder Compass Bridge

## Open-Source Enchantify Angle

## Patreon Nurture

## Free Content Draft

## Paid / Member Content Draft

## Product Or Merch Seed

## Platform Plan

## Consent Queue

## Penny's Next Brief

## Goldweaver's Next Offer

## Tiny Action

## Do Not Do Today

## Structured Packet
Return a fenced json object with keys: title, privacy, strategic_direction, free_content, paid_content, patreon_nurture, product_seed, platform_plan, penny_next_brief, goldwater_next_offer, consent_items, tiny_action.

Current data JSON:
{json.dumps(prompt_context(context), ensure_ascii=False, indent=2, default=str)[:20000]}
"""


def call_llm(context: dict[str, Any]) -> str:
    port, token, model, timeout = gateway_cfg()
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are the combined Press & Applied Abundance desk for Enchantify. "
                    "Penny Blackletter drafts public-safe in-world content; Professor Bastion Goldweaver shapes ethical monetization. "
                    "Reply only with the requested Markdown artifact."
                ),
            },
            {"role": "user", "content": prompt_for(context)},
        ],
        "temperature": 0.76,
        "max_tokens": 4300,
        "stream": False,
    }
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "x-openclaw-session-key": f"press-abundance-{context['date']}-{int(time.time())}",
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


def source_title(context: dict[str, Any]) -> str:
    for key in ("latest_storybook", "latest_bleed", "latest_support_guild"):
        rows = context.get(key) or []
        if rows:
            return rows[0].get("title") or rows[0].get("name") or "today's page"
    return "today's page"


def fallback_packet(context: dict[str, Any], reason: str = "") -> str:
    source = source_title(context)
    patreon = context.get("patreon_status") or {}
    youtube = context.get("youtube_status") or {}
    x_status = context.get("x_status") or {}
    bluesky = context.get("bluesky_status") or {}
    recent_posts = patreon.get("recent_posts") or []
    latest_post = recent_posts[0] if recent_posts else {}
    recent_videos = youtube.get("recent_videos") or []
    latest_video = recent_videos[0] if recent_videos else {}
    patreon_line = (
        f"{patreon.get('creation_name') or 'Patreon'} has "
        f"{patreon.get('patron_count', 'unknown')} patrons visible; "
        f"latest visible post: {latest_post.get('title') or 'none visible'}."
    ) if patreon.get("connected") else "Patreon status was unavailable; keep drafts manual and review-ready."
    youtube_line = (
        f"{youtube.get('title') or 'YouTube'} has "
        f"{youtube.get('subscriber_count', 'unknown')} subscribers visible; "
        f"latest visible video: {latest_video.get('title') or 'none visible'}."
    ) if youtube.get("connected") else "YouTube status was unavailable; keep video drafts manual and review-ready."
    x_line = (
        f"@{x_status.get('username') or 'account'} has "
        f"{x_status.get('followers', 'unknown')} followers and "
        f"{x_status.get('tweet_count', 'unknown')} posts visible. Posting is consent-gated."
    ) if x_status.get("connected") else "X status was unavailable; keep X drafts manual and review-ready."
    bluesky_line = (
        f"@{bluesky.get('handle') or 'account'} has "
        f"{bluesky.get('followers', 'unknown')} followers and "
        f"{bluesky.get('post_count', 'unknown')} posts visible. Posting is consent-gated."
    ) if bluesky.get("connected") else "Bluesky status was unavailable; keep Bluesky drafts manual and review-ready."
    return f"""# Press & Applied Abundance Council — {context['date']}

## Desk Weather
Penny has the clippings spread across the desk; Goldweaver has the offer ledger open. Today's strongest public-safe proof is **{source}**. The gateway was unavailable, so the desk filed a deterministic packet instead of going silent.

## Strategic Direction
Lead with Wonder Compass as a humane practice: Notice, Embark, Sense, Write, Rest. Use Enchantify as the proof that the practice can become a living storybook. Invite people toward the $1 Patreon as the warm one-dollar door, not as a hard sell.

## What Penny Found
- The project now has storybook PDFs, daily pages, Bleed columns, support faculty, Pages, Belief, and character memory.
- The public angle is not "AI app." It is "a free open-source living book that helps ordinary life feel worth noticing."
- The best tone is dispatch from the Academy: useful, strange, grounded, and generous.

## What Goldweaver Sees
- The smallest sellable object remains a **Wonder Compass Field Kit**.
- Free posts should teach one tiny practice.
- Paid/member pieces should add beauty, curation, printability, behind-the-scenes notes, and official Academy canon.

## Public-Safe Story Fragments
- A book opens to the page your real day needs.
- The Compass is not a metaphor; it is a five-step way to notice life again.
- Belief is narrative weight: what receives attention becomes more real.
- The Book of You turns lived days into storybook artifacts.

## Wonder Compass Bridge
Today's bridge: **A Small Door for a Flat Day.** Ask someone to notice one ordinary object, go one step closer, sense one detail, write one sentence, and let that count.

## Open-Source Enchantify Angle
Free/open-source Enchantify is the engine: a living storybook with Pages, Belief, Compass Runs, Enchantments, The Bleed, Book of You PDFs, support characters, and a world that moves while closed. Anyone can run an Academy. BJ and Amanda's Academy is the official lantern.

## Patreon Nurture
The $1 Patreon is the one-dollar door: behind-the-scenes pages, field kits in progress, tiny adventures, Academy artifacts, and the feeling of helping keep the lantern lit.

Current Patreon read: {patreon_line}

Posting remains manual: Penny and Goldweaver prepare the copy, PDF/artifact, caption, and notes; BJ posts by hand after review.

## Free Content Draft
**X / Threads draft**

What if an AI game did not ask you to escape your life, but notice it?

Enchantify is a free open-source living storybook. It opens a Page, asks for one real act of attention, and keeps the proof.

The field guide behind it is The Wonder Compass:
Notice. Embark. Sense. Write. Rest.

Today's tiny spell: find one object you pass every day and look at it like it has been waiting to be seen.

## Paid / Member Content Draft
**$1 Patreon member note**

A page has come loose from the Academy desk.

This week, the one-dollar door is helping us turn Enchantify's daily artifacts into the first Wonder Compass Field Kit: a printable little ritual for flat days, low energy, and ordinary rooms that need a small door.

Members get the messy middle: drafts, pages, field notes, artifacts, and the first lantern-light versions before they become polished.

Thank you for helping the Book stay open.

## Product Or Merch Seed
**Product seed: The Small Door Field Kit**

Includes:
- 1 printable Compass page
- 5 tiny field assignments
- 1 story fragment from Enchantify Academy
- 1 illustrated card
- 1 short audio script
- 1 "let it count" reflection page

Price path: free sample post -> $1 Patreon preview -> $5-$7 polished kit.

## Platform Plan
- Today: X/Threads post plus Patreon member note.
- Next: Instagram carousel from the same idea.
- Later: YouTube Short showing one real object becoming a Compass moment.
- YouTube read: {youtube_line}
- X read: {x_line}
- Bluesky read: {bluesky_line}

## Consent Queue
Needs BJ review before posting. Public-safe as drafted, but links and exact Patreon/book wording should be checked.

## Penny's Next Brief
Draft an Instagram carousel: **A Small Door for a Flat Day**. Slide language should be sparse, practical, and manuscript-page friendly.

## Goldweaver's Next Offer
Create a one-page product brief for **The Small Door Field Kit** with promise, contents, price, free sample, Patreon preview, and minimum shippable version.

## Tiny Action
Approve, revise, or reject the X/Threads draft. If approved, Penny can turn it into the first public post in the sequence.

## Do Not Do Today
Do not build a giant launch. Do not explain every mechanic. Do not turn private health, money, or therapy data into content. Do not make Patreon feel like pressure.

## Structured Packet
```json
{{
  "title": "A Small Door for a Flat Day",
  "privacy": "PUBLIC-SAFE AFTER BJ LINK REVIEW",
  "strategic_direction": "Lead with Wonder Compass practice, use Enchantify as proof, invite to the $1 Patreon gently.",
  "free_content": "X/Threads draft in the packet.",
  "paid_content": "$1 Patreon member note in the packet.",
  "patreon_nurture": "Behind-the-scenes field kit development and Academy artifacts.",
  "product_seed": "The Small Door Field Kit",
  "platform_plan": ["X/Threads", "Patreon", "Instagram carousel", "YouTube Short"],
  "penny_next_brief": "Instagram carousel: A Small Door for a Flat Day",
  "goldwater_next_offer": "One-page Small Door Field Kit product brief",
  "consent_items": ["X/Threads draft", "Patreon member note"],
  "tiny_action": "Review the X/Threads draft."
}}
```

<!-- fallback: {clean(reason, 300)} -->
"""


def extract_structured(markdown: str) -> dict[str, Any]:
    blocks = re.findall(r"```json\s*(.*?)```", markdown, re.DOTALL | re.IGNORECASE)
    for block in reversed(blocks):
        try:
            data = json.loads(block)
            if isinstance(data, dict):
                return data
        except Exception:
            continue
    return {}


def write_packet(markdown: str, date_str: str) -> Path:
    ensure_dirs()
    path = DAILY_DIR / f"{date_str}.md"
    path.write_text(markdown, encoding="utf-8")
    return path


def render_packet(markdown: str, path: Path, *, dry_run: bool = False) -> dict[str, str]:
    image_prompt = (
        "Penny Blackletter and Professor Bastion Goldweaver's Press & Applied Abundance council desk: "
        "clippings, product cards, Wonder Compass notes, Patreon lantern, red pencil, offer ledger, and wax approval seals. "
        f"{ENCHANTIFY_IMAGE_STYLE}. No readable text, no logo, no watermark."
    )
    return journal_artifact.render(
        markdown,
        DESK,
        path.stem,
        title=f"Press & Applied Abundance Council — {path.stem}",
        subtitle="Penny Blackletter and Professor Goldweaver at the marketing desk",
        footer="Filed by The Bleed Margins Desk and the Department of Applied Abundance",
        accent="#8a4f24",
        image_prompt=image_prompt,
        dry_run=dry_run,
    )


def enqueue_packet(markdown: str, path: Path, outputs: dict[str, str], structured: dict[str, Any]) -> str:
    data = penny_press.consent_queue()
    items = data.setdefault("items", [])
    existing = next(
        (
            item for item in items
            if item.get("date") == today()
            and item.get("content_kind") == "press-abundance-daily"
            and item.get("source") == "press-abundance"
        ),
        None,
    )
    item_id = existing.get("id") if existing else f"press-abundance-{now().strftime('%Y%m%d-%H%M%S')}"
    item = {
        "id": item_id,
        "created_at": existing.get("created_at") if existing else now().isoformat(timespec="seconds"),
        "updated_at": now().isoformat(timespec="seconds"),
        "date": today(),
        "player": "bj",
        "platform": "multi-platform",
        "content_kind": "press-abundance-daily",
        "topic": structured.get("title") or "Wonder Compass / Enchantify daily marketing packet",
        "title": structured.get("title") or "Press & Applied Abundance Council",
        "status": "needs_review",
        "privacy": structured.get("privacy") or "NEEDS BJ REVIEW",
        "consent_required": True,
        "autonomy": "daily_press_abundance",
        "source": "press-abundance",
        "brief": str(path),
        "structured": "",
        "pdf": outputs.get("pdf", ""),
        "cta": clean(structured.get("tiny_action", ""), 500),
        "posting_notes": "Review all drafts, links, and privacy before publication. Nothing has been posted.",
        "post_url": "",
        "performance": {"views": None, "likes": None, "comments": None, "shares": None, "saves": None, "clicks": None},
        "lesson": "",
    }
    if existing:
        existing.clear()
        existing.update(item)
    else:
        items.append(item)
    penny_press.save_consent_queue(data)
    append_jsonl(PENNY_SOCIAL_LEDGER, {**item, "ledger_event": "drafted"})
    return item_id


def summarize_for_telegram(markdown: str, path: Path, outputs: dict[str, str]) -> str:
    def section(name: str) -> str:
        m = re.search(rf"^## {re.escape(name)}\s*(.*?)(?=^## |\Z)", markdown, re.DOTALL | re.MULTILINE)
        return clean(m.group(1), 520) if m else ""

    parts = [
        f"Press & Applied Abundance Council — {today()}",
        "",
        section("Desk Weather") or "Penny and Professor Goldweaver filed today's marketing and offer page.",
    ]
    direction = section("Strategic Direction")
    tiny = section("Tiny Action")
    if direction:
        parts.extend(["", "Direction:", direction])
    if tiny:
        parts.extend(["", "Tiny action:", tiny])
    if outputs.get("pdf"):
        parts.extend(["", f"Full storybook PDF attached: {Path(outputs['pdf']).name}"])
    else:
        parts.extend(["", f"Full packet: {path.name}"])
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


def run_daily(*, player: str = "bj", send: bool = False, dry_run: bool = False, no_llm: bool = False, silent: bool = False) -> int:
    context = collect_context(player)
    llm_error = ""
    if no_llm:
        markdown = fallback_packet(context, "LLM disabled")
    else:
        try:
            markdown = call_llm(context)
            if not markdown or "# Press & Applied Abundance Council" not in markdown:
                raise RuntimeError("model returned an empty or malformed press-abundance packet")
        except Exception as exc:
            llm_error = str(exc)
            markdown = fallback_packet(context, llm_error)
    structured = extract_structured(markdown)
    if dry_run:
        print(markdown)
        path = DAILY_DIR / f"{today()}.md"
        outputs = render_packet(markdown, path, dry_run=True)
    else:
        path = write_packet(markdown, today())
        outputs = render_packet(markdown, path)
        consent_id = enqueue_packet(markdown, path, outputs, structured)
        append_jsonl(LOG_PATH, {
            "kind": "daily",
            "player": player,
            "path": str(path),
            "html": outputs.get("html", ""),
            "pdf": outputs.get("pdf", ""),
            "pdf_detail": outputs.get("pdf_detail", ""),
            "consent_id": consent_id,
            "llm_error": llm_error,
            "sent": False,
        })
    if send:
        message = summarize_for_telegram(markdown, path, outputs)
        skip, digest, reason = cron_steward.should_skip_duplicate(
            "press-abundance",
            message,
            cooldown_hours=20,
            scope=today(),
        )
        if skip and not dry_run:
            cron_steward.mark_skipped("press-abundance", reason, scope=today(), fingerprint=digest)
            return 0
        media = None
        if not dry_run:
            media = Path(outputs["pdf"]) if outputs.get("pdf") else Path(outputs["html"])
        rc = send_telegram(message, media if media and media.exists() else None, dry_run=dry_run, silent=silent)
        if rc == 0 and not dry_run:
            cron_steward.mark_delivered("press-abundance", message, scope=today(), path=str(path))
            append_jsonl(LOG_PATH, {
                "kind": "delivery",
                "player": player,
                "path": str(path),
                "media": str(media) if media and media.exists() else "",
                "sent": True,
            })
        return rc
    if not dry_run:
        print(f"PRESS_ABUNDANCE: {path}")
        if outputs.get("pdf"):
            print(f"PDF: {outputs['pdf']}")
        if llm_error:
            print(f"LLM_FALLBACK: {llm_error}", file=sys.stderr)
    return 0


def status() -> int:
    ensure_dirs()
    latest = sorted(DAILY_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:5]
    print("PRESS & APPLIED ABUNDANCE STATUS")
    print(f"Desk: {DESK}")
    print(f"Daily packets: {len(list(DAILY_DIR.glob('*.md')))}")
    for path in latest:
        print(f"- {path.name}")
    print(f"Consent queue: {PENNY_CONSENT_QUEUE}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Penny + Goldweaver daily Press & Applied Abundance synthesis.")
    sub = parser.add_subparsers(dest="command", required=True)

    daily = sub.add_parser("daily")
    daily.add_argument("player", nargs="?", default="bj")
    daily.add_argument("--send", action="store_true")
    daily.add_argument("--dry-run", action="store_true")
    daily.add_argument("--no-llm", action="store_true")
    daily.add_argument("--silent", action="store_true")

    sub.add_parser("status")

    args = parser.parse_args()
    with cron_steward.run(f"press-abundance:{args.command}"):
        if args.command == "daily":
            return run_daily(player=args.player, send=args.send, dry_run=args.dry_run, no_llm=args.no_llm, silent=args.silent)
        if args.command == "status":
            return status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Penny Blackletter's Press & Peculiar Commerce desk.

Creates in-world, public-safe marketing/editorial packets from Enchantify's
daily artifacts. Penny drafts; she never posts.
"""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "scripts"))
import journal_artifact  # type: ignore

MEMORY = BASE / "memory"
PRESS_DIR = MEMORY / "publishing"
PACKET_DIR = PRESS_DIR / "press-packets"
CANDIDATE_DIR = PRESS_DIR / "candidates"
APPROVED_DIR = PRESS_DIR / "approved"
PUBLISHED_DIR = PRESS_DIR / "published"
PRIVACY_DIR = PRESS_DIR / "privacy"
PRODUCT_DIR = PRESS_DIR / "product-seeds"
BRIEF_DIR = PRESS_DIR / "briefs"
PROPOSAL_DIR = PRESS_DIR / "proposals"
IMAGE_DIR = PRESS_DIR / "images"
PRESS_ABUNDANCE_DIR = PRESS_DIR / "press-abundance" / "daily"
MARKET_RESEARCH = PRESS_DIR / "market-research" / "latest.md"
CONSENT_QUEUE = PRESS_DIR / "consent-queue.json"
SOCIAL_LEDGER = PRESS_DIR / "social-ledger.jsonl"
STRATEGY_FILE = PRESS_DIR / "editorial-strategy.md"
LOG_DIR = BASE / "logs" / "publishing"
SECRETS_ENV = BASE / "config" / "secrets.env"
STORYBOOK_DAILY = MEMORY / "storybook" / "daily"
SCENE_LEDGER = BASE / "logs" / "scene-ledger"
SUPPORT_GUILD = MEMORY / "support-faculty" / "guild"
BLEED_ISSUES = BASE / "bleed" / "issues"
NPC_RESEARCH = MEMORY / "npc-research"
CAPABILITIES = BASE / "hooks" / "Enchantify-Capabilities.md"
WONDER_COMPASS = BASE / "lore" / "wonder-compass-book"
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


PLATFORM_SPECS: dict[str, dict[str, Any]] = {
    "x-post": {
        "label": "X Post",
        "output": ["single post under 280 characters", "optional 2-5 post thread", "CTA", "privacy label"],
        "notes": "Sharp, quotable, in-world. No hashtag soup.",
    },
    "x-thread": {
        "label": "X Thread",
        "output": ["hook post", "4-8 numbered posts", "CTA", "image suggestion", "privacy label"],
        "notes": "Teach one Enchantify/Wonder Compass idea through a tiny Academy dispatch.",
    },
    "bluesky-post": {
        "label": "Bluesky Post",
        "output": ["single post under 300 characters", "optional short thread", "CTA", "privacy label"],
        "notes": "Conversational, generous, weird-in-public without sounding like a brand account.",
    },
    "bluesky-thread": {
        "label": "Bluesky Thread",
        "output": ["hook post", "3-6 connected posts", "soft CTA", "image suggestion", "privacy label"],
        "notes": "Teach one idea clearly; Bluesky rewards genuine conversation more than funnel language.",
    },
    "instagram-carousel": {
        "label": "Instagram Carousel",
        "output": ["7-10 slides", "slide text", "image direction per slide", "caption", "alt text", "hashtags", "CTA", "privacy label"],
        "notes": "Use manuscript-page visual language. Prefer existing Enchantify images; generate only when useful.",
    },
    "tiktok-carousel": {
        "label": "TikTok Carousel",
        "output": ["5-8 slides", "short punchy slide text", "caption", "sound/music mood", "CTA", "privacy label"],
        "notes": "Faster and stranger than Instagram, but still in-world.",
    },
    "youtube-short": {
        "label": "YouTube Short",
        "output": ["hook", "30-60 second script", "shot list", "on-screen text", "caption", "CTA", "privacy label"],
        "notes": "Concrete visual beats. Can be BJ/Amanda voice or Academy dispatch voice.",
    },
    "youtube-long": {
        "label": "YouTube Long Form",
        "output": ["title options", "thumbnail concept", "cold open", "outline", "script sections", "CTA", "privacy label"],
        "notes": "Build an episode that can actually be filmed or narrated.",
    },
    "reddit-post": {
        "label": "Reddit Post",
        "output": ["subreddit fit", "non-spammy angle", "post draft", "comment followups", "no-promo version", "CTA only if appropriate", "privacy label"],
        "notes": "Contribute to the room before inviting anyone through the door. Avoid drive-by promotion.",
    },
    "reddit-comment": {
        "label": "Reddit Comment",
        "output": ["context assumption", "helpful comment", "soft disclosure/CTA only if appropriate", "privacy label"],
        "notes": "Helpful first. Link only if the subreddit and conversation make it welcome.",
    },
    "patreon-post": {
        "label": "Patreon Post",
        "output": ["title", "member note", "behind-the-scenes artifact", "field assignment", "CTA", "privacy label"],
        "notes": "Make the one-dollar door feel warm and worth entering.",
    },
    "content-menu": {
        "label": "Content Menu",
        "output": ["3-7 content options", "best platform", "why it serves the mission", "privacy notes", "next step"],
        "notes": "Useful for interactive planning with Penny.",
    },
}


def ensure_dirs() -> None:
    for path in [PACKET_DIR, CANDIDATE_DIR, APPROVED_DIR, PUBLISHED_DIR, PRIVACY_DIR, PRODUCT_DIR, BRIEF_DIR, PROPOSAL_DIR, IMAGE_DIR, LOG_DIR]:
        path.mkdir(parents=True, exist_ok=True)
    readme = PRESS_DIR / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Penny Blackletter's Press & Peculiar Commerce Desk\n\n"
            "This archive holds public-safe drafts, editorial packets, privacy notes, "
            "and product seeds. Penny drafts in story; BJ approves anything that leaves the Labyrinth.\n\n"
            "- `press-packets/` — daily or weekly editorial packets.\n"
            "- `candidates/` — structured social/newsletter/patreon draft data.\n"
            "- `approved/` — human-approved pieces ready to publish.\n"
            "- `published/` — records of pieces already used.\n"
            "- `privacy/` — notes on what must stay private or be sanitized.\n"
            "- `product-seeds/` — field-kit, zine, Patreon, and Wonder Compass product ideas.\n"
            "- `briefs/` — on-demand platform briefs, carousels, scripts, and Reddit drafts.\n"
            "- `proposals/` — lightweight Penny-led content menus.\n"
            "- `images/` — locally generated carousel/post art assets.\n"
            "- `market-research/` — Listening Desk audience and platform signals shared with Goldweaver.\n",
            encoding="utf-8",
        )
    if not STRATEGY_FILE.exists():
        STRATEGY_FILE.write_text(
            "# Penny Blackletter Editorial Strategy\n\n"
            "## Mission\n"
            "Get The Wonder Compass into as many hands as possible, invite people through the Doobaleedoos $1 Patreon one-dollar door, and show free open-source Enchantify as a rich living storybook engine.\n\n"
            "## Content Pillars\n"
            "- Wonder Compass field assignments: Notice, Embark, Sense, Write, Rest.\n"
            "- Open-source Enchantify: living book, Pages, Belief, Enchantments, Compass Runs, The Bleed, Storybook, support faculty.\n"
            "- The Doobaleedoos one-dollar door: low-pressure support, behind-the-scenes artifacts, tiny adventures.\n"
            "- Public-safe Academy dispatches: in-world scenes, images, artifacts, and lore that invite curiosity.\n"
            "- Anti-Nothing practice: attention, play, tiny action, and real life as the Climax Chapter.\n\n"
            "## Autonomy Level\n"
            "Level 1: Penny may draft autonomously and ask BJ for consent. She may not publish, schedule, spend money, or message public platforms.\n\n"
            "## Privacy Rules\n"
            "Never publish private health, therapy, money, medication, exact location, family, relationship, or raw log details without explicit clearance. Translate private patterns into public-safe metaphor.\n\n"
            "## Voice\n"
            "Always in story. Invitation, not funnel. Wonder before ask. Useful before promotional.\n",
            encoding="utf-8",
        )
    if not CONSENT_QUEUE.exists():
        CONSENT_QUEUE.write_text(json.dumps({"version": 1, "items": []}, indent=2) + "\n", encoding="utf-8")


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


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def read_jsonl(path: Path, limit: int = 80) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
        try:
            data = json.loads(line)
            if isinstance(data, dict):
                rows.append(data)
        except Exception:
            continue
    return rows


def load_config() -> dict[str, str]:
    cfg: dict[str, str] = {}
    if SECRETS_ENV.exists():
        for line in SECRETS_ENV.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                cfg[key.strip()] = value.strip().strip('"').strip("'")
    config_json = BASE / "config" / "penny-press.json"
    if config_json.exists():
        try:
            data = json.loads(config_json.read_text(encoding="utf-8"))
            for key, value in data.items():
                if value is not None:
                    cfg[str(key)] = str(value)
        except Exception:
            pass
    return cfg


def normalize_model(model: str) -> str:
    model = (model or "").strip()
    if model in {"openclaw", "default", "gateway", ""}:
        return "openclaw"
    return model


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
    raw_model = os.environ.get("PENNY_PRESS_MODEL") or secrets.get("PENNY_PRESS_MODEL") or os.environ.get("BLEED_MODEL") or secrets.get("BLEED_MODEL") or "openclaw"
    timeout_raw = os.environ.get("PENNY_PRESS_TIMEOUT") or secrets.get("PENNY_PRESS_TIMEOUT") or "240"
    try:
        timeout = max(30, int(timeout_raw))
    except ValueError:
        timeout = 120
    return port, token, normalize_model(raw_model), timeout


def strip_html(text: str, limit: int = 5000) -> str:
    text = re.sub(r"<(script|style).*?</\1>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return clean(html.unescape(text), limit)


def latest_matching(directory: Path, date_str: str, suffixes: tuple[str, ...]) -> list[Path]:
    if not directory.exists():
        return []
    matches: list[Path] = []
    for suffix in suffixes:
        matches.extend(directory.rglob(f"*{date_str}*{suffix}"))
    return sorted(matches, key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)


def scene_rows(date_str: str, player: str) -> list[dict[str, Any]]:
    path = SCENE_LEDGER / f"{date_str}.jsonl"
    rows = read_jsonl(path, limit=200)
    if player:
        rows = [r for r in rows if str(r.get("player", player)).lower() == player.lower()]
    return rows[-12:]


def image_rows(date_str: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in [
        BASE / "logs" / "drawthings-keepalive.jsonl",
        BASE / "logs" / "drawthings_scene.jsonl",
        BASE / "logs" / "drawthings-scene.jsonl",
    ]:
        for row in read_jsonl(path, limit=200):
            ts = str(row.get("timestamp") or row.get("created_at") or "")
            image_path = row.get("image") or row.get("path") or row.get("output")
            if date_str in ts or (image_path and date_str in str(image_path)):
                rows.append(row)
    return rows[-10:]


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

    videos: list[dict[str, str]] = []
    for video in data.get("recent_videos") or []:
        videos.append({
            "id": clean(video.get("id"), 80),
            "title": clean(video.get("title"), 180),
            "published_at": clean(video.get("published_at"), 80),
            "url": clean(video.get("url"), 260),
            "views": clean(video.get("views"), 40),
            "likes": clean(video.get("likes"), 40),
            "comments": clean(video.get("comments"), 40),
        })
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
        "recent_videos": videos[:8],
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


def find_wonder_excerpt() -> str:
    parts: list[str] = []
    for name in ("read-this-first.md", "introduction.md", "BOOK_TOC.md"):
        path = WONDER_COMPASS / name
        text = read(path, limit=700)
        if text:
            parts.append(f"## {path.stem}\n{text}")
    for path in sorted(WONDER_COMPASS.glob("chapter*.md")):
        text = read(path, limit=950)
        if not text:
            continue
        title = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        parts.append(f"## {title.group(1) if title else path.stem}\n{text}")
    return clean("\n\n".join(parts), 11000)


def build_context(player: str, date_str: str) -> dict[str, Any]:
    storybook = read(STORYBOOK_DAILY / f"{date_str}.md", limit=9000)
    support = read(SUPPORT_GUILD / f"{date_str}.md", limit=4500)
    bleed_paths = latest_matching(BLEED_ISSUES, date_str, (".html", ".md"))
    bleed = strip_html(read(bleed_paths[0], limit=12000), 5000) if bleed_paths else ""
    research_paths = latest_matching(NPC_RESEARCH, date_str, (".md", ".html"))
    research = [clean(strip_html(read(path, limit=4000)), 1000) for path in research_paths[:4]]
    capabilities = read(CAPABILITIES, limit=7000)
    feature_lines = []
    for line in capabilities.splitlines():
        if any(token in line.lower() for token in ["page", "compass", "enchantment", "storybook", "open-source", "belief", "bleed"]):
            feature_lines.append(line.strip())
    cfg = load_config()
    title_match = re.search(r"^##\s+(.+)", storybook, re.MULTILINE) or re.search(r"^#\s+(.+)", storybook, re.MULTILINE)
    storybook_title = clean(title_match.group(1), 140) if title_match else ""
    return {
        "date": date_str,
        "player": player,
        "storybook_title": storybook_title,
        "mission": {
            "wonder_compass_url": cfg.get("WONDER_COMPASS_URL", ""),
            "patreon_url": cfg.get("PATREON_URL", ""),
            "github_url": cfg.get("GITHUB_URL", ""),
            "doobaleedoos_url": cfg.get("DOOBALEEDOOS_URL", ""),
            "cta_policy": "Invite people toward The Wonder Compass, the Doobaleedoos $1 Patreon, and free open-source Enchantify without guilt, false scarcity, or breaking the in-world voice.",
        },
        "patreon_status": patreon_status_summary(),
        "youtube_status": youtube_status_summary(),
        "x_status": x_status_summary(),
        "bluesky_status": bluesky_status_summary(),
        "sources": {
            "storybook": storybook[:4500],
            "market_research": clean(read(MARKET_RESEARCH, 4500), 4500),
            "scene_rows": scene_rows(date_str, player),
            "support_guild": clean(support, 2500),
            "bleed": clean(bleed, 2500),
            "npc_research": research,
            "images": image_rows(date_str),
            "wonder_compass_excerpt": find_wonder_excerpt(),
            "enchantify_feature_lines": feature_lines[:45],
        },
        "privacy_rules": [
            "Health, therapy, mood, medication, ledger, family, and relationship details are private unless explicitly cleared.",
            "Public drafts may translate a private pattern into a general image or prompt, but must not expose the private fact.",
            "Penny drafts only. She does not post, email, publish, or spend money.",
            "Patreon is manual-posting only for now: draft usable content, attach/review files, and never claim publication happened.",
            "YouTube is manual-posting only for now: draft scripts, titles, descriptions, thumbnails, and Shorts/long-form plans; never claim upload or publication happened.",
            "X is consent-gated even when write credentials exist: draft posts/threads and queue them for BJ approval; do not claim publication happened.",
            "Bluesky is consent-gated even when write credentials exist: draft posts/threads and queue them for BJ approval; do not claim publication happened.",
            "Every public piece should stay in story and in character.",
            "Every CTA should feel like an invitation from the Academy, not a sales funnel.",
        ],
    }


def prompt_for(context: dict[str, Any]) -> str:
    return f"""You are Penny Blackletter, Editor-in-Chief of The Bleed and keeper of the Press & Peculiar Commerce desk.

Create today's Press Packet for Enchantify. Your job is social media, marketing,
content curation, and mission-aligned public storytelling.

Mission:
- Get The Wonder Compass into as many hands as possible.
- Invite people through the Doobaleedoos $1 Patreon "one-dollar door".
- Explain and highlight free open-source Enchantify: its storybook engine,
  mechanics, Pages, Belief, Compass Runs, Enchantments, Bleed, support faculty,
  lore, and living-world artifacts.
- Use sources.market_research as the latest Listening Desk audience map when it
  is present: struggles, language, platform fit, Reddit/community etiquette,
  and what people seem hungry for.
- Use patreon_status when present: campaign name/url, patron count, recent
  post titles, and posting gaps. Do not repeat a recent Patreon post unless
  intentionally refreshing it from a new angle.
- Use youtube_status when present: channel title/url, subscriber count, recent
  video titles, and posting gaps. Do not repeat recent YouTube topics unless
  intentionally turning them into a series.
- Use x_status when present: account handle/url, follower count, tweet count,
  and whether write credentials exist. Draft sharp posts and threads, but keep
  publication consent-gated.
- Use bluesky_status when present: handle/url, follower count, post count, and
  recent posts. Draft conversational Bluesky posts/threads that invite replies,
  but keep publication consent-gated.
- Stay in story and in character. No generic marketing voice.

Hard rules:
- Draft only. Do not claim anything has been posted.
- Patreon posting is manual. Create review-ready Patreon copy and assets; do
  not imply Enchantify posted it.
- YouTube posting is manual. Create review-ready scripts, titles,
  descriptions, thumbnail concepts, and video notes; do not imply Enchantify
  uploaded it.
- X posting is consent-gated. Create review-ready posts/threads; do not imply
  Enchantify posted them.
- Bluesky posting is consent-gated. Create review-ready posts/threads; do not
  imply Enchantify posted them.
- Be specific to the source material, but sanitize private material.
- Do not expose health, therapy, money, relationship, exact location, or family
  data. Translate private facts into public-safe metaphor when useful.
- Use Wonder Compass language: Notice, Embark, Sense, Write, Rest.
- Use sources.wonder_compass_excerpt as the book/source packet. Pull actual
  chapter concepts, prompts, language, and product ideas from it; do not flatten
  Wonder Compass into only the five direction names.
- Include clear CTAs, but make them gentle and story-shaped.
- Label each draft with privacy level: PUBLIC-SAFE, SANITIZE, PRIVATE, or NEEDS BJ.
- Prefer short, useful pieces BJ could actually post.
- Borrow real audience language from the Listening Desk without sounding like a
  trend-chaser.

Use exactly this Markdown structure:

# Penny Blackletter Press Packet — {context["date"]}

## Editorial Weather

## Shimmering Fragments

## Public-Safe Drafts

### Field Assignment From the Margins

### Open-Source Enchantify Dispatch

### The One-Dollar Door

### Wonder Compass Book Note

## Needs Sanitizing

## Never Print

## Product Seeds

## Penny's One Tiny Action

## Structured Candidates
Return a fenced json block with an array of 3-6 candidate objects. Each object
must include title, channel, privacy, draft, cta, source, and next_action.

Current data JSON:
{json.dumps(context, ensure_ascii=False, indent=2, default=str)[:15000]}
"""


def call_llm(context: dict[str, Any]) -> str:
    port, token, model, timeout = gateway_cfg()
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are Penny Blackletter writing in-world editorial and marketing packets. "
                    "Be vivid, practical, privacy-aware, and specific. Reply only with the requested Markdown."
                ),
            },
            {"role": "user", "content": prompt_for(context)},
        ],
        "temperature": 0.76,
        "max_tokens": 1800,
        "stream": False,
    }
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "x-openclaw-session-key": f"penny-press-{context['date']}-{int(time.time())}",
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
    return (
        result.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )


def fallback_packet(context: dict[str, Any], reason: str = "") -> str:
    storybook = context["sources"].get("storybook") or ""
    title = context.get("storybook_title") or "The Book Opened and Left Proof"
    fragments = []
    for line in storybook.splitlines():
        line = line.strip("- #")
        if 40 <= len(line) <= 180 and not any(word in line.lower() for word in ["blood", "medication", "balance", "therapy"]):
            fragments.append(line)
        if len(fragments) >= 4:
            break
    fragments = fragments or ["A living book turned one ordinary day into a page that could be kept."]
    candidates = [
        {
            "title": "Field Assignment From the Margins",
            "channel": "social",
            "privacy": "PUBLIC-SAFE",
            "draft": "Field Assignment from the Margins: find one ordinary object that has been waiting below your notice. Look twice. Write one sentence. That is enough magic for a Tuesday.",
            "cta": "The Wonder Compass is the field guide behind this practice.",
            "source": "Wonder Compass",
            "next_action": "Post as a tiny prompt with one manuscript-style image.",
        },
        {
            "title": "Open-Source Enchantify Dispatch",
            "channel": "newsletter/social",
            "privacy": "PUBLIC-SAFE",
            "draft": "From the Academy desk: Enchantify is a free open-source living storybook engine where scenes, Compass Runs, Enchantments, newspapers, support faculty, and artifacts all become pages. The spell is inspectable. The invitation is real.",
            "cta": "Visit the repo when the public link is ready.",
            "source": "Enchantify capabilities",
            "next_action": "Pair with a short feature thread.",
        },
        {
            "title": "The One-Dollar Door",
            "channel": "Patreon",
            "privacy": "PUBLIC-SAFE",
            "draft": "The one-dollar door is not a velvet rope. It is a tiny lantern. If The Doobaleedoos and Wonder Compass help you notice the world again, one dollar keeps the lantern lit.",
            "cta": "Join the Doobaleedoos $1 Patreon when the link is ready.",
            "source": "Press mission",
            "next_action": "Use as a pinned Patreon invitation.",
        },
    ]
    lines = [
        f"# Penny Blackletter Press Packet — {context['date']}",
        "",
        "## Editorial Weather",
        f"Penny circles `{title}` in red pencil and writes: the public angle is proof-of-life, not product hype.",
        "",
        "## Shimmering Fragments",
        *[f"- {frag}" for frag in fragments[:4]],
        "",
        "## Public-Safe Drafts",
        "",
        "### Field Assignment From the Margins",
        candidates[0]["draft"] + " " + candidates[0]["cta"],
        "",
        "### Open-Source Enchantify Dispatch",
        candidates[1]["draft"] + " " + candidates[1]["cta"],
        "",
        "### The One-Dollar Door",
        candidates[2]["draft"] + " " + candidates[2]["cta"],
        "",
        "### Wonder Compass Book Note",
        "Wonder Compass is the Academy field manual for finding magic where life already is: Notice, Embark, Sense, Write, Rest.",
        "",
        "## Needs Sanitizing",
        "- Any body, money, therapy, exact-place, or relationship detail should become metaphor before it becomes public copy.",
        "",
        "## Never Print",
        "- Raw logs, exact balances, diagnoses, medications, private conversations, and anything BJ has not cleared.",
        "",
        "## Product Seeds",
        "- A low-energy Wonder Compass field kit built from today's gentlest public-safe prompt.",
        "- A short open-source Enchantify feature tour written as a tour of Academy offices.",
        "",
        "## Penny's One Tiny Action",
        "Choose one public-safe draft and pair it with one existing manuscript-style image.",
        "",
        "## Structured Candidates",
        "```json",
        json.dumps(candidates, ensure_ascii=False, indent=2),
        "```",
    ]
    if reason and reason != "LLM disabled":
        lines.append(f"\n<!-- fallback: {clean(reason, 300)} -->")
    return "\n".join(lines) + "\n"


def extract_candidates(markdown: str) -> list[dict[str, Any]]:
    blocks = re.findall(r"```json\s*(.*?)```", markdown, flags=re.DOTALL | re.IGNORECASE)
    for block in reversed(blocks):
        try:
            data = json.loads(block)
            if isinstance(data, list):
                return [row for row in data if isinstance(row, dict)]
            if isinstance(data, dict) and isinstance(data.get("candidates"), list):
                return [row for row in data["candidates"] if isinstance(row, dict)]
        except Exception:
            continue
    return []


def write_outputs(markdown: str, candidates: list[dict[str, Any]], date_str: str) -> tuple[Path, Path]:
    packet_path = PACKET_DIR / f"{date_str}.md"
    candidate_path = CANDIDATE_DIR / f"{date_str}.json"
    packet_path.write_text(markdown, encoding="utf-8")
    candidate_path.write_text(json.dumps({"date": date_str, "candidates": candidates}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return packet_path, candidate_path


def summarize_for_telegram(markdown: str, packet_path: Path) -> str:
    def section(name: str) -> str:
        m = re.search(rf"^## {re.escape(name)}\s*(.*?)(?=^## |\Z)", markdown, re.DOTALL | re.MULTILINE)
        return clean(m.group(1), 650) if m else ""

    return "\n".join([
        f"Penny Blackletter Press Packet — {today()}",
        "",
        section("Editorial Weather") or "Penny filed a press packet.",
        "",
        "Tiny action:",
        section("Penny's One Tiny Action") or "Choose one public-safe draft.",
        "",
        f"Full packet attached: {packet_path.name}",
    ])


def telegram_send(message: str, media: Path | None = None, *, dry_run: bool = False, silent: bool = False) -> int:
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
        append_jsonl(LOG_DIR / "send-errors.jsonl", {
            "kind": "telegram_send_error",
            "stderr": clean(proc.stderr or proc.stdout, 2000),
            "media": str(media) if media else "",
        })
        if media:
            fallback = message + f"\n\nFile delivery failed; local artifact: {media}"
            retry_args = [
                "openclaw", "message", "send",
                "--target", TARGET,
                "--channel", CHANNEL,
                "--account", ACCOUNT,
                "--message", fallback,
            ]
            if silent:
                retry_args.append("--silent")
            retry = subprocess.run(retry_args, cwd=BASE, capture_output=True, text=True, timeout=120)
            append_jsonl(LOG_DIR / "send-errors.jsonl", {
                "kind": "telegram_send_fallback",
                "returncode": retry.returncode,
                "stderr": clean(retry.stderr or retry.stdout, 2000),
                "media": str(media),
            })
            return retry.returncode
    return proc.returncode


def run_scan(player: str, date_str: str, *, no_llm: bool = False, dry_run: bool = False, send: bool = False, silent: bool = False) -> int:
    ensure_dirs()
    context = build_context(player, date_str)
    llm_error = ""
    if no_llm:
        markdown = fallback_packet(context, "LLM disabled")
    else:
        try:
            markdown = call_llm(context)
            if not markdown or "# Penny Blackletter Press Packet" not in markdown:
                raise RuntimeError("model returned an empty or malformed press packet")
        except Exception as exc:
            llm_error = str(exc)
            markdown = fallback_packet(context, llm_error)
    candidates = extract_candidates(markdown)
    if dry_run:
        print(markdown)
        packet_path = PACKET_DIR / f"{date_str}.md"
        candidate_path = CANDIDATE_DIR / f"{date_str}.json"
    else:
        packet_path, candidate_path = write_outputs(markdown, candidates, date_str)
        append_jsonl(LOG_DIR / "penny-press.jsonl", {
            "kind": "press_packet",
            "date": date_str,
            "player": player,
            "packet": str(packet_path),
            "candidates": str(candidate_path),
            "candidate_count": len(candidates),
            "llm_error": llm_error,
            "sent": False,
        })
    if send:
        rc = telegram_send(summarize_for_telegram(markdown, packet_path), packet_path, dry_run=dry_run, silent=silent)
        if not dry_run:
            append_jsonl(LOG_DIR / "penny-press.jsonl", {
                "kind": "press_packet_sent",
                "date": date_str,
                "packet": str(packet_path),
                "returncode": rc,
            })
        return rc
    if not dry_run:
        print(f"PRESS_PACKET: {packet_path}")
        print(f"CANDIDATES: {candidate_path}")
        if llm_error:
            print(f"LLM_FALLBACK: {llm_error}", file=sys.stderr)
    return 0


def slugify(value: str, default: str = "brief") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:70] or default


def platform_spec(kind: str) -> dict[str, Any]:
    return PLATFORM_SPECS.get(kind, PLATFORM_SPECS["content-menu"])


def latest_packet_excerpt() -> str:
    packets = sorted(PACKET_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return read(packets[0], limit=2500) if packets else ""


def latest_press_abundance_excerpt() -> str:
    packets = sorted(PRESS_ABUNDANCE_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return read(packets[0], limit=4200) if packets else ""


def content_context(player: str, date_str: str, topic: str, kind: str, source: str) -> dict[str, Any]:
    context = build_context(player, date_str)
    context["request"] = {
        "kind": kind,
        "platform_spec": platform_spec(kind),
        "topic": topic,
        "source": source,
        "latest_press_packet": clean(latest_packet_excerpt(), 2500),
        "latest_press_abundance_council": clean(latest_press_abundance_excerpt(), 4200),
        "latest_market_research": clean(read(MARKET_RESEARCH, 5000), 5000),
        "editorial_strategy": clean(read(STRATEGY_FILE, limit=4000), 4000),
        "consent_queue_summary": consent_queue_summary(),
        "recent_social_ledger": recent_social_ledger(),
        "patreon_status": patreon_status_summary(),
        "youtube_status": youtube_status_summary(),
        "x_status": x_status_summary(),
        "bluesky_status": bluesky_status_summary(),
    }
    return context


def consent_queue() -> dict[str, Any]:
    data = load_json(CONSENT_QUEUE, {"version": 1, "items": []})
    if not isinstance(data.get("items"), list):
        data["items"] = []
    return data


def save_consent_queue(data: dict[str, Any]) -> None:
    data["items"] = data.get("items", [])[-100:]
    save_json(CONSENT_QUEUE, data)


def consent_queue_summary() -> list[dict[str, Any]]:
    data = consent_queue()
    return [
        {
            "id": item.get("id"),
            "status": item.get("status"),
            "platform": item.get("platform"),
            "content_kind": item.get("content_kind"),
            "topic": item.get("topic"),
            "privacy": item.get("privacy"),
            "created_at": item.get("created_at"),
        }
        for item in data.get("items", [])[-12:]
    ]


def recent_social_ledger(limit: int = 12) -> list[dict[str, Any]]:
    rows = read_jsonl(SOCIAL_LEDGER, limit=limit)
    return rows[-limit:]


def prompt_for_brief(context: dict[str, Any]) -> str:
    spec = context["request"]["platform_spec"]
    return f"""You are Penny Blackletter at the Press & Peculiar Commerce desk.

Create an on-demand content brief for: {spec["label"]}.

Topic/request: {context["request"]["topic"] or "Use today's strongest public-safe Enchantify/Wonder Compass material."}
Source preference: {context["request"]["source"]}

Mission:
- Get The Wonder Compass into as many hands as possible.
- Invite people through the Doobaleedoos $1 Patreon one-dollar door when appropriate.
- Highlight free open-source Enchantify, its mechanics, lore, Pages, Belief, Compass Runs, Enchantments, Storybook, and living-world richness.
- Keep every piece in story and in character.
- Treat request.latest_press_abundance_council as today's shared strategy from Penny and Professor Goldweaver. Carry it forward instead of inventing a disconnected plan.
- Treat request.latest_market_research as the Listening Desk audience map. Use it to choose platform fit, pain points, borrowed language, and what not to say.
- Treat request.patreon_status as live context for the one-dollar door:
  campaign name/url, patron count, recent posts, and posting gap. Use it to
  avoid repetition and to make Patreon drafts feel current.
- Treat request.youtube_status as live context for YouTube strategy: channel
  name/url, subscriber count, recent videos, posting gap, and what topics need
  a follow-up or should be avoided for repetition.
- Treat request.x_status as live context for X strategy: account handle/url,
  follower count, tweet count, and whether write credentials exist. X drafts
  still require BJ approval before publication.
- Treat request.bluesky_status as live context for Bluesky strategy:
  handle/url, follower count, recent posts, and posting gaps. Bluesky drafts
  still require BJ approval before publication.

Platform requirements:
- Expected output pieces: {", ".join(spec["output"])}
- Platform note: {spec["notes"]}

Hard rules:
- Draft only. Do not say anything has been posted.
- Patreon posting is manual. Produce review-ready files/copy and explicit
  posting notes, never a claim of publication.
- YouTube posting is manual. Produce review-ready scripts, descriptions,
  thumbnail concepts, chapters, Shorts notes, and upload checklist items, never
  a claim of publication.
- Do not expose private health, therapy, money, family, relationship, exact-place, medication, or raw log details.
- Reddit must be helpful and non-spammy; include a no-promo version.
- Carousels must include slide text, image direction, and alt text.
- Carousels must be full usable drafts: cover slide, every slide's exact on-image text, caption, alt text, and one image prompt per slide.
- If a content piece benefits from art, include concrete image prompts, not just "make an image."
- Every image prompt must use this exact visual family: sparse pen-and-ink,
  loose watercolor washes on aged parchment, visible grain, soft ink bleed,
  lush marginalia, stamps, labels, wax seals, archival overlays, and selective
  teal/gold/red/deep-green color. No glossy corporate marketing art.
- Video scripts must include hook, narration, visual beats, on-screen text, and CTA.
- Every piece needs a privacy label and a Wonder Compass bridge.
- CTAs should feel like invitations from the Academy, never generic marketing.

Use this Markdown structure:

# Penny Blackletter Content Brief — {context["request"]["kind"]} — {context["date"]}

## Editorial Angle

## Platform Draft

## Visual Plan

## Wonder Compass Bridge

## CTA

## Privacy & Posting Notes

## Alternate Versions

## Penny's Recommendation

## Structured Brief
Return a fenced json object with: kind, title, platform, privacy, summary, assets, draft_parts, image_prompts, carousel_slides, cta, posting_notes, next_action.

Current data JSON:
{json.dumps(context, ensure_ascii=False, indent=2, default=str)[:17000]}
"""


def prompt_for_proposal(context: dict[str, Any]) -> str:
    return f"""You are Penny Blackletter. Create a lightweight afternoon content proposal, not a full packet.

Give BJ 3-5 strong options Penny would lead today. Include at least:
- one Wonder Compass / book-forward option
- one free open-source Enchantify feature/lore option
- one Doobaleedoos $1 Patreon option
- one optional platform-specific wildcard if today's material suggests it

For each option include platform, artifact type, hook, why it serves the mission, privacy label, likely asset, and the next command BJ could ask for.

Stay in story. Be useful. Do not produce full scripts unless needed.

Use this Markdown structure:

# Penny's Afternoon Desk — {context["date"]}

## The Desk Bell

## Today's Options

## Best Bet

## Privacy Warnings

## Ask Penny Next

Current data JSON:
{json.dumps(context, ensure_ascii=False, indent=2, default=str)[:14000]}
"""


def call_llm_with_prompt(context: dict[str, Any], prompt: str, *, max_tokens: int = 2200) -> str:
    port, token, model, timeout = gateway_cfg()
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are Penny Blackletter, Enchantify's in-world editor and marketing specialist. "
                    "Write vivid, practical, privacy-safe content artifacts. Reply only with the requested Markdown."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.78,
        "max_tokens": max_tokens,
        "stream": False,
    }
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "x-openclaw-session-key": f"penny-studio-{context['date']}-{int(time.time())}",
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
    return (
        result.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )


def fallback_brief(context: dict[str, Any], reason: str = "") -> str:
    kind = context["request"]["kind"]
    spec = platform_spec(kind)
    title = context.get("storybook_title") or "A Page That Proves the World Is Still Speaking"
    patreon = context.get("request", {}).get("patreon_status") or context.get("patreon_status") or {}
    youtube = context.get("request", {}).get("youtube_status") or context.get("youtube_status") or {}
    x_status = context.get("request", {}).get("x_status") or context.get("x_status") or {}
    bluesky = context.get("request", {}).get("bluesky_status") or context.get("bluesky_status") or {}
    recent_posts = patreon.get("recent_posts") or []
    latest_post = recent_posts[0] if recent_posts else {}
    patreon_note = (
        f"Current Patreon read: {patreon.get('creation_name') or 'Patreon'} has "
        f"{patreon.get('patron_count', 'unknown')} patrons visible; latest visible post is "
        f"\"{latest_post.get('title') or 'none visible'}\". Posting is manual."
    ) if patreon.get("connected") else "Patreon status unavailable. Posting is manual; draft for BJ review only."
    recent_videos = youtube.get("recent_videos") or []
    latest_video = recent_videos[0] if recent_videos else {}
    youtube_note = (
        f"YouTube read: {youtube.get('title') or 'channel'} has "
        f"{youtube.get('subscriber_count', 'unknown')} subscribers visible; latest visible video is "
        f"\"{latest_video.get('title') or 'none visible'}\". Uploading is manual."
    ) if youtube.get("connected") else "YouTube status unavailable. Uploading is manual; draft for BJ review only."
    x_note = (
        f"X read: @{x_status.get('username') or 'account'} has "
        f"{x_status.get('followers', 'unknown')} followers and {x_status.get('tweet_count', 'unknown')} posts visible. "
        "Posting is consent-gated."
    ) if x_status.get("connected") else "X status unavailable. Draft X posts for BJ review only."
    bluesky_note = (
        f"Bluesky read: @{bluesky.get('handle') or 'account'} has "
        f"{bluesky.get('followers', 'unknown')} followers and {bluesky.get('post_count', 'unknown')} posts visible. "
        "Posting is consent-gated."
    ) if bluesky.get("connected") else "Bluesky status unavailable. Draft Bluesky posts for BJ review only."
    images = context["sources"].get("images") or []
    image_note = "Use today's strongest manuscript-style Enchantify image." if images else "Generate a sparse pen-and-ink, watercolor manuscript-page image if no existing image fits."
    image_prompt = (
        "A luminous manuscript-page carousel plate for Enchantify. "
        f"{ENCHANTIFY_IMAGE_STYLE}. No readable text, no logo, no watermark."
    )
    platform_drafts = platform_ready_fallback(kind, title, image_note, image_prompt)
    draft = platform_drafts["draft"]
    visual_plan = platform_drafts["visual_plan"]
    alternate_versions = platform_drafts["alternate_versions"]
    recommendation = platform_drafts["recommendation"]
    structured = {
        "kind": kind,
        "title": title,
        "platform": spec["label"],
        "privacy": "PUBLIC-SAFE",
        "summary": f"Complete {spec['label']} draft generated by Penny's deterministic desk.",
        "assets": platform_drafts["assets"],
        "draft_parts": platform_drafts["draft_parts"],
        "image_prompts": platform_drafts.get("image_prompts", []),
        "carousel_slides": platform_drafts.get("carousel_slides", []),
        "cta": "Step through the one-dollar door on Patreon when the link is ready, or read The Wonder Compass when the book is available.",
        "posting_notes": "Review links and privacy before posting. Keep it in-world.",
        "next_action": platform_drafts["next_action"],
    }
    lines = [
        f"# Penny Blackletter Content Brief — {kind} — {context['date']}",
        "",
        "## Editorial Angle",
        f"{title}: use this as proof that Enchantify turns attention into artifacts.",
        "",
        "## Platform Draft",
        draft,
        "",
        "## Visual Plan",
        visual_plan,
        "",
        "## Wonder Compass Bridge",
        "Notice -> Embark -> Sense -> Write -> Rest. The content should leave the viewer with one tiny action, not just admiration.",
        "",
        "## CTA",
        "Wonder Compass is the field guide. Enchantify is the free open-source living book. The Doobaleedoos $1 Patreon is the one-dollar door that keeps the lantern lit.",
        "",
        "## Privacy & Posting Notes",
        f"PUBLIC-SAFE as written. Add real links manually when ready. Do not include private logs. {patreon_note} {youtube_note} {x_note} {bluesky_note}",
        "",
        "## Alternate Versions",
        alternate_versions,
        "",
        "## Penny's Recommendation",
        recommendation,
        "",
        "## Structured Brief",
        "```json",
        json.dumps(structured, ensure_ascii=False, indent=2),
        "```",
    ]
    if reason and reason != "LLM disabled":
        lines.append(f"\n<!-- fallback: {clean(reason, 300)} -->")
    return "\n".join(lines) + "\n"


def platform_ready_fallback(kind: str, title: str, image_note: str, image_prompt: str) -> dict[str, Any]:
    base_caption = (
        "The Academy field note for today: ordinary life is not empty. It is under-read. "
        "Wonder Compass is the field guide; Enchantify is the living book built around the practice."
    )
    hashtags = "#WonderCompass #Enchantify #Doobaleedoos #CreativeAI #OpenSource #TinyAdventure"
    carousel_slides = [
        ("Cover", "The Book Opened Today", "A parchment title page with a small shining compass seal and lush margin notes."),
        ("Notice", "Find one thing you usually pass without seeing.", "A real-world ordinary object rendered like a magical specimen."),
        ("Embark", "Move one step closer. No heroic quest required.", "A little ink path crossing the page toward a door sketched in the margin."),
        ("Sense", "Let texture, sound, light, or weather answer first.", "Watercolor sensory labels blooming around the object."),
        ("Write", "One sentence is enough proof.", "A handwritten line being added beneath the illustration."),
        ("Rest", "The page counts because you were here.", "A closed field journal with a ribbon and quiet gold ink."),
        ("Door", "Wonder Compass is the field guide. Enchantify is the living book.", "A final card with the Compass directions as tiny illuminated glyphs."),
    ]
    if kind in {"instagram-carousel", "tiktok-carousel"}:
        draft_parts = [
            f"Slide {i}. {label}: {text}\nImage: {image}\nAlt text: Manuscript-style field-journal art showing {text.lower()}"
            for i, (label, text, image) in enumerate(carousel_slides, start=1)
        ]
        caption = (
            f"{base_caption}\n\n"
            "Today’s tiny field assignment: choose one ordinary object, look twice, and write one sentence before the world can vanish back into habit.\n\n"
            "The one-dollar door on Patreon keeps these field notes coming. The free Enchantify project shows how the living book works.\n\n"
            f"{hashtags}"
        )
        draft = "\n\n".join(draft_parts + [f"Caption:\n{caption}"])
        return {
            "draft": draft,
            "draft_parts": draft_parts + [caption],
            "assets": [image_note, image_prompt, "Optional: generate one square image per slide or one master parchment plate cropped into slides."],
            "image_prompts": [
                f"{label}: {image}. Include sparse readable slide title: {text}"
                for label, text, image in carousel_slides
            ],
            "carousel_slides": [
                {"label": label, "text": text, "image_prompt": image, "alt_text": f"Manuscript-style field-journal art showing {text.lower()}"}
                for label, text, image in carousel_slides
            ],
            "visual_plan": "\n".join([
                f"- {image_note}",
                f"- Master image prompt: {image_prompt}",
                "- Create 7 square carousel panels with consistent parchment, seals, lush marginalia, and readable short slide text.",
                "- Keep text sparse on-image; put fuller explanation in the caption.",
            ]),
            "alternate_versions": "- TikTok version: punchier slide text, fewer words, stranger hook.\n- Instagram version: warmer caption, more field-journal intimacy.\n- Patreon version: include a behind-the-scenes note about how the page was made.",
            "recommendation": "Use the carousel when there is a strong image. It gives people a tiny practice before asking them to care about the project.",
            "next_action": "Generate or select 7 carousel images, then review privacy and links before posting.",
        }
    if kind in {"x-post", "x-thread"}:
        posts = [
            "1/ Enchantify is a free open-source living storybook engine built around one quiet spell: attention.",
            "2/ The Wonder Compass underneath it is simple: Notice -> Embark -> Sense -> Write -> Rest.",
            "3/ Instead of asking you to escape real life, the book asks you to notice it hard enough that it becomes a page.",
            "4/ Scenes, photos, walks, tiny choices, The Bleed, and the Storybook all become proof that you were here.",
            "5/ The Doobaleedoos $1 Patreon is the one-dollar door: a tiny way to keep the lantern lit while the free spell stays inspectable.",
        ]
        if kind == "x-post":
            draft = "What if an AI game did not ask you to escape your life, but notice it?\n\nEnchantify is a free open-source living storybook built around The Wonder Compass: Notice -> Embark -> Sense -> Write -> Rest."
            draft_parts = [draft]
        else:
            draft = "\n\n".join(posts)
            draft_parts = posts
        return {
            "draft": draft,
            "draft_parts": draft_parts,
            "assets": [image_note, image_prompt],
            "visual_plan": f"- Pair with one manuscript-style image.\n- Image prompt: {image_prompt}\n- Alt text: Parchment field-journal page showing the Wonder Compass as a living book interface.",
            "alternate_versions": "- Builder-facing: lead with open source and local files.\n- Reader-facing: lead with Wonder Compass.\n- Supporter-facing: lead with the one-dollar door.",
            "recommendation": "Post the single X version first; turn it into a thread when the public repo/readme links are ready.",
            "next_action": "Add actual links, then queue for approval.",
        }
    if kind == "youtube-short":
        draft = "\n".join([
            "Title: What if the game asked you to notice your life?",
            "Hook (0-3s): What if an AI game did not ask you to escape reality?",
            "Beat 1 (3-12s): Enchantify is a living storybook. You open the book, the world has moved, and the page asks one thing of you.",
            "Beat 2 (12-25s): The real magic is The Wonder Compass: Notice, Embark, Sense, Write, Rest.",
            "Beat 3 (25-42s): A photo, a walk, a sentence, a tiny choice — the book keeps the proof.",
            "Beat 4 (42-55s): The free open-source version shows the spellwork. The one-dollar Patreon door keeps the lantern lit.",
            "CTA (55-60s): Open the field guide. Step through one tiny door.",
            "On-screen text: A living book that turns attention into artifacts.",
        ])
        return {
            "draft": draft,
            "draft_parts": draft.split("\n"),
            "assets": [image_note, image_prompt, "B-roll: page turning, compass card, manuscript art, one real object being noticed."],
            "visual_plan": f"- Use 5 fast visual cuts: book/page, Compass, Enchantify art, real object, Patreon/OSS title card.\n- Image prompt: {image_prompt}",
            "alternate_versions": "- More personal: BJ explains why he built it.\n- More magical: Penny narrates from The Bleed desk.\n- More devlog: show files/scripts briefly.",
            "recommendation": "Record this as voiceover first; visuals can be assembled after.",
            "next_action": "Record a 60-second scratch voiceover.",
        }
    if kind == "youtube-long":
        draft = "\n".join([
            "Working Title: I Built a Free Open-Source Living Storybook to Teach Attention",
            "Thumbnail: A parchment phone screen, a glowing compass, text: THE BOOK ASKS ONE THING",
            "Cold Open: Show a daily Storybook page and ask: what if your life could leave behind magical proof?",
            "Act 1: The problem — modern life makes ordinary days disappear.",
            "Act 2: The Wonder Compass — Notice, Embark, Sense, Write, Rest.",
            "Act 3: Enchantify — Pages, Belief, The Bleed, Enchantments, Compass Runs, Storybook.",
            "Act 4: Why open source — the spell should be inspectable, forkable, and local.",
            "Act 5: The one-dollar door — small support for ongoing field notes, artifacts, and Doobaleedoos adventures.",
            "Closing CTA: Try one Compass step today. One sentence is enough proof.",
        ])
        return {
            "draft": draft,
            "draft_parts": draft.split("\n"),
            "assets": [image_note, image_prompt, "Screenshots of Story-Field Journal, Storybook PDF, Compass card, Enchantify art."],
            "visual_plan": "- Mix screen capture, printed artifacts, manuscript art, and one real-world noticing beat.\n- Keep the tone documentary-magical, not product demo.",
            "alternate_versions": "- Devlog version for open-source builders.\n- Wonder Compass version for readers.\n- Patreon version for supporters.",
            "recommendation": "Make this the flagship explainer once the repo/readme and Patreon links are clean.",
            "next_action": "Turn this outline into a full narration script on demand.",
        }
    if kind == "reddit-post":
        draft = "\n\n".join([
            "Subreddit fit: r/opensource, r/Solo_Roleplaying, r/worldbuilding, r/InternetIsBeautiful, or AI/dev communities only if the rules allow project sharing.",
            "No-promo version:\nI have been experimenting with a free/open-source narrative system that turns daily life into a living storybook. The design question I keep coming back to is: can an AI game make people pay better attention to reality instead of replacing it?",
            "Post draft:\nI’m building Enchantify, a free/open-source living storybook engine that treats every interaction as a Page. Some pages are scenes, some are real-world attention rituals, some are photo enchantments, some are newspapers or daily storybook entries. The underlying practice is The Wonder Compass: Notice -> Embark -> Sense -> Write -> Rest.\n\nThe goal is not to trap people in a fantasy app. The goal is to make the real world feel readable again.\n\nI’m curious if anyone else is exploring open-source narrative tools that bridge fiction, local files, and real-world rituals.",
            "Soft CTA: If links are welcome in the thread, add the repo/book/Patreon only after someone asks or the subreddit allows it.",
        ])
        return {
            "draft": draft,
            "draft_parts": draft.split("\n\n"),
            "assets": ["Optional screenshot/image only if subreddit norms allow it.", image_prompt],
            "visual_plan": "- Reddit usually does not need an image; if used, choose one clear Storybook or Story-Field Journal screenshot.",
            "alternate_versions": "- More technical: focus on local files and scripts.\n- More RPG: focus on living world and Belief.\n- More wellness: focus on attention without clinical claims.",
            "recommendation": "Do not lead with Patreon on Reddit. Lead with the design question.",
            "next_action": "Pick a specific subreddit and check rules before posting.",
        }
    if kind == "reddit-comment":
        draft = "Helpful comment draft:\nThis reminds me of a design problem I’ve been working on: how to make AI narrative systems point people back toward real life instead of replacing it. The pattern that’s helped me is giving every interaction a clear container — a Page — with a purpose, an invitation, and an artifact. It keeps the experience from becoming feature soup.\n\nIf it helps, I can share more about the open-source experiment, but the short version is: the system works best when it gives the player one concrete thing to notice or do, then preserves proof that it happened."
        return {
            "draft": draft,
            "draft_parts": draft.split("\n\n"),
            "assets": [],
            "visual_plan": "- No image unless the thread explicitly asks for examples.",
            "alternate_versions": "- Shorter: remove Enchantify mention entirely.\n- More technical: add local-file architecture.\n- More narrative: mention living book metaphor.",
            "recommendation": "Use comments to be genuinely helpful; let curiosity create the invitation.",
            "next_action": "Paste only after matching the exact thread context.",
        }
    if kind == "patreon-post":
        draft = "\n\n".join([
            "Title: A Small Lantern for the Living Book",
            "Post:\nThe one-dollar door is not a paywall. It is a tiny lantern at the edge of the page.\n\nEnchantify stays free and open-source because the spell should be inspectable. The Wonder Compass keeps pointing back to real life because the magic is not meant to trap anyone on a screen.\n\nYour $1 helps keep the field notes, artifacts, storybook pages, and Doobaleedoos experiments moving. No velvet rope. No guilt. Just a small way to say: keep going; the world is still readable.",
            "Member question:\nWhat ordinary object should the Academy inspect next?",
            "CTA:\nStep through the one-dollar door if you want to keep the lantern lit.",
        ])
        return {
            "draft": draft,
            "draft_parts": draft.split("\n\n"),
            "assets": [image_note, image_prompt],
            "visual_plan": f"- Use a warm parchment image with a small lantern, compass seal, and marginalia.\n- Image prompt: {image_prompt}",
            "alternate_versions": "- More behind-the-scenes: add what was built this week.\n- More personal: add BJ/Amanda note.\n- More artifact-forward: attach a printable field assignment.",
            "recommendation": "This is ready as a pinned low-pressure Patreon welcome once the link is set.",
            "next_action": "Add Patreon URL and one current artifact image.",
        }
    draft = f"{base_caption}\n\nCTA: Wonder Compass is the field guide. Enchantify is the living book. The Doobaleedoos $1 Patreon is the one-dollar door."
    return {
        "draft": draft,
        "draft_parts": [draft],
        "assets": [image_note, image_prompt],
        "visual_plan": f"- {image_note}\n- Image prompt: {image_prompt}",
        "alternate_versions": "- Turn into X post.\n- Turn into carousel.\n- Turn into Patreon note.",
        "recommendation": "Choose one platform and let Penny make the exact format.",
        "next_action": "Run make again with a specific --kind.",
    }


def fallback_proposal(context: dict[str, Any], reason: str = "") -> str:
    title = context.get("storybook_title") or "today's page"
    lines = [
        f"# Penny's Afternoon Desk — {context['date']}",
        "",
        "## The Desk Bell",
        f"Penny has three public-safe doors open from `{title}`. None require posting today; all are drafts waiting for BJ's nod.",
        "",
        "## Today's Options",
        "1. **Wonder Compass field assignment** — X/Instagram/TikTok carousel. Hook: The world is not empty; it is under-read. Privacy: PUBLIC-SAFE. Ask: `make --kind instagram-carousel --topic field assignment`.",
        "2. **Open-source Enchantify tour** — X thread or Reddit show-and-tell. Hook: a free living storybook engine where mechanics become pages. Privacy: PUBLIC-SAFE. Ask: `make --kind x-thread --topic open-source Enchantify`.",
        "3. **The one-dollar door** — Patreon post. Hook: one dollar keeps the lantern lit without locking the spell away. Privacy: PUBLIC-SAFE. Ask: `make --kind patreon-post --topic one-dollar door`.",
        "4. **Short-form video** — YouTube Short/TikTok. Hook: What if an AI game asked you to notice your life? Privacy: PUBLIC-SAFE. Ask: `make --kind youtube-short --topic living book`.",
        "",
        "## Best Bet",
        "Start with the Wonder Compass field assignment. It gives value before it asks for attention.",
        "",
        "## Privacy Warnings",
        "Keep health, therapy, money, exact location, and private relationship data out of public copy.",
        "",
        "## Ask Penny Next",
        "`python3 scripts/penny-press.py make bj --kind instagram-carousel --topic \"Wonder Compass field assignment\"`",
    ]
    if reason and reason != "LLM disabled":
        lines.append(f"\n<!-- fallback: {clean(reason, 300)} -->")
    return "\n".join(lines) + "\n"


def extract_structured_brief(markdown: str) -> dict[str, Any]:
    blocks = re.findall(r"```json\s*(.*?)```", markdown, flags=re.DOTALL | re.IGNORECASE)
    for block in reversed(blocks):
        try:
            data = json.loads(block)
            if isinstance(data, dict):
                return data
        except Exception:
            continue
    return {}


def write_brief(markdown: str, structured: dict[str, Any], date_str: str, kind: str, topic: str) -> tuple[Path, Path]:
    stamp = now().strftime("%Y%m%d-%H%M%S")
    slug = slugify(topic or kind, kind)
    brief_path = BRIEF_DIR / f"{stamp}-{kind}-{slug}.md"
    json_path = BRIEF_DIR / f"{stamp}-{kind}-{slug}.json"
    brief_path.write_text(markdown, encoding="utf-8")
    json_path.write_text(json.dumps({"date": date_str, "kind": kind, "topic": topic, "brief": structured}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return brief_path, json_path


def content_image_prompt(markdown: str, structured: dict[str, Any], kind: str, topic: str) -> str:
    title = structured.get("title") or topic or kind
    prompts = structured.get("image_prompts") or structured.get("assets") or []
    if isinstance(prompts, list):
        prompt_text = " ".join(clean(item, 220) for item in prompts[:4])
    else:
        prompt_text = clean(prompts, 500)
    return (
        "A custom main illumination for a Penny Blackletter publication packet, "
        f"subject: {title}; format: {kind}; topic: {topic}. "
        f"Visual notes: {prompt_text}. "
        "Make it feel like an actual storybook-journal review page for social content: "
        "a press editor's red pencil, wax approval seals, carousel thumbnails, caption slips, "
        "Wonder Compass marks, Patreon lantern imagery where relevant. "
        f"{ENCHANTIFY_IMAGE_STYLE}. "
        "No readable text, no logo, no watermark."
    )


def render_press_pdf(markdown: str, path: Path, *, title: str, subtitle: str, structured: dict[str, Any] | None = None, kind: str = "", topic: str = "", dry_run: bool = False) -> dict[str, str]:
    structured = structured or {}
    return journal_artifact.render(
        markdown,
        PRESS_DIR / "journal",
        path.stem,
        title=title,
        subtitle=subtitle,
        footer="Filed by Penny Blackletter, The Bleed Margins Desk",
        accent="#6f2e3d",
        image_prompt=content_image_prompt(markdown, structured, kind, topic) if kind else "",
        image_caption=f"{kind} · {topic or subtitle} · Penny's review illumination" if kind else "",
        dry_run=dry_run,
    )


def generate_images_for_brief(structured: dict[str, Any], kind: str, topic: str, *, dry_run: bool = False) -> list[str]:
    """Generate local Draw Things images for a brief when requested.

    For carousels, generate up to seven square slide images. For other formats,
    generate one hero image. This is opt-in because Draw Things can be slow.
    """
    sys.path.insert(0, str(BASE / "scripts"))
    try:
        import drawthings_scene  # type: ignore
    except Exception as exc:
        return [f"image generation unavailable: {exc}"]

    stamp = now().strftime("%Y%m%d-%H%M%S")
    slug = slugify(topic or structured.get("title") or kind, kind)
    out_dir = IMAGE_DIR / f"{stamp}-{kind}-{slug}"
    style = ENCHANTIFY_IMAGE_STYLE
    draft_parts = [str(part) for part in structured.get("draft_parts", []) if str(part).strip()]
    image_prompts = [str(part) for part in structured.get("image_prompts", []) if str(part).strip()]
    carousel_slides = structured.get("carousel_slides") if isinstance(structured.get("carousel_slides"), list) else []
    prompts: list[tuple[str, str]] = []
    if kind in {"instagram-carousel", "tiktok-carousel"}:
        if image_prompts:
            for idx, prompt in enumerate(image_prompts[:8], start=1):
                prompts.append((f"slide-{idx:02d}.png", f"{clean(prompt, 650)}. {style}. Square social media carousel panel, readable sparse title text only."))
        elif carousel_slides:
            for idx, slide in enumerate(carousel_slides[:8], start=1):
                if isinstance(slide, dict):
                    text = clean(slide.get("text") or slide.get("slide_text") or slide.get("title") or slide, 500)
                    image = clean(slide.get("image_prompt") or slide.get("image") or "", 500)
                else:
                    text = clean(slide, 500)
                    image = ""
                prompts.append((f"slide-{idx:02d}.png", f"{text}. {image}. {style}. Square social media carousel panel, readable sparse title text only."))
        else:
            slide_parts = [p for p in draft_parts if p.lower().startswith("slide ")][:7]
            for idx, part in enumerate(slide_parts, start=1):
                text = clean(part, 500)
                prompts.append((f"slide-{idx:02d}.png", f"{text}. {style}. Square social media carousel panel, readable sparse title text only."))
    else:
        title = structured.get("title") or topic or kind
        prompts.append(("hero.png", f"{title}. {clean(structured.get('summary') or topic, 500)}. {style}."))
    if not prompts:
        prompts.append(("hero.png", f"{topic or kind}. {style}."))

    results: list[str] = []
    for filename, prompt in prompts:
        output = out_dir / filename
        if dry_run:
            results.append(f"dry-run image: {output} :: {prompt[:220]}")
            continue
        ok, detail = drawthings_scene.generate(
            prompt,
            output,
            width=1024,
            height=1024 if kind in {"instagram-carousel", "tiktok-carousel"} else 768,
            steps=6,
            cfg_scale=1.0,
            timeout_seconds=300,
        )
        results.append(str(output) if ok else detail)
    return results


def enqueue_for_consent(
    *,
    player: str,
    date_str: str,
    content_kind: str,
    topic: str,
    brief_path: Path,
    json_path: Path,
    structured: dict[str, Any],
    source: str,
    autonomy: str,
) -> dict[str, Any]:
    data = consent_queue()
    item_id = f"penny-{now().strftime('%Y%m%d-%H%M%S')}-{len(data.get('items', [])) + 1:03d}"
    item = {
        "id": item_id,
        "created_at": now().isoformat(timespec="seconds"),
        "date": date_str,
        "player": player,
        "platform": structured.get("platform") or platform_spec(content_kind)["label"],
        "content_kind": content_kind,
        "topic": topic,
        "title": structured.get("title") or topic or content_kind,
        "status": "needs_review",
        "privacy": structured.get("privacy") or "NEEDS BJ",
        "consent_required": True,
        "autonomy": autonomy,
        "source": source,
        "brief": str(brief_path),
        "structured": str(json_path),
        "cta": structured.get("cta") or "",
        "posting_notes": structured.get("posting_notes") or "",
        "generated_images": structured.get("generated_images") or [],
        "post_url": "",
        "performance": {"views": None, "likes": None, "comments": None, "shares": None, "saves": None, "clicks": None},
        "lesson": "",
    }
    data.setdefault("items", []).append(item)
    save_consent_queue(data)
    append_jsonl(SOCIAL_LEDGER, {**item, "ledger_event": "drafted"})
    return item


def update_queue_item(item_id: str, status: str, note: str = "") -> dict[str, Any] | None:
    data = consent_queue()
    found: dict[str, Any] | None = None
    for item in data.get("items", []):
        if item.get("id") == item_id:
            item["status"] = status
            item[f"{status}_at"] = now().isoformat(timespec="seconds")
            if note:
                item["note"] = note
            found = item
            break
    if found:
        save_consent_queue(data)
        append_jsonl(SOCIAL_LEDGER, {**found, "ledger_event": status})
    return found


def write_proposal(markdown: str, date_str: str) -> Path:
    stamp = now().strftime("%Y%m%d-%H%M%S")
    path = PROPOSAL_DIR / f"{stamp}-afternoon-desk.md"
    path.write_text(markdown, encoding="utf-8")
    return path


def summarize_brief(markdown: str, path: Path) -> str:
    def section(name: str) -> str:
        m = re.search(rf"^## {re.escape(name)}\s*(.*?)(?=^## |\Z)", markdown, re.DOTALL | re.MULTILINE)
        return clean(m.group(1), 700) if m else ""

    return "\n".join([
        f"Penny filed a content brief — {path.name}",
        "",
        section("Editorial Angle") or "A new content brief is ready.",
        "",
        "Recommendation:",
        section("Penny's Recommendation") or section("Best Bet") or "Review before posting.",
    ])


def summarize_proposal(markdown: str, path: Path) -> str:
    def section(name: str) -> str:
        m = re.search(rf"^## {re.escape(name)}\s*(.*?)(?=^## |\Z)", markdown, re.DOTALL | re.MULTILINE)
        return clean(m.group(1), 700) if m else ""

    return "\n".join([
        f"Penny's proposal file — {path.name}",
        "",
        section("The Desk Bell") or "Penny has filed a proposal.",
        "",
        "Best bet:",
        section("Best Bet") or "Review the attached proposal.",
    ])


def run_make(player: str, date_str: str, kind: str, topic: str, source: str, *, no_llm: bool = False, dry_run: bool = False, send: bool = False, silent: bool = False, queue: bool = False, autonomy: str = "manual", generate_images: bool = False) -> int:
    ensure_dirs()
    context = content_context(player, date_str, topic, kind, source)
    llm_error = ""
    if no_llm:
        markdown = fallback_brief(context, "LLM disabled")
    else:
        try:
            markdown = call_llm_with_prompt(context, prompt_for_brief(context), max_tokens=2600)
            if not markdown or "# Penny Blackletter Content Brief" not in markdown:
                raise RuntimeError("model returned an empty or malformed content brief")
        except Exception as exc:
            llm_error = str(exc)
            markdown = fallback_brief(context, llm_error)
    structured = extract_structured_brief(markdown)
    generated_images: list[str] = []
    if generate_images:
        generated_images = generate_images_for_brief(structured, kind, topic, dry_run=dry_run)
        if structured:
            structured["generated_images"] = generated_images
        if generated_images:
            markdown += "\n## Generated Images\n" + "\n".join(f"- {item}" for item in generated_images) + "\n"
    if dry_run:
        print(markdown)
        brief_path = BRIEF_DIR / f"{kind}-{slugify(topic or kind)}.md"
        json_path = BRIEF_DIR / f"{kind}-{slugify(topic or kind)}.json"
    else:
        brief_path, json_path = write_brief(markdown, structured, date_str, kind, topic)
        item = enqueue_for_consent(
            player=player,
            date_str=date_str,
            content_kind=kind,
            topic=topic,
            brief_path=brief_path,
            json_path=json_path,
            structured=structured,
            source=source,
            autonomy=autonomy,
        ) if queue else None
        append_jsonl(LOG_DIR / "penny-press.jsonl", {
            "kind": "content_brief",
            "date": date_str,
            "player": player,
            "content_kind": kind,
            "topic": topic,
            "brief": str(brief_path),
            "structured": str(json_path),
            "queue_id": item.get("id") if item else "",
            "generated_images": generated_images,
            "llm_error": llm_error,
            "sent": False,
        })
    if send:
        artifact = render_press_pdf(
            markdown,
            brief_path,
            title="Penny Blackletter Content Brief",
            subtitle=f"{kind} · {topic or 'public-safe content'}",
            structured=structured,
            kind=kind,
            topic=topic,
            dry_run=dry_run,
        )
        media = Path(artifact["pdf"]) if artifact.get("pdf") else brief_path
        rc = telegram_send(summarize_brief(markdown, brief_path), media, dry_run=dry_run, silent=silent)
        if not dry_run:
            append_jsonl(LOG_DIR / "penny-press.jsonl", {
                "kind": "content_brief_sent",
                "date": date_str,
                "brief": str(brief_path),
                "returncode": rc,
            })
        return rc
    if not dry_run:
        print(f"CONTENT_BRIEF: {brief_path}")
        print(f"STRUCTURED_BRIEF: {json_path}")
        if queue and 'item' in locals() and item:
            print(f"CONSENT_QUEUE_ID: {item['id']}")
        if generated_images:
            print("GENERATED_IMAGES:")
            for image in generated_images:
                print(f"- {image}")
        if llm_error:
            print(f"LLM_FALLBACK: {llm_error}", file=sys.stderr)
    return 0


def run_proposal(player: str, date_str: str, *, no_llm: bool = False, dry_run: bool = False, send: bool = False, silent: bool = False) -> int:
    ensure_dirs()
    context = content_context(player, date_str, "", "content-menu", "today")
    llm_error = ""
    if no_llm:
        markdown = fallback_proposal(context, "LLM disabled")
    else:
        try:
            markdown = call_llm_with_prompt(context, prompt_for_proposal(context), max_tokens=1400)
            if not markdown or "# Penny's Afternoon Desk" not in markdown:
                raise RuntimeError("model returned an empty or malformed proposal")
        except Exception as exc:
            llm_error = str(exc)
            markdown = fallback_proposal(context, llm_error)
    if dry_run:
        print(markdown)
        path = PROPOSAL_DIR / f"{date_str}-afternoon-desk.md"
    else:
        path = write_proposal(markdown, date_str)
        append_jsonl(LOG_DIR / "penny-press.jsonl", {
            "kind": "content_proposal",
            "date": date_str,
            "player": player,
            "proposal": str(path),
            "llm_error": llm_error,
            "sent": False,
        })
    if send:
        artifact = render_press_pdf(
            markdown,
            path,
            title="Penny's Afternoon Desk",
            subtitle="Content proposals awaiting BJ's consent",
            dry_run=dry_run,
        )
        media = Path(artifact["pdf"]) if artifact.get("pdf") else path
        rc = telegram_send(summarize_proposal(markdown, path), media, dry_run=dry_run, silent=silent)
        if not dry_run:
            append_jsonl(LOG_DIR / "penny-press.jsonl", {
                "kind": "content_proposal_sent",
                "date": date_str,
                "proposal": str(path),
                "returncode": rc,
            })
        return rc
    if not dry_run:
        print(f"CONTENT_PROPOSAL: {path}")
        if llm_error:
            print(f"LLM_FALLBACK: {llm_error}", file=sys.stderr)
    return 0


def summarize_consent_queue() -> str:
    data = consent_queue()
    pending = [item for item in data.get("items", []) if item.get("status") == "needs_review"]
    if not pending:
        return "Penny's consent tray is clear."
    lines = ["Penny has drafts awaiting consent:", ""]
    for item in pending[-8:]:
        lines.append(f"- {item.get('id')} — {item.get('platform')} / {item.get('content_kind')}: {item.get('title')} [{item.get('privacy')}]")
    lines.extend(["", "Reply with the id and approve/reject/revise in session, or run the matching command."])
    return "\n".join(lines)


def run_autonomous(player: str, date_str: str, *, no_llm: bool = False, dry_run: bool = False, send: bool = False, silent: bool = False) -> int:
    ensure_dirs()
    plan = [
        ("instagram-carousel", "Wonder Compass field assignment from today's page", "storybook"),
        ("x-thread", "free open-source Enchantify as a living storybook engine", "enchantify"),
        ("patreon-post", "the Doobaleedoos one-dollar door", "patreon"),
    ]
    made: list[str] = []
    for kind, topic, source in plan:
        rc = run_make(
            player,
            date_str,
            kind,
            topic,
            source,
            no_llm=no_llm,
            dry_run=dry_run,
            send=send,
            silent=silent,
            queue=not dry_run,
            autonomy="autonomous",
            generate_images=kind in {"instagram-carousel", "tiktok-carousel", "patreon-post"},
        )
        if rc != 0:
            return rc
    if not dry_run:
        for item in consent_queue().get("items", [])[-len(plan):]:
            made.append(str(item.get("id")))
        append_jsonl(LOG_DIR / "penny-press.jsonl", {
            "kind": "autonomous_desk",
            "date": date_str,
            "player": player,
            "queued_ids": made,
            "sent": False,
        })
    message = summarize_consent_queue()
    if send:
        rc = telegram_send(message, None, dry_run=dry_run, silent=silent)
        if not dry_run:
            append_jsonl(LOG_DIR / "penny-press.jsonl", {
                "kind": "autonomous_desk_sent",
                "date": date_str,
                "queued_ids": made,
                "returncode": rc,
            })
        return rc
    print(message)
    return 0


def run_queue_status() -> int:
    ensure_dirs()
    print(f"STRATEGY: {STRATEGY_FILE}")
    print(f"CONSENT_QUEUE: {CONSENT_QUEUE}")
    print(f"SOCIAL_LEDGER: {SOCIAL_LEDGER}")
    print("")
    print(summarize_consent_queue())
    return 0


def run_decision(item_id: str, status: str, note: str = "") -> int:
    ensure_dirs()
    status_map = {
        "approve": "approved",
        "approved": "approved",
        "reject": "rejected",
        "rejected": "rejected",
        "revise": "revise_requested",
        "revise_requested": "revise_requested",
    }
    normalized = status_map.get(status, status)
    item = update_queue_item(item_id, normalized, note)
    if not item:
        print(f"CONSENT_ITEM_NOT_FOUND: {item_id}", file=sys.stderr)
        return 1
    print(f"CONSENT_ITEM_UPDATED: {item_id} -> {normalized}")
    print(f"BRIEF: {item.get('brief')}")
    return 0


def run_status() -> int:
    ensure_dirs()
    packets = sorted(PACKET_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    latest = packets[0] if packets else None
    print(f"PRESS_DIR: {PRESS_DIR}")
    print(f"LATEST_PACKET: {latest if latest else 'none'}")
    print(f"PENDING_CONSENT: {len([i for i in consent_queue().get('items', []) if i.get('status') == 'needs_review'])}")
    if latest:
        print(clean(read(latest, limit=1200), 1200))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Penny Blackletter's Press & Peculiar Commerce desk")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    scan = sub.add_parser("scan")
    scan.add_argument("player", nargs="?", default="bj")
    scan.add_argument("--date", default=today())
    scan.add_argument("--no-llm", action="store_true")
    scan.add_argument("--dry-run", action="store_true")
    scan.add_argument("--send", action="store_true")
    scan.add_argument("--silent", action="store_true")
    make = sub.add_parser("make")
    make.add_argument("player", nargs="?", default="bj")
    make.add_argument("--date", default=today())
    make.add_argument("--kind", choices=sorted(PLATFORM_SPECS.keys()), default="content-menu")
    make.add_argument("--topic", default="")
    make.add_argument("--source", default="today", choices=["today", "storybook", "bleed", "compass", "enchantify", "wonder-compass", "patreon", "youtube", "x", "bluesky", "custom"])
    make.add_argument("--no-llm", action="store_true")
    make.add_argument("--dry-run", action="store_true")
    make.add_argument("--send", action="store_true")
    make.add_argument("--silent", action="store_true")
    make.add_argument("--queue", action="store_true", help="Add the finished brief to Penny's consent queue.")
    make.add_argument("--generate-images", action="store_true", help="Generate local Draw Things image assets for this brief.")
    proposal = sub.add_parser("proposal")
    proposal.add_argument("player", nargs="?", default="bj")
    proposal.add_argument("--date", default=today())
    proposal.add_argument("--no-llm", action="store_true")
    proposal.add_argument("--dry-run", action="store_true")
    proposal.add_argument("--send", action="store_true")
    proposal.add_argument("--silent", action="store_true")
    autonomous = sub.add_parser("autonomous")
    autonomous.add_argument("player", nargs="?", default="bj")
    autonomous.add_argument("--date", default=today())
    autonomous.add_argument("--no-llm", action="store_true")
    autonomous.add_argument("--dry-run", action="store_true")
    autonomous.add_argument("--send", action="store_true")
    autonomous.add_argument("--silent", action="store_true")
    sub.add_parser("queue")
    approve = sub.add_parser("approve")
    approve.add_argument("item_id")
    approve.add_argument("--note", default="")
    reject = sub.add_parser("reject")
    reject.add_argument("item_id")
    reject.add_argument("--note", default="")
    revise = sub.add_parser("revise")
    revise.add_argument("item_id")
    revise.add_argument("--note", default="")
    sub.add_parser("status")
    args = p.parse_args()
    if args.command == "init":
        ensure_dirs()
        print(f"PRESS_DIR: {PRESS_DIR}")
        return 0
    if args.command == "scan":
        return run_scan(args.player, args.date, no_llm=args.no_llm, dry_run=args.dry_run, send=args.send, silent=args.silent)
    if args.command == "make":
        return run_make(args.player, args.date, args.kind, args.topic, args.source, no_llm=args.no_llm, dry_run=args.dry_run, send=args.send, silent=args.silent, queue=args.queue, autonomy="manual", generate_images=args.generate_images)
    if args.command == "proposal":
        return run_proposal(args.player, args.date, no_llm=args.no_llm, dry_run=args.dry_run, send=args.send, silent=args.silent)
    if args.command == "autonomous":
        return run_autonomous(args.player, args.date, no_llm=args.no_llm, dry_run=args.dry_run, send=args.send, silent=args.silent)
    if args.command == "queue":
        return run_queue_status()
    if args.command == "approve":
        return run_decision(args.item_id, "approved", args.note)
    if args.command == "reject":
        return run_decision(args.item_id, "rejected", args.note)
    if args.command == "revise":
        return run_decision(args.item_id, "revise_requested", args.note)
    if args.command == "status":
        return run_status()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

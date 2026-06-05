#!/usr/bin/env python3
"""Professor Bastion Goldweaver's Applied Abundance desk.

Goldweaver turns Enchantify, Wonder Compass, Penny's drafts, and recent story
artifacts into ethical product and revenue experiments. He drafts; he does not
publish, spend, schedule, or promise income.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "scripts"))
import journal_artifact  # type: ignore

MEMORY = BASE / "memory"
PUBLISHING = MEMORY / "publishing"
DESK = PUBLISHING / "applied-abundance"
BRIEFS = DESK / "briefs"
OFFERS = DESK / "offers"
EXPERIMENTS = DESK / "experiments"
LOG_DIR = BASE / "logs" / "publishing"
LOG_PATH = LOG_DIR / "goldwater.jsonl"
CHART = BASE / "players" / "bj-goldwater-chart.md"
PENNY_STRATEGY = PUBLISHING / "editorial-strategy.md"
PENNY_PROPOSALS = PUBLISHING / "proposals"
PENNY_BRIEFS = PUBLISHING / "briefs"
PRODUCT_SEEDS = PUBLISHING / "product-seeds"
PRESS_ABUNDANCE_DAILY = PUBLISHING / "press-abundance" / "daily"
MARKET_RESEARCH = PUBLISHING / "market-research" / "latest.md"
STORYBOOK_DAILY = MEMORY / "storybook" / "daily"
SUPPORT_GUILD = MEMORY / "support-faculty" / "guild"
BLEED_ISSUES = BASE / "bleed" / "issues"
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


def latest_files(path: Path, pattern: str = "*.md", limit: int = 5) -> list[dict[str, str]]:
    if not path.exists():
        return []
    rows = []
    for file in sorted(path.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
        text = read(file, 1600)
        title = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        rows.append({
            "name": file.name,
            "path": str(file),
            "title": clean(title.group(1) if title else file.stem, 160),
            "mtime": datetime.fromtimestamp(file.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
            "excerpt": clean(text, 900),
        })
    return rows


def ensure_dirs() -> None:
    for path in (DESK, BRIEFS, OFFERS, EXPERIMENTS, PRODUCT_SEEDS, LOG_DIR):
        path.mkdir(parents=True, exist_ok=True)
    readme = DESK / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Professor Bastion Goldweaver's Applied Abundance Desk\n\n"
            "This desk turns public-safe Enchantify/Wonder Compass material into ethical offers, product experiments, launch plans, pricing notes, and tiny shippable next actions.\n\n"
            "- `briefs/` - daily or on-demand Applied Abundance briefs.\n"
            "- `offers/` - product and offer briefs ready for review.\n"
            "- `experiments/` - small revenue experiments and outcomes.\n",
            encoding="utf-8",
        )


def wonder_compass_excerpt() -> str:
    parts: list[str] = []
    for name in ("read-this-first.md", "introduction.md", "BOOK_TOC.md"):
        path = WONDER_COMPASS / name
        text = read(path, 700)
        if text:
            parts.append(f"## {path.stem}\n{text}")
    for path in sorted(WONDER_COMPASS.glob("chapter*.md")):
        text = read(path, 950)
        if not text:
            continue
        title = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        parts.append(f"## {title.group(1) if title else path.stem}\n{text}")
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


def postmaster_context(*, ensure_fresh: bool = False, max_age_hours: float = 8.0) -> dict[str, Any]:
    try:
        spec = importlib.util.spec_from_file_location("postmaster", BASE / "scripts" / "postmaster.py")
        if not spec or not spec.loader:
            raise RuntimeError("postmaster module unavailable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.desk_context(ensure_fresh=ensure_fresh, max_age_hours=max_age_hours)
    except Exception as exc:
        return {"available": False, "diagnosis": clean(str(exc), 300)}


def collect_context(player: str = "bj") -> dict[str, Any]:
    ensure_dirs()
    return {
        "date": today(),
        "player": player,
        "chart": read(CHART, 5000),
        "penny_strategy": read(PENNY_STRATEGY, 3500),
        "market_research": read(MARKET_RESEARCH, 5000),
        "patreon_status": patreon_status_summary(),
        "youtube_status": youtube_status_summary(),
        "x_status": x_status_summary(),
        "bluesky_status": bluesky_status_summary(),
        "latest_press_abundance_council": latest_files(PRESS_ABUNDANCE_DAILY, "*.md", 3),
        "latest_storybook": latest_files(STORYBOOK_DAILY, "*.md", 3),
        "latest_penny_proposals": latest_files(PENNY_PROPOSALS, "*.md", 5),
        "latest_penny_briefs": latest_files(PENNY_BRIEFS, "*.md", 5),
        "product_seeds": latest_files(PRODUCT_SEEDS, "*.md", 8),
        "latest_goldwater_briefs": latest_files(BRIEFS, "*.md", 5),
        "latest_offers": latest_files(OFFERS, "*.md", 5),
        "latest_support_guild": latest_files(SUPPORT_GUILD, "*.md", 3),
        "latest_bleed": latest_files(BLEED_ISSUES, "*.md", 2),
        "capabilities_excerpt": read(CAPABILITIES, 2500),
        "wonder_compass_excerpt": wonder_compass_excerpt(),
        "postmaster": postmaster_context(ensure_fresh=False),
    }


def best_source_title(context: dict[str, Any]) -> str:
    for key in ("latest_press_abundance_council", "latest_penny_briefs", "latest_penny_proposals", "latest_storybook"):
        rows = context.get(key) or []
        if rows:
            return rows[0].get("title") or rows[0].get("name") or "today's proof"
    return "today's proof"


def deterministic_brief(context: dict[str, Any], focus: str = "") -> str:
    source = best_source_title(context)
    focus_text = focus or "turn the newest public-safe proof into one small sellable artifact"
    recent_penny = context.get("latest_penny_briefs") or context.get("latest_penny_proposals") or []
    latest_council = context.get("latest_press_abundance_council") or []
    council_hint = latest_council[0]["title"] if latest_council else "no Press & Applied Abundance council packet visible yet"
    seed_rows = context.get("product_seeds") or []
    seed_hint = seed_rows[0]["title"] if seed_rows else "Wonder Compass Field Kit"
    market_hint = clean(context.get("market_research"), 500) or "no Listening Desk market brief visible yet"
    compass_hint = clean(context.get("wonder_compass_excerpt"), 700) or "Wonder Compass chapter packet not found."
    patreon = context.get("patreon_status") or {}
    youtube = context.get("youtube_status") or {}
    x_status = context.get("x_status") or {}
    bluesky = context.get("bluesky_status") or {}
    recent_posts = patreon.get("recent_posts") or []
    latest_post = recent_posts[0] if recent_posts else {}
    recent_videos = youtube.get("recent_videos") or []
    latest_video = recent_videos[0] if recent_videos else {}
    if patreon.get("connected"):
        patreon_hint = (
            f"{patreon.get('creation_name') or 'Patreon'}; "
            f"{patreon.get('patron_count', 'unknown')} patrons visible; "
            f"latest visible post: {latest_post.get('title') or 'none visible'}; "
            f"url: {patreon.get('url') or 'not provided'}"
        )
    else:
        patreon_hint = "Patreon status unavailable; keep all member work manual and review-ready."
    if youtube.get("connected"):
        youtube_hint = (
            f"{youtube.get('title') or 'YouTube'}; "
            f"{youtube.get('subscriber_count', 'unknown')} subscribers visible; "
            f"latest visible video: {latest_video.get('title') or 'none visible'}; "
            f"url: {youtube.get('url') or 'not provided'}"
        )
    else:
        youtube_hint = "YouTube status unavailable; keep all video work manual and review-ready."
    if x_status.get("connected"):
        x_hint = (
            f"@{x_status.get('username') or 'account'}; "
            f"{x_status.get('followers', 'unknown')} followers visible; "
            f"{x_status.get('tweet_count', 'unknown')} posts visible; "
            f"url: {x_status.get('url') or 'not provided'}; "
            "posting is consent-gated"
        )
    else:
        x_hint = "X status unavailable; keep all X drafts manual and review-ready."
    if bluesky.get("connected"):
        bluesky_hint = (
            f"@{bluesky.get('handle') or 'account'}; "
            f"{bluesky.get('followers', 'unknown')} followers visible; "
            f"{bluesky.get('post_count', 'unknown')} posts visible; "
            f"url: {bluesky.get('url') or 'not provided'}; "
            "posting is consent-gated"
        )
    else:
        bluesky_hint = "Bluesky status unavailable; keep all Bluesky drafts manual and review-ready."
    postmaster = context.get("postmaster") or {}
    if postmaster.get("available"):
        postmaster_hint = (
            f"{postmaster.get('message_count', 0)} actionable message(s); "
            f"{len(postmaster.get('goldweaver_reply_suggestions') or [])} review-only reply draft(s); "
            f"next: {clean(postmaster.get('smallest_next_action'), 220)}"
        )
    else:
        postmaster_hint = clean(postmaster.get("diagnosis"), 220) or "No correspondence brief visible yet."
    return f"""# Professor Bastion Goldweaver Applied Abundance Brief - {context['date']}

Goldweaver arrives in a waistcoat the color of unreasonable confidence, places Penny's latest clippings beside the product ledger, and taps the table once.

"Splendid. Now let us make the magic pay rent without selling its soul."

## Commercial Weather
- Source material: {source}
- Working focus: {focus_text}
- Latest Penny/Goldweaver council: {council_hint}
- Strongest existing seed: {seed_hint}
- Listening Desk market read: {market_hint}
- Wonder Compass source read: {compass_hint}
- Patreon read: {patreon_hint}
- YouTube read: {youtube_hint}
- X read: {x_hint}
- Bluesky read: {bluesky_hint}
- Postmaster read: {postmaster_hint}
- Current posture: draft only; no posting, spending, scheduling, or public promise without BJ's approval.

## Correspondence And Reply Drafts
When Postmaster Finch surfaced review-only reply suggestions, treat them as starting points for BJ to edit. The Postmaster never sends mail on his own. Prioritize human business leads over platform digests.

## Best Offer Candidate
**The Wonder Compass Field Kit: A Small Door for a Flat Day**

Promise: turn one ordinary low-energy day into a tiny, real-world adventure using Notice, Embark, Sense, Write, and Rest.

Why now: Enchantify is already producing scenes, images, Book of You pages, Penny drafts, Compass language, and proof-of-life artifacts. The smallest sellable thing is not the app. It is a beautiful, finished packet that helps someone try the practice today.

## Free Version
- One public in-character field assignment from Penny.
- One open-source Enchantify feature highlight.
- One short explanation of Wonder Compass as "the field guide behind the Academy."
- One specific idea from the Wonder Compass chapter packet, not just the five-step summary.

## Paid Version
- Printable 2-4 page field kit.
- One illustrated card.
- One guided audio script or rough recording.
- One Enchantify story fragment.
- One "try this today" Compass ritual.
- Patreon version includes behind-the-scenes notes from BJ and Amanda.
- Patreon posting remains manual: prepare copy, artifact, caption, and review notes for BJ to post by hand.
- YouTube version includes a Short script, long-form episode angle, title set,
  description, thumbnail concept, and upload checklist. Uploading remains
  manual.
- X version includes one post and one short thread tailored to @{x_status.get('username') or 'the Academy account'}.
  Posting remains consent-gated even though account credentials are connected.
- Bluesky version includes one conversational post and one short thread tailored
  to @{bluesky.get('handle') or 'the Academy account'}. Posting remains
  consent-gated even when account credentials are connected.

## Suggested Price
- $1 Patreon access as the warmest door.
- $5-$7 standalone download once polished.
- Bundle later into a monthly packet.

## Penny Handoff
Penny should draft:
- X thread: "What if an AI game asked you to notice your life?"
- Instagram carousel: "A Small Door for a Flat Day"
- Patreon post: "The first Field Kit from the Academy margins"

## Privacy And Ethics
- Do not use health, therapy, ledger, exact location, family, or relationship details.
- Translate personal struggle into general language: flat days, low energy, wanting the world to feel real again.
- Keep the free version genuinely useful.

## One Tiny Action
Choose one Field Kit title and let Goldweaver create a one-page product brief. Then let Penny make one public-safe post that points toward it.

## Recent Inputs Goldweaver Considered
{chr(10).join(f"- {row.get('title', row.get('name', 'untitled'))}" for row in recent_penny[:5]) or "- Penny's desk is quiet; use Storybook and Wonder Compass instead."}
"""


def write_brief(player: str = "bj", focus: str = "") -> Path:
    context = collect_context(player)
    markdown = deterministic_brief(context, focus)
    path = BRIEFS / f"{now().strftime('%Y%m%d-%H%M%S')}-applied-abundance.md"
    path.write_text(markdown, encoding="utf-8")
    append_jsonl(LOG_PATH, {
        "kind": "brief",
        "player": player,
        "path": str(path),
        "focus": focus,
        "summary": "Applied Abundance brief generated.",
    })
    return path


def render_brief_pdf(markdown: str, path: Path, *, dry_run: bool = False) -> dict[str, str]:
    image_prompt = (
        "Professor Bastion Goldweaver's Applied Abundance desk: an offer ledger, product cards, a Wonder Compass field kit, "
        "Patreon lantern, coins as weather not worth, theatrical waistcoat details, and ethical-commerce marginal notes. "
        f"{ENCHANTIFY_IMAGE_STYLE}. No readable text, no logo, no watermark."
    )
    return journal_artifact.render(
        markdown,
        DESK / "journal",
        path.stem,
        title="Professor Goldweaver's Applied Abundance Brief",
        subtitle="Offer ladder, product shape, and one shippable next action",
        footer="Filed by Professor Bastion Goldweaver, Chair of Applied Abundance",
        accent="#8a4f24",
        image_prompt=image_prompt,
        dry_run=dry_run,
    )


def summarize(markdown: str, path: Path) -> str:
    def section(name: str) -> str:
        m = re.search(rf"^## {re.escape(name)}\s*(.*?)(?=^## |\Z)", markdown, re.DOTALL | re.MULTILINE)
        return clean(m.group(1), 600) if m else ""

    return "\n".join([
        f"Professor Bastion Goldweaver - Applied Abundance Brief - {today()}",
        "",
        section("Commercial Weather") or "Goldweaver has filed a commerce brief.",
        "",
        "Best offer:",
        section("Best Offer Candidate") or "Review the attached brief.",
        "",
        "Tiny action:",
        section("One Tiny Action") or "Choose one small offer to shape.",
        "",
        f"Full brief attached: {path.name}",
    ])


def telegram_send(message: str, media: Path | None = None, *, dry_run: bool = False) -> int:
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


def status(player: str = "bj") -> str:
    context = collect_context(player)
    latest = context.get("latest_goldwater_briefs") or []
    offers = context.get("latest_offers") or []
    patreon = context.get("patreon_status") or {}
    youtube = context.get("youtube_status") or {}
    lines = [
        "Professor Bastion Goldweaver's Applied Abundance desk is open.",
        f"Briefs: {len(latest)} recent visible",
        f"Offers: {len(offers)} recent visible",
        f"Latest source: {best_source_title(context)}",
    ]
    if patreon.get("connected"):
        lines.append(f"Patreon: {patreon.get('creation_name') or 'connected'} ({patreon.get('patron_count', 'unknown')} patrons visible)")
    else:
        lines.append("Patreon: status unavailable; manual drafts only")
    if youtube.get("connected"):
        lines.append(f"YouTube: {youtube.get('title') or 'connected'} ({youtube.get('subscriber_count', 'unknown')} subscribers visible)")
    else:
        lines.append("YouTube: status unavailable; manual video drafts only")
    if latest:
        lines.append(f"Latest brief: {latest[0]['title']} ({latest[0]['mtime']})")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Professor Bastion Goldweaver's Applied Abundance desk")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init")
    brief = sub.add_parser("brief")
    brief.add_argument("player", nargs="?", default="bj")
    brief.add_argument("--focus", default="")
    brief.add_argument("--send", action="store_true")
    brief.add_argument("--dry-run", action="store_true")

    stat = sub.add_parser("status")
    stat.add_argument("player", nargs="?", default="bj")

    args = parser.parse_args()
    if args.command == "init":
        ensure_dirs()
        print(f"Goldweaver desk ready: {DESK}")
        return 0
    if args.command == "status":
        print(status(args.player))
        return 0
    if args.command == "brief":
        path = write_brief(args.player, args.focus)
        print(f"Goldweaver brief: {path}")
        if args.send:
            markdown = read(path)
            artifact = render_brief_pdf(markdown, path, dry_run=args.dry_run)
            media = Path(artifact["pdf"]) if artifact.get("pdf") else path
            return telegram_send(summarize(markdown, path), media, dry_run=args.dry_run)
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

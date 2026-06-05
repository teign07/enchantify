#!/usr/bin/env python3
"""Bluesky Listening Desk for Penny and Goldweaver.

Reads public Bluesky posts/threads, finds possible conversation leads, drafts
public-safe replies, and saves review packets. It never posts, likes, follows,
or replies directly.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "memory" / "publishing" / "bluesky-listening"
LOG = BASE / "logs" / "publishing" / "bluesky-listening.jsonl"
TARGET = "8729557865"
CHANNEL = "telegram"
ACCOUNT = "enchantify"
# public.api.bsky.app often 403s searchPosts; api.bsky.app is the working unauthenticated host.
PUBLIC_API = "https://api.bsky.app/xrpc"

DEFAULT_QUERIES = [
    "creative journaling",
    "personal knowledge management",
    "indie author marketing",
    "open source AI",
    "AI agents",
    "mental health journaling",
    "small adventures",
    "wonder practice",
    "local exploration",
    "Patreon creators",
]

PROMO_WORDS = {
    "buy",
    "sale",
    "discount",
    "crypto",
    "nft",
    "giveaway",
    "follow back",
    "dm me",
}

MISSION_WORDS = {
    "journal",
    "journaling",
    "wonder",
    "story",
    "stories",
    "creative",
    "open source",
    "opensource",
    "ai",
    "agent",
    "agents",
    "patreon",
    "creator",
    "adventure",
    "attention",
    "routine",
    "depression",
    "small",
    "meaning",
}


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def clean(value: Any, limit: int = 1000) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit].rstrip() + ("..." if len(text) > limit else "")


def slug(value: str, limit: int = 64) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return (text or "bluesky")[:limit].strip("-") or "bluesky"


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    row.setdefault("timestamp", now())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def load_adapter():
    adapter_path = BASE / "scripts" / "bluesky-adapter.py"
    spec = importlib.util.spec_from_file_location("bluesky_adapter", adapter_path)
    if not spec or not spec.loader:
        raise RuntimeError("Could not load scripts/bluesky-adapter.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def public_request_json(nsid: str, params: dict[str, Any]) -> dict[str, Any]:
    url = f"{PUBLIC_API}/{nsid}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "enchantify/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def bsky_url(uri: str, handle: str = "") -> str:
    if not uri.startswith("at://"):
        return uri
    parts = uri.split("/")
    if len(parts) < 5:
        return uri
    actor = handle or parts[2]
    post_id = parts[-1]
    return f"https://bsky.app/profile/{actor}/post/{post_id}"


def search_posts(query: str, limit: int = 12, sort: str = "latest") -> list[dict[str, Any]]:
    params = {"q": query, "limit": max(1, min(limit, 100)), "sort": sort}
    try:
        data = public_request_json("app.bsky.feed.searchPosts", params)
    except urllib.error.HTTPError:
        adapter = load_adapter()
        data = adapter.request_json("app.bsky.feed.searchPosts", params=params, token=adapter.access_token())
    rows = []
    for post in data.get("posts") or []:
        record = post.get("record") or {}
        author = post.get("author") or {}
        text = clean(record.get("text"), 700)
        handle = author.get("handle") or ""
        row = {
            "query": query,
            "uri": post.get("uri") or "",
            "cid": post.get("cid") or "",
            "text": text,
            "author": handle,
            "display_name": clean(author.get("displayName"), 120),
            "created_at": record.get("createdAt") or "",
            "likes": post.get("likeCount") or 0,
            "reposts": post.get("repostCount") or 0,
            "replies": post.get("replyCount") or 0,
            "quotes": post.get("quoteCount") or 0,
            "url": bsky_url(post.get("uri") or "", handle),
        }
        row["lead_score"] = score_lead(row)
        row["reply_draft"] = draft_reply(row)
        row["comment_angle"] = comment_angle(row)
        rows.append(row)
    rows.sort(key=lambda item: int(item.get("lead_score") or 0), reverse=True)
    return rows


def get_thread(uri: str, depth: int = 6) -> dict[str, Any]:
    params = {"uri": uri, "depth": max(1, min(depth, 30)), "parentHeight": 3}
    try:
        return public_request_json("app.bsky.feed.getPostThread", params)
    except urllib.error.HTTPError:
        adapter = load_adapter()
        return adapter.request_json("app.bsky.feed.getPostThread", params=params, token=adapter.access_token())


def flatten_thread(node: dict[str, Any], rows: list[dict[str, Any]] | None = None, level: int = 0) -> list[dict[str, Any]]:
    rows = rows if rows is not None else []
    post = node.get("post") or {}
    record = post.get("record") or {}
    author = post.get("author") or {}
    if post:
        handle = author.get("handle") or ""
        rows.append({
            "level": level,
            "uri": post.get("uri") or "",
            "cid": post.get("cid") or "",
            "author": handle,
            "display_name": clean(author.get("displayName"), 120),
            "text": clean(record.get("text"), 700),
            "created_at": record.get("createdAt") or "",
            "likes": post.get("likeCount") or 0,
            "reposts": post.get("repostCount") or 0,
            "replies": post.get("replyCount") or 0,
            "url": bsky_url(post.get("uri") or "", handle),
        })
    for reply in node.get("replies") or []:
        flatten_thread(reply, rows, level + 1)
    return rows


def score_lead(row: dict[str, Any]) -> int:
    text = clean(row.get("text"), 1000).lower()
    score = 0
    score += min(int(row.get("likes") or 0), 50) * 2
    score += min(int(row.get("reposts") or 0), 30) * 4
    score += min(int(row.get("replies") or 0), 40) * 3
    score += min(int(row.get("quotes") or 0), 20) * 3
    for word in MISSION_WORDS:
        if word in text:
            score += 8
    for word in PROMO_WORDS:
        if word in text:
            score -= 25
    if "?" in text:
        score += 10
    if 60 <= len(text) <= 500:
        score += 8
    return max(score, 0)


def comment_angle(row: dict[str, Any]) -> str:
    text = clean(row.get("text"), 700).lower()
    if "journal" in text or "journaling" in text:
        return "Add a Wonder Compass angle: one sensory sentence makes the day easier to remember."
    if "open source" in text or "opensource" in text or "agent" in text:
        return "Offer Enchantify as an inspectable story-shaped agent experiment, without hard selling."
    if "patreon" in text or "creator" in text:
        return "Add a low-pressure creator-sustainability note: small doors beat aggressive funnels."
    if "depression" in text or "routine" in text or "stuck" in text:
        return "Respond with care: tiny attention rituals, no productivity shame."
    if "adventure" in text or "local" in text:
        return "Bridge to tiny adventures: ordinary places can become field assignments."
    if "?" in text:
        return "Answer the question generously, then invite one tiny action."
    return "Notice one strong idea in the post, add a useful adjacent thought, and leave the door open."


def draft_reply(row: dict[str, Any]) -> str:
    text = clean(row.get("text"), 700).lower()
    if "journal" in text or "journaling" in text:
        return clean(
            "This is why I keep coming back to one-sentence souvenirs: not a whole journal entry, just one sensory line that helps the day survive the day. Tiny, but weirdly powerful.",
            300,
        )
    if "open source" in text or "opensource" in text or "agent" in text:
        return clean(
            "One thing I love about open-source AI tools is that the magic becomes inspectable. You can ask: what does it remember, what can it touch, and what does it refuse to do?",
            300,
        )
    if "patreon" in text or "creator" in text:
        return clean(
            "I keep thinking small memberships work best when they feel like a warm door, not a velvet rope: one clear reason to support, one honest glimpse behind the curtain.",
            300,
        )
    if "depression" in text or "routine" in text or "stuck" in text:
        return clean(
            "This is the zone where tiny counts. Not a grand transformation, just one real detail noticed on purpose. Sometimes that is the first stitch back into the day.",
            300,
        )
    if "adventure" in text or "local" in text:
        return clean(
            "I love this. The smallest adventures are often just ordinary places approached with a better question: what have I stopped noticing here?",
            300,
        )
    return clean(
        "This feels adjacent to something we keep circling at Enchantify: attention becomes easier when it has a little story-shape around it. Not bigger, just more alive.",
        300,
    )


def scan(queries: list[str], limit: int = 10, top: int = 12, sort: str = "latest") -> dict[str, Any]:
    all_rows: list[dict[str, Any]] = []
    errors: list[str] = []
    seen: set[str] = set()
    for query in queries:
        try:
            rows = search_posts(query, limit=limit, sort=sort)
        except Exception as exc:
            errors.append(f"{query}: {clean(exc, 300)}")
            continue
        for row in rows:
            uri = row.get("uri")
            if uri and uri not in seen:
                seen.add(uri)
                all_rows.append(row)
    all_rows.sort(key=lambda item: int(item.get("lead_score") or 0), reverse=True)
    chosen = all_rows[:top]
    packet = {
        "generated_at": now(),
        "queries": queries,
        "sort": sort,
        "lead_count": len(chosen),
        "searched_count": len(all_rows),
        "errors": errors,
        "leads": chosen,
    }
    return packet


def render_markdown(packet: dict[str, Any]) -> str:
    lines = [
        f"# Bluesky Listening Desk — {packet.get('generated_at')}",
        "",
        "Penny Blackletter has been listening at the public windows. These are leads, not marching orders. Nothing has been liked, followed, replied to, or posted.",
        "",
        "## Queries",
        ", ".join(packet.get("queries") or []),
        "",
        "## Best Leads",
    ]
    for idx, lead in enumerate(packet.get("leads") or [], 1):
        lines.extend([
            "",
            f"### {idx}. @{lead.get('author')} — score {lead.get('lead_score')}",
            f"- URL: {lead.get('url')}",
            f"- Engagement: {lead.get('likes')} likes · {lead.get('reposts')} reposts · {lead.get('replies')} replies · {lead.get('quotes')} quotes",
            f"- Query: {lead.get('query')}",
            "",
            "> " + clean(lead.get("text"), 700),
            "",
            f"**Why it might matter:** {lead.get('comment_angle')}",
            "",
            "**Draft reply for BJ review:**",
            "",
            "> " + clean(lead.get("reply_draft"), 320),
        ])
    if packet.get("errors"):
        lines.extend(["", "## Fetch Notes"])
        lines.extend(f"- {err}" for err in packet.get("errors") or [])
    lines.extend([
        "",
        "## Consent Rules",
        "- Penny may draft replies and posts.",
        "- BJ approves before public action.",
        "- Liking, following, replying, reposting, or posting requires an explicit command later.",
    ])
    return "\n".join(lines).rstrip() + "\n"


def save_packet(packet: dict[str, Any], label: str = "scan") -> tuple[Path, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base = OUT_DIR / f"{today()}-{slug(label)}"
    json_path = base.with_suffix(".json")
    md_path = base.with_suffix(".md")
    json_path.write_text(json.dumps(packet, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    md_path.write_text(render_markdown(packet), encoding="utf-8")
    append_jsonl(LOG, {"kind": "scan", "markdown": str(md_path), "json": str(json_path), "lead_count": packet.get("lead_count")})
    return md_path, json_path


def telegram_send(message: str, media: Path | None = None, *, dry_run: bool = False) -> int:
    if dry_run:
        print(message)
        if media:
            print(f"[dry-run media] {media}")
        return 0
    args = [
        "openclaw",
        "message",
        "send",
        "--target",
        TARGET,
        "--channel",
        CHANNEL,
        "--account",
        ACCOUNT,
        "--message",
        message,
    ]
    if media:
        args += ["--media", str(media), "--force-document"]
    proc = subprocess.run(args, cwd=BASE, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        append_jsonl(LOG, {"kind": "telegram_error", "stderr": clean(proc.stderr or proc.stdout, 1200), "media": str(media) if media else ""})
    return proc.returncode


def print_status() -> int:
    adapter = load_adapter()
    data = adapter.status()
    payload = {
        "connected": bool(data.get("connected")),
        "handle": data.get("handle"),
        "followers": data.get("followers"),
        "post_count": data.get("post_count"),
        "write_enabled": bool(data.get("write_enabled")),
        "listening_desk": str(OUT_DIR),
        "diagnosis": "Can read profile, search public posts, inspect threads, draft replies, and create review packets. Public actions remain consent-gated.",
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    return 0 if payload["connected"] else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Penny's Bluesky Listening Desk")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    search = sub.add_parser("search")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=12)
    search.add_argument("--sort", default="latest", choices=["latest", "top"])
    thread = sub.add_parser("thread")
    thread.add_argument("uri")
    thread.add_argument("--depth", type=int, default=6)
    scan_cmd = sub.add_parser("scan")
    scan_cmd.add_argument("--query", action="append", default=[])
    scan_cmd.add_argument("--limit", type=int, default=10)
    scan_cmd.add_argument("--top", type=int, default=12)
    scan_cmd.add_argument("--sort", default="latest", choices=["latest", "top"])
    scan_cmd.add_argument("--send", action="store_true")
    scan_cmd.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.command == "status":
        return print_status()
    if args.command == "search":
        print(json.dumps(search_posts(args.query, args.limit, args.sort), indent=2, ensure_ascii=False, default=str))
        return 0
    if args.command == "thread":
        rows = flatten_thread(get_thread(args.uri, args.depth).get("thread") or {})
        print(json.dumps(rows, indent=2, ensure_ascii=False, default=str))
        return 0
    if args.command == "scan":
        queries = args.query or DEFAULT_QUERIES
        packet = scan(queries, limit=args.limit, top=args.top, sort=args.sort)
        md_path, json_path = save_packet(packet, label="scan")
        print(f"BLUESKY_LISTENING_PACKET: {md_path}")
        print(f"BLUESKY_LISTENING_JSON: {json_path}")
        print(f"LEADS: {packet.get('lead_count')} of {packet.get('searched_count')} searched")
        if args.send:
            msg = (
                "Penny has sealed a Bluesky Listening Desk packet.\n\n"
                f"Leads: {packet.get('lead_count')}\n"
                "Nothing was liked, followed, replied to, or posted."
            )
            return telegram_send(msg, md_path, dry_run=args.dry_run)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

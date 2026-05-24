#!/usr/bin/env python3
"""Enchantify-local Bluesky adapter.

Official AT Protocol / Bluesky server API only. Credentials live in:

  config/bluesky.env

Current role: read account/profile status, inspect recent posts, prepare
consent-gated post payloads, and provide a future posting path.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent.parent
CONFIG = BASE / "config" / "bluesky.env"
EXAMPLE = BASE / "config" / "bluesky.env.example"
LOG = BASE / "logs" / "publishing" / "bluesky-adapter.jsonl"
DEFAULT_SERVICE = "https://bsky.social"


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def clean(value: Any, limit: int = 800) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit].rstrip() + ("..." if len(text) > limit else "")


def parse_env(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def write_env(path: Path, updates: dict[str, str]) -> None:
    existing = parse_env(path)
    keys = list(existing.keys())
    for key in updates:
        if key not in keys:
            keys.append(key)
    existing.update(updates)
    lines = [
        "# Enchantify-local Bluesky / AT Protocol integration.",
        "# bluesky.env is gitignored.",
        "",
    ] + [f"{key}={existing.get(key, '')}" for key in keys if key]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    path.chmod(0o600)


def config() -> dict[str, str]:
    return parse_env(CONFIG)


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    row.setdefault("timestamp", now())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def init() -> Path:
    if not CONFIG.exists():
        CONFIG.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
        CONFIG.chmod(0o600)
    return CONFIG


def service() -> str:
    return (config().get("BLUESKY_SERVICE") or DEFAULT_SERVICE).rstrip("/")


def request_json(
    nsid: str,
    *,
    params: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
    token: str = "",
    method: str = "GET",
) -> dict[str, Any]:
    url = f"{service()}/xrpc/{nsid}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"HTTP {exc.code}: {body_text}") from exc


def login() -> dict[str, Any]:
    init()
    cfg = config()
    handle = cfg.get("BLUESKY_HANDLE", "")
    password = cfg.get("BLUESKY_APP_PASSWORD", "")
    if not handle or not password:
        return {
            "ok": False,
            "error": "BLUESKY_HANDLE and BLUESKY_APP_PASSWORD are required in config/bluesky.env.",
        }
    payload = request_json(
        "com.atproto.server.createSession",
        body={"identifier": handle, "password": password},
        method="POST",
    )
    updates = {
        "BLUESKY_DID": payload.get("did", ""),
        "BLUESKY_ACCESS_JWT": payload.get("accessJwt", ""),
        "BLUESKY_REFRESH_JWT": payload.get("refreshJwt", ""),
        "BLUESKY_HANDLE": payload.get("handle", handle),
        "BLUESKY_TOKEN_CREATED_AT": str(int(time.time())),
    }
    write_env(CONFIG, updates)
    append_jsonl(LOG, {"kind": "login", "ok": True, "handle": updates["BLUESKY_HANDLE"], "did": updates["BLUESKY_DID"]})
    return {"ok": True, "handle": updates["BLUESKY_HANDLE"], "did": updates["BLUESKY_DID"], "token_saved": bool(updates["BLUESKY_ACCESS_JWT"])}


def refresh() -> dict[str, Any]:
    cfg = config()
    token = cfg.get("BLUESKY_REFRESH_JWT", "")
    if not token:
        return {"ok": False, "error": "BLUESKY_REFRESH_JWT missing. Run login."}
    payload = request_json("com.atproto.server.refreshSession", token=token, method="POST")
    updates = {
        "BLUESKY_DID": payload.get("did", cfg.get("BLUESKY_DID", "")),
        "BLUESKY_ACCESS_JWT": payload.get("accessJwt", ""),
        "BLUESKY_REFRESH_JWT": payload.get("refreshJwt", ""),
        "BLUESKY_HANDLE": payload.get("handle", cfg.get("BLUESKY_HANDLE", "")),
        "BLUESKY_TOKEN_CREATED_AT": str(int(time.time())),
    }
    write_env(CONFIG, updates)
    append_jsonl(LOG, {"kind": "refresh", "ok": True})
    return {"ok": True, "handle": updates["BLUESKY_HANDLE"], "did": updates["BLUESKY_DID"]}


def access_token() -> str:
    cfg = config()
    token = cfg.get("BLUESKY_ACCESS_JWT", "")
    created = float(cfg.get("BLUESKY_TOKEN_CREATED_AT", "0") or "0")
    if cfg.get("BLUESKY_REFRESH_JWT") and (not token or created < time.time() - 90 * 60):
        result = refresh()
        if result.get("ok"):
            token = config().get("BLUESKY_ACCESS_JWT", token)
    if not token:
        raise RuntimeError("BLUESKY_ACCESS_JWT missing. Run login.")
    return token


def profile() -> dict[str, Any]:
    cfg = config()
    actor = cfg.get("BLUESKY_HANDLE") or cfg.get("BLUESKY_DID")
    if not actor:
        raise RuntimeError("BLUESKY_HANDLE missing.")
    return request_json("app.bsky.actor.getProfile", params={"actor": actor}, token=access_token())


def recent_posts(limit: int = 8) -> list[dict[str, Any]]:
    cfg = config()
    actor = cfg.get("BLUESKY_HANDLE") or cfg.get("BLUESKY_DID")
    if not actor:
        return []
    data = request_json(
        "app.bsky.feed.getAuthorFeed",
        params={"actor": actor, "limit": max(1, min(limit, 30)), "filter": "posts_no_replies"},
        token=access_token(),
    )
    rows: list[dict[str, Any]] = []
    for item in data.get("feed") or []:
        if item.get("reason", {}).get("$type") == "app.bsky.feed.defs#reasonRepost":
            continue
        post = item.get("post") or {}
        record = post.get("record") or {}
        uri = post.get("uri", "")
        post_id = uri.rsplit("/", 1)[-1] if uri else ""
        author = post.get("author") or {}
        handle = author.get("handle") or actor
        rows.append({
            "uri": uri,
            "cid": post.get("cid", ""),
            "id": post_id,
            "text": clean(record.get("text"), 500),
            "created_at": record.get("createdAt"),
            "url": f"https://bsky.app/profile/{handle}/post/{post_id}" if handle and post_id else "",
            "reply_count": post.get("replyCount"),
            "repost_count": post.get("repostCount"),
            "like_count": post.get("likeCount"),
            "quote_count": post.get("quoteCount"),
        })
    return rows


def status() -> dict[str, Any]:
    cfg = config()
    if not cfg.get("BLUESKY_HANDLE"):
        data = {
            "connected": False,
            "manual_posting": True,
            "write_enabled": False,
            "diagnosis": "BLUESKY_HANDLE missing. Run init and fill config/bluesky.env.",
        }
        append_jsonl(LOG, {"kind": "status", **data})
        return data
    if not cfg.get("BLUESKY_ACCESS_JWT") and cfg.get("BLUESKY_APP_PASSWORD"):
        login_result = login()
        if not login_result.get("ok"):
            data = {"connected": False, "manual_posting": True, "write_enabled": False, "diagnosis": clean(login_result.get("error"), 800)}
            append_jsonl(LOG, {"kind": "status", **data})
            return data
    try:
        prof = profile()
        posts = recent_posts(8)
        data = {
            "connected": True,
            "manual_posting": True,
            "write_enabled": bool(config().get("BLUESKY_APP_PASSWORD")),
            "did": prof.get("did"),
            "handle": prof.get("handle"),
            "display_name": clean(prof.get("displayName"), 180),
            "description": clean(prof.get("description"), 500),
            "url": f"https://bsky.app/profile/{prof.get('handle')}" if prof.get("handle") else "",
            "followers": prof.get("followersCount"),
            "following": prof.get("followsCount"),
            "post_count": prof.get("postsCount"),
            "recent_posts": posts,
            "diagnosis": "Enchantify-local Bluesky AT Protocol integration is live. Posting remains consent-gated.",
        }
    except Exception as exc:
        data = {"connected": False, "manual_posting": True, "write_enabled": False, "diagnosis": clean(exc, 1000)}
    append_jsonl(LOG, {"kind": "status", **data})
    return data


def draft_post_payload(text: str) -> dict[str, Any]:
    return {
        "collection": "app.bsky.feed.post",
        "repo": config().get("BLUESKY_DID", ""),
        "record": {
            "$type": "app.bsky.feed.post",
            "text": text,
            "createdAt": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        },
    }


def create_post(text: str) -> dict[str, Any]:
    """Consent-gated primitive. Publication Desk should approve before calling."""
    cfg = config()
    repo = cfg.get("BLUESKY_DID")
    if not repo:
        login()
        repo = config().get("BLUESKY_DID")
    payload = draft_post_payload(text)
    payload["repo"] = repo
    result = request_json("com.atproto.repo.createRecord", body=payload, token=access_token(), method="POST")
    append_jsonl(LOG, {"kind": "create-post", "ok": True, "uri": result.get("uri"), "cid": result.get("cid")})
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Enchantify Bluesky adapter")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("login")
    sub.add_parser("refresh")
    sub.add_parser("status")
    recent = sub.add_parser("recent-posts")
    recent.add_argument("--limit", type=int, default=8)
    payload = sub.add_parser("post-payload")
    payload.add_argument("text")
    post = sub.add_parser("create-post")
    post.add_argument("text")
    args = parser.parse_args()

    if args.command == "init":
        print(f"BLUESKY_CONFIG: {init()}")
        return 0
    if args.command == "login":
        data = login()
        print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
        return 0 if data.get("ok") else 2
    if args.command == "refresh":
        data = refresh()
        print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
        return 0 if data.get("ok") else 2
    if args.command == "status":
        data = status()
        print("BLUESKY_ADAPTER_STATUS:")
        print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
        return 0 if data.get("connected") else 2
    if args.command == "recent-posts":
        print(json.dumps(recent_posts(args.limit), indent=2, ensure_ascii=False, default=str))
        return 0
    if args.command == "post-payload":
        print(json.dumps(draft_post_payload(args.text), indent=2, ensure_ascii=False, default=str))
        return 0
    if args.command == "create-post":
        print(json.dumps(create_post(args.text), indent=2, ensure_ascii=False, default=str))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

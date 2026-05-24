#!/usr/bin/env python3
"""Enchantify-local YouTube read adapter.

Uses a YouTube Data API key and channel ID stored in this install:

  config/youtube.env

Fallback reads legacy YT_KEY / YT_CH_ID values from config/secrets.env.
This adapter is read-only. Uploading videos requires OAuth and is deliberately
not enabled here.
"""

from __future__ import annotations

import argparse
import http.server
import json
import secrets
import socketserver
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent.parent
CONFIG = BASE / "config" / "youtube.env"
LEGACY_CONFIG = BASE / "config" / "secrets.env"
EXAMPLE = BASE / "config" / "youtube.env.example"
LOG = BASE / "logs" / "publishing" / "youtube-adapter.jsonl"
API_BASE = "https://www.googleapis.com/youtube/v3"
TOKEN_URL = "https://oauth2.googleapis.com/token"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
DEFAULT_REDIRECT_URI = "http://127.0.0.1:8765/oauth2callback"
READ_SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]
UPLOAD_SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.upload",
]


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
    existing.update({k: v for k, v in updates.items() if v is not None})
    comments = [
        "# Enchantify-local YouTube read integration.",
        "# youtube.env is gitignored.",
        "",
    ]
    lines = comments + [f"{key}={existing.get(key, '')}" for key in keys if key]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    path.chmod(0o600)


def config() -> dict[str, str]:
    data = parse_env(LEGACY_CONFIG)
    data.update({k: v for k, v in parse_env(CONFIG).items() if v})
    return data


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


def oauth_headers(cfg: dict[str, str], *, allow_refresh: bool = True) -> dict[str, str]:
    token = cfg.get("YT_ACCESS_TOKEN", "")
    expires_at = float(cfg.get("YT_TOKEN_EXPIRES_AT", "0") or "0")
    if allow_refresh and cfg.get("YT_REFRESH_TOKEN") and expires_at and expires_at < time.time() + 60:
        refreshed = refresh()
        if refreshed.get("ok"):
            cfg = config()
            token = cfg.get("YT_ACCESS_TOKEN", token)
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def request_json(
    path: str,
    params: dict[str, Any],
    timeout: int = 20,
    *,
    auth: bool = False,
    api_key_ok: bool = True,
) -> dict[str, Any]:
    cfg = config()
    headers = {"Accept": "application/json"}
    if auth:
        headers.update(oauth_headers(cfg))
        if "Authorization" not in headers:
            raise RuntimeError("YouTube OAuth token missing. Run auth-url/auth-server first.")
    if api_key_ok and "Authorization" not in headers:
        key = cfg.get("YT_KEY", "")
        if not key:
            raise RuntimeError("YT_KEY is missing. Add it to config/youtube.env.")
        params = {**params, "key": key}
    url = f"{API_BASE}/{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc


def oauth_post(form: dict[str, str]) -> dict[str, Any]:
    body = urllib.parse.urlencode(form).encode("utf-8")
    req = urllib.request.Request(
        TOKEN_URL,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")[:800]
        raise RuntimeError(f"HTTP {exc.code}: {body_text}") from exc


def scopes_for(mode: str) -> list[str]:
    return UPLOAD_SCOPES if mode == "upload" else READ_SCOPES


def auth_url(mode: str = "readonly", state: str = "") -> str:
    cfg = config()
    client_id = cfg.get("YT_CLIENT_ID", "")
    if not client_id:
        raise RuntimeError("YT_CLIENT_ID missing. Add OAuth client values to config/youtube.env.")
    redirect_uri = cfg.get("YT_REDIRECT_URI") or DEFAULT_REDIRECT_URI
    state = state or secrets.token_urlsafe(16)
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes_for(mode)),
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent",
        "state": state,
    }
    return f"{AUTH_URL}?{urllib.parse.urlencode(params)}"


def exchange_code(code: str) -> dict[str, Any]:
    cfg = config()
    client_id = cfg.get("YT_CLIENT_ID", "")
    client_secret = cfg.get("YT_CLIENT_SECRET", "")
    redirect_uri = cfg.get("YT_REDIRECT_URI") or DEFAULT_REDIRECT_URI
    if not client_id or not client_secret:
        raise RuntimeError("YT_CLIENT_ID and YT_CLIENT_SECRET are required.")
    payload = oauth_post({
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    })
    expires_at = str(int(time.time()) + int(payload.get("expires_in", 3600)))
    updates = {
        "YT_ACCESS_TOKEN": payload.get("access_token", ""),
        "YT_TOKEN_EXPIRES_AT": expires_at,
        "YT_OAUTH_SCOPE": payload.get("scope", ""),
    }
    if payload.get("refresh_token"):
        updates["YT_REFRESH_TOKEN"] = payload["refresh_token"]
    write_env(CONFIG, updates)
    append_jsonl(LOG, {"kind": "exchange-code", "ok": True, "scope": payload.get("scope", "")})
    return {"ok": True, "scope": payload.get("scope", ""), "expires_at": expires_at, "refresh_token_saved": bool(payload.get("refresh_token"))}


def refresh() -> dict[str, Any]:
    cfg = config()
    if not cfg.get("YT_REFRESH_TOKEN"):
        return {"ok": False, "error": "YT_REFRESH_TOKEN missing."}
    if not cfg.get("YT_CLIENT_ID") or not cfg.get("YT_CLIENT_SECRET"):
        return {"ok": False, "error": "YT_CLIENT_ID/YT_CLIENT_SECRET missing."}
    payload = oauth_post({
        "client_id": cfg["YT_CLIENT_ID"],
        "client_secret": cfg["YT_CLIENT_SECRET"],
        "refresh_token": cfg["YT_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    })
    expires_at = str(int(time.time()) + int(payload.get("expires_in", 3600)))
    write_env(CONFIG, {
        "YT_ACCESS_TOKEN": payload.get("access_token", ""),
        "YT_TOKEN_EXPIRES_AT": expires_at,
    })
    append_jsonl(LOG, {"kind": "refresh", "ok": True})
    return {"ok": True, "expires_at": expires_at}


def channel_status() -> dict[str, Any]:
    cfg = config()
    channel_id = cfg.get("YT_CH_ID", "")
    has_oauth = bool(cfg.get("YT_ACCESS_TOKEN") or cfg.get("YT_REFRESH_TOKEN"))
    if not (cfg.get("YT_KEY") or has_oauth) or not channel_id:
        return {
            "connected": False,
            "config": str(CONFIG),
            "legacy_config": str(LEGACY_CONFIG),
            "diagnosis": "YT_KEY/OAuth and/or YT_CH_ID missing. Add them to config/youtube.env.",
            "manual_posting": True,
            "upload_enabled": False,
            "oauth_connected": has_oauth,
        }

    channel = request_json(
        "channels",
        {
            "part": "snippet,statistics,contentDetails",
            "id": channel_id,
            "maxResults": 1,
        },
        auth=has_oauth,
    )
    items = channel.get("items") or []
    if not items:
        return {
            "connected": False,
            "channel_id": channel_id,
            "diagnosis": "No YouTube channel returned for YT_CH_ID.",
            "manual_posting": True,
            "upload_enabled": False,
        }

    channel_item = items[0]
    recent = request_json(
        "search",
        {
            "part": "snippet",
            "channelId": channel_id,
            "order": "date",
            "type": "video",
            "maxResults": 8,
        },
        auth=has_oauth,
    )
    video_ids = [
        row.get("id", {}).get("videoId")
        for row in recent.get("items", [])
        if row.get("id", {}).get("videoId")
    ]
    video_stats: dict[str, dict[str, Any]] = {}
    if video_ids:
        videos = request_json(
            "videos",
            {
                "part": "snippet,statistics",
                "id": ",".join(video_ids),
                "maxResults": len(video_ids),
            },
            auth=has_oauth,
        )
        for video in videos.get("items", []):
            video_stats[str(video.get("id"))] = video

    recent_videos: list[dict[str, Any]] = []
    for row in recent.get("items", []):
        video_id = row.get("id", {}).get("videoId", "")
        snippet = row.get("snippet") or {}
        stats = (video_stats.get(video_id) or {}).get("statistics") or {}
        recent_videos.append({
            "id": video_id,
            "title": clean(snippet.get("title"), 180),
            "published_at": snippet.get("publishedAt", ""),
            "url": f"https://www.youtube.com/watch?v={video_id}" if video_id else "",
            "views": stats.get("viewCount"),
            "likes": stats.get("likeCount"),
            "comments": stats.get("commentCount"),
        })

    attrs = channel_item.get("snippet") or {}
    stats = channel_item.get("statistics") or {}
    return {
        "connected": True,
        "oauth_connected": has_oauth,
        "manual_posting": True,
        "upload_enabled": "https://www.googleapis.com/auth/youtube.upload" in cfg.get("YT_OAUTH_SCOPE", ""),
        "channel_id": channel_item.get("id"),
        "title": clean(attrs.get("title"), 180),
        "description": clean(attrs.get("description"), 500),
        "url": f"https://www.youtube.com/channel/{channel_item.get('id')}",
        "subscriber_count": stats.get("subscriberCount"),
        "view_count": stats.get("viewCount"),
        "video_count": stats.get("videoCount"),
        "recent_videos": recent_videos,
        "diagnosis": "Enchantify-local YouTube integration is live. Public upload/posting remains manual until explicitly enabled.",
    }


def research(query: str, max_results: int = 8) -> dict[str, Any]:
    data = request_json(
        "search",
        {
            "part": "snippet",
            "q": query,
            "type": "video",
            "order": "relevance",
            "maxResults": max(1, min(max_results, 25)),
            "safeSearch": "moderate",
        },
    )
    video_ids = [
        row.get("id", {}).get("videoId")
        for row in data.get("items", [])
        if row.get("id", {}).get("videoId")
    ]
    stats_by_id: dict[str, dict[str, Any]] = {}
    if video_ids:
        videos = request_json(
            "videos",
            {
                "part": "snippet,statistics,contentDetails",
                "id": ",".join(video_ids),
                "maxResults": len(video_ids),
            },
        )
        for video in videos.get("items", []):
            stats_by_id[str(video.get("id"))] = video
    results = []
    for row in data.get("items", []):
        video_id = row.get("id", {}).get("videoId", "")
        snippet = row.get("snippet") or {}
        stats = (stats_by_id.get(video_id) or {}).get("statistics") or {}
        details = (stats_by_id.get(video_id) or {}).get("contentDetails") or {}
        results.append({
            "id": video_id,
            "title": clean(snippet.get("title"), 220),
            "channel_title": clean(snippet.get("channelTitle"), 160),
            "published_at": snippet.get("publishedAt", ""),
            "url": f"https://www.youtube.com/watch?v={video_id}" if video_id else "",
            "description": clean(snippet.get("description"), 350),
            "views": stats.get("viewCount"),
            "likes": stats.get("likeCount"),
            "comments": stats.get("commentCount"),
            "duration": details.get("duration"),
        })
    row = {"kind": "research", "query": query, "result_count": len(results)}
    append_jsonl(LOG, row)
    return {"query": query, "results": results, "diagnosis": "Public YouTube video metadata search complete."}


def status() -> dict[str, Any]:
    try:
        data = channel_status()
    except Exception as exc:
        data = {
            "connected": False,
            "manual_posting": True,
            "upload_enabled": False,
            "config": str(CONFIG),
            "diagnosis": clean(exc, 1000),
        }
    append_jsonl(LOG, {"kind": "status", **data})
    return data


class OAuthHandler(http.server.BaseHTTPRequestHandler):
    code: str = ""
    error: str = ""

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        OAuthHandler.code = (params.get("code") or [""])[0]
        OAuthHandler.error = (params.get("error") or [""])[0]
        body = (
            "<html><body><h1>Enchantify YouTube OAuth</h1>"
            "<p>The YouTube pact has been sealed. You can return to Codex.</p>"
            "</body></html>"
        )
        if OAuthHandler.error:
            body = (
                "<html><body><h1>Enchantify YouTube OAuth</h1>"
                f"<p>Google returned an error: {OAuthHandler.error}</p>"
                "</body></html>"
            )
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, format: str, *args: Any) -> None:
        return


def auth_server(mode: str = "readonly", port: int = 8765) -> dict[str, Any]:
    init()
    cfg = config()
    redirect_uri = cfg.get("YT_REDIRECT_URI") or DEFAULT_REDIRECT_URI
    parsed = urllib.parse.urlparse(redirect_uri)
    port = parsed.port or port
    url = auth_url(mode=mode)
    print("YOUTUBE_AUTH_URL:")
    print(url)
    print(f"Waiting for Google callback on http://127.0.0.1:{port}/oauth2callback ...")
    with socketserver.TCPServer(("127.0.0.1", port), OAuthHandler) as httpd:
        httpd.handle_request()
    if OAuthHandler.error:
        return {"ok": False, "error": OAuthHandler.error}
    if not OAuthHandler.code:
        return {"ok": False, "error": "No OAuth code received."}
    return exchange_code(OAuthHandler.code)


def main() -> int:
    parser = argparse.ArgumentParser(description="Enchantify YouTube read adapter")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("status")
    auth_url_parser = sub.add_parser("auth-url")
    auth_url_parser.add_argument("--mode", choices=["readonly", "upload"], default="readonly")
    exchange = sub.add_parser("exchange-code")
    exchange.add_argument("code")
    refresh_parser = sub.add_parser("refresh")
    auth_server_parser = sub.add_parser("auth-server")
    auth_server_parser.add_argument("--mode", choices=["readonly", "upload"], default="readonly")
    auth_server_parser.add_argument("--port", type=int, default=8765)
    research_parser = sub.add_parser("research")
    research_parser.add_argument("query")
    research_parser.add_argument("--max-results", type=int, default=8)
    args = parser.parse_args()

    if args.command == "init":
        print(f"YOUTUBE_CONFIG: {init()}")
        return 0
    if args.command == "status":
        data = status()
        print("YOUTUBE_ADAPTER_STATUS:")
        print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
        return 0 if data.get("connected") else 2
    if args.command == "auth-url":
        print(auth_url(mode=args.mode))
        return 0
    if args.command == "exchange-code":
        print(json.dumps(exchange_code(args.code), indent=2, ensure_ascii=False))
        return 0
    if args.command == "refresh":
        print(json.dumps(refresh(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "auth-server":
        print(json.dumps(auth_server(args.mode, args.port), indent=2, ensure_ascii=False))
        return 0
    if args.command == "research":
        print(json.dumps(research(args.query, args.max_results), indent=2, ensure_ascii=False, default=str))
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

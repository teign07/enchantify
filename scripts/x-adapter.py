#!/usr/bin/env python3
"""Enchantify-local X adapter.

Official X API only. No browser cookie scraping, no internal GraphQL endpoints.

Credentials live in:

  config/x.env

Current role: read channel/account status, search public X when the account/app
has API access, and prepare for future consent-gated posting.
"""

from __future__ import annotations

import argparse
import base64
import hmac
import hashlib
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
CONFIG = BASE / "config" / "x.env"
EXAMPLE = BASE / "config" / "x.env.example"
LOG = BASE / "logs" / "publishing" / "x-adapter.jsonl"
API_BASE = "https://api.x.com/2"
API_V1_BASE = "https://api.twitter.com/1.1"
AUTH_URL = "https://twitter.com/i/oauth2/authorize"
TOKEN_URL = "https://api.x.com/2/oauth2/token"
DEFAULT_REDIRECT_URI = "http://127.0.0.1:8766/oauth2callback"
READ_SCOPES = ["tweet.read", "users.read", "offline.access"]
WRITE_SCOPES = ["tweet.read", "users.read", "tweet.write", "offline.access"]


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
        "# Enchantify-local X / Twitter integration.",
        "# x.env is gitignored.",
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


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def scopes_for(mode: str) -> list[str]:
    return WRITE_SCOPES if mode == "write" else READ_SCOPES


def auth_url(mode: str = "readonly", state: str = "") -> str:
    init()
    cfg = config()
    client_id = cfg.get("X_CLIENT_ID", "")
    if not client_id:
        raise RuntimeError("X_CLIENT_ID missing. Add it to config/x.env.")
    redirect_uri = cfg.get("X_REDIRECT_URI") or DEFAULT_REDIRECT_URI
    verifier = b64url(secrets.token_bytes(48))
    challenge = b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    write_env(CONFIG, {"X_CODE_VERIFIER": verifier})
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes_for(mode)),
        "state": state or secrets.token_urlsafe(16),
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return f"{AUTH_URL}?{urllib.parse.urlencode(params)}"


def token_headers(cfg: dict[str, str]) -> dict[str, str]:
    headers = {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}
    if cfg.get("X_CLIENT_SECRET"):
        raw = f"{cfg.get('X_CLIENT_ID', '')}:{cfg['X_CLIENT_SECRET']}".encode("utf-8")
        headers["Authorization"] = "Basic " + base64.b64encode(raw).decode("ascii")
    return headers


def oauth1_ready(cfg: dict[str, str] | None = None) -> bool:
    cfg = cfg or config()
    return all(cfg.get(key) for key in ("X_CONSUMER_KEY", "X_CONSUMER_SECRET", "X_ACCESS_TOKEN_V1", "X_ACCESS_TOKEN_SECRET_V1"))


def oauth1_quote(value: Any) -> str:
    return urllib.parse.quote(str(value), safe="~-._")


def oauth1_header(method: str, url: str, request_params: dict[str, Any] | None = None) -> str:
    cfg = config()
    if not oauth1_ready(cfg):
        raise RuntimeError("X OAuth 1.0a tokens missing.")
    oauth_params = {
        "oauth_consumer_key": cfg["X_CONSUMER_KEY"],
        "oauth_nonce": secrets.token_urlsafe(24),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": cfg["X_ACCESS_TOKEN_V1"],
        "oauth_version": "1.0",
    }
    signature_params = {**(request_params or {}), **oauth_params}
    encoded_pairs = sorted((oauth1_quote(k), oauth1_quote(v)) for k, v in signature_params.items() if v is not None)
    param_string = "&".join(f"{k}={v}" for k, v in encoded_pairs)
    base_string = "&".join([method.upper(), oauth1_quote(url), oauth1_quote(param_string)])
    signing_key = f"{oauth1_quote(cfg['X_CONSUMER_SECRET'])}&{oauth1_quote(cfg['X_ACCESS_TOKEN_SECRET_V1'])}"
    signature = base64.b64encode(hmac.new(signing_key.encode("utf-8"), base_string.encode("utf-8"), hashlib.sha1).digest()).decode("ascii")
    oauth_params["oauth_signature"] = signature
    return "OAuth " + ", ".join(f'{oauth1_quote(k)}="{oauth1_quote(v)}"' for k, v in sorted(oauth_params.items()))


def request_oauth1_json(path: str, params: dict[str, Any] | None = None, *, method: str = "GET") -> dict[str, Any]:
    params = params or {}
    url = f"{API_V1_BASE}/{path.lstrip('/')}"
    request_url = url
    data = None
    headers = {"Accept": "application/json", "Authorization": oauth1_header(method, url, params)}
    if method.upper() == "GET":
        if params:
            request_url += "?" + urllib.parse.urlencode(params)
    else:
        data = urllib.parse.urlencode(params).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(request_url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"HTTP {exc.code}: {body_text}") from exc


def oauth_post(form: dict[str, str]) -> dict[str, Any]:
    cfg = config()
    body = urllib.parse.urlencode(form).encode("utf-8")
    req = urllib.request.Request(TOKEN_URL, data=body, headers=token_headers(cfg))
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"HTTP {exc.code}: {body_text}") from exc


def exchange_code(code: str) -> dict[str, Any]:
    cfg = config()
    client_id = cfg.get("X_CLIENT_ID", "")
    redirect_uri = cfg.get("X_REDIRECT_URI") or DEFAULT_REDIRECT_URI
    verifier = cfg.get("X_CODE_VERIFIER", "")
    if not client_id or not verifier:
        raise RuntimeError("X_CLIENT_ID and X_CODE_VERIFIER are required.")
    payload = oauth_post({
        "code": code,
        "grant_type": "authorization_code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_verifier": verifier,
    })
    expires_at = str(int(time.time()) + int(payload.get("expires_in", 7200)))
    write_env(CONFIG, {
        "X_ACCESS_TOKEN": payload.get("access_token", ""),
        "X_REFRESH_TOKEN": payload.get("refresh_token", ""),
        "X_TOKEN_EXPIRES_AT": expires_at,
        "X_OAUTH_SCOPE": payload.get("scope", ""),
    })
    append_jsonl(LOG, {"kind": "exchange-code", "ok": True, "scope": payload.get("scope", "")})
    return {"ok": True, "scope": payload.get("scope", ""), "expires_at": expires_at, "refresh_token_saved": bool(payload.get("refresh_token"))}


def refresh() -> dict[str, Any]:
    cfg = config()
    if not cfg.get("X_REFRESH_TOKEN"):
        return {"ok": False, "error": "X_REFRESH_TOKEN missing."}
    payload = oauth_post({
        "refresh_token": cfg["X_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
        "client_id": cfg.get("X_CLIENT_ID", ""),
    })
    expires_at = str(int(time.time()) + int(payload.get("expires_in", 7200)))
    updates = {
        "X_ACCESS_TOKEN": payload.get("access_token", ""),
        "X_TOKEN_EXPIRES_AT": expires_at,
        "X_OAUTH_SCOPE": payload.get("scope", cfg.get("X_OAUTH_SCOPE", "")),
    }
    if payload.get("refresh_token"):
        updates["X_REFRESH_TOKEN"] = payload["refresh_token"]
    write_env(CONFIG, updates)
    append_jsonl(LOG, {"kind": "refresh", "ok": True})
    return {"ok": True, "expires_at": expires_at}


def bearer() -> str:
    cfg = config()
    token = cfg.get("X_ACCESS_TOKEN", "")
    expires_at = float(cfg.get("X_TOKEN_EXPIRES_AT", "0") or "0")
    if cfg.get("X_REFRESH_TOKEN") and expires_at and expires_at < time.time() + 60:
        result = refresh()
        if result.get("ok"):
            token = config().get("X_ACCESS_TOKEN", token)
    if not token:
        raise RuntimeError("X_ACCESS_TOKEN missing. Run auth-url/auth-server first.")
    return token


def request_json(path: str, params: dict[str, Any] | None = None, *, method: str = "GET", body: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"{API_BASE}/{path.lstrip('/')}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Authorization": f"Bearer {bearer()}", "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"HTTP {exc.code}: {body_text}") from exc


def status() -> dict[str, Any]:
    cfg = config()
    if not cfg.get("X_CLIENT_ID"):
        data = {"connected": False, "diagnosis": "X_CLIENT_ID missing. Add app credentials to config/x.env.", "manual_posting": True}
        append_jsonl(LOG, {"kind": "status", **data})
        return data
    if not cfg.get("X_ACCESS_TOKEN"):
        if oauth1_ready(cfg):
            try:
                user = request_oauth1_json("account/verify_credentials.json", {"include_email": "false", "skip_status": "true"})
                data = {
                    "connected": True,
                    "manual_posting": True,
                    "write_enabled": True,
                    "oauth_mode": "oauth1a-user-context",
                    "id": user.get("id_str"),
                    "name": clean(user.get("name"), 180),
                    "username": user.get("screen_name"),
                    "url": f"https://x.com/{user.get('screen_name')}" if user.get("screen_name") else "",
                    "followers": user.get("followers_count"),
                    "following": user.get("friends_count"),
                    "tweet_count": user.get("statuses_count"),
                    "diagnosis": "Enchantify-local X OAuth 1.0a integration is live. Posting remains consent-gated.",
                }
            except Exception as exc:
                data = {"connected": False, "manual_posting": True, "auth_url_ready": True, "diagnosis": f"OAuth2 token missing, and OAuth 1.0a verification failed: {clean(exc, 900)}"}
        else:
            data = {"connected": False, "diagnosis": "X OAuth token missing. Run auth-url/auth-server or add OAuth 1.0a user tokens.", "manual_posting": True, "auth_url_ready": True}
        append_jsonl(LOG, {"kind": "status", **data})
        return data
    try:
        me = request_json("users/me", {"user.fields": "description,public_metrics,username,verified"})
        user = me.get("data") or {}
        metrics = user.get("public_metrics") or {}
        data = {
            "connected": True,
            "manual_posting": True,
            "write_enabled": "tweet.write" in cfg.get("X_OAUTH_SCOPE", ""),
            "id": user.get("id"),
            "name": clean(user.get("name"), 180),
            "username": user.get("username"),
            "url": f"https://x.com/{user.get('username')}" if user.get("username") else "",
            "followers": metrics.get("followers_count"),
            "following": metrics.get("following_count"),
            "tweet_count": metrics.get("tweet_count"),
            "scope": cfg.get("X_OAUTH_SCOPE", ""),
            "diagnosis": "Enchantify-local X OAuth integration is live. Posting remains consent-gated.",
        }
    except Exception as exc:
        data = {"connected": False, "manual_posting": True, "diagnosis": clean(exc, 1000)}
    append_jsonl(LOG, {"kind": "status", **data})
    return data


def research(query: str, max_results: int = 10) -> dict[str, Any]:
    data = request_json(
        "tweets/search/recent",
        {
            "query": query,
            "max_results": max(10, min(max_results, 100)),
            "tweet.fields": "created_at,public_metrics,lang,context_annotations",
            "expansions": "author_id",
            "user.fields": "username,name,public_metrics",
        },
    )
    users = {row.get("id"): row for row in (data.get("includes", {}) or {}).get("users", [])}
    rows = []
    for tweet in data.get("data") or []:
        author = users.get(tweet.get("author_id")) or {}
        metrics = tweet.get("public_metrics") or {}
        rows.append({
            "id": tweet.get("id"),
            "text": clean(tweet.get("text"), 500),
            "created_at": tweet.get("created_at"),
            "author": author.get("username"),
            "author_name": author.get("name"),
            "url": f"https://x.com/{author.get('username')}/status/{tweet.get('id')}" if author.get("username") and tweet.get("id") else "",
            "likes": metrics.get("like_count"),
            "replies": metrics.get("reply_count"),
            "reposts": metrics.get("retweet_count"),
            "quotes": metrics.get("quote_count"),
        })
    append_jsonl(LOG, {"kind": "research", "query": query, "count": len(rows)})
    return {"query": query, "results": rows, "diagnosis": "Recent X search complete."}


def draft_post_payload(text: str) -> dict[str, Any]:
    return {"text": text}


class OAuthHandler(http.server.BaseHTTPRequestHandler):
    code: str = ""
    error: str = ""

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        OAuthHandler.code = (params.get("code") or [""])[0]
        OAuthHandler.error = (params.get("error") or [""])[0]
        body = "<html><body><h1>Enchantify X OAuth</h1><p>The X pact has been sealed. You can return to Codex.</p></body></html>"
        if OAuthHandler.error:
            body = f"<html><body><h1>Enchantify X OAuth</h1><p>X returned an error: {OAuthHandler.error}</p></body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, format: str, *args: Any) -> None:
        return


def auth_server(mode: str = "readonly", port: int = 8766) -> dict[str, Any]:
    url = auth_url(mode)
    cfg = config()
    redirect_uri = cfg.get("X_REDIRECT_URI") or DEFAULT_REDIRECT_URI
    parsed = urllib.parse.urlparse(redirect_uri)
    port = parsed.port or port
    print("X_AUTH_URL:", flush=True)
    print(url, flush=True)
    print(f"Waiting for X callback on http://127.0.0.1:{port}/oauth2callback ...", flush=True)
    with socketserver.TCPServer(("127.0.0.1", port), OAuthHandler) as httpd:
        httpd.handle_request()
    if OAuthHandler.error:
        return {"ok": False, "error": OAuthHandler.error}
    if not OAuthHandler.code:
        return {"ok": False, "error": "No OAuth code received."}
    return exchange_code(OAuthHandler.code)


def main() -> int:
    parser = argparse.ArgumentParser(description="Enchantify X adapter")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("status")
    auth_url_parser = sub.add_parser("auth-url")
    auth_url_parser.add_argument("--mode", choices=["readonly", "write"], default="readonly")
    auth_server_parser = sub.add_parser("auth-server")
    auth_server_parser.add_argument("--mode", choices=["readonly", "write"], default="readonly")
    auth_server_parser.add_argument("--port", type=int, default=8766)
    exchange = sub.add_parser("exchange-code")
    exchange.add_argument("code")
    sub.add_parser("refresh")
    research_parser = sub.add_parser("research")
    research_parser.add_argument("query")
    research_parser.add_argument("--max-results", type=int, default=10)
    post_payload = sub.add_parser("post-payload")
    post_payload.add_argument("text")
    args = parser.parse_args()

    if args.command == "init":
        print(f"X_CONFIG: {init()}")
        return 0
    if args.command == "status":
        data = status()
        print("X_ADAPTER_STATUS:")
        print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
        return 0 if data.get("connected") else 2
    if args.command == "auth-url":
        print(auth_url(args.mode))
        return 0
    if args.command == "auth-server":
        print(json.dumps(auth_server(args.mode, args.port), indent=2, ensure_ascii=False, default=str))
        return 0
    if args.command == "exchange-code":
        print(json.dumps(exchange_code(args.code), indent=2, ensure_ascii=False, default=str))
        return 0
    if args.command == "refresh":
        print(json.dumps(refresh(), indent=2, ensure_ascii=False, default=str))
        return 0
    if args.command == "research":
        print(json.dumps(research(args.query, args.max_results), indent=2, ensure_ascii=False, default=str))
        return 0
    if args.command == "post-payload":
        print(json.dumps(draft_post_payload(args.text), indent=2, ensure_ascii=False))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

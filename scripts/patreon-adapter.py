#!/usr/bin/env python3
"""Enchantify-local Patreon adapter.

Keeps all Patreon OAuth credentials and tokens inside this Enchantify install:
`config/patreon.env`. Direct public posting remains disabled until Patreon's
write path is verified; the Publication Desk can export Patreon-ready drafts.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent
CONFIG = BASE / "config" / "patreon.env"
CONFIG_EXAMPLE = BASE / "config" / "patreon.env.example"
PUBLISHING = BASE / "memory" / "publishing"
EXECUTION_QUEUE = PUBLISHING / "execution-queue.json"
READY_DIR = PUBLISHING / "patreon-ready"
LEDGER = PUBLISHING / "publication-ledger.jsonl"
LOG_DIR = BASE / "logs" / "publishing"
API_BASE = "https://www.patreon.com/api/oauth2/v2"
TOKEN_URL = "https://www.patreon.com/api/oauth2/token"
DEFAULT_REDIRECT = "http://localhost:8765/patreon/callback"


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def clean(value: Any, limit: int = 900) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit].rstrip() + ("..." if len(text) > limit else "")


def read(path: Path, limit: int | None = None) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[:limit] if limit else text


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else default
    except Exception:
        return default


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    row.setdefault("timestamp", now())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def parse_env(path: Path = CONFIG) -> dict[str, str]:
    cfg: dict[str, str] = {}
    if not path.exists():
        return cfg
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        cfg[key.strip()] = value.strip().strip('"').strip("'")
    return cfg


def write_env(updates: dict[str, str]) -> None:
    current = parse_env()
    current.update({k: v for k, v in updates.items() if v is not None})
    order = [
        "PATREON_CLIENT_ID",
        "PATREON_CLIENT_SECRET",
        "PATREON_ACCESS_TOKEN",
        "PATREON_REFRESH_TOKEN",
        "PATREON_CAMPAIGN_ID",
        "PATREON_CAMPAIGN_URL",
        "PATREON_REDIRECT_URI",
    ]
    lines = [
        "# Enchantify Patreon credentials. Local and gitignored.",
        "# Create an app at Patreon Developer Portal, then run:",
        "# python3 scripts/patreon-adapter.py auth-url",
        "",
    ]
    for key in order:
        lines.append(f"{key}={current.get(key, '')}")
    for key in sorted(k for k in current if k not in order):
        lines.append(f"{key}={current[key]}")
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    try:
        CONFIG.chmod(0o600)
    except Exception:
        pass


def init_config(*, client_id: str = "", client_secret: str = "", campaign_url: str = "https://www.patreon.com/c/thedoobaleedoos") -> None:
    CONFIG_EXAMPLE.write_text(
        "# Copy to config/patreon.env. Do not commit real values.\n"
        "PATREON_CLIENT_ID=\n"
        "PATREON_CLIENT_SECRET=\n"
        "PATREON_ACCESS_TOKEN=\n"
        "PATREON_REFRESH_TOKEN=\n"
        "PATREON_CAMPAIGN_ID=\n"
        "PATREON_CAMPAIGN_URL=https://www.patreon.com/c/thedoobaleedoos\n"
        f"PATREON_REDIRECT_URI={DEFAULT_REDIRECT}\n",
        encoding="utf-8",
    )
    if not CONFIG.exists():
        write_env({
            "PATREON_CLIENT_ID": client_id,
            "PATREON_CLIENT_SECRET": client_secret,
            "PATREON_CAMPAIGN_URL": campaign_url,
            "PATREON_REDIRECT_URI": DEFAULT_REDIRECT,
        })
    else:
        updates = {}
        if client_id:
            updates["PATREON_CLIENT_ID"] = client_id
        if client_secret:
            updates["PATREON_CLIENT_SECRET"] = client_secret
        if campaign_url:
            updates["PATREON_CAMPAIGN_URL"] = campaign_url
        if updates:
            write_env(updates)


def required(cfg: dict[str, str], *keys: str) -> list[str]:
    return [key for key in keys if not cfg.get(key)]


def urlopen_json(req: urllib.request.Request, timeout: int = 45) -> dict[str, Any]:
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def oauth_post(form: dict[str, str]) -> dict[str, Any]:
    body = urllib.parse.urlencode(form).encode("utf-8")
    req = urllib.request.Request(
        TOKEN_URL,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    return urlopen_json(req)


def refresh_token() -> dict[str, Any]:
    cfg = parse_env()
    missing = required(cfg, "PATREON_CLIENT_ID", "PATREON_CLIENT_SECRET", "PATREON_REFRESH_TOKEN")
    if missing:
        return {"ok": False, "error": f"Missing {', '.join(missing)} in {CONFIG}"}
    try:
        payload = oauth_post({
            "grant_type": "refresh_token",
            "refresh_token": cfg["PATREON_REFRESH_TOKEN"],
            "client_id": cfg["PATREON_CLIENT_ID"],
            "client_secret": cfg["PATREON_CLIENT_SECRET"],
        })
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        result = {"ok": False, "error": f"HTTP {exc.code}: {clean(body, 700)}"}
        append_jsonl(LOG_DIR / "patreon-adapter.jsonl", {"kind": "refresh", **result})
        return result
    except Exception as exc:
        result = {"ok": False, "error": clean(exc, 700)}
        append_jsonl(LOG_DIR / "patreon-adapter.jsonl", {"kind": "refresh", **result})
        return result
    access = payload.get("access_token")
    refresh = payload.get("refresh_token") or cfg.get("PATREON_REFRESH_TOKEN", "")
    if not access:
        result = {"ok": False, "error": "No access_token in refresh response", "keys": sorted(payload.keys())}
        append_jsonl(LOG_DIR / "patreon-adapter.jsonl", {"kind": "refresh", **result})
        return result
    write_env({"PATREON_ACCESS_TOKEN": access, "PATREON_REFRESH_TOKEN": refresh})
    result = {"ok": True, "token_type": payload.get("token_type", ""), "expires_in": payload.get("expires_in", "")}
    append_jsonl(LOG_DIR / "patreon-adapter.jsonl", {"kind": "refresh", **result})
    return result


def auth_url(redirect_uri: str | None = None, *, state: str = "enchantify") -> str:
    cfg = parse_env()
    missing = required(cfg, "PATREON_CLIENT_ID")
    if missing:
        raise SystemExit(f"Missing PATREON_CLIENT_ID in {CONFIG}. Run init after creating a Patreon app.")
    redirect = redirect_uri or cfg.get("PATREON_REDIRECT_URI") or DEFAULT_REDIRECT
    params = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": cfg["PATREON_CLIENT_ID"],
        "redirect_uri": redirect,
        "scope": "identity identity[email] campaigns.members campaigns.posts",
        "state": state,
    })
    return f"https://www.patreon.com/oauth2/authorize?{params}"


def exchange_code(code: str, redirect_uri: str | None = None) -> dict[str, Any]:
    cfg = parse_env()
    missing = required(cfg, "PATREON_CLIENT_ID", "PATREON_CLIENT_SECRET")
    if missing:
        return {"ok": False, "error": f"Missing {', '.join(missing)} in {CONFIG}"}
    redirect = redirect_uri or cfg.get("PATREON_REDIRECT_URI") or DEFAULT_REDIRECT
    try:
        payload = oauth_post({
            "grant_type": "authorization_code",
            "code": code,
            "client_id": cfg["PATREON_CLIENT_ID"],
            "client_secret": cfg["PATREON_CLIENT_SECRET"],
            "redirect_uri": redirect,
        })
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        result = {"ok": False, "error": f"HTTP {exc.code}: {clean(body, 700)}"}
        append_jsonl(LOG_DIR / "patreon-adapter.jsonl", {"kind": "exchange", **result})
        return result
    except Exception as exc:
        result = {"ok": False, "error": clean(exc, 700)}
        append_jsonl(LOG_DIR / "patreon-adapter.jsonl", {"kind": "exchange", **result})
        return result
    access = payload.get("access_token")
    refresh = payload.get("refresh_token")
    if not access or not refresh:
        result = {"ok": False, "error": "No access_token/refresh_token in exchange response", "keys": sorted(payload.keys())}
        append_jsonl(LOG_DIR / "patreon-adapter.jsonl", {"kind": "exchange", **result})
        return result
    write_env({"PATREON_ACCESS_TOKEN": access, "PATREON_REFRESH_TOKEN": refresh, "PATREON_REDIRECT_URI": redirect})
    result = {"ok": True, "token_type": payload.get("token_type", ""), "expires_in": payload.get("expires_in", "")}
    append_jsonl(LOG_DIR / "patreon-adapter.jsonl", {"kind": "exchange", **result})
    return result


def api_get(path: str, params: dict[str, str] | None = None, *, retry: bool = True) -> dict[str, Any]:
    cfg = parse_env()
    missing = required(cfg, "PATREON_ACCESS_TOKEN")
    if missing:
        raise RuntimeError(f"Missing PATREON_ACCESS_TOKEN in {CONFIG}")
    url = f"{API_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {cfg['PATREON_ACCESS_TOKEN']}"})
    try:
        return urlopen_json(req)
    except urllib.error.HTTPError as exc:
        if retry and exc.code == 401 and refresh_token().get("ok"):
            return api_get(path, params, retry=False)
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {clean(body, 700)}") from exc


def campaign_id() -> str:
    cfg = parse_env()
    if cfg.get("PATREON_CAMPAIGN_ID"):
        return cfg["PATREON_CAMPAIGN_ID"]
    data = api_get("/campaigns", {
        "fields[campaign]": "creation_name,patron_count,url",
    })
    first = (data.get("data") or [{}])[0]
    ident = str(first.get("id") or "")
    if ident:
        write_env({"PATREON_CAMPAIGN_ID": ident})
    return ident


def status() -> dict[str, Any]:
    try:
        cid = campaign_id()
        campaigns = api_get("/campaigns", {"fields[campaign]": "creation_name,patron_count,url"})
        posts = api_get(f"/campaigns/{cid}/posts", {
            "page[count]": "3",
            "fields[post]": "title,published_at,url",
        }) if cid else {}
        result = {
            "connected": True,
            "campaign_id": cid,
            "campaigns": campaigns.get("data", [])[:1],
            "posts": posts.get("data", [])[:3],
            "diagnosis": "Enchantify-local Patreon read integration is live.",
        }
    except Exception as exc:
        result = {
            "connected": False,
            "config": str(CONFIG),
            "diagnosis": clean(exc, 900),
        }
    append_jsonl(LOG_DIR / "patreon-adapter.jsonl", {"kind": "status", **result})
    return result


class AuthHandler(BaseHTTPRequestHandler):
    server_version = "EnchantifyPatreonAuth/1.0"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        code = (qs.get("code") or [""])[0]
        error = (qs.get("error") or [""])[0]
        self.server.auth_result = {"code": code, "error": error}  # type: ignore[attr-defined]
        body = (
            "<html><body><h1>Enchantify Patreon Auth</h1>"
            + ("<p>Code received. You can return to Codex.</p>" if code else f"<p>Error: {html.escape(error or 'missing code')}</p>")
            + "</body></html>"
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_: Any) -> None:
        return


def auth_server(port: int = 8765) -> dict[str, Any]:
    redirect = f"http://localhost:{port}/patreon/callback"
    print("Open this URL and authorize Patreon:")
    print(auth_url(redirect))
    httpd = HTTPServer(("127.0.0.1", port), AuthHandler)
    httpd.auth_result = {}  # type: ignore[attr-defined]
    httpd.handle_request()
    code = httpd.auth_result.get("code", "")  # type: ignore[attr-defined]
    error = httpd.auth_result.get("error", "")  # type: ignore[attr-defined]
    if error or not code:
        return {"ok": False, "error": error or "No code received"}
    return exchange_code(code, redirect)


def execution_item(item_id: str) -> dict[str, Any] | None:
    data = load_json(EXECUTION_QUEUE, {"version": 1, "items": []})
    items = data.get("items") if isinstance(data.get("items"), list) else []
    if item_id == "latest":
        candidates = [item for item in items if item.get("status") in {"queued", "review_sent", "ready", "patreon_ready"}]
        return candidates[-1] if candidates else None
    return next((item for item in items if item.get("id") == item_id), None)


def update_execution(item_id: str, **updates: Any) -> None:
    data = load_json(EXECUTION_QUEUE, {"version": 1, "items": []})
    for item in data.get("items", []):
        if item.get("id") == item_id:
            item.update(updates)
            break
    save_json(EXECUTION_QUEUE, data)


def structured_payload(item: dict[str, Any]) -> dict[str, Any]:
    path = Path(str(item.get("structured") or ""))
    data = load_json(path, {}) if path.exists() else {}
    brief = data.get("brief")
    return brief if isinstance(brief, dict) else data


def post_body_from_payload(payload: dict[str, Any], fallback_text: str) -> tuple[str, str]:
    title = clean(payload.get("title") or "A Note From The Doobaleedoos", 140)
    parts = payload.get("draft_parts")
    if isinstance(parts, list) and parts:
        body = "\n\n".join(str(part).strip() for part in parts if str(part).strip())
    else:
        body = fallback_text
    cta = clean(payload.get("cta") or "", 1000)
    if cta and cta not in body:
        body = body.rstrip() + "\n\n---\n\n" + cta
    return title, body.strip()


def export(item_id: str) -> dict[str, Any]:
    READY_DIR.mkdir(parents=True, exist_ok=True)
    item = execution_item(item_id)
    if not item:
        raise SystemExit(f"PATREON_ADAPTER: execution item not found: {item_id}")
    payload = structured_payload(item)
    brief_path = Path(str(item.get("brief") or ""))
    fallback = read(brief_path, 12000)
    title, body = post_body_from_payload(payload, fallback)
    images = payload.get("generated_images") or item.get("generated_images") or []
    if not isinstance(images, list):
        images = [str(images)]
    out = READY_DIR / f"{item['id']}.md"
    out.write_text(
        "\n".join([
            f"# {title}",
            "",
            body,
            "",
            "---",
            "",
            "## Publication Desk Notes",
            f"- Execution ID: `{item.get('id')}`",
            f"- Consent ID: `{item.get('source_id')}`",
            "- Destination: Patreon",
            "- Status: ready for manual Patreon draft or future verified adapter.",
            "",
            "## Image Assets",
            *(f"- {image}" for image in images),
        ]) + "\n",
        encoding="utf-8",
    )
    update_execution(item["id"], status="patreon_ready", patreon_ready_file=str(out), patreon_ready_at=now())
    row = {"kind": "patreon_ready", "execution_id": item["id"], "path": str(out), "title": title}
    append_jsonl(LEDGER, row)
    append_jsonl(LOG_DIR / "patreon-adapter.jsonl", row)
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description="Enchantify-local Patreon adapter")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--client-id", default="")
    init.add_argument("--client-secret", default="")
    init.add_argument("--campaign-url", default="https://www.patreon.com/c/thedoobaleedoos")
    sub.add_parser("status")
    sub.add_parser("refresh")
    au = sub.add_parser("auth-url")
    au.add_argument("--redirect-uri", default="")
    au.add_argument("--state", default="enchantify")
    auth = sub.add_parser("auth-server")
    auth.add_argument("--port", type=int, default=8765)
    ex_code = sub.add_parser("exchange-code")
    ex_code.add_argument("--code", required=True)
    ex_code.add_argument("--redirect-uri", default="")
    ex = sub.add_parser("export")
    ex.add_argument("execution_id")
    args = parser.parse_args()
    if args.command == "init":
        init_config(client_id=args.client_id, client_secret=args.client_secret, campaign_url=args.campaign_url)
        print(f"PATREON_CONFIG: {CONFIG}")
        print(f"PATREON_EXAMPLE: {CONFIG_EXAMPLE}")
        return 0
    if args.command == "status":
        result = status()
        print("PATREON_ADAPTER_STATUS:")
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        return 0 if result.get("connected") else 2
    if args.command == "refresh":
        result = refresh_token()
        print("PATREON_REFRESH:")
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        return 0 if result.get("ok") else 1
    if args.command == "auth-url":
        print(auth_url(args.redirect_uri or None, state=args.state))
        return 0
    if args.command == "auth-server":
        result = auth_server(args.port)
        print("PATREON_AUTH_SERVER:")
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        return 0 if result.get("ok") else 1
    if args.command == "exchange-code":
        result = exchange_code(args.code, args.redirect_uri or None)
        print("PATREON_EXCHANGE:")
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        return 0 if result.get("ok") else 1
    if args.command == "export":
        result = export(args.execution_id)
        print("PATREON_READY:")
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

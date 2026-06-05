#!/usr/bin/env python3
"""Cinematic Story-Field Journal — player-facing game interface (separate from Mission Control).

Serves a holographic folio UI on port 9192 by default. Mission Control (9191) is unchanged.

Usage:
  python3 scripts/story-field-journal.py --serve
  python3 scripts/story-field-journal.py --folio bj
  python3 scripts/story-field-journal.py --serve --open
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import mimetypes
import os
import re
import subprocess
import sys
import webbrowser
from datetime import date, datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

BASE = Path(__file__).resolve().parents[1]
SCRIPTS = BASE / "scripts"
HOOKS = BASE / "hooks"
STATIC = HOOKS / "story-field-journal"
PLAYERS = BASE / "players"
LORE = BASE / "lore"
REGISTER_F = LORE / "world-register.md"
PACKET_VERSION = "folio.cinematic.v0"
DEFAULT_PORT = 9192

PHASE_ALIASES = {
    "dormant": "dormant",
    "setup": "setup",
    "rising": "rising",
    "climax": "climax",
    "resolution": "resolution",
    "permanent": "permanent",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def safe_player(raw: str | None) -> str:
    value = re.sub(r"[^A-Za-z0-9_-]+", "", raw or "bj")
    return value or "bj"


def run_json(args: list[str], *, timeout: int = 60) -> dict[str, Any]:
    try:
        proc = subprocess.run(args, cwd=BASE, capture_output=True, text=True, timeout=timeout)
    except Exception:
        return {}
    if proc.returncode != 0:
        return {}
    try:
        data = json.loads(proc.stdout)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def load_mobile_gateway():
    path = SCRIPTS / "mobile-gateway.py"
    spec = importlib.util.spec_from_file_location("enchantify_mobile_gateway", path)
    if not spec or not spec.loader:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def thread_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (name or "").lower())


def canonical_phase(raw: str) -> str:
    raw = (raw or "").strip().lower()
    if not raw:
        return "dormant"
    first = raw.split()[0].rstrip(",")
    return PHASE_ALIASES.get(first, first if first in PHASE_ALIASES.values() else "dormant")


def parse_active_threads() -> list[dict[str, Any]]:
    if not REGISTER_F.exists():
        return []
    register = REGISTER_F.read_text(encoding="utf-8", errors="replace")
    active_m = re.search(r"(?m)^## Active Threads\s*\n(.*?)(?=^## |\Z)", register, re.DOTALL)
    if not active_m:
        return []
    threads: list[dict[str, Any]] = []
    for m in re.finditer(
        r"^\|\s*([^|]+?)\s*\|\s*Thread\s*\|\s*(\d+)\s*\|\s*([^|]*)\s*\|",
        active_m.group(1),
        re.MULTILINE | re.IGNORECASE,
    ):
        name = m.group(1).strip()
        if name.lower() in ("entity", "---", ""):
            continue
        notes = re.sub(r"\s+", " ", m.group(3).strip())
        phase = "dormant"
        status = notes
        pm = re.search(r"[Pp]hase:\s*([A-Za-z_-]+)(?:\s*[\-–—]\s*(.+))?", notes)
        if pm:
            phase = canonical_phase(pm.group(1))
            status = (pm.group(2) or "").strip() or notes
        threads.append(
            {
                "id": thread_key(name),
                "name": name,
                "belief": int(m.group(2)),
                "phase": phase,
                "status": status[:220],
            }
        )
    return sorted(threads, key=lambda t: (-t["belief"], t["name"].lower()))


def parse_player_card(player: str) -> dict[str, Any]:
    path = PLAYERS / f"{player}.md"
    if not path.exists():
        return {"player": player}
    text = path.read_text(encoding="utf-8", errors="replace")
    out: dict[str, Any] = {"player": player}

    for label, key in (
        (r"\*\*Belief:\*\*\s*(\d+)", "belief"),
        (r"\*\*Chapter:\*\*\s*(.+)", "chapter"),
        (r"\*\*Tutorial Progress:\*\*\s*(\S+)", "tutorial"),
    ):
        m = re.search(label, text)
        if m:
            out[key] = int(m.group(1)) if key == "belief" else m.group(1).strip()

    quests: list[dict[str, str]] = []
    cover = re.search(r"## The Inside Cover\s*\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    if cover:
        for row in re.finditer(
            r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]*)\s*\|",
            cover.group(1),
            re.MULTILINE,
        ):
            title = row.group(1).strip()
            if title.lower() in ("quest", "status", "---") or title.startswith("-"):
                continue
            quests.append(
                {
                    "title": title,
                    "status": row.group(2).strip(),
                    "note": row.group(3).strip()[:160],
                }
            )
    out["quests"] = quests[:8]
    return out


def load_field_graph_module():
    path = SCRIPTS / "field-graph.py"
    spec = importlib.util.spec_from_file_location("enchantify_field_graph", path)
    if not spec or not spec.loader:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def build_field_graph(player: str) -> dict[str, Any]:
    mod = load_field_graph_module()
    if mod and hasattr(mod, "build_field_graph"):
        return mod.build_field_graph(player)
    return {"error": "field-graph unavailable", "nodes": [], "links": []}


def build_folio(player: str) -> dict[str, Any]:
    gateway = load_mobile_gateway()
    mobile: dict[str, Any] = {}
    if gateway and hasattr(gateway, "build_state"):
        try:
            mobile = gateway.build_state(player)
        except Exception:
            mobile = {}

    scene_contract = run_json(
        [sys.executable, str(SCRIPTS / "scene-contract.py"), player, "--json"],
        timeout=90,
    )
    narrative = run_json(
        [sys.executable, str(SCRIPTS / "narrative-health.py"), player, "--json"],
        timeout=45,
    )

    return {
        "packet_version": PACKET_VERSION,
        "generated_at": utc_now(),
        "player": player,
        "surface": "Cinematic Folio",
        "mission_control_url": "http://127.0.0.1:9191/hooks/mission-control.html",
        "mobile": mobile,
        "player_card": parse_player_card(player),
        "threads": parse_active_threads(),
        "scene_contract": scene_contract,
        "narrative_health": narrative,
        "tabs": ["today", "compass", "enchantments", "library", "desk"],
    }


class FolioHandler(BaseHTTPRequestHandler):
    server_version = "EnchantifyCinematicFolio/0.1"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        player = safe_player((params.get("player") or ["bj"])[0])

        if parsed.path in ("/", "/index.html"):
            return self._serve_file(STATIC / "index.html", "text/html; charset=utf-8")
        if parsed.path in ("/field", "/field.html"):
            return self._serve_file(STATIC / "field.html", "text/html; charset=utf-8")
        if parsed.path == "/api/folio":
            return self.send_json(build_folio(player))
        if parsed.path == "/api/graph":
            return self.send_json(build_field_graph(player))
        if parsed.path == "/api/health":
            return self.send_json(
                {
                    "ok": True,
                    "packet_version": PACKET_VERSION,
                    "static_root": str(STATIC),
                    "generated_at": utc_now(),
                }
            )
        if parsed.path.startswith("/assets/"):
            rel = parsed.path[len("/assets/") :]
            target = (STATIC / rel).resolve()
            if not str(target).startswith(str(STATIC.resolve())):
                return self.send_error(HTTPStatus.FORBIDDEN)
            if target.is_file():
                ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
                return self._serve_file(target, ctype)
        if parsed.path == "/api/widget-image":
            for candidate in (
                HOOKS / "widget-image.png",
                BASE / "hooks" / "widget-image.png",
            ):
                if candidate.exists():
                    return self._serve_file(candidate, "image/png")
            return self.send_json({"error": "no_image"}, status=HTTPStatus.NOT_FOUND)
        if parsed.path == "/api/asset":
            rel = (params.get("path") or [""])[0]
            if not rel or ".." in rel:
                return self.send_error(HTTPStatus.BAD_REQUEST)
            target = (BASE / rel).resolve()
            if not str(target).startswith(str(BASE.resolve())) or not target.is_file():
                return self.send_error(HTTPStatus.NOT_FOUND)
            ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            return self._serve_file(target, ctype)
        return self.send_json({"error": "not_found", "path": parsed.path}, status=HTTPStatus.NOT_FOUND)

    def _serve_file(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[story-field-journal] {self.address_string()} - {fmt % args}")

    def send_json(self, payload: dict[str, Any], *, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> int:
    parser = argparse.ArgumentParser(description="Cinematic Story-Field Journal (player UI)")
    parser.add_argument("player", nargs="?", default="bj")
    parser.add_argument("--folio", action="store_true", help="Print folio JSON and exit")
    parser.add_argument("--serve", action="store_true", help=f"Serve UI at http://127.0.0.1:{DEFAULT_PORT}")
    parser.add_argument("--host", default=os.environ.get("ENCHANTIFY_FOLIO_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("ENCHANTIFY_FOLIO_PORT", str(DEFAULT_PORT))))
    parser.add_argument("--open", action="store_true", help="Open browser when serving")
    args = parser.parse_args()

    player = safe_player(args.player)
    if not STATIC.exists():
        print(f"Missing static UI at {STATIC}", file=sys.stderr)
        return 1

    if args.folio or not args.serve:
        print(json.dumps(build_folio(player), ensure_ascii=False, indent=2))
        return 0

    url = f"http://{args.host}:{args.port}/"
    httpd = ThreadingHTTPServer((args.host, args.port), FolioHandler)
    print(f"Cinematic Story-Field Journal → {url}")
    print(f"API: {url}api/folio?player={player}")
    print(f"Field graph: {url}field?player={player}")
    print("Mission Control (ops desk) remains at http://127.0.0.1:9191/")
    if args.open:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nCinematic folio stopped.")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

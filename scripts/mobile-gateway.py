#!/usr/bin/env python3
"""Small local HTTP gateway for the Enchantify mobile app.

The phone app should not call raw OpenClaw chat completions. This gateway owns
the Enchantify-facing packet shape and gives the app a stable API surface while
the deeper play routes are wired one at a time.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


BASE = Path(__file__).resolve().parents[1]
SCRIPTS = BASE / "scripts"
PLAYERS = BASE / "players"
TMP_SCENE = BASE / "tmp" / "scene-outbox" / "enchantify-scene-packet.json"
PENDING_CONSENTS = BASE / "logs" / "pending-consents.jsonl"
PACT_ACTIONS = BASE / "logs" / "pact-actions.jsonl"

PACKET_VERSION = "mobile.page-packet.v0"
MAX_TEXT_CHARS = 6000
MAX_PROMPT_CHARS = 1200


def safe_player(raw: str | None) -> str:
    value = re.sub(r"[^A-Za-z0-9_-]+", "", raw or "bj")
    return value or "bj"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(BASE))
    except ValueError:
        return str(path)


def read_text(path: Path, limit: int | None = None) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[:limit] if limit else text


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def read_jsonl_tail(path: Path, limit: int = 5) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[-max(limit * 3, limit):]:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows[-limit:]


def run_json(args: list[str], *, timeout: int = 45) -> dict[str, Any]:
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


def module_from(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def widget_state(player: str) -> dict[str, Any]:
    module = module_from(SCRIPTS / "widget-state.py", "enchantify_widget_state")
    if not module or not hasattr(module, "build_state"):
        return {}
    try:
        state = module.build_state(player)
        return state if isinstance(state, dict) else {}
    except Exception:
        return {}


def page_contract(player: str) -> dict[str, Any]:
    return run_json([sys.executable, str(SCRIPTS / "page-contract.py"), player, "--json"], timeout=60)


def current_scene() -> dict[str, Any]:
    packet = read_json(TMP_SCENE)
    if not packet:
        return {}
    text = ((packet.get("text") or {}).get("text") or "").strip()
    voice = ((packet.get("voice") or {}).get("text") or "").strip()
    metadata = packet.get("metadata") or {}
    image = packet.get("image") or {}
    audio = packet.get("audio") or {}
    return {
        "scene_id": packet.get("scene_id", ""),
        "title": packet.get("title", ""),
        "mood": packet.get("mood", ""),
        "intensity": packet.get("intensity", ""),
        "channel": packet.get("channel", ""),
        "text": truncate_text(text, MAX_TEXT_CHARS),
        "voice_text": truncate_text(voice, MAX_TEXT_CHARS),
        "choices": extract_choices(text),
        "image": normalize_artifact(image),
        "audio": normalize_artifact(audio),
        "updated_at": packet_mtime(TMP_SCENE),
        "location": ((metadata.get("scene_contract") or {}).get("current_location") or ""),
        "mode": ((metadata.get("scene_contract") or {}).get("scene_mode") or ""),
        "drama_budget": ((metadata.get("scene_contract") or {}).get("drama_budget") or ""),
    }


def truncate_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n\n[continued in full scene archive]"


def normalize_artifact(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    out = {k: v for k, v in value.items() if k in {"path", "url", "status", "caption", "prompt", "duration", "error"}}
    if isinstance(out.get("prompt"), str) and len(out["prompt"]) > MAX_PROMPT_CHARS:
        out["prompt"] = out["prompt"][:MAX_PROMPT_CHARS].rstrip() + "..."
    for key in ("path", "url"):
        if out.get(key):
            out[key] = str(out[key])
    return out


def packet_mtime(path: Path) -> str:
    if not path.exists():
        return ""
    return datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")


def extract_choices(text: str) -> list[dict[str, str]]:
    choices: list[dict[str, str]] = []
    for match in re.finditer(r"(?m)^\s*([123])\.\s*(?:\[(LIFE|ARC|SURPRISE)\]\s*)?(.+)$", text or ""):
        choices.append({
            "index": match.group(1),
            "kind": match.group(2) or "",
            "text": match.group(3).strip(),
        })
    return choices[-3:] if len(choices) > 3 else choices


def compact_row(row: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    return {key: row.get(key) for key in keys if row.get(key) not in (None, "")}


def compass_status(player: str) -> dict[str, Any]:
    path = PLAYERS / f"{player}-compass-run.json"
    state = read_json(path)
    if not state:
        return {"status": "idle"}
    keep = [
        "status", "date", "mood", "scale", "north_spark", "east_destination",
        "east_delight", "east_definition", "south_mission", "west_souvenir",
        "recipe_reason", "printed",
    ]
    out = compact_row(state, keep)
    out["updated_at"] = packet_mtime(path)
    return out


def book_jump_status(player: str) -> dict[str, Any]:
    path = PLAYERS / f"{player}-book-jump.json"
    state = read_json(path)
    if not state:
        return {"status": "idle"}
    keep = [
        "status", "title", "kind", "anchor", "intention", "guide", "depth",
        "degradation", "return_count", "nothing_pressure", "souvenir_due",
    ]
    out = compact_row(state, keep)
    out["updated_at"] = packet_mtime(path)
    return out


def support_summary(player: str) -> dict[str, Any]:
    inkrest = [compact_support_row(row) for row in read_jsonl_tail(PLAYERS / f"{player}-inkrest-log.jsonl", 5)]
    vellum = [compact_support_row(row) for row in read_jsonl_tail(PLAYERS / f"{player}-vellum-log.jsonl", 5)]
    ledger = [compact_support_row(row) for row in read_jsonl_tail(PLAYERS / f"{player}-ledger-log.jsonl", 5)]
    memory = read_json(PLAYERS / f"{player}-support-memory.json")
    return {
        "player": player,
        "inkrest": {
            "latest": inkrest[-1] if inkrest else {},
            "recent": inkrest,
        },
        "vellum": {
            "latest": vellum[-1] if vellum else {},
            "recent": vellum,
        },
        "gimble": {
            "latest": ledger[-1] if ledger else {},
            "recent": ledger,
        },
        "memory": {
            "latest_daily": (memory.get("daily") or [])[-1] if isinstance(memory.get("daily"), list) and memory.get("daily") else {},
            "watching": memory.get("watching", []) if isinstance(memory.get("watching"), list) else [],
            "experiments": memory.get("experiments", []) if isinstance(memory.get("experiments"), list) else [],
        },
    }


def compact_support_row(row: dict[str, Any]) -> dict[str, Any]:
    """Keep mobile support cards readable and avoid dumping provider payloads."""
    if not isinstance(row, dict):
        return {}
    compact = compact_row(row, [
        "timestamp", "date", "kind", "slot", "word", "context", "note",
        "message", "sent", "status", "owner", "experiment", "metric",
        "heartbeat_focus", "heartbeat_pacing", "steps", "fuel",
    ])
    actual = row.get("actual") if isinstance(row.get("actual"), dict) else row.get("summary")
    if isinstance(actual, dict):
        compact["actual"] = compact_actual_summary(actual)
    return trim_strings(compact)


def compact_actual_summary(actual: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": actual.get("generated_at"),
        "budget_month": actual.get("budget_month"),
        "accounts": [
            compact_row(account, ["name", "balance", "available", "offbudget"])
            for account in actual.get("accounts", [])[:6]
            if isinstance(account, dict)
        ],
        "month": compact_row(actual.get("month") or {}, [
            "income_available", "total_budgeted", "total_spent", "total_balance", "to_budget",
        ]),
        "transaction_window": compact_row(actual.get("transaction_window") or {}, ["start", "end", "count"]),
        "uncategorized_count": actual.get("uncategorized_count", 0),
        "recent": [
            compact_row(txn, ["date", "account", "payee", "category", "amount"])
            for txn in actual.get("recent", [])[:7]
            if isinstance(txn, dict)
        ],
    }


def trim_strings(value: Any, limit: int = 240) -> Any:
    if isinstance(value, str):
        return value if len(value) <= limit else value[:limit].rstrip() + "..."
    if isinstance(value, list):
        return [trim_strings(item, limit) for item in value]
    if isinstance(value, dict):
        return {key: trim_strings(item, limit) for key, item in value.items()}
    return value


def pending_actions() -> list[dict[str, Any]]:
    pending: list[dict[str, Any]] = []
    seen: set[str] = set()
    latest_consents: dict[str, dict[str, Any]] = {}
    for row in read_jsonl_tail(PENDING_CONSENTS, 40):
        ident = str(row.get("id") or "")
        if ident:
            latest_consents[ident] = row
    for row in latest_consents.values():
        if row.get("status") != "pending":
            continue
        ident = str(row.get("id") or "")
        if ident and ident in seen:
            continue
        if ident:
            seen.add(ident)
        pending.append(compact_row(row, ["id", "timestamp", "chapter", "app", "tier", "proposal", "telegram_sent"]))
    for row in read_jsonl_tail(PACT_ACTIONS, 8):
        if row.get("event") == "consent_required" and row.get("telegram_sent") is False:
            ident = str(row.get("consent_id") or row.get("id") or "")
            if ident and ident in seen:
                continue
            pending.append(compact_row(row, ["timestamp", "chapter", "app", "tier", "proposal", "result", "telegram_sent"]))
    return pending[-8:]


def margins(page: dict[str, Any], support: dict[str, Any], actions: list[dict[str, Any]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if page.get("page_label"):
        out.append({
            "kind": "page",
            "title": str(page.get("page_label")),
            "text": str(page.get("small_model_rule") or page.get("purpose") or ""),
        })
    obligations = ((page.get("state_hints") or {}).get("narrative_obligations") or [])
    for item in obligations[:2]:
        if isinstance(item, dict):
            out.append({
                "kind": "stewardship",
                "title": str(item.get("title") or "Narrative stewardship"),
                "text": str(item.get("scene_hook") or item.get("satisfy_by") or ""),
            })
    latest_mood = ((support.get("inkrest") or {}).get("latest") or {}).get("word")
    if latest_mood:
        out.append({"kind": "inkrest", "title": "Dr. Inkrest", "text": f"Latest inner weather: {latest_mood}."})
    if actions:
        out.append({"kind": "consent", "title": "Consent Needed", "text": f"{len(actions)} action(s) are waiting at the Desk."})
    return out[:6]


def build_state(player: str) -> dict[str, Any]:
    page = page_contract(player)
    widget = widget_state(player)
    scene = current_scene()
    support = support_summary(player)
    actions = pending_actions()
    state = {
        "packet_version": PACKET_VERSION,
        "generated_at": utc_now(),
        "player": player,
        "app": {
            "name": "Enchantify",
            "surface": "Story-Field Journal",
            "tabs": ["today", "compass", "enchantments", "library", "desk"],
        },
        "page": page,
        "today": {
            "title": widget.get("title") or page.get("page_label") or "Today’s Page",
            "day": widget.get("day", ""),
            "block": widget.get("block", ""),
            "now": widget.get("now", ""),
            "next": widget.get("next", ""),
            "practice": widget.get("practice", ""),
            "practice_prompt": widget.get("practicePrompt", ""),
            "note": widget.get("note", ""),
            "image": {"path": widget.get("image", ""), "has_embedded_data": bool(widget.get("imageData"))},
        },
        "scene": scene,
        "choices": scene.get("choices", []),
        "compass": compass_status(player),
        "enchantments": {
            "status": "available",
            "known_source": "lore/enchantments.md",
            "active": {},
        },
        "book_jump": book_jump_status(player),
        "library": {
            "story_threads_source": "lore/threads.md",
            "bleed_archive_source": "bleed/",
            "letters_source": "memory/npc-research/letters/",
            "souvenirs_source": "souvenirs/",
        },
        "desk": {
            "support": support,
            "pending_actions": actions,
        },
    }
    state["margins"] = margins(page, support, actions)
    return state


def build_health() -> dict[str, Any]:
    return {
        "packet_version": PACKET_VERSION,
        "generated_at": utc_now(),
        "gateway": {"ok": True, "script": rel(Path(__file__).resolve())},
        "files": {
            "heartbeat": file_status(BASE / "HEARTBEAT.md"),
            "scene_packet": file_status(TMP_SCENE),
            "mission_control": file_status(BASE / "hooks" / "mission-control.html"),
            "actual_budget_config": file_status(BASE / "config" / "actual-budget.json"),
        },
        "commands": {
            "openclaw": bool(shutil.which("openclaw")),
            "python": sys.executable,
        },
        "notes": [
            "POST play/compass/enchantment mutation routes are intentionally not wired yet.",
            "Use GET /api/state for the first read-only app shell.",
        ],
    }


def file_status(path: Path) -> dict[str, Any]:
    return {
        "exists": path.exists(),
        "path": rel(path),
        "mtime": packet_mtime(path),
        "size": path.stat().st_size if path.exists() else 0,
    }


def schema() -> dict[str, Any]:
    return {
        "packet_version": PACKET_VERSION,
        "routes": {
            "GET /api/state?player=bj": "Current mobile page packet for the Story-Field Journal app.",
            "GET /api/health": "Gateway and local dependency status for the Desk tab.",
            "GET /api/schema": "This schema.",
            "POST /api/play": "Planned: complete buffered active-play packet.",
            "POST /api/compass/start|answer|complete": "Planned: Compass Run wrappers.",
            "POST /api/enchantment/start|complete": "Planned: Enchantment wrappers.",
        },
        "top_level": [
            "packet_version", "generated_at", "player", "app", "page", "today",
            "scene", "choices", "compass", "enchantments", "book_jump", "library",
            "desk", "margins",
        ],
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "EnchantifyMobileGateway/0.1"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        player = safe_player((params.get("player") or ["bj"])[0])
        if parsed.path == "/api/state":
            self.send_json(build_state(player))
        elif parsed.path == "/api/health":
            self.send_json(build_health())
        elif parsed.path == "/api/schema":
            self.send_json(schema())
        else:
            self.send_json({"error": "not_found", "path": parsed.path}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        planned = {
            "/api/play",
            "/api/compass/start",
            "/api/compass/answer",
            "/api/compass/complete",
            "/api/enchantment/start",
            "/api/enchantment/complete",
        }
        if parsed.path in planned:
            self.send_json({
                "error": "not_implemented",
                "path": parsed.path,
                "message": "This route is reserved; read-only state is wired first.",
            }, status=HTTPStatus.NOT_IMPLEMENTED)
        else:
            self.send_json({"error": "not_found", "path": parsed.path}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[mobile-gateway] {self.address_string()} - {fmt % args}")

    def send_json(self, payload: dict[str, Any], *, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False, indent=2, default=str).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve Enchantify mobile app packets")
    parser.add_argument("--host", default=os.environ.get("ENCHANTIFY_MOBILE_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("ENCHANTIFY_MOBILE_PORT", "8765")))
    parser.add_argument("--state", action="store_true", help="Print one state packet and exit")
    parser.add_argument("--health", action="store_true", help="Print health packet and exit")
    parser.add_argument("--player", default="bj")
    args = parser.parse_args()

    player = safe_player(args.player)
    if args.state:
        print(json.dumps(build_state(player), ensure_ascii=False, indent=2, default=str))
        return 0
    if args.health:
        print(json.dumps(build_health(), ensure_ascii=False, indent=2, default=str))
        return 0

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Enchantify mobile gateway serving at http://{args.host}:{args.port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nEnchantify mobile gateway stopped.")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Canonical 'open the book' prep — lock, entry, preflight, story context, scene contract.

Usage:
  python3 scripts/open-book.py [player]
  python3 scripts/open-book.py bj --json

After this succeeds, the Labyrinth writes the opening scene to /tmp, then:
  Telegram: python3 scripts/run-live-scene.py [player] --text-file ... --voice-file ...
  Cursor/chat: python3 scripts/run-live-scene.py [player] --text-file ... --surface chat
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent
SCRIPTS = BASE / "scripts"
DEFAULT_TELEGRAM_TARGET = "8729557865"
DEFAULT_TELEGRAM_ACCOUNT = "enchantify"
OPENING_PING = (
    "The Book stirs—finding your place among the pages. "
    "Hold a moment; your scene is being written."
)


def run(cmd: list[str], *, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=BASE,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def parse_entry_mode(session_entry_text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in session_entry_text.splitlines():
        if line.startswith("ENTRY_MODE:"):
            out["entry_mode"] = line.split(":", 1)[1].strip()
        elif line.startswith("PAGE_TYPE:"):
            out["page_type"] = line.split(":", 1)[1].strip().split("(")[0].strip()
    return out


def recommended_scene_mode(entry: dict[str, str]) -> str:
    mode = entry.get("entry_mode", "")
    if mode == "in_media_res":
        return "slice"
    if mode.startswith("dorm_"):
        return "dorm"
    return "slice"


def notify_telegram_opening(
    target: str = DEFAULT_TELEGRAM_TARGET,
    account: str = DEFAULT_TELEGRAM_ACCOUNT,
) -> dict[str, Any]:
    proc = subprocess.run(
        [
            "openclaw",
            "message",
            "send",
            "--channel",
            "telegram",
            "--account",
            account,
            "--target",
            target,
            "--message",
            OPENING_PING,
        ],
        capture_output=True,
        text=True,
        timeout=90,
    )
    ok = proc.returncode == 0
    detail = (proc.stdout or proc.stderr or "").strip()
    return {"ok": ok, "detail": detail[:500]}


def open_book(
    player: str,
    *,
    notify_telegram: bool = False,
    telegram_target: str = DEFAULT_TELEGRAM_TARGET,
    telegram_account: str = DEFAULT_TELEGRAM_ACCOUNT,
) -> dict[str, Any]:
    result: dict[str, Any] = {"player": player, "ok": False, "steps": []}

    if notify_telegram:
        ping = notify_telegram_opening(telegram_target, telegram_account)
        result["steps"].append({"step": "telegram-ping", **ping})
        if not ping.get("ok"):
            result["telegram_ping_warning"] = ping.get("detail", "telegram ping failed")

    lock_path = BASE / "config" / "session-active.lock"
    if not lock_path.exists():
        proc = run([sys.executable, str(SCRIPTS / "set-lock.py")])
        result["steps"].append({"step": "set-lock", "ok": proc.returncode == 0})
        if proc.returncode != 0:
            result["error"] = "set-lock failed"
            return result
    else:
        result["steps"].append({"step": "set-lock", "ok": True, "skipped": "already locked"})

    entry = run([sys.executable, str(SCRIPTS / "session-entry.py"), player])
    result["steps"].append({"step": "session-entry", "ok": entry.returncode == 0})
    if entry.returncode != 0:
        result["error"] = (entry.stderr or entry.stdout or "session-entry failed")[:500]
        return result
    entry_text = entry.stdout or ""
    entry_info = parse_entry_mode(entry_text)
    scene_mode = recommended_scene_mode(entry_info)

    preflight = run([sys.executable, str(SCRIPTS / "mechanics-preflight.py"), player])
    result["steps"].append({"step": "mechanics-preflight", "ok": preflight.returncode == 0})
    if preflight.returncode != 0:
        result["error"] = (preflight.stderr or preflight.stdout or "mechanics-preflight failed")[:500]
        return result

    story = run([sys.executable, str(SCRIPTS / "story-context.py"), player])
    result["steps"].append({"step": "story-context", "ok": story.returncode == 0})

    contract = run(
        [
            sys.executable,
            str(SCRIPTS / "scene-contract.py"),
            player,
            "--mode",
            scene_mode,
        ]
    )
    result["steps"].append({"step": "scene-contract", "ok": contract.returncode == 0})
    if contract.returncode != 0:
        result["error"] = (contract.stderr or contract.stdout or "scene-contract failed")[:500]
        return result

    result.update(
        {
            "ok": True,
            "entry_mode": entry_info.get("entry_mode", ""),
            "scene_mode": scene_mode,
            "session_entry": entry_text,
            "story_context": story.stdout or "",
            "scene_contract": contract.stdout or "",
            "scene_files": {
                "scene": "/tmp/enchantify-scene.txt",
                "voice": "/tmp/enchantify-voice.txt",
            },
            "next_telegram": (
                f"python3 scripts/run-live-scene.py {player} "
                f"--text-file /tmp/enchantify-scene.txt --voice-file /tmp/enchantify-voice.txt "
                f"--scene-mode {scene_mode}"
            ),
            "next_chat": (
                f"python3 scripts/run-live-scene.py {player} "
                f"--text-file /tmp/enchantify-scene.txt --surface chat --scene-mode {scene_mode}"
            ),
        }
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare an Enchantify session open")
    parser.add_argument("player", nargs="?", default="bj")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--notify-telegram",
        action="store_true",
        help="Send an immediate in-world ping on Telegram while the opening scene is prepared",
    )
    parser.add_argument("--telegram-target", default=DEFAULT_TELEGRAM_TARGET)
    parser.add_argument("--telegram-account", default=DEFAULT_TELEGRAM_ACCOUNT)
    args = parser.parse_args()

    payload = open_book(
        args.player,
        notify_telegram=args.notify_telegram,
        telegram_target=args.telegram_target,
        telegram_account=args.telegram_account,
    )
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0 if payload.get("ok") else 1

    if not payload.get("ok"):
        print("OPEN_BOOK_FAILED")
        print(payload.get("error", "unknown error"))
        return 1

    print("OPEN_BOOK_READY")
    if args.notify_telegram:
        ping = next((s for s in payload.get("steps", []) if s.get("step") == "telegram-ping"), {})
        print(f"TELEGRAM_PING: {'sent' if ping.get('ok') else 'failed'}")
    print(f"PLAYER: {payload['player']}")
    print(f"ENTRY_MODE: {payload.get('entry_mode')}")
    print(f"SCENE_MODE: {payload.get('scene_mode')}")
    print("WRITE_SCENE_TO: /tmp/enchantify-scene.txt and /tmp/enchantify-voice.txt")
    print(f"THEN_TELEGRAM: {payload['next_telegram']}")
    print(f"THEN_CHAT: {payload['next_chat']}")
    print("--- SESSION ENTRY (excerpt) ---")
    excerpt = payload.get("session_entry", "")
    for line in excerpt.splitlines()[:25]:
        print(line)
    print("--- SCENE CONTRACT (excerpt) ---")
    for line in (payload.get("scene_contract") or "").splitlines()[:35]:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

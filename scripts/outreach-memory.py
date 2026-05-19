#!/usr/bin/env python3
"""Record character outreach and player replies as game memory.

This is deliberately small and deterministic. It does not call an LLM.
Outreach delivery records who reached out and what they said; a later Telegram
reply can be attached to the most recent pending outreach so active play can
fold that relationship beat back into scenes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

BASE = Path(__file__).resolve().parent.parent
LOG_PATH = BASE / "logs" / "character-outreach.jsonl"
PENDING_PATH = BASE / "players" / "bj-outreach-pending.json"
TICK_QUEUE = BASE / "memory" / "tick-queue.md"
DEFAULT_REPLY_WINDOW_HOURS = 72


def now() -> datetime:
    return datetime.now()


def clean(text: str, limit: int = 500) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def event_id(sender: str, message: str, timestamp: str) -> str:
    raw = f"{sender}\n{message}\n{timestamp}".encode("utf-8", errors="replace")
    return hashlib.sha1(raw).hexdigest()[:12]


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def load_pending() -> Optional[dict[str, Any]]:
    if not PENDING_PATH.exists():
        return None
    try:
        data = json.loads(PENDING_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict) or data.get("status") != "awaiting-reply":
        return None
    return data


def save_pending(data: dict[str, Any]) -> None:
    PENDING_PATH.parent.mkdir(parents=True, exist_ok=True)
    PENDING_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def pending_is_fresh(pending: dict[str, Any], hours: int = DEFAULT_REPLY_WINDOW_HOURS) -> bool:
    try:
        sent_at = datetime.fromisoformat(str(pending.get("sent_at", "")))
    except ValueError:
        return False
    return now() - sent_at <= timedelta(hours=hours)


def record_sent(args: argparse.Namespace) -> int:
    timestamp = now().isoformat(timespec="seconds")
    eid = event_id(args.sender, args.message, timestamp)
    row = {
        "id": eid,
        "kind": "sent",
        "timestamp": timestamp,
        "player": args.player,
        "sender": args.sender,
        "entity_type": args.entity_type,
        "belief": args.belief,
        "voice": args.voice,
        "message": clean(args.message, 900),
        "text_ok": args.text_ok,
        "voice_ok": args.voice_ok,
        "source": args.source,
    }
    append_jsonl(LOG_PATH, row)
    if args.text_ok or args.voice_ok:
        save_pending({
            "status": "awaiting-reply",
            "id": eid,
            "player": args.player,
            "sender": args.sender,
            "entity_type": args.entity_type,
            "belief": args.belief,
            "voice": args.voice,
            "message": clean(args.message, 900),
            "sent_at": timestamp,
            "source": args.source,
        })
    print(json.dumps({"recorded": True, "id": eid, "pending": bool(args.text_ok or args.voice_ok)}, indent=2))
    return 0


def append_tick_queue(sender: str, original: str, reply: str) -> None:
    TICK_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    line = (
        f"\n- [OUTREACH REPLY: {sender}] bj replied to the outreach: "
        f"\"{clean(reply, 180)}\". Original outreach: \"{clean(original, 220)}\". "
        "Fold this into relationship continuity when the sender or related thread appears.\n"
    )
    with TICK_QUEUE.open("a", encoding="utf-8") as f:
        f.write(line)


def record_reply_text(text: str, *, player: str = "bj", context: str = "telegram-reply", consume: bool = False) -> dict[str, Any]:
    pending = load_pending()
    if not pending:
        return {"recorded": False, "reason": "no pending outreach"}
    if not pending_is_fresh(pending):
        return {"recorded": False, "reason": "pending outreach expired", "sender": pending.get("sender")}

    timestamp = now().isoformat(timespec="seconds")
    row = {
        "id": pending.get("id"),
        "kind": "reply",
        "timestamp": timestamp,
        "player": player,
        "sender": pending.get("sender"),
        "entity_type": pending.get("entity_type"),
        "belief": pending.get("belief"),
        "original_message": pending.get("message"),
        "reply": clean(text, 900),
        "context": context,
    }
    append_jsonl(LOG_PATH, row)
    append_tick_queue(str(pending.get("sender") or "Unknown"), str(pending.get("message") or ""), text)
    pending["status"] = "replied"
    pending["reply"] = clean(text, 900)
    pending["replied_at"] = timestamp
    save_pending(pending)
    return {"recorded": True, "sender": pending.get("sender"), "id": pending.get("id"), "consume": consume}


def recent_events(limit: int = 6) -> list[dict[str, Any]]:
    if not LOG_PATH.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        rows.append(row)
    return rows[-limit:]


def main() -> int:
    parser = argparse.ArgumentParser(description="Record Enchantify character outreach and replies.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sent = sub.add_parser("record-sent")
    sent.add_argument("--player", default="bj")
    sent.add_argument("--sender", required=True)
    sent.add_argument("--entity-type", default="")
    sent.add_argument("--belief", type=int, default=0)
    sent.add_argument("--voice", default="")
    sent.add_argument("--message", required=True)
    sent.add_argument("--text-ok", action="store_true")
    sent.add_argument("--voice-ok", action="store_true")
    sent.add_argument("--source", default="reach-out")

    reply = sub.add_parser("record-reply")
    reply.add_argument("text")
    reply.add_argument("--player", default="bj")
    reply.add_argument("--context", default="telegram-reply")
    reply.add_argument("--consume", action="store_true")

    route = sub.add_parser("route")
    route.add_argument("text")
    route.add_argument("--player", default="bj")
    route.add_argument("--context", default="telegram-reply")
    route.add_argument("--consume", action="store_true")

    recent = sub.add_parser("recent")
    recent.add_argument("--limit", type=int, default=6)
    recent.add_argument("--json", action="store_true")

    args = parser.parse_args()
    if args.cmd == "record-sent":
        return record_sent(args)
    if args.cmd in ("record-reply", "route"):
        result = record_reply_text(args.text, player=args.player, context=args.context, consume=args.consume)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if args.cmd == "route" or result.get("recorded") else 1
    if args.cmd == "recent":
        events = recent_events(args.limit)
        if args.json:
            print(json.dumps(events, indent=2, ensure_ascii=False))
        else:
            for event in events:
                if event.get("kind") == "reply":
                    print(f"reply to {event.get('sender')}: {clean(event.get('reply', ''), 180)}")
                else:
                    print(f"sent from {event.get('sender')}: {clean(event.get('message', ''), 180)}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

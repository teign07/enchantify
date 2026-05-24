#!/usr/bin/env python3
"""In-game consent desk for Penny drafts and talisman content requests."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent
PENNY_QUEUE = BASE / "memory" / "publishing" / "consent-queue.json"
SOCIAL_LEDGER = BASE / "memory" / "publishing" / "social-ledger.jsonl"
EXECUTION_QUEUE = BASE / "memory" / "publishing" / "execution-queue.json"
PENDING_CONSENTS = BASE / "logs" / "pending-consents.jsonl"
PACT_ACTIONS = BASE / "logs" / "pact-actions.jsonl"

PENNY_PENDING = {"needs_review", "drafted", "awaiting_consent", "consent_required"}
PACT_PENDING = {"pending"}


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def clean(value: Any, limit: int = 260) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[: limit - 1].rstrip() + "…" if len(text) > limit else text


def read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        return data if isinstance(data, dict) else default
    except Exception:
        return default


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    row.setdefault("timestamp", now())
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def load_publication_desk():
    spec = importlib.util.spec_from_file_location("publication_desk", BASE / "scripts" / "publication-desk.py")
    if not spec or not spec.loader:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            data = json.loads(line)
        except Exception:
            continue
        if isinstance(data, dict):
            rows.append(data)
    return rows


def penny_items() -> list[dict[str, Any]]:
    data = read_json(PENNY_QUEUE, {"version": 1, "items": []})
    items = data.get("items", [])
    return items if isinstance(items, list) else []


def pact_latest() -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(PENDING_CONSENTS):
        ident = str(row.get("id") or "")
        if ident:
            latest[ident] = row
    return latest


def open_items() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in penny_items():
        if str(item.get("status") or "") in PENNY_PENDING or item.get("consent_required") and str(item.get("status") or "") not in {"approved", "rejected", "revise_requested", "published"}:
            out.append({**item, "source": "penny"})
    for item in pact_latest().values():
        if str(item.get("status") or "pending") in PACT_PENDING:
            out.append({**item, "source": "talisman"})
    return out


def find_item(item_id: str) -> tuple[str, dict[str, Any] | None]:
    item_id = item_id.strip()
    for item in penny_items():
        if str(item.get("id") or "") == item_id:
            return "penny", item
    for ident, item in pact_latest().items():
        if ident == item_id:
            return "talisman", item
    return "", None


def summarize_item(item: dict[str, Any]) -> str:
    if item.get("source") == "penny":
        return f"{item.get('id')} — Penny: {item.get('platform')} / {item.get('content_kind')}: {item.get('title')} [{item.get('privacy')}]"
    return f"{item.get('id')} — {item.get('chapter')} → {item.get('app')} ({item.get('tier')}): {clean(item.get('proposal'), 140)}"


def list_text() -> str:
    items = open_items()
    if not items:
        return "CONSENT_DESK: clear\nMESSAGE: The Consent Desk is clear. Nothing is waiting for your yes or no."
    lines = ["CONSENT_DESK: pending", "MESSAGE: The Consent Desk has these items waiting:"]
    for item in items[-10:]:
        lines.append(f"- {summarize_item(item)}")
    lines.append("Say approve/decline/revise plus the ID.")
    return "\n".join(lines)


def update_penny(item_id: str, status: str, note: str) -> dict[str, Any] | None:
    data = read_json(PENNY_QUEUE, {"version": 1, "items": []})
    found = None
    for item in data.get("items", []):
        if str(item.get("id") or "") == item_id:
            item["status"] = status
            item[f"{status}_at"] = now()
            if note:
                item["note"] = note
            found = item
            break
    if not found:
        return None
    save_json(PENNY_QUEUE, data)
    append_jsonl(SOCIAL_LEDGER, {**found, "ledger_event": status})
    return found


def update_talisman(item: dict[str, Any], status: str, note: str) -> dict[str, Any]:
    updated = dict(item)
    updated["status"] = status
    updated[f"{status}_at"] = now()
    if note:
        updated["note"] = note
    append_jsonl(PENDING_CONSENTS, updated)
    append_jsonl(PACT_ACTIONS, {
        "event": f"consent_{status}",
        "consent_id": updated.get("id"),
        "chapter": updated.get("chapter"),
        "app": updated.get("app"),
        "tier": updated.get("tier"),
        "proposal": updated.get("proposal"),
        "content_file": updated.get("content_file", ""),
        "note": note,
        "result": "Consent recorded. No public post or external message was executed by consent-desk.",
    })
    return updated


def decide(item_id: str, status: str, note: str = "") -> str:
    source, item = find_item(item_id)
    if not item:
        return f"CONSENT_DESK: not_found\nMESSAGE: I could not find consent item `{item_id}`."
    if source == "penny":
        updated = update_penny(item_id, status, note)
        if not updated:
            return f"CONSENT_DESK: not_found\nMESSAGE: I could not update Penny item `{item_id}`."
        verb = {"approved": "approved", "rejected": "declined", "revise_requested": "sent back for revision"}[status]
        execution_note = ""
        if status == "approved":
            try:
                desk = load_publication_desk()
                if desk:
                    desk.ensure_dirs()
                    queued = desk.queue_item_from_consent(updated, destination="telegram-review")
                    execution_note = f" Madame Redwax queued it for Telegram review as `{queued.get('id')}`."
            except Exception as exc:
                execution_note = f" Publication Desk queueing failed: {clean(exc, 180)}."
        return (
            f"CONSENT_DESK: {status}\n"
            f"MESSAGE: Penny's draft `{item_id}` is {verb}. "
            "Nothing was posted automatically; it is now marked in her publishing ledger."
            f"{execution_note}"
        )
    updated = update_talisman(item, status, note)
    verb = {"approved": "approved", "rejected": "declined", "revise_requested": "held for revision"}[status]
    return (
        f"CONSENT_DESK: {status}\n"
        f"MESSAGE: Talisman request `{updated.get('id')}` is {verb}. "
        "The Desk recorded your decision. Nothing was posted or externally sent automatically."
    )


def parse_route(message: str) -> tuple[str, str, str]:
    text = message.strip()
    low = text.lower()
    if re.search(r"\b(consent|approval|approve|decline|reject|revise|penny draft|talisman request)\b", low) and re.search(r"\b(show|list|what|queue|waiting|pending)\b", low):
        return "list", "", ""
    id_match = re.search(r"\b((?:penny|press-abundance)-[a-z0-9-]+|[a-f0-9]{10})\b", text, re.IGNORECASE)
    ident = id_match.group(1) if id_match else ""
    note = ""
    note_match = re.search(r"\b(?:note|because|with note|revise(?: it)? to)\b[:\s-]*(.+)$", text, re.IGNORECASE)
    if note_match:
        note = note_match.group(1).strip()
    if re.search(r"\b(approve|approved|yes|consent|allow|clear it|send it)\b", low) and ident:
        return "approved", ident, note
    if re.search(r"\b(decline|declined|reject|rejected|no|deny|do not|don't)\b", low) and ident:
        return "rejected", ident, note
    if re.search(r"\b(revise|revision|change|rewrite|needs work)\b", low) and ident:
        return "revise_requested", ident, note
    implied = "__latest__" if re.search(r"\b(latest|last|that|this one|current)\b", low) else ""
    if implied and re.search(r"\b(approve|approved|yes|consent|allow|clear it|send it)\b", low):
        return "approved", implied, note
    if implied and re.search(r"\b(decline|declined|reject|rejected|no|deny|do not|don't)\b", low):
        return "rejected", implied, note
    if implied and re.search(r"\b(revise|revision|change|rewrite|needs work)\b", low):
        return "revise_requested", implied, note
    return "", "", ""


def route(message: str) -> int:
    action, ident, note = parse_route(message)
    if action == "list":
        print("CONSENT_ROUTE: handled")
        print(list_text())
        return 0
    if action in {"approved", "rejected", "revise_requested"} and ident:
        if ident == "__latest__":
            items = open_items()
            if not items:
                print("CONSENT_ROUTE: handled")
                print("CONSENT_DESK: clear\nMESSAGE: The Consent Desk is clear. Nothing is waiting for that decision.")
                return 0
            ident = str(items[-1].get("id") or "")
        print("CONSENT_ROUTE: handled")
        print(decide(ident, action, note))
        return 0
    print("CONSENT_ROUTE: pass")
    return 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Consent Desk for in-game approvals")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    route_p = sub.add_parser("route")
    route_p.add_argument("message")
    for name, status in [("approve", "approved"), ("decline", "rejected"), ("reject", "rejected"), ("revise", "revise_requested")]:
        p = sub.add_parser(name)
        p.add_argument("item_id")
        p.add_argument("--note", default="")
        p.set_defaults(status=status)
    args = parser.parse_args()
    if args.command == "list":
        print(list_text())
        return 0
    if args.command == "route":
        return route(args.message)
    if hasattr(args, "status"):
        print(decide(args.item_id, args.status, args.note))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

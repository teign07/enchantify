#!/usr/bin/env python3
"""Publication / Execution Desk for approved Enchantify content.

The Desk may package approved drafts for BJ's review and may later publish
through platform adapters. It never acts on unapproved items.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent
PUBLISHING = BASE / "memory" / "publishing"
CONSENT_QUEUE = PUBLISHING / "consent-queue.json"
EXECUTION_QUEUE = PUBLISHING / "execution-queue.json"
PUBLICATION_LEDGER = PUBLISHING / "publication-ledger.jsonl"
PACT_DIR = PUBLISHING / "pacts"
REVIEW_DIR = PUBLISHING / "publication-desk"
LOG_DIR = BASE / "logs" / "publishing"
TARGET = "8729557865"
CHANNEL = "telegram"
ACCOUNT = "enchantify"


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def clean(value: Any, limit: int = 700) -> str:
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


def ensure_dirs() -> None:
    for path in (PUBLISHING, PACT_DIR, REVIEW_DIR, LOG_DIR):
        path.mkdir(parents=True, exist_ok=True)
    if not EXECUTION_QUEUE.exists():
        save_json(EXECUTION_QUEUE, {"version": 1, "items": []})
    patreon = PACT_DIR / "patreon.md"
    if not patreon.exists():
        patreon.write_text(
            "# Pact: Patreon\n\n"
            "## May\n"
            "- Package approved Penny/Goldweaver content for Patreon review.\n"
            "- Save Patreon-ready drafts and assets.\n"
            "- Record final published URLs when BJ supplies them.\n\n"
            "## Must Ask Before\n"
            "- Posting, scheduling, editing, deleting, or charging anything.\n"
            "- Using private health, therapy, ledger, family, relationship, or exact-place details.\n\n"
            "## Must Never\n"
            "- Publish unapproved content.\n"
            "- Pretend a draft was posted.\n"
            "- Monetize guilt, scarcity, shame, or surveillance.\n\n"
            "## Current Adapter\n"
            "Telegram review/export only. Direct Patreon API posting is not enabled yet.\n",
            encoding="utf-8",
        )
    youtube = PACT_DIR / "youtube.md"
    if not youtube.exists():
        youtube.write_text(
            "# Pact: YouTube\n\n"
            "## May\n"
            "- Package approved Penny/Goldweaver YouTube Shorts and long-form drafts for review.\n"
            "- Save titles, descriptions, thumbnail concepts, chapters, tags, and upload checklists.\n"
            "- Read public channel stats and recent videos through the local YouTube adapter when configured.\n\n"
            "## Must Ask Before\n"
            "- Uploading, scheduling, editing, deleting, changing visibility, or replying publicly.\n"
            "- Using private health, therapy, ledger, family, relationship, or exact-place details.\n\n"
            "## Must Never\n"
            "- Publish unapproved video content.\n"
            "- Pretend a draft was uploaded.\n"
            "- Chase metrics by flattening the Wonder Compass or Enchantify voice.\n\n"
            "## Current Adapter\n"
            "Read-only channel stats and recent videos via `scripts/youtube-adapter.py`. Public uploading is manual.\n",
            encoding="utf-8",
        )
    x_pact = PACT_DIR / "x.md"
    if not x_pact.exists():
        x_pact.write_text(
            "# Pact: X\n\n"
            "## May\n"
            "- Package approved Penny/Goldweaver X posts and threads for review.\n"
            "- Save post text, thread structure, alt text, image notes, and manual posting checklist.\n"
            "- Read account status and public search only through the official X API when configured.\n\n"
            "## Must Ask Before\n"
            "- Posting, scheduling, replying, liking, reposting, deleting, or changing account/app permissions.\n"
            "- Using private health, therapy, ledger, family, relationship, or exact-place details.\n\n"
            "## Must Never\n"
            "- Publish unapproved content.\n"
            "- Pretend a draft was posted.\n"
            "- Use browser cookie scraping or unofficial internal X endpoints.\n"
            "- Chase engagement by flattening the Academy voice.\n\n"
            "## Current Adapter\n"
            "Official API OAuth scaffold via `scripts/x-adapter.py`. Public posting remains manual unless a later explicit consent-gated adapter is enabled.\n",
            encoding="utf-8",
        )
    bluesky_pact = PACT_DIR / "bluesky.md"
    if not bluesky_pact.exists():
        bluesky_pact.write_text(
            "# Pact: Bluesky\n\n"
            "## May\n"
            "- Package approved Penny/Goldweaver Bluesky posts and threads for review.\n"
            "- Save post text, thread structure, alt text, image notes, and manual posting checklist.\n"
            "- Read account status and recent posts through the official AT Protocol API when configured.\n\n"
            "## Must Ask Before\n"
            "- Posting, scheduling, replying, liking, reposting, deleting, or changing account/app permissions.\n"
            "- Using private health, therapy, ledger, family, relationship, or exact-place details.\n\n"
            "## Must Never\n"
            "- Publish unapproved content.\n"
            "- Pretend a draft was posted.\n"
            "- Use browser cookie scraping or unofficial Bluesky endpoints.\n"
            "- Chase engagement by flattening the Academy voice.\n\n"
            "## Current Adapter\n"
            "Official AT Protocol adapter via `scripts/bluesky-adapter.py`. Public posting remains consent-gated.\n",
            encoding="utf-8",
        )


def consent_items() -> list[dict[str, Any]]:
    data = load_json(CONSENT_QUEUE, {"version": 1, "items": []})
    items = data.get("items")
    return items if isinstance(items, list) else []


def execution_data() -> dict[str, Any]:
    data = load_json(EXECUTION_QUEUE, {"version": 1, "items": []})
    if not isinstance(data.get("items"), list):
        data["items"] = []
    return data


def approved_item(item_id: str) -> dict[str, Any] | None:
    if item_id == "latest":
        approved = [item for item in consent_items() if str(item.get("status")) == "approved"]
        return approved[-1] if approved else None
    for item in consent_items():
        if str(item.get("id")) == item_id and str(item.get("status")) == "approved":
            return item
    return None


def queue_item_from_consent(item: dict[str, Any], *, destination: str = "telegram-review") -> dict[str, Any]:
    queue = execution_data()
    existing = [
        row for row in queue.get("items", [])
        if row.get("source_id") == item.get("id") and row.get("destination") == destination and row.get("status") not in {"done", "cancelled"}
    ]
    if existing:
        return existing[-1]
    ident = f"exec-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{len(queue.get('items', [])) + 1:03d}"
    row = {
        "id": ident,
        "source": "penny-consent",
        "source_id": item.get("id"),
        "created_at": now(),
        "destination": destination,
        "platform": item.get("platform"),
        "content_kind": item.get("content_kind"),
        "title": item.get("title"),
        "topic": item.get("topic"),
        "status": "queued",
        "approved_at": item.get("approved_at"),
        "brief": item.get("brief"),
        "structured": item.get("structured"),
        "review_pdf": "",
        "published_url": "",
        "notes": "Telegram review/export first. Public posting requires a platform adapter and a second explicit execute command.",
    }
    queue.setdefault("items", []).append(row)
    save_json(EXECUTION_QUEUE, queue)
    append_jsonl(PUBLICATION_LEDGER, {**row, "ledger_event": "queued"})
    return row


def list_text() -> str:
    ensure_dirs()
    queue = execution_data().get("items", [])
    active = [item for item in queue if item.get("status") in {"queued", "review_sent", "ready"}]
    if not active:
        return "PUBLICATION_DESK: clear\nMESSAGE: Madame Redwax has no approved items waiting at the Publication Desk."
    lines = ["PUBLICATION_DESK: pending", "MESSAGE: Madame Redwax has these approved items waiting:"]
    for item in active[-10:]:
        lines.append(f"- {item.get('id')} — {item.get('destination')} / {item.get('content_kind')}: {item.get('title')} [{item.get('status')}]")
    return "\n".join(lines)


def brief_markdown(item: dict[str, Any]) -> str:
    brief = Path(str(item.get("brief") or ""))
    structured = Path(str(item.get("structured") or ""))
    text = read(brief, 16000) if brief.exists() else ""
    data = load_json(structured, {}) if structured.exists() else {}
    return "\n".join([
        f"# Publication Desk Review — {item.get('title') or item.get('content_kind')}",
        "",
        "## Desk Seal",
        "This item has player approval. It has not been published. The Publication Desk is packaging it for review.",
        "",
        f"- Execution ID: `{item.get('id')}`",
        f"- Consent ID: `{item.get('source_id')}`",
        f"- Destination: `{item.get('destination')}`",
        f"- Platform: `{item.get('platform')}`",
        f"- Content kind: `{item.get('content_kind')}`",
        "",
        "## Approved Draft",
        text or "_No brief text found._",
        "",
        "## Structured Payload",
        "```json",
        json.dumps(data.get("brief", data), indent=2, ensure_ascii=False, default=str)[:9000],
        "```",
        "",
        "## Posting Rule",
        "Review/export is allowed. Public posting still requires a platform adapter and explicit execute command.",
    ])


def render_review_pdf(item: dict[str, Any], *, dry_run: bool = False) -> dict[str, str]:
    import sys

    sys.path.insert(0, str(BASE / "scripts"))
    import journal_artifact  # type: ignore

    markdown = brief_markdown(item)
    return journal_artifact.render(
        markdown,
        REVIEW_DIR,
        item["id"],
        title="Publication Desk Review",
        subtitle=f"{item.get('content_kind')} · {item.get('destination')}",
        footer="Sealed by Madame Redwax, Clerk of Public Seals",
        accent="#7b2f2f",
        dry_run=dry_run,
        image_required=False,
    )


def load_patreon_adapter():
    spec = importlib.util.spec_from_file_location("patreon_adapter", BASE / "scripts" / "patreon-adapter.py")
    if not spec or not spec.loader:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def telegram_send(message: str, media: Path | None = None, *, dry_run: bool = False) -> int:
    if dry_run:
        print(message)
        if media:
            print(f"[dry-run media] {media}")
        return 0
    args = [
        "openclaw", "message", "send",
        "--target", TARGET,
        "--channel", CHANNEL,
        "--account", ACCOUNT,
        "--message", message,
    ]
    if media:
        args += ["--media", str(media), "--force-document"]
    proc = subprocess.run(args, cwd=BASE, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        append_jsonl(LOG_DIR / "publication-desk-errors.jsonl", {
            "kind": "telegram_send_error",
            "stderr": clean(proc.stderr or proc.stdout, 2000),
            "media": str(media) if media else "",
        })
    return proc.returncode


def update_execution(item_id: str, **updates: Any) -> dict[str, Any] | None:
    data = execution_data()
    found = None
    for item in data.get("items", []):
        if item.get("id") == item_id:
            item.update(updates)
            found = item
            break
    if found:
        save_json(EXECUTION_QUEUE, data)
    return found


def enqueue(item_id: str, *, destination: str) -> int:
    ensure_dirs()
    item = approved_item(item_id)
    if not item:
        print(f"PUBLICATION_DESK: not_approved\nMESSAGE: I could not find an approved consent item `{item_id}`.")
        return 1
    queued = queue_item_from_consent(item, destination=destination)
    print(f"PUBLICATION_DESK: queued\nMESSAGE: `{queued['id']}` is queued for {destination}.")
    print(f"EXECUTION_ID: {queued['id']}")
    return 0


def execute(item_id: str, *, dry_run: bool = False) -> int:
    ensure_dirs()
    data = execution_data()
    items = data.get("items", [])
    item = None
    if item_id == "latest":
        active = [row for row in items if row.get("status") in {"queued", "ready"}]
        item = active[-1] if active else None
    else:
        item = next((row for row in items if row.get("id") == item_id), None)
    if not item:
        print(f"PUBLICATION_DESK: not_found\nMESSAGE: I could not find execution item `{item_id}`.")
        return 1
    if item.get("destination") == "patreon":
        adapter = load_patreon_adapter()
        if not adapter:
            print("PUBLICATION_DESK: adapter_missing\nMESSAGE: Patreon adapter could not be loaded.")
            return 2
        if dry_run:
            print(f"PUBLICATION_DESK: dry_run\nMESSAGE: Would export `{item.get('id')}` to a Patreon-ready draft and send a Telegram review packet.")
            return 0
        ready = adapter.export(str(item["id"]))
        artifact = render_review_pdf({**item, "destination": "patreon", "patreon_ready_file": ready.get("path", "")}, dry_run=False)
        media = Path(artifact["pdf"]) if artifact.get("pdf") else Path(str(ready.get("path", "")))
        status = adapter.status()
        diagnosis = status.get("diagnosis") or "Patreon status unavailable."
        message = (
            "Madame Redwax prepared a Patreon-ready publication packet.\n\n"
            f"Execution: {item.get('id')}\n"
            f"Draft file: {Path(str(ready.get('path', ''))).name}\n"
            f"Patreon status: {diagnosis}\n\n"
            "Nothing has been posted. Full PDF attached for review/export."
        )
        rc = telegram_send(message, media if media.exists() else Path(str(ready.get("path", ""))), dry_run=False)
        updated = update_execution(item["id"], status="patreon_ready_sent" if rc == 0 else "patreon_ready", review_pdf=str(media), patreon_ready_file=ready.get("path", ""), patreon_status=diagnosis)
        append_jsonl(PUBLICATION_LEDGER, {**(updated or item), "ledger_event": "patreon_ready_sent" if rc == 0 else "patreon_ready"})
        return rc
    if item.get("destination") != "telegram-review":
        print(
            "PUBLICATION_DESK: adapter_missing\n"
            f"MESSAGE: `{item.get('destination')}` is not wired for direct posting yet. "
            "Use telegram-review until the platform pact and adapter are enabled."
        )
        return 2
    artifact = render_review_pdf(item, dry_run=dry_run)
    media = Path(artifact["pdf"]) if artifact.get("pdf") else Path(str(item.get("brief") or ""))
    message = (
        "Madame Redwax has sealed an approved publication review packet.\n\n"
        f"Execution: {item.get('id')}\n"
        f"Content: {item.get('title')}\n"
        "Nothing has been posted. Full PDF attached for review."
    )
    rc = telegram_send(message, media if media.exists() else None, dry_run=dry_run)
    if rc == 0 and not dry_run:
        updated = update_execution(item["id"], status="review_sent", review_pdf=str(media), review_sent_at=now())
        append_jsonl(PUBLICATION_LEDGER, {**(updated or item), "ledger_event": "review_sent"})
    return rc


def mark_published(item_id: str, url: str, note: str = "") -> int:
    ensure_dirs()
    item = update_execution(item_id, status="done", published_url=url, published_at=now(), note=note)
    if not item:
        print(f"PUBLICATION_DESK: not_found\nMESSAGE: I could not find execution item `{item_id}`.")
        return 1
    append_jsonl(PUBLICATION_LEDGER, {**item, "ledger_event": "published"})
    print(f"PUBLICATION_DESK: published\nMESSAGE: `{item_id}` is marked published: {url}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Consent-locked Publication Desk")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("list")
    q = sub.add_parser("enqueue")
    q.add_argument("item_id", help="approved consent id, or latest")
    q.add_argument("--destination", default="telegram-review", choices=["telegram-review", "patreon", "x", "bluesky"])
    ex = sub.add_parser("execute")
    ex.add_argument("item_id", help="execution id, or latest")
    ex.add_argument("--dry-run", action="store_true")
    mp = sub.add_parser("mark-published")
    mp.add_argument("item_id")
    mp.add_argument("--url", required=True)
    mp.add_argument("--note", default="")
    args = parser.parse_args()
    if args.command == "init":
        ensure_dirs()
        print(f"PUBLICATION_DESK: {PUBLISHING}")
        return 0
    if args.command == "list":
        print(list_text())
        return 0
    if args.command == "enqueue":
        return enqueue(args.item_id, destination=args.destination)
    if args.command == "execute":
        return execute(args.item_id, dry_run=args.dry_run)
    if args.command == "mark-published":
        return mark_published(args.item_id, args.url, args.note)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

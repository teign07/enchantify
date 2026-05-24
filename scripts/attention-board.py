#!/usr/bin/env python3
"""
attention-board.py — gather Enchantify items that need BJ's attention.

This script writes memory/attention-board.json for Mission Control. It is
intentionally non-authoritative: source systems still own their state; this is a
desk view that gathers open doors in one place.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent
MEMORY = BASE / "memory"
PLAYERS = BASE / "players"
LOGS = BASE / "logs"
OUT = MEMORY / "attention-board.json"

PENDING_STATUSES = {
    "pending",
    "needs_review",
    "needs_revision",
    "drafted",
    "draft",
    "queued",
    "awaiting_consent",
    "consent_required",
    "ready_for_review",
}


def now() -> datetime:
    return datetime.now()


def read(path: Path, limit: int | None = None) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[:limit] if limit else text


def read_json(path: Path) -> Any:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return {}


def clean(text: Any, limit: int = 220) -> str:
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    return value[: limit - 1].rstrip() + "…" if len(value) > limit else value


def mtime_label(path: Path) -> str:
    if not path.exists():
        return ""
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")


def age_hours(path: Path) -> float | None:
    if not path.exists():
        return None
    return (now() - datetime.fromtimestamp(path.stat().st_mtime)).total_seconds() / 3600


def card(
    column: str,
    title: str,
    text: str,
    *,
    source: str,
    priority: str = "normal",
    owner: str = "",
    action: str = "",
    path: str = "",
    due: str = "",
    card_id: str = "",
) -> dict[str, str]:
    return {
        "id": card_id or re.sub(r"[^a-z0-9]+", "-", f"{source}-{title}".lower()).strip("-")[:80],
        "column": column,
        "title": clean(title, 120),
        "text": clean(text, 420),
        "source": source,
        "priority": priority,
        "owner": owner,
        "action": clean(action, 160),
        "path": path,
        "due": due,
    }


def latest_md_files(path: Path, limit: int = 4) -> list[Path]:
    if not path.exists():
        return []
    return sorted(path.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]


def title_from_md(path: Path) -> str:
    text = read(path, 1200)
    m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    return clean(m.group(1), 120) if m else path.stem


def collect_consent() -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    queue = read_json(MEMORY / "publishing" / "consent-queue.json")
    items = queue.get("items", []) if isinstance(queue, dict) else []
    for item in items:
        status = str(item.get("status") or "pending")
        if status not in PENDING_STATUSES and not item.get("consent_required"):
            continue
        title = item.get("title") or item.get("topic") or item.get("platform") or "Content awaiting review"
        platform = item.get("platform") or item.get("content_kind") or "content"
        text = item.get("topic") or item.get("posting_notes") or item.get("cta") or "Penny has a draft that needs a yes, no, or revision note."
        out.append(card(
            "needs_consent",
            f"{platform}: {title}",
            text,
            source="Penny / Goldweaver consent queue",
            priority="high",
            owner="Penny Blackletter",
            action="Review, approve, reject, or ask Penny to revise.",
            path=item.get("pdf") or item.get("brief") or item.get("structured") or "",
            due=item.get("date", ""),
            card_id=str(item.get("id") or ""),
        ))
    return out


def collect_pact_consent() -> list[dict[str, str]]:
    path = LOGS / "pact-actions.jsonl"
    if not path.exists():
        return []
    pending_status: dict[str, str] = {}
    pending_path = LOGS / "pending-consents.jsonl"
    if pending_path.exists():
        for line in pending_path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                row = json.loads(line)
            except Exception:
                continue
            ident = str(row.get("id") or "")
            if ident:
                pending_status[ident] = str(row.get("status") or "pending")
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[-120:]:
        try:
            row = json.loads(line)
        except Exception:
            continue
        ident = str(row.get("consent_id") or row.get("id") or "")
        if (
            isinstance(row, dict)
            and row.get("event") == "consent_required"
            and not row.get("dry_run")
            and pending_status.get(ident, "pending") == "pending"
        ):
            rows.append(row)
    latest: dict[str, dict] = {}
    for row in rows:
        key = row.get("consent_id") or f"{row.get('chapter')}:{row.get('app')}:{row.get('proposal')}"
        latest[str(key)] = row
    out = []
    for row in list(latest.values())[-8:]:
        title = f"{row.get('chapter', 'Talisman')} → {row.get('app', 'app')}"
        out.append(card(
            "needs_consent",
            title,
            row.get("proposal") or row.get("result") or "A talisman action needs consent.",
            source="Talisman app action",
            priority="high",
            owner=str(row.get("chapter") or "Talisman"),
            action="Approve, reject, or ask for a safer/revised version.",
            path=row.get("content_file") or "",
            due=row.get("timestamp", ""),
            card_id=f"pact-{row.get('consent_id') or title}",
        ))
    return out


def collect_publishing_work() -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for p in latest_md_files(MEMORY / "publishing" / "market-research", 1):
        out.append(card(
            "watching",
            "Latest market brief",
            f"{title_from_md(p)} · {mtime_label(p)}",
            source="Listening Desk",
            owner="Penny + Goldweaver",
            action="Use as direction for the next content/profit experiment.",
            path=str(p),
        ))
    for p in latest_md_files(MEMORY / "publishing" / "press-abundance" / "daily", 1):
        out.append(card(
            "in_progress",
            "Press & Abundance daily plan",
            f"{title_from_md(p)} · {mtime_label(p)}",
            source="Penny + Professor Goldweaver",
            owner="Penny + Goldweaver",
            action="Turn the strongest draft into one public-facing piece.",
            path=str(p),
        ))
    return out


def collect_rituals(player: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    compass = read_json(PLAYERS / f"{player}-compass-run.json")
    if isinstance(compass, dict) and compass:
        status = str(compass.get("status") or compass.get("step") or "active")
        if status.lower() not in {"complete", "completed", "idle", "cancelled"}:
            task = compass.get("player_task") or compass.get("task") or compass.get("north") or "Continue the active Compass Run."
            out.append(card(
                "waiting_on_bj",
                f"Compass Run: {status}",
                task,
                source="Wonder Compass",
                priority="high",
                owner="Stonebrook / Compass",
                action="Answer the current step or complete West with a real souvenir sentence.",
                path=str(PLAYERS / f"{player}-compass-run.json"),
            ))
    book = read_json(PLAYERS / f"{player}-book-jump.json")
    if isinstance(book, dict) and book:
        status = str(book.get("status") or "")
        if status and status.lower() not in {"returned", "complete", "completed", "idle", "cancelled"}:
            out.append(card(
                "waiting_on_bj",
                f"Book Jump: {book.get('title') or status}",
                book.get("intention") or book.get("world") or "A book-world is still holding a thread.",
                source="Book Jumping",
                priority="high" if book.get("souvenir_due") else "normal",
                owner="Professor Permancer",
                action="Continue, stabilize, return, or provide the souvenir if due.",
                path=str(PLAYERS / f"{player}-book-jump.json"),
            ))
    for path in PLAYERS.glob(f"{player}-*enchantment*.json"):
        data = read_json(path)
        status = str(data.get("status") or "")
        if status and status.lower() not in {"complete", "completed", "idle", "cancelled"}:
            out.append(card(
                "waiting_on_bj",
                f"Enchantment: {data.get('spell') or path.stem}",
                data.get("target") or data.get("proof_due") or "An Enchantment is awaiting real proof.",
                source="Enchantment",
                priority="high",
                owner="Flyleaf",
                action="Send the photo/description proof or cancel the spell.",
                path=str(path),
            ))
    return out


def collect_support(player: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    support_dir = MEMORY / "support-faculty"
    for name, owner in [
        ("vellum", "Dr. Elowen Vellum"),
        ("inkrest", "Dr. Selene Inkrest"),
        ("gimble", "Gimble"),
        ("bellkeeper", "The Bellkeeper"),
    ]:
        chart = PLAYERS / f"{player}-{name}-chart.md"
        if chart.exists():
            text = read(chart, 5000)
            experiments = re.findall(r"^- \[[ xX]\]\s+(.+)$", text, re.MULTILINE)
            for exp in experiments[:3]:
                out.append(card(
                    "in_progress",
                    f"{owner}: open experiment",
                    exp,
                    source="Support Faculty",
                    owner=owner,
                    action="Check whether this still helps or should be revised.",
                    path=str(chart),
                ))
    latest_guild = latest_md_files(support_dir / "guild", 1)
    if latest_guild:
        p = latest_guild[0]
        out.append(card(
            "watching",
            "Latest Support Guild meeting",
            f"{title_from_md(p)} · {mtime_label(p)}",
            source="Support Guild",
            owner="Support Faculty",
            action="Review the council's single most useful next move.",
            path=str(p),
        ))
    return out


def collect_system_health() -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    checks = [
        ("Heartbeat Pulse", BASE / "HEARTBEAT.md", 1.0, "pulse.py may be stale."),
        ("The Bleed", LOGS / "bleed.log", 30.0, "The newspaper may not have run recently."),
        ("Actual / Gimble", LOGS / "support-faculty.log", 30.0, "Support faculty cron log is stale."),
        ("Draw Things keepalive", LOGS / "drawthings-keepalive.log", 2.5, "Hourly image keepalive may be stale."),
        ("Mission Control", BASE / "hooks" / "mission-control.html", 0.75, "Mission Control folio may be stale."),
    ]
    for title, path, threshold, message in checks:
        age = age_hours(path)
        if age is None:
            out.append(card("watching", f"{title} missing", message, source="System", priority="warning", action="Check the cron/log path.", path=str(path)))
        elif age > threshold:
            out.append(card(
                "watching",
                f"{title} stale",
                f"{message} Last update: {mtime_label(path)}.",
                source="System",
                priority="warning",
                action="Check cron health or rerun the script.",
                path=str(path),
            ))
    return out


def collect_apple_reminders(limit: int = 12) -> list[dict[str, str]]:
    script = r'''
set output to ""
tell application "Reminders"
  repeat with reminderList in every list
    repeat with r in reminders of reminderList
      if completed of r is false then
        set dueText to ""
        try
          set d to due date of r
          if d is not missing value then
            set dueText to (d as string)
          end if
        end try
        if dueText is not "" then
          set output to output & name of r & tab & name of reminderList & tab & dueText & linefeed
        end if
      end if
    end repeat
  end repeat
end tell
return output
'''
    try:
        run = subprocess.run(["osascript"], input=script, capture_output=True, text=True, timeout=8)
    except Exception as exc:
        return [card("watching", "Apple Reminders unavailable", str(exc), source="Apple Reminders", priority="warning", action="Grant Reminders automation access if you want this live.")]
    if run.returncode != 0:
        raw_error = run.stderr or run.stdout
        if "Connection invalid" in raw_error or "Can’t get application" in raw_error:
            msg = "Reminders could not be reached from this process. The board will still show game consent and support tasks."
        else:
            msg = clean(raw_error)
        return [card("watching", "Apple Reminders unavailable", msg, source="Apple Reminders", priority="warning", action="Grant Reminders automation access if you want this live.")]
    out = []
    for line in run.stdout.splitlines()[:limit]:
        parts = line.split("\t")
        if not parts or not parts[0].strip():
            continue
        title = parts[0].strip()
        list_name = parts[1].strip() if len(parts) > 1 else "Reminders"
        due = parts[2].strip() if len(parts) > 2 else ""
        out.append(card(
            "today",
            title,
            f"{list_name} · {due}",
            source="Apple Reminders",
            priority="high",
            owner="Bellkeeper",
            action="Do, defer, or delete with mercy.",
            due=due,
        ))
    return out


def build(player: str = "bj", include_reminders: bool = True) -> dict[str, Any]:
    cards: list[dict[str, str]] = []
    cards.extend(collect_consent())
    cards.extend(collect_pact_consent())
    if include_reminders:
        cards.extend(collect_apple_reminders())
    cards.extend(collect_rituals(player))
    cards.extend(collect_support(player))
    cards.extend(collect_publishing_work())
    cards.extend(collect_system_health())

    order = ["needs_consent", "today", "waiting_on_bj", "in_progress", "watching", "done"]
    by_column = {col: [] for col in order}
    for item in cards:
        by_column.setdefault(item["column"], []).append(item)
    for values in by_column.values():
        values.sort(key=lambda c: (c.get("priority") != "high", c.get("due") or "", c.get("title") or ""))

    return {
        "version": 1,
        "generated_at": now().isoformat(timespec="seconds"),
        "player": player,
        "columns": by_column,
        "counts": {col: len(items) for col, items in by_column.items()},
        "total": len(cards),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Enchantify's Mission Control attention board.")
    parser.add_argument("player", nargs="?", default="bj")
    parser.add_argument("--write", action="store_true", help=f"Write {OUT}")
    parser.add_argument("--no-reminders", action="store_true", help="Skip Apple Reminders scan.")
    args = parser.parse_args()
    board = build(args.player, include_reminders=not args.no_reminders)
    if args.write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(board, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"ATTENTION_BOARD: wrote {OUT} ({board['total']} cards)")
    else:
        print(json.dumps(board, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

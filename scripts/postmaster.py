#!/usr/bin/env python3
"""Postmaster Finch Threadneedle, Keeper of the Dead Letter Aviary.

Local Gmail/gog bridge for Enchantify. It reads configured mailboxes when they
are authenticated, summarizes what matters, and routes useful correspondence
to support characters. It never sends mail.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent.parent
PLAYERS = BASE / "players"
MEMORY = BASE / "memory" / "support-faculty" / "postmaster"
BRIEF_DIR = MEMORY / "briefs"
LATEST_JSON = MEMORY / "latest.json"
LATEST_MD = MEMORY / "latest.md"
LOG = BASE / "logs" / "support-faculty" / "postmaster.jsonl"
CONFIG = BASE / "config" / "postmaster.json"
CHART = PLAYERS / "bj-postmaster-chart.md"
POSTMASTER_LOG = PLAYERS / "bj-postmaster-log.jsonl"
PUBLISHING_HANDOFF = BASE / "memory" / "publishing" / "postmaster-handoffs.jsonl"
TARGET = "8729557865"
CHANNEL = "telegram"
ACCOUNT = "enchantify"

DEFAULT_CONFIG = {
    "version": 1,
    "character": "Postmaster Finch Threadneedle",
    "enabled": True,
    "mailboxes": [
        {
            "account": "enchantifyacademy@gmail.com",
            "role": "Enchantify Academy public/project correspondence",
            "enabled": True,
        },
        {
            "account": "thedoobaleedoos@gmail.com",
            "role": "Doobaleedoos, Wonder Compass, Patreon, creator/business correspondence",
            "enabled": True,
        },
    ],
    "max_messages_per_account": 10,
    "gog_client": "postmaster",
    "default_query": "newer_than:14d -in:spam -in:trash",
    "urgent_query": "newer_than:14d -in:spam -in:trash (urgent OR deadline OR invoice OR payment OR appointment OR collaboration OR Patreon OR YouTube OR sponsor OR press)",
    "telegram_default": False,
    "can_send_email": False,
    "can_create_gmail_drafts": False,
    "handoff_to_penny_goldweaver": True,
    "handoff_to_gimble": True,
    "handoff_to_bellkeeper": True,
}

NOISE_SENDER_FRAGMENTS = (
    "noreply",
    "no-reply",
    "donotreply",
    "do-not-reply",
    "mail.instagram.com",
    "bsky.social",
    "newsletter@",
    "redditmail.com",
    "googleaistudio",
    "service.tiktok.com",
    "facebookmail.com",
    "accounts.google.com",
    "mailer-daemon",
    "postmaster@",
)

NOISE_SUBJECT_FRAGMENTS = (
    "your code is",
    "verification code",
    "password reset",
    "security alert",
    "confirm your",
    "unsubscribe",
    "digest",
    "newsletter",
    "recommended for you",
    "build android apps in minutes",
)

STRONG_PENNY_PATTERNS = (
    "patreon",
    "collaboration",
    "sponsor",
    "press inquiry",
    "interview request",
    "interview",
    "guest post",
    "podcast",
    "gumroad",
    "kofi",
    "ko-fi",
    "wonder compass",
    "enchantify academy",
    "rights inquiry",
    "licensing",
    "brand deal",
    "media kit",
)

ROUTE_PATTERNS = {
    "penny_goldweaver": list(STRONG_PENNY_PATTERNS),
    "gimble": [
        "invoice",
        "receipt",
        "payment",
        "billing",
        "subscription",
        "renewal",
        "tax",
        "statement",
        "refund",
        "charge",
    ],
    "bellkeeper": [
        "appointment",
        "schedule",
        "calendar",
        "meeting",
        "deadline",
        "event",
        "reservation",
        "booking",
        "reminder",
    ],
    "inkrest": [
        "stress",
        "grief",
        "difficult",
        "therapy",
        "mental health",
        "overwhelmed",
    ],
}


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def clean(value: Any, limit: int = 800) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit].rstrip() + ("..." if len(text) > limit else "")


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    row.setdefault("timestamp", now())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return dict(default)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else dict(default)
    except Exception:
        return dict(default)


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def ensure_files() -> None:
    MEMORY.mkdir(parents=True, exist_ok=True)
    BRIEF_DIR.mkdir(parents=True, exist_ok=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    if not CONFIG.exists():
        save_json(CONFIG, DEFAULT_CONFIG)


def gog_path() -> str:
    return shutil.which("gog") or ""


def run_gog(account: str, query: str, max_results: int, *, client: str = "") -> tuple[bool, Any, str]:
    gog = gog_path()
    if not gog:
        return False, None, "gog CLI is not installed or not on PATH."
    args = [
        gog,
        "gmail",
        "-a",
        account,
    ]
    if client:
        args += ["--client", client]
    args += ["--json", "--results-only", "search", query, "--max", str(max_results)]
    proc = subprocess.run(args, cwd=BASE, capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        return False, None, clean(proc.stderr or proc.stdout, 1200)
    try:
        return True, json.loads(proc.stdout or "[]"), ""
    except Exception as exc:
        return False, None, f"Could not parse gog output: {clean(exc)}"


def message_text(row: dict[str, Any]) -> str:
    return f"{row.get('subject', '')} {row.get('sender', '')} {row.get('snippet', '')}".lower()


def human_sender(row: dict[str, Any]) -> bool:
    sender = message_text(row)
    if any(fragment in sender for fragment in NOISE_SENDER_FRAGMENTS):
        return False
    if "@" not in sender:
        return False
    return True


def is_noise(row: dict[str, Any]) -> bool:
    text = message_text(row)
    if any(fragment in text for fragment in NOISE_SUBJECT_FRAGMENTS):
        return True
    if any(fragment in text for fragment in NOISE_SENDER_FRAGMENTS):
        return True
    if re.search(r"\b\d{4,8}\b is your (instagram|facebook|google) code", text):
        return True
    if "tiktok" in text and "newsletter@service.tiktok.com" in text:
        return True
    if "reddit" in text and "noreply@redditmail.com" in text:
        return True
    return False


def route_message(row: dict[str, Any]) -> list[str]:
    if is_noise(row):
        return ["postmaster"]
    text = message_text(row)
    routes: list[str] = []
    for route, tokens in ROUTE_PATTERNS.items():
        if route == "penny_goldweaver":
            if any(token in text for token in tokens):
                routes.append(route)
            continue
        if any(token in text for token in tokens):
            routes.append(route)
    if "penny_goldweaver" in routes and not human_sender(row):
        routes = [route for route in routes if route != "penny_goldweaver"]
    if not routes:
        routes = ["postmaster"]
    return routes


def classify_message(row: dict[str, Any]) -> str:
    if is_noise(row):
        return "noise"
    routes = row.get("routes") or []
    text = message_text(row)
    if "penny_goldweaver" in routes and int(row.get("priority") or 0) >= 28:
        return "lead"
    if any(route in routes for route in ("gimble", "bellkeeper", "inkrest")):
        return "attention"
    if human_sender(row) and any(token in text for token in ("question", "hello", "hi ", "wonder", "enchantify", "book", "patreon")):
        return "attention"
    if "penny_goldweaver" in routes:
        return "lead"
    return "archive"


def priority(row: dict[str, Any]) -> int:
    if is_noise(row):
        return 0
    text = message_text(row)
    score = 0
    if human_sender(row):
        score += 15
    if "urgent" in text or "deadline" in text:
        score += 40
    if "invoice" in text or "payment" in text or "billing" in text:
        score += 30
    if "appointment" in text or "meeting" in text:
        score += 25
    if "collaboration" in text or "sponsor" in text or "press" in text:
        score += 30
    if "patreon" in text or ("youtube" in text and "creator" in text) or "wonder compass" in text:
        score += 20
    score += 5 * len(row.get("routes") or [])
    if row.get("classification") == "noise":
        return 0
    return score


def suggest_reply(row: dict[str, Any]) -> str:
    text = message_text(row)
    subject = row.get("subject") or "your note"
    if "invoice" in text or "receipt" in text or "billing" in text:
        return (
            "Thanks — received. I'll review this against the ledger and follow up if anything needs action. "
            "No payment or account changes will happen without explicit approval."
        )
    if "appointment" in text or "meeting" in text or "calendar" in text:
        return (
            "Thank you. I'll check whether this belongs on the calendar and reply with a clear yes/no "
            "once I've confirmed timing."
        )
    if any(token in text for token in ("collaboration", "sponsor", "press", "interview", "podcast", "guest")):
        return (
            f"Thanks for reaching out about “{clean(subject, 120)}”. "
            "We're a small Academy-shaped project, so we move carefully — but we're interested. "
            "Could you share timing, audience, and what you hope we'd contribute?"
        )
    if "patreon" in text:
        return (
            "Thank you for writing. We're tending the Doobaleedoos one-dollar door gently and appreciate members "
            "who notice the work. Tell me what brought you to the Patreon, and I'll answer personally."
        )
    return (
        f"Thanks for your message about “{clean(subject, 120)}”. "
        "I read everything that reaches the Aviary; give me a day to answer properly."
    )


def build_reply_suggestions(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    for row in messages:
        if row.get("classification") not in {"attention", "lead"}:
            continue
        routes = row.get("routes") or []
        if not any(route in routes for route in ("penny_goldweaver", "gimble", "bellkeeper", "postmaster")):
            continue
        suggestions.append({
            "subject": row.get("subject"),
            "sender": row.get("sender"),
            "account": row.get("account"),
            "routes": routes,
            "classification": row.get("classification"),
            "suggested_reply": suggest_reply(row),
            "review_note": "Draft only. Postmaster never sends mail without explicit BJ approval.",
        })
    suggestions.sort(key=lambda item: 0 if item.get("classification") == "lead" else 1)
    return suggestions[:6]


def normalize_messages(raw: Any, account: str) -> list[dict[str, Any]]:
    if isinstance(raw, dict):
        candidates = raw.get("threads") or raw.get("messages") or raw.get("items") or raw.get("results") or []
    else:
        candidates = raw if isinstance(raw, list) else []
    rows: list[dict[str, Any]] = []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        subject = item.get("subject") or item.get("Subject") or item.get("snippet") or item.get("title") or "(no subject)"
        sender = item.get("from") or item.get("sender") or item.get("From") or item.get("author") or ""
        date = item.get("date") or item.get("internalDate") or item.get("lastMessageDate") or item.get("received") or ""
        snippet = item.get("snippet") or item.get("summary") or item.get("body") or ""
        message_id = item.get("id") or item.get("messageId") or item.get("message_id") or ""
        thread_id = item.get("threadId") or item.get("thread_id") or ""
        row = {
            "account": account,
            "subject": clean(subject, 240),
            "sender": clean(sender, 220),
            "date": clean(date, 120),
            "snippet": clean(snippet, 500),
            "message_id": message_id,
            "thread_id": thread_id,
        }
        row["routes"] = route_message(row)
        row["classification"] = classify_message(row)
        row["priority"] = priority(row)
        rows.append(row)
    rows.sort(key=lambda r: int(r.get("priority") or 0), reverse=True)
    return rows


def mailbox_status(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    client = str(cfg.get("gog_client") or "")
    for box in cfg.get("mailboxes", []):
        account = box.get("account", "")
        ok, _raw, err = run_gog(account, "newer_than:1d -in:spam -in:trash", 1, client=client)
        rows.append({
            "account": account,
            "role": box.get("role", ""),
            "enabled": bool(box.get("enabled", True)),
            "authenticated": ok,
            "status": "ready" if ok else err,
        })
    return rows


def build_brief(query: str = "", max_results: int | None = None) -> dict[str, Any]:
    ensure_files()
    cfg = load_json(CONFIG, DEFAULT_CONFIG)
    max_n = max_results or int(cfg.get("max_messages_per_account") or 10)
    client = str(cfg.get("gog_client") or "")
    query = query or str(cfg.get("default_query") or DEFAULT_CONFIG["default_query"])
    accounts = [box for box in cfg.get("mailboxes", []) if box.get("enabled", True)]
    account_rows = []
    raw_messages: list[dict[str, Any]] = []
    for box in accounts:
        account = str(box.get("account") or "")
        ok, raw, err = run_gog(account, query, max_n, client=client)
        status = {"account": account, "role": box.get("role", ""), "authenticated": ok, "error": err}
        account_rows.append(status)
        if ok:
            raw_messages.extend(normalize_messages(raw, account))
    noise_rows = [row for row in raw_messages if row.get("classification") == "noise"]
    messages = [row for row in raw_messages if row.get("classification") != "noise"]
    routes = Counter(route for row in messages for route in row.get("routes", []))
    lead_rows = [
        row for row in messages
        if "penny_goldweaver" in row.get("routes", []) and row.get("classification") in {"lead", "attention"}
    ]
    attention_rows = [row for row in messages if row.get("classification") == "attention"][:8]
    reply_suggestions = build_reply_suggestions(messages)
    packet = {
        "generated_at": now(),
        "character": cfg.get("character", "Postmaster Finch Threadneedle"),
        "query": query,
        "accounts": account_rows,
        "raw_message_count": len(raw_messages),
        "message_count": len(messages),
        "noise_filtered_count": len(noise_rows),
        "route_counts": dict(routes),
        "messages": messages[: max_n * max(1, len(accounts))],
        "penny_goldweaver_leads": lead_rows[:8],
        "attention_queue": attention_rows,
        "goldweaver_reply_suggestions": reply_suggestions,
        "smallest_next_action": smallest_next_action(account_rows, messages, reply_suggestions),
    }
    return packet


def smallest_next_action(
    accounts: list[dict[str, Any]],
    messages: list[dict[str, Any]],
    reply_suggestions: list[dict[str, Any]] | None = None,
) -> str:
    missing = [row["account"] for row in accounts if not row.get("authenticated")]
    if missing:
        return "Authenticate the desired Gmail accounts with `gog auth add <account> --services gmail`."
    if reply_suggestions:
        top = reply_suggestions[0]
        return (
            f"Goldweaver suggests a review-only reply draft for `{top.get('subject')}` — "
            "edit before sending; Postmaster never mails on his own."
        )
    if not messages:
        return "No actionable mail matched the query after filtering newsletters and auth codes. The Aviary can stay quiet."
    top = messages[0]
    if top.get("classification") == "lead":
        return f"Penny and Goldweaver should review `{top.get('subject')}` as a creator/business lead."
    if "gimble" in top.get("routes", []):
        return f"Ask Gimble to inspect `{top.get('subject')}` as a bill/receipt/subscription clue."
    if "bellkeeper" in top.get("routes", []):
        return f"Ask Bellkeeper whether `{top.get('subject')}` belongs on the calendar."
    return f"Open or summarize `{top.get('subject')}` before drafting anything."


def render_markdown(packet: dict[str, Any]) -> str:
    lines = [
        f"# Postmaster Finch Correspondence Brief — {packet.get('generated_at')}",
        "",
        "The Aviary is not aflame. These are envelopes and threads, not moral judgments.",
        "",
        f"**Query:** `{packet.get('query')}`",
        f"**Actionable messages:** {packet.get('message_count')} "
        f"(filtered {packet.get('noise_filtered_count', 0)} newsletter/auth/no-reply items)",
        "",
        "## Mailbox Status",
    ]
    for row in packet.get("accounts", []):
        mark = "ready" if row.get("authenticated") else "needs auth"
        lines.append(f"- **{row.get('account')}** — {mark}. {clean(row.get('role'), 140)}")
        if not row.get("authenticated"):
            lines.append(f"  - {clean(row.get('error'), 300)}")
    lines.extend(["", "## Route Weather"])
    counts = packet.get("route_counts") or {}
    if counts:
        for route, count in sorted(counts.items()):
            lines.append(f"- {route}: {count}")
    else:
        lines.append("- No routed messages yet.")
    lines.extend(["", "## Letters Tapping At The Glass"])
    for idx, row in enumerate(packet.get("messages", [])[:12], 1):
        routes = ", ".join(row.get("routes") or [])
        lines.extend([
            "",
            f"### {idx}. {row.get('subject')}",
            f"- Account: {row.get('account')}",
            f"- From: {row.get('sender') or 'unknown'}",
            f"- Date: {row.get('date') or 'unknown'}",
            f"- Routes: {routes}",
            f"- Priority: {row.get('priority')}",
        ])
        if row.get("snippet"):
            lines.extend(["", "> " + clean(row.get("snippet"), 500)])
    leads = packet.get("penny_goldweaver_leads") or []
    lines.extend(["", "## Penny / Goldweaver Leads"])
    if leads:
        for row in leads[:6]:
            lines.append(
                f"- **{row.get('subject')}** from {row.get('sender') or 'unknown'} "
                f"({row.get('account')}) — {row.get('classification')}"
            )
    else:
        lines.append("- No creator/business leads surfaced in this pass.")
    attention = packet.get("attention_queue") or []
    lines.extend(["", "## Attention Queue"])
    if attention:
        for row in attention[:6]:
            lines.append(f"- **{row.get('subject')}** — routes: {', '.join(row.get('routes') or [])}")
    else:
        lines.append("- Nothing urgent after filtering noise.")
    suggestions = packet.get("goldweaver_reply_suggestions") or []
    lines.extend(["", "## Goldweaver Reply Drafts (Review Only)"])
    if suggestions:
        for item in suggestions[:5]:
            lines.extend([
                "",
                f"### {item.get('subject')}",
                f"- From: {item.get('sender') or 'unknown'}",
                f"- Routes: {', '.join(item.get('routes') or [])}",
                "",
                item.get("suggested_reply") or "",
                "",
                f"_{item.get('review_note')}_",
            ])
    else:
        lines.append("- No reply drafts suggested this pass.")
    lines.extend([
        "",
        "## Smallest Next Action",
        str(packet.get("smallest_next_action") or "No action required."),
        "",
        "## Consent",
        "The Postmaster may read/search configured mail and draft review text. He may not send, archive, delete, label, or reply without explicit approval.",
    ])
    return "\n".join(lines).rstrip() + "\n"


def save_brief(packet: dict[str, Any]) -> Path:
    BRIEF_DIR.mkdir(parents=True, exist_ok=True)
    path = BRIEF_DIR / f"{today()}-correspondence-brief.md"
    markdown = render_markdown(packet)
    path.write_text(markdown, encoding="utf-8")
    LATEST_MD.write_text(markdown, encoding="utf-8")
    LATEST_JSON.write_text(json.dumps(packet, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    append_jsonl(LOG, {
        "kind": "brief",
        "path": str(path),
        "message_count": packet.get("message_count"),
        "noise_filtered_count": packet.get("noise_filtered_count"),
        "route_counts": packet.get("route_counts"),
        "reply_suggestions": len(packet.get("goldweaver_reply_suggestions") or []),
    })
    append_jsonl(POSTMASTER_LOG, {
        "kind": "brief",
        "path": str(path),
        "message_count": packet.get("message_count"),
        "smallest_next_action": packet.get("smallest_next_action"),
    })
    for lead in packet.get("penny_goldweaver_leads") or []:
        append_jsonl(PUBLISHING_HANDOFF, {"kind": "email_lead", **lead})
    for suggestion in packet.get("goldweaver_reply_suggestions") or []:
        append_jsonl(PUBLISHING_HANDOFF, {"kind": "reply_suggestion", **suggestion})
    return path


def load_latest_packet() -> dict[str, Any]:
    if LATEST_JSON.exists():
        try:
            data = json.loads(LATEST_JSON.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    path = BRIEF_DIR / f"{today()}-correspondence-brief.md"
    if path.exists():
        return {"generated_at": today(), "brief_path": str(path), "message_count": 0}
    return {}


def brief_age_hours() -> float | None:
    if not LATEST_JSON.exists():
        return None
    age_seconds = max(0.0, datetime.now().timestamp() - LATEST_JSON.stat().st_mtime)
    return age_seconds / 3600.0


def ensure_brief(*, max_age_hours: float = 8.0, query: str = "", max_results: int | None = None) -> dict[str, Any]:
    age = brief_age_hours()
    if age is None or age > max_age_hours:
        packet = build_brief(query=query, max_results=max_results)
        save_brief(packet)
        return packet
    return load_latest_packet()


def desk_context(*, ensure_fresh: bool = False, max_age_hours: float = 8.0) -> dict[str, Any]:
    packet = ensure_brief(max_age_hours=max_age_hours) if ensure_fresh else load_latest_packet()
    if not packet:
        return {"available": False, "diagnosis": "No Postmaster brief filed yet. Run `python3 scripts/postmaster.py daily`."}
    leads = packet.get("penny_goldweaver_leads") or []
    suggestions = packet.get("goldweaver_reply_suggestions") or []
    attention = packet.get("attention_queue") or []
    return {
        "available": True,
        "generated_at": packet.get("generated_at"),
        "brief_path": str(LATEST_MD if LATEST_MD.exists() else BRIEF_DIR / f"{today()}-correspondence-brief.md"),
        "message_count": packet.get("message_count"),
        "noise_filtered_count": packet.get("noise_filtered_count"),
        "route_counts": packet.get("route_counts"),
        "smallest_next_action": packet.get("smallest_next_action"),
        "penny_goldweaver_leads": leads[:6],
        "attention_queue": attention[:6],
        "goldweaver_reply_suggestions": suggestions[:5],
        "top_messages": [
            {
                "subject": row.get("subject"),
                "sender": row.get("sender"),
                "account": row.get("account"),
                "routes": row.get("routes"),
                "classification": row.get("classification"),
                "priority": row.get("priority"),
            }
            for row in (packet.get("messages") or [])[:6]
        ],
        "excerpt": clean(LATEST_MD.read_text(encoding="utf-8", errors="replace"), 2800) if LATEST_MD.exists() else "",
    }


def load_postmaster_desk(*, ensure_fresh: bool = False, max_age_hours: float = 8.0) -> dict[str, Any]:
    """Import-safe helper for other Enchantify desks."""
    return desk_context(ensure_fresh=ensure_fresh, max_age_hours=max_age_hours)


def telegram_send(message: str, media: Path | None = None, *, dry_run: bool = False) -> int:
    if dry_run:
        print(message)
        if media:
            print(f"[dry-run media] {media}")
        return 0
    args = [
        "openclaw",
        "message",
        "send",
        "--target",
        TARGET,
        "--channel",
        CHANNEL,
        "--account",
        ACCOUNT,
        "--message",
        message,
    ]
    if media:
        args += ["--media", str(media), "--force-document"]
    proc = subprocess.run(args, cwd=BASE, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        append_jsonl(LOG, {"kind": "telegram_error", "stderr": clean(proc.stderr or proc.stdout, 1200), "media": str(media) if media else ""})
    return proc.returncode


def cmd_init() -> int:
    ensure_files()
    print(f"POSTMASTER_CONFIG: {CONFIG}")
    print(f"POSTMASTER_CHART: {CHART}")
    return 0


def cmd_status() -> int:
    ensure_files()
    cfg = load_json(CONFIG, DEFAULT_CONFIG)
    rows = mailbox_status(cfg)
    print("POSTMASTER_STATUS:")
    print(json.dumps({
        "character": cfg.get("character"),
        "gog": gog_path() or "missing",
        "gog_client": cfg.get("gog_client") or "",
        "mailboxes": rows,
        "chart": str(CHART),
        "brief_dir": str(BRIEF_DIR),
    }, indent=2, ensure_ascii=False, default=str))
    return 0 if all(row.get("authenticated") for row in rows) else 2


def cmd_brief(args: argparse.Namespace) -> int:
    packet = build_brief(query=args.query, max_results=args.max)
    path = save_brief(packet)
    print(f"POSTMASTER_BRIEF: {path}")
    print(f"MESSAGES: {packet.get('message_count')}")
    print(f"FILTERED_NOISE: {packet.get('noise_filtered_count')}")
    print(f"REPLY_DRAFTS: {len(packet.get('goldweaver_reply_suggestions') or [])}")
    print(f"NEXT: {packet.get('smallest_next_action')}")
    if args.send:
        message = (
            "Postmaster Finch has sealed a Correspondence Brief.\n\n"
            f"Actionable messages: {packet.get('message_count')} "
            f"(filtered {packet.get('noise_filtered_count', 0)} noise items)\n"
            f"Reply drafts for review: {len(packet.get('goldweaver_reply_suggestions') or [])}\n"
            f"Next: {packet.get('smallest_next_action')}"
        )
        return telegram_send(message, path, dry_run=args.dry_run)
    return 0


def cmd_daily(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(BASE / "scripts"))
    import cron_steward  # type: ignore

    with cron_steward.run("postmaster:daily"):
        packet = build_brief(query=args.query, max_results=args.max)
        path = save_brief(packet)
        print(f"POSTMASTER_BRIEF: {path}")
        print(f"MESSAGES: {packet.get('message_count')}")
        print(f"FILTERED_NOISE: {packet.get('noise_filtered_count')}")
        if args.send:
            message = (
                "Postmaster Finch — daily correspondence brief.\n\n"
                f"Actionable: {packet.get('message_count')} · "
                f"Filtered noise: {packet.get('noise_filtered_count', 0)}\n"
                f"Next: {packet.get('smallest_next_action')}"
            )
            return telegram_send(message, path, dry_run=args.dry_run, silent=args.silent)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Postmaster Finch correspondence support")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("status")
    brief = sub.add_parser("brief")
    brief.add_argument("--query", default="")
    brief.add_argument("--max", type=int, default=None)
    brief.add_argument("--send", action="store_true")
    brief.add_argument("--dry-run", action="store_true")
    daily = sub.add_parser("daily", help="Build today's correspondence brief (cron-friendly).")
    daily.add_argument("--query", default="")
    daily.add_argument("--max", type=int, default=None)
    daily.add_argument("--send", action="store_true")
    daily.add_argument("--dry-run", action="store_true")
    daily.add_argument("--silent", action="store_true")
    args = parser.parse_args()
    if args.command == "init":
        return cmd_init()
    if args.command == "status":
        return cmd_status()
    if args.command == "brief":
        return cmd_brief(args)
    if args.command == "daily":
        return cmd_daily(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

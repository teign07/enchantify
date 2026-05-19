#!/usr/bin/env python3
"""Daily Support Guild meeting for Enchantify's support characters.

One LLM call may turn fresh body, mood, and ledger data into a single
in-world council artifact. If the gateway is unavailable, the deterministic
fallback still files a useful daily meeting instead of going silent.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent.parent
PLAYERS = BASE / "players"
LOG_DIR = BASE / "logs" / "support-faculty"
GUILD_DIR = BASE / "memory" / "support-faculty" / "guild"
HEARTBEAT = BASE / "HEARTBEAT.md"
VELLUM_CHART = PLAYERS / "bj-vellum-chart.md"
INKREST_CHART = PLAYERS / "bj-therapy-chart.md"
LEDGER_CHART = PLAYERS / "bj-ledger-chart.md"
VELLUM_LOG = PLAYERS / "bj-vellum-log.jsonl"
INKREST_LOG = PLAYERS / "bj-inkrest-log.jsonl"
LEDGER_LOG = PLAYERS / "bj-ledger-log.jsonl"
SUPPORT_MEMORY = PLAYERS / "bj-support-memory.json"
ACTUAL_API = BASE / "scripts" / "actual-api.mjs"
SECRETS_ENV = BASE / "config" / "secrets.env"
TARGET = "8729557865"
CHANNEL = "telegram"
ACCOUNT = "enchantify"

sys.path.insert(0, str(BASE / "scripts"))
import cron_steward  # type: ignore


def now() -> datetime:
    return datetime.now()


def today() -> str:
    return now().strftime("%Y-%m-%d")


def ensure_dirs() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    GUILD_DIR.mkdir(parents=True, exist_ok=True)


def read(path: Path, limit: int | None = None) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[:limit] if limit else text


def clean(value: Any, limit: int = 500) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit].rstrip() + ("..." if len(text) > limit else "")


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    row.setdefault("timestamp", now().isoformat(timespec="seconds"))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def read_jsonl(path: Path, days: int = 14) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    cutoff = now() - timedelta(days=days)
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
            ts = datetime.fromisoformat(str(row.get("timestamp", "")))
            if ts.tzinfo is not None:
                ts = ts.replace(tzinfo=None)
        except Exception:
            continue
        if ts >= cutoff:
            rows.append(row)
    return rows


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_json(path: Path, data: dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def heartbeat_field(label: str) -> str:
    text = read(HEARTBEAT)
    patterns = [
        rf"\*\*{re.escape(label)}:\*\*\s*([^|\n]+)",
        rf"- \*\*{re.escape(label)}:\*\*\s*(.+)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            return clean(m.group(1), 240)
    return ""


def steps_value() -> int | None:
    text = read(HEARTBEAT)
    m = re.search(r"Steps:\s*([\d,]+)", text, re.IGNORECASE)
    if not m:
        m = re.search(r"([\d,]+)\s+steps", text, re.IGNORECASE)
    return int(m.group(1).replace(",", "")) if m else None


def actual_summary() -> dict[str, Any] | None:
    if not ACTUAL_API.exists():
        return latest_logged_actual_summary()
    proc = subprocess.run(
        ["node", str(ACTUAL_API), "summary"],
        cwd=BASE,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if proc.returncode != 0:
        append_jsonl(LOG_DIR / "guild-errors.jsonl", {
            "kind": "actual_summary_error",
            "stderr": clean(proc.stderr or proc.stdout, 2000),
        })
        return latest_logged_actual_summary()
    try:
        m = re.search(r"__ACTUAL_JSON_START__\s*(.*?)\s*__ACTUAL_JSON_END__", proc.stdout, re.DOTALL)
        return json.loads(m.group(1) if m else proc.stdout)
    except Exception:
        append_jsonl(LOG_DIR / "guild-errors.jsonl", {
            "kind": "actual_summary_parse_error",
            "stdout": clean(proc.stdout, 2000),
        })
        return latest_logged_actual_summary()


def latest_logged_actual_summary() -> dict[str, Any] | None:
    """Use Gimble's newest cached Actual summary when live API access fails."""
    for row in reversed(read_jsonl(LEDGER_LOG, days=7)):
        summary = row.get("summary")
        if isinstance(summary, dict) and summary.get("accounts"):
            cached = dict(summary)
            cached["source"] = f"ledger-log:{row.get('kind', 'unknown')}"
            cached["cached_at"] = row.get("timestamp")
            return cached
    return None


def build_context() -> dict[str, Any]:
    inkrest = read_jsonl(INKREST_LOG, days=10)
    vellum = read_jsonl(VELLUM_LOG, days=10)
    ledger = read_jsonl(LEDGER_LOG, days=10)
    mood_rows = [r for r in inkrest if r.get("kind") == "mood-word" and r.get("word")]
    prompt_rows = [r for r in inkrest if r.get("kind") == "prompt"]
    mood_words = [str(r.get("word", "")).strip() for r in mood_rows]
    latest_mood = mood_rows[-1] if mood_rows else {}
    latest_prompt = prompt_rows[-1] if prompt_rows else {}
    unanswered_since_latest = 0
    if latest_prompt:
        try:
            latest_mood_ts = datetime.fromisoformat(str(latest_mood.get("timestamp", "1970-01-01")).replace("Z", "+00:00"))
            if latest_mood_ts.tzinfo is not None:
                latest_mood_ts = latest_mood_ts.replace(tzinfo=None)
        except Exception:
            latest_mood_ts = datetime.min
        for row in prompt_rows:
            try:
                ts = datetime.fromisoformat(str(row.get("timestamp", "")))
                if ts.tzinfo is not None:
                    ts = ts.replace(tzinfo=None)
            except Exception:
                continue
            if ts > latest_mood_ts:
                unanswered_since_latest += 1
    ledger_latest = ledger[-1] if ledger else {}
    actual = actual_summary()
    accounts = (actual or {}).get("accounts", [])
    on_budget = [a for a in accounts if not a.get("offbudget") and not a.get("closed")]
    context = {
        "date": today(),
        "heartbeat": {
            "focus": heartbeat_field("Focus"),
            "pacing": heartbeat_field("Pacing"),
            "fuel": heartbeat_field("Fuel"),
            "watch": heartbeat_field("Watch"),
            "location": heartbeat_field("Location"),
            "steps": steps_value(),
        },
        "charts": {
            "vellum": clean(read(VELLUM_CHART, 3500), 3500),
            "inkrest": clean(read(INKREST_CHART, 3500), 3500),
            "ledger": clean(read(LEDGER_CHART, 2500), 2500),
        },
        "recent": {
            "mood_words": dict(Counter(mood_words).most_common()),
            "latest_mood": latest_mood,
            "latest_prompt": latest_prompt,
            "unanswered_prompts_since_latest_mood": unanswered_since_latest,
            "inkrest_pending": load_json(PLAYERS / "bj-inkrest-pending.json"),
            "mood_log_tail": inkrest[-8:],
            "vellum_log_tail": vellum[-6:],
            "ledger_log_tail": ledger[-4:],
            "latest_ledger_message": clean(ledger_latest.get("message", ""), 900),
        },
        "actual_budget": {
            "connected": bool(actual),
            "source": (actual or {}).get("source", "live") if actual else "unavailable",
            "cached_at": (actual or {}).get("cached_at"),
            "account_count": len(accounts),
            "on_budget_total": round(sum(float(a.get("balance") or 0) for a in on_budget), 2),
            "uncategorized_count": (actual or {}).get("uncategorized_count"),
            "recent_transactions": ((actual or {}).get("recent") or (actual or {}).get("transactions") or [])[:7],
        },
        "support_memory": load_json(SUPPORT_MEMORY),
    }
    return context


def load_config() -> dict[str, str]:
    cfg: dict[str, str] = {}
    if SECRETS_ENV.exists():
        for line in SECRETS_ENV.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                cfg[key.strip()] = value.strip().strip('"').strip("'")
    return cfg


def normalize_model(model: str) -> str:
    model = (model or "").strip()
    if model in {"openclaw", "default", "gateway", ""}:
        return "openclaw"
    return model


def gateway_cfg() -> tuple[int, str, str, int]:
    secrets = load_config()
    oc_cfg: dict[str, Any] = {}
    oc_path = Path.home() / ".openclaw" / "openclaw.json"
    if oc_path.exists():
        try:
            loaded = json.loads(oc_path.read_text(encoding="utf-8"))
            oc_cfg = loaded if isinstance(loaded, dict) else {}
        except Exception:
            oc_cfg = {}
    port = int(
        os.environ.get("OPENCLAW_GATEWAY_PORT")
        or secrets.get("OPENCLAW_GATEWAY_PORT")
        or oc_cfg.get("gateway", {}).get("port")
        or "18789"
    )
    token = (
        os.environ.get("OPENCLAW_GATEWAY_TOKEN")
        or secrets.get("OPENCLAW_GATEWAY_TOKEN")
        or oc_cfg.get("gateway", {}).get("auth", {}).get("token")
        or ""
    )
    raw_model = os.environ.get("SUPPORT_GUILD_MODEL") or secrets.get("SUPPORT_GUILD_MODEL") or os.environ.get("BLEED_MODEL") or secrets.get("BLEED_MODEL") or "openclaw"
    timeout_raw = os.environ.get("SUPPORT_GUILD_TIMEOUT") or secrets.get("SUPPORT_GUILD_TIMEOUT") or "120"
    try:
        timeout = max(30, int(timeout_raw))
    except ValueError:
        timeout = 120
    return port, token, normalize_model(raw_model), timeout


def prompt_for(context: dict[str, Any]) -> str:
    return f"""Write today's Enchantify Support Character Guild Meeting.

This is one daily council artifact, not three separate reports. Present it as
Dr. Elowen Vellum, Dr. Selene Inkrest, and Gimble of the Errata Registry
sharing notes and agreeing on a tiny support plan for BJ.

Rules:
- Be specific to the data. Do not use boilerplate.
- No shame, no pressure, no diagnosing, no medication changes, no financial
  transactions, no medical certainty.
- Vellum may discuss longevity/body/fuel/research translation at safe daily-life level.
- Inkrest may discuss narrative therapy, mood patterns, overwhelm, and next-hour care.
- Treat recent.latest_mood and recent.inkrest_pending as the authoritative
  Inkrest freshness state. Do not claim an older mood is the latest if a newer
  mood appears there. If a prompt is pending, say the check-in is awaiting a
  reply; do not imply BJ ignored it unless the log proves that. Do not enumerate
  unanswered prompt counts unless explicitly asked; this should feel like
  continuity, not attendance-taking.
- Gimble may discuss ledger visibility, Actual Budget, transactions, and safe next action.
- Treat actual_budget.connected/source as the authoritative ledger freshness signal.
  Do not call bank sync dry-run or disconnected merely because an older ledger
  log row contains dry-run test data.
- End with no more than three tiny actions.
- Include a "Do Not Push Today" section.
- Keep it warm, practical, and in-world, like a meeting minute tucked into a magical field journal.

Use exactly this Markdown structure:

# Support Guild Meeting — {context["date"]}

## Guild Weather

## Dr. Vellum

## Dr. Inkrest

## Gimble

## Shared Hypothesis

## Tiny Plan

## Do Not Push Today

## Artifact

Current data JSON:
{json.dumps(context, ensure_ascii=False, indent=2, default=str)[:22000]}
"""


def call_llm(context: dict[str, Any]) -> str:
    port, token, model, timeout = gateway_cfg()
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You write concise Enchantify support-faculty council notes. "
                    "The output is practical, specific, non-shaming, and in-world. "
                    "Reply only with the requested Markdown artifact."
                ),
            },
            {"role": "user", "content": prompt_for(context)},
        ],
        "temperature": 0.72,
        "max_tokens": 1800,
        "stream": False,
    }
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "x-openclaw-session-key": f"support-guild-{int(time.time())}",
        },
        data=json.dumps(payload).encode("utf-8"),
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"Gateway returned HTTP {exc.code}: {body}") from exc
    except Exception as exc:
        raise RuntimeError(f"Gateway call failed: {exc}") from exc
    return (
        result.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )


def fallback_meeting(context: dict[str, Any], reason: str = "") -> str:
    hb = context["heartbeat"]
    recent = context["recent"]
    budget = context["actual_budget"]
    mood = recent.get("mood_words") or {}
    latest_mood = recent.get("latest_mood") or {}
    latest_word = latest_mood.get("word") or next(iter(mood.keys()), "not yet logged")
    pending = recent.get("inkrest_pending") or {}
    fuel = hb.get("fuel") or "fuel signal unavailable"
    steps = hb.get("steps")
    uncategorized = budget.get("uncategorized_count")
    lines = [
        f"# Support Guild Meeting — {context['date']}",
        "",
        "## Guild Weather",
        f"The table has enough signal for a modest plan: latest mood weather is `{latest_word}`, fuel reads `{fuel}`, and ledger visibility is {'online' if budget.get('connected') else 'not yet online'}.",
        "",
        "## Dr. Vellum",
        f"Body note: steps are {steps if steps is not None else 'unknown'}. Today's useful hinge is boring support: water, one protein/fiber anchor, and a movement dose small enough to actually happen.",
        "",
        "## Dr. Inkrest",
        f"Psyche note: the latest logged mood word is `{latest_word}`. "
        f"{'A check-in is currently awaiting reply.' if pending else 'No fresh check-in is pending.'} "
        "Treat the word as weather, not identity. One honest word is enough data.",
        "",
        "## Gimble",
        f"Ledger note: Actual Budget is {'connected' if budget.get('connected') else 'not connected'}. Unbound Echoes: {uncategorized if uncategorized is not None else 'unknown'}. Bind a small number, never the whole storm.",
        "",
        "## Shared Hypothesis",
        "Today improves most if the support faculty lowers friction rather than adding quests.",
        "",
        "## Tiny Plan",
        "1. Log one real fuel item if anything has been missed.",
        "2. Answer Inkrest with one word when asked.",
        "3. Let Gimble bind only the clearest ledger items.",
        "",
        "## Do Not Push Today",
        "Do not turn care into homework. Do not dump long lists. Do not interpret missing data as failure.",
        "",
        "## Artifact",
        "A margin note from the faculty: accuracy, gentleness, and one small visible action are enough to keep the page open.",
    ]
    if reason:
        lines.append(f"\n<!-- fallback: {clean(reason, 300)} -->")
    return "\n".join(lines) + "\n"


def write_meeting(text: str) -> Path:
    path = GUILD_DIR / f"{today()}.md"
    path.write_text(text, encoding="utf-8")
    return path


def summarize_for_telegram(text: str, path: Path) -> str:
    def section(name: str) -> str:
        m = re.search(rf"^## {re.escape(name)}\s*(.*?)(?=^## |\Z)", text, re.DOTALL | re.MULTILINE)
        return clean(m.group(1), 500) if m else ""

    weather = section("Guild Weather") or "The support guild met and filed today's notes."
    plan = section("Tiny Plan")
    do_not = section("Do Not Push Today")
    parts = [
        f"Support Guild Meeting — {today()}",
        "",
        weather,
    ]
    if plan:
        parts.extend(["", "Tiny plan:", plan])
    if do_not:
        parts.extend(["", "Do not push:", do_not])
    parts.extend(["", f"Full minutes attached: {path.name}"])
    return "\n".join(parts)


def send_telegram(message: str, media: Path | None = None, *, dry_run: bool = False, silent: bool = False) -> int:
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
    if silent:
        args.append("--silent")
    if media:
        args += ["--media", str(media), "--force-document"]
    proc = subprocess.run(args, cwd=BASE, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        append_jsonl(LOG_DIR / "guild-send-errors.jsonl", {
            "kind": "telegram_send_error",
            "stderr": clean(proc.stderr or proc.stdout, 2000),
            "media": str(media) if media else "",
        })
    return proc.returncode


def update_support_memory(path: Path, text: str, context: dict[str, Any]) -> None:
    memory = load_json(SUPPORT_MEMORY) or {"version": 1}
    meetings = memory.get("guild_meetings", [])
    if not isinstance(meetings, list):
        meetings = []
    meetings = [m for m in meetings if m.get("date") != today()]
    meetings.append({
        "date": today(),
        "path": str(path),
        "summary": clean(summarize_for_telegram(text, path), 900),
        "heartbeat": context.get("heartbeat", {}),
        "actual_budget": context.get("actual_budget", {}),
    })
    memory["guild_meetings"] = meetings[-30:]
    save_json(SUPPORT_MEMORY, memory)


def run_meeting(*, send: bool = False, dry_run: bool = False, no_llm: bool = False, silent: bool = False) -> int:
    ensure_dirs()
    context = build_context()
    llm_error = ""
    if no_llm:
        text = fallback_meeting(context, "LLM disabled")
    else:
        try:
            text = call_llm(context)
            if not text or "# Support Guild Meeting" not in text:
                raise RuntimeError("model returned an empty or malformed meeting")
        except Exception as exc:
            llm_error = str(exc)
            text = fallback_meeting(context, llm_error)
    if dry_run:
        print(text)
        path = GUILD_DIR / f"{today()}.md"
    else:
        path = write_meeting(text)
        update_support_memory(path, text, context)
        append_jsonl(LOG_DIR / "guild.jsonl", {
            "kind": "guild_meeting",
            "path": str(path),
            "llm_error": llm_error,
            "sent": False,
        })
    if send:
        message = summarize_for_telegram(text, path)
        skip, digest, reason = cron_steward.should_skip_duplicate(
            "support-guild",
            message,
            cooldown_hours=20,
            scope=today(),
        )
        if skip and not dry_run:
            cron_steward.mark_skipped("support-guild", reason, scope=today(), fingerprint=digest)
            return 0
        rc = send_telegram(message, path if not dry_run else None, dry_run=dry_run, silent=silent)
        if rc == 0 and not dry_run:
            cron_steward.mark_delivered("support-guild", message, scope=today(), path=str(path))
            append_jsonl(LOG_DIR / "guild.jsonl", {
                "kind": "guild_delivery",
                "path": str(path),
                "llm_error": llm_error,
                "sent": True,
            })
        return rc
    return 0


def status() -> int:
    ensure_dirs()
    latest = sorted(GUILD_DIR.glob("*.md"))[-5:]
    print("SUPPORT GUILD STATUS")
    print(f"Guild dir: {GUILD_DIR}")
    print(f"Meetings: {len(list(GUILD_DIR.glob('*.md')))}")
    for path in latest:
        print(f"- {path.name}")
    print(f"Support memory: {SUPPORT_MEMORY}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Enchantify Support Character Guild meeting")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("daily", help="Generate today's guild meeting")
    p.add_argument("--send", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-llm", action="store_true")
    p.add_argument("--silent", action="store_true")

    sub.add_parser("status", help="Show support guild status")

    args = parser.parse_args()
    with cron_steward.run(f"support-guild:{args.command}"):
        if args.command == "daily":
            return run_meeting(send=args.send, dry_run=args.dry_run, no_llm=args.no_llm, silent=args.silent)
        if args.command == "status":
            return status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

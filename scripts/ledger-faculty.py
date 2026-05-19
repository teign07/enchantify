#!/usr/bin/env python3
"""Gimble's finance support loop.

This script is intentionally useful before bank sync exists. It keeps a
ledger chart, logs finance observations, and exposes dry-run Actual Budget
adapter points for the later SimpleFIN/Actual setup.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent.parent
PLAYERS = BASE / "players"
LOG_DIR = BASE / "logs" / "support-faculty"
MEMORY_DIR = BASE / "memory" / "support-faculty" / "ledger"
CHART = PLAYERS / "bj-ledger-chart.md"
LEDGER_LOG = PLAYERS / "bj-ledger-log.jsonl"
ACTUAL_CONFIG = BASE / "config" / "actual-budget.json"
ACTUAL_EXAMPLE = BASE / "config" / "actual-budget.example.json"
ACTUAL_API = BASE / "scripts" / "actual-api.mjs"

sys.path.insert(0, str(BASE / "scripts"))
import cron_steward  # type: ignore


TEMPLATE = """# Gimble's Errata Ledger — BJ

This chart is the private working context for Gimble of the Errata Registry, Goblin Bursar of Small Abundances. It is for shame-free financial visibility, category review, upcoming bills, safe-to-spend estimates, tiny-adventure planning, and useful questions. Unknowns stay unknown until BJ supplies data or Actual Budget is connected.

## Gimble Rules

- Money is not moral worth. It is weather, logistics, and life-energy given shape.
- Gimble corrects errors and binds unrecorded transactions; he does not scold.
- Gimble may categorize spending, summarize accounts, flag upcoming bills, identify leaks, suggest category moves, and propose tiny next actions.
- Gimble must not move money, make purchases, approve bank actions, give tax/legal certainty, make risky investment recommendations, or shame debt.
- If the ledger is overwhelming, show the smallest useful slice: never dump a wall of transactions.
- If more than five uncategorized transactions are found, bind only the three largest or three most recent unless BJ asks for more.
- For bank sync, use Actual Budget and SimpleFIN only after BJ has completed the external authentication steps.

## Vocabulary

| Finance Term | Gimble Term | Meaning |
|---|---|---|
| Transactions | Kinetic Ink | Money moving through the Unwritten Chapter |
| Budget Categories | Vessels | Jobs assigned to money |
| Uncategorized Transactions | Unbound Echoes | Reality not yet written into the ledger |
| Categorizing | Binding the Ink | Giving a transaction a truthful place |
| Overspending | Overflow | A vessel needs repair or a deliberate transfer |
| Debt | Temporal Tether | A future claim on current energy, not a moral stain |
| Emergency Fund | Storm Lantern | Reserve that keeps the room lit when weather turns |
| Fun Money | Tiny Adventure Vessel | Permission to enjoy without fog |

## Current Setup

| Field | Value |
|---|---|
| Budget tool | Actual Budget planned |
| Bank sync | SimpleFIN planned |
| Actual server URL | Unknown |
| Budget ID | Unknown |
| Bank accounts connected | Unknown |
| Primary goal | Build visibility without shame |
| Review rhythm | Daily tiny binding; weekly Alchemical Audit |

## Vessel Map

| Actual Category | Gimble Vessel | Notes |
|---|---|---|
| Groceries | Refectory Vessel | Food for ordinary life |
| Dining Out | Tavern Vessel | Convenience, fatigue, pleasure, social meals |
| Gas / Transit | Nimbus Fuel | Commute and wandering |
| Medical | Body Marginalia | Health, medication, care |
| Subscriptions | Tiny Leaks | Recurring charges that deserve periodic review |
| Emergency Fund | Storm Lantern | Buffer and safety |
| Doobaleedoos / Adventure | Tiny Adventure Vessel | Wonder, trips, filming, shared life |
| Pets | Familiar Care | Cat/familiar needs |

## Known Fixed Obligations

| Name | Amount | Due | Notes |
|---|---:|---|---|

## Watch List

| Pattern | Why It Matters | Current Approach |
|---|---|---|
| Delivery / convenience food | May reflect fatigue, mood, schedule, or food availability | Track without shame; correlate with Vellum and Inkrest only when useful |
| Subscriptions | Small recurring leaks can create fog | Review weekly/monthly |

## Current Experiments

Each experiment should be small, time-bounded, and non-shaming.

| Date | Experiment | Metric | Review |
|---|---|---|---|

## Questions For BJ

| Date | Question | Status |
|---|---|---|

## Gimble Output Format

When Gimble gives a substantial report, he should prefer this structure:

1. Weather: one sentence about the ledger state.
2. One number: the most useful number BJ needs right now.
3. One risk: the smallest truthful risk, not a catastrophe.
4. One action: the next transaction/category/bill/adventure decision.
5. No shame clause: a blunt reminder that accuracy is the only moral demand in the Errata Registry.
"""


def now() -> datetime:
    return datetime.now()


def today() -> str:
    return now().strftime("%Y-%m-%d")


def ensure_dirs() -> None:
    PLAYERS.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def clean(value: Any, limit: int = 500) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit].rstrip() + ("..." if len(text) > limit else "")


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    row.setdefault("timestamp", now().isoformat(timespec="seconds"))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def read_jsonl(path: Path, days: int = 30) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    cutoff = now() - timedelta(days=days)
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
            ts = datetime.fromisoformat(str(row.get("timestamp", "")))
        except Exception:
            continue
        if ts >= cutoff:
            rows.append(row)
    return rows


def ensure_chart() -> Path:
    if not CHART.exists():
        CHART.write_text(TEMPLATE, encoding="utf-8")
    return CHART


def chart_summary() -> str:
    ensure_chart()
    return CHART.read_text(encoding="utf-8", errors="replace")


def load_actual_config() -> dict[str, Any]:
    if not ACTUAL_CONFIG.exists():
        return {}
    try:
        return json.loads(ACTUAL_CONFIG.read_text(encoding="utf-8"))
    except Exception:
        return {}


def actual_ready() -> tuple[bool, str]:
    cfg = load_actual_config()
    required = ["server_url", "sync_id"]
    missing = [key for key in required if not cfg.get(key)]
    password = cfg.get("password") or os.environ.get("ACTUAL_PASSWORD")
    password_file = cfg.get("password_file")
    if not password and password_file:
        try:
            password = Path(password_file).read_text(encoding="utf-8").strip()
        except Exception:
            password = ""
    if not password:
        missing.append("password, password_file, or ACTUAL_PASSWORD")
    if missing:
        return False, "missing " + ", ".join(missing)
    return True, "configured"


def actual_summary() -> dict[str, Any] | None:
    return actual_command("summary")


def actual_command(command: str, *extra: str, timeout: int = 300) -> dict[str, Any] | None:
    ready, _reason = actual_ready()
    if not ready:
        return None
    proc = subprocess.run(
        ["node", str(ACTUAL_API), command, *extra],
        cwd=BASE,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if proc.returncode != 0:
        append_jsonl(LOG_DIR / "ledger-errors.jsonl", {
            "kind": "actual_command_error",
            "command": command,
            "stderr": clean(proc.stderr or proc.stdout, 2000),
        })
        return None
    try:
        out = proc.stdout
        m = re.search(r"__ACTUAL_JSON_START__\s*(.*?)\s*__ACTUAL_JSON_END__", out, re.DOTALL)
        return json.loads(m.group(1) if m else out)
    except Exception:
        append_jsonl(LOG_DIR / "ledger-errors.jsonl", {
            "kind": "actual_command_parse_error",
            "command": command,
            "stdout": clean(proc.stdout, 2000),
        })
        return None


def write_actual_example() -> Path:
    if not ACTUAL_EXAMPLE.exists():
        ACTUAL_EXAMPLE.write_text(json.dumps({
            "server_url": "http://127.0.0.1:5006",
            "budget_id": "your-budget-id-or-sync-id",
            "data_dir": "data/actual-budget",
            "notes": "Copy to config/actual-budget.json after Actual is installed. Store password in ACTUAL_PASSWORD when possible.",
        }, indent=2) + "\n", encoding="utf-8")
    return ACTUAL_EXAMPLE


def actual_stub(command: str, *, dry_run: bool = False) -> dict[str, Any]:
    ready, reason = actual_ready()
    if not ready:
        return {
            "ok": False,
            "mode": "not_configured",
            "reason": reason,
            "next_step": "Install/connect Actual Budget, then create config/actual-budget.json from the example.",
        }
    if dry_run:
        return {"ok": True, "mode": "dry_run", "command": command, "reason": "Actual is configured but dry-run was requested."}
    return {
        "ok": False,
        "mode": "adapter_pending",
        "reason": "Actual API adapter is scaffolded but not enabled until dependencies are installed.",
        "command": command,
    }


def weather_from_logs() -> str:
    rows = read_jsonl(LEDGER_LOG, days=14)
    if not rows:
        return "The ledger is quiet because it has not been connected yet."
    kinds = {}
    for row in rows:
        kinds[row.get("kind", "unknown")] = kinds.get(row.get("kind", "unknown"), 0) + 1
    latest = rows[-1]
    return f"{len(rows)} ledger notes in the last 14 days; latest was {latest.get('kind', 'unknown')}."


def money_weather(*, dry_run: bool = False) -> str:
    ensure_chart()
    actual = actual_stub("money-weather", dry_run=True)
    summary = actual_summary()
    if summary:
        accounts = summary.get("accounts", [])
        on_budget = [a for a in accounts if not a.get("offbudget") and not a.get("closed")]
        total = sum(float(a.get("balance") or 0) for a in on_budget)
        uncategorized = int(summary.get("uncategorized_count") or 0)
        biggest = summary.get("uncategorized", [])[:3]
        echo_lines = []
        for t in biggest:
            amount = abs(float(t.get("amount") or 0))
            echo_lines.append(f"- {t.get('date','?')}: {t.get('payee') or t.get('imported_payee') or 'Unknown'} · ${amount:.2f}")
        lines = [
            "Gimble of the Errata Registry:",
            f"Weather: Actual is connected. {len(accounts)} account(s); ${total:.2f} on budget.",
            f"One number: {uncategorized} Unbound Echoes need categories.",
            "One risk: a large uncategorized queue creates fog; bind only a few at a time.",
            "One action: bind the three clearest Echoes first.",
        ]
        if echo_lines:
            lines.append("Largest/most recent Echoes:")
            lines.extend(echo_lines)
        lines.append("Registry clause: accuracy first. Shame is not an accounting method.")
        message = "\n".join(lines)
        if dry_run:
            print(message)
        append_jsonl(LEDGER_LOG, {"kind": "money_weather", "message": message, "actual": actual, "summary": summary})
        return message
    lines = [
        "Gimble of the Errata Registry:",
        f"Weather: {weather_from_logs()}",
        f"Actual Budget: {actual.get('mode')} — {actual.get('reason')}",
        "One number: unavailable until Actual Budget is connected.",
        "One risk: no live transaction visibility yet; this is setup fog, not failure.",
        "One action: connect Actual + SimpleFIN when ready, or tell Gimble one bill/category to add to the chart.",
        "Registry clause: accuracy first. Shame is not an accounting method.",
    ]
    message = "\n".join(lines)
    if dry_run:
        print(message)
    append_jsonl(LEDGER_LOG, {"kind": "money_weather", "message": message, "actual": actual})
    return message


def weekly_audit(*, dry_run: bool = False) -> str:
    ensure_chart()
    actual = actual_stub("weekly-audit", dry_run=True)
    summary = actual_summary()
    if summary:
        month = summary.get("month") or {}
        uncategorized = int(summary.get("uncategorized_count") or 0)
        total_spent = month.get("total_spent")
        total_balance = month.get("total_balance")
        message = "\n".join([
            "Gimble's Alchemical Audit:",
            "Connection: Actual Budget is connected.",
            f"Month: spent ${abs(float(total_spent or 0)):.2f}; balance ${float(total_balance or 0):.2f}.",
            f"Unbound Echoes: {uncategorized}.",
            "Audit rule: do not bind the whole storm. Bind three Echoes, then stop.",
        ])
        if dry_run:
            print(message)
        append_jsonl(LEDGER_LOG, {"kind": "weekly_audit", "message": message, "summary": summary})
        return message
    message = "\n".join([
        "Gimble's Alchemical Audit:",
        f"Connection: {actual.get('mode')} — {actual.get('reason')}",
        "Audit scope: pending. Once Actual is connected, this will summarize safe-to-spend, upcoming bills, uncategorized transactions, category overflow, and one Tiny Leak.",
        "Today: bind one known obligation or category name into the chart if you have the energy.",
    ])
    if dry_run:
        print(message)
    append_jsonl(LEDGER_LOG, {"kind": "weekly_audit", "message": message, "actual": actual})
    return message


def adventure_permission(*, dry_run: bool = False) -> str:
    ensure_chart()
    actual = actual_stub("adventure-permission", dry_run=True)
    message = "\n".join([
        "Gimble's Tiny Adventure Permission Slip:",
        f"Ledger connection: {actual.get('mode')} — {actual.get('reason')}",
        "Permission: undecidable from live balances until Actual is connected.",
        "Useful fallback: choose a tiny adventure with a hard cash cap you name in advance.",
        "Goblin note: a bounded joy is not a leak. It is a vessel with a lid.",
    ])
    if dry_run:
        print(message)
    append_jsonl(LEDGER_LOG, {"kind": "adventure_permission", "message": message, "actual": actual})
    return message


def question(text: str) -> int:
    ensure_chart()
    append_jsonl(LEDGER_LOG, {"kind": "question", "text": clean(text, 1000)})
    print(f"Gimble noted the question: {clean(text, 160)}")
    return 0


def status() -> int:
    ensure_chart()
    write_actual_example()
    ready, reason = actual_ready()
    rows = read_jsonl(LEDGER_LOG, days=30)
    print("GIMBLE LEDGER STATUS")
    print(f"Chart: {CHART}")
    print(f"Log: {LEDGER_LOG}")
    print(f"Actual config: {'ready' if ready else 'not ready'} ({reason})")
    print(f"Actual example: {ACTUAL_EXAMPLE}")
    print(f"Recent ledger log rows: {len(rows)}")
    if ready:
        summary = actual_summary()
        if summary:
            print(f"Actual accounts: {len(summary.get('accounts', []))}")
            print(f"Actual uncategorized: {summary.get('uncategorized_count', '?')}")
        else:
            print("Actual summary: failed; check logs/support-faculty/ledger-errors.jsonl")
    return 0


def telegram_send(message: str, *, dry_run: bool = False) -> int:
    if dry_run:
        print(message)
        return 0
    proc = subprocess.run([
        "openclaw", "message", "send",
        "--target", "8729557865",
        "--channel", "telegram",
        "--account", "enchantify",
        "--message", message,
    ], cwd=BASE, capture_output=True, text=True, timeout=90)
    if proc.returncode != 0:
        (LOG_DIR / "ledger-send-errors.log").open("a", encoding="utf-8").write(
            f"\n[{now().isoformat(timespec='seconds')}]\n{proc.stderr or proc.stdout}\n"
        )
    return proc.returncode


def brief(*, dry_run: bool = False, send: bool = False) -> int:
    message = money_weather(dry_run=False)
    if send:
        return telegram_send(message, dry_run=dry_run)
    if dry_run:
        print(message)
    return 0


def daily_sync(*, dry_run: bool = False, send: bool = False) -> int:
    ensure_chart()
    setup = actual_command("setup-gimble-categories", timeout=300) if not dry_run else {"dry_run": True}
    sync = actual_command("bank-sync", timeout=600) if not dry_run else {"dry_run": True}
    categorization = actual_command(
        "auto-categorize",
        *(["--dry-run"] if dry_run else []),
        timeout=600,
    )
    summary = actual_summary()
    append_jsonl(LEDGER_LOG, {
        "kind": "daily_sync",
        "setup": setup,
        "bank_sync": sync,
        "categorization": categorization,
        "summary": summary,
    })

    if summary:
        accounts = summary.get("accounts", [])
        on_budget = [a for a in accounts if not a.get("offbudget") and not a.get("closed")]
        total = sum(float(a.get("balance") or 0) for a in on_budget)
        uncategorized = int(summary.get("uncategorized_count") or 0)
    else:
        total = 0.0
        uncategorized = -1
    categorized = int((categorization or {}).get("categorized_count") or 0)
    seen = int((categorization or {}).get("uncategorized_seen") or 0)
    sample_rows = (categorization or {}).get("sample") or []
    sample_lines = []
    for row in sample_rows[:5]:
        amount = abs(float(row.get("amount") or 0))
        sample_lines.append(f"- {row.get('date','?')}: {row.get('payee') or 'Unknown'} · ${amount:.2f} → {row.get('category')}")

    lines = [
        "Gimble's Daily Binding:",
        "Bank sync: attempted through Actual/SimpleFIN." if not dry_run else "Bank sync: dry run only.",
        f"Binding: {categorized} Echoes bound automatically from {seen} seen.",
        f"Weather now: ${total:.2f} on budget; {uncategorized if uncategorized >= 0 else '?'} Unbound Echoes remain.",
    ]
    if sample_lines:
        lines.append("Fresh bindings:")
        lines.extend(sample_lines)
    lines.append("Registry clause: automatic does not mean judgmental. It only means the ink has a shelf.")
    message = "\n".join(lines)
    if dry_run:
        print(message)
    if send:
        return telegram_send(message, dry_run=dry_run)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Gimble's finance support loop")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Create chart and Actual config example")
    sub.add_parser("status", help="Show local finance support status")

    p = sub.add_parser("money-weather", help="Generate a money weather report")
    p.add_argument("--send", action="store_true")
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("weekly-audit", help="Generate an Alchemical Audit")
    p.add_argument("--send", action="store_true")
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("adventure-permission", help="Generate a tiny adventure permission slip")
    p.add_argument("--send", action="store_true")
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("question", help="Record a finance question")
    p.add_argument("text")

    p = sub.add_parser("brief", help="Alias for money-weather")
    p.add_argument("--send", action="store_true")
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("daily-sync", help="Sync Actual, auto-categorize transactions, and optionally send Gimble's fresh report")
    p.add_argument("--send", action="store_true")
    p.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()
    ensure_dirs()
    with cron_steward.run(f"ledger-faculty:{args.command}"):
        if args.command == "init":
            ensure_chart()
            write_actual_example()
            return status()
        if args.command == "status":
            return status()
        if args.command == "money-weather":
            message = money_weather(dry_run=args.dry_run)
            return telegram_send(message, dry_run=args.dry_run) if args.send else 0
        if args.command == "weekly-audit":
            message = weekly_audit(dry_run=args.dry_run)
            return telegram_send(message, dry_run=args.dry_run) if args.send else 0
        if args.command == "adventure-permission":
            message = adventure_permission(dry_run=args.dry_run)
            return telegram_send(message, dry_run=args.dry_run) if args.send else 0
        if args.command == "question":
            return question(args.text)
        if args.command == "brief":
            return brief(dry_run=args.dry_run, send=args.send)
        if args.command == "daily-sync":
            return daily_sync(dry_run=args.dry_run, send=args.send)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

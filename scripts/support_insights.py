#!/usr/bin/env python3
"""Shared cross-domain insight helpers for Enchantify support characters.

The support faculty should not merely recite fresh telemetry. This module reads
the same small evidence spread for Vellum, Inkrest, Gimble, and the Support
Guild, then returns deterministic observations they can speak from their own
voices.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent.parent
PLAYERS = BASE / "players"
HEARTBEAT = BASE / "HEARTBEAT.md"
FUEL_LOG = BASE / "scripts" / "fuel-log.txt"
INKREST_LOG = PLAYERS / "bj-inkrest-log.jsonl"
VELLUM_LOG = PLAYERS / "bj-vellum-log.jsonl"
LEDGER_LOG = PLAYERS / "bj-ledger-log.jsonl"
SUPPORT_MEMORY = PLAYERS / "bj-support-memory.json"
ACTUAL_API = BASE / "scripts" / "actual-api.mjs"


def now() -> datetime:
    return datetime.now()


def clean(value: Any, limit: int = 500) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit].rstrip() + ("..." if len(text) > limit else "")


def read(path: Path, limit: int | None = None) -> str:
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


def read_jsonl(path: Path, days: int = 14) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    cutoff = now() - timedelta(days=days)
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
            ts = datetime.fromisoformat(str(row.get("timestamp", "")).replace("Z", "+00:00"))
            if ts.tzinfo is not None:
                ts = ts.replace(tzinfo=None)
        except Exception:
            continue
        if ts >= cutoff:
            rows.append(row)
    return rows


def heartbeat_field(label: str) -> str:
    text = read(HEARTBEAT)
    patterns = [
        rf"\*\*{re.escape(label)}:\*\*\s*([^|\n]+)",
        rf"- \*\*{re.escape(label)}:\*\*\s*(.+)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            return clean(m.group(1), 300)
    return ""


def steps_value() -> int | None:
    text = read(HEARTBEAT)
    m = re.search(r"Steps:\s*([\d,]+)", text, re.IGNORECASE)
    if not m:
        m = re.search(r"([\d,]+)\s+steps", text, re.IGNORECASE)
    return int(m.group(1).replace(",", "")) if m else None


def latest_logged_actual_summary(days: int = 7) -> dict[str, Any] | None:
    for row in reversed(read_jsonl(LEDGER_LOG, days=days)):
        summary = row.get("summary")
        if isinstance(summary, dict) and summary.get("accounts"):
            cached = dict(summary)
            cached["source"] = f"ledger-log:{row.get('kind', 'unknown')}"
            cached["cached_at"] = row.get("timestamp")
            return cached
    return None


def actual_summary(live: bool = True) -> dict[str, Any] | None:
    if not live or not ACTUAL_API.exists():
        return latest_logged_actual_summary()
    try:
        proc = subprocess.run(
            ["node", str(ACTUAL_API), "summary"],
            cwd=BASE,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except Exception:
        return latest_logged_actual_summary()
    if proc.returncode != 0:
        return latest_logged_actual_summary()
    try:
        m = re.search(r"__ACTUAL_JSON_START__\s*(.*?)\s*__ACTUAL_JSON_END__", proc.stdout, re.DOTALL)
        data = json.loads(m.group(1) if m else proc.stdout)
        data["source"] = "live"
        return data
    except Exception:
        return latest_logged_actual_summary()


def txn_label(txn: dict[str, Any]) -> str:
    return clean(txn.get("category") or txn.get("payee") or txn.get("imported_payee") or txn.get("notes") or "Unknown", 80)


def money_patterns(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    cats = Counter()
    payees = Counter()
    spending_by_cat: dict[str, float] = defaultdict(float)
    for txn in transactions:
        amount = float(txn.get("amount") or 0)
        if amount >= 0:
            continue
        cat = clean(txn.get("category") or "Uncategorized", 80)
        payee = clean(txn.get("payee") or txn.get("imported_payee") or "Unknown", 80)
        cats[cat] += 1
        payees[payee] += 1
        spending_by_cat[cat] += abs(amount)
    top_spend = sorted(spending_by_cat.items(), key=lambda item: item[1], reverse=True)[:5]
    return {
        "category_counts": dict(cats.most_common(8)),
        "payee_counts": dict(payees.most_common(8)),
        "top_spend_categories": [{"category": k, "amount": round(v, 2)} for k, v in top_spend],
    }


def merchant_spending_signals(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Translate merchant/payee traces into non-shaming care/story signals.

    This never awards or removes Belief directly. It gives Gimble, Vellum,
    Inkrest, and the Guild plain context for what money is touching.
    """
    signals: dict[str, dict[str, Any]] = {}

    def add(kind: str, title: str, detail: str, action: str, *, weight: int = 1, payee: str = "", category: str = "") -> None:
        row = signals.setdefault(kind, {
            "kind": kind,
            "title": title,
            "details": [],
            "action": action,
            "weight": 0,
            "payees": [],
            "categories": [],
        })
        row["weight"] += weight
        if detail:
            row["details"].append(clean(detail, 180))
        if payee and payee not in row["payees"]:
            row["payees"].append(payee)
        if category and category not in row["categories"]:
            row["categories"].append(category)

    for txn in transactions:
        amount = float(txn.get("amount") or 0)
        if amount >= 0:
            continue
        payee = clean(txn.get("payee") or txn.get("imported_payee") or txn.get("notes") or "Unknown", 100)
        category = clean(txn.get("category") or "Uncategorized", 80)
        haystack = f"{payee} {category} {txn.get('notes') or ''}".lower()
        detail = f"{payee} ({category})"

        if any(term in haystack for term in ["book", "library", "barnes", "audible", "kindle", "learning"]):
            add(
                "books_learning",
                "Books or learning purchase",
                detail,
                "A relevant character may notice this as reading, learning, or project fuel, while Gimble keeps the cost clear.",
                weight=2,
                payee=payee,
                category=category,
            )
        if any(term in haystack for term in ["craft", "joann", "michaels", "art", "stationery", "paper", "thrift", "antique"]):
            add(
                "creative_supplies",
                "Creative supplies purchase",
                detail,
                "A relevant character may treat this as possible making/art/project material, while Gimble keeps the transaction plain.",
                weight=2,
                payee=payee,
                category=category,
            )
        if category in {"Groceries", "Food"} or any(term in haystack for term in ["hannaford", "market", "grocery", "food"]):
            add(
                "groceries",
                "Grocery or food purchase",
                detail,
                "Let Vellum read this as possible fuel context, while asking what was actually eaten before drawing conclusions.",
                weight=1,
                payee=payee,
                category=category,
            )
        if category == "Dining Out" or any(term in haystack for term in ["doordash", "uber eats", "mcdonald", "burger king", "subway", "dunkin", "starbucks", "pizza"]):
            add(
                "convenience_food",
                "Convenience food pattern",
                detail,
                "If repeated, Vellum should offer a low-energy Refectory Experiment; Inkrest may ask what need the purchase met.",
                weight=2,
                payee=payee,
                category=category,
            )
        if category in {"Beer", "Nicotine / Tobacco"} or any(term in haystack for term in ["cigaret", "tobacco", "beer", "liquor"]):
            add(
                "coping_signal",
                "Possible coping purchase",
                detail,
                "Treat as a care signal, not a failure. Ask what the nervous system needed and whether a gentler substitute is available.",
                weight=2,
                payee=payee,
                category=category,
            )
        if category in {"Medical", "Medication", "Therapy", "Supplements", "Fitness / Movement"}:
            add(
                "care_investment",
                "Health or care purchase",
                detail,
                "Let Vellum/Inkrest count this as real-world care infrastructure and ask whether follow-through support is needed.",
                weight=2,
                payee=payee,
                category=category,
            )
        if category in {"Doobaleedoos", "Tiny Adventures", "Apps / Tools"}:
            add(
                "project_fuel",
                "Project or adventure purchase",
                detail,
                "Let Penny/Goldweaver consider whether this supports the mission or needs a clearer category/budget plan.",
                weight=1,
                payee=payee,
                category=category,
            )

    return sorted(signals.values(), key=lambda row: (-int(row["weight"]), row["title"]))[:8]


def fuel_entry_dt(row: dict[str, Any]) -> datetime | None:
    try:
        return datetime.fromisoformat(f"{row.get('date')}T{row.get('time') or '00:00'}")
    except Exception:
        return None


def summarize_fuel_rows(rows: list[dict[str, Any]], label: str) -> str:
    if not rows:
        return f"{label}: nothing logged."
    totals = {
        key: sum(int(row.get(key, 0) or 0) for row in rows)
        for key in ("calories", "protein", "carbs", "fat", "fiber", "sodium")
    }
    items = " / ".join(str(row.get("description") or "fuel") for row in rows[-6:])
    return (
        f"{label}: {items} -- {totals['calories']} cal, {totals['protein']}g protein, "
        f"{totals['carbs']}g carbs, {totals['fat']}g fat, {totals['fiber']}g fiber, "
        f"{totals['sodium']}mg sodium."
    )


def fuel_context() -> dict[str, Any]:
    try:
        from food_log import summarize, read_entries  # type: ignore

        today_summary = summarize(days=1).replace("Today: ", "", 1)
        rows = read_entries(days=2)
        cutoff = now() - timedelta(hours=24)
        recent_rows = [row for row in rows if (fuel_entry_dt(row) or datetime.min) >= cutoff]
        recent_summary = summarize_fuel_rows(recent_rows, "Last 24h")
        tail = [
            f"{row.get('date')} {row.get('time')} | {row.get('description')} | {row.get('calories', 0)} cal | {row.get('protein', 0)}g protein"
            for row in recent_rows[-8:]
        ]
        return {
            "today": today_summary,
            "recent_24h": recent_summary,
            "combined": f"Today: {today_summary} | {recent_summary}",
            "tail": tail,
            "rows_24h": recent_rows[-12:],
        }
    except Exception:
        fuel = heartbeat_field("Fuel") or ""
        return {"today": fuel, "recent_24h": "", "combined": fuel, "tail": [], "rows_24h": []}


def build_context(*, live_actual: bool = True, actual_override: dict[str, Any] | None = None) -> dict[str, Any]:
    inkrest = read_jsonl(INKREST_LOG, days=14)
    vellum = read_jsonl(VELLUM_LOG, days=14)
    ledger = read_jsonl(LEDGER_LOG, days=14)
    mood_rows = [r for r in inkrest if r.get("kind") == "mood-word" and r.get("word")]
    prompt_rows = [r for r in inkrest if r.get("kind") == "prompt"]
    latest_mood = mood_rows[-1] if mood_rows else {}
    mood_words = [clean(r.get("word"), 60).lower() for r in mood_rows if r.get("word")]
    latest_prompt = prompt_rows[-1] if prompt_rows else {}
    unanswered = 0
    try:
        latest_mood_ts = datetime.fromisoformat(str(latest_mood.get("timestamp", "1970-01-01")).replace("Z", "+00:00"))
        if latest_mood_ts.tzinfo is not None:
            latest_mood_ts = latest_mood_ts.replace(tzinfo=None)
    except Exception:
        latest_mood_ts = datetime.min
    for row in prompt_rows:
        try:
            ts = datetime.fromisoformat(str(row.get("timestamp", "")).replace("Z", "+00:00"))
            if ts.tzinfo is not None:
                ts = ts.replace(tzinfo=None)
        except Exception:
            continue
        if ts > latest_mood_ts:
            unanswered += 1

    actual = actual_override if actual_override is not None else actual_summary(live=live_actual) or {}
    accounts = actual.get("accounts") or []
    on_budget = [a for a in accounts if not a.get("offbudget") and not a.get("closed")]
    recent_txns = (actual.get("recent") or actual.get("transactions") or [])[:20]
    month = actual.get("month") or {}
    fuel_pack = fuel_context()
    fuel = fuel_pack.get("combined") or fuel_pack.get("today") or ""
    fuel_tail = fuel_pack.get("tail") or []

    return {
        "generated_at": now().isoformat(timespec="seconds"),
        "heartbeat": {
            "focus": heartbeat_field("Focus"),
            "pacing": heartbeat_field("Pacing"),
            "fuel": fuel,
            "fuel_today": fuel_pack.get("today", ""),
            "fuel_recent_24h": fuel_pack.get("recent_24h", ""),
            "watch": heartbeat_field("Watch"),
            "location": heartbeat_field("Location"),
            "steps": steps_value(),
        },
        "mood": {
            "latest": latest_mood,
            "latest_word": clean(latest_mood.get("word") or "", 80),
            "counts": dict(Counter(mood_words).most_common(8)),
            "unanswered_prompts_since_latest_mood": unanswered,
            "latest_prompt": latest_prompt,
            "tail": mood_rows[-8:],
        },
        "vellum": {
            "latest_briefs": [r for r in vellum if r.get("kind") == "brief"][-5:],
            "fuel_tail": fuel_tail,
            "fuel_rows_24h": fuel_pack.get("rows_24h", []),
        },
        "ledger": {
            "connected": bool(actual),
            "source": actual.get("source") or "unavailable",
            "cached_at": actual.get("cached_at"),
            "account_count": len(accounts),
            "on_budget_total": round(sum(float(a.get("balance") or 0) for a in on_budget), 2),
            "uncategorized_count": actual.get("uncategorized_count"),
            "month": month,
            "recent_transactions": recent_txns[:12],
            "patterns": money_patterns(recent_txns),
            "merchant_spending_signals": merchant_spending_signals(recent_txns),
            "latest_log": ledger[-1] if ledger else {},
        },
        "support_memory": read_json(SUPPORT_MEMORY),
    }


def has_any(text: str, words: list[str]) -> bool:
    low = text.lower()
    return any(word in low for word in words)


def insight(kind: str, title: str, detail: str, action: str, confidence: str = "medium") -> dict[str, str]:
    return {
        "kind": kind,
        "title": title,
        "detail": clean(detail, 420),
        "action": clean(action, 260),
        "confidence": confidence,
    }


def derive_insights(context: dict[str, Any], *, perspective: str = "guild", limit: int = 4) -> list[dict[str, str]]:
    hb = context.get("heartbeat", {})
    mood = context.get("mood", {})
    ledger = context.get("ledger", {})
    fuel = str(hb.get("fuel") or "")
    steps = hb.get("steps")
    latest_word = str(mood.get("latest_word") or "").lower()
    txns = ledger.get("recent_transactions") or []
    cat_counts = ledger.get("patterns", {}).get("category_counts", {})
    top_spend = ledger.get("patterns", {}).get("top_spend_categories", [])
    merchant_signals = ledger.get("merchant_spending_signals") or []
    month = ledger.get("month") or {}
    uncategorized = ledger.get("uncategorized_count")
    out: list[dict[str, str]] = []

    if ledger.get("connected") and uncategorized == 0:
        out.append(insight(
            "ledger",
            "Transactions are categorized; budgeting is now the useful frontier",
            "Actual Budget is connected and the current summary shows zero uncategorized transactions. Gimble does not need to keep announcing sync as the victory; the next real question is whether dollars have jobs.",
            "Have Gimble focus on funding categories, upcoming bills, and one small recurring charge instead of repeating account balances.",
            "high",
        ))
    elif ledger.get("connected") and isinstance(uncategorized, int) and uncategorized > 0:
        out.append(insight(
            "ledger",
            "There is still transaction fog",
            f"Actual Budget is connected, but {uncategorized} transaction(s) still need categories. That is enough to blur the ledger if presented as a wall.",
            "Bind only the three clearest transactions and stop; do not dump the full queue.",
            "high",
        ))

    if float(month.get("total_budgeted") or 0) == 0 and ledger.get("connected"):
        out.append(insight(
            "ledger",
            "Actual can see money moving, but categories are unfunded",
            "The month data shows transactions and income, but total budgeted is still zero. That means Actual is functioning as visibility, not yet as envelope budgeting.",
            "Choose three starter categories to fund: bills, groceries, and tiny adventure/buffer.",
            "high",
        ))

    foodish = int(cat_counts.get("Groceries", 0)) + int(cat_counts.get("Dining Out", 0)) + int(cat_counts.get("Coffee / Snacks", 0))
    alcoholish = int(cat_counts.get("Beer", 0))
    tobaccoish = int(cat_counts.get("Nicotine / Tobacco", 0))
    if ledger.get("connected") and (foodish or alcoholish or tobaccoish) and (not fuel or "nothing logged" in fuel.lower() or "low protein" in fuel.lower()):
        signals = []
        if foodish:
            signals.append(f"{foodish} recent food/coffee/grocery transaction(s)")
        if alcoholish:
            signals.append(f"{alcoholish} beer transaction(s)")
        if tobaccoish:
            signals.append(f"{tobaccoish} nicotine/tobacco transaction(s)")
        out.append(insight(
            "cross-domain",
            "Ledger and fuel are describing the same body-day",
            f"The money trail shows {', '.join(signals)}, while the fuel read is `{clean(fuel, 140) or 'thin'}`. That is not a scolding pattern; it means Vellum should use ledger evidence as a prompt for care when food logging is sparse.",
            "Ask for one concrete fuel update before giving nutrition conclusions; then compare it with grocery/snack/beer/tobacco categories.",
            "medium",
        ))

    convenience = next((row for row in merchant_signals if row.get("kind") == "convenience_food"), None)
    if convenience and int(convenience.get("weight") or 0) >= 2:
        out.append(insight(
            "cross-domain",
            "Convenience spending may be a care flare",
            f"Actual shows a repeated convenience-food pattern: {', '.join((convenience.get('payees') or [])[:4])}. This may mean fatigue, schedule pressure, mood weather, or pleasure; it is not evidence of failure.",
            "Vellum should offer one low-energy Refectory Experiment and Inkrest should ask what need the purchase met before making a story about it.",
            "medium",
        ))

    coping = next((row for row in merchant_signals if row.get("kind") == "coping_signal"), None)
    if coping:
        out.append(insight(
            "body-psyche",
            "Some purchases may be nervous-system notes",
            f"Actual contains possible coping purchases around {', '.join((coping.get('payees') or coping.get('categories') or [])[:4])}. Gimble should name the pattern without moral verdict; Inkrest and Vellum can help offer substitute supports.",
            "Ask one concrete question: what was the purchase doing for BJ in that moment: relief, stimulation, transition, hunger, or companionship?",
            "medium",
        ))

    learning = next((row for row in merchant_signals if row.get("kind") == "books_learning"), None)
    creative = next((row for row in merchant_signals if row.get("kind") == "creative_supplies"), None)
    if learning or creative:
        source = learning or creative
        out.append(insight(
            "ledger",
            source.get("title", "Merchant trace supports the story"),
            f"Actual includes story-positive purchases: {', '.join((source.get('payees') or [])[:4])}. These are possible Library/Academy hooks, not just expenses.",
            "Let Gimble surface the cost and let a relevant NPC notice the meaning; do not automatically award Belief without an explicit rule.",
            "medium",
        ))

    if latest_word in {"nauseous", "sick", "queasy"} or has_any(fuel, ["nause", "low protein", "nothing logged"]):
        out.append(insight(
            "body-psyche",
            "Interpret mood through the body before story",
            f"The latest mood/fuel spread contains `{latest_word or 'no mood word'}` and `{clean(fuel, 150) or 'no fuel signal'}`. Inkrest should not over-symbolize this before checking food, hydration, medication timing, and rest.",
            "Use a body-first check: water, simple food if tolerated, and a non-demanding mood word later.",
            "medium",
        ))

    if isinstance(steps, int) and steps < 2500:
        out.append(insight(
            "body",
            "Movement is a tiny-dose target today",
            f"Heartbeat reports {steps:,} steps. That is low enough that Vellum and Inkrest should treat movement as nervous-system support, not fitness pressure.",
            "Suggest a two-minute walk or five slow sit-to-stands; do not frame it as catching up.",
            "high",
        ))
    elif isinstance(steps, int) and steps >= 6000:
        out.append(insight(
            "body",
            "The body already carried real load",
            f"Heartbeat reports {steps:,} steps. Vellum can count the day as physically engaged instead of piling on another exercise demand.",
            "Favor protein, hydration, and recovery over extra movement unless BJ asks.",
            "high",
        ))

    if mood.get("unanswered_prompts_since_latest_mood", 0) > 1:
        out.append(insight(
            "psyche",
            "Mood check-ins may need less friction",
            f"{mood.get('unanswered_prompts_since_latest_mood')} Inkrest prompts appear after the last logged mood. This is a usability signal, not avoidance evidence.",
            "Let Inkrest ask for one word only and accept late replies without making them a narrative scene.",
            "medium",
        ))
    elif latest_word:
        out.append(insight(
            "psyche",
            "The one-word channel is working",
            f"The latest Inkrest word is `{latest_word}`. There is enough fresh signal for a gentle check-in without pretending the word is the whole person.",
            "Use the word as weather: acknowledge it, then ask for one next-hour support action only if useful.",
            "medium",
        ))

    if top_spend:
        biggest = top_spend[0]
        out.append(insight(
            "ledger",
            "Top recent spend has a name",
            f"The largest recent spending category in the current transaction window is {biggest.get('category')} at about ${float(biggest.get('amount') or 0):.2f}.",
            "Gimble should turn this into one clear question: does this category need funding, a boundary, or simply accurate acceptance?",
            "medium",
        ))

    if not out:
        out.append(insight(
            "support",
            "No strong cross-domain pattern yet",
            "The spread is readable but not conclusive. That is still useful: the faculty should collect one more mood word, one fuel update, and one ledger snapshot before making claims.",
            "Keep gathering low-friction data; no dramatic interpretation today.",
            "low",
        ))

    weights = {
        "gimble": {"ledger": 0, "cross-domain": 1, "body-psyche": 3, "psyche": 4, "body": 4, "support": 5},
        "vellum": {"body": 0, "body-psyche": 1, "cross-domain": 2, "ledger": 4, "psyche": 4, "support": 5},
        "inkrest": {"psyche": 0, "body-psyche": 1, "cross-domain": 2, "body": 3, "ledger": 4, "support": 5},
        "guild": {"cross-domain": 0, "body-psyche": 1, "ledger": 2, "body": 2, "psyche": 2, "support": 5},
    }
    ranking = weights.get(perspective, weights["guild"])
    out.sort(key=lambda row: (ranking.get(row["kind"], 9), row["title"]))
    return out[:limit]


def format_insights(insights: list[dict[str, str]], *, heading: str = "Cross-domain insights") -> str:
    lines = [heading + ":"]
    for row in insights:
        lines.append(f"- {row['title']}: {row['detail']} Next: {row['action']}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic cross-domain support insights")
    parser.add_argument("player", nargs="?", default="bj")
    parser.add_argument("--perspective", choices=["guild", "gimble", "vellum", "inkrest"], default="guild")
    parser.add_argument("--limit", type=int, default=4)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-live-actual", action="store_true")
    args = parser.parse_args()
    _ = args.player
    context = build_context(live_actual=not args.no_live_actual)
    insights = derive_insights(context, perspective=args.perspective, limit=args.limit)
    if args.json:
        print(json.dumps({"context": context, "insights": insights}, indent=2, ensure_ascii=False, default=str))
    else:
        print(format_insights(insights, heading=f"{args.perspective.title()} insights"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

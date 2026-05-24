#!/usr/bin/env python3
"""Daily Support Guild meeting for Enchantify's support characters.

One LLM call may turn fresh body, mood, and ledger data into a single
in-world council artifact. If the gateway is unavailable, the deterministic
fallback still files a useful daily meeting instead of going silent.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
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
MEMORY = BASE / "memory"
PLAYERS = BASE / "players"
LOG_DIR = BASE / "logs" / "support-faculty"
GUILD_DIR = MEMORY / "support-faculty" / "guild"
GUILD_HTML_DIR = GUILD_DIR / "html"
GUILD_PDF_DIR = GUILD_DIR / "pdf"
HEARTBEAT = BASE / "HEARTBEAT.md"
VELLUM_CHART = PLAYERS / "bj-vellum-chart.md"
INKREST_CHART = PLAYERS / "bj-therapy-chart.md"
LEDGER_CHART = PLAYERS / "bj-ledger-chart.md"
GOLDWATER_CHART = PLAYERS / "bj-goldwater-chart.md"
BELLKEEPER_CHART = PLAYERS / "bj-bellkeeper-chart.md"
VELLUM_LOG = PLAYERS / "bj-vellum-log.jsonl"
INKREST_LOG = PLAYERS / "bj-inkrest-log.jsonl"
LEDGER_LOG = PLAYERS / "bj-ledger-log.jsonl"
BELLKEEPER_LOG = PLAYERS / "bj-bellkeeper-log.jsonl"
SUPPORT_MEMORY = PLAYERS / "bj-support-memory.json"
PUBLISHING_DIR = MEMORY / "publishing"
PENNY_STRATEGY = PUBLISHING_DIR / "editorial-strategy.md"
PENNY_CONSENT_QUEUE = PUBLISHING_DIR / "consent-queue.json"
PENNY_PROPOSALS = PUBLISHING_DIR / "proposals"
PENNY_BRIEFS = PUBLISHING_DIR / "briefs"
GOLDWATER_DESK = PUBLISHING_DIR / "applied-abundance"
GOLDWATER_BRIEFS = GOLDWATER_DESK / "briefs"
GOLDWATER_OFFERS = GOLDWATER_DESK / "offers"
GOLDWATER_LOG = BASE / "logs" / "publishing" / "goldwater.jsonl"
SUPPORT_RESEARCH_DIR = MEMORY / "support-faculty" / "research"
ACTUAL_API = BASE / "scripts" / "actual-api.mjs"
SECRETS_ENV = BASE / "config" / "secrets.env"
TARGET = "8729557865"
CHANNEL = "telegram"
ACCOUNT = "enchantify"

sys.path.insert(0, str(BASE / "scripts"))
import cron_steward  # type: ignore
import journal_artifact  # type: ignore
import support_insights  # type: ignore
try:
    from food_log import summarize as summarize_fuel  # type: ignore
except Exception:
    summarize_fuel = None


GUILD_RESEARCH_LANES = {
    "Vellum": [
        "Longevity lane: sleep regularity, protein adequacy, resistance stimulus, blood pressure readiness, fiber, alcohol/caffeine timing, medications and supplement-safety questions.",
        "Evidence posture: strong evidence for movement, sleep consistency, BP control, cardiometabolic basics, protein/resistance training in aging; cautious source-family language for cutting-edge claims.",
    ],
    "Inkrest": [
        "Therapy lane: narrative therapy, unique outcomes, preferred identity, ACT/CBT defusion, parts/body checks, consciousness/brain-study translation, and daydream material when present.",
        "Evidence posture: practical psychotherapy frameworks and measurement-based mood trends; no diagnosis, no symbolic certainty, no trauma excavation without consent.",
    ],
    "Gimble": [
        "Ledger lane: Actual Budget, SimpleFIN freshness, uncategorized transactions, unfunded envelopes, upcoming bills, food/coffee/beer/tobacco patterns, tiny adventure affordability.",
        "Evidence posture: accuracy without shame; money is behavioral weather and resource allocation, not moral worth.",
    ],
    "Penny": [
        "Press lane: public-safe fragments, Wonder Compass education, open-source Enchantify storytelling, Patreon path, X/Instagram/Reddit/YouTube/TikTok drafts, consent queue and performance notes.",
        "Evidence posture: every public piece should teach Notice, Embark, Sense, Write, or Rest while protecting private life.",
    ],
    "Bellkeeper": [
        "Time lane: calendar shape, upcoming appointments, transition support, recovery windows, proactive Today Pages, evening scraps, weekly openings.",
        "Evidence posture: time support reduces friction only when it respects energy, consent, and actual schedule constraints.",
    ],
    "Goldweaver": [
        "Abundance lane: ethical monetization, offer ladders, field kits, Patreon experiments, pricing, product backlog, tiny shippable revenue actions.",
        "Evidence posture: sell curation, beauty, convenience, official canon, and community; never monetize guilt or surveillance.",
    ],
}

GUILD_EXPERIMENT_LIBRARY = {
    "body_time": {
        "name": "Same-Door Morning",
        "owner": "Vellum + Bellkeeper",
        "action": "Choose one morning anchor for seven days: medication time, first light, or first protein. Bellkeeper protects the cue; Vellum watches the body signal.",
        "metric": "mood word, fuel visibility, sleep/wake regularity, and whether workday starts feel less effortful.",
    },
    "psyche_body": {
        "name": "Weather Then Body",
        "owner": "Inkrest + Vellum",
        "action": "Every mood check-in may add one body word: hungry, caffeinated, sore, rested, wired, low-fuel, hydrated.",
        "metric": "whether body context changes the story Inkrest would otherwise tell.",
    },
    "ledger_fuel": {
        "name": "Refectory Ledger Bridge",
        "owner": "Gimble + Vellum",
        "action": "When fuel logging is sparse, Gimble may surface food/coffee/grocery clues as neutral prompts, never conclusions.",
        "metric": "one concrete fuel update before nutrition advice; no shame language.",
    },
    "press_offer": {
        "name": "One Public Door",
        "owner": "Penny + Goldweaver",
        "action": "Penny selects one public-safe fragment; Goldweaver decides whether it is free post, Patreon jewel, or field-kit seed.",
        "metric": "one drafted asset with consent status and one next shippable revenue step.",
    },
    "calendar_creation": {
        "name": "Protected Making Window",
        "owner": "Bellkeeper + Penny + Goldweaver",
        "action": "Find one realistic window for publishing/product work and define the minimum deliverable before it begins.",
        "metric": "window proposed, accepted/skipped, and whether it ended with a saved artifact.",
    },
}


def now() -> datetime:
    return datetime.now()


def today() -> str:
    return now().strftime("%Y-%m-%d")


def ensure_dirs() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    GUILD_DIR.mkdir(parents=True, exist_ok=True)
    GUILD_HTML_DIR.mkdir(parents=True, exist_ok=True)
    GUILD_PDF_DIR.mkdir(parents=True, exist_ok=True)


def read(path: Path, limit: int | None = None) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[:limit] if limit else text


def clean(value: Any, limit: int = 500) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit].rstrip() + ("..." if len(text) > limit else "")


def guild_phrase(value: Any, limit: int = 500) -> str:
    text = clean(value, limit)
    text = re.sub(r"\s*Status:\s*ask the player[^.]*\.", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*Status:\s*", " ", text, flags=re.IGNORECASE)
    return clean(text, limit)


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


def latest_files(path: Path, pattern: str = "*.md", limit: int = 5) -> list[dict[str, str]]:
    if not path.exists():
        return []
    rows = []
    for file in sorted(path.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
        text = read(file, 1400)
        title = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        rows.append({
            "name": file.name,
            "path": str(file),
            "title": clean(title.group(1) if title else file.stem, 180),
            "mtime": datetime.fromtimestamp(file.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
            "excerpt": clean(text, 900),
        })
    return rows


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


def current_fuel_summary() -> str:
    try:
        context = support_insights.fuel_context()
        fuel = context.get("combined") or context.get("today") or ""
        if fuel:
            return guild_phrase(str(fuel), 500)
    except Exception:
        pass
    if summarize_fuel:
        try:
            return guild_phrase(summarize_fuel(days=1).replace("Today: ", "", 1), 500)
        except Exception:
            pass
    return guild_phrase(heartbeat_field("Fuel"), 500)


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
    bellkeeper = read_jsonl(BELLKEEPER_LOG, days=10)
    penny_queue = load_json(PENNY_CONSENT_QUEUE)
    penny_items = penny_queue.get("items", []) if isinstance(penny_queue.get("items"), list) else []
    penny_pending = [
        item for item in penny_items
        if str(item.get("status") or "pending") in {
            "pending", "needs_review", "needs_revision", "drafted", "draft", "queued",
            "awaiting_consent", "consent_required", "ready_for_review",
        }
    ]
    goldwater_logs = read_jsonl(GOLDWATER_LOG, days=14)
    actual = actual_summary()
    accounts = (actual or {}).get("accounts", [])
    on_budget = [a for a in accounts if not a.get("offbudget") and not a.get("closed")]
    insight_context = support_insights.build_context(live_actual=False, actual_override=actual)
    guild_insights = support_insights.derive_insights(insight_context, perspective="guild", limit=5)
    insight_heartbeat = insight_context.get("heartbeat", {})
    insight_vellum = insight_context.get("vellum", {})
    context = {
        "date": today(),
        "heartbeat": {
            "focus": heartbeat_field("Focus"),
            "pacing": heartbeat_field("Pacing"),
            "fuel": insight_heartbeat.get("fuel") or current_fuel_summary(),
            "fuel_today": insight_heartbeat.get("fuel_today", ""),
            "fuel_recent_24h": insight_heartbeat.get("fuel_recent_24h", ""),
            "watch": heartbeat_field("Watch"),
            "location": heartbeat_field("Location"),
            "steps": steps_value(),
        },
        "charts": {
            "vellum": clean(read(VELLUM_CHART, 3500), 3500),
            "inkrest": clean(read(INKREST_CHART, 3500), 3500),
            "ledger": clean(read(LEDGER_CHART, 2500), 2500),
            "bellkeeper": clean(read(BELLKEEPER_CHART, 2500), 2500),
            "goldwater": clean(read(GOLDWATER_CHART, 2800), 2800),
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
            "fuel_log_tail": insight_vellum.get("fuel_tail", []),
            "latest_ledger_message": clean(ledger_latest.get("message", ""), 900),
            "bellkeeper_tail": bellkeeper[-6:],
            "latest_bellkeeper": bellkeeper[-1] if bellkeeper else {},
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
        "press_and_abundance": {
            "penny_strategy": clean(read(PENNY_STRATEGY, 2500), 2500),
            "penny_pending_count": len(penny_pending),
            "penny_pending_tail": penny_pending[-6:],
            "latest_penny_proposals": latest_files(PENNY_PROPOSALS, limit=4),
            "latest_penny_briefs": latest_files(PENNY_BRIEFS, limit=4),
            "latest_goldwater_briefs": latest_files(GOLDWATER_BRIEFS, limit=4),
            "latest_goldwater_offers": latest_files(GOLDWATER_OFFERS, limit=4),
            "goldwater_log_tail": goldwater_logs[-6:],
        },
        "recent_support_research": latest_files(SUPPORT_RESEARCH_DIR, limit=6),
        "guild_research_lanes": GUILD_RESEARCH_LANES,
        "guild_experiment_library": GUILD_EXPERIMENT_LIBRARY,
        "cross_domain_insights": guild_insights,
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
    raw_model = os.environ.get("SUPPORT_GUILD_MODEL") or secrets.get("SUPPORT_GUILD_MODEL") or "openclaw/gpt55"
    timeout_raw = os.environ.get("SUPPORT_GUILD_TIMEOUT") or secrets.get("SUPPORT_GUILD_TIMEOUT") or "600"
    try:
        timeout = max(180, int(timeout_raw))
    except ValueError:
        timeout = 600
    return port, token, normalize_model(raw_model), timeout


def prompt_context(context: dict[str, Any]) -> dict[str, Any]:
    """Compact the council packet so the model spends tokens synthesizing, not reading dumps."""
    press = context.get("press_and_abundance") or {}
    support_memory = context.get("support_memory") or {}
    return {
        "date": context.get("date"),
        "heartbeat": context.get("heartbeat"),
        "recent": context.get("recent"),
        "actual_budget": context.get("actual_budget"),
        "cross_domain_insights": context.get("cross_domain_insights"),
        "recent_support_research": context.get("recent_support_research"),
        "guild_research_lanes": context.get("guild_research_lanes"),
        "guild_experiment_library": context.get("guild_experiment_library"),
        "press_and_abundance": {
            "penny_pending_count": press.get("penny_pending_count"),
            "penny_pending_tail": press.get("penny_pending_tail"),
            "latest_penny_proposals": press.get("latest_penny_proposals"),
            "latest_penny_briefs": press.get("latest_penny_briefs"),
            "latest_goldwater_briefs": press.get("latest_goldwater_briefs"),
            "latest_goldwater_offers": press.get("latest_goldwater_offers"),
            "goldwater_log_tail": press.get("goldwater_log_tail"),
            "penny_strategy_excerpt": clean(press.get("penny_strategy"), 1200),
        },
        "support_memory": {
            "experiments": (support_memory.get("experiments") or [])[-10:],
            "guild_meetings": (support_memory.get("guild_meetings") or [])[-3:],
        },
        "chart_principles": {
            "vellum": clean((context.get("charts") or {}).get("vellum"), 1200),
            "inkrest": clean((context.get("charts") or {}).get("inkrest"), 1200),
            "ledger": clean((context.get("charts") or {}).get("ledger"), 900),
            "bellkeeper": clean((context.get("charts") or {}).get("bellkeeper"), 900),
            "goldwater": clean((context.get("charts") or {}).get("goldwater"), 1000),
        },
    }


def prompt_for(context: dict[str, Any]) -> str:
    return f"""Write today's Enchantify Support Character Guild Meeting as a detailed storybook-journal council brief.

This is one daily synthesis artifact, not separate status reports. Present it as
Dr. Elowen Vellum, Dr. Selene Inkrest, Gimble of the Errata Registry,
Penny Blackletter, Bellkeeper Elian Quill, and Professor Bastion Goldweaver
sharing notes and agreeing on a tiny support plan for BJ.

Rules:
- Be specific to the data. Do not use boilerplate, generic wellness copy, or generic business advice.
- Make connections between body/fuel/longevity, mood/consciousness/narrative identity, money, calendar/time, Penny's content work, and Goldweaver's monetization work.
- Include at least one surprising but sane cross-domain insight.
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
- Penny may discuss public-safe content, pending drafts, marketing/editorial opportunities,
  and the mission of spreading Wonder Compass, Patreon, and open-source Enchantify.
- Bellkeeper may discuss the shape of time, upcoming support, transition care, and what
  the Book should prepare or not prepare.
- Goldweaver may discuss ethical monetization, offer ladders, product seeds, Patreon,
  pricing, and the smallest shippable revenue action.
- Use guild_research_lanes and recent_support_research as the council's research shelf.
- If you discuss research, use source-family language unless a precise citation is present in context. Do not invent paper titles, authors, years, URLs, or fake browsing.
- Use cross_domain_insights as hard observations. They are not flavor; they are
  the deterministic support spread across heartbeat, fuel, mood, and ledger.
- Treat actual_budget.connected/source as the authoritative ledger freshness signal.
  Do not call bank sync dry-run or disconnected merely because an older ledger
  log row contains dry-run test data.
- End with no more than three tiny actions. They should coordinate the whole guild; do not give each character separate homework.
- Include one explicit experiment card with owner, duration, minimum version, metric, review date, and stop/scale-down signals.
- Include one content/revenue thread that Penny and Goldweaver can carry forward, but protect private data.
- Include a "Do Not Push Today" section.
- Keep it warm, practical, and in-world, like a meeting minute tucked into a magical field journal.

Use exactly this Markdown structure:

# Support Guild Meeting — {context["date"]}

## Guild Weather

## Research Shelf

## Connection Map

## Dr. Vellum — Body and Longevity

## Dr. Inkrest — Mood, Consciousness, and Story

## Gimble — Ledger and Friction

## Penny — Press and Public Signal

## Bellkeeper — Time and Proactive Support

## Professor Goldweaver — Offers and Abundance

## Shared Hypothesis

## Experiment Card

## Cross-Domain Insights

## Press and Revenue Thread

## Tiny Plan

## Do Not Push Today

## Artifact

Current data JSON:
{json.dumps(prompt_context(context), ensure_ascii=False, indent=2, default=str)[:18000]}
"""


def call_llm(context: dict[str, Any]) -> str:
    port, token, model, timeout = gateway_cfg()
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You write detailed Enchantify support-faculty council briefs. "
                    "The output is practical, specific, non-shaming, researched, and in-world. "
                    "Reply only with the requested Markdown artifact."
                ),
            },
            {"role": "user", "content": prompt_for(context)},
        ],
        "temperature": 0.74,
        "max_tokens": 3800,
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


def choose_guild_experiment(context: dict[str, Any]) -> dict[str, str]:
    hb = context.get("heartbeat", {})
    press = context.get("press_and_abundance", {})
    budget = context.get("actual_budget", {})
    if hb.get("fuel") and "nothing logged" in str(hb.get("fuel")).lower():
        return GUILD_EXPERIMENT_LIBRARY["ledger_fuel"]
    if press.get("penny_pending_count", 0) or press.get("latest_goldwater_briefs"):
        return GUILD_EXPERIMENT_LIBRARY["press_offer"]
    if budget.get("connected"):
        return GUILD_EXPERIMENT_LIBRARY["psyche_body"]
    return GUILD_EXPERIMENT_LIBRARY["body_time"]


def fallback_meeting(context: dict[str, Any], reason: str = "") -> str:
    hb = context["heartbeat"]
    recent = context["recent"]
    budget = context["actual_budget"]
    mood = recent.get("mood_words") or {}
    latest_mood = recent.get("latest_mood") or {}
    latest_word = latest_mood.get("word") or next(iter(mood.keys()), "not yet logged")
    pending = recent.get("inkrest_pending") or {}
    fuel = guild_phrase(hb.get("fuel") or "fuel signal unavailable")
    steps = hb.get("steps")
    uncategorized = budget.get("uncategorized_count")
    insights = context.get("cross_domain_insights") or []
    press = context.get("press_and_abundance") or {}
    latest_penny = (press.get("latest_penny_briefs") or press.get("latest_penny_proposals") or [{}])[0]
    latest_goldwater = (press.get("latest_goldwater_briefs") or press.get("latest_goldwater_offers") or [{}])[0]
    latest_bellkeeper = recent.get("latest_bellkeeper") or {}
    primary = insights[0] if insights else {}
    experiment = choose_guild_experiment(context)
    research_files = context.get("recent_support_research") or []
    body_action = next((row.get("action") for row in insights if row.get("kind") in {"body", "body-psyche"}), "water, one protein/fiber anchor, and a movement dose small enough to actually happen.")
    ledger_action = next((row.get("action") for row in insights if row.get("kind") == "ledger"), "Bind a small number, never the whole storm.")
    insight_lines = [
        f"- {guild_phrase(row.get('title'))}: {guild_phrase(row.get('detail'), 700)} Next: {guild_phrase(row.get('action'), 500)}"
        for row in insights[:4]
    ]
    lines = [
        f"# Support Guild Meeting — {context['date']}",
        "",
        "## Guild Weather",
        f"The table has enough signal for a real synthesis: latest mood weather is `{latest_word}`, fuel reads `{fuel}`, ledger visibility is {'online' if budget.get('connected') else 'not yet online'}, and the Press wing has {press.get('penny_pending_count', 0)} piece(s) waiting for consent or review.",
        "",
        "## Research Shelf",
        "- Vellum brings the longevity lane: sleep, protein, resistance, BP readiness, caffeine/alcohol timing, medication/supplement safety, and what can be tried without pretending to be a doctor.",
        "- Inkrest brings narrative therapy plus consciousness/brain-study translation: mood as weather, unique outcomes, rumination loops, daydream material, and body-first interpretation.",
        "- Gimble brings Actual Budget and SimpleFIN as behavior data, not moral evidence.",
        "- Penny and Goldweaver bring the public mission: Wonder Compass into more hands, $1 Patreon traffic, open-source Enchantify made legible, and one ethical offer at a time.",
        *(f"- Recent support research: {clean(item.get('title') or item.get('name'), 160)}." for item in research_files[:3]),
        "",
        "## Connection Map",
        f"- **Body ↔ Mood:** `{latest_word}` should not be interpreted without fuel, sleep, medication timing, and recovery context.",
        f"- **Ledger ↔ Nutrition:** Actual can reveal food/coffee/beer/grocery patterns when fuel logs are sparse, but only as a neutral prompt.",
        f"- **Calendar ↔ Creation:** Bellkeeper should find realistic making windows before Penny or Goldweaver ask for output.",
        f"- **Content ↔ Money:** Penny's best public-safe fragment becomes Goldweaver's smallest offer test, not a giant launch.",
        "",
        "## Dr. Vellum — Body and Longevity",
        f"Body note: steps are {steps if steps is not None else 'unknown'}. Today's useful hinge: {body_action}",
        "",
        "## Dr. Inkrest — Mood, Consciousness, and Story",
        f"Psyche note: the latest logged mood word is `{latest_word}`. "
        f"{'A check-in is currently awaiting reply.' if pending else 'No fresh check-in is pending.'} "
        "Treat the word as weather, not identity. Her consciousness-study question today is simple: what changes when the body is checked before the story explains itself?",
        "",
        "## Gimble — Ledger and Friction",
        f"Ledger note: Actual Budget is {'connected' if budget.get('connected') else 'not connected'}. Uncategorized transactions: {uncategorized if uncategorized is not None else 'unknown'}. {ledger_action}",
        "",
        "## Penny — Press and Public Signal",
        f"Press note: {press.get('penny_pending_count', 0)} draft(s) appear to be awaiting consent. Latest editorial scrap: {latest_penny.get('title', 'no fresh Penny draft visible')}. Penny's job today is to choose the public-safe door, not turn the whole life into content.",
        "",
        "## Bellkeeper — Time and Proactive Support",
        f"Time note: latest bell is {clean(latest_bellkeeper.get('kind') or latest_bellkeeper.get('title') or 'quiet', 120)}. Bellkeeper recommends preparing the next page around actual available time, not imaginary energy.",
        "",
        "## Professor Goldweaver — Offers and Abundance",
        f"Abundance note: latest offer lens is {latest_goldwater.get('title', 'not yet filed')}. Goldweaver wants one small sellable artifact shaped before any grand launch is allowed to enter the room.",
        "",
        "## Shared Hypothesis",
        guild_phrase(primary.get("detail"), 900) or "Today improves most if the support faculty lowers friction, chooses one public-safe opportunity, and protects BJ's energy while the project learns how to pay rent.",
        "",
        "## Experiment Card",
        f"- **Name:** {experiment['name']}",
        f"- **Owner:** {experiment['owner']}",
        "- **Duration:** 7 days",
        f"- **Daily action:** {experiment['action']}",
        "- **Minimum version:** one sentence, one cue, or one saved draft. No catch-up.",
        f"- **Metric:** {experiment['metric']}",
        f"- **Review date:** {(now() + timedelta(days=7)).strftime('%Y-%m-%d')}",
        "- **Stop / scale-down signals:** dread, shame, sleep disruption, privacy concern, or the sense that the council has become another boss.",
        "",
        "## Cross-Domain Insights",
        *(insight_lines or ["- No strong cross-domain pattern yet; collect one more mood word, one fuel update, and one ledger snapshot."]),
        "",
        "## Press and Revenue Thread",
        f"Penny should choose one public-safe fragment from the latest briefs/proposals. Goldweaver should label it as one of three things only: free post, $1 Patreon invitation, or field-kit seed. If it touches health, intimacy, family, finances, or therapy, it stays private or becomes anonymized theme only.",
        "",
        "## Tiny Plan",
        f"1. {insights[0].get('action') if len(insights) > 0 else 'Log one real fuel item if anything has been missed.'}",
        f"2. {insights[1].get('action') if len(insights) > 1 else 'Let Penny and Goldweaver choose one public-safe Field Kit or Patreon door to shape, not five.'}",
        f"3. {insights[2].get('action') if len(insights) > 2 else 'Let Bellkeeper protect one recovery or creation window so the plan has somewhere to land.'}",
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


def title_from_meeting(text: str) -> str:
    m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    return clean(m.group(1), 140) if m else f"Support Guild Meeting — {today()}"


def meeting_markdown_to_html(text: str) -> str:
    body: list[str] = []
    in_list = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            if in_list:
                body.append("</ul>")
                in_list = False
            continue
        if line.startswith("<!--"):
            continue
        if line.startswith("# "):
            if in_list:
                body.append("</ul>")
                in_list = False
            body.append(f"<h1>{html.escape(line[2:].strip())}</h1>")
        elif line.startswith("## "):
            if in_list:
                body.append("</ul>")
                in_list = False
            body.append(f"<h2>{html.escape(line[3:].strip())}</h2>")
        elif line.startswith("### "):
            if in_list:
                body.append("</ul>")
                in_list = False
            body.append(f"<h3>{html.escape(line[4:].strip())}</h3>")
        elif line.startswith(("- ", "* ")):
            if not in_list:
                body.append("<ul>")
                in_list = True
            body.append(f"<li>{html.escape(line[2:].strip())}</li>")
        else:
            if in_list:
                body.append("</ul>")
                in_list = False
            body.append(f"<p>{html.escape(line)}</p>")
    if in_list:
        body.append("</ul>")

    css = """
    :root { color-scheme: light; }
    body {
      margin: 0;
      background: #161712;
      color: #2d241b;
      font-family: Georgia, 'Times New Roman', serif;
      line-height: 1.6;
    }
    .page {
      max-width: 860px;
      margin: 34px auto;
      padding: 52px min(7vw, 72px);
      background:
        radial-gradient(circle at 14% 10%, rgba(119, 80, 34, .15), transparent 25%),
        radial-gradient(circle at 88% 16%, rgba(35, 90, 82, .13), transparent 22%),
        linear-gradient(90deg, rgba(86,54,24,.10), transparent 12%, transparent 88%, rgba(86,54,24,.10)),
        #eadcc4;
      box-shadow: 0 20px 80px rgba(0,0,0,.45);
      border: 1px solid rgba(58, 40, 23, .35);
      position: relative;
    }
    .page:before {
      content: "";
      position: absolute;
      inset: 18px;
      border: 1px solid rgba(63, 44, 27, .22);
      pointer-events: none;
    }
    h1, h2, h3 { font-weight: 500; text-align: center; letter-spacing: .03em; }
    h1 { font-size: 2.15rem; margin: 0 0 1.4rem; color: #2b2118; }
    h2 { font-size: 1.25rem; margin: 2rem 0 .7rem; color: #473421; border-top: 1px solid rgba(71,52,33,.22); padding-top: 1rem; }
    h3 { font-size: 1.05rem; color: #31534c; }
    p { font-size: 1.04rem; margin: .75rem 0; }
    ul { padding-left: 1.35rem; }
    li { margin: .42rem 0; }
    .stamp {
      text-align: center;
      color: #70412f;
      margin-top: 2rem;
      font-size: .82rem;
      letter-spacing: .12em;
      text-transform: uppercase;
    }
    """
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title_from_meeting(text))}</title>
  <style>{css}</style>
</head>
<body>
  <main class="page">
    {''.join(body)}
    <div class="stamp">Filed by the Support Character Guild · {html.escape(today())}</div>
  </main>
</body>
</html>
"""


def maybe_pdf(html_path: Path, pdf_path: Path) -> tuple[bool, str]:
    tool = shutil.which("wkhtmltopdf")
    if tool:
        proc = subprocess.run([tool, "--quiet", str(html_path), str(pdf_path)], cwd=BASE, capture_output=True, text=True, timeout=120)
        if proc.returncode == 0 and pdf_path.exists():
            return True, f"wkhtmltopdf rendered {pdf_path}"
        return False, clean(proc.stderr or proc.stdout or "wkhtmltopdf failed", 500)

    chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    if chrome.exists():
        proc = subprocess.run(
            [
                str(chrome),
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                f"--print-to-pdf={pdf_path}",
                html_path.resolve().as_uri(),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode == 0 and pdf_path.exists():
            return True, f"Google Chrome headless rendered {pdf_path}"
        return False, clean(proc.stderr or proc.stdout or "Google Chrome headless PDF render failed", 500)

    cups = shutil.which("cupsfilter")
    if cups:
        proc = subprocess.run([cups, "-m", "application/pdf", str(html_path)], cwd=BASE, capture_output=True, timeout=120)
        if proc.returncode == 0 and proc.stdout:
            pdf_path.write_bytes(proc.stdout)
            return True, f"cupsfilter rendered {pdf_path}"
        detail = (proc.stderr or proc.stdout or b"cupsfilter failed").decode("utf-8", errors="replace")
        return False, clean(detail, 500)

    return False, "No PDF renderer found."


def render_meeting_artifacts(text: str, *, dry_run: bool = False) -> dict[str, str]:
    date_str = today()
    return journal_artifact.render(
        text,
        GUILD_DIR,
        date_str,
        title=f"Support Guild Meeting — {date_str}",
        subtitle="A council page from the support faculty",
        footer="Filed by Vellum, Inkrest, Gimble, Penny, Bellkeeper, and Goldweaver",
        accent="#31534c",
        dry_run=dry_run,
    )


def summarize_for_telegram(text: str, path: Path, outputs: dict[str, str] | None = None) -> str:
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
    if outputs and outputs.get("pdf"):
        parts.extend(["", f"Full minutes PDF attached: {Path(outputs['pdf']).name}"])
    elif outputs and outputs.get("html"):
        parts.extend(["", f"Full minutes HTML attached: {Path(outputs['html']).name}"])
    else:
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
        "press_and_abundance": {
            "penny_pending_count": (context.get("press_and_abundance") or {}).get("penny_pending_count", 0),
            "latest_penny_briefs": (context.get("press_and_abundance") or {}).get("latest_penny_briefs", [])[:2],
            "latest_goldwater_briefs": (context.get("press_and_abundance") or {}).get("latest_goldwater_briefs", [])[:2],
            "latest_goldwater_offers": (context.get("press_and_abundance") or {}).get("latest_goldwater_offers", [])[:2],
        },
        "cross_domain_insights": context.get("cross_domain_insights", []),
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
        outputs = render_meeting_artifacts(text)
        update_support_memory(path, text, context)
        append_jsonl(LOG_DIR / "guild.jsonl", {
            "kind": "guild_meeting",
            "path": str(path),
            "html": outputs.get("html", ""),
            "pdf": outputs.get("pdf", ""),
            "pdf_detail": outputs.get("pdf_detail", ""),
            "llm_error": llm_error,
            "sent": False,
        })
    if dry_run:
        outputs = render_meeting_artifacts(text, dry_run=True)
    if send:
        message = summarize_for_telegram(text, path, outputs)
        skip, digest, reason = cron_steward.should_skip_duplicate(
            "support-guild",
            message,
            cooldown_hours=20,
            scope=today(),
        )
        if skip and not dry_run:
            cron_steward.mark_skipped("support-guild", reason, scope=today(), fingerprint=digest)
            return 0
        media = None
        if not dry_run:
            media = Path(outputs["pdf"]) if outputs.get("pdf") else Path(outputs["html"])
        rc = send_telegram(message, media if media and media.exists() else None, dry_run=dry_run, silent=silent)
        if rc == 0 and not dry_run:
            cron_steward.mark_delivered("support-guild", message, scope=today(), path=str(path))
            append_jsonl(LOG_DIR / "guild.jsonl", {
                "kind": "guild_delivery",
                "path": str(path),
                "media": str(media) if media and media.exists() else "",
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

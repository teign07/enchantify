#!/usr/bin/env python3
"""Self-healing obligation queue for narrative stewardship.

The steward does not edit story files. It converts narrative-health findings
into explicit obligations that scene/context/closeout rituals can satisfy.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent.parent
STATE_FILE = BASE / "config" / "narrative-steward-state.json"
HEALTH_SCRIPT = BASE / "scripts" / "narrative-health.py"


def load_health_module():
    spec = importlib.util.spec_from_file_location("narrative_health", HEALTH_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules["narrative_health"] = module
    spec.loader.exec_module(module)
    return module


def load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {"obligations": [], "history": []}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"obligations": [], "history": []}


def save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(STATE_FILE)


def slug(text: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return text[:72] or "obligation"


def stable_id(kind: str, summary: str) -> str:
    digest = hashlib.sha1(f"{kind}:{summary}".encode("utf-8")).hexdigest()[:8]
    return f"{kind}:{slug(summary)}:{digest}"


def thread_name_from_summary(summary: str) -> str:
    m = re.match(r"(.+?)\s+is pushing\b", summary)
    return m.group(1).strip() if m else ""


def obligation_from_finding(finding: dict[str, Any], arc: dict[str, Any]) -> dict[str, Any] | None:
    area = finding.get("area", "")
    level = finding.get("level", "WATCH")
    summary = finding.get("summary", "")
    detail = finding.get("detail", "")

    if area == "Threads" and "without a delivered beat" in summary:
        thread = thread_name_from_summary(summary)
        recovery_arc = str(arc.get("genre", "")).lower().startswith("recovery")
        guidance = (
            "Surface this as a bounded optional beat. Protect LIFE choice and ordinary care; do not let overdue drama seize the whole scene."
            if recovery_arc
            else "Surface or explicitly defer one grounded beat in the next suitable scene."
        )
        return {
            "kind": "thread_beat_due",
            "severity": level,
            "title": f"{thread or 'Thread'} needs a delivered or deferred beat",
            "summary": summary,
            "detail": detail,
            "thread": thread,
            "scene_hook": guidance,
            "satisfy_by": "Deliver a grounded beat, explicitly defer/cool it in-scene, or update closeout thread_updates after a beat lands.",
            "choice_pressure": "ARC",
        }

    if area == "Thread Seeds":
        return {
            "kind": "seed_triage_due",
            "severity": level,
            "title": "Thread seeds need triage",
            "summary": summary,
            "detail": detail,
            "scene_hook": "If one seed naturally appears in play, promote only that one; otherwise keep seeds ambient and do not multiply subplots.",
            "satisfy_by": "Promote one seed to a real thread, explicitly defer the rest, or record why none are ready.",
            "choice_pressure": "SURPRISE",
        }

    if area == "Long Memory":
        return {
            "kind": "memory_refresh_due",
            "severity": level,
            "title": "Long memory needs refresh",
            "summary": summary,
            "detail": detail,
            "scene_hook": "Use recent realized scenes over stale alive-moment summaries; avoid leaning on old pressure as if it is current.",
            "satisfy_by": "Refresh player story memory from recent scene ledger and closeout events.",
            "choice_pressure": "CONTEXT",
        }

    if area == "Simulation" and level in {"WARN", "ALERT"}:
        return {
            "kind": "drama_budget_guard",
            "severity": level,
            "title": "Simulation needs arc-tone balancing",
            "summary": summary,
            "detail": detail,
            "scene_hook": "Current arc tone outranks raw event volume. Let recovery/rest, daily life, and quiet care remain real story motion.",
            "satisfy_by": "Choose scene mode/drama budget that matches the current arc, or explicitly justify a dramatic exception.",
            "choice_pressure": "LIFE",
        }

    return None


def today_iso() -> str:
    return date.today().isoformat()


def is_deferred_active(obligation: dict[str, Any]) -> bool:
    until = obligation.get("deferred_until", "")
    if not until:
        return False
    try:
        return date.fromisoformat(until) >= date.today()
    except ValueError:
        return False


def refresh(player: str) -> dict[str, Any]:
    health = load_health_module().build_report(player)
    state = load_state()
    prior = {item.get("id"): item for item in state.get("obligations", []) if item.get("id")}
    now = datetime.now().isoformat(timespec="seconds")
    active: list[dict[str, Any]] = []

    for finding in health.get("findings", []):
        if finding.get("level") == "OK":
            continue
        obligation = obligation_from_finding(finding, health.get("arc", {}))
        if not obligation:
            continue
        obligation["id"] = stable_id(obligation["kind"], obligation["summary"])
        old = prior.get(obligation["id"], {})
        status = old.get("status", "open")
        if status == "resolved":
            status = "open"
        obligation.update({
            "status": status,
            "created_at": old.get("created_at", now),
            "updated_at": now,
            "last_seen_at": now,
            "source": "narrative-health",
            "player": player,
        })
        if old.get("deferred_until") and is_deferred_active(old):
            obligation["status"] = "deferred"
            obligation["deferred_until"] = old.get("deferred_until")
            obligation["defer_reason"] = old.get("defer_reason", "")
        active.append(obligation)

    active_ids = {item["id"] for item in active}
    history = state.get("history", [])
    for old_id, old in prior.items():
        if old_id not in active_ids and old.get("status") != "resolved":
            old["status"] = "resolved"
            old["resolved_at"] = now
            old["resolved_reason"] = "health finding cleared"
            history.append(old)

    state = {
        "generated_at": now,
        "player": player,
        "health_status": health.get("status"),
        "health_score": health.get("score"),
        "arc": health.get("arc", {}),
        "obligations": active,
        "history": history[-50:],
    }
    save_state(state)
    return state


def open_obligations(state: dict[str, Any], include_deferred: bool = False) -> list[dict[str, Any]]:
    statuses = {"open", "deferred"} if include_deferred else {"open"}
    return [item for item in state.get("obligations", []) if item.get("status", "open") in statuses]


def mark_status(obligation_id: str, status: str, reason: str = "", days: int = 1) -> dict[str, Any]:
    state = load_state()
    now = datetime.now().isoformat(timespec="seconds")
    found = False
    for item in state.get("obligations", []):
        if item.get("id") != obligation_id:
            continue
        found = True
        item["status"] = status
        item["updated_at"] = now
        if status == "resolved":
            item["resolved_at"] = now
            item["resolved_reason"] = reason
        if status == "deferred":
            item["deferred_at"] = now
            item["deferred_until"] = (date.today() + timedelta(days=days)).isoformat()
            item["defer_reason"] = reason
        break
    if not found:
        raise SystemExit(f"obligation not found: {obligation_id}")
    save_state(state)
    return state


def print_text(state: dict[str, Any], include_deferred: bool = False) -> None:
    print(f"NARRATIVE STEWARD: {state.get('health_status', '?')} ({state.get('health_score', '?')}/100)")
    obligations = open_obligations(state, include_deferred=include_deferred)
    if not obligations:
        print("Open obligations: none")
        return
    print(f"Open obligations: {len(obligations)}")
    for item in obligations:
        print(f"- {item['id']}")
        print(f"  {item.get('severity', 'WATCH')} {item.get('title', '')}")
        print(f"  Hook: {item.get('scene_hook', '')}")
        print(f"  Satisfy: {item.get('satisfy_by', '')}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Maintain narrative self-healing obligations.")
    parser.add_argument("player", nargs="?", default="bj")
    parser.add_argument("--refresh", action="store_true", help="Refresh obligations from narrative-health.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--include-deferred", action="store_true")
    parser.add_argument("--resolve", help="Mark an obligation resolved by id.")
    parser.add_argument("--defer", help="Mark an obligation deferred by id.")
    parser.add_argument("--reason", default="")
    parser.add_argument("--days", type=int, default=1)
    args = parser.parse_args()

    if args.resolve:
        state = mark_status(args.resolve, "resolved", args.reason)
    elif args.defer:
        state = mark_status(args.defer, "deferred", args.reason, args.days)
    elif args.refresh or not STATE_FILE.exists():
        state = refresh(args.player)
    else:
        state = load_state()

    if args.json:
        print(json.dumps(state, indent=2, ensure_ascii=False))
    else:
        print_text(state, include_deferred=args.include_deferred)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

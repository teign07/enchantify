#!/usr/bin/env python3
"""Lifecycle ledger for autonomous NPC simulation actions.

Simulation actions should become playable hooks, not evaporate into flavor.
This module records open actions, surfaces the freshest unresolved hooks, and
marks them noticed when later delivered scenes mention their actor/thread/deed.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent
ACTION_LEDGER = BASE_DIR / "logs" / "npc-action-lifecycle.jsonl"


def _append(event: dict[str, Any]) -> None:
    ACTION_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(event)
    payload.setdefault("timestamp", datetime.now().isoformat())
    with ACTION_LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _read_events() -> list[dict[str, Any]]:
    if not ACTION_LEDGER.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in ACTION_LEDGER.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def _compact(text: str, limit: int = 360) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _keywords(text: str) -> list[str]:
    words = []
    for word in re.findall(r"[A-Za-z][A-Za-z'\-]{3,}", text or ""):
        clean = word.strip("'-.").lower()
        if clean in {
            "through",
            "pressure",
            "source",
            "result",
            "acted",
            "belief",
            "thread",
            "academy",
            "students",
            "before",
            "after",
        }:
            continue
        if clean not in words:
            words.append(clean)
    return words[:12]


def record_open_action(entry: dict[str, Any]) -> None:
    """Record one simulation action as an unresolved playable hook."""
    if entry.get("kind") != "action":
        return
    action_id = entry.get("id")
    if not action_id:
        return
    narrative = entry.get("narrative") or ""
    hidden = entry.get("hidden_effect") or ""
    _append({
        "event": "opened",
        "action_id": action_id,
        "status": "open",
        "actor": entry.get("actor", ""),
        "actor_kind": entry.get("actor_kind", ""),
        "chapter": entry.get("chapter", ""),
        "action": entry.get("action", ""),
        "thread_name": entry.get("thread_name", ""),
        "thread_id": entry.get("thread_id", ""),
        "target": entry.get("target", ""),
        "intensity": entry.get("intensity", ""),
        "priority": entry.get("priority", "NORMAL"),
        "narrative": _compact(narrative, 520),
        "hidden_effect": _compact(hidden, 300),
        "reason": _compact(entry.get("reason", ""), 300),
        "keywords": _keywords(" ".join([narrative, hidden, entry.get("actor", ""), entry.get("thread_name", ""), entry.get("target", "")])),
        "source_timestamp": entry.get("timestamp", ""),
    })


def open_actions(limit: int = 8) -> list[dict[str, Any]]:
    """Return unresolved action records, newest/highest priority first."""
    latest: dict[str, dict[str, Any]] = {}
    closed: set[str] = set()
    for event in _read_events():
        action_id = event.get("action_id")
        if not action_id:
            continue
        if event.get("event") in {"noticed", "resolved", "expired"}:
            closed.add(action_id)
        elif event.get("event") == "opened" and action_id not in closed:
            latest[action_id] = event

    records = [item for action_id, item in latest.items() if action_id not in closed]
    records.sort(
        key=lambda item: (
            1 if item.get("priority") == "HIGH" else 0,
            item.get("source_timestamp") or item.get("timestamp") or "",
        ),
        reverse=True,
    )
    return records[:limit]


def render_open_actions(limit: int = 5) -> list[str]:
    lines = []
    for action in open_actions(limit=limit):
        target = f" -> {action['target']}" if action.get("target") else ""
        lines.append(
            f"{action.get('actor')} {action.get('action', '').replace('_', ' ')}{target} "
            f"via {action.get('thread_name')}: {action.get('narrative')}"
        )
    return lines


def _mentioned(action: dict[str, Any], text: str) -> bool:
    lower = (text or "").lower()
    if not lower:
        return False
    strong_terms = [
        action.get("actor", ""),
        action.get("thread_name", ""),
        action.get("target", ""),
    ]
    strong_hits = sum(1 for term in strong_terms if term and term.lower() in lower)
    keyword_hits = sum(1 for word in action.get("keywords", []) if word and word in lower)
    return strong_hits >= 2 or (strong_hits >= 1 and keyword_hits >= 2) or keyword_hits >= 4


def mark_actions_noticed_from_scene(scene_text: str, scene_id: str = "", player: str = "bj") -> list[str]:
    """Mark open actions noticed when scene text clearly carries them forward."""
    noticed: list[str] = []
    for action in open_actions(limit=30):
        action_id = action.get("action_id")
        if not action_id or not _mentioned(action, scene_text):
            continue
        _append({
            "event": "noticed",
            "action_id": action_id,
            "status": "noticed",
            "player": player,
            "scene_id": scene_id,
            "actor": action.get("actor", ""),
            "thread_name": action.get("thread_name", ""),
        })
        noticed.append(action_id)
    return noticed


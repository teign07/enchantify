#!/usr/bin/env python3
"""Write daily Bleed awareness into entity memory without LLM calls."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent
SCRIPTS = BASE / "scripts"
RIPPLES_LOG = BASE / "logs" / "bleed-ripples.jsonl"
STATE_PATH = BASE / "memory" / "entities" / "bleed-awareness.json"

sys.path.insert(0, str(SCRIPTS))
import entity_memory  # noqa: E402


SECTION_WATCHERS: dict[str, list[str]] = {
    "FUEL": ["Dr. Elowen Vellum"],
    "VELLUM": ["Dr. Elowen Vellum"],
    "PROVISIONS": ["Dr. Elowen Vellum"],
    "INKREST": ["Dr. Selene Inkrest"],
    "GIMBLE": ["Gimble of the Errata Registry"],
    "GOBLINEXCHANGE": ["Gimble of the Errata Registry"],
    "EXCHANGE": ["Gimble of the Errata Registry"],
    "EDITOR": ["Penny Blackletter"],
    "PRESS": ["Penny Blackletter"],
    "MARKET": ["Penny Blackletter", "Professor Bastion Goldweaver"],
    "WARREPORT": ["Dusk Thorn"],
    "TALISMAN": ["Dusk Thorn"],
    "CLASSIFIEDS": ["Headmistress Thorne"],
    "HEADLINE": ["Penny Blackletter"],
    "FEATURE": ["Penny Blackletter"],
    "GOSSIP": ["Penny Blackletter"],
}

ENTITY_DENYLIST = {
    "by staff correspondent the",
    "office hours",
    "difficult pages",
    "goblin finance support",
    "first quarter",
    "simple joys",
}


def clean(text: str, limit: int = 420) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def load_ripples() -> list[dict[str, Any]]:
    if not RIPPLES_LOG.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in RIPPLES_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def latest_issue(rows: list[dict[str, Any]]) -> tuple[str, int, list[dict[str, Any]]]:
    if not rows:
        return "", 0, []

    def key(row: dict[str, Any]) -> tuple[str, int]:
        try:
            issue = int(row.get("issue_number") or 0)
        except (TypeError, ValueError):
            issue = 0
        return str(row.get("date") or ""), issue

    date, issue = max(key(row) for row in rows)
    return date, issue, [row for row in rows if key(row) == (date, issue)]


def stance_for(entity: str, row: dict[str, Any]) -> str:
    options = [
        "may reference this as corridor talk",
        "has reason to notice this public story",
        "may treat this as pressure in the room",
        "can mention this as the latest issue's interpretation",
        "is likely carrying this as fresh Academy gossip",
    ]
    seed = f"{entity}|{row.get('id')}|{row.get('section')}"
    idx = int(hashlib.sha1(seed.encode("utf-8")).hexdigest(), 16) % len(options)
    return options[idx]


def entities_for(row: dict[str, Any]) -> list[str]:
    section = str(row.get("section") or "").upper()
    raw_entities = [
        str(item).strip()
        for item in (row.get("entities") or [])
        if str(item).strip() and str(item).strip().lower() not in ENTITY_DENYLIST
    ]
    haystack = " ".join([
        str(row.get("section") or ""),
        str(row.get("pressure") or ""),
        str(row.get("detail") or ""),
        " ".join(raw_entities),
    ])
    names: list[str] = []
    seen: set[str] = set()

    for name in entity_memory.detect_entities(haystack, extra_names=[], limit=10):
        low = name.lower()
        if low not in seen:
            seen.add(low)
            names.append(name)

    for name in raw_entities:
        low = name.lower()
        if low not in seen and (low.startswith("the ") or len(name.split()) <= 3):
            seen.add(low)
            names.append(name)

    for watcher in SECTION_WATCHERS.get(section, []):
        low = watcher.lower()
        if low not in seen:
            seen.add(low)
            names.append(watcher)

    return names[:8]


def build_state() -> dict[str, Any]:
    date, issue, rows = latest_issue(load_ripples())
    by_entity: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        for name in entities_for(row):
            entry = {
                "ripple_id": row.get("id", ""),
                "date": row.get("date") or date,
                "issue_number": row.get("issue_number") or issue,
                "section": row.get("section", ""),
                "pressure": clean(str(row.get("pressure") or ""), 180),
                "detail": clean(str(row.get("detail") or ""), 420),
                "stance": stance_for(name, row),
                "weight": row.get("weight", 1),
            }
            by_entity.setdefault(name, []).append(entry)

    for name, entries in list(by_entity.items()):
        entries.sort(key=lambda item: int(item.get("weight") or 0), reverse=True)
        by_entity[name] = entries[:4]

    return {
        "date": date,
        "issue_number": issue,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": str(RIPPLES_LOG.relative_to(BASE)),
        "entities": by_entity,
    }


def update() -> dict[str, Any]:
    state = build_state()
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(STATE_PATH)

    for entity in sorted(state.get("entities") or {}):
        entity_memory.render_entity_file(entity)
    return state


def status() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return {}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["update", "status"], nargs="?", default="update")
    args = parser.parse_args()

    data = update() if args.command == "update" else status()
    entities = sorted((data.get("entities") or {}).keys()) if isinstance(data, dict) else []
    print(
        f"BLEED_MEMORY: issue={data.get('issue_number') or '?'} date={data.get('date') or '?'} "
        f"entities={len(entities)}"
    )
    for name in entities[:16]:
        print(f"- {name}: {len(data['entities'].get(name) or [])} notice(s)")


if __name__ == "__main__":
    main()

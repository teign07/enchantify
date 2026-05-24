#!/usr/bin/env python3
"""Deterministic per-entity memory for Enchantify characters and presences.

The goal is continuity, not biography. Simulation, outreach, and live scenes
write small factual memory events here; story-context later injects compact,
relevant memory so characters can remember what they did and what BJ said.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent
CHARACTERS_MD = BASE / "lore" / "characters.md"
MEMORY_DIR = BASE / "memory" / "entities"
LOG_PATH = BASE / "logs" / "entity-memory.jsonl"
BLEED_AWARENESS_PATH = MEMORY_DIR / "bleed-awareness.json"

MAX_SUMMARY = 700
MAX_ENTITY_EVENTS = 80


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def clean(text: str, limit: int = MAX_SUMMARY) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return slug or "unknown"


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def load_rows(limit: int = 0) -> list[dict[str, Any]]:
    if not LOG_PATH.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows[-limit:] if limit else rows


def canonical_character_names() -> list[str]:
    if not CHARACTERS_MD.exists():
        return []
    text = CHARACTERS_MD.read_text(encoding="utf-8", errors="replace")
    names: list[str] = []
    seen: set[str] = set()

    def add(name: str) -> None:
        name = clean(re.sub(r"\s*[—-].*$", "", re.sub(r"\s*\([^)]*\)", "", name)), 120)
        if not name or len(name) < 3:
            return
        low = name.lower()
        if low in seen:
            return
        seen.add(low)
        names.append(name)

    for line in text.splitlines():
        m = re.match(r"^###\s+(.+)$", line.strip())
        if m:
            add(m.group(1))
        m = re.match(r"^\*\*(.+?)\*\*", line.strip())
        if m:
            add(m.group(1))
    return names


def detect_entities(text: str, extra_names: list[str] | None = None, limit: int = 8) -> list[str]:
    """Detect known entity names in a scene or note."""
    hay = text or ""
    names = list(extra_names or []) + canonical_character_names()
    found: list[str] = []
    seen: set[str] = set()
    for name in sorted(names, key=len, reverse=True):
        if not name or name.lower() in seen:
            continue
        pattern = r"(?<!\w)" + re.escape(name) + r"(?!\w)"
        if re.search(pattern, hay, flags=re.IGNORECASE):
            seen.add(name.lower())
            found.append(name)
        if len(found) >= limit:
            break
    return found


def parse_cast_names(cast_text: str) -> list[str]:
    if not cast_text:
        return []
    names = []
    known = canonical_character_names()
    lowered = cast_text.lower()
    for name in known:
        if name.lower() in lowered:
            names.append(name)
    return names[:8]


def entity_rows(entity: str) -> list[dict[str, Any]]:
    low = entity.lower()
    rows = [row for row in load_rows() if str(row.get("entity", "")).lower() == low]
    return rows[-MAX_ENTITY_EVENTS:]


def load_bleed_awareness() -> dict[str, Any]:
    if not BLEED_AWARENESS_PATH.exists():
        return {}
    try:
        data = json.loads(BLEED_AWARENESS_PATH.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def entity_bleed_awareness(entity: str, limit: int = 3) -> list[dict[str, Any]]:
    data = load_bleed_awareness()
    entities = data.get("entities") if isinstance(data.get("entities"), dict) else {}
    for name, rows in entities.items():
        if str(name).lower() == entity.lower() and isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)][:limit]
    return []


def record_event(
    entity: str,
    kind: str,
    summary: str,
    *,
    timestamp: str = "",
    source: str = "",
    player: str = "bj",
    thread: str = "",
    target: str = "",
    scene_id: str = "",
    metadata: dict[str, Any] | None = None,
    render: bool = True,
) -> dict[str, Any]:
    entity = clean(entity, 120)
    row = {
        "timestamp": timestamp or now_iso(),
        "entity": entity,
        "kind": clean(kind, 80),
        "summary": clean(summary),
        "source": clean(source, 80),
        "player": clean(player, 80),
        "thread": clean(thread, 160),
        "target": clean(target, 160),
        "scene_id": clean(scene_id, 160),
        "metadata": metadata or {},
    }
    append_jsonl(LOG_PATH, row)
    if render:
        render_entity_file(entity)
    return row


def event_key(row: dict[str, Any]) -> str:
    meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    return "|".join([
        str(row.get("entity", "")),
        str(row.get("kind", "")),
        str(row.get("source", "")),
        str(row.get("scene_id", "")),
        str(meta.get("source_id", "") or meta.get("outreach_id", "")),
        str(row.get("summary", ""))[:120],
    ]).lower()


def record_event_once(*args: Any, **kwargs: Any) -> dict[str, Any] | None:
    preview = {
        "entity": args[0] if len(args) > 0 else kwargs.get("entity", ""),
        "kind": args[1] if len(args) > 1 else kwargs.get("kind", ""),
        "summary": args[2] if len(args) > 2 else kwargs.get("summary", ""),
        "source": kwargs.get("source", ""),
        "scene_id": kwargs.get("scene_id", ""),
        "metadata": kwargs.get("metadata") or {},
    }
    existing = {event_key(row) for row in load_rows()}
    if event_key(preview) in existing:
        return None
    return record_event(*args, **kwargs)


def record_simulation_action(action: Any, *, source: str = "world-pulse") -> None:
    summary = action.visible_trace or f"{action.npc} moved around {action.thread_name}."
    record_event(
        action.npc,
        "simulation_action",
        summary,
        source=source,
        thread=action.thread_name,
        target=action.target or "",
        metadata={
            "action": action.action,
            "intensity": action.intensity,
            "actor_kind": action.actor_kind,
            "chapter": action.chapter,
            "belief_cost": action.belief_cost,
            "hidden_effect": action.hidden_effect,
            "reason": action.reason,
        },
    )


def record_simulation_consequence(item: Any, *, source: str = "world-pulse") -> None:
    record_event(
        item.name,
        "belief_shift",
        f"Belief shifted {item.before} -> {item.after} ({item.delta:+d}). {item.reason}",
        source=source,
        metadata={"kind": item.kind, "before": item.before, "after": item.after, "delta": item.delta},
    )


def record_outreach_sent(sender: str, message: str, *, player: str = "bj", source: str = "reach-out", event_id: str = "") -> None:
    record_event(
        sender,
        "outreach_sent",
        f"Reached out to BJ: \"{clean(message, 360)}\"",
        source=source,
        player=player,
        metadata={"outreach_id": event_id},
    )


def record_outreach_reply(sender: str, original: str, reply: str, *, player: str = "bj", source: str = "outreach-memory", event_id: str = "") -> None:
    record_event(
        sender,
        "player_reply",
        f"BJ replied: \"{clean(reply, 360)}\" after the outreach: \"{clean(original, 260)}\"",
        source=source,
        player=player,
        metadata={"outreach_id": event_id},
    )


def record_scene_memory(
    *,
    player: str,
    scene_id: str,
    text: str,
    cast: str = "",
    title: str = "",
    source: str = "live-scene",
    timestamp: str = "",
) -> list[str]:
    extra = parse_cast_names(cast)
    entities = detect_entities(text, extra_names=extra, limit=6)
    for name in extra:
        if name.lower() not in {item.lower() for item in entities}:
            entities.append(name)
        if len(entities) >= 6:
            break
    if not entities:
        return []
    summary = summarize_scene_text(text, title=title)
    writer = record_event_once if source.endswith("backfill") else record_event
    for entity in entities:
        writer(
            entity,
            "live_scene",
            summary,
            timestamp=timestamp,
            source=source,
            player=player,
            scene_id=scene_id,
            metadata={"title": title, "source_id": scene_id},
        )
    return entities


def summarize_scene_text(text: str, *, title: str = "") -> str:
    lines = []
    for line in (text or "").splitlines():
        line = re.sub(r"^\[[^\]]+\]\s*", "", line).strip()
        if not line or line.startswith("What do you do?"):
            continue
        if re.match(r"^\d+\.\s+", line):
            continue
        lines.append(line)
    body = clean(" ".join(lines[:8]), 520)
    if title:
        return f"{title}: {body}"
    return body


def compact_memory(entity: str, limit: int = 6) -> dict[str, Any]:
    rows = entity_rows(entity)
    recent = rows[-limit:]
    sim = [r for r in rows if r.get("kind") == "simulation_action"][-3:]
    replies = [r for r in rows if r.get("kind") == "player_reply"][-3:]
    scenes = [r for r in rows if r.get("kind") == "live_scene"][-3:]
    bleed_awareness = entity_bleed_awareness(entity, limit=3)
    return {
        "entity": entity,
        "recent": [format_row(r) for r in recent],
        "simulation": [format_row(r) for r in sim],
        "player_replies": [format_row(r) for r in replies],
        "live_scenes": [format_row(r) for r in scenes],
        "bleed_awareness": bleed_awareness,
    }


def format_row(row: dict[str, Any]) -> str:
    stamp = str(row.get("timestamp", ""))[:16].replace("T", " ")
    kind = row.get("kind", "memory")
    tail = ""
    if row.get("thread"):
        tail = f" [{row.get('thread')}]"
    return clean(f"{stamp} {kind}{tail}: {row.get('summary', '')}", 360)


def render_entity_file(entity: str) -> Path:
    rows = entity_rows(entity)
    path = MEMORY_DIR / f"{slugify(entity)}.md"
    path.parent.mkdir(parents=True, exist_ok=True)

    by_kind: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_kind[str(row.get("kind") or "memory")].append(row)

    lines = [
        f"# {entity} — Entity Memory",
        "",
        "*Generated by `scripts/entity_memory.py`. Edit the source events through the script, not by hand.*",
        "",
        "## Current Carry",
    ]
    for row in rows[-8:]:
        lines.append(f"- {format_row(row)}")
    if not rows:
        lines.append("- No recorded entity memory yet.")

    awareness = entity_bleed_awareness(entity, limit=4)
    lines.extend(["", "## Latest Bleed Notice"])
    if awareness:
        for item in awareness:
            issue = item.get("issue_number") or "?"
            section = item.get("section") or "Bleed"
            stance = item.get("stance") or "may reference this as public rumor"
            detail = clean(str(item.get("detail") or item.get("hook") or ""), 320)
            lines.append(f"- Issue #{issue} [{section}]: {stance}. {detail}")
    else:
        lines.append("- No current issue-specific notice.")

    lines.extend(["", "## Relationship With BJ"])
    relationship = by_kind.get("player_reply", []) + by_kind.get("live_scene", []) + by_kind.get("outreach_sent", [])
    for row in sorted(relationship, key=lambda r: str(r.get("timestamp", "")))[-8:]:
        lines.append(f"- {format_row(row)}")
    if not relationship:
        lines.append("- No direct relationship memories recorded yet.")

    lines.extend(["", "## Simulation Actions"])
    for row in by_kind.get("simulation_action", [])[-8:]:
        lines.append(f"- {format_row(row)}")
    if not by_kind.get("simulation_action"):
        lines.append("- No simulation actions recorded yet.")

    lines.extend(["", "## Belief And Consequence"])
    for row in by_kind.get("belief_shift", [])[-8:]:
        lines.append(f"- {format_row(row)}")
    if not by_kind.get("belief_shift"):
        lines.append("- No belief shifts recorded yet.")

    lines.extend(["", "## Full Event Tail"])
    for row in rows[-30:]:
        lines.append(f"- {format_row(row)}")

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def render_all() -> int:
    entities = sorted({str(row.get("entity", "")) for row in load_rows() if row.get("entity")})
    for entity in entities:
        render_entity_file(entity)
    return len(entities)


def recent_log_paths(root: Path, pattern: str, days: int) -> list[Path]:
    if not root.exists():
        return []
    cutoff = datetime.now() - timedelta(days=days)
    paths = []
    for path in sorted(root.glob(pattern)):
        try:
            if datetime.fromtimestamp(path.stat().st_mtime) >= cutoff:
                paths.append(path)
        except OSError:
            continue
    return paths


def backfill_recent(days: int = 7, limit: int = 240) -> dict[str, int]:
    counts = {"simulation": 0, "outreach": 0, "scenes": 0}

    for path in recent_log_paths(BASE / "logs" / "simulations", "*.jsonl", days):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("kind") == "action" and row.get("actor"):
                written = record_event_once(
                    row.get("actor"),
                    "simulation_action",
                    row.get("narrative") or row.get("raw") or "",
                    timestamp=row.get("timestamp", ""),
                    source="simulation-backfill",
                    thread=row.get("thread_name", ""),
                    target=row.get("target", ""),
                    metadata={
                        "source_id": row.get("id", ""),
                        "action": row.get("action", ""),
                        "belief_cost": row.get("belief_cost"),
                        "hidden_effect": row.get("hidden_effect", ""),
                    },
                )
                counts["simulation"] += 1 if written else 0
            elif row.get("kind") == "consequence" and row.get("name"):
                written = record_event_once(
                    row.get("name"),
                    "belief_shift",
                    row.get("narrative") or row.get("raw") or "",
                    timestamp=row.get("timestamp", ""),
                    source="simulation-backfill",
                    metadata={"source_id": row.get("id", ""), "delta": row.get("delta")},
                )
                counts["simulation"] += 1 if written else 0

    outreach_path = BASE / "logs" / "character-outreach.jsonl"
    if outreach_path.exists():
        for line in outreach_path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("kind") == "sent" and row.get("sender"):
                written = record_event_once(
                    row.get("sender"),
                    "outreach_sent",
                    f"Reached out to BJ: \"{clean(row.get('message', ''), 360)}\"",
                    timestamp=row.get("timestamp", ""),
                    source="outreach-backfill",
                    player=row.get("player", "bj"),
                    metadata={"source_id": row.get("id", "")},
                )
                counts["outreach"] += 1 if written else 0
            elif row.get("kind") == "reply" and row.get("sender"):
                written = record_event_once(
                    row.get("sender"),
                    "player_reply",
                    f"BJ replied: \"{clean(row.get('reply', ''), 360)}\" after the outreach: \"{clean(row.get('original_message', ''), 260)}\"",
                    timestamp=row.get("timestamp", ""),
                    source="outreach-backfill",
                    player=row.get("player", "bj"),
                    metadata={"source_id": row.get("id", "")},
                )
                counts["outreach"] += 1 if written else 0

    for path in recent_log_paths(BASE / "logs" / "scene-ledger", "*.jsonl", days):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not row.get("delivery_ok"):
                continue
            text = "\n".join(part for part in [row.get("text", ""), row.get("voice", "")] if part)
            before = len(load_rows())
            record_scene_memory(
                player=row.get("player", "bj"),
                scene_id=row.get("scene_id", ""),
                text=text,
                cast=row.get("cast", ""),
                title=row.get("title", ""),
                source="scene-backfill",
                timestamp=row.get("recorded_at", ""),
            )
            counts["scenes"] += max(0, len(load_rows()) - before)

    return counts


def rebuild_from_backfill(days: int = 7, limit: int = 240) -> dict[str, int]:
    if LOG_PATH.exists():
        LOG_PATH.unlink()
    if MEMORY_DIR.exists():
        for path in MEMORY_DIR.glob("*.md"):
            path.unlink()
    return backfill_recent(days=days, limit=limit)


def main() -> int:
    parser = argparse.ArgumentParser(description="Record and render Enchantify entity memory.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    rec = sub.add_parser("record")
    rec.add_argument("--entity", required=True)
    rec.add_argument("--kind", required=True)
    rec.add_argument("--summary", required=True)
    rec.add_argument("--source", default="")
    rec.add_argument("--player", default="bj")
    rec.add_argument("--thread", default="")
    rec.add_argument("--target", default="")
    rec.add_argument("--scene-id", default="")

    detect = sub.add_parser("detect")
    detect.add_argument("text")

    ctx = sub.add_parser("context")
    ctx.add_argument("--entity", action="append", required=True)
    ctx.add_argument("--limit", type=int, default=6)
    ctx.add_argument("--json", action="store_true")

    sub.add_parser("render-all")

    backfill = sub.add_parser("backfill")
    backfill.add_argument("--days", type=int, default=7)
    backfill.add_argument("--limit", type=int, default=240)

    rebuild = sub.add_parser("rebuild")
    rebuild.add_argument("--days", type=int, default=7)
    rebuild.add_argument("--limit", type=int, default=240)

    args = parser.parse_args()
    if args.cmd == "record":
        row = record_event(
            args.entity,
            args.kind,
            args.summary,
            source=args.source,
            player=args.player,
            thread=args.thread,
            target=args.target,
            scene_id=args.scene_id,
        )
        print(json.dumps(row, indent=2, ensure_ascii=False))
        return 0
    if args.cmd == "detect":
        print(json.dumps(detect_entities(args.text), indent=2, ensure_ascii=False))
        return 0
    if args.cmd == "context":
        payload = [compact_memory(entity, args.limit) for entity in args.entity]
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            for item in payload:
                print(f"ENTITY_MEMORY: {item['entity']}")
                for line in item["recent"]:
                    print(f"- {line}")
        return 0
    if args.cmd == "render-all":
        print(f"rendered_entities={render_all()}")
        return 0
    if args.cmd == "backfill":
        print(json.dumps(backfill_recent(days=args.days, limit=args.limit), indent=2, ensure_ascii=False))
        return 0
    if args.cmd == "rebuild":
        print(json.dumps(rebuild_from_backfill(days=args.days, limit=args.limit), indent=2, ensure_ascii=False))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

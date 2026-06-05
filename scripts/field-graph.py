#!/usr/bin/env python3
"""Build a present-moment force graph for the cinematic Field explorer.

Nodes: player, NPCs, threads, current scene, recent images, key objects.
Edges: player relationships, NPC↔NPC stances, thread anchors, scene cast, co-presence.

Usage:
  python3 scripts/field-graph.py bj
  python3 scripts/field-graph.py bj --json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent
SCRIPTS = BASE / "scripts"
LORE = BASE / "lore"
PLAYERS = BASE / "players"
THREADS_F = LORE / "threads.md"
REGISTER_F = LORE / "world-register.md"
VISUALS_F = LORE / "character-visuals.json"
TMP_SCENE = BASE / "tmp" / "scene-outbox" / "enchantify-scene-packet.json"
ENTITY_LOG = BASE / "logs" / "entity-memory.jsonl"
GALLERY = BASE / "logs" / "scene-gallery"
STORYBOOK_DIR = BASE / "memory" / "storybook" / "entries"
STORYBOOK_DAILY_DIR = BASE / "memory" / "storybook" / "daily"
COMPASS_BOOK_DIR = BASE / "lore" / "wonder-compass"

GRAPH_VERSION = "field.present.v1"
MAX_NPC = 72
MAX_NPC_EDGES = 320
MAX_THREADS = 28
MAX_IMAGES = 12
MAX_ENTITY_EVENTS = 40
MAX_COMPASS_CHAPTERS = 14


def slug(text: str, prefix: str = "") -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:64]
    return f"{prefix}{base}" if prefix else base


def load_relationships():
    spec = importlib.util.spec_from_file_location("enchantify_rel", SCRIPTS / "relationships.py")
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def run_json(cmd: list[str], timeout: int = 60) -> dict[str, Any]:
    try:
        proc = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True, timeout=timeout)
        if proc.returncode != 0:
            return {}
        data = json.loads(proc.stdout)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def parse_active_threads() -> list[dict[str, Any]]:
    register = REGISTER_F.read_text(encoding="utf-8", errors="replace") if REGISTER_F.exists() else ""
    threads_text = THREADS_F.read_text(encoding="utf-8", errors="replace") if THREADS_F.exists() else ""
    active_rows: dict[str, dict] = {}
    active_m = re.search(r"(?m)^## Active Threads\s*\n(.*?)(?=^## |\Z)", register, re.DOTALL)
    if active_m:
        for m in re.finditer(
            r"^\|\s*([^|]+?)\s*\|\s*Thread\s*\|\s*(\d+)\s*\|\s*([^|]*)\s*\|",
            active_m.group(1),
            re.MULTILINE | re.IGNORECASE,
        ):
            name = m.group(1).strip()
            if name.lower() in ("entity", "---", ""):
                continue
            active_rows[name.lower()] = {
                "name": name,
                "belief": int(m.group(2)),
                "status": m.group(3).strip()[:200],
            }

    anchors: dict[str, str] = {}
    for section in re.split(r"(?m)^## Thread:\s*", threads_text)[1:]:
        lines = section.splitlines()
        title = lines[0].strip() if lines else ""
        if not title or title.startswith("["):
            continue
        anchor_m = re.search(r"\*\*npc_anchor:\*\*\s*(.+)", section, re.IGNORECASE)
        if anchor_m:
            raw = anchor_m.group(1).strip()
            if raw.lower().startswith("none") or raw.startswith("*"):
                continue
            npc = re.sub(r"\s*\(Belief.*", "", raw).strip()
            anchors[title.lower()] = npc

    out: list[dict[str, Any]] = []
    for key, row in list(active_rows.items())[:MAX_THREADS]:
        out.append(
            {
                "name": row["name"],
                "belief": row["belief"],
                "status": row["status"],
                "npc_anchor": anchors.get(key, ""),
            }
        )
    return out


def current_scene() -> dict[str, Any]:
    if not TMP_SCENE.exists():
        return {}
    try:
        packet = json.loads(TMP_SCENE.read_text(encoding="utf-8"))
    except Exception:
        return {}
    text = ((packet.get("text") or {}).get("text") or "").strip()
    meta = packet.get("metadata") or {}
    sc = meta.get("scene_contract") or {}
    return {
        "scene_id": packet.get("scene_id", ""),
        "title": packet.get("title", "") or "Live scene",
        "mood": packet.get("mood", ""),
        "text_preview": text[:400],
        "location": sc.get("current_location", ""),
        "mode": sc.get("scene_mode", ""),
    }


def detect_names_in_text(text: str, roster: set[str]) -> list[str]:
    found: list[str] = []
    lower = text.lower()
    for name in roster:
        if len(name) < 4:
            continue
        if name.lower() in lower:
            found.append(name)
    return found[:12]


def recent_gallery_images() -> list[dict[str, Any]]:
    if not GALLERY.exists():
        return []
    images: list[dict[str, Any]] = []
    for path in sorted(GALLERY.rglob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)[:MAX_IMAGES * 2]:
        if not path.is_file():
            continue
        rel = str(path.relative_to(BASE))
        images.append(
            {
                "id": slug(path.stem, "img-"),
                "label": path.stem.replace("-", " ")[:48],
                "path": rel,
                "url": f"/api/asset?path={rel}",
                "mtime": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
            }
        )
        if len(images) >= MAX_IMAGES:
            break
    return images


def recent_entity_events(limit: int = MAX_ENTITY_EVENTS) -> list[dict[str, Any]]:
    if not ENTITY_LOG.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in ENTITY_LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-limit * 2 :]:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if isinstance(row, dict) and row.get("entity"):
            rows.append(row)
    return rows[-limit:]


def player_inventory(player: str) -> list[str]:
    path = PLAYERS / f"{player}.md"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    items: list[str] = []
    for m in re.finditer(r"^\s*-\s+\*\*([^*]+)\*\*", text, re.MULTILINE):
        name = m.group(1).strip()
        if name.startswith("Belief") or name.startswith("Chapter"):
            continue
        items.append(name[:80])
    return items[:10]


def latest_file(paths: list[Path], patterns: tuple[str, ...]) -> Path | None:
    found: list[Path] = []
    for root in paths:
        if not root.exists():
            continue
        for pattern in patterns:
            found.extend(p for p in root.glob(pattern) if p.is_file())
    return max(found, key=lambda p: p.stat().st_mtime) if found else None


def first_heading(path: Path, fallback: str) -> str:
    if not path.exists():
        return fallback
    text = path.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines()[:80]:
        m = re.match(r"^#{1,3}\s+(.+?)\s*$", line)
        if m:
            return m.group(1).strip()[:80]
    return fallback


def strip_html(text: str) -> str:
    text = re.sub(r"<script.*?</script>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def build_field_graph(player: str) -> dict[str, Any]:
    rel_mod = load_relationships()
    graph_data = rel_mod.load_graph(player) if rel_mod else {"player_npc": {}, "npc_npc": {}}

    visuals: dict[str, Any] = {}
    if VISUALS_F.exists():
        try:
            visuals = json.loads(VISUALS_F.read_text(encoding="utf-8")).get("characters", {})
        except Exception:
            visuals = {}

    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []

    def add_node(nid: str, **kwargs: Any) -> None:
        if nid in nodes:
            nodes[nid].update({k: v for k, v in kwargs.items() if v not in (None, "")})
            return
        nodes[nid] = {"id": nid, **kwargs}

    def add_edge(source: str, target: str, kind: str, weight: float = 1.0, label: str = "", **extra: Any) -> None:
        if source == target or source not in nodes or target not in nodes:
            return
        edges.append(
            {
                "source": source,
                "target": target,
                "kind": kind,
                "weight": weight,
                "label": label,
                **extra,
            }
        )

    player_id = f"player:{player}"
    add_node(
        player_id,
        label=player,
        kind="player",
        size=14,
        color="#f0b35a",
        detail="You — the reader at the center of the field.",
    )

    # NPCs from player relationships (strongest first)
    ranked_npc = sorted(
        graph_data.get("player_npc", {}).items(),
        key=lambda kv: abs(int(kv[1].get("score", 0))),
        reverse=True,
    )[:MAX_NPC]
    roster_names = {name for name, _ in ranked_npc}

    for name, row in ranked_npc:
        nid = slug(name, "npc-")
        score = int(row.get("score", 0))
        visual = visuals.get(name, {})
        add_node(
            nid,
            label=name,
            kind="npc",
            size=4 + min(abs(score) / 12, 8),
            color=_score_color(score),
            score=score,
            tier=row.get("tier", ""),
            chapter=row.get("chapter", ""),
            notes=(row.get("notes") or "")[:200],
            palette=visual.get("palette", ""),
            image_hint=visual.get("signature", ""),
        )
        add_edge(player_id, nid, "player_bond", weight=max(1.0, abs(score) / 25), label=f"{score:+d}")

    # NPC ↔ NPC (strongest edges, capped)
    npc_edges = sorted(
        graph_data.get("npc_npc", {}).values(),
        key=lambda e: int(e.get("strength", 0)),
        reverse=True,
    )[:MAX_NPC_EDGES]
    for edge in npc_edges:
        a, b = edge.get("a", ""), edge.get("b", "")
        if a not in roster_names and b not in roster_names:
            # include if at least one endpoint is in top NPC set OR lore-locked
            if not (edge.get("locked") or edge.get("source") in {"lore", "manual"}):
                continue
        aid, bid = slug(a, "npc-"), slug(b, "npc-")
        if aid not in nodes:
            add_node(aid, label=a, kind="npc", size=5, color="#8b9cb3")
        if bid not in nodes:
            add_node(bid, label=b, kind="npc", size=5, color="#8b9cb3")
        strength = int(edge.get("strength", 50))
        add_edge(
            aid,
            bid,
            "npc_stance",
            weight=strength / 40,
            label=edge.get("stance", ""),
            stance=edge.get("stance", ""),
            notes=(edge.get("notes") or "")[:120],
        )

    # Threads
    for thread in parse_active_threads():
        tid = slug(thread["name"], "thread-")
        add_node(
            tid,
            label=thread["name"],
            kind="thread",
            size=5 + min(thread["belief"] / 15, 6),
            color="#5ee7ff",
            belief=thread["belief"],
            status=thread["status"],
            phase=_phase_from_status(thread["status"]),
        )
        add_edge(player_id, tid, "thread", weight=thread["belief"] / 30, label="active")
        anchor = thread.get("npc_anchor", "")
        if anchor:
            aid = slug(anchor, "npc-")
            if aid not in nodes:
                add_node(aid, label=anchor, kind="npc", size=6, color="#b794f6")
            add_edge(aid, tid, "anchors", weight=2.5, label="anchor")

    # Current arc / story spine
    if CURRENT_ARC := (LORE / "current-arc.md"):
        if CURRENT_ARC.exists():
            arc_title = first_heading(CURRENT_ARC, "Current Arc")
            arc_text = CURRENT_ARC.read_text(encoding="utf-8", errors="replace")[:800]
            arc_id = "arc-current"
            add_node(
                arc_id,
                label=arc_title,
                kind="arc",
                size=10,
                color="#f59e0b",
                detail=arc_text[:260],
            )
            add_edge(player_id, arc_id, "arc", weight=2.5, label="living arc")
            for thread in parse_active_threads()[:12]:
                add_edge(arc_id, slug(thread["name"], "thread-"), "contains", weight=1.2, label="thread")

    # Current scene hub
    scene = current_scene()
    if scene.get("scene_id") or scene.get("text_preview"):
        sid = slug(scene.get("scene_id") or "live-scene", "scene-")
        add_node(
            sid,
            label=scene.get("title", "Now playing"),
            kind="scene",
            size=10,
            color="#c084fc",
            detail=scene.get("text_preview", ""),
            location=scene.get("location", ""),
            mode=scene.get("mode", ""),
        )
        add_edge(player_id, sid, "present", weight=3.0, label="now")
        roster = set(roster_names)
        for name in detect_names_in_text(scene.get("text_preview", ""), roster):
            add_edge(slug(name, "npc-"), sid, "in_scene", weight=1.8, label="mentioned")

    # Inventory objects
    for item in player_inventory(player):
        oid = slug(item, "obj-")
        add_node(oid, label=item[:40], kind="object", size=4, color="#d4a574", detail="Inventory")
        add_edge(player_id, oid, "carries", weight=1.2)

    # The Bleed and Book of You as public/private memory surfaces
    latest_bleed = latest_file([BASE / "bleed" / "issues"], ("*.html", "*.md"))
    if latest_bleed:
        raw = latest_bleed.read_text(encoding="utf-8", errors="replace")[:12000]
        plain = strip_html(raw) if latest_bleed.suffix.lower() == ".html" else raw
        bid = "artifact-bleed-latest"
        add_node(
            bid,
            label=f"The Bleed · {latest_bleed.stem}",
            kind="artifact",
            size=8,
            color="#38bdf8",
            detail=plain[:320],
            path=str(latest_bleed.relative_to(BASE)),
        )
        add_edge(player_id, bid, "reads", weight=1.2, label="latest issue")
        for name in detect_names_in_text(plain, roster_names):
            add_edge(slug(name, "npc-"), bid, "mentioned", weight=1.0, label="in The Bleed")

    latest_storybook = latest_file([STORYBOOK_DIR, STORYBOOK_DAILY_DIR], ("*.md",))
    if latest_storybook:
        title = first_heading(latest_storybook, f"Book of You · {latest_storybook.stem}")
        text = latest_storybook.read_text(encoding="utf-8", errors="replace")[:10000]
        sid = "artifact-book-of-you-latest"
        add_node(
            sid,
            label=title,
            kind="artifact",
            size=8,
            color="#f0b35a",
            detail=text[:320],
            path=str(latest_storybook.relative_to(BASE)),
        )
        add_edge(player_id, sid, "remembers", weight=1.5, label="latest page")
        for name in detect_names_in_text(text, roster_names):
            add_edge(slug(name, "npc-"), sid, "remembered", weight=1.0, label="in Book of You")

    # Wonder Compass chapters as a method map.
    compass_files = list((BASE / "lore").glob("*Wonder*Compass*.md"))
    compass_files += list((BASE / "lore").glob("*wonder*compass*.md"))
    if COMPASS_BOOK_DIR.exists():
        compass_files += list(COMPASS_BOOK_DIR.glob("*.md"))
    compass_files = sorted(dict.fromkeys(compass_files))
    if compass_files:
        hub = "compass-wonder"
        add_node(
            hub,
            label="Wonder Compass",
            kind="compass",
            size=9,
            color="#84cc16",
            detail="The real-world method behind noticing, embarking, sensing, writing, and resting.",
        )
        add_edge(player_id, hub, "method", weight=1.6, label="field practice")
        for path in compass_files[:MAX_COMPASS_CHAPTERS]:
            cid = slug(path.stem, "compass-")
            add_node(
                cid,
                label=first_heading(path, path.stem.replace("-", " ").title()),
                kind="compass",
                size=4.5,
                color="#a3e635",
                detail=path.read_text(encoding="utf-8", errors="replace")[:220],
                path=str(path.relative_to(BASE)),
            )
            add_edge(hub, cid, "chapter", weight=0.8, label="chapter")

    # Recent images (linked to NPC if name match)
    for img in recent_gallery_images():
        add_node(
            img["id"],
            label=img["label"],
            kind="image",
            size=3.5,
            color="#67e8f9",
            image_url=img["url"],
            path=img["path"],
        )
        linked = False
        for name in roster_names:
            if name.split()[0].lower() in img["label"].lower() or name.lower() in img["path"].lower():
                add_edge(slug(name, "npc-"), img["id"], "portrayed", weight=1.0)
                linked = True
        if not linked:
            add_edge(player_id, img["id"], "memory", weight=0.6)

    # Entity memory ripples
    for row in recent_entity_events():
        entity = str(row.get("entity", "")).strip()
        if not entity:
            continue
        eid = slug(entity, "npc-")
        if eid not in nodes:
            add_node(eid, label=entity, kind="npc", size=4, color="#94a3b8")
        kind = str(row.get("kind", "memory"))
        add_edge(
            eid,
            player_id,
            "memory",
            weight=0.8,
            label=kind,
            summary=(row.get("summary") or "")[:100],
        )

    # Agendas (light links)
    for name, agenda in list(graph_data.get("npc_agenda", {}).items())[:24]:
        nid = slug(name, "npc-")
        if nid not in nodes:
            continue
        goal = (agenda.get("goal") or "")[:80]
        if goal:
            nodes[nid]["agenda"] = goal

    page = run_json([sys.executable, str(SCRIPTS / "page-contract.py"), player, "--json"])
    nothing = run_json([sys.executable, str(SCRIPTS / "narrative-health.py"), player, "--json"])

    return {
        "packet_version": GRAPH_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "player": player,
        "nodes": list(nodes.values()),
        "links": edges,
        "meta": {
            "node_count": len(nodes),
            "link_count": len(edges),
            "page_type": page.get("page_type", ""),
            "narrative_health": nothing.get("status", ""),
            "kinds": _kind_counts(nodes),
        },
    }


def _kind_counts(nodes: dict[str, dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for n in nodes.values():
        k = n.get("kind", "unknown")
        counts[k] = counts.get(k, 0) + 1
    return counts


def _score_color(score: int) -> str:
    if score >= 50:
        return "#4ade80"
    if score >= 10:
        return "#a3e635"
    if score > -10:
        return "#94a3b8"
    if score > -50:
        return "#fb923c"
    return "#f87171"


def _phase_from_status(status: str) -> str:
    m = re.search(r"[Pp]hase:\s*(\w+)", status or "")
    return m.group(1).lower() if m else ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Build present-moment field graph JSON")
    parser.add_argument("player", nargs="?", default="bj")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = build_field_graph(args.player)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

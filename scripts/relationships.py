#!/usr/bin/env python3
"""Canonical social graph for Enchantify: player↔NPC scores and NPC↔NPC stances.

`memory/relationships/{player}.json` is the source of truth. The Relationships
table in `players/{player}.md` is kept in sync as a human-readable view.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent
PLAYERS_DIR = BASE / "players"
GRAPH_DIR = BASE / "memory" / "relationships"

SCORE_MIN, SCORE_MAX = -100, 100
GRAPH_VERSION = 2
DEFAULT_PLAYER = "bj"

# stance → how it affects propagation when player is close to one party
STANCE_PROPAGATION: dict[str, str] = {
    "ally": "warm",
    "mentor": "warm",
    "protects": "warm",
    "close_friend": "warm",
    "loyal_crew": "warm",
    "chapter_mate": "warm",
    "teachers_pet": "warm",
    "faculty_favorite": "warm",
    "chapter_head": "warm",
    "rivalry": "wary",
    "feud": "wary",
    "suspects": "wary",
    "faculty_wary": "wary",
    "chapter_cool": "neutral",
    "owes": "neutral",
    "hidden_alliance": "neutral",
    "professional": "neutral",
    "faculty_tie": "neutral",
    "cross_chapter_formal": "neutral",
    "respectful_rival": "mixed",
    "best_friend": "warm",
    "admires": "warm",
    "crush": "warm",
    "study_partner": "warm",
    "protectorate": "warm",
    "creative_rival": "mixed",
    "colleague": "neutral",
    "philosophical_rival": "mixed",
    "name_confusion": "neutral",
    "distant_acquaintance": "neutral",
    "faculty_favorite": "warm",
}


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def graph_path(player: str) -> Path:
    return GRAPH_DIR / f"{player}.json"


def tier_from_score(score: int) -> str:
    if score >= 100:
        return "devoted"
    if score >= 75:
        return "close_friend"
    if score >= 50:
        return "ally"
    if score >= 25:
        return "friendly"
    if score > -25:
        return "neutral"
    if score > -50:
        return "wary"
    if score > -75:
        return "antagonistic"
    if score > -100:
        return "enemy"
    return "mortal_enemy"


def tier_label(tier: str) -> str:
    return tier.replace("_", " ").title()


def edge_key(a: str, b: str) -> str:
    pair = sorted([a.strip(), b.strip()])
    return f"{pair[0]}||{pair[1]}"


def parse_delta(delta_arg: str) -> tuple[str, int]:
    arg = (delta_arg or "").strip()
    if arg.lower().startswith("set"):
        return "set", int(arg.split()[-1])
    return "delta", int(arg.replace("+", ""))


def default_graph(player: str) -> dict[str, Any]:
    return {
        "version": GRAPH_VERSION,
        "player": player,
        "updated_at": now_iso(),
        "player_npc": {},
        "npc_npc": {},
        "npc_agenda": {},
    }


def load_graph(player: str, *, create: bool = True) -> dict[str, Any]:
    path = graph_path(player)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = default_graph(player)
        else:
            data.setdefault("player_npc", {})
            data.setdefault("npc_npc", {})
            data.setdefault("npc_agenda", {})
            if len(data["npc_npc"]) < 5:
                data = seed_npc_edges(data)
                save_graph(player, data)
            return data
    if not create:
        return default_graph(player)
    data = import_from_player_md(player, save=False)
    data = seed_npc_edges(data)
    save_graph(player, data)
    return data


def save_graph(player: str, data: dict[str, Any]) -> Path:
    data["version"] = GRAPH_VERSION
    data["player"] = player
    data["updated_at"] = now_iso()
    path = graph_path(player)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def parse_relationships_table(player: str) -> dict[str, dict[str, Any]]:
    """Read player↔NPC rows from the player markdown file."""
    path = PLAYERS_DIR / f"{player}.md"
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    rows: dict[str, dict[str, Any]] = {}
    in_table = False
    for line in text.splitlines():
        if "## Relationships" in line:
            in_table = True
            continue
        if in_table:
            if line.startswith("##"):
                break
            if not line.startswith("|") or "---" in line or "NPC" in line:
                continue
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) < 3:
                continue
            name = parts[0]
            score_m = re.search(r"([+-]?\d+)", parts[2])
            if not name or not score_m:
                continue
            score = int(score_m.group(1))
            rows[name] = {
                "score": max(SCORE_MIN, min(SCORE_MAX, score)),
                "tier": tier_from_score(score),
                "chapter": parts[1] if len(parts) > 1 else "—",
                "notes": parts[3] if len(parts) > 3 else "",
            }
    return rows


def import_from_player_md(player: str, *, save: bool = True) -> dict[str, Any]:
    data = load_graph(player, create=False) if graph_path(player).exists() else default_graph(player)
    imported = parse_relationships_table(player)
    for name, row in imported.items():
        existing = data["player_npc"].get(name, {})
        data["player_npc"][name] = {
            "score": row["score"],
            "tier": row["tier"],
            "chapter": row.get("chapter") or existing.get("chapter") or "—",
            "notes": row.get("notes") or existing.get("notes") or "",
            "updated_at": existing.get("updated_at") or now_iso(),
        }
    if save:
        save_graph(player, data)
    return data


def sync_to_player_md(player: str, dry_run: bool = False) -> None:
    """Rewrite the Relationships table from JSON."""
    path = PLAYERS_DIR / f"{player}.md"
    if not path.exists():
        return
    data = load_graph(player)
    content = path.read_text(encoding="utf-8", errors="replace")

    header = "| NPC | Chapter | Score | Notes |\n|---|---|---|---|\n"
    rows = sorted(data["player_npc"].items(), key=lambda kv: kv[0].lower())
    body = ""
    for name, row in rows:
        score = int(row.get("score", 0))
        score_str = f"{score:+d}" if score != 0 else "0"
        chapter = (row.get("chapter") or "—").strip()
        notes = (row.get("notes") or "").strip()
        body += f"| {name} | {chapter} | {score_str} | {notes} |\n"

    table = header + body
    section_re = re.compile(
        r"(## Relationships\s*\n)(?:\| NPC \|.*?\n)(?:\|[-| ]+\|\n)(?:\|[^\n]+\|\n)*",
        re.MULTILINE,
    )
    if section_re.search(content):
        new_content = section_re.sub(r"\1" + table, content, count=1)
    else:
        new_content = content.rstrip() + "\n\n## Relationships\n\n" + table

    if dry_run:
        return
    path.write_text(new_content, encoding="utf-8")


def apply_player_delta(
    player: str,
    npc_name: str,
    delta_arg: str,
    note: str = "",
    *,
    sync_md: bool = True,
) -> dict[str, Any]:
    mode, value = parse_delta(delta_arg)
    data = load_graph(player)
    row = data["player_npc"].get(npc_name, {"score": 0, "chapter": "—", "notes": ""})
    current = int(row.get("score", 0))
    if mode == "delta":
        new_score = current + value
    else:
        new_score = value
    new_score = max(SCORE_MIN, min(SCORE_MAX, new_score))
    if note:
        old_notes = (row.get("notes") or "").strip()
        row["notes"] = f"{old_notes} {note}".strip() if old_notes else note
    row["score"] = new_score
    row["tier"] = tier_from_score(new_score)
    row["updated_at"] = now_iso()
    data["player_npc"][npc_name] = row
    save_graph(player, data)
    if sync_md:
        sync_to_player_md(player)
    return {"npc": npc_name, "before": current, "after": new_score, "tier": row["tier"]}


def set_npc_edge(
    player: str,
    a: str,
    b: str,
    stance: str,
    strength: int = 50,
    note: str = "",
) -> dict[str, Any]:
    data = load_graph(player)
    key = edge_key(a, b)
    data["npc_npc"][key] = {
        "a": sorted([a, b])[0],
        "b": sorted([a, b])[1],
        "stance": stance.strip().lower().replace(" ", "_"),
        "strength": max(0, min(100, int(strength))),
        "notes": note.strip(),
        "source": "manual",
        "locked": True,
        "updated_at": now_iso(),
    }
    save_graph(player, data)
    return data["npc_npc"][key]


def player_scores(player: str) -> dict[str, int]:
    data = load_graph(player)
    return {name: int(row.get("score", 0)) for name, row in data["player_npc"].items()}


def npc_edges(player: str) -> list[dict[str, Any]]:
    data = load_graph(player)
    return list(data.get("npc_npc", {}).values())


def propagation_hints(
    player: str,
    *,
    cast: list[str] | None = None,
    limit: int = 6,
) -> list[str]:
    """How player standing with A may color scenes with B (NPC↔NPC graph)."""
    data = load_graph(player)
    scores = {k: int(v.get("score", 0)) for k, v in data["player_npc"].items()}
    hints: list[str] = []
    cast_set = {n.lower() for n in (cast or [])}

    for key, edge in data.get("npc_npc", {}).items():
        a, b = edge.get("a", ""), edge.get("b", "")
        stance = edge.get("stance", "")
        strength = int(edge.get("strength", 0))
        if strength < 40:
            continue
        effect = STANCE_PROPAGATION.get(stance, "neutral")
        if effect == "neutral":
            continue
        for anchor, other in ((a, b), (b, a)):
            player_score = scores.get(anchor)
            if player_score is None:
                continue
            if abs(player_score) < 25:
                continue
            if cast_set and other.lower() not in cast_set and anchor.lower() not in cast_set:
                continue
            direction = "trusts" if player_score > 0 else "distrusts"
            if effect == "warm" and player_score > 0:
                hints.append(
                    f"{other} may read warmth toward you because {anchor} ({direction}, {tier_label(tier_from_score(player_score))}) is {stance.replace('_', ' ')} with them."
                )
            elif effect == "wary" and player_score > 0:
                hints.append(
                    f"{other} may be guarded: you are close to {anchor}, who {stance.replace('_', ' ')} with them."
                )
            elif effect == "wary" and player_score < 0:
                hints.append(
                    f"{other} may relax slightly: {anchor} opposes you and {stance.replace('_', ' ')} with them."
                )
            if len(hints) >= limit:
                return hints
    return hints


def social_snapshot(
    player: str,
    *,
    cast: list[str] | None = None,
    top_n: int = 8,
) -> dict[str, Any]:
    data = load_graph(player)
    cast_lower = {c.lower() for c in (cast or [])}

    ranked = sorted(
        data["player_npc"].items(),
        key=lambda kv: abs(int(kv[1].get("score", 0))),
        reverse=True,
    )
    seen_npc: set[str] = set()
    player_rows = []

    def add_row(name: str, row: dict[str, Any]) -> None:
        low = name.lower()
        if low in seen_npc:
            return
        score = int(row.get("score", 0))
        player_rows.append(
            {
                "npc": name,
                "score": score,
                "tier": row.get("tier") or tier_from_score(score),
                "notes": truncate(row.get("notes") or "", 120),
            }
        )
        seen_npc.add(low)

    for name, row in ranked[: min(4, top_n)]:
        add_row(name, row)
    if cast_lower:
        for name, row in data["player_npc"].items():
            if name.lower() in cast_lower:
                add_row(name, row)
            if len(player_rows) >= top_n:
                break

    edges = []
    for edge in data.get("npc_npc", {}).values():
        a, b = edge.get("a", ""), edge.get("b", "")
        strength = int(edge.get("strength", 0))
        in_cast = cast_lower and (
            a.lower() in cast_lower or b.lower() in cast_lower
        )
        is_lore = edge.get("source") in {"lore", "manual"} or edge.get("locked")
        if cast_lower and not in_cast:
            continue
        edges.append(
            {
                "a": a,
                "b": b,
                "stance": edge.get("stance"),
                "strength": edge.get("strength"),
                "notes": truncate(edge.get("notes") or "", 100),
                "source": edge.get("source"),
                "locked": edge.get("locked"),
            }
        )

    agendas = []
    for name in sorted(data.get("npc_agenda", {})):
        if cast_lower and name.lower() not in cast_lower:
            continue
        row = data["npc_agenda"][name]
        agendas.append(
            {
                "npc": name,
                "goal": truncate(row.get("goal") or "", 100),
                "fear": truncate(row.get("fear") or "", 80),
                "watching": (row.get("watching") or [])[:3],
                "if_absent_24h": truncate(row.get("if_absent_24h") or "", 120),
            }
        )
        if len(agendas) >= 6:
            break

    return {
        "player_npc": player_rows,
        "npc_npc": sorted(
            edges,
            key=lambda e: (
                0 if e.get("source") in {"lore", "manual"} else 1,
                -int(e.get("strength") or 0),
            ),
        )[:20],
        "npc_agenda": agendas,
        "propagation_hints": propagation_hints(player, cast=cast),
    }


def actor_social_context(player: str, actor: str, *, limit: int = 6) -> dict[str, Any]:
    """Compact relationship context for one actor, suitable for simulation packets."""
    data = load_graph(player)
    player_row = data.get("player_npc", {}).get(actor, {})
    agenda = dict(data.get("npc_agenda", {}).get(actor, {}))
    edges = edges_for_npc(player, actor, min_strength=45)[:limit]
    compact_edges = []
    for edge in edges:
        other = edge["b"] if edge.get("a") == actor else edge.get("a")
        compact_edges.append(
            {
                "other": other,
                "stance": edge.get("stance", ""),
                "strength": edge.get("strength", 0),
                "notes": truncate(edge.get("notes") or "", 120),
            }
        )
    score = int(player_row.get("score", 0)) if player_row else 0
    return {
        "player_bond": {
            "score": score,
            "tier": player_row.get("tier") or tier_from_score(score),
            "notes": truncate(player_row.get("notes") or "", 160),
        } if player_row else {},
        "agenda": {
            "goal": truncate(agenda.get("goal") or "", 160),
            "fear": truncate(agenda.get("fear") or "", 120),
            "watching": (agenda.get("watching") or [])[:4],
        } if agenda else {},
        "edges": compact_edges,
    }


def bleed_social_weather(player: str = DEFAULT_PLAYER, *, limit: int = 10) -> str:
    """Relationship graph summary for The Bleed and other artifacts.

    This is intentionally plain data in readable sentences. The newspaper can turn
    it into gossip, but the source layer stays legible and non-metaphorical.
    """
    data = load_graph(player)
    lines: list[str] = ["RELATIONSHIP GRAPH / SOCIAL WEATHER:"]

    player_rows = sorted(
        data.get("player_npc", {}).items(),
        key=lambda kv: abs(int(kv[1].get("score", 0))),
        reverse=True,
    )
    if player_rows:
        lines.append("Player-facing bonds:")
        for name, row in player_rows[:5]:
            score = int(row.get("score", 0))
            note = truncate(row.get("notes") or "", 120)
            lines.append(f"- {name}: {score:+d} ({tier_label(row.get('tier') or tier_from_score(score))})" + (f" — {note}" if note else ""))
    else:
        lines.append("Player-facing bonds: no scored NPC relationships yet.")

    edges = sorted(
        data.get("npc_npc", {}).values(),
        key=lambda e: (
            0 if e.get("source") in {"manual", "lore"} or e.get("locked") else 1,
            -int(e.get("strength", 0)),
        ),
    )
    selected = []
    seen_pairs: set[str] = set()
    for edge in edges:
        stance = str(edge.get("stance") or "")
        strength = int(edge.get("strength", 0))
        if strength < 55:
            continue
        key = edge_key(str(edge.get("a") or ""), str(edge.get("b") or ""))
        if key in seen_pairs:
            continue
        seen_pairs.add(key)
        selected.append(edge)
        if len(selected) >= limit:
            break

    if selected:
        lines.append("Corridor ties likely to produce gossip or consequences:")
        for edge in selected:
            note = truncate(edge.get("notes") or "", 110)
            text = f"- {edge.get('a')} ↔ {edge.get('b')}: {edge.get('stance')} ({edge.get('strength')})"
            lines.append(text + (f" — {note}" if note else ""))

    agendas = []
    for name, row in data.get("npc_agenda", {}).items():
        watching = row.get("watching") or []
        if watching:
            agendas.append((name, row, watching))
    if agendas:
        lines.append("Watch-list pressure:")
        for name, row, watching in agendas[:6]:
            goal = truncate(row.get("goal") or "", 95)
            lines.append(f"- {name} is watching {', '.join(watching[:3])}" + (f"; goal: {goal}" if goal else ""))

    lines.append(
        "Gossip guidance: use these as social evidence, not exposition. A gossip item should name one relationship, one observable behavior, and one uncertainty."
    )
    return "\n".join(lines)


def truncate(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def seed_npc_edges(data: dict[str, Any]) -> dict[str, Any]:
    """Core cast NPC↔NPC edges (world bible, not player-specific history)."""
    seeds = [
        ("Zara Finch", "Finn Bridges", "rivalry", 60, "Honorable tension; loyalty vs independence."),
        ("Zara Finch", "Serenity Brown", "close_friend", 75, "Tidecrest allies; both orbit the player."),
        ("Finn Bridges", "Wicker Eddies", "respectful_rival", 55, "Antagonists who recognize each other's code."),
        ("Wicker Eddies", "Melisande Blackwood", "loyal_crew", 85, "Core Duskthorn-adjacent crew loyalty."),
        ("Wicker Eddies", "Damien Nights", "loyal_crew", 80, "Crew cohesion."),
        ("Headmistress Seraphina Thorne", "Professor Kyle Momort", "hidden_alliance", 70, "Shared Duskthorn purpose; never surface early."),
        ("Professor Wellend Thickets", "Professor Kyle Momort", "hidden_alliance", 65, "Duskthorn coordination under cooperative cover."),
        ("Professor Cedric Stonebrook", "Headmistress Seraphina Thorne", "professional", 50, "Formal deference; he avoids her conflicts."),
        ("Index", "Serenity Brown", "ally", 40, "Faculty-adjacent helpful presence in Riddlewind orbit."),
    ]
    for a, b, stance, strength, note in seeds:
        key = edge_key(a, b)
        if key in data["npc_npc"]:
            continue
        pair = sorted([a.strip(), b.strip()])
        data["npc_npc"][key] = {
            "a": pair[0],
            "b": pair[1],
            "stance": stance,
            "strength": strength,
            "notes": note,
            "updated_at": now_iso(),
        }
    return data


def cmd_import(player: str) -> int:
    data = import_from_player_md(player, save=True)
    sync_to_player_md(player)
    print(f"✓ Imported {len(data['player_npc'])} player↔NPC rows → {graph_path(player)}")
    return 0


def cmd_sync(player: str) -> int:
    sync_to_player_md(player)
    print(f"✓ Synced Relationships table for {player}")
    return 0


def cmd_delta(player: str, npc: str, delta_arg: str, note: str) -> int:
    result = apply_player_delta(player, npc, delta_arg, note)
    print(
        f"✓ {result['npc']}: {result['before']:+d} → {result['after']:+d} ({tier_label(result['tier'])})"
    )
    return 0


def cmd_edge(player: str, a: str, b: str, stance: str, strength: int, note: str) -> int:
    edge = set_npc_edge(player, a, b, stance, strength, note)
    print(f"✓ NPC edge: {edge['a']} ↔ {edge['b']} [{edge['stance']}] strength {edge['strength']}")
    return 0


def agenda_for(player: str, npc: str) -> dict[str, Any]:
    data = load_graph(player)
    return dict(data.get("npc_agenda", {}).get(npc, {}))


def edges_for_npc(player: str, npc: str, *, min_strength: int = 40) -> list[dict[str, Any]]:
    data = load_graph(player)
    low = npc.lower()
    out = []
    for edge in data.get("npc_npc", {}).values():
        if edge.get("a", "").lower() == low or edge.get("b", "").lower() == low:
            if int(edge.get("strength", 0)) >= min_strength:
                out.append(edge)
    return sorted(out, key=lambda e: int(e.get("strength", 0)), reverse=True)


def social_pulse_beats(
    player: str,
    sim_actions: list[Any],
    *,
    limit: int = 2,
) -> list[dict[str, str]]:
    """Turn simulation actors + agendas into tick-queue social seeds."""
    data = load_graph(player)
    beats: list[dict[str, str]] = []
    seen: set[str] = set()

    for action in sim_actions:
        npc = getattr(action, "npc", None) or (action.get("npc") if isinstance(action, dict) else None)
        if not npc or npc in seen:
            continue
        seen.add(npc)
        agenda = data.get("npc_agenda", {}).get(npc, {})
        if not agenda:
            continue
        watching = agenda.get("watching") or []
        partner = watching[0] if watching else None
        if not partner:
            edges = edges_for_npc(player, npc, min_strength=55)
            if edges:
                e = edges[0]
                partner = e["b"] if e["a"] == npc else e["a"]
        thread = getattr(action, "thread_name", None) or (
            action.get("thread_name") if isinstance(action, dict) else ""
        )
        goal = truncate(agenda.get("goal") or "their own business", 90)
        absent = truncate(agenda.get("if_absent_24h") or "moved through the Academy offscreen.", 140)
        if partner:
            seed = f"{npc} ({goal}) — toward {partner}: {absent}"
        else:
            seed = f"{npc} ({goal}): {absent}"
        if thread:
            seed = f"{seed} Thread pressure: {thread}."
        beats.append(
            {
                "raw": f"Social beat: {npc}",
                "seed": seed,
                "priority": "NORMAL",
            }
        )
        if len(beats) >= limit:
            break
    return beats


def cmd_generate(player: str, dry_run: bool = False) -> int:
    import relationship_generator

    data = load_graph(player)
    before_edges = len(data.get("npc_npc", {}))
    data = relationship_generator.generate_full_graph(data)
    if not dry_run:
        save_graph(player, data)
    print(
        f"✓ Generated social graph for {player}: "
        f"{before_edges} → {len(data.get('npc_npc', {}))} edges, "
        f"{len(data.get('npc_agenda', {}))} agendas"
    )
    return 0


def cmd_context(player: str, cast: str) -> int:
    names = [n.strip() for n in cast.split(",") if n.strip()] if cast else None
    snap = social_snapshot(player, cast=names)
    print("SOCIAL_GRAPH")
    print("PLAYER_NPC:")
    for row in snap["player_npc"]:
        print(f"- {row['npc']}: {row['score']:+d} ({tier_label(row['tier'])}) — {row['notes']}")
    if snap["npc_npc"]:
        print("NPC_NPC:")
        for edge in snap["npc_npc"]:
            print(
                f"- {edge['a']} ↔ {edge['b']}: {edge['stance']} ({edge['strength']}) — {edge['notes']}"
            )
    if snap.get("npc_agenda"):
        print("NPC_AGENDA:")
        for row in snap["npc_agenda"]:
            watching = ", ".join(row.get("watching") or []) or "—"
            print(f"- {row['npc']}: goal={row['goal']} | fear={row['fear']} | watching={watching}")
    if snap["propagation_hints"]:
        print("SOCIAL_PRESSURE:")
        for hint in snap["propagation_hints"]:
            print(f"- {hint}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Enchantify social relationship graph")
    sub = parser.add_subparsers(dest="command", required=True)

    p_import = sub.add_parser("import", help="Import player.md Relationships into JSON")
    p_import.add_argument("player", nargs="?", default="bj")

    p_sync = sub.add_parser("sync", help="Write JSON scores back to player.md")
    p_sync.add_argument("player", nargs="?", default="bj")

    p_delta = sub.add_parser("delta", help="Apply player↔NPC score change")
    p_delta.add_argument("player", nargs="?", default="bj")
    p_delta.add_argument("npc")
    p_delta.add_argument("delta")
    p_delta.add_argument("--note", default="")

    p_edge = sub.add_parser("edge", help="Set or update NPC↔NPC stance")
    p_edge.add_argument("player", nargs="?", default="bj")
    p_edge.add_argument("a")
    p_edge.add_argument("b")
    p_edge.add_argument("stance")
    p_edge.add_argument("--strength", type=int, default=50)
    p_edge.add_argument("--note", default="")

    p_ctx = sub.add_parser("context", help="Print social snapshot for scene injection")
    p_ctx.add_argument("player", nargs="?", default="bj")
    p_ctx.add_argument("--cast", default="", help="Comma-separated NPC names in scene")

    p_gen = sub.add_parser("generate", help="Generate baseline npc_npc + npc_agenda from roster")
    p_gen.add_argument("player", nargs="?", default="bj")
    p_gen.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()
    if args.command == "import":
        return cmd_import(args.player)
    if args.command == "sync":
        return cmd_sync(args.player)
    if args.command == "delta":
        return cmd_delta(args.player, args.npc, args.delta, args.note)
    if args.command == "edge":
        return cmd_edge(args.player, args.a, args.b, args.stance, args.strength, args.note)
    if args.command == "context":
        return cmd_context(args.player, args.cast)
    if args.command == "generate":
        return cmd_generate(args.player, dry_run=args.dry_run)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

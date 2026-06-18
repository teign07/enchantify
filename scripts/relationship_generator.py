#!/usr/bin/env python3
"""Generate baseline NPC↔NPC edges and default agendas from roster + overrides."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import relationship_roster as roster_mod

try:
    import narrative_sim
except ImportError:
    narrative_sim = None  # type: ignore

BASE = Path(__file__).resolve().parent.parent
OVERRIDES_PATH = BASE / "config" / "relationship-overrides.json"

try:
    import sys

    sys.path.insert(0, str(BASE / "config"))
    import relationship_lore as lore_data
except ImportError:
    lore_data = None  # type: ignore

# stance keys used by generator (see mechanics/npc.md + relationships.py propagation)
STUDENT_INTRA = ("chapter_mate", 52, "Same chapter; shared corridors and house pride.")
STUDENT_CROSS = ("chapter_cool", 28, "Different chapters; polite distance by default.")
CHAPTER_HEAD = ("chapter_head", 62, "Head of chapter; formal mentorship.")
FACULTY_TIE = ("faculty_tie", 45, "Chapter faculty and student.")
CROSS_FACULTY = ("cross_chapter_formal", 30, "Faculty outside the student's chapter.")
HEAD_PROFESSIONAL = ("professional", 38, "Headmistress/Headmaster and academy member.")
CREW_INTERNAL = ("loyal_crew", 80, "Wicker's crew cohesion.")


def _stable_int(*parts: str, lo: int = 0, hi: int = 100) -> int:
    digest = hashlib.sha256("|".join(parts).encode()).hexdigest()
    span = max(1, hi - lo + 1)
    return lo + int(digest[:8], 16) % span


def load_overrides() -> dict[str, Any]:
    if not OVERRIDES_PATH.exists():
        return {"edges": [], "agenda_overrides": {}}
    return json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))


def edge_record(
    a: str,
    b: str,
    stance: str,
    strength: int,
    notes: str,
    *,
    source: str = "generated",
    locked: bool = False,
) -> dict[str, Any]:
    pair = sorted([a.strip(), b.strip()])
    return {
        "a": pair[0],
        "b": pair[1],
        "stance": stance,
        "strength": max(0, min(100, int(strength))),
        "notes": notes.strip(),
        "source": source,
        "locked": locked,
    }


def generate_edges(roster: dict[str, roster_mod.CharacterEntry]) -> dict[str, dict[str, Any]]:
    edges: dict[str, dict[str, Any]] = {}
    students = roster_mod.students_by_chapter(roster)
    faculty = roster_mod.faculty_by_chapter(roster)

    def put(edge: dict[str, Any]) -> None:
        key = f"{edge['a']}||{edge['b']}"
        existing = edges.get(key)
        if existing and (existing.get("locked") or existing.get("source") == "manual"):
            if int(existing.get("strength", 0)) >= int(edge.get("strength", 0)):
                return
        edges[key] = edge

    # ── Students: intra-chapter (chapter-tuned) ──
    for chapter, names in students.items():
        profile = (lore_data.CHAPTER_PROFILES.get(chapter, {}) if lore_data else {})
        intra_bonus = int(profile.get("intra_bonus", 0))
        for i, a in enumerate(names):
            for b in names[i + 1 :]:
                stance, base, note = STUDENT_INTRA
                jitter = _stable_int(a, b, "intra", lo=-8, hi=8)
                strength = base + intra_bonus + jitter
                # ~18% of pairs are cordial-but-distant (richer hallway texture)
                if _stable_int(a, b, "distant", lo=0, hi=99) < 18:
                    put(
                        edge_record(
                            a,
                            b,
                            "distant_acquaintance",
                            max(32, strength - 18),
                            f"Same chapter; orbit different circles ({chapter}).",
                        )
                    )
                else:
                    put(
                        edge_record(
                            a,
                            b,
                            stance,
                            strength,
                            f"{note} ({chapter})",
                        )
                    )

    # ── Students: cross-chapter cool ──
    chapter_list = [c for c in students if students[c]]
    for i, ch_a in enumerate(chapter_list):
        for ch_b in chapter_list[i + 1 :]:
            for a in students[ch_a]:
                for b in students[ch_b]:
                    stance, base, note = STUDENT_CROSS
                    cross_bonus = 0
                    if lore_data:
                        cross_bonus = max(
                            lore_data.CHAPTER_PROFILES.get(ch_a, {}).get("cross_bonus", 0),
                            lore_data.CHAPTER_PROFILES.get(ch_b, {}).get("cross_bonus", 0),
                        )
                    jitter = _stable_int(a, b, "cross", lo=-5, hi=5)
                    put(
                        edge_record(
                            a,
                            b,
                            stance,
                            base + cross_bonus + jitter,
                            f"{note} ({ch_a} ↔ {ch_b})",
                        )
                    )

    # ── Faculty ↔ chapter students ──
    for chapter, names in students.items():
        if not names:
            continue
        heads = [n for n in faculty.get(chapter, []) if "Head of" in n]
        profs = [n for n in faculty.get(chapter, []) if n not in heads]
        for student in names:
            for head in heads:
                stance, base, note = CHAPTER_HEAD
                put(edge_record(student, head, stance, base + _stable_int(student, head, "head", lo=-4, hi=4), note))
            for prof in profs:
                stance, base, note = FACULTY_TIE
                put(
                    edge_record(
                        student,
                        prof,
                        stance,
                        base + _stable_int(student, prof, "fac", lo=-5, hi=5),
                        f"{note} ({chapter})",
                    )
                )
        for other_ch, other_profs in faculty.items():
            if other_ch == chapter:
                continue
            for student in names:
                for prof in other_profs:
                    stance, base, note = CROSS_FACULTY
                    put(
                        edge_record(
                            student,
                            prof,
                            stance,
                            base,
                            f"{note}",
                        )
                    )

    # ── Faculty ↔ faculty (same chapter colleagues) ──
    for chapter, profs in faculty.items():
        for i, a in enumerate(profs):
            for b in profs[i + 1 :]:
                put(
                    edge_record(
                        a,
                        b,
                        "colleague",
                        48 + _stable_int(a, b, "facpeer", lo=0, hi=14),
                        f"Shared {chapter} faculty corridor politics.",
                    )
                )

    # ── Headmistress ↔ faculty (sparse) ──
    heads_of_academy = [
        n
        for n, e in roster.items()
        if e.role == "head" or "Headmistress" in n or "Headmaster" in n
    ]
    all_faculty = [n for n, e in roster.items() if e.role == "faculty"]
    for h in heads_of_academy:
        for prof in all_faculty:
            put(edge_record(h, prof, *HEAD_PROFESSIONAL))

    # ── Wicker crew internal mesh ──
    crew = [n for n, e in roster.items() if "wicker_crew" in e.tags]
    for i, a in enumerate(crew):
        for b in crew[i + 1 :]:
            put(edge_record(a, b, *CREW_INTERNAL))

    # ── Duskthorn-tagged: low-profile mutual recognition ──
    dusk = [n for n, e in roster.items() if "duskthorn" in e.tags]
    for i, a in enumerate(dusk):
        for b in dusk[i + 1 :]:
            put(
                edge_record(
                    a,
                    b,
                    "hidden_alliance",
                    55 + _stable_int(a, b, "dusk", lo=0, hi=15),
                    "Shared Duskthorn pressure; never surface early.",
                )
            )

    # ── Personality nudges: rivals / friends within chapter ──
    rivalry_words = ("antagonistic", "competitive", "rebellious", "brooding", "cunning", "manipulative")
    friend_words = ("loyal", "kind", "empathetic", "cooperative", "joyful", "carefree", "best friend")
    for chapter, names in students.items():
        lore = _lore_map()
        for i, a in enumerate(names):
            la = lore.get(a, {})
            pa = (la.get("personality") or "").lower()
            for b in names[i + 1 :]:
                pb = (lore.get(b, {}) or {}).get("personality", "").lower()
                key = f"{sorted([a,b])[0]}||{sorted([a,b])[1]}"
                riv_bonus = 0
                if lore_data and chapter in lore_data.CHAPTER_PROFILES:
                    riv_bonus = int(lore_data.CHAPTER_PROFILES[chapter].get("rivalry_bonus", 0))
                if any(w in pa for w in rivalry_words) and any(w in pb for w in rivalry_words):
                    put(
                        edge_record(
                            a,
                            b,
                            "rivalry",
                            45 + riv_bonus + _stable_int(a, b, "riv", lo=0, hi=15),
                            f"Personality friction within {chapter}.",
                        )
                    )
                elif _stable_int(a, b, "study", lo=0, hi=99) < 32:
                    put(
                        edge_record(
                            a,
                            b,
                            "study_partner",
                            52 + _stable_int(a, b, "sp", lo=0, hi=12),
                            f"Shared study tables ({chapter}).",
                        )
                    )
                elif any(w in pa for w in friend_words) and any(w in pb for w in friend_words):
                    existing = edges.get(key)
                    if existing and existing.get("stance") == "chapter_mate":
                        existing["stance"] = "close_friend"
                        existing["strength"] = min(100, int(existing["strength"]) + 12)
                        existing["notes"] = f"Warm chapter bond ({chapter})."

    edges = apply_relationship_lore(edges, roster)
    return edges


def apply_relationship_lore(
    edges: dict[str, dict[str, Any]],
    roster: dict[str, roster_mod.CharacterEntry],
) -> dict[str, dict[str, Any]]:
    if not lore_data:
        return edges

    def put(edge: dict[str, Any]) -> None:
        key = f"{edge['a']}||{edge['b']}"
        edge["source"] = "lore"
        edge["locked"] = True
        edges[key] = edge

    roster_names = set(roster.keys())

    for clique in lore_data.CLIQUES:
        members = [m for m in clique["members"] if m in roster_names]
        stance = clique.get("stance", "close_friend")
        strength = int(clique.get("strength", 70))
        note = clique.get("notes", clique.get("name", "Clique"))
        for i, a in enumerate(members):
            for b in members[i + 1 :]:
                put(edge_record(a, b, stance, strength, f"{note} [{clique.get('name', 'clique')}]"))

    for a, b, stance, strength, note in lore_data.CURATED_EDGES:
        if a not in roster_names or b not in roster_names:
            continue
        put(edge_record(a, b, stance, strength, note))

    return edges


def _lore_map() -> dict[str, dict[str, str]]:
    if narrative_sim is None:
        return {}
    return narrative_sim.parse_character_lore()


def derive_agenda(name: str, entry: roster_mod.CharacterEntry) -> dict[str, Any]:
    lore = _lore_map().get(name, {})
    chapter = entry.chapter or "the Academy"
    interest = lore.get("unwritten interest") or lore.get("personality") or entry.role
    faults = lore.get("faults") or "being misunderstood"
    goals = lore.get("goals") or lore.get("story hooks") or f"Do right by {chapter}"

    watching: list[str] = []
    if entry.role == "student" and entry.chapter:
        roster = roster_mod.parse_roster()
        students = roster_mod.students_by_chapter(roster).get(entry.chapter, [])
        if students:
            idx = _stable_int(name, "watch", lo=0, hi=max(0, len(students) - 1))
            pick = students[idx]
            if pick != name:
                watching.append(pick)

    if "wicker_crew" in entry.tags:
        watching.append("Wicker Eddies")
    if entry.role == "faculty":
        watching.append("Headmistress Seraphina Thorne")

    if entry.role == "student":
        absent = f"Leave a small {entry.chapter} chapter trace — a note, rumor, or object — tied to: {interest[:80]}."
    elif entry.role == "faculty":
        absent = f"Annotate something in the {chapter} wing that only attentive students would notice."
    else:
        absent = "Tend their usual duty so the Academy feels occupied when the player returns."

    return {
        "goal": goals[:200],
        "fear": faults[:160],
        "watching": watching[:4],
        "if_absent_24h": absent[:220],
        "source": "generated",
    }


def generate_agendas(roster: dict[str, roster_mod.CharacterEntry]) -> dict[str, dict[str, Any]]:
    agendas: dict[str, dict[str, Any]] = {}
    for name, entry in roster.items():
        if entry.role not in {"student", "faculty", "head", "staff"}:
            continue
        if entry.role == "staff" and "Library" not in entry.section and "Book Fae" not in entry.section:
            continue
        agendas[name] = derive_agenda(name, entry)
    return agendas


def apply_overrides(
    edges: dict[str, dict[str, Any]],
    agendas: dict[str, dict[str, Any]],
    overrides: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    if lore_data:
        for name, agenda in lore_data.AGENDA_LORE.items():
            merged = agendas.get(name, {})
            merged.update(agenda)
            merged["source"] = "lore"
            agendas[name] = merged
    for raw in overrides.get("edges", []):
        edge = edge_record(
            raw["a"],
            raw["b"],
            raw["stance"],
            raw.get("strength", 50),
            raw.get("notes", ""),
            source="manual",
            locked=bool(raw.get("locked", True)),
        )
        key = f"{edge['a']}||{edge['b']}"
        edges[key] = edge
    for name, agenda in (overrides.get("agenda_overrides") or {}).items():
        merged = agendas.get(name, {})
        merged.update(agenda)
        merged["source"] = "manual"
        agendas[name] = merged
    return edges, agendas


def merge_into_graph(
    data: dict[str, Any],
    generated_edges: dict[str, dict[str, Any]],
    generated_agendas: dict[str, dict[str, Any]],
    *,
    replace_generated: bool = True,
) -> dict[str, Any]:
    """Merge generated edges/agendas; preserve locked/manual rows."""
    if replace_generated:
        kept = {
            k: v
            for k, v in data.get("npc_npc", {}).items()
            if v.get("locked") or v.get("source") in {"manual", None}
        }
        data["npc_npc"] = kept

    for key, edge in generated_edges.items():
        existing = data["npc_npc"].get(key)
        if existing and existing.get("locked"):
            continue
        if existing and existing.get("source") == "manual":
            continue
        data["npc_npc"][key] = edge

    data.setdefault("npc_agenda", {})
    if replace_generated:
        data["npc_agenda"] = {
            k: v
            for k, v in data["npc_agenda"].items()
            if v.get("source") == "manual"
        }
    for name, agenda in generated_agendas.items():
        if data["npc_agenda"].get(name, {}).get("source") == "manual":
            continue
        data["npc_agenda"][name] = agenda

    data["graph_meta"] = {
        "edge_count": len(data["npc_npc"]),
        "agenda_count": len(data["npc_agenda"]),
        "generator": "relationship_generator.py",
    }
    return data


def generate_full_graph(data: dict[str, Any], *, replace_generated: bool = True) -> dict[str, Any]:
    roster = roster_mod.parse_roster()
    roster_mod.write_roster_cache()
    edges = generate_edges(roster)
    agendas = generate_agendas(roster)
    edges, agendas = apply_overrides(edges, agendas, load_overrides())
    return merge_into_graph(data, edges, agendas, replace_generated=replace_generated)


def main() -> int:
    import argparse
    import relationships

    parser = argparse.ArgumentParser(description="Generate Enchantify social graph baselines")
    parser.add_argument("player", nargs="?", default="bj")
    parser.add_argument("--roster-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.roster_only:
        path = roster_mod.write_roster_cache()
        roster = roster_mod.parse_roster()
        print(f"✓ Roster: {len(roster)} characters → {path}")
        return 0

    data = relationships.load_graph(args.player)
    before = len(data.get("npc_npc", {}))
    data = generate_full_graph(data)
    after = len(data.get("npc_npc", {}))
    if not args.dry_run:
        relationships.save_graph(args.player, data)
    print(f"✓ Generated graph for {args.player}: {before} → {after} npc_npc edges, {len(data.get('npc_agenda', {}))} agendas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

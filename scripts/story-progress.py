#!/usr/bin/env python3
"""Diagnose arc handoff and thread development health.

This script is intentionally plain-spoken: it turns hidden narrative state into
small, checkable signals so lower-tier models do not have to infer too much.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent
LORE = BASE / "lore"
MEMORY = BASE / "memory"
CURRENT_ARC = LORE / "current-arc.md"
THREADS = LORE / "threads.md"
REGISTER = LORE / "world-register.md"
QUEUE = MEMORY / "tick-queue.md"
PROPOSED = BASE / "proposed"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def load_thread_sync():
    path = BASE / "scripts" / "thread_sync.py"
    spec = importlib.util.spec_from_file_location("thread_sync", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def phase_rank(phase: str) -> int:
    order = ["dormant", "setup", "rising", "climax", "resolution"]
    phase = normalize_phase(phase)
    return order.index(phase) if phase in order else -1


def normalize_phase(phase: str) -> str:
    phase = (phase or "").strip().lower().rstrip(",")
    if phase in ("escalating", "escalation"):
        return "rising"
    return phase


@dataclass
class ArcState:
    title: str
    phase: str
    day: int | None
    started: str

    @property
    def ready_for_handoff(self) -> bool:
        if self.phase.upper() == "QUIET":
            return True
        if self.phase.upper() == "RESOLUTION" and (self.day or 0) >= 3:
            return True
        return False


def parse_arc() -> ArcState:
    text = read(CURRENT_ARC)
    title_m = re.search(r"^# Current Arc[\s:—-]+(.+)", text, re.MULTILINE)
    phase_m = re.search(r"^## Phase:\s*(.+)", text, re.MULTILINE)
    day_m = re.search(r"^## Day:\s*(\d+)", text, re.MULTILINE)
    started_m = re.search(r"^## Started:\s*(.+)", text, re.MULTILINE)
    return ArcState(
        title=title_m.group(1).strip() if title_m else "(unreadable)",
        phase=phase_m.group(1).strip() if phase_m else "",
        day=int(day_m.group(1)) if day_m else None,
        started=started_m.group(1).strip() if started_m else "",
    )


def pending_proposals() -> list[str]:
    if not PROPOSED.exists():
        return []
    return sorted(path.name for path in PROPOSED.glob("arc-*.md"))


def malformed_thread_fields(text: str) -> list[str]:
    labels = [
        "phase",
        "Next beat",
        "Last advanced",
        "Last visited",
        "born",
        "closed",
    ]
    label_re = "|".join(re.escape(label) for label in labels)
    found = []
    for i, line in enumerate(text.splitlines(), start=1):
        if re.match(rf"^\*\*({label_re}):(?!(?:\*\*))", line, re.IGNORECASE):
            found.append(f"line {i}: {line[:90]}")
    return found


def parse_thread_sections(text: str) -> list[dict]:
    sections = re.split(r"^## Thread:\s*", text, flags=re.MULTILINE)
    threads = []
    for section in sections[1:]:
        lines = section.strip().splitlines()
        if not lines:
            continue
        name = lines[0].strip()

        def field(label: str) -> str:
            m = re.search(rf"\*\*{re.escape(label)}:(?:\*\*)?\s*([^\n]+)", section, re.IGNORECASE)
            return m.group(1).strip() if m else ""

        threads.append(
            {
                "name": name,
                "id": field("id").strip("`"),
                "phase": normalize_phase(field("phase").split()[0] if field("phase") else ""),
                "pressure": field("pressure"),
                "next_beat": field("Next beat"),
                "last_advanced": field("Last advanced"),
                "npc_anchor": field("npc_anchor"),
            }
        )
    return threads


def parse_register_threads(text: str) -> dict[str, dict]:
    rows = {}
    for line in text.splitlines():
        m = re.match(r"^\|\s*([^|]+?)\s*\|\s*Thread\s*\|\s*(\d+)\s*\|\s*([^|]*)\|", line)
        if not m:
            continue
        name, belief, notes = m.group(1).strip(), int(m.group(2)), m.group(3).strip()
        id_m = re.search(r"\[id:([^\]]+)\]", notes)
        phase_m = re.search(r"Phase:\s*(\w+)", notes, re.IGNORECASE)
        rows[name] = {
            "id": id_m.group(1).strip() if id_m else "",
            "belief": belief,
            "phase": normalize_phase(phase_m.group(1) if phase_m else ""),
            "notes": notes,
        }
    return rows


def queue_thread_seeds() -> list[str]:
    text = read(QUEUE)
    seeds = []
    for line in text.splitlines():
        m = re.search(r"\[THREAD SEED:\s*([^\]]+)\]", line)
        if m:
            seeds.append(m.group(1).strip())
    return sorted(set(seeds))


def repair_threads(dry_run: bool) -> tuple[bool, int]:
    text = read(THREADS)
    sync = load_thread_sync()
    fixed = sync.normalize_thread_fields(text)
    if fixed == text:
        return False, 0
    changes = len(malformed_thread_fields(text))
    if not dry_run:
        THREADS.write_text(fixed, encoding="utf-8")
    return True, changes


def build_report() -> tuple[list[str], bool]:
    arc = parse_arc()
    proposals = pending_proposals()
    threads_text = read(THREADS)
    register_text = read(REGISTER)
    threads = parse_thread_sections(threads_text)
    register_threads = parse_register_threads(register_text)
    malformed = malformed_thread_fields(threads_text)
    seeds = queue_thread_seeds()

    lines = ["STORY PROGRESS"]
    lines.append(f"Arc: {arc.title}")
    lines.append(f"Phase: {arc.phase or '(missing)'} | Day: {arc.day if arc.day is not None else '(missing)'}")
    lines.append(f"Started: {arc.started or '(missing)'}")
    lines.append(f"Arc handoff: {'READY' if arc.ready_for_handoff else 'not ready'}")
    if proposals:
        lines.append(f"Pending proposals: {', '.join(proposals)}")
    elif arc.ready_for_handoff:
        lines.append("Pending proposals: none - generator should be allowed to dream one")
    else:
        lines.append("Pending proposals: none")

    lines.append("")
    lines.append("THREAD LEDGER")
    mismatches = []
    for thread in threads:
        if thread["name"].startswith("[") and thread["name"].endswith("]"):
            continue
        if thread["id"] in ("main-arc", ""):
            continue
        row = next((value for value in register_threads.values() if value["id"] == thread["id"]), None)
        if not row:
            if thread["id"] != "academy-daily":
                mismatches.append(f"{thread['name']}: missing Active Threads row")
            continue
        thread_phase = thread["phase"]
        row_phase = row["phase"]
        if row_phase and thread_phase and row_phase != thread_phase and thread["id"] != "academy-daily":
            mismatches.append(f"{thread['name']}: threads.md={thread_phase}, world-register={row_phase}")
        pressure = f"belief {row['belief']}, phase {row_phase or thread_phase or 'unknown'}"
        lines.append(f"- {thread['name']}: {pressure}")

    if malformed:
        lines.append("")
        lines.append("Malformed thread fields:")
        lines.extend(f"- {item}" for item in malformed[:8])
    if mismatches:
        lines.append("")
        lines.append("Thread mismatches:")
        lines.extend(f"- {item}" for item in mismatches[:8])
    if seeds:
        lines.append("")
        lines.append("Thread seeds in queue:")
        lines.extend(f"- {seed}" for seed in seeds)
    else:
        lines.append("")
        lines.append("Thread seeds in queue: none")

    ok = bool(arc.phase) and not malformed
    return lines, ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose narrative progress state.")
    parser.add_argument("player", nargs="?", default="bj")
    parser.add_argument("--repair-threads", action="store_true", help="Normalize malformed thread fields.")
    parser.add_argument("--dry-run", action="store_true", help="Show repairs without writing.")
    parser.add_argument("--check-only", action="store_true", help="Exit nonzero if progress rails need repair.")
    args = parser.parse_args()

    if args.repair_threads:
        changed, count = repair_threads(args.dry_run)
        action = "would repair" if args.dry_run else "repaired"
        if changed:
            print(f"THREAD FIELD REPAIR: {action} {count} malformed field(s)")
        else:
            print("THREAD FIELD REPAIR: no changes needed")

    lines, ok = build_report()
    print("\n".join(lines))
    return 1 if args.check_only and not ok else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Narrative stewardship health report.

This is a read-only diagnostic for the Narrative OS layer. It turns scattered
story ledgers into simple pressure signals a smaller model can act on.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent
LORE = BASE / "lore"
MEMORY = BASE / "memory"
LOGS = BASE / "logs"
CURRENT_ARC = LORE / "current-arc.md"
THREADS = LORE / "threads.md"
REGISTER = LORE / "world-register.md"
QUEUE = MEMORY / "tick-queue.md"
SIM_LOG_DIR = LOGS / "simulations"
PLAYERS = BASE / "players"


@dataclass
class Finding:
    level: str
    area: str
    summary: str
    detail: str = ""
    action: str = ""


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def clean(text: str) -> str:
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text or "")
    text = text.replace("*", "")
    text = re.sub(r"\[(?:id|thread):[^\]]+\]\s*", "", text)
    return re.sub(r"\s+", " ", text).strip(" ;")


def parse_iso_date(raw: str) -> date | None:
    m = re.search(r"\d{4}-\d{2}-\d{2}", raw or "")
    if not m:
        return None
    try:
        return date.fromisoformat(m.group(0))
    except ValueError:
        return None


def days_since(raw: str) -> int | None:
    parsed = parse_iso_date(raw)
    return (date.today() - parsed).days if parsed else None


def phase_rank(phase: str) -> int:
    order = ["dormant", "setup", "rising", "climax", "resolution"]
    phase = normalize_phase(phase)
    return order.index(phase) if phase in order else -1


def normalize_phase(phase: str) -> str:
    phase = (phase or "").strip().lower().rstrip(",")
    if phase in {"escalating", "escalation"}:
        return "rising"
    if phase == "quiet":
        return "permanent"
    return phase


def parse_arc() -> dict:
    text = read(CURRENT_ARC)
    title = re.search(r"^#\s*(?:Current Arc\s*[:—-]\s*)?(.+)", text, re.MULTILINE)
    phase = re.search(r"^## Phase:\s*(.+)", text, re.MULTILINE)
    day = re.search(r"^## Day:\s*(\d+)", text, re.MULTILINE)
    genre = re.search(r"^## Genre:\s*(.+)", text, re.MULTILINE)
    compass = re.search(r"^## Compass:\s*(.+)", text, re.MULTILINE)
    return {
        "title": clean(title.group(1)) if title else "(missing)",
        "phase": clean(phase.group(1)) if phase else "",
        "day": int(day.group(1)) if day else None,
        "genre": clean(genre.group(1)) if genre else "",
        "compass": clean(compass.group(1)) if compass else "",
    }


def parse_register_threads() -> dict[str, dict]:
    rows: dict[str, dict] = {}
    active_m = re.search(r"(?m)^## Active Threads\s*\n(.*?)(?=^## |\Z)", read(REGISTER), re.DOTALL)
    if not active_m:
        return rows
    for m in re.finditer(
        r"^\|\s*([^|]+?)\s*\|\s*Thread\s*\|\s*(\d+)\s*\|\s*([^|]*)\|",
        active_m.group(1),
        re.MULTILINE | re.IGNORECASE,
    ):
        name, belief, notes = m.group(1).strip(), int(m.group(2)), clean(m.group(3))
        if name.lower() in {"entity", "---"}:
            continue
        id_m = re.search(r"\[id:([^\]]+)\]", m.group(3))
        phase_m = re.search(r"Phase:\s*([A-Za-z_-]+)", notes, re.IGNORECASE)
        rows[name.lower()] = {
            "name": name,
            "id": id_m.group(1).strip() if id_m else "",
            "belief": belief,
            "phase": normalize_phase(phase_m.group(1) if phase_m else ""),
            "status": clean(re.split(r"Phase:\s*[A-Za-z_-]+\s*[\-–—]\s*", notes, maxsplit=1)[-1]),
        }
    return rows


def parse_thread_sections() -> dict[str, dict]:
    sections: dict[str, dict] = {}
    for section in re.split(r"^## Thread:\s*", read(THREADS), flags=re.MULTILINE)[1:]:
        lines = section.strip().splitlines()
        if not lines:
            continue
        name = lines[0].strip()
        if name.startswith("["):
            continue

        def field(label: str) -> str:
            m = re.search(rf"\*\*{re.escape(label)}:(?:\*\*)?\s*([^\n]+)", section, re.IGNORECASE)
            return clean(m.group(1)) if m else ""

        sections[name.lower()] = {
            "name": name,
            "id": field("id").strip("`"),
            "phase": normalize_phase(field("phase").split()[0] if field("phase") else ""),
            "pressure": field("pressure"),
            "next_beat": field("Next beat"),
            "last_advanced": field("Last advanced"),
            "npc_anchor": field("npc_anchor"),
        }
    return sections


def parse_phase_signals() -> dict[str, dict]:
    signals: dict[str, dict] = {}
    current_ts = ""
    for line in read(QUEUE).splitlines():
        tick_m = re.match(r"^## Tick (\d{4}-\d{2}-\d{2} \d{2}:\d{2})", line)
        if tick_m:
            current_ts = tick_m.group(1)
            continue
        m = re.search(
            r"\[THREAD (ESCALATION|COOLING): ([^\]]+)\].*?"
            r"Readiness\s+(\d+)\s+pushes this thread from `([^`]+)` toward `([^`]+)`\.\s*(.+)",
            line,
            re.IGNORECASE,
        )
        if not m:
            continue
        kind, name, readiness, from_phase, toward, why = m.groups()
        signals[name.lower()] = {
            "kind": kind.lower(),
            "name": clean(name),
            "readiness": int(readiness),
            "from": normalize_phase(from_phase),
            "toward": normalize_phase(toward),
            "why": clean(why),
            "ts": current_ts,
        }
    return signals


def claimed_thread_anchors() -> set[str]:
    claimed: set[str] = set()
    for section in re.split(r"^## Thread:\s*", read(THREADS), flags=re.MULTILINE)[1:]:
        for label in ("npc_anchor", "entities"):
            m = re.search(rf"\*\*{label}:(?:\*\*)?\s*([^\n]+)", section, re.IGNORECASE)
            if not m:
                continue
            for item in re.split(r",|;", m.group(1)):
                item = clean(item).strip("`")
                if item and item.lower() not in {"all npcs", "none", "unknown"}:
                    claimed.add(item.lower())
    return claimed


def queue_thread_seeds() -> list[str]:
    claimed = claimed_thread_anchors()
    seeds = []
    for line in read(QUEUE).splitlines():
        m = re.search(r"\[THREAD SEED:\s*([^\]]+)\]", line)
        if m and clean(m.group(1)).lower() not in claimed:
            seeds.append(clean(m.group(1)))
    return sorted(set(seeds))


def parse_simulation_events(hours: int = 24) -> list[dict]:
    if not SIM_LOG_DIR.exists():
        return []
    cutoff = datetime.now() - timedelta(hours=hours)
    events = []
    for path in sorted(SIM_LOG_DIR.glob("*.jsonl"), reverse=True):
        for line in read(path).splitlines():
            try:
                obj = json.loads(line)
                ts = datetime.fromisoformat(obj.get("timestamp", ""))
            except Exception:
                continue
            if ts >= cutoff:
                events.append(obj)
    return sorted(events, key=lambda e: e.get("timestamp", ""))


def parse_story_memory(player: str) -> dict:
    path = PLAYERS / f"{player}-story.md"
    text = read(path)
    updated = re.search(r"\*Updated:\s*(\d{4}-\d{2}-\d{2})", text)
    dated_moments = re.findall(r"^\*\*(\d{4}-\d{2}-\d{2}):\*\*", text, re.MULTILINE)
    latest_moment = max(dated_moments) if dated_moments else ""
    return {
        "exists": path.exists(),
        "updated": updated.group(1) if updated else "",
        "latest_alive_moment": latest_moment,
        "latest_alive_age_days": days_since(latest_moment) if latest_moment else None,
    }


def level_score(level: str) -> int:
    return {"OK": 0, "WATCH": 4, "WARN": 10, "ALERT": 18}.get(level, 0)


def build_report(player: str) -> dict:
    arc = parse_arc()
    register_threads = parse_register_threads()
    thread_sections = parse_thread_sections()
    phase_signals = parse_phase_signals()
    seeds = queue_thread_seeds()
    sim_events = parse_simulation_events()
    memory = parse_story_memory(player)

    findings: list[Finding] = []

    if arc["phase"]:
        findings.append(Finding("OK", "Arc", f"{arc['title']} is {arc['phase']} day {arc['day']}", f"{arc['genre']} / {arc['compass']}"))
    else:
        findings.append(Finding("ALERT", "Arc", "Current arc is unreadable", "Missing phase/title fields.", "Repair lore/current-arc.md before play."))

    for key, signal in phase_signals.items():
        thread = register_threads.get(key, {})
        section = thread_sections.get(key, {})
        if not thread:
            continue
        if signal["toward"] == "permanent":
            continue
        last = section.get("last_advanced", "")
        age = days_since(last)
        if age is None:
            level = "WARN"
            summary = f"{thread['name']} has phase pressure but no readable Last advanced date"
        elif age >= 10:
            level = "ALERT"
            summary = f"{thread['name']} is pushing {signal['from']} -> {signal['toward']} after {age} day(s) without a delivered beat"
        elif age >= 5:
            level = "WARN"
            summary = f"{thread['name']} is pushing {signal['from']} -> {signal['toward']} and has waited {age} day(s)"
        else:
            level = "WATCH"
            summary = f"{thread['name']} is pushing {signal['from']} -> {signal['toward']}"
        findings.append(Finding(
            level,
            "Threads",
            summary,
            f"Readiness {signal['readiness']} at {signal['ts']}. {signal['why']}",
            "Deliver or explicitly defer one grounded beat; then update lore/threads.md Last advanced and next beat.",
        ))

    if len(seeds) >= 4:
        findings.append(Finding(
            "WARN",
            "Thread Seeds",
            f"{len(seeds)} recurring thread seeds are waiting for triage",
            ", ".join(seeds),
            "Choose one seed to promote, explicitly defer the rest, or let them remain ambient.",
        ))
    elif seeds:
        findings.append(Finding("WATCH", "Thread Seeds", f"{len(seeds)} thread seed(s) waiting", ", ".join(seeds)))
    else:
        findings.append(Finding("OK", "Thread Seeds", "No pending thread seeds"))

    if not sim_events:
        findings.append(Finding("ALERT", "Simulation", "No simulation events in the last 24 hours", action="Check world-pulse cron."))
    else:
        by_thread = Counter(e.get("thread_name") or e.get("name") or "unthreaded" for e in sim_events)
        high_count = sum(1 for e in sim_events if e.get("priority") == "HIGH")
        dominant, count = by_thread.most_common(1)[0]
        pct = int(count / max(len(sim_events), 1) * 100)
        level = "WATCH" if pct >= 55 else "OK"
        if arc["genre"].lower().startswith("recovery") and any("duskthorn" in (e.get("thread_name") or "").lower() for e in sim_events if e.get("priority") == "HIGH"):
            level = "WARN"
        findings.append(Finding(
            level,
            "Simulation",
            f"{len(sim_events)} event(s) in 24h; {high_count} high-priority",
            f"Dominant thread: {dominant} ({pct}%).",
            "Keep recovery/rest signals above drama when the current arc calls for it." if level == "WARN" else "",
        ))

    alive_age = memory.get("latest_alive_age_days")
    if not memory["exists"]:
        findings.append(Finding("ALERT", "Long Memory", f"{player}-story.md is missing"))
    elif alive_age is None:
        findings.append(Finding("WARN", "Long Memory", "No dated alive moments found", action="Run/update nightly story intelligence."))
    elif alive_age >= 10:
        findings.append(Finding(
            "ALERT",
            "Long Memory",
            f"Latest alive moment is {alive_age} day(s) old",
            f"Latest alive moment: {memory['latest_alive_moment']}; file updated: {memory['updated'] or 'unknown'}.",
            "Refresh the story memory from recent scene ledger and closeout events.",
        ))
    elif alive_age >= 4:
        findings.append(Finding("WARN", "Long Memory", f"Latest alive moment is {alive_age} day(s) old"))
    else:
        findings.append(Finding("OK", "Long Memory", "Recent alive moments are present"))

    penalties = sum(level_score(f.level) for f in findings)
    score = max(0, 100 - penalties)
    if any(f.level == "ALERT" for f in findings):
        status = "ALERT"
    elif any(f.level == "WARN" for f in findings):
        status = "WARN"
    elif any(f.level == "WATCH" for f in findings):
        status = "WATCH"
    else:
        status = "OK"

    next_actions = [f.action for f in findings if f.action]
    return {
        "status": status,
        "score": score,
        "arc": arc,
        "findings": [asdict(f) for f in findings],
        "next_actions": list(dict.fromkeys(next_actions))[:5],
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }


def print_text(report: dict) -> None:
    print(f"NARRATIVE HEALTH: {report['status']} ({report['score']}/100)")
    arc = report["arc"]
    print(f"Arc: {arc['title']} | {arc['phase']} day {arc['day']} | {arc['genre']} / {arc['compass']}")
    print("")
    for finding in report["findings"]:
        print(f"{finding['level']:5} {finding['area']}: {finding['summary']}")
        if finding.get("detail"):
            print(f"      {finding['detail']}")
    if report["next_actions"]:
        print("")
        print("NEXT STEWARDSHIP")
        for action in report["next_actions"]:
            print(f"- {action}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Report Narrative OS stewardship health.")
    parser.add_argument("player", nargs="?", default="bj")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument("--strict", action="store_true", help="Exit nonzero on WARN or ALERT.")
    args = parser.parse_args()

    report = build_report(args.player)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_text(report)

    if args.strict and report["status"] in {"WARN", "ALERT"}:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

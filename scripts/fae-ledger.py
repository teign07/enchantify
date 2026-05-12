#!/usr/bin/env python3
"""fae-ledger.py — living bargain ledger for Book Fae.

Fae bargains are contracts, not quests. This script keeps the player-visible
Margin table and a machine-readable event ledger in sync so fae consequences can
surface in scenes, Mission Control, and The Bleed.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent
PLAYERS = BASE / "players"
LOG = BASE / "logs" / "fae-ledger.jsonl"
QUEUE = BASE / "memory" / "tick-queue.md"

STATUSES = {"OPEN", "DELIVERED", "OVERDUE", "BROKEN", "EXPIRED", "REPAIRED"}


FAE_LAW = {
    "goblin": {
        "style": "mercantile, exact, archivist of attention",
        "consequence": "the useful thing loses labels, directions, or provenance; the debt appears in a ledger with a second door-price",
        "repair": "pay the original sensory detail, then add one unlabeled thing noticed without looking for it",
    },
    "index empire": {
        "style": "bureaucratic, ancient, impossibly indexed",
        "consequence": "records remain true but cross-references turn sideways; the next useful rumor arrives without its shelfmark",
        "repair": "bring one precise overlooked label, number, receipt, sign, or margin mark from the Climax",
    },
    "hearthkin": {
        "style": "domestic, exacting, sacred hospitality",
        "consequence": "warmth remains but stops waiting; a vessel clouds or cools until a simple joy is honestly offered",
        "repair": "offer the missed simple pleasure plus one unperformed act of care noticed in the same day",
    },
    "wayskeeper": {
        "style": "threshold-bound, patient, concerned with unfinished arrivals",
        "consequence": "the path still opens, but descriptions become conditional; an arrival is delayed by one true sentence",
        "repair": "speak one sentence about an arrival, then name what was late without apologizing theatrically",
    },
    "sorter": {
        "style": "goblin craft-economy, potential over sentiment",
        "consequence": "objects still glow, but not for the player; unnamed potential is moved to the stubborn shelf",
        "repair": "name what one overlooked object could become, specifically enough that it could be made",
    },
    "sprite": {
        "style": "small, emotional, editorial",
        "consequence": "an Academy label, plaque, or remembered phrase changes by one word and will not explain itself",
        "repair": "bring a small honest feeling with one physical detail attached",
    },
    "salamander": {
        "style": "warmth, vitality, visible reaction",
        "consequence": "borrowed courage overheats into irritability; the flame dims around generic reports",
        "repair": "bring one alive detail that has heat, motion, or appetite in it",
    },
    "pixie": {
        "style": "punctuation, rhythm, unstable naming",
        "consequence": "the debt is redenominated; a word or mark in a recent text becomes suspiciously wrong",
        "repair": "bring a sentence whose punctuation changed how it felt",
    },
    "literary elf": {
        "style": "precise, formal, allergic to dishonest polish",
        "consequence": "the granted sentence remains elegant but loses honesty; margins become quietly severe",
        "repair": "revise one true sentence until it is plainer and more accurate",
    },
    "dwarf": {
        "style": "deep, binding, structural",
        "consequence": "the buried fact grows heavier; the next threshold has one word waiting: Still",
        "repair": "bring the underlayer: what was holding something up without being thanked",
    },
}


@dataclass
class Bargain:
    fae: str
    gave: str
    terms: str
    deadline: str
    status: str = "OPEN"
    stage: int = 0
    consequence: str = ""
    repair: str = ""
    source: str = ""
    created: str = ""
    updated: str = ""


def today() -> str:
    return date.today().isoformat()


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def player_path(player: str) -> Path:
    return PLAYERS / f"{player}.md"


def read_player(player: str) -> str:
    path = player_path(player)
    if not path.exists():
        raise SystemExit(f"Player file not found: {path}")
    return path.read_text(encoding="utf-8")


def write_player(player: str, text: str, dry_run: bool = False) -> None:
    path = player_path(player)
    if dry_run:
        print(f"[dry-run] Would update {path}")
        return
    backup = path.with_suffix(".md.bak")
    backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")


def profile_for(fae: str) -> dict:
    key = fae.lower()
    for needle, profile in FAE_LAW.items():
        if needle in key:
            return profile
    return {
        "style": "old Faerie protocol, literal and recoverable",
        "consequence": "the gift remains, but its relationship to the player changes until the terms are honored",
        "repair": "pay the original terms with one additional precise sensory detail",
    }


def clean_cell(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip()).replace("|", "/")


def parse_margin(text: str) -> tuple[list[Bargain], tuple[int, int] | None]:
    m = re.search(r"(## The Margin\n.*?\n\| Fae \| What They Gave \| Terms \(what you owe\) \| Deadline \| Status \|\n\|---\|---\|---\|---\|---\|\n)(.*?)(?=\n---\n|\n## |\Z)", text, re.DOTALL)
    if not m:
        return [], None
    bargains: list[Bargain] = []
    for line in m.group(2).splitlines():
        if not line.startswith("|") or "*(The margin is clean" in line:
            continue
        parts = [p.strip() for p in line.split("|")[1:-1]]
        if len(parts) < 5 or not parts[0]:
            continue
        status = re.sub(r"[*`]", "", parts[4]).upper()
        bargains.append(Bargain(parts[0], parts[1], parts[2], parts[3], status if status in STATUSES else parts[4]))
    return bargains, (m.start(2), m.end(2))


def render_rows(bargains: list[Bargain]) -> str:
    if not bargains:
        return "| *(The margin is clean — no bargains yet)* | | | | |\n"
    rows = []
    for b in bargains:
        rows.append(
            f"| {clean_cell(b.fae)} | {clean_cell(b.gave)} | {clean_cell(b.terms)} | {clean_cell(b.deadline)} | {clean_cell(b.status.upper())} |"
        )
    return "\n".join(rows) + "\n"


def replace_margin(text: str, bargains: list[Bargain]) -> str:
    _, span = parse_margin(text)
    if span:
        return text[: span[0]] + render_rows(bargains) + text[span[1] :]
    section = (
        "\n## The Margin\n"
        "*Fae bargains live here, not in the Inside Cover. Fae give first — the player always owes a return.*\n"
        "*These are contracts, not quests. The Fae remember everything.*\n\n"
        "| Fae | What They Gave | Terms (what you owe) | Deadline | Status |\n"
        "|---|---|---|---|---|\n"
        + render_rows(bargains)
        + "\n---\n"
    )
    return text.rstrip() + "\n" + section


def append_event(player: str, action: str, bargain: Bargain, dry_run: bool = False) -> None:
    payload = {"timestamp": now(), "player": player, "action": action, **asdict(bargain)}
    if dry_run:
        print(json.dumps(payload, ensure_ascii=False))
        return
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def append_tick_seed(player: str, bargain: Bargain, dry_run: bool = False) -> None:
    seed = (
        f"\n[FAE DEBT:{bargain.status.upper()}] {bargain.fae} remembers an unpaid bargain for {player}. "
        f"Consequence stage {bargain.stage}: {bargain.consequence} "
        f"Repair path: {bargain.repair}\n"
    )
    if dry_run:
        print("[dry-run] Would append tick seed:")
        print(seed.strip())
        return
    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    with QUEUE.open("a", encoding="utf-8") as f:
        f.write(seed)


def is_date_overdue(deadline: str, as_of: str) -> bool:
    m = re.match(r"^\d{4}-\d{2}-\d{2}$", (deadline or "").strip())
    return bool(m and deadline < as_of)


def find_bargain(bargains: list[Bargain], query: str) -> Bargain | None:
    q = query.lower()
    for b in bargains:
        hay = " ".join([b.fae, b.gave, b.terms, b.deadline]).lower()
        if q in hay:
            return b
    return None


def cmd_add(args) -> int:
    text = read_player(args.player)
    bargains, _ = parse_margin(text)
    profile = profile_for(args.fae)
    b = Bargain(
        fae=args.fae,
        gave=args.gave,
        terms=args.terms,
        deadline=args.deadline,
        status="OPEN",
        stage=0,
        consequence=profile["consequence"],
        repair=profile["repair"],
        source=args.source or "",
        created=today(),
        updated=today(),
    )
    bargains.append(b)
    write_player(args.player, replace_margin(text, bargains), args.dry_run)
    append_event(args.player, "add", b, args.dry_run)
    print(f"BARGAIN_ADDED {b.fae} deadline={b.deadline} status=OPEN")
    print(f"LAW: {profile['style']}")
    print(f"IF_BROKEN: {b.consequence}")
    print(f"REPAIR: {b.repair}")
    return 0


def cmd_list(args) -> int:
    bargains, _ = parse_margin(read_player(args.player))
    as_of = args.as_of or today()
    visible = [b for b in bargains if args.all or b.status.upper() in {"OPEN", "OVERDUE", "BROKEN", "EXPIRED"}]
    if not visible:
        print("FAE_LEDGER clean")
        return 0
    print(f"FAE_LEDGER {args.player} ({len(visible)} visible)")
    for b in visible:
        marker = " overdue" if b.status.upper() == "OPEN" and is_date_overdue(b.deadline, as_of) else ""
        profile = profile_for(b.fae)
        print(f"- {b.status.upper()}{marker}: {b.fae} | gave: {b.gave} | owes: {b.terms} | due: {b.deadline}")
        if args.details:
            print(f"  consequence: {profile['consequence']}")
            print(f"  repair: {profile['repair']}")
    return 0


def cmd_tick(args) -> int:
    text = read_player(args.player)
    bargains, _ = parse_margin(text)
    changed = 0
    as_of = args.as_of or today()
    for b in bargains:
        if b.status.upper() == "OPEN" and is_date_overdue(b.deadline, as_of):
            profile = profile_for(b.fae)
            b.status = "OVERDUE"
            b.stage = 1
            b.consequence = profile["consequence"]
            b.repair = profile["repair"]
            b.updated = as_of
            append_event(args.player, "overdue", b, args.dry_run)
            append_tick_seed(args.player, b, args.dry_run)
            changed += 1
    if changed:
        write_player(args.player, replace_margin(text, bargains), args.dry_run)
    print(f"FAE_TICK overdue_marked={changed}")
    return 0


def cmd_fulfill(args) -> int:
    text = read_player(args.player)
    bargains, _ = parse_margin(text)
    b = find_bargain(bargains, args.query)
    if not b:
        print(f"BARGAIN_NOT_FOUND {args.query!r}")
        return 1
    b.status = "DELIVERED" if not args.repair else "REPAIRED"
    b.updated = today()
    if args.report:
        b.gave = f"{b.gave} / Report: {args.report[:120]}"
    write_player(args.player, replace_margin(text, bargains), args.dry_run)
    append_event(args.player, "repair" if args.repair else "fulfill", b, args.dry_run)
    print(f"BARGAIN_{b.status.upper()} {b.fae}")
    print("The debt is paid; future scenes should let the relationship change, not reset.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Fae bargain ledger")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("add")
    p.add_argument("player")
    p.add_argument("--fae", required=True)
    p.add_argument("--gave", required=True)
    p.add_argument("--terms", required=True)
    p.add_argument("--deadline", required=True)
    p.add_argument("--source", default="")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_add)

    p = sub.add_parser("list")
    p.add_argument("player")
    p.add_argument("--all", action="store_true")
    p.add_argument("--details", action="store_true")
    p.add_argument("--as-of")
    p.set_defaults(fn=cmd_list)

    p = sub.add_parser("tick")
    p.add_argument("player")
    p.add_argument("--as-of")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_tick)

    p = sub.add_parser("fulfill")
    p.add_argument("player")
    p.add_argument("query")
    p.add_argument("--report", default="")
    p.add_argument("--repair", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_fulfill)

    args = parser.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())

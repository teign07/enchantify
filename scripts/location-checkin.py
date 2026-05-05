#!/usr/bin/env python3
"""
location-checkin.py — deterministic GPS front door for anchors.

Rules:
- If coordinates fall within an existing anchor's radius, check into that room.
- If no anchor is nearby and --create is passed, create a new anchor room there.
- If no anchor is nearby and --create is absent, report the nearest anchor.

This keeps the agent from having to identify coordinates by intuition.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

BASE = Path(__file__).parent.parent
SCRIPTS = BASE / "scripts"
PLAYERS = BASE / "players"
VISIT_LOG = BASE / "logs" / "anchor-visits.jsonl"
DEFAULT_RADIUS_M = 200


def _load_anchor_check():
    spec = importlib.util.spec_from_file_location("anchor_check", SCRIPTS / "anchor-check.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def extract_coordinates(text: str) -> tuple[float, float] | None:
    text = text or ""
    patterns = [
        r"(?:lat(?:itude)?)[=:,\s]+([+-]?\d+(?:\.\d+)?)[,\s]+(?:lon(?:gitude)?|lng)[=:,\s]+([+-]?\d+(?:\.\d+)?)",
        r"[?&]q=([+-]?\d+(?:\.\d+)?),([+-]?\d+(?:\.\d+)?)",
        r"@([+-]?\d+(?:\.\d+)?),([+-]?\d+(?:\.\d+)?)",
        r"\b([+-]?\d{1,2}\.\d+)\s*,\s*([+-]?\d{1,3}\.\d+)\b",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if not m:
            continue
        lat, lon = float(m.group(1)), float(m.group(2))
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return lat, lon
    return None


def anchor_file(player: str) -> Path:
    return PLAYERS / f"{player}-anchors.md"


def current_season() -> str:
    return _load_anchor_check().get_current_season()


def append_anchor_record(player: str, record: str, dry_run: bool = False) -> None:
    path = anchor_file(player)
    if not path.exists():
        header = (
            f"# Anchors — {player}\n\n"
            "*Places invested with Belief. Each one opens a GPS-gated door into the Outer Stacks.*\n\n"
            "---\n"
        )
        if dry_run:
            print(f"[dry-run] Would create {path}")
            return
        path.write_text(header + "\n" + record, encoding="utf-8")
        return

    text = path.read_text(encoding="utf-8")
    placeholder = "\n*(No Anchors yet. The Ley Line map is blank — waiting for the first sacred place.)*\n"
    text = text.replace(placeholder, "\n")
    new_text = text.rstrip() + "\n\n" + record
    if dry_run:
        print(f"[dry-run] Would append anchor to {path}")
        return
    backup = path.with_suffix(".md.bak")
    shutil.copy2(path, backup)
    tmp = path.with_suffix(".md.tmp")
    tmp.write_text(new_text if new_text.endswith("\n") else new_text + "\n", encoding="utf-8")
    tmp.rename(path)


def sentence(text: str, fallback: str) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    return text.rstrip(".") + "." if text else fallback


def generated_room(name: str, anchor_type: str, words: str, belief: int) -> dict[str, str]:
    direction = {
        "NOTICE": "small overlooked details",
        "EMBARK": "routes, departures, and things becoming ready",
        "SENSE": "texture, sound, scent, and embodied knowing",
        "WRITE": "sentences, records, and what can be kept",
        "REST": "warmth, pause, and protected simplicity",
        "FIND": "objects waiting for their next use",
    }.get(anchor_type.upper(), "the exact meaning of this place")
    room = (
        f"{name} opens as a room of {direction}: shelves and thresholds arranged around the player's words, "
        f"\"{words}\". The space is already built when the anchor is made, but remains unseen until the first real visit. "
        f"It carries {belief} Belief at birth, so its magic is specific, intimate, and local."
    )
    fae = (
        "A local Outer Stacks keeper tends the room without introducing themself at first. "
        "They know the difference between visiting a place and claiming it."
    )
    mini = (
        "Something in the room has been waiting for a repeat arrival. The first visit reveals the shape; later visits teach what the room remembers."
    )
    rule = (
        "The room only responds to real details brought from the physical place. General summaries pass through it like fog."
    )
    return {"room": room, "fae": fae, "mini_story": mini, "local_rule": rule}


def build_anchor_record(args, lat: float, lon: float) -> str:
    today = date.today().isoformat()
    season = args.season or current_season()
    generated = generated_room(args.name, args.type, args.words, args.belief)
    room = args.room or generated["room"]
    fae = args.fae or generated["fae"]
    mini_story = args.mini_story or generated["mini_story"]
    local_rule = args.local_rule or generated["local_rule"]
    echo = args.echo or sentence(
        f"A door appears in the Academy with {args.type.upper()} pressure from {args.name}",
        "A new door appears in the Academy, waiting for the real place to be revisited.",
    )
    return f"""## {args.name}
- **Coordinates:** {lat:.6f}, {lon:.6f}
- **Radius meters:** {args.radius}
- **Type:** {args.type.upper()}
- **Belief invested:** {args.belief}
- **Created:** {today}
- **Weather:** {args.weather or "Unknown at creation"}
- **Moon:** {args.moon or "Unknown at creation"}
- **Season:** {season}
- **Player's words:** "{args.words}"
- **Academy echo:** {echo}
- **Outer Stacks room:** {room}
- **Fae:** {fae}
- **Mini-story:** {mini_story}
- **Local rule:** {local_rule}
- **Visit count:** 0
- **Last visited:** *(none yet)*
"""


def log_creation(player: str, name: str, lat: float, lon: float, radius: int, dry_run: bool = False) -> None:
    payload = {
        "timestamp": datetime.now().isoformat(),
        "player": player,
        "anchor": name,
        "lat": lat,
        "lon": lon,
        "radius_m": radius,
        "mode": "ANCHOR_CREATED",
        "visit_count": 0,
        "dry_run": dry_run,
    }
    if dry_run:
        return
    VISIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with VISIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def run_anchor_check(player: str, lat: float, lon: float, dry_run: bool = False) -> int:
    cmd = [
        sys.executable,
        str(SCRIPTS / "anchor-check.py"),
        player,
        f"{lat:.6f}",
        f"{lon:.6f}",
        "--checkin",
    ]
    if dry_run:
        cmd.append("--dry-run")
    proc = subprocess.run(cmd, text=True)
    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministic location check-in / anchor creation")
    parser.add_argument("player")
    parser.add_argument("location_text", nargs="?", help="Raw text, maps URL, or 'lat, lon'")
    parser.add_argument("--text-file", type=Path)
    parser.add_argument("--create", action="store_true", help="Create a new anchor if no existing anchor is nearby")
    parser.add_argument("--name")
    parser.add_argument("--type", default="NOTICE")
    parser.add_argument("--words")
    parser.add_argument("--radius", type=int, default=DEFAULT_RADIUS_M)
    parser.add_argument("--belief", type=int, default=5)
    parser.add_argument("--weather")
    parser.add_argument("--moon")
    parser.add_argument("--season")
    parser.add_argument("--echo")
    parser.add_argument("--room")
    parser.add_argument("--fae")
    parser.add_argument("--mini-story")
    parser.add_argument("--local-rule")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    raw = args.location_text or ""
    if args.text_file:
        raw += "\n" + args.text_file.read_text(encoding="utf-8")
    if not raw.strip():
        raw = sys.stdin.read()

    coords = extract_coordinates(raw)
    if not coords:
        print("NO_COORDINATES_FOUND")
        print("Provide a Telegram location payload, maps URL, or plain 'lat, lon'.")
        return 2
    lat, lon = coords

    ac = _load_anchor_check()
    path = anchor_file(args.player)
    anchors = ac.parse_anchors(path.read_text(encoding="utf-8")) if path.exists() else []
    nearby = []
    for anchor in anchors:
        dist = ac.haversine(lat, lon, anchor["lat"], anchor["lon"])
        if dist <= anchor["radius"]:
            nearby.append((anchor, dist))
    if nearby:
        return run_anchor_check(args.player, lat, lon, dry_run=args.dry_run)

    if not args.create:
        if anchors:
            nearest = min(anchors, key=lambda a: ac.haversine(lat, lon, a["lat"], a["lon"]))
            dist = ac.haversine(lat, lon, nearest["lat"], nearest["lon"])
            print(f"NO_ANCHOR_NEARBY nearest={nearest['name']} distance_m={dist:.0f} radius_m={nearest['radius']}")
        else:
            print("NO_ANCHORS_EXIST")
        print("Use --create with --name and --words to make this coordinate an Outer Stacks anchor.")
        return 1

    if not args.name or not args.words:
        print("--create requires --name and --words")
        return 2

    record = build_anchor_record(args, lat, lon)
    append_anchor_record(args.player, record, dry_run=args.dry_run)
    log_creation(args.player, args.name, lat, lon, args.radius, dry_run=args.dry_run)
    print(f"ANCHOR_CREATED {args.name} at {lat:.6f}, {lon:.6f} radius={args.radius}m")
    print("ROOM_CREATED: yes")
    print("FIRST_VISIT: send a later coordinate within radius to open the room.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

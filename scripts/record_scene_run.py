#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from scene_ledger import append_entry
import action_lifecycle


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Record one scene packet plus run results into the canonical scene ledger")
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--preflight", type=Path)
    parser.add_argument("--player", default="bj")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    packet = read_json(args.packet)
    results = read_json(args.results)
    preflight = read_json(args.preflight) if args.preflight else {}
    metadata = packet.get("metadata", {})
    mechanics_preflight = preflight or metadata.get("mechanics_preflight", {})
    scene_contract = metadata.get("scene_contract", {})
    entry = {
        "recorded_at": datetime.now().isoformat(),
        "player": args.player,
        "scene_id": packet.get("scene_id"),
        "title": packet.get("title"),
        "mood": packet.get("mood"),
        "intensity": packet.get("intensity"),
        "target": packet.get("target"),
        "channel": packet.get("channel"),
        "text": (packet.get("text") or {}).get("text", ""),
        "voice": (packet.get("voice") or {}).get("text", ""),
        "sequence": results.get("sequence") or packet.get("sequence") or [],
        "results": results.get("results", results),
        "delivery_ok": results.get("delivery_ok"),
        "essential_ok": results.get("essential_ok"),
        "director_slate": metadata.get("director_slate", ""),
        "session_entry": metadata.get("session_entry", ""),
        "story": metadata.get("story", ""),
        "cast": metadata.get("cast", ""),
        "feel": metadata.get("feel", ""),
        "schedule": metadata.get("schedule", ""),
        "source_systems": metadata.get("source_systems", []),
        "mechanics_preflight": mechanics_preflight,
        "scene_contract": scene_contract,
    }
    path = append_entry(entry, dry_run=args.dry_run)
    if not args.dry_run and entry.get("delivery_ok"):
        scene_text = "\n".join(
            part for part in [entry.get("text", ""), entry.get("voice", ""), entry.get("director_slate", "")]
            if part
        )
        noticed = action_lifecycle.mark_actions_noticed_from_scene(
            scene_text,
            scene_id=entry.get("scene_id") or "",
            player=args.player,
        )
        if noticed:
            print(f"noticed_actions={len(noticed)}")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

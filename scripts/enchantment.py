#!/usr/bin/env python3
"""Canonical Enchantment ritual runner.

This script exists so an Enchantment cannot collapse into prose. It handles the
formal phases: offer, start/cost, completion/reward, decline, and status.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
MECHANICS = BASE / "mechanics"
if str(MECHANICS) not in sys.path:
    sys.path.insert(0, str(MECHANICS))
import mechanics_state  # type: ignore

SESSION_DIR = BASE / "players"
LEDGER = BASE / "logs" / "enchantments.jsonl"
BELIEF_COST = 3
BELIEF_REWARD = 9


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def session_path(player: str) -> Path:
    return SESSION_DIR / f"{player}-session.json"


def load_session(player: str) -> dict:
    data = read_json(session_path(player))
    if not isinstance(data, dict):
        data = {}
    mechanics = data.setdefault("mechanics", {})
    enchantment = mechanics.setdefault("enchantment", {})
    enchantment.setdefault("active", None)
    enchantment.setdefault("last", None)
    return data


def save_session(player: str, data: dict) -> None:
    write_json(session_path(player), data)


def append_ledger(event: str, player: str, payload: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    row = {"timestamp": now(), "event": event, "player": player, **payload}
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def update_belief(player: str, delta: int, dry_run: bool) -> None:
    if dry_run:
        return
    subprocess.run(
        [sys.executable, str(BASE / "scripts" / "update-player.py"), player, "belief", f"{delta:+d}"],
        cwd=BASE,
        check=True,
    )


def known_enchantments(player: str) -> list[str]:
    return scene_known_enchantments(player)


def scene_known_enchantments(player: str) -> list[str]:
    text = (BASE / "players" / f"{player}.md").read_text(encoding="utf-8", errors="replace")
    names: list[str] = []
    in_flyleaf = False
    for line in text.splitlines():
        if line.startswith("## The Flyleaf"):
            in_flyleaf = True
            continue
        if in_flyleaf and line.startswith("## "):
            break
        if not in_flyleaf or not line.startswith("|") or "---" in line or "Enchantment" in line:
            continue
        cells = [cell.strip().strip("*") for cell in line.strip("|").split("|")]
        if cells and cells[0]:
            names.append(cells[0])
    return names


def validate_spell(player: str, spell: str) -> None:
    known = known_enchantments(player)
    if spell not in known:
        known_text = ", ".join(known[:12]) or "none found"
        raise SystemExit(f"Unknown or unavailable Enchantment for {player}: {spell}. Known: {known_text}")


def active_or_die(player: str) -> dict:
    data = load_session(player)
    active = data.get("mechanics", {}).get("enchantment", {}).get("active")
    if not active:
        raise SystemExit("No active Enchantment awaiting proof. Start one first.")
    return data


def cmd_status(args: argparse.Namespace) -> int:
    state = mechanics_state.get_mechanics_state(BASE, args.player)
    active = state.get("active_enchantment")
    print("ENCHANTMENT STATUS")
    if active:
        print(f"ACTIVE: {active.get('spell')} on {active.get('target')}")
        print(f"STARTED: {active.get('started_at')}")
        print(f"PROOF_REQUIRED: {active.get('proof_required')}")
    else:
        print("ACTIVE: none")
    last = state.get("enchantment", {}).get("last")
    if last:
        print(f"LAST: {last.get('spell')} on {last.get('target')} -> {last.get('outcome')}")
    return 0


def cmd_offer(args: argparse.Namespace) -> int:
    validate_spell(args.player, args.spell)
    mechanics_state.record_event(BASE, args.player, "offer-enchantment")
    data = load_session(args.player)
    data["mechanics"]["enchantment"]["offer"] = {
        "spell": args.spell,
        "target": args.target,
        "reason": args.reason,
        "offered_at": now(),
    }
    save_session(args.player, data)
    append_ledger("offer", args.player, data["mechanics"]["enchantment"]["offer"])
    print(f"ENCHANTMENT_OFFERED: {args.spell}")
    print(f"TARGET: {args.target}")
    print("NEXT: If the player chooses it, run start. Do not narrate completion yet.")
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    validate_spell(args.player, args.spell)
    data = load_session(args.player)
    existing = data["mechanics"]["enchantment"].get("active")
    if existing and not args.force:
        raise SystemExit(f"Active Enchantment already awaiting proof: {existing.get('spell')} on {existing.get('target')}")

    active = {
        "spell": args.spell,
        "target": args.target,
        "mode": args.mode,
        "started_at": now(),
        "cost": BELIEF_COST,
        "proof_required": "photo" if args.mode == "photo" else "detailed real-world description",
        "status": "awaiting-proof",
    }
    if not args.dry_run:
        update_belief(args.player, -BELIEF_COST, dry_run=False)
        mechanics_state.record_event(BASE, args.player, "accept-enchantment")
        data = load_session(args.player)
        data["mechanics"]["enchantment"]["active"] = active
        save_session(args.player, data)
        append_ledger("start", args.player, active)

    print(f"ENCHANTMENT_STARTED: {args.spell}")
    print(f"TARGET: {args.target}")
    print(f"COST: -{BELIEF_COST} Belief")
    print(f"PROOF_REQUIRED: {active['proof_required']}")
    print("SCENE_INSTRUCTION: Narrate initiation only. Ask the player for the proof. Do not resolve the effect yet.")
    return 0


def cmd_complete(args: argparse.Namespace) -> int:
    data = active_or_die(args.player)
    active = data["mechanics"]["enchantment"]["active"]
    proof = (args.proof or "").strip()
    if len(proof) < 12 and not args.force:
        raise SystemExit("Proof is too thin. Require a photo description or vivid real-world detail before completion.")

    completed = {
        **active,
        "completed_at": now(),
        "proof": proof,
        "outcome": args.outcome,
        "reward": BELIEF_REWARD,
        "status": "completed",
    }
    update_belief(args.player, BELIEF_REWARD, dry_run=args.dry_run)
    if not args.dry_run:
        mechanics_state.record_event(BASE, args.player, "complete-enchantment")
        data = load_session(args.player)
        data["mechanics"]["enchantment"]["active"] = None
        data["mechanics"]["enchantment"]["last"] = completed
        save_session(args.player, data)
        append_ledger("complete", args.player, completed)

    print(f"ENCHANTMENT_COMPLETED: {completed['spell']}")
    print(f"TARGET: {completed['target']}")
    print(f"REWARD: +{BELIEF_REWARD} Belief")
    print(f"OUTCOME: {args.outcome}")
    print("SCENE_INSTRUCTION: Now narrate the sensory effect and how the real proof changes the story.")
    return 0


def cmd_decline(args: argparse.Namespace) -> int:
    mechanics_state.record_event(BASE, args.player, "decline-enchantment")
    append_ledger("decline", args.player, {"reason": args.reason})
    print("ENCHANTMENT_DECLINED")
    print("SCENE_INSTRUCTION: Acknowledge gently. Do not punish unless repeated declines are active.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Canonical Enchantify Enchantment ritual runner.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    status = sub.add_parser("status")
    status.add_argument("player", nargs="?", default="bj")
    status.set_defaults(func=cmd_status)

    offer = sub.add_parser("offer")
    offer.add_argument("player")
    offer.add_argument("--spell", required=True)
    offer.add_argument("--target", required=True)
    offer.add_argument("--reason", default="")
    offer.set_defaults(func=cmd_offer)

    start = sub.add_parser("start")
    start.add_argument("player")
    start.add_argument("--spell", required=True)
    start.add_argument("--target", required=True)
    start.add_argument("--mode", choices=["photo", "description"], default="photo")
    start.add_argument("--force", action="store_true")
    start.add_argument("--dry-run", action="store_true")
    start.set_defaults(func=cmd_start)

    complete = sub.add_parser("complete")
    complete.add_argument("player")
    complete.add_argument("--proof", required=True)
    complete.add_argument("--outcome", required=True)
    complete.add_argument("--force", action="store_true")
    complete.add_argument("--dry-run", action="store_true")
    complete.set_defaults(func=cmd_complete)

    decline = sub.add_parser("decline")
    decline.add_argument("player")
    decline.add_argument("--reason", default="")
    decline.set_defaults(func=cmd_decline)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

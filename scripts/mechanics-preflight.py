#!/usr/bin/env python3
"""
mechanics-preflight.py — explicit active-play mechanics gate.

Usage:
  python3 scripts/mechanics-preflight.py bj
  python3 scripts/mechanics-preflight.py bj --json
  python3 scripts/mechanics-preflight.py bj --strict

Purpose:
- summarize the live mechanics obligations before an active-play reply
- make Compass / Enchantment / dice pressure explicit
- give the Labyrinth one compact source of truth before scene writing

Exit code:
- 0 normally
- 1 in --strict mode when there is active pressure the caller must not ignore
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "mechanics"))

import mechanics_state  # type: ignore


DECLINE_PRESSURE_THRESHOLD = 3


def build_preflight(workspace: Path, player_name: str) -> dict:
    state = mechanics_state.get_mechanics_state(workspace, player_name)
    consecutive_declines = int(state.get("consecutive_declines") or 0)
    belief = state.get("belief")

    compass = {
        "eligible": bool(state.get("should_offer_compass")),
        "locked_today": bool(state.get("compass_locked_today")),
        "last_completed": state.get("last_compass_run"),
    }
    enchantment = {
        "recommended": bool(state.get("should_offer_enchantment")),
        "offered_today": state.get("enchantment", {}).get("offered_on"),
        "completed_today": state.get("enchantment", {}).get("completed_on"),
    }
    dice = {
        "should_roll": bool(state.get("should_roll", True)),
        "last_guidance_at": state.get("last_roll_guidance_at"),
    }
    pressure = {
        "consecutive_declines": consecutive_declines,
        "decline_pressure_active": consecutive_declines >= DECLINE_PRESSURE_THRESHOLD,
        "belief_band": state.get("belief_band"),
    }

    obligations = []
    blocks = []
    warnings = []

    if compass["eligible"]:
        obligations.append("Compass Run should be offered or deliberately deferred in-scene")
    if enchantment["recommended"]:
        obligations.append("Enchantment should be offered or its absence justified in-scene")
    if compass["locked_today"]:
        blocks.append("Do not present Compass Run completion as available again today")
    if dice["should_roll"]:
        warnings.append("Use belief dice when the next action is risky and uncertain")
    if pressure["decline_pressure_active"]:
        warnings.append("Repeated declines are active; another refusal should carry believable cost")
    if belief is not None and belief <= 20:
        warnings.append("Belief is critically low")

    summary_parts = [f"belief={belief if belief is not None else '?'} ({pressure['belief_band']})"]
    if compass["eligible"]:
        summary_parts.append("compass=offer")
    elif compass["locked_today"]:
        summary_parts.append("compass=locked-today")
    else:
        summary_parts.append("compass=not-needed-now")

    if enchantment["recommended"]:
        summary_parts.append("enchantment=offer")
    else:
        summary_parts.append("enchantment=not-needed-now")

    summary_parts.append("dice=roll-on-risk" if dice["should_roll"] else "dice=light")

    if pressure["decline_pressure_active"]:
        summary_parts.append(f"declines={consecutive_declines}:pressure")
    elif consecutive_declines:
        summary_parts.append(f"declines={consecutive_declines}")

    return {
        "player": player_name,
        "state": state,
        "compass": compass,
        "enchantment": enchantment,
        "dice": dice,
        "pressure": pressure,
        "obligations": obligations,
        "blocks": blocks,
        "warnings": warnings,
        "summary": " | ".join(summary_parts),
    }


def print_human(preflight: dict) -> None:
    print("MECHANICS PREFLIGHT")
    print(preflight["summary"])
    if preflight["obligations"]:
        print("OBLIGATIONS:")
        for item in preflight["obligations"]:
            print(f"- {item}")
    if preflight["blocks"]:
        print("BLOCKS:")
        for item in preflight["blocks"]:
            print(f"- {item}")
    if preflight["warnings"]:
        print("WARNINGS:")
        for item in preflight["warnings"]:
            print(f"- {item}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Active-play mechanics gate for Enchantify")
    parser.add_argument("player", nargs="?", default="bj")
    parser.add_argument("--workspace", default=str(BASE))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Print the current mechanics obligations without recording a preflight timestamp.",
    )
    args = parser.parse_args()

    workspace = Path(args.workspace)
    preflight = build_preflight(workspace, args.player)
    if not args.check_only:
        mechanics_state.record_event(workspace, args.player, "mechanics-preflight")

    if args.json:
        print(json.dumps(preflight, indent=2, ensure_ascii=False))
    else:
        print_human(preflight)

    if args.strict and (preflight["obligations"] or preflight["blocks"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

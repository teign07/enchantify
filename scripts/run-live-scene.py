#!/usr/bin/env python3
"""
run-live-scene.py — canonical live scene path for Enchantify.

This is the one obvious runtime entrypoint for a completed scene.
It preserves the existing story spine, then routes through play_scene so
delivery, ledgering, and conductor semantics happen consistently.

Telegram delivery rule:
Text goes to Telegram as soon as it is ready; voice and enrichments follow.
The reader should never stare at silence while TTS or image work runs.

Important:
  Run `python3 scripts/mechanics-preflight.py [player_name]` before this.
  `play_scene.py` enforces a fresh mechanics preflight from the last 15 minutes.

Usage:
  python3 scripts/mechanics-preflight.py bj
  python3 scripts/run-live-scene.py bj --text-file /tmp/enchantify-scene.txt
  python3 scripts/run-live-scene.py bj --text-file /tmp/enchantify-scene.txt --voice-file /tmp/enchantify-voice.txt --intensity ritual
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SCRIPTS = BASE / "scripts"
sys.path.insert(0, str(BASE / "mechanics"))
import mechanics_state  # type: ignore

PREFLIGHT_MAX_AGE_MINUTES = 15


def _known_enchantments(player: str) -> list[str]:
    player_file = BASE / "players" / f"{player}.md"
    if not player_file.exists():
        return []
    text = player_file.read_text(encoding="utf-8", errors="ignore")
    block = re.search(r"## The Flyleaf\s*\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    if not block:
        return []
    names: list[str] = []
    for line in block.group(1).splitlines():
        if not line.startswith("|") or "---" in line or "Enchantment" in line:
            continue
        cells = [cell.strip().strip("*") for cell in line.strip("|").split("|")]
        if cells and cells[0]:
            names.append(cells[0].lower())
    return names


def _delivered_mechanics(text_file: Path, player: str) -> dict[str, bool]:
    state = mechanics_state.get_mechanics_state(BASE, player)
    text = text_file.read_text(encoding="utf-8").lower()
    choices = "\n".join(
        line for line in text.splitlines()
        if re.match(r"^\s*(?:[*-]\s*)?\(?[123]\)?[.)]\s*", line)
    ).lower()
    known = _known_enchantments(player)
    has_compass = "compass" in choices
    has_enchantment = "enchantment" in choices or "enchant" in choices or any(name in choices for name in known)
    return {
        "compass": bool(state.get("should_offer_compass")) and has_compass,
        "enchantment": bool(state.get("should_offer_enchantment")) and has_enchantment,
    }


def _run_scene_contract(args: argparse.Namespace) -> subprocess.CompletedProcess[str]:
    contract_cmd = [
        sys.executable,
        str(SCRIPTS / "scene-contract.py"),
        args.player,
        "--validate-scene",
        str(args.text_file),
    ]
    if args.scene_mode:
        contract_cmd += ["--mode", args.scene_mode]
    if args.drama_budget:
        contract_cmd += ["--drama-budget", args.drama_budget]
    return subprocess.run(contract_cmd, capture_output=True, text=True)


def _repair_scene_contract(args: argparse.Namespace) -> subprocess.CompletedProcess[str]:
    repair_cmd = [
        sys.executable,
        str(SCRIPTS / "scene-contract.py"),
        args.player,
        "--repair-scene",
        str(args.text_file),
    ]
    if args.scene_mode:
        repair_cmd += ["--mode", args.scene_mode]
    if args.drama_budget:
        repair_cmd += ["--drama-budget", args.drama_budget]
    return subprocess.run(repair_cmd, capture_output=True, text=True)


def _run_scene_choices(args: argparse.Namespace) -> subprocess.CompletedProcess[str]:
    choices_cmd = [
        sys.executable,
        str(SCRIPTS / "scene-choices.py"),
        "--scene-file",
        str(args.text_file),
        "--strict-balance",
    ]
    return subprocess.run(choices_cmd, capture_output=True, text=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Canonical live scene runner. Requires mechanics-preflight within the last 15 minutes before delivery."
    )
    parser.add_argument("player", nargs="?", default="bj")
    parser.add_argument("--text-file", type=Path, required=True)
    parser.add_argument("--voice-file", type=Path)
    parser.add_argument("--title")
    parser.add_argument("--mood")
    parser.add_argument(
        "--scene-mode",
        choices=["slice", "school-life", "dorm", "arc", "mystery", "aftermath", "compass", "enchantment"],
    )
    parser.add_argument("--drama-budget", choices=["low", "medium", "high"])
    parser.add_argument("--intensity", default="cinematic")
    parser.add_argument("--target", default="8729557865")
    parser.add_argument("--channel", default="telegram")
    parser.add_argument("--account", default="enchantify")
    parser.add_argument(
        "--surface",
        choices=["telegram", "chat"],
        default="telegram",
        help="telegram = deliver to Telegram; chat = validate, ledger, print scene for Cursor/desktop",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--bypass-mechanics-preflight",
        action="store_true",
        help="Allow dry-run diagnostics to exercise the delivery path without recording player state.",
    )
    args = parser.parse_args()

    if args.surface == "chat":
        args.channel = "cursor"
        args.target = ""

    if args.bypass_mechanics_preflight and not args.dry_run:
        sys.stderr.write("--bypass-mechanics-preflight is only allowed with --dry-run.\n")
        return 2

    preflight_status = {"ok": True, "message": "Mechanics preflight bypassed for dry-run diagnostics."}
    if not args.bypass_mechanics_preflight:
        preflight_status = mechanics_state.get_preflight_status(BASE, args.player, max_age_minutes=PREFLIGHT_MAX_AGE_MINUTES)

    if not preflight_status.get("ok"):
        sys.stderr.write(
            "run-live-scene requires a fresh mechanics preflight first.\n"
            f"Reason: {preflight_status.get('message')}\n"
            "Run:\n"
            f"  python3 scripts/mechanics-preflight.py {args.player}\n"
        )
        return 2

    contract = _run_scene_contract(args)
    if contract.returncode != 0:
        repair = _repair_scene_contract(args)
        if repair.returncode == 0:
            contract = _run_scene_contract(args)
        if contract.returncode != 0:
            sys.stderr.write("run-live-scene refused delivery after one scene-contract repair attempt.\n")
            detail = (contract.stderr or contract.stdout or repair.stderr or repair.stdout or "").strip()
            sys.stderr.write(detail[:1600] + "\n")
            return contract.returncode or 1

    choices = _run_scene_choices(args)
    if choices.returncode != 0:
        repair = _repair_scene_contract(args)
        if repair.returncode == 0:
            contract = _run_scene_contract(args)
            choices = _run_scene_choices(args) if contract.returncode == 0 else choices
        if choices.returncode != 0:
            sys.stderr.write("run-live-scene refused delivery after one Rule of Three repair attempt.\n")
            detail = (choices.stderr or choices.stdout or repair.stderr or repair.stdout or "").strip()
            sys.stderr.write(detail[:1600] + "\n")
            return choices.returncode or 1

    cmd = [
        sys.executable,
        str(SCRIPTS / "play_scene.py"),
        args.player,
        "--text-file",
        str(args.text_file),
        "--intensity",
        args.intensity,
        "--target",
        args.target,
        "--channel",
        args.channel,
        "--account",
        args.account,
        "--fallback-tts",
    ]
    if args.voice_file:
        cmd += ["--voice-file", str(args.voice_file)]
    if args.title:
        cmd += ["--title", args.title]
    if args.mood:
        cmd += ["--mood", args.mood]
    if args.scene_mode:
        cmd += ["--scene-mode", args.scene_mode]
    if args.drama_budget:
        cmd += ["--drama-budget", args.drama_budget]
    if args.dry_run:
        cmd.append("--dry-run")
    if args.bypass_mechanics_preflight:
        cmd.append("--bypass-mechanics-preflight")

    delivered_mechanics = _delivered_mechanics(args.text_file, args.player)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    # Print a compact summary instead of raw conductor JSON, which can contain
    # voice-detail text that the LLM misreads as instructions to re-run the scene.
    if proc.returncode == 0:
        if delivered_mechanics["compass"]:
            mechanics_state.record_event(BASE, args.player, "offer-compass")
        if delivered_mechanics["enchantment"]:
            mechanics_state.record_event(BASE, args.player, "offer-enchantment")
        if args.surface == "chat":
            scene_text = args.text_file.read_text(encoding="utf-8").strip()
            print("BOOK_OPEN_OK")
            print("SCENE_FOR_PLAYER_BEGIN")
            print(scene_text)
            print("SCENE_FOR_PLAYER_END")
            print("DELIVERY: chat-surface (ledger recorded; no Telegram send)")
        else:
            print(f"SCENE DELIVERED: exit 0")
    else:
        # On failure, emit stderr so the agent can diagnose without the full JSON blob.
        err = (proc.stderr or proc.stdout or "").strip()
        print(f"SCENE FAILED: exit {proc.returncode}", file=sys.stderr)
        if err:
            print(err[:1200], file=sys.stderr)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())

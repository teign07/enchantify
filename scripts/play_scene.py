#!/usr/bin/env python3
"""
play_scene.py — real game entrypoint for multimodal scene delivery.

Canonical runtime note:
scripts/run-live-scene.py is the required live-entry wrapper for normal active play.
This file remains the implementation entrypoint underneath that wrapper.

This keeps Enchantify's story engine primary.
It assumes the narrative scene already exists as text, then:
1. builds a ScenePacket from the current game state
2. runs the scene conductor

Important runtime rule:
Normal Telegram active-play scenes should enter through run-live-scene.py,
not by calling this file directly from ad hoc flows.

Usage:
  python3 scripts/play_scene.py bj --text-file /tmp/enchantify-scene.txt
  python3 scripts/play_scene.py bj --text-file /tmp/enchantify-scene.txt --voice-file /tmp/enchantify-voice.txt --dry-run
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SCRIPTS = BASE / "scripts"
OUTBOX = BASE / "tmp" / "scene-outbox"
sys.path.insert(0, str(BASE / "mechanics"))
import mechanics_state  # type: ignore

PREFLIGHT_MAX_AGE_MINUTES = 15


def run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True)


def extract_json_payload(text: str) -> dict | None:
    text = (text or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


def text_delivery_succeeded(conducted_payload: dict | None) -> bool:
    """True when the canonical text response already reached Telegram."""
    if not isinstance(conducted_payload, dict):
        return False
    results = conducted_payload.get("results")
    if not isinstance(results, dict):
        return False
    text_result = results.get("text")
    if not isinstance(text_result, dict):
        return False
    return bool(text_result.get("ok") and (text_result.get("delivered") or text_result.get("message_ids")))


def require_fresh_mechanics_preflight(player: str) -> tuple[bool, str, dict]:
    status = mechanics_state.get_preflight_status(BASE, player, max_age_minutes=PREFLIGHT_MAX_AGE_MINUTES)
    if not status.get("ok"):
        return False, (
            "mechanics preflight required before play_scene.\n"
            f"Reason: {status.get('message')}\n"
            f"Run: python3 scripts/mechanics-preflight.py {player}"
        ), status
    return True, status.get("message", ""), status


def send_voice_fallback(voice_file: Path | None, text_file: Path, target: str, channel: str, account: str) -> int:
    # Always use the full scene text for fallback audio to avoid stubs
    scene_text = text_file.read_text(encoding="utf-8").strip()
    # Ensure it's wrapped in the default narrator voice if not already tagged
    if not scene_text.startswith("[") or "]" not in scene_text[:10]:
        fallback_text = f"[bm_lewis] {scene_text}"
    else:
        fallback_text = scene_text

    cmd = [
        sys.executable,
        str(SCRIPTS / "multi_voice_tts.py"),
        "--target",
        target,
        "--channel",
        channel,
        "--account",
        account,
        fallback_text,
    ]
    sent = run(cmd)
    if sent.stdout:
        print(sent.stdout.strip())
    if sent.returncode != 0 and sent.stderr:
        sys.stderr.write(sent.stderr.strip() + "\n")
    return sent.returncode or 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("player", nargs="?", default="bj")
    parser.add_argument("--text-file", type=Path, required=True)
    parser.add_argument("--voice-file", type=Path)
    parser.add_argument("--packet-out", type=Path)
    parser.add_argument("--title")
    parser.add_argument("--mood")
    parser.add_argument("--scene-mode", choices=["slice", "school-life", "arc", "mystery", "aftermath", "compass", "enchantment"])
    parser.add_argument("--drama-budget", choices=["low", "medium", "high"])
    parser.add_argument("--intensity", default="cinematic")
    parser.add_argument("--target", default="8729557865")
    parser.add_argument("--channel", default="telegram")
    parser.add_argument("--account", default="enchantify")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fallback-tts", action="store_true", help="If multimodal delivery fails, fall back to normal Telegram TTS delivery")
    parser.add_argument("--no-ledger", action="store_true", help="Skip canonical scene ledger recording")
    parser.add_argument("--bypass-mechanics-preflight", action="store_true", help="Deliberately bypass the fresh mechanics-preflight runtime gate")
    args = parser.parse_args()

    preflight_status = {
        "ok": True,
        "reason": "bypassed" if args.bypass_mechanics_preflight else None,
        "message": "Mechanics preflight bypassed deliberately." if args.bypass_mechanics_preflight else None,
        "last_preflight_at": None,
        "max_age_minutes": PREFLIGHT_MAX_AGE_MINUTES,
    }
    if not args.bypass_mechanics_preflight:
        ok, detail, preflight_status = require_fresh_mechanics_preflight(args.player)
        if not ok:
            sys.stderr.write(detail + "\n")
            return 2

    packet_out = args.packet_out or (OUTBOX / f"{args.text_file.stem}-packet.json")
    packet_out.parent.mkdir(parents=True, exist_ok=True)

    build_cmd = [
        sys.executable,
        str(SCRIPTS / "scene_packet_builder.py"),
        args.player,
        "--text-file",
        str(args.text_file),
        "--out",
        str(packet_out),
        "--intensity",
        args.intensity,
        "--target",
        args.target,
        "--channel",
        args.channel,
        "--account",
        args.account,
    ]
    if args.voice_file:
        build_cmd += ["--voice-file", str(args.voice_file)]
    if args.title:
        build_cmd += ["--title", args.title]
    if args.mood:
        build_cmd += ["--mood", args.mood]
    if args.scene_mode:
        build_cmd += ["--scene-mode", args.scene_mode]
    if args.drama_budget:
        build_cmd += ["--drama-budget", args.drama_budget]

    built = run(build_cmd)
    if built.returncode != 0:
        sys.stderr.write((built.stderr or built.stdout or "scene packet build failed").strip() + "\n")
        return built.returncode or 1

    conduct_cmd = [
        sys.executable,
        str(SCRIPTS / "scene_conductor.py"),
        "--packet",
        str(packet_out),
    ]
    if args.dry_run:
        conduct_cmd.append("--dry-run")

    conducted = run(conduct_cmd)
    conducted_payload = extract_json_payload(conducted.stdout)
    if conducted.stdout:
        try:
            payload = json.loads(conducted.stdout)
            print(json.dumps({
                "packet": str(packet_out),
                "results": payload,
            }, indent=2))
        except Exception:
            print(conducted.stdout.strip())
    if conducted.returncode != 0 and conducted.stderr:
        sys.stderr.write(conducted.stderr.strip() + "\n")
    actual_scene_id = (conducted_payload or {}).get("scene_id")
    run_record = (
        OUTBOX / f"{actual_scene_id}-run.json"
        if actual_scene_id
        else OUTBOX / f"{packet_out.stem.replace('-packet', '')}-run.json"
    )
    if not args.no_ledger and run_record.exists():
        ledger_meta_path = OUTBOX / f"{packet_out.stem.replace('-packet', '')}-preflight.json"
        ledger_meta_path.write_text(json.dumps(preflight_status, indent=2), encoding="utf-8")
        ledger_cmd = [
            sys.executable,
            str(SCRIPTS / "record_scene_run.py"),
            "--player",
            args.player,
            "--packet",
            str(packet_out),
            "--results",
            str(run_record),
            "--preflight",
            str(ledger_meta_path),
        ]
        if args.dry_run:
            ledger_cmd.append("--dry-run")
        ledger = run(ledger_cmd)
        if ledger.stdout:
            print(ledger.stdout.strip())
        if ledger.returncode != 0 and ledger.stderr:
            sys.stderr.write(ledger.stderr.strip() + "\n")
    if conducted.returncode != 0 and args.fallback_tts and not args.dry_run:
        if text_delivery_succeeded(conducted_payload):
            print("FALLBACK SKIPPED: text delivery already succeeded; not sending duplicate fallback.")
            return conducted.returncode
        return send_voice_fallback(args.voice_file, args.text_file, args.target, args.channel, args.account)
    return conducted.returncode


if __name__ == "__main__":
    raise SystemExit(main())

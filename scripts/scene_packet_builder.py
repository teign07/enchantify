#!/usr/bin/env python3
"""
scene_packet_builder.py — build a lightweight ScenePacket from the current
Enchantify scene spine without replacing it.

Normal live runs should enter through scripts/run-live-scene.py,
which calls play_scene.py, which calls this builder.

This is glue, not a new source of truth.
It reads the existing scene-director/session-entry outputs and wraps a finished
scene into a conductor-ready packet.

Usage:
  python3 scripts/scene_packet_builder.py bj --text-file /tmp/scene.txt
  python3 scripts/scene_packet_builder.py bj --text-file /tmp/scene.txt --voice-file /tmp/voice.txt --out /tmp/scene.json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SCRIPTS = BASE / "scripts"
DEFAULT_TARGET = "8729557865"
sys.path.insert(0, str(BASE / "mechanics"))
import mechanics_state  # type: ignore


def run_script(args: list[str]) -> str:
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        return ""
    return (proc.stdout or "").strip()


def read_text(path: Path | None) -> str:
    if not path or not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def parse_slate_value(slate: str, key: str) -> str:
    m = re.search(rf"^{re.escape(key)}:\s*(.+)$", slate, re.MULTILINE)
    return m.group(1).strip() if m else ""


def build_image_prompt(title: str, mood: str, feel: str, cast: str, scene_text: str) -> str:
    scene_hint = scene_text.replace("\n", " ").strip()
    scene_hint = re.sub(r"\s+", " ", scene_hint)
    scene_hint = scene_hint[:260]
    cast_hint = cast[:120] if cast else "current scene cast"
    feel_hint = feel[:120] if feel else mood
    style = (
        "illustrated in sparse pen-and-ink line art with watercolor washes on textured parchment, "
        "mostly muted sepia and gray, with selective pops of teal, gold, and red in magical details"
    )
    return (
        f"{title}, {mood}, {feel_hint}, featuring {cast_hint}. "
        f"Scene frame: {scene_hint}. "
        f"{style}. Literary magical-archive look. No text, no UI elements, no labels."
    )


def build_music_prompt(title: str, mood: str, feel: str, story: str, schedule: str) -> str:
    parts = [title, mood, feel, story, schedule]
    text = ", ".join(p for p in parts if p)
    text = re.sub(r"\s+", " ", text).strip()
    return f"Short instrumental scene cue, {text}, magical library atmosphere, cinematic but intimate, no vocals."


def title_from_scene_text(scene_text: str) -> str:
    for line in scene_text.splitlines():
        line = line.strip().strip("*")
        if not line or line.startswith("["):
            continue
        line = re.sub(r"\s+", " ", line)
        sentence = re.split(r"(?<=[.!?])\s+", line)[0]
        words = sentence.split()
        if len(words) > 12:
            sentence = " ".join(words[:12])
        return sentence[:90].rstrip(".,;:")
    return "Enchantify scene"


def clean_title(candidate: str, scene_text: str) -> str:
    title = (candidate or "").strip()
    if not title:
        return title_from_scene_text(scene_text)
    operational = (
        "session closed cleanly",
        "fixing",
        "scripts/",
        ".py",
        "bug",
        "hard rule now lives",
    )
    if any(item in title.lower() for item in operational):
        return title_from_scene_text(scene_text)
    return title[:110].rstrip(".,;:")


def infer_spotify_chapter(mood: str, story: str, feel: str) -> str:
    joined = " ".join([mood, story, feel]).lower()
    if any(k in joined for k in ["conflict", "thorn", "pressure", "tense", "wrong"]):
        return "Duskthorn"
    if any(k in joined for k in ["together", "friend", "shared", "collaborative"]):
        return "Riddlewind"
    if any(k in joined for k in ["still", "quiet", "gentle", "receive", "moss"]):
        return "Mossbloom"
    if any(k in joined for k in ["surge", "now", "wave", "bright", "alive"]):
        return "Tidecrest"
    return "Emberheart"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("player", nargs="?", default="bj")
    parser.add_argument("--text-file", type=Path, required=True)
    parser.add_argument("--voice-file", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--title")
    parser.add_argument("--mood")
    parser.add_argument("--scene-mode", choices=["slice", "school-life", "arc", "mystery", "aftermath", "compass", "enchantment"])
    parser.add_argument("--drama-budget", choices=["low", "medium", "high"])
    parser.add_argument("--intensity", default="cinematic")
    parser.add_argument("--target", default=DEFAULT_TARGET)
    parser.add_argument("--channel", default="telegram")
    parser.add_argument("--account", default="enchantify")
    args = parser.parse_args()

    scene_text = read_text(args.text_file)
    if not scene_text:
        print("text file missing or empty", file=sys.stderr)
        return 1

    voice_text = read_text(args.voice_file) or f"[bm_lewis] {scene_text}"
    slate = run_script([sys.executable, str(SCRIPTS / "scene-director.py"), args.player, "--slate-only"])
    entry = run_script([sys.executable, str(SCRIPTS / "session-entry.py"), args.player])

    cast = parse_slate_value(slate, "CAST")
    feel = parse_slate_value(slate, "FEEL")
    story = parse_slate_value(slate, "STORY")
    schedule = parse_slate_value(slate, "SCHEDULE")

    title = args.title or parse_slate_value(slate, "SCENE_ANCHOR") or ""
    title = clean_title(title.split("|")[0].strip() if title else "", scene_text)
    mood = args.mood or parse_slate_value(slate, "FEEL") or "living library atmosphere"

    preflight_status = mechanics_state.get_preflight_status(BASE, args.player)
    contract_cmd = [sys.executable, str(SCRIPTS / "scene-contract.py"), args.player, "--json"]
    if args.scene_mode:
        contract_cmd += ["--mode", args.scene_mode]
    if args.drama_budget:
        contract_cmd += ["--drama-budget", args.drama_budget]
    contract_text = run_script(contract_cmd)
    try:
        scene_contract = json.loads(contract_text) if contract_text else {}
    except json.JSONDecodeError:
        scene_contract = {}

    scene_id = f"scene-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    packet = {
        "scene_id": scene_id,
        "title": title,
        "mood": mood,
        "intensity": args.intensity,
        "target": args.target,
        "channel": args.channel,
        "account": args.account,
        "routing_model": "claude-cli/claude-haiku-4-5",
        "text": {
            "text": scene_text,
        },
        "voice": {
            "text": voice_text,
        },
        "image": {
            "prompt": build_image_prompt(title, mood, feel, cast, scene_text),
            "filename_hint": f"{scene_id}.png",
            "backend": "drawthings",
        },
        "music": {
            "prompt": build_music_prompt(title, mood, feel, story, schedule),
            "instrumental": True,
            "duration_seconds": 20,
            "deliver": args.intensity == "ritual",
        },
        "spotify": {
            "mood": mood,
            "action": "scene_mood",
            "chapter": infer_spotify_chapter(mood, story, feel),
            "tier": "Sovereign" if args.intensity == "ritual" else "Influenced",
        },
        "metadata": {
            "player": args.player,
            "director_slate": slate,
            "session_entry": entry,
            "cast": cast,
            "feel": feel,
            "story": story,
            "schedule": schedule,
            "preserve_scene_construction": True,
            "source_systems": ["session-entry", "scene-director", "narrative-scene"],
            "mechanics_preflight": preflight_status,
            "scene_contract": scene_contract,
        },
    }

    out = args.out or (BASE / "tmp" / "scene-outbox" / f"{scene_id}-packet.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(packet, indent=2), encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

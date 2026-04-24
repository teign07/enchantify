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
    return (
        f"{title}, {mood}, {feel_hint}, featuring {cast_hint}. "
        f"Scene frame: {scene_hint}. "
        "Whimsical, dark, modern anime with pops of color."
    )


def build_music_prompt(title: str, mood: str, feel: str, story: str, schedule: str) -> str:
    parts = [title, mood, feel, story, schedule]
    text = ", ".join(p for p in parts if p)
    text = re.sub(r"\s+", " ", text).strip()
    return f"Short instrumental scene cue, {text}, magical library atmosphere, cinematic but intimate, no vocals."


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

    title = args.title or parse_slate_value(slate, "SCENE_ANCHOR") or "Enchantify scene"
    title = title.split("|")[0].strip() if title else "Enchantify scene"
    mood = args.mood or parse_slate_value(slate, "FEEL") or "living library atmosphere"

    preflight_status = mechanics_state.get_preflight_status(BASE, args.player)

    scene_id = f"scene-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    packet = {
        "scene_id": scene_id,
        "title": title,
        "mood": mood,
        "intensity": args.intensity,
        "target": args.target,
        "channel": args.channel,
        "account": args.account,
        "routing_model": "openai-codex/gpt-5.4-mini",
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
        },
    }

    out = args.out or (BASE / "tmp" / "scene-outbox" / f"{scene_id}-packet.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(packet, indent=2), encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

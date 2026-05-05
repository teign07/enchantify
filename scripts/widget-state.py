#!/usr/bin/env python3
"""
widget-state.py — Export a compact Inside Cover state for the iOS widget.

The iOS prototype can import hooks/widget-state.json. The exporter also copies
one rotating generated Enchantify image to hooks/widget-image.png so the widget
has a living visual surface without generating a fresh image every refresh.

Usage:
  python3 scripts/widget-state.py bj
  python3 scripts/widget-state.py bj --json
"""

import argparse
import base64
import json
import random
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
HOOKS = BASE / "hooks"
SCRIPTS = BASE / "scripts"
OUT_JSON = HOOKS / "widget-state.json"
OUT_IMAGE = HOOKS / "widget-image.png"

sys.path.insert(0, str(SCRIPTS))
try:
    from schedule import get_schedule_data
except Exception:
    get_schedule_data = None


def run_json(cmd: list[str]) -> dict:
    proc = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        return {}
    try:
        return json.loads(proc.stdout)
    except Exception:
        return {}


def schedule_summary() -> dict:
    if not get_schedule_data:
        return {}
    data = get_schedule_data()
    club = data.get("club")
    cls_now = data.get("class_now")
    cls_next = data.get("class_next")
    practice = data.get("practice") or {}
    return {
        "day": f"{data.get('weekday_name')} · Day {data.get('academy_day')} · {data.get('tone')}",
        "block": str(data.get("block", "")).replace("_", " ").title(),
        "now": f"{cls_now[0]} · {cls_now[1]}" if cls_now else "No class in session",
        "next": f"{cls_next[0]} · {data.get('class_next_day')} {data.get('class_next_time')}" if cls_next else "",
        "club": f"{club[0]} · 7 PM" if club else "",
        "practice": practice.get("name", ""),
        "practicePrompt": practice.get("prompt", ""),
    }


def narrative_health(player: str) -> dict:
    report = run_json([sys.executable, str(SCRIPTS / "narrative-health.py"), player, "--json"])
    if not report:
        return {"status": "", "score": ""}
    status = report.get("status", "")
    score = report.get("score", "")
    phrase = {
        "OK": "The shelves are steady.",
        "WATCH": "The shelves are listening.",
        "WARN": "The shelves are restless.",
        "ALERT": "The shelves are ringing softly.",
        "ERROR": "The ink is blotting at the edges.",
    }.get(status, "The Book is awake.")
    return {"status": status, "score": score, "phrase": phrase}


def classroom(player: str) -> dict:
    packet = run_json([sys.executable, str(SCRIPTS / "class-lecture.py"), player, "--status", "--json"])
    if not packet:
        return {}
    return {
        "className": packet.get("class_name", ""),
        "professor": packet.get("professor", ""),
        "lesson": packet.get("lesson_title", ""),
        "segment": packet.get("segment", ""),
        "active": bool(packet.get("active")),
    }


def latest_note(schedule: dict, health: dict, class_info: dict) -> str:
    if class_info.get("active"):
        return f"{class_info.get('professor', 'The professor')} is still at the board."
    if schedule.get("club"):
        return f"{schedule['club']} is written in the margin tonight."
    if schedule.get("practice"):
        return f"Practice waits: {schedule['practice']}."
    return health.get("phrase") or "The Book is awake behind the glass."


def image_candidates() -> list[Path]:
    roots = [
        BASE / "logs" / "scene-gallery",
        BASE / "bleed" / "images",
        BASE / "wallpapers",
    ]
    found: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for ext in ("*.png", "*.jpg", "*.jpeg"):
            found.extend(root.rglob(ext))
    return [p for p in found if p.is_file()]


def choose_image() -> tuple[str, str]:
    candidates = image_candidates()
    if not candidates:
        return "", ""
    # Stable-ish daily rotation with enough variation that the page feels alive.
    seed = datetime.now().strftime("%Y-%m-%d")
    rng = random.Random(seed)
    src = rng.choice(sorted(candidates))
    try:
        shutil.copyfile(src, OUT_IMAGE)
        image_path = OUT_IMAGE
    except Exception:
        image_path = src
    try:
        image_data = base64.b64encode(image_path.read_bytes()).decode("ascii")
    except Exception:
        image_data = ""
    return str(image_path.relative_to(BASE)), image_data


def build_state(player: str) -> dict:
    sched = schedule_summary()
    health = narrative_health(player)
    klass = classroom(player)
    image_path, image_data = choose_image()
    return {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "player": player,
        "title": "The Inside Cover",
        "day": sched.get("day", ""),
        "block": sched.get("block", ""),
        "now": sched.get("now", ""),
        "next": sched.get("next", ""),
        "club": sched.get("club", ""),
        "practice": sched.get("practice", ""),
        "practicePrompt": sched.get("practicePrompt", ""),
        "classroom": klass,
        "health": health,
        "note": latest_note(sched, health, klass),
        "image": image_path,
        "imageData": image_data,
        "openURL": "telegram://",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export iOS widget state.")
    parser.add_argument("player", nargs="?", default="bj")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    state = build_state(args.player)
    HOOKS.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(state, indent=2, ensure_ascii=False))
    else:
        print(f"✓ Wrote {OUT_JSON}")
        if state.get("image"):
            print(f"✓ Widget image: {state['image']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

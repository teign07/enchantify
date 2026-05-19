#!/usr/bin/env python3
"""
class-lecture.py — Multi-turn classroom lecture state for Enchantify.

This script does not send messages. It prepares a class-scene directive for the
Labyrinth and tracks lesson progress. Lessons advance only when --attend or
--advance is used.

Usage:
  python3 scripts/class-lecture.py bj --status
  python3 scripts/class-lecture.py bj --attend
  python3 scripts/class-lecture.py bj --class-id basic-enchantments --attend
  python3 scripts/class-lecture.py bj --advance
  python3 scripts/class-lecture.py bj --json
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
CONFIG = BASE / "config" / "class-curriculum.json"
PLAYERS = BASE / "players"
WONDER = BASE / "lore" / "wonder-compass-book"

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
try:
    from schedule import get_schedule_data
except Exception:
    get_schedule_data = None


SCHEDULE_TO_CLASS = {
    "The Art of the Glint": "art-of-the-glint",
    "Wayfinding & Kineticism": "wayfinding-kineticism",
    "Synesthetic Resonance": "synesthetic-resonance",
    "Ink-Binding": "ink-binding",
    "Quiet Hours": "quiet-hours",
    "Compass Running": "quiet-hours",
    "Basic Enchantments": "basic-enchantments",
    "Book Jumping": "book-jumping",
}


CHAPTER_FILES = {
    "read-this-first": WONDER / "read-this-first.md",
    "introduction": WONDER / "introduction.md",
    "chapter1a": WONDER / "chapter1a.md",
    "chapter1b": WONDER / "chapter1b.md",
    "chapter2": WONDER / "chapter2.md",
    "chapter3": WONDER / "chapter3.md",
    "chapter4a": WONDER / "chapter4a.md",
    "chapter4b": WONDER / "chapter4b.md",
    "chapter5": WONDER / "chapter5.md",
    "chapter6a": WONDER / "chapter6a.md",
    "chapter6b": WONDER / "chapter6b.md",
    "chapter7": WONDER / "chapter7.md",
    "chapter8a": WONDER / "chapter8a.md",
    "chapter8b": WONDER / "chapter8b.md",
    "chapter9": WONDER / "chapter9.md",
    "chapter10": WONDER / "chapter10.md",
    "chapter11a": WONDER / "chapter11a.md",
    "chapter11b": WONDER / "chapter11b.md",
    "chapter11c": WONDER / "chapter11c.md",
    "chapter11d": WONDER / "chapter11d.md",
    "chapter12a": WONDER / "chapter12a.md",
    "chapter12b": WONDER / "chapter12b.md",
    "chapter13": WONDER / "chapter13.md",
    "chapter14": WONDER / "chapter14.md",
    "chapter15": WONDER / "chapter15.md",
    "chapter16": WONDER / "chapter16.md",
    "chapter17": WONDER / "chapter17.md",
    "chapter18": WONDER / "chapter18.md",
    "chapter19": WONDER / "chapter19.md",
    "chapter20": WONDER / "chapter20.md",
    "chapter21": WONDER / "chapter21.md",
    "chapter22": WONDER / "chapter22.md",
    "chapter23": WONDER / "chapter23.md",
    "chapter24": WONDER / "chapter24.md",
    "chapter25": WONDER / "chapter25.md",
    "chapter26": WONDER / "chapter26.md",
}


def load_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def state_path(player):
    return PLAYERS / f"{player}-classes.json"


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def current_class_id(include_next=True):
    if not get_schedule_data:
        return None
    data = get_schedule_data()
    cls = data.get("class_now")
    if not cls and include_next:
        cls = data.get("class_next")
    if not cls:
        return None
    return SCHEDULE_TO_CLASS.get(cls[0])


def active_class_id(state):
    for class_id, cstate in state.get("classes", {}).items():
        if cstate.get("active"):
            return class_id
    return None


def chapter_status(source):
    if source.endswith(".md") or source.startswith("lore/"):
        path = BASE / source
    else:
        path = CHAPTER_FILES.get(source)
    if not path:
        return {"id": source, "available": False, "path": ""}
    return {"id": source, "available": path.exists(), "path": str(path.relative_to(BASE))}


def class_state(state, class_id):
    classes = state.setdefault("classes", {})
    return classes.setdefault(class_id, {
        "lesson_index": 0,
        "active": None,
        "attendances": [],
        "completed_lessons": [],
        "questions": [],
        "practice_offers": []
    })


def active_or_next(course, cstate):
    syllabus = course.get("syllabus", [])
    if not syllabus:
        return None, 0, 0, False
    active = cstate.get("active")
    if active:
        idx = active.get("lesson_index", cstate.get("lesson_index", 0))
        seg = active.get("segment_index", 0)
        return syllabus[min(idx, len(syllabus) - 1)], idx, seg, True
    idx = min(cstate.get("lesson_index", 0), len(syllabus) - 1)
    return syllabus[idx], idx, 0, False


def begin_attendance(state, class_id, course, cstate):
    lesson, idx, seg, was_active = active_or_next(course, cstate)
    if not lesson:
        return None
    if not was_active:
        cstate["active"] = {
            "lesson_id": lesson["id"],
            "lesson_index": idx,
            "segment_index": 0,
            "started_at": now_iso()
        }
    cstate.setdefault("attendances", []).append({
        "at": now_iso(),
        "lesson_id": lesson["id"],
        "segment_index": cstate["active"]["segment_index"]
    })
    state["last_class_id"] = class_id
    state["updated_at"] = now_iso()
    return cstate["active"]


def advance_active(state, class_id, course, cstate):
    active = cstate.get("active")
    if not active:
        begin_attendance(state, class_id, course, cstate)
        active = cstate.get("active")
    lesson, idx, seg, _ = active_or_next(course, cstate)
    if not lesson:
        return {"completed": False, "message": "No lesson available."}
    segments = lesson.get("segments", [])
    next_seg = active.get("segment_index", 0) + 1
    if next_seg >= len(segments):
        completed = {
            "lesson_id": lesson["id"],
            "title": lesson.get("title", ""),
            "completed_at": now_iso()
        }
        cstate.setdefault("completed_lessons", []).append(completed)
        cstate["lesson_index"] = min(idx + 1, max(len(course.get("syllabus", [])) - 1, 0))
        cstate["active"] = None
        state["last_class_id"] = class_id
        state["updated_at"] = now_iso()
        return {"completed": True, "lesson": completed}
    active["segment_index"] = next_seg
    active["updated_at"] = now_iso()
    state["last_class_id"] = class_id
    state["updated_at"] = now_iso()
    return {"completed": False, "segment_index": next_seg}


def build_packet(curriculum, state, class_id):
    course = curriculum["classes"][class_id]
    cstate = class_state(state, class_id)
    lesson, idx, seg, is_active = active_or_next(course, cstate)
    segment_name = ""
    if lesson:
        segments = lesson.get("segments", [])
        if segments:
            segment_name = segments[min(seg, len(segments) - 1)]
    source_status = [chapter_status(src) for src in course.get("source_chapters", [])]
    examples = []
    for key in course.get("primary_concepts", []) + course.get("secondary_concepts", []):
        examples.extend(curriculum.get("concept_index", {}).get(key, []))
    examples = list(dict.fromkeys(examples))
    return {
        "class_id": class_id,
        "class_name": course.get("name", ""),
        "professor": course.get("professor", ""),
        "voice": course.get("voice", ""),
        "room": course.get("room", ""),
        "lesson_index": idx,
        "lesson_id": lesson.get("id", "") if lesson else "",
        "lesson_title": lesson.get("title", "") if lesson else "",
        "lesson_teaches": lesson.get("teaches", "") if lesson else "",
        "segment_index": seg,
        "segment": segment_name,
        "active": is_active,
        "classmates": course.get("classmates", []),
        "lesson_style": course.get("lesson_style", ""),
        "source_chapters": source_status,
        "cross_references": examples,
        "enchantments": lesson.get("enchantments", course.get("enchantments", [])) if lesson else course.get("enchantments", []),
        "practice_shapes": lesson.get("practice_shapes", []) if lesson else [],
        "completed_lessons": cstate.get("completed_lessons", []),
        "policy": curriculum.get("policy", {})
    }


def render_text(packet):
    available = [s["id"] for s in packet["source_chapters"] if s["available"]]
    missing = [s["id"] for s in packet["source_chapters"] if not s["available"]]
    lines = [
        "CLASS LECTURE DIRECTIVE",
        f"CLASS: {packet['class_name']}",
        f"PROFESSOR: {packet['professor']} [{packet['voice']}]",
        f"ROOM: {packet['room']}",
        f"LESSON: {packet['lesson_title']} ({packet['lesson_id']})",
        f"SEGMENT: {packet['segment_index'] + 1} - {packet['segment']}",
        f"ACTIVE_ATTENDANCE: {'yes' if packet['active'] else 'no - run --attend before treating this as attended'}",
        f"TEACHES: {packet['lesson_teaches']}",
        f"STYLE: {packet['lesson_style']}",
        f"CLASSMATES: {', '.join(packet['classmates'])}",
        f"SOURCES_AVAILABLE: {', '.join(available) if available else 'none yet'}",
        f"SOURCES_MISSING_BUT_MAPPED: {', '.join(missing) if missing else 'none'}",
    ]
    if packet["enchantments"]:
        lines.append(f"ENCHANTMENTS_TAUGHT: {', '.join(packet['enchantments'])}")
    if packet["practice_shapes"]:
        lines.append(f"PRACTICE_SHAPES: {', '.join(packet['practice_shapes'])}")
    lines.extend([
        "",
        "AUDIO_FIRST_SCENE_RULES:",
        "- Write this as a listenable classroom scene, not a summary.",
        "- Render only this segment. Do not summarize the full class, the whole lesson, future segments, or source chapters.",
        "- Make the professor actually teach one concrete idea in dialogue or close narration; do not merely report that they taught it.",
        "- Let the class breathe for 2-4 minutes of audio: several short teaching beats, not a compressed period recap.",
        "- Use explicit voice-tag blocks before Telegram/TTS delivery.",
        "- Include professor teaching, one room detail, and at least one classmate presence.",
        "- Include at least one named classmate reaction, question, mistake, joke, or interruption.",
        "- Keep this segment self-contained, with a clear invitation to continue.",
        "- Forbidden compression phrases: class passes, lecture covers, after class, by the end of class, you spend the period, the lesson wraps.",
        "- Do not mark the lesson complete unless class-lecture.py --advance completes it.",
        "- Do not mark any practice or Enchantment complete without real player action.",
        "",
        "CHOICE CONTRACT:",
        "1. [LIFE] Stay in ordinary class texture: seatmate, room detail, or a grounded classroom question.",
        "2. [ARC] Continue the lesson or ask the professor to demonstrate the next concept.",
        "3. [SURPRISE] Let a classmate, object, book, or interruption bend the class sideways.",
    ])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Prepare and track multi-turn class lectures.")
    parser.add_argument("player", nargs="?", default="bj")
    parser.add_argument("--class-id", choices=None)
    parser.add_argument("--attend", action="store_true", help="Start or resume attendance for the current lesson.")
    parser.add_argument("--advance", action="store_true", help="Advance the active lesson by one segment; completes at the end.")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    curriculum = load_json(CONFIG, {})
    if not curriculum.get("classes"):
        print("No class curriculum found.", file=sys.stderr)
        return 1

    state = load_json(state_path(args.player), {"player": args.player, "classes": {}, "created_at": now_iso()})
    class_id = (
        args.class_id
        or current_class_id(include_next=False)
        or active_class_id(state)
        or current_class_id(include_next=True)
        or state.get("last_class_id")
        or "art-of-the-glint"
    )
    if class_id not in curriculum["classes"]:
        print(f"Unknown class id: {class_id}", file=sys.stderr)
        return 2

    cstate = class_state(state, class_id)

    result = None
    if args.attend:
        result = begin_attendance(state, class_id, curriculum["classes"][class_id], cstate)
        save_json(state_path(args.player), state)
    if args.advance:
        result = advance_active(state, class_id, curriculum["classes"][class_id], cstate)
        save_json(state_path(args.player), state)

    packet = build_packet(curriculum, state, class_id)
    if result is not None:
        packet["state_change"] = result

    if args.json:
        print(json.dumps(packet, indent=2, ensure_ascii=False))
    else:
        print(render_text(packet))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

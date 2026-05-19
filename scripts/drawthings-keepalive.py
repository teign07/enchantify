#!/usr/bin/env python3
"""Keep Draw Things warm for local Enchantify image generation.

The job is intentionally simple:
- check the local Draw Things API
- open the macOS app if the API is unavailable
- optionally generate a small random Enchantify keepalive image

It does not delete images, touch models, or require external API calls.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import random
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib import error, request


BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "logs" / "drawthings-keepalive"
SCRIPTS = BASE / "scripts"
sys.path.insert(0, str(SCRIPTS))
import cron_steward  # type: ignore
import drawthings_scene  # type: ignore

_visuals_spec = importlib.util.spec_from_file_location("character_visuals", SCRIPTS / "character-visuals.py")
if not _visuals_spec or not _visuals_spec.loader:
    raise RuntimeError("Could not load scripts/character-visuals.py")
character_visuals = importlib.util.module_from_spec(_visuals_spec)
_visuals_spec.loader.exec_module(character_visuals)

API_URL = "http://127.0.0.1:8080"
TXT2IMG_URL = f"{API_URL}/sdapi/v1/txt2img"
APP_NAME = "Draw Things"
TELEGRAM_TARGET = "8729557865"
TELEGRAM_CHANNEL = "telegram"
TELEGRAM_ACCOUNT = "enchantify"

REGISTER_MD = BASE / "lore" / "world-register.md"

SCENE_SUBJECTS = [
    (
        "academy",
        "The Great Hall between classes, students and marginalia drifting around long tables, one foreground student half-turned toward a rumor",
        8,
    ),
    (
        "library",
        "The Academy library's living stacks, catalog drawers open, a ladder, ink labels, and one distant student discovering a note",
        8,
    ),
    (
        "classroom",
        "A Wonder Compass classroom desk with notebooks, a compass card, teacup rings, and a student's hands arranging one small spell-object",
        5,
    ),
    (
        "outer-stacks",
        "An Outer Stacks doorway folded into a manuscript margin, map labels, brass coordinates, and a single small figure at the threshold",
        4,
    ),
    (
        "bleed",
        "The Bleed newsroom table, clippings, gossip slips, ink stamps, and a half-finished column waiting under a green lamp",
        4,
    ),
]

SCENE_CAPTIONS = {
    "academy": (
        "The Great Hall",
        "A live Academy atmosphere plate: daily life, rumor-weather, and student motion between classes.",
    ),
    "library": (
        "The Living Stacks",
        "A library plate: catalog drawers, book-jumping pressure, and whatever the shelves are trying not to say aloud.",
    ),
    "classroom": (
        "Wonder Compass Desk",
        "A classroom study: practice objects, notes, and the small machinery of attention before it becomes magic.",
    ),
    "outer-stacks": (
        "Outer Stacks Threshold",
        "A threshold plate: one of the Labyrinth's fold-out places where real-world attention starts becoming architecture.",
    ),
    "bleed": (
        "The Bleed Desk",
        "A newsroom plate: clippings, columns, gossip slips, and the Academy trying to interpret itself in public.",
    ),
}

STYLE = (
    "illustrated in sparse pen-and-ink linework with loose watercolor washes on textured aged parchment, "
    "visible paper grain, soft ink bleed, watercolor blooms, layered manuscript-page composition, "
    "lush handwritten marginalia, lush watercolor washes, visible library stamps, wax seals, labels, tabs, arrows, "
    "annotations, archival overlays, selective pops of color in magical details, airy literary sketch-like unfinished field journal page, "
    "page furniture abundant and integral rather than timid decoration"
)


def parse_register_entities() -> dict[str, dict[str, object]]:
    text = REGISTER_MD.read_text(encoding="utf-8", errors="ignore") if REGISTER_MD.exists() else ""
    rows: dict[str, dict[str, object]] = {}
    for line in text.splitlines():
        if not line.startswith("|") or "---" in line:
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) < 4 or parts[0].lower() in {"entity", "talisman", "name"}:
            continue
        belief_m = re.search(r"\d+", parts[2])
        if not belief_m:
            continue
        rows[parts[0]] = {
            "type": parts[1],
            "belief": int(belief_m.group(0)),
            "notes": parts[3],
            "threads": re.findall(r"\[thread:([^\]]+)\]", parts[3], flags=re.IGNORECASE),
        }
    for m in re.finditer(r"^-\s+(.+?)\s+\(([^,]+),\s*Belief\s*(\d+)\)\s*(?:—\s*(.*))?$", text, re.MULTILINE):
        rows[m.group(1).strip()] = {
            "type": m.group(2).strip(),
            "belief": int(m.group(3)),
            "notes": (m.group(4) or "").strip(),
            "threads": re.findall(r"\[thread:([^\]]+)\]", m.group(4) or "", flags=re.IGNORECASE),
        }
    return rows


def active_thread_ids(rows: dict[str, dict[str, object]]) -> set[str]:
    return {
        thread
        for row in rows.values()
        if str(row.get("type", "")).lower() in {"thread", "arc"}
        for thread in (row.get("threads") or [])
    }


def weight_for_character(name: str, entry: dict[str, object], rows: dict[str, dict[str, object]], active_threads: set[str]) -> int:
    row = rows.get(name) or character_visuals.register_for(name, rows) or {}
    belief = int(row.get("belief", entry.get("belief_at_canon", 0)) or 0)
    entity_type = str(row.get("type", "NPC")).lower()
    if entity_type and entity_type != "npc":
        return 0
    if belief < 5 and int(entry.get("belief_at_canon", 0) or 0) < 5:
        return 0
    threads = set(row.get("threads") or [])
    weight = max(1, min(80, belief))
    if threads & active_threads:
        weight += 12
    if str(entry.get("source", "")).startswith("auto-core"):
        weight += 10
    if name in {"Zara Finch", "Headmistress Seraphina Thorne", "Headmistress Thorne", "Wicker Eddies"}:
        weight += 10
    return weight


def character_subjects() -> list[tuple[str, str, int]]:
    try:
        character_visuals.sync(dry_run=False)
    except Exception:
        pass
    visuals = character_visuals.load_visuals()
    characters = visuals.get("characters") or {}
    if not isinstance(characters, dict):
        return []
    rows = parse_register_entities()
    active_threads = active_thread_ids(rows)
    subjects: list[tuple[str, str, int]] = []
    for name, raw_entry in characters.items():
        if not isinstance(raw_entry, dict):
            continue
        weight = weight_for_character(name, raw_entry, rows, active_threads)
        if weight <= 0:
            continue
        fragment = character_visuals.prompt_fragment(name)
        notes = str((rows.get(name) or {}).get("notes", ""))
        thread_hint = f" Current narrative gravity: {notes}" if notes else ""
        subject = (
            f"{name} as the main foreground figure, half-length portrait in an active Academy moment. "
            f"{fragment}{thread_hint}"
        )
        subjects.append(("character", subject, weight))
    return subjects


def choose_keepalive_subject(*, character_ratio: float = 0.78) -> tuple[str, str]:
    char_subjects = character_subjects()
    if char_subjects and random.random() < character_ratio:
        kind, subject, _weight = random.choices(char_subjects, weights=[item[2] for item in char_subjects], k=1)[0]
        return kind, subject
    kind, subject, _weight = random.choices(SCENE_SUBJECTS, weights=[item[2] for item in SCENE_SUBJECTS], k=1)[0]
    return kind, subject


def subject_label(selection: dict[str, str]) -> str:
    kind = selection.get("kind", "")
    subject = selection.get("subject", "")
    if kind == "character":
        return subject.split(" as the main foreground figure", 1)[0].strip() or "Academy character"
    return SCENE_CAPTIONS.get(kind, (kind.replace("-", " ").title() or "Academy plate", ""))[0]


def deterministic_caption(selection: dict[str, str]) -> str:
    """Build a Telegram caption from selection metadata. No LLM call."""
    kind = selection.get("kind", "")
    subject = selection.get("subject", "")
    rows = parse_register_entities()
    if kind == "character":
        name = subject_label(selection)
        row = rows.get(name) or character_visuals.register_for(name, rows) or {}
        belief = row.get("belief")
        entity_type = str(row.get("type") or "NPC")
        notes = re.sub(r"\[thread:[^\]]+\]", "", str(row.get("notes") or "")).strip()
        notes = re.sub(r"\s+", " ", notes)
        role = notes[:170].rstrip(" .") if notes else "selected from the character visual canon by narrative weight."
        belief_text = f" · Belief {belief}" if belief not in (None, "") else ""
        return (
            f"Hourly Field-Journal Plate: {name}\n"
            f"{entity_type}{belief_text}\n"
            f"{role}"
        )
    title, detail = SCENE_CAPTIONS.get(
        kind,
        (subject_label(selection), "A non-character Academy atmosphere plate from the keepalive rotation."),
    )
    return f"Hourly Field-Journal Plate: {title}\n{detail}"


def api_alive(timeout: float = 2.0) -> tuple[bool, str]:
    try:
        req = request.Request(f"{API_URL}/sdapi/v1/options", headers={"Accept": "application/json"})
        with request.urlopen(req, timeout=timeout) as response:
            if response.status < 400:
                return True, f"api alive: HTTP {response.status}"
    except error.URLError as exc:
        return False, f"api unavailable: {exc}"
    except Exception as exc:
        return False, f"api check failed: {exc}"
    return False, "api returned no usable status"


def open_app(*, dry_run: bool = False) -> tuple[bool, str]:
    if dry_run:
        return True, f"dry-run would open {APP_NAME}"
    proc = subprocess.run(["open", "-a", APP_NAME], capture_output=True, text=True, timeout=20)
    if proc.returncode == 0:
        return True, f"opened {APP_NAME}"
    return False, (proc.stderr or proc.stdout or f"failed to open {APP_NAME}").strip()


def wait_for_api(seconds: int) -> tuple[bool, str]:
    deadline = time.time() + seconds
    last = ""
    while time.time() < deadline:
        ok, detail = api_alive(timeout=2.5)
        last = detail
        if ok:
            return True, detail
        time.sleep(5)
    return False, last or "api did not become ready"


def keepalive_prompt() -> tuple[str, str, str]:
    kind, subject = choose_keepalive_subject()
    if kind == "character":
        focus = (
            "Keep the character dominant: face, posture, hands, recurring signature object, and one meaningful action. "
            "Background should support the person, never become the subject."
        )
    else:
        focus = (
            "Keep the scene airy and lived-in, with one small human-scale focal point and abundant manuscript page furniture."
        )
    prompt = f"{subject}, {STYLE}. {focus} No UI, no readable text, no room-first composition when a character is present."
    return prompt, kind, subject


def generate_keepalive_image(*, dry_run: bool = False, width: int = 768, height: int = 512, steps: int = 4) -> tuple[bool, str, Optional[Path], dict[str, str]]:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output = OUT_DIR / f"keepalive-{stamp}.png"
    prompt, kind, subject = keepalive_prompt()
    selection = {"kind": kind, "subject": subject, "prompt": prompt}
    if dry_run:
        return True, f"dry-run would generate {output}: {prompt[:240]}", output, selection
    ok, detail = drawthings_scene.generate(
        prompt,
        output,
        width=width,
        height=height,
        steps=steps,
        cfg_scale=1.0,
        timeout_seconds=240,
    )
    if ok:
        latest = OUT_DIR / "latest.png"
        try:
            latest.unlink()
        except FileNotFoundError:
            pass
        latest.symlink_to(output.name)
        return True, str(output), output, selection
    return False, detail, None, selection


def send_telegram_image(
    image_path: Path,
    *,
    caption: str,
    dry_run: bool = False,
    silent: bool = False,
    force_document: bool = False,
) -> tuple[bool, str]:
    if dry_run:
        return True, f"dry-run would send Telegram media {image_path}"
    if not image_path.exists():
        return False, f"Telegram image missing: {image_path}"
    args = [
        "openclaw", "message", "send",
        "--target", TELEGRAM_TARGET,
        "--channel", TELEGRAM_CHANNEL,
        "--account", TELEGRAM_ACCOUNT,
        "--media", str(image_path),
    ]
    if caption:
        args += ["--message", caption[:1000]]
    if silent:
        args.append("--silent")
    if force_document:
        args.append("--force-document")
    try:
        proc = subprocess.run(args, cwd=BASE, capture_output=True, text=True, timeout=120)
    except Exception as exc:
        return False, f"Telegram send failed: {exc}"
    if proc.returncode == 0:
        return True, f"Telegram image sent: {image_path.name}"
    detail = (proc.stderr or proc.stdout or "unknown OpenClaw send failure").strip()
    return False, f"Telegram send failed: {detail[:300]}"


def cleanup_old_images(keep: int = 24) -> None:
    if not OUT_DIR.exists():
        return
    images = sorted(
        [path for path in OUT_DIR.glob("keepalive-*.png") if path.is_file()],
        key=lambda p: p.stat().st_mtime,
    )
    for path in images[:-keep]:
        try:
            path.unlink()
        except OSError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Keep Draw Things open and optionally generate a small keepalive image.")
    parser.add_argument("--generate", action="store_true", help="Generate a small random Enchantify keepalive image after API is alive.")
    parser.add_argument("--telegram", action="store_true", help="Send generated keepalive image to the Enchantify Telegram channel. No LLM is used.")
    parser.add_argument("--telegram-caption", default="", help="Override the deterministic image caption.")
    parser.add_argument("--telegram-silent", action="store_true", help="Send Telegram image silently when supported.")
    parser.add_argument("--force-document", action="store_true", help="Send image as a Telegram document to avoid compression.")
    parser.add_argument("--open-if-needed", action="store_true", default=True)
    parser.add_argument("--wait-seconds", type=int, default=90)
    parser.add_argument("--keep-images", type=int, default=24)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with cron_steward.run("drawthings-keepalive", dry_run=args.dry_run, generate=args.generate) as ctx:
        events: list[str] = []
        alive, detail = api_alive()
        events.append(detail)
        opened = False
        generated = False
        telegram_sent = False
        image_path: Optional[Path] = None
        selection: dict[str, str] = {}
        telegram_caption = ""

        if not alive and args.open_if_needed:
            ok, open_detail = open_app(dry_run=args.dry_run)
            opened = ok
            events.append(open_detail)
            if ok and not args.dry_run:
                alive, wait_detail = wait_for_api(args.wait_seconds)
                events.append(wait_detail)

        if alive and args.generate:
            ok, image_detail, image_path, selection = generate_keepalive_image(dry_run=args.dry_run)
            generated = ok
            events.append(image_detail)
            if ok and args.telegram and image_path:
                telegram_caption = args.telegram_caption or deterministic_caption(selection)
                sent, send_detail = send_telegram_image(
                    image_path,
                    caption=telegram_caption,
                    dry_run=args.dry_run,
                    silent=args.telegram_silent,
                    force_document=args.force_document,
                )
                telegram_sent = sent
                events.append(send_detail)
        elif args.telegram:
            events.append("Telegram image not sent: --generate is required")

        if not args.dry_run:
            cleanup_old_images(keep=args.keep_images)

        ctx["api_alive"] = alive
        ctx["opened"] = opened
        ctx["generated"] = generated
        ctx["telegram_sent"] = telegram_sent
        report = {
            "at": datetime.now().isoformat(timespec="seconds"),
            "api_alive": alive,
            "opened": opened,
            "generated": generated,
            "telegram_sent": telegram_sent,
            "image": str(image_path) if image_path else None,
            "telegram_caption": telegram_caption,
            "selection": selection,
            "events": events,
        }
        (OUT_DIR / "last-run.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print("; ".join(events))
        return 0 if alive or opened or args.dry_run else 1


if __name__ == "__main__":
    raise SystemExit(main())

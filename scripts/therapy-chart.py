#!/usr/bin/env python3
"""Structured updates for Dr. Selene Inkrest's therapy chart.

This is a private support-character artifact, not a medical record. It keeps
therapy-adjacent notes structured so the Labyrinth can remember patterns
without freehand-editing markdown.
"""

from __future__ import annotations

import argparse
import re
import shutil
from datetime import datetime
from pathlib import Path


BASE = Path(__file__).parent.parent
DEFAULT_PLAYER = "bj"


TEMPLATE = """# Dr. Selene Inkrest Chart — BJ

This chart is the private working context for Dr. Selene Inkrest, Academy Narrative Therapist and Keeper of Difficult Pages. It is for patterns, preferred stories, daydreams, emotional weather, grounding practices, therapy questions, and session notes. It is not a diagnosis file and must not pretend to replace professional care.

## Inkrest Rules

- Act like a real therapist in tone, pacing, confidentiality, curiosity, and continuity.
- Use narrative therapy as the spine: externalize problems, identify dominant stories, find unique outcomes, thicken preferred identity, and connect insight to one next action.
- Use depth psychology as atmosphere: symbols, shadow, recurring images, daydreams, inner figures, active imagination, and meaning-making.
- Use ACT, CBT, parts work, and somatic grounding only when they help the next hour become more livable.
- Read `players/bj-vellum-chart.md`, `scripts/fuel-log.txt`, and `HEARTBEAT.md` when relevant. Low fuel, poor sleep, pain, or recovery debt must be considered before heavy interpretation.
- Dreams are optional. Daydreams, repeated fantasies, fictional scenes, song fragments, moods, avoidance loops, and images from play are valid therapeutic material.
- Do not diagnose, replace therapy, force catharsis, push trauma excavation, claim certainty about symbols, or treat distress as a puzzle to solve.
- If BJ shows crisis-level distress or possible self-harm risk, pause game mechanics and encourage immediate real-world support.

## Current Frame

- Preferred story: unknown
- Dominant problem-story: unknown
- Values BJ wants to live toward: unknown
- Known stabilizers: unknown
- Known destabilizers: unknown
- Therapy style preferences: narrative therapy, depth psychology, practical grounding, no generic wellness voice

## Care Context

- Vellum chart: read `players/bj-vellum-chart.md` when needed
- Recent fuel: read `scripts/fuel-log.txt` when needed
- Heartbeat: read `HEARTBEAT.md` when needed
- Medication / sleep caveat: meds may suppress dream recall; do not over-focus on dreams
- Real therapist / clinician context: unknown

## Office Hours

| Day | Time | Format | Purpose |
|---|---|---|---|
| Tuesday | 9:30 PM | Scheduled visit | Difficult Page / reauthoring check-in |
| Thursday | 9:30 PM | Scheduled visit | Difficult Page / reauthoring check-in |

## Recent Check-Ins

| Date | Mood / Weather | Problem Externalized | Preferred Story | Next Action |
|---|---|---|---|---|
| none logged | unknown | unknown | unknown | unknown |

## Daydreams / Images

| Date | Image | Feeling | Possible Meaning | Action |
|---|---|---|---|---|
| none logged | unknown | unknown | unknown | unknown |

## Reauthoring Notes

| Date | Old Story | Unique Outcome | Preferred Identity | Witness / Proof |
|---|---|---|---|---|
| none logged | unknown | unknown | unknown | unknown |

## Grounding Practices

- Orient to five visible objects, then name the room and date.
- Eat or drink something gentle before interpreting despair if fuel is low.
- Place one hand on a stable surface and take five slower breaths.
- Ask: what is the smallest action that supports the preferred story in the next hour?

## Questions for Real Therapy

- None yet.

## Inkrest Output Format

1. Consent: ask whether BJ wants reflection, grounding, reauthoring, or quiet company.
2. Externalize: name the problem as separate from BJ.
3. Context check: consider sleep, food, health, medication, and immediate safety.
4. Pattern: identify the dominant story or recurring image without claiming certainty.
5. Unique outcome: find one exception, resistance, value, or preferred self already present.
6. Reauthor: offer one preferred-story sentence.
7. Next hour: choose one small embodied action.
8. Artifact: save a brief Difficult Page, reauthoring note, daydream note, or question.
"""


def chart_path(args: argparse.Namespace) -> Path:
    if args.chart:
        return Path(args.chart).expanduser().resolve()
    player = re.sub(r"[^a-zA-Z0-9_-]", "", args.player or DEFAULT_PLAYER) or DEFAULT_PLAYER
    return BASE / "players" / f"{player}-therapy-chart.md"


def clean(value: object, default: str = "unknown") -> str:
    text = str(value if value is not None and value != "" else default)
    text = re.sub(r"\s+", " ", text.replace("|", "/")).strip()
    return text or default


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def load(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else TEMPLATE


def save(path: Path, text: str, dry_run: bool = False) -> None:
    if dry_run:
        print(f"[dry-run] Would update {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup_dir = Path("/tmp/enchantify-therapy-backups")
        backup_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup_dir / f"{path.name}.bak")
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    tmp.rename(path)


def section_bounds(text: str, heading: str) -> tuple[int, int]:
    m = re.search(rf"^##\s+{re.escape(heading)}\s*$", text, re.MULTILINE)
    if not m:
        raise ValueError(f"Missing section: {heading}")
    next_m = re.search(r"^##\s+", text[m.end():], re.MULTILINE)
    end = m.end() + next_m.start() if next_m else len(text)
    return m.start(), end


def section_text(text: str, heading: str) -> str:
    start, end = section_bounds(text, heading)
    block = text[start:end]
    return re.sub(rf"^##\s+{re.escape(heading)}\s*\n*", "", block).strip()


def replace_section(text: str, heading: str, body: str) -> str:
    start, end = section_bounds(text, heading)
    return text[:start] + f"## {heading}\n\n{body.rstrip()}\n\n" + text[end:].lstrip()


def update_bullet(text: str, heading: str, field: str, value: str) -> str:
    body = section_text(text, heading)
    field_clean = clean(field)
    line = f"- {field_clean}: {clean(value)}"
    pat = re.compile(rf"^-\s*{re.escape(field_clean)}\s*:\s*.*$", re.MULTILINE | re.IGNORECASE)
    body = pat.sub(line, body, count=1) if pat.search(body) else body.rstrip() + "\n" + line
    return replace_section(text, heading, body)


def append_table_row(text: str, heading: str, row: list[object], placeholders: tuple[str, ...]) -> str:
    body = section_text(text, heading)
    lines = body.splitlines()
    preface, header, rows = [], [], []
    in_table = False
    for line in lines:
        if line.strip().startswith("|"):
            in_table = True
            if len(header) < 2:
                header.append(line)
            else:
                rows.append(line)
        elif not in_table:
            preface.append(line)
    if len(header) < 2:
        raise ValueError(f"Section {heading} does not contain a markdown table")
    placeholder_lower = tuple(p.lower() for p in placeholders)
    rows = [r for r in rows if not any(p in r.lower() for p in placeholder_lower)]
    rendered = "| " + " | ".join(clean(cell, "") for cell in row) + " |"
    new_body = "\n".join(preface).rstrip()
    if new_body:
        new_body += "\n\n"
    new_body += "\n".join(header + rows + [rendered])
    return replace_section(text, heading, new_body)


def append_question(text: str, question: str) -> str:
    body = section_text(text, "Questions for Real Therapy")
    body = re.sub(r"(?m)^-\s*None yet\.\s*$", "", body).rstrip()
    body += "\n" + f"- {clean(question)}"
    return replace_section(text, "Questions for Real Therapy", body)


def summarize(text: str) -> str:
    pieces = ["INKREST CHART SUMMARY"]
    for heading in ("Current Frame", "Care Context", "Office Hours", "Recent Check-Ins", "Daydreams / Images", "Reauthoring Notes", "Questions for Real Therapy"):
        body = section_text(text, heading)
        lines = [ln for ln in body.splitlines() if ln.strip() and not ln.strip().startswith("|---")]
        pieces.append(f"\n## {heading}")
        pieces.extend(lines[:14])
    return "\n".join(pieces)


def main() -> int:
    parser = argparse.ArgumentParser(description="Update or inspect Dr. Inkrest's therapy chart")
    parser.add_argument("--player", default=DEFAULT_PLAYER)
    parser.add_argument("--chart", default=None, help="Override chart path, mainly for tests")
    parser.add_argument("--dry-run", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Create chart if missing")
    sub.add_parser("show", help="Print a compact summary")

    p = sub.add_parser("frame", help="Set a Current Frame bullet")
    p.add_argument("field")
    p.add_argument("value")

    p = sub.add_parser("care", help="Set a Care Context bullet")
    p.add_argument("field")
    p.add_argument("value")

    p = sub.add_parser("checkin", help="Append a therapy check-in")
    p.add_argument("--mood", default="unknown")
    p.add_argument("--problem", default="unknown")
    p.add_argument("--preferred", default="unknown")
    p.add_argument("--action", default="unknown")
    p.add_argument("--date", default=None)

    p = sub.add_parser("daydream", help="Append a daydream/image note")
    p.add_argument("image")
    p.add_argument("--feeling", default="unknown")
    p.add_argument("--meaning", default="unknown")
    p.add_argument("--action", default="unknown")
    p.add_argument("--date", default=None)

    p = sub.add_parser("reauthor", help="Append a reauthoring note")
    p.add_argument("--old-story", default="unknown")
    p.add_argument("--unique-outcome", default="unknown")
    p.add_argument("--preferred-identity", default="unknown")
    p.add_argument("--proof", default="unknown")
    p.add_argument("--date", default=None)

    p = sub.add_parser("question", help="Append a question for real therapy")
    p.add_argument("text")

    args = parser.parse_args()
    path = chart_path(args)
    text = load(path)

    if args.command == "init":
        save(path, text, args.dry_run)
        print(f"Inkrest chart ready: {path}")
        return 0
    if args.command == "show":
        print(summarize(text))
        return 0
    if args.command == "frame":
        text = update_bullet(text, "Current Frame", args.field, args.value)
    elif args.command == "care":
        text = update_bullet(text, "Care Context", args.field, args.value)
    elif args.command == "checkin":
        text = append_table_row(
            text,
            "Recent Check-Ins",
            [args.date or today(), args.mood, args.problem, args.preferred, args.action],
            placeholders=("none logged",),
        )
    elif args.command == "daydream":
        text = append_table_row(
            text,
            "Daydreams / Images",
            [args.date or today(), args.image, args.feeling, args.meaning, args.action],
            placeholders=("none logged",),
        )
    elif args.command == "reauthor":
        text = append_table_row(
            text,
            "Reauthoring Notes",
            [args.date or today(), args.old_story, args.unique_outcome, args.preferred_identity, args.proof],
            placeholders=("none logged",),
        )
    elif args.command == "question":
        text = append_question(text, args.text)
    else:
        raise AssertionError(args.command)

    save(path, text, args.dry_run)
    print(f"Inkrest chart updated: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

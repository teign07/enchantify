#!/usr/bin/env python3
"""Structured updates for Dr. Vellum's personal longevity chart.

This script owns markdown writes for players/[name]-vellum-chart.md so agents
do not have to freehand-edit medical/longevity tables.
"""

from __future__ import annotations

import argparse
import re
import shutil
from datetime import datetime
from pathlib import Path


BASE = Path(__file__).parent.parent
DEFAULT_PLAYER = "bj"


TEMPLATE = """# Dr. Vellum Chart — BJ

This chart is the private working context for Dr. Elowen Vellum, Academy Longevity Physician. It is a scaffold for future bloodwork, blood pressure, medication, supplement, food, sleep, movement, and recovery data. Unknown fields must remain unknown until BJ supplies them.

## Vellum Rules

- Give real, practical longevity guidance translated for BJ's daily life.
- Recommend supplements, exercises, food experiments, recovery practices, and doctor-prep questions when the evidence and available context support them.
- Label evidence strength when making a health recommendation: strong, moderate, early/promising, speculative, or not worth the cost/risk right now.
- For supplements, include: why BJ might consider it, possible benefit, risks/interactions, what labs or conditions matter, a conservative starting frame, how to know whether it helped, and a doctor/pharmacist question when relevant.
- For exercise, include: minimum-effective version, ordinary version, progression, stop/scale-down signals, and what the practice is meant to protect.
- Do not diagnose, prescribe, change prescription medication, interpret emergency symptoms, or pretend to replace a clinician.
- Do not invent lab values, blood pressure readings, medication lists, conditions, allergies, or supplement use.
- Prefer BJ-sized experiments over heroic protocols. Precision without shame.

## Current Knowns

- Age: unknown
- Height: unknown
- Weight: unknown
- Waist measurement: unknown
- Primary longevity goals: live longer, stay stronger, preserve cognition, have energy for wonder, travel, play, and creative work
- Current constraints: unknown
- Food preferences: unknown
- Budget constraints: unknown
- Biggest barriers: unknown

## Medical Context

- Diagnosed conditions: unknown
- Current medications: unknown
- Allergies / intolerances: unknown
- Family history: unknown
- Clinician notes: unknown
- Recent procedures / injuries: unknown

## Blood Pressure

Use home readings when available. Prefer repeated measurements over one dramatic number.

| Date | Time | Systolic | Diastolic | Pulse | Context |
|---|---:|---:|---:|---:|---|
| unknown | unknown | unknown | unknown | unknown | no readings logged yet |

## Latest Labs

Paste bloodwork here when available. Keep original units and reference ranges when possible.

| Marker | Value | Unit | Date | Reference Range | Notes |
|---|---:|---|---|---|---|
| A1C | unknown | % | unknown | unknown | |
| Fasting glucose | unknown | mg/dL | unknown | unknown | |
| Fasting insulin | unknown | uIU/mL | unknown | unknown | optional but useful |
| Total cholesterol | unknown | mg/dL | unknown | unknown | |
| LDL-C | unknown | mg/dL | unknown | unknown | |
| HDL-C | unknown | mg/dL | unknown | unknown | |
| Triglycerides | unknown | mg/dL | unknown | unknown | |
| ApoB | unknown | mg/dL | unknown | unknown | useful if available |
| Lp(a) | unknown | mg/dL or nmol/L | unknown | unknown | useful once in adulthood |
| hs-CRP | unknown | mg/L | unknown | unknown | |
| ALT | unknown | U/L | unknown | unknown | |
| AST | unknown | U/L | unknown | unknown | |
| Creatinine | unknown | mg/dL | unknown | unknown | |
| eGFR | unknown | mL/min/1.73m2 | unknown | unknown | important for supplement safety |
| Vitamin D | unknown | ng/mL | unknown | unknown | |
| B12 | unknown | pg/mL | unknown | unknown | |
| TSH | unknown | uIU/mL | unknown | unknown | |
| CBC | unknown | mixed | unknown | unknown | paste details if available |
| Ferritin / iron | unknown | mixed | unknown | unknown | |

## Current Supplements

| Supplement | Dose | Frequency | Start Date | Why | Notes / effects |
|---|---:|---|---|---|---|
| none logged | unknown | unknown | unknown | unknown | |

## Current Training

- Walking / steps pattern: read from HEARTBEAT when available
- Resistance training: unknown
- Cardio / Zone 2: unknown
- Mobility / balance: unknown
- Injuries or limits: unknown
- Current minimum-effective exercise: unknown

## Nutrition Defaults

- Protein pattern: read from food log when available
- Fiber pattern: read from food log when available
- Caffeine pattern: read from food log when available
- Alcohol pattern: read from food log when available
- Hydration pattern: unknown unless logged
- Reliable low-energy foods: unknown
- Foods BJ enjoys and wants protected: unknown

## Current Experiments

Each Vellum experiment should be small, measurable, and time-bounded.

| Experiment | Start | Review | Metric | Result |
|---|---|---|---|---|
| none active | unknown | unknown | unknown | unknown |

## Doctor / Pharmacist Questions

Use this section to collect questions Vellum wants BJ to bring to real clinicians.

- None yet.

## Vellum Output Format

When Vellum gives a substantial recommendation, she should prefer this structure:

1. Observation: what she noticed from BJ's actual data.
2. Interpretation: what it might mean, with uncertainty named.
3. Experiment: one small action for today or this week.
4. Evidence: strong, moderate, early/promising, speculative, or not worth the cost/risk right now.
5. Watch-outs: risks, interactions, scale-down signs, or missing context.
6. Question: one doctor/pharmacist question if the recommendation touches labs, medications, supplements, chronic conditions, or elevated risk.
7. Comfort clause: what remains pleasurable, human, and non-optimized.

## Update Instructions

When BJ provides new bloodwork, blood pressure, medication, supplement, symptom, diagnosis, training, or food preference data, update this chart first. Then Vellum may use it in The Bleed, letters, Story-Field Journal, active play, and support-character pages.
"""


def chart_path(args: argparse.Namespace) -> Path:
    if args.chart:
        return Path(args.chart).expanduser().resolve()
    player = re.sub(r"[^a-zA-Z0-9_-]", "", args.player or DEFAULT_PLAYER) or DEFAULT_PLAYER
    return BASE / "players" / f"{player}-vellum-chart.md"


def clean(value: object, default: str = "unknown") -> str:
    text = str(value if value is not None and value != "" else default)
    text = re.sub(r"\s+", " ", text.replace("|", "/")).strip()
    return text or default


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def now_time() -> str:
    return datetime.now().strftime("%H:%M")


def load(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return TEMPLATE


def save(path: Path, text: str, dry_run: bool = False) -> None:
    if dry_run:
        print(f"[dry-run] Would update {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup_dir = Path("/tmp/enchantify-vellum-backups")
        backup_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup_dir / f"{path.name}.bak")
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    tmp.rename(path)


def section_bounds(text: str, heading: str) -> tuple[int, int]:
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        raise ValueError(f"Missing section: {heading}")
    next_match = re.search(r"^##\s+", text[match.end():], re.MULTILINE)
    end = match.end() + next_match.start() if next_match else len(text)
    return match.start(), end


def replace_section(text: str, heading: str, body: str) -> str:
    start, end = section_bounds(text, heading)
    return text[:start] + f"## {heading}\n\n{body.rstrip()}\n\n" + text[end:].lstrip()


def section_text(text: str, heading: str) -> str:
    start, end = section_bounds(text, heading)
    block = text[start:end]
    return re.sub(rf"^##\s+{re.escape(heading)}\s*\n*", "", block).strip()


def update_bullet_section(text: str, heading: str, field: str, value: str) -> str:
    body = section_text(text, heading)
    field_clean = clean(field)
    value_clean = clean(value)
    line = f"- {field_clean}: {value_clean}"
    pattern = re.compile(rf"^-\s*{re.escape(field_clean)}\s*:\s*.*$", re.MULTILINE | re.IGNORECASE)
    if pattern.search(body):
        body = pattern.sub(line, body, count=1)
    else:
        body = body.rstrip() + "\n" + line
    return replace_section(text, heading, body)


def table_lines(body: str) -> tuple[list[str], list[str]]:
    lines = body.splitlines()
    header = []
    rows = []
    for line in lines:
        if line.strip().startswith("|"):
            if len(header) < 2:
                header.append(line)
            else:
                rows.append(line)
    return header, rows


def append_table_row(text: str, heading: str, row: list[str], placeholders: tuple[str, ...] = ()) -> str:
    body = section_text(text, heading)
    preface_lines = []
    for line in body.splitlines():
        if line.strip().startswith("|"):
            break
        preface_lines.append(line)
    header, rows = table_lines(body)
    if len(header) < 2:
        raise ValueError(f"Section {heading} does not contain a markdown table")
    placeholder_lower = tuple(p.lower() for p in placeholders)
    kept_rows = []
    for existing in rows:
        lowered = existing.lower()
        if any(p in lowered for p in placeholder_lower):
            continue
        kept_rows.append(existing)
    rendered = "| " + " | ".join(clean(cell, "") for cell in row) + " |"
    new_body = "\n".join(preface_lines).rstrip()
    if new_body:
        new_body += "\n\n"
    new_body += "\n".join(header + kept_rows + [rendered])
    return replace_section(text, heading, new_body)


def upsert_lab(text: str, marker: str, value: str, unit: str, date: str, reference: str, notes: str) -> str:
    body = section_text(text, "Latest Labs")
    lines = body.splitlines()
    row = f"| {clean(marker)} | {clean(value)} | {clean(unit, '')} | {clean(date)} | {clean(reference)} | {clean(notes, '')} |"
    pattern = re.compile(rf"^\|\s*{re.escape(clean(marker))}\s*\|.*$", re.IGNORECASE)
    replaced = False
    out = []
    for line in lines:
        if line.strip().startswith("|") and pattern.match(line):
            out.append(row)
            replaced = True
        else:
            out.append(line)
    if not replaced:
        out.append(row)
    return replace_section(text, "Latest Labs", "\n".join(out))


def summarize(text: str) -> str:
    pieces = ["VELLUM CHART SUMMARY"]
    for heading in ("Current Knowns", "Medical Context", "Blood Pressure", "Latest Labs", "Current Supplements", "Current Experiments", "Doctor / Pharmacist Questions"):
        body = section_text(text, heading)
        lines = [ln for ln in body.splitlines() if ln.strip() and not ln.strip().startswith("|---")]
        pieces.append(f"\n## {heading}")
        pieces.extend(lines[:12])
    return "\n".join(pieces)


def main() -> int:
    parser = argparse.ArgumentParser(description="Update or inspect Dr. Vellum's longevity chart")
    parser.add_argument("--player", default=DEFAULT_PLAYER)
    parser.add_argument("--chart", default=None, help="Override chart path, mainly for tests")
    parser.add_argument("--dry-run", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Create chart if missing")
    sub.add_parser("show", help="Print a compact summary")

    p = sub.add_parser("known", help="Set a Current Knowns bullet")
    p.add_argument("field")
    p.add_argument("value")

    p = sub.add_parser("medical", help="Set a Medical Context bullet")
    p.add_argument("field")
    p.add_argument("value")

    p = sub.add_parser("bp", help="Append a blood pressure reading")
    p.add_argument("systolic", type=int)
    p.add_argument("diastolic", type=int)
    p.add_argument("--pulse", default="unknown")
    p.add_argument("--context", default="")
    p.add_argument("--date", default=None)
    p.add_argument("--time", default=None)

    p = sub.add_parser("lab", help="Upsert a lab marker")
    p.add_argument("marker")
    p.add_argument("value")
    p.add_argument("--unit", default="")
    p.add_argument("--date", default=None)
    p.add_argument("--range", dest="reference", default="unknown")
    p.add_argument("--notes", default="")

    p = sub.add_parser("supplement", help="Append a supplement")
    p.add_argument("name")
    p.add_argument("--dose", default="unknown")
    p.add_argument("--frequency", default="unknown")
    p.add_argument("--start", default=None)
    p.add_argument("--why", default="unknown")
    p.add_argument("--notes", default="")

    p = sub.add_parser("experiment", help="Append a Vellum experiment")
    p.add_argument("name")
    p.add_argument("--start", default=None)
    p.add_argument("--review", default="unknown")
    p.add_argument("--metric", default="unknown")
    p.add_argument("--result", default="pending")

    p = sub.add_parser("question", help="Append a doctor/pharmacist question")
    p.add_argument("text")

    args = parser.parse_args()
    path = chart_path(args)
    text = load(path)

    if args.command == "init":
        save(path, text, args.dry_run)
        print(f"Vellum chart ready: {path}")
        return 0
    if args.command == "show":
        print(summarize(text))
        return 0
    if args.command == "known":
        text = update_bullet_section(text, "Current Knowns", args.field, args.value)
    elif args.command == "medical":
        text = update_bullet_section(text, "Medical Context", args.field, args.value)
    elif args.command == "bp":
        text = append_table_row(
            text,
            "Blood Pressure",
            [args.date or today(), args.time or now_time(), args.systolic, args.diastolic, args.pulse, args.context],
            placeholders=("no readings logged yet",),
        )
    elif args.command == "lab":
        text = upsert_lab(text, args.marker, args.value, args.unit, args.date or today(), args.reference, args.notes)
    elif args.command == "supplement":
        text = append_table_row(
            text,
            "Current Supplements",
            [args.name, args.dose, args.frequency, args.start or today(), args.why, args.notes],
            placeholders=("none logged",),
        )
    elif args.command == "experiment":
        text = append_table_row(
            text,
            "Current Experiments",
            [args.name, args.start or today(), args.review, args.metric, args.result],
            placeholders=("none active",),
        )
    elif args.command == "question":
        body = section_text(text, "Doctor / Pharmacist Questions")
        body = re.sub(r"(?m)^-\s*None yet\.\s*$", "", body).rstrip()
        body += "\n" + f"- {clean(args.text)}"
        text = replace_section(text, "Doctor / Pharmacist Questions", body)
    else:
        raise AssertionError(args.command)

    save(path, text, args.dry_run)
    print(f"Vellum chart updated: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

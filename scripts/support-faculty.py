#!/usr/bin/env python3
"""Daily support loop for Dr. Vellum and Dr. Inkrest.

This is deliberately small and dependable. It gives the support characters
memory, check-ins, experiments, and independent briefs without routing through
ordinary NPC research.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent.parent
PLAYERS = BASE / "players"
LOG_DIR = BASE / "logs" / "support-faculty"
MEMORY_DIR = BASE / "memory" / "support-faculty"
HEARTBEAT = BASE / "HEARTBEAT.md"
VELLUM_CHART = PLAYERS / "bj-vellum-chart.md"
INKREST_CHART = PLAYERS / "bj-therapy-chart.md"
INKREST_LOG = PLAYERS / "bj-inkrest-log.jsonl"
VELLUM_LOG = PLAYERS / "bj-vellum-log.jsonl"
LEDGER_LOG = PLAYERS / "bj-ledger-log.jsonl"
SUPPORT_MEMORY = PLAYERS / "bj-support-memory.json"
INKREST_PENDING = PLAYERS / "bj-inkrest-pending.json"
DEFAULT_TARGET = "8729557865"
DEFAULT_CHANNEL = "telegram"
DEFAULT_ACCOUNT = "enchantify"

sys.path.insert(0, str(BASE / "scripts"))
import cron_steward  # type: ignore


INKREST_WORDS = {
    "good", "okay", "ok", "fine", "tired", "anxious", "sad", "angry", "flat",
    "foggy", "hopeful", "restless", "overwhelmed", "stressed", "calm", "happy",
    "lonely", "wired", "sore", "scared", "present", "numb", "peaceful", "low",
}

EXPLICIT_INKREST_PATTERNS = [
    r"^\s*log\s+(?:this\s+)?(?:for\s+)?dr\.?\s+inkrest\s*[:,-]\s*(.+)$",
    r"^\s*log\s+(?:this\s+)?(?:for\s+)?inkrest\s*[:,-]\s*(.+)$",
    r"^\s*dr\.?\s+inkrest\s*[:,-]\s*(.+)$",
    r"^\s*inkrest\s*[:,-]\s*(.+)$",
    r"^\s*log\s+(?:my\s+)?mood\s*[:,-]\s*(.+)$",
    r"^\s*mood\s*[:,-]\s*(.+)$",
]

VELLUM_RESEARCH_TOPICS = [
    ("protein floor", "protein adequacy, appetite stability, muscle preservation, and BJ-sized meal defaults"),
    ("resistance stimulus", "minimum-effective resistance training for longevity, strength, glucose handling, and adventure capacity"),
    ("sleep regularity", "sleep timing, medications, caffeine timing, and recovery debt"),
    ("blood pressure readiness", "home BP measurement habits, sodium/potassium context, stress, and clinician questions"),
    ("creatine shelf", "creatine evidence, kidney-function cautions, strength/cognition claims, and conservative trial design"),
    ("fiber and microbiome", "fiber adequacy, practical food additions, gut health evidence, and low-friction grocery choices"),
]

INKREST_RESEARCH_TOPICS = [
    ("one-word weather", "mood tracking, affect labeling, pattern detection, and low-friction emotional awareness"),
    ("hyperfocus closure", "hyperfocus, recovery rituals, launch resistance, and stopping without losing the thread"),
    ("narrative identity", "narrative therapy, preferred identity, unique outcomes, and proof the story is changing"),
    ("rumination loops", "rumination, default mode network, grounding, ACT defusion, and next-hour action"),
    ("daydream material", "daydreams, recurring images, active imagination, and practical meaning without over-interpretation"),
    ("medication and dreams", "sleep architecture, dream recall caveats, emotional interpretation, and body-first context checks"),
]


def now() -> datetime:
    return datetime.now()


def today() -> str:
    return now().strftime("%Y-%m-%d")


def ensure_dirs() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def read(path: Path, limit: int | None = None) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[:limit] if limit else text


def clean(value: Any, limit: int = 500) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit].rstrip() + ("..." if len(text) > limit else "")


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    row.setdefault("timestamp", now().isoformat(timespec="seconds"))
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def read_jsonl(path: Path, days: int = 14) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    cutoff = now() - timedelta(days=days)
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
            ts = datetime.fromisoformat(str(row.get("timestamp", "")))
            if ts.tzinfo is not None:
                ts = ts.replace(tzinfo=None)
        except Exception:
            continue
        if ts >= cutoff:
            out.append(row)
    return out


def send_telegram(message: str, *, dry_run: bool = False, silent: bool = False) -> bool:
    if dry_run:
        print(message)
        return True
    args = [
        "openclaw", "message", "send",
        "--target", DEFAULT_TARGET,
        "--channel", DEFAULT_CHANNEL,
        "--account", DEFAULT_ACCOUNT,
        "--message", message,
    ]
    if silent:
        # Older OpenClaw may ignore this; keep delivery working if unsupported.
        pass
    proc = subprocess.run(args, cwd=BASE, capture_output=True, text=True, timeout=90)
    if proc.returncode != 0:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        (LOG_DIR / "send-errors.log").open("a", encoding="utf-8").write(
            f"\n[{now().isoformat(timespec='seconds')}]\n{proc.stderr or proc.stdout}\n"
        )
        return False
    return True


def heartbeat_line(label: str) -> str:
    text = read(HEARTBEAT)
    m = re.search(rf"- \*\*{re.escape(label)}:\*\*\s*(.+)", text)
    return clean(m.group(1), 300) if m else ""


def heartbeat_field(label: str) -> str:
    text = read(HEARTBEAT)
    m = re.search(rf"\*\*{re.escape(label)}:\*\*\s*([^|\n]+)", text)
    return clean(m.group(1), 180) if m else ""


def steps_value() -> int | None:
    text = read(HEARTBEAT)
    m = re.search(r"Steps:\s*([\d,]+)", text)
    if not m:
        return None
    return int(m.group(1).replace(",", ""))


def latest_food_rows(limit: int = 6) -> list[str]:
    text = read(VELLUM_CHART)
    if "## Food Log" not in text:
        return []
    block = text.split("## Food Log", 1)[1]
    rows = [line for line in block.splitlines() if line.startswith("| ") and "---" not in line and "Date |" not in line]
    return rows[-limit:]


def load_support_memory() -> dict[str, Any]:
    if not SUPPORT_MEMORY.exists():
        return {"version": 1, "daily": [], "experiments": [], "watching": []}
    try:
        data = json.loads(SUPPORT_MEMORY.read_text(encoding="utf-8"))
        data.setdefault("daily", [])
        data.setdefault("experiments", [])
        data.setdefault("watching", [])
        return data
    except Exception:
        return {"version": 1, "daily": [], "experiments": [], "watching": []}


def save_support_memory(data: dict[str, Any]) -> None:
    SUPPORT_MEMORY.parent.mkdir(parents=True, exist_ok=True)
    tmp = SUPPORT_MEMORY.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    tmp.replace(SUPPORT_MEMORY)


def load_pending() -> dict[str, Any]:
    if not INKREST_PENDING.exists():
        return {}
    try:
        data = json.loads(INKREST_PENDING.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_pending(data: dict[str, Any]) -> None:
    INKREST_PENDING.parent.mkdir(parents=True, exist_ok=True)
    tmp = INKREST_PENDING.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    tmp.replace(INKREST_PENDING)


def clear_pending() -> None:
    try:
        INKREST_PENDING.unlink()
    except FileNotFoundError:
        pass


def pending_is_fresh(pending: dict[str, Any], *, hours: int = 6) -> bool:
    try:
        sent_at = datetime.fromisoformat(str(pending.get("sent_at", "")))
    except Exception:
        return False
    return now() - sent_at <= timedelta(hours=hours)


def looks_like_mood_answer(text: str) -> tuple[bool, str]:
    normalized = clean(text.lower(), 60).strip(" .,!?:;\"'")
    if not normalized:
        return False, normalized
    if re.search(r"\d|/|https?://", normalized):
        return False, normalized
    words = normalized.split()
    if len(words) > 3:
        return False, normalized
    if normalized in INKREST_WORDS:
        return True, normalized
    if len(words) == 1 and re.match(r"^[a-z][a-z-]{1,24}$", normalized):
        return True, normalized
    if len(words) <= 3 and any(word in INKREST_WORDS for word in words):
        return True, normalized
    return False, normalized


def extract_explicit_inkrest_mood(text: str) -> str:
    raw = clean(text, 160).strip()
    for pattern in EXPLICIT_INKREST_PATTERNS:
        m = re.match(pattern, raw, re.IGNORECASE)
        if not m:
            continue
        mood = clean(m.group(1), 80).strip(" .,!?:;\"'")
        mood = re.sub(r"^(?:i\s+am|i'm|im|feeling|feel)\s+", "", mood, flags=re.IGNORECASE).strip()
        return mood
    return ""


def inkrest_checkin(slot: str, *, dry_run: bool = False) -> int:
    prompts = {
        "morning": "Dr. Inkrest: one word for the weather in you this morning?",
        "midday": "Dr. Inkrest: one word, no explanation unless you want one. What is the weather in you?",
        "evening": "Dr. Inkrest: one word for how the day is landing in you?",
    }
    message = prompts.get(slot, prompts["midday"]) + "\n\nReply with just the word if that is all you have."
    skip, digest, reason = cron_steward.should_skip_duplicate("inkrest-checkin", message, cooldown_hours=2, scope=slot)
    if skip and not dry_run:
        cron_steward.mark_skipped("inkrest-checkin", reason, scope=slot, fingerprint=digest)
        return 0
    ok = send_telegram(message, dry_run=dry_run)
    if not dry_run:
        append_jsonl(INKREST_LOG, {"kind": "prompt", "slot": slot, "message": message, "sent": ok})
        if ok:
            save_pending({
                "kind": "inkrest-checkin",
                "slot": slot,
                "sent_at": now().isoformat(timespec="seconds"),
                "message": message,
                "status": "awaiting-reply",
            })
    if ok and not dry_run:
        cron_steward.mark_delivered("inkrest-checkin", message, scope=slot, slot=slot)
    return 0 if ok else 1


def inkrest_record(word: str, *, context: str = "manual", note: str = "") -> int:
    normalized = clean(word.lower(), 80).strip(" .,!?:;\"'")
    if not re.match(r"^[a-z][a-z ',&-]{1,78}$", normalized):
        raise SystemExit("Use a short mood phrase, e.g. anxious, tired, awake and productive.")
    row = {
        "kind": "mood-word",
        "word": normalized,
        "context": context,
        "note": clean(note, 300),
        "heartbeat_focus": heartbeat_field("Focus"),
        "heartbeat_pacing": heartbeat_field("Pacing"),
        "steps": steps_value(),
        "fuel": heartbeat_field("Fuel") or heartbeat_line("Fuel"),
    }
    append_jsonl(INKREST_LOG, row)
    clear_pending()
    print(f"INKREST_RECORDED: {normalized}")
    return 0


def inkrest_route(text: str, *, context: str = "telegram-reply") -> int:
    explicit = extract_explicit_inkrest_mood(text)
    if explicit:
        inkrest_record(explicit, context=context, note=f"Explicit Inkrest log request: {clean(text, 140)}")
        print("INKREST_ROUTE: recorded explicit")
        return 0
    pending = load_pending()
    if not pending or not pending_is_fresh(pending):
        if pending:
            clear_pending()
        print("INKREST_ROUTE: no fresh pending check-in")
        return 1
    ok, normalized = looks_like_mood_answer(text)
    if not ok:
        print("INKREST_ROUTE: pending check-in exists, but reply does not look like a mood answer")
        return 1
    inkrest_record(normalized, context=context, note=f"Answered {pending.get('slot', 'unknown')} Inkrest check-in.")
    print("INKREST_ROUTE: recorded")
    return 0


def vellum_brief(*, dry_run: bool = False) -> int:
    fuel = heartbeat_field("Fuel") or heartbeat_line("Fuel") or "fuel context unavailable"
    steps = steps_value()
    food = latest_food_rows(4)
    watch = heartbeat_field("Watch")
    if "nothing logged" in fuel.lower() and not food:
        nudge = "Please log the first food or drink you remember. Data before doctrine."
        hinge = "missing fuel data"
    elif steps is not None and steps < 2500:
        nudge = "A tiny movement dose would count: two minutes of walking or five slow sit-to-stands."
        hinge = "low movement signal"
    elif food and not any(("egg" in row.lower() or "protein" in row.lower() or "cheese" in row.lower() or "bacon" in row.lower()) for row in food):
        nudge = "Your next useful experiment is protein with the next meal, not perfection."
        hinge = "protein visibility"
    else:
        nudge = "Keep the day boringly supported: water, one protein anchor, and a reasonable stopping point tonight."
        hinge = "maintenance"
    message = (
        "Dr. Vellum: today's small hinge is "
        f"{hinge}. {nudge}\n\n"
        f"Current read: fuel: {fuel}; steps: {steps if steps is not None else 'unknown'}; watch: {watch or 'unknown'}."
    )
    skip, digest, reason = cron_steward.should_skip_duplicate("vellum-brief", message, cooldown_hours=4)
    if skip and not dry_run:
        cron_steward.mark_skipped("vellum-brief", reason, fingerprint=digest)
        return 0
    ok = send_telegram(message, dry_run=dry_run)
    if not dry_run:
        append_jsonl(VELLUM_LOG, {"kind": "brief", "hinge": hinge, "message": message, "sent": ok, "steps": steps, "fuel": fuel})
    if ok and not dry_run:
        cron_steward.mark_delivered("vellum-brief", message, hinge=hinge)
    return 0 if ok else 1


def synthesize(*, dry_run: bool = False) -> int:
    ink = [r for r in read_jsonl(INKREST_LOG, 7) if r.get("kind") == "mood-word"]
    prompts = [r for r in read_jsonl(INKREST_LOG, 7) if r.get("kind") == "prompt"]
    vellum = read_jsonl(VELLUM_LOG, 7)
    ledger = read_jsonl(LEDGER_LOG, 7)
    words = [str(r.get("word", "")).strip() for r in ink if r.get("word")]
    counts = Counter(words)
    latest_mood = ink[-1] if ink else {}
    latest_prompt = prompts[-1] if prompts else {}
    unanswered_since_latest = 0
    try:
        latest_mood_ts = datetime.fromisoformat(str(latest_mood.get("timestamp", "1970-01-01")).replace("Z", "+00:00"))
        if latest_mood_ts.tzinfo is not None:
            latest_mood_ts = latest_mood_ts.replace(tzinfo=None)
    except Exception:
        latest_mood_ts = datetime.min
    for row in prompts:
        try:
            ts = datetime.fromisoformat(str(row.get("timestamp", "")))
            if ts.tzinfo is not None:
                ts = ts.replace(tzinfo=None)
        except Exception:
            continue
        if ts > latest_mood_ts:
            unanswered_since_latest += 1
    by_hour: dict[str, list[str]] = defaultdict(list)
    for row in ink:
        try:
            hour = datetime.fromisoformat(row["timestamp"]).strftime("%H")
        except Exception:
            hour = "??"
        by_hour[hour].append(str(row.get("word", "")))
    steps = steps_value()
    fuel = heartbeat_field("Fuel") or heartbeat_line("Fuel")
    summary = {
        "date": today(),
        "mood_words": dict(counts.most_common()),
        "latest_mood": latest_mood,
        "latest_prompt": latest_prompt,
        "unanswered_prompts_since_latest_mood": unanswered_since_latest,
        "inkrest_pending": load_pending(),
        "mood_by_hour": {k: v for k, v in sorted(by_hour.items())},
        "latest_steps": steps,
        "latest_fuel": fuel,
        "vellum_briefs": [r.get("hinge") for r in vellum if r.get("kind") == "brief"][-5:],
        "ledger_notes": [r.get("kind") for r in ledger][-5:],
    }
    observations = []
    if counts:
        observations.append(f"Most frequent mood word this week: {counts.most_common(1)[0][0]}.")
    if steps is not None and steps < 2500:
        observations.append("Movement is currently a support target, not a moral score.")
    if fuel and "nothing logged" in fuel.lower():
        observations.append("Food data is missing; Vellum should ask gently before interpreting energy.")
    if ledger:
        observations.append("Ledger support has started; Inkrest and Vellum may correlate money fog with mood/fuel only without shame.")
    if not observations:
        observations.append("No strong pattern yet; keep collecting low-friction data.")
    summary["observations"] = observations

    memory = load_support_memory()
    memory["daily"] = [d for d in memory.get("daily", []) if d.get("date") != today()][-30:] + [summary]
    active_experiment = {
        "date": today(),
        "owner": "Inkrest + Vellum + Gimble",
        "experiment": "One-word weather check-ins, one body-support hinge, and optional money-weather visibility.",
        "metric": "mood words, steps/fuel visibility, ledger fog, and whether BJ feels less alone with the day.",
        "status": "active",
    }
    if not any(e.get("experiment") == active_experiment["experiment"] for e in memory.get("experiments", [])):
        memory.setdefault("experiments", []).append(active_experiment)
    text = "Support synthesis saved.\n" + "\n".join(f"- {o}" for o in observations)
    if dry_run:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        save_support_memory(memory)
        append_jsonl(LOG_DIR / "synthesis.jsonl", {"kind": "synthesis", **summary})
    return 0


def research(doctor: str, *, dry_run: bool = False, send: bool = False) -> int:
    doctor = doctor.lower()
    if doctor not in {"vellum", "inkrest"}:
        raise SystemExit("doctor must be vellum or inkrest")
    topics = VELLUM_RESEARCH_TOPICS if doctor == "vellum" else INKREST_RESEARCH_TOPICS
    index = int(now().strftime("%U")) % len(topics)
    title, subject = topics[index]
    chart = read(VELLUM_CHART if doctor == "vellum" else INKREST_CHART, 5000)
    fuel = heartbeat_field("Fuel") or heartbeat_line("Fuel")
    steps = steps_value()
    owner = "Dr. Elowen Vellum" if doctor == "vellum" else "Dr. Selene Inkrest"
    if doctor == "vellum":
        experiment = "Choose one protein/fiber/movement support action today and review tomorrow."
        safety = "Do not change medications or start supplements without checking interactions and clinician/pharmacist questions."
    else:
        experiment = "Answer one-word weather when asked; if the word is rough, choose grounding, reauthoring, or quiet company."
        safety = "Do not diagnose, force catharsis, or interpret distress before checking food, sleep, medication, and safety."
    body = f"""# {owner} Independent Brief — {title}

*Date:* {today()}
*Focus:* {subject}

## Current Personal Context

- Fuel signal: {fuel or 'unknown'}
- Steps: {steps if steps is not None else 'unknown'}
- Chart context excerpt: {clean(chart, 900)}

## Working Hypothesis

This is a useful axis to watch because it can be tested in BJ's real day without turning care into homework.

## Experiment

{experiment}

## Simulation Question

What if BJ changed only this one variable for 3-7 days, while everything else stayed ordinary?

## Watch-Outs

{safety}

## Memory Hook

If this pattern repeats, fold it into the nightly support synthesis and the next Story-Field Journal health/support panel.
"""
    path = MEMORY_DIR / "research" / f"{today()}-{doctor}-{re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')}.md"
    if dry_run:
        print(body)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        append_jsonl(LOG_DIR / "research.jsonl", {"kind": "research", "doctor": doctor, "title": title, "path": str(path)})
    if send:
        msg = f"{owner}: I filed a new independent brief on {title}. The experiment is simple: {experiment}"
        send_telegram(msg, dry_run=dry_run, silent=True)
    print(path if not dry_run else "dry-run")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Dr. Vellum / Dr. Inkrest daily support loop")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("inkrest-checkin")
    p.add_argument("--slot", choices=["morning", "midday", "evening"], default="midday")
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("inkrest-record")
    p.add_argument("word")
    p.add_argument("--context", default="manual")
    p.add_argument("--note", default="")

    p = sub.add_parser("inkrest-route")
    p.add_argument("text")
    p.add_argument("--context", default="telegram-reply")

    p = sub.add_parser("vellum-brief")
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("synthesize")
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("research")
    p.add_argument("--doctor", choices=["vellum", "inkrest"], required=True)
    p.add_argument("--send", action="store_true")
    p.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()
    ensure_dirs()
    with cron_steward.run(f"support-faculty:{args.command}"):
        if args.command == "inkrest-checkin":
            return inkrest_checkin(args.slot, dry_run=args.dry_run)
        if args.command == "inkrest-record":
            return inkrest_record(args.word, context=args.context, note=args.note)
        if args.command == "inkrest-route":
            return inkrest_route(args.text, context=args.context)
        if args.command == "vellum-brief":
            return vellum_brief(dry_run=args.dry_run)
        if args.command == "synthesize":
            return synthesize(dry_run=args.dry_run)
        if args.command == "research":
            return research(args.doctor, dry_run=args.dry_run, send=args.send)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

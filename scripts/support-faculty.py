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
import time
import urllib.error
import urllib.request
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
import journal_artifact  # type: ignore
import support_insights  # type: ignore


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

RESEARCH_SOURCE_PACKS = {
    "vellum": {
        "protein floor": [
            "Evidence lane: older adults generally need attention to protein distribution and resistance stimulus for muscle preservation; treat exact grams as individualized, not doctrine.",
            "Source families to consult when updating: NIH/NIA healthy aging guidance, ACSM/resistance-training guidance, protein-and-aging reviews, and clinician guidance for kidney disease or medication constraints.",
        ],
        "resistance stimulus": [
            "Evidence lane: resistance training has strong support for strength, function, glucose handling, fall-risk reduction, and healthspan; minimum effective doses matter for adherence.",
            "Source families to consult when updating: ACSM, NIA exercise guidance, meta-analyses on resistance training and older adults, physical-therapy safety guidance.",
        ],
        "sleep regularity": [
            "Evidence lane: sleep timing regularity, morning light, caffeine timing, and wind-down consistency are plausible high-leverage supports; medication effects and mental health context matter.",
            "Source families to consult when updating: AASM sleep hygiene/insomnia guidance, NIA sleep and aging material, circadian/sleep regularity cohort studies, pharmacist/clinician medication review.",
        ],
        "blood pressure readiness": [
            "Evidence lane: home BP technique and repeated measurements are more useful than single dramatic readings; sodium, potassium, alcohol, stress, sleep, movement, and medications all matter.",
            "Source families to consult when updating: American Heart Association home BP guidance, ACC/AHA hypertension guidelines, clinician/pharmacist medication review.",
        ],
        "creatine shelf": [
            "Evidence lane: creatine has moderate-to-strong support for strength/power when paired with training, possible cognitive/fatigue research remains mixed; kidney function and medication context matter.",
            "Source families to consult when updating: NIH Office of Dietary Supplements, sports nutrition position stands, kidney/eGFR safety literature, pharmacist interaction checks.",
        ],
        "fiber and microbiome": [
            "Evidence lane: dietary fiber has strong support for cardiometabolic and gut-health outcomes; microbiome claims should stay practical and food-first.",
            "Source families to consult when updating: Dietary Guidelines for Americans, NIH/NIA nutrition guidance, AHA Life's Essential 8, fiber intervention reviews.",
        ],
    },
    "inkrest": {
        "one-word weather": [
            "Evidence lane: affect labeling and low-friction mood tracking can reduce avoidance and reveal patterns; too much tracking can become rumination for some people.",
            "Source families to consult when updating: affect-labeling research, CBT/DBT/ACT emotion-labeling practices, measurement-based care cautions.",
        ],
        "hyperfocus closure": [
            "Evidence lane: transition rituals, implementation intentions, and recovery periods help reduce cognitive residue after intense work; mental health and sleep protection matter.",
            "Source families to consult when updating: executive-function research, implementation-intention studies, occupational recovery literature, ADHD/hyperfocus clinical guidance as adjacent not assumed.",
        ],
        "narrative identity": [
            "Evidence lane: narrative therapy uses externalizing, unique outcomes, preferred identity, and witnesses; narrative identity research links meaning-making with wellbeing without replacing clinical care.",
            "Source families to consult when updating: Michael White/David Epston narrative therapy, narrative identity research, values-based ACT practice, trauma-informed therapy ethics.",
        ],
        "rumination loops": [
            "Evidence lane: rumination is maintained by repetitive self-focused thinking; defusion, behavioral activation, attention shifting, and body-first checks can help.",
            "Source families to consult when updating: CBT rumination models, ACT defusion, behavioral activation evidence, default-mode-network research as explanatory not prescriptive.",
        ],
        "daydream material": [
            "Evidence lane: daydreams and recurring images can be treated as meaning-making material, but interpretation should be collaborative and practical, not certain or mystical.",
            "Source families to consult when updating: contemporary depth psychology, imagery rescripting, narrative therapy, trauma-informed stabilization.",
        ],
        "medication and dreams": [
            "Evidence lane: medication, sleep architecture, depression/PTSD, and sleep regularity can alter dream recall; absence of dream recall is not therapeutic failure.",
            "Source families to consult when updating: sleep architecture research, medication side-effect resources, clinician/pharmacist review, trauma-informed dreamwork cautions.",
        ],
    },
}

EXPERIMENT_LIBRARY = {
    "vellum": {
        "sleep regularity": {
            "name": "The Same-Door Sleep Trial",
            "daily_action": "Pick one repeatable sleep door: same wake time, caffeine cutoff, or a 10-minute lights-down cue. Do only that for seven days.",
            "minimum": "Write the intended wake time and stop caffeine after lunch if possible. If the day is already sideways, just dim one light 10 minutes before bed.",
            "ordinary": "Morning: get outside/light near a window for 2-5 minutes. Afternoon: no caffeine after the chosen cutoff. Night: one low-light wind-down cue before meds/bed.",
            "metric": "bedtime, wake time, caffeine-last-time, energy 1-5, mood word, and whether sleep felt regular or chaotic.",
            "watch": "Whether mood steadiness and next-day fuel choices improve more when wake time is consistent than when bedtime is forced.",
            "safety": "Do not change risperidone/escitalopram timing without clinician guidance. If sleep becomes severely reduced, agitated, or unusual, treat it as a care signal, not an experiment win.",
        },
        "protein floor": {
            "name": "The 25-Gram First Real Food Trial",
            "daily_action": "Make the first substantial food of the day include a protein anchor before trying to optimize anything else.",
            "minimum": "Add one easy protein item: Greek yogurt, eggs, tuna, chicken, protein shake, cottage cheese, beans, or whatever BJ actually tolerates.",
            "ordinary": "Aim for roughly 25-35g protein in the first real meal, plus one fiber-containing food if available.",
            "metric": "time of first protein, estimated grams, 3 PM hunger 1-5, evening snack urge 1-5, mood word.",
            "watch": "Whether afternoon steadiness changes when coffee is not carrying the whole morning alone.",
            "safety": "Protein targets should be individualized if kidney disease appears in labs. Unknown eGFR means be sensible, not extreme.",
        },
        "resistance stimulus": {
            "name": "The Useful Strength Spark",
            "daily_action": "Give the body one small reason to keep muscle: sit-to-stands, wall pushups, loaded carry, or stair practice.",
            "minimum": "One set of five sit-to-stands or five wall pushups.",
            "ordinary": "Two rounds: 5-10 sit-to-stands, 5-10 wall pushups, 20-40 seconds carrying something safe.",
            "metric": "done/not done, perceived effort 1-5, soreness next day, confidence for stairs/groceries.",
            "watch": "Whether tiny strength makes adventure capacity feel more believable without triggering dread.",
            "safety": "Stop for chest pain, dizziness, sharp joint pain, or unusual shortness of breath. Scale around injuries.",
        },
        "blood pressure readiness": {
            "name": "The Quiet Cuff Protocol",
            "daily_action": "Prepare for useful BP data instead of dramatic BP data.",
            "minimum": "If no cuff/readings exist, write the question: 'What home BP cuff and schedule does my clinician recommend?'",
            "ordinary": "When a cuff exists: sit quietly five minutes, feet flat, arm supported, take two readings one minute apart, log context.",
            "metric": "systolic/diastolic/pulse, time, caffeine/stress/sleep context, average of repeated readings.",
            "watch": "Whether repeated home readings reveal a pattern worth taking to a clinician.",
            "safety": "Very high readings or symptoms belong to real medical care. Do not self-adjust medication.",
        },
        "creatine shelf": {
            "name": "The Creatine Decision Shelf",
            "daily_action": "Do not start yet; gather the missing safety context and decide whether creatine is worth a conservative trial.",
            "minimum": "Check whether recent creatinine/eGFR exists; if not, add it to doctor questions.",
            "ordinary": "Write a pharmacist/doctor question covering eGFR, medications, dose, hydration, and what benefit BJ actually wants.",
            "metric": "eGFR known yes/no, clinician/pharmacist question created, target benefit chosen.",
            "watch": "Whether this belongs in the 'worth trying' shelf once labs/med context are known.",
            "safety": "Avoid starting if kidney function is unknown and there are concerns. Do not chase cognitive hype without a clear reason.",
        },
        "fiber and microbiome": {
            "name": "The One Added Fiber Trial",
            "daily_action": "Add one fiber source BJ can actually imagine eating, without redesigning the whole diet.",
            "minimum": "One apple, beans, oats, berries, whole-grain toast, vegetable side, or a small psyllium discussion note for later.",
            "ordinary": "Add one fiber food to the meal that already exists; pair with water.",
            "metric": "fiber source, digestion comfort 1-5, fullness 1-5, repeatability.",
            "watch": "Whether fiber is easier as an addition than a replacement.",
            "safety": "Increase gradually; sudden fiber jumps can cause GI misery. Supplement fiber may affect medication timing; ask pharmacist if used.",
        },
    },
    "inkrest": {
        "narrative identity": {
            "name": "The Unique Outcome Ledger",
            "daily_action": "Catch one moment when BJ is already living the preferred story, however small.",
            "minimum": "One sentence: 'The problem story said __, but I did __.'",
            "ordinary": "Name the problem, the exception, the value it served, and one witness who would recognize it.",
            "metric": "mood word, problem name, unique outcome yes/no, agency after note 1-5.",
            "watch": "Whether the preferred identity thickens when proof is collected instead of argued for.",
            "safety": "Do not use this to deny grief, depression, PTSD, or practical limits. Preferred story is not forced positivity.",
        },
        "one-word weather": {
            "name": "The Weather Without Trial",
            "daily_action": "Give one mood word, then one body context word, then stop unless more is wanted.",
            "minimum": "Mood word + body word: 'anxious / hungry' or 'good / sore'.",
            "ordinary": "Mood word, body context, one next-hour support action.",
            "metric": "response rate, word variety, whether check-ins feel supportive or annoying.",
            "watch": "Whether one-word logging catches patterns without becoming surveillance.",
            "safety": "If tracking starts feeling like judgment, reduce frequency immediately.",
        },
        "hyperfocus closure": {
            "name": "The Doorframe Ritual",
            "daily_action": "Before stopping a build session, leave the next self a visible thread.",
            "minimum": "Write: 'Next: ___' and close one tab/window.",
            "ordinary": "Write next action, what was finished, what can wait, and one recovery cue.",
            "metric": "shutdown happened yes/no, sleep friction 1-5, next-day restart ease 1-5.",
            "watch": "Whether closure reduces the fear that stopping means losing the whole world.",
            "safety": "Do not turn closure into more work. It should take under three minutes.",
        },
        "rumination loops": {
            "name": "The Loop Name and Exit",
            "daily_action": "When looping starts, name the loop as an external thing and choose one sensory exit.",
            "minimum": "Say: 'This is the Loop, not the whole truth.' Touch one stable surface.",
            "ordinary": "Name loop, identify trigger, choose one next-hour action aligned with values.",
            "metric": "loop intensity before/after 1-5, exit used, whether action became possible.",
            "watch": "Whether externalizing plus body contact interrupts the spiral faster than analysis.",
            "safety": "If content becomes crisis-level or unsafe, use real support immediately.",
        },
        "daydream material": {
            "name": "The Daydream Witness Card",
            "daily_action": "Treat one daydream/image as material, not a command.",
            "minimum": "Write the image and one feeling.",
            "ordinary": "Image, feeling, possible need, and one real-world kindness it asks for.",
            "metric": "image logged, feeling named, action chosen, pressure after 1-5.",
            "watch": "Whether recurring images point toward needs before they become overwhelm.",
            "safety": "No certainty claims. No forced excavation. The body gets veto power.",
        },
        "medication and dreams": {
            "name": "The No-Dream Permission Slip",
            "daily_action": "Use waking images, mood, and body signals as valid material when dreams are absent.",
            "minimum": "Log 'no dream' plus first waking mood.",
            "ordinary": "Waking mood, sleep quality, first image/song/thought, and one gentle interpretation question.",
            "metric": "dream recall yes/no, sleep quality 1-5, waking mood, usefulness of reflection.",
            "watch": "Whether removing dream-pressure makes more subtle material available.",
            "safety": "Medication effects are clinician/pharmacist territory. No medication changes for dream recall.",
        },
    },
}


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


def load_config() -> dict[str, str]:
    cfg: dict[str, str] = {}
    for path in (BASE / "config" / "secrets.env",):
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            cfg[key.strip()] = value.strip().strip('"').strip("'")
    return cfg


def _normalize_gateway_model(model: str) -> str:
    model = (model or "").strip()
    if model == "openclaw" or model.startswith("openclaw/"):
        return model
    return "openclaw"


def _oc_gateway_cfg() -> tuple[int, str, str, int]:
    oc_cfg: dict[str, Any] = {}
    cfg_path = Path.home() / ".openclaw" / "openclaw.json"
    if cfg_path.exists():
        try:
            oc_cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            oc_cfg = {}
    secrets = load_config()
    port = int(oc_cfg.get("gateway", {}).get("port", 18789))
    token = str(oc_cfg.get("gateway", {}).get("auth", {}).get("token", ""))
    raw_model = (
        secrets.get("SUPPORT_RESEARCH_MODEL")
        or secrets.get("BLEED_MODEL")
        or "openclaw"
    )
    timeout_raw = secrets.get("SUPPORT_RESEARCH_TIMEOUT") or secrets.get("BLEED_GATEWAY_TIMEOUT") or "150"
    try:
        timeout = max(30, int(timeout_raw))
    except ValueError:
        timeout = 150
    return port, token, _normalize_gateway_model(raw_model), timeout


def call_research_llm(prompt: str, *, doctor: str) -> str:
    port, token, model, timeout = _oc_gateway_cfg()
    url = f"http://127.0.0.1:{port}/v1/chat/completions"
    session_key = f"support-research-{doctor}-{int(time.time())}"
    system = (
        "You write private, practical Enchantify support-faculty research briefs. "
        "Be detailed, grounded, cautious, and useful. Do not diagnose, prescribe, "
        "claim you performed live web browsing, or invent medical/lab data. "
        "If evidence is uncertain, say so. Reply only with the brief in Markdown."
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.72,
        "max_tokens": 3600,
        "stream": False,
    }
    req = urllib.request.Request(
        url,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "x-openclaw-session-key": session_key,
        },
        data=json.dumps(payload).encode("utf-8"),
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"Gateway returned HTTP {e.code}: {body}") from e
    except Exception as e:
        raise RuntimeError(f"Gateway call failed: {e}") from e
    return clean_model_markdown(data.get("choices", [{}])[0].get("message", {}).get("content", ""))


def clean_model_markdown(text: str) -> str:
    text = str(text or "").strip()
    text = re.sub(r"^```(?:markdown)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def send_telegram(message: str, media: Path | None = None, *, dry_run: bool = False, silent: bool = False) -> bool:
    if dry_run:
        print(message)
        if media:
            print(f"[dry-run media] {media}")
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
    if media:
        args += ["--media", str(media), "--force-document"]
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
    try:
        context = support_insights.fuel_context()
        tail = context.get("tail") or []
        return [str(row) for row in tail[-limit:]]
    except Exception:
        return []


def current_fuel_summary() -> str:
    try:
        context = support_insights.fuel_context()
        return str(context.get("combined") or context.get("today") or "fuel context unavailable")
    except Exception:
        return heartbeat_field("Fuel") or heartbeat_line("Fuel") or "fuel context unavailable"


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
    artifact = render_support_pdf(
        f"# Dr. Vellum's Refectory Marginalia\n\n{message}",
        f"{today()}-vellum-brief",
        title="Dr. Vellum's Refectory Marginalia",
        subtitle=hinge,
        accent="#4f6f3a",
        dry_run=dry_run,
    )
    media = Path(artifact["pdf"]) if artifact.get("pdf") else None
    ok = send_telegram(message, media, dry_run=dry_run)
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


def vellum_personal_message(
    *,
    hinge: str,
    nudge: str,
    fuel: str,
    steps: int | None,
    watch: str,
    insight_rows: list[dict[str, Any]],
) -> str:
    lines = [
        "Dr. Vellum's Refectory Marginalia",
        "",
        "BJ,",
        "",
        "I have made a small annotation in the margin of your day. Not a prescription. Not a scold. A hinge.",
        "",
        f"Today's hinge: {hinge}.",
        nudge,
        "",
        f"My current read: fuel: {fuel}; steps: {steps if steps is not None else 'unknown'}; watch: {watch or 'unknown'}.",
    ]
    if insight_rows:
        lines.extend(["", "Cross-read from the chart edges:"])
        for row in insight_rows:
            lines.append(f"- {row['title']}: {row['detail']} Next: {row['action']}")
    lines.extend([
        "",
        "Comfort clause: the body is not a moral ledger. It is the binding. We support the binding so the story has somewhere vivid to happen.",
        "",
        "— Dr. Elowen Vellum",
    ])
    return "\n".join(lines)


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
    context = support_insights.build_context(live_actual=False)
    fuel = current_fuel_summary()
    steps = steps_value()
    food = [str(row) for row in (context.get("vellum", {}).get("fuel_tail") or latest_food_rows(4))[-4:]]
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
    insight_rows = support_insights.derive_insights(context, perspective="vellum", limit=2)
    message = vellum_personal_message(
        hinge=hinge,
        nudge=nudge,
        fuel=fuel,
        steps=steps,
        watch=watch,
        insight_rows=insight_rows,
    )
    skip, digest, reason = cron_steward.should_skip_duplicate("vellum-brief", message, cooldown_hours=4)
    if skip and not dry_run:
        cron_steward.mark_skipped("vellum-brief", reason, fingerprint=digest)
        return 0
    ok = send_telegram(message, dry_run=dry_run)
    if not dry_run:
        append_jsonl(VELLUM_LOG, {"kind": "brief", "hinge": hinge, "message": message, "sent": ok, "steps": steps, "fuel": fuel, "insights": insight_rows})
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
    context = support_insights.build_context(live_actual=False)
    fuel = context.get("heartbeat", {}).get("fuel") or heartbeat_field("Fuel") or heartbeat_line("Fuel")
    insight_rows = support_insights.derive_insights(context, perspective="guild", limit=5)
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
        "cross_domain_insights": insight_rows,
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
    observations.extend(f"{row['title']}: {row['detail']}" for row in insight_rows[:3])
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


def support_research_image_prompt(doctor: str, owner: str, topic: str) -> str:
    if doctor == "vellum":
        return (
            "A custom header illumination for Dr. Elowen Vellum's Enchantify storybook journal research page. "
            f"Subject: {topic}. Show a precise Literary Elf longevity physician's desk: green ink annotations, "
            "a silver bookmark-caliper, tiny lab labels, folded meal notes, a blood-pressure cuff sketch, "
            "exercise prescription cards, supplement caution seals, pressed herbs, and warm practical care. "
            "Lush handwritten marginalia, lush watercolor washes, prominent library stamps, wax seals, tabs, arrows, "
            "field-journal labels, ink blooms, aged parchment, elegant medical marginalia. "
            "Make the custom image feel like the research page's main illuminated plate, not a thumbnail. "
            "No readable text, no logo, no watermark."
        )
    return (
        "A custom header illumination for Dr. Selene Inkrest's Enchantify storybook journal research page. "
        f"Subject: {topic}. Show a depth therapist's quiet desk: blue-black ink notes, moonlit index cards, "
        "a reauthoring-room key, one-word mood weather slips, daydream image cards, consciousness diagrams as soft ink geometry, "
        "gentle grounding objects, and a small lamp over a difficult page. "
        "Lush handwritten marginalia, lush watercolor washes, prominent library stamps, wax seals, tabs, arrows, "
        "field-journal labels, ink blooms, aged parchment, therapeutic but magical atmosphere. "
        "Make the custom image feel like the research page's main illuminated plate, not a thumbnail. "
        "No readable text, no logo, no watermark."
    )


def render_support_pdf(
    markdown: str,
    stem: str,
    *,
    title: str,
    subtitle: str,
    accent: str,
    dry_run: bool = False,
    doctor: str = "",
) -> dict[str, str]:
    image_prompt = support_research_image_prompt(doctor, title, subtitle) if doctor in {"vellum", "inkrest"} else ""
    image_caption = f"{title} · {subtitle} · illuminated research page" if subtitle else f"{title} · illuminated research page"
    return journal_artifact.render(
        markdown,
        MEMORY_DIR / "journal",
        stem,
        title=title,
        subtitle=subtitle,
        footer="Filed by the Enchantify support faculty",
        accent=accent,
        image_prompt=image_prompt,
        image_caption=image_caption,
        image_required=doctor in {"vellum", "inkrest"},
        dry_run=dry_run,
    )


def research_context_for(doctor: str, title: str, subject: str) -> dict[str, Any]:
    context = support_insights.build_context(live_actual=False)
    chart_path = VELLUM_CHART if doctor == "vellum" else INKREST_CHART
    log_path = VELLUM_LOG if doctor == "vellum" else INKREST_LOG
    memory = load_support_memory()
    return {
        "date": today(),
        "doctor": doctor,
        "topic": title,
        "subject": subject,
        "chart_excerpt": clean(read(chart_path, 7000), 7000),
        "heartbeat": context.get("heartbeat", {}),
        "mood": context.get("mood", {}),
        "vellum": context.get("vellum", {}),
        "ledger": context.get("ledger", {}),
        "recent_support_log": read_jsonl(log_path, days=14)[-10:],
        "active_experiments": [e for e in memory.get("experiments", []) if e.get("status") in {"active", "proposed", "review"}][-8:],
        "source_pack": RESEARCH_SOURCE_PACKS.get(doctor, {}).get(title, []),
        "cross_domain_insights": support_insights.derive_insights(context, perspective=doctor, limit=4),
    }


def build_research_prompt(owner: str, doctor: str, title: str, subject: str, context: dict[str, Any]) -> str:
    if doctor == "vellum":
        voice = (
            "Dr. Elowen Vellum: precise Literary Elf longevity physician. "
            "She is direct, warm, evidence-aware, and BJ-specific. She may discuss "
            "supplements/exercise/recovery, but must name risks, missing labs, medication "
            "interaction checks, and clinician/pharmacist questions when relevant."
        )
        required = [
            "The Vellum Verdict: one surprising practical insight for BJ.",
            "Evidence Shelf: 3-5 bullets with evidence strength labels.",
            "BJ Translation: why this matters for BJ's actual age, meds, work, fuel, mood, and constraints.",
            "Experiment Card: name, duration, daily action, minimum version, ordinary version, metric, review date, stop/scale-down signals.",
            "Safety / Doctor Questions: concrete cautions and one question if relevant.",
            "What I Will Watch: what future data would change the recommendation.",
            "One Sentence for the Book.",
        ]
    else:
        voice = (
            "Dr. Selene Inkrest: narrative therapist and depth-informed consciousness researcher. "
            "She is gentle, rigorous, practical, and consent-aware. She uses narrative therapy, "
            "ACT/CBT/parts/somatic tools only to make the next hour more livable. She does not diagnose."
        )
        required = [
            "The Inkrest Reading: one surprising therapeutic angle for BJ.",
            "Research Shelf: 3-5 bullets with evidence/practice strength labels.",
            "BJ Translation: connect the idea to mood words, fuel/body context, work, creativity, and preferred identity.",
            "Experiment Card: name, duration, prompt/script, minimum version, ordinary version, metric, review date, stop/scale-down signals.",
            "Therapeutic Boundaries: what not to interpret or push.",
            "What I Will Watch: what future mood/daydream/body data would change the hypothesis.",
            "One Sentence for the Book.",
        ]
    return f"""Write a full independent support-faculty research brief.

Owner and voice:
{voice}

Topic: {title}
Focus: {subject}

Current BJ context as JSON:
{json.dumps(context, ensure_ascii=False, indent=2, default=str)}

Required sections, in this order:
{chr(10).join(f"- {item}" for item in required)}

Rules:
- Be specific enough that BJ could try the experiment today.
- Include at least one non-obvious or surprising but sane insight.
- Use the source_pack as a research lane, not as proof of live browsing.
- Do not cite fake paper titles, fake years, fake authors, or fake URLs.
- If you mention research, keep it to source families or widely established concepts unless the context contains a precise citation.
- Do not use generic wellness copy.
- Do not make the experiment heroic. BJ-sized means it can survive work, depression, PTSD, mobile-first use, and hyperfocus.
- Markdown only. Start with: # {owner} Independent Brief — {title}
"""


def fallback_research_body(owner: str, doctor: str, title: str, subject: str, context: dict[str, Any], error: str = "") -> str:
    heartbeat = context.get("heartbeat", {})
    mood = context.get("mood", {})
    source_lines = context.get("source_pack") or ["No source pack found; use chart rules and conservative practice."]
    insights = context.get("cross_domain_insights") or []
    latest_mood = clean(mood.get("latest_word") or "unknown", 80)
    fuel = clean(heartbeat.get("fuel") or "unknown", 240)
    steps = heartbeat.get("steps")
    review = (now() + timedelta(days=7)).strftime("%Y-%m-%d")
    exp = EXPERIMENT_LIBRARY.get(doctor, {}).get(title, {})
    if doctor == "vellum":
        verdict = "The useful move is to make the next body experiment measurable before making it ambitious."
        experiment_name = f"Vellum Seven-Day {title.title()} Trial"
        daily = "Choose one anchor action tied to the topic, do the minimum version on workdays, and record one number or sentence."
        minimum = "One minute, one serving, one set, or one preparation step. Count it without apology."
        ordinary = "A complete but still small version: 10-20 minutes, one planned meal component, or one repeatable evening cue."
        metric = "energy 1-5, sleep quality 1-5, steps/fuel visibility, and whether the action happened."
        watch = "Whether the signal changes when BJ logs enough body/mood/fuel context to compare ordinary days against experiment days."
        safety = "No medication changes. No supplement starts without medication/eGFR/clinician or pharmacist review when relevant."
    else:
        verdict = "The useful move is to turn the topic into a small reauthoring practice with body context checked first."
        experiment_name = f"Inkrest Seven-Day {title.title()} Trial"
        daily = "Answer one sentence: 'The problem tried to say __; the preferred story answered __.'"
        minimum = "One mood word plus one body check: food, water, sleep, pain, medication timing."
        ordinary = "A two-minute reauthoring note naming the problem, one unique outcome, and the next-hour action."
        metric = "mood word, body context, whether the note reduced pressure or increased agency."
        watch = "Whether the signal changes when BJ logs enough body/mood/fuel context to compare ordinary days against experiment days."
        safety = "Do not force catharsis, trauma excavation, or symbolic certainty. If distress spikes, switch to grounding and real support."
    experiment_name = exp.get("name", experiment_name)
    daily = exp.get("daily_action", daily)
    minimum = exp.get("minimum", minimum)
    ordinary = exp.get("ordinary", ordinary)
    metric = exp.get("metric", metric)
    watch = exp.get("watch", watch)
    safety = exp.get("safety", safety)
    insight_lines = "\n".join(f"- {row.get('title')}: {row.get('detail')} Next: {row.get('action')}" for row in insights[:3]) or "- No strong cross-domain pattern yet."
    sources = "\n".join(f"- {line}" for line in source_lines)
    return f"""# {owner} Independent Brief — {title}

*Date:* {today()}
*Focus:* {subject}
*Generation note:* deterministic fallback used{f" because {clean(error, 160)}" if error else ""}.

## The {'Vellum Verdict' if doctor == 'vellum' else 'Inkrest Reading'}

{verdict}

## Evidence Shelf

{sources}

## BJ Translation

- Latest mood trace: {latest_mood}
- Current fuel/body trace: {fuel}
- Steps: {steps if steps is not None else 'unknown'}
- Cross-domain pattern:
{insight_lines}

## Experiment Card

- **Name:** {experiment_name}
- **Duration:** 7 days
- **Daily action:** {daily}
- **Minimum version:** {minimum}
- **Ordinary version:** {ordinary}
- **Metric:** {metric}
- **Review date:** {review}
- **Stop / scale-down signals:** overwhelm, sleep disruption, dread, pain, confusion, or any sense that the experiment has become a verdict.

## {'Safety / Doctor Questions' if doctor == 'vellum' else 'Therapeutic Boundaries'}

{safety}

## What I Will Watch

{watch}

## One Sentence for the Book

The experiment is not a test of virtue; it is a little lamp placed where the fog keeps pretending there is no floor.
"""


def validate_research_body(body: str) -> bool:
    required = ["Experiment Card", "BJ Translation", "What I Will Watch", "One Sentence for the Book"]
    return len(body.split()) >= 450 and all(token.lower() in body.lower() for token in required)


def experiment_from_research(body: str, doctor: str, title: str) -> dict[str, Any]:
    def field(name: str) -> str:
        m = re.search(rf"\*\*{re.escape(name)}:\*\*\s*(.+)", body, re.IGNORECASE)
        return clean(m.group(1), 400) if m else ""

    review = field("Review date")
    return {
        "date": today(),
        "owner": "Dr. Elowen Vellum" if doctor == "vellum" else "Dr. Selene Inkrest",
        "topic": title,
        "experiment": field("Name") or f"{title.title()} support experiment",
        "duration": field("Duration") or "7 days",
        "daily_action": field("Daily action"),
        "minimum_version": field("Minimum version"),
        "ordinary_version": field("Ordinary version"),
        "metric": field("Metric"),
        "review_date": review or (now() + timedelta(days=7)).strftime("%Y-%m-%d"),
        "status": "proposed",
        "source": "support-faculty research",
    }


def remember_research_experiment(body: str, doctor: str, title: str) -> None:
    memory = load_support_memory()
    experiment = experiment_from_research(body, doctor, title)
    if not experiment.get("daily_action") and not experiment.get("metric"):
        return
    existing = memory.setdefault("experiments", [])
    key = (experiment.get("owner"), experiment.get("topic"), experiment.get("date"))
    if not any((e.get("owner"), e.get("topic"), e.get("date")) == key for e in existing):
        existing.append(experiment)
    memory["experiments"] = existing[-40:]
    save_support_memory(memory)


def research(doctor: str, *, dry_run: bool = False, send: bool = False) -> int:
    doctor = doctor.lower()
    if doctor not in {"vellum", "inkrest"}:
        raise SystemExit("doctor must be vellum or inkrest")
    topics = VELLUM_RESEARCH_TOPICS if doctor == "vellum" else INKREST_RESEARCH_TOPICS
    index = int(now().strftime("%U")) % len(topics)
    title, subject = topics[index]
    owner = "Dr. Elowen Vellum" if doctor == "vellum" else "Dr. Selene Inkrest"
    context = research_context_for(doctor, title, subject)
    error = ""
    try:
        body = call_research_llm(build_research_prompt(owner, doctor, title, subject, context), doctor=doctor)
    except Exception as e:
        error = str(e)
        body = ""
    if not validate_research_body(body):
        body = fallback_research_body(owner, doctor, title, subject, context, error or "model output missed the required experiment scaffold")
    path = MEMORY_DIR / "research" / f"{today()}-{doctor}-{re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')}.md"
    if dry_run:
        print(body)
        artifact = {"html": "", "pdf": "", "pdf_detail": "dry-run"}
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        remember_research_experiment(body, doctor, title)
        artifact = render_support_pdf(
            body,
            path.stem,
            title=f"{owner} Independent Brief",
            subtitle=title,
            accent="#31534c" if doctor == "inkrest" else "#4f6f3a",
            doctor=doctor,
            dry_run=False,
        )
        append_jsonl(LOG_DIR / "research.jsonl", {"kind": "research", "doctor": doctor, "title": title, "path": str(path), "html": artifact.get("html"), "pdf": artifact.get("pdf"), "pdf_detail": artifact.get("pdf_detail"), "llm_error": error})
    if send:
        experiment = experiment_from_research(body, doctor, title)
        msg = (
            f"{owner} filed a new illustrated storybook research page.\n\n"
            f"Topic: {title}\n"
            f"Experiment: {experiment.get('experiment') or title}\n"
            f"Review: {experiment.get('review_date') or 'in about a week'}\n\n"
            "Full PDF attached."
        )
        media = Path(artifact["pdf"]) if artifact.get("pdf") else path
        send_telegram(msg, media, dry_run=dry_run, silent=True)
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

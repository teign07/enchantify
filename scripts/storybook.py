#!/usr/bin/env python3
"""The Book of You: daily illustrated storybook artifact.

This is the player's lived day translated into Enchantify's literary memory:
real signals, play choices, support faculty notes, simulation motion, and the
day's illustrations gathered into one readable chapter.
"""

from __future__ import annotations

import argparse
import calendar
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent.parent
PLAYERS = BASE / "players"
LOGS = BASE / "logs"
MEMORY = BASE / "memory"
STORYBOOK = MEMORY / "storybook"
DAILY_DIR = STORYBOOK / "daily"
HTML_DIR = STORYBOOK / "html"
PDF_DIR = STORYBOOK / "pdf"
MONTHLY_DIR = STORYBOOK / "monthly"
MONTHLY_HTML_DIR = MONTHLY_DIR / "html"
MONTHLY_PDF_DIR = MONTHLY_DIR / "pdf"
ASSET_DIR = STORYBOOK / "assets"
INDEX = STORYBOOK / "index.md"
STORYBOOK_LOG = LOGS / "storybook.jsonl"
HEARTBEAT = BASE / "HEARTBEAT.md"
SECRETS_ENV = BASE / "config" / "secrets.env"

sys.path.insert(0, str(BASE / "scripts"))
import cron_steward  # type: ignore
try:
    import relationships  # type: ignore
    _HAS_RELATIONSHIPS = True
except Exception:
    relationships = None  # type: ignore
    _HAS_RELATIONSHIPS = False


def now() -> datetime:
    return datetime.now()


def today() -> str:
    return now().strftime("%Y-%m-%d")


def ensure_dirs() -> None:
    for path in (DAILY_DIR, HTML_DIR, PDF_DIR, MONTHLY_DIR, MONTHLY_HTML_DIR, MONTHLY_PDF_DIR, ASSET_DIR, LOGS):
        path.mkdir(parents=True, exist_ok=True)


def clean(value: Any, limit: int = 500) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit].rstrip() + ("..." if len(text) > limit else "")


def strip_raw_status(text: Any) -> str:
    """Turn machine-ish heartbeat strings into journal-safe phrases."""
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    value = re.sub(r"\s*\([^)]*(?:fallback|cached|iCloud sync lock|ago)[^)]*\)", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\bStatus:\s*", "", value, flags=re.IGNORECASE)
    value = value.replace("`", "")
    return value.strip(" ;")


def poetic_mood(text: Any) -> str:
    value = strip_raw_status(text).lower()
    if not value or value == "unwritten":
        return "quietly unwritten"
    if "tired" in value and "ache" in value:
        return "tired and achey, the body asking to be handled gently"
    if "nause" in value:
        return "nauseous weather moving under the day"
    if "content" in value:
        return "content, or close enough to let the page breathe"
    if "awake" in value and "productive" in value:
        return "awake and productive, a small lamp lit in the working part of the day"
    return value


def poetic_fuel(text: Any) -> str:
    value = strip_raw_status(text)
    if not value:
        return "fuel data not yet visible"
    pieces = []
    if "coffee" in value.lower():
        pieces.append("coffee warmth")
    if "coke" in value.lower() or "seltzer" in value.lower():
        pieces.append("bright cold bubbles")
    if "slider" in value.lower() or "gyro" in value.lower() or "beef" in value.lower():
        pieces.append("something substantial enough to count, though perhaps not enough to carry the whole day")
    if "low protein" in value.lower() or "protein" in value.lower():
        pieces.append("Dr. Vellum noticing the protein gap without turning it into a scold")
    if pieces:
        return "; ".join(dict.fromkeys(pieces))
    return clean(value, 180)


def poetic_watch(text: Any) -> str:
    value = strip_raw_status(text)
    if re.search(r"\bstale\b|waiting for|sync lock|cached|fallback", value, re.IGNORECASE):
        return "the watch was quiet; the body would have to be believed without fresh numbers"
    m = re.search(r"Steps:\s*([\d,]+)", value, re.IGNORECASE) or re.search(r"([\d,]+)\s+steps", value, re.IGNORECASE)
    if m:
        return f"{m.group(1)} steps of ordinary ground covered"
    return clean(value or "body data quiet", 160)


def read(path: Path, limit: int | None = None) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[:limit] if limit else text


def read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows[-limit:] if limit else rows


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    row.setdefault("timestamp", now().isoformat(timespec="seconds"))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def load_config() -> dict[str, str]:
    cfg: dict[str, str] = {}
    if SECRETS_ENV.exists():
        for line in SECRETS_ENV.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                cfg[key.strip()] = value.strip().strip('"').strip("'")
    return cfg


def heartbeat_field(label: str) -> str:
    text = read(HEARTBEAT)
    patterns = [
        rf"\*\*{re.escape(label)}:\*\*\s*([^|\n]+)",
        rf"- \*\*{re.escape(label)}:\*\*\s*(.+)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            return clean(m.group(1), 320)
    return ""


def scene_summary(row: dict[str, Any]) -> dict[str, Any]:
    results = row.get("results") if isinstance(row.get("results"), dict) else {}
    image = results.get("image") if isinstance(results.get("image"), dict) else {}
    return {
        "scene_id": row.get("scene_id"),
        "recorded_at": row.get("recorded_at"),
        "title": clean(row.get("title"), 160),
        "mood": clean(row.get("mood"), 220),
        "text_opening": clean(str(row.get("text") or "").splitlines()[0] if row.get("text") else "", 260),
        "text_excerpt": clean(row.get("text"), 900),
        "delivery_ok": row.get("delivery_ok"),
        "image": image.get("gallery_path") or image.get("artifact_path"),
    }


def latest_matching_jsonl(path: Path, date_str: str, limit: int = 8) -> list[dict[str, Any]]:
    rows = []
    for row in read_jsonl(path):
        stamp = str(row.get("timestamp") or row.get("recorded_at") or row.get("source_timestamp") or "")
        if stamp.startswith(date_str):
            rows.append(row)
    return rows[-limit:]


def _candidate_key(candidate: tuple[float, Path, str, str]) -> str:
    return str(candidate[1].resolve())


def is_image_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}


def _take_newest(
    candidates: list[tuple[float, Path, str, str]],
    count: int,
    used: set[str],
) -> list[tuple[float, Path, str, str]]:
    picked: list[tuple[float, Path, str, str]] = []
    for candidate in sorted(candidates, reverse=True):
        key = _candidate_key(candidate)
        if key in used:
            continue
        picked.append(candidate)
        used.add(key)
        if len(picked) >= count:
            break
    return picked


def select_storybook_images(
    scene_candidates: list[tuple[float, Path, str, str]],
    hourly_candidates: list[tuple[float, Path, str, str]],
    other_candidates: list[tuple[float, Path, str, str]],
    limit: int,
) -> list[tuple[float, Path, str, str]]:
    """Prefer played scenes, but keep the ambient hourly witness in the daily page."""
    used: set[str] = set()
    selected: list[tuple[float, Path, str, str]] = []
    has_scene = bool(scene_candidates)
    has_hourly = bool(hourly_candidates)
    if has_scene and has_hourly:
        hourly_floor = min(len(hourly_candidates), max(2, limit // 3))
        scene_target = min(len(scene_candidates), max(1, limit - hourly_floor))
        selected.extend(_take_newest(scene_candidates, scene_target, used))
        selected.extend(_take_newest(hourly_candidates, min(hourly_floor, limit - len(selected)), used))
    elif has_scene:
        selected.extend(_take_newest(scene_candidates, limit, used))
    elif has_hourly:
        selected.extend(_take_newest(hourly_candidates, limit, used))

    if len(selected) < limit:
        selected.extend(_take_newest(other_candidates, limit - len(selected), used))
    if len(selected) < limit:
        selected.extend(_take_newest(scene_candidates + hourly_candidates, limit - len(selected), used))

    # Interleave gently: two play plates, one ambient/other plate, repeat. This
    # keeps the chapter led by play while preventing eight nearly identical
    # recent scene plates or eight hourly plates from swallowing the page.
    scenes = [item for item in selected if item[2] == "Scene Plate"]
    ambient = [item for item in selected if item[2] != "Scene Plate"]
    mixed: list[tuple[float, Path, str, str]] = []
    while scenes or ambient:
        for _ in range(2):
            if scenes:
                mixed.append(scenes.pop(0))
        if ambient:
            mixed.append(ambient.pop(0))
    return mixed[:limit]


def collect_images(date_str: str, scenes: list[dict[str, Any]], limit: int = 8) -> list[dict[str, str]]:
    scene_candidates: list[tuple[float, Path, str, str]] = []
    hourly_candidates: list[tuple[float, Path, str, str]] = []
    other_candidates: list[tuple[float, Path, str, str]] = []
    for scene in scenes:
        if scene.get("image"):
            path = Path(str(scene["image"]))
            if is_image_file(path):
                scene_candidates.append((path.stat().st_mtime, path, "Scene Plate", scene.get("title") or "A played scene"))
    for path in (LOGS / "drawthings-keepalive").glob(f"keepalive-{date_str.replace('-', '')}-*.png"):
        if is_image_file(path):
            hourly_candidates.append((path.stat().st_mtime, path, "Hourly Field-Journal Plate", path.stem))
    for pattern, label in (
        (BASE / "wallpapers" / f"{date_str}-*.png", "Wallpaper Illumination"),
        (BASE / "memory" / "npc-research" / "letter-images" / f"*{date_str}.png", "Letter Illumination"),
    ):
        for path in pattern.parent.glob(pattern.name):
            if is_image_file(path):
                other_candidates.append((path.stat().st_mtime, path, label, path.stem))
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    day_assets = ASSET_DIR / date_str
    day_assets.mkdir(parents=True, exist_ok=True)
    for _mtime, path, label, caption in select_storybook_images(scene_candidates, hourly_candidates, other_candidates, limit):
        resolved = str(path.resolve())
        if resolved in seen:
            continue
        seen.add(resolved)
        dest = day_assets / path.name
        if not dest.exists() or path.stat().st_mtime > dest.stat().st_mtime:
            shutil.copy2(path, dest)
        smart_caption = image_caption(path, label, caption)
        out.append({
            "source": resolved,
            "path": str(dest),
            "relative": os.path.relpath(dest, HTML_DIR),
            "label": label,
            "caption": smart_caption,
        })
        if len(out) >= limit:
            break
    return out


def image_caption(path: Path, label: str, fallback: str) -> str:
    sidecar = path.with_suffix(".json")
    if sidecar.exists():
        try:
            data = json.loads(sidecar.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            data = {}
        if isinstance(data, dict):
            caption = data.get("caption")
            title = data.get("title")
            if caption and title:
                return clean(f"{title}: {caption}", 220)
            if caption:
                return clean(str(caption), 220)
            selection = data.get("selection") if isinstance(data.get("selection"), dict) else {}
            if selection:
                sel_caption = selection.get("caption")
                sel_title = selection.get("title")
                if sel_caption and sel_title:
                    return clean(f"{sel_title}: {sel_caption}", 220)
                if sel_caption:
                    return clean(str(sel_caption), 220)
            subject = data.get("subject") or data.get("scene") or data.get("title")
            if subject:
                return clean(str(subject), 180)
            prompt = str(data.get("prompt") or "")
            if prompt:
                first = prompt.split(", illustrated", 1)[0].split(".")[0]
                first = re.sub(r"^(Character-focused field-journal portrait of\s*)", "", first, flags=re.I)
                return clean(first, 180)
    text = str(fallback or "").replace("_", " ").replace("-", " ")
    keepalive_m = re.search(r"keepalive[-\s]+(\d{8})[-\s]+(\d{6})", path.stem, flags=re.I)
    if keepalive_m:
        hour = int(keepalive_m.group(2)[:2])
        return legacy_hourly_caption(hour, path.stem)
    text = re.sub(r"\bkeepalive\s+\d{8}\s+\d{6}\b", "", text, flags=re.I).strip()
    if text:
        return clean(text, 160)
    if "hourly" in label.lower():
        return legacy_hourly_caption(12, path.stem)
    return "A saved illumination from the day's margins."


def caption_variant(key: str, variants: list[str]) -> str:
    if not variants:
        return ""
    digest = hashlib.sha1(key.encode("utf-8", errors="ignore")).hexdigest()
    return variants[int(digest[:8], 16) % len(variants)]


def legacy_hourly_caption(hour: int, key: str) -> str:
    if 5 <= hour < 9:
        variants = [
            "Morning margin light: the Academy waking before the day has explained itself.",
            "An early-hour plate, all pale wash and first evidence.",
            "The Book's morning eye catching one thing before the page grows busy.",
        ]
    elif 9 <= hour < 13:
        variants = [
            "Late-morning fieldwork: the margin bright enough for small details to confess.",
            "A daylight plate from the working part of the Book.",
            "The Academy under useful light, where ordinary evidence begins to sharpen.",
        ]
    elif 13 <= hour < 17:
        variants = [
            "Afternoon ink: the page holding steady while the day spends itself.",
            "A mid-day plate, caught between momentum and weariness.",
            "The Book's afternoon witness: not a climax, but a kept texture.",
        ]
    elif 17 <= hour < 21:
        variants = [
            "Evening margin weather: the day lowering its voice but not disappearing.",
            "A twilight plate from the hour when evidence starts becoming memory.",
            "The Book watching the day settle into lamplight.",
        ]
    else:
        variants = [
            "Night margin: a quiet plate kept for whatever the day could not finish aloud.",
            "An after-hours illumination from the Book's sleeping edge.",
            "The page awake after dark, holding one small image in trust.",
        ]
    return caption_variant(key, variants)


def collect_day(player: str, date_str: str) -> dict[str, Any]:
    scenes = [scene_summary(row) for row in read_jsonl(LOGS / "scene-ledger" / f"{date_str}.jsonl")]
    images = collect_images(date_str, scenes)
    guild_path = MEMORY / "support-faculty" / "guild" / f"{date_str}.md"
    diary = read(MEMORY / "diary" / f"{date_str}.md", 5000)
    dream = read(MEMORY / "dreams" / f"{date_str}.md", 2500)
    transcript = read(LOGS / "transcripts" / f"{date_str}.md", 3500)
    support_synthesis = latest_matching_jsonl(LOGS / "support-faculty" / "synthesis.jsonl", date_str, 3)
    ledger = latest_matching_jsonl(PLAYERS / f"{player}-ledger-log.jsonl", date_str, 4)
    mood = latest_matching_jsonl(PLAYERS / f"{player}-inkrest-log.jsonl", date_str, 12)
    vellum = latest_matching_jsonl(PLAYERS / f"{player}-vellum-log.jsonl", date_str, 4)
    simulations = latest_matching_jsonl(LOGS / "simulations" / f"{date_str}.jsonl", date_str, 8)
    actions = latest_matching_jsonl(LOGS / "npc-action-lifecycle.jsonl", date_str, 8)
    ripples = latest_matching_jsonl(LOGS / "bleed-ripples.jsonl", date_str, 8)
    anchors = latest_matching_jsonl(LOGS / "anchor-visits.jsonl", date_str, 5)
    outreach = latest_matching_jsonl(LOGS / "character-outreach.jsonl", date_str, 5)
    compass_history = read(PLAYERS / f"{player}-compass-runs.md", 3000)
    enchantment_log = latest_matching_jsonl(LOGS / "enchantments.jsonl", date_str, 5)
    relationship_weather = ""
    if _HAS_RELATIONSHIPS:
        try:
            relationship_weather = relationships.bleed_social_weather(player, limit=8)
        except Exception:
            relationship_weather = ""
    return {
        "player": player,
        "date": date_str,
        "heartbeat": {
            "focus": heartbeat_field("Focus"),
            "pacing": heartbeat_field("Pacing"),
            "fuel": heartbeat_field("Fuel"),
            "watch": heartbeat_field("Watch"),
            "location": heartbeat_field("Location"),
        },
        "scenes": scenes,
        "images": images,
        "diary": clean(diary, 1800),
        "dream": clean(dream, 900),
        "transcript_excerpt": clean(transcript, 1200),
        "support_guild": clean(read(guild_path, 3000), 3000),
        "support_synthesis": support_synthesis,
        "ledger": ledger,
        "mood": mood,
        "vellum": vellum,
        "simulations": simulations,
        "actions": actions,
        "bleed_ripples": ripples,
        "anchors": anchors,
        "outreach": outreach,
        "relationship_weather": relationship_weather[:2200],
        "compass_excerpt": clean(compass_history, 1200),
        "enchantments": enchantment_log,
    }


def storybook_relationship_sentence(raw: str) -> str:
    for line in (raw or "").splitlines():
        if "↔" not in line and ":" not in line:
            continue
        if line.startswith("RELATIONSHIP GRAPH") or line.startswith("Player-facing"):
            continue
        text = line.strip().strip("-").strip()
        text = re.sub(r"\s*[+-]?\d+\s*\([^)]+\)", "", text)
        text = re.sub(r"\s*\(\d+\)", "", text)
        text = re.sub(r":\s*[—-]\s*", ": ", text)
        text = re.sub(r"\s+", " ", text).strip()
        if "↔" in text:
            return f"{text} was one of the social threads pulling through the day."
        if text:
            return f"{text} remained part of the day's social weather."
    return "the social field stayed quiet, which is also a kind of weather."


def normalize_model(model: str) -> str:
    model = (model or "").strip()
    if model in {"openclaw", "default", "gateway", ""}:
        return "openclaw"
    return model


def gateway_cfg() -> tuple[int, str, str, int]:
    secrets = load_config()
    oc_cfg: dict[str, Any] = {}
    oc_path = Path.home() / ".openclaw" / "openclaw.json"
    if oc_path.exists():
        try:
            loaded = json.loads(oc_path.read_text(encoding="utf-8"))
            oc_cfg = loaded if isinstance(loaded, dict) else {}
        except Exception:
            oc_cfg = {}
    port = int(
        os.environ.get("OPENCLAW_GATEWAY_PORT")
        or secrets.get("OPENCLAW_GATEWAY_PORT")
        or oc_cfg.get("gateway", {}).get("port")
        or "18789"
    )
    token = (
        os.environ.get("OPENCLAW_GATEWAY_TOKEN")
        or secrets.get("OPENCLAW_GATEWAY_TOKEN")
        or oc_cfg.get("gateway", {}).get("auth", {}).get("token")
        or ""
    )
    model = normalize_model(os.environ.get("STORYBOOK_MODEL") or secrets.get("STORYBOOK_MODEL") or os.environ.get("BLEED_MODEL") or secrets.get("BLEED_MODEL") or "openclaw")
    try:
        timeout = max(60, int(os.environ.get("STORYBOOK_TIMEOUT") or secrets.get("STORYBOOK_TIMEOUT") or "240"))
    except ValueError:
        timeout = 240
    return port, token, model, timeout


def prompt_for(context: dict[str, Any]) -> str:
    return f"""Write today's Enchantify Storybook Page: The Book of You.

This is not a report and not a diary transcript. It is literary memory: BJ's
real day, Academy play, support faculty, ledger/fuel/mood signals, and world
movement braided into one readable chapter of an ongoing illustrated storybook.

Rules:
- Be specific to the data. Do not invent real-world events, completed tasks, or
  medical/financial conclusions.
- Never expose raw telemetry, JSON, cached/fallback notes, backticks, or calorie
  strings in the prose. Translate them into sensory story language.
- Mix real life and fictional play naturally, as Enchantify does.
- No guilt for missing data, low energy, not playing, money fog, food choices,
  mood, or body state.
- Do not create new plot events. Preserve and interpret what happened.
- Write in the Labyrinth's warm, strange, best-selling magical-school voice.
- Include a title that feels like a chapter title, not a log label.
- Include image plate captions for the available images. Captions can be poetic,
  but should be tied to the day's actual scenes/images.
- Make the first 70 percent read as a chapter, not a status digest. Structured
  facts belong in Margin Notes, still translated into voice.
- Use relationship_weather as social gravity: who is close, who is watching,
  which bonds or tensions shaped the day. Do not print raw scores.
- End with one sentence the Book remembers.

Use exactly this Markdown structure:

# The Book of You
## {context['date']} — [chapter title]

[600-1100 words of chapter prose]

### Illuminations
- Plate I — [caption]
- Plate II — [caption]

### Margin Notes
- Mood weather:
- Body weather:
- Ledger weather:
- Academy weather:
- Relationship weather:
- One thing the Book remembers:

### Open Threads
- Story:
- Real life:
- Support faculty:

Current data JSON:
{json.dumps(context, ensure_ascii=False, indent=2, default=str)[:26000]}
"""


def call_llm(context: dict[str, Any]) -> str:
    port, token, model, timeout = gateway_cfg()
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You write Enchantify's daily illustrated storybook chapter. "
                    "It is literary, specific, non-shaming, and grounded in supplied data. "
                    "Reply only with the requested Markdown artifact."
                ),
            },
            {"role": "user", "content": prompt_for(context)},
        ],
        "temperature": 0.78,
        "max_tokens": 2400,
        "stream": False,
    }
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "x-openclaw-session-key": f"storybook-{context['date']}-{int(time.time())}",
        },
        data=json.dumps(payload).encode("utf-8"),
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"Gateway returned HTTP {exc.code}: {body}") from exc
    except Exception as exc:
        raise RuntimeError(f"Gateway call failed: {exc}") from exc
    return result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()


def call_llm_for_month(context: dict[str, Any]) -> str:
    port, token, model, timeout = gateway_cfg()
    prompt = f"""Write the intro page for a monthly Book of You volume.

This is the frontispiece to a collected month of daily Enchantify Storybook
Pages. It should synthesize the month without inventing events.

Rules:
- Use only the supplied daily page summaries and titles.
- Name themes, highlights, recurring moods, support faculty patterns, Academy
  developments, and real-life texture when visible.
- No guilt about gaps or missing days. Missing pages are quiet margins, not
  failure.
- Write in Enchantify's literary, magical-archive style.
- Keep it concise enough to fit as an intro page.

Use exactly this Markdown structure:

# The Book of You
## {context['month_label']} — Monthly Volume

### Frontispiece
[350-700 words of monthly intro prose]

### Themes the Book Noticed
- ...

### Highlights
- ...

### Continuing Threads
- ...

### A Note from the Margin
[one closing sentence]

Monthly data JSON:
{json.dumps(context, ensure_ascii=False, indent=2, default=str)[:26000]}
"""
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You write Enchantify's monthly Book of You frontispiece. "
                    "It is specific, non-shaming, literary, and grounded in supplied data. "
                    "Reply only with the requested Markdown artifact."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.72,
        "max_tokens": 1800,
        "stream": False,
    }
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "x-openclaw-session-key": f"storybook-monthly-{context['month']}-{int(time.time())}",
        },
        data=json.dumps(payload).encode("utf-8"),
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"Gateway returned HTTP {exc.code}: {body}") from exc
    except Exception as exc:
        raise RuntimeError(f"Gateway call failed: {exc}") from exc
    return result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()


def fallback_chapter(context: dict[str, Any], reason: str = "") -> str:
    scenes = context.get("scenes") or []
    images = context.get("images") or []
    mood_words = [row.get("word") for row in context.get("mood", []) if row.get("word")]
    latest_mood = poetic_mood(mood_words[-1] if mood_words else "unwritten")
    fuel = poetic_fuel(context.get("heartbeat", {}).get("fuel") or "fuel not yet visible")
    watch = poetic_watch(context.get("heartbeat", {}).get("watch") or "body data quiet")
    rel_line = storybook_relationship_sentence(context.get("relationship_weather") or "")
    raw_scene_title = scenes[-1].get("title") if scenes else "the page that waited"
    scene_title = re.sub(r"^Latest delivered scene\s+\S+", "the latest saved scene", str(raw_scene_title or "")).strip() or "the page that waited"
    opening = scenes[-1].get("text_excerpt") if scenes else context.get("diary") or "The Book kept the day open without forcing it to explain itself."
    plate_lines = []
    for idx, image in enumerate(images[:6], start=1):
        roman = ["I", "II", "III", "IV", "V", "VI"][idx - 1]
        caption = clean(str(image.get("caption") or "a saved image from the day").replace("_", " "), 180).rstrip(".")
        label = clean(image.get("label", "Illumination"), 80)
        plate_lines.append(f"- Plate {roman} — *{label.lower()}: {caption}.*")
    if not plate_lines:
        plate_lines.append("- Plate I — No illumination was archived today; the margin leaves a space for what could not be pictured.")

    opening_sentence = clean(opening, 520)
    opening_sentence = opening_sentence.replace("`", "")
    lines = [
        "# The Book of You",
        f"## {context['date']} — The Page That Kept the Proof",
        "",
        "The Book opened to an ordinary page and found it already marked.",
        "",
        f"The body weather was {latest_mood}. The ledger of the body did not arrive as a verdict; it arrived as paper grain: {fuel}. The watch, when it spoke, said only this much: {watch}. That was enough for the page to know where to put the first wash of color.",
        "",
        f"The Academy's strongest saved scene was {scene_title}. Its edge remained in the room like a bookmark: {opening_sentence}",
        "",
        "Around that scene, the support faculty made their quieter notes. Dr. Vellum looked for the body's smallest honest hinge. Dr. Inkrest treated the mood word as weather, not identity. Gimble read the ledger as motion rather than morality. Together they did not solve BJ; they kept BJ legible.",
        "",
        "The Book does not need every hour to become dramatic. It needs proof that a life was touched, noticed, and carried forward. Today, the proof was enough: a scene held its place, images gathered in the margin, and the page stayed warm where tomorrow could begin.",
        "",
        "### Illuminations",
        *plate_lines,
        "",
        "### Margin Notes",
        f"- Mood weather: {latest_mood}",
        f"- Body weather: {fuel}",
        "- Ledger weather: see Gimble's latest cross-read in the support faculty records.",
        "- Academy weather: the scene ledger held the day's playable proof.",
        f"- Relationship weather: {clean(rel_line, 180)}",
        "- One thing the Book remembers: care becomes real when it leaves a trace.",
        "",
        "### Open Threads",
        "- Story: carry forward the latest scene anchor before adding new pressure.",
        "- Real life: let the next page begin with one true detail.",
        "- Support faculty: keep using one-word mood, fuel, and ledger visibility as kindness, not homework.",
    ]
    if reason:
        lines.append(f"\n<!-- fallback: {clean(reason, 300)} -->")
    return "\n".join(lines) + "\n"


def parse_month(month: str | None = None) -> tuple[int, int, str, str]:
    raw = (month or today()[:7]).strip()
    m = re.fullmatch(r"(\d{4})-(\d{2})", raw)
    if not m:
        raise SystemExit("Month must be YYYY-MM")
    year = int(m.group(1))
    month_num = int(m.group(2))
    if not (1 <= month_num <= 12):
        raise SystemExit("Month must be YYYY-MM")
    month_key = f"{year:04d}-{month_num:02d}"
    month_label = f"{calendar.month_name[month_num]} {year}"
    return year, month_num, month_key, month_label


def daily_title(markdown: str, date_str: str) -> str:
    m = re.search(rf"^##\s+{re.escape(date_str)}\s+[—-]\s+(.+)$", markdown, re.MULTILINE)
    if m:
        return clean(m.group(1), 160)
    m = re.search(r"^##\s+(.+)$", markdown, re.MULTILINE)
    return clean(m.group(1), 160) if m else "Untitled Page"


def daily_digest(markdown: str, date_str: str) -> dict[str, Any]:
    def section(name: str, limit: int = 700) -> str:
        m = re.search(rf"^### {re.escape(name)}\s*(.*?)(?=^### |\Z)", markdown, re.DOTALL | re.MULTILINE)
        return clean(m.group(1), limit) if m else ""

    paragraphs = [
        clean(line, 500)
        for line in markdown.splitlines()
        if line.strip()
        and not line.startswith("#")
        and not line.startswith("- ")
        and not line.startswith("<!--")
    ]
    return {
        "date": date_str,
        "title": daily_title(markdown, date_str),
        "opening": paragraphs[0] if paragraphs else "",
        "margin_notes": section("Margin Notes", 900),
        "open_threads": section("Open Threads", 700),
        "illuminations": section("Illuminations", 700),
    }


def collect_month(player: str, month: str | None = None) -> dict[str, Any]:
    year, month_num, month_key, month_label = parse_month(month)
    _last_day = calendar.monthrange(year, month_num)[1]
    pages = []
    for path in sorted(DAILY_DIR.glob(f"{month_key}-*.md")):
        date_str = path.stem
        markdown = read(path)
        if not markdown.strip():
            continue
        pages.append({
            "date": date_str,
            "path": str(path),
            "markdown": markdown,
            "digest": daily_digest(markdown, date_str),
        })
    return {
        "player": player,
        "month": month_key,
        "month_label": month_label,
        "page_count": len(pages),
        "expected_days": _last_day,
        "pages": pages,
        "digests": [p["digest"] for p in pages],
        "generated_at": now().isoformat(timespec="seconds"),
    }


def fallback_month_intro(context: dict[str, Any], reason: str = "") -> str:
    pages = context.get("digests") or []
    titles = [p.get("title") for p in pages if p.get("title")]
    latest = pages[-1] if pages else {}
    lines = [
        "# The Book of You",
        f"## {context['month_label']} — Monthly Volume",
        "",
        "### Frontispiece",
        f"This month left {context.get('page_count', 0)} daily page(s) in the Book. The volume does not pretend every day was complete, dramatic, or tidy. It gathers the evidence that did arrive: scenes, margins, support notes, images, body weather, ledger weather, and the small acts by which ordinary life became readable again.",
        "",
        "The recurring shape was proof rather than performance. The Book noticed the places where attention landed and kept them, even when the page was quiet. The result is not a perfect record. It is a shelf of lived pages: enough continuity for the next month to inherit.",
        "",
        "### Themes the Book Noticed",
        "- Attention became an artifact whenever the day left a written trace.",
        "- Support worked best when it lowered friction instead of adding homework.",
        "- The Academy felt most alive when real life and fiction braided instead of competing.",
        "",
        "### Highlights",
    ]
    if titles:
        for title in titles[:10]:
            lines.append(f"- {title}")
    else:
        lines.append("- No daily pages were filed for this month yet.")
    lines.extend([
        "",
        "### Continuing Threads",
        f"- Latest page: {latest.get('date', 'none')} — {latest.get('title', 'no title')}",
        "- Next month should begin with one true detail, not a burden to catch up.",
        "",
        "### A Note from the Margin",
        "The month counted because the Book kept what it could and forgave the rest.",
    ])
    if reason:
        lines.append(f"\n<!-- fallback: {clean(reason, 300)} -->")
    return "\n".join(lines) + "\n"


def title_from_markdown(markdown: str, date_str: str) -> str:
    m = re.search(rf"^##\s+{re.escape(date_str)}\s+[—-]\s+(.+)$", markdown, re.MULTILINE)
    return clean(m.group(1), 120) if m else "The Page That Kept the Proof"


def markdown_to_html(markdown: str, images: list[dict[str, str]], date_str: str) -> str:
    title = title_from_markdown(markdown, date_str)
    body: list[str] = []
    in_list = False
    first_image = images[0] if images else None
    first_rel = html.escape(first_image["relative"]) if first_image else ""
    first_caption = html.escape(first_image.get("caption") or "A saved illumination") if first_image else ""
    first_label = html.escape(first_image.get("label") or "Illumination") if first_image else ""
    hero = ""
    if first_image:
        hero = f'''<figure class="hero-plate"><img src="{first_rel}" alt="{first_caption}"><figcaption><span>{first_label}</span>{first_caption}</figcaption></figure>'''
    hero_inserted = False
    for raw in markdown.splitlines():
        line = raw.rstrip()
        if not line:
            if in_list:
                body.append("</ul>")
                in_list = False
            continue
        if line.startswith("# "):
            if in_list:
                body.append("</ul>")
                in_list = False
            body.append(f"<h1>{html.escape(line[2:].strip())}</h1>")
        elif line.startswith("## "):
            if in_list:
                body.append("</ul>")
                in_list = False
            body.append(f"<h2>{html.escape(line[3:].strip())}</h2>")
            if hero and not hero_inserted:
                body.append(hero)
                body.append('<aside class="marginalia">attention became evidence; evidence became story</aside>')
                hero_inserted = True
        elif line.startswith("### "):
            if in_list:
                body.append("</ul>")
                in_list = False
            body.append(f"<h3>{html.escape(line[4:].strip())}</h3>")
            if line[4:].strip().lower() == "illuminations" and images:
                body.append('<div class="plates">')
                for idx, image in enumerate(images[1:9] if first_image else images[:8], start=1):
                    rel = html.escape(image["relative"])
                    caption = html.escape(image.get("caption") or f"Plate {idx}")
                    label = html.escape(image.get("label") or "Illumination")
                    body.append(f'<figure><img src="{rel}" alt="{caption}"><figcaption><span>{label}</span>{caption}</figcaption></figure>')
                body.append("</div>")
        elif line.startswith("- "):
            if not in_list:
                body.append("<ul>")
                in_list = True
            body.append(f"<li>{html.escape(line[2:].strip())}</li>")
        elif line.startswith("<!--"):
            continue
        else:
            if in_list:
                body.append("</ul>")
                in_list = False
            body.append(f"<p>{html.escape(line)}</p>")
    if in_list:
        body.append("</ul>")
    css = """
    :root { color-scheme: light; }
    body {
      margin: 0;
      background: #151712;
      color: #2d241b;
      font-family: Georgia, 'Times New Roman', serif;
      line-height: 1.62;
    }
    .page {
      max-width: 940px;
      margin: 32px auto;
      padding: 42px min(6vw, 66px) 56px;
      background:
        repeating-linear-gradient(90deg, rgba(82,58,35,.035) 0 1px, transparent 1px 32px),
        repeating-linear-gradient(0deg, rgba(82,58,35,.03) 0 1px, transparent 1px 34px),
        radial-gradient(circle at 12% 8%, rgba(110, 77, 34, .14), transparent 25%),
        radial-gradient(circle at 88% 18%, rgba(18, 77, 75, .13), transparent 22%),
        linear-gradient(90deg, rgba(86,54,24,.10), transparent 12%, transparent 88%, rgba(86,54,24,.10)),
        #eadcc4;
      box-shadow: 0 20px 80px rgba(0,0,0,.45);
      border: 1px solid rgba(58, 40, 23, .35);
      position: relative;
      overflow: hidden;
    }
    .page:before {
      content: "";
      position: absolute;
      inset: 18px;
      border: 1px solid rgba(63, 44, 27, .22);
      pointer-events: none;
    }
    .page:after {
      content: "FIELD JOURNAL";
      position: absolute;
      top: 28px;
      right: -38px;
      transform: rotate(7deg);
      color: rgba(112,65,47,.32);
      border: 1px solid rgba(112,65,47,.32);
      padding: .35rem 2.8rem;
      font-size: .72rem;
      letter-spacing: .18em;
      text-transform: uppercase;
    }
    .ribbon {
      position: absolute;
      left: 38px;
      top: 0;
      width: 46px;
      height: 124px;
      background: #25423c;
      box-shadow: inset 0 0 0 1px rgba(255,248,231,.2), 0 7px 18px rgba(0,0,0,.16);
    }
    .ribbon:after {
      content: "";
      position: absolute;
      bottom: -18px;
      left: 0;
      border-left: 23px solid transparent;
      border-right: 23px solid transparent;
      border-top: 18px solid #25423c;
    }
    .ribbon span {
      position: absolute;
      left: 50%;
      top: 52px;
      transform: translateX(-50%);
      color: #d7c28c;
      font-size: 1.25rem;
    }
    .folio-date {
      text-align: center;
      color: #70412f;
      font-size: .76rem;
      letter-spacing: .14em;
      text-transform: uppercase;
      margin-bottom: .45rem;
    }
    .hero-plate {
      width: min(360px, 42%);
      float: right;
      margin: .15rem 0 1rem 1.35rem;
      background: rgba(255,248,231,.54);
      border: 1px solid rgba(64,44,28,.28);
      padding: 10px;
      box-shadow: 0 10px 28px rgba(65,43,20,.14);
      transform: rotate(.45deg);
    }
    .hero-plate img { width: 100%; display: block; border: 1px solid rgba(45,36,27,.22); }
    .hero-plate figcaption { font-size: .82rem; }
    .marginalia {
      float: left;
      width: 150px;
      margin: .2rem 1.1rem .8rem -1.1rem;
      padding: .7rem .8rem;
      border-left: 2px solid rgba(49,83,76,.38);
      color: #31534c;
      font-size: .84rem;
      font-style: italic;
      transform: rotate(-.7deg);
      background: rgba(255,248,231,.23);
    }
    .botanical {
      position: absolute;
      right: 32px;
      bottom: 58px;
      width: 108px;
      height: 170px;
      opacity: .32;
      pointer-events: none;
    }
    .botanical:before {
      content: "";
      position: absolute;
      left: 48px;
      bottom: 0;
      width: 1px;
      height: 155px;
      background: #31534c;
      transform: rotate(-8deg);
    }
    .botanical i {
      position: absolute;
      width: 42px;
      height: 18px;
      border: 1px solid #31534c;
      border-radius: 100% 0 100% 0;
      transform: rotate(var(--r));
    }
    .botanical i:nth-child(1) { left: 18px; bottom: 94px; --r: 18deg; }
    .botanical i:nth-child(2) { left: 50px; bottom: 122px; --r: -28deg; }
    .botanical i:nth-child(3) { left: 16px; bottom: 44px; --r: 28deg; }
    .botanical i:nth-child(4) { left: 54px; bottom: 68px; --r: -18deg; }
    h1, h2, h3 { font-weight: 500; text-align: center; letter-spacing: .04em; }
    h1 { font-size: 2.45rem; margin: 1.55rem 0 .2rem; color: #2b2118; }
    h2 { font-size: 1.5rem; margin: 0 0 1.7rem; color: #473421; }
    h3 { margin-top: 2.4rem; padding-top: .8rem; border-top: 1px solid rgba(71,52,33,.25); color: #31534c; }
    p { font-size: 1.08rem; margin: 1.05rem 0; }
    ul { padding-left: 1.4rem; }
    li { margin: .45rem 0; }
    .plates {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 18px;
      margin: 1.4rem 0 2rem;
    }
    figure {
      margin: 0;
      background: rgba(255, 248, 231, .45);
      border: 1px solid rgba(64,44,28,.24);
      padding: 10px;
      box-shadow: 0 8px 24px rgba(65, 43, 20, .12);
      transform: rotate(var(--tilt, -.25deg));
    }
    figure:nth-child(even) { --tilt: .35deg; }
    img { width: 100%; display: block; border: 1px solid rgba(45,36,27,.22); }
    figcaption {
      font-size: .9rem;
      color: #5d4a35;
      margin-top: .65rem;
      font-style: italic;
    }
    figcaption span {
      display: block;
      color: #31534c;
      font-style: normal;
      font-size: .76rem;
      letter-spacing: .08em;
      text-transform: uppercase;
      margin-bottom: .15rem;
    }
    .stamp {
      text-align: center;
      color: #70412f;
      margin-top: 2rem;
      font-size: .85rem;
      letter-spacing: .12em;
      text-transform: uppercase;
    }
    """
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(date_str)} — {html.escape(title)}</title>
  <style>{css}</style>
</head>
<body>
  <main class="page">
    <div class="ribbon"><span>✦</span></div>
    <div class="folio-date">{html.escape(date_str)} · The Book Kept the Proof</div>
    {''.join(body)}
    <div class="botanical"><i></i><i></i><i></i><i></i></div>
    <div class="stamp">Filed in The Book of You · {html.escape(date_str)}</div>
  </main>
</body>
</html>
"""


def markdown_body_to_html(markdown: str) -> str:
    body: list[str] = []
    in_list = False
    for raw in markdown.splitlines():
        line = raw.rstrip()
        if not line:
            if in_list:
                body.append("</ul>")
                in_list = False
            continue
        if line.startswith("<!--"):
            continue
        if line.startswith("# "):
            if in_list:
                body.append("</ul>")
                in_list = False
            body.append(f"<h1>{html.escape(line[2:].strip())}</h1>")
        elif line.startswith("## "):
            if in_list:
                body.append("</ul>")
                in_list = False
            body.append(f"<h2>{html.escape(line[3:].strip())}</h2>")
        elif line.startswith("### "):
            if in_list:
                body.append("</ul>")
                in_list = False
            body.append(f"<h3>{html.escape(line[4:].strip())}</h3>")
        elif line.startswith("- "):
            if not in_list:
                body.append("<ul>")
                in_list = True
            body.append(f"<li>{html.escape(line[2:].strip())}</li>")
        else:
            if in_list:
                body.append("</ul>")
                in_list = False
            body.append(f"<p>{html.escape(line)}</p>")
    if in_list:
        body.append("</ul>")
    return "".join(body)


def monthly_to_html(intro: str, pages: list[dict[str, Any]], context: dict[str, Any]) -> str:
    sections = [f'<section class="intro">{markdown_body_to_html(intro)}</section>']
    for page in pages:
        date_str = page["date"]
        markdown = str(page.get("markdown") or "")
        sections.append(
            f'<section class="daily-page"><div class="date-tab">{html.escape(date_str)}</div>'
            f'{markdown_body_to_html(markdown)}</section>'
        )
    css = """
    :root { color-scheme: light; }
    body {
      margin: 0;
      background: #151712;
      color: #2d241b;
      font-family: Georgia, 'Times New Roman', serif;
      line-height: 1.62;
    }
    .volume {
      max-width: 900px;
      margin: 32px auto;
    }
    section {
      page-break-after: always;
      margin: 0 0 34px;
      padding: 54px min(7vw, 76px);
      background:
        repeating-linear-gradient(90deg, rgba(82,58,35,.032) 0 1px, transparent 1px 32px),
        repeating-linear-gradient(0deg, rgba(82,58,35,.028) 0 1px, transparent 1px 34px),
        radial-gradient(circle at 12% 8%, rgba(110, 77, 34, .14), transparent 25%),
        radial-gradient(circle at 88% 18%, rgba(18, 77, 75, .13), transparent 22%),
        linear-gradient(90deg, rgba(86,54,24,.10), transparent 12%, transparent 88%, rgba(86,54,24,.10)),
        #eadcc4;
      box-shadow: 0 20px 80px rgba(0,0,0,.45);
      border: 1px solid rgba(58, 40, 23, .35);
      position: relative;
      min-height: 780px;
      overflow: hidden;
    }
    section:before {
      content: "";
      position: absolute;
      inset: 18px;
      border: 1px solid rgba(63, 44, 27, .22);
      pointer-events: none;
    }
    section:after {
      content: "ARCHIVE COPY";
      position: absolute;
      right: -34px;
      top: 26px;
      transform: rotate(7deg);
      color: rgba(112,65,47,.28);
      border: 1px solid rgba(112,65,47,.30);
      padding: .35rem 2.55rem;
      font-size: .7rem;
      letter-spacing: .18em;
      text-transform: uppercase;
    }
    h1, h2, h3 { font-weight: 500; text-align: center; letter-spacing: .04em; }
    h1 { font-size: 2.35rem; margin: 1.1rem 0 .2rem; color: #2b2118; }
    h2 { font-size: 1.48rem; margin: 0 0 2rem; color: #473421; }
    h3 { margin-top: 2rem; padding-top: .8rem; border-top: 1px solid rgba(71,52,33,.25); color: #31534c; }
    p { font-size: 1.05rem; margin: 1rem 0; }
    ul { padding-left: 1.35rem; }
    li { margin: .42rem 0; }
    .date-tab {
      position: absolute;
      right: 34px;
      top: 28px;
      color: #70412f;
      font-size: .78rem;
      letter-spacing: .12em;
      text-transform: uppercase;
    }
    .date-tab:before {
      content: "✦ ";
      color: #31534c;
    }
    .stamp {
      text-align: center;
      color: #70412f;
      margin: 2rem 0 3rem;
      font-size: .85rem;
      letter-spacing: .12em;
      text-transform: uppercase;
    }
    """
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(context['month_label'])} — The Book of You</title>
  <style>{css}</style>
</head>
<body>
  <main class="volume">
    {''.join(sections)}
    <div class="stamp">Filed in The Book of You · {html.escape(context['month_label'])}</div>
  </main>
</body>
</html>
"""


def write_outputs(markdown: str, context: dict[str, Any], *, dry_run: bool = False) -> dict[str, str]:
    date_str = context["date"]
    md_path = DAILY_DIR / f"{date_str}.md"
    html_path = HTML_DIR / f"{date_str}.html"
    pdf_path = PDF_DIR / f"{date_str}.pdf"
    rendered = markdown_to_html(markdown, context.get("images", []), date_str)
    if not dry_run:
        md_path.write_text(markdown, encoding="utf-8")
        html_path.write_text(rendered, encoding="utf-8")
        if pdf_path.exists():
            pdf_path.unlink()
        pdf_ok, pdf_detail = maybe_pdf(html_path, pdf_path)
        update_index(date_str, title_from_markdown(markdown, date_str), md_path, html_path, pdf_path if pdf_path.exists() else None)
    else:
        pdf_ok, pdf_detail = False, "dry-run did not render PDF"
    return {
        "markdown": str(md_path),
        "html": str(html_path),
        "pdf": str(pdf_path) if pdf_path.exists() else "",
        "pdf_detail": pdf_detail,
    }


def write_monthly_outputs(intro: str, context: dict[str, Any], *, dry_run: bool = False) -> dict[str, str]:
    month_key = context["month"]
    md_path = MONTHLY_DIR / f"{month_key}.md"
    html_path = MONTHLY_HTML_DIR / f"{month_key}.html"
    pdf_path = MONTHLY_PDF_DIR / f"{month_key}.pdf"
    pages = context.get("pages") or []
    combined = [intro.rstrip(), ""]
    for page in pages:
        combined.extend([
            f"\n---\n",
            str(page.get("markdown") or "").strip(),
            "",
        ])
    markdown = "\n".join(combined).rstrip() + "\n"
    rendered = monthly_to_html(intro, pages, context)
    if not dry_run:
        md_path.write_text(markdown, encoding="utf-8")
        html_path.write_text(rendered, encoding="utf-8")
        if pdf_path.exists():
            pdf_path.unlink()
        pdf_ok, pdf_detail = maybe_pdf(html_path, pdf_path)
    else:
        pdf_ok, pdf_detail = False, "dry-run did not render PDF"
    return {
        "markdown": str(md_path),
        "html": str(html_path),
        "pdf": str(pdf_path) if pdf_path.exists() else "",
        "pdf_detail": pdf_detail,
        "page_count": str(len(pages)),
    }


def maybe_pdf(html_path: Path, pdf_path: Path) -> tuple[bool, str]:
    tool = shutil.which("wkhtmltopdf")
    if tool:
        proc = subprocess.run([tool, "--quiet", str(html_path), str(pdf_path)], cwd=BASE, capture_output=True, text=True, timeout=120)
        if proc.returncode == 0 and pdf_path.exists():
            return True, f"wkhtmltopdf rendered {pdf_path}"
        return False, clean(proc.stderr or proc.stdout or "wkhtmltopdf failed", 500)

    chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    if chrome.exists():
        proc = subprocess.run(
            [
                str(chrome),
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                f"--print-to-pdf={pdf_path}",
                html_path.resolve().as_uri(),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode == 0 and pdf_path.exists():
            return True, f"Google Chrome headless rendered {pdf_path}"
        detail = proc.stderr or proc.stdout or "Google Chrome headless PDF render failed"
        return False, clean(detail, 500)

    cups = shutil.which("cupsfilter")
    if cups:
        proc = subprocess.run(
            [cups, "-m", "application/pdf", str(html_path)],
            cwd=BASE,
            capture_output=True,
            timeout=120,
        )
        if proc.returncode == 0 and proc.stdout:
            pdf_path.write_bytes(proc.stdout)
            return True, f"cupsfilter rendered {pdf_path}"
        detail = (proc.stderr or proc.stdout or b"cupsfilter failed").decode("utf-8", errors="replace")
        return False, clean(detail, 500)

    return False, "No PDF renderer found. Install wkhtmltopdf or keep macOS cupsfilter available."


def telegram_send(message: str, media: Path | None = None, *, dry_run: bool = False, silent: bool = False) -> int:
    if dry_run:
        print(message)
        if media:
            print(f"[dry-run media] {media}")
        return 0
    args = [
        "openclaw", "message", "send",
        "--target", "8729557865",
        "--channel", "telegram",
        "--account", "enchantify",
        "--message", message,
    ]
    if media:
        args += ["--media", str(media), "--force-document"]
    if silent:
        args.append("--silent")
    proc = subprocess.run(args, cwd=BASE, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        append_jsonl(LOGS / "storybook-send-errors.jsonl", {
            "kind": "telegram_send_error",
            "stderr": clean(proc.stderr or proc.stdout, 1500),
            "media": str(media) if media else "",
        })
    return proc.returncode


def update_index(date_str: str, title: str, md_path: Path, html_path: Path, pdf_path: Path | None) -> None:
    existing = read(INDEX)
    line = f"- {date_str} — [{title}]({html_path.relative_to(STORYBOOK)})"
    if pdf_path:
        line += f" · [PDF]({pdf_path.relative_to(STORYBOOK)})"
    line += f" · [Markdown]({md_path.relative_to(STORYBOOK)})"
    lines = [l for l in existing.splitlines() if not l.startswith(f"- {date_str} — ")]
    if not lines:
        lines = ["# The Book of You", "", "An illustrated storybook of the player's Enchantified life.", ""]
    lines.append(line)
    header = lines[:4]
    entries = sorted(lines[4:], reverse=True)
    INDEX.write_text("\n".join(header + entries).rstrip() + "\n", encoding="utf-8")


def storybook_message(date_str: str, title: str, outputs: dict[str, str]) -> str:
    lines = [
        f"The Book of You — {date_str}",
        title,
        "",
        "Today's illustrated storybook page has been filed.",
    ]
    if outputs.get("pdf"):
        lines.append("PDF attached.")
    else:
        lines.append(f"PDF not attached: {outputs.get('pdf_detail') or 'renderer unavailable'}.")
        lines.append(f"HTML: {Path(outputs['html']).name}")
    return "\n".join(lines)


def monthly_message(context: dict[str, Any], outputs: dict[str, str]) -> str:
    lines = [
        f"The Book of You — {context['month_label']}",
        "Monthly Volume",
        "",
        f"{context.get('page_count', 0)} daily page(s) gathered with an intro frontispiece.",
    ]
    if outputs.get("pdf"):
        lines.append("Monthly PDF attached.")
    else:
        lines.append(f"PDF not attached: {outputs.get('pdf_detail') or 'renderer unavailable'}.")
        lines.append(f"HTML: {Path(outputs['html']).name}")
    return "\n".join(lines)


def run_daily(player: str, date_str: str, *, dry_run: bool = False, no_llm: bool = False, send: bool = False, silent: bool = False) -> int:
    ensure_dirs()
    context = collect_day(player, date_str)
    llm_error = ""
    if no_llm:
        markdown = fallback_chapter(context, "LLM disabled")
    else:
        try:
            markdown = call_llm(context)
            if "# The Book of You" not in markdown:
                raise RuntimeError("model returned malformed storybook page")
        except Exception as exc:
            llm_error = str(exc)
            markdown = fallback_chapter(context, llm_error)
    outputs = write_outputs(markdown, context, dry_run=dry_run)
    title = title_from_markdown(markdown, date_str)
    if dry_run:
        print(markdown)
        print(json.dumps(outputs, indent=2))
    else:
        append_jsonl(STORYBOOK_LOG, {
            "kind": "storybook_daily",
            "player": player,
            "date": date_str,
            "title": title,
            "outputs": outputs,
            "image_count": len(context.get("images", [])),
            "scene_count": len(context.get("scenes", [])),
            "llm_error": llm_error,
        })
        if send:
            media = Path(outputs["pdf"]) if outputs.get("pdf") else Path(outputs["html"])
            rc = telegram_send(storybook_message(date_str, title, outputs), media if media.exists() else None, silent=silent)
            append_jsonl(STORYBOOK_LOG, {
                "kind": "storybook_delivery",
                "player": player,
                "date": date_str,
                "title": title,
                "sent": rc == 0,
                "media": str(media) if media.exists() else "",
            })
            if rc != 0:
                return rc
        print(outputs["html"])
        if outputs.get("pdf"):
            print(outputs["pdf"])
    return 0


def run_monthly(player: str, month: str | None, *, dry_run: bool = False, no_llm: bool = False, send: bool = False, silent: bool = False) -> int:
    ensure_dirs()
    context = collect_month(player, month)
    llm_error = ""
    if not context.get("pages"):
        print(f"No daily Book of You pages found for {context['month']}.")
        return 0
    if no_llm:
        intro = fallback_month_intro(context, "LLM disabled")
    else:
        try:
            intro = call_llm_for_month(context)
            if "# The Book of You" not in intro:
                raise RuntimeError("model returned malformed monthly intro")
        except Exception as exc:
            llm_error = str(exc)
            intro = fallback_month_intro(context, llm_error)
    outputs = write_monthly_outputs(intro, context, dry_run=dry_run)
    if dry_run:
        print(intro)
        print(json.dumps(outputs, indent=2))
    else:
        append_jsonl(STORYBOOK_LOG, {
            "kind": "storybook_monthly",
            "player": player,
            "month": context["month"],
            "month_label": context["month_label"],
            "page_count": context.get("page_count", 0),
            "outputs": outputs,
            "llm_error": llm_error,
        })
        if send:
            media = Path(outputs["pdf"]) if outputs.get("pdf") else Path(outputs["html"])
            rc = telegram_send(monthly_message(context, outputs), media if media.exists() else None, silent=silent)
            append_jsonl(STORYBOOK_LOG, {
                "kind": "storybook_monthly_delivery",
                "player": player,
                "month": context["month"],
                "sent": rc == 0,
                "media": str(media) if media.exists() else "",
            })
            if rc != 0:
                return rc
        print(outputs["html"])
        if outputs.get("pdf"):
            print(outputs["pdf"])
    return 0


def status() -> int:
    ensure_dirs()
    entries = sorted(DAILY_DIR.glob("*.md"), reverse=True)[:10]
    print("STORYBOOK STATUS")
    print(f"Daily: {DAILY_DIR}")
    print(f"HTML: {HTML_DIR}")
    print(f"PDF: {PDF_DIR}")
    print(f"Index: {INDEX}")
    for path in entries:
        print(f"- {path.name}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate The Book of You daily storybook artifact")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("daily", help="Generate one daily storybook chapter")
    p.add_argument("player", nargs="?", default="bj")
    p.add_argument("--date", default=today())
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-llm", action="store_true")
    p.add_argument("--send", action="store_true", help="Send the PDF through Telegram; if PDF rendering fails, send the HTML artifact as a document.")
    p.add_argument("--silent", action="store_true")

    m = sub.add_parser("monthly", help="Collect daily pages into one monthly Book of You volume")
    m.add_argument("player", nargs="?", default="bj")
    m.add_argument("--month", default=today()[:7], help="Month to collect, YYYY-MM")
    m.add_argument("--dry-run", action="store_true")
    m.add_argument("--no-llm", action="store_true")
    m.add_argument("--send", action="store_true", help="Send the monthly PDF through Telegram; if PDF rendering fails, send the HTML artifact as a document.")
    m.add_argument("--silent", action="store_true")

    sub.add_parser("status", help="Show storybook status")

    args = parser.parse_args()
    with cron_steward.run(f"storybook:{args.command}"):
        if args.command == "daily":
            return run_daily(args.player, args.date, dry_run=args.dry_run, no_llm=args.no_llm, send=args.send, silent=args.silent)
        if args.command == "monthly":
            return run_monthly(args.player, args.month, dry_run=args.dry_run, no_llm=args.no_llm, send=args.send, silent=args.silent)
        if args.command == "status":
            return status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

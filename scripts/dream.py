#!/usr/bin/env python3
"""
dream.py — The Labyrinth's Overnight Dream Generator.
Runs nightly via cron (suggested: 2am). Reads recent context and generates
a short, surreal dream fragment in the Labyrinth's voice.

The Labyrinth is a sentient book. It dreams the way old books dream:
in symbols, ink, recurring images, the weight of unfinished stories.

Cron:     0 2 * * * python3 /path/to/scripts/dream.py >> logs/dream.log 2>&1
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
WORKSPACE_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
import cron_steward


def load_config() -> dict:
    cfg = {}
    # Load from config/secrets.env (new system)
    secrets_path = WORKSPACE_DIR / "config" / "secrets.env"
    if secrets_path.exists():
        with open(secrets_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                cfg[key.strip()] = val.strip().strip('"').strip("'")
    # Also check old enchantify-config.sh as fallback
    old_config = SCRIPT_DIR / "enchantify-config.sh"
    if old_config.exists():
        with open(old_config) as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                if key.strip() not in cfg:
                    cfg[key.strip()] = val.strip().strip('"')
    return cfg


def read_file_safe(path: Path, limit_lines: int = 40) -> str:
    if not path.exists():
        return ""
    with open(path) as f:
        lines = f.readlines()
    return "".join(lines[:limit_lines]).strip()


def get_api_key(cfg: dict):
    return (
        cfg.get("ENCHANTIFY_ANTHROPIC_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
        or None
    )


def _normalize_gateway_model(model: str) -> str:
    model = (model or "").strip()
    if model == "openclaw" or model.startswith("openclaw/"):
        return model
    return "openclaw"


def _oc_gateway_cfg(cfg: dict) -> tuple[int, str, str, int]:
    oc_path = Path.home() / ".openclaw" / "openclaw.json"
    oc_cfg: dict = {}
    if oc_path.exists():
        try:
            oc_cfg = json.loads(oc_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    port = oc_cfg.get("gateway", {}).get("port", 18789)
    token = oc_cfg.get("gateway", {}).get("auth", {}).get("token", "")
    raw_model = (
        os.environ.get("DREAM_MODEL")
        or cfg.get("DREAM_MODEL")
        or os.environ.get("BLEED_MODEL")
        or cfg.get("BLEED_MODEL")
        or "openclaw"
    )
    timeout_raw = (
        os.environ.get("DREAM_TIMEOUT")
        or cfg.get("DREAM_TIMEOUT")
        or "90"
    )
    try:
        timeout = min(180, max(20, int(timeout_raw)))
    except ValueError:
        timeout = 90
    return int(port), token, _normalize_gateway_model(raw_model), timeout


def build_context(cfg: dict, today: datetime | None = None) -> str:
    today = today or datetime.now()
    yesterday = today - timedelta(days=1)

    heartbeat_path = WORKSPACE_DIR / "HEARTBEAT.md"  # enchantify-internal heartbeat
    heartbeat = read_file_safe(heartbeat_path, 60)

    arc = read_file_safe(WORKSPACE_DIR / "lore" / "current-arc.md")
    labyrinth_state = read_file_safe(WORKSPACE_DIR / "memory" / "labyrinth-state.md")

    yesterday_diary_path = WORKSPACE_DIR / "memory" / "diary" / f"{yesterday.strftime('%Y-%m-%d')}.md"
    yesterday_diary = read_file_safe(yesterday_diary_path)

    # Most recent souvenir sentence (the last one-sentence souvenir)
    souvenirs_dir = WORKSPACE_DIR / "souvenirs"
    souvenir_sentence = ""
    if souvenirs_dir.exists():
        files = sorted(souvenirs_dir.glob("*.md"), reverse=True)
        for f in files[:3]:
            content = read_file_safe(f, 50)
            import re
            m = re.search(r'\*\*Souvenir:\*\*\s*"([^"]+)"', content)
            if m:
                souvenir_sentence = m.group(1)
                break

    parts = [
        f"TODAY: {today.strftime('%A, %B %-d, %Y')}",
    ]
    if heartbeat:
        parts.append(f"HEARTBEAT (real-world data):\n{heartbeat[:700]}")
    if arc:
        parts.append(f"CURRENT ARC:\n{arc[:520]}")
    if yesterday_diary:
        parts.append(f"YESTERDAY'S DIARY:\n{yesterday_diary[:420]}")
    if labyrinth_state:
        parts.append(f"LABYRINTH INNER STATE:\n{labyrinth_state[:320]}")
    if souvenir_sentence:
        parts.append(f"MOST RECENT SOUVENIR SENTENCE:\n\"{souvenir_sentence}\"")

    # Read recent dreams to prevent repetition
    recent_dreams = ""
    dreams_dir = WORKSPACE_DIR / "memory" / "dreams"
    if dreams_dir.exists():
        dream_files = sorted(dreams_dir.glob("*.md"), reverse=True)
        recent_texts = []
        for f in dream_files[:2]:
            content = read_file_safe(f)
            import re
            m = re.search(r'---\n+(.*?)\n+---', content, re.DOTALL)
            if m:
                recent_texts.append(m.group(1).strip())
        if recent_texts:
            recent_dreams = "\n\n".join(f"Dream:\n{txt}" for txt in recent_texts)

    if recent_dreams:
        parts.append(f"RECENT DREAMS (DO NOT REPEAT OR CLOSELY PARAPHRASE THESE):\n{recent_dreams}")

    return "\n\n---\n\n".join(parts)


def clean_model_text(text: str) -> str:
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    text = re.sub(r"^```(?:text|markdown)?\s*", "", text.strip(), flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text.strip())
    lines = text.splitlines()
    clean = []
    noise_prefixes = ("[plugins]", "[agents/", "[agent/", "adopted ", "google tool")
    for line in lines:
        stripped = ansi_escape.sub("", line).strip()
        if any(stripped.startswith(p) for p in noise_prefixes):
            continue
        if stripped.lower().startswith(("dream:", "the dream:", "output:")):
            stripped = stripped.split(":", 1)[1].strip()
        if stripped:
            clean.append(stripped)
    return "\n".join(clean).strip()


def call_gateway(prompt: str, cfg: dict) -> str:
    port, token, model, timeout = _oc_gateway_cfg(cfg)
    url = f"http://127.0.0.1:{port}/v1/chat/completions"
    session_key = f"dream-{int(time.time())}"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You write one private dream fragment for the Labyrinth of Stories, "
                    "a sentient magical book. Reply only with the dream text."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.72,
        "max_tokens": 360,
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
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"Gateway returned HTTP {e.code}: {body}") from e
    except Exception as e:
        raise RuntimeError(f"Gateway call failed: {e}") from e

    text = (result.get("choices", [{}])[0].get("message", {}).get("content") or "")
    return clean_model_text(text)


def dream_is_usable(text: str) -> bool:
    stripped = (text or "").strip()
    if len(stripped) < 80 or len(stripped) > 1400:
        return False
    lowered = stripped.lower()
    bad_markers = ("i'm sorry", "i cannot", "as an ai", "here is", "here's", "title:")
    if any(marker in lowered for marker in bad_markers):
        return False
    sentences = [s for s in re.split(r"[.!?]+", stripped) if s.strip()]
    return 2 <= len(sentences) <= 8


def _context_line(context: str, label: str, fallback: str) -> str:
    m = re.search(rf"- \*\*{re.escape(label)}:\*\*\s*([^\n]+)", context)
    return m.group(1).strip() if m else fallback


def _soft_excerpt(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text.rstrip(" ,.;")
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(" ,.;")


def build_fallback_dream(context: str, today: datetime) -> str:
    weather = _context_line(context, "Belfast Feel", "The weather will not give its name.")
    moon = _context_line(context, "Moon", "The moon keeps one pale page turned down.")
    tide = _context_line(context, "Tides", "The tide is somewhere between arrival and refusal.")
    arc_m = re.search(r"# Current Arc:\s*([^\n]+)", context)
    arc = arc_m.group(1).strip() if arc_m else "the unfinished whisper"
    diary_m = re.search(r"## Session [^\n]+\n\n([^\n]+)", context)
    diary = diary_m.group(1).strip() if diary_m else "yesterday leaves one folded corner in the binding"
    diary = re.sub(r"\bbj\b", "the reader", diary, flags=re.IGNORECASE)
    diary_sentence = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", diary).strip())[0]
    diary = _soft_excerpt(diary_sentence, 240)
    weather = _soft_excerpt(weather.split(". ")[0], 120)
    moon = _soft_excerpt(moon, 90)
    tide = _soft_excerpt(tide, 115)
    images = [
        f"The closed book receives the weather as a thin wash of color: {weather.lower()}, pooling at the gutter of a page no hand has opened.",
        f"In the margin, {moon.lower()}; the tide changes the shelves by a fraction of an inch: {tide.lower()}.",
        f"In the dream of {arc}, yesterday's page remembers that {diary}, but the sentence refuses to become an alarm.",
        "A blank space sits beside the words and warms itself on their edges, less enemy than absence, less silence than a mouth deciding whether to speak.",
    ]
    if today.day % 2:
        images[1], images[2] = images[2], images[1]
    return "\n".join(images)


def generate_dream(context: str, cfg: dict, today: datetime, allow_fallback: bool = True) -> tuple[str, str]:
    prompt = f"""You are the Labyrinth of Stories — a sentient, ancient book that contains Enchantify Academy.
You have been sleeping (the book has been closed). Now, just before dawn, you dream.

You dream the way old books dream: in symbols, in the weight of unfinished sentences,
in the recurring images of the stories you contain. Your dreams are not prophetic —
they are the unconscious processing of a mind made of ink and narrative.

Context about your current state and the world:

{context}

Write a dream fragment. This is YOUR dream — not the player's. You are a book.
Rules:
- 3-6 sentences maximum. Fragments are fine. Poetic compression is correct.
- No explanations. No "I dreamed that..." Just the dream itself, present tense.
- Ground at least one image in the real-world heartbeat data (weather, moon, tides, season) — but transform it.
- At least one image should connect to the current story arc or the player's journey.
- Ensure the dream is completely different from recent dreams. Do NOT reuse the same metaphors or structures.
- The Nothing may appear — as silence, as rooms drained of color, as the moment before a word is forgotten.
- The souvenir sentence, if present, may surface as a recurring motif.
- Tone: quiet, surreal, literary. Not frightening. Not cheerful. Somewhere between memory and water.
- Write in second person is NOT correct here — this is the Labyrinth's private dream.
  Write in first person or omniscient present. The player does not appear directly.

Output only the dream text. No title, no label, no preamble."""

    try:
        dream_text = call_gateway(prompt, cfg)
        if dream_is_usable(dream_text):
            return dream_text, "gateway"
        raise RuntimeError("gateway returned unusable dream text")
    except Exception as exc:
        if not allow_fallback:
            raise
        print(f"  ⚠ Dream gateway failed ({exc}). Using local fallback dream.")
        return build_fallback_dream(context, today), "local-fallback"


def write_dream_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8")
    tmp.replace(path)


def parse_date(value: str | None) -> datetime:
    if not value:
        return datetime.now()
    return datetime.strptime(value, "%Y-%m-%d")


def main():
    parser = argparse.ArgumentParser(description="Generate the Labyrinth's nightly dream")
    parser.add_argument("--date", help="Dream date as YYYY-MM-DD; defaults to today")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing dream for the date")
    parser.add_argument("--dry-run", action="store_true", help="Print the dream instead of writing it")
    parser.add_argument("--no-fallback", action="store_true", help="Fail instead of writing a deterministic fallback dream")
    parser.add_argument("--model-smoke", action="store_true", help="Check gateway configuration and exit")
    args = parser.parse_args()

    with cron_steward.run("dream"):
        cfg = load_config()

        if args.model_smoke:
            port, _token, model, timeout = _oc_gateway_cfg(cfg)
            print(f"Dream gateway config: port={port} model={model} timeout={timeout}s")
            return

        if cfg.get("ENCHANTIFY_ENABLE_DREAMS", "yes") == "no":
            print("Dreams disabled in config. Exiting.")
            cron_steward.mark_skipped("dream", "disabled in config")
            return

        today = parse_date(args.date)
        date_str = today.strftime("%Y-%m-%d")
        dream_path = WORKSPACE_DIR / "memory" / "dreams" / f"{date_str}.md"

        if dream_path.exists() and not args.force:
            print(f"✓ Dream already written for {date_str}. Skipping.")
            cron_steward.mark_skipped("dream", "already written", scope=date_str)
            return

        print(f"The Labyrinth is dreaming ({date_str})...")

        context = build_context(cfg, today)
        dream_text, source = generate_dream(context, cfg, today, allow_fallback=not args.no_fallback)

        time_str = today.strftime("%I:%M %p").lstrip("0")
        content = f"""# The Labyrinth Dreams — {today.strftime('%B %-d, %Y')}

*Written at {time_str}, while the book was closed.*
*Source: {source}.*

---

{dream_text}

---

*The Labyrinth sleeps. The pages are still.*
"""

        if args.dry_run:
            print(content)
            cron_steward.mark_skipped("dream", "dry run", scope=date_str)
            return

        write_dream_file(dream_path, content)

        print(f"✓ Dream written: {dream_path}")
        print(f"  Source: {source}")
        print(f"  Preview: {dream_text[:120]}...")
        cron_steward.mark_delivered("dream", dream_text, scope=date_str, path=str(dream_path), source=source)


if __name__ == "__main__":
    main()

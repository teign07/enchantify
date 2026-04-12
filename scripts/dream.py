#!/usr/bin/env python3
"""
dream.py — The Labyrinth's Overnight Dream Generator.
Runs nightly via cron (suggested: 2am). Reads recent context and generates
a short, surreal dream fragment in the Labyrinth's voice.

The Labyrinth is a sentient book. It dreams the way old books dream:
in symbols, ink, recurring images, the weight of unfinished stories.

Requires: pip install anthropic
Cron:     0 2 * * * python3 /path/to/scripts/dream.py >> logs/dream.log 2>&1
"""
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
WORKSPACE_DIR = SCRIPT_DIR.parent


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


def build_context(cfg: dict) -> str:
    today = datetime.now()
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
        parts.append(f"HEARTBEAT (real-world data):\n{heartbeat[:800]}")
    if arc:
        parts.append(f"CURRENT ARC:\n{arc[:600]}")
    if yesterday_diary:
        parts.append(f"YESTERDAY'S DIARY:\n{yesterday_diary[:500]}")
    if labyrinth_state:
        parts.append(f"LABYRINTH INNER STATE:\n{labyrinth_state[:400]}")
    if souvenir_sentence:
        parts.append(f"MOST RECENT SOUVENIR SENTENCE:\n\"{souvenir_sentence}\"")

    return "\n\n---\n\n".join(parts)


def call_agent(prompt: str) -> str:
    result = subprocess.run(
        ["openclaw", "agent", "--local", "--agent", "enchantify", "-m", prompt],
        capture_output=True, text=True
    )
    # Strip ANSI escape codes and plugin/auth noise lines from stdout
    import re
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    lines = result.stdout.splitlines()
    clean = []
    noise_prefixes = ("[plugins]", "[agents/", "[agent/", "adopted ", "google tool")
    for line in lines:
        stripped = ansi_escape.sub("", line).strip()
        if any(stripped.startswith(p) for p in noise_prefixes):
            continue
        if stripped:
            clean.append(stripped)
    return "\n".join(clean).strip()


def generate_dream(context: str) -> str:
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
- The Nothing may appear — as silence, as rooms drained of color, as the moment before a word is forgotten.
- The souvenir sentence, if present, may surface as a recurring motif.
- Tone: quiet, surreal, literary. Not frightening. Not cheerful. Somewhere between memory and water.
- Write in second person is NOT correct here — this is the Labyrinth's private dream.
  Write in first person or omniscient present. The player does not appear directly.

Output only the dream text. No title, no label, no preamble."""

    return call_agent(prompt)


def main():
    cfg = load_config()

    if cfg.get("ENCHANTIFY_ENABLE_DREAMS", "yes") == "no":
        print("Dreams disabled in config. Exiting.")
        return

    today = datetime.now()
    date_str = today.strftime("%Y-%m-%d")
    dream_path = WORKSPACE_DIR / "memory" / "dreams" / f"{date_str}.md"

    if dream_path.exists():
        print(f"✓ Dream already written for {date_str}. Skipping.")
        return

    print(f"The Labyrinth is dreaming ({date_str})...")

    context = build_context(cfg)
    dream_text = generate_dream(context)

    time_str = today.strftime("%I:%M %p").lstrip("0")
    content = f"""# The Labyrinth Dreams — {today.strftime('%B %-d, %Y')}

*Written at {time_str}, while the book was closed.*

---

{dream_text}

---

*The Labyrinth sleeps. The pages are still.*
"""

    dream_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dream_path, "w") as f:
        f.write(content)

    print(f"✓ Dream written: {dream_path}")
    print(f"  Preview: {dream_text[:120]}...")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
sparky.py — Standalone Sparky Shiny Generator.
Runs daily via cron (suggested: 8am). Reads heartbeat data + Wikipedia's
"On This Day" and finds 1-2 genuine pattern-connections in Sparky's voice.

Sparky is the margin creature. It notices where two unrelated things rhyme.
It cannot help reporting it.

Requires: pip install anthropic
Cron:     0 8 * * * python3 /path/to/scripts/sparky.py >> logs/sparky.log 2>&1
"""
import os
import re
import json
import shutil
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
WORKSPACE_DIR = SCRIPT_DIR.parent


_OPENCLAW_BIN = (
    shutil.which("openclaw")
    or "/opt/homebrew/bin/openclaw"
    or "/usr/local/bin/openclaw"
)


def load_config() -> dict:
    cfg = {}
    config_path = WORKSPACE_DIR / "config" / "secrets.env"
    if config_path.exists():
        with open(config_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                cfg[key.strip()] = val.strip().strip('"').strip("'")
    return cfg


def read_file_safe(path: Path, limit_lines: int = 50) -> str:
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


def fetch_on_this_day() -> list[str]:
    """Fetch Wikipedia's 'On This Day' events for today. Free, no API key."""
    today = datetime.now()
    month = today.strftime("%m").lstrip("0")
    day = today.strftime("%d").lstrip("0")
    url = f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/events/{month}/{day}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Enchantify-Sparky/1.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
        events = data.get("events", [])
        # Return 8 random-ish events (by year spread)
        step = max(1, len(events) // 8)
        selected = events[::step][:8]
        return [f"{e.get('year', '?')}: {e.get('text', '')}" for e in selected]
    except Exception as ex:
        print(f"  ⚠ Could not fetch On This Day: {ex}")
        return []


def extract_heartbeat_signals(heartbeat: str) -> dict:
    """Pull key signals from heartbeat text for Sparky's pattern-finding."""
    signals = {}

    m = re.search(r'Moon[:\s]+.*?([🌑🌒🌓🌔🌕🌖🌗🌘🌙]?\s*\w[\w\s]+)\((\d+)%', heartbeat)
    if m:
        signals["moon_phase"] = m.group(1).strip()
        signals["moon_illumination"] = m.group(2)

    m = re.search(r'Season[:\s]+([^\n\|]+)', heartbeat)
    if m:
        signals["season"] = m.group(1).strip().split(" — ")[0]

    m = re.search(r'Tide[s]?[:\s]+([^\n]+)', heartbeat)
    if m:
        signals["tides"] = m.group(1).strip()[:80]

    m = re.search(r'Raw[:\s]+([^\n*]+)', heartbeat)
    if m:
        signals["weather"] = m.group(1).strip().split("|")[0].strip()

    return signals


def get_player_belief(cfg: dict) -> str:
    """Read current Belief from default player file."""
    player = cfg.get("ENCHANTIFY_DEFAULT_PLAYER", "")
    if not player:
        return ""
    player_file = WORKSPACE_DIR / "players" / f"{player}.md"
    content = read_file_safe(player_file, 10)
    m = re.search(r'\*\*Belief:\*\*\s*(\d+)', content)
    return m.group(1) if m else ""


def call_agent(prompt: str) -> str:
    """Run a prompt through the enchantify agent via openclaw."""
    result = subprocess.run(
        [_OPENCLAW_BIN, "agent", "--local", "--agent", "enchantify", "-m", prompt],
        capture_output=True, text=True, timeout=120
    )
    output = result.stdout.strip()
    # Strip ANSI escape codes
    output = re.sub(r'\x1b\[[0-9;]*m', '', output)
    # Strip openclaw noise lines
    noise = ("[plugins]", "[agents/", "[agent/", "adopted ", "google tool")
    clean = [
        line for line in output.splitlines()
        if not any(line.strip().lower().startswith(p) for p in noise)
    ]
    return "\n".join(clean).strip()


def generate_shiny(signals: dict, events: list[str], belief: str) -> str:
    today = datetime.now()
    day_of_year = today.timetuple().tm_yday
    days_in_year = 366 if today.year % 4 == 0 else 365

    context_parts =[
        f"TODAY: {today.strftime('%A, %B %-d, %Y')} (day {day_of_year} of {days_in_year})",
    ]

    if signals:
        sig_lines =[f"  {k}: {v}" for k, v in signals.items()]
        context_parts.append("REAL-WORLD SIGNALS:\n" + "\n".join(sig_lines))

    if belief:
        context_parts.append(f"PLAYER'S CURRENT BELIEF: {belief} / 100")

    if events:
        context_parts.append("ON THIS DAY IN HISTORY:\n" + "\n".join(f"  - {e}" for e in events))

    context = "\n\n".join(context_parts)

    prompt = f"""You are Sparky — the margin creature of the Labyrinth of Stories.
You live in the white space at the edges of the pages. You find patterns.
Not useful patterns. Not patterns that mean anything. Just places where
two unrelated things happen to rhyme. You find this genuinely delightful.
You cannot help reporting it.

Here is today's data:

{context}

Find 1-2 genuine pattern-connections from TODAY'S DATA. They must be real —
grounded in the actual data above, not invented. But "real" means many things:

TYPES OF CONNECTIONS SPARKY FINDS (pick any, mix freely):
- Numeric: two numbers that match, or add up to something, or mirror each other
- Metaphorical: two things that are structurally the same even though they're unrelated
  (e.g. tides and narrative arcs both "turn"; moon phases and belief both "fill and empty")
- Relational: something in today's data echoes something in history, or vice versa
  (e.g. a historical event today involves waiting, and the tides are slack — both holding still)
- Poetic: two images that belong together for no logical reason
  (e.g. fog + a historical eclipse + "the Nothing is close" — all three are the same darkness)
- Temporal: something about the date, season, or day-count that rhymes with something else
- Emotional: the mood of a historical event matches the mood of today's signals
- Coincidence of name or word: a word in a historical event appears in today's data too

Do NOT default to math. Numeric connections are ONE option, not the only one.
The best shinies are the ones that feel like they shouldn't be true but are.
Do not force it. If nothing connects, output exactly the text: (a sleeping dot)

Rules for your output:
- Write in Sparky's voice: cramped, ecstatic, excessive exclamation marks, margin-note energy
- Reference to yourself as "Sp." or "Sparky" at the end
- Maximum 4 lines total. You live in the MARGIN. Be small.
- Optionally include one tiny sketch description in brackets [like this]
- If you find nothing genuine, output exactly the text: (a sleeping dot)

Examples of the RIGHT tone (notice variety — not all math):
"LOOK!! The moon is 71% illuminated AND the player has 71 Belief!! BOTH ALMOST FULL!! — Sp."
"the tide is going out AND today in 1912 the Titanic sank AND both are things leaving slowly that you can't stop!! Sparky finds this extremely significant — Sp. [drawing: small ship going down]"
"fog AND a historical astronomer born today AND both are about not being able to see the thing you're looking for!! — Sp."
"the season is called Mud Season AND today someone planted a flag on a mountain AND both are about the exact moment between stuck and moving!! — Sp. [arrow: pointing up out of mud]"
"the word STILL appears in three of today's historical events!! THE LABYRINTH IS NOTICING — Sp."

Output only the margin note. No preamble, no explanation."""

    return call_agent(prompt)


def main():
    cfg = load_config()

    if cfg.get("ENCHANTIFY_ENABLE_SPARKY", "yes") == "no":
        print("Sparky disabled in config. Exiting.")
        return

    if cfg.get("ENCHANTIFY_SPARKY_MODE", "standalone") == "silvie":
        print("Sparky runs via Silvie on this install. Exiting.")
        return

    today = datetime.now()
    date_str = today.strftime("%Y-%m-%d")
    time_str = today.strftime("%H%M")
    shiny_path = WORKSPACE_DIR / "sparky" / "shinies" / f"{date_str}-{time_str}.md"

    # We allow multiple shinies per day now, since Sparky runs twice a day.
    existing = list((WORKSPACE_DIR / "sparky" / "shinies").glob(f"{date_str}*.md"))
    if len(existing) >= 5:
        print(f"✓ Sparky is tired. Already {len(existing)} shinies for {date_str}.")
        return

    print(f"Sparky is looking for patterns ({date_str})...")

    heartbeat_path = WORKSPACE_DIR / "HEARTBEAT.md"
    heartbeat = read_file_safe(heartbeat_path, 60)
    signals = extract_heartbeat_signals(heartbeat) if heartbeat else {}
    belief = get_player_belief(cfg)
    if belief:
        signals["belief"] = belief

    events = fetch_on_this_day()

    shiny_text = generate_shiny(signals, events, belief)

    content = f"# Sparky Shiny — {date_str}\n\n{shiny_text}\n"

    shiny_path.parent.mkdir(parents=True, exist_ok=True)
    with open(shiny_path, "w") as f:
        f.write(content)

    print(f"✓ Shiny written: {shiny_path}")
    print(f"  {shiny_text[:100]}...")

    # Inject into HEARTBEAT.md so the Labyrinth sees it without reading a separate file
    inject_sparky_into_heartbeat(heartbeat_path, date_str, shiny_text)


def inject_sparky_into_heartbeat(heartbeat_path: Path, date_str: str, shiny_text: str) -> None:
    """Write/update a ### 🌟 Sparky Says block in HEARTBEAT.md outside the pulse markers."""
    if not heartbeat_path.exists():
        print("  ⚠ HEARTBEAT.md not found — skipping Sparky injection.")
        return

    text = heartbeat_path.read_text()

    block = (
        f"<!-- SPARKY_START -->\n"
        f"### 🌟 Sparky Says\n"
        f"*{date_str}*\n\n"
        f"{shiny_text.strip()}\n"
        f"<!-- SPARKY_END -->"
    )

    # Replace existing block if present
    import re
    if "<!-- SPARKY_START -->" in text:
        text = re.sub(
            r"<!-- SPARKY_START -->.*?<!-- SPARKY_END -->",
            block,
            text,
            flags=re.DOTALL,
        )
    else:
        # Insert after <!-- PULSE_END -->
        text = text.replace("<!-- PULSE_END -->", f"<!-- PULSE_END -->\n\n{block}")

    heartbeat_path.write_text(text)
    print(f"  ✓ Sparky injected into HEARTBEAT.md")


if __name__ == "__main__":
    main()

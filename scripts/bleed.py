#!/usr/bin/env python3
"""
bleed.py — The Bleed, daily edition.

The Academy student newspaper. Publishes at 6pm.
Synthesizes simulation data, player biometrics, thread pressures, and active play
into in-world journalism.

Forever issue numbering tracked in bleed/issue-number.txt.
Broadsheet HTML saved to bleed/issues/YYYY-MM-DD.html.
Telegram text edition sent at 6pm if TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID are set.
CUPS print sent if BLEED_PRINTER is set (uses wkhtmltopdf → PDF if available).

Usage:
  python3 scripts/bleed.py             # publish today's issue
  python3 scripts/bleed.py --force     # regenerate even if already published today

Cron: 0 18 * * * cd /path/to/enchantify && /usr/bin/python3 scripts/bleed.py >> logs/bleed.log 2>&1
"""

import os
import re
import sys
import json
import shutil
import subprocess
import urllib.request
from datetime import datetime, date
from pathlib import Path
import sys as _sys

SCRIPT_DIR   = Path(__file__).parent
WORKSPACE_DIR = SCRIPT_DIR.parent

# Import schedule module
_sys.path.insert(0, str(SCRIPT_DIR))
try:
    from schedule import get_schedule_data, WEEKDAY_NAMES
    _SCHEDULE_AVAILABLE = True
except ImportError:
    _SCHEDULE_AVAILABLE = False

ISSUE_NUMBER_FILE = WORKSPACE_DIR / "bleed" / "issue-number.txt"
ISSUES_DIR        = WORKSPACE_DIR / "bleed" / "issues"


# ── Config ────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    cfg = {}
    secrets_path = WORKSPACE_DIR / "config" / "secrets.env"
    if secrets_path.exists():
        for line in secrets_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                cfg[k.strip()] = v.strip().strip('"').strip("'")
    return cfg


# ── Issue numbering ───────────────────────────────────────────────────────────

def get_issue_number() -> int:
    ISSUE_NUMBER_FILE.parent.mkdir(parents=True, exist_ok=True)
    if ISSUE_NUMBER_FILE.exists():
        try:
            return int(ISSUE_NUMBER_FILE.read_text().strip()) + 1
        except ValueError:
            pass
    return 1


def save_issue_number(n: int):
    ISSUE_NUMBER_FILE.write_text(str(n))


# ── Data readers ──────────────────────────────────────────────────────────────

def read_file_safe(path: Path, limit_lines: int = 0) -> str:
    if not path.exists():
        return ""
    text = path.read_text().strip()
    if limit_lines:
        return "\n".join(text.splitlines()[:limit_lines])
    return text


def extract_pulse_section(heartbeat: str) -> str:
    m = re.search(r'<!-- PULSE_START -->(.*?)<!-- PULSE_END -->', heartbeat, re.DOTALL)
    return m.group(1).strip() if m else ""


def get_sparky_shiny(date_str: str) -> str:
    shinies_dir = WORKSPACE_DIR / "sparky" / "shinies"
    if not shinies_dir.exists():
        return ""
    matches = list(shinies_dir.glob(f"{date_str}*.md"))
    if not matches:
        return ""
    text = matches[0].read_text()
    # Strip H1 header line
    return re.sub(r'^# .+\n', '', text).strip()


def get_player_data(cfg: dict) -> dict:
    player = cfg.get("ENCHANTIFY_DEFAULT_PLAYER", "bj")
    content = read_file_safe(WORKSPACE_DIR / "players" / f"{player}.md", 15)
    data = {}

    m = re.search(r'\*\*Belief:\*\*\s*(\d+)', content)
    data["belief"] = m.group(1) if m else "?"

    m = re.search(r'\*\*Chapter:\*\*\s*(\S+)', content)
    data["chapter"] = m.group(1) if m else "?"

    m = re.search(r'\*\*Tutorial Progress:\*\*\s*(\S+)', content)
    data["tutorial"] = m.group(1) if m else "?"

    return data


def get_thread_summary() -> str:
    content = read_file_safe(WORKSPACE_DIR / "lore" / "threads.md")
    lines = []
    for section in re.split(r'^## Thread: ', content, flags=re.MULTILINE)[1:]:
        slines = section.strip().splitlines()
        name = slines[0].strip() if slines else "?"
        phase_m    = re.search(r'\*\*phase:\*\*\s*(.+)', section)
        pressure_m = re.search(r'\*\*pressure:\*\*\s*(.+)', section)
        beat_m     = re.search(r'\*\*Next beat:\*\*\s*(.+)', section)
        phase    = phase_m.group(1).strip() if phase_m else "?"
        pressure = pressure_m.group(1).strip() if pressure_m else "?"
        beat     = beat_m.group(1).strip()[:120] if beat_m else ""
        lines.append(f"- {name} [{phase}, pressure: {pressure}]: {beat}")
    return "\n".join(lines)


def get_weather_forecast_from_heartbeat() -> str:
    """Pull the Forecast line from the pulse section of HEARTBEAT.md."""
    heartbeat = read_file_safe(WORKSPACE_DIR / "HEARTBEAT.md", 120)
    pulse = extract_pulse_section(heartbeat)
    lines = []
    capture = False
    for line in pulse.splitlines():
        if "**Forecast:**" in line:
            # First line: strip the label
            first = line.split("**Forecast:**", 1)[-1].strip()
            if first:
                lines.append(first)
            capture = True
        elif capture:
            # Forecast is multi-line until next bullet or blank section header
            if line.startswith("- **") or line.startswith("###"):
                break
            if line.strip():
                lines.append(line.strip().lstrip("- "))
    return "\n".join(lines) if lines else ""


def calculate_market_odds() -> list:
    """Derive predictions market odds from thread + entity data. Pure math, no LLM."""
    threads_text = read_file_safe(WORKSPACE_DIR / "lore" / "threads.md")
    register_text = read_file_safe(WORKSPACE_DIR / "lore" / "world-register.md")

    # Sum belief per thread from world register [thread:id] tags
    thread_belief = {}
    row_re = re.compile(r"^\|\s*[^|]+\s*\|\s*[^|]+\s*\|\s*(\d+)\s*\|\s*([^|]*)\s*\|", re.MULTILINE)
    for m in row_re.finditer(register_text):
        belief, notes = int(m.group(1)), m.group(2)
        tid_m = re.search(r'\[thread:([^\]]+)\]', notes)
        if tid_m:
            for tid in tid_m.group(1).split(','):
                tid = tid.strip()
                thread_belief[tid] = thread_belief.get(tid, 0) + belief

    # Parse thread phases and nothing pressure
    odds_list = []
    for section in re.split(r'^## Thread: ', threads_text, flags=re.MULTILINE)[1:]:
        slines = section.strip().splitlines()
        name = slines[0].strip() if slines else "?"
        if name.startswith("Ley Line") or name.startswith("Adding"):
            continue

        id_m      = re.search(r'\*\*id:\*\*\s*`([^`]+)`', section)
        phase_m   = re.search(r'\*\*phase:\*\*\s*(.+)', section)
        nothing_m = re.search(r'\*\*Nothing pressure:\*\*\s*(.+)', section)
        beat_m    = re.search(r'\*\*Next beat:\*\*\s*(.+)', section)

        tid     = id_m.group(1).strip() if id_m else ""
        phase   = phase_m.group(1).strip().lower() if phase_m else ""
        nothing = nothing_m.group(1).strip().lower() if nothing_m else ""
        beat    = beat_m.group(1).strip()[:100] if beat_m else ""

        belief = thread_belief.get(tid, 0)
        if belief == 0 and tid == "main-arc":
            belief = 80  # main arc always has pressure

        # Base probability from combined belief (log-ish curve: 10 belief = 10%, 100 = 90%)
        base = min(90, max(10, int(belief * 0.8)))

        # Phase modifier
        phase_mod = {
            "escalating": +15, "setup": +5, "quiet": -5,
            "dormant": -20, "permanent": +0,
        }.get(phase.split()[0] if phase else "", 0)

        # Nothing pressure modifier
        nothing_mod = -10 if "high" in nothing else (-5 if "medium" in nothing else +3)

        pct = max(5, min(95, base + phase_mod + nothing_mod))

        if name not in ("Academy Daily Life",):  # skip slice-of-life, always active
            odds_list.append({
                "name": name,
                "tid": tid,
                "phase": phase,
                "belief": belief,
                "yes": pct,
                "no": 100 - pct,
                "beat": beat,
            })

    odds_list.sort(key=lambda x: -x["belief"])
    return odds_list


def get_entity_standings() -> str:
    content = read_file_safe(WORKSPACE_DIR / "lore" / "world-register.md")
    entities = []
    row_re = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|", re.MULTILINE)
    for m in row_re.finditer(content):
        name, etype, belief = m.groups()
        name = name.strip()
        if name.lower() in ('entity', 'talisman', 'name', '---', ''):
            continue
        entities.append((name, etype.strip(), int(belief)))
    entities.sort(key=lambda x: -x[2])
    return "\n".join(f"- {n} ({t}): Belief {b}" for n, t, b in entities[:10])


def extract_health_from_pulse(pulse: str) -> str:
    """Pull health/biometric lines from the pulse section."""
    health_lines = []
    for line in pulse.splitlines():
        if any(kw in line for kw in ("Steps", "Sleep", "HRV", "Resting", "Health", "Distance", "Flights")):
            health_lines.append(line.strip().lstrip("- ").strip())
    return "\n".join(health_lines[:6]) if health_lines else ""


# ── Agent call ────────────────────────────────────────────────────────────────

_OPENCLAW_BIN = (
    shutil.which("openclaw")
    or "/opt/homebrew/bin/openclaw"
    or "/usr/local/bin/openclaw"
)

def call_agent(prompt: str) -> str:
    result = subprocess.run(
        [_OPENCLAW_BIN, "agent", "--local", "--agent", "enchantify", "-m", prompt],
        capture_output=True, text=True, timeout=240
    )
    output = result.stdout.strip()

    # Strip ANSI codes
    ansi = re.compile(r'\x1b\[[0-9;]*m')
    output = ansi.sub('', output)

    # Strip plugin/agent noise lines
    noise = ("[plugins]", "[agents/", "[agent/", "adopted ", "google tool")
    clean = [
        line for line in output.splitlines()
        if not any(line.strip().lower().startswith(p) for p in noise)
    ]
    return "\n".join(clean).strip()


# ── Content generation ────────────────────────────────────────────────────────

def generate_content(data: dict) -> dict:
    prompt = f"""You are writing THE BLEED — the Academy student newspaper.

Publication date: {data['date_str']}
Issue number: #{data['issue_number']}

THE BLEED's voice: Dry, precise, slightly gothic. It reports on the Academy as a real institution.
This is not a parody — it's a real paper. The extraordinary is covered with the same deadpan
reportage as the ordinary. Specificity is everything. Invent concrete details where needed —
named corridors, specific times, partial quotes — the kind of texture that makes a place feel real.

The reader should be able to SETTLE INTO THIS PAPER. Every section except The Barometer,
The Exchange, The Correction, and The Missing should be substantial, readable prose.

DATA FEEDS (synthesize into journalism — never quote data directly):

SIMULATION ACTIVITY (tick queue):
{data['tick_queue']}

THREAD STATES:
{data['thread_summary']}

ENTITY STANDINGS (Belief = public influence):
{data['entity_standings']}

PLAYER STATUS:
- Chapter: {data['player']['chapter']}
- Belief: {data['player']['belief']} / 100
- Tutorial: {data['player']['tutorial']}

ENVIRONMENTAL (heartbeat):
{data['pulse']}

WEATHER FORECAST (4-day, real data — use these exact conditions):
{data['forecast']}

HEALTH SIGNALS (map to Academy conditions):
{data['health']}

---

Write the newspaper in EXACTLY this format. Start with ===HEADLINE=== — no preamble.

===HEADLINE===
Title: [specific, factual headline — 8 words max]
Subhead: [one sentence expanding the headline]
Body: [A full front-page article. 5-7 paragraphs of real reporting. Quote sources (unnamed
is fine: "one second-year student, who declined to be identified"). Give specific details —
times, locations within the Academy, observations. Report the dominant thread or simulation
activity as factual news. This is the main story — write it like one.]

===GOSSIP===
[The social column, in W.E.'s voice. Write 5-6 separate gossip items — each item is its own
paragraph of 2-4 sentences. Wicker reports true things slanted. He names names when it suits
him and withholds them when it doesn't. He is never without an angle. He always knows more
than he lets on. He never directly identifies himself. Each item should feel like a distinct
morsel — a different corner of the Academy social world. End with his byline: — W.E.]

===WEATHER===
[The Academy Meteorological Society's 4-day outlook, written entirely in Academy terms.
Rain = the Unwritten pressing through the membrane. Clear sky = the Labyrinth open and legible.
Fog = the Nothing is close. Wind = narrative pressure. Temperature = the ambient emotional register.
Use the actual forecast data provided to you — do not invent temperatures or conditions.
Write it as if it were a real forecast from a school publication, 4-5 lines, one per day.
A brief final line: what this weather means for the Labyrinth's mood this week.]

===FORECAST===
[The Story Forecast — written exactly like a weather forecast, but for narrative.
Use thread pressures and phases to predict what story conditions will prevail this week.
Format: probability + what to expect, for each major thread. Be specific. Quote odds.
Example: "70% chance of significant antagonist activity by Thursday; Wicker's Campaign
is in escalating phase and his crew's silence suggests something is being positioned."
4-6 lines. End with an overall narrative outlook for the week: volatile, settled, building, etc.
This is journalism forecasting narrative weather — dry, specific, slightly ominous.]

===MARKET===
[The Thread Futures Market — a predictions market for story outcomes.
You are given pre-calculated odds (YES% / NO%). Format as a proper market listing.
Each line: the question | YES: X | NO: Y | one-word trend (RISING/FALLING/STEADY/VOLATILE)
Below the ticker: 2-3 sentences of market commentary. What does the current pattern suggest
about where the story is going? Who is overvalued? What is the market not pricing in?
This is the most analytical column — precise, slightly clinical, the newspaper's quant desk.]

MARKET ODDS DATA (pre-calculated from entity belief and thread phase):
{data['market_odds_formatted']}

===BAROMETER===
[Health/biometric data AS Academy conditions. Steps = distance covered on Academy grounds.
Sleep/HRV = student vitality index. Weather = atmospheric pressure. 4-6 short lines,
formatted like a weather/conditions report. Brief is correct here.]

===EXCHANGE===
[The Belief Exchange ticker. List ALL significant entities with Belief scores as prices.
Mark trend: ↑ rising / ↓ falling / — steady. One paragraph of market commentary below
the ticker — what does the current pattern mean narratively?]

===FEATURE===
[A longer in-world piece: a profile, an investigation, a history, or an opinion column.
4-6 paragraphs. Choose the most interesting thread or entity from the data and write
something with depth — not news, but context. Could be: a profile of a figure who's been
in the news, an investigation into something that's been going on for weeks, a brief history
of a location, or an opinion piece attributed to a named Academy figure. Give it a title
and a byline. This is what the reader lingers over.]

===CLASSIFIEDS===
[5-6 classified notices. Each one 2-4 sentences — enough to feel real and slightly eerie.
Mix labels: LOST: / FOUND: / NOTICE: / SEEKING: / WARNING: / REWARD: / POSITION AVAILABLE: etc.
These are story seeds. The reader should want to investigate at least two of them.]

===CORRECTION===
[One dry, formal correction. Deadpan and specific. 1-2 sentences. Brief is correct here.]

===MISSING===
[Threads currently dormant — noted as quiet absence. 2-4 lines.
The quietest column. Brief is correct here. It only notes absence, never explains it.]"""

    raw = call_agent(prompt)
    return parse_sections(raw)


def parse_sections(raw: str) -> dict:
    sections = {}
    current_key = None
    current_lines = []

    for line in raw.splitlines():
        m = re.match(r'^===(\w+)===\s*$', line.strip())
        if m:
            if current_key:
                sections[current_key] = "\n".join(current_lines).strip()
            current_key = m.group(1).upper()
            current_lines = []
        elif current_key:
            current_lines.append(line)

    if current_key:
        sections[current_key] = "\n".join(current_lines).strip()

    return sections


def parse_headline(text: str) -> dict:
    result = {"title": "Edition", "subhead": "", "body": ""}
    for line in text.splitlines():
        if line.startswith("Title:"):
            result["title"] = line[6:].strip()
        elif line.startswith("Subhead:"):
            result["subhead"] = line[8:].strip()
        elif line.startswith("Body:"):
            result["body"] = line[5:].strip()
        elif result["body"] and line.strip():
            result["body"] += " " + line.strip()
    return result


# ── HTML broadsheet ───────────────────────────────────────────────────────────

def nl2br(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>\n")


def paragraphs(text: str) -> str:
    """Wrap double-newline-separated blocks in <p> tags. Single newlines become <br>."""
    if not text:
        return ""
    blocks = re.split(r'\n{2,}', text.strip())
    return "\n".join(
        f"<p>{b.strip().replace(chr(10), '<br>')}</p>"
        for b in blocks if b.strip()
    )


def build_timetable_html() -> str:
    """Pure-data timetable for the right rail — no LLM."""
    if not _SCHEDULE_AVAILABLE:
        return "<p><em>Schedule unavailable.</em></p>"

    sched = get_schedule_data()
    lines = []

    day_tone = f"Day {sched['academy_day']} — {sched['tone']}"
    lines.append(f"<p><strong>{sched['weekday_name']}</strong> &middot; {day_tone}</p>")

    cls_now = sched["class_now"]
    if cls_now:
        subj, prof, room = cls_now
        lines.append(f"<p>&#9679;&nbsp;<strong>Now:</strong> {subj}<br><em>{prof}</em></p>")
    else:
        block_pretty = sched["block"].replace("_", " ").title()
        lines.append(f"<p>&#9675;&nbsp;<em>{block_pretty} — no class</em></p>")

    cls_next = sched["class_next"]
    if cls_next:
        subj, prof, _ = cls_next
        next_label = sched["class_next_time"]
        if sched["class_next_day"] != sched["weekday_name"]:
            next_label = f"{sched['class_next_day']} {next_label}"
        lines.append(f"<p>&#8594;&nbsp;<strong>{next_label}:</strong> {subj}<br><em>{prof}</em></p>")

    club = sched["club"]
    if club:
        lines.append(f"<p>&#9733;&nbsp;<strong>Tonight (7 PM):</strong> {club[0]}</p>")
    else:
        lines.append(f"<p>&#9733;&nbsp;<em>No club tonight</em></p>")

    practice = sched["practice"]
    if practice:
        lines.append(f"<p style='margin-top:5pt; border-top: 1px solid #ddd; padding-top:4pt;'>"
                     f"<strong>Practice:</strong> {practice['name']}<br>"
                     f"<em>{practice['prompt']}</em><br>"
                     f"Belief: {practice['belief']}</p>")

    return "\n".join(lines)


def build_html(sections: dict, sparky: str, meta: dict) -> str:
    hl          = parse_headline(sections.get("HEADLINE", ""))
    gossip      = sections.get("GOSSIP", "")
    feature     = sections.get("FEATURE", "")
    barometer   = sections.get("BAROMETER", "")
    exchange    = sections.get("EXCHANGE", "")
    timetable   = build_timetable_html()
    classifieds = sections.get("CLASSIFIEDS", "")
    weather     = sections.get("WEATHER", "")
    forecast    = sections.get("FORECAST", "")
    market      = sections.get("MARKET", "")
    correction  = sections.get("CORRECTION", "")
    missing     = sections.get("MISSING", "")

    date_obj  = datetime.strptime(meta["date_str"], "%Y-%m-%d")
    date_long = date_obj.strftime("%A, %B %-d, %Y")

    sparky_html = paragraphs(sparky) if sparky else "<p><em>(a sleeping dot)</em></p>"

    # Extract feature title/byline if the LLM included them
    feature_title = ""
    feature_byline = ""
    feature_body = feature
    if feature:
        lines = feature.strip().splitlines()
        if lines and not lines[0].startswith("By ") and len(lines[0]) < 80:
            feature_title = lines[0].strip().strip("*#").strip()
            rest = "\n".join(lines[1:]).strip()
            if rest.startswith("By ") or rest.startswith("*By "):
                byline_line = rest.splitlines()[0]
                feature_byline = byline_line.strip().strip("*").strip()
                feature_body = "\n".join(rest.splitlines()[1:]).strip()
            else:
                feature_body = rest

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>The Bleed — Issue #{meta['issue_number']}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=UnifrakturMaguntia&family=IM+Fell+English:ital@0;1&family=IM+Fell+English+SC&display=swap');

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: 'IM Fell English', Georgia, 'Times New Roman', serif;
    font-size: 10pt;
    background: #e8e2d5;
    color: #111;
    line-height: 1.6;
  }}

  .page {{
    width: 8.5in;
    min-height: 11in;
    margin: 0.25in auto;
    padding: 0.45in 0.5in 0.5in;
    background: #faf5ea;
    box-shadow: 0 2px 16px rgba(0,0,0,0.25);
  }}

  p {{ margin-bottom: 0.55em; }}
  p:last-child {{ margin-bottom: 0; }}

  /* ── MASTHEAD ── */
  .masthead {{
    text-align: center;
    border-bottom: 3px double #111;
    padding-bottom: 6pt;
    margin-bottom: 6pt;
  }}

  .nameplate {{
    font-family: 'UnifrakturMaguntia', 'IM Fell English', serif;
    font-size: 54pt;
    line-height: 1;
    letter-spacing: -1px;
    color: #0a0a0a;
  }}

  .tagline {{
    font-style: italic;
    font-size: 8pt;
    color: #555;
    margin: 3pt 0;
  }}

  .masthead-bar {{
    display: flex;
    justify-content: space-between;
    font-size: 8pt;
    border-top: 1px solid #111;
    border-bottom: 1px solid #111;
    padding: 2.5pt 0;
    margin-top: 4pt;
  }}

  /* ── SECTION LABEL ── */
  .col-head {{
    font-family: 'IM Fell English SC', Georgia, serif;
    font-size: 7.5pt;
    letter-spacing: 1.8px;
    text-transform: uppercase;
    border-bottom: 1px solid #111;
    padding-bottom: 2pt;
    margin-bottom: 6pt;
  }}

  .byline {{
    font-style: italic;
    font-size: 8pt;
    color: #555;
    margin-bottom: 6pt;
  }}

  /* ── ABOVE THE FOLD ── */
  .above-fold {{
    border-bottom: 2px solid #111;
    padding-bottom: 10pt;
    margin-bottom: 10pt;
  }}

  .headline {{
    font-family: 'IM Fell English SC', Georgia, serif;
    font-size: 28pt;
    line-height: 1.05;
    margin-bottom: 5pt;
  }}

  .subhead {{
    font-size: 12pt;
    font-style: italic;
    color: #333;
    margin-bottom: 8pt;
    border-bottom: 1px solid #ccc;
    padding-bottom: 6pt;
  }}

  .headline-body {{
    font-size: 10pt;
    line-height: 1.6;
    column-count: 3;
    column-gap: 18pt;
    column-rule: 1px solid #ccc;
  }}

  /* ── MAIN CONTENT GRID ── */
  /* Row 1: Gossip (wide) | Right rail (narrow) */
  .content-row {{
    display: grid;
    column-gap: 0;
    border-bottom: 1.5px solid #111;
    margin-bottom: 8pt;
  }}

  .row-gossip-feature {{
    grid-template-columns: 3fr 1.1fr;
  }}

  .row-bottom {{
    grid-template-columns: 1.5fr 1fr 1.5fr;
    border-bottom: none;
  }}

  .col {{
    padding: 8pt 14pt 6pt 0;
    border-right: 1px solid #aaa;
  }}

  .col:last-child {{
    border-right: none;
    padding-right: 0;
  }}

  .col + .col {{
    padding-left: 14pt;
    padding-right: 14pt;
  }}

  .col:last-child {{
    padding-left: 14pt;
    padding-right: 0;
  }}

  /* ── GOSSIP ── */
  .gossip-body p {{
    margin-bottom: 0.7em;
  }}

  /* ── FEATURE ── */
  .feature-title {{
    font-family: 'IM Fell English SC', Georgia, serif;
    font-size: 13pt;
    line-height: 1.15;
    margin-bottom: 4pt;
  }}

  /* ── RIGHT RAIL (barometer + exchange stacked) ── */
  .rail-section {{
    margin-bottom: 10pt;
    padding-bottom: 10pt;
    border-bottom: 1px solid #ccc;
  }}

  .rail-section:last-child {{
    border-bottom: none;
    margin-bottom: 0;
    padding-bottom: 0;
  }}

  .rail-body {{
    font-size: 8.5pt;
    line-height: 1.6;
  }}

  .ticker-line {{
    display: flex;
    justify-content: space-between;
    font-size: 8pt;
    line-height: 1.7;
    font-family: 'IM Fell English SC', Georgia, serif;
  }}

  .ticker-line .trend {{
    font-style: normal;
    color: #444;
  }}

  /* ── FORECAST ROW ── */
  .row-forecasts {{
    grid-template-columns: 1fr 1fr 1fr;
    border-bottom: 1.5px solid #111;
    margin-bottom: 8pt;
  }}

  .weather-body {{
    font-size: 9pt;
    line-height: 1.65;
    font-style: italic;
  }}

  .market-ticker {{
    font-family: 'IM Fell English SC', Georgia, serif;
    font-size: 8pt;
    line-height: 1.8;
    border-bottom: 1px solid #ddd;
    margin-bottom: 5pt;
    padding-bottom: 5pt;
  }}

  /* ── BOTTOM STRIP ── */
  .sparky-text {{
    font-size: 8.5pt;
    line-height: 1.6;
    font-style: italic;
    color: #2a2a2a;
  }}

  .correction-box {{
    font-size: 8.5pt;
    line-height: 1.55;
    background: #ede7d8;
    border: 1px solid #bbb;
    padding: 5pt 6pt;
  }}

  .missing-text {{
    font-style: italic;
    font-size: 9pt;
    color: #555;
    line-height: 1.65;
  }}

  /* ── FOOTER ── */
  .footer {{
    text-align: center;
    font-size: 7pt;
    color: #999;
    border-top: 1px solid #ccc;
    padding-top: 5pt;
    margin-top: 8pt;
    font-style: italic;
  }}

  @media print {{
    body {{ background: white; }}
    .page {{ margin: 0; box-shadow: none; padding: 0.4in; }}
  }}
</style>
</head>
<body>
<div class="page">

  <!-- MASTHEAD -->
  <div class="masthead">
    <div class="nameplate">The Bleed</div>
    <div class="tagline">Where the Labyrinth meets the page. Where the page bleeds into the world.</div>
    <div class="masthead-bar">
      <span>Issue #{meta['issue_number']}</span>
      <span>{date_long}</span>
      <span>Belief Exchange: {meta['belief']} / 100</span>
    </div>
  </div>

  <!-- ABOVE THE FOLD: headline + full article in 3 columns -->
  <div class="above-fold">
    <div class="headline">{hl['title']}</div>
    <div class="subhead">{hl['subhead']}</div>
    <div class="headline-body">{paragraphs(hl['body'])}</div>
  </div>

  <!-- ROW 1: Gossip (wide left) + right rail -->
  <div class="content-row row-gossip-feature">

    <div class="col gossip-body">
      <div class="col-head">Gossip &amp; Corridor Whispers</div>
      <div class="byline">Our Social Correspondent, W.E.</div>
      {paragraphs(gossip)}
    </div>

    <div class="col" style="padding-right:0;">
      <div class="rail-section">
        <div class="col-head">The Barometer</div>
        <div class="rail-body">{paragraphs(barometer)}</div>
      </div>
      <div class="rail-section">
        <div class="col-head">The Exchange</div>
        <div class="rail-body">{paragraphs(exchange)}</div>
      </div>
      <div class="rail-section">
        <div class="col-head">Today at the Academy</div>
        <div class="rail-body" style="font-size:8pt; line-height:1.65;">{timetable}</div>
      </div>
    </div>

  </div>

  <!-- ROW 2: Feature (left) + Classifieds (mid) + Sparky/Correction/Missing (right stack) -->
  <!-- ROW 3: Weather | Story Forecast | Predictions Market -->
  <div class="content-row row-forecasts">

    <div class="col">
      <div class="col-head">Academy Meteorological Society</div>
      <div class="weather-body">{paragraphs(weather)}</div>
    </div>

    <div class="col">
      <div class="col-head">Story Forecast</div>
      {paragraphs(forecast)}
    </div>

    <div class="col" style="padding-right:0;">
      <div class="col-head">Thread Futures Market</div>
      <div class="market-ticker">{paragraphs(market)}</div>
    </div>

  </div>

  <!-- ROW 2 (now Row 4): Feature + Classifieds + right stack -->
  <div class="content-row row-bottom">

    <div class="col">
      <div class="col-head">Feature</div>
      {'<div class="feature-title">' + feature_title + '</div>' if feature_title else ''}
      {'<div class="byline">' + feature_byline + '</div>' if feature_byline else ''}
      {paragraphs(feature_body)}
    </div>

    <div class="col">
      <div class="col-head">Classifieds</div>
      {paragraphs(classifieds)}
    </div>

    <div class="col" style="padding-right:0;">
      <div class="rail-section">
        <div class="col-head">Sparky's Corner</div>
        <div class="sparky-text">{sparky_html}</div>
      </div>
      <div class="rail-section">
        <div class="col-head">The Correction</div>
        <div class="correction-box">{paragraphs(correction)}</div>
      </div>
      <div class="rail-section">
        <div class="col-head">The Missing</div>
        <div class="missing-text">{paragraphs(missing)}</div>
      </div>
    </div>

  </div>

  <div class="footer">
    The Bleed is published daily at 6pm Academy time. Accuracy is aspired to. The editors regret most errors once they become apparent.
    Belief Exchange rates reflect close of market. Thread pressures subject to simulation. Issue #{meta['issue_number']}.
    &nbsp;·&nbsp; <em>The Labyrinth of Stories — Where what you believe becomes what is real.</em>
  </div>

</div>
</body>
</html>"""


# ── Telegram ──────────────────────────────────────────────────────────────────

def build_telegram_text(sections: dict, sparky: str, meta: dict) -> str:
    hl = parse_headline(sections.get("HEADLINE", ""))
    date_obj  = datetime.strptime(meta["date_str"], "%Y-%m-%d")
    date_short = date_obj.strftime("%b %-d")

    def esc(text: str) -> str:
        """Minimal HTML escaping for Telegram HTML mode."""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    parts = [
        f"<b>THE BLEED</b> — Issue #{meta['issue_number']}, {date_short}",
        f"Belief Exchange: {meta['belief']} / 100",
        "",
        f"<b>{esc(hl['title'])}</b>",
    ]
    if hl["subhead"]:
        parts.append(f"<i>{esc(hl['subhead'])}</i>")
    if hl["body"]:
        parts += [esc(hl["body"]), ""]

    gossip = sections.get("GOSSIP", "")
    if gossip:
        parts += [f"<b>— Gossip (W.E.) —</b>", esc(gossip[:800] + ("…" if len(gossip) > 800 else "")), ""]

    feature = sections.get("FEATURE", "")
    if feature:
        lines = feature.strip().splitlines()
        title = lines[0].strip().strip("*#").strip() if lines else "Feature"
        body  = "\n".join(lines[1:]).strip()[:600]
        parts += [f"<b>— {esc(title)} —</b>", esc(body) + "…", ""]

    barometer = sections.get("BAROMETER", "")
    if barometer:
        parts += [f"<b>Barometer</b>", esc(barometer), ""]

    exchange = sections.get("EXCHANGE", "")
    if exchange:
        parts += [f"<b>The Exchange</b>", esc(exchange), ""]

    if _SCHEDULE_AVAILABLE:
        sched = get_schedule_data()
        timetable_lines = [f"<b>Today at the Academy</b>",
                           f"{sched['weekday_name']} · Day {sched['academy_day']} ({sched['tone']})"]
        cls_now = sched["class_now"]
        if cls_now:
            timetable_lines.append(f"&#9679; Now: {cls_now[0]} ({cls_now[1]})")
        cls_next = sched["class_next"]
        if cls_next:
            timetable_lines.append(f"&#8594; Next: {cls_next[0]} ({cls_next[1]}, {sched['class_next_time']})")
        club = sched["club"]
        if club:
            timetable_lines.append(f"&#9733; Tonight 7 PM: {club[0]}")
        practice = sched["practice"]
        if practice:
            timetable_lines.append(f"Practice: {practice['name']} — {practice['prompt']}")
        parts += timetable_lines + [""]

    classifieds = sections.get("CLASSIFIEDS", "")
    if classifieds:
        parts += [f"<b>Classifieds</b>", esc(classifieds), ""]

    if sparky:
        parts += [f"<b>Sparky:</b>", f"<i>{esc(sparky)}</i>", ""]

    forecast = sections.get("FORECAST", "")
    if forecast:
        parts += [f"<b>Story Forecast</b>", esc(forecast[:600]) + "…", ""]

    market = sections.get("MARKET", "")
    if market:
        parts += [f"<b>Thread Futures</b>", esc(market[:500]) + "…", ""]

    missing = sections.get("MISSING", "")
    if missing:
        parts += [f"<b>The Missing</b>", f"<i>{esc(missing)}</i>"]

    return "\n".join(parts)


def send_telegram(text: str, cfg: dict):
    token   = cfg.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = cfg.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        print("  ℹ Telegram not configured (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID) — skipping.")
        return

    # Telegram message limit: 4096 chars
    if len(text) > 4000:
        text = text[:3990] + "\n…"

    url     = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text, "parse_mode": "HTML"}).encode()

    try:
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            resp = json.loads(r.read())
        if resp.get("ok"):
            print("  ✓ Telegram edition sent.")
        else:
            print(f"  ⚠ Telegram error: {resp}")
    except Exception as ex:
        print(f"  ⚠ Telegram send failed: {ex}")


# ── CUPS print ────────────────────────────────────────────────────────────────

CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def html_to_pdf(html_path: Path) -> Path:
    """Convert HTML to PDF. Tries wkhtmltopdf, then Chrome headless."""
    pdf_path = html_path.with_suffix(".pdf")

    if shutil.which("wkhtmltopdf"):
        r = subprocess.run(
            ["wkhtmltopdf", "--page-size", "Letter", "--quiet",
             str(html_path), str(pdf_path)],
            capture_output=True, timeout=30
        )
        if r.returncode == 0:
            return pdf_path

    chrome = CHROME_PATH if os.path.exists(CHROME_PATH) else shutil.which("google-chrome") or shutil.which("chromium")
    if chrome:
        r = subprocess.run(
            [chrome, "--headless", "--disable-gpu", "--no-sandbox",
             f"--print-to-pdf={pdf_path}",
             "--print-to-pdf-no-header",
             str(html_path)],
            capture_output=True, timeout=45
        )
        if r.returncode == 0 and pdf_path.exists():
            return pdf_path

    return html_path  # fallback: return original HTML


def print_to_cups(html_path: Path, cfg: dict):
    printer = cfg.get("BLEED_PRINTER", "")
    if not printer:
        print("  ℹ CUPS print not configured (BLEED_PRINTER) — skipping.")
        return

    print("  Converting to PDF...")
    print_file = html_to_pdf(html_path)

    result = subprocess.run(
        ["lp", "-d", printer, "-o", "media=Letter", str(print_file)],
        capture_output=True, text=True, timeout=15
    )
    if result.returncode == 0:
        print(f"  ✓ Sent to printer: {printer}")
    else:
        print(f"  ⚠ Print failed: {result.stderr.strip()}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    today    = date.today()
    date_str = today.strftime("%Y-%m-%d")
    now_str  = datetime.now().strftime("%Y-%m-%d %H:%M")

    print(f"The Bleed — {now_str}")

    cfg = load_config()

    # Skip if already published today (unless --force)
    ISSUES_DIR.mkdir(parents=True, exist_ok=True)
    issue_path = ISSUES_DIR / f"{date_str}.html"
    if issue_path.exists() and "--force" not in sys.argv:
        print(f"  ✓ Issue already published today. Use --force to regenerate.")
        return

    issue_number = get_issue_number()
    print(f"  Preparing issue #{issue_number}...")

    # ── Read data sources ────────────────────────────────────────────────────
    player_data = get_player_data(cfg)

    heartbeat = read_file_safe(WORKSPACE_DIR / "HEARTBEAT.md", 100)
    pulse     = extract_pulse_section(heartbeat)[:1200]
    health    = extract_health_from_pulse(pulse) or "(health data not available today)"

    tick_queue       = read_file_safe(WORKSPACE_DIR / "memory" / "tick-queue.md", 40)
    thread_summary   = get_thread_summary()
    entity_standings = get_entity_standings()
    sparky           = get_sparky_shiny(date_str)
    forecast         = get_weather_forecast_from_heartbeat()
    market_odds      = calculate_market_odds()

    # Format market odds for prompt injection
    market_odds_formatted = "\n".join(
        f"- {o['name']} ({o['phase']}, combined Belief {o['belief']}): "
        f"Will this thread significantly stir this week? YES: {o['yes']}% / NO: {o['no']}%"
        + (f"  Next beat: {o['beat']}" if o['beat'] else "")
        for o in market_odds
    ) or "(no thread data available)"

    data = {
        "date_str":              date_str,
        "issue_number":          issue_number,
        "player":                player_data,
        "pulse":                 pulse,
        "health":                health,
        "forecast":              forecast or "(forecast not yet loaded — check pulse)",
        "tick_queue":            tick_queue or "(no simulation activity since last session)",
        "thread_summary":        thread_summary,
        "entity_standings":      entity_standings,
        "market_odds_formatted": market_odds_formatted,
    }

    # ── Generate content ─────────────────────────────────────────────────────
    print("  Generating newspaper content...")
    sections = generate_content(data)

    if not sections:
        print("  ⚠ Agent returned no content. Check logs.")
        return

    # ── Build HTML ───────────────────────────────────────────────────────────
    meta = {
        "date_str":     date_str,
        "issue_number": issue_number,
        "belief":       player_data.get("belief", "?"),
    }
    html = build_html(sections, sparky, meta)

    # ── Save ─────────────────────────────────────────────────────────────────
    issue_path.write_text(html)
    save_issue_number(issue_number)
    print(f"  ✓ Issue #{issue_number} saved → {issue_path}")

    # ── Telegram edition ─────────────────────────────────────────────────────
    telegram_text = build_telegram_text(sections, sparky, meta)
    send_telegram(telegram_text, cfg)

    # ── CUPS print ───────────────────────────────────────────────────────────
    print_to_cups(issue_path, cfg)

    print(f"  ✓ The Bleed #{issue_number} published.")


if __name__ == "__main__":
    main()

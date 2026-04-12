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

SCRIPT_DIR   = Path(__file__).parent
WORKSPACE_DIR = SCRIPT_DIR.parent

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

def call_agent(prompt: str) -> str:
    result = subprocess.run(
        ["openclaw", "agent", "--local", "--agent", "enchantify", "-m", prompt],
        capture_output=True, text=True, timeout=120
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
Headlines are specific and factual. The gossip column has a slant. The classifieds are cryptic.
This is not a parody — it's a real paper. The extraordinary is covered with the same deadpan
reportage as the ordinary.

DATA FEEDS (synthesize into journalism — do not quote data directly):

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

HEALTH SIGNALS (map to Academy conditions):
{data['health']}

---

Write the newspaper in EXACTLY this format. Start with ===HEADLINE=== — no preamble.
Keep each section SHORT — this is a physical newspaper.

===HEADLINE===
Title: [specific, factual headline — 8 words max]
Subhead: [one sentence expanding the headline]
Body: [2-3 sentences. Report on the dominant thread or simulation activity. Use Academy setting, not meta-language. No "the simulation" — just "sources report" or "The Observatory has been quiet."]

===GOSSIP===
[3-4 sentences in the voice of W.E. — Wicker Eddies — as social columnist. He reports true things slanted. He always knows more than he lets on. He never mentions himself directly. Byline already added in layout.]

===BAROMETER===
[Report health/biometric data AS Academy conditions. Steps = distance covered on Academy grounds. Sleep/HRV = student vitality index. Weather from heartbeat = atmospheric pressure in the Labyrinth. 3-4 short lines, like a weather report.]

===EXCHANGE===
[The Belief Exchange — like a market ticker for narrative influence. List 4-5 entities with Belief scores as prices. Include at least one moving (rising or falling) with a one-word trend indicator. One sentence on overall market conditions.]

===CLASSIFIEDS===
[3 cryptic classified notices. Each under 20 words. Labels: LOST: / FOUND: / NOTICE: / SEEKING: / WARNING: etc. These seed story hooks — things the player might investigate. They should feel like real classifieds from a slightly eerie school.]

===CORRECTION===
[One formal correction. The Bleed takes accuracy seriously. Can be from yesterday's edition or a general clarification. Deadpan and specific. 1-2 sentences max.]

===MISSING===
[Threads currently dormant or unengaged — reported as "no word from [person/place] this week." 1-3 lines. The quietest column. Only notes absence, never explains it.]"""

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


def build_html(sections: dict, sparky: str, meta: dict) -> str:
    hl          = parse_headline(sections.get("HEADLINE", ""))
    gossip      = sections.get("GOSSIP", "")
    barometer   = sections.get("BAROMETER", "")
    exchange    = sections.get("EXCHANGE", "")
    classifieds = sections.get("CLASSIFIEDS", "")
    correction  = sections.get("CORRECTION", "")
    missing     = sections.get("MISSING", "")

    date_obj  = datetime.strptime(meta["date_str"], "%Y-%m-%d")
    date_long = date_obj.strftime("%A, %B %-d, %Y")

    sparky_html = nl2br(sparky) if sparky else "<em>(a sleeping dot)</em>"

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
    font-size: 9.5pt;
    background: #e8e2d5;
    color: #111;
  }}

  .page {{
    width: 8.5in;
    min-height: 11in;
    margin: 0.25in auto;
    padding: 0.45in 0.5in 0.4in;
    background: #faf5ea;
    box-shadow: 0 2px 16px rgba(0,0,0,0.25);
  }}

  /* ── MASTHEAD ── */
  .masthead {{
    text-align: center;
    border-bottom: 3px double #111;
    padding-bottom: 6pt;
    margin-bottom: 5pt;
  }}

  .nameplate {{
    font-family: 'UnifrakturMaguntia', 'IM Fell English', serif;
    font-size: 52pt;
    line-height: 1;
    letter-spacing: -1px;
    color: #0a0a0a;
  }}

  .tagline {{
    font-style: italic;
    font-size: 7.5pt;
    color: #555;
    margin: 3pt 0;
  }}

  .masthead-bar {{
    display: flex;
    justify-content: space-between;
    font-size: 7.5pt;
    border-top: 1px solid #111;
    border-bottom: 1px solid #111;
    padding: 2pt 0;
    margin-top: 4pt;
  }}

  /* ── ABOVE THE FOLD ── */
  .above-fold {{
    border-bottom: 2px solid #111;
    padding-bottom: 9pt;
    margin-bottom: 8pt;
  }}

  .headline {{
    font-family: 'IM Fell English SC', Georgia, serif;
    font-size: 26pt;
    line-height: 1.05;
    margin-bottom: 4pt;
  }}

  .subhead {{
    font-size: 11pt;
    font-style: italic;
    color: #333;
    margin-bottom: 6pt;
  }}

  .headline-body {{
    font-size: 9.5pt;
    line-height: 1.55;
    column-count: 2;
    column-gap: 18pt;
  }}

  /* ── BELOW THE FOLD ── */
  .below-fold {{
    display: grid;
    grid-template-columns: 2.1fr 1fr 1fr;
    column-gap: 0;
    border-bottom: 1.5px solid #111;
    margin-bottom: 7pt;
  }}

  .col {{
    padding: 0 12pt 6pt 0;
    border-right: 1px solid #999;
  }}

  .col:last-child {{
    border-right: none;
    padding-right: 0;
  }}

  .col + .col {{
    padding-left: 12pt;
  }}

  .col-head {{
    font-family: 'IM Fell English SC', Georgia, serif;
    font-size: 7.5pt;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    border-bottom: 1px solid #111;
    padding-bottom: 2pt;
    margin-bottom: 4pt;
  }}

  .byline {{
    font-style: italic;
    font-size: 7.5pt;
    color: #666;
    margin-bottom: 4pt;
  }}

  /* ── BOTTOM STRIP ── */
  .bottom-strip {{
    display: grid;
    grid-template-columns: 1fr 1fr 2fr;
    column-gap: 0;
  }}

  .bottom-strip .col {{
    padding-bottom: 0;
  }}

  .sparky-text {{
    font-size: 8pt;
    line-height: 1.55;
    font-style: italic;
    color: #2a2a2a;
  }}

  .correction-box {{
    font-size: 8pt;
    line-height: 1.5;
    background: #ede7d8;
    border: 1px solid #bbb;
    padding: 4pt 5pt;
  }}

  .missing-text {{
    font-style: italic;
    font-size: 8.5pt;
    color: #555;
    line-height: 1.6;
  }}

  /* ── FOOTER ── */
  .footer {{
    text-align: center;
    font-size: 6.5pt;
    color: #999;
    border-top: 1px solid #ccc;
    padding-top: 4pt;
    margin-top: 7pt;
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

  <!-- ABOVE THE FOLD -->
  <div class="above-fold">
    <div class="headline">{hl['title']}</div>
    <div class="subhead">{hl['subhead']}</div>
    <div class="headline-body">{nl2br(hl['body'])}</div>
  </div>

  <!-- BELOW THE FOLD -->
  <div class="below-fold">

    <div class="col">
      <div class="col-head">Gossip &amp; Corridor Whispers</div>
      <div class="byline">Our Social Correspondent, W.E.</div>
      <p>{nl2br(gossip)}</p>
    </div>

    <div class="col">
      <div class="col-head">The Barometer</div>
      <p style="font-size:8.5pt; line-height:1.55;">{nl2br(barometer)}</p>
      <br>
      <div class="col-head">The Exchange</div>
      <p style="font-size:8pt; line-height:1.6;">{nl2br(exchange)}</p>
    </div>

    <div class="col">
      <div class="col-head">Classifieds</div>
      <p style="font-size:8.5pt; line-height:1.7;">{nl2br(classifieds)}</p>
    </div>

  </div>

  <!-- BOTTOM STRIP -->
  <div class="bottom-strip">

    <div class="col">
      <div class="col-head">Sparky's Corner</div>
      <div class="sparky-text">{sparky_html}</div>
    </div>

    <div class="col">
      <div class="col-head">The Correction</div>
      <div class="correction-box">{nl2br(correction)}</div>
    </div>

    <div class="col">
      <div class="col-head">The Missing</div>
      <div class="missing-text">{nl2br(missing)}</div>
    </div>

  </div>

  <div class="footer">
    The Bleed is published daily at 6pm Academy time. Accuracy is aspired to. The editors regret most errors once they become apparent.
    Belief Exchange rates reflect close of market. Thread pressures subject to simulation. Issue #{meta['issue_number']}.
    <br><em>The Labyrinth of Stories — Where what you believe becomes what is real.</em>
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
        parts += [f"<b>— Gossip (W.E.) —</b>", esc(gossip), ""]

    barometer = sections.get("BAROMETER", "")
    if barometer:
        parts += [f"<b>Barometer</b>", esc(barometer), ""]

    exchange = sections.get("EXCHANGE", "")
    if exchange:
        parts += [f"<b>The Exchange</b>", esc(exchange), ""]

    classifieds = sections.get("CLASSIFIEDS", "")
    if classifieds:
        parts += [f"<b>Classifieds</b>", esc(classifieds), ""]

    if sparky:
        parts += [f"<b>Sparky:</b>", f"<i>{esc(sparky)}</i>", ""]

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

def print_to_cups(html_path: Path, cfg: dict):
    printer = cfg.get("BLEED_PRINTER", "")
    if not printer:
        print("  ℹ CUPS print not configured (BLEED_PRINTER) — skipping.")
        return

    print_file = str(html_path)

    # Prefer PDF via wkhtmltopdf if available
    if shutil.which("wkhtmltopdf"):
        pdf_path = html_path.with_suffix(".pdf")
        result = subprocess.run(
            ["wkhtmltopdf", "--page-size", "Letter", "--quiet",
             str(html_path), str(pdf_path)],
            capture_output=True, timeout=30
        )
        if result.returncode == 0:
            print_file = str(pdf_path)

    result = subprocess.run(
        ["lp", "-d", printer, "-o", "media=Letter", print_file],
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

    data = {
        "date_str":        date_str,
        "issue_number":    issue_number,
        "player":          player_data,
        "pulse":           pulse,
        "health":          health,
        "tick_queue":      tick_queue or "(no simulation activity since last session)",
        "thread_summary":  thread_summary,
        "entity_standings": entity_standings,
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

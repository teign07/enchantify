#!/usr/bin/env python3
"""
mission-control.py — Enchantify Mission Control Dashboard

Reads live workspace data and generates a self-refreshing HTML dashboard.

Usage:
  python3 scripts/mission-control.py           # generate → mission-control.html
  python3 scripts/mission-control.py --open    # generate + open in browser
  python3 scripts/mission-control.py --serve   # serve on http://localhost:9191
"""
import os
import re
import sys
import json
import shutil
import subprocess
import argparse
from pathlib import Path
from datetime import datetime, date, timedelta

BASE        = Path(__file__).parent.parent
THREADS_F   = BASE / "lore" / "threads.md"
REGISTER_F  = BASE / "lore" / "world-register.md"
QUEUE_F     = BASE / "memory" / "tick-queue.md"
PATTERNS_F  = BASE / "memory" / "patterns.md"
ISSUES_DIR  = BASE / "bleed" / "issues"
LOGS_DIR    = BASE / "logs"
PLAYERS_DIR = BASE / "players"

_OPENCLAW = shutil.which("openclaw") or "/opt/homebrew/bin/openclaw"

# ── Chapter colours ───────────────────────────────────────────────────────────
CHAPTER_COLOR = {
    "riddlewind": "#7c3aed",
    "emberheart":  "#dc2626",
    "mossbloom":   "#15803d",
    "tidecrest":   "#0284c7",
    "duskthorn":   "#9f1239",
}

PHASE_COLOR = {
    "dormant":    "#3f3f46",
    "setup":      "#4e6b8a",
    "rising":     "#92681a",
    "climax":     "#c2410c",
    "resolution": "#15803d",
    "permanent":  "#374151",
}

PHASE_ORDER = ["dormant", "setup", "rising", "climax", "resolution"]
PHASE_PCT   = {"dormant": 0, "setup": 20, "rising": 45, "climax": 70, "resolution": 92, "permanent": 0}

# ── Data parsers ──────────────────────────────────────────────────────────────

def read(path: Path) -> str:
    return path.read_text(errors="replace") if path.exists() else ""


def parse_threads() -> list[dict]:
    text = read(THREADS_F)
    register = read(REGISTER_F)

    # Build belief lookup from world-register Active Threads
    belief: dict[str, int] = {}
    active_m = re.search(r'## Active Threads(.*?)(?=^## |\Z)', register, re.DOTALL | re.MULTILINE)
    if active_m:
        for m in re.finditer(r'^\|\s*([^|]+?)\s*\|\s*Thread\s*\|\s*(\d+)\s*\|',
                             active_m.group(1), re.MULTILINE | re.IGNORECASE):
            belief[m.group(1).strip().lower()] = int(m.group(2))

    threads = []
    for section in re.split(r'^## Thread: ', text, flags=re.MULTILINE)[1:]:
        lines = section.strip().splitlines()
        name = lines[0].strip() if lines else "?"

        def field(pat):
            m = re.search(pat, section)
            return m.group(1).strip() if m else ""

        phase_raw = field(r'\*\*phase:\*\*\s*(.+)')
        phase_word = phase_raw.split()[0].lower() if phase_raw else "dormant"
        if phase_word not in PHASE_ORDER and phase_word != "permanent":
            phase_word = "dormant"

        born_raw  = field(r'\*\*born:\*\*\s*(\S+)')
        closed_raw = field(r'\*\*closed:\*\*\s*(\S+)')
        b = belief.get(name.lower(), 0)

        # Age badge
        age_note = ""
        if born_raw and born_raw not in ("—", "-", ""):
            try:
                born = date.fromisoformat(born_raw)
                days = (date.today() - born).days
                if days <= 7:
                    age_note = "new"
            except ValueError:
                pass

        threads.append({
            "name":         name,
            "phase":        phase_word,
            "phase_raw":    phase_raw,
            "belief":       b,
            "pressure":     field(r'\*\*pressure:\*\*\s*(.+)'),
            "nothing":      field(r'\*\*Nothing pressure:\*\*\s*(.+)'),
            "next_beat":    field(r'\*\*Next beat:\*\*\s*(.+)'),
            "last_advanced":field(r'\*\*Last advanced:\*\*\s*(.+)'),
            "born":         born_raw,
            "closed":       closed_raw,
            "age_note":     age_note,
            "npc_anchor":   field(r'\*\*npc_anchor:\*\*\s*(.+)'),
        })

    # Sort: climax first, then by belief desc
    def sort_key(t):
        pi = PHASE_ORDER.index(t["phase"]) if t["phase"] in PHASE_ORDER else 0
        return (-pi, -t["belief"])

    threads.sort(key=sort_key)
    return threads


def parse_entities() -> tuple[list, list, list]:
    """Returns (npcs, threads_register, talismans)."""
    text = read(REGISTER_F)
    npcs, threads_r, talismans = [], [], []

    row_re = re.compile(
        r'^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|\s*([^|]*)\s*\|',
        re.MULTILINE
    )

    in_talismans = False
    in_active    = False
    for line in text.splitlines():
        if "## Chapter Talismans" in line:
            in_talismans = True; in_active = False; continue
        if "## Active Threads" in line:
            in_active = True; in_talismans = False; continue
        if line.startswith("## ") and "Active Threads" not in line and "Chapter Talismans" not in line:
            in_talismans = False; in_active = False

        m = row_re.match(line)
        if not m: continue
        name, etype, bstr, notes = m.group(1).strip(), m.group(2).strip(), m.group(3), m.group(4).strip()
        if name.lower() in ("entity", "talisman", "name", "---", ""): continue
        try: b = int(bstr)
        except ValueError: continue

        thread_m = re.search(r'\[thread:([^\]]+)\]', notes)
        threads_tag = [t.strip() for t in thread_m.group(1).split(",")] if thread_m else []
        clean_notes = re.sub(r'\[thread:[^\]]+\]', '', notes).strip().strip(";").strip()

        if in_talismans:
            chapter = etype.strip().lower()
            talismans.append({
                "name": name, "chapter": chapter, "belief": b,
                "color": CHAPTER_COLOR.get(chapter, "#555"),
                "philosophy": clean_notes[:80],
            })
        elif in_active:
            pass  # handled in parse_threads
        else:
            npcs.append({
                "name": name, "type": etype, "belief": b,
                "threads": threads_tag, "notes": clean_notes[:100],
            })

    npcs.sort(key=lambda x: -x["belief"])
    talismans.sort(key=lambda x: -x["belief"])
    return npcs, talismans


def parse_player(name: str = "bj") -> dict:
    text = read(PLAYERS_DIR / f"{name}.md")
    if not text: return {}

    def field(pat, default="?"):
        m = re.search(pat, text)
        return m.group(1).strip() if m else default

    # Quests from Inside Cover
    cover_m = re.search(r'## The Inside Cover\n(.*?)(?=\n##|\Z)', text, re.DOTALL)
    quests = []
    if cover_m:
        for m in re.finditer(r'\|\s*\*\*([^*]+)\*\*\s*\|([^|]*)\|\s*\*\*ACTIVE\*\*', cover_m.group(1)):
            quests.append({"npc": m.group(1).strip(), "desc": m.group(2).strip()[:60]})

    # Fae margin
    margin_m = re.search(r'## The Margin\n(.*?)(?=\n##|\Z)', text, re.DOTALL)
    bargains = []
    if margin_m:
        for m in re.finditer(r'^\|\s*([^|*][^|]*)\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|',
                             margin_m.group(1), re.MULTILINE):
            fae, gave, terms, deadline, status = [x.strip() for x in m.groups()]
            if fae and not fae.startswith("*"):
                bargains.append({"fae": fae, "status": status, "deadline": deadline})

    return {
        "name":    name,
        "belief":  field(r'\*\*Belief:\*\*\s*(\d+)', "?"),
        "chapter": field(r'\*\*Chapter:\*\*\s*(\S+)', "?"),
        "tutorial":field(r'\*\*Tutorial Progress:\*\*\s*(\S+)', "?"),
        "quests":  quests,
        "bargains":bargains,
        "compass_total": field(r'\*\*Total runs:\*\*\s*(\d+)', "0"),
        "compass_last":  field(r'\*\*Last run:\*\*\s*(.+)', "never"),
    }


def parse_tick_queue(limit: int = 30) -> list[dict]:
    text = read(QUEUE_F)
    entries = []
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("*"):
            continue
        if not line.startswith("-"):
            continue

        entry_type = "normal"
        if "[THREAD ESCALATION" in line: entry_type = "escalation"
        elif "[THREAD COOLING"   in line: entry_type = "cooling"
        elif "[THREAD SEED"      in line: entry_type = "seed"
        elif "[FAE DEBT"         in line: entry_type = "fae"
        elif "[PRIORITY: HIGH]"  in line: entry_type = "priority"
        elif "[Pact War"         in line: entry_type = "war"
        elif "[Talisman"         in line: entry_type = "talisman"
        elif "[Belief Investment]" in line: entry_type = "invest"
        elif "[Beat:"            in line: entry_type = "beat"
        elif "[Thread:"          in line: entry_type = "thread"
        elif "[world-pulse]"     in line: entry_type = "pulse"

        entries.append({"text": line[2:].strip(), "type": entry_type})
        if len(entries) >= limit:
            break

    return entries  # already reversed (newest first)


def parse_bleed_status() -> dict:
    today = date.today().strftime("%Y-%m-%d")
    last_issue = ""
    delivered  = False

    if ISSUES_DIR.exists():
        htmls = sorted(ISSUES_DIR.glob("*.html"))
        if htmls:
            last_issue = htmls[-1].stem
            # Check for delivered flag
            flag = ISSUES_DIR / f"{last_issue}.delivered"
            if flag.exists():
                delivered = True
            # Also count as delivered if today's exists and bleed.log says so
            if last_issue == today:
                log = read(LOGS_DIR / "bleed.log")
                if "already published" in log or "Telegram" in log:
                    delivered = True

    issue_n = ""
    num_f = BASE / "bleed" / "issue-number.txt"
    if num_f.exists():
        issue_n = num_f.read_text().strip()

    return {
        "last_issue": last_issue,
        "today": today,
        "is_today": last_issue == today,
        "delivered": delivered,
        "issue_number": issue_n,
    }


def parse_cron_jobs() -> list[dict]:
    jobs = []
    try:
        result = subprocess.run(
            [_OPENCLAW, "cron", "list", "--json"],
            capture_output=True, text=True, timeout=10
        )
        data = json.loads(result.stdout)
        items = data if isinstance(data, list) else data.get("jobs", data.get("data", []))
        for j in items:
            name   = j.get("name", "?")
            status = j.get("status", "?")
            last   = j.get("last", j.get("lastRun", ""))
            nxt    = j.get("next", j.get("nextRun", ""))
            agent  = j.get("agentId", j.get("agent_id", ""))
            # Only show enchantify jobs
            if agent and "enchantify" not in str(agent).lower():
                continue
            jobs.append({
                "name":   name[:40],
                "status": status,
                "last":   last,
                "next":   nxt,
            })
    except Exception:
        # Fallback: parse plain-text output
        try:
            result = subprocess.run(
                [_OPENCLAW, "cron", "list"],
                capture_output=True, text=True, timeout=10
            )
            for line in result.stdout.splitlines():
                if "enchantify" not in line.lower():
                    continue
                parts = line.split()
                if len(parts) < 3:
                    continue
                jobs.append({
                    "name":   " ".join(parts[1:5])[:40],
                    "status": "ok" if "ok" in line.lower() else "?",
                    "last":   "",
                    "next":   "",
                })
        except Exception:
            pass
    return jobs


# ── HTML generation ───────────────────────────────────────────────────────────

def phase_bar(phase: str, belief: int) -> str:
    """Return an SVG phase bar showing belief position across four bands."""
    if phase == "permanent":
        return '<div class="phase-bar permanent"><span>permanent</span></div>'

    pct  = min(100, max(0, belief * 1.5))  # rough visual fill (belief 65 = 100%)
    color = PHASE_COLOR.get(phase, "#555")
    label = phase.upper()

    bands = [
        ("#3f3f46", 8,  "D"),
        ("#4e6b8a", 20, "S"),
        ("#92681a", 25, "R"),
        ("#c2410c", 25, "C"),
        ("#15803d", 22, "Re"),
    ]
    band_html = "".join(
        f'<div class="band" style="width:{w}%;background:{c};opacity:0.35" title="{t}"></div>'
        for c, w, t in bands
    )

    return f'''<div class="phase-bar-wrap">
      <div class="phase-bands">{band_html}</div>
      <div class="phase-fill" style="width:{pct:.0f}%;background:{color}"></div>
      <div class="phase-label" style="color:{color}">{label} · {belief}</div>
    </div>'''


def entry_class(t: str) -> str:
    return {
        "escalation": "entry-escalation",
        "cooling":    "entry-cooling",
        "seed":       "entry-seed",
        "fae":        "entry-fae",
        "priority":   "entry-priority",
        "war":        "entry-war",
        "beat":       "entry-beat",
        "thread":     "entry-thread",
        "talisman":   "entry-talisman",
        "invest":     "entry-invest",
        "pulse":      "entry-pulse",
    }.get(t, "entry-normal")


def h(s: str) -> str:
    """HTML-escape."""
    return (str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def render_thread_card(t: dict) -> str:
    color  = PHASE_COLOR.get(t["phase"], "#555")
    badge  = f'<span class="badge-new">new</span>' if t["age_note"] == "new" else ""
    anchor = f'<div class="card-anchor">{h(t["npc_anchor"])}</div>' if t["npc_anchor"] else ""
    beat   = h(t["next_beat"][:160]) if t["next_beat"] else "—"
    last   = h(t["last_advanced"]) if t["last_advanced"] else "never"
    nothing_low = "low" in t["nothing"].lower() if t["nothing"] else True
    nothing_dot = f'<span class="nothing-dot" style="color:{("var(--nothing)" if not nothing_low else "var(--muted)")}" title="Nothing pressure: {h(t["nothing"])}">◆</span>'

    return f'''<div class="card" style="border-color:{color}22;--phase-color:{color}">
      <div class="card-header">
        <div class="card-title" style="color:{color}">{h(t["name"])}{badge}</div>
        {nothing_dot}
      </div>
      {anchor}
      {phase_bar(t["phase"], t["belief"])}
      <div class="card-beat">{beat}</div>
      <div class="card-meta">last advanced: {last}</div>
    </div>'''


def render_talisman_bar(tal: dict, max_belief: int) -> str:
    pct   = min(100, int(tal["belief"] / max(max_belief, 1) * 100))
    color = tal["color"]
    return f'''<div class="tal-row">
      <div class="tal-name" style="color:{color}">{h(tal["name"])}</div>
      <div class="tal-bar-wrap">
        <div class="tal-bar" style="width:{pct}%;background:{color}"></div>
      </div>
      <div class="tal-belief">{tal["belief"]}</div>
      <div class="tal-chapter" style="color:{color}">{h(tal["chapter"].title())}</div>
    </div>'''


def render_entity_row(e: dict) -> str:
    b = e["belief"]
    # Belief dot intensity
    if b >= 30:   dot, dc = "●●●", "var(--climax)"
    elif b >= 15: dot, dc = "●●○", "var(--rising)"
    elif b >= 5:  dot, dc = "●○○", "var(--setup)"
    else:         dot, dc = "○○○", "var(--muted)"

    thread_tags = " ".join(
        f'<span class="tag">{h(tid)}</span>'
        for tid in e["threads"]
        if tid != "academy-daily"
    ) if e["threads"] else ""

    return f'''<tr>
      <td><span style="color:{dc};font-size:.7rem">{dot}</span></td>
      <td class="ent-name">{h(e["name"])}</td>
      <td class="ent-type muted">{h(e["type"])}</td>
      <td class="ent-belief">{b}</td>
      <td class="ent-tags">{thread_tags}</td>
    </tr>'''


def render_queue_entry(entry: dict) -> str:
    css  = entry_class(entry["type"])
    text = h(entry["text"])
    # Bold any **..** markers
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    # Italicise *..* markers
    text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
    return f'<div class="entry {css}">{text}</div>'


def render_cron_row(job: dict) -> str:
    status = job["status"].lower()
    dot = "🟢" if status in ("ok", "success") else ("🔴" if "fail" in status or "error" in status else "⚪")
    last = h(job["last"][:16]) if job["last"] else "—"
    nxt  = h(job["next"][:16]) if job["next"] else "—"
    return f'''<tr>
      <td style="font-size:1rem">{dot}</td>
      <td class="cron-name">{h(job["name"])}</td>
      <td class="muted">{last}</td>
      <td class="muted">{nxt}</td>
    </tr>'''


# ── Full page ─────────────────────────────────────────────────────────────────

def build_html(threads, npcs, talismans, player, queue, bleed, crons) -> str:
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Thread cards
    thread_cards = "".join(render_thread_card(t) for t in threads)

    # Talisman bars
    max_tal = max((t["belief"] for t in talismans), default=1)
    tal_bars = "".join(render_talisman_bar(t, max_tal) for t in talismans)

    # Top-N entities
    top_npcs = "".join(render_entity_row(e) for e in npcs[:25])

    # Queue entries
    queue_html = "".join(render_queue_entry(e) for e in queue) or '<div class="muted">Queue is clear.</div>'

    # Player quests
    quest_html = ""
    for q in player.get("quests", []):
        quest_html += f'<div class="quest-row"><span class="quest-npc">{h(q["npc"])}</span><span class="quest-desc muted">{h(q["desc"])}</span></div>'
    if not quest_html:
        quest_html = '<div class="muted">No active quests.</div>'

    # Fae bargains
    fae_html = ""
    for b in player.get("bargains", []):
        status = b["status"].upper()
        color = {"OPEN": "var(--seed)", "OVERDUE": "var(--climax)", "DELIVERED": "var(--muted)"}.get(status, "var(--muted)")
        fae_html += f'<div class="fae-row"><span style="color:{color}">{h(status)}</span> <span class="muted">{h(b["fae"])}</span> · {h(b["deadline"])}</div>'
    if not fae_html:
        fae_html = '<div class="muted">The Margin is clean.</div>'

    # Bleed status
    bleed_status_color = "var(--seed)" if bleed["is_today"] and bleed["delivered"] else \
                         "var(--rising)" if bleed["is_today"] else "var(--muted)"
    bleed_label = "Today's issue published" if bleed["is_today"] and bleed["delivered"] else \
                  "Today's issue pending" if bleed["is_today"] else \
                  f"Last: {bleed['last_issue']}"
    bleed_issue = f"#{bleed['issue_number']}" if bleed["issue_number"] else ""

    # Cron table
    cron_html = ""
    for j in crons:
        cron_html += render_cron_row(j)
    if not cron_html:
        cron_html = '<tr><td colspan="4" class="muted">No jobs found.</td></tr>'

    # Belief bar
    try:
        belief_val = int(player.get("belief", 0))
        belief_pct = min(100, belief_val)
    except (ValueError, TypeError):
        belief_val = 0
        belief_pct = 0

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="60">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Enchantify — Mission Control</title>
<style>
  :root {{
    --bg:         #111113;
    --surface:    #1c1c1f;
    --border:     #2a2a2f;
    --text:       #d4d4d8;
    --muted:      #52525b;
    --dormant:    #3f3f46;
    --setup:      #4e6b8a;
    --rising:     #92681a;
    --climax:     #c2410c;
    --resolution: #15803d;
    --nothing:    #7f1d1d;
    --seed:       #166534;
    --fae:        #6b21a8;
    --priority:   #dc2626;
    --war:        #b45309;
    --invest:     #1d4ed8;
    --beat:       #374151;
    --pulse:      #1f2937;
    --thread-line:#1e3a5f;
    font-family: 'Georgia', 'Times New Roman', serif;
  }}
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); min-height: 100vh; font-size: 14px; }}
  a {{ color: inherit; text-decoration: none; }}

  /* ── Layout ── */
  .topbar {{
    display: flex; align-items: center; gap: 1.5rem;
    padding: .7rem 1.5rem;
    background: var(--surface); border-bottom: 1px solid var(--border);
    font-family: monospace; font-size: .8rem;
  }}
  .topbar-title {{
    font-family: Georgia, serif; font-size: 1rem; letter-spacing: .08em;
    color: #a1a1aa; text-transform: uppercase;
  }}
  .topbar-divider {{ color: var(--border); }}
  .topbar-item {{ display: flex; gap: .4rem; align-items: center; }}
  .topbar-label {{ color: var(--muted); }}
  .topbar-refresh {{ margin-left: auto; color: var(--muted); font-size: .7rem; }}
  .belief-inline {{
    display: inline-block; width: 60px; height: 6px;
    background: var(--border); border-radius: 3px; vertical-align: middle;
    position: relative; overflow: hidden;
  }}
  .belief-inline-fill {{
    position: absolute; left: 0; top: 0; height: 100%;
    background: #7c3aed; border-radius: 3px;
  }}

  .grid {{
    display: grid;
    grid-template-columns: 1fr 340px;
    grid-template-rows: auto auto;
    gap: 1rem; padding: 1rem;
    max-width: 1600px; margin: 0 auto;
  }}

  /* ── Panels ── */
  .panel {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 4px; overflow: hidden;
  }}
  .panel-header {{
    padding: .5rem 1rem;
    border-bottom: 1px solid var(--border);
    font-family: monospace; font-size: .7rem; letter-spacing: .1em;
    color: var(--muted); text-transform: uppercase; display: flex;
    align-items: center; gap: .8rem;
  }}
  .panel-header span {{ color: var(--text); }}
  .panel-body {{ padding: 1rem; }}

  /* ── Thread cards ── */
  .thread-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: .75rem; }}
  .card {{
    background: var(--bg); border: 1px solid; border-radius: 4px;
    padding: .75rem; display: flex; flex-direction: column; gap: .5rem;
  }}
  .card-header {{ display: flex; align-items: center; justify-content: space-between; }}
  .card-title {{ font-size: .85rem; font-weight: bold; }}
  .card-anchor {{ font-size: .7rem; color: var(--muted); }}
  .card-beat {{ font-size: .78rem; color: var(--text); line-height: 1.5; font-style: italic; }}
  .card-meta {{ font-size: .65rem; color: var(--muted); font-family: monospace; }}
  .badge-new {{
    display: inline-block; margin-left: .5rem;
    background: var(--seed); color: #86efac;
    font-size: .55rem; padding: .1rem .3rem; border-radius: 2px;
    font-family: monospace; text-transform: uppercase; vertical-align: middle;
  }}
  .nothing-dot {{ font-size: .7rem; }}

  /* ── Phase bar ── */
  .phase-bar-wrap {{
    position: relative; height: 18px; border-radius: 2px; overflow: visible;
  }}
  .phase-bands {{
    display: flex; position: absolute; inset: 0; border-radius: 2px; overflow: hidden;
  }}
  .band {{ height: 100%; }}
  .phase-fill {{
    position: absolute; top: 0; left: 0; height: 100%;
    border-radius: 2px; opacity: .75; transition: width .3s;
  }}
  .phase-label {{
    position: absolute; right: 0; top: 0; height: 100%;
    display: flex; align-items: center;
    font-family: monospace; font-size: .65rem; font-weight: bold;
    padding-right: .3rem; text-shadow: 0 0 6px #000;
  }}
  .phase-bar.permanent {{
    background: var(--dormant); border-radius: 2px; height: 18px;
    display: flex; align-items: center; padding: 0 .5rem;
  }}
  .phase-bar.permanent span {{ font-size: .65rem; color: var(--muted); font-family: monospace; }}

  /* ── Talisman bars ── */
  .tal-row {{ display: flex; align-items: center; gap: .6rem; margin-bottom: .4rem; }}
  .tal-name {{ width: 100px; font-size: .75rem; font-weight: bold; flex-shrink: 0; }}
  .tal-bar-wrap {{ flex: 1; height: 8px; background: var(--bg); border-radius: 4px; overflow: hidden; }}
  .tal-bar {{ height: 100%; border-radius: 4px; transition: width .4s; }}
  .tal-belief {{ width: 30px; text-align: right; font-family: monospace; font-size: .75rem; flex-shrink: 0; }}
  .tal-chapter {{ width: 80px; font-size: .65rem; font-family: monospace; flex-shrink: 0; }}

  /* ── Entity table ── */
  .ent-table {{ width: 100%; border-collapse: collapse; font-size: .75rem; }}
  .ent-table td {{ padding: .25rem .4rem; border-bottom: 1px solid var(--border); }}
  .ent-table tr:last-child td {{ border-bottom: none; }}
  .ent-name {{ color: var(--text); }}
  .ent-type {{ font-family: monospace; font-size: .65rem; }}
  .ent-belief {{ font-family: monospace; text-align: right; color: var(--text); }}
  .ent-tags {{ font-family: monospace; font-size: .6rem; }}
  .tag {{
    display: inline-block; background: var(--thread-line); color: #93c5fd;
    border-radius: 2px; padding: .05rem .3rem; margin-right: .2rem; font-size: .6rem;
  }}

  /* ── Tick feed ── */
  .tick-feed {{ display: flex; flex-direction: column; gap: .3rem; max-height: 360px; overflow-y: auto; }}
  .entry {{
    padding: .35rem .6rem; border-radius: 3px; font-size: .72rem; line-height: 1.5;
    border-left: 3px solid transparent;
  }}
  .entry-escalation {{ background: #2d1b00; border-color: var(--rising); color: #fcd34d; }}
  .entry-cooling     {{ background: #1a1a2e; border-color: var(--setup); color: #93c5fd; }}
  .entry-seed        {{ background: #052e16; border-color: var(--seed); color: #86efac; }}
  .entry-fae         {{ background: #1e0533; border-color: var(--fae); color: #d8b4fe; }}
  .entry-priority    {{ background: #2d0000; border-color: var(--priority); color: #fca5a5; }}
  .entry-war         {{ background: #271500; border-color: var(--war); color: #fde68a; }}
  .entry-beat        {{ background: #1a1f2e; border-color: var(--beat); }}
  .entry-thread      {{ background: #1a2030; border-color: var(--thread-line); color: #93c5fd; }}
  .entry-talisman    {{ background: #1c1510; border-color: var(--war); color: #fcd34d; }}
  .entry-invest      {{ background: #0d1b35; border-color: var(--invest); color: #93c5fd; }}
  .entry-pulse       {{ background: #111; border-color: var(--border); color: var(--muted); }}
  .entry-normal      {{ background: #161618; border-color: var(--border); color: var(--text); }}

  /* ── Player panel ── */
  .belief-bar-wrap {{ margin: .5rem 0; }}
  .belief-bar-track {{
    height: 8px; background: var(--bg); border-radius: 4px; overflow: hidden;
  }}
  .belief-bar-fill {{
    height: 100%; background: #7c3aed; border-radius: 4px;
  }}
  .belief-label {{ font-family: monospace; font-size: .7rem; color: var(--muted); margin-top: .2rem; }}
  .stat-row {{ display: flex; gap: .8rem; flex-wrap: wrap; margin-bottom: .5rem; }}
  .stat {{ font-family: monospace; font-size: .7rem; }}
  .stat-key {{ color: var(--muted); }}
  .quest-row {{ padding: .3rem 0; border-bottom: 1px solid var(--border); display: flex; gap: .5rem; align-items: baseline; }}
  .quest-row:last-child {{ border-bottom: none; }}
  .quest-npc {{ font-size: .75rem; font-weight: bold; flex-shrink: 0; }}
  .quest-desc {{ font-size: .7rem; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .fae-row {{ font-size: .72rem; padding: .2rem 0; }}
  .section-label {{ font-family: monospace; font-size: .65rem; color: var(--muted); text-transform: uppercase; letter-spacing: .08em; margin: .7rem 0 .3rem; }}

  /* ── Bleed ── */
  .bleed-status {{
    display: flex; align-items: center; gap: .5rem;
    font-family: monospace; font-size: .8rem; padding: .5rem .75rem;
    border-radius: 3px; background: var(--bg);
  }}
  .bleed-dot {{ font-size: 1rem; }}

  /* ── Cron table ── */
  .cron-table {{ width: 100%; border-collapse: collapse; font-size: .72rem; }}
  .cron-table td {{ padding: .25rem .4rem; border-bottom: 1px solid var(--border); }}
  .cron-table tr:last-child td {{ border-bottom: none; }}
  .cron-name {{ color: var(--text); font-family: monospace; }}

  .muted {{ color: var(--muted); }}

  /* ── Scrollbar ── */
  ::-webkit-scrollbar {{ width: 4px; }}
  ::-webkit-scrollbar-track {{ background: var(--bg); }}
  ::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 2px; }}

  /* ── Sub-tabs ── */
  .tab-bar {{ display: flex; border-bottom: 1px solid var(--border); padding: 0 1rem; gap: .25rem; }}
  .tab {{
    padding: .35rem .75rem; font-family: monospace; font-size: .65rem;
    text-transform: uppercase; letter-spacing: .08em;
    color: var(--muted); cursor: pointer; border-bottom: 2px solid transparent;
    background: none; border-top: none; border-left: none; border-right: none;
    transition: color .15s;
  }}
  .tab.active {{ color: var(--text); border-bottom-color: #7c3aed; }}
  .tab-content {{ display: none; padding: .75rem 1rem; }}
  .tab-content.active {{ display: block; }}
</style>
</head>
<body>

<div class="topbar">
  <div class="topbar-title">⋈ Enchantify</div>
  <div class="topbar-divider">·</div>
  <div class="topbar-item">
    <span class="topbar-label">student</span>
    <span>{h(player.get("name","bj").upper())}</span>
  </div>
  <div class="topbar-item">
    <span class="topbar-label">belief</span>
    <span>{h(player.get("belief","?"))}</span>
    <span class="belief-inline"><span class="belief-inline-fill" style="width:{belief_pct}%"></span></span>
  </div>
  <div class="topbar-item">
    <span class="topbar-label">chapter</span>
    <span style="color:{CHAPTER_COLOR.get(player.get("chapter","?").lower(),"#a1a1aa")}">{h(player.get("chapter","?"))}</span>
  </div>
  <div class="topbar-item">
    <span class="topbar-label">tutorial</span>
    <span>{h(player.get("tutorial","?"))}</span>
  </div>
  <div class="topbar-item">
    <span class="topbar-label">bleed</span>
    <span style="color:{bleed_status_color}">{bleed_label} {bleed_issue}</span>
  </div>
  <div class="topbar-refresh">↻ auto-refresh 60s · generated {generated}</div>
</div>

<div class="grid">

  <!-- ── Left column ── -->
  <div style="display:flex;flex-direction:column;gap:1rem">

    <!-- Thread Map -->
    <div class="panel">
      <div class="panel-header">Thread Map <span>{len(threads)} active</span></div>
      <div class="panel-body">
        <div class="thread-grid">
          {thread_cards}
        </div>
      </div>
    </div>

    <!-- World Register + Tick Feed (tabbed) -->
    <div class="panel">
      <div class="tab-bar">
        <button class="tab active" onclick="switchTab(this,'tick')">Tick Feed</button>
        <button class="tab" onclick="switchTab(this,'entities')">Entities</button>
        <button class="tab" onclick="switchTab(this,'talismans')">Talisman War</button>
      </div>
      <div id="tick" class="tab-content active">
        <div class="tick-feed">{queue_html}</div>
      </div>
      <div id="entities" class="tab-content">
        <table class="ent-table">
          <tbody>{top_npcs}</tbody>
        </table>
      </div>
      <div id="talismans" class="tab-content">
        {tal_bars}
      </div>
    </div>

  </div>

  <!-- ── Right column ── -->
  <div style="display:flex;flex-direction:column;gap:1rem">

    <!-- Player -->
    <div class="panel">
      <div class="panel-header">Player Status</div>
      <div class="panel-body">
        <div class="stat-row">
          <div class="stat"><span class="stat-key">name </span>{h(player.get("name","?"))}</div>
          <div class="stat"><span class="stat-key">compass </span>{h(player.get("compass_total","0"))} runs</div>
        </div>
        <div class="belief-bar-wrap">
          <div class="belief-bar-track">
            <div class="belief-bar-fill" style="width:{belief_pct}%"></div>
          </div>
          <div class="belief-label">Belief {h(player.get("belief","?"))} / 100</div>
        </div>
        <div class="section-label">Active Quests</div>
        {quest_html}
        <div class="section-label">The Margin (Fae)</div>
        {fae_html}
      </div>
    </div>

    <!-- Automation -->
    <div class="panel">
      <div class="panel-header">Automation</div>
      <div class="panel-body">
        <div class="bleed-status">
          <span class="bleed-dot" style="color:{bleed_status_color}">◉</span>
          <span>The Bleed — {bleed_label} {bleed_issue}</span>
        </div>
        <div class="section-label" style="margin-top:.8rem">Cron Jobs</div>
        <table class="cron-table">
          <tbody>{cron_html}</tbody>
        </table>
      </div>
    </div>

  </div>
</div>

<script>
function switchTab(btn, id) {{
  const panel = btn.closest('.panel');
  panel.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  panel.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById(id).classList.add('active');
}}
</script>
</body>
</html>'''


# ── Entry point ───────────────────────────────────────────────────────────────

def generate() -> str:
    threads   = parse_threads()
    npcs, talismans = parse_entities()
    player    = parse_player()
    queue     = parse_tick_queue()
    bleed     = parse_bleed_status()
    crons     = parse_cron_jobs()
    return build_html(threads, npcs, talismans, player, queue, bleed, crons)


def main():
    parser = argparse.ArgumentParser(description="Enchantify Mission Control")
    parser.add_argument("--open",  action="store_true", help="Open in browser after generating")
    parser.add_argument("--serve", action="store_true", help="Serve on http://localhost:9191 with live refresh")
    parser.add_argument("--out",   default=str(BASE / "mission-control.html"), help="Output path")
    args = parser.parse_args()

    out = Path(args.out)

    if args.serve:
        import http.server, threading, time

        def regen():
            while True:
                try:
                    out.write_text(generate())
                except Exception as e:
                    print(f"  [warn] regen error: {e}")
                time.sleep(30)

        t = threading.Thread(target=regen, daemon=True)
        t.start()
        out.write_text(generate())  # initial

        import webbrowser
        os.chdir(out.parent)
        webbrowser.open(f"http://localhost:9191/{out.name}")

        class Handler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, fmt, *a): pass  # silence

        print(f"  Serving at http://localhost:9191/{out.name} — Ctrl-C to stop")
        http.server.HTTPServer(("localhost", 9191), Handler).serve_forever()
        return

    html = generate()
    out.write_text(html)
    print(f"  ✓ Generated {out}")

    if args.open:
        import subprocess as _sp
        _sp.run(["open", str(out)])


if __name__ == "__main__":
    main()

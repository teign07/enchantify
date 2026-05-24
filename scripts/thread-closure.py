#!/usr/bin/env python3
"""Close and archive story threads.

Resolution should be a door, not a parking lot. This script makes thread
endings deterministic: find threads ready for closure, dry-run the archive
operation, or close a named thread after the final beat has been played.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent
LORE = BASE / "lore"
MEMORY = BASE / "memory"
LOGS = BASE / "logs"
PLAYERS = BASE / "players"

THREADS = LORE / "threads.md"
REGISTER = LORE / "world-register.md"
QUEUE = MEMORY / "tick-queue.md"
LOG = LOGS / "thread-closure.jsonl"
ENDING_DIR = MEMORY / "thread-endings"
ENDING_HTML_DIR = ENDING_DIR / "html"
ENDING_PDF_DIR = ENDING_DIR / "pdf"

PROTECTED_THREAD_IDS = {"academy-daily", "main-arc"}
PROTECTED_THREAD_NAMES = {"Academy Daily Life", "The Current Arc"}


@dataclass
class ThreadRecord:
    name: str
    thread_id: str
    phase: str
    belief: int | None
    status: str
    next_beat: str
    last_advanced: str
    born: str
    closed: str
    npc_anchor: str
    section: str


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def write(path: Path, text: str, dry_run: bool = False) -> None:
    if dry_run:
        print(f"[dry-run] Would write {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    tmp.replace(path)


def clean(value: str) -> str:
    value = re.sub(r"\*\*([^*]+)\*\*", r"\1", value or "")
    value = value.replace("*", "")
    return re.sub(r"\s+", " ", value).strip(" ;")


def short(value: object, limit: int = 500) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit].rstrip() + ("..." if len(text) > limit else "")


def slug(value: str) -> str:
    value = re.sub(r"'s\b", "", value.lower())
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-") or "thread"


def normalize_phase(value: str) -> str:
    phase = clean(value).lower().split()[0] if value else ""
    if phase in {"quiet", "background"}:
        return "permanent"
    if phase in {"escalating", "escalation"}:
        return "rising"
    return phase


def parse_date(raw: str) -> date | None:
    m = re.search(r"\d{4}-\d{2}-\d{2}", raw or "")
    if not m:
        return None
    try:
        return date.fromisoformat(m.group(0))
    except ValueError:
        return None


def days_since(raw: str) -> int | None:
    parsed = parse_date(raw)
    return (date.today() - parsed).days if parsed else None


def field(section: str, label: str) -> str:
    m = re.search(rf"^\*\*{re.escape(label)}:(?:\*\*)?\s*([^\n]*)", section, re.MULTILINE | re.IGNORECASE)
    return clean(m.group(1)) if m else ""


def thread_section_pattern(name: str) -> re.Pattern[str]:
    bare = re.sub(r"^[Tt]he\s+", "", name).strip()
    return re.compile(
        r"(^## Thread:\s*(?:The\s+)?" + re.escape(bare) + r"\s*$)(.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )


def parse_register_threads() -> dict[str, dict[str, str | int]]:
    rows: dict[str, dict[str, str | int]] = {}
    for line in read(REGISTER).splitlines():
        m = re.match(r"^\|\s*([^|]+?)\s*\|\s*Thread\s*\|\s*(\d+)\s*\|\s*([^|]*)\|", line)
        if not m:
            continue
        name, belief, notes = m.group(1).strip(), int(m.group(2)), m.group(3).strip()
        if name.lower() in {"entity", "---"}:
            continue
        id_m = re.search(r"\[id:([^\]]+)\]", notes)
        phase_m = re.search(r"Phase:\s*([A-Za-z-]+)", notes)
        status = re.sub(r"^\[id:[^\]]+\]\s*", "", notes)
        status = re.sub(r"^Phase:\s*[A-Za-z-]+\s*[—-]?\s*", "", status).strip()
        row = {
            "name": name,
            "belief": belief,
            "thread_id": id_m.group(1).strip() if id_m else slug(name),
            "phase": normalize_phase(phase_m.group(1) if phase_m else ""),
            "status": clean(status),
            "line": line,
        }
        rows[str(row["thread_id"])] = row
        rows[slug(name)] = row
    return rows


def parse_threads() -> list[ThreadRecord]:
    threads_text = read(THREADS)
    register = parse_register_threads()
    records: list[ThreadRecord] = []
    for m in re.finditer(r"^## Thread:\s*(.+?)\s*$", threads_text, re.MULTILINE):
        name = clean(m.group(1))
        next_m = re.search(r"^## ", threads_text[m.end():], re.MULTILINE)
        end = m.end() + next_m.start() if next_m else len(threads_text)
        section = threads_text[m.start():end].strip()
        thread_id = field(section, "id").strip("`") or slug(name)
        row = register.get(thread_id) or register.get(slug(name)) or {}
        records.append(
            ThreadRecord(
                name=name,
                thread_id=thread_id,
                phase=normalize_phase(field(section, "phase") or str(row.get("phase", ""))),
                belief=int(row["belief"]) if isinstance(row.get("belief"), int) else None,
                status=str(row.get("status", "")),
                next_beat=field(section, "Next beat"),
                last_advanced=field(section, "Last advanced") or field(section, "Last visited"),
                born=field(section, "born"),
                closed=field(section, "closed"),
                npc_anchor=field(section, "npc_anchor"),
                section=section,
            )
        )
    return records


def find_thread(name: str) -> ThreadRecord:
    wanted = slug(name)
    for record in parse_threads():
        if slug(record.name) == wanted or record.thread_id == name or record.thread_id == wanted:
            return record
    raise SystemExit(f"Could not find active thread: {name}")


def protected(record: ThreadRecord) -> bool:
    return record.thread_id in PROTECTED_THREAD_IDS or record.name in PROTECTED_THREAD_NAMES


def closure_candidates(include_protected: bool = False) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    for record in parse_threads():
        if protected(record) and not include_protected:
            continue
        age = days_since(record.last_advanced)
        phase = record.phase
        signal = ""
        if phase == "resolution":
            signal = "ENDING_PAGE_REQUIRED" if age is None or age < 3 else "READY_TO_ARCHIVE"
        elif record.belief == 0:
            signal = "UNFINISHED_ARCHIVE_READY"
        elif age is not None and age >= 14 and phase in {"setup", "rising"}:
            signal = "REVIVE_OR_COOL"
        if not signal:
            continue
        candidates.append(
            {
                "name": record.name,
                "id": record.thread_id,
                "phase": phase,
                "belief": record.belief,
                "signal": signal,
                "last_advanced": record.last_advanced,
                "days_since": age,
                "next_beat": record.next_beat,
                "status": record.status,
            }
        )
    return candidates


def replace_closed_field(section: str, closed_line: str) -> str:
    pat = re.compile(r"^\*\*closed:(?:\*\*)?\s*.*$", re.MULTILINE | re.IGNORECASE)
    if pat.search(section):
        return pat.sub(f"**closed:** {closed_line}", section, count=1)
    return section.rstrip() + f"\n**closed:** {closed_line}\n"


def replace_phase_field(section: str, phase: str) -> str:
    pat = re.compile(r"^\*\*phase:(?:\*\*)?\s*.*$", re.MULTILINE | re.IGNORECASE)
    if pat.search(section):
        return pat.sub(f"**phase:** {phase}", section, count=1)
    return section.rstrip() + f"\n**phase:** {phase}\n"


def archive_section(record: ThreadRecord, outcome: str, mode: str) -> str:
    today = date.today().isoformat()
    section = record.section
    section = re.sub(r"^## Thread:", "## Archive:", section, count=1, flags=re.MULTILINE)
    section = replace_phase_field(section, "archived")
    section = replace_closed_field(section, f"{today} — {mode}: {outcome}")
    if "Ending Page:" not in section:
        section = section.rstrip() + f"\n\n**Ending Page:** {outcome}\n"
    return section.strip() + "\n"


def remove_thread_section(threads_text: str, record: ThreadRecord) -> tuple[str, bool]:
    pat = thread_section_pattern(record.name)
    updated, count = pat.subn("", threads_text, count=1)
    updated = re.sub(r"\n{4,}", "\n\n\n", updated)
    return updated, bool(count)


def append_archive(threads_text: str, archived: str) -> str:
    placeholder = "\n*(No archived threads yet — the Academy is young.)*"
    if placeholder in threads_text:
        threads_text = threads_text.replace(placeholder, "", 1)
    marker = "\n## Archive"
    if marker in threads_text:
        return threads_text.rstrip() + "\n\n" + archived
    return threads_text.rstrip() + "\n\n## Archive\n\n*Threads that have reached their conclusion — natural resolution or quiet extinction.*\n\n" + archived


def remove_register_row(register_text: str, record: ThreadRecord) -> tuple[str, bool]:
    names = {record.name, re.sub(r"^[Tt]he\s+", "", record.name).strip()}
    changed = False
    updated = register_text
    for name in sorted(names, key=len, reverse=True):
        pat = re.compile(
            r"^\|\s*(?:The\s+)?" + re.escape(name) + r"\s*\|\s*Thread\s*\|\s*\d+\s*\|[^\n]*\n?",
            re.MULTILINE | re.IGNORECASE,
        )
        updated, count = pat.subn("", updated, count=1)
        changed = changed or bool(count)
    return updated, changed


def append_player_story(player: str, record: ThreadRecord, outcome: str, mode: str, dry_run: bool) -> None:
    story_path = PLAYERS / f"{player}-story.md"
    today = date.today().isoformat()
    existing = read(story_path)
    entry = f"- **{today} — {record.name}:** {outcome} *(Ending Page: {mode}; archived from {record.phase or 'unknown'}.)*"
    if "## Thread Closures" in existing:
        updated = existing.rstrip() + "\n" + entry + "\n"
    else:
        updated = existing.rstrip() + "\n\n## Thread Closures\n\n" + entry + "\n"
    write(story_path, updated, dry_run=dry_run)


def append_tick(record: ThreadRecord, outcome: str, dry_run: bool) -> None:
    existing = read(QUEUE)
    line = f"- **[THREAD CLOSED: {record.name}]** {outcome}"
    write(QUEUE, existing.rstrip() + "\n" + line + "\n", dry_run=dry_run)


def html_escape(text: object) -> str:
    return html.escape(str(text or ""), quote=True)


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
        if line.startswith("# "):
            if in_list:
                body.append("</ul>")
                in_list = False
            body.append(f"<h1>{html_escape(line[2:].strip())}</h1>")
        elif line.startswith("## "):
            if in_list:
                body.append("</ul>")
                in_list = False
            body.append(f"<h2>{html_escape(line[3:].strip())}</h2>")
        elif line.startswith("### "):
            if in_list:
                body.append("</ul>")
                in_list = False
            body.append(f"<h3>{html_escape(line[4:].strip())}</h3>")
        elif line.startswith("- "):
            if not in_list:
                body.append("<ul>")
                in_list = True
            body.append(f"<li>{html_escape(line[2:].strip())}</li>")
        else:
            if in_list:
                body.append("</ul>")
                in_list = False
            body.append(f"<p>{html_escape(line)}</p>")
    if in_list:
        body.append("</ul>")
    return "".join(body)


def ending_markdown(record: ThreadRecord, outcome: str, mode: str) -> str:
    today = date.today().isoformat()
    status = record.status or "The register held no public summary, only pressure."
    next_beat = record.next_beat or "No final next beat was written before the archive page opened."
    born = record.born or "unknown"
    last = record.last_advanced or "unknown"
    belief = record.belief if record.belief is not None else "unknown"
    title = f"{record.name}: The Ending Page"
    return f"""# Thread Ending Page

## {title}

Filed: {today}
Thread ID: `{record.thread_id}`
Mode: {mode}
Belief at closure: {belief}
Born: {born}
Last advanced: {last}

### What This Story Was

{record.name} gathered enough Belief to become a gravity well in the Academy. Its anchor was {record.npc_anchor or "not a single person, but a pressure moving through the halls"}. It carried {record.phase or "unknown"} pressure when the archive opened, and its public register had come to this:

{status}

### The Last Visible Thread

Before closure, the story's waiting beat was:

{next_beat}

### How It Ended

{outcome}

### What Changed

- The active thread row left the world register.
- The full thread moved into the Archive.
- The player's story log gained this Ending Page.
- The next opening of the book may feel the aftermath instead of repeating the same unresolved pressure.

### Archivist's Note

An ending is not erasure. It is the moment the Book stops asking the same question and starts remembering the answer.
"""


def ending_html(markdown: str, record: ThreadRecord) -> str:
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
      max-width: 860px;
      margin: 32px auto;
      padding: 54px min(7vw, 76px);
      background:
        radial-gradient(circle at 13% 10%, rgba(110, 77, 34, .14), transparent 25%),
        radial-gradient(circle at 88% 18%, rgba(20, 82, 76, .13), transparent 22%),
        linear-gradient(90deg, rgba(86,54,24,.10), transparent 12%, transparent 88%, rgba(86,54,24,.10)),
        #eadcc4;
      box-shadow: 0 20px 80px rgba(0,0,0,.45);
      border: 1px solid rgba(58, 40, 23, .35);
      position: relative;
    }
    .page:before {
      content: "";
      position: absolute;
      inset: 18px;
      border: 1px solid rgba(63, 44, 27, .22);
      pointer-events: none;
    }
    h1, h2, h3 { font-weight: 500; text-align: center; letter-spacing: .04em; }
    h1 { font-size: 2.2rem; margin: 0 0 .25rem; color: #2b2118; }
    h2 { font-size: 1.45rem; margin: 0 0 2rem; color: #473421; }
    h3 { margin-top: 2.2rem; padding-top: .8rem; border-top: 1px solid rgba(71,52,33,.25); color: #31534c; }
    p { font-size: 1.06rem; margin: 1.05rem 0; }
    ul { padding-left: 1.35rem; }
    li { margin: .42rem 0; }
    code { color: #70412f; background: rgba(255,248,231,.45); padding: .08rem .25rem; }
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
  <title>{html_escape(record.name)} — Thread Ending Page</title>
  <style>{css}</style>
</head>
<body>
  <main class="page">
    {markdown_body_to_html(markdown)}
    <div class="stamp">Filed in the Thread Archive · {html_escape(date.today().isoformat())}</div>
  </main>
</body>
</html>
"""


def maybe_pdf(html_path: Path, pdf_path: Path) -> tuple[bool, str]:
    tool = shutil.which("wkhtmltopdf")
    if tool:
        proc = subprocess.run([tool, "--quiet", str(html_path), str(pdf_path)], cwd=BASE, capture_output=True, text=True, timeout=120)
        if proc.returncode == 0 and pdf_path.exists():
            return True, f"wkhtmltopdf rendered {pdf_path}"
        return False, short(proc.stderr or proc.stdout or "wkhtmltopdf failed", 500)

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
        return False, short(proc.stderr or proc.stdout or "Google Chrome headless PDF render failed", 500)

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
        return False, short(detail, 500)

    return False, "No PDF renderer found."


def write_ending_artifact(record: ThreadRecord, outcome: str, mode: str, dry_run: bool) -> dict[str, str]:
    date_str = date.today().isoformat()
    name_slug = slug(record.name)
    md_path = ENDING_DIR / f"{date_str}-{name_slug}.md"
    html_path = ENDING_HTML_DIR / f"{date_str}-{name_slug}.html"
    pdf_path = ENDING_PDF_DIR / f"{date_str}-{name_slug}.pdf"
    markdown = ending_markdown(record, outcome, mode)
    rendered = ending_html(markdown, record)
    if dry_run:
        print(f"[dry-run] Would write {md_path}")
        print(f"[dry-run] Would write {html_path}")
        print(f"[dry-run] Would render {pdf_path}")
        return {
            "markdown": str(md_path),
            "html": str(html_path),
            "pdf": "",
            "pdf_detail": "dry-run did not render PDF",
        }
    ENDING_DIR.mkdir(parents=True, exist_ok=True)
    ENDING_HTML_DIR.mkdir(parents=True, exist_ok=True)
    ENDING_PDF_DIR.mkdir(parents=True, exist_ok=True)
    md_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(rendered, encoding="utf-8")
    _ok, detail = maybe_pdf(html_path, pdf_path)
    return {
        "markdown": str(md_path),
        "html": str(html_path),
        "pdf": str(pdf_path) if pdf_path.exists() else "",
        "pdf_detail": detail,
    }


def telegram_send(message: str, media: Path | None = None, *, dry_run: bool = False) -> bool:
    if dry_run:
        print(message)
        if media:
            print(f"[dry-run media] {media}")
        return True
    args = [
        "openclaw", "message", "send",
        "--target", "8729557865",
        "--channel", "telegram",
        "--account", "enchantify",
        "--message", message,
    ]
    if media:
        args += ["--media", str(media), "--force-document"]
    proc = subprocess.run(args, cwd=BASE, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        log_event({
            "ts": datetime.now().isoformat(timespec="seconds"),
            "kind": "telegram_send_error",
            "thread_media": str(media) if media else "",
            "stderr": short(proc.stderr or proc.stdout, 1500),
        }, dry_run=False)
        return False
    return True


def log_event(event: dict[str, object], dry_run: bool) -> None:
    if dry_run:
        print("[dry-run] Would append logs/thread-closure.jsonl")
        return
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def close_thread(name: str, outcome: str, player: str, mode: str, dry_run: bool = False, force: bool = False, send: bool = False) -> dict[str, object]:
    record = find_thread(name)
    if protected(record) and not force:
        raise SystemExit(f"{record.name} is protected; use --force only if you really mean to archive it.")
    if not outcome.strip():
        raise SystemExit("Closing a thread requires a concrete one-line outcome.")

    archived = archive_section(record, clean(outcome), mode)
    threads_text = read(THREADS)
    register_text = read(REGISTER)
    without_thread, thread_removed = remove_thread_section(threads_text, record)
    without_row, row_removed = remove_register_row(register_text, record)
    if not thread_removed:
        raise SystemExit(f"Could not remove thread section for {record.name}.")

    updated_threads = append_archive(without_thread, archived)
    write(THREADS, updated_threads, dry_run=dry_run)
    write(REGISTER, without_row, dry_run=dry_run)
    append_player_story(player, record, clean(outcome), mode, dry_run)
    append_tick(record, clean(outcome), dry_run)
    artifact = write_ending_artifact(record, clean(outcome), mode, dry_run)
    telegram_sent = False
    if send:
        media_path = Path(artifact["pdf"] or artifact["html"] or artifact["markdown"])
        caption = (
            f"📖 Thread Ending Page: {record.name}\n\n"
            f"{short(outcome, 360)}"
        )
        telegram_sent = telegram_send(caption, media_path if media_path.exists() or dry_run else None, dry_run=dry_run)

    event = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "player": player,
        "thread": asdict(record),
        "outcome": clean(outcome),
        "mode": mode,
        "thread_removed": thread_removed,
        "register_row_removed": row_removed,
        "artifact": artifact,
        "telegram_sent": telegram_sent,
        "dry_run": dry_run,
    }
    log_event(event, dry_run=dry_run)
    return event


def render_status(as_json: bool = False) -> str:
    candidates = closure_candidates()
    if as_json:
        return json.dumps({"generated_at": datetime.now().isoformat(timespec="seconds"), "candidates": candidates}, indent=2, ensure_ascii=False)
    lines = ["THREAD CLOSURE STATUS"]
    if not candidates:
        lines.append("- No active closure candidates.")
        return "\n".join(lines)
    for item in candidates:
        age = item.get("days_since")
        age_text = f"{age} day(s)" if age is not None else "unknown age"
        lines.append(f"- {item['signal']}: {item['name']} [{item['phase']}, Belief {item.get('belief') if item.get('belief') is not None else '?'}; last advanced {age_text}]")
        if item.get("status"):
            lines.append(f"  status: {item['status']}")
        if item.get("next_beat"):
            lines.append(f"  next beat: {item['next_beat']}")
    return "\n".join(lines)


def read_outcome(args: argparse.Namespace) -> str:
    if args.outcome_file:
        return read(Path(args.outcome_file)).strip()
    return (args.outcome or "").strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect and archive resolved Enchantify story threads.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    status = sub.add_parser("status", help="Show threads ready for Ending Pages or archive decisions.")
    status.add_argument("--json", action="store_true")

    close = sub.add_parser("close", help="Archive one thread after its final beat has been delivered.")
    close.add_argument("name")
    close.add_argument("--player", default="bj")
    close.add_argument("--outcome")
    close.add_argument("--outcome-file")
    close.add_argument("--mode", choices=["completed", "unfinished", "transformed"], default="completed")
    close.add_argument("--dry-run", action="store_true")
    close.add_argument("--force", action="store_true")
    close.add_argument("--send", action="store_true", help="Send the Thread Ending Page PDF/HTML through Telegram.")

    args = parser.parse_args()
    if args.cmd == "status":
        print(render_status(as_json=args.json))
        return 0
    if args.cmd == "close":
        event = close_thread(
            args.name,
            read_outcome(args),
            player=args.player,
            mode=args.mode,
            dry_run=args.dry_run,
            force=args.force,
            send=args.send,
        )
        print(json.dumps(event, indent=2, ensure_ascii=False))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

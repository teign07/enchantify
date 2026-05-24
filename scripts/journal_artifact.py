#!/usr/bin/env python3
"""Shared storybook-journal renderer for Enchantify support artifacts."""

from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent.parent
BUNDLED_PYTHON = Path("/Users/bj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3")
REPORTLAB_HELPER = BASE / "scripts" / "journal_artifact_reportlab.py"
DRAWTHINGS = BASE / "scripts" / "drawthings_scene.py"
LOG_PATH = BASE / "logs" / "journal-artifact.log"


def clean(value: Any, limit: int = 500) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit].rstrip() + ("..." if len(text) > limit else "")


def log_event(message: str) -> None:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(message.rstrip() + "\n")
    except Exception:
        pass


def _inline(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*(.+?)\*", r"<em>\1</em>", escaped)
    escaped = re.sub(r"`(.+?)`", r"<code>\1</code>", escaped)
    return escaped


def markdown_body(markdown: str) -> str:
    body: list[str] = []
    in_list = False
    for raw in markdown.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            if in_list:
                body.append("</ul>")
                in_list = False
            continue
        if stripped.startswith("<!--"):
            continue
        if stripped.startswith("# "):
            if in_list:
                body.append("</ul>")
                in_list = False
            body.append(f"<h1>{_inline(stripped[2:].strip())}</h1>")
        elif stripped.startswith("## "):
            if in_list:
                body.append("</ul>")
                in_list = False
            body.append(f"<h2>{_inline(stripped[3:].strip())}</h2>")
        elif stripped.startswith("### "):
            if in_list:
                body.append("</ul>")
                in_list = False
            body.append(f"<h3>{_inline(stripped[4:].strip())}</h3>")
        elif stripped.startswith(("- ", "* ")):
            if not in_list:
                body.append("<ul>")
                in_list = True
            body.append(f"<li>{_inline(stripped[2:].strip())}</li>")
        elif re.match(r"^\d+\.\s+", stripped):
            if not in_list:
                body.append("<ul>")
                in_list = True
            numbered = re.sub(r"^\d+\.\s+", "", stripped)
            body.append(f"<li>{_inline(numbered)}</li>")
        else:
            if in_list:
                body.append("</ul>")
                in_list = False
            body.append(f"<p>{_inline(stripped)}</p>")
    if in_list:
        body.append("</ul>")
    return "\n".join(body)


def marginalia_lines(markdown: str, *, title: str, subtitle: str = "") -> list[str]:
    seeds = [
        "evidence became ink",
        "one small action is enough",
        "filed in the living margin",
        "no shame enters this page",
    ]
    for raw in markdown.splitlines():
        stripped = raw.strip()
        if stripped.startswith("## "):
            seeds.append(stripped[3:].strip().lower())
        elif stripped.startswith("- **") and ":" in stripped:
            seeds.append(re.sub(r"[*:]", "", stripped.split(":", 1)[0]).strip().lower())
    if subtitle:
        seeds.insert(0, subtitle.lower())
    if title:
        seeds.insert(0, title.lower())
    out: list[str] = []
    for item in seeds:
        item = clean(item, 72)
        if item and item not in out:
            out.append(item)
    return out[:6]


def journal_image_prompt(markdown: str, *, title: str, subtitle: str = "", accent: str = "#31534c") -> str:
    topics = ", ".join(marginalia_lines(markdown, title=title, subtitle=subtitle)[:5])
    return (
        "A custom main illumination for an Enchantify storybook journal page, "
        f"subject: {title}; {subtitle}; themes: {topics}. "
        "Focus on a symbolic council-table still life with one or two character-presence hints: "
        "a precise literary elf doctor's green ink, a depth therapist's blue-black note, "
        "a goblin ledger stamp, a press editor's red pencil, a bellkeeper's clock card, "
        "and a flamboyant professor's gold ribbon if relevant. "
        "Lush handwritten marginalia, lush watercolor washes, visible library stamps, wax seals, labels, tabs, arrows, "
        "pressed botanicals, ink blooms, archival overlays, field-journal texture, storybook page composition. "
        "Make the marginalia and stamps prominent, not timid decoration. "
        "Airy literary watercolor and ink, manuscript artifact, magical but practical. "
        "No readable text, no logo, no watermark."
    )


def generate_journal_image(
    markdown: str,
    image_dir: Path,
    stem: str,
    *,
    title: str,
    subtitle: str = "",
    accent: str = "#31534c",
    image_prompt: str = "",
    timeout_seconds: int | None = None,
) -> Path | None:
    if os.environ.get("JOURNAL_ARTIFACT_IMAGE", "1").lower() in {"0", "false", "no"}:
        log_event(f"{stem}: image disabled by JOURNAL_ARTIFACT_IMAGE")
        return None
    if not DRAWTHINGS.exists():
        log_event(f"{stem}: drawthings script missing")
        return None
    image_dir.mkdir(parents=True, exist_ok=True)
    output = image_dir / f"{stem}.png"
    if output.exists() and output.stat().st_size > 0:
        return output
    prompt = image_prompt or journal_image_prompt(markdown, title=title, subtitle=subtitle, accent=accent)
    timeout = timeout_seconds or int(os.environ.get("JOURNAL_ARTIFACT_IMAGE_TIMEOUT", "420"))
    try:
        proc = subprocess.run(
            [
                "python3",
                str(DRAWTHINGS),
                "--prompt",
                prompt,
                "--output",
                str(output),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except Exception as exc:
        log_event(f"{stem}: image generation exception: {clean(exc, 400)}")
        return None
    if proc.returncode == 0 and output.exists() and output.stat().st_size > 0:
        log_event(f"{stem}: image generated at {output}")
        return output
    log_event(f"{stem}: image generation failed rc={proc.returncode} detail={clean(proc.stderr or proc.stdout, 800)}")
    return None


def html_document(markdown: str, *, title: str, subtitle: str = "", footer: str = "", accent: str = "#31534c", image_path: Path | None = None, image_caption: str = "") -> str:
    notes = marginalia_lines(markdown, title=title, subtitle=subtitle)
    marginalia = "\n".join(f"<p>{html.escape(note)}</p>" for note in notes)
    image_html = ""
    if image_path and image_path.exists():
        image_html = f"""
    <figure class="hero-plate">
      <img src="{image_path.resolve().as_uri()}" alt="journal illumination">
      <figcaption><span>Illumination</span>{html.escape(image_caption or subtitle or title)}</figcaption>
    </figure>"""
    css = f"""
@page {{ size: Letter; margin: .34in; }}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  background: #151611;
  color: #2d241b;
  font-family: Georgia, "Times New Roman", serif;
  line-height: 1.52;
}}
.page {{
  min-height: 10.25in;
  max-width: 8.05in;
  margin: 0 auto;
  padding: .42in .48in .34in;
  position: relative;
  border: 1px solid rgba(83,68,44,.42);
  background:
    radial-gradient(circle at 14% 8%, rgba(255,255,255,.36), transparent 22%),
    radial-gradient(circle at 86% 15%, {accent}22, transparent 20%),
    linear-gradient(90deg, rgba(87,68,39,.08) 0 1px, transparent 1px 100%),
    linear-gradient(#f6ecd7, #eadbbd);
  background-size: auto, auto, 22px 22px, auto;
  overflow: hidden;
}}
.page:before {{
  content: "";
  position: absolute;
  inset: .16in;
  border: 1px solid rgba(83,68,44,.24);
  pointer-events: none;
}}
.page:after {{
  content: "";
  position: absolute;
  inset: .06in;
  pointer-events: none;
  background-image:
    repeating-linear-gradient(0deg, rgba(49,39,25,.024) 0 1px, transparent 1px 4px),
    radial-gradient(circle at 7% 78%, {accent}1d, transparent 15%),
    radial-gradient(circle at 94% 86%, rgba(67,52,31,.13), transparent 16%);
  mix-blend-mode: multiply;
}}
.masthead {{
  position: relative;
  text-align: center;
  padding-bottom: .16in;
  margin-bottom: .18in;
  border-bottom: 2px solid {accent};
}}
.kicker {{
  color: #75644b;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: .16em;
}}
.masthead h1 {{
  margin: .04in 0 .03in;
  font-size: 28px;
  font-weight: 500;
  color: {accent};
  letter-spacing: .02em;
}}
.subtitle {{
  color: #6f6048;
  font-size: 12px;
  font-style: italic;
}}
.body {{
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 1.45in;
  gap: .22in;
  align-items: start;
}}
.main-flow {{ min-width: 0; }}
.margin {{
  border-left: 1px solid rgba(83,68,44,.24);
  padding-left: .14in;
  color: #5f503a;
  font-size: 10.4px;
  font-style: italic;
  break-inside: avoid;
}}
.margin .stamp {{
  display: inline-block;
  margin: .02in 0 .14in;
  padding: .05in .08in;
  border: 1px solid {accent};
  color: {accent};
  text-transform: uppercase;
  letter-spacing: .12em;
  font-size: 8px;
  font-style: normal;
  transform: rotate(-2deg);
}}
.margin p {{
  margin: 0 0 .13in;
  transform: rotate(-.8deg);
}}
.hero-plate {{
  position: relative;
  margin: .19in 0 .18in;
  padding: .075in;
  border: 1px solid rgba(83,68,44,.32);
  background:
    linear-gradient(180deg, rgba(255,255,255,.30), rgba(102,78,42,.08)),
    rgba(255,255,255,.17);
  box-shadow: 0 1px 0 rgba(255,255,255,.45) inset, 0 8px 18px rgba(71,51,25,.12);
  break-inside: avoid;
}}
.hero-plate:before {{
  content: "✦";
  position: absolute;
  top: -.08in;
  right: .16in;
  color: {accent};
  font-size: 22px;
  transform: rotate(9deg);
}}
.hero-plate img {{
  display: block;
  width: 100%;
  max-height: 2.65in;
  object-fit: cover;
  border: 1px solid rgba(83,68,44,.26);
  filter: sepia(.12) contrast(.96) saturate(.94);
}}
.hero-plate figcaption {{
  margin-top: .055in;
  color: #62533d;
  font-size: 10.4px;
  font-style: italic;
}}
.hero-plate figcaption span {{
  margin-right: .08in;
  color: {accent};
  text-transform: uppercase;
  letter-spacing: .12em;
  font-style: normal;
  font-size: 8.2px;
}}
h1 {{ display: none; }}
h2 {{
  margin: .22in 0 .08in;
  padding-top: .08in;
  border-top: 1px solid rgba(83,68,44,.22);
  color: {accent};
  font-size: 17px;
  font-weight: 500;
  letter-spacing: .035em;
}}
h3 {{
  margin: .14in 0 .05in;
  color: #5e4530;
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: .09em;
}}
p {{ margin: 0 0 .1in; font-size: 12.8px; }}
ul {{ margin: .04in 0 .12in; padding-left: .22in; }}
li {{ margin: .035in 0; font-size: 12.3px; }}
code {{
  background: rgba(255,255,255,.25);
  padding: 0 .05in;
  border-radius: 3px;
}}
.seal {{
  position: absolute;
  right: .22in;
  top: .18in;
  width: .52in;
  height: .52in;
  border: 2px solid {accent};
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: {accent};
  opacity: .78;
  transform: rotate(8deg);
}}
.seal:before {{ content: "✦"; font-size: 21px; }}
.footer {{
  position: relative;
  margin-top: .2in;
  padding-top: .08in;
  border-top: 1px solid rgba(83,68,44,.24);
  color: #766850;
  font-size: 10px;
  display: flex;
  justify-content: space-between;
  gap: .2in;
}}
"""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  <style>{css}</style>
</head>
<body>
  <main class="page">
    <div class="seal"></div>
    <header class="masthead">
      <div class="kicker">Enchantify Storybook Journal Fragment</div>
      <h1>{html.escape(title)}</h1>
      <div class="subtitle">{html.escape(subtitle)}</div>
    </header>
    <section class="body">
      <article class="main-flow">
        {image_html}
        {markdown_body(markdown)}
      </article>
      <aside class="margin">
        <div class="stamp">Filed</div>
        {marginalia}
      </aside>
    </section>
    <footer class="footer">
      <span>{html.escape(footer or "Filed by the Labyrinth of Stories")}</span>
      <span>memory/support-faculty · storybook fragment</span>
    </footer>
  </main>
</body>
</html>
"""


def render_pdf(html_path: Path, pdf_path: Path) -> tuple[bool, str]:
    chrome_detail = ""
    tool = shutil.which("wkhtmltopdf")
    if tool:
        proc = subprocess.run([tool, "--page-size", "Letter", "--quiet", "--enable-local-file-access", str(html_path), str(pdf_path)], cwd=BASE, capture_output=True, text=True, timeout=120)
        if proc.returncode == 0 and pdf_path.exists():
            return True, f"wkhtmltopdf rendered {pdf_path}"
        return False, clean(proc.stderr or proc.stdout or "wkhtmltopdf failed", 500)
    chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    if chrome.exists():
        profile = pdf_path.parent / ".chrome-profile"
        profile.mkdir(parents=True, exist_ok=True)
        try:
            proc = subprocess.run([str(chrome), "--headless=new", "--disable-gpu", "--no-sandbox", f"--user-data-dir={profile}", f"--print-to-pdf={pdf_path}", html_path.resolve().as_uri()], cwd=BASE, capture_output=True, text=True, timeout=120)
            if proc.returncode == 0 and pdf_path.exists():
                return True, f"Chrome rendered {pdf_path}"
            chrome_detail = clean(proc.stderr or proc.stdout or "Chrome PDF failed", 500)
        except Exception as e:
            if pdf_path.exists() and pdf_path.stat().st_size > 0:
                return True, f"Chrome rendered {pdf_path} before exit ({e})"
            chrome_detail = clean(f"Chrome PDF failed: {e}", 500)
    cups = shutil.which("cupsfilter")
    if cups:
        proc = subprocess.run([cups, "-m", "application/pdf", str(html_path)], cwd=BASE, capture_output=True, timeout=120)
        if proc.returncode == 0 and proc.stdout:
            pdf_path.write_bytes(proc.stdout)
            return True, f"cupsfilter rendered {pdf_path}"
        detail = (proc.stderr or proc.stdout or b"cupsfilter failed").decode("utf-8", errors="replace")
        if chrome_detail:
            detail = f"{chrome_detail} | cupsfilter: {detail}"
        return False, clean(detail, 500)
    return False, chrome_detail or "No PDF renderer found."


def render(
    markdown: str,
    out_dir: Path,
    stem: str,
    *,
    title: str,
    subtitle: str = "",
    footer: str = "",
    accent: str = "#31534c",
    dry_run: bool = False,
    prefer_html_pdf: bool = False,
    image_prompt: str = "",
    image_caption: str = "",
    image_required: bool = False,
) -> dict[str, str]:
    html_dir = out_dir / "html"
    pdf_dir = out_dir / "pdf"
    image_dir = out_dir / "images"
    html_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(parents=True, exist_ok=True)
    html_path = html_dir / f"{stem}.html"
    pdf_path = pdf_dir / f"{stem}.pdf"
    if dry_run:
        return {"html": str(html_path), "pdf": "", "pdf_detail": "dry-run did not render PDF"}
    image_path = generate_journal_image(markdown, image_dir, stem, title=title, subtitle=subtitle, accent=accent, image_prompt=image_prompt)
    if image_required and not image_path:
        log_event(f"{stem}: required image missing; PDF will render without header illumination")
    image_caption = image_caption or f"{subtitle or title} · marginal illumination"
    html_path.write_text(html_document(markdown, title=title, subtitle=subtitle, footer=footer, accent=accent, image_path=image_path, image_caption=image_caption), encoding="utf-8")
    detail = ""
    if prefer_html_pdf:
        ok, render_detail = render_pdf(html_path, pdf_path)
        if ok and pdf_path.exists():
            return {"html": str(html_path), "pdf": str(pdf_path), "pdf_detail": render_detail}
        detail = f"html-pdf: {render_detail}"
    if BUNDLED_PYTHON.exists() and REPORTLAB_HELPER.exists():
        payload_path = pdf_dir / f"{stem}.json"
        payload_path.write_text(
            json.dumps(
                {
                    "markdown": markdown,
                    "pdf": str(pdf_path),
                    "title": title,
                    "subtitle": subtitle,
                    "footer": footer,
                    "accent": accent,
                    "image": str(image_path) if image_path else "",
                    "image_caption": image_caption if image_path else "",
                    "marginalia": marginalia_lines(markdown, title=title, subtitle=subtitle),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        proc = subprocess.run([str(BUNDLED_PYTHON), str(REPORTLAB_HELPER), str(payload_path)], cwd=BASE, capture_output=True, text=True, timeout=120)
        if proc.returncode == 0 and pdf_path.exists():
            return {"html": str(html_path), "pdf": str(pdf_path), "pdf_detail": f"ReportLab rendered {pdf_path}"}
        reportlab_detail = clean(proc.stderr or proc.stdout or "ReportLab helper failed", 500)
        detail = f"{detail} | reportlab: {reportlab_detail}" if detail else f"reportlab: {reportlab_detail}"
    if not prefer_html_pdf:
        ok, render_detail = render_pdf(html_path, pdf_path)
        detail = f"{detail} | {render_detail}" if detail else render_detail
        return {"html": str(html_path), "pdf": str(pdf_path) if ok and pdf_path.exists() else "", "pdf_detail": detail}
    return {"html": str(html_path), "pdf": str(pdf_path) if pdf_path.exists() else "", "pdf_detail": detail}

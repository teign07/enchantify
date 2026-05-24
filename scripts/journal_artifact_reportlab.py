#!/usr/bin/env python3
"""Render a simple storybook-journal PDF from a JSON payload.

This helper is intentionally dependency-light for the project itself. It is
called with the bundled Codex Python when the system Python lacks ReportLab.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def clean_inline(text: str) -> str:
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", text)
    text = text.replace("&", "&amp;").replace("<b>", "§B§").replace("</b>", "§/B§")
    text = text.replace("<i>", "§I§").replace("</i>", "§/I§")
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    return text.replace("§B§", "<b>").replace("§/B§", "</b>").replace("§I§", "<i>").replace("§/I§", "</i>")


def story(flow, markdown: str, styles: dict[str, ParagraphStyle]) -> None:
    pending: list[str] = []

    def flush() -> None:
        nonlocal pending
        if pending:
            flow.append(Paragraph(clean_inline(" ".join(pending)), styles["body"]))
            flow.append(Spacer(1, 0.11 * inch))
            pending = []

    for raw in markdown.splitlines():
        line = raw.strip()
        if not line:
            flush()
            continue
        if line == "---":
            flush()
            flow.append(Spacer(1, 0.18 * inch))
            continue
        if line.startswith("# "):
            flush()
            flow.append(Paragraph(clean_inline(line[2:]), styles["h1"]))
            flow.append(Spacer(1, 0.08 * inch))
            continue
        if line.startswith("## "):
            flush()
            flow.append(Paragraph(clean_inline(line[3:]), styles["h2"]))
            flow.append(Spacer(1, 0.06 * inch))
            continue
        if line.startswith("### "):
            flush()
            flow.append(Paragraph(clean_inline(line[4:]), styles["h3"]))
            flow.append(Spacer(1, 0.04 * inch))
            continue
        if line.startswith("- "):
            flush()
            flow.append(Paragraph("&#8226; " + clean_inline(line[2:]), styles["bullet"]))
            continue
        pending.append(line)
    flush()


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: journal_artifact_reportlab.py payload.json", file=sys.stderr)
        return 2
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    pdf_path = Path(payload["pdf"])
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    base = getSampleStyleSheet()
    styles = {
        "h1": ParagraphStyle("JournalH1", parent=base["Title"], fontName="Times-Bold", fontSize=22, leading=26, textColor=colors.HexColor("#2b2118"), alignment=1, spaceAfter=8),
        "h2": ParagraphStyle("JournalH2", parent=base["Heading2"], fontName="Times-Bold", fontSize=14, leading=17, textColor=colors.HexColor(payload.get("accent", "#31534c")), spaceBefore=8, spaceAfter=3),
        "h3": ParagraphStyle("JournalH3", parent=base["Heading3"], fontName="Times-BoldItalic", fontSize=11, leading=14, textColor=colors.HexColor("#4e3d2d"), spaceBefore=5),
        "body": ParagraphStyle("JournalBody", parent=base["BodyText"], fontName="Times-Roman", fontSize=10.5, leading=15, textColor=colors.HexColor("#2f271d")),
        "bullet": ParagraphStyle("JournalBullet", parent=base["BodyText"], leftIndent=0.18 * inch, firstLineIndent=-0.12 * inch, fontName="Times-Roman", fontSize=10, leading=14, textColor=colors.HexColor("#2f271d")),
        "subtitle": ParagraphStyle("JournalSubtitle", parent=base["BodyText"], fontName="Times-Italic", fontSize=10, leading=13, textColor=colors.HexColor("#5f5142"), alignment=1),
        "footer": ParagraphStyle("JournalFooter", parent=base["BodyText"], fontName="Times-Italic", fontSize=8, leading=10, textColor=colors.HexColor("#6c5b48"), alignment=1),
        "caption": ParagraphStyle("JournalCaption", parent=base["BodyText"], fontName="Times-Italic", fontSize=8.5, leading=10, textColor=colors.HexColor("#62533d")),
        "margin": ParagraphStyle("JournalMargin", parent=base["BodyText"], fontName="Times-Italic", fontSize=8, leading=10, textColor=colors.HexColor("#5f503a")),
    }

    def page(canvas, doc):
        canvas.saveState()
        w, h = letter
        canvas.setFillColor(colors.HexColor("#efe1c5"))
        canvas.rect(0, 0, w, h, fill=1, stroke=0)
        canvas.setStrokeColor(colors.HexColor("#7b6041"))
        canvas.setLineWidth(1.2)
        canvas.rect(0.45 * inch, 0.45 * inch, w - 0.9 * inch, h - 0.9 * inch, fill=0, stroke=1)
        canvas.setStrokeColor(colors.HexColor(payload.get("accent", "#31534c")))
        canvas.setLineWidth(0.5)
        canvas.rect(0.58 * inch, 0.58 * inch, w - 1.16 * inch, h - 1.16 * inch, fill=0, stroke=1)
        canvas.setFont("Times-Italic", 8)
        canvas.setFillColor(colors.HexColor("#6c5b48"))
        canvas.drawCentredString(w / 2, 0.32 * inch, payload.get("footer", "Filed by the Labyrinth of Stories"))
        canvas.restoreState()

    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter, rightMargin=0.78 * inch, leftMargin=0.78 * inch, topMargin=0.78 * inch, bottomMargin=0.72 * inch)
    flow = [
        Paragraph(clean_inline(payload.get("title") or "Journal Fragment"), styles["h1"]),
        Paragraph(clean_inline(payload.get("subtitle") or "A page from the living book"), styles["subtitle"]),
        Spacer(1, 0.18 * inch),
    ]
    image_value = str(payload.get("image") or "").strip()
    image_path = Path(image_value) if image_value else None
    if image_path and image_path.exists() and image_path.is_file():
        img = Image(str(image_path))
        max_w = 5.65 * inch
        max_h = 2.55 * inch
        scale = min(max_w / img.imageWidth, max_h / img.imageHeight)
        img.drawWidth = img.imageWidth * scale
        img.drawHeight = img.imageHeight * scale
        flow.append(KeepTogether([
            img,
            Paragraph(clean_inline(payload.get("image_caption") or "Illumination from the margin"), styles["caption"]),
            Spacer(1, 0.12 * inch),
        ]))

    main_flow: list = []
    story(main_flow, payload.get("markdown", ""), styles)
    marginalia = payload.get("marginalia") or []
    if marginalia:
        margin_text = " · ".join(str(note) for note in marginalia[:6])
        flow.append(Paragraph("<b>Filed in the margin:</b> " + clean_inline(margin_text), styles["margin"]))
        flow.append(Spacer(1, 0.12 * inch))
        flow.extend(main_flow)
    else:
        flow.extend(main_flow)
    flow.append(Spacer(1, 0.12 * inch))
    flow.append(Paragraph(clean_inline(payload.get("footer", "")), styles["footer"]))
    doc.build(flow, onFirstPage=page, onLaterPages=page)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

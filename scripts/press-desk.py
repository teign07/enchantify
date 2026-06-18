#!/usr/bin/env python3
"""Press Desk — execution trunk after the Press & Applied Abundance council.

The Listening Desk gathers weather. The council sets direction. The Press Desk
turns that direction into review-ready platform briefs, a Goldweaver offer lens,
one bundled Content Trunk PDF, and consent-queue rows. Nothing posts automatically.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "scripts"))
import cron_steward  # type: ignore
import journal_artifact  # type: ignore

MEMORY = BASE / "memory" / "publishing"
TRUNK_DIR = MEMORY / "content-trunk"
TRUNK_DAILY = TRUNK_DIR / "daily"
PRESS_ABUNDANCE_DAILY = MEMORY / "press-abundance" / "daily"
MARKET_RESEARCH = MEMORY / "market-research" / "latest.md"
LOG_PATH = BASE / "logs" / "publishing" / "press-desk.jsonl"
TARGET = "8729557865"
CHANNEL = "telegram"
ACCOUNT = "enchantify"
MAX_TASKS = 4
ENCHANTIFY_IMAGE_STYLE = (
    "Enchantify storybook-journal illustration style: sparse pen-and-ink linework with loose watercolor washes "
    "on textured aged parchment, visible paper grain, soft ink bleed, lush handwritten marginalia, stamps, wax seals, "
    "selective jewel-like pops of teal, gold, red, and deep green, never glossy corporate marketing art"
)

_PLATFORM_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"instagram|carousel", re.I), "instagram-carousel"),
    (re.compile(r"tiktok", re.I), "tiktok-carousel"),
    (re.compile(r"youtube.*short|shorts?", re.I), "youtube-short"),
    (re.compile(r"youtube.*(long[\s-]?form|episode)|long[\s-]?form.*youtube", re.I), "youtube-long"),
    (re.compile(r"youtube", re.I), "youtube-short"),
    (re.compile(r"patreon|member", re.I), "patreon-post"),
    (re.compile(r"bluesky.*thread|bsky.*thread", re.I), "bluesky-thread"),
    (re.compile(r"bluesky|bsky", re.I), "bluesky-post"),
    (re.compile(r"x[\s/]*thread|twitter.*thread|threads?", re.I), "x-thread"),
    (re.compile(r"\bx\b|twitter", re.I), "x-post"),
    (re.compile(r"reddit.*comment", re.I), "reddit-comment"),
    (re.compile(r"reddit", re.I), "reddit-post"),
    (re.compile(r"blog|newsletter|substack", re.I), "content-menu"),
]


def now() -> datetime:
    return datetime.now()


def today() -> str:
    return now().strftime("%Y-%m-%d")


def clean(value: Any, limit: int = 900) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit].rstrip() + ("..." if len(text) > limit else "")


def read(path: Path, limit: int | None = None) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[:limit] if limit else text


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    row.setdefault("timestamp", now().isoformat(timespec="seconds"))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def extract_structured(markdown: str) -> dict[str, Any]:
    for block in re.findall(r"```json\s*(.*?)```", markdown, re.DOTALL | re.IGNORECASE):
        try:
            data = json.loads(block)
            if isinstance(data, dict):
                return data
        except Exception:
            continue
    return {}


def council_section(markdown: str, name: str, limit: int = 1200) -> str:
    match = re.search(rf"^## {re.escape(name)}\s*(.*?)(?=^## |\Z)", markdown, re.DOTALL | re.MULTILINE)
    return clean(match.group(1), limit) if match else ""


def map_platform_hint(text: str) -> str:
    for pattern, kind in _PLATFORM_RULES:
        if pattern.search(text):
            return kind
    return ""


def infer_kind_from_text(text: str) -> str:
    mapped = map_platform_hint(text)
    if mapped and mapped != "content-menu":
        return mapped
    lower = text.lower()
    if "thread" in lower:
        return "bluesky-thread" if "bluesky" in lower or "bsky" in lower else "x-thread"
    if "carousel" in lower or "instagram" in lower:
        return "instagram-carousel"
    if "patreon" in lower or "member" in lower:
        return "patreon-post"
    if "short" in lower and "youtube" in lower:
        return "youtube-short"
    return ""


def kinds_from_text(text: str) -> list[str]:
    found: list[str] = []
    for pattern, kind in _PLATFORM_RULES:
        if kind == "content-menu":
            continue
        if pattern.search(text) and kind not in found:
            found.append(kind)
    return found


def latest_council_path() -> Path | None:
    today_path = PRESS_ABUNDANCE_DAILY / f"{today()}.md"
    if today_path.exists():
        return today_path
    packets = sorted(PRESS_ABUNDANCE_DAILY.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return packets[0] if packets else None


def ensure_dirs() -> None:
    for path in (TRUNK_DIR, TRUNK_DAILY, LOG_PATH.parent):
        path.mkdir(parents=True, exist_ok=True)
    readme = TRUNK_DIR / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Content Trunk\n\n"
            "After the Press & Applied Abundance council, the Press Desk executes: "
            "platform briefs from Penny, an Applied Abundance lens from Goldweaver, "
            "and one bundled review PDF for Telegram. Individual drafts also land in "
            "`memory/publishing/briefs/` and the consent queue.\n\n"
            "- `daily/` — bundled trunk markdown and rendered PDFs.\n",
            encoding="utf-8",
        )


def distill_topic(text: str, *, fallback: str = "") -> str:
    raw = str(text or "")
    raw = re.sub(r"\*\*([^*]+)\*\*", r"\1", raw)
    raw = re.sub(r"^#+\s*", "", raw, flags=re.MULTILINE)
    raw = raw.replace("---", " ")
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip() and not ln.strip().startswith(">")]
    skip_prefixes = ("full social draft", "draft a", "draft b", "platform:", "format:", "price point:")
    for line in lines:
        lower = line.lower()
        if any(lower.startswith(prefix) for prefix in skip_prefixes):
            continue
        if len(line) >= 12:
            return clean(line, 140)
    return clean(raw, 140) or fallback


def build_execution_plan(council_md: str, structured: dict[str, Any]) -> list[dict[str, str]]:
    tasks: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(kind: str, topic: str, source: str = "press-abundance") -> None:
        if not kind or len(tasks) >= MAX_TASKS:
            return
        if kind in seen:
            return
        topic = distill_topic(topic, fallback=kind.replace("-", " "))
        tasks.append({"kind": kind, "topic": topic, "source": source})
        seen.add(kind)

    title = clean(structured.get("title") or "today's council direction", 120)

    penny_next = distill_topic(
        structured.get("penny_next_brief") or council_section(council_md, "Penny's Next Brief", 400),
        fallback="today's editorial priority from council",
    )
    if penny_next:
        add(infer_kind_from_text(penny_next) or "instagram-carousel", penny_next, "press-abundance")

    free_topic = distill_topic(
        structured.get("free_content") or council_section(council_md, "Free Content Draft", 400),
        fallback="Center-is-the-pin — public Wonder Compass dispatch",
    )
    if free_topic:
        add(infer_kind_from_text(free_topic) or "bluesky-thread", free_topic, "press-abundance")

    paid_topic = distill_topic(
        structured.get("paid_content") or council_section(council_md, "Paid / Member Content Draft", 400),
        fallback="Write Direction Pocket Kit member note",
    )
    if paid_topic:
        add("patreon-post", paid_topic, "press-abundance")

    product_seed = distill_topic(
        structured.get("product_seed") or council_section(council_md, "Product Or Merch Seed", 300),
        fallback="Wonder Compass field kit seed",
    )
    if product_seed and "patreon-post" not in seen:
        add("patreon-post", product_seed, "press-abundance")

    platform_plan = structured.get("platform_plan")
    if isinstance(platform_plan, str):
        platform_plan = [platform_plan]
    if isinstance(platform_plan, list):
        for entry in platform_plan:
            entry_str = str(entry)
            if len(entry_str) > 140:
                for kind in kinds_from_text(entry_str):
                    add(kind, f"{title} — {kind.replace('-', ' ')}", "press-abundance")
            else:
                hint = map_platform_hint(entry_str)
                if hint and hint != "content-menu":
                    add(hint, f"{title} — {clean(entry_str, 160)}", "press-abundance")

    platform_section = council_section(council_md, "Platform Plan", 500)
    if platform_section and len(tasks) < MAX_TASKS:
        for kind in kinds_from_text(platform_section):
            add(kind, title, "press-abundance")

    if len(tasks) < 3:
        defaults = [
            ("instagram-carousel", penny_next or "Wonder Compass field assignment from today's council page", "wonder-compass"),
            ("bluesky-thread", "free open-source Enchantify as a living storybook engine", "enchantify"),
            ("patreon-post", clean(structured.get("patreon_nurture") or "the Doobaleedoos one-dollar door", 160), "patreon"),
        ]
        for kind, topic, source in defaults:
            add(kind, topic, source)

    return tasks[:MAX_TASKS]


def goldweaver_focus(structured: dict[str, Any], council_md: str) -> str:
    for key in ("goldwater_next_offer", "product_seed", "paid_content"):
        value = clean(structured.get(key), 240)
        if value:
            return value
    for section in ("Goldweaver's Next Offer", "Product Or Merch Seed", "Paid / Member Content Draft"):
        value = council_section(council_md, section, 240)
        if value:
            return value
    return "One shippable Wonder Compass field-kit offer shaped from today's council page"


def brief_excerpt(path: Path, limit: int = 2200) -> str:
    text = read(path, limit + 400)
    if not text:
        return "_Brief file missing._"
    parts: list[str] = []
    for section_name in (
        "Editorial Angle",
        "Penny's Recommendation",
        "Draft",
        "Caption",
        "Hook",
        "Member Note",
        "Posting Notes",
        "Privacy Label",
    ):
        bit = council_section(text, section_name, 500)
        if bit:
            parts.append(f"**{section_name}:** {bit}")
    if not parts:
        return clean(text, limit)
    return "\n\n".join(parts)


def find_consent_item(penny_press: Any, brief_path: Path) -> dict[str, Any] | None:
    brief = str(brief_path)
    for item in reversed(penny_press.consent_queue().get("items", [])):
        if item.get("brief") == brief:
            return item
    return None


def run_goldweaver(goldwater: Any, player: str, focus: str, *, dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {"path": "", "pdf": "", "focus": focus, "dry_run": True}
    path = goldwater.write_brief(player, focus)
    markdown = read(path)
    artifact = goldwater.render_brief_pdf(markdown, path, dry_run=False)
    return {
        "path": str(path),
        "pdf": artifact.get("pdf", ""),
        "focus": focus,
        "excerpt": council_section(markdown, "Best Offer Candidate", 700)
            or council_section(markdown, "One Tiny Action", 500),
    }


def run_penny_task(
    penny_press: Any,
    player: str,
    date_str: str,
    task: dict[str, str],
    *,
    dry_run: bool,
    generate_images: bool,
) -> dict[str, Any]:
    brief_dir = penny_press.BRIEF_DIR
    before = {p.name for p in brief_dir.glob("*.md")}
    rc = penny_press.run_make(
        player,
        date_str,
        task["kind"],
        task["topic"],
        task.get("source", "press-abundance"),
        no_llm=False,
        dry_run=dry_run,
        send=False,
        silent=True,
        queue=not dry_run,
        autonomy="press-desk",
        generate_images=generate_images,
    )
    row: dict[str, Any] = {
        "kind": task["kind"],
        "topic": task["topic"],
        "source": task.get("source", "press-abundance"),
        "returncode": rc,
        "generate_images": generate_images,
    }
    if rc != 0 or dry_run:
        return row
    new_files = [p for p in brief_dir.glob("*.md") if p.name not in before]
    brief_path = max(new_files, key=lambda p: p.stat().st_mtime) if new_files else None
    if not brief_path:
        candidates = sorted(brief_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        brief_path = candidates[0] if candidates else None
    if brief_path:
        row["brief"] = str(brief_path)
        row["excerpt"] = brief_excerpt(brief_path)
        item = find_consent_item(penny_press, brief_path)
        if item:
            row["consent_id"] = item.get("id")
            row["privacy"] = item.get("privacy")
            row["title"] = item.get("title")
    return row


def build_trunk_markdown(
    *,
    date_str: str,
    council_path: Path | None,
    council_md: str,
    structured: dict[str, Any],
    gold: dict[str, Any],
    penny_rows: list[dict[str, Any]],
) -> str:
    strategic = council_section(council_md, "Strategic Direction", 700)
    market_read = council_section(council_md, "Market Research Read", 600)
    tiny = clean(structured.get("tiny_action") or council_section(council_md, "Tiny Action"), 400)
    do_not = council_section(council_md, "Do Not Do Today", 400)
    lines = [
        f"# Content Trunk — {date_str}",
        "",
        "## Desk Weather",
        council_section(council_md, "Desk Weather", 500)
        or "Penny and Goldweaver have moved from council notes into review-ready drafts.",
        "",
        "## Strategic Direction",
        strategic or clean(structured.get("strategic_direction"), 700) or "_Council direction not filed yet._",
        "",
        "## Market Research Read",
        market_read or clean(read(MARKET_RESEARCH, 900), 900) or "_Listening Desk brief not visible._",
        "",
        f"## Council Anchor",
        f"- Packet: `{council_path}`" if council_path else "- Packet: _no council page found; defaults used_",
        "",
        "## Goldweaver Offer Lens",
        f"**Focus:** {clean(gold.get('focus'), 240)}",
        "",
        gold.get("excerpt") or "_Applied Abundance brief excerpt unavailable._",
        "",
        f"- Brief: `{gold.get('path')}`" if gold.get("path") else "",
        "",
        "## Penny's Drafts",
    ]
    if not penny_rows:
        lines.append("_No platform briefs were generated._")
    else:
        for row in penny_rows:
            if row.get("returncode") not in {0, None}:
                lines.extend([
                    "",
                    f"### {row.get('kind')} — {row.get('topic')}",
                    f"_Generation failed (code {row.get('returncode')})._",
                ])
                continue
            lines.extend([
                "",
                f"### {row.get('kind')} — {row.get('title') or row.get('topic')}",
                f"- Consent ID: `{row.get('consent_id', 'pending')}`",
                f"- Privacy: {row.get('privacy', 'NEEDS BJ REVIEW')}",
                f"- Brief: `{row.get('brief', '')}`",
                "",
                row.get("excerpt") or "_Excerpt unavailable._",
            ])
    consent_ids = [row.get("consent_id") for row in penny_rows if row.get("consent_id")]
    lines.extend([
        "",
        "## Consent Tray",
        "Review each draft in the consent queue before anything leaves the Labyrinth.",
        "",
    ])
    if consent_ids:
        lines.extend(f"- `{item_id}`" for item_id in consent_ids)
    else:
        lines.append("- _No new consent rows from this trunk run._")
    lines.extend([
        "",
        "## Tiny Action",
        tiny or "Open the trunk PDF and approve or revise one draft.",
        "",
        "## Do Not Do Today",
        do_not or "Do not post, schedule, or promise publication without explicit consent.",
        "",
        "---",
        "_Filed by the Press Desk. Strategy lives in the council packet; this trunk is for execution and review._",
    ])
    return "\n".join(lines)


def enqueue_trunk(penny_press: Any, *, date_str: str, player: str, trunk_path: Path, pdf: str, structured: dict[str, Any], consent_ids: list[str]) -> str:
    data = penny_press.consent_queue()
    items = data.setdefault("items", [])
    existing = next(
        (
            item for item in items
            if item.get("date") == date_str
            and item.get("content_kind") == "press-desk-trunk"
            and item.get("source") == "press-desk"
        ),
        None,
    )
    item_id = existing.get("id") if existing else f"press-desk-{now().strftime('%Y%m%d-%H%M%S')}"
    item = {
        "id": item_id,
        "created_at": existing.get("created_at") if existing else now().isoformat(timespec="seconds"),
        "updated_at": now().isoformat(timespec="seconds"),
        "date": date_str,
        "player": player,
        "platform": "multi-platform",
        "content_kind": "press-desk-trunk",
        "topic": structured.get("title") or "Daily Content Trunk",
        "title": structured.get("title") or f"Content Trunk — {date_str}",
        "status": "needs_review",
        "privacy": structured.get("privacy") or "NEEDS BJ REVIEW",
        "consent_required": True,
        "autonomy": "press_desk",
        "source": "press-desk",
        "brief": str(trunk_path),
        "structured": json.dumps({"child_consent_ids": consent_ids}, ensure_ascii=False),
        "pdf": pdf,
        "cta": clean(structured.get("tiny_action"), 400),
        "posting_notes": "Bundled review packet. Approve or revise individual drafts in the consent tray before posting.",
        "post_url": "",
        "performance": {"views": None, "likes": None, "comments": None, "shares": None, "saves": None, "clicks": None},
        "lesson": "",
    }
    if existing:
        existing.clear()
        existing.update(item)
    else:
        items.append(item)
    penny_press.save_consent_queue(data)
    penny_press.append_jsonl(penny_press.SOCIAL_LEDGER, {**item, "ledger_event": "trunk_drafted"})
    return item_id


def render_trunk(markdown: str, path: Path, *, dry_run: bool = False) -> dict[str, str]:
    image_prompt = (
        "Penny Blackletter and Professor Goldweaver's Press Desk content trunk: stacked platform briefs, "
        "carousel thumbnails, Patreon lantern, offer cards, red editor's pencil, wax seals, and manuscript tabs. "
        f"{ENCHANTIFY_IMAGE_STYLE}. No readable text, no logo, no watermark."
    )
    return journal_artifact.render(
        markdown,
        TRUNK_DIR,
        path.stem,
        title=f"Content Trunk — {path.stem}",
        subtitle="Penny's drafts and Goldweaver's offer lens, bundled for review",
        footer="Filed by the Press Desk · consent required before publication",
        accent="#6f2e3d",
        image_prompt=image_prompt,
        dry_run=dry_run,
        prefer_html_pdf=True,
    )


def summarize_telegram(markdown: str, trunk_path: Path, outputs: dict[str, str], penny_rows: list[dict[str, Any]], trunk_id: str) -> str:
    weather = council_section(markdown, "Desk Weather", 420)
    tiny = council_section(markdown, "Tiny Action", 320)
    kinds = [row.get("kind") for row in penny_rows if row.get("returncode") == 0]
    parts = [
        f"Content Trunk — {today()}",
        "",
        weather or "Penny and Goldweaver filed today's execution bundle.",
        "",
        f"Drafts inside: {', '.join(kinds) if kinds else 'see trunk'}",
        f"Consent trunk id: {trunk_id}",
    ]
    if tiny:
        parts.extend(["", f"Tiny action: {tiny}"])
    if outputs.get("pdf"):
        parts.extend(["", f"Full review PDF: {Path(outputs['pdf']).name}"])
    else:
        parts.extend(["", f"Trunk file: {trunk_path.name}"])
    return "\n".join(parts)


def send_telegram(message: str, media: Path | None = None, *, dry_run: bool = False, silent: bool = False) -> int:
    if dry_run:
        print(message)
        if media:
            print(f"[dry-run media] {media}")
        return 0
    args = [
        "openclaw", "message", "send",
        "--target", TARGET,
        "--channel", CHANNEL,
        "--account", ACCOUNT,
        "--message", message,
    ]
    if silent:
        args.append("--silent")
    if media:
        args += ["--media", str(media), "--force-document"]
    proc = subprocess.run(args, cwd=BASE, capture_output=True, text=True, timeout=180)
    if proc.returncode != 0:
        append_jsonl(LOG_PATH, {
            "kind": "telegram_send_error",
            "stderr": clean(proc.stderr or proc.stdout, 2000),
            "media": str(media) if media else "",
        })
    return proc.returncode


def run_execute(
    player: str = "bj",
    *,
    send: bool = False,
    dry_run: bool = False,
    no_llm: bool = False,
    silent: bool = False,
    generate_images: bool = False,
) -> int:
    ensure_dirs()
    penny_press = load_module("penny_press", BASE / "scripts" / "penny-press.py")
    goldwater = load_module("goldwater", BASE / "scripts" / "goldwater.py")
    penny_press.ensure_dirs()
    goldwater.ensure_dirs()

    date_str = today()
    council_path = latest_council_path()
    council_md = read(council_path) if council_path else ""
    structured = extract_structured(council_md)
    plan = build_execution_plan(council_md, structured)

    if no_llm:
        trunk_md = build_trunk_markdown(
            date_str=date_str,
            council_path=council_path,
            council_md=council_md,
            structured=structured,
            gold={"focus": goldweaver_focus(structured, council_md), "excerpt": "_LLM skipped._"},
            penny_rows=[],
        )
        if dry_run:
            print(trunk_md)
            return 0
        trunk_path = TRUNK_DAILY / f"{date_str}.md"
        trunk_path.write_text(trunk_md, encoding="utf-8")
        print(f"PRESS_DESK_TRUNK: {trunk_path} (no execution; --no-llm)")
        return 0

    focus = goldweaver_focus(structured, council_md)
    gold = run_goldweaver(goldwater, player, focus, dry_run=dry_run)

    penny_rows: list[dict[str, Any]] = []
    carousel_images_used = 0
    for task in plan:
        want_images = generate_images and task["kind"] in {"instagram-carousel", "tiktok-carousel"} and carousel_images_used < 1
        row = run_penny_task(
            penny_press,
            player,
            date_str,
            task,
            dry_run=dry_run,
            generate_images=want_images,
        )
        if want_images and row.get("returncode") == 0:
            carousel_images_used += 1
        penny_rows.append(row)

    trunk_md = build_trunk_markdown(
        date_str=date_str,
        council_path=council_path,
        council_md=council_md,
        structured=structured,
        gold=gold,
        penny_rows=penny_rows,
    )
    if dry_run:
        print(trunk_md)
        return 0

    trunk_path = TRUNK_DAILY / f"{date_str}.md"
    trunk_path.write_text(trunk_md, encoding="utf-8")
    outputs = render_trunk(trunk_md, trunk_path, dry_run=False)
    consent_ids = [str(row["consent_id"]) for row in penny_rows if row.get("consent_id")]
    trunk_id = enqueue_trunk(
        penny_press,
        date_str=date_str,
        player=player,
        trunk_path=trunk_path,
        pdf=outputs.get("pdf", ""),
        structured=structured,
        consent_ids=consent_ids,
    )
    append_jsonl(LOG_PATH, {
        "kind": "execute",
        "player": player,
        "council": str(council_path) if council_path else "",
        "trunk": str(trunk_path),
        "pdf": outputs.get("pdf", ""),
        "tasks": plan,
        "penny_rows": penny_rows,
        "gold": gold,
        "trunk_consent_id": trunk_id,
    })

    if send:
        message = summarize_telegram(trunk_md, trunk_path, outputs, penny_rows, trunk_id)
        skip, digest, reason = cron_steward.should_skip_duplicate(
            "press-desk",
            message,
            cooldown_hours=20,
            scope=date_str,
        )
        if skip:
            cron_steward.mark_skipped("press-desk", reason, scope=date_str, fingerprint=digest)
            return 0
        media = Path(outputs["pdf"]) if outputs.get("pdf") else trunk_path
        rc = send_telegram(message, media if media.exists() else None, dry_run=False, silent=silent)
        if rc == 0:
            cron_steward.mark_delivered("press-desk", message, scope=date_str, path=str(trunk_path))
            append_jsonl(LOG_PATH, {"kind": "delivery", "trunk": str(trunk_path), "media": str(media), "sent": True})
        return rc

    print(f"PRESS_DESK_TRUNK: {trunk_path}")
    if outputs.get("pdf"):
        print(f"PDF: {outputs['pdf']}")
    print(f"CONSENT_TRUNK_ID: {trunk_id}")
    return 0


def run_status() -> int:
    ensure_dirs()
    latest = sorted(TRUNK_DAILY.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    council = latest_council_path()
    print("PRESS DESK STATUS")
    print(f"Trunk dir: {TRUNK_DIR}")
    print(f"Latest council: {council or 'none'}")
    print(f"Trunks filed: {len(list(TRUNK_DAILY.glob('*.md')))}")
    if latest:
        print(f"Latest trunk: {latest[0]}")
        print(clean(read(latest[0], 900), 900))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Press Desk — execute council direction into review-ready drafts.")
    sub = parser.add_subparsers(dest="command", required=True)

    execute = sub.add_parser("execute", help="Generate platform briefs, Goldweaver lens, and bundled Content Trunk.")
    execute.add_argument("player", nargs="?", default="bj")
    execute.add_argument("--send", action="store_true", help="Send trunk PDF summary to Telegram.")
    execute.add_argument("--dry-run", action="store_true")
    execute.add_argument("--no-llm", action="store_true", help="Write trunk shell only; skip brief generation.")
    execute.add_argument("--silent", action="store_true")
    execute.add_argument("--generate-images", action="store_true", help="Generate Draw Things art for the first carousel brief.")

    sub.add_parser("status")

    args = parser.parse_args()
    with cron_steward.run(f"press-desk:{args.command}"):
        if args.command == "execute":
            return run_execute(
                args.player,
                send=args.send,
                dry_run=args.dry_run,
                no_llm=args.no_llm,
                silent=args.silent,
                generate_images=args.generate_images,
            )
        if args.command == "status":
            return run_status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

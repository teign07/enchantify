#!/usr/bin/env python3
"""Build the local reference library used by the Inside Cover iOS app."""

from __future__ import annotations

import json
import re
import importlib.util
import html
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "ios" / "InsideCover" / "Shared" / "BookReferenceLibrary.json"
PATREON_URL = "https://patreon.com/thedoobaleedoos"

WONDER_DIR = ROOT / "lore" / "wonder-compass-book"
CHARACTER_VISUALS = ROOT / "lore" / "character-visuals.json"
LORE_FILES = [
    ROOT / "lore" / "characters.md",
    ROOT / "lore" / "belief-system.md",
    ROOT / "lore" / "belief-investments.md",
    ROOT / "lore" / "belief-combat.md",
    ROOT / "lore" / "wonder-compass.md",
    ROOT / "lore" / "compass-directions.md",
    ROOT / "lore" / "compass-run.md",
    ROOT / "lore" / "outer-stacks.md",
    ROOT / "lore" / "ley-lines.md",
    ROOT / "lore" / "locations.md",
    ROOT / "lore" / "threads.md",
    ROOT / "lore" / "chapters.md",
    ROOT / "lore" / "school-life.md",
    ROOT / "lore" / "academy-events.md",
    ROOT / "lore" / "world.md",
    ROOT / "lore" / "the-pitch.md",
]

def clean_markdown(text: str) -> str:
    text = text.replace("\f", "\n")
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"^\s*[-*_]{3,}\s*$", "", text, flags=re.M)
    text = re.sub(r"[*_`>#]", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def first_heading(text: str, fallback: str) -> str:
    markdown_heading = None
    for line in text.splitlines():
        stripped = line.strip()
        lowered = stripped.lower()
        if stripped.startswith("#") and markdown_heading is None:
            markdown_heading = stripped.lstrip("#").strip()
        if lowered.startswith("chapter "):
            return stripped
    if markdown_heading:
        return markdown_heading
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("part "):
            return stripped
    return fallback


def clean_paragraphs(text: str) -> list[str]:
    cleaned = clean_markdown(text)
    return [
        paragraph.strip()
        for paragraph in cleaned.split("\n\n")
        if len(paragraph.strip()) > 80 and not paragraph.strip().startswith("Chapter ")
    ]


def excerpt(text: str, limit: int = 640) -> str:
    paragraphs = clean_paragraphs(text)
    body = paragraphs[0] if paragraphs else cleaned
    body = re.sub(r"\s+", " ", body).strip()
    if len(body) <= limit:
        return body
    clipped = body[:limit].rsplit(" ", 1)[0].rstrip(" ,;:")
    return f"{clipped}..."


def plain_text(value: object, limit: int = 420) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    text = clean_markdown(text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    clipped = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:")
    return f"{clipped}..."


def slugify(value: str) -> str:
    text = re.sub(r"[“”\"'’]", "", value.lower())
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "character"


def pascal_slug(slug: str) -> str:
    return "".join(part.capitalize() for part in slug.split("-") if part)


def clipped_excerpt(text: str, limit: int = 1_150) -> str:
    body = re.sub(r"\s+", " ", text).strip()
    if len(body) <= limit:
        return body
    clipped = body[:limit].rsplit(" ", 1)[0].rstrip(" ,;:")
    return f"{clipped}..."


def tags_for_text(source: str, text: str) -> list[str]:
    lowered = text.lower()
    tags = [source]
    keywords = {
        "notice": ["notice", "noticing", "attention", "glint"],
        "embark": ["embark", "adventure", "threshold", "walk"],
        "sense": ["sense", "sensory", "sound", "texture", "body"],
        "write": ["write", "sentence", "souvenir", "memory"],
        "rest": ["rest", "center", "gentle", "tired"],
        "belief": ["belief", "narrative weight", "lifeblood"],
        "characters": ["character", "npc", "professor", "student"],
        "relationships": ["relationship", "gossip", "trust"],
        "outer-stacks": ["outer stacks", "location", "anchor"],
        "nothing": ["nothing", "duskthorn", "unwritten"],
    }
    for tag, needles in keywords.items():
        if any(needle in lowered for needle in needles):
            tags.append(tag)
    return sorted(set(tags))


def prompt_for_wonder(title: str, body: str) -> str:
    lowered = f"{title} {body}".lower()
    if "rest" in lowered or "fatigue" in lowered or "dark" in lowered:
        return "Let the Compass get smaller."
    if "write" in lowered or "souvenir" in lowered:
        return "Keep one sentence before the day blurs."
    if "sense" in lowered or "texture" in lowered or "sound" in lowered:
        return "Give one sense a tiny mission."
    if "embark" in lowered or "adventure" in lowered:
        return "Cross one tiny threshold."
    if "notice" in lowered or "attention" in lowered:
        return "Notice one thing your brain tried to skip."
    return "Try one small Compass loop."


def prompt_for_lore(title: str, body: str) -> str:
    lowered = f"{title} {body}".lower()
    if "character" in lowered or "professor" in lowered or "npc" in lowered:
        return "Let a character tug the margin."
    if "belief" in lowered:
        return "Notice what has narrative weight."
    if "outer stacks" in lowered or "location" in lowered:
        return "Let place become story logic."
    if "nothing" in lowered:
        return "Name the pressure without feeding it."
    return "Let the lore brush against today."


def character_prompt(name: str, profile: dict[str, object]) -> str:
    core = plain_text(profile.get("core"), limit=520)
    signature = plain_text(profile.get("signature"), limit=180)
    palette = plain_text(profile.get("palette"), limit=160)
    silhouette = plain_text(profile.get("silhouette"), limit=180)
    continuity = plain_text(profile.get("continuity"), limit=220)
    marginalia = "; ".join(character_marginalia(name, profile))
    return (
        "Create an Enchantify Academy character dossier illustration in the uploaded reference style: "
        "antique parchment collage, central sparse graphite-and-ink portrait, delicate crosshatching, warm sepia paper, "
        "transparent watercolor washes, restrained shadows, and small pops of jewel-like color from the character palette. "
        "Build the margins from character-specific scraps: taped field notes, an academy stamp, small compass marks, "
        "botanical or symbolic marginalia, handwritten annotations, weathered edges, subtle ink stains, and a miniature inset portrait or evidence scrap. "
        f"Character: {name}. Canon visual profile: {core}. Signature object: {signature}. "
        f"Palette: {palette}. Silhouette and pose: {silhouette}. Continuity rule: {continuity}. "
        f"Marginalia should reference: {marginalia}. "
        "Keep the character as the first read, with the academy-file scraps supporting the portrait."
    )


def character_negative_prompt(profile: dict[str, object]) -> str:
    avoid = plain_text(profile.get("avoid"), limit=320)
    base = (
        "Do not make a generic fantasy pinup, shiny digital concept art, glossy anime, plastic skin, "
        "photo-real celebrity likeness, modern office portrait, cluttered room-first scene, illegible face, "
        "heavy oil paint, neon glow, thick airbrush rendering, overfull collage, or inconsistent signature object."
    )
    return f"{base} Avoid: {avoid}" if avoid else base


def character_marginalia(name: str, profile: dict[str, object]) -> list[str]:
    chapter = plain_text(profile.get("chapter"), limit=80)
    signature = plain_text(profile.get("signature"), limit=120)
    palette = plain_text(profile.get("palette"), limit=120)
    core = plain_text(profile.get("core"), limit=220)
    notes = [
        f"file tab labeled {name}",
        f"signature evidence: {signature}" if signature else "signature evidence",
        f"jewel-color swatches: {palette}" if palette else "jewel-color swatches",
    ]
    if chapter:
        notes.append(f"chapter mark: {chapter}")
    if core:
        notes.append(f"one short handwritten note from the canon profile: {core}")
    return notes


def character_tags(name: str, profile: dict[str, object]) -> list[str]:
    tags = ["character", "illustration", slugify(name)]
    chapter = profile.get("chapter")
    status = profile.get("status")
    if chapter:
        tags.append(slugify(str(chapter)))
    if status:
        tags.append(slugify(str(status)))
    return sorted(set(tags))


def character_illustration_profiles() -> list[dict[str, object]]:
    if not CHARACTER_VISUALS.exists():
        return []

    raw = json.loads(CHARACTER_VISUALS.read_text(encoding="utf-8"))
    characters = raw.get("characters") or {}
    profiles: list[dict[str, object]] = []
    for name, profile in characters.items():
        if not isinstance(profile, dict):
            continue
        slug = slugify(name)
        intended_asset_name = f"LabyrinthCharacter{pascal_slug(slug)}"
        profiles.append({
            "id": slug,
            "characterName": name,
            "slug": slug,
            "status": str(profile.get("status") or ""),
            "chapter": profile.get("chapter"),
            "core": plain_text(profile.get("core"), limit=620),
            "signature": plain_text(profile.get("signature"), limit=220),
            "palette": plain_text(profile.get("palette"), limit=220),
            "silhouette": plain_text(profile.get("silhouette"), limit=260),
            "continuity": plain_text(profile.get("continuity"), limit=320),
            "avoid": plain_text(profile.get("avoid"), limit=360),
            "assetName": intended_asset_name,
            "intendedAssetName": intended_asset_name,
            "prompt": character_prompt(name, profile),
            "negativePrompt": character_negative_prompt(profile),
            "marginalia": character_marginalia(name, profile),
            "tags": character_tags(name, profile),
        })
    return profiles


def wonder_files() -> list[Path]:
    files = [path for path in WONDER_DIR.glob("*.md") if path.name != "BOOK_TOC.md"]
    return sorted(files, key=lambda path: path.name.lower())


def snippet(path: Path, source_id: str, prompt_builder) -> dict[str, object]:
    raw = path.read_text(encoding="utf-8")
    title = first_heading(raw, path.stem.replace("-", " ").title())
    body = excerpt(raw)
    return {
        "id": f"{source_id}-{path.stem.lower()}",
        "sourceID": source_id,
        "title": title,
        "prompt": prompt_builder(title, body),
        "body": body,
        "tags": tags_for_text(source_id, f"{title}\n{raw}"),
    }


def wonder_snippets(path: Path) -> list[dict[str, object]]:
    raw = path.read_text(encoding="utf-8")
    title = first_heading(raw, path.stem.replace("-", " ").title())
    paragraphs = clean_paragraphs(raw)
    if not paragraphs:
        body = excerpt(raw, limit=1_150)
        return [{
            "id": f"wonder-compass-{path.stem.lower()}",
            "sourceID": "wonder-compass",
            "title": title,
            "prompt": prompt_for_wonder(title, body),
            "body": body,
            "tags": tags_for_text("wonder-compass", f"{title}\n{raw}"),
        }]

    windows: list[str] = []
    window: list[str] = []
    current_length = 0
    for paragraph in paragraphs:
        normalized = re.sub(r"\s+", " ", paragraph).strip()
        if not normalized:
            continue
        if window and current_length + len(normalized) > 1_250:
            windows.append(" ".join(window))
            window = []
            current_length = 0
        window.append(normalized)
        current_length += len(normalized) + 1
    if window:
        windows.append(" ".join(window))

    chapter_tags = tags_for_text("wonder-compass", f"{title}\n{raw}")
    snippets: list[dict[str, object]] = []
    for index, body in enumerate(windows[:6], start=1):
        passage_title = title if len(windows) == 1 else f"{title} · Passage {index}"
        snippets.append({
            "id": f"wonder-compass-{path.stem.lower()}-p{index}",
            "sourceID": "wonder-compass",
            "title": passage_title,
            "prompt": prompt_for_wonder(title, body),
            "body": clipped_excerpt(body),
            "tags": tags_for_text("wonder-compass", f"{passage_title}\n{body}\n{' '.join(chapter_tags)}"),
        })
    return snippets


def patreon_snippets() -> list[dict[str, object]]:
    fallback = [
        {
            "id": "patreon-clubhouse-free-shelf",
            "sourceID": "patreon-packet",
            "title": "Patreon Clubhouse",
            "prompt": "The free shelf is open.",
            "body": (
                "The Wonder Compass ebook, printable play-sheets, Spark menus, Playful Mission menus, "
                f"and Clubhouse notes live at {PATREON_URL}. The practice is free; the attention is real."
            ),
            "tags": ["patreon", "clubhouse", "wonder-compass", "free"],
        }
    ]

    adapter_path = ROOT / "scripts" / "patreon-adapter.py"
    if not adapter_path.exists():
        return fallback
    try:
        spec = importlib.util.spec_from_file_location("patreon_adapter_for_inside_cover", adapter_path)
        if spec is None or spec.loader is None:
            return fallback
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        status = module.status()
    except Exception:
        return fallback

    if not status.get("connected"):
        return fallback

    campaign = (status.get("campaigns") or [{}])[0]
    attrs = campaign.get("attributes") or {}
    campaign_name = clean_markdown(str(attrs.get("creation_name") or "Real Life, Re-Enchanted"))
    campaign_url = str(attrs.get("url") or PATREON_URL).strip() or PATREON_URL
    posts = status.get("posts") or []
    recent = []
    for post in posts[:6]:
        post_attrs = post.get("attributes") or {}
        title = clean_markdown(str(post_attrs.get("title") or "")).strip()
        published = str(post_attrs.get("published_at") or "")[:10]
        excerpt_text = plain_text(
            post_attrs.get("content")
            or post_attrs.get("teaser_text")
            or post_attrs.get("excerpt")
            or post_attrs.get("post_metadata")
            or ""
        )
        if title:
            recent.append((title, published, excerpt_text))

    if not recent:
        return fallback

    recent_lines = "\n".join(
        f"- {title}" + (f" ({published})" if published else "")
        for title, published, _ in recent[:5]
    )
    body = (
        f"{campaign_name} is the public Clubhouse shelf at {campaign_url}.\n\n"
        f"Recent posts:\n{recent_lines}\n\n"
        "The app keeps private pages local; this card only points to public/shared material."
    )
    snippets = [
        {
            "id": "patreon-current-shelf",
            "sourceID": "patreon-packet",
            "title": campaign_name,
            "prompt": "See what is new in the Clubhouse.",
            "body": body,
            "tags": ["patreon", "clubhouse", "recent-posts", "wonder-compass"],
        }
    ]
    for post in posts[:8]:
        post_attrs = post.get("attributes") or {}
        title = clean_markdown(str(post_attrs.get("title") or "")).strip()
        published = str(post_attrs.get("published_at") or "")[:10]
        raw_url = str(post_attrs.get("url") or "").strip()
        preview = plain_text(
            post_attrs.get("content")
            or post_attrs.get("teaser_text")
            or post_attrs.get("excerpt")
            or post_attrs.get("post_metadata")
            or ""
        )
        if not title:
            continue
        full_url = raw_url if raw_url.startswith("http") else f"https://www.patreon.com{raw_url}"
        snippets.append({
            "id": f"patreon-post-{post.get('id')}",
            "sourceID": "patreon-packet",
            "title": title,
            "prompt": "A Clubhouse post is ready.",
            "body": (
                f"{title}"
                + (f"\nPublished: {published}" if published else "")
                + (f"\nPreview: {preview}" if preview else "")
                + f"\n{full_url}"
            ),
            "tags": ["patreon", "clubhouse", "post"],
            "url": full_url,
            "publishedAt": published,
            "preview": preview,
        })
    return snippets


def existing_payload_section(key: str) -> list[dict[str, object]]:
    if not OUTPUT.exists():
        return []
    try:
        payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
    except Exception:
        return []
    section = payload.get(key)
    return section if isinstance(section, list) else []


def main() -> None:
    wonder = [
        item
        for path in wonder_files()
        for item in wonder_snippets(path)
    ]
    lore = [
        snippet(path, "enchantify-lore", prompt_for_lore)
        for path in LORE_FILES
        if path.exists()
    ]
    patreon = patreon_snippets()
    if patreon and patreon[0].get("id") == "patreon-clubhouse-free-shelf":
        patreon = existing_payload_section("patreon") or patreon
    character_illustrations = character_illustration_profiles()
    payload = {
        "version": 1,
        "generatedFrom": {
            "wonderCompass": str(WONDER_DIR.relative_to(ROOT)),
            "enchantifyLore": [str(path.relative_to(ROOT)) for path in LORE_FILES if path.exists()],
            "patreon": "scripts/patreon-adapter.py status",
            "characterVisuals": str(CHARACTER_VISUALS.relative_to(ROOT)),
        },
        "wonderCompass": wonder,
        "enchantifyLore": lore,
        "patreon": patreon,
        "characterIllustrations": character_illustrations,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")
    print(f"Wonder Compass snippets: {len(wonder)}")
    print(f"Enchantify lore snippets: {len(lore)}")
    print(f"Patreon snippets: {len(patreon)}")
    print(f"Character illustration profiles: {len(character_illustrations)}")


if __name__ == "__main__":
    main()

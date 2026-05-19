#!/usr/bin/env python3
"""Build and maintain Enchantify's character visual canon.

The visual bible is self-forming: recurring/high-Belief characters receive a
stable prompt dossier without requiring manual approval. The generated entries
are intentionally compact so image prompts stay consistent without becoming
police sketches.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent
CHARACTERS_MD = BASE / "lore" / "characters.md"
REGISTER_MD = BASE / "lore" / "world-register.md"
VISUALS_JSON = BASE / "lore" / "character-visuals.json"

CORE_NAMES = {
    "Headmistress Seraphina Thorne",
    "Headmistress Thorne",
    "Zara Finch",
    "Wicker Eddies",
    "Finn Bridges",
    "Serenity Brown",
    "Professor Cedric Stonebrook",
    "Professor Stonebrook",
    "Professor Luna Wispwood",
    "Professor Eleanor Euphony",
    "Professor Lydia Boggle",
    "Boggle",
    "Professor Vivian Villanelle",
    "Dr. Elowen Vellum",
    "Dr. Selene Inkrest",
    "Quentin Pagester",
    "Archibald Evergreen",
}

CANON_BELIEF = 20
AUTO_BELIEF = 15

CHAPTER_PALETTES = {
    "Emberheart": "ember red, warm gold, charcoal ink",
    "Mossbloom": "moss green, bark brown, soft lichen gray",
    "Riddlewind": "ink blue, parchment cream, quick silver",
    "Tidecrest": "sea-glass green, storm gray, tidal blue",
    "Duskthorn": "black violet, tarnished brass, cold white",
}

CHAPTER_OBJECTS = {
    "Emberheart": "a red-chalk mark or small brass striker",
    "Mossbloom": "a moss-edged notebook or pressed leaf",
    "Riddlewind": "a puzzle slip or annotated index card",
    "Tidecrest": "a sea-glass charm or ribbon that looks wind-tugged",
    "Duskthorn": "a wrong-looking key or a margin sigil",
}

ROLE_OBJECTS = [
    ("therap", "a black-sand hourglass"),
    ("longevity", "a silver bookmark-caliper"),
    ("diet", "a silver bookmark-caliper"),
    ("librarian", "a ring of catalog keys"),
    ("archivist", "a precise catalog card"),
    ("headmistress", "an antique star-dark key"),
    ("headmaster", "a severe black journal"),
    ("professor", "a lesson object held like evidence"),
    ("enchantment guardian", "a small warding charm"),
    ("benefactor", "a polished calling card"),
    ("villain", "a torn margin scrap"),
]

INTEREST_OBJECTS = [
    ("sea glass", "a chipped blue sea-glass pendant"),
    ("thrift", "a thrifted satchel of found objects"),
    ("elder scrolls", "a tiny hand-drawn Tamriel map charm"),
    ("consciousness", "a black-sand hourglass"),
    ("longevity", "a silver bookmark-caliper"),
    ("architecture", "a miniature foundation stone"),
    ("music", "a tuning fork"),
    ("poetry", "a narrow folded poem"),
    ("stationery", "a fountain pen with a labeled nib"),
    ("weather", "a pocket barometer"),
    ("geocaching", "a brass coordinate tag"),
    ("plants", "a little green cutting in a glass vial"),
    ("library", "a catalog card"),
    ("book", "a catalog card"),
    ("gossip", "a folded note sealed with a smirk"),
    ("martial", "wrapped sparring tape"),
    ("parks", "a pressed trail leaf"),
    ("riddle", "a folded puzzle slip"),
    ("puns", "a punning margin note"),
]

PERSONALITY_POSTURES = [
    ("quiet", "slight, inward posture; attentive hands"),
    ("perceptive", "watchful eyes; head tilted as if listening between words"),
    ("charismatic", "open stance; one hand mid-invitation"),
    ("cunning", "half-smile; fingers near the meaningful object"),
    ("patient", "still posture; hands relaxed and deliberate"),
    ("spontaneous", "leaning forward as if already leaving"),
    ("energetic", "animated posture; coat or scarf caught in motion"),
    ("meticulous", "upright posture; hands arranging one exact detail"),
    ("warm", "soft expression; shoulders lowered in welcome"),
    ("brooding", "chin lowered; eyes under shadowed brows"),
    ("dreamy", "unfocused gaze; body half-turned toward an unseen thought"),
    ("competitive", "squared shoulders; challenging gaze"),
    ("playful", "bright expression; hands caught in a joke or trick"),
]

PERSONALITY_FEATURES = [
    ("quiet", "soft mouth and observant eyes"),
    ("charismatic", "bright, controlled expression"),
    ("cunning", "sharp eyes and a knowing half-smile"),
    ("patient", "calm eyes and weathered gentleness"),
    ("spontaneous", "wind-tossed hair and lively eyes"),
    ("meticulous", "neat hair and precise gaze"),
    ("warm", "kind eyes and an expression that listens"),
    ("brooding", "shadowed eyes and severe cheekbones"),
    ("dreamy", "faraway eyes and softened edges"),
    ("competitive", "direct gaze and taut jaw"),
    ("playful", "mischievous eyes and a ready grin"),
]


def clean(value: str, limit: int = 240) -> str:
    value = re.sub(r"`([^`]+)`", r"\1", value or "")
    value = re.sub(r"\*\*([^*]+)\*\*", r"\1", value)
    value = re.sub(r"\[(?:thread|id):[^\]]+\]", "", value, flags=re.IGNORECASE)
    value = value.replace("*", "")
    value = re.sub(r"\s+", " ", value).strip()
    return value[:limit].rstrip() + ("..." if len(value) > limit else "")


def parse_characters() -> dict[str, dict[str, str]]:
    text = CHARACTERS_MD.read_text(encoding="utf-8", errors="ignore") if CHARACTERS_MD.exists() else ""
    roster: dict[str, dict[str, str]] = {}

    for m in re.finditer(r"^###\s+(.+?)(?:\s+[—-].*)?$", text, re.MULTILINE):
        name = m.group(1).strip()
        next_m = re.search(r"^###\s+", text[m.end():], re.MULTILINE)
        section = text[m.end():m.end() + next_m.start()] if next_m else text[m.end():]
        fields: dict[str, str] = {}
        for fm in re.finditer(r"^\*\*([^*:]+):\*\*\s*(.+)$", section, re.MULTILINE):
            fields[fm.group(1).strip().lower()] = clean(fm.group(2), 500)
        roster[name] = fields

    compact_re = re.compile(
        r"^\*\*([^*\n]+?)\*\*(?:\s+\([^\n]*?\)|\s+\*\([^\n]*?\)\*)?\s+[—-]\s+(.+?)(?=^\*\*|\n-----|\n## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    for m in compact_re.finditer(text):
        name = m.group(1).strip()
        body = clean(m.group(2), 900)
        fields = roster.setdefault(name, {})
        interest_m = re.search(r"Unwritten Interest:\s*(.+?)(?:Voice:|$)", body, re.IGNORECASE)
        voice_m = re.search(r"Voice:\s*(.+)$", body, re.IGNORECASE)
        personality = re.sub(r"\s*(?:Unwritten Interest|Voice):.*$", "", body, flags=re.IGNORECASE).strip()
        if personality:
            fields.setdefault("personality", personality)
        if interest_m:
            fields.setdefault("unwritten interest", clean(interest_m.group(1).rstrip("."), 260))
        if voice_m:
            fields.setdefault("voice", clean(voice_m.group(1), 180))
    return roster


def parse_register() -> dict[str, dict[str, object]]:
    text = REGISTER_MD.read_text(encoding="utf-8", errors="ignore") if REGISTER_MD.exists() else ""
    rows: dict[str, dict[str, object]] = {}
    for line in text.splitlines():
        if not line.startswith("|") or "---" in line:
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) < 4 or parts[0].lower() in {"entity", "talisman", "name"}:
            continue
        try:
            belief = int(re.search(r"(\d+)", parts[2]).group(1))
        except Exception:
            continue
        rows[parts[0]] = {
            "type": parts[1],
            "belief": belief,
            "notes": parts[3],
            "threads": re.findall(r"\[thread:([^\]]+)\]", parts[3]),
        }
    return rows


def normalize_name(name: str) -> str:
    name = re.sub(r"\s+\([^)]*\)", "", name).strip()
    if name.startswith("Headmistress ") and name != "Headmistress Thorne":
        return name
    return name


def register_for(name: str, register: dict[str, dict[str, object]]) -> dict[str, object]:
    if name in register:
        return register[name]
    aliases = {
        "Headmistress Seraphina Thorne": "Headmistress Thorne",
        "Professor Cedric Stonebrook": "Professor Stonebrook",
        "Professor Lydia Boggle": "Boggle",
    }
    if aliases.get(name) in register:
        return register[aliases[name]]
    last = name.split()[-1].lower()
    for key, row in register.items():
        if key.split()[-1].lower() == last:
            return row
    return {}


def infer_chapter(name: str, fields: dict[str, str], row: dict[str, object]) -> str:
    text = " ".join([name, " ".join(fields.values()), str(row.get("notes", ""))])
    for chapter in CHAPTER_PALETTES:
        if chapter.lower() in text.lower():
            return chapter
    return ""


def pick_first(text: str, choices: list[tuple[str, str]], default: str) -> str:
    low = text.lower()
    for key, value in choices:
        if key in low:
            return value
    return default


def visual_entry(name: str, fields: dict[str, str], row: dict[str, object]) -> dict[str, object]:
    chapter = infer_chapter(name, fields, row)
    belief = int(row.get("belief", 0) or 0)
    notes = str(row.get("notes", ""))
    role = fields.get("role") or notes or fields.get("species") or "Academy character"
    personality = fields.get("personality", "")
    quirks = fields.get("quirks", "")
    interest = fields.get("unwritten interest", "")
    species = fields.get("species", "")
    combined = " ".join([name, role, personality, quirks, interest, species, notes])

    feature = pick_first(combined, PERSONALITY_FEATURES, "clear expressive eyes and a memorable silhouette")
    posture = pick_first(combined, PERSONALITY_POSTURES, "recognizable posture; hands involved in the scene")
    object_default = CHAPTER_OBJECTS.get(chapter, "one small object tied to their current story")
    signature = pick_first(combined, INTEREST_OBJECTS, pick_first(combined, ROLE_OBJECTS, object_default))
    palette = CHAPTER_PALETTES.get(chapter, "muted sepia, soft gray, one jewel-toned accent")

    if "Vellum" in name:
        feature = "silver-pale hair pinned with exacting care; sharp kind eyes"
        posture = "upright, precise posture; hands annotating or measuring"
        signature = "a silver bookmark-caliper and red marginal notes"
        palette = "warm parchment, clinical silver, cranberry ink"
    elif "Inkrest" in name:
        feature = "dark thoughtful eyes; soft silver-black hair; calm listening face"
        posture = "still, grounded posture; hands around a teacup or hourglass"
        signature = "a black-sand hourglass and tea cup with marginalia"
        palette = "charcoal ink, moonlit gray, muted violet"
    elif "Zara Finch" in name:
        feature = "watchful gray eyes; ink-dark bobbed hair; quiet attentive face"
        posture = "slight inward posture; careful hands protecting a found object"
        signature = "a chipped blue sea-glass pendant and thrifted satchel"
        palette = "sea-glass green, storm gray, faded brass"
    elif "Wicker Eddies" in name:
        feature = "sharp smile; bright predatory eyes; handsome face that never fully relaxes"
        posture = "easy confident lean; fingers near a wrong-door brass key"
        signature = "a wrong-door brass key and tiny chaos sigils in the margins"
        palette = "black violet, tarnished brass, cold red"
    elif "Thorne" in name and "Headmistress" in name:
        feature = "ageless literary-elf face; star-cold eyes; hair pinned like a dark crown"
        posture = "regal stillness; one hand resting on an antique key"
        signature = "an antique star-dark key and a crownlike hairpin"
        palette = "ink black, old silver, star-gold"
    elif name in {"Boggle", "Professor Lydia Boggle"}:
        feature = "bright mischievous eyes; expressive mouth caught before a pun"
        posture = "springy sideways posture; hands presenting a joke as evidence"
        signature = "a punning margin note and ink-smudged fingertips"
        palette = "ink blue, warm yellow, raspberry red"

    confidence = "core" if name in CORE_NAMES or belief >= CANON_BELIEF else "auto"
    core = f"{clean(role, 150)}; {feature}"
    avoid = "generic anime face, room-first composition, inconsistent signature object, polished digital fantasy portrait"
    if "Book Fae" in combined or "Literary Elf" in combined:
        avoid += ", ordinary human office-worker styling"

    return {
        "status": "canonical",
        "source": "auto-core" if confidence == "core" else "auto-belief",
        "belief_at_canon": belief,
        "chapter": chapter or None,
        "core": clean(core, 260),
        "signature": clean(signature, 180),
        "palette": palette,
        "silhouette": clean(posture, 180),
        "continuity": "Preserve these identifiers across images; clothes, pose, age-light, and mood may vary with the scene.",
        "avoid": avoid,
        "updated": datetime.now().strftime("%Y-%m-%d"),
    }


def should_canonize(name: str, row: dict[str, object]) -> bool:
    belief = int(row.get("belief", 0) or 0)
    threads = row.get("threads") or []
    return name in CORE_NAMES or belief >= AUTO_BELIEF or bool(threads and belief >= 8)


def load_visuals() -> dict[str, object]:
    if not VISUALS_JSON.exists():
        return {"version": 1, "updated": None, "characters": {}}
    try:
        data = json.loads(VISUALS_JSON.read_text(encoding="utf-8"))
        data.setdefault("characters", {})
        return data
    except Exception:
        return {"version": 1, "updated": None, "characters": {}}


def save_visuals(data: dict[str, object], dry_run: bool = False) -> None:
    data["updated"] = datetime.now().strftime("%Y-%m-%d")
    if dry_run:
        print(json.dumps(data, indent=2, ensure_ascii=False)[:4000])
        return
    VISUALS_JSON.parent.mkdir(parents=True, exist_ok=True)
    tmp = VISUALS_JSON.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(VISUALS_JSON)


def sync(dry_run: bool = False) -> dict[str, object]:
    roster = parse_characters()
    register = parse_register()
    data = load_visuals()
    characters = data.setdefault("characters", {})
    assert isinstance(characters, dict)
    changed = []
    for name, fields in roster.items():
        row = register_for(name, register)
        if should_canonize(name, row):
            existing = characters.get(name)
            entry = visual_entry(name, fields, row)
            if existing:
                if str(existing.get("source", "")).startswith("manual"):
                    # Keep hand-tuned visual canon, but refresh metadata.
                    merged = dict(entry)
                    merged.update(existing)
                    merged["belief_at_canon"] = max(int(existing.get("belief_at_canon", 0) or 0), int(entry["belief_at_canon"]))
                    merged["updated"] = entry["updated"]
                    entry = merged
            if characters.get(name) != entry:
                characters[name] = entry
                changed.append(name)
    data["last_changed"] = changed
    save_visuals(data, dry_run=dry_run)
    return data


def visual_for(name: str) -> dict[str, object] | None:
    data = load_visuals()
    chars = data.get("characters") or {}
    if name in chars:
        return chars[name]
    aliases = {
        "Headmistress Thorne": "Headmistress Seraphina Thorne",
        "Professor Stonebrook": "Professor Cedric Stonebrook",
        "Boggle": "Professor Lydia Boggle",
        "Professor Boggle": "Professor Lydia Boggle",
    }
    if aliases.get(name) in chars:
        return chars[aliases[name]]
    last = name.split()[-1].lower()
    for key, value in chars.items():
        if key.split()[-1].lower() == last:
            return value
    return None


def prompt_fragment(name: str) -> str:
    entry = visual_for(name)
    if not entry:
        return ""
    parts = [
        f"CANONICAL VISUAL IDENTITY for {name}: {entry.get('core')}",
        f"Recurring signature: {entry.get('signature')}",
        f"Palette: {entry.get('palette')}",
        f"Silhouette/posture: {entry.get('silhouette')}",
        str(entry.get("continuity") or ""),
        f"Avoid: {entry.get('avoid')}",
    ]
    return " ".join(clean(str(p), 320) for p in parts if p)


def main() -> int:
    parser = argparse.ArgumentParser(description="Maintain character visual canon")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("sync", help="Update lore/character-visuals.json from characters/register")
    p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("fragment", help="Print prompt fragment for one character")
    p.add_argument("name")
    sub.add_parser("list", help="List canonical character visuals")
    args = parser.parse_args()

    if args.command == "sync":
        data = sync(dry_run=args.dry_run)
        chars = data.get("characters") or {}
        changed = data.get("last_changed") or []
        print(f"Character visuals synced: {len(chars)} canonical; {len(changed)} changed")
        for name in changed[:20]:
            print(f"- {name}")
        if len(changed) > 20:
            print(f"...and {len(changed) - 20} more")
        return 0
    if args.command == "fragment":
        print(prompt_fragment(args.name))
        return 0
    if args.command == "list":
        data = load_visuals()
        for name in sorted((data.get("characters") or {}).keys()):
            print(name)
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Parse lore/characters.md into a roster with chapter, role, and tags."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent
CHARACTERS_MD = BASE / "lore" / "characters.md"
ROSTER_CACHE = BASE / "config" / "character-roster.json"

CHAPTERS = ("Riddlewind", "Emberheart", "Mossbloom", "Tidecrest", "Duskthorn")
INVALID_NAME_RE = re.compile(
    r"^(Personality|Faults|Quirks|Goals|Role|Species|Secret|Voice|"
    r"Unwritten Interest|Story hooks|Chapter alignment|Data sources|"
    r"Functions|Beliefs|Magical tradition|Therapeutic spine|"
    r"Office hours|Output shape|Safety and limits|Supplement).*:?$",
    re.I,
)


CHAPTER_ALIASES = {
    "riddlewind": "Riddlewind",
    "emberheart": "Emberheart",
    "mossbloom": "Mossbloom",
    "tidecrest": "Tidecrest",
    "duskthorn": "Duskthorn",
}


@dataclass
class CharacterEntry:
    name: str
    role: str = "unknown"
    chapter: str = ""
    tags: list[str] = field(default_factory=list)
    section: str = ""


def _clean_name(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"\s*\*[^*]+\*\s*", " ", raw)
    raw = re.sub(r"\s*\([^)]*Wicker[^)]*\)\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s+\([^)]*(?:Mossbloom|Emberheart|Tidecrest|Riddlewind)[^)]*\)\s*$", "", raw, flags=re.I)
    raw = re.sub(r"\s+[—-]\s+.*$", "", raw)
    return re.sub(r"\s+", " ", raw).strip()


def _valid_name(name: str) -> bool:
    if not name or len(name) < 3:
        return False
    if name.endswith(":"):
        return False
    if INVALID_NAME_RE.match(name):
        return False
    return True


def _chapter_from_text(text: str) -> str:
    for key, canon in CHAPTER_ALIASES.items():
        if re.search(rf"\b{key}\b", text, re.IGNORECASE):
            return canon
    return ""


def parse_roster(text: str | None = None) -> dict[str, CharacterEntry]:
    text = text if text is not None else CHARACTERS_MD.read_text(encoding="utf-8", errors="replace")
    roster: dict[str, CharacterEntry] = {}
    current_section = ""
    current_chapter = ""

    def add(name: str, role: str, chapter: str = "", tags: list[str] | None = None) -> None:
        name = _clean_name(name)
        if not _valid_name(name):
            return
        tags = list(tags or [])
        if "Wicker" in name or "wicker" in (text or ""):
            pass
        entry = roster.get(name)
        if entry:
            if chapter and not entry.chapter:
                entry.chapter = chapter
            if role != "unknown" and entry.role == "unknown":
                entry.role = role
            for tag in tags:
                if tag not in entry.tags:
                    entry.tags.append(tag)
            return
        roster[name] = CharacterEntry(
            name=name,
            role=role,
            chapter=chapter,
            tags=tags,
            section=current_section,
        )

    for line in text.splitlines():
        if line.startswith("## "):
            current_section = line[3:].strip()
            m = re.match(r"Students\s*[—-]\s*Chapter\s+(\w+)", current_section, re.I)
            current_chapter = CHAPTER_ALIASES.get(m.group(1).lower(), m.group(1)) if m else ""
            if "Library Staff" in current_section:
                current_chapter = "Mossbloom"
            continue

        if line.startswith("### "):
            title = line[4:].strip()
            name = re.sub(r"\s+[—-].*$", "", title).strip()
            chapter = _chapter_from_text(title)
            role = "faculty"
            if re.search(r"headmistress|headmaster", title, re.I):
                role = "head"
            tags: list[str] = []
            if "duskthorn" in title.lower() or "secret" in text[text.find(line) : text.find(line) + 800].lower():
                if "duskthorn" in text[text.find(line) : text.find(line) + 1200].lower():
                    tags.append("duskthorn")
            add(name, role, chapter or current_chapter, tags)
            continue

        m = re.match(r"^\*\*(.+?)\*\*", line.strip())
        if m and "—" in line:
            name = m.group(1).strip()
            tags = []
            if re.search(r"Wicker", line, re.I):
                tags.append("wicker_crew")
            if re.search(r"Duskthorn", line, re.I):
                tags.append("duskthorn")
            if "Library Staff" in current_section:
                add(name, "staff", current_chapter or "Mossbloom", tags)
            else:
                add(name, "student", current_chapter, tags)
            continue

        m = re.match(r"^\*\*(.+?)\*\*\s*\(", line.strip())
        if m and current_section and "Staff" in current_section:
            add(m.group(1).strip(), "staff", current_chapter, [])

    # Second pass: duskthorn secrets in ### blocks
    for m in re.finditer(r"^###\s+(.+?)$", text, re.MULTILINE):
        name = _clean_name(m.group(1))
        end = text.find("\n### ", m.end())
        block = text[m.end() : end if end != -1 else len(text)]
        if re.search(r"chapter\s+duskthorn|member of chapter duskthorn|part of chapter duskthorn", block, re.I):
            entry = roster.get(name)
            if entry and "duskthorn" not in entry.tags:
                entry.tags.append("duskthorn")

    for m in re.finditer(r"^\*\*(.+?)\*\*.*$", text, re.MULTILINE):
        name = _clean_name(m.group(1))
        if name in roster:
            continue
        if "—" not in m.group(0) and len(name) > 3:
            section = ""
            pos = m.start()
            prior = text[:pos]
            sec_m = re.findall(r"^## (.+)$", prior, re.MULTILINE)
            if sec_m:
                section = sec_m[-1]
            role = "staff" if any(x in section for x in ("Staff", "Fae", "Library", "Guardian", "Benefactor")) else "other"
            add(name, role, "", [])

    return roster


def roster_as_dict(roster: dict[str, CharacterEntry] | None = None) -> dict[str, Any]:
    roster = roster or parse_roster()
    return {name: asdict(entry) for name, entry in sorted(roster.items())}


def write_roster_cache() -> Path:
    ROSTER_CACHE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "generated_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "count": 0,
        "characters": roster_as_dict(),
    }
    data["count"] = len(data["characters"])
    ROSTER_CACHE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return ROSTER_CACHE


def students_by_chapter(roster: dict[str, CharacterEntry]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {c: [] for c in CHAPTERS if c != "Duskthorn"}
    for name, entry in roster.items():
        if entry.role == "student" and entry.chapter in out:
            out[entry.chapter].append(name)
    return out


def faculty_by_chapter(roster: dict[str, CharacterEntry]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {c: [] for c in CHAPTERS if c != "Duskthorn"}
    for name, entry in roster.items():
        if entry.role in {"faculty", "head"} and entry.chapter in out:
            out[entry.chapter].append(name)
    return out


if __name__ == "__main__":
    path = write_roster_cache()
    roster = parse_roster()
    students = students_by_chapter(roster)
    print(f"Wrote {path} ({len(roster)} characters)")
    for ch, names in students.items():
        print(f"  {ch}: {len(names)} students")

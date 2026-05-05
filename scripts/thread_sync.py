#!/usr/bin/env python3
"""Shared thread synchronization helpers for threads.md and world-register.md."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

BASE = Path(__file__).resolve().parent.parent
THREADS_MD = BASE / "lore" / "threads.md"
REGISTER_MD = BASE / "lore" / "world-register.md"


def read_text(path: Path) -> str:
    return path.read_text() if path.exists() else ""


def write_text(path: Path, content: str, dry_run: bool = False) -> None:
    if dry_run:
        print(f"  [dry-run] Would write {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _thread_section_pattern(name: str):
    bare = re.sub(r'^[Tt]he\s+', '', name)
    return re.compile(
        r'(^## Thread:\s*(?:The\s+)?' + re.escape(bare) + r'.*?$)(.*?)(?=^## |\Z)',
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )


def _thread_row_pattern(name: str):
    bare = re.sub(r'^[Tt]he\s+', '', name)
    return re.compile(
        r'^(\|\s*(?:The\s+)?' + re.escape(bare) + r'\s*\|\s*Thread\s*\|\s*\d+\s*\|)\s*([^|]*)\|',
        re.MULTILINE | re.IGNORECASE,
    )


def normalize_thread_fields(content: str) -> str:
    """Repair common thread field markdown scars without changing story text."""
    field_names = (
        "id",
        "type",
        "phase",
        "pressure",
        "npc_anchor",
        "locations",
        "entities",
        "Nothing pressure",
        "Next beat",
        "Last advanced",
        "Last visited",
        "born",
        "closed",
        "GPS",
    )
    label_pattern = "|".join(re.escape(name) for name in sorted(field_names, key=len, reverse=True))
    return re.sub(
        rf"^\*\*({label_pattern}):(?!(?:\*\*))\s*(.*)$",
        lambda m: f"**{m.group(1)}:** {m.group(2).strip()}",
        content,
        flags=re.MULTILINE | re.IGNORECASE,
    )


def _replace_thread_field(section: str, label: str, value: str) -> tuple[str, bool]:
    """Set a thread field, accepting both canonical and half-formed bold labels."""
    pat = re.compile(
        rf"^\*\*({re.escape(label)}):(?:\*\*)?\s*.*$",
        re.MULTILINE | re.IGNORECASE,
    )
    updated, count = pat.subn(f"**{label}:** {value}", section, count=1)
    return updated, count > 0


def update_thread_in_threads_text(content: str, name: str, phase: Optional[str] = None, next_beat: Optional[str] = None, last_advanced: Optional[str] = None) -> tuple[str, bool]:
    content = normalize_thread_fields(content)
    pat = _thread_section_pattern(name)
    m = pat.search(content)
    if not m:
        return content, False

    section = m.group(2)
    changed = False

    if phase:
        new_section, field_changed = _replace_thread_field(section, "phase", phase)
        changed = changed or field_changed
        section = new_section

    if next_beat:
        new_section, field_changed = _replace_thread_field(section, "Next beat", next_beat)
        changed = changed or field_changed
        section = new_section

    if last_advanced:
        new_section, field_changed = _replace_thread_field(section, "Last advanced", last_advanced)
        changed = changed or field_changed
        section = new_section

    if not changed:
        return content, False
    return content[:m.start(2)] + section + content[m.end(2):], True


def update_thread_in_register_text(content: str, name: str, phase: Optional[str] = None, status: Optional[str] = None) -> tuple[str, bool]:
    pat = _thread_row_pattern(name)
    m = pat.search(content)
    if not m:
        return content, False

    old_notes = m.group(2).strip()
    id_tag = re.search(r'\[id:[^\]]+\]', old_notes)
    existing_phase = re.search(r'Phase:\s*(\w+)', old_notes, re.IGNORECASE)
    existing_status = re.search(r'Phase:\s*\w+\s*—\s*(.+)$', old_notes, re.IGNORECASE)

    final_phase = phase or (existing_phase.group(1) if existing_phase else None)
    final_status = status or (existing_status.group(1).strip() if existing_status else None)
    if not final_phase and not final_status:
        return content, False

    pieces = []
    if id_tag:
        pieces.append(id_tag.group(0))
    if final_phase:
        pieces.append(f'Phase: {final_phase}')
    if final_status:
        if final_phase:
            pieces[-1] += f' — {final_status}'
        else:
            pieces.append(final_status)
    new_notes = ' ' + ' '.join(pieces) + ' '
    new_row = m.group(1) + new_notes + '|'
    new_content = content[:m.start()] + new_row + content[m.end():]
    return new_content, new_content != content


def sync_thread_files(name: str, phase: Optional[str] = None, status: Optional[str] = None, next_beat: Optional[str] = None, last_advanced: Optional[str] = None, dry_run: bool = False) -> dict:
    threads_text = read_text(THREADS_MD)
    register_text = read_text(REGISTER_MD)

    updated_threads, threads_changed = update_thread_in_threads_text(
        threads_text,
        name,
        phase=phase,
        next_beat=next_beat,
        last_advanced=last_advanced,
    )
    updated_register, register_changed = update_thread_in_register_text(
        register_text,
        name,
        phase=phase,
        status=status,
    )

    if threads_changed:
        write_text(THREADS_MD, updated_threads, dry_run=dry_run)
    if register_changed:
        write_text(REGISTER_MD, updated_register, dry_run=dry_run)

    return {
        "threads_changed": threads_changed,
        "register_changed": register_changed,
        "threads_text": updated_threads,
        "register_text": updated_register,
    }

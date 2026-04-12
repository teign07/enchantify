"""
actions/obsidian.py — Obsidian vault operations via filesystem.

Requires ENCHANTIFY_OBSIDIAN_VAULT env var (set in enchantify-config.sh).
Standard interface: run(action_id, params) → {"success": bool, "message": str}
"""
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional


def _vault() -> Optional[Path]:
    v = os.environ.get("ENCHANTIFY_OBSIDIAN_VAULT", "")
    if not v:
        return None
    p = Path(v)
    return p if p.exists() else None


def create_note(title: str, content: str, tags: list[str] = None, folder: str = None) -> dict:
    vault = _vault()
    if not vault:
        return {"success": False, "message": "ENCHANTIFY_OBSIDIAN_VAULT not set or not found"}

    tags = tags or []
    tag_block = "\n".join(f"  - {t}" for t in tags)
    frontmatter = f"---\ntags:\n{tag_block}\ncreated: {datetime.now().strftime('%Y-%m-%d')}\nsource: enchantify\n---\n\n" if tags else ""

    target_dir = vault / folder if folder else vault
    target_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize filename
    safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '-')
    path = target_dir / f"{safe_title}.md"

    # Don't overwrite existing notes
    if path.exists():
        return {"success": False, "message": f"Note already exists: {path.name}"}

    path.write_text(frontmatter + content)
    return {"success": True, "message": f"Created note: {path.relative_to(vault)}"}


def add_tag(note_path: str, tag: str) -> dict:
    vault = _vault()
    if not vault:
        return {"success": False, "message": "ENCHANTIFY_OBSIDIAN_VAULT not set or not found"}

    path = vault / note_path
    if not path.exists():
        return {"success": False, "message": f"Note not found: {note_path}"}

    text = path.read_text()

    # Insert into existing tags block or add frontmatter
    if "tags:" in text:
        text = re.sub(r"(tags:.*?\n)(---)", lambda m: m.group(1) + f"  - {tag}\n" + m.group(2), text, flags=re.DOTALL)
    else:
        text = f"---\ntags:\n  - {tag}\n---\n\n" + text

    path.write_text(text)
    return {"success": True, "message": f"Added tag '{tag}' to {note_path}"}


def run(action_id: str, params: dict) -> dict:
    dispatch = {
        "obsidian_note_create": lambda: create_note(
            params.get("title", "Untitled"),
            params.get("content", ""),
            params.get("tags", []),
            params.get("folder"),
        ),
        "obsidian_note_tag": lambda: add_tag(
            params.get("path", ""),
            params.get("tag", ""),
        ),
    }
    fn = dispatch.get(action_id)
    if not fn:
        return {"success": False, "message": f"Unknown Obsidian action: {action_id}"}
    return fn()

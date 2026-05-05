#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent
LEDGER_DIR = BASE / "logs" / "scene-ledger"
GALLERY_DIR = BASE / "logs" / "scene-gallery"


def _archive_image_for_gallery(payload: dict[str, Any]) -> dict[str, Any]:
    results = payload.get("results")
    if not isinstance(results, dict):
        return payload

    image_result = results.get("image")
    if not isinstance(image_result, dict) or not image_result.get("ok"):
        return payload

    source_path = image_result.get("artifact_path")
    if not source_path:
        detail = str(image_result.get("detail") or "")
        import re
        m = re.search(r'(?:from|at)\s+([^\s]+\.(?:png|jpg|jpeg|webp|gif))', detail, re.IGNORECASE)
        if m:
            source_path = m.group(1)
    if not source_path:
        return payload

    source = Path(str(source_path)).expanduser()
    if source.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        return payload
    if not source.exists():
        return payload

    date_str = str(payload.get("recorded_at") or datetime.now().isoformat())[:10]
    dest_dir = GALLERY_DIR / date_str
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / source.name
    if not dest.exists() or source.stat().st_mtime > dest.stat().st_mtime:
        shutil.copy2(source, dest)

    image_result["gallery_path"] = str(dest)
    image_result["gallery_uri"] = dest.resolve().as_uri()
    return payload


def ledger_path(date_str: str | None = None) -> Path:
    day = date_str or datetime.now().strftime("%Y-%m-%d")
    return LEDGER_DIR / f"{day}.jsonl"


def append_entry(payload: dict[str, Any], date_str: str | None = None, dry_run: bool = False) -> Path:
    payload = _archive_image_for_gallery(payload)
    path = ledger_path(date_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, ensure_ascii=False)
    if not dry_run:
        with path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    return path


def load_entries(date_str: str | None = None) -> list[dict[str, Any]]:
    path = ledger_path(date_str)
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description="Append or inspect the Enchantify scene ledger")
    parser.add_argument("--append", action="store_true")
    parser.add_argument("--payload-file")
    parser.add_argument("--date")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--print", action="store_true", dest="do_print")
    args = parser.parse_args()

    if args.append:
        if not args.payload_file:
            raise SystemExit("--append requires --payload-file")
        payload = json.loads(Path(args.payload_file).read_text(encoding="utf-8"))
        path = append_entry(payload, date_str=args.date, dry_run=args.dry_run)
        print(path)
        return 0

    if args.do_print:
        print(json.dumps(load_entries(args.date), indent=2, ensure_ascii=False))
        return 0

    raise SystemExit("Pass --append --payload-file FILE or --print")


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Small stewardship helpers for unattended Enchantify jobs.

The goal is boring reliability: every cron ritual can record what happened and
can avoid sending the same artifact twice unless explicitly forced.
"""

from __future__ import annotations

import hashlib
import json
import socket
import time
import traceback
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterator


BASE_DIR = Path(__file__).resolve().parent.parent
LEDGER_DIR = BASE_DIR / "logs" / "steward"
RUN_LEDGER = LEDGER_DIR / "cron-runs.jsonl"
STATE_FILE = BASE_DIR / "config" / "cron-steward-state.json"


def _now() -> datetime:
    return datetime.now()


def now_iso() -> str:
    return _now().isoformat(timespec="seconds")


def content_hash(content: Any) -> str:
    if not isinstance(content, str):
        content = json.dumps(content, sort_keys=True, ensure_ascii=False, default=str)
    normalized = " ".join(content.split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {}
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    tmp.replace(STATE_FILE)


def _append(record: dict[str, Any]) -> None:
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    record.setdefault("at", now_iso())
    record.setdefault("host", socket.gethostname())
    with RUN_LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def record_event(job: str, event: str, **fields: Any) -> None:
    payload = {"job": job, "event": event}
    payload.update(fields)
    _append(payload)


@contextmanager
def run(job: str, **fields: Any) -> Iterator[dict[str, Any]]:
    started = time.time()
    run_id = f"{job}-{int(started)}"
    context: dict[str, Any] = {"run_id": run_id, "job": job}
    context.update(fields)
    record_event(job, "start", run_id=run_id, **fields)
    try:
        yield context
    except Exception as exc:
        record_event(
            job,
            "failed",
            run_id=run_id,
            duration_s=round(time.time() - started, 3),
            error=str(exc),
            traceback=traceback.format_exc()[-2000:],
        )
        raise
    else:
        record_event(
            job,
            "finished",
            run_id=run_id,
            duration_s=round(time.time() - started, 3),
            **{k: v for k, v in context.items() if k not in {"run_id", "job"}},
        )


def should_skip_duplicate(
    job: str,
    content: Any,
    *,
    cooldown_hours: float,
    force: bool = False,
    scope: str = "default",
) -> tuple[bool, str, str]:
    digest = content_hash(content)
    if force:
        return False, digest, "forced"

    state = _load_state()
    key = f"{job}:{scope}"
    entry = state.get(key, {})
    if entry.get("hash") == digest:
        try:
            last = datetime.fromisoformat(entry.get("at", ""))
            age = _now() - last
        except Exception:
            age = timedelta.max
        if age < timedelta(hours=cooldown_hours):
            minutes = int(age.total_seconds() // 60)
            return True, digest, f"duplicate content sent {minutes}m ago"
    return False, digest, "new content"


def mark_delivered(job: str, content: Any, *, scope: str = "default", **fields: Any) -> str:
    digest = content_hash(content)
    state = _load_state()
    key = f"{job}:{scope}"
    state[key] = {"hash": digest, "at": now_iso()}
    state[key].update(fields)
    _save_state(state)
    record_event(job, "delivered", scope=scope, fingerprint=digest[:16], **fields)
    return digest


def mark_skipped(job: str, reason: str, *, scope: str = "default", fingerprint: str = "", **fields: Any) -> None:
    record_event(job, "skipped", reason=reason, scope=scope, fingerprint=fingerprint[:16], **fields)

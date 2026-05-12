from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path


MECHANICS_STATE_VERSION = 1
PREFLIGHT_MAX_AGE_MINUTES = 15


def _read_safe(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _player_belief(workspace: Path, player_name: str) -> int | None:
    text = _read_safe(workspace / "players" / f"{player_name}.md")
    m = re.search(r'- \*\*Belief:\*\*\s*(\d+)', text)
    return int(m.group(1)) if m else None


def _last_compass_run(workspace: Path, player_name: str) -> str | None:
    souvenirs = workspace / "souvenirs"
    if not souvenirs.exists():
        return None

    dates = []
    for path in souvenirs.glob(f"*-{player_name}*.md"):
        m = re.match(r'(\d{4}-\d{2}-\d{2})-', path.name)
        if m:
            dates.append(m.group(1))
    return max(dates) if dates else None


def _session_file(workspace: Path, player_name: str) -> Path:
    return workspace / "players" / f"{player_name}-session.json"


def _load_runtime_state(workspace: Path, player_name: str) -> dict:
    path = _session_file(workspace, player_name)
    data = _read_json(path)
    if not isinstance(data, dict):
        data = {}

    mechanics = data.get("mechanics", {})
    if not isinstance(mechanics, dict):
        mechanics = {}

    mechanics.setdefault("version", MECHANICS_STATE_VERSION)
    mechanics.setdefault("last_roll_guidance_at", None)
    mechanics.setdefault("last_preflight_at", None)
    mechanics.setdefault("compass", {})
    mechanics.setdefault("enchantment", {})
    mechanics.setdefault("session", {})

    session = mechanics["session"]
    today = date.today().isoformat()
    if session.get("date") != today:
        mechanics["session"] = {
            "date": today,
            "enchantment_offers": 0,
            "enchantment_declines": 0,
            "compass_offers": 0,
            "compass_declines": 0,
            "last_offer_type": None,
            "last_offer_at": None,
        }
    else:
        session.setdefault("enchantment_offers", 0)
        session.setdefault("enchantment_declines", 0)
        session.setdefault("compass_offers", 0)
        session.setdefault("compass_declines", 0)
        session.setdefault("last_offer_type", None)
        session.setdefault("last_offer_at", None)

    mechanics["compass"].setdefault("offered_on", None)
    mechanics["compass"].setdefault("accepted_on", None)
    mechanics["compass"].setdefault("completed_on", None)
    mechanics["enchantment"].setdefault("offered_on", None)
    mechanics["enchantment"].setdefault("accepted_on", None)
    mechanics["enchantment"].setdefault("completed_on", None)
    mechanics["enchantment"].setdefault("active", None)
    mechanics["enchantment"].setdefault("last", None)
    data["mechanics"] = mechanics
    return data


def _save_runtime_state(workspace: Path, player_name: str, data: dict) -> None:
    path = _session_file(workspace, player_name)
    existing = _read_json(path)
    if isinstance(existing, dict):
        existing.update({k: v for k, v in data.items() if k != "mechanics"})
        existing["mechanics"] = data.get("mechanics", {})
        data = existing
    _write_json(path, data)


def record_event(workspace: Path, player_name: str, event: str) -> dict:
    data = _load_runtime_state(workspace, player_name)
    mechanics = data.setdefault("mechanics", {})
    session = mechanics.setdefault("session", {})
    today = date.today().isoformat()
    now = datetime.now().isoformat(timespec="seconds")

    if event == "offer-enchantment":
        session["enchantment_offers"] = session.get("enchantment_offers", 0) + 1
        session["last_offer_type"] = "enchantment"
        session["last_offer_at"] = now
        mechanics.setdefault("enchantment", {})["offered_on"] = today
    elif event == "decline-enchantment":
        session["enchantment_declines"] = session.get("enchantment_declines", 0) + 1
        session["last_offer_type"] = "enchantment"
        session["last_offer_at"] = now
    elif event == "accept-enchantment":
        mechanics.setdefault("enchantment", {})["accepted_on"] = today
    elif event == "complete-enchantment":
        mechanics.setdefault("enchantment", {})["completed_on"] = today
    elif event == "offer-compass":
        session["compass_offers"] = session.get("compass_offers", 0) + 1
        session["last_offer_type"] = "compass"
        session["last_offer_at"] = now
        mechanics.setdefault("compass", {})["offered_on"] = today
    elif event == "decline-compass":
        session["compass_declines"] = session.get("compass_declines", 0) + 1
        session["last_offer_type"] = "compass"
        session["last_offer_at"] = now
    elif event == "accept-compass":
        mechanics.setdefault("compass", {})["accepted_on"] = today
    elif event == "complete-compass":
        mechanics.setdefault("compass", {})["completed_on"] = today
    elif event == "roll-guidance":
        mechanics["last_roll_guidance_at"] = now
    elif event == "mechanics-preflight":
        mechanics["last_preflight_at"] = now
    else:
        raise ValueError(f"Unknown mechanics event: {event}")

    _save_runtime_state(workspace, player_name, data)
    return get_mechanics_state(workspace, player_name)


def get_preflight_status(workspace: Path, player_name: str, max_age_minutes: int = PREFLIGHT_MAX_AGE_MINUTES) -> dict:
    state = get_mechanics_state(workspace, player_name)
    last = state.get("last_preflight_at")
    if not last:
        return {
            "ok": False,
            "reason": "missing",
            "message": f"No recorded mechanics preflight for {player_name}.",
            "last_preflight_at": None,
            "max_age_minutes": max_age_minutes,
        }
    try:
        ts = datetime.fromisoformat(last)
    except ValueError:
        return {
            "ok": False,
            "reason": "invalid",
            "message": f"Mechanics preflight timestamp is invalid: {last}",
            "last_preflight_at": last,
            "max_age_minutes": max_age_minutes,
        }

    age = datetime.now() - ts
    if age > timedelta(minutes=max_age_minutes):
        return {
            "ok": False,
            "reason": "stale",
            "message": f"Mechanics preflight is stale, last run at {last}.",
            "last_preflight_at": last,
            "age_minutes": round(age.total_seconds() / 60, 1),
            "max_age_minutes": max_age_minutes,
        }

    return {
        "ok": True,
        "reason": None,
        "message": f"Mechanics preflight satisfied, last run at {last}.",
        "last_preflight_at": last,
        "age_minutes": round(age.total_seconds() / 60, 1),
        "max_age_minutes": max_age_minutes,
    }


def get_mechanics_state(workspace: Path, player_name: str) -> dict:
    belief = _player_belief(workspace, player_name)
    souvenir_last_run = _last_compass_run(workspace, player_name)
    today = date.today().isoformat()

    runtime_data = _load_runtime_state(workspace, player_name)
    mechanics = runtime_data.get("mechanics", {})
    compass_state = mechanics.get("compass", {})
    enchantment_state = mechanics.get("enchantment", {})
    session = mechanics.get("session", {})

    last_run = max([d for d in [souvenir_last_run, compass_state.get("completed_on")] if d] or [None])
    compass_locked_today = last_run == today

    if belief is None:
        belief_band = "unknown"
    elif belief <= 25:
        belief_band = "critical"
    elif belief <= 40:
        belief_band = "strained"
    else:
        belief_band = "healthy"

    should_offer_enchantment = belief is not None and belief <= 40
    should_offer_compass = belief is not None and belief <= 25 and not compass_locked_today

    consecutive_declines = 0
    last_offer_type = session.get("last_offer_type")
    if last_offer_type == "compass":
        consecutive_declines = session.get("compass_declines", 0)
    elif last_offer_type == "enchantment":
        consecutive_declines = session.get("enchantment_declines", 0)

    return {
        "belief": belief,
        "belief_band": belief_band,
        "last_compass_run": last_run,
        "compass_locked_today": compass_locked_today,
        "should_offer_enchantment": should_offer_enchantment,
        "should_offer_compass": should_offer_compass,
        "should_roll": True,
        "last_roll_guidance_at": mechanics.get("last_roll_guidance_at"),
        "last_preflight_at": mechanics.get("last_preflight_at"),
        "consecutive_declines": consecutive_declines,
        "session": session,
        "compass": compass_state,
        "enchantment": enchantment_state,
        "active_enchantment": enchantment_state.get("active"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read or update Enchantify mechanics state")
    parser.add_argument("player", nargs="?", default="bj")
    parser.add_argument("--workspace", default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument("--event", default=None,
                        choices=[
                            "offer-enchantment", "decline-enchantment", "accept-enchantment", "complete-enchantment",
                            "offer-compass", "decline-compass", "accept-compass", "complete-compass",
                            "roll-guidance", "mechanics-preflight",
                        ])
    args = parser.parse_args()

    workspace = Path(args.workspace)
    state = record_event(workspace, args.player, args.event) if args.event else get_mechanics_state(workspace, args.player)
    state["preflight_status"] = get_preflight_status(workspace, args.player)
    print(json.dumps(state, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

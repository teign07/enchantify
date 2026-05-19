#!/usr/bin/env python3
"""
compass-run.py — deterministic Wonder Compass run state machine.

The LLM supplies atmosphere. This script owns the ritual state:
North -> East -> South -> West -> Center, plus souvenir, print, Belief, and
history updates on completion.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

try:
    from food_log import summarize as summarize_fuel
except Exception:
    summarize_fuel = None


BASE = Path(__file__).resolve().parent.parent
PLAYERS = BASE / "players"
HEARTBEAT = BASE / "HEARTBEAT.md"
ACTIVATION_COST = 3
COMPLETION_REWARD = 9


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def state_path(player: str) -> Path:
    return PLAYERS / f"{safe_player(player)}-compass-run.json"


def player_path(player: str) -> Path:
    return PLAYERS / f"{safe_player(player)}.md"


def safe_player(player: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "", player or "bj") or "bj"


def load_state(player: str) -> dict[str, Any]:
    path = state_path(player)
    if not path.exists():
        return {"status": "idle"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"status": "idle", "invalid_previous_state": True}
    return data if isinstance(data, dict) else {"status": "idle"}


def save_state(player: str, data: dict[str, Any]) -> None:
    write(state_path(player), json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def clear_state(player: str) -> None:
    state_path(player).unlink(missing_ok=True)


def compact(text: str, limit: int = 260) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    return text if len(text) <= limit else text[: max(0, limit - 1)].rstrip() + "…"


def player_text(player: str) -> str:
    path = player_path(player)
    if not path.exists():
        raise SystemExit(f"Player file not found: {path}")
    return read(path)


def current_belief(player: str) -> int:
    m = re.search(r"^- \*\*Belief:\*\*\s*(\d+)", player_text(player), re.MULTILINE)
    return int(m.group(1)) if m else 0


def has_wonder_compass(player: str) -> bool:
    return "The Wonder Compass" in player_text(player)


def last_run_date(player: str) -> str:
    text = player_text(player)
    m = re.search(r"## Compass Run History\b(.*?)(?=\n##|\Z)", text, re.DOTALL)
    if m:
        last = re.search(r"- \*\*Last run:\*\*\s*(.+)", m.group(1))
        if last:
            value = last.group(1).strip()
            return "" if value.lower() in {"never", "—", "-"} else value[:10]
    souvenirs = BASE / "souvenirs"
    dates = []
    for path in souvenirs.glob(f"*-{safe_player(player)}*.md"):
        mm = re.match(r"(\d{4}-\d{2}-\d{2})-", path.name)
        if mm:
            dates.append(mm.group(1))
    return max(dates) if dates else ""


def heartbeat_context() -> dict[str, str]:
    text = read(HEARTBEAT)
    def grab(pattern: str, default: str = "") -> str:
        m = re.search(pattern, text, re.MULTILINE)
        return compact(m.group(1), 180) if m else default
    fuel = grab(r"- \*\*Fuel:\*\*\s*(.+)", "")
    if summarize_fuel:
        try:
            fuel = summarize_fuel(1) or fuel
        except Exception:
            pass
    return {
        "pulse": grab(r"^## Pulse\s*[—-]\s*(.+)", datetime.now().strftime("%I:%M %p")),
        "feel": grab(r"- \*\*Belfast Feel:\*\*\s*(.+)", "local atmosphere unavailable"),
        "raw_weather": grab(r"\*Raw:\s*([^\n*]+)", ""),
        "forecast": grab(r"- \*\*Forecast:\*\*\s*(.+)", ""),
        "season": grab(r"- \*\*Season:\*\*\s*(.+)", ""),
        "moon": grab(r"- \*\*Moon:\*\*\s*(.+)", ""),
        "tides": grab(r"- \*\*Tides:\*\*\s*(.+)", ""),
        "presence": grab(r"- \*\*Presence:\*\*\s*([^|]+)", ""),
        "focus": grab(r"\|\s*\*\*Focus:\*\*\s*([^\n]+)", ""),
        "pacing": grab(r"- \*\*Pacing:\*\*\s*(.+)", ""),
        "task": grab(r"- \*\*Current Task:\*\*\s*(.+)", ""),
        "location": grab(r"- \*\*Location:\*\*\s*(.+)", ""),
        "steps": grab(r"- \*\*Watch:\*\*\s*Steps:\s*([\d,]+)", ""),
        "fuel": fuel,
        "today": compact("\n".join(text.split("### 📅 Today", 1)[1].splitlines()[:12]), 900) if "### 📅 Today" in text else "",
    }


def _step_count(hb: dict[str, str]) -> int:
    raw = re.sub(r"[^\d]", "", hb.get("steps", ""))
    return int(raw) if raw else 0


def _hour(hb: dict[str, str]) -> int:
    pulse = hb.get("pulse") or ""
    m = re.search(r"(\d{1,2}):(\d{2})\s*(AM|PM)", pulse, re.I)
    if not m:
        return datetime.now().hour
    h = int(m.group(1))
    if m.group(3).upper() == "PM" and h != 12:
        h += 12
    if m.group(3).upper() == "AM" and h == 12:
        h = 0
    return h


def _weather_flags(hb: dict[str, str]) -> set[str]:
    text = " ".join(str(hb.get(k, "")) for k in ("feel", "raw_weather", "forecast")).lower()
    flags: set[str] = set()
    if any(w in text for w in ("rain", "drizzle", "showers", "storm", "thunder", "fog", "mist", "snow")):
        flags.add("inside-favored")
    if any(w in text for w in ("clear", "sunny", "fair", "window-open", "mild", "warm")):
        flags.add("outside-friendly")
    if any(w in text for w in ("wind", "gust")):
        flags.add("wind")
    if any(w in text for w in ("hot", "86°", "90°")):
        flags.add("heat")
    if any(w in text for w in ("cold", "freez", "30°", "20°")):
        flags.add("cold")
    return flags


def _fuel_flags(hb: dict[str, str]) -> set[str]:
    text = (hb.get("fuel") or "").lower()
    flags: set[str] = set()
    if not text or "nothing logged" in text or "no fuel" in text:
        flags.add("unknown")
    if "low protein" in text:
        flags.add("low-protein")
    m = re.search(r"(\d+)\s*cal", text)
    if m and int(m.group(1)) < 700:
        flags.add("underfueled")
    if any(w in text for w in ("coffee", "caffeine")):
        flags.add("caffeinated")
    if any(w in text for w in ("beer", "alcohol", "bud light", "modelo")):
        flags.add("alcohol")
    return flags


def calibration(player: str, mood: str, requested: str = "") -> dict[str, Any]:
    hb = heartbeat_context()
    hour = _hour(hb)
    steps = _step_count(hb)
    weather = _weather_flags(hb)
    fuel = _fuel_flags(hb)
    today = hb.get("today", "").lower()
    location = (hb.get("location") or "").lower()
    focus = (hb.get("focus") or "").lower()
    is_workday = any(w in today for w in ("athenahealth", "work", "ibml", "scanner")) and "off work" not in today
    pressure: list[str] = []
    if mood in {"low", "tired"}:
        pressure.append("low-energy mood")
    if "underfueled" in fuel or "low-protein" in fuel:
        pressure.append("fuel needs care")
    elif "unknown" in fuel:
        pressure.append("fuel unlogged")
    if steps < 1500:
        pressure.append("low movement so far")
    if "deep focus" in focus or is_workday:
        pressure.append("work/focus constraints")
    if "inside-favored" in weather:
        pressure.append("weather favors indoor threshold")
    scale = infer_scale(
        mood,
        requested,
        hb=hb,
        hour=hour,
        steps=steps,
        weather=weather,
        fuel=fuel,
        is_workday=is_workday,
    )
    return {
        "heartbeat": hb,
        "hour": hour,
        "steps": steps,
        "weather_flags": sorted(weather),
        "fuel_flags": sorted(fuel),
        "is_workday": is_workday,
        "at_home": "home" in location or "belfast" in location,
        "pressure": pressure,
        "scale": scale,
    }


def infer_scale(
    mood: str,
    requested: str = "",
    *,
    hb: dict[str, str] | None = None,
    hour: int | None = None,
    steps: int | None = None,
    weather: set[str] | None = None,
    fuel: set[str] | None = None,
    is_workday: bool = False,
) -> str:
    requested = requested.lower().strip()
    if requested in {"micro", "indoor", "local", "daytrip", "rest"}:
        return requested
    hb = hb or {}
    hour = datetime.now().hour if hour is None else hour
    steps = 0 if steps is None else steps
    weather = weather or _weather_flags(hb)
    fuel = fuel or _fuel_flags(hb)
    if mood == "low":
        return "rest"
    if mood == "tired":
        if "inside-favored" in weather or "underfueled" in fuel or "low-protein" in fuel or "unknown" in fuel:
            return "indoor"
        return "micro"
    if is_workday or hour < 8 or hour >= 20:
        return "micro"
    if mood == "restless":
        return "local"
    if steps < 1500 and "outside-friendly" in weather:
        return "local"
    return "micro"


def seed_recipe(scale: str, mood: str, hb: dict[str, str], ctx: dict[str, Any] | None = None) -> dict[str, str]:
    ctx = ctx or {}
    feel = (hb.get("feel") or "").lower()
    fuel_flags = set(ctx.get("fuel_flags", []))
    weather_flags = set(ctx.get("weather_flags", []))
    steps = int(ctx.get("steps") or 0)
    hour = int(ctx.get("hour") or datetime.now().hour)
    location = hb.get("location") or "the nearest real threshold"
    fuel_needs_care = bool({"underfueled", "low-protein"} & fuel_flags)
    fuel_unknown_and_low = "unknown" in fuel_flags and mood in {"low", "tired"}
    rainy = "inside-favored" in weather_flags or any(word in feel for word in ("rain", "drizzle", "mist", "fog", "wet"))
    if scale == "rest":
        return {
            "spark": "I wonder what rest is trying to protect before I turn it into another task?",
            "destination": "A real resting place: chair, bed, porch, parked car, or window.",
            "delight": "Water, tea, a blanket, or one gentle light. If you have not eaten, bring one small nourishing bite.",
            "definition": "Five deliberate minutes. Nothing has to be improved.",
            "mission": "Notice one body sensation and one outside sound without fixing either of them.",
            "why": "Mood, fuel, or weather suggests Center first; the Compass begins from rest, not pressure.",
        }
    if fuel_needs_care or fuel_unknown_and_low:
        return {
            "spark": "I wonder what tiny act of care would make the next hour easier to inhabit?",
            "destination": "Kitchen, water bottle, fridge, pantry, or the nearest place you can choose one small fuel anchor.",
            "delight": "Something easy and kind: water, coffee with actual food, protein if available, or a favorite cup.",
            "definition": "One snack or drink decision, then stop. This is an adventure of care, not optimization.",
            "mission": "Find one color, smell, texture, or temperature in the food/drink before you consume it.",
            "why": "Fuel data is missing or thin; the Compass can make care tangible without moralizing.",
        }
    if scale == "indoor" or (scale == "micro" and rainy):
        return {
            "spark": "I wonder what ordinary object within arm's reach has been waiting to be properly noticed?",
            "destination": f"One small indoor threshold near {location}: desk, kitchen counter, window, or doorway.",
            "delight": "A warm drink, one favorite song, or the softest available light.",
            "definition": "Two minutes, one object, one detail. Stop before it becomes homework.",
            "mission": "Pick up one overlooked object, turn it slowly, and find the detail you have never named.",
            "why": "Weather, time, or energy favors a tiny indoor prediction-error.",
        }
    if scale == "local":
        noun = "morning" if hour < 11 else "day" if hour < 17 else "evening"
        spark = f"I wonder what the {noun} looks like if I add one gentle loop to it?" if steps < 2000 else "I wonder what has changed on the nearest familiar street while I was busy surviving?"
        return {
            "spark": spark,
            "destination": "A short loop outside: mailbox, corner, car, shopfront, or one safe block.",
            "delight": "Coffee, a playlist, or permission to turn back the moment the loop is complete.",
            "definition": "One loop or ten minutes, whichever ends first.",
            "mission": "Find one odd sign, color, sound, smell, or texture that would not appear on a map.",
            "why": "Conditions can support a small outside loop without making it a production.",
        }
    if scale == "daytrip":
        return {
            "spark": "I wonder what nearby place could give today a story-shape without demanding heroics?",
            "destination": "One reachable place with a clear endpoint: thrift shelf, diner counter, waterfront, library, or bookstore.",
            "delight": "A small treat, a good playlist, and a hard return time.",
            "definition": "One destination, one playful find, then home.",
            "mission": "Find the strangest object or detail in the place, photograph or name it, and do not explain it away.",
            "why": "Schedule and energy leave room for a larger lowercase-a adventure.",
        }
    return {
        "spark": "I wonder what small thing has been trying to become visible today?",
        "destination": "A nearby threshold: window, porch, mailbox, desk, parked car, or one familiar shelf.",
        "delight": "A drink, a song, a soft light, or permission to stop early.",
        "definition": "Three minutes and one discovered detail.",
        "mission": "Find the smallest thing that changed since yesterday and name it without explaining it.",
        "why": "A micro-run fits the present constraints while still breaking the prediction machine.",
    }


def directive(title: str, lines: list[tuple[str, str]] | list[str]) -> str:
    out = [f"COMPASS_DIRECTIVE: {title}"]
    for item in lines:
        if isinstance(item, tuple):
            out.append(f"{item[0]}: {item[1]}")
        else:
            out.append(str(item))
    return "\n".join(out)


def run_cmd(args: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=BASE, capture_output=True, text=True, timeout=timeout)


def update_player_belief(player: str, delta: int) -> None:
    result = run_cmd([sys.executable, "scripts/update-player.py", player, "belief", f"{delta:+d}"])
    if result.returncode != 0:
        raise SystemExit(result.stderr or result.stdout or "belief update failed")


def record_mechanics(player: str, event: str) -> None:
    result = run_cmd([sys.executable, "mechanics/mechanics_state.py", player, "--event", event])
    if result.returncode != 0:
        print(f"WARN: mechanics event failed: {event}: {(result.stderr or result.stdout).strip()[:240]}")


def update_player_history(player: str, state: dict[str, Any], souvenir_file: str = "") -> None:
    path = player_path(player)
    text = read(path)
    today = date.today().isoformat()
    history_match = re.search(r"## Compass Run History\n(.*?)(?=\n##|\Z)", text, re.DOTALL)
    run_number = 1
    if history_match:
        totals = re.search(r"- \*\*Total runs:\*\*\s*(\d+)", history_match.group(1))
        run_number = int(totals.group(1)) + 1 if totals else 1
        block = history_match.group(1)
        block = re.sub(r"- \*\*Last run:\*\*.*", f"- **Last run:** {today}", block)
        block = re.sub(r"- \*\*Total runs:\*\*\s*\d+", f"- **Total runs:** {run_number}", block)
        souvenirs = re.search(r"- \*\*Souvenirs:\*\*\s*(\d+)", block)
        if souvenirs:
            block = re.sub(r"- \*\*Souvenirs:\*\*\s*\d+", f"- **Souvenirs:** {int(souvenirs.group(1)) + 1}", block)
        else:
            block = block.rstrip() + "\n- **Souvenirs:** 1\n"
        run_block = format_run_history(run_number, state, souvenir_file)
        replacement = "## Compass Run History\n" + block.rstrip() + "\n\n" + run_block + "\n"
        text = text[:history_match.start()] + replacement + text[history_match.end():]
    else:
        replacement = (
            "## Compass Run History\n\n"
            f"- **Last run:** {today}\n- **Total runs:** 1\n- **Souvenirs:** 1\n\n"
            + format_run_history(1, state, souvenir_file)
            + "\n\n"
        )
        insert = re.search(r"\n## The Inside Cover\b", text)
        if insert:
            text = text[:insert.start()] + "\n" + replacement + text[insert.start():]
        else:
            text = text.rstrip() + "\n\n" + replacement
    write(path, text)


def format_run_history(run_number: int, state: dict[str, Any], souvenir_file: str = "") -> str:
    today = date.today().isoformat()
    net = COMPLETION_REWARD - (ACTIVATION_COST if state.get("activation_charged") else 0)
    lines = [
        f"### Run {run_number} — {today}",
        f"- **Scale:** {state.get('scale', 'micro')}",
        f"- **Mood:** {state.get('mood', 'unspecified')}",
        f"- **Calibration:** {calibration_summary(state)}",
        f"- **North:** {state.get('north_spark', '')}",
        f"- **East:** Destination: {state.get('east_destination', '')}; Delight: {state.get('east_delight', '')}; Definition: {state.get('east_definition', '')}",
        f"- **South:** {state.get('south_mission', '')}",
        f"- **Souvenir:** *\"{state.get('west_souvenir', '')}\"*",
        f"- **Belief change:** -{ACTIVATION_COST} activation +{COMPLETION_REWARD} completion = **+{net} net**",
    ]
    if souvenir_file:
        lines.append(f"- **Souvenir file:** `{souvenir_file}`")
    return "\n".join(lines)


def calibration_summary(state: dict[str, Any]) -> str:
    cal = state.get("calibration") or {}
    if not isinstance(cal, dict):
        return "no calibration recorded"
    bits = []
    if cal.get("hour") is not None:
        bits.append(f"hour {cal.get('hour')}")
    if cal.get("steps") is not None:
        bits.append(f"steps {cal.get('steps')}")
    if cal.get("weather_flags"):
        bits.append("weather " + ",".join(cal.get("weather_flags") or []))
    if cal.get("fuel_flags"):
        bits.append("fuel " + ",".join(cal.get("fuel_flags") or []))
    if cal.get("is_workday"):
        bits.append("workday")
    if cal.get("at_home"):
        bits.append("at home")
    if cal.get("pressure"):
        bits.append("pressure: " + "; ".join(cal.get("pressure") or []))
    return compact(" | ".join(bits), 500) if bits else "quiet day"


def update_compass_item_belief(player: str) -> None:
    path = player_path(player)
    text = read(path)
    pattern = re.compile(r"(\*\*The Wonder Compass:\*\*.*?Belief:\s*)(\d+)", re.DOTALL)
    m = pattern.search(text)
    if m:
        current = int(m.group(2))
        text = text[:m.start(2)] + str(min(100, current + 1)) + text[m.end(2):]
        write(path, text)

    register = BASE / "lore" / "world-register.md"
    reg = read(register)
    row = re.compile(r"^(\|\s*The Wonder Compass\s*\|\s*Object\s*\|\s*)(\d+)(\s*\|.*)$", re.MULTILINE)
    mm = row.search(reg)
    if mm:
        current = int(mm.group(2))
        reg = reg[:mm.start(2)] + str(min(100, current + 1)) + reg[mm.end(2):]
        write(register, reg)


def cmd_start(args: argparse.Namespace) -> int:
    player = safe_player(args.player)
    if not has_wonder_compass(player):
        raise SystemExit("COMPASS_BLOCKED: player does not have The Wonder Compass.")
    state = load_state(player)
    if state.get("status") not in {"idle", "complete", "cancelled", "abandoned"} and not args.force:
        print(render_status(player, state))
        print("COMPASS_BLOCKED: active run already exists. Use status, answer, complete-west, or cancel.")
        return 1
    today = date.today().isoformat()
    last = last_run_date(player)
    if last == today and not args.force:
        print(directive("RESTING", [
            ("STATUS", "blocked"),
            ("REASON", "The Wonder Compass has already completed a run today."),
            ("MODEL_TASK", "Decline warmly in character. Offer Rest at the center, not another run."),
        ]))
        return 1

    ctx = calibration(player, args.mood, args.scale)
    hb = ctx["heartbeat"]
    scale = ctx["scale"]
    recipe = seed_recipe(scale, args.mood, hb, ctx)
    state = {
        "status": "north",
        "player": player,
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "date": today,
        "mood": args.mood or "unspecified",
        "scale": scale,
        "heartbeat": hb,
        "calibration": {k: v for k, v in ctx.items() if k != "heartbeat"},
        "recipe_reason": recipe.get("why", ""),
        "north_spark": args.spark or recipe["spark"],
        "east_destination": args.destination or recipe["destination"],
        "east_delight": args.delight or recipe["delight"],
        "east_definition": args.definition or recipe["definition"],
        "south_mission": args.mission or recipe["mission"],
        "activation_charged": False,
        "belief_awarded": False,
        "printed": False,
    }
    if not args.no_charge:
        update_player_belief(player, -ACTIVATION_COST)
        state["activation_charged"] = True
    record_mechanics(player, "accept-compass")
    save_state(player, state)
    print(directive("NORTH_NOTICE", [
        ("STATUS", "active"),
        ("STEP", "North / Notice"),
        ("MOOD", state["mood"]),
        ("SCALE", state["scale"]),
        ("CALIBRATION", calibration_summary(state)),
        ("REAL_CONTEXT", f"{hb.get('pulse')}; {hb.get('feel')}; {hb.get('season')}; {hb.get('location')}; steps {hb.get('steps') or 'unknown'}; fuel: {compact(hb.get('fuel', ''), 140)}"),
        ("WHY_THIS_RUN", state.get("recipe_reason", "")),
        ("SPARK", state["north_spark"]),
        ("PLAYER_TASK", "Answer the Spark, alter it, or say yes to carry it into East."),
        ("MODEL_TASK", "Present the Spark as an invitation. Do not advance to East until the player accepts or revises it."),
    ]))
    return 0


def cmd_answer(args: argparse.Namespace) -> int:
    player = safe_player(args.player)
    state = load_state(player)
    status = state.get("status", "idle")
    text = (args.text or "").strip()
    if status == "north":
        if text:
            state["north_response"] = text
        state["status"] = "east"
        save_state(player, state)
        print(directive("EAST_EMBARK", [
            ("STEP", "East / Embark"),
            ("DESTINATION", state["east_destination"]),
            ("DELIGHT", state["east_delight"]),
            ("DEFINITION", state["east_definition"]),
            ("PLAYER_TASK", "Cross the threshold and begin the real-world adventure. Return when the Definition is complete."),
            ("MODEL_TASK", "Give the 3 D's clearly. Do not summarize the adventure as completed."),
        ]))
    elif status == "east":
        if text:
            state["east_report"] = text
        state["status"] = "south"
        save_state(player, state)
        print(directive("SOUTH_SENSE", [
            ("STEP", "South / Sense"),
            ("MISSION", state["south_mission"]),
            ("PLAYER_TASK", "Do this one sensory mission. Return with what you found, touched, heard, smelled, tasted, or noticed."),
            ("MODEL_TASK", "Offer exactly one playful mission. No options. No completion until the player reports back."),
        ]))
    elif status == "south":
        if text:
            state["south_response"] = text
        state["status"] = "west"
        save_state(player, state)
        print(directive("WEST_WRITE", [
            ("STEP", "West / Write"),
            ("PLAYER_TASK", "Write one sentence only: one specific sensory detail or feeling from the adventure."),
            ("MODEL_TASK", "Ask reverently for the One-Sentence Souvenir. If the answer is vague, ask for one concrete detail."),
        ]))
    else:
        print(render_status(player, state))
        print("COMPASS_BLOCKED: answer only advances north, east, or south. Use complete-west for the souvenir.")
        return 1
    return 0


def latest_souvenir_file(player: str) -> str:
    souvenirs = sorted((BASE / "souvenirs").glob(f"*-{safe_player(player)}*.md"), key=lambda p: p.stat().st_mtime)
    return souvenirs[-1].name if souvenirs else ""


def cmd_complete_west(args: argparse.Namespace) -> int:
    player = safe_player(args.player)
    state = load_state(player)
    if state.get("status") != "west" and not args.force:
        print(render_status(player, state))
        print("COMPASS_BLOCKED: West is not ready. Advance through North, East, and South first.")
        return 1
    souvenir = (args.souvenir or "").strip()
    if len(souvenir.split()) < 3 and not args.force:
        print(directive("WEST_NEEDS_DETAIL", [
            ("STATUS", "needs-detail"),
            ("REASON", "The souvenir is too thin to preserve the adventure."),
            ("PLAYER_TASK", "Offer one full sentence with one concrete sensory detail or feeling."),
        ]))
        return 1
    state["west_souvenir"] = souvenir

    write_args = [
        sys.executable,
        "scripts/write-souvenir.py",
        player,
        souvenir,
        "--north",
        state.get("north_response") or state.get("north_spark", ""),
        "--east",
        state.get("east_report") or state.get("east_destination", ""),
        "--south",
        state.get("south_response") or state.get("south_mission", ""),
    ]
    mood = state.get("mood")
    if mood in {"ready", "tired", "low", "restless"}:
        write_args.extend(["--mood", mood])
    if args.no_print:
        write_args.append("--no-print")
    result = run_cmd(write_args, timeout=90)
    print(result.stdout.strip())
    if result.returncode != 0:
        raise SystemExit(result.stderr or result.stdout or "souvenir write failed")

    if not state.get("belief_awarded"):
        update_player_belief(player, COMPLETION_REWARD)
        state["belief_awarded"] = True
    state["printed"] = not args.no_print
    state["status"] = "complete"
    state["completed_at"] = datetime.now().isoformat(timespec="seconds")
    souvenir_file = latest_souvenir_file(player)
    update_player_history(player, state, souvenir_file=souvenir_file)
    update_compass_item_belief(player)
    record_mechanics(player, "complete-compass")
    save_state(player, state)
    print(directive("CENTER_REST", [
        ("STATUS", "complete"),
        ("SOUVENIR_FILE", souvenir_file or "unknown"),
        ("BELIEF", f"+{COMPLETION_REWARD} completion; net +{COMPLETION_REWARD - (ACTIVATION_COST if state.get('activation_charged') else 0)}"),
        ("PRINTED", "yes" if state["printed"] else "no"),
        ("MODEL_TASK", "Narrate the Center/Rest. Let the Nothing thin quietly. Do not rush back to plot."),
    ]))
    return 0


def render_status(player: str, state: dict[str, Any]) -> str:
    return directive("STATUS", [
        ("PLAYER", player),
        ("STATUS", state.get("status", "idle")),
        ("DATE", state.get("date", "")),
        ("MOOD", state.get("mood", "")),
        ("SCALE", state.get("scale", "")),
        ("CALIBRATION", calibration_summary(state)),
        ("WHY_THIS_RUN", state.get("recipe_reason", "")),
        ("NORTH", state.get("north_spark", "")),
        ("EAST_DESTINATION", state.get("east_destination", "")),
        ("EAST_DELIGHT", state.get("east_delight", "")),
        ("EAST_DEFINITION", state.get("east_definition", "")),
        ("SOUTH", state.get("south_mission", "")),
        ("WEST", state.get("west_souvenir", "")),
        ("LAST_RUN", last_run_date(player)),
    ])


def cmd_status(args: argparse.Namespace) -> int:
    player = safe_player(args.player)
    print(render_status(player, load_state(player)))
    return 0


def cmd_cancel(args: argparse.Namespace) -> int:
    player = safe_player(args.player)
    state = load_state(player)
    state["status"] = "cancelled"
    state["cancelled_at"] = datetime.now().isoformat(timespec="seconds")
    state["cancel_reason"] = args.reason or "cancelled by operator/player"
    save_state(player, state)
    print(directive("CANCELLED", [
        ("STATUS", "cancelled"),
        ("REASON", state["cancel_reason"]),
        ("MODEL_TASK", "Close softly. No guilt. A partial Compass Run can be resumed manually if needed."),
    ]))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministic Wonder Compass run state machine")
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start", help="Start a Compass Run and emit North directive")
    start.add_argument("player", nargs="?", default="bj")
    start.add_argument("--mood", choices=["ready", "tired", "low", "restless"], default="ready")
    start.add_argument("--scale", choices=["auto", "micro", "indoor", "local", "daytrip", "rest"], default="auto")
    start.add_argument("--spark", default="")
    start.add_argument("--destination", default="")
    start.add_argument("--delight", default="")
    start.add_argument("--definition", default="")
    start.add_argument("--mission", default="")
    start.add_argument("--force", action="store_true")
    start.add_argument("--no-charge", action="store_true")
    start.set_defaults(func=cmd_start)

    answer = sub.add_parser("answer", help="Advance North/East/South with the player's latest report")
    answer.add_argument("player", nargs="?", default="bj")
    answer.add_argument("text", nargs="?", default="")
    answer.set_defaults(func=cmd_answer)

    west = sub.add_parser("complete-west", help="Complete West with the One-Sentence Souvenir")
    west.add_argument("player", nargs="?", default="bj")
    west.add_argument("souvenir")
    west.add_argument("--force", action="store_true")
    west.add_argument("--no-print", action="store_true")
    west.set_defaults(func=cmd_complete_west)

    status = sub.add_parser("status", help="Print active Compass Run state")
    status.add_argument("player", nargs="?", default="bj")
    status.set_defaults(func=cmd_status)

    cancel = sub.add_parser("cancel", help="Cancel the active Compass Run")
    cancel.add_argument("player", nargs="?", default="bj")
    cancel.add_argument("--reason", default="")
    cancel.set_defaults(func=cmd_cancel)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

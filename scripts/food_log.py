#!/usr/bin/env python3
"""Durable food/fuel logging for Enchantify.

The legacy format is pipe-delimited and append-only:
date|time|description|calories|protein|carbs|fat|fiber|sugar|sodium|source|confidence

The first five fields are kept compatible with older readers.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from pathlib import Path

BASE = Path(__file__).parent.parent
SCRIPT_DIR = Path(__file__).parent
FUEL_LOG = SCRIPT_DIR / "fuel-log.txt"
SECRETS = BASE / "config" / "secrets.env"


@dataclass
class Nutrition:
    calories: int = 0
    protein: int = 0
    carbs: int = 0
    fat: int = 0
    fiber: int = 0
    sugar: int = 0
    sodium: int = 0
    source: str = "manual"
    confidence: str = "unknown"


def _load_env() -> dict[str, str]:
    cfg = dict(os.environ)
    if SECRETS.exists():
        for line in SECRETS.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            cfg.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return cfg


def _to_int(value: object) -> int:
    try:
        if value is None or value == "":
            return 0
        return max(0, int(round(float(value))))
    except (TypeError, ValueError):
        return 0


def _safe_desc(desc: str) -> str:
    return re.sub(r"\s+", " ", (desc or "unknown").replace("|", "/")).strip() or "unknown"


def _is_placeholder_desc(desc: str) -> bool:
    return (desc or "").strip().lower() in {"", "description", "unknown", "n/a", "none"}


def _nutrient_lookup(food: dict, names: tuple[str, ...]) -> int:
    for n in food.get("foodNutrients", []) or []:
        name = str(n.get("nutrientName") or n.get("name") or "").lower()
        if any(target in name for target in names):
            return _to_int(n.get("value"))
    return 0


def usda_lookup(description: str, cfg: dict[str, str]) -> Nutrition | None:
    key = (
        cfg.get("ENCHANTIFY_USDA_API_KEY")
        or cfg.get("USDA_API_KEY")
        or cfg.get("FDC_API_KEY")
        or ""
    ).strip()
    if not key:
        return None

    query = urllib.parse.urlencode({
        "query": description,
        "pageSize": "1",
        "api_key": key,
    })
    url = f"https://api.nal.usda.gov/fdc/v1/foods/search?{query}"
    req = urllib.request.Request(url, headers={"User-Agent": "Enchantify food logger"})
    try:
        with urllib.request.urlopen(req, timeout=8) as res:
            payload = json.loads(res.read().decode("utf-8", errors="replace"))
    except Exception:
        return None

    foods = payload.get("foods") or []
    if not foods:
        return None
    food = foods[0]
    cal = _nutrient_lookup(food, ("energy",))
    return Nutrition(
        calories=cal,
        protein=_nutrient_lookup(food, ("protein",)),
        carbs=_nutrient_lookup(food, ("carbohydrate",)),
        fat=_nutrient_lookup(food, ("total lipid", "total fat")),
        fiber=_nutrient_lookup(food, ("fiber",)),
        sugar=_nutrient_lookup(food, ("sugars",)),
        sodium=_nutrient_lookup(food, ("sodium",)),
        source="usda",
        confidence="api",
    )


def estimate_nutrition(description: str) -> Nutrition:
    """Small local fallback so logging never depends on network/API health."""
    text = description.lower()
    n = Nutrition(source="local-estimate", confidence="estimate")

    patterns: list[tuple[str, int, int, int, int, int, int, int]] = [
        (r"\bcoffee\b", 35, 0, 5, 1, 0, 4, 10),
        (r"\bcream and sugar\b", 70, 0, 9, 3, 0, 8, 15),
        (r"\b7\.?5\s*oz\s*coke\b|\bcoca-?cola\b", 90, 0, 25, 0, 0, 25, 25),
        (r"\bbud light\b", 220, 2, 13, 0, 0, 1, 20),
        (r"\bmodelo\b|\blager\b|\bbeer\b", 150, 1, 13, 0, 0, 1, 15),
        (r"\bbacon egg (?:and )?(?:american )?cheese english muffin\b", 450, 18, 35, 24, 2, 3, 900),
        (r"\benglish muffin\b", 150, 5, 28, 1, 2, 2, 250),
        (r"\bpepperoni\b.*\bpizza\b|\bpizza\b", 320, 13, 36, 14, 2, 4, 760),
        (r"\bfries\b", 365, 4, 48, 17, 4, 0, 300),
        (r"\bdonut\b", 260, 3, 31, 14, 1, 14, 300),
        (r"\bprotein drink\b|\bprotein shake\b", 160, 30, 8, 3, 1, 4, 180),
        (r"\boatmeal\b", 160, 6, 27, 3, 4, 1, 120),
        (r"\bsoup\b", 300, 18, 30, 10, 6, 5, 900),
        (r"\breuben\b", 750, 30, 55, 38, 4, 8, 1800),
        (r"\bnachos\b", 850, 30, 75, 45, 8, 5, 1500),
    ]

    matched = False
    for pattern, cal, protein, carbs, fat, fiber, sugar, sodium in patterns:
        count = len(re.findall(pattern, text))
        if not count:
            continue
        matched = True
        n.calories += cal * count
        n.protein += protein * count
        n.carbs += carbs * count
        n.fat += fat * count
        n.fiber += fiber * count
        n.sugar += sugar * count
        n.sodium += sodium * count

    # Simple quantity phrases.
    if re.search(r"\btwo\b|\b2\b", text) and "coffee" in text and n.calories < 120:
        n.calories += 70
    if re.search(r"\bthree\b|\b3\b", text) and "coffee" in text and n.calories < 180:
        n.calories += 105
    if re.search(r"\bfour\b|\b4\b", text) and "coffee" in text and n.calories < 240:
        n.calories += 140

    if not matched:
        n.confidence = "unknown"
    return n


def nutrition_for(description: str, args: argparse.Namespace) -> Nutrition:
    manual = Nutrition(
        calories=_to_int(args.calories),
        protein=_to_int(args.protein),
        carbs=_to_int(args.carbs),
        fat=_to_int(args.fat),
        fiber=_to_int(args.fiber),
        sugar=_to_int(args.sugar),
        sodium=_to_int(args.sodium),
        source="manual",
        confidence="manual",
    )
    if any((manual.calories, manual.protein, manual.carbs, manual.fat, manual.fiber, manual.sugar, manual.sodium)):
        return manual

    if not args.no_api:
        api = usda_lookup(description, _load_env())
        if api and (api.calories or api.protein):
            return api
    return estimate_nutrition(description)


def append_log(description: str, nutrition: Nutrition, when: datetime | None = None) -> None:
    when = when or datetime.now()
    if _is_placeholder_desc(description):
        raise ValueError("Refusing to log placeholder food description")
    FUEL_LOG.parent.mkdir(parents=True, exist_ok=True)
    row = [
        when.strftime("%Y-%m-%d"),
        when.strftime("%H:%M"),
        _safe_desc(description),
        str(nutrition.calories),
        str(nutrition.protein),
        str(nutrition.carbs),
        str(nutrition.fat),
        str(nutrition.fiber),
        str(nutrition.sugar),
        str(nutrition.sodium),
        nutrition.source,
        nutrition.confidence,
    ]
    with FUEL_LOG.open("a", encoding="utf-8") as f:
        f.write("|".join(row) + "\n")


def read_entries(days: int = 1) -> list[dict[str, object]]:
    if not FUEL_LOG.exists():
        return []
    cutoff = date.today() - timedelta(days=max(days - 1, 0))
    entries = []
    for line in FUEL_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.strip().split("|")
        if len(parts) < 5:
            continue
        try:
            entry_date = date.fromisoformat(parts[0])
        except ValueError:
            continue
        if _is_placeholder_desc(parts[2]) and all(_to_int(p) == 0 for p in parts[3:10]):
            continue
        if entry_date < cutoff:
            continue
        entries.append({
            "date": parts[0],
            "time": parts[1],
            "description": parts[2],
            "calories": _to_int(parts[3]),
            "protein": _to_int(parts[4]),
            "carbs": _to_int(parts[5] if len(parts) > 5 else 0),
            "fat": _to_int(parts[6] if len(parts) > 6 else 0),
            "fiber": _to_int(parts[7] if len(parts) > 7 else 0),
            "sugar": _to_int(parts[8] if len(parts) > 8 else 0),
            "sodium": _to_int(parts[9] if len(parts) > 9 else 0),
            "source": parts[10] if len(parts) > 10 else "legacy",
            "confidence": parts[11] if len(parts) > 11 else "legacy",
        })
    return entries


def summarize(days: int = 1) -> str:
    entries = read_entries(days)
    today = date.today().isoformat()
    todays = [e for e in entries if e["date"] == today]
    if not todays:
        return "Today: nothing logged yet. Status: ask the player what they ate or drank when it naturally comes up."

    totals = {
        key: sum(int(e.get(key, 0) or 0) for e in todays)
        for key in ("calories", "protein", "carbs", "fat", "fiber", "sugar", "sodium")
    }
    items = " / ".join(str(e["description"]) for e in todays)
    if totals["protein"] < 30:
        status = "low protein; suggest something substantial with care, not judgment"
    elif totals["calories"] < 700:
        status = "light fuel day; a proper meal would help"
    elif totals["fiber"] < 10:
        status = "adequate fuel, low fiber signal"
    else:
        status = "steady fuel"
    return (
        f"Today: {items} -- {totals['calories']} cal, {totals['protein']}g protein, "
        f"{totals['carbs']}g carbs, {totals['fat']}g fat, {totals['fiber']}g fiber, "
        f"{totals['sodium']}mg sodium. Status: {status}."
    )


def refresh_heartbeat() -> None:
    script = SCRIPT_DIR / "update-weather.sh"
    if script.exists():
        subprocess.Popen(["bash", str(script)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Log and summarize Enchantify food/fuel.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    log = sub.add_parser("log", help="Append a food/drink entry.")
    log.add_argument("description")
    log.add_argument("--calories", "--cal", default=0)
    log.add_argument("--protein", "--pro", default=0)
    log.add_argument("--carbs", default=0)
    log.add_argument("--fat", default=0)
    log.add_argument("--fiber", default=0)
    log.add_argument("--sugar", default=0)
    log.add_argument("--sodium", default=0)
    log.add_argument("--no-api", action="store_true", help="Skip optional USDA lookup.")
    log.add_argument("--no-refresh", action="store_true", help="Do not refresh heartbeat after logging.")

    summary = sub.add_parser("summary", help="Print today's fuel summary.")
    summary.add_argument("--days", type=int, default=1)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "summary":
        print(summarize(args.days))
        return 0
    if args.cmd == "log":
        nutrition = nutrition_for(args.description, args)
        append_log(args.description, nutrition)
        print(
            f"Logged: {_safe_desc(args.description)} "
            f"({nutrition.calories} cal, {nutrition.protein}g protein, "
            f"{nutrition.carbs}g carbs, {nutrition.fat}g fat, source={nutrition.source}, confidence={nutrition.confidence})"
        )
        if not args.no_refresh:
            refresh_heartbeat()
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

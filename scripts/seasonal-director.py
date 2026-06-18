#!/usr/bin/env python3
"""seasonal-director.py - derive active seasonal events for scene systems.

This script turns `lore/seasonal-calendar.md` intent into runtime guidance.
It reads HEARTBEAT and player context, then emits active seasonal events with
compact directives for atmosphere, NPC behavior, Nothing pressure, and
Enchantment/Compass flavor.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent


def read_safe(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def first_match(pattern: str, text: str, default: str = "") -> str:
    m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    return m.group(1).strip() if m else default


def compact(text: str, limit: int = 140) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def day_key(d: date) -> str:
    return f"{d.month:02d}-{d.day:02d}"


def make_event(
    name: str,
    layer: str,
    atmosphere: str,
    npc_shift: str,
    nothing_shift: str,
    enchantment_shift: str,
    compass_flavor: str,
) -> dict[str, str]:
    return {
        "name": name,
        "layer": layer,
        "atmosphere": atmosphere,
        "npc_shift": npc_shift,
        "nothing_shift": nothing_shift,
        "enchantment_shift": enchantment_shift,
        "compass_flavor": compass_flavor,
    }


def heartbeat_snapshot() -> dict[str, str]:
    text = read_safe(BASE / "HEARTBEAT.md")
    season = (
        first_match(r"\*\*Season:\*\*\s*([^\n]+)", text)
        or first_match(r"Season:\s*([^\n]+)", text)
    )
    moon = (
        first_match(r"\*\*Moon:\*\*\s*([^\n]+)", text)
        or first_match(r"Moon:\s*([^\n]+)", text)
    )
    weather = (
        first_match(r"\*\*Belfast Feel:\*\*\s*([^\n]+)", text)
        or first_match(r"Belfast Feel:\s*([^\n]+)", text)
    )
    raw_weather = first_match(r"\*\*Raw:\*\*\s*([^\n]+)", text)
    temp_text = first_match(r"(-?\d+(?:\.\d+)?)\s*°?\s*F", text)
    return {
        "season": season,
        "moon": moon,
        "weather": weather,
        "raw_weather": raw_weather,
        "temp_f": temp_text,
    }


def player_dates(player: str) -> dict[str, str]:
    text = read_safe(BASE / "players" / f"{player}.md")
    found: dict[str, str] = {}
    for m in re.finditer(r"(\d{4}-\d{2}-\d{2})\s*:\s*([^\n]+)", text):
        found[m.group(1)] = m.group(2).strip()
    return found


def detect_events(player: str, today: date) -> list[dict[str, str]]:
    hb = heartbeat_snapshot()
    season = (hb.get("season") or "").lower()
    moon = (hb.get("moon") or "").lower()
    weather = f"{hb.get('weather', '')} {hb.get('raw_weather', '')}".lower()
    temp_f = float(hb["temp_f"]) if hb.get("temp_f") else None

    events: list[dict[str, str]] = []
    key = day_key(today)

    # Astronomical windows.
    if key in {"06-20", "06-21", "06-22"}:
        events.append(
            make_event(
                "The Longest Day",
                "astronomical",
                "sun-drunk, expansive, bright with late-hour restlessness",
                "professors and students drift outdoors; everyone acts one beat later than usual",
                "Nothing retreats to shadows and offstage corners",
                "light or warmth motifs gain extra confidence",
                "ask the player what detail still glows after sunset",
            )
        )
    if key in {"12-20", "12-21", "12-22"}:
        events.append(
            make_event(
                "The Darkest Class",
                "astronomical",
                "candlelit, intimate, careful with long pauses",
                "people speak lower and stay physically closer",
                "Nothing is stronger but easier to see",
                "light-based enchantments should feel precious and deliberate",
                "offer one tiny noticing ritual in the darkest corner available",
            )
        )
    if key in {"03-19", "03-20", "03-21", "09-21", "09-22", "09-23"}:
        events.append(
            make_event(
                "The Rebalancing",
                "astronomical",
                "balanced, fresh, mildly disorienting",
                "unlikely pairs collaborate for one scene beat",
                "Nothing loses confidence in this balance",
                "any known enchantment can be framed as viable today",
                "invite the player to choose direction by feeling, not urgency",
            )
        )

    # Moon cycle.
    if "full" in moon:
        events.append(
            make_event(
                "The Luminous Gathering",
                "moon",
                "open-hearted and generous under bright night texture",
                "strangers become easier to talk to",
                "Nothing withdraws from exposed spaces",
                "souvenir proof moments should feel unusually resonant",
                "ask for one moonlit detail that should be remembered tomorrow",
            )
        )
    elif "new" in moon:
        events.append(
            make_event(
                "The Quiet Hours",
                "moon",
                "quiet, whisper-close, attentive to small sounds",
                "characters huddle, confide, and listen before acting",
                "Nothing is bolder but less subtle in silence",
                "sound/silence motifs become stronger than spectacle",
                "offer a brief stillness task before movement",
            )
        )

    # Local seasonal names.
    season_events = {
        "mud": make_event(
            "The Thaw",
            "local-season",
            "wet, heavy, alive with runoff and rearranged footing",
            "boots by doors, damp cuffs, practical humor",
            "Nothing dissolves a little in waterlogged places",
            "earth/water framing feels easier to justify",
            "ask what changed shape after getting wet",
        ),
        "bloom": make_event(
            "The Awakening",
            "local-season",
            "lush, overflowing, green-edged abundance",
            "professors get distracted by beauty and growth",
            "Nothing struggles to hold form in pollen-rich spaces",
            "growth and voice motifs come through vividly",
            "ask what ordinary thing looks newly alive",
        ),
        "gold": make_event(
            "The Burning",
            "local-season",
            "gold-lit, bittersweet, high-sensory beauty",
            "students linger in windows and hallways to watch light move",
            "Nothing hides in roots and lower corridors",
            "beauty-linked enchantment framing lands strongly",
            "ask what they do not want to lose before winter",
        ),
        "stick": make_event(
            "The Bare Branches",
            "local-season",
            "bare, honest, echoing, less ornament",
            "NPCs are more direct and less decorative",
            "Nothing blends in; detail accuracy matters more",
            "truth/reveal motifs become more salient",
            "ask what is visible now that leaves are gone",
        ),
        "deep winter": make_event(
            "The Long Quiet",
            "local-season",
            "quiet, crystalline, patient and close to heat sources",
            "people cluster around fireplaces and shared warmth",
            "Nothing leaves clearer traces in cold spaces",
            "warmth, shelter, and light feel ritual-significant",
            "ask which small warmth is keeping the page alive",
        ),
        "summer": make_event(
            "The Red Harvest",
            "local-season",
            "salty, amused, sun-warmed with playful edge",
            "Tidecrest energy and debate rise in common spaces",
            "Nothing slumps during peak heat hours",
            "water motifs read as naturally amplified",
            "ask what the season is insisting be enjoyed now",
        ),
    }
    for key_word, event in season_events.items():
        if key_word in season:
            events.append(event)
            break

    # Weather micro-events.
    if "fog" in weather:
        events.append(
            make_event(
                "Fog Drift",
                "weather",
                "soft edges, elongated corridors, uncertain distance",
                "unexpected encounters become plausible",
                "Nothing can hide easier, but acts slower",
                "outcomes can feel surprising and delayed",
                "follow one detail that appears then disappears",
            )
        )
    if any(x in weather for x in ("thunder", "lightning", "storm")):
        events.append(
            make_event(
                "Storm Pressure",
                "weather",
                "charged, crackling, physically alert",
                "people gather inside and speak over weather noise",
                "Nothing pulls back from the loudest strike zones",
                "high-energy effects feel volatile and immediate",
                "replace wide travel with a contained observation task",
            )
        )
    if "rain" in weather and temp_f is not None and temp_f > 45:
        events.append(
            make_event(
                "Rain Reading",
                "weather",
                "flowing and reflective with motion everywhere",
                "more messages, paper, and improvised shelter beats",
                "running water weakens static absence",
                "water/synesthetic motifs become vivid",
                "ask what the rain is saying in plain language",
            )
        )
    if "wind" in weather:
        events.append(
            make_event(
                "High Wind",
                "weather",
                "restless, quick, pages and voices moving faster",
                "NPCs interrupt and pivot more often",
                "Nothing has trouble maintaining one shape",
                "air, movement, and chance are easier to foreground",
                "ask what was carried in and what was blown away",
            )
        )

    # Personal dates.
    if player == "bj" and key == "12-24":
        events.append(
            make_event(
                "Northern Light Anniversary",
                "personal",
                "heavy, respectful quiet without theatricality",
                "care through presence, not speeches",
                "Nothing backs off from this kind of grief-presence",
                "no amplification; presence itself is the magic",
                "if offered, keep it tiny and optional",
            )
        )
    for iso, label in player_dates(player).items():
        if iso.endswith(f"-{key}"):
            events.append(
                make_event(
                    f"Personal Date: {compact(label, 48)}",
                    "personal",
                    "warm, specific, biographical texture",
                    "one character should acknowledge with tact",
                    "Nothing pressure should not be center stage",
                    "small memory-object framing is favored",
                    "invite one concrete remembrance",
                )
            )
            break

    # Keep output compact and deterministic.
    unique: dict[str, dict[str, str]] = {}
    for event in events:
        unique[event["name"]] = event
    result = list(unique.values())[:4]
    if result:
        return result
    if season:
        return [
            make_event(
                f"Ambient Season: {compact(hb.get('season', ''), 40)}",
                "ambient",
                "carry current season texture in room details and pacing",
                "npc behavior should reflect weather and day rhythm",
                "Nothing pressure follows standard cadence for the day",
                "no special seasonal amplification required",
                "keep Compass prompts grounded in what is physically present now",
            )
        ]
    return []


def build_packet(player: str = "bj", today: date | None = None) -> dict[str, Any]:
    current = today or date.today()
    hb = heartbeat_snapshot()
    events = detect_events(player, current)
    event_dicts = events
    atmosphere = " | ".join(event["atmosphere"] for event in events[:2])
    npc_shift = " | ".join(event["npc_shift"] for event in events[:2])
    nothing_shift = " | ".join(event["nothing_shift"] for event in events[:2])
    enchantment_shift = " | ".join(event["enchantment_shift"] for event in events[:2])
    compass_flavor = " | ".join(event["compass_flavor"] for event in events[:2])
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "player": player,
        "date": current.isoformat(),
        "heartbeat": hb,
        "active_events": event_dicts,
        "event_names": [event["name"] for event in event_dicts],
        "atmosphere_shift": compact(atmosphere, 220),
        "npc_shift": compact(npc_shift, 220),
        "nothing_shift": compact(nothing_shift, 220),
        "enchantment_shift": compact(enchantment_shift, 220),
        "compass_flavor": compact(compass_flavor, 220),
        "scene_hook": compact(
            " ; ".join(
                f"{event['name']}: {event['atmosphere']}" for event in event_dicts[:2]
            ),
            260,
        ),
    }


def render_text(packet: dict[str, Any]) -> str:
    lines = [
        "SEASONAL DIRECTIVE",
        f"DATE: {packet.get('date')}",
        f"PLAYER: {packet.get('player')}",
        f"HEARTBEAT_SEASON: {packet.get('heartbeat', {}).get('season', '') or 'unknown'}",
        f"HEARTBEAT_MOON: {packet.get('heartbeat', {}).get('moon', '') or 'unknown'}",
        f"HEARTBEAT_WEATHER: {packet.get('heartbeat', {}).get('weather', '') or 'unknown'}",
    ]
    if packet.get("active_events"):
        lines.append("ACTIVE_EVENTS:")
        for item in packet["active_events"]:
            lines.append(f"- {item['name']} [{item['layer']}]")
            lines.append(f"  atmosphere: {item['atmosphere']}")
            lines.append(f"  npc_shift: {item['npc_shift']}")
    else:
        lines.append("ACTIVE_EVENTS: none (ambient season only)")
    lines.append(f"ATMOSPHERE_SHIFT: {packet.get('atmosphere_shift') or 'none'}")
    lines.append(f"NPC_SHIFT: {packet.get('npc_shift') or 'none'}")
    lines.append(f"NOTHING_SHIFT: {packet.get('nothing_shift') or 'none'}")
    lines.append(f"ENCHANTMENT_SHIFT: {packet.get('enchantment_shift') or 'none'}")
    lines.append(f"COMPASS_FLAVOR: {packet.get('compass_flavor') or 'none'}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Derive active seasonal directives.")
    parser.add_argument("player", nargs="?", default="bj")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    packet = build_packet(args.player)
    if args.json:
        print(json.dumps(packet, ensure_ascii=False, indent=2))
    else:
        print(render_text(packet))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

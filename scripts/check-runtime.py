#!/usr/bin/env python3
"""Run Enchantify's small reliability checks without sending live messages.

This is a smoke test for the existing ritual path, not a gameplay entrypoint.
It avoids installer files in the repository root and keeps generated artifacts
under /tmp or tmp/scene-outbox.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent
SCRIPTS = BASE / "scripts"


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""


def run(
    cmd: list[str],
    *,
    name: str | None = None,
    env: dict[str, str] | None = None,
    timeout: int = 120,
) -> Check:
    label = name or " ".join(cmd[:3])
    try:
        proc = subprocess.run(
            cmd,
            cwd=BASE,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return Check(label, False, f"timed out after {timeout}s")

    detail = (proc.stdout or proc.stderr or "").strip()
    if proc.returncode != 0 and proc.stderr:
        detail = proc.stderr.strip()
    return Check(label, proc.returncode == 0, detail.splitlines()[0] if detail else "")


def check_required_files() -> Check:
    required = [
        "AGENTS.md",
        "SOUL.md",
        "config/voice-assignments.md",
        "scripts/mechanics-preflight.py",
        "scripts/fae-ledger.py",
        "scripts/enchantment.py",
        "scripts/food_log.py",
        "scripts/therapy-chart.py",
        "scripts/vellum-chart.py",
        "scripts/support-faculty.py",
        "scripts/housekeeping.py",
        "scripts/drawthings-keepalive.py",
        "scripts/check-health.py",
        "scripts/scene-contract.py",
        "scripts/page-contract.py",
        "scripts/scene-choices.py",
        "scripts/scene-preflight.py",
        "scripts/run-live-scene.py",
        "scripts/story-progress.py",
        "scripts/narrative-health.py",
        "scripts/narrative-steward.py",
        "scripts/thread-steward.py",
        "scripts/write-thread-row.py",
        "scripts/cron_steward.py",
        "scripts/class-lecture.py",
        "scripts/widget-state.py",
        "scripts/story-context.py",
        "scripts/play_scene.py",
        "scripts/scene_packet_builder.py",
        "scripts/scene_conductor.py",
        "hooks/on-install.sh",
        "hooks/install.sh",
        "hooks/bootstrap.sh",
        "mechanics/pages.md",
    ]
    missing = [item for item in required if not (BASE / item).exists()]
    if missing:
        return Check("required files", False, "missing: " + ", ".join(missing))
    return Check("required files", True, f"{len(required)} present")


def check_root_stays_lean() -> Check:
    blocked = ["README.md", "install.sh", "bootstrap.sh", "requirements.txt", "package.json"]
    present = [item for item in blocked if (BASE / item).exists()]
    if present:
        return Check("lean root", False, "unexpected root files: " + ", ".join(present))
    return Check("lean root", True, "install/docs entrypoints remain under hooks/")


def check_agents_size() -> Check:
    path = BASE / "AGENTS.md"
    size = len(path.read_text(encoding="utf-8")) if path.exists() else 0
    limit = 13_500
    if size > limit:
        return Check("AGENTS size", False, f"{size} chars exceeds {limit}")
    installed = Path.home() / ".openclaw" / "agents" / "enchantify" / "agent.md"
    if installed.exists():
        installed_size = len(installed.read_text(encoding="utf-8"))
        if installed_size > limit:
            return Check("AGENTS size", False, f"installed agent.md {installed_size} chars exceeds {limit}")
        return Check("AGENTS size", True, f"workspace {size}, installed {installed_size} chars below loader cutoff")
    return Check("AGENTS size", True, f"workspace {size} chars below loader cutoff")


def check_compile() -> Check:
    env = os.environ.copy()
    env["PYTHONPYCACHEPREFIX"] = "/private/tmp/enchantify-pycache"
    result = run(
        [
            sys.executable,
            "-m",
            "compileall",
            "-q",
            "scripts",
            "mechanics",
            "skill-lore",
            "skills",
        ],
        name="python syntax",
        env=env,
    )
    if result.ok and not result.detail:
        result.detail = "scripts and skills compile"
    return result


def check_scene_choices() -> Check:
    scene = (
        "You stand where the last page left you.\n\n"
        "What do you do?\n"
        "1. [LIFE] Ask whether anyone wants tea before the next strange thing happens.\n"
        "2. [ARC] Open the marked drawer and read the note inside.\n"
        "3. [SURPRISE] Follow the draft under the door no one mentioned.\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".txt", prefix="enchantify-scene-", delete=False) as f:
        f.write(scene)
        path = Path(f.name)
    try:
        result = run([
            sys.executable,
            str(SCRIPTS / "scene-choices.py"),
            "--scene-file",
            str(path),
            "--strict-balance",
        ])
        if not result.ok:
            return Check("scene choices", False, result.detail)
        cleaned = path.read_text(encoding="utf-8")
        if any(tag in cleaned for tag in ("[LIFE]", "[ARC]", "[SURPRISE]")):
            return Check("scene choices", False, "choice tags were not stripped")
        return Check("scene choices", True, "validated and stripped")
    finally:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def substantial_scene(location: str = "the Academy threshold") -> str:
    return (
        f"You are still at {location}. The first thing the page does is keep faith with the room: "
        "the cup nearest your hand is cooling, the nearest chair keeps its angle, and the last thing said has not been swept away for the convenience of the next beat.\n\n"
        "Zara notices the pause before anyone names it. She does not fill it immediately. She turns her mug by a quarter inch, watches the tea answer with one small ring of steam, and lets the silence become social instead of empty.\n\n"
        "\"If the Book is going to ask us for courage,\" she says, \"it can at least let us know which kind.\" The line lands lightly, but not lazily. It gives the scene a hinge: ordinary enough to stay human, strange enough to belong here.\n\n"
        "The weather presses its gray forehead to the window. Somewhere beyond the door, another student laughs and then lowers their voice, as if laughter has rules in this part of the hall. The details become more accountable because the page is refusing to rush: the table grain, the sleeve cuff, the way everyone waits to see whether this becomes comfort or investigation.\n\n"
        "A folded note waits near the candle, but no one grabs it. Zara sees you see it and smiles with one side of her mouth, the expression she uses when she is not sure whether curiosity is kindness yet. She taps the table once. The note does not move. The candle leans as if listening.\n\n"
        "For a moment the Academy feels less like a machine for plot and more like a place where people have to decide what kind of attention they are offering each other. A passing student carries a tray of cups toward the far benches. The sound is practical, ceramic, human. It keeps the scene from turning into a bulletin board of clues.\n\n"
        "Zara finally says, \"We could be careful without being solemn.\" That is the invitation under the whole page. Careful could mean tea. Careful could mean evidence. Careful could mean following the one detail that has chosen to be odd in public.\n\n"
        "You have enough time to notice her properly: ink on the side of her thumb, the small tension at the corner of her jaw, the way she keeps looking at the note and then back to you as if asking whether the two of you are allowed to be ordinary first. This is the part short scenes usually skip, and it matters. Relationship is not a caption under an event. It is the event taking its time.\n\n"
        "The room gives you supporting evidence. The candle gutters once, recovers, and leaves a bead of wax shaped like a comma. The benches farther away are scuffed from years of knees and satchels. Someone has carved a tiny star into the table edge, then tried to sand it out and failed. The page keeps these things because they make the choice feel inhabited rather than assigned.\n\n"
        "If real risk enters, it will need a Belief roll before the page pretends to know the outcome. For now, the choice is smaller and therefore sharper: stay with care, turn toward the marked clue, or follow the one detail that does not belong. The scene has earned the handoff, and the handoff has enough life in it to be chosen. Even the pause before choosing feels playable, which is the whole point of this smoke scene today, here, now.\n\n"
        "What do you do?\n"
        "1. [LIFE] Ask whether anyone wants tea before the next strange thing happens, giving the room one ordinary kindness to gather around.\n"
        "2. [ARC] Try a Belief roll to investigate the marked drawer and read the clue inside, letting the current thread answer through evidence instead of panic.\n"
        "3. [SURPRISE] Follow the draft under the side door no one mentioned, because the page may be asking a better sideways question.\n"
    )


def check_housekeeping() -> Check:
    result = run(
        [sys.executable, str(SCRIPTS / "housekeeping.py"), "--dry-run", "--json"],
        name="housekeeping",
        timeout=120,
    )
    if not result.ok:
        return result
    return Check("housekeeping", True, "dry-run storage cleanup reports safely")


def check_drawthings_keepalive() -> Check:
    result = run(
        [sys.executable, str(SCRIPTS / "drawthings-keepalive.py"), "--dry-run", "--generate", "--json"],
        name="drawthings keepalive",
        timeout=60,
    )
    if not result.ok:
        return result
    return Check("drawthings keepalive", True, "dry-run app/API poke and image prompt works")


def check_scene_contract(player: str) -> Check:
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "scene-contract.py"), player, "--mode", "slice", "--json"],
        cwd=BASE,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()
        return Check("scene contract", False, detail[0] if detail else "scene contract failed")
    try:
        contract_data = json.loads(proc.stdout)
    except Exception as exc:
        return Check("scene contract", False, f"invalid JSON: {exc}")
    if not (contract_data.get("tool_packet_suggestion") or {}).get("sequence"):
        return Check("scene contract", False, "missing page-aware tool packet suggestion")
    location = contract_data.get("current_location") or "Academy room"
    scene = substantial_scene(location)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", prefix="enchantify-contract-", delete=False) as f:
        f.write(scene)
        path = Path(f.name)
    try:
        built = run(
            [sys.executable, str(SCRIPTS / "scene-contract.py"), player, "--mode", "slice"],
            name="scene contract",
        )
        if not built.ok:
            return built
        validated = run(
            [
                sys.executable,
                str(SCRIPTS / "scene-contract.py"),
                player,
                "--mode",
                "slice",
                "--validate-scene",
                str(path),
            ],
            name="scene contract validate",
        )
        if not validated.ok:
            return validated
        return Check("scene contract", True, "built and validated")
    finally:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def check_live_scene_repair_retry(player: str) -> Check:
    bad_scene = (
        "The Nothing screams through the dormitory window and Wicker's threat shatters the room before you can breathe.\n\n"
        + substantial_scene("the dormitory table").split("What do you do?")[0]
        +
        "What do you do?\n"
        "1. [LIFE] Investigate the Duskthorn clue in the marked drawer.\n"
        "2. [ARC] Sit quietly for tea and wait.\n"
        "3. [SURPRISE] Think about the situation."
    )
    with tempfile.NamedTemporaryFile("w", suffix=".txt", prefix="enchantify-repair-", delete=False) as f:
        f.write(bad_scene)
        path = Path(f.name)
    try:
        result = run(
            [
                sys.executable,
                str(SCRIPTS / "run-live-scene.py"),
                player,
                "--text-file",
                str(path),
                "--scene-mode",
                "slice",
                "--dry-run",
                "--bypass-mechanics-preflight",
            ],
            name="live scene repair",
            timeout=120,
        )
        if not result.ok:
            return result
        repaired = path.read_text(encoding="utf-8")
        required = ["tea", "clue", "Follow the odd draft"]
        missing = [item for item in required if item not in repaired]
        if missing:
            return Check("live scene repair", False, "repair missing: " + ", ".join(missing))
        if any(tag in repaired for tag in ("[LIFE]", "[ARC]", "[SURPRISE]")):
            return Check("live scene repair", False, "choice tags were not stripped after repair")
        return Check("live scene repair", True, "contract/choice failures repair once before delivery")
    finally:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def check_page_tool_packet_builder(player: str) -> Check:
    scene = substantial_scene("the Academy threshold")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", prefix="enchantify-packet-", delete=False) as f:
        f.write(scene)
        scene_path = Path(f.name)
    out_path = Path(tempfile.gettempdir()) / "enchantify-page-tool-packet.json"
    try:
        state_path = Path(tempfile.gettempdir()) / "enchantify-page-tool-state.json"
        try:
            state_path.unlink()
        except FileNotFoundError:
            pass
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "scene_packet_builder.py"),
                player,
                "--text-file",
                str(scene_path),
                "--scene-mode",
                "arc",
                "--out",
                str(out_path),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "ENCHANTIFY_TOOL_STATE": str(state_path)},
        )
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip().splitlines()
            return Check("page tool packet", False, detail[0] if detail else "packet build failed")
        packet = json.loads(out_path.read_text(encoding="utf-8"))
        metadata = packet.get("metadata") or {}
        if metadata.get("tool_authority") != "page-tool-posture":
            return Check("page tool packet", False, "packet did not use Page tool posture")
        expected = ["text", "lights", "image", "voice", "music", "spotify", "wallpaper", "app_actions"]
        if packet.get("sequence") != expected:
            return Check("page tool packet", False, "conflict page sequence not applied")
        if "lights" not in packet or "music" not in packet or "wallpaper" not in packet or "app_actions" not in packet:
            return Check("page tool packet", False, "page-native high-intrusion cues missing")
        return Check("page tool packet", True, "Page tool posture overrides legacy intensity with intrusion rails")
    finally:
        for path in (scene_path, out_path, Path(tempfile.gettempdir()) / "enchantify-page-tool-state.json"):
            try:
                path.unlink()
            except FileNotFoundError:
                pass


def check_character_image_prompt() -> Check:
    sync = run([sys.executable, str(SCRIPTS / "character-visuals.py"), "sync"], name="character visuals", timeout=60)
    if not sync.ok:
        return sync
    spec = importlib.util.spec_from_file_location("scene_packet_builder", SCRIPTS / "scene_packet_builder.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    prompt = module.build_image_prompt(
        "Wicker waits by the wrong door",
        "tense invitation",
        "lamps burn too gold",
        "Wicker Eddies; Zara Finch",
        "Wicker Eddies tilts his head and holds up a brass key. Zara Finch watches from the stair.",
    )
    lowered = prompt.lower()
    required = ["character-focused", "face", "posture", "hands", "meaningful object"]
    missing = [item for item in required if item not in lowered]
    if missing:
        return Check("character image prompt", False, "missing: " + ", ".join(missing))
    for item in ("canonical visual identity", "wrong-door brass key", "chaos sigils"):
        if item not in lowered:
            return Check("character image prompt", False, f"missing Wicker visual canon: {item}")
    if "scene frame" in lowered:
        return Check("character image prompt", False, "room-first Scene frame language returned")
    return Check("character image prompt", True, "image prompts prefer character canon over rooms")


def check_page_contract(player: str) -> Check:
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "page-contract.py"), player, "--json"],
        cwd=BASE,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()
        return Check("page contract", False, detail[0] if detail else "page contract failed")
    try:
        data = json.loads(proc.stdout)
    except Exception as exc:
        return Check("page contract", False, f"invalid JSON: {exc}")
    required = ["page_type", "page_label", "purpose", "artifact_due", "recommended_scene_mode"]
    missing = [key for key in required if not data.get(key)]
    if missing:
        return Check("page contract", False, "missing: " + ", ".join(missing))
    posture = data.get("tool_posture") or {}
    if not posture.get("preferred_tools") or not posture.get("triggers"):
        return Check("page contract", False, "missing page tool posture")
    enchantment = run(
        [sys.executable, str(SCRIPTS / "page-contract.py"), player, "--page-type", "enchantment"],
        name="page contract enchantment",
        timeout=60,
    )
    if not enchantment.ok:
        return Check("page contract", False, enchantment.detail)
    difficult = run(
        [sys.executable, str(SCRIPTS / "page-contract.py"), player, "--page-type", "difficult", "--json"],
        name="page contract difficult",
        timeout=60,
    )
    if not difficult.ok:
        return Check("page contract", False, difficult.detail)
    return Check("page contract", True, f"{data.get('page_label')} selected; explicit pages work")


def check_story_context(player: str) -> Check:
    result = run(
        [sys.executable, str(SCRIPTS / "story-context.py"), player],
        name="story context",
    )
    if not result.ok:
        return result
    if "CONTINUITY_THREADS:" not in result.detail and result.detail != "STORY CONTEXT":
        return Check("story context", False, "unexpected output")
    return Check("story context", True, "long memory synthesized")


def check_story_progress(player: str) -> Check:
    result = run(
        [sys.executable, str(SCRIPTS / "story-progress.py"), player],
        name="story progress",
    )
    if not result.ok:
        return result
    if result.detail != "STORY PROGRESS":
        return Check("story progress", False, "unexpected output")
    return Check("story progress", True, "arc/thread barometer runs")


def check_class_lecture(player: str) -> Check:
    result = run(
        [
            sys.executable,
            str(SCRIPTS / "class-lecture.py"),
            player,
            "--class-id",
            "basic-enchantments",
            "--status",
        ],
        name="class lecture",
    )
    if not result.ok:
        return result
    if result.detail != "CLASS LECTURE DIRECTIVE":
        return Check("class lecture", False, "unexpected output")
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "class-lecture.py"),
            player,
            "--class-id",
            "basic-enchantments",
            "--status",
        ],
        cwd=BASE,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if "Render only this segment" not in proc.stdout or "Forbidden compression phrases" not in proc.stdout:
        return Check("class lecture", False, "directive missing anti-compression rules")
    return Check("class lecture", True, "non-mutating lecture directive builds with segment rails")


def check_classroom_contract_validation() -> Check:
    spec = importlib.util.spec_from_file_location("scene_contract", SCRIPTS / "scene-contract.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    contract = {
        "scene_mode": "school-life",
        "current_location": "The Quillquarium",
        "mechanics": {},
        "page_contract": {"page_type": "slice_of_life", "page_label": "Slice of Life Page"},
        "story_context": {},
        "classroom_contract": {
            "active": True,
            "professor": "Professor Luna Wispwood",
            "room": "The Quillquarium",
            "classmates": ["Serenity Brown", "Zara Finch"],
            "lesson_title": "Object Address",
            "segment_index": 0,
            "segment": "professor demonstration",
        },
    }
    compressed_scene = (
        "In the Quillquarium, class passes quickly. Professor Luna Wispwood covers Object Address while everyone listens.\n\n"
        "What do you do?\n"
        "1. [LIFE] Ask whether Serenity wants tea after the classroom quiets.\n"
        "2. [ARC] Continue the lesson by asking Luna to demonstrate the next concept.\n"
        "3. [SURPRISE] Follow the draft under the side door no one mentioned.\n"
    )
    failures = module.validate_scene(compressed_scene, contract)
    if not any("compressed" in failure for failure in failures):
        return Check("classroom validation", False, "compressed class scene was not rejected")
    return Check("classroom validation", True, "compressed class summaries are rejected")


def check_widget_state(player: str) -> Check:
    result = run(
        [sys.executable, str(SCRIPTS / "widget-state.py"), player, "--json"],
        name="widget state",
        timeout=120,
    )
    if not result.ok:
        return result
    state_path = BASE / "hooks" / "widget-state.json"
    image_path = BASE / "hooks" / "widget-image.png"
    if not state_path.exists():
        return Check("widget state", False, "widget-state.json missing")
    if not image_path.exists():
        return Check("widget state", False, "widget-image.png missing")
    return Check("widget state", True, "inside cover JSON and image exported")


def check_narrative_health(player: str) -> Check:
    result = run(
        [sys.executable, str(SCRIPTS / "narrative-health.py"), player, "--json"],
        name="narrative health",
    )
    if not result.ok:
        return result
    try:
        import json
        report = json.loads(result.detail if result.detail.startswith("{") else "")
    except Exception:
        # run() keeps only the first line for detail, so call directly when JSON
        # spans lines. This path stays local and read-only.
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "narrative-health.py"), player, "--json"],
            cwd=BASE,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode != 0:
            return Check("narrative health", False, (proc.stderr or proc.stdout).splitlines()[0])
        report = json.loads(proc.stdout)
    status = report.get("status", "?")
    score = report.get("score", "?")
    return Check("narrative health", True, f"{status} ({score}/100) - stewardship report runs")


def check_narrative_steward(player: str) -> Check:
    result = run(
        [sys.executable, str(SCRIPTS / "narrative-steward.py"), player, "--refresh", "--json"],
        name="narrative steward",
    )
    if not result.ok:
        return result
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "narrative-steward.py"), player, "--refresh", "--json"],
        cwd=BASE,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        return Check("narrative steward", False, (proc.stderr or proc.stdout).splitlines()[0])
    import json
    state = json.loads(proc.stdout)
    open_count = sum(1 for item in state.get("obligations", []) if item.get("status", "open") == "open")
    return Check("narrative steward", True, f"{open_count} open obligation(s) queued")


def check_closeout_events_validator() -> Check:
    payload = {
        "belief_final": 77,
        "belief_changes": [],
        "belief_investments": [],
        "nothing_events": [],
        "enchantments_cast": [],
        "npc_interactions": [],
        "inventory_changes": [],
        "fae_bargains": [],
        "quests_completed": [],
        "quests_added": [],
        "compass_runs_completed": 0,
        "page": {
            "type": "archive",
            "label": "Archive Page",
            "artifact_created": "runtime validation note",
            "closed": True,
            "proof": "The smoke test preserved a page-shaped closeout event.",
        },
        "session_summary": "A quiet validation scene closed cleanly; no narrative state changed.",
        "most_alive_moment": "The Book checked its own binding.",
        "what_fell_flat": None,
        "thread_updates": [],
        "closed_threads": [
            {
                "name": "Runtime Smoke Thread",
                "outcome": "The validator proved closed thread events are accepted.",
                "closure_type": "natural",
                "aftercare": "No real thread was touched.",
            }
        ],
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", prefix="enchantify-events-", delete=False) as f:
        import json
        json.dump(payload, f)
        path = Path(f.name)
    try:
        result = run(
            [
                sys.executable,
                str(SCRIPTS / "close-session.py"),
                "--events-file",
                str(path),
                "--validate-only",
            ],
            name="closeout validator",
        )
        if result.ok:
            return Check("closeout validator", True, "events schema accepted")
        # close-session still needs a transcript/session file before validation,
        # so call the validator function directly as a lightweight import check.
        inline = (
            "import importlib.util, json, pathlib, sys; "
            "sys.path.insert(0, 'scripts'); "
            f"p=pathlib.Path({str(path)!r}); "
            "spec=importlib.util.spec_from_file_location('close_session','scripts/close-session.py'); "
            "m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); "
            "problems=m.validate_events(json.loads(p.read_text())); "
            "print('OK' if not problems else problems); "
            "raise SystemExit(0 if not problems else 1)"
        )
        return run([sys.executable, "-c", inline], name="closeout validator")
    finally:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def check_health_reader() -> Check:
    result = run([sys.executable, str(SCRIPTS / "check-health.py")], name="health reader", timeout=60)
    if not result.ok:
        return result
    if result.detail.startswith("HEALTH_BACKEND"):
        return Check("health reader", True, "diagnostic command works")
    return result


def check_bleed_fallback() -> Check:
    inline = (
        "import sys; sys.path.insert(0, 'scripts'); import bleed; "
        "data={'date_str':'2026-04-29','issue_number':99,"
        "'player':{'name':'bj','chapter':'Riddlewind','belief':'77','tutorial':'T15'},"
        "'thread_summary':'- Academy Daily Life [Belief 44, quiet, background]: tea returns\\n- The Weight of a Whisper [Belief 40, setup, front page]: whispers gain weight',"
        "'tick_queue':'- A corridor remembers a soft word.',"
        "'entity_standings':'Zara Finch 26',"
        "'classified_leads':'- FOUND: a quiet cup',"
        "'market_odds_formatted':'Academy Daily Life | YES: 58 | NO: 42 | STEADY',"
        "'war_data':'No chapter is near a threshold.',"
        "'outer_stacks':'- ANCHOR: The Crossroads of Simple Joys waits.',"
        "'player_recap':'bj was last seen near the Great Hall.',"
        "'talisman_data':'Wind Cipher leads Riddlewind.',"
        "'fuel_data':'Coffee and dinner logged.',"
        "'forecast':'Cool, cloudy, legible.',"
        "'health':'Steps modest; sleep unknown.'}; "
        "sections=bleed.build_fallback_sections(data); "
        "problems=bleed.validate_generated_sections(sections); "
        "print('OK' if not problems else problems); "
        "raise SystemExit(0 if not problems else 1)"
    )
    result = run([sys.executable, "-c", inline], name="bleed fallback")
    if result.ok:
        return Check("bleed fallback", True, "local issue scaffold validates")
    return result


def check_bleed_vellum_column() -> Check:
    text = (SCRIPTS / "bleed.py").read_text(encoding="utf-8")
    required = [
        "Dr. Vellum's Desk",
        "DR. VELLUM LONGEVITY BRIEF",
        "VELLUM CHART / KNOWN PERSONAL CONTEXT",
        "Department of Applied Longevity physician",
        "resistance training",
        "doctor/pharmacist question",
        "Do not invent meals",
    ]
    missing = [item for item in required if item not in text]
    if missing:
        return Check("bleed vellum column", False, "missing: " + ", ".join(missing))
    return Check("bleed vellum column", True, "Provisions Log is now Vellum longevity desk")


def check_vellum_chart() -> Check:
    path = BASE / "players" / "bj-vellum-chart.md"
    if not path.exists():
        return Check("vellum chart", False, "players/bj-vellum-chart.md missing")
    text = path.read_text(encoding="utf-8")
    required = [
        "Vellum Rules",
        "Latest Labs",
        "Blood Pressure",
        "Current Supplements",
        "Current Experiments",
        "Doctor / Pharmacist Questions",
    ]
    missing = [item for item in required if item not in text]
    if missing:
        return Check("vellum chart", False, "missing sections: " + ", ".join(missing))
    return Check("vellum chart", True, "personal longevity context scaffold present")


def check_vellum_chart_helper() -> Check:
    tmp_chart = Path(tempfile.gettempdir()) / "enchantify-vellum-chart-check.md"
    try:
        try:
            tmp_chart.unlink()
        except FileNotFoundError:
            pass
        commands = [
            [sys.executable, str(SCRIPTS / "vellum-chart.py"), "--chart", str(tmp_chart), "init"],
            [sys.executable, str(SCRIPTS / "vellum-chart.py"), "--chart", str(tmp_chart), "bp", "128", "82", "--pulse", "74", "--context", "after coffee"],
            [sys.executable, str(SCRIPTS / "vellum-chart.py"), "--chart", str(tmp_chart), "lab", "A1C", "5.4", "--unit", "%", "--date", "2026-05-10"],
            [sys.executable, str(SCRIPTS / "vellum-chart.py"), "--chart", str(tmp_chart), "supplement", "creatine monohydrate", "--dose", "5g", "--frequency", "daily", "--why", "strength experiment"],
            [sys.executable, str(SCRIPTS / "vellum-chart.py"), "--chart", str(tmp_chart), "experiment", "Lunch protein floor", "--metric", "3 PM hunger"],
            [sys.executable, str(SCRIPTS / "vellum-chart.py"), "--chart", str(tmp_chart), "question", "Is creatine appropriate with my kidney markers?"],
        ]
        for cmd in commands:
            result = run(cmd, name="vellum chart helper", timeout=60)
            if not result.ok:
                return result
        text = tmp_chart.read_text(encoding="utf-8")
        required = ["128 | 82", "| A1C | 5.4", "creatine monohydrate", "Lunch protein floor", "kidney markers"]
        missing = [item for item in required if item not in text]
        if missing:
            return Check("vellum chart helper", False, "missing writes: " + ", ".join(missing))
        return Check("vellum chart helper", True, "structured BP/lab/supplement/experiment/question writes work")
    finally:
        try:
            tmp_chart.unlink()
        except FileNotFoundError:
            pass


def check_therapy_chart_helper() -> Check:
    tmp_chart = Path(tempfile.gettempdir()) / "enchantify-therapy-chart-check.md"
    try:
        try:
            tmp_chart.unlink()
        except FileNotFoundError:
            pass
        commands = [
            [sys.executable, str(SCRIPTS / "therapy-chart.py"), "--chart", str(tmp_chart), "init"],
            [sys.executable, str(SCRIPTS / "therapy-chart.py"), "--chart", str(tmp_chart), "checkin", "--mood", "tight chest", "--problem", "The Fog", "--preferred", "BJ who takes one small step", "--action", "drink water"],
            [sys.executable, str(SCRIPTS / "therapy-chart.py"), "--chart", str(tmp_chart), "daydream", "a locked reading room", "--feeling", "curious", "--meaning", "privacy with a door", "--action", "write one sentence"],
            [sys.executable, str(SCRIPTS / "therapy-chart.py"), "--chart", str(tmp_chart), "reauthor", "--old-story", "I always stall", "--unique-outcome", "I asked for help", "--preferred-identity", "someone who returns", "--proof", "the chart exists"],
            [sys.executable, str(SCRIPTS / "therapy-chart.py"), "--chart", str(tmp_chart), "question", "What pattern should I bring to a therapist?"],
        ]
        for cmd in commands:
            result = run(cmd, name="therapy chart helper", timeout=60)
            if not result.ok:
                return result
        text = tmp_chart.read_text(encoding="utf-8")
        required = ["The Fog", "locked reading room", "I always stall", "bring to a therapist"]
        missing = [item for item in required if item not in text]
        if missing:
            return Check("therapy chart helper", False, "missing writes: " + ", ".join(missing))
        return Check("therapy chart helper", True, "structured check-in/daydream/reauthor/question writes work")
    finally:
        try:
            tmp_chart.unlink()
        except FileNotFoundError:
            pass


def check_support_faculty_helper() -> Check:
    tmp_home = Path(tempfile.gettempdir()) / "enchantify-support-faculty-check"
    pending = BASE / "players" / "bj-inkrest-pending.json"
    ink_log = BASE / "players" / "bj-inkrest-log.jsonl"
    pending_before = pending.read_text(encoding="utf-8") if pending.exists() else None
    ink_before = ink_log.read_text(encoding="utf-8") if ink_log.exists() else None
    try:
        result = run(
            [sys.executable, str(SCRIPTS / "support-faculty.py"), "inkrest-checkin", "--slot", "midday", "--dry-run"],
            name="support faculty",
            timeout=60,
        )
        if not result.ok:
            return result
        if "one word" not in result.detail.lower() or "weather in you" not in result.detail.lower():
            return Check("support faculty", False, "Inkrest check-in prompt missing")
        vellum = run(
            [sys.executable, str(SCRIPTS / "support-faculty.py"), "vellum-brief", "--dry-run"],
            name="support faculty vellum",
            timeout=60,
        )
        if not vellum.ok:
            return vellum
        if "Dr. Vellum" not in vellum.detail or "small hinge" not in vellum.detail:
            return Check("support faculty", False, "Vellum brief missing body/fuel read")
        research = run(
            [sys.executable, str(SCRIPTS / "support-faculty.py"), "research", "--doctor", "inkrest", "--dry-run"],
            name="support faculty research",
            timeout=60,
        )
        if not research.ok:
            return research
        if "Independent Brief" not in research.detail:
            return Check("support faculty", False, "support research brief missing experiment")
        pending.write_text(
            json.dumps({
                "kind": "inkrest-checkin",
                "slot": "midday",
                "sent_at": datetime.now().isoformat(timespec="seconds"),
                "message": "runtime test",
                "status": "awaiting-reply",
            }),
            encoding="utf-8",
        )
        routed = run(
            [sys.executable, str(SCRIPTS / "support-faculty.py"), "inkrest-route", "tired", "--context", "runtime-test"],
            name="support faculty route",
            timeout=60,
        )
        if not routed.ok:
            return routed
        if pending.exists():
            return Check("support faculty", False, "Inkrest pending marker was not cleared")
        return Check("support faculty", True, "Inkrest/Vellum check-ins, routing, briefs, and research dry-run")
    finally:
        if pending_before is None:
            try:
                pending.unlink()
            except FileNotFoundError:
                pass
        else:
            pending.write_text(pending_before, encoding="utf-8")
        if ink_before is None:
            try:
                ink_log.unlink()
            except FileNotFoundError:
                pass
        else:
            ink_log.write_text(ink_before, encoding="utf-8")
        try:
            tmp_home.unlink()
        except FileNotFoundError:
            pass


def check_inkrest_calendar() -> Check:
    result = run([sys.executable, str(SCRIPTS / "build-academy-calendar.py")], name="academy calendar", timeout=60)
    if not result.ok:
        return result
    ics = (BASE / "hooks" / "enchantify_schedule.ics").read_text(encoding="utf-8", errors="replace")
    required = ["Dr. Inkrest Office Hours", "RRULE:FREQ=WEEKLY;BYDAY=TU", "RRULE:FREQ=WEEKLY;BYDAY=TH", "Reauthoring Rooms"]
    missing = [item for item in required if item not in ics]
    if missing:
        return Check("inkrest calendar", False, "missing: " + ", ".join(missing))
    return Check("inkrest calendar", True, "recurring Tuesday/Thursday office hours in Academy calendar")


def check_mission_control_vellum() -> Check:
    out_path = Path(tempfile.gettempdir()) / "enchantify-mission-control-vellum-check.html"
    try:
        result = run(
            [sys.executable, str(SCRIPTS / "mission-control.py"), "--out", str(out_path)],
            name="mission control vellum",
            timeout=120,
        )
        if not result.ok:
            return result
        html = out_path.read_text(encoding="utf-8", errors="replace")
        required = ['id="vellum"', "Dr. Vellum's Desk", "Latest Health Signals", "Recent Fuel Log", "Vellum Chart"]
        missing = [item for item in required if item not in html]
        if missing:
            return Check("mission control vellum", False, "missing: " + ", ".join(missing))
        return Check("mission control vellum", True, "Story-Field Journal exposes Vellum health/fuel/chart context")
    finally:
        try:
            out_path.unlink()
        except FileNotFoundError:
            pass


def check_bleed_ripples() -> Check:
    inline = (
        "import sys, pathlib; sys.path.insert(0, 'scripts'); import bleed; "
        "bleed.BLEED_RIPPLES_LOG = pathlib.Path('/private/tmp/enchantify-bleed-ripples-check.jsonl'); "
        "sections={"
        "'HEADLINE':'TITLE: Library Rumor Finds a Door\\nSUMMARY: Students now believe the stacks are listening.',"
        "'FEATURE':'Zara Finch pinned a correction to the noticeboard before breakfast.',"
        "'GOSSIP':'Mira Wending says the corridor heard its name.',"
        "'WARREPORT':'Duskthorn pressure rose around X / Twitter.',"
        "'TALISMAN':'Tide Glass keeps asking what the hour wants.',"
        "'FUEL':'Dr. Vellum recommends protein before the evening walk.',"
        "'GOBLINEXCHANGE':'Offering: one brass bookmark. Wanted: a true errand.',"
        "'CLASSIFIEDS':'NOTICE: A folded map seeks its owner.'}; "
        "ripples=bleed.record_bleed_ripples('2099-01-01', 1, sections, {}); "
        "print(len(ripples)); "
        "raise SystemExit(0 if len(ripples) >= 6 and any(r.get('effect_type')=='rumor_pressure' for r in ripples) else 1)"
    )
    result = run([sys.executable, "-c", inline], name="bleed ripples")
    if result.ok:
        return Check("bleed ripples", True, "published articles create public-pressure records")
    return result


def check_npc_research_path(player: str) -> Check:
    source = (SCRIPTS / "npc-research.py").read_text(encoding="utf-8")
    blocked = ('"openclaw", "agent"', "'openclaw', 'agent'")
    if any(needle in source for needle in blocked):
        return Check("npc research path", False, "spawns openclaw agent instead of gateway")
    result = run(
        [
            sys.executable,
            str(SCRIPTS / "npc-research.py"),
            player,
            "--dry-run",
            "--no-print",
            "--no-icloud",
        ],
        name="npc research path",
        timeout=30,
    )
    if result.ok:
        return Check("npc research path", True, "gateway path present; dry-run works")
    return result


def check_outreach_path() -> Check:
    source = (SCRIPTS / "reach-out.py").read_text(encoding="utf-8")
    blocked = ('"openclaw", "agent"', "'openclaw', 'agent'", "has been thinking about you")
    found = [needle for needle in blocked if needle in source]
    if found:
        return Check("outreach path", False, "blocked fallback/path present: " + ", ".join(found))
    result = run(
        [
            sys.executable,
            str(SCRIPTS / "reach-out.py"),
            "--dry-run",
            "--force",
            "Zara Finch",
        ],
        name="outreach path",
        timeout=120,
    )
    if not result.ok:
        return result
    if "thinking about you" in result.detail.lower() or "not logged in" in result.detail.lower():
        return Check("outreach path", False, "weak or operational message generated")
    return Check("outreach path", True, "gateway path present; dry-run works")


def check_cron_steward() -> Check:
    inline = (
        "import sys, uuid; sys.path.insert(0, 'scripts'); import cron_steward; "
        "scope='test-'+uuid.uuid4().hex; "
        "payload={'kind':'smoke','value':'same'}; "
        "skip,digest,reason=cron_steward.should_skip_duplicate('runtime-smoke', payload, cooldown_hours=1, force=False, scope=scope); "
        "assert not skip; "
        "cron_steward.mark_delivered('runtime-smoke', payload, scope=scope); "
        "skip,digest,reason=cron_steward.should_skip_duplicate('runtime-smoke', payload, cooldown_hours=1, force=False, scope=scope); "
        "print(reason); "
        "raise SystemExit(0 if skip else 1)"
    )
    result = run([sys.executable, "-c", inline], name="cron steward")
    if result.ok:
        return Check("cron steward", True, "ledger and duplicate guard work")
    return result


def check_fae_ledger(player: str) -> Check:
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "fae-ledger.py"),
            "add",
            player,
            "--fae",
            "Goblin Index Empire",
            "--gave",
            "one test shelfmark",
            "--terms",
            "one precise overlooked label",
            "--deadline",
            "2099-01-01",
            "--dry-run",
        ],
        cwd=BASE,
        capture_output=True,
        text=True,
        timeout=20,
    )
    add_output = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0 or "BARGAIN_ADDED" not in add_output:
        return Check("fae ledger", False, add_output.strip().splitlines()[0] if add_output.strip() else "dry-run add failed")

    listing = run(
        [sys.executable, str(SCRIPTS / "fae-ledger.py"), "list", player, "--details"],
        name="fae ledger list",
    )
    if not listing.ok:
        return Check("fae ledger", False, listing.detail)
    return Check("fae ledger", True, "add/list path works")


def check_thread_steward() -> Check:
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "thread-steward.py"), "--json"],
        cwd=BASE,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()
        return Check("thread steward", False, detail[0] if detail else "thread steward failed")
    try:
        data = json.loads(proc.stdout)
    except Exception as exc:
        return Check("thread steward", False, f"invalid JSON: {exc}")
    if "actions" not in data or "summary" not in data:
        return Check("thread steward", False, "missing actions/summary in report")
    return Check("thread steward", True, "lifecycle report runs")


def check_thread_closure_path() -> Check:
    inline = """
import importlib.util
import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, 'scripts')
spec = importlib.util.spec_from_file_location('close_session', 'scripts/close-session.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

with tempfile.TemporaryDirectory(prefix='enchantify-thread-close-') as d:
    d = pathlib.Path(d)
    threads = d / 'threads.md'
    register = d / 'world-register.md'
    shutil.copy2('lore/threads.md', threads)
    shutil.copy2('lore/world-register.md', register)
    old_threads = m.THREADS_MD
    old_register = m.REGISTER_MD
    m.THREADS_MD = threads
    m.REGISTER_MD = register
    m.apply_closed_threads([{
        'name': "Elowen's Refectory Experiments",
        'outcome': 'Runtime smoke ending only.',
        'closure_type': 'natural',
        'aftercare': 'The real thread remains open.',
    }], False)
    out_t = threads.read_text()
    out_r = register.read_text()
    m.THREADS_MD = old_threads
    m.REGISTER_MD = old_register
    assert "## Archive: Elowen's Refectory Experiments" in out_t
    assert "| Elowen's Refectory Experiments | Thread |" not in out_r
print('OK')
"""
    result = run([sys.executable, "-c", inline], name="thread closure path")
    if result.ok:
        return Check("thread closure path", True, "archive/remove dry-run works")
    return result


def check_narrative_sim_variety() -> Check:
    inline = """
import sys
sys.path.insert(0, 'scripts')
import narrative_sim

profile = narrative_sim.ActorProfile(name='Runtime Watcher', chapter='Mossbloom')
state = {
    'pulse_index': 8,
    'recent_actions': [{
        'npc': 'Someone Else',
        'thread_id': 'academy-daily',
        'action': 'reposition',
        'visible_trace': 'Someone acted in courtyard path: held the gate open long enough for the wet-footed students to cross without slipping.',
        'hidden_effect': 'Concrete daily-life action: courtyard path / held the gate open long enough for the wet-footed students to cross without slipping / result: the afternoon route bent around care instead of impatience.',
        'trace_signature': narrative_sim.normalize_trace_signature('held the gate open long enough for the wet-footed students to cross without slipping'),
    }],
}
visible, hidden = narrative_sim.build_daily_life_trace(profile, 'reposition', [], state)
print(visible)
blocked = ['held the gate open', 'moved the noisy first-years', 'changed the order of the return crates']
raise SystemExit(1 if any(item in visible.lower() for item in blocked) or 'Runtime Watcher' not in visible else 0)
"""
    result = run([sys.executable, "-c", inline], name="simulation variety")
    if result.ok:
        return Check("simulation variety", True, "daily-life traces are actor-composed, not bank boilerplate")
    return result


def check_narrative_sim_character_lore() -> Check:
    inline = """
import sys
sys.path.insert(0, 'scripts')
import narrative_sim

register = '''
| Entity | Type | Belief | Notes |
| Dr. Selene Inkrest | NPC | 31 | [thread:academy-daily,inkrest-difficult-pages] Book Fae; Academy Narrative Therapist; Unwritten Interest: consciousness and brain studies as they relate to BJ |
'''
entities, talismans, anchors = narrative_sim.parse_world_register(register)
profile = narrative_sim.derive_actor_profile(entities['Dr. Selene Inkrest'], {'Dr. Selene Inkrest'})
visible, hidden = narrative_sim.build_daily_life_trace(profile, 'research', [], {'pulse_index': 1, 'recent_actions': []})
print(profile.lore_summary)
print(visible)
ok = (
    'consciousness' in profile.lore_summary.lower()
    and 'narrative therapy' in profile.lore_summary.lower()
    and 'reauthoring card' in visible.lower()
    and 'feeling' in visible.lower()
)
raise SystemExit(0 if ok else 1)
"""
    result = run([sys.executable, "-c", inline], name="simulation character lore")
    if result.ok:
        return Check("simulation character lore", True, "actor profiles use rich character lore")
    return result


def check_live_scene_dry_run(player: str) -> Check:
    scene_text = substantial_scene("Corin's marked room")
    voice_text = "[bm_lewis] " + scene_text
    with tempfile.NamedTemporaryFile("w", suffix=".txt", prefix="enchantify-scene-", delete=False) as scene_file:
        scene_file.write(scene_text)
        scene_path = Path(scene_file.name)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", prefix="enchantify-voice-", delete=False) as voice_file:
        voice_file.write(voice_text)
        voice_path = Path(voice_file.name)
    try:
        return run(
            [
                sys.executable,
                str(SCRIPTS / "run-live-scene.py"),
                player,
                "--text-file",
                str(scene_path),
                "--voice-file",
                str(voice_path),
                "--dry-run",
                "--bypass-mechanics-preflight",
                "--intensity",
                "quiet",
                "--target",
                "DRY_RUN",
            ],
            name="live scene dry-run",
            timeout=180,
        )
    finally:
        for path in (scene_path, voice_path):
            try:
                path.unlink()
            except FileNotFoundError:
                pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Enchantify runtime smoke checks.")
    parser.add_argument("player", nargs="?", default="bj")
    args = parser.parse_args()

    checks = [
        check_required_files(),
        check_root_stays_lean(),
        check_agents_size(),
        check_compile(),
        check_housekeeping(),
        check_drawthings_keepalive(),
        run(
            [sys.executable, str(SCRIPTS / "mechanics-preflight.py"), args.player, "--check-only"],
            name="mechanics preflight",
        ),
        run(
            [sys.executable, str(SCRIPTS / "scene-preflight.py"), "--speaker", "Zara Finch", "--strict"],
            name="speaker preflight",
        ),
        check_story_context(args.player),
        check_story_progress(args.player),
        check_page_contract(args.player),
        check_class_lecture(args.player),
        check_classroom_contract_validation(),
        check_widget_state(args.player),
        check_narrative_health(args.player),
        check_narrative_steward(args.player),
        check_scene_contract(args.player),
        check_page_tool_packet_builder(args.player),
        check_character_image_prompt(),
        check_scene_choices(),
        check_closeout_events_validator(),
        check_health_reader(),
        check_bleed_fallback(),
        check_bleed_vellum_column(),
        check_vellum_chart(),
        check_vellum_chart_helper(),
        check_therapy_chart_helper(),
        check_support_faculty_helper(),
        check_inkrest_calendar(),
        check_mission_control_vellum(),
        check_bleed_ripples(),
        check_cron_steward(),
        check_fae_ledger(args.player),
        check_thread_steward(),
        check_thread_closure_path(),
        check_narrative_sim_variety(),
        check_narrative_sim_character_lore(),
        check_npc_research_path(args.player),
        check_outreach_path(),
        check_live_scene_repair_retry(args.player),
        check_live_scene_dry_run(args.player),
    ]

    width = max(len(check.name) for check in checks)
    failed = False
    for check in checks:
        mark = "OK" if check.ok else "FAIL"
        print(f"{mark:4} {check.name:<{width}}  {check.detail}")
        failed = failed or not check.ok

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

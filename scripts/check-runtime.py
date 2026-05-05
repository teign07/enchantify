#!/usr/bin/env python3
"""Run Enchantify's small reliability checks without sending live messages.

This is a smoke test for the existing ritual path, not a gameplay entrypoint.
It avoids installer files in the repository root and keeps generated artifacts
under /tmp or tmp/scene-outbox.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
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
        "scripts/check-health.py",
        "scripts/scene-contract.py",
        "scripts/scene-choices.py",
        "scripts/scene-preflight.py",
        "scripts/run-live-scene.py",
        "scripts/story-progress.py",
        "scripts/narrative-health.py",
        "scripts/narrative-steward.py",
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
    return Check("AGENTS size", True, f"{size} chars below loader cutoff")


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


def check_scene_contract(player: str) -> Check:
    scene = (
        "You are still at the Great Hall, at the Riddlewind table. The cups, the long benches, "
        "and the ordinary scrape of chairs remain where the last page left them.\n\n"
        "What do you do?\n"
        "1. [LIFE] Ask whether anyone wants tea before the next strange thing happens.\n"
        "2. [ARC] Investigate the marked drawer and read the clue inside.\n"
        "3. [SURPRISE] Follow the draft under the side door no one mentioned.\n"
    )
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
    return Check("class lecture", True, "non-mutating lecture directive builds")


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
        "session_summary": "A quiet validation scene closed cleanly; no narrative state changed.",
        "most_alive_moment": "The Book checked its own binding.",
        "what_fell_flat": None,
        "thread_updates": [],
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


def check_live_scene_dry_run(player: str) -> Check:
    scene_text = (
        "You stand in the Academy corridor. The lamps remember your name.\n\n"
        "What do you do?\n"
        "1. Ask whether anyone wants tea before the next strange thing happens.\n"
        "2. Open the marked drawer and read the note inside.\n"
        "3. Follow the draft under the door no one mentioned.\n"
    )
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
        check_class_lecture(args.player),
        check_widget_state(args.player),
        check_narrative_health(args.player),
        check_narrative_steward(args.player),
        check_scene_contract(args.player),
        check_scene_choices(),
        check_closeout_events_validator(),
        check_health_reader(),
        check_bleed_fallback(),
        check_cron_steward(),
        check_npc_research_path(args.player),
        check_outreach_path(),
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

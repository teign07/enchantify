#!/usr/bin/env python3
import argparse
import re
import subprocess
from pathlib import Path

BASE = Path('/Users/bj/.openclaw/workspace/enchantify')
STATE = BASE / 'lore' / 'academy-state.md'
ARC = BASE / 'lore' / 'current-arc.md'
LOG = BASE / 'logs' / 'academy-hourly.md'
TTS = BASE / 'scripts' / 'multi_voice_tts.py'


def read(path: Path) -> str:
    return path.read_text() if path.exists() else ''


def find(pattern: str, text: str, default: str = '') -> str:
    m = re.search(pattern, text, re.M)
    return m.group(1).strip() if m else default


def first_row_note(name: str, text: str) -> str:
    for line in text.splitlines():
        if f'**{name}**' in line:
            parts = [p.strip() for p in line.split('|')]
            if parts:
                return parts[-1].strip()
    return ''


def first_thread(text: str) -> tuple[str, str]:
    for line in text.splitlines():
        if line.startswith('| **'):
            parts = [p.strip() for p in line.strip('|').split('|')]
            if len(parts) >= 3:
                return parts[0].replace('**', ''), parts[2]
    return 'Academy Daily Life', 'The Academy keeps breathing between bells.'


def first_environment(text: str) -> tuple[str, str]:
    seen_header = False
    for line in text.splitlines():
        if line.startswith('## Environment'):
            seen_header = True
            continue
        if seen_header and line.startswith('| **'):
            parts = [p.strip() for p in line.strip('|').split('|')]
            if len(parts) >= 3:
                return parts[0].replace('**', ''), parts[2]
    return 'The Academy', 'The halls hold their weather quietly.'


def latest_log_line(text: str) -> str:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return lines[-1] if lines else ''


def build_dispatch() -> str:
    state = read(STATE)
    arc = read(ARC)
    log = read(LOG)

    updated = find(r'\*\*Last Updated:\*\*\s*(.+)', state, 'Unknown')
    current_hour = find(r'\*\*Current Hour:\*\*\s*(.+)', state, 'Unknown')
    arc_title = find(r'^# Current Arc —\s*(.+)', arc, 'Unknown Arc')
    phase = find(r'^## Phase:\s*(.+)', arc, 'Unknown')
    day = find(r'^## Day:\s*(.+)', arc, '?')
    mode = 'FULL'
    last_log = latest_log_line(log)
    if 'HOLD-BREATH' in last_log:
        mode = 'HOLD-BREATH'
    npc_note = first_row_note('Professor Euphony', state) or first_row_note('Headmistress Thorne', state) or 'The faculty are listening closely to the Academy\'s pulse.'
    npc_name = 'Professor Euphony' if 'Professor Euphony' in state else 'Headmistress Thorne'
    thread_name, thread_note = first_thread(state)
    env_name, env_note = first_environment(state)

    dispatch = (
        f"### {updated}\n"
        f"**Arc:** {arc_title} | **Phase:** {phase} | **Day:** {day}\n"
        f"**Mode:** {mode}\n\n"
        f"**NPC Decisions:** - {npc_name}: {npc_note}\n"
        f"**Story Threads:** - {thread_name}: {thread_note}\n"
        f"**Environment:** - {env_name}: {env_note}\n"
        f"**One-Liner:** 📖 Academy: {last_log.split(' — ', 1)[-1] if ' — ' in last_log else current_hour}."
    )
    return dispatch[:1500]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', default='8729557865')
    parser.add_argument('--channel', default='telegram')
    parser.add_argument('--account', default='enchantify')
    args = parser.parse_args()

    dispatch = build_dispatch()
    cmd = [
        'python3', str(TTS),
        '--target', args.target,
        '--channel', args.channel,
        '--account', args.account,
        f'[bm_lewis] {dispatch}'
    ]
    res = subprocess.run(cmd, text=True)
    raise SystemExit(res.returncode)


if __name__ == '__main__':
    main()

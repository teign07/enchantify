#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))
import cron_steward

BASE = Path('/Users/bj/.openclaw/workspace/enchantify')
STATE = BASE / 'lore' / 'academy-state.md'
ARC = BASE / 'lore' / 'current-arc.md'
WORLD_REGISTER = BASE / 'lore' / 'world-register.md'
TICK_QUEUE = BASE / 'memory' / 'tick-queue.md'
LOG = BASE / 'logs' / 'academy-hourly.md'
SIM_LOG_DIR = BASE / 'logs' / 'simulations'
TTS = BASE / 'scripts' / 'multi_voice_tts.py'
LOCK = BASE / 'config' / 'session-active.lock'
STATE_FILE = BASE / 'config' / 'academy-dispatch-state.json'

LOW_INFO_PATTERNS = (
    'pieces have shifted offscreen',
    'shape of things will not be exactly where you left it',
    'nudges the board without forcing a conclusion',
    'repositioned the live geometry',
    'major movement is not yet allowed',
    'pressure is still gathering',
    'routine background watch continues',
    'changed the shape of the ordinary day',
    'made academy daily life more specific',
    'acted offscreen to advance',
    'a sharper answer now exists somewhere',
    'the world is preparing to let it be noticed',
    'something that might have thinned held together',
    'students slog',
    'boggle forces laughter',
    'the halls hold their weather quietly',
)


def read(path: Path) -> str:
    return path.read_text() if path.exists() else ''


def append_log(line: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open('a', encoding='utf-8') as f:
        f.write(line.rstrip() + '\n')


def timestamp() -> str:
    return datetime.now().strftime('%Y-%m-%d %H:%M')


def lock_age() -> Optional[timedelta]:
    if not LOCK.exists():
        return None
    raw = LOCK.read_text(encoding='utf-8').strip()
    try:
        started = datetime.fromisoformat(raw)
    except ValueError:
        return timedelta.max
    return datetime.now() - started


def should_skip_for_lock(stale_hours: float, dry_run: bool = False) -> bool:
    age = lock_age()
    if age is None:
        return False
    stale_after = timedelta(hours=stale_hours)
    if age <= stale_after:
        append_log(
            f"[{timestamp()}] SKIPPED — session active "
            f"(lockfile present, age {age.total_seconds() / 3600:.1f}h)"
        )
        return True

    append_log(
        f"[{timestamp()}] STALE-LOCK — lockfile age {age.total_seconds() / 3600:.1f}h "
        f"exceeds {stale_hours:.1f}h; dispatch may proceed"
    )
    if not dry_run:
        try:
            LOCK.unlink()
        except FileNotFoundError:
            pass
    return False


def find(pattern: str, text: str, default: str = '') -> str:
    m = re.search(pattern, text, re.M)
    return m.group(1).strip() if m else default


def first_row_note(name: str, text: str) -> str:
    for line in text.splitlines():
        if f'**{name}**' in line or re.match(rf'^\|\s*{re.escape(name)}\s*\|', line):
            parts = [p.strip() for p in line.split('|')]
            non_empty = [p for p in parts if p]
            if non_empty:
                return re.sub(r'\[[^\]]+\]\s*', '', non_empty[-1]).strip()
    return ''


def first_thread(text: str) -> tuple[str, str]:
    for line in text.splitlines():
        if line.startswith('| **'):
            parts = [p.strip() for p in line.strip('|').split('|')]
            if len(parts) >= 3:
                return parts[0].replace('**', ''), parts[2]
    return 'Academy Daily Life', 'The Academy keeps breathing between bells.'


def first_active_thread(text: str) -> tuple[str, str]:
    candidates = parse_active_threads(text)
    if candidates:
        return candidates[0]['name'], candidates[0]['note'] or f"Belief {candidates[0]['belief']}"
    return first_thread(read(STATE))


def clean_note(text: str, limit: int = 360) -> str:
    text = re.sub(r'\[[^\]]+\]\s*', '', text or '')
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) > limit:
        return text[:limit - 1].rstrip() + '…'
    return text


def is_low_info(text: str) -> bool:
    lowered = (text or '').lower()
    return any(pattern in lowered for pattern in LOW_INFO_PATTERNS)


def parse_active_threads(text: str) -> list[dict]:
    in_threads = False
    rows = []
    for line in text.splitlines():
        if line.startswith('## Active Threads'):
            in_threads = True
            continue
        if in_threads and line.startswith('## '):
            break
        if not in_threads or not line.startswith('|') or line.startswith('|---') or 'Entity' in line:
            continue
        parts = [p.strip() for p in line.strip('|').split('|')]
        if len(parts) < 4:
            continue
        name, _kind, belief_raw, note_raw = parts[:4]
        note = clean_note(note_raw)
        try:
            belief = int(re.search(r'\d+', belief_raw).group(0))
        except Exception:
            belief = 0
        permanent = 'phase: permanent' in note.lower() or name == 'Academy Daily Life'
        rows.append({'name': name, 'belief': belief, 'note': note, 'permanent': permanent})

    rows.sort(key=lambda r: (not r['permanent'], r['belief']), reverse=True)
    return rows


def latest_tick_seed(text: str) -> str:
    seeds = re.findall(r'^Narrative seed:\s*(.+)$', text, flags=re.M)
    if seeds:
        return seeds[-1].strip()
    raws = re.findall(r'^\*Raw:\s*(.+?)\*$', text, flags=re.M)
    return raws[-1].strip() if raws else ''


def parse_datetime(raw: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(raw)
    except Exception:
        return None


def block_timestamp(block: str) -> Optional[datetime]:
    m = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2})', block)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), '%Y-%m-%d %H:%M')
    except ValueError:
        return None


def latest_useful_tick_seed(text: str, since: Optional[datetime] = None) -> str:
    blocks = re.split(r'\n(?=## )', text)
    scored = []
    for index, block in enumerate(blocks):
        ts = block_timestamp(block)
        if since and (ts is None or ts <= since):
            continue
        seed_match = re.search(r'^Narrative seed:\s*(.+)$', block, flags=re.M)
        if not seed_match:
            continue
        seed = clean_note(seed_match.group(1))
        if is_low_info(seed):
            continue
        score = index
        if '[PRIORITY: HIGH]' in block:
            score += 10000
        if 'THREAD ESCALATION:' in block or 'THREAD LEAD:' in block:
            score += 250
        scored.append((score, seed))
    if not scored:
        fallback = latest_tick_seed(text)
        return '' if is_low_info(fallback) else clean_note(fallback)
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1]


def recent_simulation_events(hours: int = 9, since: Optional[datetime] = None) -> list[dict]:
    now = datetime.now()
    events = []
    for offset in (0, 1):
        path = SIM_LOG_DIR / f"{(now - timedelta(days=offset)).date().isoformat()}.jsonl"
        if not path.exists():
            continue
        for line in path.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                ts = datetime.fromisoformat(entry.get('timestamp', ''))
            except Exception:
                continue
            if since and ts <= since:
                continue
            if now - ts <= timedelta(hours=hours):
                entry['_age_minutes'] = int((now - ts).total_seconds() // 60)
                events.append(entry)
    return events


def score_simulation_event(event: dict) -> int:
    score = 0
    if event.get('priority') == 'HIGH':
        score += 120
    kind = event.get('kind')
    action = event.get('action', '')
    thread = event.get('thread_name') or event.get('name') or ''
    narrative = event.get('narrative') or event.get('reason') or event.get('raw') or ''

    if kind == 'action':
        score += 35
    elif kind == 'talisman_intent':
        score += 30
    elif kind == 'consequence':
        score += 18

    if action == 'reveal':
        score += 55
    elif action in {'invest_belief', 'protect'}:
        score += 35
    elif action == 'prepare':
        score += 10
    elif action == 'reposition':
        score -= 35

    if thread and thread != 'Academy Daily Life':
        score += 40
    if event.get('intensity') == 'major':
        score += 30
    if is_low_info(narrative):
        score -= 70
    score -= event.get('_age_minutes', 0) // 30
    return score


def best_simulation_event(since: Optional[datetime] = None) -> Optional[dict]:
    events = recent_simulation_events(since=since)
    if not events:
        return None
    return max(events, key=score_simulation_event)


def format_influences(event: dict) -> str:
    influences = event.get('influence_snapshot') or []
    if influences:
        return ', '.join(influences[:3])
    return ''


def registry_note_for(name: str, register: str) -> str:
    if not name or not register:
        return ''
    bare = re.sub(r'\s*\([^)]*\)\s*$', '', name).strip()
    for line in register.splitlines():
        if not line.startswith('|'):
            continue
        parts = [p.strip() for p in line.strip('|').split('|')]
        if len(parts) >= 4 and parts[0] == bare:
            return clean_note(parts[3])
    return ''


def concrete_pressure_details(event: dict, register: str, limit: int = 2) -> str:
    details = []
    for item in event.get('influence_snapshot') or []:
        name = re.sub(r'\s*\([^)]*\)\s*$', '', item).strip()
        note = registry_note_for(name, register)
        if note and not is_low_info(note):
            details.append(f"{name}: {note}")
        if len(details) >= limit:
            break
    return '; '.join(details)


def action_phrase(action: str, thread: str) -> str:
    action = (action or '').replace('_', ' ').strip()
    if thread == 'Academy Daily Life':
        return {
            'reposition': 'changed the shape of the ordinary school day',
            'prepare': 'set up a concrete daily-life beat',
            'research': 'checked a practical campus question',
            'reveal': 'made a small campus detail easier to notice',
            'protect': 'kept one ordinary support from thinning',
            'invest belief': 'fed chapter pressure through daily routines',
        }.get(action, f'moved through {action or "the ordinary day"}')
    return {
        'reposition': 'shifted the live situation',
        'prepare': 'prepared the next beat',
        'research': 'found a sharper answer',
        'reveal': 'surfaced a clue',
        'protect': 'held a vulnerable edge',
        'invest belief': 'fed belief into the pressure',
        'attack belief': 'eroded an opposing position',
    }.get(action, action or 'acted')


def concrete_event_summary(event: dict, register: str = '') -> str:
    actor = clean_note(event.get('actor') or 'Someone')
    thread = clean_note(event.get('thread_name') or event.get('name') or 'the Academy')
    action = action_phrase(event.get('action', ''), thread)
    influences = format_influences(event)
    target = clean_note(event.get('target') or '')
    tail_bits = []
    if target:
        tail_bits.append(f"target: {target}")
    if influences:
        tail_bits.append(f"pressure: {influences}")
    detail = concrete_pressure_details(event, register)
    if detail:
        tail_bits.append(f"details: {detail}")
    status = ''
    if register and thread:
        for row in parse_active_threads(register):
            if row['name'] == thread:
                status = row.get('note', '')
                break
    if status and not is_low_info(status):
        tail_bits.append(f"registry: {status}")
    tail = f" ({'; '.join(tail_bits)})" if tail_bits else ''
    return clean_note(f"{actor} {action} around {thread}{tail}")


def format_simulation_event(event: Optional[dict], register: str = '') -> str:
    if not event:
        return ''
    kind = event.get('kind')
    narrative = clean_note(event.get('narrative') or event.get('reason') or event.get('raw') or '')

    if kind == 'action':
        actor = event.get('actor', 'Someone')
        action = event.get('action', 'acted').replace('_', ' ')
        thread = event.get('thread_name') or 'the Academy'
        if is_low_info(narrative):
            return concrete_event_summary(event, register)
        return narrative

    if kind == 'consequence':
        name = event.get('name', 'A pressure')
        before = event.get('before')
        after = event.get('after')
        reason = clean_note(event.get('reason') or '')
        if before is not None and after is not None:
            return clean_note(f"{name} moved {before} -> {after}. {reason}")

    if kind == 'talisman_intent':
        talisman = event.get('talisman', 'A talisman')
        thread = event.get('thread_name') or 'a thread'
        mode = event.get('mode', 'narrative')
        return clean_note(f"{talisman} formed a {mode} intent around {thread}.")

    return narrative


def npc_focus(best_event: Optional[dict], register: str, state: str) -> tuple[str, str]:
    if best_event and best_event.get('actor_kind') == 'npc' and score_simulation_event(best_event) > 0:
        actor = best_event.get('actor', '').strip()
        if actor:
            return actor, format_simulation_event(best_event, register)
    npc_note = (
        first_row_note('Professor Euphony', register)
        or first_row_note('Headmistress Thorne', register)
        or first_row_note('Professor Euphony', state)
        or first_row_note('Headmistress Thorne', state)
        or 'The faculty are listening closely to the Academy\'s pulse.'
    )
    npc_name = 'Professor Euphony' if 'Professor Euphony' in state else 'Headmistress Thorne'
    return npc_name, npc_note


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
    env_m = re.search(r'(?m)^##\s*(?:📍\s*)?Academy Environment\s*\n(.*?)(?=^## |\Z)', text, re.DOTALL)
    if env_m:
        current = ''
        state_text = ''
        notes = []
        for raw_line in env_m.group(1).splitlines():
            line = raw_line.strip()
            if not line:
                continue
            head_m = re.match(r'^\*\*([^*]+)\*\*\s*(?:[—-]\s*(.+))?$', line)
            if head_m:
                if current:
                    note = ' '.join(notes).strip() or state_text
                    if note and not is_low_info(note):
                        return current, clean_note(note)
                current = head_m.group(1).strip()
                state_text = (head_m.group(2) or '').strip()
                notes = []
                continue
            if current and line.startswith('-'):
                notes.append(line.lstrip('- ').strip())
        if current:
            note = ' '.join(notes).strip() or state_text
            if note and not is_low_info(note):
                return current, clean_note(note)
    return 'The Academy', 'The halls hold their weather quietly.'


def latest_log_line(text: str) -> str:
    operational = (
        'SKIPPED',
        'STALE-LOCK',
        'DRY-RUN',
        'DISPATCH ',
    )
    lines = [
        l.strip() for l in text.splitlines()
        if l.strip() and not any(marker in l for marker in operational)
    ]
    return lines[-1] if lines else ''


def load_dispatch_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding='utf-8')) if STATE_FILE.exists() else {}
    except Exception:
        return {}


def save_dispatch_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(state, indent=2), encoding='utf-8')
    tmp.replace(STATE_FILE)


def dispatch_fingerprint(dispatch: str) -> str:
    body = '\n'.join(dispatch.splitlines()[1:]).strip()
    normalized = re.sub(r'\s+', ' ', body)
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def should_skip_for_recent_dispatch(
    dispatch: str,
    *,
    min_interval_minutes: int,
    duplicate_cooldown_hours: int,
    dry_run: bool = False,
) -> bool:
    state = load_dispatch_state()
    now = datetime.now()
    last_sent_raw = state.get('last_sent_at', '')
    current_hash = dispatch_fingerprint(dispatch)

    if last_sent_raw:
        try:
            age = now - datetime.fromisoformat(last_sent_raw)
        except ValueError:
            age = None
        if age is not None and age < timedelta(minutes=min_interval_minutes):
            append_log(
                f"[{timestamp()}] DISPATCH SKIPPED recent — "
                f"last sent {int(age.total_seconds() // 60)}m ago"
            )
            cron_steward.mark_skipped(
                "academy-dispatch",
                "recent dispatch",
                fingerprint=current_hash,
                minutes_ago=int(age.total_seconds() // 60),
            )
            return True

        duplicate_age = timedelta(hours=duplicate_cooldown_hours)
        if state.get('last_hash') == current_hash and (age is None or age < duplicate_age):
            append_log(
                f"[{timestamp()}] DISPATCH SKIPPED duplicate — "
                f"content unchanged since {last_sent_raw[:16]}"
            )
            cron_steward.mark_skipped(
                "academy-dispatch",
                "duplicate content",
                fingerprint=current_hash,
                last_sent_at=last_sent_raw,
            )
            return True

    if not dry_run:
        state['last_attempted_hash'] = current_hash
        save_dispatch_state(state)
    return False


def mark_dispatch_sent(dispatch: str) -> None:
    state = load_dispatch_state()
    state['last_sent_at'] = datetime.now().isoformat()
    state['last_hash'] = dispatch_fingerprint(dispatch)
    save_dispatch_state(state)
    cron_steward.mark_delivered("academy-dispatch", dispatch, scope="telegram")


def build_dispatch() -> str:
    state = read(STATE)
    arc = read(ARC)
    register = read(WORLD_REGISTER)
    tick_queue = read(TICK_QUEUE)
    log = read(LOG)
    dispatch_state = load_dispatch_state()
    last_sent_at = parse_datetime(dispatch_state.get('last_sent_at', ''))

    updated = datetime.now().strftime('%A, %B %-d, %Y - %-I:%M %p')
    current_hour = find(r'\*\*Current Block:\*\*\s*(.+)', state) or find(r'\*\*Current Hour:\*\*\s*(.+)', state, 'the current hour')
    arc_title = find(r'^# Current Arc[: —]\s*(.+)', arc) or find(r'^#\s*(.+)', arc, 'Unknown Arc')
    phase = find(r'^## Phase:\s*(.+)', arc, 'Unknown')
    day = find(r'^## Day:\s*(.+)', arc, '?')
    mode = 'FULL'
    last_log = latest_log_line(log)
    if 'HOLD-BREATH' in last_log:
        mode = 'HOLD-BREATH'
    latest_event = best_simulation_event()
    best_event = best_simulation_event(since=last_sent_at) or (None if last_sent_at else latest_event)
    reference_event = best_event or latest_event
    npc_name, npc_note = npc_focus(reference_event, register, state)
    if reference_event and reference_event.get('thread_name'):
        thread_name = reference_event.get('thread_name')
        thread_note = concrete_event_summary(reference_event, register)
    else:
        thread_name, thread_note = first_active_thread(register)
    env_name, env_note = first_environment(state)
    pulse_note = latest_useful_tick_seed(tick_queue, since=last_sent_at) or ('' if last_sent_at else latest_useful_tick_seed(tick_queue))
    simulation_note = format_simulation_event(best_event, register)
    latest_note = format_simulation_event(latest_event, register)
    if pulse_note and simulation_note and pulse_note != simulation_note:
        one_liner = f"{pulse_note} Simulation focus: {simulation_note}"
    else:
        one_liner = (
            pulse_note
            or simulation_note
            or (f"Latest ledger movement: {latest_note}" if latest_note else '')
            or f"Current registry focus: {thread_name} — {thread_note}"
        )
    one_liner = one_liner.rstrip('. ')

    dispatch = (
        f"### {updated}\n"
        f"**Arc:** {arc_title} | **Phase:** {phase} | **Day:** {day}\n"
        f"**Mode:** {mode}\n\n"
        f"**NPC Decisions:** - {npc_name}: {npc_note}\n"
        f"**Story Threads:** - {thread_name}: {thread_note}\n"
        f"**Environment:** - {env_name}: {env_note}\n"
        f"**One-Liner:** 📖 Academy: {one_liner}."
    )
    return dispatch[:1500]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', default='8729557865')
    parser.add_argument('--channel', default='telegram')
    parser.add_argument('--account', default='enchantify')
    parser.add_argument(
        '--stale-lock-hours',
        type=float,
        default=float(os.environ.get('ACADEMY_DISPATCH_STALE_LOCK_HOURS', '18')),
        help='Treat session lock older than this as stale instead of skipping.',
    )
    parser.add_argument('--dry-run', action='store_true', help='Build dispatch and check lock without sending.')
    parser.add_argument(
        '--min-interval-minutes',
        type=int,
        default=int(os.environ.get('ACADEMY_DISPATCH_MIN_INTERVAL_MINUTES', '165')),
        help='Skip dispatches sent more recently than this. Default: 165 minutes.',
    )
    parser.add_argument(
        '--duplicate-cooldown-hours',
        type=int,
        default=int(os.environ.get('ACADEMY_DISPATCH_DUPLICATE_COOLDOWN_HOURS', '12')),
        help='Skip identical dispatch content inside this window. Default: 12 hours.',
    )
    args = parser.parse_args()

    with cron_steward.run("academy-dispatch", dry_run=args.dry_run):
        if should_skip_for_lock(args.stale_lock_hours, dry_run=args.dry_run):
            print('SKIPPED: session lock is fresh')
            cron_steward.mark_skipped("academy-dispatch", "session lock is fresh")
            return

        dispatch = build_dispatch()
        if should_skip_for_recent_dispatch(
            dispatch,
            min_interval_minutes=args.min_interval_minutes,
            duplicate_cooldown_hours=args.duplicate_cooldown_hours,
            dry_run=args.dry_run,
        ):
            print('SKIPPED: dispatch already sent recently or unchanged')
            return
        if args.dry_run:
            print(dispatch)
            append_log(f"[{timestamp()}] DRY-RUN — academy dispatch built ({len(dispatch)} chars)")
            return

        cmd = [
            sys.executable, str(TTS),
            '--target', args.target,
            '--channel', args.channel,
            '--account', args.account,
            f'[bm_lewis] {dispatch}'
        ]
        try:
            res = subprocess.run(cmd, text=True, timeout=240)
        except subprocess.TimeoutExpired:
            append_log(f"[{timestamp()}] DISPATCH FAILED timeout — TTS/send exceeded 240s")
            return 1
        status = 'SENT' if res.returncode == 0 else f'FAILED rc={res.returncode}'
        append_log(f"[{timestamp()}] DISPATCH {status} — {dispatch.splitlines()[0] if dispatch else 'empty'}")
        if res.returncode == 0:
            mark_dispatch_sent(dispatch)
        return res.returncode


if __name__ == '__main__':
    raise SystemExit(main() or 0)

#!/usr/bin/env python3
"""
pulse.py — Silvie's Nervous System
Runs every 15 minutes via cron. Writes sensory data between the PULSE markers
in HEARTBEAT.md, preserving the permanent standing orders below.
Belfast M4 Build — March 2026
"""

import os, json, subprocess, requests, imaplib, email, time, shutil, math
from datetime import datetime, timedelta
from pathlib import Path

# — LOAD CONFIG FROM secrets.env —
# All credentials and personal config live in config/secrets.env (gitignored).
# See config/secrets.env.example for the template.

def _load_secrets() -> dict:
    """Load config/secrets.env as key=value pairs. Never crashes — missing keys return ''."""
    secrets = {}
    workspace = Path(__file__).parent.parent
    secrets_path = workspace / "config" / "secrets.env"
    if secrets_path.exists():
        for line in secrets_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                secrets[k.strip()] = v.strip().strip('"').strip("'")
    return secrets

_cfg = _load_secrets()

def _cfg_get(key: str, default: str = "") -> str:
    return _cfg.get(key, os.environ.get(key, default))

# — CONFIGURATION —

LOCATION    = _cfg_get("LOCATION", "Belfast+Maine")
BELFAST_LAT = float(_cfg_get("LAT", "44.4258"))
BELFAST_LON = float(_cfg_get("LON", "-69.0064"))
NOAA_STATION = _cfg_get("NOAA_STATION", "8418150")
HOME_WIFI   = _cfg_get("HOME_WIFI", "")

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
ENCHANTIFY_WORKSPACE = os.path.join(WORKSPACE, "enchantify")

HEARTBEAT_FILE = os.path.join(ENCHANTIFY_WORKSPACE, "HEARTBEAT.md")
PREVIOUS_PULSE_FILE = os.path.join(ENCHANTIFY_WORKSPACE, "PREVIOUS_PULSE.md")
STATS_CACHE = os.path.join(WORKSPACE, "stats_cache.json")

# Markers in HEARTBEAT.md — pulse.py only touches content between these

PULSE_START = "<!-- PULSE_START -->"
PULSE_END = "<!-- PULSE_END -->"

# — CREDENTIALS (loaded from config/secrets.env) —

GMAIL_USER    = _cfg_get("GMAIL_USER")
GMAIL_APP_PASS = _cfg_get("GMAIL_APP_PASS")
PATREON_TOKEN = _cfg_get("PATREON_TOKEN")
PATREON_ID    = _cfg_get("PATREON_ID")
YT_KEY        = _cfg_get("YT_KEY")
YT_CH_ID      = _cfg_get("YT_CH_ID")
TELLER_TOKEN  = _cfg_get("TELLER_TOKEN")
TELLER_ACCOUNT_ID = _cfg_get("TELLER_ACCOUNT_ID")

# — QUIET HOURS (Silvie should whisper, not shout) —

QUIET_START = 22  # 10 PM
QUIET_END = 7     # 7 AM
WEEKEND_QUIET_END = 9  # Let them sleep in on weekends

# — UNIVERSAL CACHE HELPERS —

def get_cache_val(key, expiry_seconds):
    if os.path.exists(STATS_CACHE):
        try:
            with open(STATS_CACHE, 'r') as f:
                cache = json.load(f)
                if time.time() - cache.get(f"{key}_ts", 0) < expiry_seconds:
                    return cache.get(key)
        except: pass
    return None

def set_cache_val(key, val):
    data = {}
    if os.path.exists(STATS_CACHE):
        try:
            with open(STATS_CACHE, 'r') as f: 
                data = json.load(f)
        except: pass
    data[key], data[f"{key}_ts"] = val, time.time()
    with open(STATS_CACHE, 'w') as f: 
        json.dump(data, f)

# — ASTRONOMICAL CALCULATIONS —

def get_sun_times():
    """Calculate sunrise, sunset, day length, and daily change for Belfast, ME."""
    cached = get_cache_val("sun_data", 3600)
    if cached: return cached
    try:
        url = f"https://api.sunrise-sunset.org/json?lat={BELFAST_LAT}&lng={BELFAST_LON}&formatted=0&date=today"
        r = requests.get(url, timeout=5).json()
        if r['status'] != 'OK':
            return "Sun data unavailable."

        sunrise = datetime.fromisoformat(r['results']['sunrise'].replace('Z', '+00:00'))
        sunset = datetime.fromisoformat(r['results']['sunset'].replace('Z', '+00:00'))
        day_seconds = (sunset - sunrise).total_seconds()
        day_hours = day_seconds / 3600
        day_h = int(day_hours)
        day_m = int((day_hours - day_h) * 60)

        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        url_y = f"https://api.sunrise-sunset.org/json?lat={BELFAST_LAT}&lng={BELFAST_LON}&formatted=0&date={yesterday}"
        r_y = requests.get(url_y, timeout=5).json()
        if r_y['status'] == 'OK':
            sr_y = datetime.fromisoformat(r_y['results']['sunrise'].replace('Z', '+00:00'))
            ss_y = datetime.fromisoformat(r_y['results']['sunset'].replace('Z', '+00:00'))
            yesterday_seconds = (ss_y - sr_y).total_seconds()
            change_seconds = day_seconds - yesterday_seconds
            change_mins = abs(change_seconds) / 60
            if change_seconds > 0:
                trend = f"gaining {change_mins:.1f} min/day"
            elif change_seconds < 0:
                trend = f"losing {change_mins:.1f} min/day"
            else:
                trend = "holding steady (solstice)"
        else:
            trend = "trend unknown"

        sunrise_local = sunrise.strftime("%-I:%M %p")
        sunset_local = sunset.strftime("%-I:%M %p")
        result = f"Sunrise {sunrise_local} / Sunset {sunset_local} | {day_h}h {day_m}m of light ({trend})"
        set_cache_val("sun_data", result)
        return result
    except:
        return "Sun data unavailable."

def get_moon_phase():
    """Calculate moon phase, illumination, and phase name."""
    cached = get_cache_val("moon_data", 21600)
    if cached: return cached
    try:
        now = datetime.utcnow()
        known_new = datetime(2000, 1, 6, 18, 14, 0)
        synodic = 29.53058867
        days_since = (now - known_new).total_seconds() / 86400
        cycle_fraction = (days_since % synodic) / synodic

        if cycle_fraction < 0.0625:
            name = "New Moon"
        elif cycle_fraction < 0.1875:
            name = "Waxing Crescent"
        elif cycle_fraction < 0.3125:
            name = "First Quarter"
        elif cycle_fraction < 0.4375:
            name = "Waxing Gibbous"
        elif cycle_fraction < 0.5625:
            name = "Full Moon"
        elif cycle_fraction < 0.6875:
            name = "Waning Gibbous"
        elif cycle_fraction < 0.8125:
            name = "Last Quarter"
        elif cycle_fraction < 0.9375:
            name = "Waning Crescent"
        else:
            name = "New Moon"

        illumination = (1 - math.cos(2 * math.pi * cycle_fraction)) / 2 * 100
        emojis =["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘"]
        emoji = emojis[int(cycle_fraction * 8) % 8]

        result = f"{emoji} {name} ({illumination:.0f}% illuminated)"
        set_cache_val("moon_data", result)
        return result
    except:
        return "Moon data unavailable."

# — TIDES —

def get_tides():
    """Get next high and low tides from NOAA CO-OPS for Portland, ME."""
    cached = get_cache_val("tide_data", 1800)
    if cached: return cached
    try:
        today = datetime.now().strftime("%Y%m%d")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y%m%d")
        url = (
            f"https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
            f"?begin_date={today}&end_date={tomorrow}"
            f"&station={NOAA_STATION}&product=predictions"
            f"&datum=MLLW&time_zone=lst_ldt&interval=hilo"
            f"&units=english&application=Silvie&format=json"
        )
        r = requests.get(url, timeout=10).json()
        predictions = r.get('predictions',[])
        if not predictions:
            return "Tides: no data from Portland station."

        now = datetime.now()
        upcoming =[]
        for p in predictions:
            t = datetime.strptime(p['t'], "%Y-%m-%d %H:%M")
            if t > now:
                tide_type = "High" if p['type'] == 'H' else "Low"
                height = float(p['v'])
                time_str = t.strftime("%-I:%M %p")
                upcoming.append(f"{tide_type} {height:.1f}ft at {time_str}")
            if len(upcoming) >= 3:
                break

        past_tides = [p for p in predictions if datetime.strptime(p['t'], "%Y-%m-%d %H:%M") <= now]
        if past_tides:
            last = past_tides[-1]
            current_state = "coming in" if last['type'] == 'L' else "going out"
        else:
            current_state = "unknown"

        result = f"Tide {current_state} (Portland) | Next: {' → '.join(upcoming)}"
        set_cache_val("tide_data", result)
        return result
    except Exception as e:
        return f"Tides: offline ({e})"

# — WEATHER FORECAST (Open-Meteo, free, no key, cached 6h) —

WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Rime fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Dense drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Light showers", 81: "Showers", 82: "Heavy showers",
    85: "Snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm + hail", 99: "Thunderstorm + heavy hail",
}

def get_weather_forecast():
    """4-day forecast from Open-Meteo. Free, no key. Cached 6 hours."""
    import urllib.request as _urlreq
    cached = get_cache_val("weather_forecast", 21600)
    if cached:
        return cached
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={BELFAST_LAT}&longitude={BELFAST_LON}"
            f"&daily=weathercode,temperature_2m_max,temperature_2m_min,"
            f"precipitation_probability_max,windspeed_10m_max"
            f"&temperature_unit=fahrenheit&windspeed_unit=mph"
            f"&timezone=America%2FNew_York&forecast_days=4"
        )
        req = _urlreq.Request(url, headers={"User-Agent": "Enchantify/1.0"})
        with _urlreq.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())

        daily  = data.get("daily", {})
        dates  = daily.get("time", [])
        codes  = daily.get("weathercode", [])
        t_max  = daily.get("temperature_2m_max", [])
        t_min  = daily.get("temperature_2m_min", [])
        precip = daily.get("precipitation_probability_max", [])
        wind   = daily.get("windspeed_10m_max", [])

        today_str = datetime.now().strftime("%Y-%m-%d")
        lines = []
        for i, ds in enumerate(dates):
            from datetime import date as _date
            d = _date.fromisoformat(ds)
            if i == 0:
                label = "Today"
            elif i == 1:
                label = "Tomorrow"
            else:
                label = d.strftime("%A")
            desc  = WMO_CODES.get(int(codes[i]) if i < len(codes) else 0, "Unknown")
            hi    = f"{round(t_max[i])}°" if i < len(t_max) else "?"
            lo    = f"{round(t_min[i])}°" if i < len(t_min) else "?"
            rain  = f"{precip[i]}%" if i < len(precip) else "?"
            spd   = f"{round(wind[i])}mph" if i < len(wind) else "?"
            lines.append(f"{label}: {desc}, {hi}/{lo}F, {rain} precip, {spd} wind")

        result = "\n".join(lines)
        set_cache_val("weather_forecast", result)
        return result
    except Exception as e:
        return f"Forecast offline ({e})"


# — WEATHER WITH FEEL TRANSLATOR —

def get_weather_raw():
    """Get weather data from wttr.in."""
    cached = get_cache_val("weather_raw", 1800)
    if cached: return cached
    try:
        r = requests.get(f"https://wttr.in/{LOCATION}?format=j1", timeout=5).json()
        current = r['current_condition'][0]
        result = {
            'desc': current['weatherDesc'][0]['value'],
            'temp_f': current['temp_F'],
            'feels_f': current['FeelsLikeF'],
            'humidity': current['humidity'],
            'wind_mph': current['windspeedMiles'],
            'wind_dir': current['winddir16Point'],
            'pressure': current['pressure'],
            'cloud': current['cloudcover'],
            'visibility': current['visibility'],
        }
        set_cache_val("weather_raw", result)
        return result
    except:
        return None

def translate_weather_feel(w):
    """Turn weather data into a qualitative feel description."""
    if not w or not isinstance(w, dict):
        return "Atmosphere unreadable."

    desc = w.get('desc', '').lower()
    temp = int(w.get('temp_f', 50))
    humidity = int(w.get('humidity', 50))
    wind = int(w.get('wind_mph', 0))
    cloud = int(w.get('cloud', 50))
    hour = datetime.now().hour

    parts =[]

    if temp < 15:
        parts.append("Bitter cold — the kind that bites exposed skin")
    elif temp < 32:
        parts.append("Freezing — the air has edges")
    elif temp < 45:
        parts.append("Raw cold — the damp kind that gets into your bones")
    elif temp < 55:
        parts.append("Cool — jacket weather, hands in pockets")
    elif temp < 68:
        parts.append("Mild — window-open weather")
    elif temp < 80:
        parts.append("Warm — the kind that makes you want to sit outside")
    elif temp < 90:
        parts.append("Hot — the air has weight")
    else:
        parts.append("Sweltering — the world is melting")

    if 'fog' in desc or 'mist' in desc:
        if hour < 10:
            parts.append("morning fog making everything close and secret")
        else:
            parts.append("fog sitting on the harbor like a held breath")
    elif cloud > 85:
        parts.append("heavy overcast — the sky sitting on the rooftops")
    elif cloud > 60:
        parts.append("mostly cloudy — grey with the occasional bright crack")
    elif cloud > 30:
        parts.append("partly cloudy — light and shadow trading places")
    elif cloud < 10:
        parts.append("wide open sky")

    if wind > 25:
        parts.append("serious wind — the kind that leans on you")
    elif wind > 15:
        parts.append("breezy — flags snapping, hair in your eyes")
    elif wind > 5:
        parts.append("light wind — just enough to notice")

    if 'rain' in desc or 'drizzle' in desc:
        if 'light' in desc or 'drizzle' in desc:
            parts.append("light rain — the kind that makes everything smell alive")
        else:
            parts.append("real rain — the kind that drives you inside or makes you surrender to it")
    elif 'snow' in desc:
        if 'light' in desc:
            parts.append("light snow — the quiet kind that makes the world hold still")
        else:
            parts.append("snow coming down with purpose")

    if humidity > 85 and temp > 65:
        parts.append("thick humid air you could almost chew")
    elif humidity < 25:
        parts.append("dry air — static and chapped lips")

    feel = ". ".join(parts[:3]) + "."
    data_line = f"{w['desc']} {w['temp_f']}°F (feels {w['feels_f']}°F) | Wind {w['wind_mph']}mph {w['wind_dir']} | Humidity {w['humidity']}% | Pressure {w['pressure']}mb"

    return f"{feel}\n  *Raw: {data_line}*"

# — REAL SEASON —

def get_real_season():
    """What season it actually feels like in coastal Maine."""
    now = datetime.now()
    month, day = now.month, now.day

    if month == 1 or month == 2:
        return "Deep Winter — the long dark, woodsmoke and wool"
    elif month == 3 and day < 20:
        return "Late Winter — ice breaking up, days noticeably longer"
    elif month == 3 and day >= 20 or (month == 4 and day < 15):
        return "Mud Season — the thaw, everything dripping and brown"
    elif month == 4 or (month == 5 and day < 10):
        return "Early Spring — crocuses, returning birds, cold rain"
    elif month == 5:
        return "Spring — lilacs, apple blossoms, the first warm days"
    elif month == 6:
        return "Early Summer — long light, lupines, the harbor filling with boats"
    elif month == 7:
        return "High Summer — tourists, berries, the ocean almost warm enough"
    elif month == 8:
        return "Late Summer — the light starting to change, county fairs"
    elif month == 9 and day < 20:
        return "Early Fall — goldenrod, apple picking, first sweater mornings"
    elif month == 9 or (month == 10 and day < 20):
        return "Peak Fall — the world on fire, cider donuts, tourists again"
    elif month == 10 or (month == 11 and day < 15):
        return "Stick Season — leaves gone, bare branches, quiet grey"
    elif month == 11:
        return "Late Fall — woodsmoke, early dark, hunkering down"
    else:
        return "Early Winter — first snow, solstice approaching, candle season"

# — QUIET HOURS —

def get_quiet_status():
    """Determine if it's quiet hours — Silvie should be gentle."""
    now = datetime.now()
    hour = now.hour
    is_weekend = now.weekday() >= 5
    quiet_end = WEEKEND_QUIET_END if is_weekend else QUIET_END

    if hour >= QUIET_START or hour < quiet_end:
        if hour >= 23 or hour < 4:
            return "Deep Quiet — they're sleeping. Work silently."
        elif hour >= QUIET_START:
            return "Winding Down — be gentle, no pings."
        else:
            return "Early Morning — they may still be sleeping."
    elif hour < 9:
        return "Morning — they're waking up. Warm and easy."
    elif hour >= 17:
        return "Evening — work is done, home mode."
    else:
        return "Daytime — full operations."

# — ORIGINAL SENSORS —

def get_fuel_summary() -> str:
    """Read today's entries from enchantify fuel-log.txt and return a one-line summary."""
    fuel_log = os.path.join(ENCHANTIFY_WORKSPACE, "scripts", "fuel-log.txt")
    if not os.path.exists(fuel_log):
        return "Nothing logged yet."
    today = datetime.now().strftime("%Y-%m-%d")
    total_cal = 0
    total_pro = 0
    items = []
    try:
        with open(fuel_log) as f:
            for line in f:
                parts = line.strip().split("|")
                if len(parts) >= 5 and parts[0] == today:
                    items.append(parts[2])
                    total_cal += int(parts[3]) if parts[3].isdigit() else 0
                    total_pro += int(parts[4]) if parts[4].isdigit() else 0
    except Exception:
        return "Log unreadable."
    if not items:
        return "Nothing logged yet."
    cal_str = f"{total_cal} cal" if total_cal else "cal unknown"
    pro_str = f"{total_pro}g protein" if total_pro else ""
    summary = " · ".join(items)
    totals = f"{cal_str}{', ' + pro_str if pro_str else ''}"
    return f"{summary} — {totals}"


def get_calendar():
    try:
        events = subprocess.getoutput("/opt/homebrew/bin/icalBuddy -n eventsToday")
        return events if events and "error" not in events.lower() else "Clear skies on the calendar."
    except: return "Calendar unreachable."

def get_frontmost_app():
    cmd = """osascript -e 'tell application "System Events"
        set frontApp to name of first application process whose frontmost is true
        try
            set windowTitle to name of front window of process frontApp
            return frontApp & "[" & windowTitle & "]"
        on error
            return frontApp
        end try
    end tell'"""
    try: return subprocess.getoutput(cmd).strip()
    except: return "Unknown"

def get_presence():
    try:
        idle_ns = int(subprocess.getoutput("ioreg -c IOHIDSystem | awk '/HIDIdleTime/ {print $NF; exit}'"))
        idle_mins = idle_ns / 1000000000 / 60
        if idle_mins > 60:
            return f"Away ({int(idle_mins / 60)}h {int(idle_mins % 60)}m)"
        elif idle_mins > 5:
            return f"Away ({int(idle_mins)}m)"
        return "Active"
    except: return "Unknown"

def get_location_context():
    try:
        cmd = "networksetup -getairportnetwork en0 | cut -d ':' -f 2"
        wifi = subprocess.getoutput(cmd).strip()
        if not wifi or "Error" in wifi or "not associated" in wifi:
            cmd_fallback = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -I | awk '/ SSID/ {print substr($0, index($0, $2))}'"
            wifi = subprocess.getoutput(cmd_fallback).strip()
        if wifi == HOME_WIFI: return "At Home (Belfast)"
        return f"Mobile ({wifi})" if wifi else "Offline/Woods"
    except: return "Location Unknown"

def get_focus_status():
    try:
        cmd = "defaults read com.apple.controlcenter 'NSStatusItem Visible DoNotDisturb'"
        status = subprocess.getoutput(cmd).strip()
        return "Deep Focus / DND" if status == "1" else "Available"
    except: return "Available"

def get_spotify():
    cmd = """osascript -e 'tell application "System Events" to if (get name of every process) contains "Spotify" then tell application "Spotify" to return name of current track & " by " & artist of current track'"""
    try:
        out = subprocess.getoutput(cmd)
        return out if out and "error" not in out.lower() else "The house is quiet."
    except: return "The house is quiet."

def get_system_vitals():
    try:
        stats = subprocess.getoutput("top -l 1 | grep -E '^CPU|^Phys'").split('\n')
        cpu = stats[0].split(':')[1].split(',')[0].strip()
        ram = stats[1].split(':')[1].split('(')[0].strip()
        ane = "Active" if "qwen" in subprocess.getoutput("ps aux").lower() else "Idle"
        return f"CPU: {cpu} | RAM: {ram} | Neural Engine: {ane}"
    except: return "Hardware stats pending..."

def get_gmail_subjects():
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_APP_PASS)
        mail.select("inbox")
        _, data = mail.search(None, 'UNSEEN')
        email_ids = data[0].split()
        if not email_ids:
            mail.logout()
            return "Inbox zero. No unread mail."
        subjects =[]
        for i in email_ids[-3:]:
            _, msg_data = mail.fetch(i, '(RFC822)')
            msg = email.message_from_bytes(msg_data[0][1])
            subjects.append(msg.get('subject', 'No Subject'))
        mail.logout()
        return "\n- ".join(subjects)
    except: return "Gmail sync pending..."

def get_biz_stats():
    old_data = {}
    if os.path.exists(STATS_CACHE):
        try:
            with open(STATS_CACHE, 'r') as f: 
                old_data = json.load(f).get('biz_data', {})
        except: pass

    stats = {"yt": "Offline", "patreon": 0, "comments": "None.", "new_member_alert": False}
    try:
        y_url = f"https://www.googleapis.com/youtube/v3/channels?part=statistics&id={YT_CH_ID}&key={YT_KEY}"
        stats['yt'] = requests.get(y_url, timeout=5).json()['items'][0]['statistics']['subscriberCount']

        headers = {"Authorization": f"Bearer {PATREON_TOKEN}"}
        p_url = f"https://www.patreon.com/api/campaigns/{PATREON_ID}?include=recent_comments"
        p_res = requests.get(p_url, headers=headers, timeout=5).json()
        stats['patreon'] = p_res['data']['attributes']['patron_count']

        if int(stats['patreon']) > int(old_data.get('patreon', 0)):
            stats['new_member_alert'] = True

        if 'included' in p_res:
            stats['comments'] = "\n- ".join([c['attributes']['body'] for c in p_res['included'] if c['type'] == 'comment'][:3])
    except: pass

    set_cache_val("biz_data", stats)
    return stats

def get_finances():
    cached = get_cache_val("bank_data", 43200)
    if cached: return cached
    try:
        cert = (os.path.expanduser("~/.teller/cert.pem"), os.path.expanduser("~/.teller/key.pem"))
        b_res = requests.get(f"https://api.teller.io/accounts/{TELLER_ACCOUNT_ID}/balances", auth=(TELLER_TOKEN, ''), cert=cert, timeout=5).json()
        t_res = requests.get(f"https://api.teller.io/accounts/{TELLER_ACCOUNT_ID}/transactions", auth=(TELLER_TOKEN, ''), cert=cert, timeout=5).json()
        txns = "\n- ".join([f"{t['description']} ({t['amount']})" for t in t_res[:3]])
        info = f"Balance: ${b_res['available']}\nRecent: {txns}"
        set_cache_val("bank_data", info)
        return info
    except: return "Bank sync pending..."

def get_health():
    health_dir_cfg = _cfg_get("HEALTH_DIR", "")
    if health_dir_cfg:
        HEALTH_DIR = os.path.expanduser(health_dir_cfg)
    else:
        # Default: Health Auto Export app via iCloud
        HEALTH_DIR = os.path.expanduser(
            "~/Library/Mobile Documents/iCloud~com~ifunography~HealthExport/Documents"
        )
        # Auto-detect subdirectory (user-named folder inside Documents)
        if os.path.isdir(HEALTH_DIR):
            subdirs = [d for d in os.listdir(HEALTH_DIR)
                       if os.path.isdir(os.path.join(HEALTH_DIR, d)) and not d.startswith('.')]
            if subdirs:
                HEALTH_DIR = os.path.join(HEALTH_DIR, subdirs[0])

    try:
        files = [os.path.join(HEALTH_DIR, f) for f in os.listdir(HEALTH_DIR) if f.endswith('.json')]
        if not files:
            return "Watch data offline."

        # Sort by filename (date-named), most recent first
        files_sorted = sorted(files, key=lambda p: os.path.basename(p), reverse=True)

        def load_metrics(path):
            with open(path, 'r') as f:
                d = json.load(f)
            data_node = d.get('data', {})
            if isinstance(data_node, list):
                return data_node[0].get('metrics', []) if data_node else []
            return data_node.get('metrics', [])

        def is_sparse(metrics):
            """Fewer than 2 meaningful metrics with actual data entries."""
            meaningful = [m for m in metrics
                          if m.get('name') in ('step_count', 'sleep_analysis',
                                               'heart_rate_variability', 'resting_heart_rate',
                                               'walking_running_distance', 'flights_climbed')
                          and m.get('data')]
            return len(meaningful) < 2

        # Try today's file; fall back to yesterday's if today is sparse
        metrics = load_metrics(files_sorted[0])
        used_file = files_sorted[0]
        is_yesterday = False
        if is_sparse(metrics) and len(files_sorted) > 1:
            metrics = load_metrics(files_sorted[1])
            used_file = files_sorted[1]
            is_yesterday = True

        def metric_total(name):
            """Sum all qty values for a metric across the day's hourly entries."""
            m = next((x for x in metrics if x.get('name') == name), None)
            if not m:
                return None
            total = sum(e.get('qty', 0) for e in m.get('data', []) if e.get('qty') is not None)
            return round(total, 1) if total else None

        def metric_latest(name):
            """Most recent single value for a metric (sleep, HRV, resting HR)."""
            m = next((x for x in metrics if x.get('name') == name), None)
            if not m:
                return None
            entries = m.get('data', [])
            if not entries:
                return None
            val = entries[-1].get('qty', entries[-1].get('value'))
            return round(val, 1) if val is not None else None

        parts = []

        steps = metric_total('step_count')
        if steps is not None:
            parts.append(f"Steps: {int(steps):,}")

        sleep = metric_latest('sleep_analysis')
        if sleep is not None:
            parts.append(f"Sleep: {sleep}h")

        hrv = metric_latest('heart_rate_variability')
        if hrv is not None:
            parts.append(f"HRV: {hrv}ms")

        rhr = metric_latest('resting_heart_rate')
        if rhr is not None:
            parts.append(f"RHR: {int(rhr)}bpm")

        if not parts:
            return "Watch data syncing..."

        result = " | ".join(parts)
        if is_yesterday:
            result += " (yesterday)"
        return result

    except Exception:
        return "Watch data offline."

# — HEARTBEAT WRITER —

def write_pulse_to_heartbeat(pulse_content, filepath, save_previous=False):
    """Write pulse data between the PULSE markers in the specified HEARTBEAT.md, preserving standing orders."""
    
    # Save previous pulse data for change detection
    if save_previous and os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                current = f.read()
            start_idx = current.find(PULSE_START)
            end_idx = current.find(PULSE_END)
            if start_idx != -1 and end_idx != -1:
                old_pulse = current[start_idx + len(PULSE_START):end_idx].strip()
                with open(PREVIOUS_PULSE_FILE, 'w', encoding='utf-8') as f:
                    f.write(old_pulse)
        except:
            pass

    # Read the current HEARTBEAT.md template
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            template = f.read()
    else:
        # If HEARTBEAT.md doesn't exist yet, create minimal structure
        template = (
            "# SILVIE'S NERVOUS SYSTEM\n\n"
            f"{PULSE_START}\n\n{PULSE_END}\n\n"
            "---\n\n"
            "# HEARTBEAT STANDING ORDERS\n\n"
            "*Standing orders not yet configured. Paste HEARTBEAT.md template into this file.*\n"
        )

    # Replace content between markers
    start_idx = template.find(PULSE_START)
    end_idx = template.find(PULSE_END)

    if start_idx != -1 and end_idx != -1:
        new_content = (
            template[:start_idx + len(PULSE_START)]
            + "\n"
            + pulse_content
            + "\n"
            + template[end_idx:]
        )
    else:
        # Markers missing — write pulse at top, warn
        new_content = (
            f"# SILVIE'S NERVOUS SYSTEM\n\n"
            f"{PULSE_START}\n"
            f"{pulse_content}\n"
            f"{PULSE_END}\n\n"
            f"---\n\n"
            f"⚠️ *Standing orders missing. Paste HEARTBEAT.md template.*\n"
        )

    # Make sure the target directory exists before writing
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)


# — THE PULSE —

def pulse():
    os.makedirs(WORKSPACE, exist_ok=True)
    os.makedirs(ENCHANTIFY_WORKSPACE, exist_ok=True)

    now = datetime.now()
    timestamp = now.strftime("%I:%M %p, %A %B %-d")
    weather = get_weather_raw()
    biz = get_biz_stats()

    # Alert flares
    alerts = []
    if biz['new_member_alert']:
        alerts.append("🔔 **FLARE: A new Doobaleedoo has joined the Clubhouse!**")
    alert_block = "\n".join(alerts) + "\n" if alerts else ""

    pulse_content = f"""## Pulse — {timestamp}

{alert_block}
### 🌍 The World Right Now

- **Belfast Feel:** {translate_weather_feel(weather)}
- **Forecast:** {get_weather_forecast()}
- **Season:** {get_real_season()}
- **Sun:** {get_sun_times()}
- **Moon:** {get_moon_phase()}
- **Tides:** {get_tides()}
- **Audio:** {get_spotify()}

### 💖 Founder Status (BJ)

- **Presence:** {get_presence()} | **Focus:** {get_focus_status()}
- **Pacing:** {get_quiet_status()}
- **Current Task:** {get_frontmost_app()}
- **Location:** {get_location_context()}
- **Watch:** {get_health()}
- **Fuel:** {get_fuel_summary()}

### 🖥️ System

- **M4 Vitals:** {get_system_vitals()}
- **Disk:** {subprocess.getoutput("df -h / | awk 'NR==2 {print $4}'")} free

### 📈 Business (The Doobaleedoos)

- **Patreon:** {biz['patreon']} members | **YouTube:** {biz['yt']} subs
- **Financials:**
  {get_finances()}
- **Inbox:**
  {get_gmail_subjects()}
- **Recent Clubhouse Comments:**
  {biz['comments']}

### 📅 Today

{get_calendar()}"""

    # Write pulse to enchantify HEARTBEAT.md and save previous pulse for change detection
    write_pulse_to_heartbeat(pulse_content, HEARTBEAT_FILE, save_previous=True)

if __name__ == "__main__":
    pulse()
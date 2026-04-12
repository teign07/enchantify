#!/bin/bash
# Enchantify — Heartbeat Update Script
# Fetches weather, sun, tides, and moon data and writes to player-heartbeat.md
# Runs hourly via cron. Works on Mac and Linux.
#
# Dependencies: curl, jq (both standard on Mac; `apt install jq` on Linux)
# Configuration: Set by installer in scripts/enchantify-config.sh

set -e

# ============================================================================
# Load Configuration
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/enchantify-config.sh"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERROR: enchantify-config.sh not found. Run the installer first."
    exit 1
fi

source "$CONFIG_FILE"

# Defaults if not set
LOCATION="${ENCHANTIFY_LOCATION:-Unknown}"
LAT="${ENCHANTIFY_LAT:-44.4260}"
LONG="${ENCHANTIFY_LONG:--69.0066}"
TIMEZONE="${ENCHANTIFY_TIMEZONE:-America/New_York}"
NOAA_STATION="${ENCHANTIFY_NOAA_STATION:-}"
HEMISPHERE="${ENCHANTIFY_HEMISPHERE:-north}"
S_WINTER="${ENCHANTIFY_S_WINTER:-Winter}"
S_SPRING="${ENCHANTIFY_S_SPRING:-Spring}"
S_SUMMER="${ENCHANTIFY_S_SUMMER:-Summer}"
S_AUTUMN="${ENCHANTIFY_S_AUTUMN:-Autumn}"
OUTPUT="${ENCHANTIFY_OUTPUT:-$HOME/.openclaw/workspace/enchantify/config/player-heartbeat.md}"

# ============================================================================
# Helper: Get Season
# ============================================================================

get_season() {
    local month=$(date +%m)

    case $month in
        12|01|02) echo "$S_WINTER" ;;
        03|04|05) echo "$S_SPRING" ;;
        06|07|08) echo "$S_SUMMER" ;;
        09|10|11) echo "$S_AUTUMN" ;;
        *) echo "Season of the Mist" ;;
    esac
}

# ============================================================================
# Helper: Beaufort Wind Description
# ============================================================================

wind_desc() {
    local kmh=$1
    if [[ $kmh -lt 2 ]]; then echo "calm"
    elif [[ $kmh -lt 12 ]]; then echo "light"
    elif [[ $kmh -lt 29 ]]; then echo "gentle"
    elif [[ $kmh -lt 50 ]]; then echo "moderate"
    elif [[ $kmh -lt 75 ]]; then echo "strong"
    else echo "gale"
    fi
}

# ============================================================================
# Fetch Weather (wttr.in — free, no API key)
# ============================================================================

WEATHER_JSON=$(curl -s --max-time 10 "wttr.in/${LOCATION}?format=j1" 2>/dev/null || echo "{}")

TEMP_C=$(echo "$WEATHER_JSON" | jq -r '.current_condition[0].temp_C // "?"' 2>/dev/null || echo "?")
TEMP_F=$(echo "$WEATHER_JSON" | jq -r '.current_condition[0].temp_F // "?"' 2>/dev/null || echo "?")
FEELS_C=$(echo "$WEATHER_JSON" | jq -r '.current_condition[0].FeelsLikeC // "?"' 2>/dev/null || echo "?")
FEELS_F=$(echo "$WEATHER_JSON" | jq -r '.current_condition[0].FeelsLikeF // "?"' 2>/dev/null || echo "?")
CONDITION=$(echo "$WEATHER_JSON" | jq -r '.current_condition[0].weatherDesc[0].value // "Unknown"' 2>/dev/null || echo "Unknown")
HUMIDITY=$(echo "$WEATHER_JSON" | jq -r '.current_condition[0].humidity // "?"' 2>/dev/null || echo "?")
WIND_KMH=$(echo "$WEATHER_JSON" | jq -r '.current_condition[0].windspeedKmph // "0"' 2>/dev/null || echo "0")
WIND_MPH=$(echo "$WEATHER_JSON" | jq -r '.current_condition[0].windspeedMiles // "0"' 2>/dev/null || echo "0")
WIND_DIR=$(echo "$WEATHER_JSON" | jq -r '.current_condition[0].winddir16Point // "?"' 2>/dev/null || echo "?")
PRESSURE=$(echo "$WEATHER_JSON" | jq -r '.current_condition[0].pressure // "?"' 2>/dev/null || echo "?")
VISIBILITY=$(echo "$WEATHER_JSON" | jq -r '.current_condition[0].visibility // "?"' 2>/dev/null || echo "?")

WIND_QUALITY=$(wind_desc "${WIND_KMH:-0}")

# ============================================================================
# Fetch Sun Data (sunrise-sunset.org — free, no API key)
# ============================================================================

SUN_JSON=$(curl -s --max-time 10 "https://api.sunrise-sunset.org/json?lat=${LAT}&lng=${LONG}&date=today&formatted=0" 2>/dev/null || echo "{}")

# Times come back as UTC ISO strings; convert to local
SUNRISE_UTC=$(echo "$SUN_JSON" | jq -r '.results.sunrise // ""' 2>/dev/null || echo "")
SUNSET_UTC=$(echo "$SUN_JSON" | jq -r '.results.sunset // ""' 2>/dev/null || echo "")
SOLAR_NOON_UTC=$(echo "$SUN_JSON" | jq -r '.results.solar_noon // ""' 2>/dev/null || echo "")
DAY_LENGTH=$(echo "$SUN_JSON" | jq -r '.results.day_length // ""' 2>/dev/null || echo "")

# Convert UTC to local time
if [ -n "$SUNRISE_UTC" ] && command -v TZ &>/dev/null || true; then
    SUNRISE_LOCAL=$(TZ="$TIMEZONE" date -d "$SUNRISE_UTC" "+%I:%M %p" 2>/dev/null || \
                    TZ="$TIMEZONE" date -jf "%Y-%m-%dT%H:%M:%S+00:00" "$SUNRISE_UTC" "+%I:%M %p" 2>/dev/null || \
                    echo "$SUNRISE_UTC")
    SUNSET_LOCAL=$(TZ="$TIMEZONE" date -d "$SUNSET_UTC" "+%I:%M %p" 2>/dev/null || \
                   TZ="$TIMEZONE" date -jf "%Y-%m-%dT%H:%M:%S+00:00" "$SUNSET_UTC" "+%I:%M %p" 2>/dev/null || \
                   echo "$SUNSET_UTC")
else
    SUNRISE_LOCAL="${SUNRISE_UTC:-6:00 AM}"
    SUNSET_LOCAL="${SUNSET_UTC:-7:00 PM}"
fi

# ============================================================================
# Fetch Moon Phase (farmsense.net — free, no API key, astronomically accurate)
# ============================================================================

UNIX_NOW=$(date +%s)
MOON_JSON=$(curl -s --max-time 10 "https://api.farmsense.net/v1/moonphases/?d=${UNIX_NOW}" 2>/dev/null || echo "[]")

MOON_PHASE_NAME=$(echo "$MOON_JSON" | jq -r '.[0].Phase // ""' 2>/dev/null || echo "")
MOON_ILLUMINATION=$(echo "$MOON_JSON" | jq -r '.[0].Illumination // ""' 2>/dev/null || echo "")
MOON_AGE=$(echo "$MOON_JSON" | jq -r '.[0].Age // ""' 2>/dev/null || echo "")

# Fallback: use moonphase.co API if farmsense fails
if [ -z "$MOON_PHASE_NAME" ]; then
    MOON_JSON2=$(curl -s --max-time 10 "https://api.weatherapi.com/v1/astronomy.json?key=free&q=${LAT},${LONG}&dt=$(date +%Y-%m-%d)" 2>/dev/null || echo "{}")
    MOON_PHASE_NAME=$(echo "$MOON_JSON2" | jq -r '.astronomy.astro.moon_phase // "Unknown"' 2>/dev/null || echo "Unknown")
    MOON_ILLUMINATION=$(echo "$MOON_JSON2" | jq -r '.astronomy.astro.moon_illumination // "?"' 2>/dev/null || echo "?")
fi

# Emoji mapping
case "$MOON_PHASE_NAME" in
    *"New Moon"*)        MOON_EMOJI="🌑" ;;
    *"Waxing Crescent"*) MOON_EMOJI="🌒" ;;
    *"First Quarter"*)   MOON_EMOJI="🌓" ;;
    *"Waxing Gibbous"*)  MOON_EMOJI="🌔" ;;
    *"Full Moon"*)       MOON_EMOJI="🌕" ;;
    *"Waning Gibbous"*)  MOON_EMOJI="🌖" ;;
    *"Last Quarter"*)    MOON_EMOJI="🌗" ;;
    *"Waning Crescent"*) MOON_EMOJI="🌘" ;;
    *)                   MOON_EMOJI="🌙" ;;
esac

# ============================================================================
# Fetch Tides (NOAA — free, US coastal only)
# ============================================================================

TIDE_STATUS=""
TIDE_NEXT_HIGH=""
TIDE_NEXT_LOW=""
TIDE_CURRENT_HEIGHT=""
TIDE_DIRECTION=""

if [ -n "$NOAA_STATION" ]; then
    TODAY=$(date +%Y%m%d)
    TIDE_JSON=$(curl -s --max-time 10 \
        "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?begin_date=${TODAY}&end_date=${TODAY}&station=${NOAA_STATION}&product=predictions&datum=MLLW&time_zone=lst_ldt&interval=hilo&units=english&application=enchantify&format=json" \
        2>/dev/null || echo "{}")

    # Parse hi/lo predictions
    TIDE_HIGHS=$(echo "$TIDE_JSON" | jq -r '.predictions[] | select(.type=="H") | "\(.t) \(.v)ft"' 2>/dev/null || echo "")
    TIDE_LOWS=$(echo "$TIDE_JSON" | jq -r '.predictions[] | select(.type=="L") | "\(.t) \(.v)ft"' 2>/dev/null || echo "")

    CURRENT_HOUR=$(date +"%Y-%m-%d %H")
    TIDE_NEXT_HIGH=$(echo "$TIDE_HIGHS" | awk -v now="$CURRENT_HOUR" '$0 > now {print; exit}')
    TIDE_NEXT_LOW=$(echo "$TIDE_LOWS" | awk -v now="$CURRENT_HOUR" '$0 > now {print; exit}')

    # Determine incoming vs outgoing by comparing current time to last high/low
    LAST_HIGH=$(echo "$TIDE_HIGHS" | awk -v now="$CURRENT_HOUR" '$0 <= now {last=$0} END {print last}')
    LAST_LOW=$(echo "$TIDE_LOWS" | awk -v now="$CURRENT_HOUR" '$0 <= now {last=$0} END {print last}')

    if [[ "$LAST_HIGH" > "$LAST_LOW" ]]; then
        TIDE_DIRECTION="going out"
    else
        TIDE_DIRECTION="coming in"
    fi

    TIDE_STATUS="Active (NOAA station ${NOAA_STATION})"
else
    TIDE_STATUS="Not configured"
fi

# ============================================================================
# Get Season
# ============================================================================

SEASON=$(get_season)

# ============================================================================
# Fetch optional integrations
# ============================================================================

# --- Spotify (macOS AppleScript) ---
SPOTIFY_LINE="*Not configured.*"
if [[ "${ENCHANTIFY_ENABLE_SPOTIFY}" == "yes" ]] && [[ "$OSTYPE" == "darwin"* ]]; then
    SPOTIFY_STATE=$(osascript -e 'tell application "Spotify" to get player state' 2>/dev/null || echo "stopped")
    if [[ "$SPOTIFY_STATE" == "playing" ]]; then
        SP_TRACK=$(osascript -e 'tell application "Spotify" to get name of current track' 2>/dev/null || echo "")
        SP_ARTIST=$(osascript -e 'tell application "Spotify" to get artist of current track' 2>/dev/null || echo "")
        if [ -n "$SP_TRACK" ]; then
            SPOTIFY_LINE="${SP_TRACK} by ${SP_ARTIST}"
        else
            SPOTIFY_LINE="Playing (track info unavailable)"
        fi
    elif [[ "$SPOTIFY_STATE" == "paused" ]]; then
        SP_TRACK=$(osascript -e 'tell application "Spotify" to get name of current track' 2>/dev/null || echo "")
        SP_ARTIST=$(osascript -e 'tell application "Spotify" to get artist of current track' 2>/dev/null || echo "")
        SPOTIFY_LINE="Paused: ${SP_TRACK} by ${SP_ARTIST}"
    else
        SPOTIFY_LINE="Not playing"
    fi
fi

# --- Fuel Gauge ---
FUEL_SECTION="*Not configured.*"
FUEL_LOG="${SCRIPT_DIR}/fuel-log.txt"
if [[ "${ENCHANTIFY_ENABLE_FUEL}" == "yes" ]]; then
    if [ -f "$FUEL_LOG" ] && [ -s "$FUEL_LOG" ]; then
        # Read last few entries (file is append-only, one entry per line: timestamp|description|cal|protein)
        LAST_ENTRY=$(tail -1 "$FUEL_LOG")
        LAST_TIME=$(echo "$LAST_ENTRY" | cut -d'|' -f1)
        LAST_DESC=$(echo "$LAST_ENTRY" | cut -d'|' -f2)
        LAST_CAL=$(echo "$LAST_ENTRY" | cut -d'|' -f3)
        LAST_PROT=$(echo "$LAST_ENTRY" | cut -d'|' -f4)

        # Sum today's calories and protein
        TODAY_DATE=$(date +"%Y-%m-%d")
        TODAY_CAL=$(grep "^${TODAY_DATE}" "$FUEL_LOG" 2>/dev/null | awk -F'|' '{sum += $3} END {print int(sum)}' || echo "0")
        TODAY_PROT=$(grep "^${TODAY_DATE}" "$FUEL_LOG" 2>/dev/null | awk -F'|' '{sum += $4} END {print int(sum)}' || echo "0")
        TODAY_MEALS=$(grep -c "^${TODAY_DATE}" "$FUEL_LOG" 2>/dev/null || echo "0")

        # Status note
        if [[ "$TODAY_PROT" -lt 30 ]]; then
            FUEL_STATUS="Low protein — something substantial would help."
        elif [[ "$TODAY_CAL" -lt 500 ]]; then
            FUEL_STATUS="Light day — consider a proper meal."
        else
            FUEL_STATUS="OK"
        fi

        FUEL_SECTION="- **Last Logged:** ${LAST_TIME} (${LAST_DESC})
- **Today:** ~${TODAY_CAL} Cal / ~${TODAY_PROT}g protein (${TODAY_MEALS} entries)
- **Status:** ${FUEL_STATUS}"
    else
        FUEL_SECTION="- **Today:** Nothing logged yet.
- **Status:** Log food by telling your agent what you ate.
- *(Example: 'log fuel: coffee and oatmeal, about 300 cal')*"
    fi
fi

# --- Steps (macOS Shortcuts → Apple Health) ---
STEPS_LINE="*Not configured.*"
if [[ "${ENCHANTIFY_ENABLE_STEPS}" == "yes" ]] && [[ "$OSTYPE" == "darwin"* ]]; then
    # Try to read steps via a Shortcuts shortcut named "Get Steps Today"
    # Player needs to create this shortcut; installer notes it
    STEPS_RAW=$(shortcuts run "Get Steps Today" 2>/dev/null || echo "")
    if [ -n "$STEPS_RAW" ] && [[ "$STEPS_RAW" =~ ^[0-9]+$ ]]; then
        STEPS_LINE="${STEPS_RAW} steps today"
    else
        STEPS_LINE="Watch offline or shortcut not configured (see docs/steps-setup.md)"
    fi
fi

# --- Guild Wars 2 ---
GW2_LINE="*Not configured.*"
if [[ "${ENCHANTIFY_ENABLE_GW2}" == "yes" ]] && [ -n "${ENCHANTIFY_GW2_API_KEY}" ]; then
    GW2_ACCOUNT=$(curl -s --max-time 8 \
        -H "Authorization: Bearer ${ENCHANTIFY_GW2_API_KEY}" \
        "https://api.guildwars2.com/v2/account" 2>/dev/null || echo "{}")
    GW2_NAME=$(echo "$GW2_ACCOUNT" | jq -r '.name // ""' 2>/dev/null || echo "")

    if [ -n "$GW2_NAME" ]; then
        # Daily AP check
        GW2_DAILY=$(curl -s --max-time 8 \
            -H "Authorization: Bearer ${ENCHANTIFY_GW2_API_KEY}" \
            "https://api.guildwars2.com/v2/account/dailycrafting" 2>/dev/null | \
            jq 'length // 0' 2>/dev/null || echo "?")

        # Check if currently in a map (last session won't tell us live status, but wallet changes will)
        GW2_LINE="${GW2_NAME} | Daily AP tracked"
    else
        GW2_LINE="API key configured but account not reachable (check key permissions)"
    fi
fi

# --- Sparky Shinies ---
# Two modes:
#   "heartbeat" — Sparky writes directly into a source HEARTBEAT.md (Silvie/shared installs)
#   "files"     — Sparky writes to sparky/shinies/*.md (standalone installs)
# ENCHANTIFY_SPARKY_SOURCE can be set to a path to override; defaults to file-based.

SPARKY_LINE="*Not configured.*"
if [[ "${ENCHANTIFY_ENABLE_SPARKY}" == "yes" ]]; then
    if [ -n "${ENCHANTIFY_SPARKY_SOURCE}" ] && [ -f "${ENCHANTIFY_SPARKY_SOURCE}" ]; then
        # Extract the ### 🌟 Sparky Says section from the source heartbeat
        SPARKY_LINE=$(awk '/^### 🌟 Sparky Says/{found=1; next} found && /^###/{exit} found{print}' \
            "${ENCHANTIFY_SPARKY_SOURCE}" | head -12 | sed '/^[[:space:]]*$/d' | tr '\n' ' ')
        if [ -z "$SPARKY_LINE" ]; then
            SPARKY_LINE="*(No shiny yet today)*"
        fi
    else
        # File-based mode: read from sparky/shinies/
        SPARKY_DIR="$(dirname "$SCRIPT_DIR")/sparky/shinies"
        TODAY_DATE=$(date +"%Y-%m-%d")
        LATEST_SHINY=$(ls -t "${SPARKY_DIR}/${TODAY_DATE}"*.md 2>/dev/null | head -1)
        if [ -n "$LATEST_SHINY" ]; then
            SHINY_CONTENT=$(cat "$LATEST_SHINY" 2>/dev/null | head -10 | tr '\n' ' ')
            SHINY_TIME=$(basename "$LATEST_SHINY" .md | cut -d'-' -f4-)
            SPARKY_LINE="**LATEST SHINY! (${SHINY_TIME})** ${SHINY_CONTENT}"
        else
            ANY_SHINY=$(ls -t "${SPARKY_DIR}"/*.md 2>/dev/null | head -1)
            if [ -n "$ANY_SHINY" ]; then
                SHINY_CONTENT=$(cat "$ANY_SHINY" 2>/dev/null | head -10 | tr '\n' ' ')
                SPARKY_LINE="*(No shiny yet today)* — Last: ${SHINY_CONTENT}"
            else
                SPARKY_LINE="Active — first shiny pending next cron run (8am)."
            fi
        fi
    fi
fi

# ============================================================================
# Write Heartbeat File
# ============================================================================

TIMESTAMP=$(date +"%Y-%m-%d %H:%M %Z")
NEXT_UPDATE=$(date -v+1H +"%H:%M %Z" 2>/dev/null || date -d "+1 hour" +"%H:%M %Z" 2>/dev/null || echo "next hour")

mkdir -p "$(dirname "$OUTPUT")"

cat > "$OUTPUT" << HEARTBEAT_EOF
# Player Heartbeat — Enchantify

*Updated: ${TIMESTAMP} — next update ~${NEXT_UPDATE}*

---

## 📍 Location

**Place:** ${LOCATION}
**Coordinates:** ${LAT}, ${LONG}
**Timezone:** ${TIMEZONE}

---

## 🌤 Weather

**Condition:** ${CONDITION}
**Temperature:** ${TEMP_F}°F / ${TEMP_C}°C
**Feels Like:** ${FEELS_F}°F / ${FEELS_C}°C
**Humidity:** ${HUMIDITY}%
**Wind:** ${WIND_MPH} mph ${WIND_DIR} (${WIND_QUALITY})
**Pressure:** ${PRESSURE} mb
**Visibility:** ${VISIBILITY} km

---

## ☀️ Sun

**Sunrise:** ${SUNRISE_LOCAL}
**Sunset:** ${SUNSET_LOCAL}
**Day Length:** ${DAY_LENGTH}

---

## ${MOON_EMOJI} Moon

**Phase:** ${MOON_PHASE_NAME}
**Illumination:** ${MOON_ILLUMINATION}%
**Age:** ${MOON_AGE} days

---

## 🌊 Tides

**Status:** ${TIDE_STATUS}
**Direction:** ${TIDE_DIRECTION}
**Next High:** ${TIDE_NEXT_HIGH}
**Next Low:** ${TIDE_NEXT_LOW}

---

## 🌿 Season

**Season:** ${SEASON}

---

## 🎵 Audio

${SPOTIFY_LINE}

---

## 🥗 Fuel Gauge

${FUEL_SECTION}

---

## 👟 Movement

${STEPS_LINE}

---

## 🎮 Guild Wars 2

${GW2_LINE}

---

## ✨ Sparky Shinies

${SPARKY_LINE}

---

*Enchantify Heartbeat v2.0 — update-weather.sh*
HEARTBEAT_EOF

echo "✓ Heartbeat updated for ${LOCATION} at ${TIMESTAMP}"
echo "  Weather: ${CONDITION}, ${TEMP_F}°F (feels ${FEELS_F}°F)"
echo "  Moon: ${MOON_EMOJI} ${MOON_PHASE_NAME} ${MOON_ILLUMINATION}%"
echo "  Season: ${SEASON}"
if [ -n "$NOAA_STATION" ]; then
    echo "  Tides: ${TIDE_DIRECTION}, next high ${TIDE_NEXT_HIGH}"
fi

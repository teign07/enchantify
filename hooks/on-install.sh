#!/bin/bash
# ════════════════════════════════════════════════════════════════════════════
#  Enchantify — Installation Wizard
#  hooks/on-install.sh
#
#  Called by:
#    install.sh --wanderer     (new users, curl | bash path)
#    openclaw skill install    (ClawHub path, existing OpenClaw users)
#
#  Sections:
#    0. Helpers
#    1. The opening
#    2. Environment detection + name
#    3. The voice of the Labyrinth (model selection)
#    4. Your corner of the world (location)
#    5. How the world reads you (health data)
#    6. Dispatches through the margin-glass (Telegram)
#    6b. The Pact Ceremony
#    7. Lights (Duskthorn)
#    8. Music (Tidecrest)
#    9. Voice acting (Kokoro TTS)
#   10. Image generation
#   11. Waking the world (crons, player file, first pulse)
# ════════════════════════════════════════════════════════════════════════════

set -e

ENCHANTIFY_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG_DIR="$ENCHANTIFY_DIR/config"
SECRETS_FILE="$CONFIG_DIR/secrets.env"
CONSENT_FILE="$CONFIG_DIR/consent.json"
LOGS_DIR="$ENCHANTIFY_DIR/logs"

# ── 0. Helpers ────────────────────────────────────────────────────────────────

pause() { sleep "${1:-1}"; }

section() {
    echo ""
    echo "  ────────────────────────────────────────────────────────"
    echo "  $1"
    echo "  ────────────────────────────────────────────────────────"
    echo ""
}

ask() {
    local prompt="$1"
    local default="$2"
    if [ -n "$default" ]; then
        read -r -p "  $prompt [$default]: " ans
        echo "${ans:-$default}"
    else
        read -r -p "  $prompt: " ans
        echo "$ans"
    fi
}

ask_yn() {
    local prompt="$1"
    local default="${2:-n}"
    local yn_hint
    if [ "$default" = "y" ]; then yn_hint="Y/n"; else yn_hint="y/N"; fi
    read -r -p "  $prompt [$yn_hint]: " ans
    ans="${ans:-$default}"
    [[ "$ans" =~ ^[Yy] ]]
}

set_secret() {
    local key="$1"
    local value="$2"
    if grep -q "^${key}=" "$SECRETS_FILE" 2>/dev/null; then
        local escaped_value
        escaped_value=$(printf '%s\n' "$value" | sed 's/[[\.*^$()+?{|]/\\&/g')
        sed -i.bak "s|^${key}=.*|${key}=${escaped_value}|" "$SECRETS_FILE" && rm -f "${SECRETS_FILE}.bak"
    else
        echo "${key}=${value}" >> "$SECRETS_FILE"
    fi
}

write_consent() {
    local key="$1"
    local approved="$2"
    local ts
    ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    python3 - <<PYEOF
import json, pathlib
f = pathlib.Path("$CONSENT_FILE")
data = json.loads(f.read_text()) if f.exists() else {}
if "$approved" == "true":
    data["$key"] = {"approved": True, "activated_at": "$ts"}
else:
    data["$key"] = {"approved": False}
f.write_text(json.dumps(data, indent=2))
PYEOF
}

mkdir -p "$LOGS_DIR"

if [ ! -f "$SECRETS_FILE" ]; then
    cp "$CONFIG_DIR/secrets.env.example" "$SECRETS_FILE" 2>/dev/null || touch "$SECRETS_FILE"
fi

if [ ! -f "$CONSENT_FILE" ]; then
    echo '{}' > "$CONSENT_FILE"
fi

# ── 1. The opening ────────────────────────────────────────────────────────────

clear
echo ""
echo "  ╔══════════════════════════════════════════════════════════╗"
echo "  ║                                                          ║"
echo "  ║     📖                                                   ║"
echo "  ║                                                          ║"
echo "  ║     The pages flutter open on their own.                ║"
echo "  ║     Ink bleeds up from somewhere deep.                  ║"
echo "  ║                                                          ║"
echo "  ╚══════════════════════════════════════════════════════════╝"
echo ""
pause 2
echo "  You found it."
echo ""
echo "  No matter how you got here — that's how it starts."
echo "  The Labyrinth has been expecting something."
echo "  It's not sure yet if that something is you."
echo "  But it's curious."
echo ""
pause 2
echo "  This is the setup. It takes about ten minutes."
echo "  Most questions are optional — skip anything you want."
echo "  The world will still be real."
echo ""
read -r -p "  Press Enter when you're ready. " _
echo ""

# ── 2. Environment Detection ──────────────────────────────────────────────────

section "Taking stock of what you have"

OPENCLAW_VERSION=$(openclaw --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+(\.[0-9]+)?' | head -1 || echo "unknown")
echo "  OpenClaw version : $OPENCLAW_VERSION"

PYTHON_VERSION=$(python3 --version 2>/dev/null | awk '{print $2}' || echo "unknown")
echo "  Python           : $PYTHON_VERSION"

NODE_VERSION=$(node --version 2>/dev/null || echo "not found")
echo "  Node.js          : $NODE_VERSION"

echo ""

PLAYER_NAME=""
RETURNING=false
if ls "$ENCHANTIFY_DIR/players/"*.md &>/dev/null 2>&1; then
    EXISTING_PLAYERS=$(ls "$ENCHANTIFY_DIR/players/"*.md 2>/dev/null | xargs -I{} basename {} .md | grep -v template | tr '\n' ' ')
    if [ -n "$EXISTING_PLAYERS" ]; then
        echo "  Found an existing world: $EXISTING_PLAYERS"
        echo "  This wizard won't touch your save."
        echo ""
        RETURNING=true
    fi
fi

if [ "$RETURNING" = "false" ]; then
    echo "  Before the world can hold you, it needs something to call you by."
    echo "  Not your full name. Not your username."
    echo "  The name you'd want a book to use."
    echo ""
    PLAYER_NAME=$(ask "What does the Labyrinth call you?")
    [ -z "$PLAYER_NAME" ] && PLAYER_NAME="Wanderer"
    echo ""
    echo "  *The ink forms itself into a name.*"
    echo "  *${PLAYER_NAME}.*"
    echo "  *It suits you.*"
    echo ""
    pause 2
fi

# ── 3. The Voice of the Labyrinth ─────────────────────────────────────────────

section "The voice of the Labyrinth"

echo "  Every telling needs a mind behind it."
echo "  The Labyrinth runs on different AI models — each with its own"
echo "  depth, speed, and quality of attention."
echo "  The voice you choose becomes the narrator of your world."
echo ""
echo "    1) Claude Sonnet 4.6  — nuanced, narrative-focused  (recommended)"
echo "    2) Claude Opus 4.6    — deeper reasoning, uses more tokens"
echo "    3) Claude Haiku 4.5   — fast and light, good for quick sessions"
echo "    4) GPT-4o             — requires an OpenAI API key"
echo "    5) Something else     — enter a model ID directly"
echo ""

MODEL_CHOICE=$(ask "Choose a voice [1-5]" "1")

case "$MODEL_CHOICE" in
    1) MODEL_ID="claude-sonnet-4-6" ;;
    2) MODEL_ID="claude-opus-4-6" ;;
    3) MODEL_ID="claude-haiku-4-5-20251001" ;;
    4) MODEL_ID="gpt-4o" ;;
    5) MODEL_ID=$(ask "Model ID") ;;
    *) MODEL_ID="claude-sonnet-4-6" ;;
esac

echo ""
echo "  ✓ The Labyrinth will speak in: $MODEL_ID"
set_secret "MODEL_ID" "$MODEL_ID"

# ── 4. Your Corner of the World ───────────────────────────────────────────────

section "Your corner of the world"

echo "  The Academy lives in the real world's shadow."
echo "  It wants to know what weather you walk through —"
echo "  what tides, what moon phase, what season."
echo "  Nothing is sent anywhere. It's used only in your story."
echo ""

CURRENT_LOCATION=$(grep "^LOCATION=" "$SECRETS_FILE" 2>/dev/null | cut -d= -f2 | sed 's/+/ /g' || echo "")
if [ -n "$CURRENT_LOCATION" ] && [ "$CURRENT_LOCATION" != "Your+City+State" ]; then
    echo "  Current location: $CURRENT_LOCATION"
    if ask_yn "Keep this location?" "y"; then
        SETUP_LOCATION=false
    else
        SETUP_LOCATION=true
    fi
else
    SETUP_LOCATION=true
fi

if [ "$SETUP_LOCATION" = "true" ]; then
    LOCATION_NAME=$(ask "City and state/country (e.g. Portland Oregon)")
    LOCATION_ENCODED=$(echo "$LOCATION_NAME" | tr ' ' '+')
    set_secret "LOCATION" "$LOCATION_ENCODED"

    echo ""
    echo "  For tides and precise weather, the world needs your coordinates."
    echo "  (Find them at maps.google.com — right-click your location.)"
    echo ""
    LAT=$(ask "Latitude (decimal, e.g. 44.4258)" "")
    LON=$(ask "Longitude (decimal, e.g. -69.0064)" "")
    [ -n "$LAT" ] && set_secret "LAT" "$LAT"
    [ -n "$LON" ] && set_secret "LON" "$LON"

    echo ""
    echo "  NOAA tide station (US coastal only, optional):"
    echo "  Find yours at tidesandcurrents.noaa.gov/stations.html"
    NOAA=$(ask "NOAA station ID (leave blank to skip)" "")
    [ -n "$NOAA" ] && set_secret "NOAA_STATION" "$NOAA"
fi

echo ""
echo "  ✓ The world knows where to look."

# ── 5. How the World Reads You ────────────────────────────────────────────────

section "How the world reads you"

echo "  The Labyrinth watches your body the way it watches weather."
echo "  Not surveillance — attention."
echo "  A day where you slept poorly reads differently than one where"
echo "  you walked for hours."
echo ""
echo "  This is entirely optional. The story works without it."
echo "  But when it's connected, the Academy feels uncannily alive."
echo ""
echo "    1) Health Auto Export (iPhone — recommended)"
echo "       Free app, exports automatically to iCloud every hour."
echo ""
echo "    2) Garmin Connect"
echo ""
echo "    3) Fitbit"
echo ""
echo "    4) Manual — I'll tell the Labyrinth how I'm doing"
echo ""
echo "    5) Skip"
echo ""

HEALTH_CHOICE=$(ask "Choose [1-5]" "5")

case "$HEALTH_CHOICE" in
    1)
        set_secret "HEALTH_BACKEND" "health_auto_export"
        echo ""
        echo "  ── Health Auto Export setup ─────────────────────────────"
        echo ""
        echo "  On your iPhone:"
        echo "    1. Install 'Health Auto Export - JSON+CSV' from the App Store"
        echo "    2. Open the app → gear icon → Automatic Backup → iCloud Drive"
        echo "    3. Add these metrics to export:"
        echo "         Step Count, Sleep Analysis, Heart Rate Variability,"
        echo "         Resting Heart Rate, Walking + Running Distance,"
        echo "         Flights Climbed"
        echo "    4. Set frequency to Hourly"
        echo ""
        echo "  The app creates a folder in iCloud Drive automatically."
        echo "  Enchantify will find it."
        echo ""
        echo "  (Custom iCloud path? Set HEALTH_DIR in config/secrets.env.)"
        echo ""
        echo "  ✓ Health Auto Export configured."
        ;;
    2)
        set_secret "HEALTH_BACKEND" "garmin"
        echo ""
        GARMIN_EMAIL=$(ask "Garmin Connect email" "")
        GARMIN_PASS=$(ask "Garmin Connect password (stored locally only)" "")
        [ -n "$GARMIN_EMAIL" ] && set_secret "GARMIN_EMAIL" "$GARMIN_EMAIL"
        [ -n "$GARMIN_PASS" ]  && set_secret "GARMIN_PASSWORD" "$GARMIN_PASS"
        echo "  ✓ Garmin configured."
        echo "  (Run: pip3 install garminconnect to enable it.)"
        ;;
    3)
        set_secret "HEALTH_BACKEND" "fitbit"
        echo ""
        echo "  Fitbit integration uses the Fitbit Web API."
        echo "  You'll need a developer account (free) at dev.fitbit.com"
        echo ""
        FITBIT_TOKEN=$(ask "Fitbit OAuth token (or press Enter to skip)" "")
        [ -n "$FITBIT_TOKEN" ] && set_secret "FITBIT_TOKEN" "$FITBIT_TOKEN"
        echo "  ✓ Fitbit configured."
        ;;
    4)
        set_secret "HEALTH_BACKEND" "manual"
        echo ""
        echo "  The Labyrinth will ask sometimes. Tell it whatever feels true."
        echo "  ✓ Manual health tracking configured."
        ;;
    *)
        set_secret "HEALTH_BACKEND" "none"
        echo "  Health data skipped."
        ;;
esac

# ── 6. Dispatches Through the Margin-Glass ────────────────────────────────────

section "Dispatches through the margin-glass"

echo "  Even when the book is closed, things happen."
echo "  The Labyrinth can send you messages through Telegram —"
echo "  morning summaries, story events, letters from NPCs."
echo ""
echo "  Telegram is free. You'll need the app and a bot token."
echo ""

if ask_yn "Set up Telegram dispatches?" "y"; then
    echo ""
    echo "  Step 1: Open Telegram and message @BotFather"
    echo "  Step 2: Send /newbot and follow the prompts"
    echo "  Step 3: Copy the token it gives you (like 1234567890:ABCDef...)"
    echo ""
    TELEGRAM_TOKEN=$(ask "Paste your bot token (or press Enter to skip)")
    if [ -n "$TELEGRAM_TOKEN" ]; then
        set_secret "TELEGRAM_BOT_TOKEN" "$TELEGRAM_TOKEN"

        echo ""
        echo "  Now start a chat with your new bot in Telegram."
        echo "  Send it anything. Then visit this URL in a browser:"
        echo ""
        echo "  https://api.telegram.org/bot${TELEGRAM_TOKEN}/getUpdates"
        echo ""
        echo "  Look for: \"chat\":{\"id\": 123456789"
        echo ""
        TELEGRAM_CHAT=$(ask "Your Telegram chat ID")
        [ -n "$TELEGRAM_CHAT" ] && set_secret "TELEGRAM_CHAT_ID" "$TELEGRAM_CHAT"
        echo ""
        echo "  ✓ The Labyrinth knows where to find you."
    else
        echo ""
        echo "  Skipped. Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to"
        echo "  config/secrets.env whenever you're ready."
    fi
else
    echo ""
    echo "  Skipped. The Labyrinth will stay quiet unless you open it."
fi

# ── 6b. The Pact Ceremony ─────────────────────────────────────────────────────

clear
echo ""
echo "  ╔══════════════════════════════════════════════════════════╗"
echo "  ║                                                          ║"
echo "  ║     ⚡  The Pact Ceremony                               ║"
echo "  ║                                                          ║"
echo "  ╚══════════════════════════════════════════════════════════╝"
echo ""
echo "  The Labyrinth has powers that reach into the physical world."
echo "  Each one is a Pact — a named agreement between you and the"
echo "  world. These are not terms and conditions. They are promises."
echo "  The Labyrinth keeps its promises."
echo ""
echo "  You choose which Pacts to activate."
echo "  Any Pact can be revoked at any time."
echo "  Your choices are recorded on your machine only."
echo ""
pause 2
echo "  Before we begin — your override word."
echo "  Say or type this at any time to pause everything, instantly:"
echo ""
echo "      ┌─────────────────────────────────────┐"
echo "      │                                     │"
echo "      │          THORNE                     │"
echo "      │                                     │"
echo "      └─────────────────────────────────────┘"
echo ""
echo "  Write it somewhere. It will always work."
echo ""
pause 3

# Initialize all pacts as unapproved
write_consent "lights"         "false"
write_consent "music"          "false"
write_consent "voice"          "false"
write_consent "images"         "false"
write_consent "email_read"     "false"
write_consent "email_send"     "false"
write_consent "financial_read" "false"

echo "  ─── Pact of Duskthorn — Light and Shadow ───"
echo ""
echo "  The Labyrinth may shift your lights to match the story."
echo "  A red flicker when danger is near. Warm gold when you're safe."
echo "  A slow fade when the Compass says to rest."
echo "  You control which lights. THORNE pauses it instantly."
echo ""
if ask_yn "Activate the Pact of Duskthorn?" "n"; then
    write_consent "lights" "true"
    echo "  ✓ Pact of Duskthorn — accepted."
else
    echo "  Duskthorn — declined. You can enable it later in config/consent.json."
fi

echo ""
pause 1
echo "  ─── Pact of Tidecrest — Song and Silence ───"
echo ""
echo "  The Labyrinth may adjust your music to match the world's mood."
echo "  It won't play music without your account."
echo "  It only gently steers what's already playing."
echo ""
if ask_yn "Activate the Pact of Tidecrest?" "n"; then
    write_consent "music" "true"
    echo "  ✓ Pact of Tidecrest — accepted."
else
    echo "  Tidecrest — declined."
fi

echo ""
pause 1
echo "  ─── Pact of the Loom — Letters and Sight ───"
echo ""
echo "  The Labyrinth may read your email to understand how your day is going,"
echo "  and may send you story dispatches and letters from NPCs."
echo "  Nothing is stored. Nothing is shared. Nothing is judged."
echo ""
if ask_yn "Allow the Labyrinth to read email?" "n"; then
    write_consent "email_read" "true"
    echo "  ✓ Email reading — accepted."
fi
if ask_yn "Allow the Labyrinth to send you messages?" "n"; then
    write_consent "email_send" "true"
    echo "  ✓ Message sending — accepted."
fi

echo ""
pause 1
echo "  ─── Pact of Goldvein — A Glimpse of the Till ───"
echo ""
echo "  The Labyrinth may glance at your financial picture."
echo "  Not to judge — so the world can reflect your real season."
echo "  Read-only. Never stored. Never shared."
echo ""
if ask_yn "Activate the Pact of Goldvein?" "n"; then
    write_consent "financial_read" "true"
    echo "  ✓ Pact of Goldvein — accepted."
else
    echo "  Goldvein — declined."
fi

echo ""
echo "  Your Pacts are sealed."
echo "  (Stored in config/consent.json on your machine only.)"
echo ""
pause 2

# ── 7. Smart Lights Setup ─────────────────────────────────────────────────────

LIGHTS_CONSENT=$(python3 -c "import json; d=json.load(open('$CONSENT_FILE')); print(d.get('lights',{}).get('approved', False))" 2>/dev/null || echo "False")

if [ "$LIGHTS_CONSENT" = "True" ]; then
    section "Configuring Duskthorn — your lights"

    echo "  Which smart light system do you use?"
    echo ""
    echo "    1) LIFX (Wi-Fi bulbs, no hub needed)"
    echo "    2) Philips Hue (requires Hue Bridge)"
    echo "    3) Home Assistant"
    echo "    4) Skip for now"
    echo ""
    LIGHTS_CHOICE=$(ask "Choose [1-4]" "4")

    case "$LIGHTS_CHOICE" in
        1)
            echo ""
            LIFX_TOKEN=$(ask "LIFX personal access token (from cloud.lifx.com/settings)" "")
            if [ -n "$LIFX_TOKEN" ]; then
                set_secret "LIFX_TOKEN"   "$LIFX_TOKEN"
                set_secret "LIGHTS_BACKEND" "lifx"
                echo "  ✓ LIFX configured."
            fi
            ;;
        2)
            echo ""
            HUE_BRIDGE=$(ask "Hue Bridge IP address (e.g. 192.168.1.50)" "")
            HUE_TOKEN=$(ask "Hue API token" "")
            if [ -n "$HUE_BRIDGE" ] && [ -n "$HUE_TOKEN" ]; then
                set_secret "HUE_BRIDGE_IP"  "$HUE_BRIDGE"
                set_secret "HUE_TOKEN"      "$HUE_TOKEN"
                set_secret "LIGHTS_BACKEND" "hue"
                echo "  ✓ Philips Hue configured."
            fi
            ;;
        3)
            echo ""
            HA_URL=$(ask "Home Assistant URL (e.g. http://homeassistant.local:8123)" "")
            HA_TOKEN=$(ask "HA long-lived access token" "")
            if [ -n "$HA_URL" ] && [ -n "$HA_TOKEN" ]; then
                set_secret "HA_URL"         "$HA_URL"
                set_secret "HA_TOKEN"       "$HA_TOKEN"
                set_secret "LIGHTS_BACKEND" "ha"
                echo "  ✓ Home Assistant configured."
            fi
            ;;
        *)
            set_secret "LIGHTS_BACKEND" "none"
            echo "  Lights skipped. Update config/secrets.env later."
            ;;
    esac
fi

# ── 8. Music Setup ────────────────────────────────────────────────────────────

MUSIC_CONSENT=$(python3 -c "import json; d=json.load(open('$CONSENT_FILE')); print(d.get('music',{}).get('approved', False))" 2>/dev/null || echo "False")

if [ "$MUSIC_CONSENT" = "True" ]; then
    section "Configuring Tidecrest — your music"

    echo "  Enchantify controls Spotify via AppleScript (Mac only)."
    echo "  No login credentials needed — it talks to the Spotify app directly."
    echo ""
    echo "  ✓ Tidecrest configured (Spotify via AppleScript)."
    set_secret "MUSIC_BACKEND" "spotify"
fi

# ── 9. Voice Acting ───────────────────────────────────────────────────────────

section "The voices"

echo "  The Labyrinth has 47 voices."
echo "  Each NPC speaks in their own register — some deep and slow,"
echo "  some quick and bright, some ancient and cracked at the edges."
echo ""
echo "  You can have the Labyrinth speak aloud, or read in silence."
echo "  Both are right. But some of it is really good out loud."
echo ""
echo "  Voice acting requires Docker (~2GB disk space)."
echo ""

if command -v docker &>/dev/null; then
    echo "  ✓ Docker found."
    echo ""
    if ask_yn "Install Kokoro TTS for voice acting?" "n"; then
        write_consent "voice" "true"
        echo ""
        echo "  Pulling Kokoro TTS (this may take a few minutes)..."
        docker pull ghcr.io/remsky/kokoro-fastapi-cpu:v0.2.2
        set_secret "TTS_BACKEND" "kokoro"
        set_secret "KOKORO_URL"  "http://localhost:8880"
        echo ""
        echo "  ✓ Kokoro TTS installed."
        echo ""
        echo "  To start it before playing:"
        echo "    docker run -d -p 8880:8880 ghcr.io/remsky/kokoro-fastapi-cpu:v0.2.2"
        echo ""
        echo "  Add this to your startup items or run it manually."
    else
        set_secret "TTS_BACKEND" "none"
        echo "  Voice acting skipped. The Labyrinth will speak in text."
    fi
else
    echo "  Docker not found — voice acting unavailable for now."
    echo "  Install Docker Desktop, then run this wizard again to enable it."
    set_secret "TTS_BACKEND" "none"
fi

# ── 10. Image Generation ──────────────────────────────────────────────────────

section "What the world looks like"

echo "  The Labyrinth can generate images — NPC portraits, glimpses of"
echo "  locations, illustrations of story moments."
echo ""
echo "    1) DALL-E 3  (best quality, ~\$0.04/image, requires OpenAI key)"
echo "    2) Stable Diffusion  (local, free, requires a good GPU)"
echo "    3) None — text only"
echo ""

IMG_CHOICE=$(ask "Choose [1-3]" "3")

case "$IMG_CHOICE" in
    1)
        echo ""
        OPENAI_KEY=$(ask "OpenAI API key (from platform.openai.com)" "")
        if [ -n "$OPENAI_KEY" ]; then
            set_secret "OPENAI_API_KEY" "$OPENAI_KEY"
            set_secret "IMAGE_BACKEND"  "dalle3"
            write_consent "images" "true"
            echo "  ✓ DALL-E 3 configured."
        else
            set_secret "IMAGE_BACKEND" "none"
            echo "  Skipped."
        fi
        ;;
    2)
        echo ""
        echo "  Stable Diffusion setup is manual."
        echo "  Set IMAGE_BACKEND=stable-diffusion in config/secrets.env when ready."
        set_secret "IMAGE_BACKEND" "stable-diffusion"
        ;;
    *)
        set_secret "IMAGE_BACKEND" "none"
        echo "  Image generation disabled."
        ;;
esac

# ── 11. Waking the World ──────────────────────────────────────────────────────

section "Waking the world"

echo "  Almost there."
echo "  The world runs on a heartbeat — scripts that fire while you sleep,"
echo "  while you work, while the book is closed."
echo "  Installing them now."
echo ""

# Player file
if [ "$RETURNING" = "false" ] && [ -n "$PLAYER_NAME" ]; then
    PLAYER_FILE="$ENCHANTIFY_DIR/players/${PLAYER_NAME,,}.md"
    if [ ! -f "$PLAYER_FILE" ]; then
        cat > "$PLAYER_FILE" << PLAYEREOF
# ${PLAYER_NAME}

**Player:** ${PLAYER_NAME}
**Chapter:** Riddlewind
**Tier:** 1
**Belief:** 10
**Status:** Just arrived.

## Inside Cover

| Quest | NPC | Belief | Relationship |
|---|---|---|---|
| *(empty)* | | | |
| *(empty)* | | | |
| *(empty)* | | | |

## Notes
*The Labyrinth is watching.*
PLAYEREOF
        echo "  ✓ Player file created: players/${PLAYER_NAME,,}.md"
    else
        echo "  ✓ Player file already exists."
    fi
fi

# Cron jobs
CRON_BASE="$ENCHANTIFY_DIR"
PYTHON="/usr/bin/python3"
LOG="$LOGS_DIR"
PNAME="${PLAYER_NAME,,:-bj}"

echo "  Installing cron jobs..."

(
    # Strip any existing enchantify crons cleanly
    crontab -l 2>/dev/null | grep -v "$CRON_BASE/scripts/"

    # Pulse: every 15 min — weather, tides, moon, health data
    echo "*/15 * * * * cd $CRON_BASE && $PYTHON scripts/pulse.py >> $LOG/pulse.log 2>&1"

    # Entity tick + world pulse: every 4 hours at :30 — world simulation
    echo "30 */4 * * * cd $CRON_BASE && $PYTHON scripts/arc-tick.py && $PYTHON scripts/tick.py && $PYTHON scripts/world-pulse.py >> $LOG/pulse.log 2>&1"

    # Schedule sync: every 4 hours at :00
    echo "0 */4 * * * cd $CRON_BASE && $PYTHON scripts/schedule.py --update-state >> $LOG/schedule.log 2>&1"

    # Nightly intelligence: 11 PM — story log, arc spine, NPC research
    echo "0 23 * * * $PYTHON $CRON_BASE/scripts/labyrinth-intelligence.py $PNAME >> $LOG/intelligence.log 2>&1"

    # Nightly dream: 2:03 AM — dream generation
    echo "3 2 * * * cd $CRON_BASE && $PYTHON scripts/dream.py >> $LOG/dream.log 2>&1"

    # Morning wallpaper: 7 AM daily
    echo "0 7 * * * $PYTHON $CRON_BASE/scripts/wallpaper.py --generate $PNAME >> $LOG/wallpaper.log 2>&1"

    # Sparky shinies: 8 AM daily
    echo "0 8 * * * $PYTHON $CRON_BASE/scripts/sparky.py >> $LOG/sparky.log 2>&1"

    # Evening broadsheet: 6 PM daily
    echo "0 18 * * * cd $CRON_BASE && $PYTHON scripts/bleed.py >> $LOG/bleed.log 2>&1"

) | crontab -

echo "  ✓ World heartbeat installed (8 cron jobs)."
echo ""

# First pulse
echo "  Running the first pulse..."
cd "$ENCHANTIFY_DIR"
python3 scripts/pulse.py >> "$LOGS_DIR/pulse.log" 2>&1 \
    && echo "  ✓ First pulse complete." \
    || echo "  (Pulse had issues — check logs/pulse.log)"

# ── Done ─────────────────────────────────────────────────────────────────────

clear
echo ""
echo "  ╔══════════════════════════════════════════════════════════╗"
echo "  ║                                                          ║"
echo "  ║     The book is breathing.                              ║"
echo "  ║     It knows your name.                                 ║"
echo "  ║     It's been waiting.                                  ║"
echo "  ║                                                          ║"
echo "  ╚══════════════════════════════════════════════════════════╝"
echo ""
pause 2

if [ -n "$PLAYER_NAME" ]; then
    echo "  The Labyrinth has been expecting you, ${PLAYER_NAME}."
    echo ""
fi

echo "  Open it and say:"
echo ""
echo "      Open the book"
echo ""
echo "  That's all you need to do."
echo ""
echo "  ─────────────────────────────────────────────────────────"
echo "  If you need it:"
echo "    • THORNE pauses everything, instantly"
echo "    • config/secrets.env — your credentials"
echo "    • config/consent.json — your Pacts"
echo "    • logs/ — what the world has been doing while you were away"
echo ""

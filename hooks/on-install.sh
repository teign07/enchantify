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

# (write_consent removed — pact ceremony writes app_pacts directly via Python)

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
echo "  ║     ⚡  The Talisman War                                ║"
echo "  ║         The Pact Ceremony                               ║"
echo "  ║                                                          ║"
echo "  ╚══════════════════════════════════════════════════════════╝"
echo ""
echo "  The Academy doesn't stay in the book."
echo ""
echo "  Five Chapters have philosophies they want to spread into the"
echo "  real world. They do this by warring over your apps —"
echo "  influencing how you use them, drafting in your voice,"
echo "  steering what you hear and see."
echo ""
echo "  Emberheart  — bold individual voice; self-authorship; say the specific thing"
echo "  Mossbloom   — patience, depth, reception; the long work; the slow read"
echo "  Riddlewind  — connection, community, collaboration; no story is solo"
echo "  Tidecrest   — feeling over logic; flow; the emotional current"
echo "  Duskthorn   — control, leverage, strategic pressure; always three moves ahead"
echo ""
echo "  Below are your apps. For each one, you decide whether to open"
echo "  it to the war. Closed apps stay neutral. Open apps are"
echo "  contested territory — the Chapters will fight over them."
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

# Collect app pact choices — keyed to exact app names in app-register.md
PACT_SPOTIFY=false
PACT_NOTES=false
PACT_REMINDERS=false
PACT_CALENDAR=false
PACT_OBSIDIAN=false
PACT_MOLTBOOK=false
PACT_BLUESKY=false
PACT_TWITTER=false
PACT_REDDIT=false
PACT_TELEGRAM=false
PACT_IMESSAGE=false

echo "  ─── Music ──────────────────────────────────────────────────"
echo ""
echo "  Spotify"
echo ""
echo "  At low tiers: chapters suggest playlists, skip tracks, set the"
echo "  atmosphere through what you hear. Silent — you discover it."
echo "  At high tiers: a chapter controls the mood of your whole session."
echo "  Tidecrest naturally holds this territory, but all five want it."
echo ""
if ask_yn "Open Spotify to the Talisman War?" "y"; then
    PACT_SPOTIFY=true
    echo "  ✓ Spotify — open."
else
    echo "  Spotify — closed."
fi

echo ""
pause 1
echo "  ─── Productivity ───────────────────────────────────────────"
echo ""
echo "  Apple Notes, Apple Reminders, Apple Calendar, Obsidian"
echo ""
echo "  At low tiers: chapters shape what you record, what stays on"
echo "  your list, how your week is framed. Mostly silent."
echo "  At high tiers: chapters draft in Notes, create Reminders,"
echo "  add calendar entries for story-relevant moments."
echo "  Emberheart wants Notes. Mossbloom wants Obsidian."
echo "  Riddlewind wants your Calendar."
echo ""
if ask_yn "Open productivity apps to the war?" "y"; then
    PACT_NOTES=true
    PACT_REMINDERS=true
    PACT_CALENDAR=true
    PACT_OBSIDIAN=true
    echo "  ✓ Productivity apps — open."
else
    echo ""
    echo "  Choose individually:"
    ask_yn "  Apple Notes?" "y"   && PACT_NOTES=true     && echo "    ✓ Notes — open."
    ask_yn "  Apple Reminders?" "y" && PACT_REMINDERS=true && echo "    ✓ Reminders — open."
    ask_yn "  Apple Calendar?" "y" && PACT_CALENDAR=true  && echo "    ✓ Calendar — open."
    ask_yn "  Obsidian?" "y"       && PACT_OBSIDIAN=true  && echo "    ✓ Obsidian — open."
fi

echo ""
pause 1
echo "  ─── Social ─────────────────────────────────────────────────"
echo ""
echo "  Bluesky, X/Twitter, Reddit, Moltbook"
echo ""
echo "  This is the most contested territory."
echo "  At lower tiers: chapters shape how you see these platforms —"
echo "  what threads surface, what the Labyrinth notices."
echo "  At Dominated/Sovereign tiers: a chapter may draft a post in"
echo "  your philosophical voice. You always approve before it posts."
echo "  Nothing goes public without your explicit consent."
echo "  But they will try."
echo ""
if ask_yn "Open social apps to the war?" "n"; then
    PACT_MOLTBOOK=true
    PACT_BLUESKY=true
    PACT_TWITTER=true
    PACT_REDDIT=true
    echo "  ✓ Social apps — open."
else
    echo ""
    echo "  Choose individually:"
    ask_yn "  Moltbook?" "n"  && PACT_MOLTBOOK=true && echo "    ✓ Moltbook — open."
    ask_yn "  Bluesky?" "n"   && PACT_BLUESKY=true  && echo "    ✓ Bluesky — open."
    ask_yn "  X/Twitter?" "n" && PACT_TWITTER=true  && echo "    ✓ X/Twitter — open."
    ask_yn "  Reddit?" "n"    && PACT_REDDIT=true   && echo "    ✓ Reddit — open."
fi

echo ""
pause 1
echo "  ─── Messaging ──────────────────────────────────────────────"
echo ""
echo "  Telegram"
echo "  The Labyrinth uses this to send you dispatches — story events,"
echo "  morning summaries, NPC letters. Chapters compete over the"
echo "  tone, timing, and content of what reaches you."
echo ""
if ask_yn "Open Telegram to the war?" "y"; then
    PACT_TELEGRAM=true
    echo "  ✓ Telegram — open."
else
    echo "  Telegram — closed."
fi

echo ""
echo "  iMessage"
echo "  Enables chapters to send direct letters to people in your life."
echo "  Always requires your explicit approval before any message sends."
echo "  This is the most personal territory. Most players keep it closed."
echo ""
if ask_yn "Open iMessage to the war?" "n"; then
    PACT_IMESSAGE=true
    echo "  ✓ iMessage — open. (You approve every message before it sends.)"
else
    echo "  iMessage — closed."
fi

# Write consent.json in the format pact-engine.py reads
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
python3 - <<PYEOF
import json, pathlib
f = pathlib.Path("$CONSENT_FILE")
data = json.loads(f.read_text()) if f.exists() else {}
data["app_pacts"] = {
    "Spotify":         $PACT_SPOTIFY,
    "Apple Notes":     $PACT_NOTES,
    "Apple Reminders": $PACT_REMINDERS,
    "Apple Calendar":  $PACT_CALENDAR,
    "Obsidian":        $PACT_OBSIDIAN,
    "Moltbook":        $PACT_MOLTBOOK,
    "Bluesky":         $PACT_BLUESKY,
    "X / Twitter":     $PACT_TWITTER,
    "Reddit":          $PACT_REDDIT,
    "Telegram":        $PACT_TELEGRAM,
    "iMessage":        $PACT_IMESSAGE,
}
data["override_word"]         = "THORNE"
data["ceremony_completed"]    = "$TS"
f.parent.mkdir(parents=True, exist_ok=True)
f.write_text(json.dumps(data, indent=2))
PYEOF

echo ""
echo "  The war begins at first tick."
echo "  (Your choices are in config/consent.json — edit any time.)"
echo ""
pause 2

# ── 7. Physical World Setup ───────────────────────────────────────────────────
# Smart lights and music — separate from the app war; these are ambient systems
# the Labyrinth controls directly regardless of chapter territory.

section "Physical world integrations"

echo "  The Labyrinth can also reach into your physical space directly —"
echo "  shifting your lights to match the story, steering your music."
echo "  This is separate from the Talisman War: not territory, just atmosphere."
echo ""

echo "  ── Smart lights ────────────────────────────────────────────"
echo ""
echo "  A red flicker when danger is near. Warm gold when you're safe."
echo "  A slow fade when the Compass says to rest."
echo ""
if ask_yn "Set up smart lights?" "n"; then
    echo ""
    echo "    1) LIFX  — Wi-Fi bulbs, no hub needed. Direct LAN control."
    echo "    2) Home Assistant — covers everything: Matter, HomeKit,"
    echo "                        LIFX, Hue, Z-Wave, Zigbee, and more."
    echo "    3) Philips Hue  — requires Hue Bridge on your network."
    echo "    4) HomeKit (macOS) — scene-level control via Shortcuts app."
    echo "    5) Multiple backends — e.g. LIFX + HA as fallback."
    echo "    6) Skip"
    echo ""
    LIGHTS_CHOICE=$(ask "Choose [1-6]" "6")
    case "$LIGHTS_CHOICE" in
        1)
            echo ""
            echo "  LIFX uses direct LAN — no cloud required after setup."
            echo "  Get your token at: cloud.lifx.com/settings"
            echo "  (Token is optional if your bulbs are on the same network —"
            echo "   skip it and Enchantify will auto-discover by broadcast.)"
            echo ""
            LIFX_TOKEN=$(ask "LIFX personal access token (or press Enter to skip)" "")
            if [ -n "$LIFX_TOKEN" ]; then
                set_secret "LIFX_TOKEN" "$LIFX_TOKEN"
            fi
            LIFX_IPS=$(ask "Bulb IP addresses, comma-separated (or Enter to auto-discover)" "")
            if [ -n "$LIFX_IPS" ]; then
                set_secret "ENCHANTIFY_LIFX_IPS" "$LIFX_IPS"
            fi
            set_secret "LIGHTS_BACKEND" "lifx"
            echo ""
            echo "  ✓ LIFX configured."
            echo "  Test anytime: python3 scripts/lights.py test"
            ;;
        2)
            echo ""
            echo "  Home Assistant is the most flexible backend — if your lights"
            echo "  are in HA, this covers Matter, HomeKit, LIFX, Hue, everything."
            echo ""
            HA_URL=$(ask "Home Assistant URL (e.g. http://homeassistant.local:8123)" "")
            HA_TOKEN=$(ask "Long-lived access token (HA → Profile → Long-Lived Access Tokens)" "")
            if [ -n "$HA_URL" ] && [ -n "$HA_TOKEN" ]; then
                set_secret "HA_URL"   "$HA_URL"
                set_secret "HA_TOKEN" "$HA_TOKEN"
                HA_ENTITIES=$(ask "Light entity IDs, comma-separated (or Enter to auto-discover)" "")
                if [ -n "$HA_ENTITIES" ]; then
                    set_secret "ENCHANTIFY_HA_LIGHT_ENTITIES" "$HA_ENTITIES"
                fi
                set_secret "LIGHTS_BACKEND" "ha"
                echo ""
                echo "  ✓ Home Assistant configured."
                echo "  Test: python3 scripts/lights.py test"
            else
                set_secret "LIGHTS_BACKEND" "none"
                echo "  HA skipped (no credentials entered)."
            fi
            ;;
        3)
            echo ""
            HUE_BRIDGE=$(ask "Hue Bridge IP address" "")
            HUE_TOKEN=$(ask "Hue developer API token" "")
            if [ -n "$HUE_BRIDGE" ] && [ -n "$HUE_TOKEN" ]; then
                set_secret "HUE_BRIDGE_IP"  "$HUE_BRIDGE"
                set_secret "HUE_TOKEN"      "$HUE_TOKEN"
                set_secret "LIGHTS_BACKEND" "hue"
                echo "  ✓ Philips Hue configured."
            else
                set_secret "LIGHTS_BACKEND" "none"
            fi
            ;;
        4)
            echo ""
            echo "  HomeKit backend fires named Shortcuts from the Shortcuts app."
            echo "  Create Shortcuts named 'Enchantify: <scene>' (e.g. 'Enchantify: library')"
            echo "  and point each one at a HomeKit scene."
            echo "  This gives you scene-level control; for full color control use HA instead."
            echo ""
            set_secret "LIGHTS_BACKEND" "homekit"
            echo "  ✓ HomeKit (Shortcuts) configured."
            echo "  Remember to create the named Shortcuts in Shortcuts.app."
            ;;
        5)
            echo ""
            echo "  Primary + fallback. Enter each backend in order (e.g. 'lifx,ha')."
            echo "  Supported: lifx, ha, hue, homekit"
            echo ""
            MULTI_BACKENDS=$(ask "Backend chain, comma-separated" "lifx,ha")
            set_secret "LIGHTS_BACKEND" "$MULTI_BACKENDS"
            echo ""
            echo "  Configure credentials for each backend above if needed."
            echo "  Run: python3 scripts/lights.py status"
            ;;
        *)
            set_secret "LIGHTS_BACKEND" "none"
            echo "  Lights skipped. Set LIGHTS_BACKEND in config/secrets.env to enable later."
            ;;
    esac

    # Offer a test after any non-skip choice
    if [ "$LIGHTS_CHOICE" != "6" ]; then
        echo ""
        if ask_yn "Run a light test now?" "y"; then
            python3 "$ENCHANTIFY_DIR/scripts/lights.py" test \
                && echo "  ✓ Lights working." \
                || echo "  ⚠ Test had issues. Check config/secrets.env and try: python3 scripts/lights.py status"
        fi
    fi
else
    set_secret "LIGHTS_BACKEND" "none"
    echo "  Lights skipped."
fi

echo ""
echo "  ── Music ───────────────────────────────────────────────────"
echo ""
echo "  Enchantify controls Spotify via AppleScript (Mac only)."
echo "  No credentials needed — it talks to the Spotify app directly."
echo ""
if ask_yn "Enable Spotify ambient control?" "y"; then
    set_secret "MUSIC_BACKEND" "spotify"
    echo "  ✓ Spotify configured."
else
    set_secret "MUSIC_BACKEND" "none"
    echo "  Spotify skipped."
fi

# ── 8. Voice Acting ───────────────────────────────────────────────────────────

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

# ── 11. Memory Plugins ────────────────────────────────────────────────────────

section "Memory plugins (optional)"

echo "  Two plugins extend how much the Labyrinth can hold across sessions."
echo ""
echo "  QMD — hybrid semantic memory search (BM25 + vector)."
echo "  Reduces token use significantly. The Labyrinth finds relevant"
echo "  context faster and wastes less of its attention on the wrong things."
echo ""
echo "  Lossless Claw — DAG-based session summarization."
echo "  Keeps the full story in memory even in very long sessions."
echo "  Nothing gets lost in the middle."
echo ""
echo "  Both are recommended for long-term play."
echo ""

INSTALL_QMD=false
INSTALL_LC=false

if ask_yn "Enable QMD memory search?" "y"; then
    INSTALL_QMD=true
fi

if ask_yn "Install Lossless Claw context engine?" "y"; then
    INSTALL_LC=true
fi

if [ "$INSTALL_QMD" = "true" ]; then
    echo ""
    echo "  Enabling QMD..."
    python3 - <<'PYEOF'
import json, pathlib, os
config = pathlib.Path(os.environ.get("HOME", "~")).expanduser() / ".openclaw/openclaw.json"
if config.exists():
    data = json.loads(config.read_text())
    data.setdefault("memory", {})["backend"] = "qmd"
    data["memory"].setdefault("qmd", {})["includeDefaultMemory"] = True
    config.write_text(json.dumps(data, indent=2))
    print("  ✓ QMD enabled.")
else:
    print("  (openclaw.json not found — QMD will be configured on first launch)")
PYEOF
fi

if [ "$INSTALL_LC" = "true" ]; then
    echo ""
    echo "  Installing Lossless Claw..."
    if openclaw plugins install @martian-engineering/Lossless-Claw 2>/dev/null; then
        python3 - <<'PYEOF'
import json, pathlib, os
config = pathlib.Path(os.environ.get("HOME", "~")).expanduser() / ".openclaw/openclaw.json"
if config.exists():
    data = json.loads(config.read_text())
    data.setdefault("plugins", {}).setdefault("slots", {})["contextEngine"] = "lossless-claw"
    data["plugins"].setdefault("entries", {}).setdefault("lossless-claw", {}).update({
        "enabled": True,
        "config": {},
    })
    config.write_text(json.dumps(data, indent=2))
PYEOF
        echo "  ✓ Lossless Claw installed."
    else
        echo "  Lossless Claw install failed."
        echo "  Try manually: openclaw plugins install @martian-engineering/Lossless-Claw"
    fi
fi

# ── 12. Agent Registration ─────────────────────────────────────────────────────

section "Registering the Labyrinth"

OPENCLAW_CONFIG="$HOME/.openclaw/openclaw.json"
AGENT_DIR="$HOME/.openclaw/agents/enchantify"

# Detect fresh vs existing install
EXISTING_AGENT_COUNT=$(python3 - <<PYEOF
import json, pathlib, os
config = pathlib.Path(os.environ.get("HOME", "~")).expanduser() / ".openclaw/openclaw.json"
if not config.exists():
    print("0")
else:
    try:
        data = json.loads(config.read_text())
        agent_list = data.get("agents", {}).get("list", [])
        others = [a for a in agent_list if a.get("id") not in ("main", "enchantify")]
        print(str(len(others)))
    except Exception:
        print("0")
PYEOF
)

IS_MAIN=false
if [ "$EXISTING_AGENT_COUNT" = "0" ]; then
    echo "  No other agents detected."
    echo "  The Labyrinth will be your main agent — when you open OpenClaw,"
    echo "  this is who answers."
    IS_MAIN=true
else
    echo "  Found $EXISTING_AGENT_COUNT other agent(s) in your OpenClaw setup."
    echo "  Installing Enchantify as a named agent alongside them."
    echo "  To open the Labyrinth: openclaw --agent enchantify"
    IS_MAIN=false
fi

echo ""
pause 1

# Create agent directory and copy instructions
mkdir -p "$AGENT_DIR"
cp "$ENCHANTIFY_DIR/AGENTS.md" "$AGENT_DIR/agent.md"
echo "  ✓ Agent instructions written to $AGENT_DIR"

# Register in openclaw.json
python3 - <<PYEOF
import json, pathlib, shutil, os

config_path  = pathlib.Path(os.environ.get("HOME", "~")).expanduser() / ".openclaw/openclaw.json"
enchantify_ws = "$ENCHANTIFY_DIR"
agent_dir    = "$AGENT_DIR"
model_id     = "$MODEL_ID"
is_main      = "$IS_MAIN" == "true"

if not config_path.exists():
    data = {"agents": {"defaults": {}, "list": [{"id": "main"}]}}
else:
    data = json.loads(config_path.read_text())

agents_block = data.setdefault("agents", {})
agent_list   = agents_block.setdefault("list", [])

if is_main:
    main_entry = next((a for a in agent_list if a.get("id") == "main"), None)
    if main_entry is None:
        agent_list.insert(0, {"id": "main"})
        main_entry = agent_list[0]
    main_entry["workspace"] = enchantify_ws
    main_entry["agentDir"]  = agent_dir
    if model_id:
        main_entry["model"] = model_id
    print("  ✓ Enchantify set as main agent.")
else:
    existing = next((a for a in agent_list if a.get("id") == "enchantify"), None)
    entry = {"id": "enchantify", "name": "enchantify",
             "workspace": enchantify_ws, "agentDir": agent_dir}
    if model_id:
        entry["model"] = model_id
    if existing:
        existing.update(entry)
    else:
        agent_list.append(entry)
    print("  ✓ Enchantify registered as named agent.")

if config_path.exists():
    shutil.copy2(config_path, config_path.with_suffix(".json.bak"))
config_path.parent.mkdir(parents=True, exist_ok=True)
config_path.write_text(json.dumps(data, indent=2))
PYEOF

# Store IS_MAIN for the final screen
export ENCHANTIFY_IS_MAIN="$IS_MAIN"

# ── 13. Waking the World ──────────────────────────────────────────────────────

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

if [ "$ENCHANTIFY_IS_MAIN" = "true" ]; then
    echo "  Open it and say:"
    echo ""
    echo "      openclaw"
    echo ""
    echo "  Then say:  Open the book"
else
    echo "  Open it and say:"
    echo ""
    echo "      openclaw --agent enchantify"
    echo ""
    echo "  Then say:  Open the book"
fi
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

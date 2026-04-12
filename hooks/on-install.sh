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
#    1. Welcome
#    2. Environment detection
#    3. Model selection
#    4. Location setup
#    5. Telegram setup
#    6. The Pact Ceremony (consent)
#    7. Smart lights (optional)
#    8. Music (Spotify, optional)
#    9. Voice acting — Kokoro TTS (optional)
#   10. Image generation — DALL-E 3 or local (optional)
#   11. Ambient music — Meta MusicGen Small (optional)
#   12. Memory plugins — QMD + Lossless Claw (optional)
#   13. Final setup — write config, install cron, first run
# ════════════════════════════════════════════════════════════════════════════

set -e

ENCHANTIFY_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG_DIR="$ENCHANTIFY_DIR/config"
SECRETS_FILE="$CONFIG_DIR/secrets.env"
CONSENT_FILE="$CONFIG_DIR/consent.json"
LOGS_DIR="$ENCHANTIFY_DIR/logs"

# ── 0. Helpers ────────────────────────────────────────────────────────────────

pause() { sleep "${1:-1}"; }

print_box() {
    local msg="$1"
    local width=60
    local border
    border=$(printf '%0.s═' $(seq 1 $width))
    echo ""
    echo "  ╔${border}╗"
    echo "  ║  $(printf "%-${width}s" "$msg")  ║"
    echo "  ╚${border}╝"
    echo ""
}

section() {
    echo ""
    echo "  ────────────────────────────────────────────────────────"
    echo "  $1"
    echo "  ────────────────────────────────────────────────────────"
    echo ""
}

ask() {
    # ask <prompt> <default>
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
    # ask_yn <prompt> <default: y|n>
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
        # Update existing line
        local escaped_value
        escaped_value=$(printf '%s\n' "$value" | sed 's/[[\.*^$()+?{|]/\\&/g')
        sed -i.bak "s|^${key}=.*|${key}=${escaped_value}|" "$SECRETS_FILE" && rm -f "${SECRETS_FILE}.bak"
    else
        echo "${key}=${value}" >> "$SECRETS_FILE"
    fi
}

write_consent() {
    local key="$1"
    local approved="$2"   # true | false
    local ts
    ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    # Use python to update JSON atomically
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

# Ensure secrets.env exists (copy from example if needed)
if [ ! -f "$SECRETS_FILE" ]; then
    cp "$CONFIG_DIR/secrets.env.example" "$SECRETS_FILE"
fi

# Ensure consent.json exists (start empty — everything unapproved)
if [ ! -f "$CONSENT_FILE" ]; then
    echo '{}' > "$CONSENT_FILE"
fi

# ── 1. Welcome ────────────────────────────────────────────────────────────────

clear
echo ""
echo "  ╔══════════════════════════════════════════════════════════╗"
echo "  ║                                                          ║"
echo "  ║     📖  The Labyrinth of Stories                        ║"
echo "  ║         Enchantify — Installation Wizard                ║"
echo "  ║                                                          ║"
echo "  ╚══════════════════════════════════════════════════════════╝"
echo ""
echo "  You are about to step through a door."
echo "  On the other side: a living world that runs on your machine,"
echo "  knows your name, and keeps going even when you look away."
echo ""
echo "  This wizard will set everything up."
echo "  Most questions are optional. Take your time."
echo ""
pause 2

# ── 2. Environment Detection ──────────────────────────────────────────────────

section "Checking your environment"

OPENCLAW_VERSION=$(openclaw --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+(\.[0-9]+)?' | head -1 || echo "unknown")
echo "  OpenClaw version : $OPENCLAW_VERSION"

PYTHON_VERSION=$(python3 --version 2>/dev/null | awk '{print $2}' || echo "unknown")
echo "  Python           : $PYTHON_VERSION"

NODE_VERSION=$(node --version 2>/dev/null || echo "not found")
echo "  Node.js          : $NODE_VERSION"

echo ""

# Check for existing player files
PLAYER_NAME=""
if ls "$ENCHANTIFY_DIR/players/"*.md &>/dev/null; then
    EXISTING_PLAYERS=$(ls "$ENCHANTIFY_DIR/players/"*.md 2>/dev/null | xargs -I{} basename {} .md | tr '\n' ' ')
    echo "  Found existing player files: $EXISTING_PLAYERS"
    echo "  (Returning player? This wizard will not overwrite your save.)"
    echo ""
    RETURNING=true
else
    RETURNING=false
fi

if [ "$RETURNING" = "false" ]; then
    echo "  Welcome, new Wanderer."
    echo ""
    PLAYER_NAME=$(ask "What should the Labyrinth call you?")
    if [ -z "$PLAYER_NAME" ]; then PLAYER_NAME="Wanderer"; fi
fi

# ── 3. Model Selection ────────────────────────────────────────────────────────

section "Choosing your AI model"

echo "  Enchantify can work with any LLM that OpenClaw supports."
echo "  Your model choice becomes the 'mind' of the Labyrinth."
echo ""
echo "  Popular choices:"
echo "    1) Claude Sonnet 4.6  (recommended — nuanced, narrative-focused)"
echo "    2) Claude Opus 4.6    (deeper reasoning, uses more tokens)"
echo "    3) Claude Haiku 4.5   (fast, lightweight)"
echo "    4) GPT-4o             (requires OpenAI API key)"
echo "    5) Custom             (enter your own model ID)"
echo ""

MODEL_CHOICE=$(ask "Choose [1-5]" "1")

case "$MODEL_CHOICE" in
    1) MODEL_ID="claude-sonnet-4-6" ;;
    2) MODEL_ID="claude-opus-4-6" ;;
    3) MODEL_ID="claude-haiku-4-5-20251001" ;;
    4) MODEL_ID="gpt-4o" ;;
    5) MODEL_ID=$(ask "Model ID") ;;
    *) MODEL_ID="claude-sonnet-4-6" ;;
esac

echo ""
echo "  ✓ Model: $MODEL_ID"
set_secret "MODEL_ID" "$MODEL_ID"

# ── 4. Location Setup ─────────────────────────────────────────────────────────

section "Your corner of the world"

echo "  The Labyrinth watches the real world — weather, tides, sunrise."
echo "  This is used only to enrich your story. Nothing is sent anywhere."
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
    echo "  For tides and precise weather, we need your coordinates."
    echo "  (Find them at: maps.google.com — right-click your location)"
    echo ""
    LAT=$(ask "Latitude (decimal, e.g. 44.4258)" "")
    LON=$(ask "Longitude (decimal, e.g. -69.0064)" "")
    [ -n "$LAT" ] && set_secret "LAT" "$LAT"
    [ -n "$LON" ] && set_secret "LON" "$LON"

    echo ""
    echo "  NOAA tide station ID (US coastal only, optional):"
    echo "  Find yours at tidesandcurrents.noaa.gov/stations.html"
    NOAA=$(ask "NOAA station ID (leave blank to skip)" "")
    [ -n "$NOAA" ] && set_secret "NOAA_STATION" "$NOAA"
fi

echo ""
echo "  ✓ Location configured."

# ── 5. Telegram Setup ─────────────────────────────────────────────────────────

section "Telegram — messages while you're away"

echo "  Enchantify can send you dispatches via Telegram:"
echo "  morning summaries, story events, NPC messages."
echo "  (Telegram is free. You'll need the app and a bot token.)"
echo ""

if ask_yn "Set up Telegram now?" "y"; then
    echo ""
    echo "  Step 1: Open Telegram and message @BotFather"
    echo "  Step 2: Send: /newbot"
    echo "  Step 3: Follow the prompts — you'll get a token like:"
    echo "          1234567890:ABCDEFghijklmnopqrstuvwxyz"
    echo ""
    TELEGRAM_TOKEN=$(ask "Paste your bot token here (or press Enter to skip)")
    if [ -n "$TELEGRAM_TOKEN" ]; then
        set_secret "TELEGRAM_BOT_TOKEN" "$TELEGRAM_TOKEN"

        echo ""
        echo "  Now start a chat with your new bot in Telegram."
        echo "  Then message it anything (like 'hello')."
        echo "  Then visit this URL in a browser to find your chat ID:"
        echo "  https://api.telegram.org/bot${TELEGRAM_TOKEN}/getUpdates"
        echo "  Look for: \"chat\":{\"id\": 123456789"
        echo ""
        TELEGRAM_CHAT=$(ask "Your Telegram chat ID")
        [ -n "$TELEGRAM_CHAT" ] && set_secret "TELEGRAM_CHAT_ID" "$TELEGRAM_CHAT"
        echo ""
        echo "  ✓ Telegram configured."
    else
        echo ""
        echo "  Skipped. You can add it later by editing config/secrets.env"
    fi
else
    echo ""
    echo "  Skipped. Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to config/secrets.env later."
fi

# ── 6. The Pact Ceremony ──────────────────────────────────────────────────────

clear
echo ""
echo "  ╔══════════════════════════════════════════════════════════╗"
echo "  ║                                                          ║"
echo "  ║     ⚡  The Pact Ceremony                               ║"
echo "  ║                                                          ║"
echo "  ╚══════════════════════════════════════════════════════════╝"
echo ""
echo "  The Labyrinth has powers that reach into your physical world."
echo "  Each power is a Pact — a named agreement between you and the"
echo "  world. You choose which ones to activate. You can revoke"
echo "  any Pact at any time."
echo ""
echo "  Your override word — say or type this to pause everything:"
echo ""
echo "      ┌─────────────────────────────────────┐"
echo "      │                                     │"
echo "      │          THORNE                     │"
echo "      │                                     │"
echo "      └─────────────────────────────────────┘"
echo ""
echo "  Write it down somewhere. It will always work."
echo ""
pause 3

# Initialize all pacts as unapproved
write_consent "lights" "false"
write_consent "music" "false"
write_consent "voice" "false"
write_consent "images" "false"
write_consent "ambient_music" "false"
write_consent "email_read" "false"
write_consent "email_send" "false"
write_consent "financial_read" "false"

echo ""
echo "  ─── Pact of Duskthorn — Light and Shadow ───"
echo ""
echo "  The Labyrinth may shift your lights to match the story."
echo "  (Plain English: it can dim or change the color of your smart bulbs"
echo "   at story moments — a red flash when danger is near, warm gold"
echo "   when you're safe, slow fade when the Compass says to rest.)"
echo ""
echo "  You control which lights. You can pause it any time."
echo ""
if ask_yn "Activate the Pact of Duskthorn?" "n"; then
    write_consent "lights" "true"
    echo "  ✓ Pact of Duskthorn — accepted."
else
    echo "  Duskthorn — declined. You can enable it later."
fi

echo ""
pause 1
echo "  ─── Pact of Tidecrest — Song and Silence ───"
echo ""
echo "  The Labyrinth may adjust your music to match the world's mood."
echo "  (Plain English: it can pause Spotify when the story calls for"
echo "   silence, or suggest a playlist. It won't play music without"
echo "   your Spotify account; it only gently steers what's already playing.)"
echo ""
if ask_yn "Activate the Pact of Tidecrest?" "n"; then
    write_consent "music" "true"
    echo "  ✓ Pact of Tidecrest — accepted."
else
    echo "  Tidecrest — declined. You can enable it later."
fi

echo ""
pause 1
echo "  ─── Pact of the Loom — Letters and Sight ───"
echo ""
echo "  The Labyrinth may read your email to understand how your day is going,"
echo "  and may send you story dispatches."
echo "  (Plain English: it will scan your inbox for context — not store it,"
echo "   not share it. It may send you a Telegram or email from an NPC.)"
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
echo "  The Labyrinth may glance at your financial picture — not to judge,"
echo "  but so the world can reflect your real season."
echo "  (Plain English: read-only access to your bank balance via Teller.io."
echo "   This is never stored, never shared, never acted on.)"
echo ""
if ask_yn "Activate the Pact of Goldvein?" "n"; then
    write_consent "financial_read" "true"
    echo "  ✓ Pact of Goldvein — accepted."
else
    echo "  Goldvein — declined."
fi

echo ""
echo "  Your Pacts have been recorded."
echo "  (Stored in config/consent.json on your machine only.)"
echo ""
echo "  Remember: THORNE pauses everything, instantly."
echo ""
pause 2

# ── 7. Smart Lights Setup ─────────────────────────────────────────────────────

LIGHTS_CONSENT=$(python3 -c "import json; d=json.load(open('$CONSENT_FILE')); print(d.get('lights',{}).get('approved', False))" 2>/dev/null || echo "False")

if [ "$LIGHTS_CONSENT" = "True" ]; then
    section "Smart lights — Duskthorn setup"

    echo "  Which smart light system do you use?"
    echo ""
    echo "    1) LIFX (Wi-Fi bulbs, no hub needed)"
    echo "    2) Philips Hue (requires Hue Bridge)"
    echo "    3) Home Assistant (if you already run HA)"
    echo "    4) Skip for now"
    echo ""
    LIGHTS_CHOICE=$(ask "Choose [1-4]" "4")

    case "$LIGHTS_CHOICE" in
        1)
            echo ""
            echo "  LIFX bulbs are auto-discovered on your Wi-Fi."
            LIFX_TOKEN=$(ask "LIFX personal access token (from cloud.lifx.com/settings)" "")
            if [ -n "$LIFX_TOKEN" ]; then
                set_secret "LIFX_TOKEN" "$LIFX_TOKEN"
                set_secret "LIGHTS_BACKEND" "lifx"
                echo "  ✓ LIFX configured."
            fi
            ;;
        2)
            echo ""
            HUE_BRIDGE=$(ask "Hue Bridge IP address (e.g. 192.168.1.50)" "")
            HUE_TOKEN=$(ask "Hue API token (from your bridge)" "")
            if [ -n "$HUE_BRIDGE" ] && [ -n "$HUE_TOKEN" ]; then
                set_secret "HUE_BRIDGE_IP" "$HUE_BRIDGE"
                set_secret "HUE_TOKEN" "$HUE_TOKEN"
                set_secret "LIGHTS_BACKEND" "hue"
                echo "  ✓ Philips Hue configured."
            fi
            ;;
        3)
            echo ""
            HA_URL=$(ask "Home Assistant URL (e.g. http://homeassistant.local:8123)" "")
            HA_TOKEN=$(ask "HA long-lived access token" "")
            if [ -n "$HA_URL" ] && [ -n "$HA_TOKEN" ]; then
                set_secret "HA_URL" "$HA_URL"
                set_secret "HA_TOKEN" "$HA_TOKEN"
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

# ── 8. Music — Spotify ────────────────────────────────────────────────────────

MUSIC_CONSENT=$(python3 -c "import json; d=json.load(open('$CONSENT_FILE')); print(d.get('music',{}).get('approved', False))" 2>/dev/null || echo "False")

if [ "$MUSIC_CONSENT" = "True" ]; then
    section "Music — Tidecrest setup"

    echo "  Spotify integration uses the Spotify Web API."
    echo "  You'll need a free Spotify Developer account."
    echo ""
    echo "  Steps:"
    echo "    1. Go to developer.spotify.com/dashboard"
    echo "    2. Create an app (name: Enchantify, redirect: http://localhost:8888/callback)"
    echo "    3. Copy your Client ID and Client Secret"
    echo ""

    SPOTIFY_CLIENT=$(ask "Spotify Client ID (or press Enter to skip)" "")
    if [ -n "$SPOTIFY_CLIENT" ]; then
        set_secret "SPOTIFY_CLIENT_ID" "$SPOTIFY_CLIENT"
        SPOTIFY_SECRET=$(ask "Spotify Client Secret" "")
        [ -n "$SPOTIFY_SECRET" ] && set_secret "SPOTIFY_CLIENT_SECRET" "$SPOTIFY_SECRET"
        set_secret "MUSIC_BACKEND" "spotify"
        echo "  ✓ Spotify configured."
    else
        set_secret "MUSIC_BACKEND" "none"
        echo "  Skipped. Add Spotify credentials to config/secrets.env later."
    fi
fi

# ── 9. Voice Acting — Kokoro TTS ──────────────────────────────────────────────

section "Voice acting (optional)"

echo "  Enchantify has full multi-voice acting — every NPC has a voice."
echo "  This uses Kokoro TTS, a free local model (runs on your machine)."
echo "  Requires: Docker Desktop."
echo ""
echo "  Without this: Enchantify works silently (text only)."
echo ""

if command -v docker &>/dev/null; then
    echo "  ✓ Docker found."
    echo ""
    if ask_yn "Install Kokoro TTS for voice acting?" "n"; then
        write_consent "voice" "true"
        echo ""
        echo "  Pulling Kokoro TTS image (this may take a few minutes)..."
        docker pull ghcr.io/remsky/kokoro-fastapi-cpu:v0.2.2
        set_secret "TTS_BACKEND" "kokoro"
        set_secret "KOKORO_URL" "http://localhost:8880"
        echo ""
        echo "  ✓ Kokoro TTS installed."
        echo "  To start it: docker run -d -p 8880:8880 ghcr.io/remsky/kokoro-fastapi-cpu:v0.2.2"
        echo ""
        echo "  Add this to your startup items or run it manually before playing."
    else
        set_secret "TTS_BACKEND" "none"
        echo "  Voice acting skipped."
    fi
else
    echo "  Docker not found. Skipping voice acting."
    echo "  To enable later: install Docker Desktop, then run this wizard again."
    set_secret "TTS_BACKEND" "none"
fi

# ── 10. Image Generation ──────────────────────────────────────────────────────

section "Image generation (optional)"

echo "  The Labyrinth can generate images — portraits of NPCs, glimpses"
echo "  of locations, illustrations of story moments."
echo ""
echo "  Options:"
echo "    1) DALL-E 3 (OpenAI — best quality, requires API key + costs ~\$0.04/image)"
echo "    2) Stable Diffusion (local, free, requires good GPU and setup)"
echo "    3) None — text only"
echo ""

IMG_CHOICE=$(ask "Choose [1-3]" "3")

case "$IMG_CHOICE" in
    1)
        echo ""
        OPENAI_KEY=$(ask "OpenAI API key (from platform.openai.com)" "")
        if [ -n "$OPENAI_KEY" ]; then
            set_secret "OPENAI_API_KEY" "$OPENAI_KEY"
            set_secret "IMAGE_BACKEND" "dalle3"
            write_consent "images" "true"
            echo "  ✓ DALL-E 3 configured."
        else
            set_secret "IMAGE_BACKEND" "none"
            echo "  Skipped."
        fi
        ;;
    2)
        echo ""
        echo "  Stable Diffusion setup is manual. See docs/stable-diffusion.md"
        echo "  Set IMAGE_BACKEND=stable-diffusion in config/secrets.env when ready."
        set_secret "IMAGE_BACKEND" "stable-diffusion"
        ;;
    *)
        set_secret "IMAGE_BACKEND" "none"
        echo "  Image generation disabled."
        ;;
esac

# ── 11. Ambient Music — MusicGen ──────────────────────────────────────────────

section "Ambient music generation (optional)"

echo "  Meta MusicGen Small can generate ambient music for story scenes."
echo "  Requires Docker and ~2GB disk space."
echo ""

if command -v docker &>/dev/null; then
    if ask_yn "Install Meta MusicGen Small for ambient music?" "n"; then
        write_consent "ambient_music" "true"
        echo ""
        echo "  Pulling MusicGen image..."
        docker pull ghcr.io/enchantify/musicgen-small:latest 2>/dev/null || \
            echo "  (Image not yet available — will be set up on first run)"
        set_secret "MUSIC_GEN_BACKEND" "musicgen"
        echo "  ✓ MusicGen configured."
    else
        set_secret "MUSIC_GEN_BACKEND" "none"
        echo "  Ambient music skipped."
    fi
else
    set_secret "MUSIC_GEN_BACKEND" "none"
    echo "  Docker not found. Skipping MusicGen."
fi

# ── 12. Memory Plugins ────────────────────────────────────────────────────────

section "Memory plugins (optional)"

echo "  OpenClaw's built-in memory is solid. These plugins extend it:"
echo ""
echo "  QMD — hybrid BM25 + vector search, reduces token use 50-80%."
echo "  Lossless Claw — long-context SQLite persistence."
echo ""
echo "  These are recommended if you plan long, deep sessions."
echo ""

INSTALL_QMD=false
INSTALL_LC=false

if ask_yn "Install QMD memory plugin?" "y"; then
    INSTALL_QMD=true
fi
if ask_yn "Install Lossless Claw memory plugin?" "y"; then
    INSTALL_LC=true
fi

if [ "$INSTALL_QMD" = "true" ]; then
    echo "  Installing QMD..."
    openclaw plugins install qmd 2>/dev/null && echo "  ✓ QMD installed." || echo "  QMD install failed — try: openclaw plugins install qmd"
fi
if [ "$INSTALL_LC" = "true" ]; then
    echo "  Installing Lossless Claw..."
    openclaw plugins install @martian-engineering/Lossless-Claw 2>/dev/null && echo "  ✓ Lossless Claw installed." || echo "  Lossless Claw install failed — try: openclaw plugins install @martian-engineering/Lossless-Claw"
fi

# ── 13. Final Setup ───────────────────────────────────────────────────────────

section "Setting up your world"

echo "  Creating player file..."

if [ "$RETURNING" = "false" ] && [ -n "$PLAYER_NAME" ]; then
    PLAYER_FILE="$ENCHANTIFY_DIR/players/${PLAYER_NAME,,}.md"
    if [ ! -f "$PLAYER_FILE" ]; then
        if [ -f "$ENCHANTIFY_DIR/players/player-template.md" ]; then
            cp "$ENCHANTIFY_DIR/players/player-template.md" "$PLAYER_FILE"
            sed -i.bak "s/{{PLAYER_NAME}}/$PLAYER_NAME/g" "$PLAYER_FILE" && rm -f "${PLAYER_FILE}.bak"
            echo "  ✓ Player file created: players/${PLAYER_NAME,,}.md"
        else
            # Create minimal player file
            cat > "$PLAYER_FILE" << PLAYEREOF
# ${PLAYER_NAME}

**Player:** ${PLAYER_NAME}
**Tier:** 1
**Belief:** 0
**Status:** Just arrived.

## Notes
*Your story begins here.*
PLAYEREOF
            echo "  ✓ Player file created."
        fi
    fi
fi

echo "  Setting up cron job (world pulse every 15 minutes)..."

CRON_CMD="*/15 * * * * cd $ENCHANTIFY_DIR && /usr/bin/python3 scripts/pulse.py >> $LOGS_DIR/pulse.log 2>&1"
(crontab -l 2>/dev/null | grep -v "enchantify.*pulse.py"; echo "$CRON_CMD") | crontab -
echo "  ✓ Cron job installed."

echo "  Running first world pulse..."
cd "$ENCHANTIFY_DIR"
python3 scripts/pulse.py >> "$LOGS_DIR/pulse.log" 2>&1 && echo "  ✓ First pulse complete." || echo "  (Pulse had issues — check logs/pulse.log)"

# ── Done ─────────────────────────────────────────────────────────────────────

clear
echo ""
echo "  ╔══════════════════════════════════════════════════════════╗"
echo "  ║                                                          ║"
echo "  ║     ✨  The Labyrinth is ready.                         ║"
echo "  ║                                                          ║"
echo "  ╚══════════════════════════════════════════════════════════╝"
echo ""
echo "  Your world is alive. It's been breathing since the pulse ran."
echo ""
echo "  To begin:"
echo ""
echo "    openclaw"
echo ""
echo "    Then say: Open the book"
echo ""
echo "  ─────────────────────────────────────────────────────────"
echo ""
echo "  A few things to remember:"
echo "    • Say THORNE to pause all Pacts instantly"
echo "    • Your config is in: config/secrets.env"
echo "    • Your consent is in: config/consent.json"
echo "    • Logs live in: logs/"
echo ""
if [ -n "$PLAYER_NAME" ]; then
    echo "  The Labyrinth has been expecting you, $PLAYER_NAME."
    echo ""
fi
echo "  Good luck."
echo ""

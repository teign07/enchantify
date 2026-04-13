#!/bin/bash
# ================================================================
# Enchantify Uninstaller
# ================================================================
# Removes Enchantify from your system. By default removes only
# Enchantify-specific files. Pass flags to remove shared components.
#
# Usage:
#   bash scripts/uninstall.sh                  # Enchantify only
#   bash scripts/uninstall.sh --dry-run        # show what would change
#   bash scripts/uninstall.sh --keep-story     # archive player data first
#   bash scripts/uninstall.sh --with-voice     # also remove Kokoro TTS (~800MB)
#   bash scripts/uninstall.sh --with-memory    # also remove Lossless Claw + all LCM files
#   bash scripts/uninstall.sh --with-openclaw  # remove everything including OpenClaw
#   bash scripts/uninstall.sh --yes            # skip all confirmation prompts
#
# ⚠ --with-memory removes conversation history for ALL OpenClaw agents, not just Enchantify.
# ⚠ --with-openclaw implies --with-voice and --with-memory.
# ================================================================

set -euo pipefail

# ── Colours ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
YEL='\033[0;33m'
GRN='\033[0;32m'
DIM='\033[2m'
BLD='\033[1m'
RST='\033[0m'

# ── Parse flags ────────────────────────────────────────────────────────────────
DRY_RUN=false
KEEP_STORY=false
WITH_VOICE=false
WITH_MEMORY=false
WITH_OPENCLAW=false
YES=false

for arg in "$@"; do
    case "$arg" in
        --dry-run)       DRY_RUN=true ;;
        --keep-story)    KEEP_STORY=true ;;
        --with-voice)    WITH_VOICE=true ;;
        --with-memory)   WITH_MEMORY=true ;;
        --with-openclaw) WITH_OPENCLAW=true; WITH_VOICE=true; WITH_MEMORY=true ;;
        --yes)           YES=true ;;
        --help|-h)
            grep "^#" "$0" | head -20 | sed 's/^# \?//'
            exit 0
            ;;
        *)
            echo "Unknown flag: $arg  (use --help)" >&2
            exit 1
            ;;
    esac
done

# ── Helpers ────────────────────────────────────────────────────────────────────

log()    { echo -e "${DIM}[uninstall]${RST} $*"; }
ok()     { echo -e "${GRN}  ✓${RST} $*"; }
skip()   { echo -e "${DIM}  — $*${RST}"; }
warn()   { echo -e "${YEL}  ⚠${RST} $*"; }
err()    { echo -e "${RED}  ✗${RST} $*"; }
drylog() { echo -e "${DIM}  [dry-run] would remove: $*${RST}"; }

remove_path() {
    local p="$1"
    local label="${2:-$1}"
    if [ -e "$p" ] || [ -L "$p" ]; then
        if $DRY_RUN; then
            drylog "$label"
        else
            rm -rf "$p"
            ok "Removed $label"
        fi
    else
        skip "$label (not found)"
    fi
}

confirm() {
    if $YES; then return 0; fi
    echo -ne "${BLD}$1${RST} [y/N] "
    read -r ans
    [[ "$ans" =~ ^[Yy] ]]
}

dir_size() {
    du -sh "$1" 2>/dev/null | cut -f1 || echo "?"
}

# ── Paths ──────────────────────────────────────────────────────────────────────
OPENCLAW_DIR="$HOME/.openclaw"
AGENT_DIR="$OPENCLAW_DIR/agents/enchantify"
WORKSPACE="$OPENCLAW_DIR/workspace/enchantify"
GLASS_DIR="$OPENCLAW_DIR/workspace/enchantify-glass"
KOKORO_DIR="$OPENCLAW_DIR/workspace/tools/Kokoro-FastAPI"
LCM_EXT="$OPENCLAW_DIR/extensions/lossless-claw"
LCM_DB="$OPENCLAW_DIR/lcm.db"
LCM_DB_SHM="$OPENCLAW_DIR/lcm.db-shm"
LCM_DB_WAL="$OPENCLAW_DIR/lcm.db-wal"
LCM_FILES="$OPENCLAW_DIR/lcm-files"

# ── Header ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BLD}=================================================${RST}"
echo -e "${BLD}   Enchantify Uninstaller${RST}"
$DRY_RUN && echo -e "${YEL}   DRY RUN — no changes will be made${RST}"
echo -e "${BLD}=================================================${RST}"
echo ""

# ── Inventory ──────────────────────────────────────────────────────────────────
echo -e "${BLD}What will be removed:${RST}"
echo ""
echo -e "  ${BLD}Enchantify (always):${RST}"
[ -d "$WORKSPACE" ]  && echo "    • Workspace          $WORKSPACE  ($(dir_size "$WORKSPACE"))"
[ -d "$GLASS_DIR" ]  && echo "    • Glass UI           $GLASS_DIR  ($(dir_size "$GLASS_DIR"))"
[ -d "$AGENT_DIR" ]  && echo "    • Agent + sessions   $AGENT_DIR  ($(dir_size "$AGENT_DIR"))"

MEDIA_COUNT=$(ls "$OPENCLAW_DIR"/media/enchantify_* 2>/dev/null | wc -l | tr -d ' ')
[ "$MEDIA_COUNT" -gt 0 ] && echo "    • Audio files        $MEDIA_COUNT enchantify_*.mp3 in $OPENCLAW_DIR/media/"

CRON_LINES=$(crontab -l 2>/dev/null | grep -c enchantify 2>/dev/null || echo 0)
[ "$CRON_LINES" -gt 0 ] && echo "    • Cron entries       $CRON_LINES job(s)"

echo ""

if $WITH_VOICE || $WITH_OPENCLAW; then
    echo -e "  ${BLD}Voice (--with-voice):${RST}"
    [ -d "$KOKORO_DIR" ] && echo "    • Kokoro TTS         $KOKORO_DIR  ($(dir_size "$KOKORO_DIR"))" \
        || echo "    • Kokoro TTS         (not found)"
    echo ""
fi

if $WITH_MEMORY || $WITH_OPENCLAW; then
    echo -e "  ${BLD}Conversation Memory (--with-memory):${RST}"
    [ -d "$LCM_EXT" ]   && echo "    • Lossless Claw ext  $LCM_EXT"
    [ -f "$LCM_DB" ]    && echo "    • LCM database       $LCM_DB  (all agents)"
    [ -d "$LCM_FILES" ] && echo "    • LCM files          $LCM_FILES  ($(ls "$LCM_FILES" 2>/dev/null | wc -l | tr -d ' ') files, all agents)"
    echo ""
fi

if $WITH_OPENCLAW; then
    echo -e "  ${BLD}OpenClaw (--with-openclaw):${RST}"
    [ -d "$OPENCLAW_DIR" ] && echo "    • OpenClaw directory $OPENCLAW_DIR  ($(dir_size "$OPENCLAW_DIR"))"
    command -v openclaw &>/dev/null && echo "    • openclaw (npm global)"
    command -v clawhub  &>/dev/null && echo "    • clawhub  (npm global)"
    echo ""
fi

# ── Player data ────────────────────────────────────────────────────────────────
PLAYER_DIR="$WORKSPACE/players"
if [ -d "$PLAYER_DIR" ] && [ "$(ls -A "$PLAYER_DIR" 2>/dev/null)" ]; then
    echo -e "${YEL}  ⚠  Player data detected in $PLAYER_DIR${RST}"
    echo -e "${YEL}     This contains your story, Belief progress, anchors, and diary.${RST}"
    echo ""

    if $KEEP_STORY || confirm "  Archive player data to ~/Desktop before removing?"; then
        BACKUP_DIR="$HOME/Desktop/enchantify-story-$(date +%Y-%m-%d)"
        if $DRY_RUN; then
            drylog "archive players/ + memory/ + key lore → $BACKUP_DIR"
        else
            mkdir -p "$BACKUP_DIR"
            cp -r "$PLAYER_DIR"                          "$BACKUP_DIR/players"       2>/dev/null || true
            cp -r "$WORKSPACE/memory"                    "$BACKUP_DIR/memory"        2>/dev/null || true
            cp    "$WORKSPACE/lore/current-arc.md"       "$BACKUP_DIR/"              2>/dev/null || true
            cp    "$WORKSPACE/lore/threads.md"           "$BACKUP_DIR/"              2>/dev/null || true
            cp    "$WORKSPACE/lore/academy-state.md"     "$BACKUP_DIR/"              2>/dev/null || true
            cp    "$WORKSPACE/lore/nothing-intelligence.md" "$BACKUP_DIR/"           2>/dev/null || true
            ok "Story archived → $BACKUP_DIR"
        fi
    fi
    echo ""
fi

# ── Shared component warnings ──────────────────────────────────────────────────
if $WITH_MEMORY && ! $WITH_OPENCLAW; then
    echo -e "${RED}  ⚠  --with-memory will delete conversation history for ALL OpenClaw agents,${RST}"
    echo -e "${RED}     not just Enchantify (scribe, athena, etc. conversations included).${RST}"
    echo ""
    if ! confirm "  Remove all Lossless Claw data?"; then
        WITH_MEMORY=false
        ok "Lossless Claw data kept"
        echo ""
    fi
fi

if $WITH_OPENCLAW; then
    OTHER_AGENTS=$(ls "$OPENCLAW_DIR/agents/" 2>/dev/null | grep -v enchantify | tr '\n' ' ' || true)
    if [ -n "$OTHER_AGENTS" ]; then
        warn "Other OpenClaw agents will also be removed: $OTHER_AGENTS"
        echo ""
        if ! $YES; then
            if ! confirm "  Remove OpenClaw and all agents?"; then
                echo "Aborted."
                exit 0
            fi
        fi
    fi
fi

# ── Final confirmation ─────────────────────────────────────────────────────────
if ! $DRY_RUN && ! $YES; then
    echo -e "${RED}${BLD}This cannot be undone (except for the archived story data).${RST}"
    confirm "  Begin uninstall?" || { echo "Aborted."; exit 0; }
    echo ""
fi

# ════════════════════════════════════════════════════════════════════════════════
# REMOVALS
# ════════════════════════════════════════════════════════════════════════════════

# ── Step 1: Cron ───────────────────────────────────────────────────────────────
echo -e "${BLD}[1/6] Cron entries${RST}"
if crontab -l 2>/dev/null | grep -q enchantify; then
    if $DRY_RUN; then
        echo "  [dry-run] would remove:"
        crontab -l 2>/dev/null | grep enchantify | sed 's/^/    /'
    else
        crontab -l 2>/dev/null | grep -v enchantify | crontab -
        ok "Enchantify cron entries removed"
    fi
else
    skip "No enchantify cron entries"
fi
echo ""

# ── Step 2: Workspace + Glass ──────────────────────────────────────────────────
echo -e "${BLD}[2/6] Workspace & Glass UI${RST}"
remove_path "$WORKSPACE"  "enchantify workspace"
remove_path "$GLASS_DIR"  "enchantify-glass"
echo ""

# ── Step 3: Agent ─────────────────────────────────────────────────────────────
echo -e "${BLD}[3/6] OpenClaw agent${RST}"
remove_path "$AGENT_DIR"  "enchantify agent (sessions, qmd memory)"
echo ""

# ── Step 4: Media ─────────────────────────────────────────────────────────────
echo -e "${BLD}[4/6] Media files${RST}"
if ls "$OPENCLAW_DIR"/media/enchantify_* &>/dev/null; then
    if $DRY_RUN; then
        COUNT=$(ls "$OPENCLAW_DIR"/media/enchantify_* 2>/dev/null | wc -l | tr -d ' ')
        drylog "$COUNT enchantify audio files"
    else
        rm -f "$OPENCLAW_DIR"/media/enchantify_*
        ok "Enchantify audio files removed"
    fi
else
    skip "No enchantify audio files"
fi
echo ""

# ── Step 5: Voice (Kokoro) ────────────────────────────────────────────────────
echo -e "${BLD}[5/6] Voice / Kokoro TTS${RST}"
if $WITH_VOICE; then
    remove_path "$KOKORO_DIR" "Kokoro-FastAPI (model + venv)"
else
    skip "Kokoro kept (pass --with-voice to remove)"
fi
echo ""

# ── Step 6: Memory (Lossless Claw) ───────────────────────────────────────────
echo -e "${BLD}[6/6] Conversation memory (Lossless Claw)${RST}"
if $WITH_MEMORY; then
    remove_path "$LCM_EXT"   "lossless-claw extension"
    remove_path "$LCM_DB"    "lcm.db"
    remove_path "$LCM_DB_SHM" "lcm.db-shm"
    remove_path "$LCM_DB_WAL" "lcm.db-wal"
    remove_path "$LCM_FILES" "lcm-files/"
else
    skip "Lossless Claw kept (pass --with-memory to remove)"
fi
echo ""

# ── OpenClaw itself ───────────────────────────────────────────────────────────
if $WITH_OPENCLAW; then
    echo -e "${BLD}[+] OpenClaw${RST}"
    remove_path "$OPENCLAW_DIR" "OpenClaw directory (~/.openclaw)"

    if command -v openclaw &>/dev/null; then
        if $DRY_RUN; then
            drylog "npm uninstall -g openclaw"
        else
            npm uninstall -g openclaw 2>/dev/null \
                && ok "openclaw npm package removed" \
                || warn "Could not remove openclaw via npm — run: npm uninstall -g openclaw"
        fi
    else
        skip "openclaw npm package (not found)"
    fi

    if command -v clawhub &>/dev/null; then
        if $DRY_RUN; then
            drylog "npm uninstall -g clawhub"
        else
            npm uninstall -g clawhub 2>/dev/null \
                && ok "clawhub npm package removed" \
                || warn "Could not remove clawhub via npm — run: npm uninstall -g clawhub"
        fi
    else
        skip "clawhub npm package (not found)"
    fi
    echo ""
fi

# ── Done ───────────────────────────────────────────────────────────────────────
echo -e "${BLD}=================================================${RST}"
if $DRY_RUN; then
    echo -e "${YEL}  Dry run complete — no changes made.${RST}"
    echo ""
    echo "  Re-run without --dry-run to actually uninstall."
else
    echo -e "${GRN}${BLD}  Done.${RST}"
    echo ""
    if [ -n "${BACKUP_DIR:-}" ] && [ -d "${BACKUP_DIR:-/nonexistent}" ]; then
        echo -e "  Your story was archived to:"
        echo -e "  ${BLD}$BACKUP_DIR${RST}"
        echo ""
    fi
    echo -e "${DIM}  Manual steps (if applicable):${RST}"
    echo -e "${DIM}  • Telegram bot: BotFather → /mybots → Delete Bot${RST}"
    echo -e "${DIM}  • LIFX / Spotify: local-only, no accounts affected${RST}"
    if ! $WITH_MEMORY; then
        echo -e "${DIM}  • Lossless Claw conversation history kept in ~/.openclaw/lcm.db${RST}"
        echo -e "${DIM}    Remove with: bash scripts/uninstall.sh --with-memory${RST}"
    fi
    if ! $WITH_VOICE; then
        echo -e "${DIM}  • Kokoro TTS kept in ~/.openclaw/workspace/tools/Kokoro-FastAPI${RST}"
        echo -e "${DIM}    Remove with: bash scripts/uninstall.sh --with-voice${RST}"
    fi
fi
echo -e "${BLD}=================================================${RST}"
echo ""

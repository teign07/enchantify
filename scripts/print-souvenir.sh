#!/bin/bash
# print-souvenir.sh — Print a Compass Run souvenir card
# Usage: bash scripts/print-souvenir.sh [souvenir-file.md]
# If no file given, prints the most recent file in souvenirs/

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(dirname "$SCRIPT_DIR")"
SOUVENIRS_DIR="$WORKSPACE_DIR/souvenirs"

# Read printer from config, fall back to sensible defaults
CONFIG_FILE="$SCRIPT_DIR/enchantify-config.sh"
PRINTER=""
BACKUP_PRINTER=""
if [ -f "$CONFIG_FILE" ]; then
    PRINTER=$(grep "^ENCHANTIFY_PRINTER=" "$CONFIG_FILE" 2>/dev/null | cut -d= -f2- | tr -d '"')
    BACKUP_PRINTER=$(grep "^ENCHANTIFY_PRINTER_BACKUP=" "$CONFIG_FILE" 2>/dev/null | cut -d= -f2- | tr -d '"')
fi
PRINTER="${PRINTER:-Silvie_s_Printer}"
BACKUP_PRINTER="${BACKUP_PRINTER:-Canon_MG3600_series_backup}"
TEMP_HTML="/tmp/enchantify-souvenir-$$.html"

# Find the file to print
if [ -n "$1" ] && [ -f "$1" ]; then
    SOUVENIR_FILE="$1"
elif [ -n "$1" ] && [ -f "$SOUVENIRS_DIR/$1" ]; then
    SOUVENIR_FILE="$SOUVENIRS_DIR/$1"
else
    # Most recent souvenir
    SOUVENIR_FILE=$(ls -t "$SOUVENIRS_DIR"/*.md 2>/dev/null | head -1)
fi

if [ -z "$SOUVENIR_FILE" ] || [ ! -f "$SOUVENIR_FILE" ]; then
    echo "❌ No souvenir file found. Pass a filename or run a Compass Run first."
    exit 1
fi

echo "📖 Printing souvenir: $(basename "$SOUVENIR_FILE")"

# Read the souvenir content
CONTENT=$(cat "$SOUVENIR_FILE")

# Extract key fields for the card
PLAYER=$(echo "$CONTENT" | grep -m1 "^\*\*Player:\*\*" | sed 's/\*\*Player:\*\* //')
DATE=$(echo "$CONTENT" | grep -m1 "^## Compass Run" | sed 's/## Compass Run — //')
CHAPTER=$(echo "$CONTENT" | grep -m1 "^\*\*Chapter:\*\*" | sed 's/\*\*Chapter:\*\* //')
WEATHER=$(echo "$CONTENT" | grep -m1 "^\*\*Weather:\*\*" | sed 's/\*\*Weather:\*\* //')
SEASON=$(echo "$CONTENT" | grep -m1 "^\*\*Season:\*\*" | sed 's/\*\*Season:\*\* //')
MOON=$(echo "$CONTENT" | grep -m1 "^\*\*Moon:\*\*" | sed 's/\*\*Moon:\*\* //')
SOUVENIR=$(echo "$CONTENT" | grep -m1 "^\*\*Souvenir:\*\*" | sed 's/\*\*Souvenir:\*\* //' | tr -d '"')
BELIEF=$(echo "$CONTENT" | grep -m1 "^\*\*Belief before:\*\*" | sed 's/\*\*Belief before:\*\* //')

# If no souvenir line extracted, try the West section
if [ -z "$SOUVENIR" ]; then
    SOUVENIR=$(echo "$CONTENT" | awk '/### West — Write/,/###/' | grep -m1 '^\- \*\*Souvenir:\*\*' | sed 's/- \*\*Souvenir:\*\* //' | tr -d '"')
fi

# Generate a clean HTML card for printing
cat > "$TEMP_HTML" << HTMLEOF
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  @page {
    size: 4in 6in;
    margin: 0.3in;
  }
  body {
    font-family: "Georgia", serif;
    font-size: 11pt;
    color: #1a1a2e;
    background: #faf8f3;
    margin: 0;
    padding: 0;
  }
  .card {
    border: 2px solid #3d2c6b;
    border-radius: 8px;
    padding: 16px 18px;
    background: #faf8f3;
    min-height: 90%;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }
  .header {
    text-align: center;
    border-bottom: 1px solid #ccc;
    padding-bottom: 8px;
    margin-bottom: 10px;
  }
  .header h1 {
    font-size: 13pt;
    color: #3d2c6b;
    margin: 0 0 2px 0;
    letter-spacing: 0.05em;
  }
  .header .subtitle {
    font-size: 9pt;
    color: #888;
    font-style: italic;
  }
  .meta {
    font-size: 9pt;
    color: #555;
    line-height: 1.6;
    margin-bottom: 12px;
  }
  .meta span {
    display: inline-block;
    margin-right: 8px;
  }
  .souvenir-box {
    border-left: 3px solid #3d2c6b;
    padding: 10px 14px;
    background: #f0ecf8;
    border-radius: 0 6px 6px 0;
    margin: 10px 0;
    flex-grow: 1;
  }
  .souvenir-text {
    font-size: 12pt;
    font-style: italic;
    color: #1a1a2e;
    line-height: 1.5;
  }
  .footer {
    text-align: center;
    font-size: 8pt;
    color: #aaa;
    border-top: 1px solid #eee;
    padding-top: 6px;
    margin-top: 10px;
    font-style: italic;
  }
  .compass {
    display: flex;
    justify-content: center;
    font-size: 18pt;
    letter-spacing: 0.2em;
    color: #3d2c6b;
    margin: 6px 0;
  }
  .player-info {
    font-size: 10pt;
    color: #3d2c6b;
    font-weight: bold;
  }
  .belief-badge {
    display: inline-block;
    background: #3d2c6b;
    color: white;
    font-size: 8pt;
    padding: 2px 8px;
    border-radius: 10px;
    float: right;
  }
</style>
</head>
<body>
<div class="card">
  <div class="header">
    <h1>✦ Compass Run ✦</h1>
    <div class="subtitle">Enchantify Academy — One-Sentence Souvenir</div>
  </div>

  <div>
    <span class="player-info">${PLAYER:-The Reader}</span>
    <span class="belief-badge">+9 Belief</span>
    <div style="clear:both"></div>
    <div style="font-size:9pt; color:#888; margin-top:2px;">
      ${CHAPTER:-Tidecrest} &nbsp;·&nbsp; ${DATE:-Today}
    </div>
  </div>

  <div class="meta" style="margin-top:10px;">
    🌤 ${WEATHER:-—} &nbsp;·&nbsp; 🌙 ${MOON:-—} &nbsp;·&nbsp; 🌿 ${SEASON:-—}
  </div>

  <div class="souvenir-box">
    <div class="souvenir-text">"${SOUVENIR:-A moment worth keeping.}"</div>
  </div>

  <div class="compass">N ↑ E → S ↓ W ←</div>

  <div class="footer">
    The Labyrinth of Stories &nbsp;·&nbsp; This page will never go blank.
  </div>
</div>
</body>
</html>
HTMLEOF

echo "🎨 Card generated. Sending to printer..."

# Try primary printer, fall back to backup
if lpstat -p "$PRINTER" &>/dev/null; then
    lp -d "$PRINTER" \
       -o media=Custom.4x6in \
       -o fit-to-page \
       "$TEMP_HTML" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "✅ Printed to $PRINTER"
    else
        echo "⚠️  Primary printer failed. Trying $BACKUP_PRINTER..."
        lp -d "$BACKUP_PRINTER" -o fit-to-page "$TEMP_HTML"
    fi
else
    echo "⚠️  $PRINTER not available. Trying $BACKUP_PRINTER..."
    lp -d "$BACKUP_PRINTER" -o fit-to-page "$TEMP_HTML"
fi

# Clean up
rm -f "$TEMP_HTML"
echo "📖 Done. The souvenir is physical now."

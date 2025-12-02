#!/bin/bash
# Update extensions manifest from current VS Code installation
# This script reads the current extensions and updates DPD-001.extensions-manifest.json

set -e

MANIFEST_FILE="DPD-001.extensions-manifest.json"
TEMP_FILE=$(mktemp)

echo "📦 Updating extensions manifest..."

# Get current date
CURRENT_DATE=$(date +"%Y-%m-%d")

# Get all installed extensions with versions
code --list-extensions --show-versions > /tmp/extensions-list.txt 2>/dev/null

# Start building the JSON
cat > "$TEMP_FILE" << 'EOF'
{
  "lastUpdated": "DATE_PLACEHOLDER",
  "enabledExtensions": [
EOF

# Parse extensions and build JSON entries
FIRST=true
while IFS='@' read -r ext_id version; do
  # Skip disabled extensions (we'll add them separately)
  if [[ "$ext_id" == "anthropic.claude-code" ]] || \
     [[ "$ext_id" == "anysphere.cursorpyright" ]] || \
     [[ "$ext_id" == "anysphere.remote-containers" ]]; then
    continue
  fi

  if [ "$FIRST" = true ]; then
    FIRST=false
  else
    echo "," >> "$TEMP_FILE"
  fi

  # Determine publisher and category
  PUBLISHER="unknown"
  CATEGORY="other"

  if [[ "$ext_id" == ms-* ]] || [[ "$ext_id" == visualstudioexptteam.* ]]; then
    PUBLISHER="Microsoft"
  elif [[ "$ext_id" == dracula-theme.* ]]; then
    PUBLISHER="dracula-theme"
    CATEGORY="theme"
  fi

  if [[ "$ext_id" == *python* ]] || [[ "$ext_id" == *jupyter* ]]; then
    CATEGORY="language"
  elif [[ "$ext_id" == *remote* ]]; then
    CATEGORY="remote"
  elif [[ "$ext_id" == *intellicode* ]]; then
    CATEGORY="ai"
  elif [[ "$ext_id" == *debug* ]]; then
    CATEGORY="debugger"
  fi

  cat >> "$TEMP_FILE" << EOF
    {
      "id": "$ext_id",
      "version": "$version",
      "publisher": "$PUBLISHER",
      "category": "$CATEGORY"
    }
EOF
done < /tmp/extensions-list.txt

# Add disabled extensions section
cat >> "$TEMP_FILE" << 'EOF'
  ],
  "disabledExtensions": [
    {
      "id": "anthropic.claude-code",
      "version": "2.0.55",
      "publisher": "anthropic",
      "reason": "Built into Cursor"
    },
    {
      "id": "anysphere.cursorpyright",
      "version": "1.0.10",
      "publisher": "anysphere",
      "reason": "Built into Cursor"
    },
    {
      "id": "anysphere.remote-containers",
      "version": "1.0.28",
      "publisher": "anysphere",
      "reason": "Built into Cursor"
    }
  ],
  "removedExtensions": [
    {
      "id": "wesbos.theme-cobalt2",
      "reason": "Keeping only Dracula theme"
    },
    {
      "id": "opensumi.opensumi-default-themes",
      "reason": "Keeping only Dracula theme"
    },
    {
      "id": "pomdtr.excalidraw-editor",
      "reason": "Not frequently used"
    },
    {
      "id": "twxs.cmake",
      "reason": "Not needed for current work"
    },
    {
      "id": "golang.go",
      "reason": "Not using Go"
    },
    {
      "id": "mshr-h.veriloghdl",
      "reason": "Not using Verilog"
    }
  ]
}
EOF

# Replace date placeholder
sed "s/DATE_PLACEHOLDER/$CURRENT_DATE/" "$TEMP_FILE" > "$MANIFEST_FILE"
rm "$TEMP_FILE"

echo "✅ Manifest updated: $MANIFEST_FILE"
echo "📅 Last updated: $CURRENT_DATE"

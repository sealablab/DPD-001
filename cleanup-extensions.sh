#!/bin/bash
# VS Code Extension Cleanup Script
# This script will:
# 1. Remove extra themes (keeping Dracula)
# 2. Disable Cursor-specific extensions
# 3. Remove specialized tools and language extensions

set -e

echo "🧹 Starting VS Code extension cleanup..."
echo ""

# 1. Remove extra themes (keeping Dracula)
echo "📦 Removing extra themes..."
code --uninstall-extension wesbos.theme-cobalt2 2>/dev/null || echo "  ⚠️  Cobalt2 theme not found or already removed"
code --uninstall-extension opensumi.opensumi-default-themes 2>/dev/null || echo "  ⚠️  OpenSumi themes not found or already removed"
echo "  ✅ Keeping Dracula theme"
echo ""

# 2. Disable Cursor-specific extensions
echo "🔌 Disabling Cursor-specific extensions..."
code --disable-extension anthropic.claude-code 2>/dev/null || echo "  ⚠️  Claude Code extension not found"
code --disable-extension anysphere.cursorpyright 2>/dev/null || echo "  ⚠️  CursorPyright extension not found"
code --disable-extension anysphere.remote-containers 2>/dev/null || echo "  ⚠️  Remote Containers extension not found"
echo ""

# 3. Remove specialized tools and language extensions
echo "🗑️  Removing specialized tools and language extensions..."
code --uninstall-extension pomdtr.excalidraw-editor 2>/dev/null || echo "  ⚠️  Excalidraw editor not found or already removed"
code --uninstall-extension twxs.cmake 2>/dev/null || echo "  ⚠️  CMake extension not found or already removed"
code --uninstall-extension golang.go 2>/dev/null || echo "  ⚠️  Go extension not found or already removed"
code --uninstall-extension mshr-h.veriloghdl 2>/dev/null || echo "  ⚠️  VerilogHDL extension not found or already removed"
echo ""

echo "✅ Cleanup complete!"
echo ""
echo "📋 Remaining extensions:"
code --list-extensions

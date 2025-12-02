# `.vscode/` Directory

This directory contains **baseline settings** that work in both VS Code and Cursor.

## Contents

- **`settings.json`** - Editor, file explorer, language, terminal, and git settings
- **`extensions.json`** - Extension recommendations (enabled and disabled extensions)

## Why `.vscode/`?

Since Cursor is based on VS Code, it reads `.vscode/` settings automatically. This means:
- ✅ Settings work in both VS Code and Cursor
- ✅ Standard location that other developers expect
- ✅ Version control friendly
- ✅ Shareable across team members using either editor

## Organization

- **Baseline settings** → `.vscode/` (this directory)
- **Cursor-specific customizations** → `.cursor/` (keybindings, workspace files, etc.)

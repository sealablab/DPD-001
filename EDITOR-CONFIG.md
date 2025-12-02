# Editor Configuration Organization

This document explains how editor settings are organized in this project.

## Directory Structure

```
.vscode/              # Baseline settings (VS Code + Cursor compatible)
├── settings.json     # Editor, file explorer, language, terminal settings
├── extensions.json   # Extension recommendations
└── README.md         # Documentation

.cursor/              # Cursor-specific customizations
├── keybindings.json  # Custom keybindings
├── settings.json     # Placeholder (baseline moved to .vscode/)
├── DPD-001.code-workspace  # Workspace file (if needed)
└── README.md         # Documentation
```

## Philosophy

**Baseline settings** → `.vscode/` (works in both VS Code and Cursor)
- Editor preferences (fonts, themes, behavior)
- File explorer settings
- Language-specific settings (Python, VHDL, Markdown, etc.)
- Terminal configuration
- Git settings
- Extension recommendations

**Cursor-specific** → `.cursor/` (Cursor-only customizations)
- Custom keybindings
- Workspace files (if using multi-root workspaces)
- Cursor-specific overrides (if any)

## Why This Organization?

1. **Compatibility**: `.vscode/` is the standard location that both VS Code and Cursor read
2. **Clarity**: Clear separation between shared and Cursor-specific settings
3. **Version Control**: Both directories can be committed, but `.vscode/` is more universal
4. **Team Collaboration**: Other developers using VS Code will automatically get the baseline settings

## Migration Notes

- All comprehensive settings from `.cursor/settings.json` were moved to `.vscode/settings.json`
- `.cursor/settings.json` is now a placeholder for future Cursor-specific overrides
- Keybindings remain in `.cursor/` as they're workflow-specific customizations

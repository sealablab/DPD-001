# Workspace Files vs `.cursor/` Directory

## Quick Comparison

| Feature | `.cursor/` Directory | `.code-workspace` File |
|---------|---------------------|------------------------|
| **Auto-applied** | ✅ Yes (when opening folder) | ❌ No (must open explicitly) |
| **Multi-root workspaces** | ❌ No | ✅ Yes (multiple folders) |
| **Folder-specific settings** | ❌ No | ✅ Yes (per folder) |
| **Extension recommendations** | ❌ No | ✅ Yes |
| **Tasks (build/test)** | ✅ Yes (`.cursor/tasks.json`) | ✅ Yes (in workspace file) |
| **Launch configs (debug)** | ✅ Yes (`.cursor/launch.json`) | ✅ Yes (in workspace file) |
| **Snippets** | ✅ Yes (`.cursor/snippets/`) | ✅ Yes (`.cursor/snippets/`) |
| **Keybindings** | ✅ Yes (`.cursor/keybindings.json`) | ✅ Yes (`.cursor/keybindings.json`) |
| **Settings** | ✅ Yes (`.cursor/settings.json`) | ✅ Yes (in workspace file) |
| **Version control friendly** | ✅ Yes | ✅ Yes |
| **Shareable** | ✅ Yes | ✅ Yes (single file) |

## When to Use `.cursor/` Directory

**Best for:**
- ✅ Single-folder projects
- ✅ Simple setup that "just works"
- ✅ When you want automatic application
- ✅ Most common use case

**How it works:**
- Open folder → Cursor automatically reads `.cursor/settings.json`
- No extra steps needed
- Settings apply immediately

## When to Use `.code-workspace` File

**Best for:**
- ✅ **Multi-root workspaces** (multiple folders in one window)
- ✅ **Monorepos** (frontend + backend + shared libs)
- ✅ **Team collaboration** (extension recommendations)
- ✅ **Complex projects** with different settings per folder
- ✅ **Build/debug configurations** you want in one place

**Example use cases:**

### 1. Multi-Root Workspace
```json
{
  "folders": [
    { "path": ".", "name": "Main Project" },
    { "path": "../shared-lib", "name": "Shared Library" },
    { "path": "../docs", "name": "Documentation" }
  ]
}
```

### 2. Folder-Specific Settings
```json
{
  "folders": [
    {
      "path": ".",
      "settings": {
        "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python"
      }
    },
    {
      "path": "../legacy-code",
      "settings": {
        "editor.tabSize": 8  // Different for legacy code!
      }
    }
  ]
}
```

### 3. Team Extension Recommendations
```json
{
  "extensions": {
    "recommendations": [
      "ms-python.python",
      "ms-python.black-formatter"
    ]
  }
}
```

### 4. Integrated Tasks & Launch Configs
```json
{
  "tasks": { /* build/test tasks */ },
  "launch": { /* debug configurations */ }
}
```

## Your Current Setup

You have **both** approaches set up:

1. **`.cursor/settings.json`** - Auto-applied when opening folder
2. **`.cursor/keybindings.json`** - Auto-applied when opening folder  
3. **`.cursor/DPD-001.code-workspace`** - Available if you want workspace features

**Recommendation for your project:**
- **Use `.cursor/` directory** (just open folder) - simpler, works great
- **Keep workspace file** if you later need:
  - Multiple folders (e.g., add `libs/moku-models-v4` as separate root)
  - Team extension recommendations
  - Integrated tasks/launch configs

## Can They Work Together?

**Yes!** Priority order:
1. Folder-specific settings (in workspace file)
2. Workspace settings (in workspace file)
3. `.cursor/settings.json` (directory settings)
4. User settings (global)

Settings cascade, so workspace file can override directory settings if needed.


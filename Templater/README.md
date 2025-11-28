# Templater

This directory contains all Obsidian Templater-related files for the DPD-001 project.

## Structure

```
Templater/
├── Templates/          # Actual template files (point Templater here)
│   ├── user_scripts/   # JavaScript modules for templates
│   └── times_debug/   # Debug templates (optional)
└── docs/              # Documentation for templates
```

## Quick Start

### For Users

1. **Configure Templater:**
   - Settings → Plugins → Templater
   - Set **Template folder location** to: `Templater/Templates`
   - Set **User scripts folder location** to: `Templater/Templates/user_scripts`

2. **Create a VHDL Component:**
   - `CMD-P` → `Templater: Create new note from template`
   - Select: `new_vhdl_component`
   - Follow prompts

### Available Templates

- **`new_vhdl_component.md`** ⭐ - Create paired VHDL component files
- **`base.md`** - Standard base template with frontmatter
- **`00_times_startup_hook.md`** - Startup hook (auto-runs)

## Documentation

See `docs/` folder for detailed documentation:
- VHDL pair template system
- Frontmatter time fields
- Configuration guides

## User Scripts

The `Templates/user_scripts/` folder contains JavaScript modules:
- `templater_times.js` - Frontmatter time management
- `templater_vhdl_pair.js` - VHDL pair creation helpers
- `templater_internal_module.js` - Internal utilities

These are loaded automatically by Templater when templates use them.


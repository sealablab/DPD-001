# Templater Configuration Guide

## Problem

Templater is showing too many files in the template selection menu, including:
- User scripts (`.js` files in `user_scripts/`)
- Documentation files (`.md` files that aren't templates)

## Solution: Configure Templater Exclusions

### Step 1: Open Templater Settings

1. Open Obsidian Settings (`CMD-,`)
2. Go to **Plugins** → **Templater**
3. Click **Settings**

### Step 2: Configure Template Folder

Ensure **Template folder location** is set to: `Templater/Templates`

Also set **User scripts folder location** to: `Templater/Templates/user_scripts`

### Step 3: Add Exclusion Patterns

In the Templater settings, look for **"Exclude files from template list"** or similar option.

If available, add these exclusion patterns:

```
user_scripts/**
_docs/**
times_debug/**
*.js
*README*.md
*QUICKSTART*.md
*_TEMPLATE*.md
```

### Alternative: File Organization

Files are now organized in a cleaner structure:

- ✅ **`Templater/Templates/`**: Actual template files (point Templater here)
- 📁 **`Templater/docs/`**: Documentation files (separate from templates)
- 📁 **`Templater/Templates/user_scripts/`**: JavaScript modules (needed for templates to work)
- 📁 **`Templater/Templates/times_debug/`**: Debug templates (optional)

### Manual Exclusion (If Needed)

If your Templater version doesn't support exclusion patterns:

1. Move documentation to `_docs/` subfolder (already done)
2. Consider moving `times_debug/` to a different location if you don't use debug templates
3. User scripts must stay in `user_scripts/` for templates to work, but they shouldn't appear as templates if they're `.js` files

## Recommended Template List

After configuration, your template list should show:

- `00_times_startup_hook`
- `base`
- `new_vhdl_component` ⭐
- `vhdl_doc.vhd`
- `vhdl_file.vhd`

That's it! Much cleaner. 🎉


# Migration Notes: Templates → Templater

## What Changed

The `Templates/` folder has been reorganized into a cleaner `Templater/` structure:

**Old Structure:**
```
Templates/
├── user_scripts/
├── _docs/
├── times_debug/
└── [template files]
```

**New Structure:**
```
Templater/
├── Templates/          # Actual template files
│   ├── user_scripts/   # JavaScript modules
│   └── times_debug/    # Debug templates
└── docs/              # Documentation (separated)
```

## Action Required

### Update Templater Settings

1. Open Obsidian Settings (`CMD-,`)
2. Go to **Plugins** → **Templater** → **Settings**
3. Update these paths:
   - **Template folder location**: `Templater/Templates` (was: `Templates`)
   - **User scripts folder location**: `Templater/Templates/user_scripts` (was: `Templates/user_scripts`)

### Verify Template List

After updating settings, your template list should show:
- `00_times_startup_hook`
- `base`
- `new_vhdl_component` ⭐
- `vhdl_doc.vhd`
- `vhdl_file.vhd`

Documentation files are now in `Templater/docs/` and won't appear in the template list.

## Benefits

✅ **Cleaner organization** - All Templater-related files in one place  
✅ **Separated concerns** - Docs separate from templates  
✅ **Easier configuration** - Clear folder structure  
✅ **Better template list** - Only actual templates shown


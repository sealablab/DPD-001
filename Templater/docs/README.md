# Templates Documentation

This folder contains documentation for the template system. These files are not templates themselves.

## Available Templates

### VHDL Component Templates
- **`new_vhdl_component.md`** - ⭐ Master template - Creates paired `.vhd` and `.vhd.md` files
- **`vhdl_file.vhd`** - Template for `.vhd` files (manual creation)
- **`vhdl_doc.vhd.md`** - Template for `.vhd.md` files (manual creation)

### General Templates
- **`base.md`** - Standard base template with frontmatter
- **`00_times_startup_hook.md`** - Startup hook for templater_times

### Debug Templates
- **`times_debug/`** - Debug versions of templates (for development)

## Documentation Files

- **`VHDL_PAIR_TEMPLATE_README.md`** - Full documentation for VHDL pair template system
- **`VHDL_PAIR_QUICKSTART.md`** - Quick reference for VHDL component creation
- **`TEMPLATE_FRONTMATTER_TIMES.md`** - Documentation for frontmatter time fields

## User Scripts

The `user_scripts/` folder contains JavaScript modules used by templates:
- `templater_times.js` - Frontmatter time management
- `templater_vhdl_pair.js` - VHDL pair creation helpers
- `templater_internal_module.js` - Internal utilities

These are **not templates** and should be excluded from Templater's template list.


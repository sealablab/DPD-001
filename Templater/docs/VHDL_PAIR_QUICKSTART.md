---
created: 2025-11-27
---

# VHDL Component Pair - Quick Start

## One-Command Creation

**CMD-P** → `Templater: Create new note from template` → Select `new_vhdl_component`

Then enter:
1. **Directory**: `rtl`, `RUN-RTL`, or any path (default: `rtl`)
2. **Component name**: `clk-divider`, `4way_mux`, etc. (hyphens → underscores)
3. **Author**: Your name (default: `jellch`)

## What Gets Created

Two files with compatible frontmatter and bidirectional links:

- `{directory}/{component_name}.vhd` - VHDL code file
- `{directory}/{component_name}.vhd.md` - Documentation file

## Example

**Input:**
- Directory: `RUN-RTL`
- Name: `clk-divider`
- Author: `jellch`

**Output:**
- `RUN-RTL/clk_divider.vhd`
- `RUN-RTL/clk_divider.vhd.md`

Both files are created, linked, and opened automatically.

## Features

✅ Compatible frontmatter (comment-style ↔ YAML)  
✅ Bidirectional linking (works in Obsidian, GitHub, plain text)  
✅ Obsidian-native links (automatic rename/move tracking)  
✅ Cross-platform (works outside Obsidian too)  
✅ No additional plugins required

## See Also

- [Full Documentation](VHDL_PAIR_TEMPLATE_README.md)
- Helper script: `Templater/Templates/user_scripts/templater_vhdl_pair.js`


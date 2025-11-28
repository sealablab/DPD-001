---
created: 2025-11-27
modified: 2025-11-27 22:14:09
accessed: 2025-11-27 22:15:15
times_debug_last_event: active-leaf-change
times_debug_last_run: 2025-11-27 22:15:15
---
# VHDL File Pair Template System

## Overview

This system provides a workflow for creating paired `.vhd` and `.vhd.md` files with **compatible frontmatter** that works both inside and outside Obsidian. The files are linked bidirectionally using relative paths that work as plain text links.

## Key Design Principles

1. **Compatible Frontmatter**: Fields are trivially mappable between comment-style (`.vhd`) and YAML (`.vhd.md`)
2. **File-Based Linking**: Uses relative paths that work in Obsidian and as plain text
3. **Obsidian Integration**: Works well in Obsidian but doesn't fundamentally depend on it
4. **Editor Agnostic**: Files can be edited in `vi`, VS Code, or any editor without breaking the system

## Compatible Frontmatter Schema

Both file types share these core fields:

| Field | `.vhd` Format | `.vhd.md` Format | Description |
|-------|---------------|------------------|-------------|
| `file` | `-- File: filename.vhd` | `file: filename.vhd` | The VHDL filename |
| `author` | `-- Author: name` | `author: name` | Author name |
| `created` | `-- Created: YYYY-MM-DD` | `created: YYYY-MM-DD` | Creation date |
| `modified` | `-- Modified: YYYY-MM-DD HH:MM:SS` | `modified: YYYY-MM-DD HH:MM:SS` | Last modification (from filesystem) |
| `doc` | `-- Doc: [link](path)` | N/A | Link to `.vhd.md` file (in `.vhd` only) |
| `code` | N/A | `code: [link](path)` | Link to `.vhd` file (in `.vhd.md` only) |
| `accessed` | N/A | `accessed: YYYY-MM-DD HH:MM:SS` | Last accessed (Obsidian-only, managed by templater_times) |

## File Structure

### `.vhd` File Format

```vhdl
---
-- File: component_name.vhd
-- Author: author_name
-- Created: 2025-01-27
-- Modified: 2025-01-27 14:30:00
-- Doc: [component_name.vhd.md](path/to/component_name.vhd.md)
---

-- VHDL code starts here
library IEEE;
-- ...
```

### `.vhd.md` File Format

```markdown
---
file: component_name.vhd
author: author_name
created: 2025-01-27
modified: 2025-01-27 14:30:00
accessed: 2025-01-27 14:30:00
code: [component_name.vhd](path/to/component_name.vhd)
---

# [component_name.vhd.md](path/to/component_name.vhd.md)

## CODE-XREF [component_name.vhd](path/to/component_name.vhd)

## Overview
[Documentation content]
```

## Usage

### Creating a New VHDL Component Pair (Recommended - One-Step Process)

**Quick Start:**
1. Press `CMD-P` (or `CMD-O` on Mac) to open the command palette
2. Type: `Templater: Create new note from template`
3. Select: `new_vhdl_component`
4. Follow the prompts:
   - **Destination directory**: Enter path like `rtl`, `RUN-RTL`, or `components/utils` (default: `rtl`)
   - **Component base name**: Enter name like `clk-divider`, `4way_mux`, or `my_component` (hyphens will be converted to underscores)
   - **Author name**: Enter author (default: `jellch`)

The template will:
- ✅ Create both `.vhd` and `.vhd.md` files automatically
- ✅ Set up compatible frontmatter in both files
- ✅ Create bidirectional links between the files
- ✅ Open both files in Obsidian
- ✅ Use Obsidian-native links (so renames/moves are tracked automatically)

**Example:**
- Input: Directory=`RUN-RTL`, Name=`clk-divider`, Author=`jellch`
- Output: 
  - `RUN-RTL/clk_divider.vhd` (with frontmatter linking to `.vhd.md`)
  - `RUN-RTL/clk_divider.vhd.md` (with frontmatter linking to `.vhd`)

### Manual Creation (Alternative - Two-Step Process)

If you prefer to create files manually:

1. **Create the `.vhd` file first:**
   - In Obsidian, create a new file: `my_component.vhd`
   - Apply template: `vhdl_file.vhd` (from Templater/Templates/)
   - The template will prompt for author name and populate frontmatter

2. **Create the paired `.vhd.md` file:**
   - In Obsidian, create: `my_component.vhd.md` (same directory)
   - Apply template: `vhdl_doc.vhd.md` (from Templater/Templates/)
   - The template will automatically link to the `.vhd` file

### Manual Creation (Outside Obsidian)

If creating files manually (e.g., in `vi`), follow the frontmatter schema above. The key is:

- Use relative paths for linking (e.g., `[file.vhd.md](./file.vhd.md)`)
- Keep field names consistent between both files
- The pairing is implicit via filename: `foo_bar.vhd` pairs with `foo_bar.vhd.md`

## Template Files

- **`Templater/Templates/new_vhdl_component.md`**: ⭐ **Master template** - Creates both files in one step (recommended)
- **`Templater/Templates/vhdl_file.vhd`**: Template for `.vhd` files (manual creation)
- **`Templater/Templates/vhdl_doc.vhd.md`**: Template for `.vhd.md` files (manual creation)
- **`Templater/Templates/user_scripts/templater_vhdl_pair.js`**: Helper functions for linking and field management

## Integration with templater_times

The `.vhd.md` template integrates with `templater_times.js` to automatically manage `created`, `modified`, and `accessed` fields when used in Obsidian. If the script isn't available (e.g., when editing outside Obsidian), the system gracefully falls back to filesystem timestamps.

## Naming Conventions

- Use **underscores** as delimiters (VHDL build systems prefer them over hyphens)
- Examples: `my_component.vhd`, `bpd_runp_runb.vhd`
- The base name (without extensions) must match between `.vhd` and `.vhd.md`

## Bidirectional Linking

The system creates bidirectional links:

- **`.vhd` → `.vhd.md`**: Via `Doc:` field in frontmatter
- **`.vhd.md` → `.vhd`**: Via `code:` field in frontmatter and `CODE-XREF` section

These links work in:
- **Obsidian**: Native markdown links - Obsidian will automatically track renames and moves
- **GitHub**: Renders as clickable markdown links
- **Plain text**: Readable paths that work in any editor

### Obsidian Link Tracking

The links use Obsidian's native markdown link format: `[filename](path/to/filename)`. This means:

- ✅ **Automatic rename tracking**: If you rename a file in Obsidian, links update automatically
- ✅ **Move tracking**: If you move files, Obsidian can update links (with confirmation)
- ✅ **Graph view**: Files appear connected in Obsidian's graph view
- ✅ **Backlinks**: Each file shows backlinks to the other in the backlinks panel

The links use **relative paths** (just the filename when in the same directory), which ensures they work correctly even if the vault is moved or shared.

## Future Enhancements

Potential improvements:
- Automatic frontmatter synchronization script
- Validation to ensure paired files stay in sync
- Support for additional metadata fields
- Integration with VHDL build systems


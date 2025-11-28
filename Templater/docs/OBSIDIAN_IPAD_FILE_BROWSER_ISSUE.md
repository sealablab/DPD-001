# Obsidian iPad File Browser Issue

## Problem

When opening a `.vhd.md` file on the Obsidian iPad client, the file browser incorrectly highlights the corresponding `.vhd` file instead of the `.vhd.md` file.

**Example:**
- Opening `yoshi_island.vhd.md` causes the file browser to highlight `yoshi_island.vhd`
- The document viewer correctly shows `yoshi_island.vhd.md`

## Root Cause

This appears to be a UI bug in Obsidian's iPad client where the file browser does fuzzy matching by base filename. When you open a file, it matches the base name (`yoshi_island`) and highlights the first match it finds (the `.vhd` file) rather than the exact file you opened.

## Status

- ✅ **Files sync correctly** - Both files exist with correct extensions
- ✅ **Links work correctly** - All links resolve properly
- ❌ **File browser display** - UI incorrectly highlights the wrong file

## Workarounds

### Option 1: Use Explicit Paths in Links

The template system now uses explicit full paths (e.g., `Yoshi/yoshi_island.vhd.md`) instead of relative paths (e.g., `yoshi_island.vhd.md`). This helps Obsidian better distinguish between files.

### Option 2: Manual File Selection

When opening files on iPad:
1. Use the search/quick switcher (`CMD-O`) instead of the file browser
2. Type the full filename including extension (e.g., `yoshi_island.vhd.md`)
3. This will correctly open and highlight the right file

### Option 3: Use Desktop Client

The issue appears to be specific to the iPad client. The desktop version correctly highlights the opened file.

## Reporting

This should be reported to Obsidian as a bug:
- **Issue**: File browser highlights wrong file when files share base name
- **Platform**: iPad client
- **Reproduction**: Create two files with same base name but different extensions (e.g., `file.vhd` and `file.vhd.md`), open the `.vhd.md` file, observe file browser highlights `.vhd` instead

## Technical Details

The files themselves are correct:
- Both files exist with correct extensions
- Frontmatter links use explicit paths
- Obsidian sync logs show correct filenames
- The issue is purely in the file browser UI

## Related Files

- Template generation: `Templater/Templates/user_scripts/templater_vhdl_pair.js`
- Uses explicit paths in `code:`, `doc:`, and `self:` fields to help distinguish files


# Obsidian created / modified / accessed automation (Templater)

This overlay adds:

- `Templates/base.md` – updated base template with empty `created` / `modified` / `accessed` properties
- `Templates/99_internal_on_open_accessed.md` – on-open hook template
- `.obsidian/plugins/templater/user_scripts/templater_internal_module.js` – logic to manage timestamps

## How it behaves

On note open (desktop or mobile, if Templater is enabled and configured):

- **created**
  - If missing/empty, set once from filesystem `ctime`/`mtime` (`YYYY-MM-DD`).
  - Never changed again.
- **modified**
  - Synced from filesystem `mtime` (`YYYY-MM-DD HH:mm`) each time the script runs.
  - This keeps the property aligned with the actual save time.
- **accessed**
  - Logical "last opened in Obsidian" time (`YYYY-MM-DD HH:mm`).
  - Only updated if the previous value is older than `THRESHOLD_MINUTES_ACCESS` (default 15 minutes),
    to avoid excessive file churn.

## Wiring it up

1. Copy this archive to the **root of your vault** and extract it, allowing it to merge with existing folders:
   - `Templates/`
   - `.obsidian/plugins/templater/user_scripts/`

2. In Obsidian → **Templater settings**:

   - Set **Template Folder Location** to `Templates` (or keep your existing setting if it's already that).
   - Under **Trigger Templater on file open**, select:
     `Templates/99_internal_on_open_accessed.md`

3. Make sure Templater is enabled on **all devices** (desktop + mobile).

After that, opening any note will keep these three frontmatter properties in sync.

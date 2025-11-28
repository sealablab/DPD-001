---
created: 2025-11-27
modified: 2025-11-27 21:10:45
accessed: 2025-11-27 22:14:48
times_debug_last_event: active-leaf-change
times_debug_last_run: 2025-11-27 22:14:48
---
# Frontmatter time fields (`created` / `modified` / `accessed`)

This vault uses a small Templater + JS bridge to keep three frontmatter
timestamps consistent across notes:

- `created`  – when the file first appeared in the vault (from filesystem ctime/mtime)
- `modified` – last on-disk edit time (from filesystem mtime)
- `accessed` – last time the note was *opened in Obsidian* (logical atime)

All three live in YAML, which makes them easy to query from Dataview and to
diff in git.

---

## How it works

There are two moving pieces:

1. **Startup hook template**

   - File: `Templater/Templates/00_times_startup_hook.md`
   - Wired in Templater as a **Startup template**.
   - On plugin start, it calls:

     ```templater
     <%* await tp.user.templater_times.register_times_hook(tp) %>
     ```

   - This registers a single `active-leaf-change` listener on the Obsidian
     workspace.

2. **User script**

   - File: `Templater/Templates/user_scripts/templater_times.js`
   - Loaded via Templater's "Script files folder location".
   - Exposes two functions:

     ```js
     tp.user.templater_times.register_times_hook(tp)
     tp.user.templater_times.touch_current_file(tp)
     ```

   - On `active-leaf-change`, the hook:

     1. Checks if the new leaf is a markdown file.
     2. Reads filesystem metadata via `app.vault.adapter.stat(file.path)`.
     3. Updates the note's frontmatter via `app.fileManager.processFrontMatter`:

        - `created`
          - If missing/empty, set once from `ctime || mtime` (format `YYYY-MM-DD`).
        - `modified`
          - Always mirrored from `mtime` (format `YYYY-MM-DD HH:MM:SS`).
        - `accessed`
          - Set to "now" (same `YYYY-MM-DD HH:MM:SS` format) whenever the
            previous value is missing or older than 15 minutes.

---

## Base template and manual application

The standard base template lives at:

- `Templater/Templates/base.md`

Its frontmatter includes placeholders:

```yaml
created: ""
modified: ""
accessed: ""

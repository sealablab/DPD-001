// .obsidian/plugins/templater/user_scripts/templater_internal_module.js
// Manage created / modified / accessed frontmatter fields in a consistent way.
//
// - created: set once from filesystem ctime/mtime if missing; never touched again.
// - modified: synced from filesystem mtime on each run.
// - accessed: logical "last opened in Obsidian" time, updated on open with a throttle.
//
// You probably want to call ensure_file_times() from a small "on-open" template.

const THRESHOLD_MINUTES_ACCESS = 15; // don't bump `accessed` more often than this; set to 0 to always update

function parseDateTime(str) {
  if (!str || typeof str !== "string") return NaN;
  // Accept "YYYY-MM-DD" or "YYYY-MM-DD HH:mm"
  const normalized = str.includes("T") ? str : str.replace(" ", "T");
  const d = new Date(normalized);
  return d.getTime();
}

module.exports = {
  /**
   * Ensure frontmatter.created / modified / accessed are populated.
   *
   * @param {any} tp - Templater tp object (must be passed from the template)
   * @param {Object} opts
   * @param {string|null} opts.baseTemplate - Optional template (relative to Templates folder)
   *                                         to apply if frontmatter update fails.
   */
  async ensure_file_times(tp, opts = {}) {
    const baseTemplate = opts.baseTemplate || null;

    // Compute filesystem metadata up front.
    const relPath = tp.file.path(true); // vault-relative
    let stat = null;

    try {
      stat = await app.vault.adapter.stat(relPath);
    } catch (e) {
      console.error("ensure_file_times(): stat failed for", relPath, e);
    }

    const now      = new Date();
    const nowStr   = tp.date.now("YYYY-MM-DD HH:mm", now);
    const createdStrFromFs = (() => {
      if (!stat) return tp.date.now("YYYY-MM-DD", now);
      const src = stat.ctime || stat.mtime || Date.now();
      return tp.date.now("YYYY-MM-DD", new Date(src));
    })();

    const modifiedStrFromFs = (() => {
      if (!stat) return tp.date.now("YYYY-MM-DD HH:mm", now);
      const src = stat.mtime || stat.ctime || Date.now();
      return tp.date.now("YYYY-MM-DD HH:mm", new Date(src));
    })();

    const doUpdate = async () => {
      await tp.file.update_frontmatter(fm => {
        // created: set once if missing/empty, never touched again.
        if (!fm.created || fm.created === "") {
          fm.created = createdStrFromFs;
        }

        // modified: always aligned to filesystem mtime when stat is available.
        if (modifiedStrFromFs) {
          if (fm.modified !== modifiedStrFromFs) {
            fm.modified = modifiedStrFromFs;
          }
        }

        // accessed: logical last-opened time, throttled.
        const prevAccessed = fm.accessed;
        const prevMs = parseDateTime(prevAccessed);
        const nowMs  = now.getTime();

        if (
          THRESHOLD_MINUTES_ACCESS <= 0 ||
          Number.isNaN(prevMs) ||
          ((nowMs - prevMs) / 60000) >= THRESHOLD_MINUTES_ACCESS
        ) {
          fm.accessed = nowStr;
        }
      });
    };

    try {
      await doUpdate();
    } catch (e) {
      console.error("ensure_file_times(): frontmatter update failed", e);

      if (baseTemplate) {
        try {
          await tp.templates.apply_template(baseTemplate);
          await doUpdate();
        } catch (e2) {
          console.error("ensure_file_times(): failed even after baseTemplate", e2);
        }
      }
    }

    return nowStr;
  }
};

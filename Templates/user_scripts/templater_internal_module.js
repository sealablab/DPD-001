// Templates/user_scripts/templater_internal_module.js
// Manage created / modified / accessed frontmatter fields.
//
// - created: set once from filesystem ctime/mtime if missing; never touched again.
// - modified: mirrored from filesystem mtime on each run.
// - accessed: logical "last opened in Obsidian" time, throttled.
//
// Uses Obsidian's app.fileManager.processFrontMatter instead of tp.file.update_frontmatter,
// so it works on older Templater versions.

const THRESHOLD_MINUTES_ACCESS = 15; // set to 0 to always bump `accessed`

function parseDateTime(str) {
  if (!str || typeof str !== "string") return NaN;
  const normalized = str.includes("T") ? str : str.replace(" ", "T");
  return new Date(normalized).getTime();
}

// Small helper: mutate frontmatter via Obsidian's fileManager API.
async function withFrontmatter(tp, updater) {
  const relPath = tp.file.path(true);           // vault-relative path of current file
  const file = app.vault.getAbstractFileByPath(relPath);

  if (!file || !file.extension) {
    console.error("withFrontmatter(): not a TFile for path", relPath, file);
    return;
  }

  // processFrontMatter is sync, but we wrap it in a Promise so callers can await.
  await new Promise(resolve => {
    app.fileManager.processFrontMatter(file, fm => {
      updater(fm);
      resolve();
    });
  });
}

module.exports = {
  async ensure_file_times(tp) {
    const relPath = tp.file.path(true);
    let stat = null;

    try {
      stat = await app.vault.adapter.stat(relPath);
    } catch (e) {
      console.error("ensure_file_times(): stat failed for", relPath, e);
    }

    const now    = new Date();
    const nowStr = tp.date.now("YYYY-MM-DD HH:mm", now);

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

    await withFrontmatter(tp, fm => {
      // created: set once if missing / empty
      if (!fm.created || fm.created === "") {
        fm.created = createdStrFromFs;
      }

      // modified: mirror filesystem mtime
      if (modifiedStrFromFs && fm.modified !== modifiedStrFromFs) {
        fm.modified = modifiedStrFromFs;
      }

      // accessed: logical last-opened time with throttle
      const prevMs = parseDateTime(fm.accessed);
      const nowMs  = now.getTime();

      if (
        THRESHOLD_MINUTES_ACCESS <= 0 ||
        Number.isNaN(prevMs) ||
        ((nowMs - prevMs) / 60000) >= THRESHOLD_MINUTES_ACCESS
      ) {
        fm.accessed = nowStr;
      }
    });

    return nowStr;
  }
};
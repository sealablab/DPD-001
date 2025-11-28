// Templates/user_scripts/templater_internal_module_debug.js
// Debug-heavy version of the time management module.
// Logs aggressively to console and marks frontmatter with debug fields.

const THRESHOLD_MINUTES_ACCESS = 1; // very low to force frequent updates during debugging

function parseDateTime(str) {
  if (!str || typeof str !== "string") return NaN;
  const normalized = str.includes("T") ? str : str.replace(" ", "T");
  return new Date(normalized).getTime();
}

async function withFrontmatter(tp, updater) {
  const relPath = tp.file.path(true);
  const file = app.vault.getAbstractFileByPath(relPath);

  console.log("[DEBUG] withFrontmatter: relPath =", relPath, "file =", file);

  if (!file || !file.extension) {
    console.error("[DEBUG] withFrontmatter: not a TFile, aborting", relPath);
    return;
  }

  await new Promise(resolve => {
    console.log("[DEBUG] withFrontmatter: entering processFrontMatter for", relPath);
    app.fileManager.processFrontMatter(file, fm => {
      console.log("[DEBUG] withFrontmatter: current frontmatter =", JSON.stringify(fm));
      updater(fm);
      console.log("[DEBUG] withFrontmatter: updated frontmatter =", JSON.stringify(fm));
      resolve();
    });
  });
}

module.exports = {
  async ensure_file_times(tp) {
    const relPath = tp.file.path(true);
    console.log("[DEBUG] ensure_file_times: START for", relPath);

    let stat = null;
    try {
      stat = await app.vault.adapter.stat(relPath);
      console.log("[DEBUG] ensure_file_times: stat =", stat);
    } catch (e) {
      console.error("[DEBUG] ensure_file_times: stat failed for", relPath, e);
    }

    const now    = new Date();
    const nowStr = tp.date.now("YYYY-MM-DD HH:mm:ss", now);

    const createdStrFromFs = (() => {
      if (!stat) {
        const val = tp.date.now("YYYY-MM-DD", now);
        console.log("[DEBUG] createdStrFromFs: no stat, using now =", val);
        return val;
      }
      const src = stat.ctime || stat.mtime || Date.now();
      const val = tp.date.now("YYYY-MM-DD", new Date(src));
      console.log("[DEBUG] createdStrFromFs: from stat =", src, "->", val);
      return val;
    })();

    const modifiedStrFromFs = (() => {
      if (!stat) {
        const val = tp.date.now("YYYY-MM-DD HH:mm:ss", now);
        console.log("[DEBUG] modifiedStrFromFs: no stat, using now =", val);
        return val;
      }
      const src = stat.mtime || stat.ctime || Date.now();
      const val = tp.date.now("YYYY-MM-DD HH:mm:ss", new Date(src));
      console.log("[DEBUG] modifiedStrFromFs: from stat =", src, "->", val);
      return val;
    })();

    await withFrontmatter(tp, fm => {
      console.log("[DEBUG] ensure_file_times: updater running, fm before =", JSON.stringify(fm));

      // created
      if (!fm.created || fm.created === "") {
        fm.created = createdStrFromFs;
        console.log("[DEBUG] ensure_file_times: set created ->", fm.created);
      }

      // modified
      if (modifiedStrFromFs && fm.modified !== modifiedStrFromFs) {
        console.log("[DEBUG] ensure_file_times: updating modified from", fm.modified, "to", modifiedStrFromFs);
        fm.modified = modifiedStrFromFs;
      }

      // accessed
      const prevMs = parseDateTime(fm.accessed);
      const nowMs  = now.getTime();
      const diffMin = Number.isNaN(prevMs) ? Infinity : (nowMs - prevMs) / 60000;

      console.log("[DEBUG] ensure_file_times: accessed before =", fm.accessed, "diffMin =", diffMin);

      if (
        THRESHOLD_MINUTES_ACCESS <= 0 ||
        Number.isNaN(prevMs) ||
        diffMin >= THRESHOLD_MINUTES_ACCESS
      ) {
        fm.accessed = nowStr;
        console.log("[DEBUG] ensure_file_times: set accessed ->", fm.accessed);
      }

      // mark that the debug hook ran
      fm.debug_hook_ran = true;
      fm.debug_last_run = nowStr;

      console.log("[DEBUG] ensure_file_times: updater finished, fm after =", JSON.stringify(fm));
    });

    console.log("[DEBUG] ensure_file_times: END for", relPath, "at", nowStr);
    return nowStr;
  }
};

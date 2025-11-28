// Templates/user_scripts/templater_times_debug.js
// Debug version of a "created / modified / accessed" manager that hooks
// Obsidian's active-leaf-change events via a startup template.
// No reliance on deprecated "trigger on file open" option.

let hookRegistered = false;
const ACCESS_THRESHOLD_MIN = 1; // update accessed if older than this

function pad(n) {
  return String(n).padStart(2, "0");
}

function fmtDate(d) {
  return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
}

function fmtDateTime(d) {
  return (
    fmtDate(d) +
    " " +
    pad(d.getHours()) + ":" +
    pad(d.getMinutes()) + ":" +
    pad(d.getSeconds())
  );
}

function parseDateTime(str) {
  if (!str || typeof str !== "string") return NaN;
  // Accept "YYYY-MM-DD" or "YYYY-MM-DD HH:mm[:ss]"
  const parts = str.trim().split(/[ T]/);
  if (parts.length === 0) return NaN;
  const [datePart, timePart] = parts;
  const [y, m, d] = datePart.split("-").map(x => parseInt(x, 10));
  if (!y || !m || !d) return NaN;
  let hh = 0, mm = 0, ss = 0;
  if (timePart) {
    const t = timePart.split(":").map(x => parseInt(x, 10));
    hh = t[0] || 0;
    mm = t[1] || 0;
    ss = t[2] || 0;
  }
  const dt = new Date(y, m - 1, d, hh, mm, ss);
  return dt.getTime();
}

async function updateTimesForFile(file) {
  const relPath = file.path;
  console.log("[TIMES-DEBUG] updateTimesForFile: START for", relPath);

  let stat = null;
  try {
    stat = await app.vault.adapter.stat(relPath);
    console.log("[TIMES-DEBUG] stat =", stat);
  } catch (e) {
    console.error("[TIMES-DEBUG] stat failed for", relPath, e);
  }

  const now = new Date();
  const nowStr = fmtDateTime(now);

  const createdStrFromFs = (() => {
    if (!stat) {
      const val = fmtDate(now);
      console.log("[TIMES-DEBUG] createdStrFromFs: no stat, using now =", val);
      return val;
    }
    const src = stat.ctime || stat.mtime || Date.now();
    const val = fmtDate(new Date(src));
    console.log("[TIMES-DEBUG] createdStrFromFs from stat =", src, "->", val);
    return val;
  })();

  const modifiedStrFromFs = (() => {
    if (!stat) {
      const val = fmtDateTime(now);
      console.log("[TIMES-DEBUG] modifiedStrFromFs: no stat, using now =", val);
      return val;
    }
    const src = stat.mtime || stat.ctime || Date.now();
    const val = fmtDateTime(new Date(src));
    console.log("[TIMES-DEBUG] modifiedStrFromFs from stat =", src, "->", val);
    return val;
  })();

  const fileManager = app.fileManager;

  await new Promise(resolve => {
    console.log("[TIMES-DEBUG] processFrontMatter for", relPath);
    fileManager.processFrontMatter(file, fm => {
      console.log("[TIMES-DEBUG] frontmatter BEFORE =", JSON.stringify(fm));

      // created: set once
      if (!fm.created || fm.created === "") {
        fm.created = createdStrFromFs;
        console.log("[TIMES-DEBUG] set created ->", fm.created);
      }

      // modified: mirror FS mtime
      if (modifiedStrFromFs && fm.modified !== modifiedStrFromFs) {
        console.log("[TIMES-DEBUG] update modified", fm.modified, "->", modifiedStrFromFs);
        fm.modified = modifiedStrFromFs;
      }

      // accessed: logical last-opened time
      const prevMs = parseDateTime(fm.accessed);
      const nowMs = now.getTime();
      const diffMin = Number.isNaN(prevMs) ? Infinity : (nowMs - prevMs) / 60000;
      console.log("[TIMES-DEBUG] accessed before =", fm.accessed, "diffMin =", diffMin);

      if (
        ACCESS_THRESHOLD_MIN <= 0 ||
        Number.isNaN(prevMs) ||
        diffMin >= ACCESS_THRESHOLD_MIN
      ) {
        fm.accessed = nowStr;
        console.log("[TIMES-DEBUG] set accessed ->", fm.accessed);
      }

      fm.times_debug_last_event = "active-leaf-change";
      fm.times_debug_last_run = nowStr;

      console.log("[TIMES-DEBUG] frontmatter AFTER =", JSON.stringify(fm));
      resolve();
    });
  });

  console.log("[TIMES-DEBUG] updateTimesForFile: END for", relPath);
}

function register_times_hook() {
  if (hookRegistered) {
    console.log("[TIMES-DEBUG] register_times_hook: already registered");
    return;
  }
  hookRegistered = true;
  console.log("[TIMES-DEBUG] register_times_hook: registering active-leaf-change listener");

  app.workspace.on("active-leaf-change", leaf => {
    try {
      const view = leaf && leaf.view;
      const file = view && view.file;
      if (!file || file.extension !== "md") return;
      console.log("[TIMES-DEBUG] active-leaf-change for", file.path);
      updateTimesForFile(file);
    } catch (e) {
      console.error("[TIMES-DEBUG] active-leaf-change handler error:", e);
    }
  });
}

module.exports = {
  // Called from startup template
  async register_times_hook(tp) {
    console.log("[TIMES-DEBUG] register_times_hook(tp) called");
    register_times_hook();
  },

  // Optional: manual call from templates (like base_times_debug)
  async touch_current_file(tp) {
    const relPath = tp.file.path(true);
    const file = app.vault.getAbstractFileByPath(relPath);
    console.log("[TIMES-DEBUG] touch_current_file for", relPath, "->", file);
    if (!file || !file.extension) {
      console.error("[TIMES-DEBUG] touch_current_file: not a TFile");
      return;
    }
    await updateTimesForFile(file);
  }
};

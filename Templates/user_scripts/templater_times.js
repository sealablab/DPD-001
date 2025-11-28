// Templates/user_scripts/templater_times.js
// Production manager for created / modified / accessed frontmatter.
//
// - created: set once from filesystem ctime/mtime if missing; never touched again.
// - modified: mirrored from filesystem mtime on each run.
// - accessed: logical "last opened in Obsidian" time, updated when you switch notes,
//             with a 15-minute throttle to avoid excessive churn.
//
// This module is wired up via:
//   - Templates/00_times_startup_hook.md  (startup template)
//   - Templates/base.md                   (manual template apply)

let hookRegistered = false;
const ACCESS_THRESHOLD_MIN = 15;

function pad(n) {
  return String(n).padStart(2, "0");
}

function fmtDate(d) {
  return (
    d.getFullYear() +
    "-" +
    pad(d.getMonth() + 1) +
    "-" +
    pad(d.getDate())
  );
}

function fmtDateTime(d) {
  return (
    fmtDate(d) +
    " " +
    pad(d.getHours()) +
    ":" +
    pad(d.getMinutes()) +
    ":" +
    pad(d.getSeconds())
  );
}

function parseDateTime(str) {
  if (!str || typeof str !== "string") return NaN;
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
  let stat = null;

  try {
    stat = await app.vault.adapter.stat(relPath);
  } catch (e) {
    // If stat fails (rare), fall back to "now".
  }

  const now = new Date();
  const nowDate = fmtDate(now);
  const nowDateTime = fmtDateTime(now);

  const createdStrFromFs = (() => {
    if (!stat) return nowDate;
    const src = stat.ctime || stat.mtime || Date.now();
    return fmtDate(new Date(src));
  })();

  const modifiedStrFromFs = (() => {
    if (!stat) return nowDateTime;
    const src = stat.mtime || stat.ctime || Date.now();
    return fmtDateTime(new Date(src));
  })();

  const fileManager = app.fileManager;

  await new Promise(resolve => {
    fileManager.processFrontMatter(file, fm => {
      // created: set once if missing/empty
      if (!fm.created || fm.created === "") {
        fm.created = createdStrFromFs;
      }

      // modified: mirror FS mtime
      if (modifiedStrFromFs && fm.modified !== modifiedStrFromFs) {
        fm.modified = modifiedStrFromFs;
      }

      // accessed: logical last-opened time, throttled
      const prevMs = parseDateTime(fm.accessed);
      const nowMs = now.getTime();
      const diffMin = Number.isNaN(prevMs) ? Infinity : (nowMs - prevMs) / 60000;

      if (
        ACCESS_THRESHOLD_MIN <= 0 ||
        Number.isNaN(prevMs) ||
        diffMin >= ACCESS_THRESHOLD_MIN
      ) {
        fm.accessed = nowDateTime;
      }

      resolve();
    });
  });
}

function register_times_hook() {
  if (hookRegistered) return;
  hookRegistered = true;

  app.workspace.on("active-leaf-change", leaf => {
    try {
      const view = leaf && leaf.view;
      const file = view && view.file;
      if (!file || file.extension !== "md") return;
      updateTimesForFile(file);
    } catch (e) {
      // swallow; we don't want to break workspace events
    }
  });
}

module.exports = {
  // Called from Templates/00_times_startup_hook.md
  async register_times_hook(tp) {
    register_times_hook();
  },

  // Optional: manual call from base.md or other templates
  async touch_current_file(tp) {
    const relPath = tp.file.path(true);
    const file = app.vault.getAbstractFileByPath(relPath);
    if (!file || !file.extension) return;
    await updateTimesForFile(file);
  }
};

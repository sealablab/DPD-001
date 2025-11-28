---
publish: "true"
type: documentation
created: ""
modified: ""
accessed: ""
debug_hook_ran: false
tags: []
---
# <% tp.file.title %>

> DEBUG: base_debug_times applied at <% tp.date.now("YYYY-MM-DD HH:mm:ss") %>

## Overview

[Description of this document]

## See Also

---
**View this document:**
- 📖 [Obsidian Publish](https://publish.obsidian.md/dpd-001/<% tp.file.path(true).replace(/\.md$/, '').replace(/ /g, '%20') %>)
- 💻 [GitHub](https://github.com/sealablab/DPD-001/blob/main/<% tp.file.path(true).replace(/ /g, '%20') %>)
- ✏️ [Edit on GitHub](https://github.com/sealablab/DPD-001/edit/main/<% tp.file.path(true).replace(/ /g, '%20') %>)

<%* 
  console.log("[DEBUG] base_debug_times: calling ensure_file_times for", tp.file.path(true));
  await tp.user.templater_internal_module_debug.ensure_file_times(tp);
%>

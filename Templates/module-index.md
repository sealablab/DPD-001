---
publish: "true"
type: reference
created: <% tp.file.creation_date("YYYY-MM-DD") %>
modified: <% tp.file.last_modified_date("YYYY-MM-DD") %>
tags: []
---
# <% tp.file.title %>

[Brief description of this directory/module]

## module_name
**Module:** `path/to/module.py` ([source](https://github.com/sealablab/DPD-001/blob/main/path/to/module.py))

[Description of what this module does]

## another_module
**Module:** `path/to/another.py` ([source](https://github.com/sealablab/DPD-001/blob/main/path/to/another.py))

[Description of what this module does]

## See Also

---
**View this document:**
- 📖 [Obsidian Publish](https://publish.obsidian.md/dpd-001/<% tp.file.path(true).replace(/\.md$/, '').replace(/ /g, '%20') %>)
- 💻 [GitHub](https://github.com/sealablab/DPD-001/blob/main/<% tp.file.path(true).replace(/ /g, '%20') %>)
- ✏️ [Edit on GitHub](https://github.com/sealablab/DPD-001/edit/main/<% tp.file.path(true).replace(/ /g, '%20') %>)

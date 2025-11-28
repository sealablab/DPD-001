---
<%*
  // Template for creating a new .vhd.md file with compatible frontmatter
  const vhdlPair = tp.user.templater_vhdl_pair;
  
  // Get the current file path (will be the new .vhd.md file)
  const currentPath = tp.file.path(true);
  const baseName = vhdlPair.getBaseName(currentPath);
  
  // Get frontmatter fields
  const fields = await vhdlPair.getMarkdownFrontmatter(tp, currentPath);
  
  // Prompt for author if not set
  if (!fields.author) {
    fields.author = await tp.system.prompt("Author name:", "jellch");
  }
  
  // Set created date if not set
  if (!fields.created) {
    const stat = await app.vault.adapter.stat(currentPath).catch(() => null);
    if (stat) {
      const createdDate = new Date(stat.ctime || stat.mtime || Date.now());
      fields.created = createdDate.toISOString().split('T')[0]; // YYYY-MM-DD
    } else {
      fields.created = tp.date.now("YYYY-MM-DD");
    }
  }
  
  // Set modified date
  const stat = await app.vault.adapter.stat(currentPath).catch(() => null);
  if (stat) {
    const modifiedDate = new Date(stat.mtime || stat.ctime || Date.now());
    fields.modified = modifiedDate.toISOString().split('T')[0] + " " + 
                      modifiedDate.toTimeString().split(' ')[0]; // YYYY-MM-DD HH:MM:SS
  } else {
    fields.modified = tp.date.now("YYYY-MM-DD HH:mm:ss");
  }
  
  // Initialize accessed if not set
  if (!fields.accessed) {
    fields.accessed = fields.modified;
  }
  
  // Output YAML frontmatter
%>file: <%= fields.file %>
author: <%= fields.author %>
created: <%= fields.created %>
modified: <%= fields.modified %>
accessed: <%= fields.accessed %>
code: <%= fields.code %>
---

# [<%= baseName %>.vhd.md](<%= currentPath %>)

## CODE-XREF <%= fields.code %>

## Overview

[Description of this VHDL component]

## Architecture

[Architecture details]

## Usage

[Usage instructions]

<%*
  // Generate See Also section
  const pairedPath = vhdlPair.getPairedFilePath(currentPath);
  const pairedName = `${baseName}.vhd`;
%>
# See Also
## [<%= pairedName %>](<%= pairedPath %>)

---

<%*
  // Integrate with templater_times if available
  try {
    await tp.user.templater_times.touch_current_file(tp);
  } catch (e) {
    // templater_times not available, that's okay
  }
%>


---
<%*
  // Template for creating a new .vhd file with compatible frontmatter
  const vhdlPair = tp.user.templater_vhdl_pair;
  
  // Get the current file path (will be the new .vhd file)
  const currentPath = tp.file.path(true);
  const baseName = vhdlPair.getBaseName(currentPath);
  
  // Get frontmatter fields
  const fields = await vhdlPair.getVhdlFrontmatter(tp, currentPath);
  
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
  
  // Generate the frontmatter
  const frontmatter = vhdlPair.generateVhdlFrontmatter(fields);
%>
<%= frontmatter %>


-- TODO: Add VHDL code here
-- This is a placeholder template for the .vhd file


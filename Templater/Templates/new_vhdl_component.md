<%*
  // Master template for creating a new VHDL component pair
  // This template creates both .vhd and .vhd.md files in one step
  
  const vhdlPair = tp.user.templater_vhdl_pair;
  
  // Step 1: Directory picker using suggester
  const allDirs = vhdlPair.getAllDirectories();
  const defaultDir = "rtl";
  
  // Build directory list with default first, then others, then root, then manual entry
  const dirsList = [];
  const displayNames = [];
  
  // Add default if it exists
  if (allDirs.includes(defaultDir)) {
    dirsList.push(defaultDir);
    displayNames.push(`⭐ ${defaultDir} (default)`);
  }
  
  // Add other directories (excluding default and root)
  allDirs.filter(d => d !== defaultDir && d !== '.').forEach(dir => {
    dirsList.push(dir);
    displayNames.push(dir);
  });
  
  // Add root option
  dirsList.push('.');
  displayNames.push('(root directory)');
  
  // Add manual entry option
  dirsList.push('__MANUAL__');
  displayNames.push('✏️ Enter path manually...');
  
  const selectedDir = await tp.system.suggester(
    displayNames,
    dirsList,
    false,
    "Select destination directory:"
  );
  
  if (selectedDir === null || selectedDir === undefined) {
    // User cancelled - close this template file
    const currentFile = tp.file.path(true);
    const file = app.vault.getAbstractFileByPath(currentFile);
    if (file) {
      await app.vault.delete(file);
    }
    return;
  }
  
  let targetDir;
  if (selectedDir === '__MANUAL__') {
    // Manual entry fallback
    const manualDir = await tp.system.prompt(
      "Enter directory path (relative to vault root):",
      defaultDir
    );
    if (manualDir === null || manualDir === undefined) {
      const currentFile = tp.file.path(true);
      const file = app.vault.getAbstractFileByPath(currentFile);
      if (file) {
        await app.vault.delete(file);
      }
      return;
    }
    targetDir = manualDir.trim() || '.';
  } else {
    targetDir = selectedDir === '.' ? '.' : selectedDir;
  }
  
  // Step 2: Prompt for base name (trimmed down)
  const baseNamePrompt = await tp.system.prompt(
    "Component base name (hyphens will be converted to underscores):",
    ""
  );
  
  if (baseNamePrompt === null || !baseNamePrompt.trim()) {
    new Notice("❌ Component name is required. Cancelled.");
    const currentFile = tp.file.path(true);
    const file = app.vault.getAbstractFileByPath(currentFile);
    if (file) {
      await app.vault.delete(file);
    }
    return;
  }
  
  // Step 3: Prompt for author (optional, with default)
  const authorPrompt = await tp.system.prompt(
    "Author name:",
    "jellch"
  );
  
  const author = authorPrompt ? authorPrompt.trim() : "jellch";
  
  // Step 4: Create both files
  try {
    const result = await vhdlPair.createVhdlPair(tp, targetDir, baseNamePrompt, author);
    
    if (result.success) {
      // Open files in new panes
      const vhdFile = app.vault.getAbstractFileByPath(result.vhdPath);
      const mdFile = app.vault.getAbstractFileByPath(result.mdPath);
      const readmeFile = result.readmePath ? app.vault.getAbstractFileByPath(result.readmePath) : null;
      
      if (vhdFile) {
        await app.workspace.openLinkText(vhdFile.path, '', false);
      }
      if (mdFile) {
        await app.workspace.openLinkText(mdFile.path, '', true);
      }
      
      const filesCreated = result.readmePath 
        ? `${result.vhdPath}\n${result.mdPath}\n${result.readmePath}`
        : `${result.vhdPath}\n${result.mdPath}`;
      new Notice(`✅ Created VHDL component:\n${filesCreated}`, 5000);
      
      // Close this template file (it was just a trigger)
      const currentFile = tp.file.path(true);
      const file = app.vault.getAbstractFileByPath(currentFile);
      if (file && file.path.includes('new_vhdl_component')) {
        // Only delete if this is the template file itself
        await app.vault.delete(file);
      }
    }
  } catch (error) {
    new Notice(`❌ Error creating files: ${error.message}`, 5000);
    console.error("VHDL pair creation error:", error);
    
    // Close this template file on error too
    const currentFile = tp.file.path(true);
    const file = app.vault.getAbstractFileByPath(currentFile);
    if (file && file.path.includes('new_vhdl_component')) {
      await app.vault.delete(file);
    }
  }
%>


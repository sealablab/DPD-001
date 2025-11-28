// Templater/Templates/user_scripts/templater_vhdl_pair.js
// Helper functions for managing paired .vhd and .vhd.md files
//
// Provides:
// - Bidirectional linking between .vhd and .vhd.md files
// - Compatible frontmatter field mapping
// - Path resolution that works in and out of Obsidian

/**
 * Get the base name (without extension) from a file path
 */
function getBaseName(filePath) {
  const name = filePath.split('/').pop().split('\\').pop();
  if (name.endsWith('.vhd.md')) {
    return name.slice(0, -7); // Remove .vhd.md
  } else if (name.endsWith('.vhd')) {
    return name.slice(0, -4); // Remove .vhd
  } else if (name.endsWith('.md')) {
    return name.slice(0, -3); // Remove .md
  }
  return name;
}

/**
 * Get the directory path from a file path
 */
function getDirPath(filePath) {
  const parts = filePath.split('/');
  if (parts.length === 1) {
    return '.'; // Same directory
  }
  parts.pop(); // Remove filename
  return parts.join('/');
}

/**
 * Generate relative path from one file to another
 */
function getRelativePath(fromPath, toPath) {
  const fromDir = getDirPath(fromPath);
  const toDir = getDirPath(toPath);
  const toFile = toPath.split('/').pop();
  
  if (fromDir === toDir) {
    return toFile; // Same directory, just filename
  }
  
  // Simple relative path calculation
  // For now, assume they're in the same directory or use full path
  // This can be enhanced later if needed
  return toPath;
}

/**
 * Get the paired file path (e.g., foo.vhd -> foo.vhd.md or vice versa)
 */
function getPairedFilePath(filePath) {
  const baseName = getBaseName(filePath);
  const dirPath = getDirPath(filePath);
  const isVhd = filePath.endsWith('.vhd');
  
  if (isVhd) {
    return dirPath === '.' 
      ? `${baseName}.vhd.md`
      : `${dirPath}/${baseName}.vhd.md`;
  } else if (filePath.endsWith('.vhd.md')) {
    return dirPath === '.'
      ? `${baseName}.vhd`
      : `${dirPath}/${baseName}.vhd`;
  }
  return null;
}

/**
 * Extract frontmatter fields from VHDL comment-style frontmatter
 * Returns an object with the fields, or null if not found
 */
function parseVhdlFrontmatter(content) {
  const lines = content.split('\n');
  const frontmatter = {};
  let inFrontmatter = false;
  let frontmatterEnd = -1;
  
  // Look for --- delimiter
  if (lines[0] && lines[0].trim() === '---') {
    inFrontmatter = true;
    for (let i = 1; i < lines.length; i++) {
      if (lines[i].trim() === '---') {
        frontmatterEnd = i;
        break;
      }
      
      // Parse comment lines: -- Key: value
      const match = lines[i].match(/^--\s*(\w+):\s*(.+)$/);
      if (match) {
        const key = match[1].toLowerCase();
        let value = match[2].trim();
        
        // Remove markdown link syntax if present: [text](path) -> path
        const linkMatch = value.match(/\[([^\]]+)\]\(([^)]+)\)/);
        if (linkMatch) {
          value = linkMatch[2]; // Extract the path
        }
        
        frontmatter[key] = value;
      }
    }
  }
  
  return { frontmatter, frontmatterEnd };
}

/**
 * Format a VHDL frontmatter comment line
 */
function formatVhdlFrontmatterLine(key, value) {
  const capitalizedKey = key.charAt(0).toUpperCase() + key.slice(1);
  return `-- ${capitalizedKey}: ${value}`;
}

/**
 * Generate VHDL comment-style frontmatter from an object
 */
function generateVhdlFrontmatter(fields) {
  const lines = ['---'];
  
  // Standard field order - all files have code_link, doc_link, and self_link for consistency
  // type: field for Obsidian template integration
  const fieldOrder = ['file', 'type', 'author', 'created', 'modified', 'code_link', 'doc_link', 'self_link'];
  
  for (const key of fieldOrder) {
    if (fields[key]) {
      lines.push(formatVhdlFrontmatterLine(key, fields[key]));
    }
  }
  
  // Add any extra fields (but skip 'accessed' which is markdown-only)
  for (const [key, value] of Object.entries(fields)) {
    if (!fieldOrder.includes(key) && key !== 'accessed' && !key.endsWith('_link')) {
      lines.push(formatVhdlFrontmatterLine(key, value));
    }
  }
  
  lines.push('---');
  return lines.join('\n');
}

/**
 * Get all directories in the vault (excluding hidden/system folders)
 * Returns array of directory paths relative to vault root
 */
function getAllDirectories() {
  const dirs = new Set(['.']); // Include root directory
  
  // Get all folders from the vault
  const allFolders = app.vault.getAllFolders();
  allFolders.forEach(folder => {
    const path = folder.path;
    // Skip hidden/system folders and Templater folder
    if (path && 
        !path.startsWith('.') && 
        !path.includes('node_modules') &&
        !path.startsWith('Templater/')) {
      dirs.add(path);
    }
  });
  
  return Array.from(dirs).sort();
}

/**
 * Generate README.md content for a VHDL component directory
 * Uses wikilinks with quotes for consistency with frontmatter pattern
 */
function generateReadme(dirPath, baseName, vhdFileName, mdFileName, vhdPath, mdPath) {
  const readmePath = dirPath === '.' ? 'README.md' : `${dirPath}/README.md`;
  const componentName = baseName.replace(/_/g, ' ');
  
  // Use the same wikilink format with quotes as frontmatter
  const vhdLink = `"[[${vhdPath}|${vhdFileName}]]"`;
  const mdLink = `"[[${mdPath}|${mdFileName}]]"`;
  const readmeLink = `"[[${readmePath}|README]]"`;
  
  // Extract wikilinks without quotes for display in headings
  const vhdLinkDisplay = `[[${vhdPath}|${vhdFileName}]]`;
  const mdLinkDisplay = `[[${mdPath}|${mdFileName}]]`;
  const readmeLinkDisplay = `[[${readmePath}|README]]`;
  
  // Use markdown links in "See Also" section (intentional - testing Obsidian's handling)
  const vhdMarkdownLink = `[${vhdFileName}](${vhdPath})`;
  const mdMarkdownLink = `[${mdFileName}](${mdPath})`;
  
  const readme = `# ${readmeLinkDisplay}

This directory houses the __${componentName}__ component. It contains:


| filename                    | type       | link                                                           | GH               | Publish          |
| --------------------------- | ---------- | -------------------------------------------------------------- | ---------------- | ---------------- |
| \`${vhdFileName}\`    | \`rtl_vhdl\` | ${vhdLinkDisplay}       | [XXX fill me in] | [XXX fill me in] |
| \`${mdFileName}\` | \`rtl_md\`   | ${mdLinkDisplay} |                  |                  |
# See Also
## ${vhdMarkdownLink} 
## ${mdMarkdownLink}
`;

  return readme;
}

module.exports = {
  getBaseName,
  getDirPath,
  getRelativePath,
  getPairedFilePath,
  parseVhdlFrontmatter,
  formatVhdlFrontmatterLine,
  generateVhdlFrontmatter,
  getAllDirectories,
  
  /**
   * Get frontmatter fields for a .vhd file
   * Returns an object with standard fields
   */
  async getVhdlFrontmatter(tp, filePath) {
    const baseName = getBaseName(filePath);
    const pairedPath = getPairedFilePath(filePath);
    const relativeDocPath = getRelativePath(filePath, pairedPath);
    
    // Try to read existing file to extract frontmatter
    // All files have code_link, doc_link, and self_link for consistency
    const vhdFileName = `${baseName}.vhd`;
    let existingFields = {
      file: vhdFileName, // Accurate filename
      type: 'rtl_vhdl', // Type for Obsidian template integration
      author: '',
      created: '',
      modified: '',
      code_link: `"[[${filePath}|${vhdFileName}]]"`, // Code file (points to self for .vhd) - wikilink with quotes
      doc_link: `"[[${pairedPath}|${baseName}.vhd.md]]"`, // Doc file - wikilink with quotes
      self_link: `"[[${filePath}|${vhdFileName}]]"` // Self-reference - wikilink with quotes
    };
    
    try {
      const file = app.vault.getAbstractFileByPath(filePath);
      if (file) {
        const content = await app.vault.read(file);
        const { frontmatter } = parseVhdlFrontmatter(content);
        if (Object.keys(frontmatter).length > 0) {
          existingFields = { ...existingFields, ...frontmatter };
        }
      }
    } catch (e) {
      // File doesn't exist yet, use defaults
    }
    
    // Update all three links for consistency (use wikilink format with quotes)
    existingFields.code_link = `"[[${filePath}|${vhdFileName}]]"`; // Code file (points to self for .vhd) - wikilink with quotes
    existingFields.doc_link = `"[[${pairedPath}|${baseName}.vhd.md]]"`; // Doc file - wikilink with quotes
    existingFields.self_link = `"[[${filePath}|${vhdFileName}]]"`; // Self-reference - wikilink with quotes
    
    return existingFields;
  },
  
  /**
   * Get frontmatter fields for a .vhd.md file
   * Returns an object compatible with YAML frontmatter
   */
  async getMarkdownFrontmatter(tp, filePath) {
    const baseName = getBaseName(filePath);
    const pairedPath = getPairedFilePath(filePath);
    const relativeCodePath = getRelativePath(filePath, pairedPath);
    
    // Try to read existing file
    // All files have code_link, doc_link, and self_link for consistency
    const mdFileName = `${baseName}.vhd.md`;
    let existingFields = {
      file: mdFileName, // Accurate filename (the .vhd.md file itself)
      type: 'rtl_md', // Type for Obsidian template integration (simplified)
      author: '',
      created: '',
      modified: '',
      accessed: '',
      code_link: `"[[${pairedPath}|${baseName}.vhd]]"`, // Code file - wikilink with quotes
      doc_link: `"[[${filePath}|${mdFileName}]]"`, // Doc file (points to self for .vhd.md) - wikilink with quotes
      self_link: `"[[${filePath}|${mdFileName}]]"` // Self-reference - wikilink with quotes
    };
    
    try {
      const file = app.vault.getAbstractFileByPath(filePath);
      if (file) {
        await app.fileManager.processFrontMatter(file, fm => {
          if (fm.file) existingFields.file = fm.file;
          if (fm.type) existingFields.type = fm.type;
          if (fm.author) existingFields.author = fm.author;
          if (fm.created) existingFields.created = fm.created;
          if (fm.modified) existingFields.modified = fm.modified;
          if (fm.accessed) existingFields.accessed = fm.accessed;
          if (fm.code_link) existingFields.code_link = fm.code_link;
          if (fm.doc_link) existingFields.doc_link = fm.doc_link;
          if (fm.self_link) existingFields.self_link = fm.self_link;
          // Legacy support for old field names
          if (fm.code && !fm.code_link) existingFields.code_link = `"${fm.code}"`;
          if (fm.doc && !fm.doc_link) existingFields.doc_link = `"${fm.doc}"`;
          if (fm.self && !fm.self_link) existingFields.self_link = `"${fm.self}"`;
        });
      }
    } catch (e) {
      // File doesn't exist yet, use defaults
    }
    
    // Update all three links for consistency (use wikilink format with quotes for mobile compatibility)
    existingFields.code_link = `"[[${pairedPath}|${baseName}.vhd]]"`; // Code file - wikilink with quotes
    existingFields.doc_link = `"[[${filePath}|${mdFileName}]]"`; // Doc file (points to self for .vhd.md) - wikilink with quotes
    existingFields.self_link = `"[[${filePath}|${mdFileName}]]"`; // Self-reference - wikilink with quotes
    
    return existingFields;
  },
  
  /**
   * Create both .vhd and .vhd.md files with proper frontmatter and linking
   * @param {Object} tp - Templater instance
   * @param {string} dirPath - Directory path (e.g., "RUN-RTL" or "rtl")
   * @param {string} baseName - Base name for the component (e.g., "clk_divider")
   * @param {string} author - Author name
   * @returns {Object} Object with vhdPath and mdPath
   */
  async createVhdlPair(tp, dirPath, baseName, author) {
    // Normalize directory path (remove leading/trailing slashes, handle empty)
    const normalizedDir = dirPath.trim().replace(/^\/+|\/+$/g, '') || '.';
    
    // Ensure base name uses underscores (convert hyphens)
    const normalizedBase = baseName.trim().replace(/-/g, '_');
    
    // Build file paths
    const vhdFileName = `${normalizedBase}.vhd`;
    const mdFileName = `${normalizedBase}.vhd.md`;
    const vhdPath = normalizedDir === '.' ? vhdFileName : `${normalizedDir}/${vhdFileName}`;
    const mdPath = normalizedDir === '.' ? mdFileName : `${normalizedDir}/${mdFileName}`;
    
    // Get current timestamp
    const now = new Date();
    const createdDate = now.toISOString().split('T')[0]; // YYYY-MM-DD
    const modifiedDateTime = `${createdDate} ${now.toTimeString().split(' ')[0]}`; // YYYY-MM-DD HH:MM:SS
    
    // Generate VHDL file content
    // All files have code_link, doc_link, and self_link for consistency (orthogonality)
    // Use wikilink format with quotes for mobile compatibility
    const vhdFields = {
      file: vhdFileName, // Accurate filename
      type: 'rtl_vhdl', // Type for Obsidian template integration
      author: author,
      created: createdDate,
      modified: modifiedDateTime,
      code_link: `"[[${vhdPath}|${vhdFileName}]]"`, // Code file (points to self for .vhd) - wikilink with quotes
      doc_link: `"[[${mdPath}|${mdFileName}]]"`, // Doc file (points to .vhd.md) - wikilink with quotes
      self_link: `"[[${vhdPath}|${vhdFileName}]]"` // Self-reference - wikilink with quotes
    };
    const vhdFrontmatter = generateVhdlFrontmatter(vhdFields);
    const vhdSeeAlso = `-- See Also\n-- ## [${mdFileName}](${mdPath})`;
    const vhdContent = `${vhdFrontmatter}\n\n\n-- TODO: Add VHDL code here\n-- This is a placeholder template for the .vhd file\n\n${vhdSeeAlso}\n`;
    
    // Generate markdown file content
    // All files have code_link, doc_link, and self_link for consistency (orthogonality)
    // Use wikilink format with quotes in YAML frontmatter for mobile compatibility
    const mdFields = {
      file: mdFileName, // Accurate filename (the .vhd.md file itself)
      type: 'rtl_md', // Type for Obsidian template integration (simplified from rtl_vhdl_md)
      author: author,
      created: createdDate,
      modified: modifiedDateTime,
      accessed: modifiedDateTime,
      code_link: `"[[${vhdPath}|${vhdFileName}]]"`, // Code file (points to .vhd) - wikilink with quotes
      doc_link: `"[[${mdPath}|${mdFileName}]]"`, // Doc file (points to self for .vhd.md) - wikilink with quotes
      self_link: `"[[${mdPath}|${mdFileName}]]"` // Self-reference - wikilink with quotes
    };
    const mdFrontmatter = `---\nfile: ${mdFields.file}\ntype: ${mdFields.type}\nauthor: ${mdFields.author}\ncreated: ${mdFields.created}\nmodified: ${mdFields.modified}\naccessed: ${mdFields.accessed}\ncode_link: ${mdFields.code_link}\ndoc_link: ${mdFields.doc_link}\nself_link: ${mdFields.self_link}\n\n---`;
    // Extract wikilink from self_link (remove quotes) for heading
    const selfLinkForHeading = mdFields.self_link.replace(/^"|"$/g, ''); // Remove surrounding quotes
    const mdSeeAlso = `# See Also\n## [${vhdFileName}](${vhdPath})`;
    const mdContent = `${mdFrontmatter}\n\n# ${selfLinkForHeading}\n\n## Overview\n\n[Description of this VHDL component]\n\n## Architecture\n\n[Architecture details]\n\n## Usage\n\n[Usage instructions]\n\n${mdSeeAlso}\n\n---\n`;
    
    // Create both files
    try {
      // Check if files already exist
      const existingVhd = app.vault.getAbstractFileByPath(vhdPath);
      const existingMd = app.vault.getAbstractFileByPath(mdPath);
      
      if (existingVhd || existingMd) {
        throw new Error(`Files already exist: ${existingVhd ? vhdPath : ''} ${existingMd ? mdPath : ''}`);
      }
      
      // Create .vhd file
      await app.vault.create(vhdPath, vhdContent);
      
      // Create .vhd.md file
      await app.vault.create(mdPath, mdContent);
      
      // Create README.md file in the same directory
      const readmePath = normalizedDir === '.' ? 'README.md' : `${normalizedDir}/README.md`;
      const readmeContent = generateReadme(normalizedDir, normalizedBase, vhdFileName, mdFileName, vhdPath, mdPath);
      
      // Only create README if it doesn't exist (don't overwrite existing)
      const existingReadme = app.vault.getAbstractFileByPath(readmePath);
      if (!existingReadme) {
        await app.vault.create(readmePath, readmeContent);
      }
      
      // If templater_times is available, update the markdown file's frontmatter
      // Note: We can't use touch_current_file here since we're not in that file's context
      // The templater_times hook will update it when the file is opened
      
      return { vhdPath, mdPath, readmePath, success: true };
    } catch (error) {
      // Clean up if one file was created but the other failed
      try {
        const vhdFile = app.vault.getAbstractFileByPath(vhdPath);
        if (vhdFile) await app.vault.delete(vhdFile);
      } catch (e) {}
      try {
        const mdFile = app.vault.getAbstractFileByPath(mdPath);
        if (mdFile) await app.vault.delete(mdFile);
      } catch (e) {}
      
      throw error;
    }
  }
};


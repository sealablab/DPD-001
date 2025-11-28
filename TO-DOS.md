# TO-DOS

## Templater README Link Format Investigation - 2025-11-28 02:31

- **Investigate Obsidian link tracking for README files** - Test whether markdown links `[file](path)` in generated READMEs get updated on directory rename. **Problem:** Discovered that Obsidian doesn't update all link types consistently - wikilinks in tables weren't tracked, VHDL file links weren't tracked. Need to verify the new simplified README format (H2 + markdown links) actually gets tracked properly. **Files:** `Templater/Templates/user_scripts/templater_vhdl_pair.js:206-227`, `boot_prop_files/README.md`. **Solution:** Create test component, rename directory, verify links update. If not, consider using wikilinks `[[path|display]]` instead of markdown links.

## Boot Subsystem Integration & Docs Update - 2025-11-28 02:35

- **Integrate rtl/boot components into DPD architecture** - Flesh out the boot subsystem VHDL files with actual implementation. **Problem:** Boot components (B0_BOOT_TOP, B1_BOOT_BIOS, L2_BUFF_LOADER, P3_PROG_START) are templated placeholders that need to implement the P0/P1/P2 boot phases described in platform-boot-up.md. **Files:** `rtl/boot/B0_BOOT_TOP.vhd`, `rtl/boot/B1_BOOT_BIOS.vhd`, `rtl/boot/L2_BUFF_LOADER.vhd`, `rtl/boot/P3_PROG_START.vhd`, `rtl/boot/README.md`. **Solution:** Start with BRAM loader (L2), then wire up boot sequence in B0/B1, finally hand off to P3.

- **Cross-reference docs with boot implementation** - Keep docs updated as boot subsystem is implemented. **Problem:** docs/platform-boot-up.md describes the boot concept but needs to reference actual RTL files once implemented. Other docs (api-v4.md, network-register-sync.md) may need updates for boot-phase CR usage. **Files:** `docs/platform-boot-up.md`, `docs/api-v4.md`, `docs/network-register-sync.md`, `docs/README.md`. **Solution:** Update docs incrementally as each boot component is implemented; add links to RTL files; update docs/README.md file organization tree.

## Uncommitted Work-in-Progress - 2025-11-28 02:40

- **Review and commit bootup-proposal reorganization** - Bootup proposal docs were restructured but not committed. **Problem:** Work-in-progress changes sitting in working directory need review before committing. **Files:** `docs/api-v4.md` (modified), `docs/platform-boot-up.md` (modified), `docs/bootup-proposal/B000_BOOT.md` (new), `docs/bootup-proposal/B010_BIOS.md` (new), `docs/bootup-proposal/B100_PROG.md` (new). **Solution:** Review changes with `git diff`, commit when ready. Old files (BITS_BIOS.md, BPD_RUNP_RUNB.md) were deleted/renamed.


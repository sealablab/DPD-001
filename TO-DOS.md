# TO-DOS

## Templater README Link Format Investigation - 2025-11-28 02:31

- **Investigate Obsidian link tracking for README files** - Test whether markdown links `[file](path)` in generated READMEs get updated on directory rename. **Problem:** Discovered that Obsidian doesn't update all link types consistently - wikilinks in tables weren't tracked, VHDL file links weren't tracked. Need to verify the new simplified README format (H2 + markdown links) actually gets tracked properly. **Files:** `Templater/Templates/user_scripts/templater_vhdl_pair.js:206-227`, `boot_prop_files/README.md`. **Solution:** Create test component, rename directory, verify links update. If not, consider using wikilinks `[[path|display]]` instead of markdown links.

## Boot Subsystem Integration & Docs Update - 2025-11-28 02:35

- **Integrate rtl/boot components into DPD architecture** - Flesh out the boot subsystem VHDL files with actual implementation. **Problem:** Boot components (B0_BOOT_TOP, B1_BOOT_BIOS, L2_BUFF_LOADER, P3_PROG_START) are templated placeholders that need to implement the P0/P1/P2 boot phases described in platform-boot-up.md. **Files:** `rtl/boot/B0_BOOT_TOP.vhd`, `rtl/boot/B1_BOOT_BIOS.vhd`, `rtl/boot/L2_BUFF_LOADER.vhd`, `rtl/boot/P3_PROG_START.vhd`, `rtl/boot/README.md`. **Solution:** Start with BRAM loader (L2), then wire up boot sequence in B0/B1, finally hand off to P3.

- **Cross-reference docs with boot implementation** - Keep docs updated as boot subsystem is implemented. **Problem:** docs/platform-boot-up.md describes the boot concept but needs to reference actual RTL files once implemented. Other docs (api-v4.md, network-register-sync.md) may need updates for boot-phase CR usage. **Files:** `docs/platform-boot-up.md`, `docs/api-v4.md`, `docs/network-register-sync.md`, `docs/README.md`. **Solution:** Update docs incrementally as each boot component is implemented; add links to RTL files; update docs/README.md file organization tree.

## Uncommitted Work-in-Progress - 2025-11-28 02:40

- **Review and commit bootup-proposal reorganization** - Bootup proposal docs were restructured but not committed. **Problem:** Work-in-progress changes sitting in working directory need review before committing. **Files:** `docs/api-v4.md` (modified), `docs/platform-boot-up.md` (modified), `docs/bootup-proposal/B000_BOOT.md` (new), `docs/bootup-proposal/B010_BIOS.md` (new), `docs/bootup-proposal/B100_PROG.md` (new). **Solution:** Review changes with `git diff`, commit when ready. Old files (BITS_BIOS.md, BPD_RUNP_RUNB.md) were deleted/renamed.

## BIOS Clock Domain Verification - 2025-11-29 18:30

- **Run clock_probe experiment before first BIOS bitstream build** - Empirically verify whether VHDL fabric runs at ADC clock (125 MHz) or MCC fabric clock (31.25 MHz). **Problem:** Official datasheets only document ADC sample rate (125 MHz for Go). Example code uses 31.25 MHz for timing calculations. This 4× difference affects ALL timing in BIOS: ROM playback rate, FSM counters, LOADER strobe timing, HVS update rate. **Files:** `rtl/experiments/clock_probe.vhd`, `py_tools/experiments/clock_probe_test.py`, `docs/mcc-fabric-clock.md`, `docs/moku-clock-domains.md`. **Solution:** (1) Compile clock_probe.vhd for Moku:Go and Moku:Lab via Cloud Compile, (2) Run clock_probe_test.py to measure pulse width, (3) If 128ns → VHDL runs at 31.25 MHz, update clk_utils.py; If 32ns → VHDL runs at 125 MHz, example code has implicit /4. **Impact:** All BIOS timing constants depend on this result!

## Happy CLI Type Shim Upstream PR - 2025-11-29 01:40

- **Submit PR to happy-cli with claude-code type shim** - Share our fix for the missing type exports in newer @anthropic-ai/claude-code versions. **Problem:** happy-cli bundles old claude-code (2.0.24), and newer versions (2.0.31+) removed `SDKMessage`/`SDKUserMessage` type exports, breaking the build. Multiple users report this in issues #40, #49. **Files:** `happy-cli/src/types/claude-code-shim.d.ts` (our fix), `happy-cli/src/utils/MessageQueue.ts:1` (the import that needed it). **Solution:** Test the shim in real usage first, then fork repo and submit PR with the 20-line type definition file. Reference issues #40, #49, #53 in PR description.

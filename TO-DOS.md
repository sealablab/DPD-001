# TO-DOS

## Templater README Link Format Investigation - 2025-11-28 02:31

- **Investigate Obsidian link tracking for README files** - Test whether markdown links `[file](path)` in generated READMEs get updated on directory rename. **Problem:** Discovered that Obsidian doesn't update all link types consistently - wikilinks in tables weren't tracked, VHDL file links weren't tracked. Need to verify the new simplified README format (H2 + markdown links) actually gets tracked properly. **Files:** `Templater/Templates/user_scripts/templater_vhdl_pair.js:206-227`, `boot_prop_files/README.md`. **Solution:** Create test component, rename directory, verify links update. If not, consider using wikilinks `[[path|display]]` instead of markdown links.

## Boot Subsystem Integration & Docs Update - 2025-11-28 02:35

- **Integrate rtl/boot components into DPD architecture** - Flesh out the boot subsystem VHDL files with actual implementation. **Problem:** Boot components (B0_BOOT_TOP, B1_BOOT_BIOS, L2_BUFF_LOADER, P3_PROG_START) are templated placeholders that need to implement the P0/P1/P2 boot phases described in platform-boot-up.md. **Files:** `rtl/boot/B0_BOOT_TOP.vhd`, `rtl/boot/B1_BOOT_BIOS.vhd`, `rtl/boot/L2_BUFF_LOADER.vhd`, `rtl/boot/P3_PROG_START.vhd`, `rtl/boot/README.md`. **Solution:** Start with BRAM loader (L2), then wire up boot sequence in B0/B1, finally hand off to P3.

- **Cross-reference docs with boot implementation** - Keep docs updated as boot subsystem is implemented. **Problem:** docs/platform-boot-up.md describes the boot concept but needs to reference actual RTL files once implemented. Other docs (api-v4.md, network-register-sync.md) may need updates for boot-phase CR usage. **Files:** `docs/platform-boot-up.md`, `docs/api-v4.md`, `docs/network-register-sync.md`, `docs/README.md`. **Solution:** Update docs incrementally as each boot component is implemented; add links to RTL files; update docs/README.md file organization tree.

## BIOS Clock Domain Verification - 2025-11-29 18:30

- **Run clock_probe experiment before first BIOS bitstream build** - Empirically verify whether VHDL fabric runs at ADC clock (125 MHz) or MCC fabric clock (31.25 MHz). **Problem:** Official datasheets only document ADC sample rate (125 MHz for Go). Example code uses 31.25 MHz for timing calculations. This 4× difference affects ALL timing in BIOS: ROM playback rate, FSM counters, LOADER strobe timing, HVS update rate. **Files:** `rtl/experiments/clock_probe.vhd`, `py_tools/experiments/clock_probe_test.py`, `docs/mcc-fabric-clock.md`, `docs/moku-clock-domains.md`. **Solution:** (1) Compile clock_probe.vhd for Moku:Go and Moku:Lab via Cloud Compile, (2) Run clock_probe_test.py to measure pulse width, (3) If 128ns → VHDL runs at 31.25 MHz, update clk_utils.py; If 32ns → VHDL runs at 125 MHz, example code has implicit /4. **Impact:** All BIOS timing constants depend on this result!

## Happy CLI Type Shim Upstream PR - 2025-11-29 01:40

- **Submit PR to happy-cli with claude-code type shim** - Share our fix for the missing type exports in newer @anthropic-ai/claude-code versions. **Problem:** happy-cli bundles old claude-code (2.0.24), and newer versions (2.0.31+) removed `SDKMessage`/`SDKUserMessage` type exports, breaking the build. Multiple users report this in issues #40, #49. **Files:** `happy-cli/src/types/claude-code-shim.d.ts` (our fix), `happy-cli/src/utils/MessageQueue.ts:1` (the import that needed it). **Solution:** Test the shim in real usage first, then fork repo and submit PR with the 20-line type definition file. Reference issues #40, #49, #53 in PR description.

## Rename PROG_DPD Symbols in BOOT Subsystem - 2025-11-30 15:07

- **Rename 'PROG_DPD_INST' and related symbols inside BOOT/BIOS** - Decouple BOOT subsystem naming from the specific 'DPD' application. **Problem:** B0_BOOT_TOP.vhd uses `PROG_DPD_INST` label and references `DPD_shim` entity directly, coupling the generic BOOT dispatcher to a specific application. The BOOT subsystem should be application-agnostic. **Files:** `rtl/boot/B0_BOOT_TOP.vhd:260` (`PROG_DPD_INST` label), `rtl/boot/B0_BOOT_TOP.vhd.md:73` (documentation reference). **Solution:** Rename to `PROG_APP_INST` or `PROG_INST`; consider using a generic `ProgWrapper` entity pattern similar to `BootWrapper` for application-swappable architecture.

## Rename CR0 References to BOOT_CR0 in Docs - 2025-11-30 15:16

- **Update documentation to use BOOT_CR0 instead of hardcoded CR0** - Establish clear naming for BOOT subsystem control register. **Problem:** Documentation (especially B0_BOOT_TOP.vhd.md Architecture section) references `CR0[31:29]`, `CR0[28:25]` directly. As BOOT becomes a reusable subsystem, the control register should have a semantic name (`BOOT_CR0`) rather than positional (`CR0`). **Files:** `rtl/boot/B0_BOOT_TOP.vhd.md:113-114` (CR0 references in Architecture), `docs/bootup-proposal/BOOT-FSM-spec.md`, `rtl/forge_common_pkg.vhd` (constant definitions). **Solution:** Define `BOOT_CR0` alias in forge_common_pkg.vhd; update docs to reference `BOOT_CR0` with note that it maps to `Control0` at the MCC interface level. Low priority - cosmetic improvement.

## Review BLANK_TOP_FILE Template - 2025-11-30 15:26

- **Review and merge BLANK_TOP_FILE.vhd.md into Templater system** - Integrate the new RTL documentation template. **Problem:** Created a blank template for `.vhd.md` documentation files based on B0_BOOT_TOP.vhd.md review session. Template needs review before becoming official, and may need integration with existing Templater user scripts. **Files:** `Templater/Templates/BLANK_TOP_FILE.vhd.md` (new), `Templater/Templates/user_scripts/templater_vhdl_pair.js` (may need update). **Solution:** Review template structure, replace `{{date}}` placeholders with proper Templater syntax, consider merging with existing `new_vhdl_component` template or creating separate `new_vhdl_top_doc` command.

## Replace BIOS Stub with MVP Implementation - 2025-11-30 15:40

- **Replace B1_BOOT_BIOS validation stub with real BIOS functionality** - Implement actual ROM waveform generation. **Problem:** Current B1_BOOT_BIOS.vhd is a validation stub that just cycles IDLE→RUN→DONE with configurable delays. The real BIOS needs to: (1) read waveform data from ROM Bank 0, (2) output waveforms on DAC, (3) provide diagnostic/calibration functions. **Files:** `rtl/boot/B1_BOOT_BIOS.vhd:37-172` (current stub), `rtl/boot/B1_BOOT_BIOS.vhd.md` (documentation), `docs/bootup-proposal/BOOT-ROM-primitives-spec.md` (ROM waveform table). **Solution:** Keep existing FSM structure but add ROM instantiation, address counter, and DAC output logic. MVP = output SIN_128 waveform on OutputA when in RUN state. Depends on clock domain verification (see BIOS Clock Domain todo).

## P1: Unified ENV_BBUF Interface - 2025-11-30 16:19

- **Design unified ENV_BBUF access interface for all modules** - Create simple, consistent interface for BIOS/LOADER/PROG to access the 4×4KB environment buffers. **Problem:** Currently L2_BUFF_LOADER owns the BRAMs and exposes a read interface (`bram_rd_addr`, `bram_rd_sel`, `bram_rd_data`), but there's no documented interface pattern for other modules (BIOS, PROG) to access these buffers. Need a clean abstraction before synthesis. **Files:** `rtl/boot/L2_BUFF_LOADER.vhd:70-73` (current read interface), `rtl/boot/B0_BOOT_TOP.vhd` (parent that routes signals), `docs/BOOT-FSM-spec.md:182-196` (ENV_BBUF allocation). **Solution:** Options: (1) Keep BRAMs in LOADER, route read ports through B0_BOOT_TOP to active module, (2) Move BRAMs to B0_BOOT_TOP, give LOADER write-only access, (3) Create shared `env_bbuf_pkg.vhd` with interface types. Must decide before first real synthesis.

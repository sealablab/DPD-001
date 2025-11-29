---
created: 2025-11-29
modified: 2025-11-29 00:17:30
accessed: 2025-11-29 00:18:52
---

# HANDOFF: Full Synthesis-Ready DPD System

**Created:** 2025-11-29
**Status:** RUNP implementation complete, ready for full synthesis
**Priority:** High - Enable vendor synthesis pipeline

---

## Session Summary

Successfully completed the RUNP implementation, enabling BOOT→PROG handoff. The DPD system now has complete boot subsystem integration with working BOOT dispatcher FSM that can transition to the main DPD application.

**Key Achievement:** Full BOOT subsystem integration with one-way handoff to PROG (DPD) complete.

---

## Current System State

### ✅ **What's Working**

1. **BOOT Subsystem Complete:**
   - BOOT dispatcher FSM (6 states: BOOT_P0/P1, BIOS/LOAD/PROG_ACTIVE, FAULT)
   - LOADER module with CRC validation (L2_BUFF_LOADER.vhd)
   - BIOS diagnostics module (B1_BOOT_BIOS.vhd)
   - PROG handoff via DPD_shim instantiation

2. **DPD Core Functionality:**
   - 6-state FSM (INITIALIZING, IDLE, ARMED, FIRING, COOLDOWN, FAULT)
   - HVS encoding on OutputC (3277 digital units/state = 0.5V steps)
   - Network register synchronization (CR2-CR10 gated on FSM state)
   - Hardware trigger support via moku_voltage_threshold_trigger_core

3. **Compilation Pipeline:**
   - GHDL compilation succeeds for all modules
   - Proper dependency ordering in Makefile
   - No entity name collisions (BootWrapper vs CustomWrapper)

### 📂 **File Structure Status**

```
rtl/
├── DPD.vhd                              ✅ Layer 1: TOP (CustomWrapper)
├── DPD_shim.vhd                         ✅ Layer 2: Register mapping + HVS
├── DPD_main.vhd                         ✅ Layer 3: FSM application logic
├── forge_hierarchical_encoder.vhd       ✅ HVS encoder
├── moku_voltage_threshold_trigger_core.vhd  ✅ Hardware trigger
├── forge_common_pkg.vhd                 ✅ Common types/constants
├── CustomWrapper_test_stub.vhd          ✅ Test entity for DPD
└── boot/
    ├── B0_BOOT_TOP.vhd                  ✅ Boot dispatcher + DPD integration
    ├── B1_BOOT_BIOS.vhd                 ✅ BIOS diagnostics
    ├── L2_BUFF_LOADER.vhd               ✅ BRAM buffer loader
    ├── BootWrapper_test_stub.vhd        ✅ Test entity for BOOT
    └── loader_crc16.vhd                 ✅ CRC utility
```

### 🧪 **Test Coverage**

- **CocoTB Simulation:** P1/P2 tests pass for both DPD and BOOT FSMs
- **P3 RUNP Tests:** Created (untested but syntax-valid)
- **Hardware Tests:** P1 level exists for DPD core

---

## Next Session Goal: Full Synthesis Pipeline

**Objective:** Create a fully synthesizable bitstream that includes both BOOT subsystem and DPD functionality, ready for vendor synthesis tools.

### Phase 1: GHDL Synthesis Validation (30 min)

**Goal:** Ensure the integrated system can be synthesized in GHDL without errors.

**Tasks:**
1. **Test P3 RUNP functionality:**
   ```bash
   cd tests/sim && python run.py boot_fsm.P3_runp
   ```

2. **Run synthesis test in GHDL:**
   ```bash
   make compile  # Already works
   ghdl --synth --work=WORK BootWrapper boot_forge  # Test synthesis
   ```

3. **Verify both entities synthesizable:**
   ```bash
   ghdl --synth --work=WORK CustomWrapper dpd_forge  # DPD
   ghdl --synth --work=WORK BootWrapper boot_forge   # BOOT
   ```

### Phase 2: Create Unified Top-Level (45 min)

**Goal:** Create a single synthesizable top-level that can switch between BOOT and DPD modes.

**Options to Consider:**

**Option A: Unified Wrapper (Recommended)**
- Create `UnifiedWrapper.vhd` that instantiates both BootWrapper and CustomWrapper
- Add configuration generic to select active subsystem
- Single bitstream, runtime-configurable

**Option B: Conditional Synthesis**
- Use VHDL generate statements in existing wrappers
- Compile-time selection between BOOT and DPD modes
- Cleaner for vendor tools

**Key Files to Create/Modify:**
- `rtl/UnifiedWrapper.vhd` (new top-level)
- Update `Makefile` synthesis targets
- Create synthesis configuration files

### Phase 3: Vendor Synthesis Prep (30 min)

**Goal:** Ensure system is ready for vendor synthesis tools (Vivado/Quartus/etc).

**Tasks:**
1. **Check for synthesis-problematic constructs:**
   - Verify all VHDL is synthesizable (no file I/O, timing delays, etc.)
   - Check clock domain crossings
   - Verify reset strategies

2. **Create synthesis scripts:**
   - Add vendor-specific synthesis targets to Makefile
   - Create constraint files for timing/pinout
   - Test with vendor tools if available

3. **Bitstream packaging:**
   - Create proper directory structure for Moku CloudCompile
   - Package as `.tar` for deployment testing

---

## Key Technical Decisions Made

### 1. **FORGE Control Simplification**
- Replaced `combine_forge_ready()` with simple AND logic in `DPD_shim.vhd:218`
- BOOT subsystem already handles RUN gating, so DPD doesn't need to re-implement it

### 2. **Entity Name Strategy**
- `BootWrapper` entity for BOOT subsystem (avoids GHDL collision)
- `CustomWrapper` entity for DPD subsystem (maintains MCC compatibility)
- Both architectures can coexist in same WORK library

### 3. **HVS Encoding Transition**
- BOOT uses pre-PROG encoding (197 units/state, 0-0.94V)
- DPD uses PROG encoding (3277 units/state, 0-2.0V in 0.5V steps)
- Intentional voltage jump (0.03V→0.5V) provides visual handoff confirmation

### 4. **One-Way PROG Semantics**
- RUNP handoff is irreversible (no RET from PROG)
- Only RUN gate removal returns to BOOT_P0
- Matches intended use: BOOT is setup, PROG is runtime

---

## Potential Synthesis Issues to Watch

### 1. **Clock Domain Considerations**
- All modules currently use single `Clk` domain
- Verify no implicit clock domain crossings in complex paths
- Check reset distribution strategy

### 2. **BRAM Inference**
- `L2_BUFF_LOADER` uses inferred BRAM (4x 4KB blocks)
- Verify vendor tools infer block RAM correctly
- May need explicit BRAM instantiation for some targets

### 3. **Signal Naming Conflicts**
- Both BootWrapper and CustomWrapper use similar signal names
- Verify no conflicts when instantiated in unified top-level

### 4. **Timing Closure**
- HVS encoder has complex arithmetic (multiply + add)
- May need pipeline stages for high-frequency targets
- Check critical path timing

---

## Testing Strategy for Synthesis

### 1. **Incremental Approach**
1. Synthesize forge_common_pkg + utilities first
2. Synthesize DPD_main standalone
3. Synthesize DPD_shim + DPD_main
4. Synthesize BOOT subsystem standalone
5. Synthesize unified system

### 2. **Validation Points**
- GHDL synthesis passes (catches VHDL issues)
- Vendor synthesis passes (catches platform issues)
- Resource utilization reasonable (< 50% FPGA capacity)
- Timing closure achieved (meets 125MHz requirement)

### 3. **Fallback Plans**
- If unified synthesis fails, use separate bitstreams
- If timing fails, reduce clock frequency or add pipeline
- If resources exceeded, remove non-essential features

---

## Files to Focus On

### Critical Path Files (must work)
1. `rtl/forge_common_pkg.vhd` - Foundation constants/types
2. `rtl/DPD_main.vhd` - Core FSM logic
3. `rtl/DPD_shim.vhd` - Register interface
4. `rtl/boot/B0_BOOT_TOP.vhd` - BOOT dispatcher + PROG integration

### Synthesis Infrastructure (create/modify)
1. `rtl/UnifiedWrapper.vhd` - New unified top-level
2. `Makefile` - Add synthesis targets
3. `synthesis/` - New directory for vendor scripts
4. Constraint files for timing/pinout

### Testing (verify)
1. `tests/sim/boot_fsm/P3_runp.py` - RUNP handoff validation
2. `tests/sim/dpd/P1_basic.py` - DPD core functionality
3. Integration tests for unified system

---

## Open Questions

1. **Synthesis Tool Preference:** Which vendor tools are available? (Vivado, Quartus, etc.)
2. **Resource Budget:** What's the target FPGA capacity utilization?
3. **Timing Requirements:** Is 125MHz the hard requirement or can we relax?
4. **Campaign Mode Timeline:** How much complexity should we add before initial synthesis?
5. **Bitstream Format:** What's the exact packaging format for Moku CloudCompile?

---

## Success Criteria

### Phase 1 (GHDL)
- [ ] P3 RUNP tests pass
- [ ] `ghdl --synth` succeeds for both BootWrapper and CustomWrapper
- [ ] No VHDL syntax/semantic errors

### Phase 2 (Unified System)
- [ ] Single synthesizable top-level created
- [ ] Both BOOT and DPD functionality accessible
- [ ] GHDL synthesis passes for unified system

### Phase 3 (Vendor Ready)
- [ ] Vendor synthesis tools accept design
- [ ] Resource utilization < 50% of target FPGA
- [ ] Timing closure achieved at 125MHz
- [ ] Bitstream package created

---

## References

- **RUNP Implementation:** `rtl/boot/B0_BOOT_TOP.vhd:256-298`
- **FORGE Control Fix:** `rtl/DPD_shim.vhd:217-218`
- **Build System:** `Makefile:7-19`
- **Test Suite:** `tests/sim/boot_fsm/P3_runp.py`
- **Architecture Docs:** `docs/bootup-proposal/BOOT-FSM-spec.md`
- **API Reference:** `docs/api-v4.md`
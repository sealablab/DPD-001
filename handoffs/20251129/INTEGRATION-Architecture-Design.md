---
status: DRAFT
date: 2025-11-29
related:
  - "[[HANDOFF-Full-Synthesis-Ready]]"
  - "[[SYNTHESIS-Planning-QA]]"
tags:
  - architecture
  - integration
  - boot
  - dpd
created: 2025-11-29
---

# BOOT+DPD Integration Architecture Design

This document outlines the strategy for integrating the BOOT subsystem and DPD application into a single runtime-configurable bitstream.

## Current State

### Separate Implementations

**DPD Subsystem** (`rtl/DPD.vhd`):
```vhdl
entity CustomWrapper is ... end entity;
architecture bpd_forge of CustomWrapper is
    -- Instantiates DPD_shim directly
    -- Extracts CR0[31:29] RUN gate
    -- Extracts CR0[2:0] lifecycle controls
end architecture;
```

**BOOT Subsystem** (`rtl/boot/B0_BOOT_TOP.vhd`):
```vhdl
entity BootWrapper is ... end entity;
architecture boot_forge of BootWrapper is
    -- 6-state BOOT FSM
    -- Instantiates: BIOS, LOADER, DPD_shim (as PROG)
    -- Combinatorial output muxing
    -- Pre-PROG HVS encoding
end architecture;
```

**Conflict**: Two entity declarations, tested separately, cannot coexist in vendor synthesis.

---

## Integration Strategy: Wrapper Consolidation

### Approach

**Keep BOOT subsystem modular**, but rebind it to `CustomWrapper` entity:

1. **Rename BOOT architecture** to avoid confusion with DPD
2. **Replace DPD.vhd** with thin wrapper that instantiates BOOT dispatcher
3. **BOOT dispatcher becomes the top-level** (it already contains DPD_shim!)
4. **Delete BootWrapper** test stub (no longer needed)

### Architecture Hierarchy

```
CustomWrapper entity (MCC-provided interface)
  └─ bpd_forge architecture (NEW DPD.vhd)
      └─ BOOT_DISPATCHER component (B0_BOOT_TOP.vhd, arch renamed)
          ├─ BIOS module
          ├─ LOADER module (with ENV_BBUFs)
          └─ PROG module (DPD_shim → DPD_main)
```

The **BOOT_DISPATCHER** is always present, but:
- When `CR0 = 0xF0000000` (RUNP), it routes to DPD_shim
- When `CR0 = 0xE8000000` (RUNB), it routes to BIOS
- When `CR0 = 0xE4000000` (RUNL), it routes to LOADER

---

## Implementation Plan

### Phase 1: Rename BOOT Architecture

**File**: `rtl/boot/B0_BOOT_TOP.vhd`

**Change**:
```vhdl
-- OLD:
architecture boot_forge of BootWrapper is
    ...
end architecture boot_forge;

-- NEW:
architecture boot_dispatcher of BootWrapper is
    ...
end architecture boot_dispatcher;
```

**Rationale**: Avoids name collision with `bpd_forge` in DPD.vhd

---

### Phase 2: Create Unified CustomWrapper

**File**: `rtl/DPD.vhd` (COMPLETE REWRITE)

**New Content**:
```vhdl
--------------------------------------------------------------------------------
-- File: DPD.vhd
-- Description:
--   CustomWrapper architecture for BOOT+DPD unified bitstream.
--   This is a thin wrapper that instantiates B0_BOOT_TOP (BOOT dispatcher).
--
-- CR0 Bit Layout (from BOOT-FSM-spec.md):
--   CR0[31:29] = RUN gate (R/U/N)
--   CR0[28]    = P (PROG select)
--   CR0[27]    = B (BIOS select)
--   CR0[26]    = L (LOADER select)
--   CR0[25]    = R (RESET select)
--   CR0[24]    = RET (return to BOOT_P1)
--
-- Commands:
--   0xF0000000 = RUNP (activate DPD application)
--   0xE8000000 = RUNB (activate BIOS diagnostics)
--   0xE4000000 = RUNL (activate buffer loader)
--   0xE2000000 = RUNR (soft reset to BOOT_P0)
--
-- Architecture:
--   Layer 0: DPD.vhd (THIS FILE - thin wrapper, binds CustomWrapper entity)
--   Layer 1: B0_BOOT_TOP.vhd (BOOT dispatcher FSM)
--   Layer 2: DPD_shim.vhd (PROG mode only, handles CR2-CR10 mapping)
--   Layer 3: DPD_main.vhd (DPD FSM application logic)
--------------------------------------------------------------------------------

library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;

architecture bpd_forge of CustomWrapper is
    -- No internal signals needed - straight passthrough
begin

    ----------------------------------------------------------------------------
    -- BOOT Dispatcher Instantiation
    --
    -- The BOOT dispatcher (B0_BOOT_TOP.vhd) is the actual top-level logic.
    -- It handles:
    -- - BOOT FSM (6 states: P0, P1, BIOS, LOAD, PROG, FAULT)
    -- - Module selection via CR0[28:25]
    -- - Output muxing (combinatorial, no delay)
    -- - HVS encoding (pre-PROG for BOOT/BIOS/LOADER, DPD for PROG)
    --
    -- Component declaration uses BootWrapper entity (from B0_BOOT_TOP.vhd)
    -- but we instantiate it here as a component inside CustomWrapper.
    ----------------------------------------------------------------------------
    BOOT_DISPATCHER: entity WORK.BootWrapper(boot_dispatcher)
        port map (
            -- Clock and Reset
            Clk   => Clk,
            Reset => Reset,

            -- MCC I/O (straight passthrough)
            InputA  => InputA,
            InputB  => InputB,
            InputC  => InputC,
            OutputA => OutputA,
            OutputB => OutputB,
            OutputC => OutputC,

            -- Control Registers (all 16 passed through)
            Control0  => Control0,
            Control1  => Control1,
            Control2  => Control2,
            Control3  => Control3,
            Control4  => Control4,
            Control5  => Control5,
            Control6  => Control6,
            Control7  => Control7,
            Control8  => Control8,
            Control9  => Control9,
            Control10 => Control10,
            Control11 => Control11,
            Control12 => Control12,
            Control13 => Control13,
            Control14 => Control14,
            Control15 => Control15
        );

end architecture bpd_forge;

--------------------------------------------------------------------------------
-- Usage Instructions
--------------------------------------------------------------------------------
--
-- 1. Platform Boot Sequence:
--
--    a) Power-on: Control0 = 0x00000000 → BOOT_P0
--    b) Set RUN gate: Control0 = 0xE0000000 → BOOT_P1 (dispatcher ready)
--
-- 2. Module Selection:
--
--    a) Activate DPD (main application):
--       Control0 = 0xF0000000  # RUNP
--       → BOOT transitions to PROG_ACTIVE
--       → DPD_shim takes control, CR2-CR10 become active
--       → DPD FSM runs (IDLE → ARMED → FIRING → COOLDOWN)
--
--    b) Activate BIOS (diagnostics):
--       Control0 = 0xE8000000  # RUNB
--       → BIOS outputs known signals for wiring validation
--
--    c) Activate LOADER (buffer population):
--       Control0 = 0xE4000000  # RUNL
--       → LOADER accepts data via CR1-CR4, populates ENV_BBUFs
--
--    d) Return from BIOS/LOADER:
--       Control0 = 0xE1000000  # RET
--       → Returns to BOOT_P1 dispatcher
--
--    e) Soft reset:
--       Control0 = 0xE2000000  # RUNR
--       → Returns to BOOT_P0 (clears ENV_BBUFs)
--
-- 3. DPD Application Mode (PROG_ACTIVE):
--
--    Once RUNP is issued, the DPD application controls all outputs.
--    This is a **one-way transition** - cannot return to BOOT without reset.
--
--    DPD uses CR0[2:0] for lifecycle control:
--    - CR0[2] = arm_enable
--    - CR0[1] = fault_clear
--    - CR0[0] = sw_trigger
--
--    DPD uses CR2-CR10 for configuration (voltage, timing, etc.)
--    See docs/api-v4.md for full register map.
--
-- 4. Expert Workflow (Example):
--
--    # Boot platform
--    Control0 = 0xE0000000  # RUN
--
--    # Load ENV_BBUFs with config data
--    Control0 = 0xE4000000  # RUNL
--    ... (populate buffers via LOADER protocol)
--    Control0 = 0xE1000000  # RET
--
--    # Run diagnostics
--    Control0 = 0xE8000000  # RUNB
--    ... (observe BIOS outputs)
--    Control0 = 0xE1000000  # RET
--
--    # Launch DPD application
--    Control0 = 0xF0000000  # RUNP (one-way!)
--    ... (configure DPD via CR2-CR10, arm/trigger via CR0[2:0])
--
-- 5. HVS Debugging:
--
--    OutputC encodes FSM state as analog voltage for oscilloscope debugging.
--
--    Pre-PROG (BOOT/BIOS/LOADER): 197 units/state (~30mV steps)
--    - BOOT_P0:     0.000V
--    - BOOT_P1:     0.030V
--    - BIOS states: 0.24V - 0.33V
--    - LOAD states: 0.48V - 0.60V
--
--    PROG (DPD): 3277 units/state (~500mV steps)
--    - DPD_IDLE:     0.5V
--    - DPD_ARMED:    1.0V
--    - DPD_FIRING:   1.5V
--    - DPD_COOLDOWN: 2.0V
--
--    Transition BOOT_P1 → DPD_IDLE: 0.03V → 0.5V (visible on scope)
--
--------------------------------------------------------------------------------
```

---

### Phase 3: Update Build System

**File**: `Makefile`

**Changes**:

```makefile
# Remove old separate builds, use unified CustomWrapper
VHDL_FILES := \
    $(RTL_DIR)/forge_common_pkg.vhd \
    $(RTL_DIR)/CustomWrapper_test_stub.vhd \
    $(RTL_DIR)/boot/BootWrapper_test_stub.vhd \   # Keep for now (B0_BOOT_TOP still uses it)
    $(RTL_DIR)/moku_voltage_threshold_trigger_core.vhd \
    $(RTL_DIR)/forge_hierarchical_encoder.vhd \
    $(RTL_DIR)/DPD_main.vhd \
    $(RTL_DIR)/DPD_shim.vhd \
    $(RTL_DIR)/boot/loader_crc16.vhd \
    $(RTL_DIR)/boot/L2_BUFF_LOADER.vhd \
    $(RTL_DIR)/boot/B1_BOOT_BIOS.vhd \
    $(RTL_DIR)/boot/B0_BOOT_TOP.vhd \       # Compile BEFORE DPD.vhd
    $(RTL_DIR)/DPD.vhd                       # Top-level wrapper
```

**Note**: We keep `BootWrapper_test_stub.vhd` because `B0_BOOT_TOP.vhd` still declares its architecture using `BootWrapper` entity. The new `DPD.vhd` instantiates it as a component.

---

### Phase 4: Testing Strategy

1. **GHDL Compilation Test**
   ```bash
   make clean && make compile
   ```
   Should succeed with no errors.

2. **CocoTB Simulation** (existing tests should still work)
   ```bash
   cd tests/sim/boot_fsm && python run.py
   cd tests/sim/dpd && python run.py
   ```
   BOOT tests use `BootWrapper`, DPD tests use `CustomWrapper` (backward compat).

3. **Hardware Validation**
   - Build bitstream with MCC
   - Test RUNP transition (BOOT_P1 → PROG_ACTIVE)
   - Observe HVS voltage jump (0.03V → 0.5V)

---

## Alternative: Component-Based Instantiation

If GHDL doesn't like instantiating `BootWrapper` inside `CustomWrapper`, we can use explicit component declaration:

```vhdl
architecture bpd_forge of CustomWrapper is
    component BootWrapper is
        port (
            Clk : in std_logic;
            Reset : in std_logic;
            -- ... (full port list)
        );
    end component;
begin
    BOOT_DISPATCHER: BootWrapper
        port map ( ... );
end architecture;
```

This avoids relying on VHDL-2008 direct entity instantiation.

---

## Open Questions

1. **BootWrapper entity - keep or rename?**
   - Option A: Keep `BootWrapper` entity, instantiate as component in `CustomWrapper`
   - Option B: Merge B0_BOOT_TOP architecture directly into CustomWrapper (no separate entity)

   **Recommendation**: Option A (component instantiation) for modularity.

2. **Test stubs - consolidate?**
   - Currently: `CustomWrapper_test_stub.vhd` + `BootWrapper_test_stub.vhd`
   - After integration: Only `CustomWrapper_test_stub.vhd` needed for vendor builds
   - Keep `BootWrapper_test_stub.vhd` for isolated BOOT testing?

   **Recommendation**: Keep both for now, remove `BootWrapper_test_stub.vhd` later.

3. **Validation mode constants**
   - `B0_BOOT_TOP.vhd` has hardcoded `LOADER_VALIDATION_MODE := true`
   - Should this be a generic parameter for vendor builds?

   **Recommendation**: Convert to generic in Phase 5 (post-integration cleanup).

---

## Migration Path

### For Developers

**Old DPD-only workflow**:
```python
dpd = CloudCompile('192.168.1.100', bitstream='DPD-bits.tar')
dpd.set_control(0, 0xE0000000)  # Enable RUN
dpd.set_control(2, threshold)   # Configure
```

**New unified workflow** (backward compatible):
```python
dpd = CloudCompile('192.168.1.100', bitstream='DPD-bits.tar')
dpd.set_control(0, 0xE0000000)  # RUN → BOOT_P1
dpd.set_control(0, 0xF0000000)  # RUNP → PROG_ACTIVE (DPD mode)
dpd.set_control(2, threshold)   # Configure (works same as before)
```

**Expert workflow** (new capabilities):
```python
# Load buffers, run diagnostics, then launch app
dpd.set_control(0, 0xE0000000)  # RUN
dpd.set_control(0, 0xE4000000)  # RUNL (load buffers)
# ... (LOADER protocol)
dpd.set_control(0, 0xE1000000)  # RET
dpd.set_control(0, 0xE8000000)  # RUNB (BIOS diagnostics)
dpd.set_control(0, 0xE1000000)  # RET
dpd.set_control(0, 0xF0000000)  # RUNP (launch DPD)
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| GHDL component instantiation issues | Use explicit component declaration (VHDL-93 compatible) |
| Vivado optimization removes unused paths | Add `DONT_TOUCH` attributes if needed |
| BOOT overhead increases resource usage | Profile with Vivado synthesis, optimize if > 50% |
| HVS voltage discontinuity confuses users | Document transition clearly, add Python helper |
| Regression in existing DPD tests | Run full P1/P2 test suite before release |

---

## Success Criteria

1. ✅ `make compile` succeeds with no errors
2. ✅ GHDL elaboration succeeds for `CustomWrapper`
3. ✅ Existing CocoTB tests pass (dpd and boot_fsm)
4. ✅ Vivado synthesis completes with no errors
5. ✅ Resource usage < 50% of xc7z020 capacity
6. ✅ Hardware validation: RUNP transition visible on oscilloscope
7. ✅ DPD functionality unchanged in PROG_ACTIVE mode

---

## Next Steps

1. Rename `B0_BOOT_TOP.vhd` architecture
2. Rewrite `DPD.vhd` with component instantiation
3. Test GHDL compilation
4. Run CocoTB regression tests
5. Prepare for Vivado synthesis

---

## References

- [BOOT-FSM-spec.md](../docs/BOOT-FSM-spec.md) - Authoritative BOOT FSM specification
- [api-v4.md](../docs/api-v4.md) - DPD register map (PROG mode)
- [HANDOFF-Full-Synthesis-Ready.md](HANDOFF-Full-Synthesis-Ready.md) - Pre-integration state
- [SYNTHESIS-Planning-QA.md](SYNTHESIS-Planning-QA.md) - User requirements

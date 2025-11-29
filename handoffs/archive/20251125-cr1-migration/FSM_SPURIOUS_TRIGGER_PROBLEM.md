# FSM Spurious Trigger Problem - Detailed Analysis

**Date:** 2025-11-25
**Status:** 🔴 **ACTIVE BUG** - FSM transitions to FIRING incorrectly
**Context:** Continuation of HANDOFF_FSM_DEBUG_CONTINUATION.md

---

## Executive Summary

The DPD FSM **spuriously transitions from INITIALIZING → FIRING** (skipping IDLE and ARMED states) at cycle 1 after register setup. This occurs even though:
- ✅ **All trigger path signals are correct** (`combined_trigger = '0'`, `ext_trigger_in = '0'`)
- ✅ **Trigger enable gates are working** (sw_trigger_enable and hw_trigger_enable both '0')
- ✅ **Synchronization added** (registered `combined_trigger_reg` to prevent glitches)
- ❌ **FSM STILL goes to FIRING state** (OutputC = 9896 instead of expected 6554 for ARMED)

---

## What We Accomplished Today ✅

### 1. Clean CR1 Interface Redesign

**Old CR1 Layout (BROKEN):**
```
CR1[0] - arm_enable
CR1[1] - sw_trigger          ← NO ENABLE GATE! (unsafe)
CR1[2] - auto_rearm_enable
CR1[3] - fault_clear
CR1[4] - hw_trigger_enable
```

**New CR1 Layout (CLEAN):**
```
CR1[0] - arm_enable
CR1[1] - auto_rearm_enable
CR1[2] - fault_clear
CR1[3] - sw_trigger_enable   ← NEW: Software trigger enable gate (default: 0)
CR1[4] - hw_trigger_enable   ← Hardware trigger enable gate (default: 0)
CR1[5] - sw_trigger          ← Trigger signal (gated by CR1[3])
```

**Benefits:**
- Both trigger paths now have explicit enable gates
- 0 = safe default (no triggers can fire until explicitly enabled)
- Logical grouping: lifecycle bits (0-2), enable gates (3-4), trigger signal (5)

### 2. Created Shared Constants File

Created `py_tools/dpd_constants.py` as **single source of truth** for:
- CR1 bit positions
- FSM state values
- HVS encoding constants
- Platform constants (clock frequency, ADC/DAC ranges)
- Helper functions (`cr1_build()`, `cr1_extract()`)

Both simulation tests and hardware tests now import from this file.

### 3. Implemented Trigger Path Safety Features

**File: `rtl/DPD_shim.vhd`**

**A. Software Trigger Enable Gate:**
```vhdl
-- Line 311
combined_trigger <= '1' when (hw_trigger_out = '1' or
                              (sw_trigger_edge = '1' and app_reg_sw_trigger_enable = '1'))
                    else '0';
```

**B. Trigger Synchronizer (added today):**
```vhdl
-- Lines 256-262
-- Register combined_trigger to prevent combinational glitches from reaching FSM
if combined_trigger = '0' or combined_trigger = '1' then
    combined_trigger_reg <= combined_trigger;
else
    combined_trigger_reg <= '0';  -- Default to '0' if metavalue detected
end if;
```

**C. FSM Input (synchronized):**
```vhdl
-- Line 369
ext_trigger_in => combined_trigger_reg,  -- Registered trigger (prevents glitches)
```

### 4. Added FSM Metavalue Guards

**File: `rtl/DPD_main.vhd` (line 292)**
```vhdl
elsif ext_trigger_in = '1' and (ext_trigger_in /= 'U' and ext_trigger_in /= 'X') then
    -- External trigger received (with metavalue guard)
    next_state <= STATE_FIRING;
end if;
```

### 5. Updated All Test Files

- Updated `dpd_wrapper_constants.py` to import from shared constants
- Updated `dpd_helpers.py` to use new CR1 bit positions
- Updated `DPDConfig` to use CR1 constants and include new enable fields
- Updated `DPD-RTL.yaml` (authoritative spec) with new CR1 layout

---

## The Remaining Bug ❌

### Test Failure

**Test:** `tests/sim/dpd_wrapper_tests/P1_dpd_wrapper_basic.py::test_forge_control`

**Expected Behavior:**
```
Cycle 0: OutputC = 0 (INITIALIZING)
  ↓ (timing registers valid)
Cycle 1: OutputC = 3277 (IDLE)
  ↓ (arm_enable=1)
Cycle 2: OutputC = 6554 (ARMED) ← Should stay here!
```

**Actual Behavior:**
```
Cycle 0: OutputC = 0 (INITIALIZING)
Cycle 1: OutputC = 9896 (FIRING) ← SPURIOUS TRIGGER!
```

**Error:**
```
AssertionError: Timeout waiting for OutputC=6554±200, stuck at 9896 after 100μs
```

### Debug Test Evidence

**Test:** `tests/sim/dpd_wrapper_tests/P1_dpd_trigger_debug.py`

**Signal Values at Cycle 1 (when spurious trigger occurs):**
```
hw_trigger_out                  = 0 ✅
sw_trigger_edge                 = U → 0 (resolves at cycle 2)
combined_trigger                = 0 ✅
combined_trigger_reg            = 0 ✅ (after synchronizer added)
hw_trigger_enable_gated         = 0 ✅
app_reg_hw_trigger_enable       = 0 ✅
app_reg_sw_trigger_enable       = 0 ✅
app_reg_sw_trigger              = 0 ✅
ext_trigger_in (to FSM)         = 0 ✅
OutputC (FSM state)             = 9896 ❌ (FIRING!)
```

**Observation:** ALL trigger path signals are correct, yet FSM transitions to FIRING!

---

## Hypotheses

### Hypothesis 1: Combinational Cascade (MOST LIKELY)
The FSM's next-state logic is **purely combinational**, allowing multiple state transitions in a single evaluation:

```
INITIALIZING → IDLE → ARMED → FIRING
   (all in the same combinational logic evaluation)
```

**Sequence:**
1. Timing registers become valid → `next_state = IDLE`
2. `arm_enable = '1'` → `next_state = ARMED`
3. `ext_trigger_in` has metavalue or glitch → `next_state = FIRING`

**Evidence:**
- FSM transitions happen "instantly" at cycle 1
- No intermediate states observed (never see IDLE or ARMED)
- Combinational logic can cascade through multiple case statements

**File:** `rtl/DPD_main.vhd` lines 267-296

### Hypothesis 2: ext_trigger_in Metavalue Interpretation
Even with synchronizer and guards, VHDL might be evaluating:
```vhdl
if ext_trigger_in = '1' then
```
as **TRUE** when `ext_trigger_in = 'U'` (uninitialized).

Standard logic says `'U' = '1'` should be FALSE, but timing/delta cycles might cause unexpected behavior.

### Hypothesis 3: Global Enable Timing Issue
The `global_enable` signal might not be stable when FSM evaluates state transitions, allowing FSM to advance before it should be gated.

**File:** `rtl/DPD_shim.vhd` line 193

### Hypothesis 4: State Register Initialization
The FSM's `state` register might not be properly initialized to INITIALIZING, causing undefined behavior.

**File:** `rtl/DPD_main.vhd` line 246

---

## Files Modified (This Session)

### VHDL
- ✅ `rtl/DPD_shim.vhd` - CR1 remapping, sw_trigger_enable gate, synchronizer
- ✅ `rtl/DPD_main.vhd` - Metavalue guards in FSM
- ✅ `rtl/DPD-RTL.yaml` - Updated CR1 specification

### Python
- ✅ `py_tools/dpd_constants.py` - **NEW FILE** (shared constants)
- ✅ `py_tools/dpd_config.py` - Import constants, add enable fields
- ✅ `tests/sim/dpd_wrapper_tests/dpd_wrapper_constants.py` - Import shared constants
- ✅ `tests/sim/dpd_wrapper_tests/dpd_helpers.py` - Use CR1 constants, add enable gates

---

## Next Steps for Investigation

### 1. Verify Combinational Cascade Hypothesis ⭐ **HIGHEST PRIORITY**

**Approach:** Add intermediate state latching to prevent cascade.

**Option A:** Add "initialization complete" flag
```vhdl
signal init_complete : std_logic := '0';

-- In FSM_STATE_REG process:
if state = STATE_INITIALIZING and next_state = STATE_IDLE then
    init_complete <= '1';
end if;

-- In next-state logic:
when STATE_INITIALIZING =>
    if (timing_valid and init_complete = '0') then
        next_state <= STATE_IDLE;
    end if;

when STATE_IDLE =>
    if init_complete = '1' and arm_enable = '1' then
        next_state <= STATE_ARMED;
    end if;
```

**Option B:** Add cycle delay after INITIALIZING
```vhdl
signal post_init_cycles : unsigned(3 downto 0) := (others => '0');

when STATE_INITIALIZING =>
    if timing_valid and post_init_cycles >= 2 then
        next_state <= STATE_IDLE;
    end if;
```

### 2. Add Comprehensive FSM State Logging

Create enhanced debug test that captures:
- `state` (current FSM state register)
- `next_state` (combinational next-state logic output)
- All FSM inputs (`arm_enable`, `ext_trigger_in`, `timeout_occurred`, etc.)
- Transition timing (which cycle each transition occurs)

**File to modify:** `tests/sim/dpd_wrapper_tests/P1_dpd_trigger_debug.py`

### 3. Use CocoTB Test Agent to Generate New Test

The user suggested using the CocoTB test generation agent to create a focused test for this specific bug scenario.

**Agent location:** `.claude/agents/cocotb-test-gen.yaml` (if exists)

### 4. Direct Signal Probing

Add VHDL assertions or modify CustomWrapper to expose:
- `state` register value
- `next_state` combinational value
- Timing of state transitions

**File:** `rtl/DPD_main.vhd`

### 5. Waveform Analysis

Enable waveform generation and analyze:
```bash
cd tests/sim
COCOTB_ENABLE_WAVE=1 uv run python run.py
gtkwave dump.vcd
```

Look for:
- Exact timing of state transitions
- Value of `ext_trigger_in` at each delta cycle
- Whether multiple transitions occur in one clock cycle

---

## Test Commands

```bash
cd /Users/johnycsh/DPD/DPD-001

# Compile VHDL
make compile

# Run basic tests
cd tests/sim && uv run python run.py

# Run debug test
TEST_MODULE=dpd_wrapper_tests.P1_dpd_trigger_debug uv run python run.py

# Run with full verbosity (no filtering)
GHDL_FILTER=none COCOTB_VERBOSITY=DEBUG uv run python run.py

# Enable waveforms
COCOTB_ENABLE_WAVE=1 uv run python run.py
```

---

## Key Files Reference

### VHDL
- `rtl/DPD_main.vhd` - FSM logic (lines 242-296: state register + next-state logic)
- `rtl/DPD_shim.vhd` - Trigger path (lines 150-157: signals, 296-311: logic, 363-385: FSM instantiation)
- `rtl/DPD.vhd` - Top-level
- `rtl/DPD-RTL.yaml` - Authoritative register specification

### Test Infrastructure
- `py_tools/dpd_constants.py` - **Shared constants (single source of truth)**
- `tests/sim/dpd_wrapper_tests/dpd_wrapper_constants.py` - Test constants (imports from dpd_constants)
- `tests/sim/dpd_wrapper_tests/dpd_helpers.py` - Test helper functions
- `tests/sim/dpd_wrapper_tests/P1_dpd_wrapper_basic.py` - Failing test
- `tests/sim/dpd_wrapper_tests/P1_dpd_trigger_debug.py` - Debug test

### Documentation
- `HANDOFF_FSM_DEBUG_CONTINUATION.md` - Previous debugging session
- `ROOT_CAUSE_ANALYSIS.md` - Initial metavalue analysis
- `DEBUG_ANALYSIS_SUMMARY.md` - Debug test results

---

## What Works ✅

1. **Trigger path is clean** - All signals correctly gated and synchronized
2. **VHDL compiles** - No syntax errors
3. **Constants infrastructure** - Single source of truth established
4. **Test infrastructure** - Debug tests capture detailed signal state
5. **CR1 interface** - Clean, safe-by-default design

## What's Broken ❌

1. **FSM state machine** - Spuriously transitions to FIRING
2. **Root cause unknown** - Despite correct inputs, FSM misbehaves
3. **Combinational cascade suspected** - Multiple state transitions in one evaluation

---

## Success Criteria

✅ VHDL compiles without errors
✅ Trigger path signals are correct (`combined_trigger = '0'`)
❌ **FSM stays in ARMED state** (Expected: OutputC = 6554)
❌ **Test passes:** `test_forge_control` reaches ARMED state

---

## Claude's Recommendations

1. **Start with Hypothesis 1** (combinational cascade) - highest likelihood
2. **Add state transition delay** after INITIALIZING to break cascade
3. **Use CocoTB test agent** to generate focused test for this scenario
4. **Enable waveforms** to visualize exact timing of transitions
5. **Consider architectural change** if cascade is confirmed - FSM may need pipelining

---

**Ready for fresh context with better debugging tools!** 🚀

All infrastructure work (constants, CR1 reorganization, enable gates) is complete and working. The remaining issue is isolated to the FSM state machine logic in `DPD_main.vhd`.

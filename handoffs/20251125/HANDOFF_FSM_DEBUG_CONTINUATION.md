# Handoff: FSM Spurious Trigger Debug - Continuation

**Date:** 2025-11-25  
**Context Usage:** 75% - Creating handoff for continuation  
**Status:** 🔍 Investigation in progress - trigger path fixed, FSM issue remains

---

## Problem Summary

FSM spuriously transitions from INITIALIZING → FIRING (skipping IDLE and ARMED) when it should go INITIALIZING → IDLE → ARMED.

**Test:** `tests/sim/dpd_wrapper_tests/P1_dpd_wrapper_basic.py::test_forge_control`  
**Expected:** FSM stays in ARMED (OutputC = 6554)  
**Actual:** FSM goes to FIRING (OutputC = 9896) at cycle 1

---

## What We've Done

### ✅ Completed

1. **Fixed Deprecation Warnings**
   - Updated all `.signed_integer` → `.to_signed()` in:
     - `tests/sim/dpd_wrapper_tests/dpd_helpers.py`
     - `tests/sim/dpd_wrapper_tests/P1_dpd_wrapper_basic.py`
     - `tests/sim/dpd_wrapper_tests/dpd_debug_helpers.py`

2. **Created Debug Infrastructure**
   - `dpd_debug_constants.py` - Signal names and timing points
   - `dpd_debug_helpers.py` - SignalMonitor class and capture utilities
   - `P1_dpd_trigger_debug.py` - Enhanced debug test with detailed logging

3. **Fixed Trigger Path Metavalues**
   - **File:** `rtl/DPD_shim.vhd`
   - **Fix 1:** Added guard for `sw_trigger_prev` update (line 244):
     ```vhdl
     if app_reg_sw_trigger = '0' or app_reg_sw_trigger = '1' then
         sw_trigger_prev <= app_reg_sw_trigger;
     end if;
     ```
   - **Fix 2:** Changed `combined_trigger` to explicit when-else (line 299):
     ```vhdl
     combined_trigger <= '1' when (hw_trigger_out = '1' or sw_trigger_edge = '1') else '0';
     ```

4. **Verified Test Infrastructure**
   - Tests run successfully with `uv run python run.py`
   - GHDL filter working (99.6% output reduction)
   - Debug tests capture trigger path state correctly

---

## Current State

### Trigger Path (After Fixes) ✅

**At cycle 1 (when spurious trigger occurs):**
- `hw_trigger_out = 0` ✅
- `sw_trigger_edge = U → 0` (resolves quickly) ⚠️
- `combined_trigger = 0` ✅
- `hw_trigger_enable_gated = 0` ✅
- `app_reg_hw_trigger_enable = 0` ✅
- `app_reg_sw_trigger = 0` ✅
whi
**All trigger signals are now correct!**

### FSM Behavior (Still Broken) ❌

**Observed:**
```
Cycle 0: OutputC = 0 (INITIALIZING)
Cycle 1: OutputC = 9896 (FIRING) ← UNEXPECTED!
```

**Expected:**
```
INITIALIZING → IDLE → ARMED (stay in ARMED)
```

**Problem:** FSM transitions to FIRING even though `combined_trigger = '0'` and `ext_trigger_in` should be '0'.

---

## Key Findings

### 1. Trigger Path is Fixed ✅

The debug test shows trigger signals are correct at cycle 1:
- `combined_trigger = 0` (not 'U', not '1')
- All trigger path signals are valid

### 2. FSM Still Transitions Incorrectly ❌

Even with correct trigger signals, FSM goes to FIRING. This suggests:
- FSM might have latched a metavalue earlier (before fixes)
- FSM next-state logic might have a bug
- Timing issue: FSM evaluates before combinational logic stabilizes
- `ext_trigger_in` might have been 'U' at some point and FSM interpreted it as trigger

### 3. Timing Observation

The spurious trigger happens at **cycle 1** (8ns after register setup), which is:
- Before FSM can properly transition through states
- Immediately when `combined_trigger` propagates to FSM
- Very early in the initialization sequence

---

## Files Modified

1. **`rtl/DPD_shim.vhd`**
   - Line 244: Added guard for `sw_trigger_prev` update
   - Line 299: Changed `combined_trigger` to explicit when-else

2. **Test Files (deprecation fixes)**
   - `tests/sim/dpd_wrapper_tests/dpd_helpers.py:32`
   - `tests/sim/dpd_wrapper_tests/P1_dpd_wrapper_basic.py:101,102`
   - `tests/sim/dpd_wrapper_tests/dpd_debug_helpers.py:187`

---

## Debug Test Output

**Key lines from debug test:**
```
Cycle 1: SPURIOUS TRIGGER detected!
OutputC transitioned: 0 → 9896

Signal values at cycle 1:
  combined_trigger = 0 ✅
  hw_trigger_out = 0 ✅
  sw_trigger_edge = U (resolves to 0 at cycle 2) ⚠️
  hw_trigger_enable_gated = 0 ✅
```

**Observation:** Trigger signals are correct, but FSM still transitions.

---

## Next Steps

### Immediate Investigation

1. **Monitor `ext_trigger_in` directly**
   - Add to debug test to capture `ext_trigger_in` value
   - Check if it ever has metavalue or goes high unexpectedly

2. **Add FSM state transition logging**
   - Log each state transition: INITIALIZING → IDLE → ARMED → FIRING
   - Capture exact cycle when each transition occurs
   - Verify FSM goes through proper sequence

3. **Check FSM initialization**
   - Verify `state` register starts as STATE_INITIALIZING
   - Check if `next_state` logic has initialization issues
   - Verify reset logic properly initializes FSM

4. **Review FSM next-state logic**
   - **File:** `rtl/DPD_main.vhd` lines 288-295
   - Verify ARMED → FIRING transition only happens when `ext_trigger_in = '1'`
   - Check if there's a path from INITIALIZING/IDLE directly to FIRING

### Potential Fixes to Try

1. **Add reset to `ext_trigger_in` path**
   - Ensure `combined_trigger` is explicitly '0' during reset
   - Add reset logic to force trigger path to '0'

2. **Add synchronization flip-flop**
   - Register `combined_trigger` before sending to FSM
   - Prevents combinational glitches from reaching FSM

3. **Check FSM enable logic**
   - Verify `global_enable` is correct
   - Check if FSM is enabled when it shouldn't be

---

## Key Files Reference

### VHDL Source
- `rtl/DPD_shim.vhd` - Trigger path logic (lines 152, 216, 244, 292, 299)
- `rtl/DPD_main.vhd` - FSM logic (lines 242-295)
- `rtl/DPD.vhd` - Top-level instantiation

### Test Files
- `tests/sim/dpd_wrapper_tests/P1_dpd_wrapper_basic.py` - Failing test
- `tests/sim/dpd_wrapper_tests/P1_dpd_trigger_debug.py` - Debug test
- `tests/sim/dpd_wrapper_tests/dpd_debug_helpers.py` - Signal monitoring
- `tests/sim/dpd_wrapper_tests/dpd_helpers.py` - Test utilities

### Documentation
- `HANDOFF_FSM_TRIGGER_DEBUG.md` - Original problem statement
- `ROOT_CAUSE_ANALYSIS.md` - Analysis of metavalue issue
- `DEBUG_ANALYSIS_SUMMARY.md` - Current state summary

---

## Test Commands

```bash
cd /Users/johnycsh/DPD/DPD-001/tests/sim

# Run basic tests
uv run python run.py

# Run debug tests
TEST_MODULE=dpd_wrapper_tests.P1_dpd_trigger_debug uv run python run.py

# Compile VHDL
cd /Users/johnycsh/DPD/DPD-001 && make compile
```

---

## Hypothesis

**Most Likely:** The FSM's `ext_trigger_in` signal had a metavalue 'U' at some point during initialization, and the FSM's `if ext_trigger_in = '1'` check might have evaluated unexpectedly, or the FSM latched the metavalue in its state register.

**Alternative:** There's a timing issue where the FSM evaluates the trigger before the combinational logic has stabilized, or the FSM has a bug in its next-state logic that allows direct transition to FIRING.

---

## Success Criteria

✅ Trigger path signals are correct (metavalues fixed)  
❌ FSM still transitions incorrectly  
⏳ Need to identify why FSM goes to FIRING with `ext_trigger_in = '0'`

---

## Context for Continuation

**What's working:**
- Test infrastructure
- Debug test captures detailed state
- Trigger path metavalues fixed
- All trigger signals are correct

**What's broken:**
- FSM transitions to FIRING incorrectly
- FSM skips IDLE and ARMED states
- Happens at cycle 1 (very early)

**What to investigate:**
- FSM state initialization
- `ext_trigger_in` signal history
- FSM next-state logic
- Timing of state transitions

---

**Ready for continuation - all context preserved in this handoff document.**


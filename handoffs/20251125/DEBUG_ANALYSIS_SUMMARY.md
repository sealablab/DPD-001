# Debug Analysis Summary

**Date:** 2025-11-25  
**Status:** 🔍 Investigation in progress

---

## Findings

### ✅ Fixed Issues

1. **Deprecation Warnings** - Fixed all `.signed_integer` → `.to_signed()` conversions
2. **Trigger Signal Metavalues** - Partially fixed:
   - `combined_trigger` now correctly evaluates to '0' (not 'U')
   - `sw_trigger_edge` still has 'U' at cycle 1, but resolves to '0' at cycle 2

### ❌ Remaining Issue

**FSM still transitions to FIRING** even though:
- `combined_trigger = '0'` at cycle 1
- `hw_trigger_out = '0'`
- `sw_trigger_edge = '0'` (after cycle 1)
- All trigger path signals are correct

**Observation:** FSM goes from INITIALIZING (0) directly to FIRING (9896), skipping IDLE and ARMED states.

---

## Current State

### Trigger Path (After Fixes)

```
Cycle 1:
  hw_trigger_out = 0 ✅
  sw_trigger_edge = U → 0 (resolves quickly) ⚠️
  combined_trigger = 0 ✅
  ext_trigger_in = 0 ✅ (should be)
```

### FSM Behavior

```
Cycle 0: OutputC = 0 (INITIALIZING)
Cycle 1: OutputC = 9896 (FIRING) ← UNEXPECTED!
Expected: Should go INITIALIZING → IDLE → ARMED
```

---

## Hypothesis

The FSM might have **latched a metavalue** in `ext_trigger_in` during an earlier cycle (before our fixes), or there's a **timing issue** where the FSM evaluates the trigger before the combinational logic stabilizes.

**Possible causes:**
1. FSM state register has initialization issue
2. `ext_trigger_in` was 'U' at some point and FSM interpreted it as trigger
3. FSM next-state logic has a bug
4. Timing: FSM evaluates trigger before combinational logic updates

---

## Next Steps

1. **Check FSM state initialization** - Verify state register starts correctly
2. **Add more detailed logging** - Capture FSM state transitions step-by-step
3. **Check if `ext_trigger_in` ever had metavalue** - Monitor this signal specifically
4. **Review FSM next-state logic** - Verify ARMED→FIRING transition conditions

---

## Files Modified

1. ✅ `dpd_helpers.py` - Fixed `.signed_integer` → `.to_signed()`
2. ✅ `P1_dpd_wrapper_basic.py` - Fixed `.signed_integer` → `.to_signed()`
3. ✅ `dpd_debug_helpers.py` - Fixed `.signed_integer` → `.to_signed()`
4. ✅ `DPD_shim.vhd` - Added guard for `sw_trigger_prev` update
5. ✅ `DPD_shim.vhd` - Changed `combined_trigger` to explicit when-else

---

## Test Results

**Debug Test:** Still shows spurious trigger at cycle 1
**Basic Test:** Still fails on `test_forge_control`

**Trigger signals are now correct, but FSM behavior is still wrong.**


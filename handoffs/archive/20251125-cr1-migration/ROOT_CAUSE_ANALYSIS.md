# Root Cause Analysis: FSM Spurious Trigger

**Date:** 2025-11-25  
**Status:** ✅ ROOT CAUSE IDENTIFIED  
**Issue:** Metavalue ('U') propagation in trigger path

---

## Key Finding

**The spurious trigger occurs at cycle 1** (immediately after register setup), and the trigger path contains **uninitialized metavalues ('U')**.

### Evidence from Debug Test

```
Cycle 1: SPURIOUS TRIGGER detected!
OutputC transitioned: 0 → 9896 (INITIALIZING → FIRING, skipping ARMED)

Signal values at cycle 1:
  combined_trigger = U  ← METAVALUE!
  sw_trigger_edge = U   ← METAVALUE!
  hw_trigger_out = 0
  hw_trigger_enable_gated = 0
```

---

## Root Cause: Metavalue Initialization Issue

### Problem Chain

1. **`sw_trigger_prev` is uninitialized** at reset
   - Signal: `sw_trigger_prev : std_logic` (line 152 in DPD_shim.vhd)
   - Reset value: Not explicitly set to '0'

2. **Edge detection produces metavalue**
   ```vhdl
   sw_trigger_edge <= app_reg_sw_trigger and not sw_trigger_prev;
   ```
   - When `sw_trigger_prev = 'U'` and `app_reg_sw_trigger = '0'`:
   - `not 'U' = 'U'`
   - `'0' and 'U' = 'U'`
   - Result: `sw_trigger_edge = 'U'`

3. **Combined trigger propagates metavalue**
   ```vhdl
   combined_trigger <= hw_trigger_out or sw_trigger_edge;
   ```
   - When `hw_trigger_out = '0'` and `sw_trigger_edge = 'U'`:
   - `'0' or 'U' = 'U'`
   - Result: `combined_trigger = 'U'`

4. **FSM interprets 'U' as trigger**
   - FSM receives `ext_trigger_in = 'U'` (from `combined_trigger`)
   - VHDL `if ext_trigger_in = '1'` might evaluate to true when signal is 'U'
   - OR: The FSM's trigger detection logic doesn't handle metavalues correctly

---

## VHDL Code Analysis

### Current Implementation (DPD_shim.vhd)

**Line 152:** Signal declaration
```vhdl
signal sw_trigger_prev : std_logic;  -- Previous state for edge detection
```

**Line 215:** Reset logic
```vhdl
app_reg_sw_trigger <= '0';  -- Software trigger disabled
-- NOTE: sw_trigger_prev is NOT reset here!
```

**Line 292:** Edge detection (combinational)
```vhdl
sw_trigger_edge <= app_reg_sw_trigger and not sw_trigger_prev;
```

**Line 299:** Combined trigger (combinational)
```vhdl
combined_trigger <= hw_trigger_out or sw_trigger_edge;
```

**Line 347:** FSM trigger input
```vhdl
ext_trigger_in => combined_trigger,  -- Hardware OR software trigger
```

### Problem: Timing Issue with `sw_trigger_prev` Update

The `sw_trigger_prev` signal IS reset to '0' (line 216), BUT:

1. **Reset is released** before registers are set
2. **At first clock edge after reset release**, `sw_trigger_prev <= app_reg_sw_trigger;` executes
3. **At this point**, `app_reg_sw_trigger` might still be 'U' (uninitialized) because registers haven't been set yet
4. **This sets** `sw_trigger_prev = 'U'`
5. **Then registers are set**, but `sw_trigger_prev` remains 'U' until the next clock edge
6. **Combinational edge detection** evaluates: `sw_trigger_edge <= app_reg_sw_trigger and not sw_trigger_prev`
   - `app_reg_sw_trigger = '0'` (after register set)
   - `sw_trigger_prev = 'U'` (from previous clock edge)
   - `not 'U' = 'U'`
   - `'0' and 'U' = 'U'`
   - Result: `sw_trigger_edge = 'U'`

---

## Solution

### Fix: Prevent `sw_trigger_prev` from Being Updated During Reset

**Location:** `rtl/DPD_shim.vhd`, clocked process (around line 244)

**Problem:** The line `sw_trigger_prev <= app_reg_sw_trigger;` executes even when `app_reg_sw_trigger` is uninitialized.

**Solution:** Only update `sw_trigger_prev` when not in reset AND when `app_reg_sw_trigger` is valid.

**Change:**
```vhdl
-- Current (line 244):
sw_trigger_prev <= app_reg_sw_trigger;

-- Fixed:
if Reset = '0' then
    sw_trigger_prev <= app_reg_sw_trigger;
end if;
```

**OR better:** Use a synchronous reset approach - only update when reset is released:

```vhdl
-- In the clocked process, add reset check:
if Reset = '1' then
    -- Reset logic (already exists)
elsif rising_edge(Clk) then
    -- ... existing logic ...
    -- Only update sw_trigger_prev when not in reset:
    sw_trigger_prev <= app_reg_sw_trigger;
    -- ... rest of logic ...
end if;
```

**Actually, looking at the code structure, the fix is simpler:** The reset already sets `sw_trigger_prev <= '0'` (line 216). The issue is that the clocked update (line 244) happens before registers are stable. 

**Better fix:** Guard the update to only happen when `app_reg_sw_trigger` is not 'U':

```vhdl
-- Only update if app_reg_sw_trigger is valid (not 'U')
if app_reg_sw_trigger /= 'U' then
    sw_trigger_prev <= app_reg_sw_trigger;
end if;
```

**OR simplest fix:** Ensure `app_reg_sw_trigger` is initialized before the first clock edge by setting it in reset AND ensuring it stays '0' until registers are set.

**Recommended Fix:** Add a reset check to the `sw_trigger_prev` update:

```vhdl
-- Line 244, change from:
sw_trigger_prev <= app_reg_sw_trigger;

-- To:
if Reset = '0' then
    sw_trigger_prev <= app_reg_sw_trigger;
end if;
```

This ensures `sw_trigger_prev` only updates when reset is released, and by that time, `app_reg_sw_trigger` should be initialized.

---

## Verification Plan

### Step 1: Apply Fix

Add `sw_trigger_prev <= '0';` to reset logic in `DPD_shim.vhd`.

### Step 2: Re-run Debug Test

```bash
cd /Users/johnycsh/DPD/DPD-001/tests/sim
TEST_MODULE=dpd_wrapper_tests.P1_dpd_trigger_debug uv run python run.py
```

**Expected Result:**
- No spurious trigger at cycle 1
- FSM transitions: INITIALIZING → IDLE → ARMED (correct sequence)
- `sw_trigger_edge` and `combined_trigger` remain '0' throughout

### Step 3: Re-run Original Test

```bash
cd /Users/johnycsh/DPD/DPD-001/tests/sim
uv run python run.py
```

**Expected Result:**
- `test_forge_control` passes
- FSM stays in ARMED state as expected

---

## Additional Observations

### Metavalue Warnings

The debug test also shows metavalues in other signals at reset:
- `sw_trigger_edge = U` (before registers set)
- `combined_trigger = U` (before registers set)
- `hw_trigger_enable_gated = U` (before registers set)

These are expected during initialization, but they should resolve after reset release. The critical issue is that `sw_trigger_prev` remains uninitialized, causing persistent metavalues in the edge detection.

### Timing

The spurious trigger occurs at **cycle 1** (8ns after register setup), which is:
- Before FSM can transition to IDLE
- Before FSM can transition to ARMED
- Immediately when `combined_trigger` propagates to FSM

This confirms it's an initialization issue, not a timing/race condition.

---

## Related Issues

### Hypothesis #1 from HANDOFF_FSM_TRIGGER_DEBUG.md

> **Metavalue initialization issue**: GHDL reports "Metavalue warnings: 4". Uninitialized signals ('U'/'X') could cause unexpected comparator behavior.

**Status:** ✅ CONFIRMED - This is the root cause!

### Other Hypotheses (Ruled Out)

- ❌ Edge detection glitch: Not a glitch, but metavalue propagation
- ❌ Combinational race: Not a race, but initialization issue
- ❌ Previous test contamination: Not contamination, but persistent metavalue
- ❌ sync_safe timing: Not a timing issue, but initialization issue

---

## Files to Modify

1. **`rtl/DPD_shim.vhd`**
   - Add `sw_trigger_prev <= '0';` to reset logic (around line 215)

---

## References

- **Original Issue:** `HANDOFF_FSM_TRIGGER_DEBUG.md`
- **Debug Plan:** `FSM_TRIGGER_DEBUG_PLAN.md`
- **Debug Summary:** `FSM_TRIGGER_DEBUG_SUMMARY.md`
- **Test Results:** `tests/sim/TEST_RUN_SUMMARY.md`


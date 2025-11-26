# Session Handoff: Network Register Handshaking Protocol

**Date:** 2025-01-19
**Branch:** `20251118-DPD` (ready to branch to `feature/network-reg-handshake`)
**Tag:** `hw-tests-p1-working`
**Status:** Hardware P1 tests working with software workarounds
**Next Task:** Design and implement proper VHDL register handshaking protocol

---

## Executive Summary

Hardware testing revealed the fundamental issue described in `Register-gating-prompt.md`: **asynchronous network register updates create race conditions**. We've implemented software workarounds (time delays) to make tests pass, but now need to implement the **proper VHDL-based register handshaking protocol** in the shim layer.

---

## Problem Statement

### Root Cause
Network register updates via `mcc.set_control()` are **completely asynchronous** with bitstream operation. When Python code writes multiple registers sequentially:

```python
mcc.set_control(4, trig_cycles)          # CR4: timing
mcc.set_control(5, intensity_cycles)     # CR5: timing
mcc.set_control(7, cooldown_cycles)      # CR7: timing
mcc.set_control(1, 0x00000001)           # CR1: arm_enable=1
```

The FSM might see `arm_enable=1` **before** timing registers have valid values, causing:
- FSM tries to arm with zero/undefined timing → stays IDLE or goes FAULT
- Non-deterministic test failures (sometimes pass, sometimes fail)

### Current Workaround (Temporary)
Added `time.sleep(0.2)` delays in `arm_probe()` to allow register propagation before setting `arm_enable=1`. **This works but is crude and production-hostile.**

### Proper Solution Needed
Implement register handshaking at the **VHDL shim layer** to:
1. ✅ Gate register visibility until FSM is in safe state
2. ✅ Latch registers atomically
3. ✅ Validate register values before use
4. ✅ Provide fault semantics for invalid configurations

---

## Context Files to Review

### 1. **Problem Definition**
- **File:** `/Users/johnycsh/workspace/SimpleSliderApp/jc_prompts/20251119/Register-gating-prompt.md`
- **Why:** Original problem statement and proposed approaches
- **Key Points:**
  - T0: When to make network registers visible to L2/L3
  - T1: Reset behavior and register latching
  - T2: Fault clearing as equivalent to reset
  - Proposed: RESET → INITIALIZING → IDLE sequence

### 2. **DPD VHDL Architecture**

#### **DPD_main.vhd** (Core FSM)
- **File:** `/Users/johnycsh/workspace/SimpleSliderApp/20251118-DemoPD/VHDL/src/DPD_main.vhd`
- **Lines to focus on:**
  - **Line 120:** `signal state : std_logic_vector(5 downto 0);` - **NO INITIALIZATION** (this caused the STATE_4 bug)
  - **Lines 226-228:** Reset mechanism: `if Reset = '1' then state <= STATE_IDLE;`
  - **Lines 286-288:** Safety mechanism: `when others => next_state <= STATE_FAULT;`
  - **Lines 52-87:** State definitions and register port declarations
  - **Lines 120-153:** Internal signal declarations (where register latching would go)
  - **Lines 171-200:** FSM state machine logic (where INITIALIZING state would be added)

#### **DPD_shim.vhd** (Register Interface)
- **File:** `/Users/johnycsh/workspace/SimpleSliderApp/20251118-DemoPD/VHDL/src/DPD_shim.vhd`
- **Lines to focus on:**
  - **Line 136:** `signal global_enable : std_logic;` declaration
  - **Line 170:** `global_enable <= combine_forge_ready(forge_ready, user_enable, clk_enable, loader_done);`
  - **Line 292:** `Enable => global_enable,` passed to DPD_main
  - **Lines 38-72:** Port declarations (network registers come in here)
  - **Lines 204-264:** Register mapping to DPD_main ports
  - **Lines 268-308:** DPD_main instantiation
  - **Key insight:** This is where register gating/handshaking should be implemented

#### **forge_common_pkg.vhd** (Utility Functions)
- **File:** `/Users/johnycsh/workspace/SimpleSliderApp/20251118-DemoPD/VHDL/src/forge_common_pkg.vhd`
- **Lines to focus on:**
  - **Lines 56-79:** `combine_forge_ready()` function (controls global_enable)
  - **Lines 81-95:** `extract_forge_ready()` function
  - **Potential addition:** Could add register latching utilities here

### 3. **Hardware Test Context**

#### **Test Results (Pre-Handshaking)**
Shows non-deterministic ARM failures:
- **Run 1:** T4 PASS, T5 FAIL, T6 FAIL
- **Run 2:** T4 FAIL, T5 FAIL, T6 FAIL

#### **arm_probe() Workaround**
- **File:** `/Users/johnycsh/workspace/SimpleSliderApp/20251118-DemoPD/hardware_progressive_tests/hw_test_helpers.py`
- **Lines 179-218:** `arm_probe()` function with 200ms delay workaround
- **Line 213:** `time.sleep(0.2)` - the crude fix we want to eliminate

#### **Register Constants**
- **File:** `/Users/johnycsh/workspace/SimpleSliderApp/20251118-DemoPD/hardware_progressive_tests/hw_test_constants.py`
- **Lines 42-51:** FORGE control bit definitions
- **Lines 90-111:** Timing conversion functions

### 4. **Register Specification**
- **File:** `/Users/johnycsh/workspace/SimpleSliderApp/20251118-DemoPD/DPD-RTL.yaml`
- **Why:** Documents control register mapping (CR0-CR15)
- **Key registers:**
  - CR0[31:29]: FORGE control (forge_ready, user_enable, clk_enable)
  - CR1[3:0]: FSM control (fault_clear, auto_rearm_enable, sw_trigger, arm_enable)
  - CR2-CR3: Voltage controls
  - CR4-CR7: Timing controls (these need atomic latching)

---

## Proposed Approaches (from Register-gating-prompt.md)

### Option 1: Register Latching on Reset/Fault
- DPD_main latches all app_reg inputs during `Reset='1'` or `fault_clear` pulse
- **Pros:** Minimal state machine changes
- **Cons:** Only safe to update registers during reset/fault, limits flexibility

### Option 2: RESET → INITIALIZING → IDLE Sequence (RECOMMENDED)
- Add new INITIALIZING state between RESET and IDLE
- INITIALIZING state:
  - Latches all app_reg values into internal signals
  - Validates timing registers (non-zero, reasonable ranges)
  - If valid: transition to IDLE
  - If invalid: transition to FAULT
- **Pros:**
  - Clear semantics for when registers are safe to update
  - Built-in validation
  - Works with existing fault_clear recovery mechanism
  - Not timing-sensitive during startup
- **Cons:** Requires new FSM state and logic

### Option 3: Ready-for-Updates Handshake Signal
- DPD_main outputs `ready_for_updates` signal when in safe state (IDLE)
- DPD_shim gates register visibility based on `ready_for_updates`
- **Pros:** Allows updates during operation (not just initialization)
- **Cons:** More complex, requires bidirectional handshaking

---

## Design Constraints

### Must Preserve
1. **FORGE control scheme** (CR0[31:29] gating) - this works well
2. **Fault recovery mechanism** (fault_clear → FAULT → IDLE)
3. **Edge detection for control signals** (sw_trigger, fault_clear)
4. **Existing register mapping** (CR0-CR15 as documented)

### Must Fix
1. **Race condition:** FSM sees arm_enable=1 before timing registers are valid
2. **No initialization:** State signal powers up to random value (STATE_4 bug already documented)
3. **Asynchronous propagation:** No guarantee of register update ordering

### Must Not Break
1. **Hardware tests** (P1 tests should still pass after changes)
2. **CocoTB tests** (simulation tests in `cocotb_tests/`)
3. **Existing FSM semantics** (IDLE → ARMED → FIRING → COOLDOWN → IDLE)

---

## Implementation Strategy (Minimally Invasive)

### Phase 1: Add INITIALIZING State (DPD_main.vhd)
1. Add `STATE_INITIALIZING` constant (value = 5, since 0-4 are taken)
2. Modify reset logic to go to INITIALIZING instead of IDLE
3. Add internal signals for latched register values
4. INITIALIZING state logic:
   - Latch all app_reg inputs to internal signals
   - Validate timing registers > 0
   - Auto-transition to IDLE if valid, FAULT if invalid
5. Use latched signals throughout FSM instead of direct app_reg ports

### Phase 2: Initialize State Signal (DPD_main.vhd)
1. Change `signal state : std_logic_vector(5 downto 0);` to have initialization
2. Consider: `signal state : std_logic_vector(5 downto 0) := STATE_INITIALIZING;`
3. This prevents random power-up states (fixes STATE_4 bug permanently)

### Phase 3: Update Shim (DPD_shim.vhd)
1. May need to add initialization signal routing (minimal changes)
2. Ensure global_enable allows INITIALIZING → IDLE transition

### Phase 4: Test and Validate
1. Run CocoTB simulation tests
2. Run hardware P1 tests (remove time.sleep workarounds)
3. Verify non-deterministic failures are eliminated

---

## Git Workflow

### Current State
- **Branch:** `20251118-DPD`
- **Tag:** `hw-tests-p1-working`
- **Commits pushed:** Yes

### Next Steps
```bash
cd /Users/johnycsh/workspace/SimpleSliderApp/20251118-DemoPD

# Create feature branch from current state
git checkout -b feature/network-reg-handshake

# Make VHDL changes incrementally
# Commit after each logical change

# Test with CocoTB
cd cocotb_tests
make

# Test with hardware (after bitstream rebuild)
cd ../hardware_progressive_tests
uv run python3 run_hw_tests.py 192.168.73.1 --bitstream ../DPD-bits.tar

# When complete, merge back to 20251118-DPD
git checkout 20251118-DPD
git merge feature/network-reg-handshake
```

---

## Key Questions to Answer

### 1. State Value Assignment
- STATE_INITIALIZING should be value 5 (next available)?
- Or reorganize: INITIALIZING=0, IDLE=1, ARMED=2, FIRING=3, COOLDOWN=4, FAULT=5?
- **Consideration:** Changing state values affects HVS encoding on OutputC
- **Recommendation:** Keep existing values, add INITIALIZING=5 for minimal impact

### 2. Validation Logic
What validations should INITIALIZING perform?
- Timing registers > 0? (prevents zero-duration pulses)
- Timing registers < MAX_VALUE? (prevents overflow)
- Voltage registers within range? (±5V = ±32768 digital)
- **Recommendation:** Start minimal - just check timing > 0

### 3. When to Re-enter INITIALIZING?
- Only on power-up/reset?
- On fault_clear (FAULT → INITIALIZING → IDLE)?
- On disarm (IDLE → INITIALIZING when registers change)?
- **Recommendation:** Only on reset and fault_clear (minimal changes)

### 4. Latched vs. Direct Registers
Which registers should be latched in INITIALIZING?
- **Must latch:** CR4, CR5, CR7 (timing - race condition source)
- **Must latch:** CR2, CR3 (voltage - consistency with timing)
- **Don't latch:** CR0 (FORGE control - needs immediate effect)
- **Don't latch:** CR1[3:1] (sw_trigger, auto_rearm, fault_clear - edge detection)
- **Do latch:** CR1[0] (arm_enable - consistency with timing)

### 5. Backward Compatibility
How to ensure existing Python code works without changes?
- **Current:** `reset_fsm_to_idle()` clears CR1-CR15, waits for IDLE
- **After change:** Should still reach IDLE, just via INITIALIZING
- **Test impact:** May need to update voltage tolerance for new state (2.5V?)

---

## Success Criteria

### Functional Requirements
1. ✅ FSM powers up to INITIALIZING (not random state)
2. ✅ INITIALIZING latches timing/voltage registers atomically
3. ✅ INITIALIZING validates timing > 0 before transitioning to IDLE
4. ✅ INITIALIZING → FAULT on invalid configuration
5. ✅ fault_clear recovery: FAULT → INITIALIZING → IDLE
6. ✅ No time.sleep() workarounds needed in Python code

### Test Requirements
1. ✅ CocoTB tests pass (all P1, P2, P3 levels)
2. ✅ Hardware P1 tests pass consistently (no non-deterministic failures)
3. ✅ Hardware P1 tests pass with time.sleep(0.2) removed from arm_probe()
4. ✅ Test runtime not significantly increased (no more than 10% slower)

### Documentation Requirements
1. ✅ Update DPD-RTL.yaml with INITIALIZING state
2. ✅ Update hw_test_constants.py with STATE_INITIALIZING voltage
3. ✅ Update README.md in hardware_progressive_tests
4. ✅ Add comments in VHDL explaining register latching logic

---

## Files That Will Need Changes

### VHDL Changes (Primary Work)
1. **DPD_main.vhd** - Add INITIALIZING state, register latching
2. **DPD_shim.vhd** - Minor changes if needed for initialization
3. **forge_common_pkg.vhd** - Potentially add latching utilities

### Python Test Changes (Cleanup)
1. **hw_test_helpers.py** - Remove time.sleep(0.2) workaround
2. **hw_test_constants.py** - Add STATE_INITIALIZING voltage mapping
3. **P1_hw_basic.py** - May need to handle new state in tests

### Documentation Changes
1. **DPD-RTL.yaml** - Document INITIALIZING state
2. **hardware_progressive_tests/README.md** - Update state machine docs
3. **Register-gating-prompt.md** - Mark as RESOLVED when complete

---

## Debugging Tips

### If INITIALIZING → IDLE Doesn't Happen
- Check `global_enable` is 1 (FORGE control enabled)
- Check `ClkEn` is 1 (clock not gated)
- Check validation logic isn't too strict (timing > 0 should be easy)
- Use `hw_test_helpers.read_fsm_state()` to observe voltage (should see 2.5V?)

### If Tests Still Fail Non-Deterministically
- INITIALIZING state didn't fully solve the problem
- May need Option 3 (ready_for_updates handshake) for runtime updates
- Check if other registers (beyond timing) also need latching

### If CocoTB Tests Fail
- State voltage encoding changed (if you renumbered states)
- Update `dpd_wrapper_constants.py` to match new state values
- Check reset behavior in testbenches (may assume IDLE immediate)

---

## Quick Start Commands for New Session

```bash
# Navigate to project
cd /Users/johnycsh/workspace/SimpleSliderApp/20251118-DemoPD

# Create feature branch
git checkout -b feature/network-reg-handshake

# Review key files
cat jc_prompts/20251119/Register-gating-prompt.md
cat VHDL/src/DPD_main.vhd | grep -A 5 "signal state"
cat VHDL/src/DPD_shim.vhd | grep -A 3 "global_enable"

# After making changes, test with CocoTB
cd cocotb_tests
make

# Test with hardware (after bitstream rebuild)
cd ../hardware_progressive_tests
uv run python3 run_hw_tests.py 192.168.73.1 --bitstream ../DPD-bits.tar --verbose
```

---

## Session Context Restoration Prompt

```
I'm continuing work on implementing a register handshaking protocol for the Demo Probe Driver (DPD) VHDL design.

**Context:**
Hardware testing revealed that asynchronous network register updates create race conditions - the FSM sometimes sees arm_enable=1 before timing registers have valid values, causing non-deterministic test failures. We've implemented a software workaround (time.sleep delays), but now need the proper VHDL solution.

**Goal:**
Implement a RESET → INITIALIZING → IDLE state sequence in DPD_main.vhd where the INITIALIZING state atomically latches and validates all timing/voltage registers before transitioning to IDLE.

**Key Files:**
- Problem definition: Register-gating-prompt.md
- Session handoff: Network-Register-Handshake-Session-Handoff.md
- VHDL FSM: DPD_main.vhd
- VHDL Shim:DPD_shim.vhd
- Test workaround: hw_test_helpers.py (line 213)


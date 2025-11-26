# FSM Spurious Trigger Debug - Summary & Action Plan

## Quick Summary

**Problem:** FSM transitions ARMED → FIRING when it should stay in ARMED
**Root Cause:** Unknown - needs investigation via waveform capture and signal monitoring
**Solution Approach:** Use cocotb agents to create progressive debug test suite

---

## Git History Context

**Recent Changes:**
- Commit `9c0bc67`: Added CR1[4] `hw_trigger_enable` to gate hardware trigger
- Issue persists despite hardware trigger being disabled by default
- Test `test_forge_control` still failing

**Key Files Modified:**
- `rtl/DPD_shim.vhd`: Added `hw_trigger_enable_gated` logic
- `rtl/DPD-RTL.yaml`: Documented new CR1[4] bit
- `tests/sim/dpd_wrapper_tests/P1_dpd_wrapper_basic.py`: Updated test (still failing)

---

## Plan Overview

### Phase 1: Signal Accessibility Assessment ⚠️ CRITICAL

**Challenge:** Trigger signals (`combined_trigger`, `hw_trigger_out`, `sw_trigger_edge`) are internal to `DPD_shim.vhd` and not exposed via `CustomWrapper_test_stub.vhd`.

**Options:**

1. **Option A: Hierarchical Access (Recommended - Try First)**
   - Access via `dut.dpd_shim_inst.combined_trigger` (DPD_shim is instantiated as `DPD_SHIM_INST` in DPD.vhd)
   - Pros: No VHDL changes, direct access
   - Cons: May not work if CocoTB doesn't support hierarchical access
   - **Hierarchy:** `CustomWrapper` → `DPD_SHIM_INST` (DPD_shim) → trigger signals

2. **Option B: Add Debug Ports (If Option A fails)**
   - Modify `DPD.vhd` to expose debug signals as optional ports
   - Add debug ports to CustomWrapper_test_stub.vhd
   - Pros: Guaranteed access
   - Cons: Requires VHDL changes

3. **Option C: Infer from Outputs (Fallback)**
   - Monitor OutputC (FSM state) and Control registers
   - Infer trigger activity from state transitions
   - Pros: No changes needed
   - Cons: Less direct, may miss glitches

**Action:** Start with Option A (hierarchical via `dut.dpd_shim_inst.*`), fall back to Option C, use Option B if needed.

---

## Implementation Steps

### Step 1: Check Signal Hierarchy (5 min)

**Confirmed Hierarchy:**
- `CustomWrapper` (entity) → `DPD.vhd` (architecture `bpd_forge`)
- `DPD_SHIM_INST` (instance of `DPD_shim`) contains trigger signals
- Try hierarchical access: `dut.dpd_shim_inst.combined_trigger`

**Test hierarchical access:**
```python
# In test
try:
    combined_trigger = dut.dpd_shim_inst.combined_trigger
    hw_trigger_out = dut.dpd_shim_inst.hw_trigger_out
    sw_trigger_edge = dut.dpd_shim_inst.sw_trigger_edge
    print("✓ Hierarchical access works")
except AttributeError as e:
    print(f"✗ Hierarchical access failed: {e}")
    print("  Will use inference from OutputC instead")
```

### Step 2: Create Debug Infrastructure (30 min)

**Files to create:**
1. `tests/sim/dpd_wrapper_tests/dpd_debug_constants.py` - Signal names, timing points
2. `tests/sim/dpd_wrapper_tests/dpd_debug_helpers.py` - SignalMonitor class

**Key features:**
- Signal monitoring with cycle-accurate logging
- State capture at key timing points
- Transition detection and logging

### Step 3: Create P1 Debug Test (45 min)

**File:** `tests/sim/dpd_wrapper_tests/P1_dpd_trigger_debug.py`

**Test structure:**
```python
@cocotb.test()
async def test_trigger_path_monitoring(dut):
    """Monitor trigger path during failing test_forge_control scenario"""
    
    # Setup
    await setup_clock(dut)
    await reset_active_high(dut)
    
    # Start signal monitoring
    monitor = SignalMonitor(dut, TRIGGER_SIGNALS)
    await monitor.start_monitoring()
    
    # Reproduce failing scenario
    await mcc_set_regs(dut, {
        0: MCC_CR0_ALL_ENABLED,
        1: 0x00000001,  # arm_enable=1, hw_trigger_enable=0
    })
    
    # Wait for ARMED
    await wait_for_state(dut, HVS_DIGITAL_ARMED, timeout_us=100)
    
    # Capture state at ARMED
    await capture_trigger_path_state(dut, "At ARMED state")
    
    # Wait a bit and check if spurious trigger occurs
    await ClockCycles(dut.Clk, 100)
    
    # Check if FSM left ARMED (spurious trigger)
    output_c = read_output_c(dut)
    if output_c != HVS_DIGITAL_ARMED:
        # Spurious trigger detected - print monitor history
        print("\n⚠️ SPURIOUS TRIGGER DETECTED!")
        monitor.print_transitions("combined_trigger")
        monitor.print_transitions("hw_trigger_out")
        monitor.print_transitions("sw_trigger_edge")
    
    # Capture final state
    await capture_trigger_path_state(dut, "After monitoring period")
```

### Step 4: Enable Waveform Capture (10 min)

**Modify `tests/sim/run.py`:**
```python
# Add waves parameter
waves = os.environ.get("WAVES", "false").lower() == "true"

cocotb_run(
    ...
    waves=waves,  # Enable waveform capture
    ...
)
```

**Usage:**
```bash
cd tests/sim
WAVES=true uv run python run.py
```

### Step 5: Run Debug Test (5 min)

```bash
cd /Users/johnycsh/DPD/DPD-001/tests/sim
WAVES=true uv run python run.py dpd_wrapper_tests.P1_dpd_trigger_debug
```

**Expected outputs:**
- Waveform file: `waves.vcd` or `waves.fst`
- Signal monitor logs showing transitions
- Trigger path state captures

### Step 6: Analyze Results (30 min)

**Check waveform:**
1. Open `waves.vcd` in GTKWave
2. Add signals: `combined_trigger`, `hw_trigger_out`, `sw_trigger_edge`, `hw_trigger_enable_gated`, `state_reg`
3. Zoom to time around ARMED → FIRING transition
4. Look for:
   - Unexpected pulse on `combined_trigger`
   - Glitch on `hw_trigger_enable_gated`
   - Edge detection firing incorrectly
   - Metavalues ('U'/'X') propagating

**Check signal monitor logs:**
- Review transition logs for unexpected changes
- Identify exact cycle when spurious trigger occurs
- Correlate with register writes

### Step 7: Implement Fix (varies)

Based on findings:
- **Combinational glitch:** Add synchronization flip-flop
- **Metavalue:** Fix initialization sequence
- **Edge detection:** Fix edge detection logic
- **Timing:** Adjust timing or add delays

### Step 8: Verify Fix (10 min)

```bash
# Re-run debug test
WAVES=true uv run python run.py dpd_wrapper_tests.P1_dpd_trigger_debug

# Re-run original failing test
uv run python run.py dpd_wrapper_tests.P1_dpd_wrapper_basic::test_forge_control
```

---

## Using CocoTB Agents

### Agent: `cocotb-integration-test`

**Purpose:** Create progressive test structure following forge-vhdl standards

**Invocation:**
```markdown
I need to create a debug test suite for the FSM spurious trigger issue.

Please read:
- DPD-001/FSM_TRIGGER_DEBUG_PLAN.md (debug plan)
- DPD-001/tests/sim/dpd_wrapper_tests/P1_dpd_wrapper_basic.py (failing test)
- .claude/agents/cocotb-integration-test/agent.md (agent guide)

Create:
1. dpd_debug_constants.py with trigger signal names
2. dpd_debug_helpers.py with SignalMonitor class
3. P1_dpd_trigger_debug.py following P1 standards (<20 lines output)

Focus on monitoring trigger path signals during the failing test_forge_control scenario.
```

**Expected Output:**
- Progressive test structure (P1/P2/P3)
- Constants file with signal names
- Helper functions for signal monitoring
- Test following forge-vhdl patterns

---

## Signal Names Reference

**From VHDL (`DPD_shim.vhd`):**
- `combined_trigger` - Final trigger to FSM (line 299)
- `hw_trigger_out` - Hardware trigger output (line 144)
- `sw_trigger_edge` - Software trigger edge (line 153)
- `hw_trigger_enable_gated` - Gated hardware enable (line 147)
- `app_reg_hw_trigger_enable` - CR1[4] register value (line 110)
- `app_reg_sw_trigger` - CR1[1] register value (line 107)
- `ext_trigger_in` - Input to FSM (should match combined_trigger)
- `state_reg` - FSM state (in DPD_main.vhd)

**Accessible via CustomWrapper:**
- `Control0` through `Control15` - Register values
- `OutputC` - FSM state (HVS encoded)
- `InputA`, `InputB`, `InputC` - Input channels

**May need debug ports:**
- All trigger path signals (internal to DPD_shim)

---

## Success Criteria

✅ **Debug test created** - P1 test with signal monitoring
✅ **Waveform captured** - VCD/FST file generated
✅ **Root cause identified** - Exact signal and timing of spurious trigger
✅ **Fix implemented** - Code change addresses root cause
✅ **Original test passes** - `test_forge_control` no longer fails
✅ **No regressions** - All other tests still pass

---

## Timeline Estimate

- **Step 1-2:** 35 min (signal check + infrastructure)
- **Step 3:** 45 min (P1 debug test)
- **Step 4:** 10 min (waveform enable)
- **Step 5:** 5 min (run test)
- **Step 6:** 30 min (analysis)
- **Step 7:** 1-4 hours (fix implementation, varies)
- **Step 8:** 10 min (verification)

**Total:** ~2-6 hours depending on root cause complexity

---

## Next Immediate Action

**Start with Step 1:** Check signal hierarchy to determine if we can access trigger signals directly, or if we need to add debug ports.

```bash
cd /Users/johnycsh/DPD/DPD-001
grep -A 20 "entity\|component\|DPD_shim" rtl/CustomWrapper_test_stub.vhd
```

If CustomWrapper_test_stub doesn't instantiate DPD_shim, we'll need to add debug ports or use inference from OutputC.

---

## References

- **Debug Plan:** `FSM_TRIGGER_DEBUG_PLAN.md` (detailed plan)
- **Problem Statement:** `HANDOFF_FSM_TRIGGER_DEBUG.md` (original issue)
- **CocoTB Agent:** `.claude/agents/cocotb-integration-test/agent.md`
- **Failing Test:** `tests/sim/dpd_wrapper_tests/P1_dpd_wrapper_basic.py::test_forge_control`
- **VHDL Trigger Logic:** `rtl/DPD_shim.vhd` (lines 287-327)


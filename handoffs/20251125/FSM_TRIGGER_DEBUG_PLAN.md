# FSM Spurious Trigger Debug Plan - Using CocoTB Agents

## Problem Summary

The DPD FSM spuriously transitions from ARMED → FIRING when it should stay in ARMED. This happens even though:
- Hardware trigger is gated by CR1[4] (hw_trigger_enable), which defaults to '0'
- Software trigger (CR1[1]) is NOT being set

**Failing Test:** `test_forge_control` in `P1_dpd_wrapper_basic.py`
**Expected:** FSM stays in ARMED (OutputC ≈ 6554 digital units = 1.0V)
**Actual:** FSM goes to FIRING (OutputC ≈ 9896 digital units ≈ 1.5V)

## Strategy: Progressive Debug Test Suite

Following the cocotb-integration-test agent patterns, we'll create a **dedicated debug test suite** that progressively narrows down the issue by:

1. **P1 Debug Test**: Signal monitoring and waveform capture
2. **P2 Debug Test**: Detailed trigger path analysis
3. **P3 Debug Test**: Comprehensive state machine trace

This approach allows us to:
- Capture waveforms for visual inspection
- Monitor all trigger-related signals in real-time
- Isolate the exact moment and cause of the spurious trigger
- Verify fixes incrementally

---

## Phase 1: Create Debug Test Infrastructure

### 1.1 Create Debug Test Constants File

**File:** `tests/sim/dpd_wrapper_tests/dpd_debug_constants.py`

```python
"""
Debug Test Constants for FSM Spurious Trigger Investigation

Focuses on trigger path signals and timing.
"""

# Signal names to monitor (must match VHDL entity ports or internal signals exposed via wrapper)
TRIGGER_SIGNALS = [
    "combined_trigger",      # Final trigger to FSM
    "hw_trigger_out",        # Hardware trigger output
    "sw_trigger_edge",       # Software trigger edge
    "hw_trigger_enable_gated",  # Gated hardware enable
    "app_reg_hw_trigger_enable",  # CR1[4] register value
    "app_reg_sw_trigger",    # CR1[1] register value
    "ext_trigger_in",        # Input to FSM (should match combined_trigger)
    "state_reg",             # FSM state register
]

# Key timing points to capture
TIMING_POINTS = {
    "RESET_ASSERTED": "Reset goes high",
    "RESET_RELEASED": "Reset goes low",
    "FORGE_ENABLED": "CR0[31:29] all set",
    "ARM_ENABLED": "CR1[0] arm_enable set",
    "IDLE_REACHED": "FSM reaches IDLE state",
    "ARMED_REACHED": "FSM reaches ARMED state",
    "SPURIOUS_TRIGGER": "Unexpected ARMED→FIRING transition",
}
```

### 1.2 Create Signal Monitor Helper

**File:** `tests/sim/dpd_wrapper_tests/dpd_debug_helpers.py`

```python
"""
Debug helpers for signal monitoring and waveform capture
"""

import cocotb
from cocotb.triggers import RisingEdge, ClockCycles
from typing import Dict, List, Optional

class SignalMonitor:
    """Monitor and log signal values over time"""
    
    def __init__(self, dut, signals: List[str], clk_signal="Clk"):
        self.dut = dut
        self.signals = signals
        self.clk = getattr(dut, clk_signal)
        self.history: Dict[str, List[tuple]] = {}  # {signal: [(cycle, value), ...]}
        self.current_cycle = 0
        
    async def start_monitoring(self):
        """Start background monitoring task"""
        cocotb.start_soon(self._monitor_loop())
    
    async def _monitor_loop(self):
        """Background task to sample signals every clock cycle"""
        while True:
            await RisingEdge(self.clk)
            self.current_cycle += 1
            
            for sig_name in self.signals:
                try:
                    sig = getattr(self.dut, sig_name, None)
                    if sig is not None:
                        value = int(sig.value) if hasattr(sig.value, '__int__') else str(sig.value)
                        if sig_name not in self.history:
                            self.history[sig_name] = []
                        self.history[sig_name].append((self.current_cycle, value))
                except (AttributeError, ValueError):
                    pass  # Signal not accessible
    
    def get_signal_at_cycle(self, signal: str, cycle: int) -> Optional[int]:
        """Get signal value at specific cycle"""
        if signal not in self.history:
            return None
        for c, v in self.history[signal]:
            if c == cycle:
                return v
        return None
    
    def print_transitions(self, signal: str, min_cycles: int = 0):
        """Print all transitions for a signal"""
        if signal not in self.history:
            print(f"  {signal}: Not accessible")
            return
        
        prev_value = None
        for cycle, value in self.history[signal]:
            if value != prev_value and cycle >= min_cycles:
                print(f"  Cycle {cycle}: {signal} = {prev_value} → {value}")
                prev_value = value

async def capture_trigger_path_state(dut, context: str = ""):
    """Capture current state of all trigger path signals"""
    signals_to_check = [
        ("hw_trigger_out", "hw_trigger_out"),
        ("sw_trigger_edge", "sw_trigger_edge"),
        ("combined_trigger", "combined_trigger"),
        ("hw_trigger_enable_gated", "hw_trigger_enable_gated"),
        ("app_reg_hw_trigger_enable", "app_reg_hw_trigger_enable"),
        ("app_reg_sw_trigger", "app_reg_sw_trigger"),
    ]
    
    print(f"\n{'='*70}")
    print(f"Trigger Path State: {context}")
    print(f"{'='*70}")
    
    for sig_name, description in signals_to_check:
        try:
            sig = getattr(dut, sig_name, None)
            if sig is not None:
                value = int(sig.value) if hasattr(sig.value, '__int__') else str(sig.value)
                print(f"  {description:30s} = {value}")
            else:
                print(f"  {description:30s} = <not accessible>")
        except Exception as e:
            print(f"  {description:30s} = <error: {e}>")
    
    # Also check FSM state via OutputC
    try:
        output_c = int(dut.OutputC.value.signed_integer)
        print(f"  {'OutputC (FSM state)':30s} = {output_c}")
    except:
        pass
    
    print(f"{'='*70}\n")
```

---

## Phase 2: Create P1 Debug Test (Signal Monitoring)

### 2.1 P1 Debug Test Structure

**File:** `tests/sim/dpd_wrapper_tests/P1_dpd_trigger_debug.py`

This test will:
1. Enable waveform capture (`waves=True` in cocotb_run)
2. Monitor all trigger signals during the failing sequence
3. Capture signal states at key timing points
4. Log transitions to identify when/why spurious trigger occurs

**Key Features:**
- Uses `SignalMonitor` to track all trigger signals
- Captures state at: reset, FORGE enable, arm enable, ARMED state, spurious trigger
- Generates waveform file for visual inspection
- Minimal output (<20 lines) following P1 standards

---

## Phase 3: Create P2 Debug Test (Detailed Analysis)

### 3.1 P2 Debug Test Structure

**File:** `tests/sim/dpd_wrapper_tests/P2_dpd_trigger_debug.py`

This test will:
1. Test each trigger path independently
2. Verify gate logic behavior
3. Check for combinational glitches
4. Test initialization sequence timing

**Test Cases:**
- `test_hw_trigger_gate_logic`: Verify CR1[4] properly gates hardware trigger
- `test_sw_trigger_edge_detection`: Verify software trigger edge detection
- `test_combined_trigger_logic`: Verify OR logic works correctly
- `test_initialization_sequence`: Check if timing issue during init
- `test_metavalue_initialization`: Check for uninitialized signals

---

## Phase 4: Create P3 Debug Test (Comprehensive Trace)

### 3.1 P3 Debug Test Structure

**File:** `tests/sim/dpd_wrapper_tests/P3_dpd_trigger_debug.py`

This test will:
1. Full FSM state machine trace
2. All register write/read operations
3. Complete trigger path from source to FSM
4. Stress test with various timing scenarios

---

## Phase 5: Enable Waveform Capture

### 5.1 Update run.py for Debug Mode

Add a debug mode that enables waveform capture:

```python
# In run.py, add waves parameter
waves = os.environ.get("WAVES", "false").lower() == "true"

cocotb_run(
    ...
    waves=waves,  # Enable waveform capture in debug mode
    ...
)
```

**Usage:**
```bash
WAVES=true python run.py  # Generate waveform file
```

### 5.2 Waveform File Location

Waveforms will be generated in test directory:
- `waves.vcd` or `waves.fst` (depending on simulator)
- Can be viewed with GTKWave or similar

---

## Phase 6: Implementation Steps

### Step 1: Create Debug Infrastructure
1. Create `dpd_debug_constants.py` with signal names and timing points
2. Create `dpd_debug_helpers.py` with `SignalMonitor` class
3. Test signal accessibility (some internal signals may need wrapper exposure)

### Step 2: Create P1 Debug Test
1. Create `P1_dpd_trigger_debug.py` following cocotb agent patterns
2. Focus on `test_forge_control` scenario that's failing
3. Add signal monitoring around the failing sequence
4. Enable waveform capture

### Step 3: Run and Analyze
1. Run P1 debug test: `cd tests/sim && WAVES=true uv run python run.py`
2. Review waveform file to see exact timing of spurious trigger
3. Check signal monitor logs for unexpected transitions
4. Identify root cause

### Step 4: Create P2/P3 Tests (if needed)
1. If P1 doesn't reveal issue, create P2 for deeper analysis
2. Create P3 for comprehensive coverage
3. Follow progressive test pattern from cocotb agent

### Step 5: Fix and Verify
1. Implement fix based on findings
2. Re-run debug tests to verify fix
3. Re-run original `test_forge_control` to confirm it passes

---

## Signal Accessibility Considerations

**Challenge:** Some signals may be internal to VHDL and not directly accessible from CocoTB.

**Solutions:**
1. **Expose via wrapper:** Add test ports to CustomWrapper_test_stub.vhd
2. **Use hierarchical access:** Try `dut.dpd_inst.signal_name` if signals are in sub-entities
3. **Infer from outputs:** Monitor OutputC (FSM state) and infer trigger activity
4. **Add debug ports:** Temporarily add debug outputs to VHDL for testing

**Signals to check accessibility:**
- `combined_trigger` - May need wrapper exposure
- `hw_trigger_out` - May need wrapper exposure  
- `sw_trigger_edge` - May need wrapper exposure
- `hw_trigger_enable_gated` - May need wrapper exposure
- `app_reg_hw_trigger_enable` - Should be accessible (register)
- `app_reg_sw_trigger` - Should be accessible (register)
- `ext_trigger_in` - May need wrapper exposure
- `state_reg` - May need wrapper exposure (can infer from OutputC)

---

## Expected Outcomes

### If Issue is Combinational Glitch:
- Waveform will show brief pulse on `combined_trigger` during initialization
- Signal monitor will catch the glitch
- Fix: Add synchronization flip-flop or delay

### If Issue is Metavalue:
- Waveform will show 'U'/'X' values propagating
- Signal monitor will show unexpected transitions
- Fix: Ensure proper initialization/reset

### If Issue is Edge Detection Bug:
- Waveform will show `sw_trigger_edge` pulsing unexpectedly
- Signal monitor will show edge detection firing
- Fix: Fix edge detection logic or initialization

### If Issue is Timing:
- Waveform will show signals changing at wrong times
- Signal monitor will show state transitions out of order
- Fix: Adjust timing or add synchronization

---

## Integration with Existing Tests

The debug tests are **separate from** the main test suite:
- Main tests: `P1_dpd_wrapper_basic.py` (failing test)
- Debug tests: `P1_dpd_trigger_debug.py` (investigation)

This allows:
- Running debug tests independently
- Not affecting main test suite structure
- Easy removal after issue is resolved

---

## Next Steps

1. **Review this plan** - Confirm approach and signal names
2. **Check signal accessibility** - Verify which signals can be monitored
3. **Create debug infrastructure** - Build constants and helpers
4. **Create P1 debug test** - Implement signal monitoring test
5. **Run and analyze** - Capture waveforms and identify root cause
6. **Fix and verify** - Implement fix and confirm resolution

---

## References

- **CocoTB Agent:** `.claude/agents/cocotb-integration-test/agent.md`
- **Debug Document:** `HANDOFF_FSM_TRIGGER_DEBUG.md`
- **Failing Test:** `tests/sim/dpd_wrapper_tests/P1_dpd_wrapper_basic.py::test_forge_control`
- **VHDL Trigger Logic:** `rtl/DPD_shim.vhd` (lines 287-327)


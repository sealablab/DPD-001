# Debug Test Usage Guide

## Quick Start

### Run Debug Tests

```bash
cd tests/sim

# Run P1 debug test (signal monitoring)
TEST_MODULE=dpd.P1_dpd_trigger_debug python run.py

# Run with waveform capture
WAVES=true TEST_MODULE=dpd.P1_dpd_trigger_debug python run.py
```

### Run Standard Tests

```bash
# Run P1 basic tests (default)
python run.py

# Run async adapter tests
TEST_MODULE=dpd.P1_async_adapter_test python run.py
```

## Debug Test Structure

### Files

1. **`dpd/dpd_debug_constants.py`** - Signal names, timing points, test configuration
2. **`dpd/dpd_debug_helpers.py`** - SignalMonitor class and capture utilities
3. **`dpd/P1_dpd_trigger_debug.py`** - P1 debug test suite

### Test Coverage

**P1 Debug Tests:**
- `test_signal_accessibility` - Check which signals are accessible
- `test_trigger_path_monitoring` - Monitor trigger path during failing scenario

## Signal Accessibility

The debug tests attempt to access trigger signals via hierarchical paths:
- `dut.dpd_shim_inst.combined_trigger`
- `dut.dpd_shim_inst.hw_trigger_out`
- `dut.dpd_shim_inst.sw_trigger_edge`
- etc.

If hierarchical access fails, the tests will:
1. Log which signals are inaccessible
2. Fall back to inference from OutputC (FSM state)
3. Still capture Control register values (accessible)

## Waveform Capture

When `WAVES=true`, cocotb-test generates a waveform file:
- **Location:** `tests/sim/waves.vcd` or `waves.fst`
- **Viewer:** GTKWave or similar VCD/FST viewer
- **Signals to add:** All trigger path signals from `dpd_debug_constants.py`

### Viewing Waveforms

```bash
# Install GTKWave (if needed)
# macOS: brew install gtkwave
# Linux: apt-get install gtkwave

# Open waveform
gtkwave waves.vcd
```

In GTKWave:
1. Add signals: `combined_trigger`, `hw_trigger_out`, `sw_trigger_edge`, etc.
2. Zoom to time around ARMED -> FIRING transition
3. Look for unexpected pulses or glitches

## Expected Output

### Successful Run (No Spurious Trigger)

```
Running dpd tests
======================================================================
Test: Signal accessibility check
  Accessible signals: 3/8
Test: Trigger path monitoring
  Trigger Path State: At ARMED state
    combined_trigger = 0
    hw_trigger_out = 0
    sw_trigger_edge = 0
    ...
  OutputC (FSM state) = 6554
  Trigger Path State: After monitoring period
    ...
Tests completed successfully!
```

### Spurious Trigger Detected

```
SPURIOUS TRIGGER: OutputC=9831 (expected ARMED=6554)
  combined_trigger transitions:
    Cycle 1234: 0 -> 1
  hw_trigger_out transitions:
    (no transitions)
  sw_trigger_edge transitions:
    Cycle 1234: 0 -> 1
```

## Troubleshooting

### "Signal not accessible" Warnings

This is expected for internal signals. The tests will:
- Still work using OutputC inference
- Log which signals are accessible
- Capture Control register values (always accessible)

### Waveform File Not Generated

Check:
1. `WAVES=true` is set (case-sensitive)
2. cocotb-test supports waveform generation for your simulator
3. Check for errors in test output

### Tests Hang or Timeout

The debug tests use the same timeout mechanisms as production tests. If they hang:
1. Check for infinite loops in signal monitoring
2. Verify clock is running
3. Check reset sequence

## Next Steps

After running debug tests:

1. **Review signal monitor logs** - Look for unexpected transitions
2. **Analyze waveforms** - Visual inspection of trigger signals
3. **Check Control registers** - Verify CR1 values
4. **Identify root cause** - Based on findings, implement fix
5. **Re-run tests** - Verify all tests pass

## References

- **Main README:** [README.md](README.md)
- **GHDL Filter:** [FILTER_QUICKSTART.md](FILTER_QUICKSTART.md)
- **Project Documentation:** `CLAUDE.md` (project root)

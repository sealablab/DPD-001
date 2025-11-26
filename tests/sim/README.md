## Demo Probe Driver (DPD) CocoTB Tests

Progressive test suite for the DPD custom instrument wrapper, following FORGE CocoTB testing standards.

### Quick Start

```bash
# Run P1 (BASIC) tests - minimal output (~73 lines with automatic filtering)
python run.py

# Run with more verbosity
COCOTB_VERBOSITY=NORMAL python run.py

# Run P2 tests (when implemented)
TEST_LEVEL=P2_INTERMEDIATE python run.py

# Disable GHDL output filtering (if needed for debugging)
GHDL_FILTER=none python run.py
```

**Note:** `run.py` now includes intelligent GHDL output filtering that reduces output by 99.6% (from ~12,500 lines to ~73 lines) while preserving all test results and errors. See [FILTER_QUICKSTART.md](FILTER_QUICKSTART.md) for details.

### Test Structure

```
cocotb_tests/
├── dpd_wrapper_tests/           # Test module package
│   ├── __init__.py
│   ├── dpd_wrapper_constants.py # Constants and configuration
│   ├── dpd_helpers.py           # DPD-specific test helpers
│   └── P1_dpd_wrapper_basic.py  # P1 (BASIC) test suite
├── conftest.py                  # CocoTB fixtures (adapted from forge-vhdl)
├── run.py                       # Test runner script
└── README.md                    # This file
```

### P1 Test Coverage

**5 Essential Tests:**

1. **test_reset** - Verify Reset drives FSM to IDLE, outputs inactive
2. **test_forge_control** - Verify FORGE control scheme (CR0[31:29]) gates operation
3. **test_fsm_software_trigger** - Complete FSM cycle via sw_trigger (CR1[1])
4. **test_fsm_hardware_trigger** - Complete FSM cycle via InputA voltage
5. **test_output_pulses** - Verify OutputA/B active during FIRING state

**FSM States Observed via OutputC (HVS encoding):**
- IDLE: digital value ~0
- ARMED: digital value ~200
- FIRING: digital value ~400
- COOLDOWN: digital value ~600

### Test Philosophy

**RELAXED TIMING:**
- Tests focus on **state transitions**, not strict cycle counts
- Timing tolerances accommodate simulator variations
- `wait_for_state()` polls OutputC until transition occurs
- `wait_cycles_relaxed()` adds margin (default 20%) to cycle waits

**OBSERVATION STRATEGY:**
- Tests observe OutputC as a "digital oscilloscope" would
- No internal signal peeking - pure black-box testing
- HVS encoding provides human-readable state + machine-readable status

### Key Test Helpers

**From `dpd_helpers.py`:**
- `wait_for_state(dut, target_digital, timeout_us)` - Poll OutputC for state transition
- `assert_state(dut, expected_digital, tolerance)` - Assert FSM state via OutputC
- `arm_dpd(dut, trig_duration, intensity_duration, cooldown)` - Arm FSM with timing
- `software_trigger(dut)` - Trigger via sw_trigger (CR1[1], edge-detected)
- `hardware_trigger(dut, voltage_mv, threshold_mv)` - Trigger via InputA voltage comparator
- `wait_for_fsm_complete_cycle(dut, firing_cycles, cooldown_cycles)` - Wait for full cycle

**From `conftest.py`:**
- `setup_clock(dut, period_ns, clk_signal)` - Start 125MHz clock
- `reset_active_high(dut, cycles, rst_signal)` - Apply active-high reset
- `mcc_set_regs(dut, control_regs, set_forge_ready)` - Set Control Registers
- `init_mcc_inputs(dut)` - Initialize InputA/B/C/D to zero

### Constants

**From `dpd_wrapper_constants.py`:**

**HVS Digital Values:**
```python
HVS_DIGITAL_IDLE = 0       # State 0 × 200
HVS_DIGITAL_ARMED = 200    # State 1 × 200
HVS_DIGITAL_FIRING = 400   # State 2 × 200
HVS_DIGITAL_COOLDOWN = 600 # State 3 × 200
HVS_DIGITAL_TOLERANCE = 20 # ±20 digital units
```

**FORGE Control:**
```python
MCC_CR0_ALL_ENABLED = 0xE0000000  # Bits 31+30+29 set
```

**P1 Timing (Fast Tests):**
```python
P1TestValues.TRIG_OUT_DURATION = 1000     # 8μs
P1TestValues.INTENSITY_DURATION = 2000    # 16μs
P1TestValues.COOLDOWN_INTERVAL = 500      # 4μs
```

### Voltage Conversion

```python
from dpd_wrapper_tests.dpd_wrapper_constants import mv_to_digital, digital_to_mv

# Moku ADC/DAC: ±5V = ±32768 digital (16-bit signed)
digital = mv_to_digital(1500)  # 1500mV → ~9830 digital
voltage = digital_to_mv(9830)  # 9830 digital → ~1500mV
```

### Expected Output

**P1 Passing Tests (<20 lines):**
```
=====================================================================
Running dpd_wrapper tests
=====================================================================
Simulator: ghdl
Top-level: customwrapper
Test Level: P1_BASIC
Verbosity: MINIMAL
Sources: 7 VHDL files
=====================================================================

P1 - BASIC TESTS
T1: Reset behavior
  ✓ PASS
T2: FORGE control scheme
  ✓ PASS
T3: FSM cycle (software trigger)
  ✓ PASS
T4: FSM cycle (hardware trigger)
  ✓ PASS
T5: Output pulses during FIRING
  ✓ PASS
ALL 5 TESTS PASSED

✅ Tests completed successfully!
```

### Debugging

**If tests fail:**

1. **Check timeout messages** - Shows which state FSM is stuck in
2. **Increase verbosity:**
   ```bash
   COCOTB_VERBOSITY=VERBOSE python run.py
   ```
3. **Enable waveforms** - Edit `run.py`, set `waves=True`
4. **Check OutputC value** - Diagnostic shows actual vs expected digital value

**Common Issues:**

| Symptom | Likely Cause |
|---------|-------------|
| Stuck in IDLE after arm | FORGE control not fully enabled (CR0[31:29] ≠ 111) |
| Stuck in ARMED after software trigger | ext_trigger_in not connected or FSM trigger logic bug |
| Stuck in ARMED after hardware trigger | Voltage threshold detection broken |
| Both triggers fail | FSM transition logic bug |
| FIRING → COOLDOWN doesn't transition | Duration counter bug |
| OutputA/B timing wrong | Pulse generator logic bug |

### Next Steps

**P2 (INTERMEDIATE) - Future Work:**
- auto_rearm_enable (COOLDOWN → ARMED loop)
- FAULT state injection and recovery
- Probe monitor feedback (InputB)
- Edge case timing values

**P3 (COMPREHENSIVE) - Future Work:**
- Stress testing (rapid trigger cycles)
- Concurrent trigger sources
- Register changes during FSM operation
- Full status register verification

### References

- **FORGE Architecture:** `examples/demo-probe-driver/FORGE_ARCHITECTURE.md`
- **Register Spec:** `examples/demo-probe-driver/DPD-RTL.yaml`
- **HVS Encoding:** `examples/demo-probe-driver/HVS.md`
- **CocoTB Standards:** `libs/forge-vhdl/CLAUDE.md`

---

**Author:** Moku Instrument Forge Team
**Date:** 2025-11-18
**Version:** 1.0.0 (P1 only)

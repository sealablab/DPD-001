## Demo Probe Driver (DPD) CocoTB Tests

Progressive test suite for the DPD custom instrument wrapper using CocoTB and GHDL simulation.

### Quick Start

```bash
cd tests/sim

# Run P1 basic tests (default)
python run.py

# Run specific test module
TEST_MODULE=dpd.P1_basic python run.py

# Run async adapter tests
TEST_MODULE=dpd.P1_async_adapter_test python run.py

# Run with more verbosity
COCOTB_VERBOSITY=NORMAL python run.py

# Disable GHDL output filtering (for debugging)
GHDL_FILTER=none python run.py
```

**Note:** `run.py` includes intelligent GHDL output filtering that reduces output by 99.6% while preserving test results. See [FILTER_QUICKSTART.md](FILTER_QUICKSTART.md) for details.

### Test Structure

```
tests/
├── lib/                        # Test library (constants, utilities)
│   ├── hw.py                   # Hardware constants (from py_tools)
│   ├── clk.py                  # Clock utilities (from py_tools)
│   ├── dpd_config.py           # DPDConfig dataclass
│   ├── timing.py               # P1Timing, P2Timing configurations
│   ├── tolerances.py           # SIM_HVS_TOLERANCE, HW_HVS_TOLERANCE
│   └── timeouts.py             # Timeout constants
├── adapters/                   # Platform adapters (unified async API)
│   ├── base.py                 # Abstract base classes
│   ├── cocotb.py               # CocoTBAsyncHarness
│   └── moku.py                 # MokuAsyncHarness
├── sim/                        # Simulation tests
│   ├── run.py                  # Test runner
│   ├── conftest.py             # CocoTB fixtures
│   ├── test_base.py            # Base test class
│   ├── ghdl_filter.py          # Output filter
│   └── dpd/                    # DPD test package
│       ├── P1_basic.py         # P1 (BASIC) test suite
│       ├── P1_async_adapter_test.py  # Unified async API tests
│       └── helpers.py          # FSM control helpers
└── shared/                     # DEPRECATED: Use tests/lib instead
```

### P1 Test Suites

**P1_basic.py** - 5 essential tests:
1. **test_reset** - Reset drives FSM to IDLE
2. **test_forge_control** - FORGE control scheme (CR0[31:29])
3. **test_fsm_software_trigger** - FSM cycle via sw_trigger
4. **test_fsm_hardware_trigger** - FSM cycle via InputA voltage
5. **test_output_pulses** - OutputA/B active during FIRING

**P1_async_adapter_test.py** - 4 unified API tests:
1. **test_async_adapter_basic** - Basic harness operation
2. **test_async_adapter_with_jitter** - Jitter simulation on CR1
3. **test_async_adapter_unified_api** - Portable sim/hw API
4. **test_jitter_validates_sync_protocol** - STATE_SYNC_SAFE validation

### Importing Test Utilities

```python
# New unified imports from tests/lib
from lib import (
    P1Timing, P2Timing,
    SIM_HVS_TOLERANCE,
    us_to_cycles, cr1_build,
    DPDConfig,
)

# Unified async adapter from tests/adapters
from adapters import CocoTBAsyncHarness
```

### FSM States via OutputC (HVS Encoding)

| State | Digital Value | Voltage |
|-------|--------------|---------|
| INITIALIZING | 0 | 0.0V |
| IDLE | ~3277 | 0.5V |
| ARMED | ~6554 | 1.0V |
| FIRING | ~9831 | 1.5V |
| COOLDOWN | ~13108 | 2.0V |
| FAULT | Negative | Negative |

### Test Philosophy

**Timing-Agnostic Initialization:**
- Set config BEFORE enabling FORGE (not during precise timing windows)
- FSM latches config in INITIALIZING state
- Works identically on simulation and hardware

**Black-Box Testing:**
- Observe OutputC as an oscilloscope would
- No internal signal peeking required
- HVS encoding provides state + status

### Debugging

```bash
# Verbose output
COCOTB_VERBOSITY=DEBUG python run.py

# Waveform capture
WAVES=true TEST_MODULE=dpd.P1_basic python run.py

# Unfiltered GHDL output
GHDL_FILTER=none python run.py
```

### References

- **Main Documentation:** `CLAUDE.md` (project root)
- **HVS Encoding:** `docs/hvs.md`
- **Register Spec:** `rtl/DPD-RTL.yaml`
- **GHDL Filter:** [FILTER_QUICKSTART.md](FILTER_QUICKSTART.md)

---

**Version:** 2.0.0 (unified async adapter)
**Date:** 2025-11-26

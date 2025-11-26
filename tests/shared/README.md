# Shared Test Infrastructure

This package contains test infrastructure shared between simulation (CocoTB) and hardware (Moku) tests for the Demo Probe Driver (DPD).

## Purpose

Reduce code duplication between `tests/sim/` and `tests/hw/` by providing:

- **Single source of truth** for constants (FSM states, HVS values, timing)
- **Common test runner logic** (verbosity, logging, result tracking)
- **Abstract interfaces** for platform-agnostic FSM operations
- **Data-driven test cases** that can be executed by both platforms

## Module Overview

### `constants.py`
Re-exports hardware constants from `py_tools/dpd_constants.py` and adds test-specific values:

```python
from tests.shared.constants import (
    # Hardware constants
    CR1, FSMState, HVS, Platform, DefaultTiming,
    cr1_build, cr1_extract,

    # FORGE control
    MCC_CR0_ALL_ENABLED,

    # Test timing configurations
    P1Timing, P2Timing,

    # HVS state values
    HVS_DIGITAL_IDLE, HVS_DIGITAL_ARMED, ...

    # Tolerances
    SIM_HVS_TOLERANCE, HW_HVS_TOLERANCE_V,
)
```

### `test_base_common.py`
Common test infrastructure mixed into platform-specific base classes:

```python
from tests.shared.test_base_common import (
    TestLevel,        # P1_BASIC, P2_INTERMEDIATE, P3_COMPREHENSIVE
    VerbosityLevel,   # SILENT, MINIMAL, NORMAL, VERBOSE, DEBUG
    TestResult,       # Dataclass for test results
    TestRunnerMixin,  # Common logging and tracking methods
)
```

### `state_helpers.py`
Abstract interfaces for FSM operations:

```python
from tests.shared.state_helpers import (
    FSMStateReader,   # Abstract: read_state_digital(), get_state()
    FSMController,    # Abstract: set_control_register(), wait_cycles()
    FSMTestHarness,   # Abstract: wait_for_state(), arm_fsm(), software_trigger()
)
```

### `test_cases.py`
Data-driven test case definitions:

```python
from tests.shared.test_cases import (
    TestCase,         # Test case dataclass
    TestCategory,     # RESET, FORGE_CONTROL, FSM_TRANSITIONS, ...
    ALL_P1_TESTS,     # List of P1 test cases
    get_tests_by_level,
)
```

## Architecture

```
tests/
├── shared/                      # Shared infrastructure
│   ├── constants.py             # All constants (imports from py_tools)
│   ├── test_base_common.py      # TestLevel, VerbosityLevel, TestRunnerMixin
│   ├── state_helpers.py         # Abstract FSMStateReader, FSMController
│   └── test_cases.py            # Data-driven test definitions
│
├── sim/                         # Simulation tests
│   ├── test_base.py             # TestBase(TestRunnerMixin) - CocoTB
│   └── dpd_wrapper_tests/
│       ├── dpd_wrapper_constants.py  # Imports from shared + sim-specific
│       ├── dpd_helpers.py            # Sim-specific FSM helpers
│       ├── sim_adapter.py            # CocoTBStateReader, CocoTBController
│       └── P1_dpd_wrapper_basic.py   # P1 test suite
│
└── hw/                          # Hardware tests
    ├── hw_test_base.py          # HardwareTestBase(TestRunnerMixin) - Moku
    ├── hw_test_constants.py     # Imports from shared + hw-specific
    ├── hw_test_helpers.py       # HW-specific FSM helpers
    ├── hw_adapter.py            # MokuStateReader, MokuController
    └── P1_hw_basic.py           # P1 test suite
```

## Usage Example

### Simulation Test

```python
from tests.shared.constants import P1Timing, MCC_CR0_ALL_ENABLED
from tests.shared.test_base_common import TestLevel, VerbosityLevel

class MySimTest(TestBase):
    async def test_arm(self):
        harness = CocoTBTestHarness(self.dut)
        harness.controller.set_forge_ready()
        await harness.arm_fsm(P1Timing)
        await harness.wait_for_state("ARMED")
```

### Hardware Test

```python
from tests.shared.constants import P2Timing, MCC_CR0_ALL_ENABLED
from hw_adapter import MokuTestHarness

class MyHWTest(HardwareTestBase):
    def test_arm(self):
        harness = MokuTestHarness(self.mcc, self.osc)
        harness.controller.set_forge_ready()
        harness.arm_fsm(P2Timing)
        harness.wait_for_state("ARMED")
```

## Backward Compatibility

Both `sim/dpd_wrapper_constants.py` and `hw/hw_test_constants.py` provide backward-compatible aliases for existing test code:

- `P1TestValues`, `P2TestValues` classes
- `HVS_DIGITAL_IDLE`, `HVS_DIGITAL_ARMED`, etc.
- `STATE_VOLTAGE_TOLERANCE`, `MCC_CR0_ALL_ENABLED`, etc.

Existing tests continue to work without modification.

## Adding New Constants

1. Add to `py_tools/dpd_constants.py` if it's a hardware constant
2. Add to `tests/shared/constants.py` if it's test-specific
3. Re-export in platform modules if needed for backward compatibility

## Key Design Decisions

1. **py_tools/dpd_constants.py is authoritative** for hardware constants
2. **Tolerances differ** between sim (±200 digital) and hw (±300mV)
3. **Timing differs** - P1 for fast sim tests, P2 for observable hw tests
4. **Abstract interfaces** allow same test logic, different execution
5. **Backward compatibility** via aliases prevents breaking existing code

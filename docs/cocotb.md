# CocoTB

**Last Updated:** 2025-11-12 (migrated 2025-01-28)  
**Maintainer:** Moku Instrument Forge Team

> **Migration Note:** This document was migrated from FORGE-V5 and expanded with DPD-001-specific implementation details.

---

## Overview

**[CocoTB](https://www.cocotb.org)** is an open source coroutine-based cosimulation testbench environment for verifying VHDL and SystemVerilog RTL using Python.

**In English:** CocoTB lets you design and run **unit tests** against your FPGA designs without the need for any vendor-specific toolchain or simulator.

The FORGE-V5 ecosystem (and DPD-001) makes **extensive use** of CocoTB for progressive testing workflows.

---

## Key Features

### 1. Python-Based Testing

**Write tests in Python, not VHDL/Verilog:**
- Use familiar Python testing patterns
- Leverage Python's rich ecosystem
- Easy integration with LLM-based workflows

### 2. No Vendor Tools Required

**Works with open-source simulators:**
- GHDL (VHDL) - used by DPD-001
- Icarus Verilog (Verilog)
- Verilator (SystemVerilog)

**No need for:**
- Xilinx Vivado (for simulation)
- Intel Quartus (for simulation)
- Cadence/Synopsys tools

### 3. Coroutine-Based

**Async/await pattern for timing:**
```python
import cocotb
from cocotb.triggers import ClockCycles, RisingEdge

@cocotb.test()
async def test_reset(dut):
    """Test reset behavior"""
    # Wait for clock cycles
    await ClockCycles(dut.clk, 10)
    
    # Wait for rising edge
    await RisingEdge(dut.clk)
    
    # Check output
    assert dut.output.value == 0
```

---

## DPD-001 Implementation

### Directory Structure

**DPD-001 uses:** `tests/sim/` (not `cocotb-tests/`)

```
tests/sim/
├── dpd_wrapper_tests/           # Test module package
│   ├── __init__.py
│   ├── dpd_wrapper_constants.py # Constants and configuration
│   ├── dpd_helpers.py           # DPD-specific test helpers
│   ├── dpd_debug_helpers.py     # Debug-specific helpers
│   └── P1_dpd_wrapper_basic.py  # P1 (BASIC) test suite
├── conftest.py                  # CocoTB fixtures
├── test_base.py                 # Progressive test base class
├── ghdl_filter.py               # GHDL output filtering
├── run.py                       # Test runner script
└── README.md                    # Test documentation
```

**Note:** FORGE-V5 originally suggested `cocotb-tests/` directory, but DPD-001 uses `tests/sim/` to align with standard Python test conventions.

### Test Base Class

**DPD-001 provides:** `TestBase` class with progressive testing support

**Location:** `tests/sim/test_base.py`

```python
from test_base import TestBase, TestLevel

class DPDWrapperBasicTests(TestBase):
    """P1 (BASIC) tests for Demo Probe Driver wrapper"""
    
    def __init__(self, dut):
        super().__init__(dut, "DPD_Wrapper")
    
    async def run_p1_basic(self):
        """P1 test suite entry point"""
        await self.setup()
        await self.test("Reset behavior", self.test_reset)
        await self.test("FORGE control", self.test_forge_control)
        # ... more tests
```

**Features:**
- Progressive test levels (P1/P2/P3/P4)
- Verbosity control
- Standardized test output
- Test result tracking

### Test Runner

**DPD-001 test runner:** `tests/sim/run.py`

```bash
# Run P1 tests (default)
cd tests/sim
python run.py

# Run P2 tests
TEST_LEVEL=P2_INTERMEDIATE python run.py

# Run with verbosity control
COCOTB_VERBOSITY=NORMAL python run.py

# Disable GHDL filtering (for debugging)
GHDL_FILTER=none python run.py
```

**Features:**
- Automatic GHDL output filtering (99.6% reduction)
- Progressive test level selection
- Verbosity control
- Test result summary

---

## CocoTB Patterns in DPD-001

### 1. Clock Setup

**Standard pattern:**
```python
from conftest import setup_clock

async def setup(self):
    """Common setup for all tests"""
    await setup_clock(self.dut, period_ns=8)  # 125 MHz for Moku:Go
    await reset_active_high(self.dut)
```

### 2. Reset Pattern

**Active-high reset:**
```python
from conftest import reset_active_high

async def setup(self):
    await reset_active_high(self.dut)
    # DUT is now in reset state
```

### 3. Signal Access

**Accessing DUT signals:**
```python
# Read output
output_value = int(dut.OutputA.value.signed_integer)  # Signed 16-bit

# Write input
dut.InputA.value = 2000  # 2000 mV (signed 16-bit)

# Read control register
cr0_value = int(dut.Control0.value)
```

**Critical:** Use `.signed_integer` for signed types to preserve sign!

### 4. Timing Control

**Wait for clock cycles:**
```python
from cocotb.triggers import ClockCycles

# Wait 10 clock cycles
await ClockCycles(dut.clk, 10)

# Wait for rising edge
from cocotb.triggers import RisingEdge
await RisingEdge(dut.clk)
```

### 5. Register Access

**DPD-001 helper functions:**
```python
from conftest import mcc_set_regs, forge_cr0

# Set FORGE control (CR0[31:29])
await forge_cr0(dut, forge_ready=True, user_enable=True, clk_enable=True)

# Set application registers
regs = [0, 0x00010001, 0, 0, 0, 0, 0, 0, 0, 0, 0]
await mcc_set_regs(dut, regs)
```

---

## Test Example

**Complete P1 test example from DPD-001:**

```python
"""
P1 - BASIC tests for Demo Probe Driver wrapper
"""

import cocotb
from cocotb.triggers import ClockCycles
from test_base import TestBase
from conftest import setup_clock, reset_active_high, forge_cr0
from dpd_wrapper_tests.dpd_helpers import (
    read_output_c,
    assert_state,
    wait_for_state,
    arm_dpd,
    software_trigger,
)

class DPDWrapperBasicTests(TestBase):
    """P1 (BASIC) tests for Demo Probe Driver wrapper"""
    
    def __init__(self, dut):
        super().__init__(dut, "DPD_Wrapper")
    
    async def setup(self):
        """Common setup for all tests"""
        await setup_clock(self.dut, period_ns=8)  # 125 MHz
        await reset_active_high(self.dut)
        await forge_cr0(self.dut, forge_ready=True, user_enable=True, clk_enable=True)
    
    async def run_p1_basic(self):
        """P1 test suite entry point"""
        await self.setup()
        
        await self.test("Reset behavior", self.test_reset)
        await self.test("FORGE control", self.test_forge_control)
        await self.test("FSM software trigger", self.test_fsm_software_trigger)
        await self.test("FSM hardware trigger", self.test_fsm_hardware_trigger)
        await self.test("Output pulses", self.test_output_pulses)
    
    async def test_reset(self):
        """Verify reset drives FSM to IDLE"""
        # After reset (in setup), check state
        state = await read_output_c(self.dut)
        assert_state(state, "IDLE", tolerance=100)
    
    async def test_fsm_software_trigger(self):
        """Complete FSM cycle via software trigger"""
        await arm_dpd(self.dut)
        await wait_for_state(self.dut, "ARMED", timeout_cycles=1000)
        await software_trigger(self.dut)
        await wait_for_fsm_complete_cycle(self.dut, timeout_cycles=5000)

@cocotb.test()
async def test_dpd_wrapper_p1(dut):
    """P1 test entry point (called by CocoTB)"""
    tester = DPDWrapperBasicTests(dut)
    await tester.run_p1_basic()
```

---

## Integration with GHDL

**DPD-001 uses GHDL for VHDL simulation:**

**Compilation:**
```bash
# Compile VHDL (order matters - dependencies first)
make compile
```

**Test Execution:**
```bash
# Run tests (GHDL is invoked automatically by CocoTB)
cd tests/sim
python run.py
```

**GHDL Output Filtering:**
- Automatic filtering via `ghdl_filter.py`
- 99.6% output reduction (12,500 lines → 55 lines)
- Preserves all errors and test results

**See:** [GHDL Output Filter](ghdl-output-filter.md) for details.

---

## Best Practices

### 1. Use Test Base Class

**Always inherit from `TestBase`:**
```python
from test_base import TestBase

class MyModuleTests(TestBase):
    def __init__(self, dut):
        super().__init__(dut, "MyModule")
```

### 2. Progressive Test Levels

**Organize tests by level:**
- P1: Essential tests only (<20 lines output)
- P2: Core functionality (<50 lines output)
- P3: Comprehensive (<100 lines output)

**See:** [Progressive Testing](progressive-testing.md) for details.

### 3. Helper Functions

**Extract common patterns:**
```python
# dpd_helpers.py
def read_output_c(dut) -> int:
    """Read OutputC (HVS encoded state)"""
    return int(dut.OutputC.value.signed_integer)

def assert_state(actual: int, expected_state: str, tolerance: int = 100):
    """Assert FSM state matches expected"""
    expected = HVS_DIGITAL_STATES[expected_state]
    assert abs(actual - expected) <= tolerance, \
        f"State mismatch: expected {expected_state} (~{expected}), got {actual}"
```

### 4. Constants File

**Centralize test constants:**
```python
# dpd_wrapper_constants.py
HVS_DIGITAL_IDLE = 0
HVS_DIGITAL_ARMED = 3277
HVS_DIGITAL_FIRING = 6554
HVS_DIGITAL_COOLDOWN = 9831
```

### 5. Signed Integer Access

**Always use `.signed_integer` for signed types:**
```python
# CORRECT
value = int(dut.OutputA.value.signed_integer)

# WRONG (loses sign!)
value = int(dut.OutputA.value)
```

---

## Resources

### Official Documentation

- **[CocoTB Documentation](https://docs.cocotb.org/)** - Official docs
- **[CocoTB Examples](https://github.com/cocotb/cocotb/tree/master/examples)** - Example testbenches
- **[CocoTB GitHub](https://github.com/cocotb/cocotb)** - Source code

### DPD-001 Resources

- [Test Architecture](test-architecture/) - Component test design patterns
- [Progressive Testing](progressive-testing.md) - Test level philosophy
- [GHDL Output Filter](ghdl-output-filter.md) - Output filtering
- [Test README](../tests/sim/README.md) - DPD-001 test documentation

---

## Migration Notes

**Source:** FORGE-V5 `/docs/FORGE-V5/CocoTB/README.md`  
**Migration Date:** 2025-01-28  
**Changes:**
- Expanded from 19 lines to comprehensive guide
- Added DPD-001-specific directory structure (`tests/sim/` vs `cocotb-tests/`)
- Documented TestBase class usage
- Added complete test examples from DPD-001
- Included GHDL integration details
- Added best practices section
- Added helper function patterns

---

**Last Updated:** 2025-01-28  
**Maintainer:** Moku Instrument Forge Team  
**Status:** Migrated and expanded with DPD-001 examples


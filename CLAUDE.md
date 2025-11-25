# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DPD-001 (Demo Probe Driver) is an FPGA-based probe controller for Moku:Go platforms. It combines VHDL hardware design with Python tooling and a comprehensive test framework.

**Platform**: Moku:Go (125 MHz clock, ±5V analog I/O, 16-bit ADC/DAC)

## Build Commands

```bash
# Compile VHDL (order matters - dependencies first)
make compile

# Clean build artifacts
make clean
```

## Test Commands

```bash
# Run CocoTB simulation tests
cd tests/sim && python run.py

# Verbosity options
COCOTB_VERBOSITY=DEBUG python run.py
GHDL_FILTER=none python run.py  # Disable output filtering

# Hardware tests (requires live Moku device)
cd tests/hw && python run_hw_tests.py <device_ip> --bitstream path/to/dpd.tar
```

## Architecture

### 3-Layer Forge Pattern (VHDL)

```
DPD.vhd (TOP)          - Extracts FORGE control bits from CR0[31:29]
    └── DPD_shim.vhd   - Maps raw registers to friendly signals, HVS encoding
        └── DPD_main.vhd  - MCC-agnostic FSM logic (portable across platforms)
```

**Layer 3 is intentionally MCC-agnostic** for cross-platform portability.

### FSM States (DPD_main.vhd)
- INITIALIZING (0x00) → IDLE (0x01) → ARMED (0x02) → FIRING (0x03) → COOLDOWN (0x04)
- FAULT (0x3F) is sticky - requires `fault_clear` bit to escape

### FORGE Control Scheme
CR0[31:29] must all be set (0xE0000000) for safe operation:
- Bit 31: `forge_ready` (set by MCC loader)
- Bit 30: `user_enable` (user control)
- Bit 29: `clk_enable` (clock gating)

### HVS (Hierarchical Voltage Scoring)
FSM state is encoded as voltage on OutputC for oscilloscope debugging:
- Each state = 3,277 digital units (~0.5V)
- IDLE=0V, ARMED=0.5V, FIRING=1.0V, COOLDOWN=1.5V

### Control Registers (CR1-CR10)
- CR1: Lifecycle bits (arm_enable, sw_trigger, auto_rearm, fault_clear)
- CR2: Trigger threshold + output voltage (16-bit signed mV each)
- CR3: Intensity voltage
- CR4-CR7: Timing in clock cycles (trigger duration, intensity duration, timeout, cooldown)
- CR8-CR10: Monitor configuration

## Key Conventions

**Voltages**: 16-bit signed integers in millivolts (stored directly, no conversion)

**Timing**: All timing values are raw clock cycles at 125 MHz. Use `py_tools/clk_utils.py` for conversions:
```python
from py_tools.clk_utils import us_to_cycles
cycles = us_to_cycles(100)  # 100μs → 12,500 cycles
```

**Config Generation**: Use `DPDConfig` dataclass, never hardcode register values:
```python
from py_tools.dpd_config import DPDConfig
config = DPDConfig(arm_enable=True, trig_out_voltage=2000)
regs = config.to_control_regs_list()
```

## Test Levels

Tests follow P1 → P2 → P3 progression:
- **P1 (Basic)**: Essential smoke tests
- **P2 (Intermediate)**: Core functionality
- **P3 (Comprehensive)**: Edge cases and stress tests

## Debug Timing

Scale timing for oscilloscope observation:
```bash
export CLK_UTILS_SLOW_MODE=1000  # 1000x slower (100μs → 100ms)
```

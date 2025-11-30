---
created: 2025-11-30
modified: 2025-11-30 14:06:26
accessed: 2025-11-30 13:56:51
---
# BOOT/BIOS Bitstream Synthesis & Validation Guide

> [!info] Session Context
> This guide walks through synthesizing the BOOT/BIOS subsystem into a working Moku:Go bitstream, creating validation test suites, and building a streaming Python client for real-time HVS feedback.
>
> **Created**: 2024-11-30
> **Branch**: `claude/boot-bios-bitstream-*`

---

@JC: START here :P

## Overview

```
┌─────────────────────────────────────────────────────────┐
│                    SESSION GOALS                        │
├─────────────────────────────────────────────────────────┤
│ 1. Synthesize BOOT+BIOS+LOADER into CloudCompile pkg    │
│ 2. Create non-interactive simulation test suite         │
│ 3. Create hardware validation test suite                │
│ 4. Build streaming HVS client with prompt_toolkit       │
└─────────────────────────────────────────────────────────┘
```


| Component         | read | approved | Location                             | `RTL`   (code) `py`                                                      | `MD` (docs)                                                           | Status     |
| ----------------- | ---- | -------- | ------------------------------------ | ------------------------------------------------------------------------ | --------------------------------------------------------------------- | ---------- |
| BOOT Dispatcher   |      |          | `rtl/boot/B0_BOOT_TOP.vhd`           | [rtl/boot/B0_BOOT_TOP.vhd](rtl/boot/B0_BOOT_TOP.vhd)                     | [B0_BOOT_TOP.vhd.md](rtl/boot/B0_BOOT_TOP.vhd.md)                     | ✅ Complete |
| BIOS Stub         |      |          | `rtl/boot/B1_BOOT_BIOS.vhd`          | [rtl/boot/B1_BOOT_BIOS.vhd](rtl/boot/B1_BOOT_BIOS.vhd)                   | [B1_BOOT_BIOS.vhd.md](rtl/boot/B1_BOOT_BIOS.vhd.md)                   | ✅ Complete |
| Buffer Loader     |      |          | `rtl/boot/L2_BUFF_LOADER.vhd`        | [rtl/boot/L2_BUFF_LOADER.vhd](rtl/boot/L2_BUFF_LOADER.vhd)               | [L2_BUFF_LOADER.vhd.md](rtl/boot/L2_BUFF_LOADER.vhd.md)               | ✅ Complete |
| CRC-16 Module     |      |          | `rtl/boot/loader_crc16.vhd`          | [rtl/boot/loader_crc16.vhd](rtl/boot/loader_crc16.vhd)                   | [loader_crc16.vhd.md](rtl/boot/loader_crc16.vhd.md)                   | ✅ Complete |
| Test Stub         |      |          | `rtl/boot/BootWrapper_test_stub.vhd` | [rtl/boot/BootWrapper_test_stub.vhd](rtl/boot/BootWrapper_test_stub.vhd) | [BootWrapper_test_stub.vhd.md](rtl/boot/BootWrapper_test_stub.vhd.md) | ✅ Complete |
| Python Constants  |      |          | `py_tools/boot_constants.py`         | [py_tools/boot_constants.py](py_tools/boot_constants.py)                 |                                                                       | ✅ Complete |
| Interactive Shell |      |          | `py_tools/boot_shell.py`             | [py_tools/boot_shell.py](py_tools/boot_shell.py)                         |                                                                       | ✅ Exists   |
| CocoTB P1 Tests   |      |          | `tests/sim/boot_fsm/P1_basic.py`     | [tests/sim/boot_fsm/P1_basic.py](tests/sim/boot_fsm/P1_basic.py)         |                                                                       | ✅ Exists   |
| LOADER P1 Tests   |      |          | `tests/sim/loader/P1_basic.py`       | [tests/sim/loader/P1_basic.py](tests/sim/loader/P1_basic.py)             |                                                                       | ✅ Exists   |


### What We're Buildingtmux 

| Deliverable | Location | Phase |
|-------------|----------|-------|
| Synthesis package | `synth/boot/` | 1 |
| Sim test runner | `tests/sim/boot_suite.py` | 2 |
| HW test suite | `tests/hw/boot/` | 3 |
| Streaming client | `py_tools/boot_client.py` | 4 |

---

## Prerequisites

- [ ] GHDL installed and working (`ghdl --version`)
- [ ] Python 3.8+ with cocotb, prompt_toolkit
- [ ] Access to Moku CloudCompile (for synthesis upload)
- [ ] Physical Moku:Go device (for Phase 3)
- [ ] Familiar with [[BOOT-FSM-spec]] and [[BOOT-HVS-state-reference]]

---

## Phase 1: Bitstream Synthesis Prep

> [!goal] Goal
> Create a synthesis-ready package that can be uploaded to Moku CloudCompile.

### Deliverables

```
synth/
└── boot/
    ├── CustomWrapper.vhd      # Top-level entity (CloudCompile expects this name)
    ├── forge_common_pkg.vhd
    ├── forge_hierarchical_encoder.vhd
    ├── loader_crc16.vhd
    ├── L2_BUFF_LOADER.vhd
    ├── B1_BOOT_BIOS.vhd
    ├── B0_BOOT_TOP.vhd
    └── boot-synth.tar         # Final upload package
```

### Steps

#### 1.1 Verify Compilation Order

The VHDL files have dependencies. Confirm this order compiles cleanly:

```bash
# From repo root
cd rtl

# 1. Package first (defines types/constants)
ghdl -a --std=08 forge_common_pkg.vhd

# 2. Support modules (no internal dependencies)
ghdl -a --std=08 forge_hierarchical_encoder.vhd
ghdl -a --std=08 boot/loader_crc16.vhd

# 3. BOOT subsystem (bottom-up)
ghdl -a --std=08 boot/L2_BUFF_LOADER.vhd
ghdl -a --std=08 boot/B1_BOOT_BIOS.vhd

# 4. DPD components (needed for PROG_ACTIVE state)
ghdl -a --std=08 moku_voltage_threshold_trigger_core.vhd
ghdl -a --std=08 DPD_main.vhd
ghdl -a --std=08 DPD_shim.vhd

# 5. BOOT top (instantiates everything)
ghdl -a --std=08 boot/B0_BOOT_TOP.vhd
```

> [!warning] Common Issue
> If you see "entity not found" errors, check that `forge_common_pkg.vhd` was analyzed first. All modules depend on it.

#### 1.2 Create CustomWrapper for CloudCompile

CloudCompile expects a top-level entity named `CustomWrapper`. You need to create a wrapper that:

1. Matches the CloudCompile port signature (Control0-10, InputA-D, OutputA-D, etc.)
2. Instantiates `B0_BOOT_TOP` as the architecture

**Key decisions:**
- Use `B0_BOOT_TOP` entity directly, or create a thin wrapper?
- The existing `BootWrapper_test_stub.vhd` is for simulation only

> [!tip] LLM Assist
> *"Review `rtl/boot/BootWrapper_test_stub.vhd` and `rtl/CustomWrapper_test_stub.vhd`. Create a synthesis-ready `CustomWrapper.vhd` that instantiates `B0_BOOT_TOP` with the correct port mapping for Moku CloudCompile."*

#### 1.3 Prepare Flat Directory

CloudCompile requires all VHDL files in a single flat directory:

```bash
mkdir -p synth/boot
cp rtl/forge_common_pkg.vhd synth/boot/
cp rtl/forge_hierarchical_encoder.vhd synth/boot/
cp rtl/boot/loader_crc16.vhd synth/boot/
cp rtl/boot/L2_BUFF_LOADER.vhd synth/boot/
cp rtl/boot/B1_BOOT_BIOS.vhd synth/boot/
cp rtl/boot/B0_BOOT_TOP.vhd synth/boot/
cp rtl/moku_voltage_threshold_trigger_core.vhd synth/boot/
cp rtl/DPD_main.vhd synth/boot/
cp rtl/DPD_shim.vhd synth/boot/
# CustomWrapper.vhd - create this
```

#### 1.4 Create Synthesis Package

```bash
cd synth/boot
tar -cvf boot-synth.tar *.vhd
```

#### 1.5 Upload to CloudCompile

- Go to Moku CloudCompile portal
- Upload `boot-synth.tar`
- Wait for synthesis (~10-15 min)
- Download resulting `.tar` bitstream

### Validation Criteria

- [ ] All VHDL files compile without errors in GHDL
- [ ] `synth/boot/` contains all required files
- [ ] `boot-synth.tar` created successfully
- [ ] CloudCompile synthesis completes without errors
- [ ] Bitstream `.tar` downloaded

---

## Phase 2: Simulation Test Suite

> [!goal] Goal
> Create a non-interactive test runner that validates all major state transitions in simulation, suitable for CI integration.

### Deliverables

```
tests/sim/
├── boot_suite.py          # Main test runner (NEW)
├── boot_fsm/
│   ├── P1_basic.py        # Existing
│   └── P2_workflow.py     # Enhanced/verified
└── loader/
    ├── P1_basic.py        # Existing
    └── P2_transfer.py     # Enhanced/verified
```

### Steps

#### 2.1 Review Existing Tests

Examine what's already tested:

```bash
# Run existing BOOT tests
cd tests/sim
python boot_run.py

# Run existing LOADER tests
TEST_MODULE=loader.P1_basic python boot_run.py
```

Document what's covered vs. gaps.

#### 2.2 Define Test Matrix

Create a test matrix covering these scenarios:

| Test ID | Category | Scenario | Expected HVS |
|---------|----------|----------|--------------|
| B1 | BOOT | Reset → P0 | 0.000V |
| B2 | BOOT | P0 → P1 (RUN) | 0.030V |
| B3 | BOOT | P1 → BIOS (RUNB) | 0.240V |
| B4 | BOOT | P1 → LOADER (RUNL) | 0.481V |
| B5 | BOOT | P1 → PROG (RUNP) | (DPD takes over) |
| B6 | BOOT | BIOS/LOAD → P1 (RET) | 0.030V |
| B7 | BOOT | Fault propagation | Negative |
| L1 | LOADER | P0 setup strobe | 0.481V |
| L2 | LOADER | P0 → P1 transfer | 0.511V |
| L3 | LOADER | 1024-word complete | 0.541V |
| L4 | LOADER | CRC validation | 0.571V |
| I1 | BIOS | IDLE → RUN auto | 0.271V |
| I2 | BIOS | RUN → DONE auto | 0.301V |

#### 2.3 Create Unified Test Runner

Create `tests/sim/boot_suite.py` that:

1. Imports all test modules
2. Runs them in sequence
3. Collects pass/fail results
4. Returns appropriate exit code (0 = all pass, 1 = failures)

**Structure suggestion:**

```python
#!/usr/bin/env python3
"""
Non-interactive BOOT/BIOS simulation test suite.
Exit code 0 = all tests passed, 1 = failures.

Usage:
    python boot_suite.py [--verbose] [--level P1|P2|P3]
"""

def main():
    # Discover and run tests
    # Aggregate results
    # Print summary
    # sys.exit(0 if all_passed else 1)
```

> [!tip] LLM Assist
> *"Create `tests/sim/boot_suite.py` that discovers and runs all CocoTB tests in `boot_fsm/` and `loader/` directories. Use subprocess to invoke `boot_run.py` with different TEST_MODULE values. Aggregate results and return exit code."*

#### 2.4 Add Missing Test Cases

Review the test matrix (2.2) and add any missing cases to:
- `boot_fsm/P1_basic.py` or `P2_workflow.py`
- `loader/P1_basic.py` or `P2_transfer.py`

Focus on:
- [ ] RET command from BIOS back to BOOT_P1
- [ ] RET command from LOADER back to BOOT_P1
- [ ] Fault injection (force BIOS/LOADER fault, verify BOOT sees it)
- [ ] RUNP one-way transition (verify no return)

### Validation Criteria

- [ ] `python boot_suite.py` runs without manual intervention
- [ ] All tests in matrix are covered
- [ ] Exit code reflects pass/fail status
- [ ] Verbose output shows HVS voltage checks

---

## Phase 3: Hardware Test Suite

> [!goal] Goal
> Create hardware tests that validate the synthesized bitstream on a real Moku:Go device using oscilloscope streaming for HVS feedback.

### Deliverables

```
tests/hw/boot/
├── __init__.py
├── constants.py           # HW-specific timing/tolerances
├── helpers.py             # Oscilloscope + CloudCompile helpers
├── hw_test_base.py        # Base class for HW tests
├── P1_basic.py            # Basic state transitions
├── P2_workflow.py         # Expert workflow validation
└── run_boot_hw_tests.py   # Main runner
```

### Steps

#### 3.1 Review Existing HW Test Infrastructure

Look at the DPD hardware tests for patterns:

```
tests/hw/
├── run_hw_tests.py        # Existing DPD runner
├── hw_test_base.py        # Existing base class
└── dpd/                   # DPD-specific tests
```

#### 3.2 Define Hardware Constants

Create `tests/hw/boot/constants.py`:

```python
# HVS voltage tolerances (wider than sim due to ADC noise)
HVS_TOLERANCE_MV = 300  # ±300mV

# Timing (slower than sim for oscilloscope observability)
REGISTER_PROPAGATION_DELAY = 0.15  # seconds
OSCILLOSCOPE_SETTLE_TIME = 0.05    # seconds
HVS_SAMPLE_COUNT = 5               # averaging

# Expected voltages (from BOOT-HVS-state-reference.md)
EXPECTED_VOLTAGES = {
    'BOOT_P0': 0.0,
    'BOOT_P1': 0.030,
    'BIOS_IDLE': 0.240,
    'BIOS_RUN': 0.271,
    'BIOS_DONE': 0.301,
    'LOAD_P0': 0.481,
    'LOAD_P1': 0.511,
    'LOAD_P2': 0.541,
    'LOAD_P3': 0.571,
}
```

#### 3.3 Create Helper Functions

Create `tests/hw/boot/helpers.py` with:

1. **`read_hvs_voltage(osc, channel='Ch1')`** - Read and average OutputC voltage
2. **`decode_hvs_state(voltage_mv)`** - Map voltage to state name
3. **`send_command(cc, cmd)`** - Set CR0 with proper delay
4. **`wait_for_state(osc, expected_state, timeout=5.0)`** - Poll until state matches

> [!note] Key Pattern
> All hardware reads go through oscilloscope (slot 1).
> All hardware writes go through CloudCompile (slot 2).
> OutputC must be routed to oscilloscope input.

#### 3.4 Create Base Test Class

Create `tests/hw/boot/hw_test_base.py`:

```python
class BootHWTestBase:
    """Base class for BOOT hardware tests."""

    def setup(self, device_ip, bitstream_path):
        # Initialize multi-instrument
        # Slot 1: Oscilloscope (for HVS reads)
        # Slot 2: CloudCompile (for control)
        # Route OutputC → OscInA
        pass

    def teardown(self):
        # Clean disconnect
        pass

    def assert_state(self, expected_state):
        # Read HVS, decode, compare
        pass
```

#### 3.5 Implement P1 Basic Tests

Create `tests/hw/boot/P1_basic.py` covering:

- [ ] Power-on state (should be BOOT_P0 or BOOT_P1 depending on RUN gate)
- [ ] RUN command → BOOT_P1
- [ ] RUNB → BIOS_IDLE
- [ ] BIOS auto-advance → BIOS_DONE
- [ ] RET → back to BOOT_P1
- [ ] RUNL → LOAD_P0

#### 3.6 Create Test Runner

Create `tests/hw/boot/run_boot_hw_tests.py`:

```bash
# Usage
python run_boot_hw_tests.py 192.168.1.100 --bitstream path/to/boot.tar
python run_boot_hw_tests.py 192.168.1.100 --bitstream path/to/boot.tar --level P2
```

> [!tip] LLM Assist
> *"Create `tests/hw/boot/run_boot_hw_tests.py` modeled after `tests/hw/run_hw_tests.py`. Accept device IP and bitstream path as arguments. Discover and run tests from P1_basic.py, aggregate results."*

### Validation Criteria

- [ ] Tests run against real Moku:Go device
- [ ] HVS voltages match expected values (±300mV)
- [ ] State transitions complete within timeout
- [ ] Clear pass/fail output with voltage readings
- [ ] Graceful handling of device connection issues

---

## Phase 4: Streaming HVS Python Client

> [!goal] Goal
> Build an interactive TUI client using prompt_toolkit that provides real-time HVS state feedback and command control.

### Deliverables

```
py_tools/
├── boot_client.py         # Main streaming client (NEW)
├── boot_constants.py      # Existing
├── boot_shell.py          # Existing (reference)
└── hvs_decoder.py         # HVS decode utilities (NEW, optional)
```

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    boot_client.py                       │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │  HVS Stream │  │  Command    │  │  State Display  │ │
│  │  (polling)  │  │  Input      │  │  (reactive)     │ │
│  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘ │
│         │                │                   │          │
│         ▼                ▼                   ▼          │
│  ┌─────────────────────────────────────────────────────┐│
│  │              Application State                      ││
│  │  - current_state: BOOTState | BIOSState | ...      ││
│  │  - voltage_mv: float                                ││
│  │  - fault_active: bool                               ││
│  │  - status_bits: int                                 ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
    Oscilloscope                  CloudCompile
    (Slot 1)                      (Slot 2)
```

### Steps

#### 4.1 Review Existing Shell

Study `py_tools/boot_shell.py` for:
- Command structure (RUN, RUNB, RUNL, RUNP, RET)
- Context-aware prompts
- Key bindings (Esc = RET)

#### 4.2 Design TUI Layout

Sketch the interface:

```
┌─────────────────────────────────────────────────────────┐
│  BOOT/BIOS Client                          Connected ● │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  State: BIOS_RUN                    Voltage: 0.271V    │
│  ████████████░░░░░░░░░░░░░░░░░░░░   Phase: 2/3        │
│                                                         │
│  Status: 0x00                       Fault: None        │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  Commands: [R]UN  [B]IOS  [L]OADER  [P]ROG  [ESC]RET  │
├─────────────────────────────────────────────────────────┤
│  > _                                                    │
└─────────────────────────────────────────────────────────┘
```

#### 4.3 Implement HVS Streaming

Create a background polling loop:

```python
async def hvs_stream(osc, callback, interval=0.1):
    """Poll oscilloscope and invoke callback with decoded state."""
    while True:
        voltage = read_channel_voltage(osc, 'Ch1')
        state, status = decode_pre_prog(voltage)
        fault = voltage < 0
        callback(state, status, voltage, fault)
        await asyncio.sleep(interval)
```

**Key considerations:**
- Use `asyncio` for non-blocking polling
- Poll rate: 100ms (10 Hz) is reasonable for human feedback
- Handle connection drops gracefully

#### 4.4 Implement State Decoder

Use functions from `boot_constants.py`:

```python
from py_tools.boot_constants import decode_pre_prog, digital_to_volts

def decode_hvs_voltage(voltage_mv):
    """Convert voltage to state name and status."""
    digital = int(voltage_mv * 32767 / 5000)  # mV to digital
    global_s, status = decode_pre_prog(digital)

    # Map global_s to state name
    if 0 <= global_s <= 7:
        state_name = f"BOOT_{['P0','P1','BIOS_ACTIVE','LOAD_ACTIVE','PROG_ACTIVE','FAULT'][min(global_s, 5)]}"
    elif 8 <= global_s <= 15:
        state_name = f"BIOS_{['IDLE','RUN','DONE','FAULT'][min(global_s-8, 3)]}"
    # ... etc

    return state_name, status
```

#### 4.5 Build prompt_toolkit Application

Key components:

1. **Layout** - Use `HSplit`/`VSplit` for panels
2. **Key bindings** - R, B, L, P, Esc for commands
3. **Async integration** - `asyncio` event loop with prompt_toolkit
4. **Reactive updates** - Redraw on state change

> [!tip] LLM Assist
> *"Create `py_tools/boot_client.py` using prompt_toolkit. Implement a full-screen TUI with: (1) status panel showing current state, voltage, fault; (2) command bar with key bindings; (3) background HVS polling via asyncio. Use the existing `boot_constants.py` for decoding."*

#### 4.6 Add Fault Indication

When voltage is negative (fault state):
- Change status panel color to red
- Show fault message
- Flash or animate to draw attention

```python
def get_state_style(fault_active):
    if fault_active:
        return "bg:red fg:white bold"
    return "bg:green fg:black"
```

#### 4.7 Add Command History

Store and display recent commands:

```python
command_history = deque(maxlen=10)

def on_command(cmd):
    command_history.append(f"{time.strftime('%H:%M:%S')} {cmd}")
    # ... execute command
```

### Validation Criteria

- [ ] TUI launches and connects to device
- [ ] State updates in real-time as commands are sent
- [ ] Fault state shows visual indication (color change)
- [ ] All commands work (RUN, RUNB, RUNL, RUNP, RET)
- [ ] Graceful exit (Ctrl+C or 'q')
- [ ] Connection loss handled gracefully

---

## Phase 5: Integration & Commit

> [!goal] Goal
> Validate everything works together and commit to the feature branch.

### Steps

#### 5.1 Run Full Simulation Suite

```bash
cd tests/sim
python boot_suite.py --verbose
```

All tests should pass.

#### 5.2 Run Hardware Validation (if device available)

```bash
cd tests/hw/boot
python run_boot_hw_tests.py <device_ip> --bitstream path/to/boot.tar
```

#### 5.3 Test Streaming Client

```bash
cd py_tools
python boot_client.py --ip <device_ip> --bitstream path/to/boot.tar
```

Walk through the full workflow:
1. Observe BOOT_P0/P1 on startup
2. Press B → verify BIOS_IDLE → RUN → DONE auto-advance
3. Press Esc → verify return to BOOT_P1
4. Press L → verify LOAD_P0
5. Press Esc → verify return to BOOT_P1
6. Press P → verify handoff to PROG (one-way)

#### 5.4 Update Documentation

Add any discoveries or corrections to:
- [ ] `docs/boot/BOOT-FSM-spec.md`
- [ ] `docs/boot/BOOT-HVS-state-reference.md`
- [ ] This guide (if needed)

#### 5.5 Commit and Push

```bash
git add .
git commit -m "feat: BOOT/BIOS synthesis, test suites, and streaming client

- Add synthesis package preparation (synth/boot/)
- Create non-interactive simulation test suite (boot_suite.py)
- Create hardware test suite (tests/hw/boot/)
- Add streaming HVS client with prompt_toolkit (boot_client.py)
- Validate all major state transitions work"

git push -u origin claude/boot-bios-bitstream-<session_id>
```

---

## Quick Reference

### Commands

| Key | Command | CR0 Value | Action |
|-----|---------|-----------|--------|
| R | RUN | 0xE0000000 | Enable RUN gate → P1 |
| B | RUNB | 0xE8000000 | Enter BIOS |
| L | RUNL | 0xE4000000 | Enter LOADER |
| P | RUNP | 0xF0000000 | Enter PROG (one-way) |
| Esc | RET | 0xE1000000 | Return to BOOT_P1 |

### HVS Quick Reference

| State | Global S | Voltage |
|-------|----------|---------|
| BOOT_P0 | 0 | 0.000V |
| BOOT_P1 | 1 | 0.030V |
| BIOS_IDLE | 8 | 0.240V |
| BIOS_RUN | 9 | 0.271V |
| BIOS_DONE | 10 | 0.301V |
| LOAD_P0 | 16 | 0.481V |
| LOAD_P1 | 17 | 0.511V |
| LOAD_P2 | 18 | 0.541V |
| LOAD_P3 | 19 | 0.571V |
| FAULT | - | Negative |

### File Locations

| What | Where |
|------|-------|
| VHDL sources | `rtl/boot/` |
| Python tools | `py_tools/` |
| Sim tests | `tests/sim/boot_fsm/`, `tests/sim/loader/` |
| HW tests | `tests/hw/boot/` |
| Synthesis | `synth/boot/` |
| Docs | `docs/boot/` |

---

## Troubleshooting

### Synthesis fails with "entity not found"

Check compilation order. `forge_common_pkg.vhd` must be first.

### HVS voltage reads 0V constantly

1. Verify OutputC → OscInA routing
2. Check RUN gate bits (CR0[31:29] all set?)
3. Confirm bitstream loaded (CloudCompile status)

### BIOS doesn't auto-advance

Check `RUN_DELAY_CYCLES` constant in `B1_BOOT_BIOS.vhd`. Default may be too long for observation.

### Client can't connect

1. Verify device IP is correct
2. Check no other Moku sessions active
3. Try power cycling the Moku:Go

---

## See Also

- [[BOOT-FSM-spec]] - Authoritative FSM specification
- [[LOAD-FSM-spec]] - Buffer loader protocol
- [[BOOT-HVS-state-reference]] - Complete voltage table
- [[BOOT-HW-VALIDATION-PLAN]] - Hardware validation strategy
- [[api-v4]] - Register interface specification

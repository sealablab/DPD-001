# DPD API v4.0 - Register Calling Convention

**Version:** 4.0 (API-breaking refactor)
**Date:** 2025-11-26
**Status:** Authoritative
**YAML Spec:** `rtl/DPD-RTL.yaml`

---

## Overview

This document defines the **software/hardware calling convention** for the Demo Probe Driver. All lifecycle controls are consolidated into CR0 for atomic single-write operations.

**Key Design Principle:** A trigger sequence should require exactly **one** register write after configuration.

---

## CR0 - Lifecycle Control Register

All real-time control is now in CR0. This enables atomic operations:

```
CR0 Bit Layout:
┌────────────────────────────────────────────────────────────────┐
│ 31 │ 30 │ 29 │ 28 │ 27-3 │  2  │  1  │  0  │
├────┼────┼────┼────┼──────┼─────┼─────┼─────┤
│ R  │ U  │ N  │ P  │ rsvd │  A  │  C  │  T  │
└────┴────┴────┴────┴──────┴─────┴─────┴─────┘

R = forge_ready       [31] - Set by loader after deployment
U = user_enable       [30] - User control (GUI toggle)
N = clk_enable        [29] - Clock gating
P = campaign_enable   [28] - Reserved for campaign mode
A = arm_enable        [2]  - Level-sensitive: IDLE → ARMED
C = fault_clear       [1]  - Edge-triggered: FAULT → INITIALIZING
T = sw_trigger        [0]  - Edge-triggered: ARMED → FIRING
```

### FORGE "RUN" Gate

Bits [31:29] form the FORGE safety gate. The FSM only operates when all three are set:

| Constant | Value | Description |
|----------|-------|-------------|
| `RUN` | `0xE0000000` | Module enabled, FSM idle |
| `RUN_ARMED` | `0xE0000004` | Module enabled, FSM armed |
| `RUN_ARMED_TRIG` | `0xE0000005` | **Single-write trigger** |
| `RUN_ARMED_CLEAR` | `0xE0000006` | Clear fault while armed |

### Edge-Triggered Signals

`sw_trigger` (T) and `fault_clear` (C) are **edge-triggered with auto-clear**:

1. RTL detects rising edge (0→1 transition)
2. Pulse stretcher holds signal for 4 clock cycles (32ns @ 125MHz)
3. Software can clear bit immediately or leave it set

This eliminates timing dependencies between software and hardware.

---

## CR1 - Reserved (Campaign Mode)

CR1 is reserved for future campaign mode (burst sequences of 100-1024 triggers with fault accumulation statistics). Currently unused.

---

## CR2-CR10 - Configuration Registers

Configuration parameters that define the probe operation. **Only update when FSM is in INITIALIZING state** (sync-safe gating).

| Register | Field | Bits | Units | Description |
|----------|-------|------|-------|-------------|
| CR2 | `input_trigger_voltage_threshold` | [31:16] | mV (signed) | HW trigger threshold on InputA |
| CR2 | `trig_out_voltage` | [15:0] | mV (signed) | Trigger pulse voltage on OutputA |
| CR3 | `intensity_voltage` | [15:0] | mV (signed) | Intensity voltage on OutputB |
| CR4 | `trig_out_duration` | [31:0] | cycles | Trigger pulse duration |
| CR5 | `intensity_duration` | [31:0] | cycles | Intensity pulse duration |
| CR6 | `trigger_wait_timeout` | [31:0] | cycles | Armed watchdog timeout |
| CR7 | `cooldown_interval` | [31:0] | cycles | Thermal safety delay |
| CR8 | `monitor_threshold_voltage` | [31:16] | mV (signed) | Monitor threshold on InputB |
| CR8 | `auto_rearm_enable` | [2] | bit | Burst mode (auto re-arm after cooldown) |
| CR8 | `monitor_expect_negative` | [1] | bit | Monitor polarity |
| CR8 | `monitor_enable` | [0] | bit | Enable feedback monitoring |
| CR9 | `monitor_window_start` | [31:0] | cycles | Monitor window delay |
| CR10 | `monitor_window_duration` | [31:0] | cycles | Monitor window length |

**Clock:** 125 MHz (8ns period). Use `py_tools/clk_utils.py` for time↔cycle conversions.

---

## Usage Patterns

### Pattern 1: One-Off Trigger (Single Shot)

```python
from py_tools.dpd_constants import CR0

# 1. Configure parameters (any order)
dpd.set_control(2, pack_cr2(threshold_mv=950, trig_mv=2000))
dpd.set_control(4, us_to_cycles(100))   # 100μs trigger pulse
dpd.set_control(7, us_to_cycles(10))    # 10μs cooldown
# ... other config registers

# 2. Enable module
dpd.set_control(0, CR0.RUN)             # 0xE0000000

# 3. Arm
dpd.set_control(0, CR0.RUN_ARMED)       # 0xE0000004

# 4. Fire (SINGLE ATOMIC WRITE)
dpd.set_control(0, CR0.RUN_ARMED_TRIG)  # 0xE0000005
# FSM: ARMED → FIRING → COOLDOWN → IDLE
```

### Pattern 2: Burst Mode (Auto Re-arm)

```python
# Enable burst mode in CR8
cr8 = pack_cr8(monitor_enable=True, auto_rearm=True)
dpd.set_control(8, cr8)

# Arm once
dpd.set_control(0, CR0.RUN_ARMED)       # 0xE0000004

# Each trigger re-arms automatically
dpd.set_control(0, CR0.RUN_ARMED_TRIG)  # Fire
# FSM: ARMED → FIRING → COOLDOWN → ARMED (auto)
dpd.set_control(0, CR0.RUN_ARMED_TRIG)  # Fire again
# ...
```

### Pattern 3: Fault Recovery

```python
# FSM is in FAULT state (monitor failure, timeout, etc.)

# Clear fault and return to IDLE
dpd.set_control(0, CR0.RUN_ARMED_CLEAR) # 0xE0000006
# FSM: FAULT → INITIALIZING → IDLE

# Re-arm when ready
dpd.set_control(0, CR0.RUN_ARMED)       # 0xE0000004
```

### Pattern 4: Parameter Update Mid-Operation

```python
# Configuration registers only update in INITIALIZING state.
# To apply new parameters:

# Force re-initialization
dpd.set_control(0, CR0.RUN | (1 << 1))  # RUN + fault_clear
# FSM: any → INITIALIZING (params latched) → IDLE

# Now safe to arm with new params
dpd.set_control(0, CR0.RUN_ARMED)
```

---

## FSM States

| State | Value | HVS Voltage | Letter | Description |
|-------|-------|-------------|--------|-------------|
| INITIALIZING | 0 | 0.0V | I | Param latch after reset/clear (transient) |
| IDLE | 1 | 0.5V | D | Waiting for arm_enable |
| ARMED | 2 | 1.0V | A | Waiting for trigger |
| FIRING | 3 | 1.5V | F | Driving output pulses |
| COOLDOWN | 4 | 2.0V | C | Thermal safety delay |
| FAULT | 63 | -0.5V | X | Sticky fault (requires clear) |

**HVS Encoding:** OutputC voltage = state × 500mV. Fault state is negative.

---

## What Was Removed (v3 → v4)

These signals **no longer exist** and should be deleted from all code:

| Removed | Was In | Reason |
|---------|--------|--------|
| `sw_trigger_enable` | CR1[4] | Unnecessary gate - FSM state already gates triggers |
| `hw_trigger_enable` | CR1[3] | Unnecessary gate - FSM state already gates triggers |
| `sw_trigger` in CR1 | CR1[5] | Moved to CR0[0] for atomic writes |
| `fault_clear` in CR1 | CR1[2] | Moved to CR0[1] for atomic writes |
| `auto_rearm_enable` in CR1 | CR1[0] | Moved to CR8[2] (it's configuration, not lifecycle) |
| `arm_enable` in CR1 | CR1[1] | Moved to CR0[2] for atomic writes |

---

## Migration Checklist

When updating code from v3 to v4:

- [ ] Replace all `CR1` lifecycle references with `CR0` equivalents
- [ ] Remove `sw_trigger_enable` and `hw_trigger_enable` logic
- [ ] Update `auto_rearm_enable` from CR1[0] to CR8[2]
- [ ] Use `CR0.RUN_ARMED_TRIG` for atomic trigger operations
- [ ] Remove any two-write trigger sequences (CR1 then CR0)
- [ ] Update state assertions to expect edge-triggered auto-clear behavior

---

## Implementation Reference

### RTL Files (3-Layer FORGE)

| Layer | File | Responsibility |
|-------|------|----------------|
| 1 (TOP) | `DPD.vhd` | Extract CR0 bits, instantiate shim |
| 2 (SHIM) | `DPD_shim.vhd` | Edge detection, pulse stretch, sync gating, HVS |
| 3 (MAIN) | `DPD_main.vhd` | FSM logic, output generation |

### Python Constants

```python
# py_tools/dpd_constants.py

class CR0:
    # Bit positions
    FORGE_READY = 31      # R
    USER_ENABLE = 30      # U
    CLK_ENABLE = 29       # N
    CAMPAIGN_ENABLE = 28  # P (reserved)
    ARM_ENABLE = 2        # A
    FAULT_CLEAR = 1       # C (edge)
    SW_TRIGGER = 0        # T (edge)

    # Pre-built constants
    RUN = 0xE0000000
    RUN_ARMED = 0xE0000004
    RUN_ARMED_TRIG = 0xE0000005
    RUN_ARMED_CLEAR = 0xE0000006

class CR8:
    # Bit positions
    MONITOR_THRESHOLD_OFFSET = 16  # [31:16]
    AUTO_REARM_ENABLE = 2          # B (burst mode)
    MONITOR_EXPECT_NEGATIVE = 1
    MONITOR_ENABLE = 0
```

---

## Authoritative Sources

| Document | Purpose |
|----------|---------|
| `rtl/DPD-RTL.yaml` | Register specification (machine-readable) |
| `docs/api-v4.md` | This file - calling convention reference |
| `py_tools/dpd_constants.py` | Python constants (generated from YAML) |

All other documentation should reference these sources. Historic documents describing CR1-based lifecycle control are **obsolete**.

---

## Test Handoff Prompts

Use these prompts when updating tests to v4 API:

### Simulation Tests (tests/sim/)

```
Update the CocoTB simulation tests to use the v4.0 API:

1. Replace CR1-based lifecycle control with CR0:
   - arm_enable: CR0[2] not CR1[1]
   - sw_trigger: CR0[0] not CR1[5] (edge-triggered, auto-clear)
   - fault_clear: CR0[1] not CR1[2] (edge-triggered, auto-clear)

2. Remove sw_trigger_enable and hw_trigger_enable - they no longer exist

3. Use single atomic writes for trigger sequences:
   - Old: write CR1 (arm+enable), write CR0 (trigger)
   - New: write CR0 with RUN_ARMED_TRIG (0xE0000005)

4. Update auto_rearm_enable from CR1[0] to CR8[2]

5. Edge-triggered signals auto-clear after 4 cycles - tests should
   not depend on software clearing these bits

Reference: docs/api-v4.md, py_tools/dpd_constants.py
```

### Hardware Tests (tests/hw/)

```
Update the hardware tests to use the v4.0 API:

1. Use CR0 for all lifecycle control:
   - CR0.RUN (0xE0000000) - module enabled
   - CR0.RUN_ARMED (0xE0000004) - module armed
   - CR0.RUN_ARMED_TRIG (0xE0000005) - atomic trigger

2. Remove any two-step trigger sequences. The v4 API guarantees
   atomic trigger in a single set_control() call.

3. Update state polling to account for transient INITIALIZING state
   (state 0, 0.0V) which appears briefly after fault_clear.

4. auto_rearm_enable is now in CR8[2], not CR1[0]

5. Remove sw_trigger_enable and hw_trigger_enable references

Reference: docs/api-v4.md, py_tools/dpd_constants.py
```

---

## Related Documents

- [Network Register Sync](network-register-sync.md) - Why CR2-CR10 are sync-gated
- [HVS Encoding](hvs.md) - FSM state debugging via OutputC voltage
- [Hardware Debug Checklist](hardware-debug-checklist.md) - Debugging workflow
- [DPD-RTL.yaml](../rtl/DPD-RTL.yaml) - Machine-readable register spec

---

**Supersedes:** All previous CR1-based lifecycle documentation
**Last Updated:** 2025-11-26

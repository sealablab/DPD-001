---
created: 2025-11-29
modified: 2025-11-30 16:04:26
status: AUTHORITATIVE
accessed: 2025-11-30 16:04:26
---

# BOOT Subsystem HVS State Reference

This document provides the **authoritative** reference for all HVS (Hierarchical Voltage Signaling) state encodings in the BOOT subsystem. All pre-PROG modules (BOOT, BIOS, LOADER) use this unified encoding scheme.

## Pre-PROG Encoding Scheme

The pre-PROG HVS encoding uses **number-theory optimized** parameters for clean decoding:

| Parameter | Value | Description |
|-----------|-------|-------------|
| `DIGITAL_UNITS_PER_STATE` | **197** | ~30mV per state @ ±5V FS |
| `DIGITAL_UNITS_PER_STATUS` | **11** | ~1.7mV per status LSB |
| Max voltage | **~0.94V** | All pre-PROG states < 1.0V |

**Why these values?**
- Both 197 and 11 are **prime** and **coprime** (`gcd(197, 11) = 1`)
- Any `(S, T)` pair maps to a unique digital value (no collisions)
- Simple decoding via number theory: `D = S × 197 + T × 11`

## Complete State Table

### Global S-Value Allocation

| S Range | Context | States | Description |
|---------|---------|--------|-------------|
| 0-7 | **BOOT** | 8 | BOOT dispatcher states |
| 8-15 | **BIOS** | 8 | BIOS diagnostic states |
| 16-23 | **LOADER** | 8 | Buffer loader states |
| 24-31 | Reserved | 8 | Future pre-PROG contexts |

### BOOT States (S = 0-7)

| State Name | S | T | Digital | Voltage | Description |
|------------|---|---|---------|---------|-------------|
| `BOOT_P0` | 0 | 0 | 0 | 0.000V | Initial/Reset phase |
| `BOOT_P1` | 1 | 0 | 197 | 0.030V | Dispatcher ready |
| `BOOT_FAULT` | 2 | 0 | 394 | 0.060V | Boot-level fault (sign-flipped) |
| Reserved | 3-7 | - | 591-1456 | 0.090-0.222V | Future BOOT sub-states |

**BOOT State Transitions:**
```
BOOT_P0 ──[RUN]──► BOOT_P1 ──[RUNB]──► BIOS_ACTIVE
                          ├──[RUNL]──► LOAD_ACTIVE
                          ├──[RUNP]──► PROG_ACTIVE (one-way)
                          └──[RUNR]──► BOOT_P0
```

### BIOS States (S = 8-15)

| State Name | S | T | Digital | Voltage | Description |
|------------|---|---|---------|---------|-------------|
| `BIOS_IDLE` | 8 | 0 | 1576 | 0.240V | Entry state (transient) |
| `BIOS_RUN` | 9 | 0 | 1773 | 0.271V | Executing diagnostics |
| `BIOS_DONE` | 10 | 0 | 1970 | 0.301V | Complete, awaiting RET |
| `BIOS_FAULT` | 11 | 0 | 2167 | 0.331V | Error state (sign-flipped) |
| Reserved | 12-15 | - | 2364-3032 | 0.361-0.462V | Future BIOS sub-states |

**BIOS State Transitions:**
```
BIOS_IDLE ──[enable rise]──► BIOS_RUN ──[delay expires]──► BIOS_DONE ──[RET]──► BOOT_P1
                                │
                                └──[error]──► BIOS_FAULT
```

**Implementation Note:** BIOS immediately transitions `IDLE → RUN` on dispatch (1 cycle). Tests should expect `BIOS_RUN` (S=9) after `RUNB` command, not `BIOS_IDLE` (S=8).

### LOADER States (S = 16-23)

| State Name | S | T | Digital | Voltage | Description |
|------------|---|---|---------|---------|-------------|
| `LOAD_P0` | 16 | 0 | 3152 | 0.481V | Setup phase |
| `LOAD_P1` | 17 | 0 | 3349 | 0.511V | Transfer phase |
| `LOAD_P2` | 18 | 0 | 3546 | 0.541V | Validation phase |
| `LOAD_P3` | 19 | 0 | 3743 | 0.571V | Complete |
| `LOAD_FAULT` | 20 | 0 | 3940 | 0.601V | CRC mismatch (sign-flipped) |
| Reserved | 21-23 | - | 4137-4604 | 0.631-0.702V | Future LOADER sub-states |

**LOADER State Transitions:**
```
LOAD_P0 ──[setup strobe]──► LOAD_P1 ──[1024 words]──► LOAD_P2 ──[CRC OK]──► LOAD_P3 ──[RET]──► BOOT_P1
                                                              │
                                                              └──[CRC fail]──► LOAD_FAULT
```

## Oscilloscope Quick Reference

### Voltage Bands (500mV/div recommended)

```
 1.0V ┬─────────────────────────────────────────
      │                    [Reserved: 0.72-0.94V]
      │
 0.5V ├── LOADER band ─────────────────────────
      │  LOAD_P0=0.48V  LOAD_P1=0.51V
      │  LOAD_P2=0.54V  LOAD_P3=0.57V
      │
 0.25V├── BIOS band ───────────────────────────
      │  BIOS_IDLE=0.24V  BIOS_RUN=0.27V
      │  BIOS_DONE=0.30V
      │
 0.0V ├── BOOT band ───────────────────────────
      │  BOOT_P0=0.00V  BOOT_P1=0.03V
      │
-0.5V ├── FAULT (any negative) ────────────────
      │  Magnitude indicates last known state
 ─────┴─────────────────────────────────────────
```

### Visual State Identification

| Voltage Range | Context | Likely States |
|---------------|---------|---------------|
| ~0.00V | BOOT | P0 (reset/initial) |
| ~0.03V | BOOT | P1 (dispatcher ready) |
| 0.24-0.35V | BIOS | IDLE/RUN/DONE |
| 0.48-0.60V | LOADER | P0/P1/P2/P3 |
| **Negative** | **FAULT** | Sign flip indicates error |

## Encoding/Decoding Reference

### VHDL Constants (`forge_common_pkg.vhd`)

```vhdl
-- Pre-PROG HVS parameters
constant HVS_PRE_STATE_UNITS  : integer := 197;
constant HVS_PRE_STATUS_UNITS : real    := 11.0;

-- BOOT global S values
constant BOOT_HVS_S_P0    : natural := 0;
constant BOOT_HVS_S_P1    : natural := 1;
constant BOOT_HVS_S_FAULT : natural := 2;

-- BIOS global S values
constant BIOS_HVS_S_IDLE  : natural := 8;
constant BIOS_HVS_S_RUN   : natural := 9;
constant BIOS_HVS_S_DONE  : natural := 10;
constant BIOS_HVS_S_FAULT : natural := 11;

-- LOADER global S values
constant LOADER_HVS_S_P0    : natural := 16;
constant LOADER_HVS_S_P1    : natural := 17;
constant LOADER_HVS_S_P2    : natural := 18;
constant LOADER_HVS_S_P3    : natural := 19;
constant LOADER_HVS_S_FAULT : natural := 20;
```

### Python Constants (`py_tools/boot_constants.py`)

```python
# Pre-PROG HVS parameters
HVS_PRE_STATE_UNITS = 197
HVS_PRE_STATUS_UNITS = 11

# Encoding
def encode_pre_prog(S: int, T: int = 0) -> int:
    return (S * HVS_PRE_STATE_UNITS) + (T * HVS_PRE_STATUS_UNITS)

# Decoding
def decode_pre_prog(digital_value: int) -> tuple:
    for S in range(32):
        remainder = digital_value - (S * HVS_PRE_STATE_UNITS)
        if remainder >= 0 and remainder % HVS_PRE_STATUS_UNITS == 0:
            T = remainder // HVS_PRE_STATUS_UNITS
            if T <= 127:
                context = ["BOOT", "BIOS", "LOADER", "RESERVED"][S // 8]
                return (context, S, T)
    return ("UNKNOWN", None, None)
```

## Test Tolerances

| Test Type | Tolerance | Notes |
|-----------|-----------|-------|
| CocoTB (simulation) | ±150 digital units | ~23mV, direct signal access |
| Hardware (oscilloscope) | ±300mV | ADC noise + polling latency |

## Fault Detection

**Sign Flip Convention:** When `status_vector[7] = '1'`, the HVS output goes **negative**. The magnitude preserves the last known state for debugging.

| Observed | Meaning |
|----------|---------|
| Positive voltage | Normal operation |
| Negative voltage | FAULT condition |
| `-0.27V` | BIOS_RUN when fault occurred |
| `-0.54V` | LOAD_P2 (validation) when CRC failed |

## Related Documents

- [HVS-encoding-scheme.md](../HVS-encoding-scheme.md) - Number theory and design rationale
- [BOOT-FSM-spec.md](../BOOT-FSM-spec.md) - BOOT dispatcher FSM
- [LOAD-FSM-spec.md](../LOAD-FSM-spec.md) - LOADER protocol
- [hvs.md](../hvs.md) - General HVS documentation (DPD context)
- [boot-process-terms.md](../boot-process-terms.md) - Naming conventions

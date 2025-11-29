---
created: 2025-11-28
modified: 2025-11-28 17:08:22
status: AUTHORITATIVE
accessed: 2025-11-28 17:08:22
---
# Boot Process Terminology

This document defines the naming conventions and terminology for the BOOT subsystem and its related modules.

## Naming Conventions

### Module-Phase Notation

Each module uses a consistent `MODULE-Pn` notation where:
- **MODULE** = The subsystem name (BOOT, BIOS, LOAD)
- **P** = Phase (for system modules)
- **n** = Phase number (0, 1, 2, ...)

| Module | Prefix | Example | Meaning |
|--------|--------|---------|---------|
| BOOT | P (Phase) | `BOOT-P0`, `BOOT-P1` | Boot process phases |
| BIOS | P (Phase) | `BIOS-P0`, `BIOS-P1` | Diagnostic module phases |
| LOAD | P (Phase) | `LOAD-P0`, `LOAD-P1` | Buffer loader phases |
| PROG | S (Stage) | `PROG-S0`, `PROG-S1` | Application stages |

> **Note:** PROG uses **Stages** instead of **Phases** to distinguish user application states from system module phases. This prevents confusion when documentation refers to internal FSM states within the application context.

## Phase Definitions

### `BOOT-P0`: Initial Reset

The platform's initial state immediately after power-on or hard reset:
- All Control Registers (CRs) are zeroed by the Moku platform
- Reset and Clock signals are applied by the platform
- ENV_BBUFs are uninitialized (contain random data)

### `BOOT-P1`: Settled / RUN

The platform has stabilized and the RUN gate (CR0[31:29]) is set:
- ENV_BBUFs are zeroed during this transition
- BOOT-FSM dispatcher is active
- User can select one of four transitions via CR0[28:25]

> **User Experience:** The transition from `BOOT-P0` → `BOOT-P1` occurs when the user/driver sets the RUN bits, proving the platform has settled and a "head" (controller) is attached.

### `BIOS-P0`: BIOS Active

Control has been transferred to the BIOS diagnostic module:
- Generates known reference signals on OutputA/B/C
- Used for wiring and connection troubleshooting
- Can access ENV_BBUFs if pre-populated by LOADER
- Can return to `BOOT-P1` via RET command

### `LOAD-P0`: Loader Active

Control has been transferred to the Buffer Loader module:
- Populates ENV_BBUFs (0-4 × 4KB BRAM regions)
- Receives data from Python client via Control Registers
- Can return to `BOOT-P1` via RET command

### `PROG-S0`: Program Active

Control has been transferred to the main application:
- One-way handoff (no return to BOOT)
- Application handles its own FSM states (`PROG-S0`, `PROG-S1`, etc.)
- BOOT module no longer monitors or intercepts PROG behavior
- Application faults are handled by PROG, not BOOT

## Command Reference

| Command | CR0 Bits | Action |
|---------|----------|--------|
| `RUN` | CR0[31:29] = `111` | Transition BOOT-P0 → BOOT-P1 |
| `RUNP` | CR0[28] = `1` | Transfer to PROG (one-way) |
| `RUNB` | CR0[27] = `1` | Transfer to BIOS |
| `RUNL` | CR0[26] = `1` | Transfer to LOADER |
| `RUNR` | CR0[25] = `1` | Soft reset to BOOT-P0 |
| `RET` | CR0[24] = `1` | Return to BOOT-P1 (from BIOS/LOAD only) |

## Expert Workflow Example

```
BOOT-P0  ──[RUN]──►  BOOT-P1  ──[RUNL]──►  LOAD-P0
                                              │
                        ┌────────[RET]────────┘
                        ▼
                    BOOT-P1  ──[RUNB]──►  BIOS-P0
                                              │
                        ┌────────[RET]────────┘
                        ▼
                    BOOT-P1  ──[RUNP]──►  PROG-S0  (one-way)
```

This workflow allows:
1. Loading configuration data into ENV_BBUFs
2. Running diagnostics that may use the loaded data
3. Launching the application with pre-configured buffers

## Design Principles

### CR0 as Privileged Register

CR0 is treated as a privileged/special-case register:
- Application (PROG) logic should not access CR0 directly
- Boot-level control is managed by the Python client
- This separation ensures clean handoff semantics

### Decoupled Terminology

Boot process terminology is intentionally decoupled from application-specific names:
- Use "PROG" not "DPD" or "BPD" in boot context
- Application-specific naming belongs in application documentation
- This keeps the boot subsystem reusable across different applications

### Consistent FSM Structure

All modules (BOOT, BIOS, LOAD, PROG) use the canonical 6-bit FSM representation:
- Enables unified HVS debugging across all layers
- Standard state/status vector interface
- Reusable test infrastructure

## See Also

- [BOOT-FSM-spec](docs/BOOT-FSM-spec.md) - Detailed BOOT FSM specification
- [B000_BOOT](B000_BOOT.md) - BOOT module overview
- [B010_BIOS](B010_BIOS.md) - BIOS diagnostic module
- [B100_PROG](B100_PROG.md) - PROG application handoff

---
file: B1_BOOT_BIOS.vhd.md
type: rtl_md
author: jellch
created: 2025-11-28
modified: 2025-11-30 15:37:24
accessed: 2025-11-30 15:38:48
code_link: "[[rtl/boot/B1_BOOT_BIOS.vhd|B1_BOOT_BIOS.vhd]]"
doc_link: "[[rtl/boot/B1_BOOT_BIOS.vhd.md|B1_BOOT_BIOS.vhd.md]]"
self_link: "[[rtl/boot/B1_BOOT_BIOS.vhd.md|B1_BOOT_BIOS.vhd.md]]"
Descr: BIOS module stub for hardware validation - 3-state FSM with observable HVS transitions
tags:
  - BOOT
  - BIOS
---

# B1_BOOT_BIOS

> [!NOTE] Authoritative Source
> `/rtl/boot/B1_BOOT_BIOS.vhd` contains the actual code and should be treated as authoritative over this description.

> [!WARN] @JC @C #TODO
> This is a **validation stub** — not the full BIOS implementation. See todo: "Replace BIOS Stub with MVP Implementation"

BIOS module stub for hardware validation. Implements a minimal 3-state FSM (IDLE → RUN → DONE) that produces observable HVS voltage transitions on the oscilloscope.

## Overview

This is a **validation stub** — not the full BIOS implementation. It auto-advances through states with a configurable delay counter, allowing oscilloscope observation of state transitions during hardware bring-up.

## Control Flow

1. BOOT dispatcher sets `bios_enable` high (enters `BIOS_ACTIVE` state)
2. BIOS detects rising edge → transitions IDLE → RUN
3. Delay counter counts down in RUN state
4. Counter expires → transitions RUN → DONE, asserts `bios_complete`
5. BOOT issues RET → `bios_enable` goes low → BIOS resets to IDLE

## Observability

HVS encoding via parent's `forge_hierarchical_encoder`:
- **S=8** (BIOS_IDLE) — Entry state after dispatch
- **S=9** (BIOS_RUN) — Executing (visible for `RUN_DELAY_CYCLES`)
- **S=10** (BIOS_DONE) — Complete, waiting for RET
- **S=11** (BIOS_FAULT) — Error state (reserved)

---

## Implements

- [[docs/boot/BOOT-HW-VALIDATION-PLAN.md|BOOT-HW-VALIDATION-PLAN]] — validation test plan

## Dependencies (RTL)

| File | Purpose |
|------|---------|
| [[rtl/forge_common_pkg.vhd\|forge_common_pkg]] | BIOS_STATE_* constants |

---

## Entity

Standalone entity (not using BootWrapper pattern — this is a child module).

| Group | Ports | Type | Direction |
|-------|-------|------|-----------|
| Clock | `Clk`, `Reset` | `std_logic` | in |
| Control | `bios_enable` | `std_logic` | in |
| State | `state_vector` | `slv(5:0)` | out |
| State | `status_vector` | `slv(7:0)` | out |
| Control | `bios_complete` | `std_logic` | out |

## Generics
```vhdl
generic (
    BIOS_STUB_DELAY_CYCLES : natural := 125000  -- 1ms @ 125MHz
);
```

**Port descriptions:**
- **bios_enable** — high when BOOT state = BIOS_ACTIVE
- **state_vector** — current FSM state for HVS encoding
- **status_vector** — debug info; bit 7 = fault indicator
- **bios_complete** — asserted when in DONE state

---

## Architecture

Architecture: `rtl of B1_BOOT_BIOS`

### Key Processes

- **Enable Edge Detection** — detects fresh dispatch via rising edge of `bios_enable`
- **FSM State Register** — synchronous state update, resets to IDLE when disabled
- **FSM Next State Logic** — combinatorial transitions
- **Delay Counter** — counts down from `RUN_DELAY_CYCLES` in RUN state

### FSM Summary

```
    ┌──────────┐  enable_rise  ┌──────────┐  counter=0  ┌──────────┐
    │ BIOS_IDLE│──────────────▶│ BIOS_RUN │────────────▶│ BIOS_DONE│
    └──────────┘               └──────────┘             └──────────┘
         ▲                                                   │
         │              bios_enable = '0' (RET)              │
         └───────────────────────────────────────────────────┘
```

### Outputs

| State | bios_complete | status[7] |
|-------|---------------|-----------|
| IDLE  | 0 | 0 |
| RUN   | 0 | 0 |
| DONE  | 1 | 0 |
| FAULT | 0 | 1 |

---

## Configuration

```vhdl
generic (
    BIOS_STUB_DELAY_CYCLES : natural := 125000  -- 1ms @ 125MHz for HW scope
);
```

> [!warning] Timing for Test Environment
> - **CocoTB sim**: Use small value (e.g., 10) for fast tests
> - **Hardware scope**: Use 125000 (1ms) for observable transitions
> - Set via generic map in [[rtl/boot/B0_BOOT_TOP.vhd|B0_BOOT_TOP]] instantiation

---

# See Also

- [[rtl/boot/B0_BOOT_TOP.vhd.md|B0_BOOT_TOP]] — parent dispatcher
- [[rtl/forge_common_pkg.vhd.md|forge_common_pkg]] — state constants
- [[docs/boot/BOOT-HVS-state-reference.md|BOOT-HVS-state-reference]] — **authoritative** HVS state table
- [[docs/BIOS-FSM-spec.md|BIOS-FSM-spec]] — FSM specification
- [[docs/boot/BOOT-HW-VALIDATION-PLAN.md|BOOT-HW-VALIDATION-PLAN]] — test plan
- [[docs/hvs.md|HVS]] — voltage encoding scheme

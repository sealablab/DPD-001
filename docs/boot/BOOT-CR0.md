---
created: 2025-11-30
modified: 2025-11-30 18:34:30
status: AUTHORITATIVE
accessed: 2025-11-30 18:54:56
---

# BOOT_CR0 Register Specification

**BOOT_CR0** is the 32-bit privileged control register that governs BOOT subsystem operation. This document is the **authoritative** reference for all `BOOT_CR0` bit allocations.

> [!IMPORTANT] Convention
> **`BOOT_CR0` is always mapped to Moku CloudCompile's `Control0`** (i.e., `set_control(0, value)`).
>
> This register has a **different bit layout** than application-level registers (`AppReg`) used by PROG applications like DPD. The BOOT_CR0 layout is only valid during BOOT/BIOS/LOADER phases.

## Bit Allocation Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│                           BOOT_CR0 (32 bits)                           │
├────────┬────────┬────────┬────────┬────────┬────────┬────────┬────────┤
│ 31  30 │ 29  28 │ 27  26 │ 25  24 │ 23  22 │ 21  20 │ 19..17 │ 16..0  │
├────────┼────────┼────────┼────────┼────────┼────────┼────────┼────────┤
│  R   U │  N   P │  B   L │  R  RET│BANK_SEL│STB DIV │DIV_SEL │ Rsvd   │
│  └──RUN gate──┘ │  └─Module Sel─┘ │(global)│        │        │        │
└────────┴────────┴────────┴────────┴────────┴────────┴────────┴────────┘
```

## Bit Field Reference

### RUN Gate [31:29] — System Enable

All three bits must be `1` for the BOOT subsystem to operate. Default all-zero state keeps everything disabled (safe power-on default).

| Bit | Name | Description |
|-----|------|-------------|
| 31 | **R** (Ready) | Platform has settled, ready for operation |
| 30 | **U** (User) | User/driver enables operation |
| 29 | **N** (clkEnable) | Clock domain is stable |

```vhdl
-- VHDL usage pattern
run_active <= BOOT_CR0(31) and BOOT_CR0(30) and BOOT_CR0(29);
```

**Transition:** `BOOT_P0 → BOOT_P1` requires `BOOT_CR0[31:29] = "111"`

### Module Select [28:25] — Dispatcher Target

Exactly **one** bit should be set to select a module. Multiple bits handled according to priority below

| Bit | Name | Command | Description |
|-----|------|---------|-------------|
| 28 | **P** (Program) | `RUNP` | Transfer to PROG (one-way, no return) |
| 27 | **B** (BIOS) | `RUNB` | Transfer to BIOS diagnostics |
| 26 | **L** (Loader) | `RUNL` | Transfer to LOADER |
| 25 | **R** (Reset) | `RUNR` | Soft reset to BOOT_P0 |

**Priority (if hardware encoder):**  `R > L > B > P `
NOTE: Reset outranks Loader outranks BIOS outranks Program (if multiple bits are set they should be handled in this order)

### RET [24] — Return Control

| Bit | Name | Description |
|-----|------|-------------|
| 24 | **RET** | Return from BIOS/LOADER to BOOT_P1 |

> [!WARNING] PROG Cannot Return
> Once control transfers to PROG via `RUNP`, there is no return path. The `RET` bit is ignored in PROG_ACTIVE state.

### ENV_BBUF Control [23:21] — Global Buffer Access

| Bit(s) | Name | Description |
|--------|------|-------------|
| 23:22 | **BANK_SEL** | Global active buffer selector (0-3) |
| 21 | **STROBE** | LOADER data strobe (falling edge triggers parallel write) |

#### BANK_SEL — Global Buffer Selector

**BANK_SEL** is a **global** 2-bit field shared by all modules (BOOT, BIOS, LOADER, PROG). It selects which of the four ENV_BBUF regions is "active" for read operations.

| BANK_SEL | Active Buffer |
|----------|---------------|
| `00` | ENV_BBUF_0 |
| `01` | ENV_BBUF_1 |
| `10` | ENV_BBUF_2 |
| `11` | ENV_BBUF_3 |

**Design Decision:** The system always has exactly **4 buffers**. There is no variable buffer count — LOADER always writes all 4 buffers in parallel.

#### STROBE — LOADER Write Trigger

During LOAD_ACTIVE state, falling edge on STROBE triggers a parallel write:
- CR1 → ENV_BBUF_0[offset]
- CR2 → ENV_BBUF_1[offset]
- CR3 → ENV_BBUF_2[offset]
- CR4 → ENV_BBUF_3[offset]

If fewer than 4 buffers contain meaningful data, the client simply zero-fills the unused CR registers.

### Clock Divider [20:17] — (PROPOSED)

| Bit(s) | Name | Description |
|--------|------|-------------|
| 20:17 | **CLK_DIV_SEL** | Clock divider select (0000=/1 ... 1111=/32768) |
| 16 | **CLK_DIV_BYPASS** | LOADER bypasses divider (preserves blind handshake timing) |

> [!NOTE] Status: PROPOSED
> Clock divider bits are specified in [BOOT-ROM-WAVES-prop.md](BOOT-ROM-WAVES-prop.md) but not yet implemented.

### Reserved [15:0]

Reserved for future use. Should be written as `0`.

## Command Constants

| Command | Hex Value | Binary [31:24] | Action |
|---------|-----------|----------------|--------|
| `CMD_RUN` | `0xE0000000` | `1110 0000` | Enable RUN gate only |
| `CMD_RUNP` | `0xF0000000` | `1111 0000` | RUN + select PROG |
| `CMD_RUNB` | `0xE8000000` | `1110 1000` | RUN + select BIOS |
| `CMD_RUNL` | `0xE4000000` | `1110 0100` | RUN + select LOADER |
| `CMD_RUNR` | `0xE2000000` | `1110 0010` | RUN + soft reset |
| `CMD_RET` | `0xE1000000` | `1110 0001` | RUN + return to dispatcher |

### Python Usage

```python
from py_tools.boot_constants import CMD

# Enable BOOT subsystem
mcc.set_control(0, CMD.RUN)        # 0xE0000000

# Launch LOADER to populate buffers
mcc.set_control(0, CMD.RUNL)       # 0xE4000000

# Return to dispatcher
mcc.set_control(0, CMD.RET)        # 0xE1000000

# Launch application (one-way)
mcc.set_control(0, CMD.RUNP)       # 0xF0000000
```

### VHDL Constants

```vhdl
-- From forge_common_pkg.vhd
constant CMD_RUN  : std_logic_vector(31 downto 0) := x"E0000000";
constant CMD_RUNP : std_logic_vector(31 downto 0) := x"F0000000";
constant CMD_RUNB : std_logic_vector(31 downto 0) := x"E8000000";
constant CMD_RUNL : std_logic_vector(31 downto 0) := x"E4000000";
constant CMD_RUNR : std_logic_vector(31 downto 0) := x"E2000000";
constant CMD_RET  : std_logic_vector(31 downto 0) := x"E1000000";
```

## Bit Position Constants

### VHDL (forge_common_pkg.vhd)

```vhdl
-- RUN Gate
constant RUN_READY_BIT : natural := 31;  -- R
constant RUN_USER_BIT  : natural := 30;  -- U
constant RUN_CLK_BIT   : natural := 29;  -- N
constant RUN_GATE_MASK : std_logic_vector(31 downto 0) := x"E0000000";

-- Module Select
constant SEL_PROG_BIT   : natural := 28;  -- P
constant SEL_BIOS_BIT   : natural := 27;  -- B
constant SEL_LOADER_BIT : natural := 26;  -- L
constant SEL_RESET_BIT  : natural := 25;  -- R

-- Return Control
constant RET_BIT : natural := 24;

-- ENV_BBUF Control (Global)
constant BANK_SEL_HI   : natural := 23;
constant BANK_SEL_LO   : natural := 22;
constant LOADER_STROBE_BIT : natural := 21;
```

### Python (py_tools/boot_constants.py)

```python
# RUN Gate
BOOT_CR0_RUN_READY_BIT = 31
BOOT_CR0_RUN_USER_BIT  = 30
BOOT_CR0_RUN_CLK_BIT   = 29
BOOT_CR0_RUN_GATE_MASK = 0xE0000000

# Module Select
BOOT_CR0_SEL_PROG_BIT   = 28
BOOT_CR0_SEL_BIOS_BIT   = 27
BOOT_CR0_SEL_LOADER_BIT = 26
BOOT_CR0_SEL_RESET_BIT  = 25

# Return Control
BOOT_CR0_RET_BIT = 24

# ENV_BBUF Control (Global)
BOOT_CR0_BANK_SEL_HI   = 23
BOOT_CR0_BANK_SEL_LO   = 22
BOOT_CR0_LOADER_STROBE_BIT = 21
```

## Helper Functions

### VHDL

```vhdl
-- Check if RUN gate is fully enabled
function is_run_active(cr0 : std_logic_vector(31 downto 0)) return boolean;

-- Check if exactly one module select bit is set
function is_valid_select(cr0 : std_logic_vector(31 downto 0)) return boolean;

-- Extract active buffer bank (0-3)
function get_bank_sel(cr0 : std_logic_vector(31 downto 0)) return natural;
```

### Python

```python
def is_run_active(cr0: int) -> bool:
    """Check if all RUN gate bits are set."""
    return (cr0 & BOOT_CR0_RUN_GATE_MASK) == BOOT_CR0_RUN_GATE_MASK

def get_bank_sel(cr0: int) -> int:
    """Extract active buffer bank (0-3)."""
    return (cr0 >> BOOT_CR0_BANK_SEL_LO) & 0x3

def set_bank_sel(cr0: int, bank: int) -> int:
    """Set the active buffer bank (0-3), preserving other bits."""
    mask = 0x3 << BOOT_CR0_BANK_SEL_LO
    return (cr0 & ~mask) | ((bank & 0x3) << BOOT_CR0_BANK_SEL_LO)
```

## BOOT_CR0 vs AppReg

| Aspect | BOOT_CR0 | AppReg |
|--------|----------|--------|
| **Context** | BOOT/BIOS/LOADER phases | PROG applications (DPD, etc.) |
| **Hardware** | Control0 | Control0-15 |
| **Bit layout** | RUN/Module/RET/LOADER | Application-specific |
| **Authoritative doc** | This document | Application docs (e.g., api-v4.md) |

After `RUNP` handoff to PROG, the application takes ownership of Control0 and may use a completely different bit layout (e.g., DPD uses CR0[31:29] for FORGE control, CR0[2:0] for arm/fault/trigger).

## State Machine Integration

The BOOT_CR0 register drives FSM transitions in:

- **B0_BOOT_TOP** — Dispatcher FSM reads RUN gate and module select
- **B1_BOOT_BIOS** — Reads RET bit for return transition
- **L2_BUFF_LOADER** — Reads BUFCNT and STROBE for buffer operations

See [BOOT-FSM-spec.md](../BOOT-FSM-spec.md) for complete state machine documentation.

## See Also

- [BOOT-FSM-spec.md](../BOOT-FSM-spec.md) — BOOT state machine (uses BOOT_CR0)
- [BIOS-FSM-spec.md](../BIOS-FSM-spec.md) — BIOS state machine
- [LOAD-FSM-spec.md](../LOAD-FSM-spec.md) — LOADER protocol
- [forge_common_pkg.vhd](../../rtl/forge_common_pkg.vhd) — VHDL constants
- [boot_constants.py](../../py_tools/boot_constants.py) — Python constants
- [BOOT-HVS-state-reference.md](BOOT-HVS-state-reference.md) — HVS state encoding
- [BOOT-ROM-WAVES-prop.md](BOOT-ROM-WAVES-prop.md) — CLK_DIV proposal

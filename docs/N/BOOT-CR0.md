---
type: N
created: 2025-11-30
modified: 2025-11-30
---

# BOOT_CR0 Quick Reference

**BOOT_CR0** — 32-bit privileged control register for BOOT/BIOS/LOADER phases.

> [!WARNING] Convention
> **`BOOT_CR0` ≡ Moku CloudCompile `Control0`** during boot phases.
> After `RUNP` handoff, the application owns Control0 with its own bit layout (`AppReg`).

## Authoritative Specification

**→ [BOOT-CR0.md](../boot/BOOT-CR0.md)** (AUTHORITATIVE)

## Bit Map

```
BOOT_CR0[31:0]
┌─────┬─────┬─────┬─────┬─────┬─────┬─────┬──────┐
│31-29│28-25│  24 │23-22│  21 │20-17│  16 │ 15-0 │
├─────┼─────┼─────┼─────┼─────┼─────┼─────┼──────┤
│ RUN │ SEL │ RET │BUFC │ STB │ DIV │ BYP │ Rsvd │
└─────┴─────┴─────┴─────┴─────┴─────┴─────┴──────┘
```

| Field | Bits | Description |
|-------|------|-------------|
| **RUN** | [31:29] | RUN gate: R/U/N must all be `1` |
| **SEL** | [28:25] | Module select: P/B/L/R (one-hot) |
| **RET** | [24] | Return to BOOT_P1 |
| **BUFCNT** | [23:22] | LOADER buffer count |
| **STROBE** | [21] | LOADER data strobe |
| **DIV** | [20:17] | Clock divider (proposed) |
| **BYP** | [16] | LOADER bypass divider (proposed) |

## Command Cheat Sheet

| Command | Value | Action |
|---------|-------|--------|
| `CMD_RUN` | `0xE0000000` | Enable RUN gate |
| `CMD_RUNP` | `0xF0000000` | → PROG (one-way) |
| `CMD_RUNB` | `0xE8000000` | → BIOS |
| `CMD_RUNL` | `0xE4000000` | → LOADER |
| `CMD_RUNR` | `0xE2000000` | → BOOT_P0 (soft reset) |
| `CMD_RET` | `0xE1000000` | Return to dispatcher |

## Quick Usage

```python
from py_tools.boot_constants import CMD

mcc.set_control(0, CMD.RUN)   # Enable boot
mcc.set_control(0, CMD.RUNL)  # Load buffers
mcc.set_control(0, CMD.RET)   # Return
mcc.set_control(0, CMD.RUNP)  # Launch app (no return)
```

## See Also

- [BOOT-CR0.md](../boot/BOOT-CR0.md) — **Authoritative** full specification
- [BOOT-FSM-spec.md](../BOOT-FSM-spec.md) — State machine using BOOT_CR0
- [forge_common_pkg.vhd](../../rtl/forge_common_pkg.vhd) — VHDL constants

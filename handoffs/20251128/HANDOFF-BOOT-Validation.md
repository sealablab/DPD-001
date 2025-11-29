---
created: 2025-11-28
session: Branch cleanup + BOOT migration
next_session: BOOT compilation fixes + test validation
branch: main
---
# Session Handoff: BOOT Compilation & Test Validation

## What We Did This Session

1. **Cleaned up git branches** - Deleted stale `claude/review-loader-plan-*` branches (local + remote)
2. **Merged web-client work** - Phases 2-4 of LOADER implementation were done by web client after PR merge
3. **Migrated tests** - Moved `boot_tests/` → `tests/sim/{boot_fsm,loader}/`, updated imports
4. **Updated handoff docs** - Removed stale Phase 2 handoff, updated status

## Current State

```
Branch: main (clean, pushed)
All BOOT RTL and tests are in place but NOT yet validated
```

## Files Added/Modified

```
rtl/boot/
├── B0_BOOT_TOP.vhd           # BOOT dispatcher (6-state FSM)
├── L2_BUFF_LOADER.vhd        # LOADER FSM (5-state) with CRC
├── loader_crc16.vhd          # Pure combinatorial CRC-16
├── BootWrapper_test_stub.vhd # CocoTB entity stub

tests/sim/
├── boot_fsm/P1_basic.py      # 6 tests for BOOT dispatcher
└── loader/P1_basic.py        # 4 tests for LOADER FSM
```

## Known Issue: Compilation Conflict

When compiling BOOT RTL, there's an entity collision:

```
rtl/CustomWrapper_test_stub.vhd      # DPD's CustomWrapper entity
rtl/boot/BootWrapper_test_stub.vhd   # BOOT's CustomWrapper entity (same name!)
```

Both declare `entity CustomWrapper` - GHDL gets confused when both are in the work library.

**Possible fixes:**
1. Rename BOOT's entity to `BootWrapper` and update `B0_BOOT_TOP.vhd` architecture binding
2. Use separate GHDL libraries for DPD vs BOOT
3. Compile only one at a time (clean between)

## Next Session Tasks

### 1. Fix BOOT Compilation
- Resolve the CustomWrapper entity collision
- Get `ghdl -a` to succeed on all BOOT files

### 2. Run BOOT Tests
- Update `tests/sim/run.py` or Makefile to support BOOT tests
- Run `boot_fsm/P1_basic.py` and `loader/P1_basic.py`
- Fix any test failures

### 3. (Optional) Update Makefile
Current Makefile only handles DPD. May want to add BOOT targets:
```makefile
compile-dpd:
    ghdl -a $(DPD_FILES)

compile-boot:
    ghdl -a $(BOOT_FILES)
```

## Context Loading for Next Session

@CLAUDE: Read these files:

```
# RTL to fix
@rtl/boot/BootWrapper_test_stub.vhd
@rtl/boot/B0_BOOT_TOP.vhd

# For reference (working DPD pattern)
@rtl/CustomWrapper_test_stub.vhd

# Tests to run
@tests/sim/boot_fsm/P1_basic.py
@tests/sim/loader/P1_basic.py

# Test runner
@tests/sim/run.py
```

## Quick Reference

### BOOT States (HVS @ 0.2V/state = 1311 units)
| State | Digital | Voltage |
|-------|---------|---------|
| BOOT_P0 | 0 | 0.0V |
| BOOT_P1 | 1311 | 0.2V |
| BIOS_ACTIVE | 2622 | 0.4V |
| LOAD_ACTIVE | 3933 | 0.6V |
| PROG_ACTIVE | 5244 | 0.8V |
| FAULT | negative | <0V |

### CR0 Commands
```
CMD.RUN  = 0xE0000000  # RUN gate only → BOOT_P1
CMD.RUNL = 0xE4000000  # Enter LOADER
CMD.RUNB = 0xE8000000  # Enter BIOS
CMD.RUNP = 0xF0000000  # Enter PROG (one-way)
CMD.RUNR = 0xE2000000  # Soft reset to P0
```

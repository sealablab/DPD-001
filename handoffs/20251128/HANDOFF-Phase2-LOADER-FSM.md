---
created: 2025-11-28
updated: 2025-11-28
session: Post-Thanksgiving - Phases 2-4 COMPLETE
next_session: BOOT test validation and PROG integration
branch: main
status: PHASES 1-4 COMPLETE
---
# Session Handoff: BOOT Subsystem Implementation

## Status: PHASES 1-4 COMPLETE ✅

The web client continued working after the initial PR merge and completed Phases 2-4.
We merged that work and migrated tests to the proper location.

## What's Done

| Phase | Deliverable | Status |
|-------|-------------|--------|
| 1 | `loader_crc16.vhd` + `boot_constants.py` | ✅ Complete |
| 2 | `L2_BUFF_LOADER.vhd` - 5-state LOADER FSM | ✅ Complete |
| 3 | `B0_BOOT_TOP.vhd` - 6-state BOOT dispatcher | ✅ Complete |
| 3 | `BootWrapper_test_stub.vhd` - CocoTB entity | ✅ Complete |
| 4 | `tests/sim/boot_fsm/P1_basic.py` | ✅ Migrated |
| 4 | `tests/sim/loader/P1_basic.py` | ✅ Migrated |

## Current State

```
Branch: main (clean, pushed)
Tests: tests/sim/boot_fsm/, tests/sim/loader/
RTL: rtl/boot/{B0_BOOT_TOP.vhd, L2_BUFF_LOADER.vhd, loader_crc16.vhd, BootWrapper_test_stub.vhd}
```

## Next Steps

### Immediate (Validation)
1. **Compile BOOT RTL** - Verify VHDL syntax is correct
2. **Run BOOT tests** - Check if tests pass against simulation
3. **Fix any issues** - The web client code may have bugs

### Later (Integration)
1. **Wire up PROG** - B0_BOOT_TOP has stubs for PROG outputs, connect DPD_shim
2. **BIOS implementation** - B1_BOOT_BIOS.vhd is a stub
3. **Python CLI** - boot_cli.py for interactive loading

## Files in rtl/boot/

```
B0_BOOT_TOP.vhd          # BOOT dispatcher (6-state FSM) - CustomWrapper architecture
L2_BUFF_LOADER.vhd       # LOADER FSM (5-state) with CRC validation
loader_crc16.vhd         # Pure combinatorial CRC-16-CCITT
BootWrapper_test_stub.vhd # Entity declaration for CocoTB
B1_BOOT_BIOS.vhd         # BIOS stub (future)
P3_PROG_START.vhd        # PROG stub (future)
```

## Key Technical Details

### CR0 Bit Allocation
```
CR0[31:29] = RUN gate (R/U/N) - must all be '1'
CR0[28]    = P (Program)   - RUNP
CR0[27]    = B (BIOS)      - RUNB
CR0[26]    = L (Loader)    - RUNL
CR0[25]    = R (Reset)     - RUNR
CR0[24]    = RET           - Return to BOOT_P1
CR0[23:22] = Buffer count  - LOADER (00=1, 01=2, 10=3, 11=4)
CR0[21]    = Data strobe   - LOADER (falling edge triggers)
```

### HVS Encoding
- **BOOT**: 1311 units/state (0.2V steps) - keeps all 6 states in 0-1V range
- **DPD/PROG**: 3277 units/state (0.5V steps)

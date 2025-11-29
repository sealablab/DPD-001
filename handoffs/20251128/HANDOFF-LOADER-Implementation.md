---
created: 2025-11-28
session: Thanksgiving 2025 - BOOT Subsystem Specification
next_session: LOADER Implementation
branch: feature/LOADER
---
# Session Handoff: LOADER Implementation

## What We Accomplished

This session we designed and documented the complete BOOT subsystem specification:

1. **BOOT-FSM-spec.md** (AUTHORITATIVE) - 6-state BOOT dispatcher FSM
2. **boot-process-terms.md** (AUTHORITATIVE) - Naming conventions and terminology
3. **LOAD-FSM-spec.md** (AUTHORITATIVE) - LOADER module specification
4. **forge_common_pkg.vhd** - Rewritten as single source of truth for CR0 definitions
5. **LOADER-implementation-plan.md** - Implementation roadmap

## Current Branch State

```
Branch: feature/LOADER (3 commits ahead of main)
Last commit: 364eff9 - docs: update LOADER implementation plan with shared package references
```

## Context Loading Instructions

@CLAUDE: To resume this work, read these files in order:

### 1. Authoritative Specifications (docs/)
```
@docs/BOOT-FSM-spec.md
@docs/boot-process-terms.md
@docs/bootup-proposal/LOAD-FSM-spec.md
```

### 2. Shared Package (CRITICAL - single source of truth)
```
@rtl/forge_common_pkg.vhd
```

### 3. Implementation Plan
```
@docs/bootup-proposal/LOADER-implementation-plan.md
```

### 4. Existing Stubs (to be implemented)
```
@rtl/boot/L2_BUFF_LOADER.vhd
@rtl/boot/README.md
```

## CR0 Bit Allocation (Quick Reference)

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

## Next Session Tasks

### Priority 1: CRC-16 Module
- [ ] Create `rtl/boot/loader_crc16.vhd`
- [ ] Pure combinatorial CRC-16-CCITT calculator
- [ ] Use `CRC16_POLYNOMIAL` and `CRC16_INIT` from `forge_common_pkg`

### Priority 2: LOADER FSM
- [ ] Implement `rtl/boot/L2_BUFF_LOADER.vhd` (replace stub)
- [ ] 5-state FSM: LOAD_P0, LOAD_P1, LOAD_P2, LOAD_P3, FAULT
- [ ] Falling edge strobe detection
- [ ] Parallel BRAM writes to ENV_BBUFs

### Priority 3: CocoTB Tests
- [ ] Create `tests/sim/loader/` package
- [ ] P1 basic tests (state transitions)
- [ ] P2 CRC validation tests

### Priority 4: Python CLI
- [ ] Create `py_tools/boot_constants.py` (mirror of forge_common_pkg.vhd)
- [ ] Create `py_tools/boot_cli.py` (RUN> shell)
- [ ] Create `py_tools/boot_loader.py` (LOADER protocol)

## Open Questions (Carry Forward)

1. **ENV_BBUF BRAM instantiation**: Should BOOT module own the BRAMs, or TOP level?
2. **State persistence**: Reset LOADER state on RUNR?
3. **Multiple load cycles**: RUNL → load → RET → RUNL → load again? (Spec says yes)
4. **Timeout**: Watchdog if Python client disappears mid-transfer?

## Key Design Decisions Made

1. **Blind handshake protocol** - No feedback path except HVS on OutputC
2. **Falling edge strobe** - More robust than rising edge
3. **Parallel BRAM writes** - All 4 buffers share same offset pointer
4. **CRC-16-CCITT** - Simple, sufficient for detecting bit flips
5. **Generous timing** - 1ms/word (~1s per 4KB buffer), reliability over speed
6. **Compressed HVS range** - 0.2V steps (1311 units) for BOOT, keeps states in 0-1V

## Files Modified This Session

```
docs/BOOT-FSM-spec.md                    (NEW - authoritative)
docs/boot-process-terms.md               (NEW - authoritative)
docs/bootup-proposal/LOAD-FSM-spec.md    (NEW - authoritative)
docs/bootup-proposal/LOADER-implementation-plan.md (NEW)
rtl/forge_common_pkg.vhd                 (REWRITTEN - authoritative)
```

## Git Commands to Resume

```bash
# Check current state
git status
git log --oneline -5

# If on main, switch to feature branch
git checkout feature/LOADER

# If starting fresh implementation
git checkout -b feature/LOADER-impl
```

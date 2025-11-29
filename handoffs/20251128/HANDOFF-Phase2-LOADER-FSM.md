---
created: 2025-11-28
session: Post-Thanksgiving Cleanup & Phase 1 Complete
next_session: Phase 2 - LOADER FSM Implementation
branch: main
---
# Session Handoff: Phase 2 - LOADER FSM Implementation

## What We Accomplished This Session

1. **Reviewed and refined LOADER implementation plan** through interactive Q&A
2. **Completed Phase 1**: Created `loader_crc16.vhd` and `boot_constants.py`
3. **Fixed repo issues**: `tests/lib/` gitignore, merged moku_md docs
4. **Resolved key architectural decisions** (documented below)
5. **Updated all plan documentation** to reflect resolved decisions

## Git State

```
Branch: main (clean)
Last commit: 02671b0 - gitignore: add **/.claude/ for nested claude settings
```

All Phase 1 deliverables are merged to main.

## Context Loading Instructions

@CLAUDE: Read these files in order:

### 1. Authoritative Specifications
```
@docs/bootup-proposal/BOOT-FSM-spec.md
@docs/bootup-proposal/LOAD-FSM-spec.md
@docs/bootup-proposal/boot-process-terms.md
```

### 2. Implementation References
```
@rtl/forge_common_pkg.vhd        # CR0 bit definitions (AUTHORITATIVE)
@rtl/boot/loader_crc16.vhd       # Phase 1 deliverable (COMPLETE)
@py_tools/boot_constants.py      # Python mirror of forge_common_pkg
```

### 3. Stubs to Implement
```
@rtl/boot/L2_BUFF_LOADER.vhd     # Phase 2 target - LOADER FSM
@rtl/boot/B0_BOOT_TOP.vhd        # Phase 3 target - BOOT dispatcher
```

### 4. Test Infrastructure Reference
```
@tests/README.md                 # Test structure overview
@tests/lib/                      # Existing test library
@tests/adapters/base.py          # StateReader to make configurable
```

## Resolved Design Decisions

| Decision | Resolution |
|----------|------------|
| BOOT architecture | Single-layer B0_BOOT_TOP (not 3-layer like DPD) |
| BRAM style | Inferred (not Xilinx primitives) |
| BRAM ownership | BOOT module owns ENV_BBUFs (synthesized as TOP) |
| Test location | `tests/sim/boot_fsm/` and `tests/sim/loader/` (not separate boot_tests/) |
| Timeout/watchdog | None - Python client responsible for completing transfer |
| PROG handoff | BOOT instantiates DPD_shim directly |
| StateReader | Make configurable with `units_per_state` parameter |
| Test stub | Create separate `BootWrapper_test_stub.vhd` |

## Implementation Phases

### Phase 1: CRC-16 Module ✅ COMPLETE
- [x] `rtl/boot/loader_crc16.vhd` - Pure combinatorial CRC-16-CCITT
- [x] `py_tools/boot_constants.py` - Python mirror of forge_common_pkg

### Phase 2: LOADER FSM (NEXT)
- [ ] Implement `rtl/boot/L2_BUFF_LOADER.vhd` (replace stub)
- [ ] 5-state FSM: LOAD_P0, LOAD_P1, LOAD_P2, LOAD_P3, FAULT
- [ ] Falling edge strobe detection on CR0[21]
- [ ] Parallel BRAM writes to 4x ENV_BBUFs
- [ ] CRC accumulation using loader_crc16

### Phase 3: BOOT_TOP + Integration
- [ ] Implement `B0_BOOT_TOP.vhd` (6-state dispatcher)
- [ ] Create `BootWrapper_test_stub.vhd` for CocoTB
- [ ] Instantiate DPD_shim as PROG module
- [ ] Wire HVS encoder with BOOT_HVS_UNITS_PER_STATE (1311)

### Phase 4: Test Infrastructure
- [ ] Add `tests/lib/boot_hw.py` (imports boot_constants.py)
- [ ] Update `tests/adapters/base.py` (configurable units_per_state)
- [ ] Create `tests/sim/boot_fsm/` and `tests/sim/loader/`
- [ ] Create `py_tools/boot_cli.py` (RUN> shell)

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
- **DPD**: 3277 units/state (0.5V steps)
- **BOOT**: 1311 units/state (0.2V steps) - keeps all 6 states in 0-1V range

### LOADER Protocol Summary
1. RUNL → LOAD_P0 (setup phase)
2. Setup strobe: latch buffer count from CR0[23:22], CRCs from CR1-CR4
3. Data strobes: 1024 falling edges on CR0[21], data from CR1-CR4
4. Auto-transition to LOAD_P2 (validate CRCs)
5. CRC match → LOAD_P3, mismatch → FAULT
6. RET → BOOT_P1

## Files Modified This Session

```
rtl/boot/loader_crc16.vhd                    (NEW - Phase 1)
py_tools/boot_constants.py                   (NEW - Phase 1)
docs/bootup-proposal/LOADER-implementation-plan.md (UPDATED)
handoffs/20251128/HANDOFF-LOADER-Implementation.md (UPDATED)
tests/README.md                              (UPDATED)
.gitignore                                   (FIXED - lib/ anchor)
```

## Notes for Next Session

1. Start with Phase 2: L2_BUFF_LOADER.vhd implementation
2. Key VHDL patterns needed:
   - Falling edge detection: `strobe_prev and not strobe_curr`
   - Parallel BRAM writes with generate statement
   - CRC accumulation per buffer
3. Reference `rtl/DPD_main.vhd` for FSM style conventions
4. Reference `rtl/DPD_shim.vhd` for edge detection pattern

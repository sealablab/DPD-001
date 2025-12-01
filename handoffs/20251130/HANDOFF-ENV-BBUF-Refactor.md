---
created: 2025-11-30
status: COMPLETE
branch: chore/BOOT_Cleanup
---

# ENV_BBUF Refactor Handoff

## Summary

Completed the migration of ENV_BBUF ownership from L2_BUFF_LOADER to B0_BOOT_TOP per the design in `docs/boot/BBUF-ALLOCATION-DRAFT.md`.

## Changes Made

### RTL Changes

| File | Changes |
|------|---------|
| `rtl/boot/B0_BOOT_TOP.vhd` | Added 4x4KB BRAM arrays, zeroing FSM, BANK_SEL read mux, LOADER write interface |
| `rtl/boot/L2_BUFF_LOADER.vhd` | Removed internal BRAMs, added `wr_data_0-3`, `wr_addr`, `wr_we` output ports |
| `rtl/forge_common_pkg.vhd` | Added `BANK_SEL_HI/LO` constants (CR0[23:22]) |

### Python Changes

| File | Changes |
|------|---------|
| `py_tools/boot_constants.py` | Added `BANK_SEL` class, updated `build_loader_cr0()`, added `build_read_cr0()` |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        B0_BOOT_TOP                               │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    ENV_BBUF (4 × 4KB)                       │ │
│  │   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │ │
│  │   │ BBUF_0  │ │ BBUF_1  │ │ BBUF_2  │ │ BBUF_3  │          │ │
│  │   └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘          │ │
│  └────────┼──────────┼──────────┼──────────┼──────────────────┘ │
│           │          │          │          │                     │
│  Write:   ▲          ▲          ▲          ▲                     │
│           └──────────┴──────────┴──────────┘                     │
│                      │                                           │
│       Zeroing FSM (P0→P1) OR L2_BUFF_LOADER (strobe)            │
│                                                                  │
│  Read: BANK_SEL[1:0] mux → bram_rd_data                         │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    L2_BUFF_LOADER                            ││
│  │  Outputs: wr_data_0-3 (CR1-4), wr_addr (offset), wr_we      ││
│  │  CRC validation: always checks all 4 buffers                 ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

1. **BRAMs owned by B0_BOOT_TOP** - Single point of ownership, not distributed
2. **Always 4 buffers** - LOADER writes all 4 in parallel, no variable count
3. **BANK_SEL for reads** - CR0[23:22] selects buffer for BIOS/PROG reads
4. **Zeroing during P0→P1** - Takes 1024 cycles, ensures clean state
5. **CRC validates all 4** - No selective CRC checking

## Verification

- All VHDL files compile with GHDL (`--std=08`)
- Python quick reference runs correctly
- Follows synthesis pattern from `WIP/bram_test_minimal` (verified on MCC)

## Files Modified

```
rtl/boot/B0_BOOT_TOP.vhd
rtl/boot/L2_BUFF_LOADER.vhd
rtl/forge_common_pkg.vhd
py_tools/boot_constants.py
```

## Next Steps

- Run CocoTB tests to verify FSM behavior
- Synthesize on MCC to verify BRAM inference
- Update `docs/boot/BBUF-ALLOCATION-DRAFT.md` checklist

## See Also

- [BBUF-ALLOCATION-DRAFT.md](../../docs/boot/BBUF-ALLOCATION-DRAFT.md) - Design specification
- [BOOT-CR0.md](../../docs/boot/BOOT-CR0.md) - Register bit definitions
- [bram_test_minimal](../../WIP/bram_test_minimal/) - Synthesis reference

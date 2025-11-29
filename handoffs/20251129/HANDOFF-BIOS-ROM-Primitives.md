---
created: 2025-11-29
session: BIOS ROM Primitives Design
status: IN_PROGRESS
---
# Handoff: BIOS ROM Primitives Design

## WORKTREE WARNING

```
┌─────────────────────────────────────────────────────────────────┐
│  YOU ARE IN A DIFFERENT WORKTREE!                               │
│                                                                 │
│  Current:   /Users/johnycsh/DPD/RUNB-BIOS   ← THIS SESSION      │
│  Main repo: /Users/johnycsh/DPD/DPD-001     ← DPD application   │
│                                                                 │
│  Branch: RUNB-BIOS                                              │
│                                                                 │
│  To switch:                                                     │
│    cd /Users/johnycsh/DPD/DPD-001     # Main DPD work           │
│    cd /Users/johnycsh/DPD/RUNB-BIOS   # BIOS/BOOT primitives    │
└─────────────────────────────────────────────────────────────────┘
```

## Session Summary

Designed the BIOS module's core functionality: providing ROM primitives and a percentage-to-voltage scaler for use by application modules (like DPD).

### Key Design Decisions

1. **Separation of Concerns**
   - ROM contains *normalized* platform-agnostic data
   - Deployment config (ENV buffers) provides voltage scaling
   - Applications just request "X%" and get the right voltage

2. **DPD Integration Model**
   ```
   DPD says: "Give me 75% intensity"
        ↓
   pct_scaler does: lookup + scale + offset
        ↓
   Result: Hardware-appropriate voltage for THIS analog frontend
   ```

3. **Clock Divider**
   - System-wide slow-motion for debugging
   - CR0[20:17] = divider select (16 options, /1 to /32768)
   - LOADER bypassed by default (timing-critical handshake)

## Created This Session

| File | Status | Description |
|------|--------|-------------|
| `docs/bootup-proposal/BOOT-ROM-primitives-spec.md` | DRAFT | Full specification |

## Proposal Contents

### ROM Bank 0: Waveforms (8 × 256 entries = 4KB)

| ID | Name | Use Case |
|----|------|----------|
| 0 | SIN_256 | AC test, phase verification |
| 1 | TRI_256 | Slew rate testing |
| 2 | SAW_UP_256 | DAC linearity |
| 3 | SAW_DN_256 | Reverse sweep |
| 4 | SQR_50_256 | Digital timing |
| 5 | SQR_25_256 | Narrow pulse |
| 6 | SQR_10_256 | Impulse-like |
| 7 | STEP_16 | DNL/INL testing |

### ROM Bank 1: Percentage Curves (4 × 101 entries = ~800B)

| ID | Name | Use Case |
|----|------|----------|
| 8 | PCT_LINEAR | Most probes (default) |
| 9 | PCT_LOG | Audio/perceptual |
| 10 | PCT_SQRT | Power→amplitude |
| 11 | PCT_GAMMA22 | Display calibration |

### New CR0 Bits

```
CR0[20:17] = CLK_DIV_SEL
CR0[16]    = CLK_DIV_LOADER_BYPASS
```

## Open Questions (Need Your Decision)

1. **Triangle polarity**: Unipolar (0→+max) or bipolar (-max→+max)?
2. **Percentage overflow**: Clamp to 100%, wrap, or fault?
3. **BRAM**: Infer or explicit instantiation?

## Next Steps

1. [ ] Review `BOOT-ROM-primitives-spec.md` in Obsidian
2. [ ] Resolve open questions
3. [ ] Mark spec as AUTHORITATIVE
4. [ ] Create `forge_rom_pkg.vhd` with ROM contents
5. [ ] Create `py_tools/forge_rom_gen.py` for synthesis
6. [ ] Implement `boot_pct_scaler.vhd` module
7. [ ] Implement clock divider in BOOT_TOP
8. [ ] Update `forge_common_pkg.vhd` with new CR0 bits

## Key Insight

The percentage→voltage abstraction lets the **same bitstream** work with different analog frontends:

```
3.3V probe:  v_scale=3300,  75% → 2.475V
5.0V probe:  v_scale=5000,  75% → 3.750V
Bipolar:     v_scale=10000, v_offset=-5000, 75% → 2.5V
```

No resynthesis needed - just different ENV buffer contents at deployment.

## Related Documents

- `docs/bootup-proposal/BOOT-ROM-primitives-spec.md` - The proposal (review this!)
- `docs/BOOT-FSM-spec.md` - BOOT state machine (AUTHORITATIVE)
- `rtl/forge_common_pkg.vhd` - CR0 definitions
- `rtl/boot/B1_BOOT_BIOS.vhd` - Current BIOS stub (to be expanded)

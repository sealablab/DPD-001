# BOOT Hardware Validation Plan

**Branch:** `feature/boot-hw-validation`
**Goal:** Synthesizable BOOT subsystem with observable HVS state transitions on real Moku hardware.

## Overview

Create minimal dummy implementations for BIOS and LOADER that produce observable HVS voltage transitions, enabling end-to-end validation of the BOOT dispatcher FSM on real hardware with an external oscilloscope.

## Expected HVS Voltage Map (Pre-PROG Scale: 100mV/state)

| Module | State | S Value | Voltage |
|--------|-------|---------|---------|
| BOOT | P0 | 0 | 0.0V |
| BOOT | P1 | 1 | 0.1V |
| BOOT | FAULT | 7 | -0.7V (sign flip) |
| BIOS | IDLE | 8 | 0.8V |
| BIOS | RUN | 9 | 0.9V |
| BIOS | DONE | 10 | 1.0V |
| LOADER | P0 | 16 | 1.6V |
| LOADER | P1 | 17 | 1.7V |
| LOADER | P2 | 18 | 1.8V |
| LOADER | P3 | 19 | 1.9V |
| LOADER | FAULT | 20 | -2.0V (sign flip) |
| PROG | STUB | 24 | 2.4V |

## Implementation Tasks

### Phase 1: BIOS Stub Enhancement
- [ ] Add simple 3-state FSM: IDLE → RUN → DONE
- [ ] IDLE: Waiting state after dispatch from BOOT
- [ ] RUN: Auto-advance after N cycles (configurable via CR)
- [ ] DONE: Assert `bios_complete` signal, wait for RET
- [ ] Wire HVS encoder with S=8,9,10 mapping

### Phase 2: LOADER Validation Mode
- [ ] Already has P0→P1→P2→P3 FSM structure
- [ ] Add "validation mode" that accepts dummy strobes
- [ ] Skip real CRC check in validation mode (always pass)
- [ ] Ensure `loader_complete` asserts in P3

### Phase 3: BOOT TOP Integration
- [ ] Add `bios_complete` signal and wire to B1_BOOT_BIOS
- [ ] Verify output muxing routes correct HVS per state
- [ ] Ensure RET logic works for both BIOS and LOADER

### Phase 4: Synthesis & Bitstream
- [ ] Create Moku CloudCompile project structure
- [ ] Verify all entities synthesize without errors
- [ ] Generate bitstream (.tar)

### Phase 5: Hardware Test Script
- [ ] Python script using Moku API
- [ ] Oscilloscope on OutputC (HVS observation)
- [ ] Sequence: P0 → P1 → LOADER → P1 → BIOS → P1 → PROG
- [ ] Log voltage readings at each state transition
- [ ] Compare against expected voltage map

## Test Sequence

```
1. Power on / Reset
   → Observe: 0.0V (BOOT_P0)

2. Set RUN gate (CR0[31:29] = 0b111)
   → Observe: 0.1V (BOOT_P1)

3. Set SEL_LOADER (CR0[26] = 1)
   → Observe: 1.6V (LOADER_P0)

4. Send strobes, watch LOADER progress
   → Observe: 1.7V → 1.8V → 1.9V (P1 → P2 → P3)

5. Set RET (CR0[24] = 1)
   → Observe: 0.1V (BOOT_P1)

6. Set SEL_BIOS (CR0[27] = 1)
   → Observe: 0.8V (BIOS_IDLE)

7. Watch BIOS auto-advance
   → Observe: 0.9V → 1.0V (RUN → DONE)

8. Set RET
   → Observe: 0.1V (BOOT_P1)

9. Set SEL_PROG (CR0[28] = 1)
   → Observe: 2.4V (PROG_STUB)
   → Note: One-way, RET has no effect

10. Clear RUN gate
    → Observe: 0.0V (BOOT_P0)
```

## Success Criteria

1. All state transitions produce expected HVS voltages (±50mV)
2. RET returns to BOOT_P1 from BIOS and LOADER
3. PROG is one-way (RET has no effect)
4. RUN gate removal always returns to BOOT_P0
5. No synthesis warnings/errors

## Files to Create/Modify

- `rtl/boot/B1_BOOT_BIOS.vhd` - Enhance with 3-state FSM
- `rtl/boot/B0_BOOT_TOP.vhd` - Add bios_complete wiring
- `rtl/boot/L2_BUFF_LOADER.vhd` - Add validation mode
- `tests/hw/boot_hw_validation.py` - Hardware test script
- `moku/BOOT_validation.moku` - CloudCompile project (if needed)

## Notes

- Using pre-PROG HVS scale (100mV/state) for finer granularity
- PROG stub uses fixed voltage until DPD integration
- Validation mode should be clearly marked (not for production)

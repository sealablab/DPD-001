---
file: L2_BUFF_LOADER.vhd.md
type: rtl_md
author: jellch
created: 2025-11-28
modified: 2025-11-30 16:14:24
accessed: 2025-11-30 17:50:45
code_link: "[[rtl/boot/L2_BUFF_LOADER.vhd|L2_BUFF_LOADER.vhd]]"
doc_link: "[[rtl/boot/L2_BUFF_LOADER.vhd.md|L2_BUFF_LOADER.vhd.md]]"
self_link: "[[rtl/boot/L2_BUFF_LOADER.vhd.md|L2_BUFF_LOADER.vhd.md]]"
Descr: LOADER module for populating ENV_BBUFs via blind handshake protocol with CRC-16 validation
tags:
  - BOOT
  - LOADER
  - BRAM
---

# L2_BUFF_LOADER

> [!NOTE] Authoritative Source
> `/rtl/boot/L2_BUFF_LOADER.vhd` contains the actual code and should be treated as authoritative over this description.

LOADER module for populating ENV_BBUFs (Environment Block Buffers) from the Python client. Uses a blind handshake protocol where the host strobes data words through Control Registers with CRC-16 validation.

## Overview

The LOADER receives data via CR1-CR4 (one word per buffer per strobe) and writes to up to 4 BRAM buffers. After 1024 words are transferred, it validates running CRCs against expected values latched during setup.

**Key features:**
- 4 parallel 4KB BRAMs (inferred block RAM)
- Blind handshake protocol (no feedback except HVS/oscilloscope)
- CRC-16-CCITT validation per buffer
- VALIDATION_MODE for hardware testing (auto-advance, skip CRC)

## Control Flow

1. BOOT dispatcher sets LOADER active → enters `LOAD_P0` (setup phase)
2. Host sends setup strobe → latch buffer count + expected CRCs from CR0/CR1-4
3. Transition to `LOAD_P1` (transfer phase)
4. Host sends 1024 data strobes → write CR1-4 to BRAMs, update running CRCs
5. After 1024 words → transition to `LOAD_P2` (validate phase)
6. Compare running CRCs vs expected → `LOAD_P3` (complete) or `FAULT`
7. User sets CR0[24] = 1 (RET) → return to `BOOT_P1`

## Observability

HVS encoding via parent's `forge_hierarchical_encoder`:
- **S=16** (LOAD_P0) — Setup phase, waiting for config strobe
- **S=17** (LOAD_P1) — Transfer phase, receiving data
- **S=18** (LOAD_P2) — Validate phase, checking CRCs
- **S=19** (LOAD_P3) — Complete, ready for RET (CR0[24])
- **S=20** (LOAD_FAULT) — CRC mismatch detected

---

## Implements

- [[docs/bootup-proposal/LOAD-FSM-spec.md|LOAD-FSM-spec]] — authoritative FSM specification
- [[docs/bootup-proposal/LOADER-implementation-plan.md|LOADER-implementation-plan]] — implementation details

## Dependencies (RTL)

| File | Purpose |
|------|---------|
| [[rtl/forge_common_pkg.vhd\|forge_common_pkg]] | LOAD_STATE_*, ENV_BBUF_*, CRC16_* constants |
| [[rtl/boot/loader_crc16.vhd\|loader_crc16]] | CRC-16-CCITT calculator (4 instances) |

---

## Entity

Standalone entity (child module, not using BootWrapper pattern).

| Group | Ports | Type | Direction |
|-------|-------|------|-----------|
| Clock | `Clk`, `Reset` | `std_logic` | in |
| Control | `CR0`-`CR4` | `slv(31:0)` | in |
| State | `state_vector` | `slv(5:0)` | out |
| State | `status_vector` | `slv(7:0)` | out |
| Control | `loader_fault` | `std_logic` | out |
| Control | `loader_complete` | `std_logic` | out |
| BRAM | `bram_rd_addr` | `slv(ENV_BBUF_ADDR_WIDTH-1:0)` | in |
| BRAM | `bram_rd_sel` | `slv(1:0)` | in |
| BRAM | `bram_rd_data` | `slv(ENV_BBUF_DATA_WIDTH-1:0)` | out |

## Generics

```vhdl
generic (
    VALIDATION_MODE         : boolean := false;   -- Skip CRC, auto-advance
    VALIDATION_DELAY_CYCLES : natural := 125000   -- 1ms @ 125MHz per state
);
```

**Port descriptions:**
- **CR0** — contains strobe bit (21), buffer count (23:22)
- **CR1-CR4** — setup: expected CRCs; transfer: data words
- **state_vector** — current FSM state for HVS encoding
- **status_vector** — debug info; [7]=fault, [3:2]=buffer_count
- **loader_fault** — asserted when in FAULT state
- **loader_complete** — asserted when in LOAD_P3 state
- **bram_rd_*** — read interface for PROG access after loading

---

## Architecture

Architecture: `rtl of L2_BUFF_LOADER`

### Instantiated Modules

| Label | Entity | Purpose |
|-------|--------|---------|
| `CRC_CALC_0..3` | [[rtl/boot/loader_crc16.vhd\|loader_crc16]] | Running CRC per buffer (4 parallel) |

### Key Processes

- **Strobe Edge Detection** — falling edge of `CR0(LOADER_STROBE_BIT)`
- **FSM State Register** — synchronous state update
- **FSM Next State Logic** — normal mode: strobe-driven; validation mode: delay-driven
- **Configuration Latch** — buffer count + expected CRCs on setup strobe
- **Offset Counter** — 0-1023 word address during transfer
- **Running CRC Update** — update on each data strobe
- **BRAM Write Logic** — parallel write to 4 buffers
- **BRAM Read Logic** — muxed read for PROG access
- **CRC Comparison** — validate running vs expected based on buffer count

### FSM Summary

> See [[docs/bootup-proposal/LOAD-FSM-spec.md|LOAD-FSM-spec]] for authoritative details

```
    ┌──────────┐  setup_strobe  ┌──────────┐  1024 words  ┌──────────┐
    │ LOAD_P0  │───────────────▶│ LOAD_P1  │─────────────▶│ LOAD_P2  │
    │ (setup)  │                │(transfer)│              │(validate)│
    └──────────┘                └──────────┘              └────┬─────┘
                                                               │
                                          ┌────────────────────┼────────────────────┐
                                          │ CRC match          │                    │ CRC mismatch
                                          ▼                    │                    ▼
                                    ┌──────────┐               │              ┌──────────┐
                                    │ LOAD_P3  │               │              │  FAULT   │
                                    │(complete)│               │              └──────────┘
                                    └──────────┘               │
                                          │ RET                │
                                          └────────────────────┘
```

### Outputs

| State | loader_complete | loader_fault | status[7] |
|-------|-----------------|--------------|-----------|
| LOAD_P0 | 0 | 0 | 0 |
| LOAD_P1 | 0 | 0 | 0 |
| LOAD_P2 | 0 | 0 | 0 |
| LOAD_P3 | 1 | 0 | 0 |
| FAULT | 0 | 1 | 1 |

---

## Configuration

### Protocol Bits (CR0)

```
CR0[23:22] = buffer_count (0=1 buffer, 3=4 buffers)
CR0[21]    = data_strobe (falling edge triggers action)
```

### Validation Mode

```vhdl
generic (
    VALIDATION_MODE         : boolean := false;
    VALIDATION_DELAY_CYCLES : natural := 125000  -- 1ms @ 125MHz
);
```

> [!warning] Test Environment Settings
> - **Normal operation**: `VALIDATION_MODE => false` — uses strobe protocol + CRC
> - **Hardware validation**: `VALIDATION_MODE => true` — auto-advances states with delay, skips CRC
> - **CocoTB sim**: Use small delay (e.g., 10) when validation mode is enabled

---

## BRAM Architecture

4 parallel block RAMs, each 1024 x 32-bit (4KB):

```
           ┌─────────────────┐
   CR1 ───▶│   bram_0 (4KB)  │───▶ bram_rd_0
           └─────────────────┘
   CR2 ───▶│   bram_1 (4KB)  │───▶ bram_rd_1
           └─────────────────┘
   CR3 ───▶│   bram_2 (4KB)  │───▶ bram_rd_2
           └─────────────────┘
   CR4 ───▶│   bram_3 (4KB)  │───▶ bram_rd_3
           └─────────────────┘
                    │
                    ▼
              bram_rd_sel (2-bit mux)
                    │
                    ▼
              bram_rd_data
```

**Note:** All 4 buffers are always written in parallel. `buffer_count` only affects CRC validation — unused buffers receive data but their CRCs are not checked.

---

# See Also

- [[rtl/boot/B0_BOOT_TOP.vhd.md|B0_BOOT_TOP]] — parent dispatcher
- [[rtl/boot/loader_crc16.vhd|loader_crc16]] — CRC-16 calculator
- [[rtl/forge_common_pkg.vhd.md|forge_common_pkg]] — shared constants
- [[docs/boot/BOOT-HVS-state-reference.md|BOOT-HVS-state-reference]] — **authoritative** HVS state table
- [[docs/bootup-proposal/LOAD-FSM-spec.md|LOAD-FSM-spec]] — FSM specification
- [[docs/hvs.md|HVS]] — voltage encoding scheme

---
file: env_bbuf_block.vhd.md
type: rtl_md
author: jellch
created: 2025-12-01
modified: 2025-12-01 15:23:14
accessed: 2025-12-01 15:15:39
code_link: "[[rtl/boot/env_bbuf_block.vhd|env_bbuf_block.vhd]]"
doc_link: "[[rtl/boot/env_bbuf_block.vhd.md|env_bbuf_block.vhd.md]]"
self_link: "[[rtl/boot/env_bbuf_block.vhd.md|env_bbuf_block.vhd.md]]"
---

# [[rtl/boot/env_bbuf_block.vhd.md|env_bbuf_block.vhd]]

> [!NOTE] Authoritative Source
> `/rtl/boot/env_bbuf_block.vhd` contains the actual code and should be treated as authoritative over this description.

Encapsulates 4x 4KB BRAM buffers with integrated zeroing FSM. Provides parallel write interface for LOADER and bank-selected read interface for BIOS/PROG.

## Overview

The `env_bbuf_block` component owns the physical BRAM resources (16KB total) and provides:
- **Parallel write interface** — LOADER writes 4 words simultaneously (CR1-4 → buf0-3)
- **Bank-selected read** — BIOS/PROG reads from one buffer at a time via `rd_sel`
- **Automatic zeroing** — FSM zeros all buffers on `zero_start` pulse

**Key features:**
- 4 parallel 4KB buffers (1024 x 32-bit each)
- Xilinx UG901 BRAM inference pattern (shared variable)
- Single-cycle write, single-cycle read latency
- Zeroing takes ~1024 cycles (~8.2µs @ 125MHz)

> [!warning] Synthesis Note
> Current implementation infers Distributed RAM (LUTRAM) rather than Block RAM. Functionally correct but uses more LUT resources. Block RAM optimization deferred for future work.

## Entity

Standalone entity (child module, not using BootWrapper pattern).

| Group | Port | Type | Dir | Description |
|-------|------|------|-----|-------------|
| Clock | `Clk` | `std_logic` | in | System clock |
| Clock | `Reset` | `std_logic` | in | Synchronous reset |
| Zero | `zero_start` | `std_logic` | in | Pulse to start zeroing |
| Zero | `zero_done` | `std_logic` | out | High when zeroing complete |
| Write | `wr` | `env_bbuf_wr_t` | in | Parallel write interface |
| Read | `rd_addr` | `env_bbuf_addr_t` | in | Read address (0-1023) |
| Read | `rd_sel` | `env_bbuf_sel_t` | in | Buffer select (0-3) |
| Read | `rd_data` | `env_bbuf_data_t` | out | Read data (1-cycle latency) |

## Architecture

Architecture: `rtl of env_bbuf_block`

### BRAM Structure

```
           wr.data_0                    rd_addr
              │                            │
              ▼                            ▼
        ┌───────────┐               ┌───────────┐
        │ env_bbuf_0│──────────────▶│  rd_data_0│───┐
        │  (4KB)    │               └───────────┘   │
        └───────────┘                               │
           wr.data_1                                │
              │                                     │
              ▼                                     │
        ┌───────────┐               ┌───────────┐   │
        │ env_bbuf_1│──────────────▶│  rd_data_1│───┼──▶ rd_sel_r
        │  (4KB)    │               └───────────┘   │      mux
        └───────────┘                               │       │
           wr.data_2                                │       │
              │                                     │       ▼
              ▼                                     │   rd_data
        ┌───────────┐               ┌───────────┐   │
        │ env_bbuf_2│──────────────▶│  rd_data_2│───┤
        │  (4KB)    │               └───────────┘   │
        └───────────┘                               │
           wr.data_3                                │
              │                                     │
              ▼                                     │
        ┌───────────┐               ┌───────────┐   │
        │ env_bbuf_3│──────────────▶│  rd_data_3│───┘
        │  (4KB)    │               └───────────┘
        └───────────┘
              ▲
              │
         wr.addr + wr.we (or zero_addr during zeroing)
```

### Key Processes

- **Zeroing FSM** — 3-state machine (IDLE → ACTIVE → DONE)
- **Write Address Mux** — selects `zero_addr` or `wr.addr` (combinatorial)
- **BRAM Write (x4)** — separate process per buffer (Xilinx inference pattern)
- **BRAM Read (x4)** — separate process per buffer (registered output)
- **Output Mux** — selects read data based on registered `rd_sel`

### Zeroing FSM

```
    ┌───────────┐  zero_start  ┌─────────────┐  addr=1023  ┌─────────────┐
    │ ZERO_IDLE │─────────────▶│ ZERO_ACTIVE │────────────▶│ ZERO_DONE   │
    └───────────┘              └─────────────┘             └──────┬──────┘
         ▲                                                        │
         │                           zero_start                   │
         └────────────────────────────────────────────────────────┘
```

| State | `zero_done` | Action |
|-------|-------------|--------|
| ZERO_IDLE | 0 | Waiting for `zero_start` pulse |
| ZERO_ACTIVE | 0 | Writing zeros to all buffers (1024 cycles) |
| ZERO_DONE | 1 | Complete, held until next `zero_start` |

## Write Interface

The `env_bbuf_wr_t` record enables type-safe parallel writes:

```vhdl
-- In LOADER or test bench
bbuf_wr.addr   <= std_logic_vector(offset);
bbuf_wr.data_0 <= Control1;  -- CR1 → buffer 0
bbuf_wr.data_1 <= Control2;  -- CR2 → buffer 1
bbuf_wr.data_2 <= Control3;  -- CR3 → buffer 2
bbuf_wr.data_3 <= Control4;  -- CR4 → buffer 3
bbuf_wr.we     <= strobe_pulse;
```

## Read Interface

Bank-selected read with 1-cycle latency:

```vhdl
-- Set address and bank
rd_addr <= "0000000101";  -- Address 5
rd_sel  <= "10";          -- Buffer 2

-- Data available on NEXT clock cycle
-- rd_data contains buffer 2, word 5
```

## Dependencies (RTL)

| File | Purpose |
|------|---------|
| [[rtl/boot/env_bbuf_pkg.vhd\|env_bbuf_pkg]] | Types: `env_bbuf_wr_t`, `env_bbuf_addr_t`, etc. |

## Compilation

Requires GHDL `-frelaxed` flag for VHDL-2008 shared variable pattern:

```bash
ghdl -a --std=08 -frelaxed env_bbuf_pkg.vhd
ghdl -a --std=08 -frelaxed env_bbuf_block.vhd
```

---

# See Also

- [[rtl/boot/env_bbuf_pkg.vhd.md|env_bbuf_pkg]] — types and constants
- [[rtl/boot/B0_BOOT_TOP.vhd.md|B0_BOOT_TOP]] — parent instantiating this block
- [[rtl/boot/L2_BUFF_LOADER.vhd.md|L2_BUFF_LOADER]] — writes to buffers
- [[docs/boot/BBUF-ALLOCATION-DRAFT.md|BBUF-ALLOCATION-DRAFT]] — design rationale

---

---
created: 2025-11-30
modified: 2025-12-01 15:33:13
accessed: 2025-12-01 15:24:24
type: N
---
# [ENV-BBUF](docs/N/ENV-BBUF.md)

An **ENV-BBUF** (Environment Block Buffer) is one of four 4KB BRAM buffers provided as a boot-time service. These buffers are loaded over the network via the [[rtl/boot/L2_BUFF_LOADER.vhd|L2_BUFF_LOADER]] and read by BIOS/PROG via bank-selected access.

**Total capacity:** 16KB (4 buffers × 1024 words × 32 bits)

---

## Package Types (`env_bbuf_pkg`)

All ENV-BBUF types are centralized in [[rtl/boot/env_bbuf_pkg.vhd|env_bbuf_pkg.vhd]]:

### Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `ENV_BBUF_WORDS` | 1024 | Words per buffer |
| `ENV_BBUF_DATA_WIDTH` | 32 | Bits per word |
| `ENV_BBUF_ADDR_WIDTH` | 10 | Address bits (log₂1024) |
| `ENV_BBUF_COUNT` | 4 | Number of buffers |
| `ENV_BBUF_SEL_WIDTH` | 2 | Bank select bits (log₂4) |

### Subtypes

| Subtype | Base | Description |
|---------|------|-------------|
| `env_bbuf_addr_t` | `slv(9:0)` | Word address (0-1023) |
| `env_bbuf_data_t` | `slv(31:0)` | Data word |
| `env_bbuf_sel_t` | `slv(1:0)` | Buffer selector (0-3) |

### Records

**`env_bbuf_wr_t`** — Parallel write interface (LOADER → buffers)
```vhdl
type env_bbuf_wr_t is record
    data_0 : env_bbuf_data_t;   -- CR1 → buffer 0
    data_1 : env_bbuf_data_t;   -- CR2 → buffer 1
    data_2 : env_bbuf_data_t;   -- CR3 → buffer 2
    data_3 : env_bbuf_data_t;   -- CR4 → buffer 3
    addr   : env_bbuf_addr_t;   -- Word address
    we     : std_logic;         -- Write enable pulse
end record;
```

**`env_bbuf_zero_t`** — Zeroing control interface
```vhdl
type env_bbuf_zero_t is record
    start : std_logic;          -- Pulse to start zeroing
    done  : std_logic;          -- High when complete
end record;
```

---

## Block Component (`env_bbuf_block`)

The [[rtl/boot/env_bbuf_block.vhd|env_bbuf_block]] component owns the physical BRAM resources:

- **Parallel write** — LOADER writes 4 words simultaneously
- **Bank-selected read** — BIOS/PROG reads one buffer at a time via `rd_sel`
- **Automatic zeroing** — FSM zeros all buffers (~1024 cycles)

> [!warning] Synthesis Note
> Current implementation infers Distributed RAM (LUTRAM) rather than Block RAM. Functionally correct but uses more LUT resources.

---

# See Also

- [[rtl/boot/env_bbuf_pkg.vhd.md|env_bbuf_pkg]] — Package documentation
- [[rtl/boot/env_bbuf_block.vhd.md|env_bbuf_block]] — Component documentation
- [[rtl/boot/L2_BUFF_LOADER.vhd.md|L2_BUFF_LOADER]] — Writes to buffers
- [[rtl/boot/B0_BOOT_TOP.vhd.md|B0_BOOT_TOP]] — Parent instantiating ENV_BBUF
- [[docs/boot/BBUF-ALLOCATION-DRAFT.md|BBUF-ALLOCATION-DRAFT]] — Design rationale
- [[docs/BOOT-FSM-spec.md|BOOT-FSM-spec]] — Boot FSM specification

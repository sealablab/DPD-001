---
file: env_bbuf_pkg.vhd.md
type: rtl_md
author: jellch
created: 2025-12-01
modified: 2025-12-01 15:22:00
accessed: 2025-12-01 15:14:57
code_link: "[[rtl/boot/env_bbuf_pkg.vhd|env_bbuf_pkg.vhd]]"
doc_link: "[[rtl/boot/env_bbuf_pkg.vhd.md|env_bbuf_pkg.vhd.md]]"
self_link: "[[rtl/boot/env_bbuf_pkg.vhd.md|env_bbuf_pkg.vhd.md]]"
---



# [[rtl/boot/env_bbuf_pkg.vhd.md|env_bbuf_pkg.vhd]]

> [!NOTE] Authoritative Source
> `/rtl/boot/env_bbuf_pkg.vhd` contains the actual code and should be treated as authoritative over this description.

VHDL package defining types, records, and constants for the ENV_BBUF (Environment Block Buffer) infrastructure. Centralizes buffer-related definitions for type-safe port mapping across BOOT subsystem modules.

## Overview

The `env_bbuf_pkg` package provides a single source of truth for ENV_BBUF types used by:
- [[rtl/boot/env_bbuf_block.vhd|env_bbuf_block]] — BRAM owner with zeroing FSM
- [[rtl/boot/L2_BUFF_LOADER.vhd|L2_BUFF_LOADER]] — writes via `env_bbuf_wr_t` record
- [[rtl/boot/B0_BOOT_TOP.vhd|B0_BOOT_TOP]] — instantiates and connects components

**Design Goals:**
1. Centralize ENV_BBUF type definitions in one place
2. Enable type-safe port mapping via records
3. Support both GHDL simulation and MCC synthesis
4. Keep memory allocation separate from FSM logic

## Package Contents

### Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `ENV_BBUF_WORDS` | 1024 | Words per buffer (4KB) |
| `ENV_BBUF_DATA_WIDTH` | 32 | Bits per word |
| `ENV_BBUF_ADDR_WIDTH` | 10 | log2(1024) |
| `ENV_BBUF_COUNT` | 4 | Number of buffers |
| `ENV_BBUF_SEL_WIDTH` | 2 | log2(4) |

### Subtypes

| Subtype | Base Type | Description |
|---------|-----------|-------------|
| `env_bbuf_addr_t` | `slv(9:0)` | Word address |
| `env_bbuf_data_t` | `slv(31:0)` | Data word |
| `env_bbuf_sel_t` | `slv(1:0)` | Buffer selector |

### Types

| Type | Description |
|------|-------------|
| `env_bbuf_t` | Array of 1024 x 32-bit words (single buffer) |
| `env_bbuf_wr_t` | Record for parallel write interface |
| `env_bbuf_zero_t` | Record for zeroing control |

### Write Interface Record (`env_bbuf_wr_t`)

```vhdl
type env_bbuf_wr_t is record
    data_0 : env_bbuf_data_t;   -- CR1 → buffer 0
    data_1 : env_bbuf_data_t;   -- CR2 → buffer 1
    data_2 : env_bbuf_data_t;   -- CR3 → buffer 2
    data_3 : env_bbuf_data_t;   -- CR4 → buffer 3
    addr   : env_bbuf_addr_t;   -- Word address (0-1023)
    we     : std_logic;         -- Write enable pulse
end record;
```

## Usage

```vhdl
library WORK;
use WORK.env_bbuf_pkg.all;

-- Declare write interface signal
signal bbuf_wr : env_bbuf_wr_t := ENV_BBUF_WR_INIT;

-- Use in port map
U_ENV_BBUF : entity work.env_bbuf_block
    port map (
        wr => bbuf_wr,
        ...
    );
```

## Dependencies

None — this is a leaf package with no dependencies.

---

# See Also

- [[rtl/boot/env_bbuf_block.vhd.md|env_bbuf_block]] — component using these types
- [[rtl/boot/L2_BUFF_LOADER.vhd.md|L2_BUFF_LOADER]] — LOADER using write interface
- [[docs/boot/BBUF-ALLOCATION-DRAFT.md|BBUF-ALLOCATION-DRAFT]] — design rationale
- [[rtl/forge_common_pkg.vhd|forge_common_pkg]] — related BOOT constants

---

---
file: B0_BOOT_TOP.vhd.md
type: rtl_md
author: jellch
created: 2025-11-28
modified: 2025-11-30 15:36:40
accessed: 2025-11-30 16:17:14
code_link: "[[rtl/boot/B0_BOOT_TOP.vhd|B0_BOOT_TOP.vhd]]"
doc_link: "[[rtl/boot/B0_BOOT_TOP.vhd.md|B0_BOOT_TOP.vhd.md]]"
self_link: "[[rtl/boot/B0_BOOT_TOP.vhd.md|B0_BOOT_TOP.vhd.md]]"
Descr: " BOOT subsystem top-level module implementing the CustomWrapper architecture."
tags:
  - BOOT
---
# See Also: Templater/Templates/BLANK_TOP_FILE.vhd.md

## [B0_BOOT_TOP](rtl/boot/B0_BOOT_TOP.vhd.md)

> [!NOTE] `/rtl/boot/B0_BOOT_TOP.vhd`
> Contains the actual code and should be treated as authoritative over this description 

BOOT subsystem top-level module implementing the CustomWrapper architecture.
This is the dispatcher FSM that routes control to BIOS, LOADER, or PROG
- The `boot_dispatcher` architecture implements a **6-state dispatcher FSM** that routes control to child modules based on CR0 module select bits.

## **Control Flow:**
1. Extract RUN gate from `CR0[31:29]` — all three must be set for operation
2. Extract module select from `CR0[28:25]` — RUNP/RUNB/RUNL/RUNR commands
3. Dispatch to appropriate module, wait for completion + RET to return

## Status / observability
the `BOOT` module will utilize OutputC to provide **HVS Encoding:** [hvs](docs/hvs.md) [HVS-encoding-scheme](docs/HVS-encoding-scheme.md)


## **Key Processes:**

- **FSM State Register** — synchronous state update with reset to `BOOT_STATE_P0`
- **FSM Next State Logic** — combinatorial transitions based on RUN gate + module select
- **Output Muxing** — combinatorial routing of OutputA/B/C based on `boot_state`

## Implements 
- [BOOT-FSM-spec](docs/BOOT-FSM-spec.md)
## Dependencies (`RTL`)
- [forge_hierarchical_encoder.vhd](rtl/forge_hierarchical_encoder.vhd.md)
- #TODO @C  / @JC we should put a list of compilation dependencies in here..


##  `Entity`
The `B0_BOOT_TOP` file implements the standard  MCC compatible interface.
It does this by using the  [[docs/N/BootWrapper|BootWrapper pattern]] - entity declared in [[rtl/boot/BootWrapper_test_stub.vhd|BootWrapper_test_stub.vhd]]

| Group   | Ports                           | Type           |
| ------- | ------------------------------- | -------------- |
| Clock   | `Clk`, `Reset`                  | `std_logic`    |
| Inputs  | `InputA`, `InputB`, `InputC`    | `signed(15:0)` |
| Outputs | `OutputA`, `OutputB`, `OutputC` | `signed(15:0)` |
| Control | `Control0`–`Control15`          | `slv(31:0)`    |

The entity provides the standard Moku CloudCompile interface:
- **Clk/Reset** — system clock and synchronous reset
- **InputA/B/C** — 16-bit signed ADC inputs (not used by BOOT dispatcher)
- **OutputA/B/C** — 16-bit signed DAC outputs (OutputC = HVS state encoding)
- **Control0–15** — 32-bit configuration registers from Moku platform

```vhdl
entity BootWrapper is
    port (
        Clk, Reset   : in  std_logic;
        InputA/B/C   : in  signed(15 downto 0);
        OutputA/B/C  : out signed(15 downto 0);
        Control0..15 : in  std_logic_vector(31 downto 0)
    );
end entity;
```


---
# `B0_BOOT_TOP`:  `Architecture`

## **Instantiated Modules:**

| Label           | Entity                                                             | Purpose                     |
| --------------- | ------------------------------------------------------------------ | --------------------------- |
| `LOADER_INST`   | [[rtl/boot/L2_BUFF_LOADER.vhd\|L2_BUFF_LOADER]]                    | ENV_BBUF BRAM population    |
| `BIOS_INST`     | [[rtl/boot/B1_BOOT_BIOS.vhd\|B1_BOOT_BIOS]]                        | ROM waveform generation     |
| `PROG_DPD_INST` | [[rtl/DPD_shim.vhd\|DPD_shim]]                                     | Application logic (one-way) |
| `*_HVS_ENCODER` | [[rtl/forge_hierarchical_encoder.vhd\|forge_hierarchical_encoder]] | HVS state→voltage (×3)      |

---
#### FSM-summary (see [BOOT-FSM-spec](docs/BOOT-FSM-spec.md) for details)

```
         ┌─────────────────────────────────────────────────┐
         │                                                 │
         ▼                                                 │
    ┌─────────┐  RUN   ┌─────────┐  RUNP   ┌─────────────┐ │
    │ BOOT_P0 │───────▶│ BOOT_P1 │────────▶│ PROG_ACTIVE │─┘ (one-way)
    └─────────┘        └────┬────┘         └─────────────┘
         ▲                  │ RUNB/RUNL
         │                  ▼
         │           ┌─────────────┐  RET
         └───────────│ BIOS/LOADER │────────┘
                     │   _ACTIVE   │
                     └─────────────┘
```


## `B0_BOOT_TOP`:  **Outputs**
- `BOOT_P0/P1/FAULT` → BOOT drives OutputC (HVS S=0-7)
- `BIOS_ACTIVE` → BIOS drives OutputC (HVS S=8-15)
- `LOAD_ACTIVE` → LOADER drives OutputC (HVS S=16-23)
- `PROG_ACTIVE` → PROG drives all outputs (DPD takes over)

---
# See Also
## [BOOT-FSM-spec](docs/BOOT-FSM-spec.md)

---

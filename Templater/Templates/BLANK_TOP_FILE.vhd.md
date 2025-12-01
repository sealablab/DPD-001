---
file: COMPONENT_NAME.vhd.md
type: rtl_md
author: jellch
created: {{date}}
modified: {{date}}
accessed: {{date}}
code_link: "[[rtl/path/COMPONENT_NAME.vhd|COMPONENT_NAME.vhd]]"
doc_link: "[[rtl/path/COMPONENT_NAME.vhd.md|COMPONENT_NAME.vhd.md]]"
self_link: "[[rtl/path/COMPONENT_NAME.vhd.md|COMPONENT_NAME.vhd.md]]"
Descr: "Brief one-line description"
tags:
  - TAG1
---

# COMPONENT_NAME

> [!NOTE] Authoritative Source
> `/rtl/path/COMPONENT_NAME.vhd` contains the actual code and should be treated as authoritative over this description.

Brief description of what this component does and its role in the system.

## Overview

High-level purpose and behavior. What problem does this solve?

## Control Flow

1. Step one of operation
2. Step two of operation
3. Step three of operation

## Observability

How is state/status exposed? (e.g., HVS encoding on OutputC)
- Links to: [[docs/hvs.md|HVS]] [[docs/HVS-encoding-scheme.md|HVS Encoding Scheme]]

---

## Implements

- [[docs/path/SPEC.md|SPEC-NAME]] — authoritative specification

## Dependencies (RTL)

| File | Purpose |
|------|---------|
| [[rtl/path/dep1.vhd\|dep1]] | What it provides |
| [[rtl/path/dep2.vhd\|dep2]] | What it provides |

---

## Entity

> Uses [[docs/N/BootWrapper|BootWrapper pattern]] if applicable

| Group   | Ports                           | Type           |
|---------|--------------------------------|----------------|
| Clock   | `Clk`, `Reset`                 | `std_logic`    |
| Inputs  | `InputA`, `InputB`, `InputC`   | `signed(15:0)` |
| Outputs | `OutputA`, `OutputB`, `OutputC`| `signed(15:0)` |
| Control | `Control0`–`Control15`         | `slv(31:0)`    |

**Port descriptions:**
- **Clk/Reset** — system clock and synchronous reset
- **InputA/B/C** — 16-bit signed ADC inputs
- **OutputA/B/C** — 16-bit signed DAC outputs
- **Control0–15** — 32-bit configuration registers

```vhdl
entity ENTITY_NAME is
    port (
        Clk, Reset   : in  std_logic;
        InputA/B/C   : in  signed(15 downto 0);
        OutputA/B/C  : out signed(15 downto 0);
        Control0..15 : in  std_logic_vector(31 downto 0)
    );
end entity;
```

---

## Architecture

Architecture: `arch_name of ENTITY_NAME`

### Instantiated Modules

| Label        | Entity                              | Purpose              |
|--------------|-------------------------------------|----------------------|
| `INST_1`     | [[rtl/path/entity1.vhd\|entity1]]   | What it does         |
| `INST_2`     | [[rtl/path/entity2.vhd\|entity2]]   | What it does         |

### Key Processes

- **Process 1** — what it does
- **Process 2** — what it does
- **Process 3** — what it does

### FSM Summary

> See [[docs/path/FSM-spec.md|FSM-spec]] for authoritative details

```
    ┌─────────┐       ┌─────────┐       ┌─────────┐
    │ STATE_A │──────▶│ STATE_B │──────▶│ STATE_C │
    └─────────┘       └─────────┘       └─────────┘
```

### Outputs

| State | OutputA | OutputB | OutputC |
|-------|---------|---------|---------|
| STATE_A | description | description | HVS S=0 |
| STATE_B | description | description | HVS S=1 |

---

## Configuration

Constants that may need adjustment for sim vs hardware:

```vhdl
constant DELAY_CYCLES : natural := 10;  -- Short for sim, 125000 for HW
```

> [!warning] Validation Mode
> Set delays appropriately for your test environment.

---

# See Also

- [[docs/path/related-spec.md|Related Spec]]
- [[rtl/path/related-component.vhd.md|Related Component]]
- [[docs/N/RelatedNote|Related Note]]

---
type: N
created: 2025-11-30
modified: 2025-11-30 14:29:42
accessed: 2025-11-30 14:29:46
---

# BootWrapper

The **BootWrapper pattern** separates VHDL entity declaration from architecture implementation across two files.


## The Problem

We need to elegantly 'multiplex' the moku [cloudcompile](moku_md/instruments/cloudcompile.md) 'CustomWrapper' entity. 
- Compiling both in the same GHDL work library causes entity name collision. 

## The solution

```
BootWrapper_test_stub.vhd     B0_BOOT_TOP.vhd
┌─────────────────────┐       ┌─────────────────────┐
│ entity BootWrapper  │──────▶│ architecture        │
│   port (...)        │       │   boot_dispatcher   │
│ end entity;         │       │ of BootWrapper      │
│                     │       │   -- FSM, HVS, etc  │
│ (NO architecture)   │       │ end architecture;   │
└─────────────────────┘       └─────────────────────┘
```

## Why This Works

1. **Namespace isolation** - `BootWrapper` vs `CustomWrapper` avoids GHDL entity collisions
2. **Simulation vs Synthesis** - Test stub provides entity for CocoTB; MCC provides its own for synthesis
3. **Swappable architectures** - Same entity can bind to different implementations


---

# See Also

- [[rtl/boot/BootWrapper_test_stub.vhd|BootWrapper_test_stub.vhd]] - Entity declaration (test stub)
- [[rtl/boot/B0_BOOT_TOP.vhd|B0_BOOT_TOP.vhd]] - Architecture implementation
- [[rtl/boot/B0_BOOT_TOP.vhd.md|B0_BOOT_TOP.vhd.md]] - Implementation docs

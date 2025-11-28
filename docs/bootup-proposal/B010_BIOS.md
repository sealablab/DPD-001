---
created: 2025-11-28
modified: 2025-11-28 02:27:01
accessed: 2025-11-28 02:26:39
---
# [B010_BIOS](docs/bootup-proposal/B010_BIOS.md)
The **BIOS** module iss part of the new [api-v4](docs/api-v4.md) calling convention.
- is a small, self-contained module that can be included that can be used to troubleshoot [mim](moku_md/instruments/mim.md) and [cloudcompile](moku_md/instruments/cloudcompile.md) related connections (predictable, safe, simple patterns output on `OutputA/B/C`)
## DEPENDENCIES
### [api-v4](docs/api-v4.md) compatible

## `RUN` + `B` (`BOOT-BIOS`)
- CR0[31] = (`R`) - (R)eady
- CR0[30] =  (`U`) - (U)ser control
- CR0[29] =  (`N`) - Clock E(N)able
- ~~CR0[28] = (`P`) - (P)rogram (BPD in this case)~~
- CR0[27] = **(`B`) - (B)OOT-BIOS**

## FEATURES

####  [api-v4](docs/api-v4.md)

# See Also
## [B000_BOOT](docs/bootup-proposal/B000_BOOT.md)
## [B100_PROG](docs/bootup-proposal/B100_PROG.md)

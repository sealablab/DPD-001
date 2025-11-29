---
created: 2025-11-28
modified: 2025-11-28 02:27:17
accessed: 2025-11-28 02:26:39
---
# [B000_BOOT](docs/bootup-proposal/B000_BOOT.md)


The **RUN_B0_BOOT** 
- is part of the new [api-v4](docs/api-v4.md) calling convention.
- is responsible for 
## DEPENDENCIES
### [api-v4](docs/api-v4.md) compatible
@JC: maybe we make this depend on the bram loader and clk divider modules ?

## `RUN` + `P` (`RUN-Program`)
- CR0[31] = (`R`) - (R)eady
- CR0[30] =  (`U`) - (U)ser control
- CR0[29] =  (`N`) - Clock E(N)able
- CR0[28] = (`P`) - (P)rogram ()

## FEATURES

# See also
## [B010_BIOS](docs/bootup-proposal/B010_BIOS.md)
## [B100_PROG](docs/bootup-proposal/B100_PROG.md)


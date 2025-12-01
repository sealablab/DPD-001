---
created: 2025-11-30
modified: 2025-11-30 13:54:18
accessed: 2025-11-30 14:38:28
publish: "true"
type: documentation
tags: 
---
# BOOT-SYNTH-START
## Overview
@JC: Keep track of your implementations to the boot-bios-loader bitstream 

NOTE: This work should / will be performed 'on main' for the sake of convenience / potentially lettign claude web workers play along.

# See also 
##  T1) [BOOT-BIOS-SYNTHESIS-GUIDE](docs/boot/BOOT-BIOS-SYNTHESIS-GUIDE.md)

## T2) [BOOT-HW-VALIDATION-PLAN](docs/boot/BOOT-HW-VALIDATION-PLAN.md)


## T3 [BOOT-HVS-state-reference](docs/boot/BOOT-HVS-state-reference.md)
- describes the allocation of precious HVS bits across the entire `BOOT` / `BIOS` / `LOAD` procedure


- B0 (complete)
- B1 (complete/stub
- L2 loader
### B0- BOOT (`complete)
 [x] [B0_BOOT_TOP.vhd](rtl/boot/B0_BOOT_TOP.vhd.md)
 Added [BootWrapper](docs/N/BootWrapper.md)
 Added [BLANK_TOP_FILE.vhd](Templater/Templates/BLANK_TOP_FILE.vhd.md) (potential template
### B1-BIOS (complete*) exists as a 'dummy' FSM but good enough for now
- FIXED: BIOS stub now uses CR0[24] as the 'return' method to BOOT loader
- 

## [L2_BUFF_LOADER.vhd](rtl/boot/L2_BUFF_LOADER.vhd.md)
- 


### 
## S2) [oscilloscope-widget-handoff](docs/boot/oscilloscope-widget-handoff.md)


---
**View this document:**
- 📖 [Obsidian Publish](https://publish.obsidian.md/dpd-001/BOOT-SYNTH-START)
- 💻 [GitHub](https://github.com/sealablab/DPD-001/blob/main/BOOT-SYNTH-START.md)
- ✏️ [Edit on GitHub](https://github.com/sealablab/DPD-001/edit/main/BOOT-SYNTH-START.md)


# 

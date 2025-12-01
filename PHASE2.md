---
created: 2025-11-30
modified: 2025-11-30 18:42:15
accessed: 2025-11-30 18:54:32
---
Claude, in this session I want you to help me with some implementation details in our 'BOOT/BIOS/LOAD' project.

# DONE

 - `BOOT_CR0` definition
 - Global BANK_SEL unification (always 4 buffers, global selector for reads)

## global ENV_BBUF allocation [[]]
- [BBUF-ALLOCATION-DRAFT](docs/boot/BBUF-ALLOCATION-DRAFT.md)

### global boot/bios/state machine definitions
- [BOOT-HVS-state-reference](docs/boot/BOOT-HVS-state-reference.md)
## global [BOOT-ROM-WAVE-TABLE](docs/N/BOOT-ROM-WAVE-TABLE.md) availability



## [BOOT-ROM-WAVE-TABLE-GEN](docs/boot/BOOT-ROM-WAVE-TABLE-GEN.md)
I think we should spend a moment to create a small standalone python utility `BOOT_ROM_WAVE_TABLE` (capitalization and spelling aside). 

the utility will serve as the reference implementation and reference __interpretation__ of the associated 
layout and contents of the
## [BOOT-ROM-WAVE-TABLE-spec](docs/boot/BOOT-ROM-WAVE-TABLE-spec.md) 
the `BOOT_ROM_WAVE_TABLE-spec`:  authoritatively describes these  layout and structure of these tables (in the abstract).  

> [!NOTE] [BOOT-ROM-WAVE-TABLE-spec](docs/boot/BOOT-ROM-WAVE-TABLE-spec.md) does __not__ define the location of the resulting files on disk. 


It exists to be a more 'abstract' description of the very concrete contents of the `BOOT-ROM-WAVE-TABLE`

tables, we need to come up with a convenient way to represent them on disk.
I __think__ I would rather spend some time creatign a `BOOT_ROM_WAVE_TABLE` python utility. It's job:
## serve 
## PHASE 2 todos (before we really synth)

- sort out global allocation of state machine states 
- [BOOT-HVS-state-reference](docs/boot/BOOT-HVS-state-reference.md)

---
created: 2025-11-28
modified: 2025-11-28 16:12:25
accessed: 2025-11-28 16:12:25
status: PRPOPOSAL
---
## STATE NAMING SCHEMES
In order to allow us to speak about these different modules with a consistent name/numbering scheme, I propose the following convention:

- `BOOT-P0`
- `BIOS-P0`
- `BUFF-P0`
- `PROG-S0`
> [!NOTE] the switch to 'Stages' for 'Program' in lieu of 'PHASES' terminology is intentional. It aligns cleanly with the 'STATE' terminiology for 'the' FSM 
> Although it is inevitable that most documentation will be __within__ the 'PROGRAM' context, this should help identify isntances when users/user-level code is trying to refer to their own internal states, while avoiding confusion between the built in `BOOT` `BIOS` and `BUFF` modules


### `BOOT-P0` : BOOT-PHASE0 
**`BOOT0-P0`** essentially represents 'instruction zero' in the boot handoff process. In this phase:
- All CR's are zero'd (by the moku platform)
- Reset and Clock will be applied by the moku platform. (See [[mim](moku_md/instruments/mim.md)] and [cloudcompile](moku_md/instruments/cloudcompile.md))

### `BOOT-P1` : 'Settled' / 'RUN'
- The platform has settled and the magical 'RUN' bits in CR0[31-29] are set.  At this point the BOOT-FSM should be engaged which will allow the python client (aka 'user') to select one of three (technically 4) possible state transitions:


> [!NOTE] From the user experience, the transition from `BOOT-P0` -> `BOOT-P1` will be the result of a user-agent typing 'RUN', thus setting CR0[31-29] and proving that the platform has indeed settle and there is a 'head' attached to this system so it can start to safely be driven. 


The follow states should be reachable from `BOOT-P1` 'RUN>' in response to the user/driver entering / selecting one of the following (which will then set the appropriately defined bit in `CR0`)
#### `BIOS-P0` (`RUNB`) -> `Run BIOS`
Control will be transferred to the BIOS module. The details of this module are out of scope for the moment, but it will be a small self-contained module that can be used to diagnose wiring/connection issues on the moku platform by reliably and safely generating known reference signals on all available outputs.

#### `LOAD-P0` (`RUNL`) -> `Run Loader`
Control will be transferred to the Buffer **L**oader  module.  -- details TBD.


#### `RESET-P0` (`RUNR`) -> `Run Reset` 
- Serves as a 'soft reset' by: 
- intentionally returning to `BOOT0-P0` with all CR's zeroized

And lastly, 
#### `PROG-P0` (`RUNP`) -> `Run Program`
Transfer control to the main application program (BPD in this case)







---
1. **BPD vs DPD**: The doc says "BPD in this case" for PROG-P0. Is this:

## Q1) BPD v DPD ?
Sorry - this is a little confusing. 
The overall boot process we are describing will and should be applicable to 'other' 'programs' (Of which `DPD` or DemoProbeDriver) is the first real 'useful' one, however. in the bootup context we are trying to simply treat this 'main' application as a generic 'PROG' or 'PROGRAM' or 'Application'.  We should keep the bootup terminology decoupled from any application specific context or uses.
## Q20)  **CR0 Bit Mapping for RUNB/RUNL/RUNR/RUNP**:

    - CR0[31:29] = RUN (established)
    - What bits encode the B/L/R/P selection? 
    We are free to decide this, but i think we should use CR0[28:25] and the order should be 'P'/'B'/'L'/'R' so that if a user starts setting the MSBs from left to right in the gui they will land on 'RUNP' first (this is actually a significant usability concern)


 
## Q3)  **Return Paths**: 
Can BIOS-P0 and LOAD-P0 return to BOOT-P1? 
Yes,  we should have a convention for this, and the python client can / will be responsible for knowing the 'calling convention' to utilize it. 

One obvious approach would be to use CR[23]-[20] for some python client->BOOT signalling. (my main point here is that we dont need to treat __All__ of CR0 as globally defined. In the early boot phase while we switch from BIOS->BOOT-P1 or LOADER->BOOT-P1 we could define a 'RET' bit or something to return to BOOT-P1 and effectively 'exit' the BIOS or BUFF Loader

## Q4) ENV_BBUF details:
We will **allocate** four individual 4K ENV_BBUFS in BRAM inside the VHDL file that implements `BOOT`. The platform will __not__ initialize them for us. As part of the transition from BOOT-P0 to BOOT-P1  we will reset these to zero. 

By allowing the BIOS or BUFF-LOADER to transition directly back to BOOT-P1 we can consitently allow the following workflow
1) BOOTUP
2) (Expert user) loads buffers RETs to BOOT-P1
3) (Exper user) transfers to BIOS
4) (Expert user) flips bits inside the BIOS that may make use of the now populated buffers.
5) (Expert user) RETS to BOOT-P1
6) (Expert user) launched 'PROGRAM' (`RUN-P`)
---
Control passes to the PROGRAM and can no longer 'reach back' without some form of reset.

## Q5) . **The Mermaid Placeholder**: 
Once we have agreed on the terminology for the different modules and states I want you to generate a marmaidjs diagram for me.


## T1) Some FSM concerns:
Although it may seem a little pedagogical, I think it would be beneficial if each of the three modules defined so far (`BOOT`, `BIOS` and `BUFF-LOADER`)utilized the canonical 6-bit FSM representation and scheme that we have tried to standardize on throughout this project. 

That means that we will actually end up with one `TOP/BOOT` level FSM inside the `BOOT` module, but that
- `BIOS` `BUFF_LOADER` and `PROG` will actually all share a __very__ similar design structure and layout. This should be considered a major design goal / win, as we have fairly advanced debugging tools that are well adapted to this pattern. 
- 
Should I replace the keyboard lock diagram with a proper BOOT-FSM state diagram, or was that intentionally left as a "fill this in" marker?



## Clarifying Questions

**Q6) FSM State Encoding for BOOT Module:**

 

You mention BOOT/BIOS/BUFF_LOADER should all use the canonical 6-bit FSM. For the BOOT module specifically, would the states map something like:

| State       | 6-bit  | Description                   |
| ----------- | ------ | ----------------------------- |
| BOOT_P0     | 000000 | Initial/Reset                 |
| BOOT_P1     | 000001 | Settled/Dispatcher            |
| BIOS_ACTIVE | 000010 | Control transferred to BIOS   |
| LOAD_ACTIVE | 000011 | Control transferred to LOADER |
| PROG_ACTIVE | 000100 | Control transferred to PROG   |
| FAULT       | 111111 | Error state                   |
|             |        |                               |

The `BOOT` module should follow the table you outlined above. And then, there will be distinct FSMs with a BIOS_P0, BIOS_P1, (in BIOS) and (BUFFLOAD_P0, BUFF_LOAD_P1), and so on. 

Our goal is to place a similar / identical 'HVS' monitoring scheme inside the 'BOOT' module, and that it will then be able to
- 'Receive' (or really, inspect) the __state__ and __status__ vectors inside each module
- Mux the appropriate Output-A/B/C from the lower down layers 'out' 

Question: If this Muxing will insert a delay cycle, in this one special case we might want to try and accomplish these assignments combinatorially.  Ideally this muxing scheme will be completely unobservable to the 'Program' code. 

**Q7) HVS Encoding for BOOT:**
See above: But yes, you have the correct idea!

**Q8) Mutual Exclusion Enforcement:**
If user sets multiple selection bits (e.g., both P and B), should hardware:
Hardware should treat this as a violation of the 'calling convention' and assert a BOOT level FAULT (which will itself by visible on OutputC using HVS encoding when wired up appropriately.)
- Go to FAULT?

**Q9) ENV_BBUF Allocation:**
The BRAMS are directly addressable after the handoff. We will need to define the exact signal routing, but the current reference app (BPD) was designed with (one) of these ENV_BBUFS in mind.



## Remaining Design Questions

**Q10) Combinatorial Mux Implementation:**
Yes, this looks like what I was expecting. This will avoid introducing delay -- right? (in general we aren't super timing sensitive, but this is something of a special case since if successfull __all__ application level outputs will end up going through it)
 

**Q11) RET Encoding:**
A single 'ret' bit that goes directly into `BOOT-P1` regardless of the 'application' running (of which the 'BIOS' and 'LOAD'er should be structually equivalent the to the 'PROG' main application)

## **Q12) FAULT Propagation:**

When a sub-module (BIOS/LOAD/PROG) enters its own FAULT state, should BOOT:
- Immediately transition to BOOT FAULT?
When 'BIOS' or 'LOAD' enter `FAULT` then `BOOT` should do the same. We can use the built-in HVS decoder to automatically reveal if we entered via 'BIOS' or 'LOAD' (or even 'BOOT' but that should be..difficult) 
`PROG` payloads asserting faults should __NOT__ be handled / caught by the 'BOOT' module in anyway. 


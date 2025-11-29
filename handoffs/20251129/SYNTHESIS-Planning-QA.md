---
status: DRAFT
date: 2025-11-29
related:
  - "[[HANDOFF-Full-Synthesis-Ready]]"
tags:
  - synthesis
  - planning
  - qa
created: 2025-11-29
modified: 2025-11-29 00:26:41
accessed: 2025-11-29 00:27:21
---

# Synthesis Planning Q&A

This document captures planning questions and decisions for moving from GHDL validation to full vendor synthesis. Edit this file to provide answers, then commit - Claude will see the diff.

# Additional context:
Review the following, then review the user responses below:
-  [BOOT-FSM-spec](docs/BOOT-FSM-spec.md) tt5r
- [boot-process-terms](docs/boot-process-terms.md)

## Synthesis Tool & Platform

### Q1: Which vendor synthesis tool do you have available?

**Answer:** Vivado-2022. 
.. here is a little bit of synth log from it
``` python
#-----------------------------------------------------------
# Vivado v2022.2_AR000035739_AR000034905 (64-bit)
# SW Build 3671981 on Fri Oct 14 04:59:54 MDT 2022
# IP Build 3669848 on Fri Oct 14 08:30:02 MDT 2022
# Start of session at: Thu Nov 27 03:53:38 2025
# Process ID: 3810638
# Current directory: /workspace/9cb16bc6-8429-4845-9320-8efad49d5cbb/output
# Command line: vivado -log synthesis.log -nojournal -mode batch -source /deps/compile/scripts/tcl/synth.tcl -tclargs /deps/compile 40 xc7z020clg400-1 mokugo /workspace/9cb16bc6-8429-4845-9320-8efad49d5cbb/src /workspace/9cb16bc6-8429-4845-9320-8efad49d5cbb/lib /workspace/9cb16bc6-8429-4845-9320-8efad49d5cbb/ipcores 2 3 0 4 4 5 3 2 0
# Log file: /workspace/9cb16bc6-8429-4845-9320-8efad49d5cbb/output/synthesis.log
# Journal file: 
# Running On: mcc-workers-7446cfdb8d-xznss, OS: Linux, CPU Frequency: 4491.536 MHz, CPU Physical cores: 28, Host memory: 50485 MB
#-----------------------------------------------------------

---------------------------------------------------------------------------------
Start Loading Part and Timing Information
---------------------------------------------------------------------------------
Loading part: xc7z020clg400-1
---------------------------------------------------------------------------------
Finished Loading Part and Timing Information : Time (s): cpu = 00:00:05 ; elapsed = 00:00:07 . Memory (MB): peak = 2690.262 ; gain = 599.301 ; free physical = 29991 ; free virtual = 42864
Synthesis current peak Physical Memory [PSS] (MB): peak = 2023.307; parent = 1769.992; children = 253.314
Synthesis current peak Virtual Memory [VSS] (MB): peak = 3621.477; parent = 2658.250; children = 963.227
---------------------------------------------------------------------------------
```

---

### Q2: What's the target FPGA device?

The specific chip we happen to be targetting is the xc7z020clg400-1 -- but most of the platform specifics are abstracted away at a high level. see @moku-models/ for some details. as well as @mim.md and @cloudcompile.md

---

## Architecture & Integration

### Q3: Unified wrapper approach preference


**Option A: Runtime-configurable**

Runtime configurable. This is the entire point of this endeavor.
- 'RUN' -> BOOT
- `RUN+P` -> PROG 
- `RUN+L` -> Loader ..

### Q4: BOOT ↔ DPD transition model

**Deployment scenarios:**

1. **Single bitstream with both subsystems**
   - BOOT diagnostic mode + DPD production mode in one package
   - Switch via runtime configuration

2. **Separate bitstreams**
   - `BOOT-diagnostics.tar` for platform validation
   - `DPD-production.tar` for normal operation

3. **DPD-only (BOOT integrated)**
   - Always start with BOOT, transition to DPD via RUNP
   - No switching back without full reset

**Questions:**
- Do you need to switch back from DPD to BOOT without reset?
- Is BOOT purely a startup subsystem, or does it need persistent availability?
- Should BOOT be available as a standalone diagnostic bitstream?

**Answer:** _(describe your preferred deployment model)_

---

## Testing & Validation

### Q5: P3 RUNP test validation priority

Current status from handoff:
- P3 tests exist (`tests/sim/boot_fsm/P3_runp.py`)
- Status: "created (untested but syntax-valid)"
- Critical test: BOOT→PROG handoff with HVS voltage transition (0.03V → 0.5V)

**Questions:**
- Should we run P3 tests before synthesis work?
- Do you have hardware access to validate HVS voltage transition on oscilloscope?
- Any known issues with the current RUNP implementation?

**Answer:** _(priority: high/medium/low, hardware availability: yes/no)_

---

### Q6: Resource budget expectations

The handoff mentions "<50% FPGA capacity" as a rough estimate.

**Questions:**
- Is 50% a hard requirement or just a guideline?
- Are there specific resource constraints?
  - LUTs (lookup tables)
  - BRAM blocks
  - DSP slices
  - IO pins
- What happens if we exceed budget? (redesign vs. upgrade FPGA)

**Answer:** _(specify constraints, or "no hard limits - just report usage")_

---

## Deployment & Timeline

### Q7: Moku CloudCompile packaging

**Questions:**
- What's the exact bitstream format expected by MCC?
- Is there documentation for the `.tar` packaging structure?
- Do you have a reference bitstream package we can examine?
- Are there signing/verification requirements?

**Answer:** _(provide links/paths to docs or reference bitstreams)_

---

### Q8: Session priority

What should we focus on in the next session?

**Options:**
- [ ] **Phase 1**: Run P3 RUNP tests + GHDL synthesis validation (safe, incremental)
- [ ] **Phase 2**: Create unified wrapper design (requires Q3/Q4 decisions)
- [ ] **Phase 3**: Vendor synthesis prep (requires Q1/Q2 answers + tool access)
- [ ] **Audit**: Review existing VHDL for synthesis issues before proceeding
- [ ] **Other**: _(specify)_

**Answer:** _(select one and explain priority)_

---

## Open Questions from Handoff

These questions were noted in `HANDOFF-Full-Synthesis-Ready.md` and remain unresolved:

1. **FORGE control in DPD_shim**
   - Current: Direct `control0_run_gate` passthrough (no redundant AND)
   - Confirm this is correct vs. double-gating

2. **CustomWrapper vs BootWrapper naming**
   - Resolution: Keep both entities, use separate test stubs
   - Vendor tools may need explicit wrapper selection

3. **ENV_BBUF lifecycle**
   - Currently: BOOT allocates, PROG reads
   - Confirm read-only access model for PROG subsystem

**Status:** _(mark "resolved" or add notes)_

---

## Decision Log

| Date | Question | Decision | Rationale |
|------|----------|----------|-----------|
| 2025-11-29 | _(example)_ | _(example)_ | _(example)_ |

---

## Notes

_(Add any additional context, constraints, or considerations here)_

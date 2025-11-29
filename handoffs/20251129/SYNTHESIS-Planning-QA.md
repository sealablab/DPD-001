---
status: DRAFT
date: 2025-11-29
related:
  - "[[HANDOFF-Full-Synthesis-Ready]]"
tags:
  - synthesis
  - planning
  - qa
---

# Synthesis Planning Q&A

This document captures planning questions and decisions for moving from GHDL validation to full vendor synthesis. Edit this file to provide answers, then commit - Claude will see the diff.

## Synthesis Tool & Platform

### Q1: Which vendor synthesis tool do you have available?

**Options:**
- [ ] Vivado (Xilinx/AMD)
- [ ] Quartus (Intel/Altera)
- [ ] Other FPGA vendor tool (specify): _____________
- [ ] Focus on GHDL synthesis validation only for now

**Answer:** _(fill in your selection)_

---

### Q2: What's the target FPGA device?

The handoff mentions "Moku:Go" but doesn't specify the exact FPGA chip. This information is needed for:
- Resource estimation
- Constraint file generation
- IP core configuration

**Answer:** _(e.g., "Xilinx Zynq-7010", "Intel Cyclone V", etc.)_

---

## Architecture & Integration

### Q3: Unified wrapper approach preference

The handoff presents two architectural options:

**Option A: Runtime-configurable**
- Single bitstream with generic parameter
- Switch between BOOT/DPD modes via configuration
- More complex routing, potential timing issues

**Option B: Compile-time selection**
- Separate bitstreams for each mode
- Cleaner for vendor tools
- Simpler resource optimization

**Answer:** _(A or B, with rationale)_

---

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

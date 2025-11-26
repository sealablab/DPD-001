# DPD-001 Documentation Index

**Last Updated:** 2025-01-28
**Project:** DPD-001 (Demo Probe Driver) - FPGA-based probe controller for Moku:Go

---

## Quick Start

For quick reference and common tasks, see [CLAUDE.md](../CLAUDE.md) in the project root.

This documentation directory contains detailed architectural notes, test design patterns, debugging guides, and FORGE framework references.

---

## Architecture & Core Concepts

### Custom Wrapper
[custom-wrapper.md](custom-wrapper.md) - **Current MCC Standard**

The CustomWrapper entity interface (Clk, Reset, InputA/B/C, OutputA/B/C, Control0-15) that DPD-001 implements. Includes FORGE control scheme (CR0[31:29]), register mapping, and I/O port usage. Critical reference for understanding DPD's top-level interface.

 
### Custom Instrument
[custom-instrument.md](custom-instrument.md) - **Future Standard**

Liquid Instruments' future "Custom Instrument" terminology with explicit ClkEn/Enable ports and state/status vectors. Comparison with CustomWrapper and migration path notes.

### HVS (Hierarchical Voltage Encoding Scheme)
[hvs.md](hvs.md) - **FSM State Debugging**

How DPD encodes FSM state + status into OutputC voltage for oscilloscope debugging. Explains 500mV state steps, ±15mV status noise, fault detection via sign flip, and digital unit conversion formulas.

### Network Register Synchronization
[network-register-sync.md](network-register-sync.md) - **Race Condition Prevention**

Why configuration registers (CR2-CR10) only update during INITIALIZING state. Explains the STATE_SYNC_SAFE protocol that prevents asynchronous network updates from corrupting active FSM operation.

### Platform Implementation Notes
[platform-implementation-notes.md](platform-implementation-notes.md) - **Moku Platform Specifications**

Hardware specifications for Moku platforms (focus on Moku:Go). Clock rates, ADC/DAC specs, I/O ranges, and platform-specific constraints for VHDL design.

---

## Testing & Validation

### Progressive Testing
[progressive-testing.md](progressive-testing.md) - **P1/P2/P3 Test Methodology**

Core testing philosophy: start minimal (P1), expand incrementally (P2/P3). Defines test levels (P1 BASIC: <20 lines output, P2 INTERMEDIATE: <50 lines, P3 COMPREHENSIVE: <100 lines). Critical for LLM-based workflows and rapid iteration.

### CocoTB Framework
[cocotb.md](cocotb.md) - **Simulation Testing**

Overview of CocoTB integration for VHDL verification. Python-based testbench framework, test structure patterns, and DPD-001 test examples.

### Test Architecture: Hierarchical Encoder
[test-architecture/forge_hierarchical_encoder_test_design.md](test-architecture/forge_hierarchical_encoder_test_design.md) - **Reference Test Design**

Comprehensive 910-line test architecture document for the HVS encoder component. Excellent reference for:
- Progressive test breakdown (P1: 4 tests, P2: 10 tests)
- Expected value calculations and VHDL arithmetic matching
- Constants file design patterns
- Signed integer handling in CocoTB
- Test wrapper design

---

## Debugging & Development Tools

### Hardware Debug Checklist
[hardware-debug-checklist.md](hardware-debug-checklist.md) - **Debugging on Real Moku**

Step-by-step workflow for debugging FSM issues on live hardware:
- Verify routing (OutputC → OscInA)
- Check FORGE control bits (CR0[31:29])
- Map oscilloscope voltage to FSM state
- Common pitfalls and solutions

### GHDL Output Filter
[ghdl-output-filter.md](ghdl-output-filter.md) - **Verbosity Management**

OS-level output filtering system that reduces GHDL verbosity by 80-98%. FilterLevel enum (AGGRESSIVE, NORMAL, MINIMAL, NONE), filter patterns, duplicate detection, and performance analysis. Critical for keeping P1 test output under 20 lines.

---

## Development Workflows

### CocoTB Test Generation Agents
[AGENTS.md](AGENTS.md) - **Agent Pipeline for Test Development**

Quick start guide for using specialized agents to generate CocoTB test suites:
- `cocotb-progressive-test-designer` - Design test architectures (P1/P2/P3)
- `cocotb-progressive-test-runner` - Implement and execute tests
- `cocotb-integration-test` - Restructure existing tests

Includes invocation examples, phase contracts, and common workflows.

---

## File Organization

```
docs/
├── README.md (this file)
│
├── Architecture & Core Concepts
│   ├── custom-wrapper.md            # Current MCC interface standard
│   ├── custom-instrument.md          # Future MCC interface standard
│   ├── hvs.md                        # FSM state debugging via voltage
│   ├── network-register-sync.md      # CR sync protocol
│   └── platform-implementation-notes.md  # Moku hardware specs
│
├── Testing & Validation
│   ├── progressive-testing.md        # P1/P2/P3 methodology
│   ├── cocotb.md                     # CocoTB framework overview
│   └── test-architecture/
│       └── forge_hierarchical_encoder_test_design.md  # Reference design
│
├── Debugging & Tools
│   ├── hardware-debug-checklist.md   # Hardware debugging workflow
│   └── ghdl-output-filter.md         # GHDL verbosity filtering
│
└── Development Workflows
    └── AGENTS.md                     # CocoTB agent pipeline
```

---

## Migration Notes

Many of these documents were migrated from the FORGE-V5 project (`/Users/johnycsh/Forge/BPD-Dev-v5/docs/FORGE-V5`) and expanded with DPD-001-specific implementation details.

**Migration Date:** 2025-01-28
**Source:** FORGE-V5 standalone notes (refactored and validated)

---

## See Also

- [CLAUDE.md](../CLAUDE.md) - Quick reference and build commands
- [N/CLAUDE.md](../N/CLAUDE.md) - Comprehensive project guide
- [rtl/DPD-RTL.yaml](../rtl/DPD-RTL.yaml) - Register specification
- [tests/sim/](../tests/sim/) - CocoTB simulation tests
- [tests/hw/](../tests/hw/) - Hardware validation tests

---

**Maintainer:** Moku Instrument Forge Team
**Last Updated:** 2025-01-28

# FORGE Agent Workflow

**Version:** 1.0.0
**Purpose:** Agent invocation patterns for VHDL component development
**Last Updated:** 2025-11-11

---

## Executive Summary

This document describes the **4-agent workflow** for developing new VHDL components in the FORGE monorepo, from requirements elicitation through test execution.

**Agent Chain:**
```
User Request
    ↓
Agent #0: forge-new-component          (Requirements & scaffolding)
    ↓ (creates placeholder .md files)
Agent #1: forge-vhdl-component-generator  (VHDL implementation)
    ↓ (implements .vhd files)
Agent #2: cocotb-progressive-test-designer  (Test architecture design)
    ↓ (designs test strategy)
Agent #3: cocotb-progressive-test-runner  (Test implementation & execution)
    ↓ (implements & runs tests)
Done ✅
```

---

## Agent Locations

**All agents located in:** `.claude/agents/`

| Agent | Purpose | Files |
|-------|---------|-------|
| **forge-new-component** | Requirements elicitation, file scaffolding | `agent.md` |
| **forge-vhdl-component-generator** | VHDL-2008 code generation | `agent.md` |
| **cocotb-progressive-test-designer** | Test architecture design | `agent.md`, `README.md` |
| **cocotb-progressive-test-runner** | Test implementation & execution | `agent.md`, `README.md` |

**Pre-Flight Validation:** `.claude/agents/validate_agent_inputs.md`

---

## Agent Responsibilities

### Agent #0: forge-new-component

**What it does:**
- Elicits requirements through iterative questioning (2-3 rounds)
- Determines file structure based on component type
- Creates placeholder `.md` files with specifications
- Specifies which agent should implement each placeholder

**What it does NOT do:**
- ❌ Implement VHDL code
- ❌ Implement test code
- ❌ Run any agents

**Input:** User's high-level component idea ("I need a PWM generator")

**Output:**
- Placeholder files: `<filename>.vhd.md`, `<filename>.py.md`
- Summary report with next steps

**Example Output Structure:**
```
vhdl/components/utilities/forge_util_pwm.vhd.md
cocotb_tests/components/forge_util_pwm_tests/
├── forge_util_pwm_constants.py.md
├── P1_forge_util_pwm_basic.py.md
└── __init__.py (created)
cocotb_tests/components/test_forge_util_pwm_progressive.py.md
```

---

### Agent #1: forge-vhdl-component-generator

**What it does:**
- Generates VHDL-2008 synthesis-ready code
- Follows VHDL coding standards (no enums, std_logic_vector FSM states)
- Ensures GHDL simulation compatibility
- Can instantiate forge-vhdl library components

**What it does NOT do:**
- ❌ Design test architectures
- ❌ Run tests
- ❌ Generate test code

**Input:**
- Specification from placeholder file (`.vhd.md`)
- OR direct user specification

**Output:**
- VHDL entity + architecture
- Synthesis-ready code
- GHDL-compatible patterns

**Critical Standards:**
- FSM states: `std_logic_vector` (NOT enums)
- Port order: clk, rst_n, clk_en, enable, data, status
- Reset hierarchy: `rst_n > clk_en > enable`

---

### Agent #2: cocotb-progressive-test-designer

**What it does:**
- Analyzes VHDL component for testability
- Designs progressive test strategy (P1/P2/P3 levels)
- Plans test wrappers for CocoTB compatibility
- Calculates expected values matching VHDL arithmetic
- Defines test infrastructure (constants, helpers, orchestrators)

**What it does NOT do:**
- ❌ Implement test code
- ❌ Run tests
- ❌ Debug GHDL issues

**Input:**
- VHDL component from Agent #1
- Component specification

**Output:**
- Test architecture document
- Constants file design
- Test module pseudocode (P1/P2/P3)
- Test wrapper VHDL (if needed)
- test_configs.py entry design

**Key Design Principles:**
- P1: 2-4 tests, <20 line output, <5s runtime
- P2: 5-10 tests, <50 line output, <30s runtime
- Match VHDL arithmetic (integer division `//` not `/`)
- CocoTB type constraints (only std_logic, signed, unsigned at entity ports)

---

### Agent #3: cocotb-progressive-test-runner

**What it does:**
- Implements Python test code from design specs
- Executes tests via CocoTB + GHDL
- Debugs test failures (signal access, timing, GHDL errors)
- Iterates on implementation until tests pass
- Validates output quality (<20 lines P1)

**What it does NOT do:**
- ❌ Design test architectures (receives from Agent #2)
- ❌ Generate VHDL components
- ❌ Redesign test strategy without designer input

**Input:**
- Test architecture document from Agent #2
- Test strategy and expected values

**Output:**
- Working test suite files
- Test wrapper VHDL (if needed)
- test_configs.py entry
- Test execution report (all passing)

**Git Workflow:** Commit after each fix/milestone (incremental commits)

**Critical Patterns:**
- Signed integer access: `dut.voltage_out.value.signed_integer`
- Integer division: `(value * 100) // 128` (match VHDL truncation)
- Reset polarity: Check VHDL (`reset='1'` vs `rst_n='0'`)

---

## Invocation Patterns

### Pattern 1: Sequential Workflow (RECOMMENDED for Complex Components)

**Use when:** Component requirements are complex or unclear

```
Step 1: Requirements & Scaffolding
→ Invoke: forge-new-component
→ Input: High-level component idea
→ Output: Placeholder files + specifications

Step 2: VHDL Implementation
→ Invoke: forge-vhdl-component-generator
→ Input: Specification from <component>.vhd.md
→ Output: Working VHDL component

Step 3: Test Design
→ Invoke: cocotb-progressive-test-designer
→ Input: VHDL component from Step 2
→ Output: Test architecture document

Step 4: Test Implementation & Execution
→ Invoke: cocotb-progressive-test-runner
→ Input: Test architecture from Step 3
→ Output: Passing test suite
```

**Example User Request:**
> "I need a PWM generator for controlling motor speed"

**Agent Sequence:**
1. `forge-new-component` → Clarify frequency range, duty cycle resolution, outputs
2. `forge-vhdl-component-generator` → Generate `forge_util_pwm.vhd`
3. `cocotb-progressive-test-designer` → Design P1/P2 test strategy
4. `cocotb-progressive-test-runner` → Implement & run tests

---

### Pattern 2: Parallel Workflow (For Well-Defined Specs)

**Use when:** Component specification is crystal clear

**Optimization:** Agents #1 and #2 can run in **parallel**

```
Step 0: Requirements (if needed)
→ forge-new-component

Step 1a: VHDL Implementation (parallel)
→ forge-vhdl-component-generator

Step 1b: Test Design (parallel)
→ cocotb-progressive-test-designer

Step 2: Test Implementation (waits for both 1a & 1b)
→ cocotb-progressive-test-runner
```

**Conditions for Parallel Execution:**
- ✅ VHDL entity interface fully defined
- ✅ Component behavior clearly specified
- ✅ No ambiguity in requirements

**Example User Request:**
> "Implement this entity: [provides complete VHDL entity signature]"

---

### Pattern 3: Test-Only Workflow (Existing VHDL)

**Use when:** VHDL component already exists, just needs tests

```
Step 1: Test Design
→ Invoke: cocotb-progressive-test-designer
→ Input: Existing VHDL component
→ Output: Test architecture

Step 2: Test Implementation & Execution
→ Invoke: cocotb-progressive-test-runner
→ Input: Test architecture from Step 1
→ Output: Passing test suite
```

**Example User Request:**
> "Add CocoTB tests to my existing counter module"

---

## Pre-Flight Validation

**CRITICAL:** Always validate inputs before invoking agents to prevent cascade failures.

**Validation Checklist:** `.claude/agents/validate_agent_inputs.md`

### Before Agent #1 (VHDL Generator)

- [ ] Specification file exists
- [ ] All required sections present (Metadata, Overview, Requirements, Interface, Behavior, Testing)
- [ ] No "TODO" or "TBD" placeholders in critical sections
- [ ] Interface fully defined (ports, types, widths)
- [ ] At least 3 P1 tests defined in spec
- [ ] Standards compliance confirmed (VHDL-2008, no enums)

### Before Agent #2 (Test Designer)

- [ ] VHDL file exists from Agent #1
- [ ] VHDL syntax is valid (parseable by GHDL)
- [ ] Entity ports match specification
- [ ] No CocoTB-incompatible types in ports (real, boolean, time, natural)
- [ ] GHDL is installed and accessible

### Before Agent #3 (Test Runner)

- [ ] Test architecture document exists from Agent #2
- [ ] VHDL file still valid and unchanged
- [ ] Test directory exists: `cocotb_tests/components/`
- [ ] GHDL installed (`which ghdl`)
- [ ] Python environment has cocotb, forge_cocotb packages (`uv sync` completed)
- [ ] Test runner script exists: `cocotb_tests/run.py`

**If validation fails:** Fix issues before proceeding. Agents cannot recover from bad inputs.

---

## Common Usage Scenarios

### Scenario 1: New Utility Component

**User Request:** "Create a clock divider with programmable divisor"

**Workflow:**
1. `forge-new-component` → Category: utilities, elicit divisor range/width
2. `forge-vhdl-component-generator` → Generate `forge_util_clk_divider.vhd`
3. `cocotb-progressive-test-designer` → Design P1 tests (reset, basic divide-by-2, enable control)
4. `cocotb-progressive-test-runner` → Implement & run tests

**Output:**
- `vhdl/components/utilities/forge_util_clk_divider.vhd`
- `cocotb_tests/components/forge_util_clk_divider_tests/` (full test suite)

---

### Scenario 2: New Package (Functions/Procedures)

**User Request:** "Create voltage conversion functions for 3.3V domain"

**Workflow:**
1. `forge-new-component` → Category: packages, determine conversion functions needed
2. `forge-vhdl-component-generator` → Generate `forge_voltage_3v3_pkg.vhd`
3. `cocotb-progressive-test-designer` → Design test wrapper (packages need wrappers!)
4. `cocotb-progressive-test-runner` → Implement wrapper + tests

**Output:**
- `vhdl/packages/forge_voltage_3v3_pkg.vhd`
- `cocotb_tests/cocotb_test_wrappers/forge_voltage_3v3_pkg_tb_wrapper.vhd` (wrapper)
- `cocotb_tests/components/forge_voltage_3v3_pkg_tests/` (full test suite)

**Note:** Packages REQUIRE test wrappers because:
- Packages can't be top-level entities
- May use real/boolean types internally

---

### Scenario 3: Complex FSM Component

**User Request:** "Implement trigger controller FSM for BPD"

**Workflow:**
1. `forge-new-component` → Clarify states, transitions, control signals (iterative!)
2. Validation → Check FSM states specified as std_logic_vector (NOT enums)
3. `forge-vhdl-component-generator` → Generate FSM with std_logic_vector states
4. `cocotb-progressive-test-designer` → Design state transition tests
5. `cocotb-progressive-test-runner` → Implement & run tests

**Critical:** FSM states MUST use `std_logic_vector`, NOT Verilog-incompatible enums

---

## Handoff Protocols

### Agent #0 → Agent #1

**What Agent #0 provides:**
- Placeholder file: `<component>.vhd.md`
- Component specification (entity, ports, behavior)

**What Agent #1 needs to know:**
- Read placeholder file completely
- Follow specification exactly
- Apply VHDL coding standards
- Remove `.md` placeholder when done

---

### Agent #1 → Agent #2

**What Agent #1 provides:**
- VHDL entity + architecture
- Component implementation

**What Agent #2 needs to know:**
- Analyze entity ports for CocoTB compatibility
- Design test strategy matching component complexity
- Calculate expected values matching VHDL arithmetic
- Design wrapper if needed

---

### Agent #2 → Agent #3

**What Agent #2 provides:**
- Test architecture document
- Test strategy (P1/P2/P3 breakdown)
- Constants file design
- Expected value calculations
- Test wrapper design (if needed)

**What Agent #3 needs to know:**
- Implement test code from design specs (don't redesign!)
- Follow Python patterns from design
- Match VHDL arithmetic exactly (integer division!)
- Commit after each fix/milestone
- Validate output <20 lines for P1

---

## Error Recovery

### If Agent #1 Produces Invalid VHDL

**Symptoms:**
- GHDL compilation errors
- Entity ports don't match specification
- Uses forbidden types (enums, records at entity ports)

**Recovery:**
1. Review VHDL against specification
2. Check VHDL coding standards compliance
3. Re-invoke Agent #1 with corrections
4. OR manually fix VHDL

**Do NOT proceed to Agent #2 until VHDL is valid!**

---

### If Agent #2 Produces Incomplete Test Architecture

**Symptoms:**
- Missing expected value calculations
- Test strategy unclear (>4 tests in P1)
- Wrapper needed but not designed

**Recovery:**
1. Review test architecture document
2. Ask Agent #2 to clarify/refine design
3. Ensure expected values match VHDL arithmetic
4. Confirm wrapper design if needed

**Do NOT proceed to Agent #3 until test architecture is complete!**

---

### If Agent #3 Tests Fail

**Symptoms:**
- Assertion failures
- GHDL runtime errors
- Output >20 lines for P1

**Recovery (Agent #3 should handle these):**
1. **Check signed integer access:** `dut.signal.value.signed_integer`
2. **Check integer division:** Use `//` not `/` (match VHDL truncation)
3. **Check reset polarity:** Active-high vs active-low
4. **Check timing:** Wait correct number of cycles for registered outputs
5. **Check GHDL filter:** Enable aggressive filtering for output reduction

**If test design is wrong:** Hand back to Agent #2 for redesign

---

## Integration with Existing Agents

**This repository also has:**
- `cocotb-integration-test` - Integration testing (cross-component)
- `deployment-orchestrator` - FPGA deployment automation
- `hardware-debug` - Hardware debugging utilities

**Workflow Position:**
```
Component Development (Agents #0-#3)
    ↓
Integration Testing (cocotb-integration-test)
    ↓
Deployment (deployment-orchestrator)
    ↓
Hardware Debug (hardware-debug)
```

**Agent #0-#3 scope:** Single component development (unit level)
**Integration agent scope:** Multi-component interaction (system level)

---

## Best Practices

### For AI Using These Agents

1. **Always read agent.md files** - They contain complete specifications
2. **Follow pre-flight validation** - Prevents cascade failures
3. **Respect agent boundaries** - Don't ask test-runner to redesign tests
4. **Use sequential workflow for complex components** - Clearer handoffs
5. **Commit granularly** - After each agent completes or significant fix
6. **Reference agent documentation** - Point user to agent locations

### For Users Requesting Components

1. **Start with clear requirements** - Helps Agent #0 scaffold correctly
2. **Be specific about interfaces** - Reduces iteration rounds
3. **Trust the workflow** - Let agents do their specialized tasks
4. **Review specifications** - Before Agent #1 implements VHDL
5. **Validate early** - Check VHDL before running tests

---

## Quick Reference

### File Locations

**Agent Definitions:**
- `.claude/agents/forge-new-component/agent.md`
- `.claude/agents/forge-vhdl-component-generator/agent.md`
- `.claude/agents/cocotb-progressive-test-designer/agent.md`
- `.claude/agents/cocotb-progressive-test-runner/agent.md`

**Validation:**
- `.claude/agents/validate_agent_inputs.md`

**Documentation:**
- `.claude/shared/AGENT_WORKFLOW.md` (this file)
- `CLAUDE.md` (root architecture guide)
- `llms.txt` (quick reference)

### Key Standards

**VHDL Coding Standards:**
- FSM states: `std_logic_vector` (NOT enums)
- Port order: clk, rst_n, clk_en, enable, data, status
- Reset hierarchy: `rst_n > clk_en > enable`

**Testing Standards:**
- P1: 2-4 tests, <20 lines, <5s
- P2: 5-10 tests, <50 lines, <30s
- CocoTB types: std_logic, signed, unsigned only

**References:**
- `docs/VHDL_CODING_STANDARDS.md`
- `docs/COCOTB_TROUBLESHOOTING.md`
- `CLAUDE.md`

---

**Version:** 1.0.0
**Maintained By:** Moku Instrument FORGE Team
**Last Updated:** 2025-11-11

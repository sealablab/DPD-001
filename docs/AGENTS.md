# CocoTB Test Generation Agents

**Quick Start Guide** for using specialized agents to generate and manage CocoTB test suites for VHDL components.

---

## Overview

This repository contains **3 specialized agents** for CocoTB test generation, part of a larger 4-agent workflow for VHDL component development:

| Agent | Purpose | Status |
|-------|---------|--------|
| **cocotb-integration-test** | Restructure existing tests or create new integration test suites | ✅ Production |
| **cocotb-progressive-test-designer** | Design test architectures (Agent #2) | ✅ Production |
| **cocotb-progressive-test-runner** | Implement and execute tests (Agent #3) | ✅ Production |

**Location:** `.claude/agents/`

---

## Quick Start: Simple Workflow

### Scenario: Add Tests to Existing VHDL Component

```markdown
# Step 1: Design Test Architecture
I have a VHDL component at `rtl/my_component.vhd` that needs CocoTB tests.

Please read:
- .claude/agents/cocotb-progressive-test-designer/agent.md
- rtl/my_component.vhd

Then design a progressive test architecture (P1/P2/P3) for this component.
```

**Agent Output:** Test architecture document with P1/P2/P3 strategy, expected values, and wrapper design (if needed).

```markdown
# Step 2: Implement and Run Tests
I have a test architecture document from the designer agent.

Please read:
- .claude/agents/cocotb-progressive-test-runner/agent.md
- [The test architecture document from Step 1]

Then implement the test code and run it. Commit after each milestone.
```

**Agent Output:** Working test suite with all P1 tests passing, <20 lines output.

---

## Detailed Workflow & Contracts

### Complete 4-Agent Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 0: Requirements & Scaffolding                         │
│ Agent: forge-new-component                                   │
│                                                              │
│ Input:  "I need a PWM generator"                            │
│ Output: Placeholder files (.vhd.md, .py.md)                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: VHDL Implementation                                │
│ Agent: forge-vhdl-component-generator                        │
│                                                              │
│ Input:  Specification from .vhd.md placeholder              │
│ Output: VHDL entity + architecture (synthesis-ready)        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 2: Test Architecture Design                          │
│ Agent: cocotb-progressive-test-designer                     │
│                                                              │
│ Input:  VHDL component from Phase 1                         │
│ Output: Test architecture document                          │
│         - P1/P2/P3 test strategy                            │
│         - Expected value calculations                        │
│         - Test wrapper design (if needed)                   │
│         - Constants file structure                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 3: Test Implementation & Execution                   │
│ Agent: cocotb-progressive-test-runner                        │
│                                                              │
│ Input:  Test architecture from Phase 2                      │
│ Output: Working test suite                                  │
│         - Constants file                                    │
│         - P1/P2/P3 test modules                             │
│         - Progressive orchestrator                          │
│         - test_configs.py entry                             │
│         - All P1 tests passing (<20 lines output)           │
└─────────────────────────────────────────────────────────────┘
```

---

## Agent Invocation Examples

### 1. cocotb-integration-test

**Use Case:** Restructure existing tests or create new integration test suites.

**Example 1: Restructure Existing Tests**

```markdown
I have CocoTB tests in `tests/legacy/test_my_module.py` that need to follow 
forge-vhdl progressive testing standards.

Please read:
- .claude/agents/cocotb-integration-test/agent.md
- libs/forge-vhdl/CLAUDE.md (testing standards)
- tests/legacy/test_my_module.py (existing tests)

Then restructure to forge-vhdl progressive pattern (P1/P2/P3).
```

**Expected Output:**
```
tests/
├── test_configs.py
├── test_my_module_progressive.py
└── my_module_tests/
    ├── __init__.py
    ├── my_module_constants.py
    ├── P1_my_module_basic.py      # 2-4 tests, <20 lines
    ├── P2_my_module_intermediate.py
    └── P3_my_module_comprehensive.py
```

**Example 2: Create New Integration Tests**

```markdown
I need to create CocoTB integration tests for my VHDL system.

Please read:
- .claude/agents/cocotb-integration-test/agent.md
- rtl/DPD_main.vhd
- rtl/DPD_shim.vhd
- rtl/DPD.vhd

Create a progressive test suite following forge-vhdl standards.
```

---

### 2. cocotb-progressive-test-designer

**Use Case:** Design test architecture for a VHDL component (Agent #2 in workflow).

**Example: Design Tests for New Component**

```markdown
I have a VHDL component that needs test architecture designed.

Please read:
- .claude/agents/cocotb-progressive-test-designer/agent.md
- rtl/forge_util_clk_divider.vhd
- CLAUDE.md (testing standards)

Design a progressive test architecture (P1/P2/P3) for this component.
Include expected value calculations and test wrapper design if needed.
```

**Expected Output:**
```markdown
# Test Architecture: forge_util_clk_divider

## Component Analysis
- Entity: forge_util_clk_divider
- Category: utilities
- CocoTB compatibility: ✅ (all std_logic ports)

## Test Strategy

### P1 - BASIC (3 tests, <20 lines)
1. Reset behavior - Verify output cleared
2. Divide by 2 - Basic divider operation
3. Enable control - Enable starts/stops operation

### P2 - INTERMEDIATE (7 tests, <50 lines)
1-3. (P1 tests)
4. Divide by max - Boundary: max divisor
5. Divide by 1 - Boundary: min divisor
6. Enable during count - State change mid-operation
7. Rapid enable toggle - Stress test

## Constants File Design
- MODULE_NAME: "forge_util_clk_divider"
- HDL_SOURCES: [rtl/forge_util_clk_divider.vhd]
- TestValues: P1_COUNT_MAX=20, P2_COUNT_MAX=1000
- Helper functions: get_count(), get_done()

## Expected Values
- Calculation: cycles // divisor (match VHDL integer division)
```

**Contract:**
- **Input:** VHDL component entity + architecture
- **Output:** Test architecture document (markdown)
- **Does NOT:** Implement test code or run tests

---

### 3. cocotb-progressive-test-runner

**Use Case:** Implement and execute tests from design (Agent #3 in workflow).

**Example: Implement Tests from Design**

```markdown
I have a test architecture document from the designer agent.

Please read:
- .claude/agents/cocotb-progressive-test-runner/agent.md
- [Test architecture document from designer]
- rtl/forge_util_clk_divider.vhd

Implement the test code and run it. Commit after each milestone.
```

**Expected Output:**
```
cocotb_tests/components/
├── test_forge_util_clk_divider_progressive.py
└── forge_util_clk_divider_tests/
    ├── __init__.py
    ├── forge_util_clk_divider_constants.py
    ├── P1_forge_util_clk_divider_basic.py
    └── [P2/P3 modules if implemented]

# Test execution:
Running CocoTB tests for forge_util_clk_divider (P1_BASIC)...
✓ Reset behavior                                    PASS
✓ Divide by 2                                       PASS
✓ Enable control                                    PASS

3/3 tests passed (0 failed)
Runtime: 2.3s
Output: 8 lines (60% under target)
```

**Contract:**
- **Input:** Test architecture document from designer
- **Output:** Working test suite + execution report
- **Does NOT:** Redesign test architecture (receives from designer)

---

## Phase Contracts Summary

### Phase 0: Requirements (forge-new-component)

**Input Contract:**
- User's high-level component idea
- Optional: Component type, category

**Output Contract:**
- Placeholder `.vhd.md` file with specification
- Placeholder test files (`.py.md`)
- Summary report with next steps

**Validation:**
- [ ] All required sections present (Metadata, Overview, Requirements, Interface, Behavior)
- [ ] No "TODO" or "TBD" in critical sections
- [ ] Interface fully defined

---

### Phase 1: VHDL Implementation (forge-vhdl-component-generator)

**Input Contract:**
- Specification from `.vhd.md` placeholder
- OR direct user specification

**Output Contract:**
- VHDL entity + architecture
- Synthesis-ready code
- GHDL-compatible patterns

**Validation:**
- [ ] VHDL syntax valid (GHDL parseable)
- [ ] Entity ports match specification
- [ ] No forbidden types (enums, records at ports)
- [ ] FSM states use `std_logic_vector` (NOT enums)

---

### Phase 2: Test Design (cocotb-progressive-test-designer)

**Input Contract:**
- VHDL component from Phase 1
- Component specification

**Output Contract:**
- Test architecture document (markdown)
- P1/P2/P3 test strategy
- Expected value calculations
- Test wrapper design (if needed)
- Constants file structure
- test_configs.py entry design

**Validation:**
- [ ] P1: 2-4 tests, <20 lines target
- [ ] P2: 5-10 tests, <50 lines target
- [ ] Expected values match VHDL arithmetic (integer division!)
- [ ] CocoTB type constraints assessed
- [ ] Wrapper designed if needed

---

### Phase 3: Test Implementation (cocotb-progressive-test-runner)

**Input Contract:**
- Test architecture document from Phase 2
- Test strategy and expected values
- Constants file design

**Output Contract:**
- Working test suite files
- Test wrapper VHDL (if needed)
- test_configs.py entry
- Test execution report

**Validation:**
- [ ] All P1 tests pass (green)
- [ ] Output <20 lines (GHDL filter enabled)
- [ ] Runtime <5 seconds
- [ ] No GHDL errors/warnings
- [ ] Signed integer access correct (`.signed_integer` where needed)
- [ ] Integer division matches VHDL (`//` not `/`)

---

## Common Workflows

### Workflow A: Test-Only (Existing VHDL)

**When:** VHDL component already exists, just needs tests.

```
Step 1: Design
→ Invoke: cocotb-progressive-test-designer
→ Input: Existing VHDL component
→ Output: Test architecture document

Step 2: Implement
→ Invoke: cocotb-progressive-test-runner
→ Input: Test architecture from Step 1
→ Output: Passing test suite
```

**Example:**
```markdown
# Step 1
Please read .claude/agents/cocotb-progressive-test-designer/agent.md
and rtl/my_component.vhd, then design test architecture.

# Step 2
Please read .claude/agents/cocotb-progressive-test-runner/agent.md
and implement the tests from the architecture document.
```

---

### Workflow B: Restructure Existing Tests

**When:** Have existing tests that need to follow forge-vhdl standards.

```
Step 1: Restructure
→ Invoke: cocotb-integration-test
→ Input: Existing test files
→ Output: Restructured P1/P2/P3 test suite
```

**Example:**
```markdown
I have tests in tests/legacy/test_my_module.py that need restructuring.

Please read:
- .claude/agents/cocotb-integration-test/agent.md
- tests/legacy/test_my_module.py

Restructure to forge-vhdl progressive pattern.
```

---

### Workflow C: Full Component Development

**When:** Creating new component from scratch.

```
Step 0: Requirements
→ Invoke: forge-new-component
→ Output: Placeholder files

Step 1: VHDL
→ Invoke: forge-vhdl-component-generator
→ Output: VHDL component

Step 2: Test Design
→ Invoke: cocotb-progressive-test-designer
→ Output: Test architecture

Step 3: Test Implementation
→ Invoke: cocotb-progressive-test-runner
→ Output: Passing tests
```

---

## Key Principles

### Progressive Testing (P1/P2/P3)

- **P1 - BASIC:** 2-4 essential tests, <20 lines output, <5s runtime
- **P2 - INTERMEDIATE:** 5-10 tests, <50 lines output, <30s runtime
- **P3 - COMPREHENSIVE:** 10-25 tests, <100 lines output, <2min runtime

**Golden Rule:** "If your P1 test output exceeds 20 lines, you're doing it wrong."

### CocoTB Type Constraints

**FORBIDDEN on entity ports:**
- ❌ `real`, `boolean`, `time`, `file`, custom records

**ALLOWED on entity ports:**
- ✅ `std_logic`, `std_logic_vector`, `signed`, `unsigned`

**Solution:** Create test wrapper to convert forbidden types.

### VHDL Arithmetic Matching

**Critical:** Python expected values must match VHDL arithmetic (integer division, truncation).

```python
# ❌ WRONG: Python rounds
expected = int((value / 100.0) * 0xFFFF + 0.5)

# ✅ CORRECT: Match VHDL truncation
expected = (value * 0xFFFF) // 100  # Integer division
```

---

## Quick Reference

### Agent Locations

```
.claude/agents/
├── cocotb-integration-test/
│   ├── agent.md
│   └── README.md
├── cocotb-progressive-test-designer/
│   ├── agent.md
│   └── README.md
└── cocotb-progressive-test-runner/
    ├── agent.md
    └── README.md
```

### Shared Documentation

```
.claude/shared/
├── AGENT_WORKFLOW.md          # Complete 4-agent workflow
├── PYTHON_INVOCATION.md       # Python/uv invocation patterns
├── ARCHITECTURE_OVERVIEW.md
├── CONTEXT_MANAGEMENT.md
└── DUPLICATE_FILES_ANALYSIS.md
```

### Test Execution

```bash
# Navigate to test directory first (CRITICAL!)
cd tests/sim/dpd_wrapper_tests

# Run P1 tests (default)
uv run python run.py

# Run P2 tests
TEST_LEVEL=P2_INTERMEDIATE uv run python run.py

# Run P3 tests
TEST_LEVEL=P3_COMPREHENSIVE uv run python run.py

# Debug mode (no filter)
GHDL_FILTER_LEVEL=none uv run python run.py
```

---

## Troubleshooting

### Test Output >20 Lines

1. Enable aggressive GHDL filter: `GHDL_FILTER_LEVEL=aggressive`
2. Reduce P1 test count (2-4 tests only)
3. Remove print statements (use `self.log()` instead)

### Signed Integer Access Errors

```python
# ❌ WRONG
output = int(dut.voltage_out.value)

# ✅ CORRECT
output = int(dut.voltage_out.value.signed_integer)
```

### Integer Division Mismatch

```python
# ❌ WRONG: Python float division
offset = (value * 100) / 128

# ✅ CORRECT: Match VHDL truncation
offset = (value * 100) // 128
```

### Import Errors

**Problem:** Cannot find `forge_cocotb` module

**Solution:** `forge_cocotb` is a uv-managed package. Use `uv run python` and import normally (NO `sys.path` manipulation).

---

## See Also

- **Full Workflow:** `.claude/shared/AGENT_WORKFLOW.md`
- **Python Patterns:** `.claude/shared/PYTHON_INVOCATION.md`
- **Agent Details:** Individual `agent.md` files in each agent directory

---

**Last Updated:** 2025-11-25  
**Version:** 1.0


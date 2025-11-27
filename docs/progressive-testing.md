# Progressive Testing

**Last Updated:** 2025-01-28 (migrated from FORGE-V5)  
**Maintainer:** Moku Instrument Forge Team

> **Migration Note:** This document was migrated from FORGE-V5 and expanded with DPD-001-specific examples and implementation details.

---

**Progressive Testing** is at the heart of the [Agent Pipeline](../.claude/agents/) and the FORGE-V5 ecosystem.

**Progressive testing** is the idea that Agents (and humans for that matter) can get farther faster if they start with very basic hardware validation tests and then progressively iterate and refine them.

Towards that end, the FORGE-V5 system (and DPD-001) outlines the following rules defining four phases of progressive tests.

---

## Test Level Philosophy

### Core Principle

**Start minimal, expand incrementally.**

Each test level builds upon the previous, adding complexity only after basic functionality is proven. This approach:

- **Reduces context consumption** for LLM-based workflows (P1 tests produce <20 lines of output)
- **Enables rapid iteration** (P1 tests run in <5 seconds)
- **Provides clear progression** from basic to comprehensive validation
- **Minimizes debugging time** by catching issues early

### Test Level Hierarchy

```
P1 (BASIC)          → Essential smoke tests only
    ↓
P2 (INTERMEDIATE)   → Core functionality + edge cases
    ↓
P3 (COMPREHENSIVE)   → Full feature coverage + stress tests
    ↓
P4 (EXHAUSTIVE)      → Debug-level, all permutations (optional)
```

---

## Test Level Definitions

### P1 - BASIC (Essential Only)

**Purpose:** Prove the component works at a fundamental level.

**Characteristics:**
- **Test Count:** 2-5 tests (minimal)
- **Output:** <20 lines (LLM-friendly)
- **Runtime:** <5 seconds
- **Coverage:** Essential functionality only

**Typical P1 Tests:**
1. Reset behavior (outputs go to safe state)
2. Basic operation (one simple use case)
3. Critical feature (one key capability)

**Example from DPD-001:**
```python
# tests/sim/dpd_wrapper_tests/P1_dpd_wrapper_basic.py

class DPDWrapperBasicTests(TestBase):
    async def run_p1_basic(self):
        await self.test("Reset behavior", self.test_reset)
        await self.test("FORGE control", self.test_forge_control)
        await self.test("FSM software trigger", self.test_fsm_software_trigger)
        await self.test("FSM hardware trigger", self.test_fsm_hardware_trigger)
        await self.test("Output pulses", self.test_output_pulses)
```

**Output Example:**
```
P1 - BASIC TESTS
  T1: Reset behavior ✓
  T2: FORGE control ✓
  T3: FSM software trigger ✓
  T4: FSM hardware trigger ✓
  T5: Output pulses ✓
  
Summary: 5 passed, 0 failed
```

---

### P2 - INTERMEDIATE (Core Functionality)

**Purpose:** Validate all major features and common edge cases.

**Characteristics:**
- **Test Count:** 5-15 tests
- **Output:** <50 lines
- **Runtime:** <30 seconds
- **Coverage:** All major features + edge cases

**Typical P2 Tests:**
- All P1 tests (included)
- Boundary conditions
- Error handling
- State transition edge cases
- Timing variations

**Example from DPD-001:**
```python
# tests/sim/dpd_wrapper_tests/P2_dpd_wrapper_intermediate.py (when implemented)

class DPDWrapperIntermediateTests(TestBase):
    async def run_p2_intermediate(self):
        # Include all P1 tests
        await self.run_p1_basic()
        
        # P2-specific tests
        await self.test("Timeout handling", self.test_timeout)
        await self.test("Fault detection", self.test_fault_detection)
        await self.test("Auto-rearm", self.test_auto_rearm)
        await self.test("Cooldown period", self.test_cooldown)
```

---

### P3 - COMPREHENSIVE (Full Coverage)

**Purpose:** Complete validation including stress tests and corner cases.

**Characteristics:**
- **Test Count:** 15-50 tests
- **Output:** <100 lines
- **Runtime:** <2 minutes
- **Coverage:** All features + stress tests + corner cases

**Typical P3 Tests:**
- All P1 and P2 tests (included)
- Stress tests (rapid state changes)
- Corner cases (boundary values)
- Error recovery
- Performance validation

---

### P4 - EXHAUSTIVE (Debug Level)

**Purpose:** Complete debug-level testing with all permutations.

**Characteristics:**
- **Test Count:** 50+ tests
- **Output:** Full verbosity
- **Runtime:** Variable (can be long)
- **Coverage:** All permutations, debug-level detail

**Note:** P4 is optional and typically used for deep debugging or final validation before release.

---

## Implementation in DPD-001

### Test Base Class

DPD-001 uses a `TestBase` class that implements progressive testing:

**Location:** `tests/sim/test_base.py`

```python
class TestLevel(IntEnum):
    """Test progression levels"""
    P1_BASIC = 1
    P2_INTERMEDIATE = 2
    P3_COMPREHENSIVE = 3
    P4_EXHAUSTIVE = 4

class TestBase:
    """Base class for CocotB tests with verbosity control."""
    
    def __init__(self, dut, module_name: str):
        # Get test level from environment (default: P1_BASIC)
        level_str = os.environ.get("TEST_LEVEL", "P1_BASIC")
        self.test_level = TestLevel[level_str]
    
    async def run_all_tests(self):
        """Run all test phases up to the configured level."""
        # Always run P1
        if hasattr(self, 'run_p1_basic'):
            await self.run_p1_basic()
        
        # Run P2 if level >= P2
        if self.should_run_level(TestLevel.P2_INTERMEDIATE):
            if hasattr(self, 'run_p2_intermediate'):
                await self.run_p2_intermediate()
        
        # ... P3, P4
```

### Environment Variable Control

**Set test level via `TEST_LEVEL` environment variable:**

```bash
# Run P1 tests (default)
python tests/sim/run.py

# Run P2 tests
TEST_LEVEL=P2_INTERMEDIATE python tests/sim/run.py

# Run P3 tests
TEST_LEVEL=P3_COMPREHENSIVE python tests/sim/run.py
```

**In code:**
```python
# tests/sim/run.py
os.environ.setdefault("TEST_LEVEL", "P1_BASIC")
```

### Test Structure Pattern

**Standard pattern for progressive tests:**

```python
# P1_dpd_wrapper_basic.py
class DPDWrapperBasicTests(TestBase):
    def __init__(self, dut):
        super().__init__(dut, "DPD_Wrapper")
    
    async def run_p1_basic(self):
        """P1 test suite entry point"""
        await self.setup()
        await self.test("Reset behavior", self.test_reset)
        await self.test("Basic operation", self.test_basic_op)
    
    async def test_reset(self):
        """Test reset behavior"""
        # Implementation
        pass
```

---

## Hardware Tests

DPD-001 also implements progressive testing for hardware tests:

**Location:** `tests/hw/hw_test_base.py`

**Test Levels:**
- `P1_BASIC`: Minimal hardware tests (<2 min runtime)
- `P2_INTERMEDIATE`: Comprehensive validation (future)
- `P3_COMPREHENSIVE`: Stress testing (future)

**Usage:**
```bash
# Run P1 hardware tests
cd tests/hw
python run_hw_tests.py <device_ip> --bitstream <path> --level P1

# Run P2 hardware tests
python run_hw_tests.py <device_ip> --bitstream <path> --level P2
```

---

## Best Practices

### 1. Start with P1

**Always begin with P1 tests:**
- Prove basic functionality first
- Get fast feedback (<5 seconds)
- Minimize context for LLM workflows

### 2. Keep P1 Minimal

**P1 should test ONLY:**
- Reset behavior
- One basic operation
- One critical feature

**P1 should NOT include:**
- Edge cases (→ P2)
- Stress tests (→ P3)
- Error handling (→ P2)

### 3. Progressive Expansion

**Build incrementally:**
```
P1 → Prove it works
P2 → Prove it works well
P3 → Prove it works in all cases
P4 → Prove it works perfectly
```

### 4. Output Targets

**Strict output limits:**
- P1: <20 lines
- P2: <50 lines
- P3: <100 lines
- P4: Full verbosity (debug mode)

**Why?** LLM context is expensive. Minimal output = faster iteration.

### 5. Test Isolation

**Each test should be independent:**
- No shared state between tests
- Each test sets up its own inputs
- Tests can run in any order

---

## Integration with Agents

Progressive testing is designed for LLM-based development workflows:

### Test Designer Agent

**Creates test architecture documents:**
- Defines P1/P2/P3 test breakdown
- Specifies expected output limits
- Documents test purposes

**See:** `.claude/agents/cocotb-progressive-test-designer/`

### Test Runner Agent

**Implements test suites:**
- Creates P1 test modules
- Implements progressive orchestrator
- Validates output limits

**See:** `.claude/agents/cocotb-progressive-test-runner/`

---

## Examples from DPD-001

### Simulation Tests

**P1 Example:** `tests/sim/dpd_wrapper_tests/P1_dpd_wrapper_basic.py`
- 5 essential tests
- <20 lines output
- <5 seconds runtime

**Test Coverage:**
1. Reset behavior
2. FORGE control scheme
3. FSM software trigger
4. FSM hardware trigger
5. Output pulses

### Hardware Tests

**P1 Example:** `tests/hw/P1_hw_basic.py`
- 5 essential hardware tests
- <2 minutes runtime
- Observes FSM via oscilloscope

**Test Coverage:**
1. Reset to IDLE
2. FORGE control validation
3. Software trigger cycle
4. Complete FSM cycle
5. Routing validation

---

## Migration Notes

**Source:** FORGE-V5 `/docs/FORGE-V5/Progressive Testing/README.md`  
**Migration Date:** 2025-01-28  
**Changes:**
- Expanded from 12 lines to comprehensive guide
- Added DPD-001-specific examples
- Documented TestBase implementation
- Added hardware test examples
- Included agent integration notes
- Added best practices section

---

## See Also

- [Test Architecture](test-architecture/) - Component test design patterns
- [GHDL Output Filter](ghdl-output-filter.md) - Output filtering for LLM workflows
- [CocoTB Testing](cocotb.md) - CocoTB framework overview
- [Agents Documentation](../.claude/agents/) - Agent pipeline integration

---

**Last Updated:** 2025-01-28  
**Maintainer:** Moku Instrument Forge Team  
**Status:** Migrated and expanded with DPD-001 examples


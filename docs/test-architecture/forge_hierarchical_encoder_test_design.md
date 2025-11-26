# Test Architecture: forge_hierarchical_encoder

**Component:** forge_hierarchical_encoder.vhd  
**Category:** Debugging utilities  
**Designer:** CocoTB Progressive Test Designer Agent  
**Date:** 2025-11-07 (migrated 2025-01-28)  
**Status:** Ready for implementation

> **⚠️ IMPORTANT:** This document was migrated from FORGE-V5 and updated to match DPD-001 implementation.  
> **Key Change:** `DIGITAL_UNITS_PER_STATE` was updated from **200** to **3277** (2025-01-18) for human-readable scope viewing.  
> All test examples and expected values have been recalculated accordingly.

---

## Component Analysis

### Entity Definition

```vhdl
entity forge_hierarchical_encoder is
    generic (
        DIGITAL_UNITS_PER_STATE  : integer := 3277;     -- Updated 2025-01-18 (was 200)
        DIGITAL_UNITS_PER_STATUS : real    := 0.78125   -- 100/128
    );
    port (
        clk           : in  std_logic;
        reset         : in  std_logic;
        state_vector  : in  std_logic_vector(5 downto 0);  -- 6-bit state (0-63)
        status_vector : in  std_logic_vector(7 downto 0);  -- 8-bit status
        voltage_out   : out signed(15 downto 0)            -- Digital output
    );
end entity;
```

### Port Types Analysis

| Port | Type | CocoTB Safe? | Notes |
|------|------|--------------|-------|
| clk | std_logic | ✅ | Standard clock |
| reset | std_logic | ✅ | Active-high reset |
| state_vector | std_logic_vector(5:0) | ✅ | Direct access |
| status_vector | std_logic_vector(7:0) | ✅ | Direct access |
| voltage_out | signed(15:0) | ✅ | **Use .signed_integer** |

**CocoTB Compatibility:** ✅ No wrapper needed

**Critical Access Pattern:**
```python
# CORRECT: Access signed output with .signed_integer
output = int(dut.voltage_out.value.signed_integer)

# WRONG: Loses sign information!
output = int(dut.voltage_out.value)
```

### Component Behavior Summary

**Encoding Algorithm:**
```
base_value = state_vector × DIGITAL_UNITS_PER_STATE        (e.g., state=2 → 6554)
status_offset = (status_vector[6:0] × 100) / 128           (e.g., 0x7F → 99)
combined_value = base_value + status_offset                (e.g., 6554 + 99 = 6653)

IF status_vector[7] = '1' THEN
    voltage_out = -combined_value   (Fault: negative output)
ELSE
    voltage_out = +combined_value   (Normal: positive output)
```

**Key Features to Test:**
1. State encoding: 3277 digital units per state (updated from 200)
2. Status offset encoding: 0.78125 digital units per LSB (integer division: status×100÷128)
3. Fault flag: status[7] negates output
4. Reset behavior: output = 0
5. Registered output: 1 clock cycle latency

---

## Test Strategy

### P1 - BASIC (4 tests, <20 lines output, <5s runtime)

**Design Philosophy:** Test MINIMUM functionality to prove component works.

**Test 1: Reset Behavior**
- **Purpose:** Verify reset drives output to 0
- **Input:** state=0, status=0x00
- **Expected:** voltage_out = 0 after reset
- **Rationale:** Simplest validation, confirms reset logic

**Test 2: State Progression (Linear)**
- **Purpose:** Verify state encoding with no status offset
- **Input:** States [0, 1, 2, 3], status=0x00 (no offset)
- **Expected:** voltage_out = [0, 3277, 6554, 9831] digital units
- **Rationale:** Validates DIGITAL_UNITS_PER_STATE constant (3277)

**Test 3: Status Offset Encoding**
- **Purpose:** Verify status adds fine-grained offset
- **Input:** state=2 (base=6554), status=[0x00, 0x7F]
- **Expected:**
  - status=0x00 → 6554 digital units (no offset)
  - status=0x7F → 6653 digital units (6554 + 99 offset)
- **Rationale:** Validates status offset formula (status×100÷128)

**Test 4: Fault Flag (Sign Flip)**
- **Purpose:** Verify status[7] negates output
- **Input:** state=2, status=[0x00, 0x80]
- **Expected:**
  - status=0x00 (normal) → +6554
  - status=0x80 (fault) → -6554
- **Rationale:** Critical fault detection mechanism

**P1 Summary:**
- Test count: 4 tests
- Clock cycles: ~20 cycles total (4-5 per test)
- Expected output: <20 lines
- Runtime estimate: <2 seconds
- Coverage: Reset, state encoding, status offset, fault flag (all core features)

### P2 - INTERMEDIATE (Optional, 7-10 tests, <50 lines output, <30s)

**Design Philosophy:** Add edge cases and comprehensive status coverage.

**Tests 1-4:** (Include all P1 tests)

**Test 5: Maximum State Value**
- **Purpose:** Verify state=63 (max 6-bit value)
- **Input:** state=63, status=0x00
- **Expected:** voltage_out = 206451 digital units (63 × 3277)
- **Rationale:** Boundary condition, prevents overflow

**Test 6: Combined Maximum (State + Status)**
- **Purpose:** Verify max state + max status
- **Input:** state=63, status=0x7F
- **Expected:** voltage_out = 206451 + 99 = 206550 digital units
- **Rationale:** Maximum positive output case

**Test 7: Status Range (Mid-Points)**
- **Purpose:** Verify status offset linearity
- **Input:** state=1 (base=3277), status=[0x00, 0x40, 0x7F]
- **Expected:**
  - status=0x00 → 3277 (offset=0)
  - status=0x40 → 3327 (offset=50)
  - status=0x7F → 3376 (offset=99)
- **Rationale:** Validates offset calculation across range

**Test 8: Fault with Offset**
- **Purpose:** Verify fault flag preserves magnitude with offset
- **Input:** state=2, status=[0x40, 0xC0]
- **Expected:**
  - status=0x40 (normal) → +6604 (6554 + 50)
  - status=0xC0 (fault) → -6604 (negated, magnitude preserved)
- **Rationale:** Ensures fault logic works with status offset

**Test 9: Zero State with Fault**
- **Purpose:** Edge case - fault flag with zero base value
- **Input:** state=0, status=[0x00, 0x80]
- **Expected:**
  - status=0x00 → 0
  - status=0x80 → 0 (negating zero = zero)
- **Rationale:** Mathematical edge case validation

**Test 10: Sequential State Transitions**
- **Purpose:** Verify output updates each clock cycle
- **Input:** Cycle through states 0→1→2→1→0 with status=0x00
- **Expected:** Outputs [0, 3277, 6554, 3277, 0] on successive clocks
- **Rationale:** Validates registered output timing

**P2 Summary:**
- Test count: 10 tests
- Clock cycles: ~50 cycles total
- Expected output: <50 lines
- Runtime estimate: <10 seconds
- Coverage: Boundary conditions, linearity, timing

---

## Test Wrapper Design

**Wrapper Needed:** ❌ No

**Rationale:**
- All entity ports use CocoTB-safe types
- std_logic, std_logic_vector, and signed are directly accessible
- No real, boolean, time, or record types at ports

**Direct DUT Access Pattern:**
```python
# All ports accessible directly
dut.state_vector.value = 3
dut.status_vector.value = 0x7F
output = int(dut.voltage_out.value.signed_integer)  # Note: .signed_integer!
```

---

## Constants File Design

**File:** `tests/sim/forge_hierarchical_encoder_tests/forge_hierarchical_encoder_constants.py`

> **Note:** This is a reference design. DPD-001 currently uses `forge_hierarchical_encoder` within `DPD_shim.vhd` rather than as a standalone test target.

```python
"""
Constants and expected value calculations for forge_hierarchical_encoder tests.

This file provides test data and expected value computation following the
hierarchical encoding scheme used in the VHDL component.

UPDATED 2025-01-28: DIGITAL_UNITS_PER_STATE changed from 200 to 3277
"""

from pathlib import Path

# ============================================================================
# Module Identification
# ============================================================================

MODULE_NAME = "forge_hierarchical_encoder"

# HDL sources (relative to tests/ directory)
PROJECT_ROOT = Path(__file__).parent.parent.parent
HDL_SOURCES = [
    PROJECT_ROOT / "rtl" / "forge_hierarchical_encoder.vhd",
]
HDL_TOPLEVEL = "forge_hierarchical_encoder"  # lowercase!


# ============================================================================
# Generic Values (match VHDL defaults)
# ============================================================================

# UPDATED 2025-01-18: Changed from 200 to 3277 for human-readable scope viewing
DIGITAL_UNITS_PER_STATE = 3277
# DIGITAL_UNITS_PER_STATUS = 0.78125  # Real in VHDL, but we use integer math


# ============================================================================
# Test Values (Progressive Sizing)
# ============================================================================

class TestValues:
    """Test values sized progressively for P1/P2/P3 testing."""

    # P1: Small, fast values (ESSENTIAL ONLY)
    P1_STATES = [0, 1, 2, 3]  # 4 basic states
    P1_STATUS = [0x00, 0x7F, 0x80, 0xC0]  # Min, max normal, fault, fault+offset

    # P2: Realistic + edge cases
    P2_STATES = [0, 1, 2, 3, 31, 63]  # Normal + boundaries
    P2_STATUS = [0x00, 0x01, 0x40, 0x7E, 0x7F, 0x80, 0xFF]  # Full range

    # P3: Comprehensive (if needed)
    P3_STATES = list(range(64))  # All 6-bit states
    P3_STATUS = [i for i in range(256)]  # All 8-bit status values


# ============================================================================
# Expected Value Calculation (MUST match VHDL arithmetic!)
# ============================================================================

def calculate_expected_digital(state: int, status: int) -> int:
    """
    Calculate expected digital output value.

    This function MUST match the VHDL arithmetic exactly:
    - base_value = state × 3277 (UPDATED from 200)
    - status_lower = status & 0x7F (lower 7 bits)
    - status_offset = (status_lower × 100) ÷ 128  (INTEGER DIVISION!)
    - combined_value = base_value + status_offset
    - IF status[7] = 1 THEN -combined_value ELSE +combined_value

    Args:
        state: 6-bit state value (0-63)
        status: 8-bit status value (0-255)
            status[7] = fault flag (1 = fault, negate output)
            status[6:0] = status offset value (0-127)

    Returns:
        Signed 16-bit digital value (-32768 to +32767)

    Example:
        >>> calculate_expected_digital(0, 0x00)
        0
        >>> calculate_expected_digital(2, 0x00)
        6554
        >>> calculate_expected_digital(2, 0x7F)
        6653  # 6554 base + 99 offset
        >>> calculate_expected_digital(2, 0x80)
        -6554  # Fault flag, negated
        >>> calculate_expected_digital(2, 0xC0)
        -6604  # Fault flag + offset (6554 + 50), negated
    """
    # Compute base value (state contribution)
    base_value = state * DIGITAL_UNITS_PER_STATE

    # Extract status fields
    status_lower = status & 0x7F  # Lower 7 bits (0-127)
    fault_flag = (status >> 7) & 1  # Upper bit (0 or 1)

    # Compute status offset using integer division (matches VHDL)
    # CRITICAL: Use // (integer division), NOT / (float division)!
    # VHDL: status_offset <= (status_lower * 100) / 128;
    status_offset = (status_lower * 100) // 128

    # Combine base + offset
    combined_value = base_value + status_offset

    # Apply sign based on fault flag
    if fault_flag == 1:
        return -combined_value  # Fault: negate output
    else:
        return combined_value   # Normal: positive output


# ============================================================================
# Helper Functions (Signal Access Patterns)
# ============================================================================

def get_voltage_out(dut) -> int:
    """
    Extract signed digital output from DUT.

    CRITICAL: Must use .signed_integer for signed types!

    Args:
        dut: CocoTB DUT handle

    Returns:
        Signed integer value (-32768 to +32767)
    """
    return int(dut.voltage_out.value.signed_integer)


def set_state_status(dut, state: int, status: int):
    """
    Set state and status inputs on DUT.

    Args:
        dut: CocoTB DUT handle
        state: 6-bit state value (0-63)
        status: 8-bit status value (0-255)
    """
    dut.state_vector.value = state
    dut.status_vector.value = status


# ============================================================================
# Error Message Templates
# ============================================================================

class ErrorMessages:
    """Consistent error message formatting."""

    WRONG_OUTPUT = "State={state}, Status=0x{status:02X}: expected {expected}, got {actual}"
    RESET_FAILED = "Expected output=0 after reset, got {actual}"
    MAGNITUDE_MISMATCH = "Fault magnitude mismatch: normal={normal}, fault={fault}"
    NOT_NEGATIVE = "Expected negative output (fault flag set), got {actual}"
    NOT_POSITIVE = "Expected positive output (normal operation), got {actual}"
    OFFSET_NOT_APPLIED = "Status offset not applied: status=0x00 → {no_offset}, status=0x7F → {with_offset}"
```

---

## Expected Values Calculation

### Formula (Matching VHDL Exactly)

**VHDL Implementation:**
```vhdl
base_value <= state_integer * DIGITAL_UNITS_PER_STATE;  -- 3277 (updated from 200)
status_offset <= (status_lower * 100) / 128;  -- Integer division!
combined_value <= base_value + status_offset;

if fault_flag = '1' then
    output_value <= to_signed(-combined_value, 16);
else
    output_value <= to_signed(combined_value, 16);
end if;
```

**Python Implementation (MUST match):**
```python
def calculate_expected_digital(state: int, status: int) -> int:
    base_value = state * 3277  # UPDATED from 200
    status_lower = status & 0x7F
    status_offset = (status_lower * 100) // 128  # Integer division: //
    combined_value = base_value + status_offset

    fault_flag = (status >> 7) & 1
    return -combined_value if fault_flag else combined_value
```

**CRITICAL:** Use `//` (integer division), NOT `/` (float division)!

### Example Calculations (Updated for 3277)

**P1 Test Cases:**

```
State=0, Status=0x00 (binary: 00000000)
  base = 0 × 3277 = 0
  status_lower = 0x00 = 0
  offset = (0 × 100) // 128 = 0
  combined = 0 + 0 = 0
  fault = 0
  → Expected: 0

State=1, Status=0x00
  base = 1 × 3277 = 3277
  offset = 0
  combined = 3277
  fault = 0
  → Expected: 3277

State=2, Status=0x00
  base = 2 × 3277 = 6554
  offset = 0
  combined = 6554
  fault = 0
  → Expected: 6554

State=2, Status=0x7F (binary: 01111111)
  base = 2 × 3277 = 6554
  status_lower = 0x7F = 127
  offset = (127 × 100) // 128 = 12700 // 128 = 99
  combined = 6554 + 99 = 6653
  fault = 0
  → Expected: 6653

State=2, Status=0x80 (binary: 10000000)
  base = 2 × 3277 = 6554
  status_lower = 0x00 = 0
  offset = 0
  combined = 6554
  fault = 1
  → Expected: -6554

State=2, Status=0xC0 (binary: 11000000)
  base = 2 × 3277 = 6554
  status_lower = 0x40 = 64
  offset = (64 × 100) // 128 = 6400 // 128 = 50
  combined = 6554 + 50 = 6604
  fault = 1
  → Expected: -6604
```

**Verification Table for P1 (Updated):**

| State | Status | Base | Offset | Combined | Fault | Expected |
|-------|--------|------|--------|----------|-------|----------|
| 0 | 0x00 | 0 | 0 | 0 | 0 | 0 |
| 1 | 0x00 | 3277 | 0 | 3277 | 0 | +3277 |
| 2 | 0x00 | 6554 | 0 | 6554 | 0 | +6554 |
| 3 | 0x00 | 9831 | 0 | 9831 | 0 | +9831 |
| 2 | 0x7F | 6554 | 99 | 6653 | 0 | +6653 |
| 2 | 0x80 | 6554 | 0 | 6554 | 1 | -6554 |
| 2 | 0xC0 | 6554 | 50 | 6604 | 1 | -6604 |

---

## Design Decisions and Rationale

### Decision 1: No Test Wrapper

**Rationale:**
- All entity ports are CocoTB-compatible types
- signed(15:0) is directly accessible via `.signed_integer`
- No real, boolean, time, or record types at boundary
- Wrapper would add complexity without benefit

### Decision 2: Test Digital Domain (Not Voltages)

**Rationale:**
- Component outputs digital values, not voltages
- Platform-agnostic testing (no DAC assumptions)
- Voltage interpretation is application-specific
- Simpler test data (integers, not floats)

### Decision 3: P1 Test Selection

**Selected Tests:**
1. Reset (essential baseline)
2. State progression (core encoding)
3. Status offset (fine-grained encoding)
4. Fault flag (critical safety feature)

**Rejected for P1:**
- Boundary conditions (state=63) → P2
- Random testing → P3
- Timing tests (sequential updates) → P2

**Rationale:** P1 must prove basic arithmetic works (<20 lines output)

### Decision 4: Integer Division in Expected Values

**CRITICAL DESIGN CHOICE:**
```python
# CORRECT:
status_offset = (status_lower * 100) // 128  # Integer division

# WRONG:
status_offset = int((status_lower * 100) / 128)  # Float division, then truncate
status_offset = round((status_lower * 100) / 128)  # Rounding mismatch!
```

**Rationale:**
- VHDL uses integer division (truncation)
- Python `/` operator uses float division
- Python `//` operator matches VHDL truncation behavior
- Mismatches cause off-by-one errors in tests

### Decision 5: Constant Update (200 → 3277)

**Change Date:** 2025-01-18  
**Reason:** Increased for human-readable scope viewing (0.5V per state step @ ±5V full scale)

**Impact:**
- All test expected values must be recalculated
- State progression: [0, 200, 400, 600] → [0, 3277, 6554, 9831]
- Maximum state (63): 12600 → 206451 digital units

---

## Design Challenges

### Challenge 1: Constant Update Migration

**Issue:** Original document used `DIGITAL_UNITS_PER_STATE = 200`, but DPD-001 uses `3277`

**Resolution:**
- Updated all test examples to use 3277
- Recalculated all expected values
- Added migration note at top of document
- Documented change date and rationale

### Challenge 2: Signed Integer Access Pattern

**Issue:** CocoTB requires `.signed_integer` for signed types

**Wrong Pattern:**
```python
output = int(dut.voltage_out.value)  # Loses sign! Treats as unsigned
```

**Correct Pattern:**
```python
output = int(dut.voltage_out.value.signed_integer)  # Preserves sign
```

**Mitigation:** Helper function `get_voltage_out(dut)` encapsulates pattern

### Challenge 3: Test Timing (Registered Output)

**Issue:** Component has 1-cycle latency (registered output)

**Pattern:**
```python
set_state_status(dut, state, status)
await ClockCycles(dut.clk, 1)  # Wait for register update
actual = get_voltage_out(dut)
```

**Rationale:** Tests must wait 1 clock after input change

---

## Implementation Notes for DPD-001

**Current Status:** `forge_hierarchical_encoder` is used within `DPD_shim.vhd` as part of the HVS (Hierarchical Voltage Scoring) system for FSM state debugging.

**Location:** `rtl/forge_hierarchical_encoder.vhd`

**Integration:**
- Instantiated in `DPD_shim.vhd` as `HVS_ENCODER_INST`
- Drives `OutputC` with encoded FSM state for oscilloscope observation
- State input comes from `DPD_main.vhd` FSM state register
- Status input comes from app-specific status vector

**Test Coverage:**
- Currently tested indirectly through DPD wrapper tests
- HVS output verified in `P1_dpd_wrapper_basic.py` via `read_output_c()` helper
- Direct unit tests for `forge_hierarchical_encoder` could be added if needed

---

## Summary

**Component:** forge_hierarchical_encoder.vhd  
**Category:** Debugging utilities (hierarchical voltage encoding)  
**Wrapper Needed:** No  
**P1 Tests:** 4 essential tests  
**P1 Output:** <20 lines (estimated)  
**P1 Runtime:** <5 seconds (estimated)

**Key Testing Principles:**
1. Test DIGITAL domain, not voltages
2. Use integer division (//) to match VHDL
3. Access signed output with .signed_integer
4. Keep P1 minimal (4 tests, small values)
5. Wait 1 clock cycle for registered output
6. **Use DIGITAL_UNITS_PER_STATE = 3277** (not 200)

**Migration Notes:**
- Document migrated from FORGE-V5 on 2025-01-28
- Constants updated to match DPD-001 implementation
- File paths updated to match DPD-001 structure
- All expected values recalculated for 3277 constant

---

**Created:** 2025-11-07  
**Migrated:** 2025-01-28  
**Designer:** CocoTB Progressive Test Designer Agent  
**Status:** Complete, ready for implementation  
**Version:** 2.0 (updated for DPD-001)


"""
Data-Driven Test Case Definitions
=================================

Shared test case definitions used by both simulation and hardware tests.
Tests are defined as data structures; execution is platform-specific.

Author: Moku Instrument Forge Team
Date: 2025-11-26
"""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class TestCategory(Enum):
    """Test categories for organization."""
    RESET = "reset"
    FORGE_CONTROL = "forge_control"
    FSM_TRANSITIONS = "fsm_transitions"
    TRIGGER = "trigger"
    OUTPUT = "output"
    TIMING = "timing"
    FAULT = "fault"
    STRESS = "stress"


@dataclass
class TestStep:
    """Single step in a test case."""
    action: str           # What to do (human readable)
    expected: str         # Expected outcome
    timeout_us: int = 100 # Timeout for this step


@dataclass
class TestCase:
    """Data-driven test case definition.

    Defines what a test does without specifying how.
    Both sim and hw tests can execute the same TestCase.
    """
    id: str                              # Unique identifier (e.g., "P1_T1")
    name: str                            # Human-readable name
    description: str                     # What this test verifies
    category: TestCategory               # Test category
    steps: List[TestStep] = field(default_factory=list)
    expected_final_state: Optional[str] = None  # Expected FSM state at end
    timeout_us: int = 1000               # Overall timeout
    level: int = 1                       # Test level (1=P1, 2=P2, etc.)

    def __str__(self) -> str:
        return f"{self.id}: {self.name}"


# =============================================================================
# P1 Test Cases - Basic Functionality
# =============================================================================

P1_TEST_RESET = TestCase(
    id="P1_T1",
    name="Reset behavior",
    description="Verify Reset drives FSM to INITIALIZING then IDLE",
    category=TestCategory.RESET,
    steps=[
        TestStep("Assert reset (Reset=1)", "FSM in INITIALIZING state"),
        TestStep("Check OutputC", "OutputC = 0 (INITIALIZING)"),
        TestStep("Check OutputA/B", "Both outputs = 0"),
        TestStep("Release reset (Reset=0)", "FSM transitions to IDLE"),
        TestStep("Wait for IDLE", "OutputC = 3277 (IDLE)"),
    ],
    expected_final_state="IDLE",
    timeout_us=100,
    level=1,
)

P1_TEST_FORGE_CONTROL = TestCase(
    id="P1_T2",
    name="FORGE control scheme",
    description="Verify partial vs complete FORGE enable gates FSM operation",
    category=TestCategory.FORGE_CONTROL,
    steps=[
        TestStep("Reset to clean state", "FSM in IDLE"),
        TestStep("Set partial FORGE (CR0=0xC0000000)", "clk_enable=0"),
        TestStep("Set arm_enable (CR1[0]=1)", "Try to arm"),
        TestStep("Check state", "FSM stays IDLE/INITIALIZING (blocked)"),
        TestStep("Reset again", "Clean state"),
        TestStep("Set complete FORGE (CR0=0xE0000000)", "All 3 bits set"),
        TestStep("Set arm_enable (CR1[0]=1)", "Arm FSM"),
        TestStep("Wait for ARMED", "FSM reaches ARMED state"),
    ],
    expected_final_state="ARMED",
    timeout_us=500,
    level=1,
)

P1_TEST_SOFTWARE_TRIGGER = TestCase(
    id="P1_T3",
    name="FSM cycle (software trigger)",
    description="Complete FSM cycle via software trigger",
    category=TestCategory.FSM_TRANSITIONS,
    steps=[
        TestStep("Enable FORGE control", "CR0=0xE0000000"),
        TestStep("Configure timing", "Set CR4, CR5, CR7"),
        TestStep("Arm FSM", "CR1[0]=1"),
        TestStep("Wait for ARMED", "FSM in ARMED state"),
        TestStep("Issue software trigger", "CR1[3]=1, CR1[5]=1"),
        TestStep("Wait for FIRING", "FSM leaves ARMED"),
        TestStep("Wait for COOLDOWN", "FSM in COOLDOWN"),
        TestStep("Wait for IDLE", "FSM returns to IDLE"),
    ],
    expected_final_state="IDLE",
    timeout_us=1000,
    level=1,
)

P1_TEST_HARDWARE_TRIGGER = TestCase(
    id="P1_T4",
    name="FSM cycle (hardware trigger)",
    description="Complete FSM cycle via InputA voltage trigger",
    category=TestCategory.TRIGGER,
    steps=[
        TestStep("Enable FORGE control", "CR0=0xE0000000"),
        TestStep("Configure timing", "Set CR4, CR5, CR7"),
        TestStep("Set InputA below threshold", "InputA < threshold"),
        TestStep("Arm with hw_trigger_enable", "CR1[0]=1, CR1[4]=1"),
        TestStep("Wait for ARMED", "FSM in ARMED state"),
        TestStep("Set InputA above threshold", "InputA > threshold"),
        TestStep("Wait for FIRING", "FSM triggers"),
        TestStep("Wait for cycle complete", "FSM returns to IDLE/COOLDOWN"),
    ],
    expected_final_state="IDLE",
    timeout_us=1000,
    level=1,
)

P1_TEST_OUTPUT_PULSES = TestCase(
    id="P1_T5",
    name="Output pulses during FIRING",
    description="Verify OutputA and OutputB are active during FIRING state",
    category=TestCategory.OUTPUT,
    steps=[
        TestStep("Arm FSM with voltage config", "Set trig_voltage, intensity_voltage"),
        TestStep("Wait for ARMED", "FSM in ARMED"),
        TestStep("Issue trigger", "Start FIRING state"),
        TestStep("Check OutputA", "OutputA = configured voltage"),
        TestStep("Check OutputB", "OutputB = configured voltage"),
        TestStep("Wait for cycle", "Outputs return to 0"),
    ],
    expected_final_state="IDLE",
    timeout_us=1000,
    level=1,
)

# =============================================================================
# P2 Test Cases - Intermediate Functionality
# =============================================================================

P2_TEST_AUTO_REARM = TestCase(
    id="P2_T1",
    name="Auto-rearm mode",
    description="Verify FSM re-arms after cooldown when auto_rearm_enable=1",
    category=TestCategory.FSM_TRANSITIONS,
    steps=[
        TestStep("Configure with auto_rearm=1", "CR1[1]=1"),
        TestStep("Arm and trigger", "Complete first cycle"),
        TestStep("After COOLDOWN", "FSM should return to ARMED (not IDLE)"),
        TestStep("Trigger again", "Second cycle starts"),
        TestStep("Disable auto_rearm", "CR1[1]=0"),
        TestStep("After COOLDOWN", "FSM returns to IDLE"),
    ],
    expected_final_state="IDLE",
    timeout_us=2000,
    level=2,
)

P2_TEST_FAULT_INJECTION = TestCase(
    id="P2_T2",
    name="Fault injection and recovery",
    description="Verify fault state behavior and fault_clear recovery",
    category=TestCategory.FAULT,
    steps=[
        TestStep("Inject fault condition", "Force fault state"),
        TestStep("Check FSM", "Should be in FAULT state"),
        TestStep("Check OutputC", "Negative voltage (fault indication)"),
        TestStep("Attempt normal operation", "Should be blocked"),
        TestStep("Pulse fault_clear", "CR1[2] edge"),
        TestStep("Wait for IDLE", "FSM recovers to IDLE"),
    ],
    expected_final_state="IDLE",
    timeout_us=1000,
    level=2,
)

# =============================================================================
# Test Collections
# =============================================================================

ALL_P1_TESTS = [
    P1_TEST_RESET,
    P1_TEST_FORGE_CONTROL,
    P1_TEST_SOFTWARE_TRIGGER,
    P1_TEST_HARDWARE_TRIGGER,
    P1_TEST_OUTPUT_PULSES,
]

ALL_P2_TESTS = [
    P2_TEST_AUTO_REARM,
    P2_TEST_FAULT_INJECTION,
]

ALL_TESTS = ALL_P1_TESTS + ALL_P2_TESTS


def get_tests_by_level(level: int) -> List[TestCase]:
    """Get all tests up to and including specified level.

    Args:
        level: Test level (1=P1, 2=P2, etc.)

    Returns:
        List of TestCase objects
    """
    return [t for t in ALL_TESTS if t.level <= level]


def get_tests_by_category(category: TestCategory) -> List[TestCase]:
    """Get all tests in a category.

    Args:
        category: TestCategory to filter by

    Returns:
        List of TestCase objects
    """
    return [t for t in ALL_TESTS if t.category == category]

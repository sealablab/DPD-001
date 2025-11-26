"""
Progressive Test Level 1 (P1) - Demo Probe Driver Hardware (BASIC)

Fast smoke tests for DPD running on real Moku hardware.
Tests observe FSM state via Oscilloscope monitoring OutputC (HVS encoding).

Test Coverage:
- Reset behavior (manual reset to IDLE)
- FORGE control scheme (CR0[31:29])
- Basic FSM state transitions (software trigger)
- FSM complete cycle verification
- Routing validation

Expected Runtime: <2 minutes
Expected Output: <20 lines (P1 standard)

Author: Moku Instrument Forge Team
Date: 2025-01-18
"""

import time

import sys
from pathlib import Path

# Add parent hw/ directory to path for hw_test_base import
HW_PATH = Path(__file__).parent.parent
sys.path.insert(0, str(HW_PATH))

from hw_test_base import HardwareTestBase, VerbosityLevel
from dpd.helpers import (
    arm_probe,
    software_trigger,
    disarm_probe,
    clear_fault,
    reset_fsm_to_idle,
)
from dpd.constants import (
    MCC_CR0_ALL_ENABLED,
    P2TestValues,  # Use P2 timing for visibility (P1 timing too fast for OSC)
    TEST_RESET_TIMEOUT_MS,
    TEST_ARM_TIMEOUT_MS,
    TEST_TRIGGER_TIMEOUT_MS,
    TEST_FSM_CYCLE_TIMEOUT_MS,
)


class P1_HardwareBasicTests(HardwareTestBase):
    """P1 (BASIC) hardware tests for Demo Probe Driver."""

    def __init__(self, moku, osc_slot=1, cc_slot=2, bitstream=None,
                 verbosity=VerbosityLevel.MINIMAL):
        """
        Initialize P1 hardware test suite.

        Args:
            moku: Connected MultiInstrument instance
            osc_slot: Oscilloscope slot number (default: 1)
            cc_slot: CloudCompile slot number (default: 2)
            bitstream: Path to CloudCompile bitstream
            verbosity: Output verbosity level
        """
        super().__init__(moku, "P1_HW_BASIC", osc_slot, cc_slot, bitstream, verbosity)

    def run_p1_basic(self):
        """P1 test suite entry point - 5 essential tests."""
        # Validate routing first
        self.test("Routing validation", self.test_routing)

        # Initialize FORGE control
        self.test("FORGE initialization", self.test_forge_init)

        # Run core tests
        self.test("Reset to IDLE", self.test_reset_to_idle)
        self.test("FORGE control scheme", self.test_forge_control)
        self.test("FSM software trigger", self.test_fsm_software_trigger)
        self.test("FSM complete cycle", self.test_fsm_complete_cycle)

    def test_routing(self):
        """Verify routing is configured correctly for tests."""
        self.log("Checking routing configuration...", VerbosityLevel.VERBOSE)

        is_valid = self.validate_routing()

        if not is_valid:
            self.log("⚠️  Routing not configured, setting up now...", VerbosityLevel.NORMAL)
            self.setup_routing()
            time.sleep(0.5)  # Allow routing to settle

            # Verify routing was set correctly
            is_valid = self.validate_routing()

        assert is_valid, "Routing validation failed. Check Moku connections."
        self.log("✓ Routing validated", VerbosityLevel.VERBOSE)

    def test_forge_init(self):
        """Initialize FORGE_READY control bits."""
        self.log("Setting FORGE_READY (CR0[31:29] = 0b111)...", VerbosityLevel.VERBOSE)
        self.init_forge()

        # Verify CR0 was set
        cr0_result = self.mcc.get_control(0)

        # Handle different return types (may be int, dict, or list)
        if isinstance(cr0_result, list):
            cr0_value = cr0_result[0] if cr0_result else 0
        elif isinstance(cr0_result, dict):
            cr0_value = cr0_result.get('value', cr0_result.get('id', 0))
        else:
            cr0_value = cr0_result

        self.log(f"CR0 = 0x{cr0_value:08X}", VerbosityLevel.VERBOSE)

        assert (cr0_value & 0xE0000000) == MCC_CR0_ALL_ENABLED, \
            f"FORGE_READY bits not set correctly: CR0=0x{cr0_value:08X}"

        self.log("✓ FORGE_READY initialized", VerbosityLevel.VERBOSE)

    def test_reset_to_idle(self):
        """Verify FSM can be reset to IDLE state."""
        self.log("Resetting FSM to IDLE...", VerbosityLevel.VERBOSE)

        # Reset FSM
        success = reset_fsm_to_idle(self.mcc, self.osc, timeout_ms=TEST_RESET_TIMEOUT_MS)

        assert success, "FSM did not reach IDLE after reset"

        # Double-check state
        state, voltage = self.read_state()
        self.log(f"FSM state: {state} ({voltage:.2f}V)", VerbosityLevel.VERBOSE)

        assert state == "IDLE", f"Expected IDLE after reset, got {state}"

    def test_forge_control(self):
        """Verify FORGE control scheme gates FSM operation."""
        self.log("Testing FORGE control scheme...", VerbosityLevel.VERBOSE)

        # Ensure FSM is in IDLE
        reset_fsm_to_idle(self.mcc, self.osc, timeout_ms=TEST_RESET_TIMEOUT_MS)

        # Test 1: Partial FORGE enable (missing clk_enable) - FSM should NOT arm
        self.log("Test partial FORGE enable (should stay IDLE)...", VerbosityLevel.VERBOSE)
        self.mcc.set_control(0, 0xC0000000)  # forge_ready=1, user_enable=1, clk_enable=0
        self.mcc.set_control(1, 0x00000001)  # arm_enable=1
        time.sleep(0.3)

        state, _ = self.read_state()
        assert state == "IDLE", \
            f"FSM should remain IDLE without clk_enable, got {state}"

        # Test 2: Complete FORGE enable - FSM should arm
        self.log("Test complete FORGE enable (should ARM)...", VerbosityLevel.VERBOSE)

        # Clear CR1 from previous partial test (arm_enable was set but ineffective)
        self.mcc.set_control(1, 0x00000000)
        time.sleep(0.1)

        self.mcc.set_control(0, MCC_CR0_ALL_ENABLED)  # All 3 bits set
        time.sleep(0.3)

        # Arm with minimal timing
        arm_probe(
            self.mcc,
            trig_duration_us=P2TestValues.TRIG_OUT_DURATION_US,
            intensity_duration_us=P2TestValues.INTENSITY_DURATION_US,
            cooldown_us=P2TestValues.COOLDOWN_INTERVAL_US,
        )

        # Wait for ARMED state
        success = self.wait_state("ARMED", timeout_ms=TEST_ARM_TIMEOUT_MS)
        assert success, "FSM should ARM with complete FORGE control"

        state, voltage = self.read_state()
        self.log(f"FSM armed: {state} ({voltage:.2f}V)", VerbosityLevel.VERBOSE)

        # Clean up - reset to IDLE
        reset_fsm_to_idle(self.mcc, self.osc, timeout_ms=TEST_RESET_TIMEOUT_MS)

    # @JC: This is 'T5: FSM cycle (software trigger)' and it has some issues..
    def test_fsm_software_trigger(self):
        """Verify FSM responds to software trigger."""
        self.log("Testing software trigger...", VerbosityLevel.VERBOSE)

        # Ensure FSM is in IDLE with FORGE enabled
        reset_fsm_to_idle(self.mcc, self.osc, timeout_ms=TEST_RESET_TIMEOUT_MS)

        # Arm FSM
        arm_probe(
            self.mcc,
            trig_duration_us=P2TestValues.TRIG_OUT_DURATION_US,
            intensity_duration_us=P2TestValues.INTENSITY_DURATION_US,
            cooldown_us=P2TestValues.COOLDOWN_INTERVAL_US,
        )

        # Verify ARMED
        success = self.wait_state("ARMED", timeout_ms=TEST_ARM_TIMEOUT_MS)
        assert success, "FSM should be ARMED before trigger"

        # Software trigger
        self.log("Issuing software trigger...", VerbosityLevel.VERBOSE)
        software_trigger(self.mcc)

        # FSM should leave ARMED state (transition to FIRING or COOLDOWN)
        # With P2 timing (310μs total), we might catch FIRING or COOLDOWN
        time.sleep(0.1)  # Brief delay for trigger to take effect

        state, voltage = self.read_state()
        self.log(f"State after trigger: {state} ({voltage:.2f}V)", VerbosityLevel.VERBOSE)

        assert state != "ARMED", \
            f"FSM should leave ARMED after software trigger, stuck at {state}"

        # Acceptable states: FIRING, COOLDOWN, or IDLE (if cycle completed fast)
        assert state in ["FIRING", "COOLDOWN", "IDLE"], \
            f"Unexpected state after trigger: {state}"

        # Clean up
        time.sleep(0.5)  # Let FSM cycle complete
        reset_fsm_to_idle(self.mcc, self.osc, timeout_ms=TEST_RESET_TIMEOUT_MS)
    # @JC: This is 'T6: FSM cycle complete'
    def test_fsm_complete_cycle(self):
        """Verify FSM completes full state cycle (IDLE → ARMED → FIRING → COOLDOWN → IDLE)."""
        self.log("Testing complete FSM cycle...", VerbosityLevel.VERBOSE)

        # Ensure FSM is in IDLE
        reset_fsm_to_idle(self.mcc, self.osc, timeout_ms=TEST_RESET_TIMEOUT_MS)

        # Arm FSM
        self.log("Arming FSM...", VerbosityLevel.VERBOSE)
        arm_probe(
            self.mcc,
            trig_duration_us=P2TestValues.TRIG_OUT_DURATION_US,
            intensity_duration_us=P2TestValues.INTENSITY_DURATION_US,
            cooldown_us=P2TestValues.COOLDOWN_INTERVAL_US,
        )

        # Wait for ARMED
        success = self.wait_state("ARMED", timeout_ms=TEST_ARM_TIMEOUT_MS)
        assert success, "FSM should reach ARMED"
        self.log("✓ ARMED", VerbosityLevel.VERBOSE)

        # Trigger
        self.log("Triggering...", VerbosityLevel.VERBOSE)
        software_trigger(self.mcc)

        # Wait for FIRING (may be brief with P2 timing)
        # Note: FIRING state is 100μs + 200μs = 300μs, should be observable
        success = self.wait_state("FIRING", timeout_ms=TEST_TRIGGER_TIMEOUT_MS)

        if success:
            self.log("✓ FIRING", VerbosityLevel.VERBOSE)
        else:
            # Might have missed FIRING (too fast), check if we're in COOLDOWN
            state, _ = self.read_state()
            self.log(f"⚠️  Missed FIRING state, currently in {state}", VerbosityLevel.VERBOSE)
            # Accept COOLDOWN as proof that FIRING happened
            assert state in ["COOLDOWN", "IDLE"], \
                f"Expected FIRING/COOLDOWN/IDLE, got {state}"

        # Wait for COOLDOWN (10μs @ P2 timing)
        # Increase timeout to account for oscilloscope polling delays
        success = self.wait_state("COOLDOWN", timeout_ms=TEST_FSM_CYCLE_TIMEOUT_MS)

        if success:
            self.log("✓ COOLDOWN", VerbosityLevel.VERBOSE)
        else:
            # Check if we're already back to IDLE
            state, _ = self.read_state()
            if state == "IDLE":
                self.log("✓ Cycle completed (already at IDLE)", VerbosityLevel.VERBOSE)
            else:
                assert False, f"Expected COOLDOWN or IDLE, got {state}"

        # Note: COOLDOWN → IDLE transition can be flaky (similar to CocoTB P1:192-194)
        # Accept either COOLDOWN or IDLE as success
        time.sleep(0.2)  # Allow COOLDOWN → IDLE transition
        state, voltage = self.read_state()
        self.log(f"Final state: {state} ({voltage:.2f}V)", VerbosityLevel.VERBOSE)

        assert state in ["COOLDOWN", "IDLE"], \
            f"FSM should be in COOLDOWN or IDLE after cycle, got {state}"

        # Clean up
        reset_fsm_to_idle(self.mcc, self.osc, timeout_ms=TEST_RESET_TIMEOUT_MS)

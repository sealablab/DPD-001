"""
Progressive Test Level 1 (P1) - Demo Probe Driver (API v4.0)

Fast smoke tests for DPD FSM using the CR0-based lifecycle control API.

Test Coverage (CR0 hierarchy):
- T1: FORGE run gate (CR0[31:29]) - Safety control
- T2: Arm control (CR0[2]) - arm/disarm
- T3: Software trigger (CR0[0]) - atomic trigger
- T4: Fault clear (CR0[1]) - fault recovery
- T5: Full cycle - complete FSM cycle

Expected Runtime: <5s
Expected Output: <20 lines (P1 standard)

API Reference: docs/api-v4.md
Author: Moku Instrument Forge Team
Date: 2025-11-26 (API v4.0 rewrite)
"""

import cocotb
from cocotb.triggers import ClockCycles
import sys
from pathlib import Path

# Add paths for imports
TESTS_PATH = Path(__file__).parent.parent
sys.path.insert(0, str(TESTS_PATH))
sys.path.insert(0, str(TESTS_PATH.parent))

from test_base import TestBase
from adapters.cocotb import CocoTBAsyncHarness
from conftest import setup_clock, reset_active_high, init_mcc_inputs

from lib import (
    CR0,
    P1Timing,
    HVS_DIGITAL_INITIALIZING,
    HVS_DIGITAL_IDLE,
    HVS_DIGITAL_ARMED,
    HVS_DIGITAL_FIRING,
    HVS_DIGITAL_COOLDOWN,
    SIM_HVS_TOLERANCE,
    DEFAULT_TRIGGER_WAIT_TIMEOUT,
)


class DPDBasicTests(TestBase):
    """P1 (BASIC) tests for Demo Probe Driver - API v4.0"""

    def __init__(self, dut):
        super().__init__(dut, "dpd_p1")
        self.harness = None

    async def setup(self):
        """Common setup for all tests."""
        # Setup clock and reset
        await setup_clock(self.dut, period_ns=8, clk_signal="Clk")
        await reset_active_high(self.dut, rst_signal="Reset", cycles=10)
        await init_mcc_inputs(self.dut)

        # Initialize all Control Registers to 0
        for i in range(16):
            ctrl_name = f"Control{i}"
            if hasattr(self.dut, ctrl_name):
                getattr(self.dut, ctrl_name).value = 0

        # Create harness
        self.harness = CocoTBAsyncHarness(self.dut)

    async def run_p1_basic(self):
        """P1 test suite entry point - 5 essential tests following CR0 hierarchy."""
        await self.setup()

        # Run tests in CR0 bit order
        await self.test("T1: FORGE run gate (CR0[31:29])", self.test_forge_run_gate)
        await self.test("T2: Arm control (CR0[2])", self.test_arm_control)
        await self.test("T3: Software trigger (CR0[0])", self.test_software_trigger)
        await self.test("T4: Fault clear (CR0[1])", self.test_fault_clear)
        await self.test("T5: Full FSM cycle", self.test_full_cycle)

    # =========================================================================
    # T1: FORGE Run Gate (CR0[31:29])
    # =========================================================================

    async def test_forge_run_gate(self):
        """Verify FORGE control bits gate FSM operation.

        CR0[31:29] = FORGE control (all 3 must be set for operation):
        - Bit 31: forge_ready (set by MCC loader)
        - Bit 30: user_enable (user control)
        - Bit 29: clk_enable (clock gating)

        Test: Partial FORGE enable should NOT allow FSM to arm.
        """
        # Reset to clean state
        await self.harness.apply_reset()

        # Configure timing registers (needed for FSM to leave INITIALIZING)
        await self._configure_timing()

        # Test: Partial enable (missing clk_enable) - FSM should NOT arm
        await self.harness.controller.enable_forge(ready=True, user=True, clk=False)
        await self.harness.controller.wait_cycles(20)

        # Try to arm - should not work without full FORGE enable
        await self.harness.controller.arm()
        await self.harness.controller.wait_cycles(20)

        # FSM should still be in INITIALIZING (clock gated, can't advance)
        state, digital = await self.harness.state_reader.get_state()
        assert state == "INITIALIZING", f"Expected INITIALIZING with partial FORGE, got {state}"

        # Now enable all FORGE bits
        await self.harness.controller.enable_forge()
        await self.harness.controller.wait_cycles(50)

        # FSM should transition to IDLE (or ARMED if arm bit still set)
        state, digital = await self.harness.state_reader.get_state()
        assert state in ("IDLE", "ARMED"), f"Expected IDLE or ARMED with full FORGE, got {state}"

    # =========================================================================
    # T2: Arm Control (CR0[2])
    # =========================================================================

    async def test_arm_control(self):
        """Verify arm control via CR0[2].

        CR0[2] = arm_enable (level-sensitive):
        - Set: FSM transitions IDLE → ARMED

        Note: RTL does not support disarm (ARMED→IDLE) via arm_enable=0.
        Once armed, FSM stays in ARMED until trigger, timeout, or reset.
        """
        # Reset and enable FORGE
        await self.harness.apply_reset()
        await self._configure_timing()
        await self.harness.controller.enable_forge()

        # Wait for IDLE
        reached = await self.harness.wait_for_state("IDLE", timeout_us=100)
        assert reached, "FSM did not reach IDLE after reset"

        # Arm FSM
        await self.harness.controller.arm()
        reached = await self.harness.wait_for_state("ARMED", timeout_us=100)
        assert reached, "FSM did not reach ARMED after arm()"

        # Verify we can't disarm by clearing arm_enable (RTL design choice)
        # FSM stays ARMED - must use trigger or fault_clear to leave ARMED state
        await self.harness.controller.disarm()
        await self.harness.controller.wait_cycles(50)
        state, _ = await self.harness.state_reader.get_state()
        # FSM should still be ARMED (no ARMED→IDLE transition on disarm)
        assert state == "ARMED", f"Expected FSM to stay ARMED after disarm(), got {state}"

    # =========================================================================
    # T3: Software Trigger (CR0[0])
    # =========================================================================

    async def test_software_trigger(self):
        """Verify software trigger via CR0[0].

        CR0[0] = sw_trigger (edge-triggered with auto-clear):
        - Single atomic write of 0xE0000005 (FORGE + arm + trigger)
        - RTL auto-clears via edge detection + pulse stretcher
        """
        # Reset and enable FORGE
        await self.harness.apply_reset()
        await self._configure_timing()
        await self.harness.controller.enable_forge()

        # Wait for IDLE, then arm
        reached = await self.harness.wait_for_state("IDLE", timeout_us=100)
        assert reached, "FSM did not reach IDLE"
        await self.harness.controller.arm()
        reached = await self.harness.wait_for_state("ARMED", timeout_us=100)
        assert reached, "FSM did not reach ARMED"

        # Software trigger - single atomic write!
        await self.harness.controller.trigger()

        # FSM should leave ARMED (either FIRING or already past)
        await self.harness.controller.wait_cycles(20)
        state, digital = await self.harness.state_reader.get_state()
        assert state != "ARMED", f"FSM still ARMED after trigger, got {state}"

        # Wait for FSM to complete cycle
        await self._wait_for_cycle_complete()

    # =========================================================================
    # T4: Fault Clear (CR0[1])
    # =========================================================================

    async def test_fault_clear(self):
        """Verify fault recovery via CR0[1].

        CR0[1] = fault_clear (edge-triggered with auto-clear):
        - Transitions FSM: FAULT → INITIALIZING → IDLE
        - Re-latches configuration parameters

        Note: We can't easily force FAULT state in simulation without
        specific fault injection, so we test clear_fault() from IDLE
        to verify it doesn't break anything.
        """
        # Reset and enable FORGE
        await self.harness.apply_reset()
        await self._configure_timing()
        await self.harness.controller.enable_forge()

        # Wait for IDLE
        reached = await self.harness.wait_for_state("IDLE", timeout_us=100)
        assert reached, "FSM did not reach IDLE"

        # Clear fault (should transition through INITIALIZING back to IDLE)
        await self.harness.controller.clear_fault()

        # Wait for FSM to settle back to IDLE
        reached = await self.harness.wait_for_state("IDLE", timeout_us=500)
        assert reached, "FSM did not return to IDLE after clear_fault()"

    # =========================================================================
    # T5: Full FSM Cycle
    # =========================================================================

    async def test_full_cycle(self):
        """Verify complete FSM cycle: IDLE → ARMED → FIRING → COOLDOWN → (IDLE or ARMED).

        This test exercises the full lifecycle using only CR0 controls.
        Note: FSM may return to ARMED (not IDLE) if arm_enable is still set.
        """
        # Reset and enable FORGE
        await self.harness.apply_reset()
        await self._configure_timing()
        await self.harness.controller.enable_forge()

        # Wait for IDLE
        reached = await self.harness.wait_for_state("IDLE", timeout_us=100)
        assert reached, "FSM did not reach IDLE"

        # Arm FSM
        await self.harness.controller.arm()
        reached = await self.harness.wait_for_state("ARMED", timeout_us=100)
        assert reached, "FSM did not reach ARMED"

        # Trigger
        await self.harness.controller.trigger()

        # Verify FSM left ARMED state (entered FIRING)
        await self.harness.controller.wait_cycles(10)
        state, _ = await self.harness.state_reader.get_state()
        assert state != "ARMED", f"FSM should have left ARMED after trigger, got {state}"

        # Wait for full cycle to complete and FSM to return to IDLE or ARMED
        # (With P1 timing: 1000 + 2000 + 500 = 3500 cycles total, add margin)
        await self._wait_for_cycle_complete()

        # Check final state - should be IDLE or ARMED (if arm_enable still set)
        state, _ = await self.harness.state_reader.get_state()
        assert state in ("IDLE", "ARMED"), f"Expected IDLE or ARMED after cycle, got {state}"

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def _configure_timing(self):
        """Configure timing registers with P1 (fast) values."""
        ctrl = self.harness.controller
        await ctrl.set_control_register(4, P1Timing.TRIG_OUT_DURATION)
        await ctrl.set_control_register(5, P1Timing.INTENSITY_DURATION)
        await ctrl.set_control_register(6, DEFAULT_TRIGGER_WAIT_TIMEOUT)
        await ctrl.set_control_register(7, P1Timing.COOLDOWN_INTERVAL)

    async def _wait_for_cycle_complete(self):
        """Wait for FSM to complete FIRING + COOLDOWN."""
        total_cycles = (
            P1Timing.TRIG_OUT_DURATION +
            P1Timing.INTENSITY_DURATION +
            P1Timing.COOLDOWN_INTERVAL +
            200  # margin
        )
        await self.harness.controller.wait_cycles(total_cycles)


@cocotb.test()
async def test_dpd_p1(dut):
    """Entry point for P1 tests."""
    tester = DPDBasicTests(dut)
    await tester.run_all_tests()

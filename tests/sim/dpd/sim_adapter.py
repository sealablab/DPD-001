"""
CocoTB Simulation Adapter
=========================

Implements the abstract FSM interfaces for CocoTB simulation testing.
Provides CocoTBStateReader, CocoTBController, and CocoTBTestHarness.

Author: Moku Instrument Forge Team
Date: 2025-11-26
"""

import sys
from pathlib import Path
from typing import Optional

# Add shared module to path
TESTS_PATH = Path(__file__).parent.parent.parent
sys.path.insert(0, str(TESTS_PATH))

from cocotb.triggers import ClockCycles

from shared.state_helpers import FSMStateReader, FSMController, FSMTestHarness
from shared.constants import (
    SIM_HVS_TOLERANCE,
    Platform,
)


class CocoTBStateReader(FSMStateReader):
    """CocoTB implementation of FSMStateReader.

    Reads OutputC directly from the DUT signal.
    """

    def __init__(self, dut):
        """Initialize with CocoTB DUT.

        Args:
            dut: CocoTB DUT object with OutputC signal
        """
        self.dut = dut

    def read_state_digital(self) -> int:
        """Read OutputC as signed digital value.

        Returns:
            Signed 16-bit digital value from OutputC
        """
        return int(self.dut.OutputC.value.to_signed())


class CocoTBController(FSMController):
    """CocoTB implementation of FSMController.

    Sets Control Registers directly on the DUT signals.
    """

    def __init__(self, dut):
        """Initialize with CocoTB DUT.

        Args:
            dut: CocoTB DUT object with ControlN signals
        """
        self.dut = dut
        self._pending_waits = []  # Store waits for async execution

    def set_control_register(self, reg_num: int, value: int):
        """Set a control register value.

        Args:
            reg_num: Register number (0-15)
            value: 32-bit value to set
        """
        ctrl_signal = getattr(self.dut, f"Control{reg_num}", None)
        if ctrl_signal is not None:
            ctrl_signal.value = value
        else:
            raise ValueError(f"Control register {reg_num} not found on DUT")

    def get_control_register(self, reg_num: int) -> int:
        """Get a control register value.

        Args:
            reg_num: Register number (0-15)

        Returns:
            Current 32-bit register value
        """
        ctrl_signal = getattr(self.dut, f"Control{reg_num}", None)
        if ctrl_signal is not None:
            return int(ctrl_signal.value)
        else:
            raise ValueError(f"Control register {reg_num} not found on DUT")

    def wait_cycles(self, cycles: int):
        """Store cycles to wait - must be awaited separately.

        Note: CocoTB requires async/await. This method stores the wait
        which must be executed via wait_pending() in an async context.

        Args:
            cycles: Number of clock cycles to wait
        """
        self._pending_waits.append(cycles)

    def wait_time_us(self, microseconds: float):
        """Convert microseconds to cycles and store wait.

        Args:
            microseconds: Time to wait in microseconds
        """
        cycles = int(microseconds * Platform.CLK_FREQ_HZ / 1e6)
        self.wait_cycles(cycles)

    async def wait_pending(self):
        """Execute all pending waits. Call from async context."""
        total_cycles = sum(self._pending_waits)
        self._pending_waits.clear()
        if total_cycles > 0:
            await ClockCycles(self.dut.Clk, total_cycles)

    async def async_wait_cycles(self, cycles: int):
        """Directly await clock cycles.

        Args:
            cycles: Number of clock cycles to wait
        """
        await ClockCycles(self.dut.Clk, cycles)


class CocoTBTestHarness(FSMTestHarness):
    """CocoTB implementation of FSMTestHarness.

    Combines state reading and control for CocoTB tests.
    """

    def __init__(self, dut):
        """Initialize with CocoTB DUT.

        Args:
            dut: CocoTB DUT object
        """
        self.dut = dut
        self._state_reader = CocoTBStateReader(dut)
        self._controller = CocoTBController(dut)

    @property
    def state_reader(self) -> FSMStateReader:
        """Get the state reader instance."""
        return self._state_reader

    @property
    def controller(self) -> FSMController:
        """Get the controller instance."""
        return self._controller

    async def wait_for_state(self, target_state: str, timeout_us: int = 100,
                              tolerance: int = SIM_HVS_TOLERANCE) -> bool:
        """Wait for FSM to reach target state.

        Args:
            target_state: Target state name
            timeout_us: Timeout in microseconds
            tolerance: Allowed deviation in digital units

        Returns:
            True if state reached, False on timeout
        """
        from shared.constants import (
            HVS_DIGITAL_INITIALIZING,
            HVS_DIGITAL_IDLE,
            HVS_DIGITAL_ARMED,
            HVS_DIGITAL_FIRING,
            HVS_DIGITAL_COOLDOWN,
        )

        state_map = {
            "INITIALIZING": HVS_DIGITAL_INITIALIZING,
            "IDLE": HVS_DIGITAL_IDLE,
            "ARMED": HVS_DIGITAL_ARMED,
            "FIRING": HVS_DIGITAL_FIRING,
            "COOLDOWN": HVS_DIGITAL_COOLDOWN,
        }

        target_digital = state_map.get(target_state)
        if target_digital is None:
            raise ValueError(f"Unknown state: {target_state}")

        timeout_cycles = int(timeout_us * Platform.CLK_FREQ_HZ / 1e6)

        for cycle in range(timeout_cycles):
            actual = self._state_reader.read_state_digital()
            if abs(actual - target_digital) <= tolerance:
                self.dut._log.info(
                    f"  \u2713 Reached {target_state} (OutputC={actual}) after {cycle} cycles"
                )
                return True
            await ClockCycles(self.dut.Clk, 1)

        # Timeout
        actual = self._state_reader.read_state_digital()
        self.dut._log.warning(
            f"Timeout waiting for {target_state}, stuck at OutputC={actual}"
        )
        return False

    async def assert_state(self, expected_state: str, context: str = "",
                           tolerance: int = SIM_HVS_TOLERANCE):
        """Assert FSM is in expected state.

        Args:
            expected_state: Expected state name
            context: Optional context for error message
            tolerance: Allowed deviation in digital units

        Raises:
            AssertionError: If state doesn't match expected
        """
        state, digital = self._state_reader.get_state()

        assert state == expected_state, (
            f"State mismatch{' (' + context + ')' if context else ''}: "
            f"expected {expected_state}, got {state} (digital={digital})"
        )

    async def apply_reset(self, cycles: int = 10):
        """Apply reset pulse.

        Args:
            cycles: Number of cycles to hold reset
        """
        self.dut.Reset.value = 1
        await ClockCycles(self.dut.Clk, cycles)
        self.dut.Reset.value = 0
        await ClockCycles(self.dut.Clk, 5)

    async def init_inputs(self):
        """Initialize all inputs to zero."""
        for input_name in ["InputA", "InputB", "InputC", "InputD"]:
            if hasattr(self.dut, input_name):
                getattr(self.dut, input_name).value = 0

    async def arm_fsm(self, timing_config):
        """Arm the FSM with specified timing.

        Args:
            timing_config: P1Timing or P2Timing class with timing constants
        """
        self._controller.configure_timing(
            trig_duration=timing_config.TRIG_OUT_DURATION,
            intensity_duration=timing_config.INTENSITY_DURATION,
            cooldown=timing_config.COOLDOWN_INTERVAL,
        )
        self._controller.set_cr1(arm_enable=True)
        await self._controller.async_wait_cycles(100)

    async def software_trigger(self):
        """Issue a software trigger."""
        self._controller.set_cr1(
            arm_enable=True,
            sw_trigger_enable=True,
            sw_trigger=True,
        )
        await self._controller.async_wait_cycles(10)
        self._controller.set_cr1(
            arm_enable=True,
            sw_trigger_enable=True,
            sw_trigger=False,
        )

    async def reset_to_idle(self) -> bool:
        """Reset FSM to IDLE state.

        Returns:
            True if IDLE reached, False on failure
        """
        await self.apply_reset()
        self._controller.set_forge_ready()
        await self._controller.async_wait_cycles(100)
        return await self.wait_for_state("IDLE", timeout_us=1000)

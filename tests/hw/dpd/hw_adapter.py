"""
Moku Hardware Adapter
=====================

Implements the abstract FSM interfaces for Moku hardware testing.
Provides MokuStateReader, MokuController, and MokuTestHarness.

Author: Moku Instrument Forge Team
Date: 2025-11-26
"""

import time
import sys
from pathlib import Path
from typing import Optional, Tuple

# Add shared module to path
TESTS_PATH = Path(__file__).parent.parent
sys.path.insert(0, str(TESTS_PATH))

from shared.state_helpers import FSMStateReader, FSMController, FSMTestHarness
from shared.constants import (
    HW_HVS_TOLERANCE_V,
    STATE_VOLTAGE_MAP,
    Platform,
    Timeouts,
)


class MokuStateReader(FSMStateReader):
    """Moku implementation of FSMStateReader.

    Reads OutputC via oscilloscope polling with averaging.
    """

    def __init__(self, osc, poll_count: int = Timeouts.OSC_POLL_COUNT,
                 poll_interval_ms: float = Timeouts.OSC_POLL_INTERVAL_MS):
        """Initialize with oscilloscope instance.

        Args:
            osc: Moku Oscilloscope instrument instance
            poll_count: Number of samples to average
            poll_interval_ms: Interval between samples in ms
        """
        self.osc = osc
        self.poll_count = poll_count
        self.poll_interval_ms = poll_interval_ms

    def read_state_digital(self) -> int:
        """Read OutputC as signed digital value.

        Reads voltage and converts to digital units.

        Returns:
            Signed 16-bit digital value equivalent
        """
        voltage = self.read_state_voltage()
        return int((voltage / 5.0) * 32768)

    def read_state_voltage(self) -> float:
        """Read OutputC as voltage (V) with averaging.

        Returns:
            Average voltage reading from oscilloscope Ch1
        """
        voltages = []
        for _ in range(self.poll_count):
            try:
                data = self.osc.get_data()
                if 'ch1' in data and len(data['ch1']) > 0:
                    # Sample middle of waveform buffer for stability
                    midpoint = len(data['ch1']) // 2
                    voltages.append(data['ch1'][midpoint])
            except Exception:
                pass  # Skip failed reads
            time.sleep(self.poll_interval_ms / 1000.0)

        if not voltages:
            raise RuntimeError("Failed to read oscilloscope data (no ch1 data)")

        return sum(voltages) / len(voltages)

    def get_state(self) -> Tuple[str, float]:
        """Get current FSM state from voltage reading.

        Returns:
            Tuple of (state_name, voltage)
        """
        voltage = self.read_state_voltage()
        state = self.decode_state_from_voltage(voltage)
        return state, voltage


class MokuController(FSMController):
    """Moku implementation of FSMController.

    Sets Control Registers via CloudCompile API.
    """

    def __init__(self, mcc):
        """Initialize with CloudCompile instance.

        Args:
            mcc: Moku CloudCompile instrument instance
        """
        self.mcc = mcc

    def set_control_register(self, reg_num: int, value: int):
        """Set a control register value.

        Args:
            reg_num: Register number (0-15)
            value: 32-bit value to set
        """
        self.mcc.set_control(reg_num, value)

    def get_control_register(self, reg_num: int) -> int:
        """Get a control register value.

        Args:
            reg_num: Register number (0-15)

        Returns:
            Current 32-bit register value
        """
        result = self.mcc.get_control(reg_num)
        # Handle different return types from Moku API
        if isinstance(result, list):
            return result[0] if result else 0
        elif isinstance(result, dict):
            return result.get('value', result.get('id', 0))
        return result

    def wait_cycles(self, cycles: int):
        """Wait for equivalent time of N clock cycles.

        Args:
            cycles: Number of clock cycles (converted to time)
        """
        time_sec = cycles / Platform.CLK_FREQ_HZ
        time.sleep(max(time_sec, 0.001))  # Minimum 1ms

    def wait_time_us(self, microseconds: float):
        """Wait for a duration in microseconds.

        Args:
            microseconds: Time to wait in microseconds
        """
        time.sleep(max(microseconds / 1e6, 0.001))


class MokuTestHarness(FSMTestHarness):
    """Moku implementation of FSMTestHarness.

    Combines state reading and control for hardware tests.
    """

    def __init__(self, mcc, osc):
        """Initialize with Moku instruments.

        Args:
            mcc: CloudCompile instrument instance
            osc: Oscilloscope instrument instance
        """
        self.mcc = mcc
        self.osc = osc
        self._state_reader = MokuStateReader(osc)
        self._controller = MokuController(mcc)

    @property
    def state_reader(self) -> FSMStateReader:
        """Get the state reader instance."""
        return self._state_reader

    @property
    def controller(self) -> FSMController:
        """Get the controller instance."""
        return self._controller

    def wait_for_state(self, target_state: str, timeout_us: int = 100,
                       tolerance: float = HW_HVS_TOLERANCE_V) -> bool:
        """Wait for FSM to reach target state.

        Args:
            target_state: Target state name
            timeout_us: Timeout in microseconds (converted to ms for HW)
            tolerance: Allowed deviation in V

        Returns:
            True if state reached, False on timeout
        """
        # Convert timeout to ms for hardware
        timeout_ms = max(timeout_us / 1000.0, Timeouts.HW_STATE_DEFAULT_MS)

        start_time = time.time()
        poll_interval_s = Timeouts.OSC_POLL_INTERVAL_MS / 1000.0

        while (time.time() - start_time) * 1000 < timeout_ms:
            state, voltage = self._state_reader.get_state()
            if state == target_state:
                return True
            time.sleep(poll_interval_s)

        return False

    def assert_state(self, expected_state: str, context: str = "",
                     tolerance: float = HW_HVS_TOLERANCE_V):
        """Assert FSM is in expected state.

        Args:
            expected_state: Expected state name
            context: Optional context for error message
            tolerance: Allowed deviation in V

        Raises:
            AssertionError: If state doesn't match expected
        """
        state, voltage = self._state_reader.get_state()

        assert state == expected_state, (
            f"State mismatch{' (' + context + ')' if context else ''}: "
            f"expected {expected_state}, got {state} ({voltage:.3f}V)"
        )

    def arm_fsm(self, timing_config):
        """Arm the FSM with specified timing.

        Args:
            timing_config: P1Timing or P2Timing class with timing constants
        """
        self._controller.configure_timing(
            trig_duration=timing_config.TRIG_OUT_DURATION,
            intensity_duration=timing_config.INTENSITY_DURATION,
            cooldown=timing_config.COOLDOWN_INTERVAL,
        )
        # Allow timing to propagate before setting arm
        time.sleep(0.2)
        self._controller.set_cr1(arm_enable=True)
        time.sleep(0.1)

    def software_trigger(self):
        """Issue a software trigger."""
        self._controller.set_cr1(
            arm_enable=True,
            sw_trigger_enable=True,
            sw_trigger=True,
        )
        time.sleep(0.05)
        self._controller.set_cr1(
            arm_enable=True,
            sw_trigger_enable=True,
            sw_trigger=False,
        )
        time.sleep(0.05)

    def reset_to_idle(self, timeout_ms: float = 2000) -> bool:
        """Reset FSM to IDLE state.

        Args:
            timeout_ms: Timeout in milliseconds

        Returns:
            True if IDLE reached, False on failure
        """
        # Ensure FORGE control is enabled
        self._controller.set_forge_ready()
        time.sleep(0.1)

        # Clear all application registers
        for i in range(1, 16):
            try:
                self._controller.set_control_register(i, 0)
            except Exception:
                pass
        time.sleep(0.2)

        # Pulse fault_clear
        self._controller.set_cr1(fault_clear=True)
        time.sleep(0.05)
        self._controller.set_cr1(fault_clear=False)
        time.sleep(0.2)

        return self.wait_for_state("IDLE", timeout_us=timeout_ms * 1000)

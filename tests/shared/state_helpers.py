"""
Abstract State Helper Interface
===============================

Abstract interface for FSM state operations that can be implemented
differently for simulation (CocoTB) and hardware (Moku) tests.

Author: Moku Instrument Forge Team
Date: 2025-11-26
"""

from abc import ABC, abstractmethod
from typing import Tuple, Optional

from .constants import (
    HVS,
    HVS_DIGITAL_INITIALIZING,
    HVS_DIGITAL_IDLE,
    HVS_DIGITAL_ARMED,
    HVS_DIGITAL_FIRING,
    HVS_DIGITAL_COOLDOWN,
    STATE_VOLTAGE_MAP,
    SIM_HVS_TOLERANCE,
    HW_HVS_TOLERANCE_V,
)


class FSMStateReader(ABC):
    """Abstract interface for reading FSM state from OutputC.

    Implementations:
    - CocoTBStateReader: Reads dut.OutputC.value directly
    - MokuStateReader: Reads via oscilloscope polling
    """

    @abstractmethod
    def read_state_digital(self) -> int:
        """Read OutputC as signed digital value.

        Returns:
            Signed 16-bit digital value from OutputC
        """
        pass

    def read_state_voltage(self) -> float:
        """Read OutputC as voltage (V).

        Returns:
            Voltage in V (derived from digital value)
        """
        digital = self.read_state_digital()
        return HVS.digital_to_volts(digital)

    def decode_state_from_digital(self, digital: int,
                                   tolerance: int = SIM_HVS_TOLERANCE) -> str:
        """Decode FSM state from digital value.

        Args:
            digital: Digital value from OutputC
            tolerance: Allowed deviation in digital units

        Returns:
            State name (INITIALIZING, IDLE, ARMED, FIRING, COOLDOWN, FAULT, UNKNOWN)
        """
        state_map = {
            "INITIALIZING": HVS_DIGITAL_INITIALIZING,
            "IDLE": HVS_DIGITAL_IDLE,
            "ARMED": HVS_DIGITAL_ARMED,
            "FIRING": HVS_DIGITAL_FIRING,
            "COOLDOWN": HVS_DIGITAL_COOLDOWN,
        }

        # Check for fault (negative value beyond tolerance)
        if digital < -tolerance:
            return "FAULT"

        # Check each state
        for state_name, expected_digital in state_map.items():
            if abs(digital - expected_digital) <= tolerance:
                return state_name

        return f"UNKNOWN({digital})"

    def decode_state_from_voltage(self, voltage: float,
                                   tolerance: float = HW_HVS_TOLERANCE_V) -> str:
        """Decode FSM state from voltage reading.

        Args:
            voltage: Voltage in V from OutputC
            tolerance: Allowed deviation in V

        Returns:
            State name (INITIALIZING, IDLE, ARMED, FIRING, COOLDOWN, FAULT, UNKNOWN)
        """
        # Check for fault (any negative voltage)
        if voltage < -tolerance:
            return "FAULT"

        # Check each state
        for state_name, expected_voltage in STATE_VOLTAGE_MAP.items():
            if abs(voltage - expected_voltage) < tolerance:
                return state_name

        return f"UNKNOWN({voltage:.3f}V)"

    def get_state(self) -> Tuple[str, int]:
        """Get current FSM state.

        Returns:
            Tuple of (state_name, digital_value)
        """
        digital = self.read_state_digital()
        state = self.decode_state_from_digital(digital)
        return state, digital

    def assert_state(self, expected_state: str, context: str = "",
                     tolerance: int = SIM_HVS_TOLERANCE):
        """Assert FSM is in expected state.

        Args:
            expected_state: Expected state name
            context: Optional context for error message
            tolerance: Allowed deviation in digital units

        Raises:
            AssertionError: If state doesn't match expected
        """
        state, digital = self.get_state()

        assert state == expected_state, (
            f"State mismatch{' (' + context + ')' if context else ''}: "
            f"expected {expected_state}, got {state} (digital={digital})"
        )


class FSMController(ABC):
    """Abstract interface for controlling the FSM via Control Registers.

    Implementations:
    - CocoTBController: Sets dut.ControlN.value directly
    - MokuController: Uses mcc.set_control() API
    """

    @abstractmethod
    def set_control_register(self, reg_num: int, value: int):
        """Set a control register value.

        Args:
            reg_num: Register number (0-15)
            value: 32-bit value to set
        """
        pass

    @abstractmethod
    def get_control_register(self, reg_num: int) -> int:
        """Get a control register value.

        Args:
            reg_num: Register number (0-15)

        Returns:
            Current 32-bit register value
        """
        pass

    @abstractmethod
    def wait_cycles(self, cycles: int):
        """Wait for N clock cycles.

        For simulation: await ClockCycles(dut.Clk, cycles)
        For hardware: time.sleep(cycles / 125_000_000)

        Args:
            cycles: Number of clock cycles to wait
        """
        pass

    @abstractmethod
    def wait_time_us(self, microseconds: float):
        """Wait for a duration in microseconds.

        Args:
            microseconds: Time to wait in microseconds
        """
        pass

    def set_forge_ready(self):
        """Enable FORGE control (CR0[31:29] = 0b111)."""
        from .constants import MCC_CR0_ALL_ENABLED
        self.set_control_register(0, MCC_CR0_ALL_ENABLED)
        self.wait_cycles(100)  # Allow propagation

    def clear_forge_ready(self):
        """Disable FORGE control."""
        self.set_control_register(0, 0x00000000)
        self.wait_cycles(100)

    def set_cr1(self, **kwargs):
        """Set CR1 using named parameters.

        Args:
            arm_enable: bool
            auto_rearm_enable: bool
            fault_clear: bool
            sw_trigger_enable: bool
            hw_trigger_enable: bool
            sw_trigger: bool
        """
        from .constants import cr1_build
        value = cr1_build(**kwargs)
        self.set_control_register(1, value)

    def configure_timing(self, trig_duration: int, intensity_duration: int,
                         cooldown: int, timeout: Optional[int] = None):
        """Configure FSM timing registers.

        Args:
            trig_duration: CR4 - trigger output duration (cycles)
            intensity_duration: CR5 - intensity output duration (cycles)
            cooldown: CR7 - cooldown interval (cycles)
            timeout: CR6 - trigger wait timeout (cycles), optional
        """
        self.set_control_register(4, trig_duration)
        self.set_control_register(5, intensity_duration)
        self.set_control_register(7, cooldown)
        if timeout is not None:
            self.set_control_register(6, timeout)

    def configure_voltages(self, threshold_mv: int, trig_voltage_mv: int,
                           intensity_voltage_mv: int):
        """Configure voltage registers.

        Args:
            threshold_mv: Trigger threshold in mV (CR2[31:16])
            trig_voltage_mv: Trigger output voltage in mV (CR2[15:0])
            intensity_voltage_mv: Intensity output voltage in mV (CR3)
        """
        cr2 = ((threshold_mv & 0xFFFF) << 16) | (trig_voltage_mv & 0xFFFF)
        self.set_control_register(2, cr2)
        self.set_control_register(3, intensity_voltage_mv & 0xFFFF)


class FSMTestHarness(ABC):
    """Combined test harness providing both state reading and control.

    Provides high-level test operations that combine state reading and control.
    """

    @property
    @abstractmethod
    def state_reader(self) -> FSMStateReader:
        """Get the state reader instance."""
        pass

    @property
    @abstractmethod
    def controller(self) -> FSMController:
        """Get the controller instance."""
        pass

    @abstractmethod
    def wait_for_state(self, target_state: str, timeout_us: int = 100,
                       tolerance: int = SIM_HVS_TOLERANCE) -> bool:
        """Wait for FSM to reach target state.

        Args:
            target_state: Target state name
            timeout_us: Timeout in microseconds
            tolerance: Allowed deviation in digital units

        Returns:
            True if state reached, False on timeout
        """
        pass

    def arm_fsm(self, timing_config):
        """Arm the FSM with specified timing.

        Args:
            timing_config: P1Timing or P2Timing class with timing constants
        """
        self.controller.configure_timing(
            trig_duration=timing_config.TRIG_OUT_DURATION,
            intensity_duration=timing_config.INTENSITY_DURATION,
            cooldown=timing_config.COOLDOWN_INTERVAL,
        )
        self.controller.set_cr1(arm_enable=True)
        self.controller.wait_cycles(100)

    def software_trigger(self):
        """Issue a software trigger.

        Sets sw_trigger_enable and sw_trigger bits, then clears sw_trigger.
        """
        self.controller.set_cr1(
            arm_enable=True,
            sw_trigger_enable=True,
            sw_trigger=True,
        )
        self.controller.wait_cycles(10)
        # Clear trigger bit (edge-detected)
        self.controller.set_cr1(
            arm_enable=True,
            sw_trigger_enable=True,
            sw_trigger=False,
        )

    def reset_to_idle(self) -> bool:
        """Reset FSM to IDLE state.

        Returns:
            True if IDLE reached, False on failure
        """
        # Clear all control except FORGE
        for i in range(1, 16):
            self.controller.set_control_register(i, 0)
        self.controller.wait_cycles(100)

        # Pulse fault_clear in case we're in FAULT state
        self.controller.set_cr1(fault_clear=True)
        self.controller.wait_cycles(10)
        self.controller.set_cr1(fault_clear=False)
        self.controller.wait_cycles(100)

        return self.wait_for_state("IDLE", timeout_us=1000)

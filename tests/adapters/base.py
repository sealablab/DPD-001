"""
Async Adapter Base Classes (API v4.0)
=====================================

Abstract interfaces for unified sim/hardware testing with strict CR0 protection.

CR0 Protection:
  - FORGE bits [31:29]: Only modifiable via enable_forge() / disable_forge()
  - Lifecycle bits [2:0]: Only modifiable via arm() / disarm() / trigger() / clear_fault()
  - No direct CR0 access from tests

Reference: docs/api-v4.md
"""

from abc import ABC, abstractmethod
from typing import Tuple, Optional

# Import from lib for constants
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib import (
    Platform,
    HVS,
    CR0,
    HVS_DIGITAL_INITIALIZING,
    HVS_DIGITAL_IDLE,
    HVS_DIGITAL_ARMED,
    HVS_DIGITAL_FIRING,
    HVS_DIGITAL_COOLDOWN,
    SIM_HVS_TOLERANCE,
)

CLK_FREQ_HZ = Platform.CLK_FREQ_HZ


class AsyncFSMController(ABC):
    """Abstract async interface for FSM control register operations.

    CR0 Protection:
        CR0 is fully encapsulated. All access is through dedicated methods.
        - FORGE bits [31:29]: enable_forge() / disable_forge()
        - Lifecycle bits [2:0]: arm() / disarm() / trigger() / clear_fault()

        The controller tracks both FORGE and lifecycle state internally
        and combines them on every write to CR0.

    Configuration registers (CR2-CR10) remain directly accessible via
    set_control_register() for configuration purposes.
    """

    def __init__(self):
        """Initialize CR0 state tracking."""
        self._forge_state: int = 0      # Tracks CR0[31:29]
        self._lifecycle_state: int = 0  # Tracks CR0[2:0]

    @abstractmethod
    async def set_control_register(self, reg_num: int, value: int):
        """Set a control register value.

        Note: For CR0, use the dedicated FORGE/lifecycle methods instead.
        Direct CR0 access is only used internally.
        """
        pass

    @abstractmethod
    async def get_control_register(self, reg_num: int) -> int:
        """Get a control register value."""
        pass

    @abstractmethod
    async def wait_cycles(self, cycles: int):
        """Wait for N clock cycles."""
        pass

    async def _write_cr0(self):
        """Internal: Combine FORGE + lifecycle and write CR0."""
        await self.set_control_register(0, self._forge_state | self._lifecycle_state)

    # =========================================================================
    # FORGE Control (CR0[31:29]) - The only way to modify FORGE bits
    # =========================================================================

    async def enable_forge(self, ready: bool = True, user: bool = True, clk: bool = True):
        """Enable FORGE control bits. Call at test setup.

        Args:
            ready: Set forge_ready (CR0[31]) - normally set by MCC loader
            user:  Set user_enable (CR0[30]) - user control
            clk:   Set clk_enable (CR0[29]) - clock gating

        For normal tests, call with no args to enable all.
        For FORGE safety tests, pass specific bits to test partial enable.
        """
        self._forge_state = (
            (CR0.FORGE_READY_MASK if ready else 0) |
            (CR0.USER_ENABLE_MASK if user else 0) |
            (CR0.CLK_ENABLE_MASK if clk else 0)
        )
        await self._write_cr0()

    async def disable_forge(self):
        """Disable all FORGE control bits."""
        self._forge_state = 0
        self._lifecycle_state = 0  # Also clear lifecycle when FORGE disabled
        await self._write_cr0()

    # =========================================================================
    # Lifecycle Control (CR0[2:0]) - The only way to modify lifecycle bits
    # =========================================================================

    async def arm(self):
        """Arm FSM (IDLE → ARMED). Sets CR0[2]."""
        self._lifecycle_state |= CR0.ARM_ENABLE_MASK
        await self._write_cr0()

    async def disarm(self):
        """Disarm FSM (ARMED → IDLE). Clears CR0[2]."""
        self._lifecycle_state &= ~CR0.ARM_ENABLE_MASK
        await self._write_cr0()

    async def trigger(self):
        """Fire software trigger. Single atomic write with arm preserved.

        This is the v4.0 "atomic trigger" - a single write of 0xE0000005
        that includes FORGE + arm + trigger in one operation.

        The RTL auto-clears trigger via edge detection + pulse stretcher,
        so no explicit clear is needed.
        """
        # Atomic: FORGE + arm + trigger in one write
        await self.set_control_register(0,
            self._forge_state | CR0.ARM_ENABLE_MASK | CR0.SW_TRIGGER_MASK)
        # RTL auto-clears trigger via edge detection + pulse stretcher

    async def clear_fault(self):
        """Clear fault state. Edge-triggered with auto-clear.

        Transitions FSM: FAULT → INITIALIZING → IDLE
        """
        await self.set_control_register(0,
            self._forge_state | CR0.FAULT_CLEAR_MASK)
        await self.wait_cycles(10)  # Let edge detection capture it
        # After clear, FSM goes to INITIALIZING then IDLE
        self._lifecycle_state = 0  # Reset lifecycle tracking

    # =========================================================================
    # Configuration Register Access (CR2-CR10)
    # =========================================================================

    async def configure_timing(self, trig_duration: int, intensity_duration: int,
                                cooldown: int, timeout: Optional[int] = None):
        """Configure FSM timing registers (CR4, CR5, CR7, optionally CR6)."""
        await self.set_control_register(4, trig_duration)
        await self.set_control_register(5, intensity_duration)
        await self.set_control_register(7, cooldown)
        if timeout is not None:
            await self.set_control_register(6, timeout)

    async def apply_config(self, config):
        """Apply a DPDConfig to registers CR2-CR10.

        Args:
            config: DPDConfig instance with configuration values

        Note: This does not modify CR0 or CR1. Use enable_forge() and arm()
        for lifecycle control.
        """
        for reg in config.to_app_regs_list():
            await self.set_control_register(reg["idx"], reg["value"])

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    async def wait_us(self, microseconds: float):
        """Wait for a duration in microseconds."""
        cycles = int(microseconds * CLK_FREQ_HZ / 1e6)
        await self.wait_cycles(cycles)

    async def wait_ms(self, milliseconds: float):
        """Wait for a duration in milliseconds."""
        await self.wait_us(milliseconds * 1000)


class AsyncFSMStateReader(ABC):
    """Abstract async interface for reading FSM state."""

    @abstractmethod
    async def read_state_digital(self) -> int:
        """Read OutputC as signed digital value."""
        pass

    async def read_state_voltage(self) -> float:
        """Read OutputC as voltage (V)."""
        digital = await self.read_state_digital()
        return HVS.digital_to_volts(digital)

    async def get_state(self) -> Tuple[str, int]:
        """Get current FSM state."""
        digital = await self.read_state_digital()
        state = decode_state_from_digital(digital)
        return state, digital


class AsyncFSMTestHarness(ABC):
    """Combined async test harness for FSM testing."""

    @property
    @abstractmethod
    def controller(self) -> AsyncFSMController:
        """Get the controller instance."""
        pass

    @property
    @abstractmethod
    def state_reader(self) -> AsyncFSMStateReader:
        """Get the state reader instance."""
        pass

    @abstractmethod
    async def wait_for_state(self, target_state: str, timeout_us: int = 1000,
                              tolerance: int = SIM_HVS_TOLERANCE) -> bool:
        """Wait for FSM to reach target state."""
        pass

    async def assert_state(self, expected_state: str, context: str = "",
                           tolerance: int = SIM_HVS_TOLERANCE):
        """Assert FSM is in expected state."""
        state, digital = await self.state_reader.get_state()
        assert state == expected_state, (
            f"State mismatch{' (' + context + ')' if context else ''}: "
            f"expected {expected_state}, got {state} (digital={digital})"
        )

    async def arm_fsm(self, timing_config=None):
        """Arm the FSM with optional timing configuration.

        Args:
            timing_config: Optional timing config with TRIG_OUT_DURATION,
                          INTENSITY_DURATION, COOLDOWN_INTERVAL attributes
        """
        if timing_config:
            await self.controller.configure_timing(
                trig_duration=timing_config.TRIG_OUT_DURATION,
                intensity_duration=timing_config.INTENSITY_DURATION,
                cooldown=timing_config.COOLDOWN_INTERVAL,
            )
        await self.controller.arm()
        await self.controller.wait_cycles(100)

    async def software_trigger(self):
        """Issue software trigger. Single atomic write."""
        await self.controller.trigger()

    async def reset_to_idle(self, timeout_us: int = 10000) -> bool:
        """Reset FSM to IDLE state via fault_clear."""
        # Clear configuration registers
        for i in range(2, 11):
            await self.controller.set_control_register(i, 0)
        await self.controller.wait_cycles(100)

        # Use fault_clear to transition to IDLE
        await self.controller.clear_fault()

        return await self.wait_for_state("IDLE", timeout_us=timeout_us)


# =============================================================================
# Helper functions
# =============================================================================

STATE_DIGITAL_MAP = {
    "INITIALIZING": HVS_DIGITAL_INITIALIZING,
    "IDLE": HVS_DIGITAL_IDLE,
    "ARMED": HVS_DIGITAL_ARMED,
    "FIRING": HVS_DIGITAL_FIRING,
    "COOLDOWN": HVS_DIGITAL_COOLDOWN,
}

STATE_VOLTAGE_MAP = HVS.STATE_VOLTAGE_MAP


def state_to_digital(state: str) -> Optional[int]:
    """Convert state name to digital value."""
    return STATE_DIGITAL_MAP.get(state)


def state_to_voltage(state: str) -> Optional[float]:
    """Convert state name to voltage."""
    return STATE_VOLTAGE_MAP.get(state)


def decode_state_from_digital(digital: int, tolerance: int = SIM_HVS_TOLERANCE) -> str:
    """Decode FSM state from digital value."""
    if digital < -tolerance:
        return "FAULT"

    for name, expected in STATE_DIGITAL_MAP.items():
        if abs(digital - expected) <= tolerance:
            return name

    return "UNKNOWN"

"""
Async Adapter Base Classes
==========================

Abstract interfaces for unified sim/hardware testing.

All wait operations are async:
- CocoTB: await ClockCycles(dut.Clk, N)
- Moku: await asyncio.sleep(seconds)
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
    cr1_build,
    HVS_DIGITAL_INITIALIZING,
    HVS_DIGITAL_IDLE,
    HVS_DIGITAL_ARMED,
    HVS_DIGITAL_FIRING,
    HVS_DIGITAL_COOLDOWN,
    SIM_HVS_TOLERANCE,
)

CLK_FREQ_HZ = Platform.CLK_FREQ_HZ


class AsyncFSMController(ABC):
    """Abstract async interface for FSM control register operations."""

    @abstractmethod
    async def set_control_register(self, reg_num: int, value: int):
        """Set a control register value."""
        pass

    @abstractmethod
    async def get_control_register(self, reg_num: int) -> int:
        """Get a control register value."""
        pass

    @abstractmethod
    async def wait_cycles(self, cycles: int):
        """Wait for N clock cycles."""
        pass

    async def wait_us(self, microseconds: float):
        """Wait for a duration in microseconds."""
        cycles = int(microseconds * CLK_FREQ_HZ / 1e6)
        await self.wait_cycles(cycles)

    async def wait_ms(self, milliseconds: float):
        """Wait for a duration in milliseconds."""
        await self.wait_us(milliseconds * 1000)

    async def set_forge_ready(self, wait_after: int = 0):
        """Enable FORGE control (CR0[31:29] = 0b111)."""
        MCC_CR0_ALL_ENABLED = 0xE0000000
        await self.set_control_register(0, MCC_CR0_ALL_ENABLED)
        if wait_after > 0:
            await self.wait_cycles(wait_after)

    async def clear_forge_ready(self):
        """Disable FORGE control."""
        await self.set_control_register(0, 0x00000000)
        await self.wait_cycles(100)

    async def set_cr1(self, **kwargs):
        """Set CR1 using named parameters."""
        value = cr1_build(**kwargs)
        await self.set_control_register(1, value)

    async def configure_timing(self, trig_duration: int, intensity_duration: int,
                                cooldown: int, timeout: Optional[int] = None):
        """Configure FSM timing registers (CR4, CR5, CR7, optionally CR6)."""
        await self.set_control_register(4, trig_duration)
        await self.set_control_register(5, intensity_duration)
        await self.set_control_register(7, cooldown)
        if timeout is not None:
            await self.set_control_register(6, timeout)


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

    async def arm_fsm(self, timing_config):
        """Arm the FSM with specified timing."""
        await self.controller.configure_timing(
            trig_duration=timing_config.TRIG_OUT_DURATION,
            intensity_duration=timing_config.INTENSITY_DURATION,
            cooldown=timing_config.COOLDOWN_INTERVAL,
        )
        await self.controller.set_cr1(arm_enable=True)
        await self.controller.wait_cycles(100)

    async def software_trigger(self):
        """Issue a software trigger."""
        await self.controller.set_cr1(
            arm_enable=True,
            sw_trigger_enable=True,
            sw_trigger=True,
        )
        await self.controller.wait_cycles(10)
        await self.controller.set_cr1(
            arm_enable=True,
            sw_trigger_enable=True,
            sw_trigger=False,
        )

    async def reset_to_idle(self, timeout_us: int = 10000) -> bool:
        """Reset FSM to IDLE state."""
        for i in range(1, 16):
            await self.controller.set_control_register(i, 0)
        await self.controller.wait_cycles(100)

        await self.controller.set_cr1(fault_clear=True)
        await self.controller.wait_cycles(10)
        await self.controller.set_cr1(fault_clear=False)
        await self.controller.wait_cycles(100)

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

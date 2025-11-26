"""
Unified Async Adapter Interface
===============================

Provides a common async interface for both CocoTB simulation and Moku hardware.
This enables "train like you fight" - same test code works on both platforms.

Key Design:
- All wait operations are `async def`
- CocoTB uses `await ClockCycles(dut.Clk, N)`
- Moku uses `await asyncio.sleep(seconds)`
- Optional jitter simulation for CocoTB to mimic network latency

Usage:
    # Simulation
    adapter = CocoTBAdapter(dut, jitter_enabled=True)

    # Hardware
    adapter = MokuAsyncAdapter(mcc, osc)

    # Same test code for both!
    await adapter.set_control_register(1, cr1_value)
    await adapter.wait_for_state("ARMED", timeout_us=1000)

Author: Moku Instrument Forge Team
Date: 2025-11-26
"""

import asyncio
import random
import time
from abc import ABC, abstractmethod
from typing import Tuple, Optional, Callable

# Platform constants
CLK_FREQ_HZ = 125_000_000
CLK_PERIOD_NS = 8


class AsyncFSMController(ABC):
    """Abstract async interface for FSM control register operations.

    All implementations must provide async methods for:
    - Setting/getting control registers
    - Waiting for time/cycles
    """

    @abstractmethod
    async def set_control_register(self, reg_num: int, value: int):
        """Set a control register value.

        Args:
            reg_num: Register number (0-15)
            value: 32-bit value to set
        """
        pass

    @abstractmethod
    async def get_control_register(self, reg_num: int) -> int:
        """Get a control register value.

        Args:
            reg_num: Register number (0-15)

        Returns:
            Current 32-bit register value
        """
        pass

    @abstractmethod
    async def wait_cycles(self, cycles: int):
        """Wait for N clock cycles.

        Args:
            cycles: Number of clock cycles to wait
        """
        pass

    async def wait_us(self, microseconds: float):
        """Wait for a duration in microseconds.

        Args:
            microseconds: Time to wait
        """
        cycles = int(microseconds * CLK_FREQ_HZ / 1e6)
        await self.wait_cycles(cycles)

    async def wait_ms(self, milliseconds: float):
        """Wait for a duration in milliseconds.

        Args:
            milliseconds: Time to wait
        """
        await self.wait_us(milliseconds * 1000)

    # -------------------------------------------------------------------------
    # Convenience methods (built on primitives above)
    # -------------------------------------------------------------------------

    async def set_forge_ready(self, wait_after: int = 0):
        """Enable FORGE control (CR0[31:29] = 0b111).

        Args:
            wait_after: Optional cycles to wait after setting. Default 0 for
                       immediate return (allows setting config registers quickly).
        """
        MCC_CR0_ALL_ENABLED = 0xE0000000
        await self.set_control_register(0, MCC_CR0_ALL_ENABLED)
        if wait_after > 0:
            await self.wait_cycles(wait_after)

    async def clear_forge_ready(self):
        """Disable FORGE control."""
        await self.set_control_register(0, 0x00000000)
        await self.wait_cycles(100)

    async def set_cr1(self, **kwargs):
        """Set CR1 using named parameters.

        Args:
            arm_enable: bool
            auto_rearm_enable: bool
            fault_clear: bool
            sw_trigger_enable: bool
            hw_trigger_enable: bool
            sw_trigger: bool
        """
        value = _cr1_build(**kwargs)
        await self.set_control_register(1, value)

    async def configure_timing(self, trig_duration: int, intensity_duration: int,
                                cooldown: int, timeout: Optional[int] = None):
        """Configure FSM timing registers.

        Args:
            trig_duration: CR4 - trigger output duration (cycles)
            intensity_duration: CR5 - intensity output duration (cycles)
            cooldown: CR7 - cooldown interval (cycles)
            timeout: CR6 - trigger wait timeout (cycles), optional
        """
        await self.set_control_register(4, trig_duration)
        await self.set_control_register(5, intensity_duration)
        await self.set_control_register(7, cooldown)
        if timeout is not None:
            await self.set_control_register(6, timeout)


class AsyncFSMStateReader(ABC):
    """Abstract async interface for reading FSM state."""

    @abstractmethod
    async def read_state_digital(self) -> int:
        """Read OutputC as signed digital value.

        Returns:
            Signed 16-bit digital value from OutputC
        """
        pass

    async def read_state_voltage(self) -> float:
        """Read OutputC as voltage (V).

        Returns:
            Voltage in V (derived from digital value)
        """
        digital = await self.read_state_digital()
        return (digital / 32768.0) * 5.0

    async def get_state(self) -> Tuple[str, int]:
        """Get current FSM state.

        Returns:
            Tuple of (state_name, digital_value)
        """
        digital = await self.read_state_digital()
        state = _decode_state_from_digital(digital)
        return state, digital


class AsyncFSMTestHarness(ABC):
    """Combined async test harness for FSM testing.

    Provides high-level async test operations.
    """

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
                              tolerance: int = 200) -> bool:
        """Wait for FSM to reach target state.

        Args:
            target_state: Target state name
            timeout_us: Timeout in microseconds
            tolerance: Allowed deviation in digital units

        Returns:
            True if state reached, False on timeout
        """
        pass

    async def assert_state(self, expected_state: str, context: str = "",
                           tolerance: int = 200):
        """Assert FSM is in expected state.

        Args:
            expected_state: Expected state name
            context: Optional context for error message
            tolerance: Allowed deviation in digital units

        Raises:
            AssertionError: If state doesn't match
        """
        state, digital = await self.state_reader.get_state()
        assert state == expected_state, (
            f"State mismatch{' (' + context + ')' if context else ''}: "
            f"expected {expected_state}, got {state} (digital={digital})"
        )

    async def arm_fsm(self, timing_config):
        """Arm the FSM with specified timing.

        Args:
            timing_config: Object with TRIG_OUT_DURATION, INTENSITY_DURATION,
                          COOLDOWN_INTERVAL attributes
        """
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
        # Clear trigger bit (edge-detected)
        await self.controller.set_cr1(
            arm_enable=True,
            sw_trigger_enable=True,
            sw_trigger=False,
        )

    async def reset_to_idle(self, timeout_us: int = 10000) -> bool:
        """Reset FSM to IDLE state.

        Returns:
            True if IDLE reached, False on failure
        """
        # Clear all control except FORGE
        for i in range(1, 16):
            await self.controller.set_control_register(i, 0)
        await self.controller.wait_cycles(100)

        # Pulse fault_clear in case we're in FAULT state
        await self.controller.set_cr1(fault_clear=True)
        await self.controller.wait_cycles(10)
        await self.controller.set_cr1(fault_clear=False)
        await self.controller.wait_cycles(100)

        return await self.wait_for_state("IDLE", timeout_us=timeout_us)


# =============================================================================
# CocoTB Implementation (with optional jitter)
# =============================================================================

class CocoTBAsyncController(AsyncFSMController):
    """CocoTB implementation with optional network-like jitter.

    When jitter_enabled=True, register writes are delayed by a random
    number of clock cycles to simulate network propagation delays.
    This helps catch race conditions that only manifest with async writes.
    """

    def __init__(self, dut, jitter_enabled: bool = False,
                 jitter_range: Tuple[int, int] = (10, 200)):
        """Initialize with CocoTB DUT.

        Args:
            dut: CocoTB DUT object
            jitter_enabled: If True, add random delays to register writes
            jitter_range: (min_cycles, max_cycles) for jitter delays
        """
        self.dut = dut
        self.jitter_enabled = jitter_enabled
        self.jitter_range = jitter_range
        self._clock_cycles = None  # Lazy import to avoid import issues

    def _get_clock_cycles(self):
        """Lazy import of ClockCycles to avoid import at module load."""
        if self._clock_cycles is None:
            from cocotb.triggers import ClockCycles
            self._clock_cycles = ClockCycles
        return self._clock_cycles

    async def set_control_register(self, reg_num: int, value: int):
        """Set control register with optional jitter delay."""
        ClockCycles = self._get_clock_cycles()

        # Apply jitter delay if enabled (simulates network latency)
        if self.jitter_enabled:
            delay = random.randint(*self.jitter_range)
            await ClockCycles(self.dut.Clk, delay)

        # Set the register
        ctrl_signal = getattr(self.dut, f"Control{reg_num}", None)
        if ctrl_signal is not None:
            ctrl_signal.value = value
        else:
            raise ValueError(f"Control register {reg_num} not found on DUT")

    async def get_control_register(self, reg_num: int) -> int:
        """Get control register value."""
        ctrl_signal = getattr(self.dut, f"Control{reg_num}", None)
        if ctrl_signal is not None:
            return int(ctrl_signal.value)
        raise ValueError(f"Control register {reg_num} not found on DUT")

    async def wait_cycles(self, cycles: int):
        """Wait for clock cycles."""
        ClockCycles = self._get_clock_cycles()
        if cycles > 0:
            await ClockCycles(self.dut.Clk, cycles)


class CocoTBAsyncStateReader(AsyncFSMStateReader):
    """CocoTB state reader - instant signal access."""

    def __init__(self, dut):
        self.dut = dut

    async def read_state_digital(self) -> int:
        """Read OutputC directly from DUT signal."""
        return int(self.dut.OutputC.value.to_signed())


class CocoTBAsyncHarness(AsyncFSMTestHarness):
    """CocoTB test harness with jitter support."""

    def __init__(self, dut, jitter_enabled: bool = False,
                 jitter_range: Tuple[int, int] = (10, 200)):
        """Initialize CocoTB harness.

        Args:
            dut: CocoTB DUT object
            jitter_enabled: Simulate network-like write delays
            jitter_range: (min_cycles, max_cycles) for jitter
        """
        self.dut = dut
        self._controller = CocoTBAsyncController(dut, jitter_enabled, jitter_range)
        self._state_reader = CocoTBAsyncStateReader(dut)

    @property
    def controller(self) -> AsyncFSMController:
        return self._controller

    @property
    def state_reader(self) -> AsyncFSMStateReader:
        return self._state_reader

    async def wait_for_state(self, target_state: str, timeout_us: int = 1000,
                              tolerance: int = 200) -> bool:
        """Wait for FSM state with cycle-accurate polling."""
        from cocotb.triggers import ClockCycles

        target_digital = _state_to_digital(target_state)
        if target_digital is None:
            raise ValueError(f"Unknown state: {target_state}")

        timeout_cycles = int(timeout_us * CLK_FREQ_HZ / 1e6)

        for _ in range(timeout_cycles):
            actual = await self._state_reader.read_state_digital()
            if abs(actual - target_digital) <= tolerance:
                return True
            await ClockCycles(self.dut.Clk, 1)

        return False

    async def apply_reset(self, cycles: int = 10):
        """Apply reset pulse."""
        from cocotb.triggers import ClockCycles
        self.dut.Reset.value = 1
        await ClockCycles(self.dut.Clk, cycles)
        self.dut.Reset.value = 0
        await ClockCycles(self.dut.Clk, 5)

    async def init_inputs(self):
        """Initialize all inputs to zero."""
        for name in ["InputA", "InputB", "InputC", "InputD"]:
            if hasattr(self.dut, name):
                getattr(self.dut, name).value = 0


# =============================================================================
# Moku Hardware Implementation (async wrapper around sync API)
# =============================================================================

class MokuAsyncController(AsyncFSMController):
    """Async wrapper around synchronous Moku CloudCompile API.

    Converts blocking Moku API calls to async operations.
    Uses asyncio.sleep() for time-based waits.
    """

    def __init__(self, mcc, propagation_delay_ms: float = 10.0):
        """Initialize with Moku CloudCompile instance.

        Args:
            mcc: CloudCompile instrument instance
            propagation_delay_ms: Delay after each write for network propagation
        """
        self.mcc = mcc
        self.propagation_delay_ms = propagation_delay_ms
        self._shadow_regs = {}  # Track what we've written (API may not support readback)

    async def set_control_register(self, reg_num: int, value: int):
        """Set control register via Moku API.

        Includes a small async delay to model network propagation.
        """
        # The sync API call (runs in event loop - acceptable for short I/O)
        self.mcc.set_control(reg_num, value)
        self._shadow_regs[reg_num] = value

        # Yield to event loop and allow propagation time
        await asyncio.sleep(self.propagation_delay_ms / 1000.0)

    async def get_control_register(self, reg_num: int) -> int:
        """Get control register value from shadow registers.

        Note: Moku CloudCompile may not support register readback.
        This returns the last written value from our shadow registers.
        """
        return self._shadow_regs.get(reg_num, 0)

    async def wait_cycles(self, cycles: int):
        """Wait for equivalent time of N clock cycles."""
        time_sec = cycles / CLK_FREQ_HZ
        await asyncio.sleep(max(time_sec, 0.001))  # Minimum 1ms


class MokuAsyncStateReader(AsyncFSMStateReader):
    """Async state reader using oscilloscope polling."""

    def __init__(self, osc, poll_count: int = 5, poll_interval_ms: float = 20):
        """Initialize with oscilloscope instance.

        Args:
            osc: Moku Oscilloscope instrument
            poll_count: Number of samples to average
            poll_interval_ms: Interval between samples
        """
        self.osc = osc
        self.poll_count = poll_count
        self.poll_interval_ms = poll_interval_ms

    async def read_state_digital(self) -> int:
        """Read OutputC as digital value via oscilloscope.

        Converts voltage reading to equivalent digital units.
        """
        voltage = await self._read_voltage_averaged()
        return int((voltage / 5.0) * 32768)

    async def read_state_voltage(self) -> float:
        """Read OutputC voltage directly."""
        return await self._read_voltage_averaged()

    async def _read_voltage_averaged(self) -> float:
        """Read oscilloscope with averaging."""
        voltages = []

        for _ in range(self.poll_count):
            try:
                data = self.osc.get_data()
                if 'ch1' in data and len(data['ch1']) > 0:
                    midpoint = len(data['ch1']) // 2
                    voltages.append(data['ch1'][midpoint])
            except Exception:
                pass  # Skip failed reads
            await asyncio.sleep(self.poll_interval_ms / 1000.0)

        if not voltages:
            raise RuntimeError("Failed to read oscilloscope data")

        return sum(voltages) / len(voltages)


class MokuAsyncHarness(AsyncFSMTestHarness):
    """Async Moku hardware test harness."""

    def __init__(self, mcc, osc, propagation_delay_ms: float = 10.0):
        """Initialize hardware harness.

        Args:
            mcc: CloudCompile instrument instance
            osc: Oscilloscope instrument instance
            propagation_delay_ms: Network propagation delay per write
        """
        self.mcc = mcc
        self.osc = osc
        self._controller = MokuAsyncController(mcc, propagation_delay_ms)
        self._state_reader = MokuAsyncStateReader(osc)

    @property
    def controller(self) -> AsyncFSMController:
        return self._controller

    @property
    def state_reader(self) -> AsyncFSMStateReader:
        return self._state_reader

    async def wait_for_state(self, target_state: str, timeout_us: int = 1000,
                              tolerance: int = 200) -> bool:
        """Wait for FSM state with polling.

        Uses time-based polling appropriate for hardware latency.
        """
        # Convert to voltage tolerance for hardware
        voltage_tolerance = (tolerance / 32768.0) * 5.0
        target_voltage = _state_to_voltage(target_state)

        if target_voltage is None:
            raise ValueError(f"Unknown state: {target_state}")

        timeout_ms = max(timeout_us / 1000.0, 100)  # Minimum 100ms for hardware
        start_time = time.time()
        poll_interval_s = 0.05  # 50ms polling for hardware

        while (time.time() - start_time) * 1000 < timeout_ms:
            voltage = await self._state_reader.read_state_voltage()
            if abs(voltage - target_voltage) < voltage_tolerance:
                return True
            await asyncio.sleep(poll_interval_s)

        return False


# =============================================================================
# Helper functions
# =============================================================================

# HVS digital values for each state
HVS_DIGITAL_INITIALIZING = 0
HVS_DIGITAL_IDLE = 3277
HVS_DIGITAL_ARMED = 6554
HVS_DIGITAL_FIRING = 9831
HVS_DIGITAL_COOLDOWN = 13108

# HVS voltage values for each state
HVS_VOLTAGE_MAP = {
    "INITIALIZING": 0.0,
    "IDLE": 0.5,
    "ARMED": 1.0,
    "FIRING": 1.5,
    "COOLDOWN": 2.0,
}


def _state_to_digital(state: str) -> Optional[int]:
    """Convert state name to digital value."""
    mapping = {
        "INITIALIZING": HVS_DIGITAL_INITIALIZING,
        "IDLE": HVS_DIGITAL_IDLE,
        "ARMED": HVS_DIGITAL_ARMED,
        "FIRING": HVS_DIGITAL_FIRING,
        "COOLDOWN": HVS_DIGITAL_COOLDOWN,
    }
    return mapping.get(state)


def _state_to_voltage(state: str) -> Optional[float]:
    """Convert state name to voltage."""
    return HVS_VOLTAGE_MAP.get(state)


def _decode_state_from_digital(digital: int, tolerance: int = 200) -> str:
    """Decode FSM state from digital value."""
    if digital < -tolerance:
        return "FAULT"

    state_map = [
        (HVS_DIGITAL_INITIALIZING, "INITIALIZING"),
        (HVS_DIGITAL_IDLE, "IDLE"),
        (HVS_DIGITAL_ARMED, "ARMED"),
        (HVS_DIGITAL_FIRING, "FIRING"),
        (HVS_DIGITAL_COOLDOWN, "COOLDOWN"),
    ]

    for expected, name in state_map:
        if abs(digital - expected) <= tolerance:
            return name

    return "UNKNOWN"


def _cr1_build(arm_enable: bool = False, auto_rearm_enable: bool = False,
               fault_clear: bool = False, sw_trigger_enable: bool = False,
               hw_trigger_enable: bool = False, sw_trigger: bool = False) -> int:
    """Build CR1 value from named parameters."""
    value = 0
    if arm_enable:
        value |= (1 << 0)
    if auto_rearm_enable:
        value |= (1 << 1)
    if fault_clear:
        value |= (1 << 2)
    if sw_trigger_enable:
        value |= (1 << 3)
    if hw_trigger_enable:
        value |= (1 << 4)
    if sw_trigger:
        value |= (1 << 5)
    return value

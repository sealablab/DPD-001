"""
CocoTB Async Adapter
====================

Provides CocoTB implementation of the unified async interface.
Supports optional jitter simulation for "train like you fight" testing.
"""

import random
from typing import Tuple

from .base import (
    AsyncFSMController,
    AsyncFSMStateReader,
    AsyncFSMTestHarness,
    state_to_digital,
    CLK_FREQ_HZ,
)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from lib import SIM_HVS_TOLERANCE


class CocoTBAsyncController(AsyncFSMController):
    """CocoTB controller with optional network-like jitter.

    When jitter_enabled=True, register writes are delayed by random
    clock cycles to simulate network propagation delays.
    """

    def __init__(self, dut, jitter_enabled: bool = False,
                 jitter_range: Tuple[int, int] = (10, 200)):
        """Initialize with CocoTB DUT.

        Args:
            dut: CocoTB DUT object
            jitter_enabled: Add random delays to register writes
            jitter_range: (min_cycles, max_cycles) for jitter delays
        """
        self.dut = dut
        self.jitter_enabled = jitter_enabled
        self.jitter_range = jitter_range
        self._clock_cycles = None

    def _get_clock_cycles(self):
        """Lazy import of ClockCycles."""
        if self._clock_cycles is None:
            from cocotb.triggers import ClockCycles
            self._clock_cycles = ClockCycles
        return self._clock_cycles

    async def set_control_register(self, reg_num: int, value: int):
        """Set control register with optional jitter delay."""
        ClockCycles = self._get_clock_cycles()

        if self.jitter_enabled:
            delay = random.randint(*self.jitter_range)
            await ClockCycles(self.dut.Clk, delay)

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
                              tolerance: int = SIM_HVS_TOLERANCE) -> bool:
        """Wait for FSM state with cycle-accurate polling."""
        from cocotb.triggers import ClockCycles

        target_digital = state_to_digital(target_state)
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

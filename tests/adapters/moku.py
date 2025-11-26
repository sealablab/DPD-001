"""
Moku Hardware Async Adapter
===========================

Provides Moku implementation of the unified async interface.
Wraps synchronous Moku API with async operations.
"""

import asyncio
import time
from typing import Tuple

from .base import (
    AsyncFSMController,
    AsyncFSMStateReader,
    AsyncFSMTestHarness,
    state_to_voltage,
    CLK_FREQ_HZ,
)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from lib import HW_HVS_TOLERANCE_V, HVS


class MokuAsyncController(AsyncFSMController):
    """Async wrapper around synchronous Moku CloudCompile API."""

    def __init__(self, mcc, propagation_delay_ms: float = 10.0):
        """Initialize with Moku CloudCompile instance.

        Args:
            mcc: CloudCompile instrument instance
            propagation_delay_ms: Delay after each write for network propagation
        """
        self.mcc = mcc
        self.propagation_delay_ms = propagation_delay_ms
        self._shadow_regs = {}

    async def set_control_register(self, reg_num: int, value: int):
        """Set control register via Moku API."""
        self.mcc.set_control(reg_num, value)
        self._shadow_regs[reg_num] = value
        await asyncio.sleep(self.propagation_delay_ms / 1000.0)

    async def get_control_register(self, reg_num: int) -> int:
        """Get control register value from shadow registers."""
        return self._shadow_regs.get(reg_num, 0)

    async def wait_cycles(self, cycles: int):
        """Wait for equivalent time of N clock cycles."""
        time_sec = cycles / CLK_FREQ_HZ
        await asyncio.sleep(max(time_sec, 0.001))


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
        """Read OutputC as digital value via oscilloscope."""
        voltage = await self._read_voltage_averaged()
        return HVS.volts_to_digital(voltage)

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
                pass
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
                              tolerance: float = HW_HVS_TOLERANCE_V) -> bool:
        """Wait for FSM state with polling."""
        target_voltage = state_to_voltage(target_state)
        if target_voltage is None:
            raise ValueError(f"Unknown state: {target_state}")

        timeout_ms = max(timeout_us / 1000.0, 100)
        start_time = time.time()
        poll_interval_s = 0.05

        while (time.time() - start_time) * 1000 < timeout_ms:
            voltage = await self._state_reader.read_state_voltage()
            if abs(voltage - target_voltage) < tolerance:
                return True
            await asyncio.sleep(poll_interval_s)

        return False

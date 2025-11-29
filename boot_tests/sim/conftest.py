"""
CocoTB Test Fixtures for BOOT Subsystem
========================================

Provides shared test utilities for BOOT and LOADER tests.

Author: Moku Instrument Forge Team
Date: 2025-11-29
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

import sys
from pathlib import Path

# Add paths
BOOT_TESTS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BOOT_TESTS_DIR))

from lib import BOOT_HVS, BOOT_SIM_HVS_TOLERANCE


# Default clock period for Moku:Go (125MHz = 8ns period)
DEFAULT_CLK_PERIOD_NS = 8


async def setup_clock(dut, period_ns=DEFAULT_CLK_PERIOD_NS):
    """Start a clock on the DUT."""
    clock = cocotb.start_soon(Clock(dut.Clk, period_ns, unit="ns").start())
    dut._log.info(f"Clock started ({period_ns}ns period = {1000 / period_ns:.1f}MHz)")
    return clock


async def reset_dut(dut, cycles=10):
    """Apply active-high reset sequence."""
    dut.Reset.value = 1
    await ClockCycles(dut.Clk, cycles)
    dut.Reset.value = 0
    await ClockCycles(dut.Clk, 1)
    dut._log.info(f"Reset complete ({cycles} cycles)")


async def init_inputs(dut):
    """Initialize all inputs to zero."""
    dut.InputA.value = 0
    dut.InputB.value = 0
    dut.InputC.value = 0
    for i in range(16):
        getattr(dut, f"Control{i}").value = 0


def decode_boot_state(digital: int, tolerance: int = BOOT_SIM_HVS_TOLERANCE) -> str:
    """Decode BOOT state from OutputC digital value."""
    if digital < -tolerance:
        return "FAULT"

    for name, expected in BOOT_HVS.STATE_DIGITAL_MAP.items():
        if abs(digital - expected) <= tolerance:
            return name

    return f"UNKNOWN({digital})"

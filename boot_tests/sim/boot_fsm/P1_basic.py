"""
BOOT FSM P1 (BASIC) Tests
=========================

Basic tests for the BOOT dispatcher FSM state transitions.

Tests:
    - test_boot_p0_initial_state: Verify BOOT starts in P0
    - test_boot_p0_to_p1_on_run: RUN gate enables P0 -> P1 transition
    - test_boot_p1_to_load_active: RUNL command transitions to LOAD_ACTIVE
    - test_boot_p1_to_bios_active: RUNB command transitions to BIOS_ACTIVE
    - test_boot_p1_to_prog_active: RUNP command transitions to PROG_ACTIVE
    - test_boot_runr_reset: RUNR command resets to P0

Author: Moku Instrument Forge Team
Date: 2025-11-29
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles

import sys
from pathlib import Path

# Add paths
BOOT_TESTS_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BOOT_TESTS_DIR))

from lib import (
    CMD, BOOTState, BOOT_HVS,
    BOOT_DIGITAL_P0, BOOT_DIGITAL_P1,
    BOOT_DIGITAL_LOAD_ACTIVE, BOOT_DIGITAL_BIOS_ACTIVE, BOOT_DIGITAL_PROG_ACTIVE,
    BOOT_SIM_HVS_TOLERANCE,
)


# Clock period (8ns = 125MHz)
CLK_PERIOD_NS = 8


async def setup_dut(dut):
    """Initialize DUT with clock and reset."""
    # Start clock
    cocotb.start_soon(Clock(dut.Clk, CLK_PERIOD_NS, units="ns").start())

    # Initialize inputs
    dut.Reset.value = 1
    dut.InputA.value = 0
    dut.InputB.value = 0
    dut.InputC.value = 0
    for i in range(16):
        getattr(dut, f"Control{i}").value = 0

    # Hold reset for 10 cycles
    await ClockCycles(dut.Clk, 10)

    # Release reset
    dut.Reset.value = 0
    await ClockCycles(dut.Clk, 2)


def get_output_c(dut) -> int:
    """Get OutputC as signed integer."""
    return dut.OutputC.value.signed_integer


def assert_state(dut, expected_name: str, expected_digital: int, context: str = ""):
    """Assert OutputC matches expected BOOT state."""
    actual = get_output_c(dut)
    diff = abs(actual - expected_digital)

    assert diff <= BOOT_SIM_HVS_TOLERANCE, (
        f"State mismatch{' (' + context + ')' if context else ''}: "
        f"expected {expected_name} ({expected_digital}), "
        f"got {actual} (diff={diff})"
    )


@cocotb.test()
async def test_boot_p0_initial_state(dut):
    """Verify BOOT starts in P0 after reset."""
    await setup_dut(dut)

    # Should be in BOOT_P0 (0.0V = 0 digital units)
    assert_state(dut, "BOOT_P0", BOOT_DIGITAL_P0, "after reset")
    dut._log.info("PASS: BOOT starts in P0 after reset")


@cocotb.test()
async def test_boot_p0_to_p1_on_run(dut):
    """Verify RUN gate enables P0 -> P1 transition."""
    await setup_dut(dut)

    # Start in P0
    assert_state(dut, "BOOT_P0", BOOT_DIGITAL_P0, "initial")

    # Apply RUN gate (CR0 = 0xE0000000)
    dut.Control0.value = CMD.RUN
    await ClockCycles(dut.Clk, 5)

    # Should transition to P1 (0.2V)
    assert_state(dut, "BOOT_P1", BOOT_DIGITAL_P1, "after RUN")
    dut._log.info("PASS: RUN gate transitions P0 -> P1")


@cocotb.test()
async def test_boot_p1_to_load_active(dut):
    """Verify RUNL command transitions to LOAD_ACTIVE."""
    await setup_dut(dut)

    # Enable RUN gate first
    dut.Control0.value = CMD.RUN
    await ClockCycles(dut.Clk, 5)
    assert_state(dut, "BOOT_P1", BOOT_DIGITAL_P1, "in P1")

    # Apply RUNL command (CR0 = 0xE4000000)
    dut.Control0.value = CMD.RUNL
    await ClockCycles(dut.Clk, 5)

    # Should transition to LOAD_ACTIVE (0.6V)
    assert_state(dut, "LOAD_ACTIVE", BOOT_DIGITAL_LOAD_ACTIVE, "after RUNL")
    dut._log.info("PASS: RUNL transitions to LOAD_ACTIVE")


@cocotb.test()
async def test_boot_p1_to_bios_active(dut):
    """Verify RUNB command transitions to BIOS_ACTIVE."""
    await setup_dut(dut)

    # Enable RUN gate first
    dut.Control0.value = CMD.RUN
    await ClockCycles(dut.Clk, 5)
    assert_state(dut, "BOOT_P1", BOOT_DIGITAL_P1, "in P1")

    # Apply RUNB command (CR0 = 0xE8000000)
    dut.Control0.value = CMD.RUNB
    await ClockCycles(dut.Clk, 5)

    # Should transition to BIOS_ACTIVE (0.4V)
    assert_state(dut, "BIOS_ACTIVE", BOOT_DIGITAL_BIOS_ACTIVE, "after RUNB")
    dut._log.info("PASS: RUNB transitions to BIOS_ACTIVE")


@cocotb.test()
async def test_boot_p1_to_prog_active(dut):
    """Verify RUNP command transitions to PROG_ACTIVE."""
    await setup_dut(dut)

    # Enable RUN gate first
    dut.Control0.value = CMD.RUN
    await ClockCycles(dut.Clk, 5)
    assert_state(dut, "BOOT_P1", BOOT_DIGITAL_P1, "in P1")

    # Apply RUNP command (CR0 = 0xF0000000)
    dut.Control0.value = CMD.RUNP
    await ClockCycles(dut.Clk, 5)

    # Should transition to PROG_ACTIVE (0.8V)
    assert_state(dut, "PROG_ACTIVE", BOOT_DIGITAL_PROG_ACTIVE, "after RUNP")
    dut._log.info("PASS: RUNP transitions to PROG_ACTIVE")


@cocotb.test()
async def test_boot_runr_reset(dut):
    """Verify RUNR command resets to P0."""
    await setup_dut(dut)

    # Get to P1 first
    dut.Control0.value = CMD.RUN
    await ClockCycles(dut.Clk, 5)
    assert_state(dut, "BOOT_P1", BOOT_DIGITAL_P1, "in P1")

    # Apply RUNR command (CR0 = 0xE2000000)
    dut.Control0.value = CMD.RUNR
    await ClockCycles(dut.Clk, 5)

    # Should reset to P0 (0.0V)
    assert_state(dut, "BOOT_P0", BOOT_DIGITAL_P0, "after RUNR")
    dut._log.info("PASS: RUNR resets to P0")

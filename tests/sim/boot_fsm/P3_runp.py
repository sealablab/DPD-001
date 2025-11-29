"""
BOOT FSM P3 (COMPREHENSIVE) Tests - RUNP Handoff
=================================================

Comprehensive tests for the BOOT → PROG handoff via RUNP command.
This verifies the final piece of the BOOT subsystem architecture.

Tests:
    - test_boot_runp_handoff: Verify BOOT → PROG handoff via RUNP command
    - test_boot_runp_no_return: Verify RET does not work from PROG state
    - test_boot_runp_hvs_voltage_jump: Verify HVS encoding transition (0.03V → 0.5V)
    - test_boot_full_workflow_to_prog: Complete workflow ending in PROG

Author: Moku Instrument Forge Team
Date: 2025-11-29
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles

import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from py_tools.boot_constants import (
    CMD, BOOTState, BOOT_HVS,
    encode_pre_prog, BOOT_HVS_S_P0, BOOT_HVS_S_P1,
    LOADER_HVS_S_P0, BIOS_HVS_S_RUN
)

from py_tools.dpd_constants import FSMState, HVS

# BOOT HVS digital values (pre-PROG encoding: 197 units/state)
BOOT_DIGITAL_P0 = encode_pre_prog(BOOT_HVS_S_P0, 0)  # S=0: 0
BOOT_DIGITAL_P1 = encode_pre_prog(BOOT_HVS_S_P1, 0)  # S=1: 197

# DPD HVS digital values (PROG encoding: 3277 units/state)
DPD_DIGITAL_IDLE = HVS.VOLTAGE_IDLE  # S=1: 3277 (~0.5V)

# Tolerance for simulation (tighter than HW)
BOOT_SIM_HVS_TOLERANCE = 150  # +/-150 digital units (~23mV)
DPD_SIM_HVS_TOLERANCE = 300   # +/-300 digital units (~45mV)

# Clock period (8ns = 125MHz)
CLK_PERIOD_NS = 8


async def setup_dut(dut):
    """Initialize DUT with clock and reset."""
    # Start clock
    cocotb.start_soon(Clock(dut.Clk, CLK_PERIOD_NS, units="ns").start())

    # Apply reset
    dut.Reset.value = 1
    dut.Control0.value = 0
    dut.Control1.value = 0
    dut.Control2.value = 0
    dut.Control3.value = 0
    dut.Control4.value = 0
    dut.InputA.value = 0
    dut.InputB.value = 0
    await ClockCycles(dut.Clk, 5)

    # Release reset
    dut.Reset.value = 0
    await ClockCycles(dut.Clk, 5)


def get_output_c(dut):
    """Get OutputC value as signed integer."""
    return dut.OutputC.value.signed_integer


def assert_state_approx(dut, expected_name, expected_digital, context="", tolerance=BOOT_SIM_HVS_TOLERANCE):
    """Assert OutputC is within tolerance of expected digital value."""
    actual = get_output_c(dut)
    diff = abs(actual - expected_digital)
    assert diff <= tolerance, (
        f"State mismatch{' (' + context + ')' if context else ''}: "
        f"expected {expected_name} ({expected_digital}), "
        f"got {actual} (diff={diff}, tolerance={tolerance})"
    )


async def wait_for_state(dut, expected_name, expected_digital, max_cycles=50, context="", tolerance=BOOT_SIM_HVS_TOLERANCE):
    """Wait for DUT to reach expected state within max_cycles."""
    for cycle in range(max_cycles):
        actual = get_output_c(dut)
        diff = abs(actual - expected_digital)
        if diff <= tolerance:
            dut._log.info(f"Reached {expected_name} after {cycle+1} cycles")
            return
        await ClockCycles(dut.Clk, 1)

    # Final check with detailed error message
    actual = get_output_c(dut)
    diff = abs(actual - expected_digital)
    assert False, (
        f"Timeout waiting for {expected_name}{' (' + context + ')' if context else ''}: "
        f"expected {expected_digital}, got {actual} (diff={diff}) after {max_cycles} cycles"
    )


@cocotb.test()
async def test_boot_runp_handoff(dut):
    """Verify BOOT → PROG handoff via RUNP command."""
    await setup_dut(dut)

    # Get to BOOT_P1
    dut.Control0.value = CMD.RUN
    await ClockCycles(dut.Clk, 5)
    assert_state_approx(dut, "BOOT_P1", BOOT_DIGITAL_P1, "after RUN")

    # RUNP → PROG_ACTIVE
    dut.Control0.value = CMD.RUNP
    await ClockCycles(dut.Clk, 5)

    # Should now see DPD HVS encoding (~0.5V = IDLE = 3277 digital)
    # Note: DPD uses different encoding than pre-PROG
    await wait_for_state(dut, "DPD_IDLE", DPD_DIGITAL_IDLE,
                         max_cycles=50, context="PROG handoff",
                         tolerance=DPD_SIM_HVS_TOLERANCE)

    dut._log.info("PASS: RUNP successfully handed off to PROG (DPD_IDLE)")


@cocotb.test()
async def test_boot_runp_no_return(dut):
    """Verify RET does not work from PROG state."""
    await setup_dut(dut)

    # Get to PROG_ACTIVE
    dut.Control0.value = CMD.RUN
    await ClockCycles(dut.Clk, 5)
    dut.Control0.value = CMD.RUNP
    await ClockCycles(dut.Clk, 10)

    # Verify we're in DPD context
    await wait_for_state(dut, "DPD_IDLE", DPD_DIGITAL_IDLE,
                         max_cycles=20, context="before RET test",
                         tolerance=DPD_SIM_HVS_TOLERANCE)

    # Try RET - should be ignored (CMD.RET already includes RUN gate)
    dut.Control0.value = CMD.RET
    await ClockCycles(dut.Clk, 10)

    # Should still be in PROG (DPD encoding), not BOOT_P1
    actual = get_output_c(dut)
    assert actual > 1000, (
        f"Expected DPD encoding (>1000), got {actual}. "
        f"RET should be ignored from PROG state!"
    )

    dut._log.info("PASS: RET command ignored from PROG state (one-way semantics)")


@cocotb.test()
async def test_boot_runp_hvs_voltage_jump(dut):
    """Verify HVS encoding transition from BOOT (197 units) to DPD (3277 units)."""
    await setup_dut(dut)

    # Start in BOOT_P1 (197 digital = ~0.03V)
    dut.Control0.value = CMD.RUN
    await ClockCycles(dut.Clk, 5)
    boot_p1_voltage = get_output_c(dut)
    assert_state_approx(dut, "BOOT_P1", BOOT_DIGITAL_P1, "pre-transition")

    # RUNP transition
    dut.Control0.value = CMD.RUNP
    await ClockCycles(dut.Clk, 5)

    # Should see voltage jump to DPD_IDLE (3277 digital = ~0.5V)
    dpd_idle_voltage = get_output_c(dut)
    voltage_jump = dpd_idle_voltage - boot_p1_voltage

    # Expect significant jump (3277 - 197 = 3080 digital units ≈ 470mV)
    expected_jump = DPD_DIGITAL_IDLE - BOOT_DIGITAL_P1  # 3277 - 197 = 3080
    jump_tolerance = 400  # Allow ±400 digital units for transition timing

    assert abs(voltage_jump - expected_jump) <= jump_tolerance, (
        f"HVS voltage jump incorrect: expected ~{expected_jump}, got {voltage_jump}. "
        f"BOOT_P1={boot_p1_voltage}, DPD_IDLE={dpd_idle_voltage}"
    )

    # Final verification: we're in DPD IDLE state
    assert_state_approx(dut, "DPD_IDLE", DPD_DIGITAL_IDLE, "after transition",
                        tolerance=DPD_SIM_HVS_TOLERANCE)

    dut._log.info(f"PASS: HVS voltage jump verified (BOOT→DPD: {voltage_jump} units)")


@cocotb.test()
async def test_boot_full_workflow_to_prog(dut):
    """Complete workflow: BOOT_P0 → BOOT_P1 → RUNL → LOADER → RET → RUNB → BIOS → RET → RUNP → DPD."""
    await setup_dut(dut)

    # Step 1: BOOT_P0 → BOOT_P1
    dut.Control0.value = CMD.RUN
    await ClockCycles(dut.Clk, 5)
    assert_state_approx(dut, "BOOT_P1", BOOT_DIGITAL_P1, "RUN gate")

    # Step 2: RUNL → LOADER (quick validation mode)
    dut.Control0.value = CMD.RUNL
    await ClockCycles(dut.Clk, 20)  # Allow LOADER to complete in validation mode

    # Step 3: RET from LOADER → BOOT_P1 (CMD.RET includes RUN gate)
    dut.Control0.value = CMD.RET
    await ClockCycles(dut.Clk, 5)
    assert_state_approx(dut, "BOOT_P1", BOOT_DIGITAL_P1, "RET from LOADER")

    # Step 4: RUNB → BIOS
    dut.Control0.value = CMD.RUNB
    await ClockCycles(dut.Clk, 20)  # Allow BIOS to complete

    # Step 5: RET from BIOS → BOOT_P1 (CMD.RET includes RUN gate)
    dut.Control0.value = CMD.RET
    await ClockCycles(dut.Clk, 5)
    assert_state_approx(dut, "BOOT_P1", BOOT_DIGITAL_P1, "RET from BIOS")

    # Step 6: RUNP → PROG (one-way)
    dut.Control0.value = CMD.RUNP
    await ClockCycles(dut.Clk, 10)

    # Final verification: DPD FSM should be in IDLE
    await wait_for_state(dut, "DPD_IDLE", DPD_DIGITAL_IDLE,
                         max_cycles=50, context="full workflow completion",
                         tolerance=DPD_SIM_HVS_TOLERANCE)

    dut._log.info("PASS: Full BOOT workflow completed, successfully handed off to PROG")
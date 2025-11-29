"""
BOOT FSM P2 (WORKFLOW) Tests
============================

Intermediate tests for the BOOT subsystem focusing on multi-module workflows
and validation mode transitions.

Tests:
    - test_boot_loader_auto_advance: LOADER auto-advances P0→P1→P2→P3 in validation mode
    - test_boot_bios_auto_complete: BIOS auto-completes IDLE→RUN→DONE
    - test_boot_loader_bios_workflow: Full BOOT→LOADER→BIOS→BOOT workflow
    - test_boot_ret_requires_complete: RET only works after module completes

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
    CMD, encode_pre_prog,
    BOOT_HVS_S_P0, BOOT_HVS_S_P1,
    LOADER_HVS_S_P0, LOADER_HVS_S_P1, LOADER_HVS_S_P2, LOADER_HVS_S_P3,
    BIOS_HVS_S_IDLE, BIOS_HVS_S_RUN, BIOS_HVS_S_DONE
)

# HVS digital values for expected states
BOOT_DIGITAL_P0 = encode_pre_prog(BOOT_HVS_S_P0, 0)
BOOT_DIGITAL_P1 = encode_pre_prog(BOOT_HVS_S_P1, 0)
LOADER_DIGITAL_P0 = encode_pre_prog(LOADER_HVS_S_P0, 0)
LOADER_DIGITAL_P1 = encode_pre_prog(LOADER_HVS_S_P1, 0)
LOADER_DIGITAL_P2 = encode_pre_prog(LOADER_HVS_S_P2, 0)
LOADER_DIGITAL_P3 = encode_pre_prog(LOADER_HVS_S_P3, 0)
BIOS_DIGITAL_IDLE = encode_pre_prog(BIOS_HVS_S_IDLE, 0)
BIOS_DIGITAL_RUN = encode_pre_prog(BIOS_HVS_S_RUN, 0)
BIOS_DIGITAL_DONE = encode_pre_prog(BIOS_HVS_S_DONE, 0)

# Tolerance for simulation
SIM_HVS_TOLERANCE = 150

# Clock period (8ns = 125MHz)
CLK_PERIOD_NS = 8


async def setup_dut(dut):
    """Initialize DUT with clock and reset."""
    cocotb.start_soon(Clock(dut.Clk, CLK_PERIOD_NS, unit="ns").start())

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
    return dut.OutputC.value.to_signed()


def assert_state_approx(dut, expected_name: str, expected_digital: int, context: str = ""):
    """Assert OutputC is within tolerance of expected HVS value."""
    actual = get_output_c(dut)
    diff = abs(actual - expected_digital)

    assert diff <= SIM_HVS_TOLERANCE, (
        f"State mismatch{' (' + context + ')' if context else ''}: "
        f"expected {expected_name} ({expected_digital}), "
        f"got {actual} (diff={diff})"
    )


async def wait_for_state(dut, expected_name: str, expected_digital: int,
                         max_cycles: int = 100, context: str = ""):
    """Wait for OutputC to reach expected state, polling each cycle."""
    for _ in range(max_cycles):
        actual = get_output_c(dut)
        if abs(actual - expected_digital) <= SIM_HVS_TOLERANCE:
            return True
        await ClockCycles(dut.Clk, 1)

    # Timeout - assert will fail
    assert_state_approx(dut, expected_name, expected_digital,
                        f"{context} (timeout after {max_cycles} cycles)")
    return False


@cocotb.test()
async def test_boot_loader_auto_advance(dut):
    """Verify LOADER auto-advances P0→P1→P2→P3 in validation mode.

    With validation mode enabled and short delay (10 cycles), LOADER should
    automatically advance through all states without any strobes.
    """
    await setup_dut(dut)

    # Get to BOOT_P1
    dut.Control0.value = CMD.RUN
    await ClockCycles(dut.Clk, 5)
    assert_state_approx(dut, "BOOT_P1", BOOT_DIGITAL_P1, "in P1")

    # Dispatch to LOADER (RUNL)
    dut.Control0.value = CMD.RUNL
    await ClockCycles(dut.Clk, 3)

    # Wait for LOADER to auto-advance through states
    # With 10-cycle delay per state, should see P0→P1→P2→P3
    dut._log.info("Waiting for LOADER P0...")
    await wait_for_state(dut, "LOADER_P0", LOADER_DIGITAL_P0, max_cycles=20, context="LOADER P0")

    dut._log.info("Waiting for LOADER P1...")
    await wait_for_state(dut, "LOADER_P1", LOADER_DIGITAL_P1, max_cycles=20, context="LOADER P1")

    dut._log.info("Waiting for LOADER P2...")
    await wait_for_state(dut, "LOADER_P2", LOADER_DIGITAL_P2, max_cycles=20, context="LOADER P2")

    dut._log.info("Waiting for LOADER P3...")
    await wait_for_state(dut, "LOADER_P3", LOADER_DIGITAL_P3, max_cycles=20, context="LOADER P3")

    dut._log.info("PASS: LOADER auto-advances through P0→P1→P2→P3")


@cocotb.test()
async def test_boot_bios_auto_complete(dut):
    """Verify BIOS auto-completes IDLE→RUN→DONE cycle."""
    await setup_dut(dut)

    # Get to BOOT_P1
    dut.Control0.value = CMD.RUN
    await ClockCycles(dut.Clk, 5)

    # Dispatch to BIOS (RUNB)
    dut.Control0.value = CMD.RUNB
    await ClockCycles(dut.Clk, 3)

    # BIOS should immediately transition to RUN (IDLE is transient)
    dut._log.info("Waiting for BIOS RUN...")
    await wait_for_state(dut, "BIOS_RUN", BIOS_DIGITAL_RUN, max_cycles=10, context="BIOS RUN")

    # Wait for BIOS to complete (after delay counter expires)
    dut._log.info("Waiting for BIOS DONE...")
    await wait_for_state(dut, "BIOS_DONE", BIOS_DIGITAL_DONE, max_cycles=30, context="BIOS DONE")

    dut._log.info("PASS: BIOS auto-completes IDLE→RUN→DONE")


@cocotb.test()
async def test_boot_loader_bios_workflow(dut):
    """Verify full BOOT→LOADER→BIOS→BOOT workflow.

    This is the "expert workflow" from the spec:
    1. BOOT_P0 → BOOT_P1 (RUN)
    2. BOOT_P1 → LOAD_ACTIVE (RUNL)
    3. LOADER completes → RET → BOOT_P1
    4. BOOT_P1 → BIOS_ACTIVE (RUNB)
    5. BIOS completes → RET → BOOT_P1
    """
    await setup_dut(dut)

    # 1. Start in BOOT_P0
    assert_state_approx(dut, "BOOT_P0", BOOT_DIGITAL_P0, "initial")

    # 2. RUN gate → BOOT_P1
    dut.Control0.value = CMD.RUN
    await ClockCycles(dut.Clk, 5)
    assert_state_approx(dut, "BOOT_P1", BOOT_DIGITAL_P1, "after RUN")
    dut._log.info("Step 1: BOOT_P0 → BOOT_P1")

    # 3. RUNL → LOADER
    dut.Control0.value = CMD.RUNL
    await ClockCycles(dut.Clk, 3)

    # Wait for LOADER to reach P3 (complete)
    await wait_for_state(dut, "LOADER_P3", LOADER_DIGITAL_P3, max_cycles=60, context="LOADER complete")
    dut._log.info("Step 2: LOADER completed (P3)")

    # 4. RET from LOADER → BOOT_P1
    dut.Control0.value = CMD.RET
    await ClockCycles(dut.Clk, 5)
    assert_state_approx(dut, "BOOT_P1", BOOT_DIGITAL_P1, "after LOADER RET")
    dut._log.info("Step 3: RET → BOOT_P1")

    # 5. RUNB → BIOS
    dut.Control0.value = CMD.RUNB
    await ClockCycles(dut.Clk, 3)

    # Wait for BIOS to reach DONE
    await wait_for_state(dut, "BIOS_DONE", BIOS_DIGITAL_DONE, max_cycles=30, context="BIOS complete")
    dut._log.info("Step 4: BIOS completed (DONE)")

    # 6. RET from BIOS → BOOT_P1
    dut.Control0.value = CMD.RET
    await ClockCycles(dut.Clk, 5)
    assert_state_approx(dut, "BOOT_P1", BOOT_DIGITAL_P1, "after BIOS RET")
    dut._log.info("Step 5: RET → BOOT_P1")

    dut._log.info("PASS: Full BOOT→LOADER→BIOS→BOOT workflow completed")


@cocotb.test()
async def test_boot_ret_requires_complete(dut):
    """Verify RET only works after module completes.

    If RET is sent before LOADER/BIOS completes, BOOT should remain
    in the ACTIVE state until completion. Then RET takes effect immediately.
    """
    await setup_dut(dut)

    # Get to BOOT_P1
    dut.Control0.value = CMD.RUN
    await ClockCycles(dut.Clk, 5)

    # Dispatch to BIOS
    dut.Control0.value = CMD.RUNB
    await ClockCycles(dut.Clk, 3)

    # Verify we're in BIOS_RUN
    await wait_for_state(dut, "BIOS_RUN", BIOS_DIGITAL_RUN, max_cycles=10, context="BIOS RUN")

    # Try RET immediately (before BIOS completes)
    dut.Control0.value = CMD.RET
    await ClockCycles(dut.Clk, 5)

    # Should still be in BIOS (RUN state - not yet complete)
    actual = get_output_c(dut)
    still_in_bios_run = abs(actual - BIOS_DIGITAL_RUN) <= SIM_HVS_TOLERANCE
    assert still_in_bios_run, (
        f"Expected BIOS_RUN ({BIOS_DIGITAL_RUN}), got {actual} - "
        f"RET should not work before completion"
    )
    dut._log.info("RET before completion: still in BIOS_RUN (correct)")

    # Wait for BIOS to complete and RET to take effect
    # Since RET is already set, as soon as BIOS_DONE is reached, it transitions to BOOT_P1
    # So we should see BOOT_P1, not BIOS_DONE
    await wait_for_state(dut, "BOOT_P1", BOOT_DIGITAL_P1, max_cycles=30, context="BOOT_P1 after BIOS complete")

    dut._log.info("PASS: RET only works after module completes (immediate transition)")

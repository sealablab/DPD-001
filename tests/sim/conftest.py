"""
CocoTB Test Fixtures and Utilities for Demo Probe Driver (DPD)

Adapted from libs/forge-vhdl/python/forge_cocotb/forge_cocotb/conftest.py

This file provides shared test utilities that eliminate code duplication
across all testbenches. pytest automatically loads this file.

Usage in tests:
    from conftest import setup_clock, reset_active_high, mcc_set_regs

    @cocotb.test()
    async def test_something(dut):
        await setup_clock(dut, clk_signal="Clk")
        await reset_active_high(dut, rst_signal="Reset")
        # ... your test logic

GHDL Output Filtering:
    The GHDL output filter is automatically enabled when running tests via run.py.
    Filter level is auto-selected based on COCOTB_VERBOSITY or can be overridden
    with the GHDL_FILTER environment variable.

Author: Moku Instrument Forge Team
Date: 2025-11-18
"""

import cocotb
import os
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, ClockCycles, with_timeout


# Default clock period for Moku:Go (125MHz = 8ns period)
DEFAULT_CLK_PERIOD_NS = 8

# Default wall-clock timeout for all tests (prevents infinite loops)
DEFAULT_TEST_TIMEOUT_SEC = 10


# =============================================================================
# Timeout Management
# =============================================================================

async def run_with_timeout(test_coro, timeout_sec=DEFAULT_TEST_TIMEOUT_SEC, test_name="test"):
    """
    Run a test coroutine with wall-clock timeout to prevent infinite loops

    This wraps test logic with a timeout that triggers after a fixed amount of
    real (wall-clock) time, not simulation cycles. Use this to prevent tests
    from hanging indefinitely if the simulation enters an infinite loop.

    Args:
        test_coro: Coroutine to run (the test logic)
        timeout_sec: Wall-clock timeout in seconds (default: 10)
        test_name: Name of test for error messages (optional)

    Raises:
        cocotb.result.SimTimeoutError: If timeout expires before test completes

    Example:
        @cocotb.test()
        async def test_something(dut):
            async def test_logic():
                await setup_clock(dut, clk_signal="Clk")
                await reset_active_high(dut, rst_signal="Reset")
                # ... your test code ...

            await run_with_timeout(test_logic(), timeout_sec=10)
    """
    try:
        result = await with_timeout(test_coro, timeout_time=timeout_sec, timeout_unit="sec")
        return result
    except Exception as e:
        # Check if it's a timeout error
        if "Timeout" in str(e) or "timeout" in str(type(e).__name__).lower():
            raise AssertionError(
                f"Test '{test_name}' TIMEOUT after {timeout_sec}s wall-clock time. "
                f"Possible infinite loop or simulation stuck. Original error: {e}"
            )
        else:
            # Re-raise other exceptions unchanged
            raise


# =============================================================================
# FORGE Control Scheme (CR0[31:29])
# =============================================================================
#
# ALL FORGE modules require THREE control bits in Control0[31:29]:
#   Control0[31] = forge_ready (active-high) - Set after deployment
#   Control0[30] = user_enable (active-high) - User control
#   Control0[29] = clk_enable (active-high) - Clock gating
#
# Correct pattern: 0xE0000000 (bits 31+30+29 all set)
# =============================================================================

FORGE_READY_BIT = 31  # Set by MCC after deployment
USER_ENABLE_BIT = 30  # User-controlled enable/disable
CLK_ENABLE_BIT = 29  # Clock gating enable

FORGE_CR0_BASE = (1 << FORGE_READY_BIT) | (1 << USER_ENABLE_BIT) | (1 << CLK_ENABLE_BIT)  # 0xE0000000


def validate_control0(cr0_value: int, context: str = ""):
    """Validate Control0 has all 3 required FORGE control bits.

    Warns if Clock Enable (bit 29) is missing, which causes modules
    to freeze even when "enabled".

    Args:
        cr0_value: Control0 register value
        context: Description of where this value is being used (for warnings)
    """
    forge_ready = (cr0_value >> FORGE_READY_BIT) & 1
    user_enable = (cr0_value >> USER_ENABLE_BIT) & 1
    clk_enable = (cr0_value >> CLK_ENABLE_BIT) & 1

    if user_enable and not clk_enable:
        import warnings
        warnings.warn(
            f"\n{'=' * 70}\n"
            f"⚠️  WARNING: Control0={cr0_value:#010x} missing Clock Enable (bit 29)!\n"
            f"{'=' * 70}\n"
            f"  Bit 31 (forge_ready): {forge_ready}\n"
            f"  Bit 30 (user_enable): {user_enable}\n"
            f"  Bit 29 (clk_enable):  {clk_enable}  ← ⚠️ MUST BE 1 for clocked modules!\n"
            f"{'=' * 70}\n"
            f"Module will FREEZE without Clock Enable!\n"
            f"Use: {(cr0_value | (1 << CLK_ENABLE_BIT)):#010x} instead\n"
            f"Context: {context}\n"
            f"{'=' * 70}",
            stacklevel=3
        )


def forge_cr0(extra_bits: int = 0) -> int:
    """Construct Control0 with mandatory FORGE 3-bit control scheme.

    Always includes bits 31+30+29 (forge_ready + user_enable + clk_enable).

    Args:
        extra_bits: Additional bits to OR in (e.g., application flags)

    Returns:
        Control0 value with all 3 FORGE control bits set

    Example:
        cr0 = forge_cr0()  # Returns 0xE0000000 (base)
        cr0 = forge_cr0(extra_bits=0x00000001)  # Returns 0xE0000001
    """
    return FORGE_CR0_BASE | extra_bits


# =============================================================================
# Clock Management
# =============================================================================

async def setup_clock(dut, period_ns=DEFAULT_CLK_PERIOD_NS, clk_signal="Clk"):
    """
    Start a clock on the DUT

    Args:
        dut: Device Under Test
        period_ns: Clock period in nanoseconds (default: 8ns = 125MHz for Moku:Go)
        clk_signal: Name of clock signal (default: "Clk" for MCC style)

    Returns:
        Clock object (can be ignored, runs in background)

    Example:
        await setup_clock(dut)  # 125MHz default
        await setup_clock(dut, period_ns=10)  # 100MHz
    """
    clk = getattr(dut, clk_signal)
    clock = cocotb.start_soon(Clock(clk, period_ns, unit="ns").start())
    dut._log.info(f"✓ Clock started on '{clk_signal}' ({period_ns}ns period = {1000 / period_ns:.1f}MHz)")
    return clock


# =============================================================================
# Reset Sequences
# =============================================================================

async def reset_active_high(dut, cycles=10, rst_signal="Reset"):
    """
    Apply active-high reset sequence (DPD uses active-high reset)

    Args:
        dut: Device Under Test
        cycles: Number of clock cycles to hold reset (default: 10)
        rst_signal: Name of reset signal (default: "Reset")

    Example:
        await reset_active_high(dut)
        await reset_active_high(dut, cycles=20)
    """
    # Try specified signal name first, fall back to common alternatives
    if hasattr(dut, rst_signal):
        rst = getattr(dut, rst_signal)
    elif hasattr(dut, "Reset"):
        rst = dut.Reset
        rst_signal = "Reset"
    else:
        rst = getattr(dut, rst_signal)  # Will raise AttributeError if not found

    clk = dut.Clk if hasattr(dut, "Clk") else dut.clk

    # Apply reset
    rst.value = 1
    await ClockCycles(clk, cycles)

    # Release reset
    rst.value = 0
    await ClockCycles(clk, 1)

    dut._log.info(f"✓ Reset complete (active-high, {cycles} cycles)")


# =============================================================================
# Signal Monitoring and Counting
# =============================================================================

async def wait_for_value(signal, expected_value, clk, timeout_cycles=1000):
    """
    Wait for a signal to reach an expected value (with timeout)

    Args:
        signal: Signal to monitor
        expected_value: Value to wait for
        clk: Clock signal
        timeout_cycles: Maximum cycles to wait (default: 1000)

    Returns:
        bool: True if value reached, False if timeout

    Example:
        success = await wait_for_value(dut.done, 1, dut.Clk)
        assert success, "Module never signaled done"
    """
    for cycle in range(timeout_cycles):
        await RisingEdge(clk)
        if signal.value == expected_value:
            return True
    return False


# =============================================================================
# MCC (Moku CustomWrapper) Helpers
# =============================================================================

async def init_mcc_inputs(dut):
    """
    Initialize all MCC input channels to zero

    Args:
        dut: Device Under Test (CustomWrapper)

    Example:
        await init_mcc_inputs(dut)
    """
    dut.InputA.value = 0
    dut.InputB.value = 0
    if hasattr(dut, "InputC"):
        dut.InputC.value = 0
    if hasattr(dut, "InputD"):
        dut.InputD.value = 0


async def mcc_set_regs(dut, control_regs, set_forge_ready=True):
    """
    Set MCC control registers for DPD

    This sets registers WITHOUT network delay simulation (simplified for tests).
    Always sets FORGE control bits unless explicitly disabled.

    Args:
        dut: Device Under Test (CustomWrapper entity)
        control_regs: Dict of {reg_num: value} to set
        set_forge_ready: If True, sets CR0[31:29]=111 after config (default: True)

    Example - Initial configuration:
        await mcc_set_regs(dut, {
            1: 0x00000001,  # arm_enable
            2: (950 << 16) | 2000,  # threshold + trig voltage
            4: 12500,  # trig_out_duration
        })

    Example - Runtime update:
        await mcc_set_regs(dut, {
            5: 25000  # Change intensity_duration only
        }, set_forge_ready=False)
    """
    # Write each register
    for reg_num, value in sorted(control_regs.items()):
        # Mask out FORGE bits from CR0 if set_forge_ready=True (we'll set them last)
        if reg_num == 0 and set_forge_ready:
            value = value & 0x1FFFFFFF  # Clear bits 31:29

        getattr(dut, f"Control{reg_num}").value = value
        dut._log.info(f"  Control{reg_num} ← 0x{value:08X}")

    await ClockCycles(dut.Clk, 2)

    # Set FORGE control bits (CR0[31:29]=111) to enable module
    if set_forge_ready:
        cr0_current = int(dut.Control0.value) if 0 in control_regs else 0
        cr0_ready = cr0_current | FORGE_CR0_BASE  # Set bits 31, 30, 29

        # Validate Control0 has all 3 required bits (warns if missing)
        validate_control0(cr0_ready, context="mcc_set_regs()")

        dut.Control0.value = cr0_ready
        dut._log.info(f"✓ FORGE control asserted (CR0 = 0x{cr0_ready:08X})")
        await ClockCycles(dut.Clk, 2)


async def wait_for_mcc_ready(dut, settle_cycles=10):
    """
    Wait for module to stabilize after FORGE control assertion

    Args:
        dut: Device Under Test
        settle_cycles: Number of clock cycles to wait (default: 10)

    Example:
        await mcc_set_regs(dut, {...})
        await wait_for_mcc_ready(dut)  # Let FSM settle
    """
    clk = dut.Clk if hasattr(dut, "Clk") else dut.clk
    await ClockCycles(clk, settle_cycles)
    dut._log.info(f"✓ Module settled ({settle_cycles} cycles after FORGE control)")

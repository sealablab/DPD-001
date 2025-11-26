"""
Demo Probe Driver (DPD) Test Helper Functions

Utilities specific to DPD FSM testing via OutputC (HVS encoding observation).

Author: Moku Instrument Forge Team
Date: 2025-11-18
"""

import cocotb
from cocotb.triggers import ClockCycles
from dpd_wrapper_tests.dpd_wrapper_constants import (
    HVS_DIGITAL_INITIALIZING,
    HVS_DIGITAL_IDLE,
    HVS_DIGITAL_ARMED,
    HVS_DIGITAL_FIRING,
    HVS_DIGITAL_COOLDOWN,
    HVS_DIGITAL_TOLERANCE,
    CLK_PERIOD_NS,
)


def read_output_c(dut) -> int:
    """Read OutputC as signed integer (HVS-encoded FSM state).

    Args:
        dut: Device Under Test

    Returns:
        Signed integer value from OutputC
    """
    return int(dut.OutputC.value.to_signed())


def assert_state(dut, expected_digital: int, tolerance: int = HVS_DIGITAL_TOLERANCE, context: str = ""):
    """Assert OutputC matches expected HVS digital value.

    Args:
        dut: Device Under Test
        expected_digital: Expected digital value (0, 3277, 6554, 9831 for states 0-3)
        tolerance: Allowed deviation (default: from constants)
        context: Optional context for error message

    Raises:
        AssertionError: If OutputC doesn't match expected value within tolerance
    """
    actual = read_output_c(dut)
    in_range = abs(actual - expected_digital) <= tolerance

    assert in_range, (
        f"OutputC state mismatch{' (' + context + ')' if context else ''}: "
        f"expected {expected_digital}±{tolerance}, got {actual}"
    )


async def wait_for_state(dut, target_digital: int, timeout_us: int = 100,
                         tolerance: int = HVS_DIGITAL_TOLERANCE):
    """Poll OutputC until target state reached or timeout.

    This function is RELAXED about timing - it just waits for the state
    transition to happen, without strict cycle counting.

    Args:
        dut: Device Under Test
        target_digital: Target HVS digital value (0, 3277, 6554, 9831 for states 0-3)
        timeout_us: Timeout in microseconds (default: 100μs)
        tolerance: Allowed deviation from target (default: from constants)

    Raises:
        AssertionError: If timeout expires before reaching target state

    Example:
        await wait_for_state(dut, HVS_DIGITAL_ARMED, timeout_us=50)
    """
    timeout_cycles = int((timeout_us * 1000) / CLK_PERIOD_NS)

    for cycle in range(timeout_cycles):
        actual = read_output_c(dut)
        if abs(actual - target_digital) <= tolerance:
            dut._log.info(f"  ✓ Reached state {target_digital} (OutputC={actual}) after {cycle} cycles")
            return  # Success

        await ClockCycles(dut.Clk, 1)

    # Timeout - raise with diagnostic
    actual = read_output_c(dut)
    raise AssertionError(
        f"Timeout waiting for OutputC={target_digital}±{tolerance}, "
        f"stuck at {actual} after {timeout_us}μs ({timeout_cycles} cycles)"
    )


async def wait_cycles_relaxed(dut, approximate_cycles: int, margin_percent: float = 20.0):
    """Wait approximately N cycles, with tolerance for simulation delays.

    This is used when we DON'T care about exact timing, just that "enough time
    has passed" for an operation to complete.

    Args:
        dut: Device Under Test
        approximate_cycles: Approximate number of cycles to wait
        margin_percent: Additional margin as percentage (default: 20%)

    Example:
        # Wait ~100μs (12500 cycles), but allow 20% margin
        await wait_cycles_relaxed(dut, 12500)
    """
    margin_cycles = int(approximate_cycles * (margin_percent / 100.0))
    total_cycles = approximate_cycles + margin_cycles

    await ClockCycles(dut.Clk, total_cycles)
    dut._log.info(f"  Waited ~{approximate_cycles} cycles (+ {margin_percent}% margin)")


async def arm_dpd(dut, trig_duration: int, intensity_duration: int, cooldown: int):
    """Arm the DPD FSM with timing parameters.

    Sets Control Registers and waits for ARMED state.

    Args:
        dut: Device Under Test
        trig_duration: Trigger pulse duration (cycles)
        intensity_duration: Intensity pulse duration (cycles)
        cooldown: Cooldown interval (cycles)

    Raises:
        AssertionError: If FSM doesn't reach ARMED state
    """
    from conftest import mcc_set_regs
    from dpd_wrapper_tests.dpd_wrapper_constants import CR1  # Import CR1 bit positions

    await mcc_set_regs(dut, {
        1: (1 << CR1.ARM_ENABLE),  # CR1: arm_enable=1, auto_rearm=0 (single shot)
        4: trig_duration,  # CR4 = trig_out_duration
        5: intensity_duration,  # CR5 = intensity_duration
        7: cooldown,  # CR7 = cooldown_interval
    })

    # Wait for ARMED state (should be quick)
    await wait_for_state(dut, HVS_DIGITAL_ARMED, timeout_us=50)


async def software_trigger(dut):
    """Trigger FSM via sw_trigger (CR1[5]).

    NOTE: Requires sw_trigger_enable (CR1[3]) to be set for trigger to propagate.
          This is a safety feature to prevent spurious triggers from metavalues.

    Args:
        dut: Device Under Test

    Raises:
        AssertionError: If FSM doesn't reach FIRING state
    """
    from conftest import mcc_set_regs
    from dpd_wrapper_tests.dpd_wrapper_constants import CR1  # Import CR1 bit positions

    # Set arm_enable=1, sw_trigger_enable=1, sw_trigger=1
    cr1_value = (
        (1 << CR1.ARM_ENABLE) |
        (1 << CR1.SW_TRIGGER_ENABLE) |  # REQUIRED: Enable software trigger path
        (1 << CR1.SW_TRIGGER)
    )
    await mcc_set_regs(dut, {
        1: cr1_value
    }, set_forge_ready=False)

    # Wait for FIRING state (should be quick)
    await wait_for_state(dut, HVS_DIGITAL_FIRING, timeout_us=50)


async def hardware_trigger(dut, voltage_mv: int, threshold_mv: int = 950):
    """Trigger FSM via InputA voltage (hardware trigger path).

    NOTE: Requires hw_trigger_enable (CR1[4]) to be set for trigger to propagate.
          This is a safety feature to prevent spurious triggers from metavalues.

    Args:
        dut: Device Under Test
        voltage_mv: Voltage to apply to InputA (in mV)
        threshold_mv: Threshold voltage (in mV, default: 950)

    Raises:
        AssertionError: If FSM doesn't reach FIRING state
    """
    from conftest import mcc_set_regs
    from dpd_wrapper_tests.dpd_wrapper_constants import mv_to_digital, CR1

    # Enable hardware trigger and set threshold in CR2[31:16]
    cr1_value = (1 << CR1.HW_TRIGGER_ENABLE)  # REQUIRED: Enable hardware trigger path
    await mcc_set_regs(dut, {
        1: cr1_value,  # CR1: hw_trigger_enable=1
        2: (threshold_mv & 0xFFFF) << 16  # CR2[31:16] = threshold
    }, set_forge_ready=False)

    # Apply voltage to InputA
    digital_value = mv_to_digital(voltage_mv)
    dut.InputA.value = digital_value
    dut._log.info(f"  Applied {voltage_mv}mV ({digital_value} digital) to InputA")

    await ClockCycles(dut.Clk, 2)  # Let hardware trigger settle

    # Wait for FIRING state
    await wait_for_state(dut, HVS_DIGITAL_FIRING, timeout_us=100)


async def wait_for_fsm_complete_cycle(dut, firing_cycles: int, cooldown_cycles: int):
    """Wait for FSM to complete FIRING → COOLDOWN → IDLE cycle.

    This function is RELAXED - it doesn't enforce strict timing, just waits
    long enough for the cycle to complete.

    Args:
        dut: Device Under Test
        firing_cycles: Approximate FIRING state duration (trig + intensity)
        cooldown_cycles: Approximate COOLDOWN state duration

    Raises:
        AssertionError: If FSM doesn't reach expected states
    """
    # Wait for FIRING → COOLDOWN transition
    # (Add generous margin for GHDL simulation timing variations)
    await wait_cycles_relaxed(dut, firing_cycles, margin_percent=200)
    await wait_for_state(dut, HVS_DIGITAL_COOLDOWN, timeout_us=1000)

    # Wait for COOLDOWN → IDLE transition
    await wait_cycles_relaxed(dut, cooldown_cycles, margin_percent=200)
    await wait_for_state(dut, HVS_DIGITAL_IDLE, timeout_us=1000)

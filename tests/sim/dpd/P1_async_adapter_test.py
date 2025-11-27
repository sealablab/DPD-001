"""
P1 Async Adapter Test - Demo of Unified Async Interface
========================================================

This test demonstrates the new unified async adapter that works
identically for CocoTB simulation and Moku hardware.

Key features tested:
- CocoTBAsyncHarness basic operation
- Jitter mode (simulates network latency on ALL register writes)
- Validates that STATE_SYNC_SAFE protocol handles jittery writes correctly

The jitter applies to ALL control register writes (CR0-CR15), simulating
real network behavior. The VHDL's STATE_SYNC_SAFE protocol gates CR2-CR10
to only propagate during INITIALIZING state, protecting against race conditions.

Author: Moku Instrument Forge Team
Date: 2025-11-26
"""

import cocotb
from cocotb.triggers import ClockCycles
import sys
from pathlib import Path

# Add tests/ to path
TESTS_PATH = Path(__file__).parent.parent.parent
sys.path.insert(0, str(TESTS_PATH))

# Use new unified imports
from adapters import CocoTBAsyncHarness
from lib import (
    P1Timing,
    DEFAULT_TRIGGER_WAIT_TIMEOUT,
)

# Backward compat alias
P1TestValues = P1Timing


async def basic_setup(dut):
    """Setup clock and initialize inputs. Does NOT release reset yet.

    The caller is responsible for the reset/config sequence.
    """
    from conftest import setup_clock, init_mcc_inputs

    await setup_clock(dut, period_ns=8, clk_signal="Clk")
    await init_mcc_inputs(dut)

    # Clear all control registers
    for i in range(16):
        if hasattr(dut, f"Control{i}"):
            getattr(dut, f"Control{i}").value = 0


async def init_with_timing(dut, harness, timing_config):
    """Initialize FSM with timing config using a robust, timing-agnostic pattern.

    The key insight: set config BEFORE enabling FORGE. This way:
    - Config is already present in registers when FSM starts
    - FSM wakes up in INITIALIZING and latches whatever is there
    - No reliance on precise cycle timing (works on sim AND hardware)

    Args:
        dut: CocoTB DUT
        harness: CocoTBAsyncHarness instance
        timing_config: Object with TRIG_OUT_DURATION, INTENSITY_DURATION,
                      COOLDOWN_INTERVAL, and optionally TRIGGER_WAIT_TIMEOUT
    """
    from cocotb.triggers import ClockCycles

    # Step 1: Ensure FORGE is disabled and FSM is held in reset
    dut.Control0.value = 0  # FORGE disabled
    dut.Reset.value = 1
    await ClockCycles(dut.Clk, 5)

    # Step 2: Set ALL config registers while FSM is frozen
    # These values are just sitting in the Control registers, waiting
    dut.Control4.value = timing_config.TRIG_OUT_DURATION
    dut.Control5.value = timing_config.INTENSITY_DURATION
    dut.Control7.value = timing_config.COOLDOWN_INTERVAL
    if hasattr(timing_config, 'TRIGGER_WAIT_TIMEOUT'):
        dut.Control6.value = timing_config.TRIGGER_WAIT_TIMEOUT
    await ClockCycles(dut.Clk, 2)  # Let values settle

    # Step 3: Enable FORGE - FSM will start running
    await harness.controller.set_forge_ready(wait_after=0)
    await ClockCycles(dut.Clk, 2)

    # Step 4: Release reset - FSM starts in INITIALIZING with config already present
    # The FSM will latch the config and transition to IDLE (or FAULT if invalid)
    dut.Reset.value = 0

    # Step 5: Wait for FSM to stabilize (not timing-precise, just "enough" time)
    await ClockCycles(dut.Clk, 50)


@cocotb.test()
async def test_async_adapter_basic(dut):
    """Test basic async adapter operation (no jitter).

    This validates the adapter API works correctly with instant writes.
    Timing config is set using the "golden pattern" that respects INITIALIZING window.
    Lifecycle control (arm, trigger) uses the async adapter.
    """
    dut._log.info("Testing async adapter - basic mode (no jitter)")

    await basic_setup(dut)

    # Create harness without jitter
    harness = CocoTBAsyncHarness(dut, jitter_enabled=False)

    # Create timing config
    class Timing:
        TRIG_OUT_DURATION = P1TestValues.TRIG_OUT_DURATION
        INTENSITY_DURATION = P1TestValues.INTENSITY_DURATION
        COOLDOWN_INTERVAL = P1TestValues.COOLDOWN_INTERVAL
        TRIGGER_WAIT_TIMEOUT = DEFAULT_TRIGGER_WAIT_TIMEOUT

    # Initialize FSM with proper sequence (respects INITIALIZING window)
    await init_with_timing(dut, harness, Timing)

    # Verify FSM reached IDLE
    success = await harness.wait_for_state("IDLE", timeout_us=100)
    assert success, "FSM should reach IDLE after init"
    dut._log.info("  ✓ FSM in IDLE")

    # Arm FSM using async adapter (lifecycle control - always passes through)
    await harness.controller.set_cr1(arm_enable=True)
    await harness.controller.wait_cycles(20)

    # Wait for ARMED
    success = await harness.wait_for_state("ARMED", timeout_us=100)
    assert success, "FSM should reach ARMED after arm_enable"
    dut._log.info("  ✓ FSM in ARMED")

    # Software trigger
    await harness.software_trigger()
    await harness.controller.wait_cycles(100)

    # Should have left ARMED
    state, digital = await harness.state_reader.get_state()
    assert state != "ARMED", f"FSM should leave ARMED after trigger, got {state}"
    dut._log.info(f"  ✓ FSM triggered, now in {state}")

    dut._log.info("  ✓ PASS - Basic async adapter works")


@cocotb.test()
async def test_async_adapter_with_jitter(dut):
    """Test async adapter with jitter on lifecycle control (CR1).

    This validates that jittery CR1 writes (arm, trigger) work correctly.
    Timing config must still be set during INITIALIZING window (that's the
    hardware constraint), but lifecycle control can be jittery.

    In production, this mimics real network latency on arm/trigger commands.
    """
    dut._log.info("Testing async adapter - jitter mode on lifecycle control")

    await basic_setup(dut)

    # Create harness WITH jitter - applies to all register writes including CR1
    harness = CocoTBAsyncHarness(dut, jitter_enabled=True, jitter_range=(5, 30))

    # Create timing config
    class Timing:
        TRIG_OUT_DURATION = P1TestValues.TRIG_OUT_DURATION
        INTENSITY_DURATION = P1TestValues.INTENSITY_DURATION
        COOLDOWN_INTERVAL = P1TestValues.COOLDOWN_INTERVAL
        TRIGGER_WAIT_TIMEOUT = DEFAULT_TRIGGER_WAIT_TIMEOUT

    # Initialize FSM with proper sequence (config during INITIALIZING)
    # Note: init_with_timing uses direct dut access for timing registers,
    # so they're set synchronously. The harness jitter applies to CR1 later.
    await init_with_timing(dut, harness, Timing)

    # Verify FSM reached IDLE
    success = await harness.wait_for_state("IDLE", timeout_us=200)
    assert success, "FSM should reach IDLE after init"
    dut._log.info("  ✓ FSM in IDLE")

    # Arm FSM with jitter - this CR1 write is delayed by 5-30 cycles
    await harness.controller.set_cr1(arm_enable=True)
    await harness.controller.wait_cycles(100)

    # Wait for ARMED
    success = await harness.wait_for_state("ARMED", timeout_us=500)
    assert success, "FSM should reach ARMED even with jittery arm_enable"
    dut._log.info("  ✓ FSM in ARMED (jittery CR1 works)")

    # Software trigger with jitter
    await harness.software_trigger()
    await harness.controller.wait_cycles(200)

    # Should have left ARMED
    state, _ = await harness.state_reader.get_state()
    assert state != "ARMED", f"FSM should respond to jittery trigger, got {state}"
    dut._log.info(f"  ✓ FSM triggered with jitter, now in {state}")

    dut._log.info("  ✓ PASS - Jitter on lifecycle control works")


@cocotb.test()
async def test_async_adapter_unified_api(dut):
    """Demonstrate the unified API that works for both sim and hardware.

    This test shows the "write once, run anywhere" pattern:
    - Same async method signatures for CocoTB and Moku
    - Same test logic structure
    - Different underlying implementations handle platform differences

    In production, you'd swap CocoTBAsyncHarness for MokuAsyncHarness
    and the test code remains unchanged.
    """
    dut._log.info("Testing unified API pattern")

    await basic_setup(dut)

    # This harness could be swapped for MokuAsyncHarness without changing test code
    harness = CocoTBAsyncHarness(dut, jitter_enabled=False)

    # Create timing config
    class Timing:
        TRIG_OUT_DURATION = P1TestValues.TRIG_OUT_DURATION
        INTENSITY_DURATION = P1TestValues.INTENSITY_DURATION
        COOLDOWN_INTERVAL = P1TestValues.COOLDOWN_INTERVAL
        TRIGGER_WAIT_TIMEOUT = DEFAULT_TRIGGER_WAIT_TIMEOUT

    # Initialize with robust pattern
    await init_with_timing(dut, harness, Timing)

    # Verify FSM reached IDLE
    success = await harness.wait_for_state("IDLE", timeout_us=200)
    assert success, "FSM should be in IDLE after init"
    dut._log.info("  ✓ FSM in IDLE")

    # Use unified arm via set_cr1
    await harness.controller.set_cr1(arm_enable=True)
    await harness.controller.wait_cycles(50)

    # Wait for ARMED
    success = await harness.wait_for_state("ARMED", timeout_us=500)
    assert success, "Unified arm should work"
    dut._log.info("  ✓ Unified arm works")

    # Use unified software_trigger
    await harness.software_trigger()
    await harness.controller.wait_cycles(100)

    state, _ = await harness.state_reader.get_state()
    assert state != "ARMED", "Unified software_trigger should work"
    dut._log.info(f"  ✓ software_trigger() works, FSM in {state}")

    dut._log.info("  ✓ PASS - Unified API works (same code for sim/hw)")


@cocotb.test()
async def test_jitter_validates_sync_protocol(dut):
    """Validate that STATE_SYNC_SAFE correctly gates config register updates.

    This test demonstrates the sync protocol behavior:
    1. Config registers (CR4-CR7) set before FSM starts → latched during INITIALIZING
    2. After FSM leaves INITIALIZING, config writes are held (not propagated)
    3. CR1 (lifecycle) always passes through regardless of state

    This is the "train like you fight" validation - proving the VHDL
    handles async network writes correctly.
    """
    dut._log.info("Testing STATE_SYNC_SAFE protocol")

    await basic_setup(dut)

    harness = CocoTBAsyncHarness(dut, jitter_enabled=False)

    # Phase 1: Configure with initial timing
    initial_duration = 1000  # Short duration for quick test

    class InitialTiming:
        TRIG_OUT_DURATION = initial_duration
        INTENSITY_DURATION = initial_duration
        COOLDOWN_INTERVAL = 500
        TRIGGER_WAIT_TIMEOUT = DEFAULT_TRIGGER_WAIT_TIMEOUT

    await init_with_timing(dut, harness, InitialTiming)

    # FSM should be in IDLE now
    success = await harness.wait_for_state("IDLE", timeout_us=200)
    assert success, "FSM should be in IDLE"
    dut._log.info("  ✓ Phase 1: Config latched, FSM in IDLE")

    # Phase 2: Try to change config AFTER leaving INITIALIZING
    # These writes should be HELD (not propagated) due to STATE_SYNC_SAFE
    different_duration = 50000  # Much longer - would be obvious if applied
    await harness.controller.set_control_register(4, different_duration)
    await harness.controller.wait_cycles(50)

    # Arm and trigger - FSM should use the ORIGINAL timing (1000 cycles)
    await harness.controller.set_cr1(arm_enable=True)
    await harness.controller.wait_cycles(50)

    success = await harness.wait_for_state("ARMED", timeout_us=200)
    assert success, "FSM should arm"
    dut._log.info("  ✓ Phase 2: FSM armed")

    # Trigger
    await harness.software_trigger()

    # Wait for original timing (~2500 cycles total) + generous margin
    # If the late config write (50000 cycles) was incorrectly applied,
    # the FSM would still be in FIRING
    await harness.controller.wait_cycles(5000)

    # Should have completed the cycle (not still FIRING with 50000 cycle duration)
    state, _ = await harness.state_reader.get_state()
    in_expected_state = state in ["COOLDOWN", "IDLE", "ARMED"]
    assert in_expected_state, f"FSM should complete with original timing (late config ignored), got {state}"
    dut._log.info(f"  ✓ Phase 3: FSM completed (used original timing), now in {state}")

    dut._log.info("  ✓ PASS - STATE_SYNC_SAFE correctly gates config updates")


# =============================================================================
# Hardware Test Entry Point
# =============================================================================
# When running via unified runner with --backend hw, these functions are called
# with a MokuAsyncHarness instead of CocoTBAsyncHarness.


async def _test_basic_async(harness, log_fn):
    """Backend-agnostic basic async test."""
    log_fn("Testing async adapter - basic mode")

    # Wait for IDLE (hardware may need more time)
    success = await harness.wait_for_state("IDLE", timeout_us=500000)
    if not success:
        # Try reset
        await harness.reset_to_idle(timeout_us=500000)
        success = await harness.wait_for_state("IDLE", timeout_us=500000)
    assert success, "FSM should reach IDLE"
    log_fn("  ✓ FSM in IDLE")

    # Arm FSM
    await harness.controller.set_cr1(arm_enable=True)
    await harness.controller.wait_ms(100)

    success = await harness.wait_for_state("ARMED", timeout_us=500000)
    assert success, "FSM should reach ARMED"
    log_fn("  ✓ FSM in ARMED")

    # Software trigger
    await harness.software_trigger()
    await harness.controller.wait_ms(200)

    state, _ = await harness.state_reader.get_state()
    assert state != "ARMED", f"FSM should leave ARMED after trigger, got {state}"
    log_fn(f"  ✓ FSM triggered, now in {state}")

    log_fn("  ✓ PASS - Basic async adapter works")
    return True


async def _test_unified_api(harness, log_fn):
    """Backend-agnostic unified API test."""
    log_fn("Testing unified API pattern")

    # Reset to known state
    await harness.reset_to_idle(timeout_us=500000)

    success = await harness.wait_for_state("IDLE", timeout_us=500000)
    assert success, "FSM should be in IDLE after reset"
    log_fn("  ✓ FSM in IDLE")

    # Arm
    await harness.controller.set_cr1(arm_enable=True)
    await harness.controller.wait_ms(100)

    success = await harness.wait_for_state("ARMED", timeout_us=500000)
    assert success, "Unified arm should work"
    log_fn("  ✓ Unified arm works")

    # Trigger
    await harness.software_trigger()
    await harness.controller.wait_ms(200)

    state, _ = await harness.state_reader.get_state()
    assert state != "ARMED", "Unified software_trigger should work"
    log_fn(f"  ✓ software_trigger() works, FSM in {state}")

    log_fn("  ✓ PASS - Unified API works")
    return True


async def run_hardware_tests(harness) -> bool:
    """
    Entry point for hardware testing via unified runner.

    This function is called by tests/run.py when --backend hw is specified.
    It runs the same test logic as the CocoTB tests but with MokuAsyncHarness.

    Args:
        harness: MokuAsyncHarness instance

    Returns:
        True if all tests pass, False otherwise
    """
    def log_fn(msg):
        print(f"  {msg}")

    print("\n" + "=" * 60)
    print("P1 Async Adapter Tests - Hardware Backend")
    print("=" * 60)

    all_passed = True

    # Initialize FSM (sets config, enables FORGE, clears fault → IDLE)
    print("\nInitializing FSM...")
    await harness.initialize_fsm()
    print("  ✓ FSM initialized")

    # Test 1: Basic async
    print("\n--- Test 1: Basic Async Adapter ---")
    try:
        await _test_basic_async(harness, log_fn)
    except AssertionError as e:
        print(f"  ❌ FAILED: {e}")
        all_passed = False

    # Test 2: Unified API
    print("\n--- Test 2: Unified API Pattern ---")
    try:
        await _test_unified_api(harness, log_fn)
    except AssertionError as e:
        print(f"  ❌ FAILED: {e}")
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL HARDWARE TESTS PASSED")
    else:
        print("❌ SOME HARDWARE TESTS FAILED")
    print("=" * 60)

    return all_passed

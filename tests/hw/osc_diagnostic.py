#!/usr/bin/env python3
"""
Oscilloscope Diagnostic Test - Software Trigger Debug Edition
=============================================================

Debug tool for the DPD FSM, specifically targeting the sw_trigger migration
from CR1[5] to CR0[0].

BACKGROUND:
-----------
We moved sw_trigger from CR1[5] to CR0[0] to provide a more direct network
path for the software trigger signal. The theory is that CR0 updates propagate
faster than CR1 since CR0 contains the FORGE control bits which are critical
for FSM operation.

REGISTER LAYOUT (after migration):
----------------------------------
CR0[31:29] = FORGE control (forge_ready, user_enable, clk_enable)
CR0[0]     = sw_trigger (edge-detected) ← NEW LOCATION

CR1[0]     = arm_enable
CR1[1]     = auto_rearm_enable
CR1[2]     = fault_clear (edge-detected)
CR1[3]     = sw_trigger_enable (gates CR0[0])
CR1[4]     = hw_trigger_enable
CR1[5]     = UNUSED (was sw_trigger) ← OLD LOCATION

@JC / @CLAUDE: 
perhaps it would make sense to migrate __all__ of the bits  that we have inside CR1 into the bottom of CR0.
We could leave CR1 'reserved' and or 'unused'. whatever the issue we are troubleshooting, this might help minimize special / edge cases. 



TRIGGER SEQUENCE:
-----------------
1. Set CR1 = 0x09  (arm_enable + sw_trigger_enable)
2. Set CR0 = 0xE0000000  (FORGE enabled, ensure sw_trigger=0)
3. Set CR0 = 0xE0000001  (rising edge on sw_trigger)
4. Set CR0 = 0xE0000000  (falling edge, clear sw_trigger)

VHDL EDGE DETECTION (DPD_shim.vhd):
-----------------------------------
The sw_trigger signal goes through edge detection in the shim layer:

  app_reg_sw_trigger <= app_reg_0(0);  -- Extract from CR0
  sw_trigger_edge <= app_reg_sw_trigger and not sw_trigger_prev;
  combined_trigger <= '1' when (sw_trigger_edge = '1' and sw_trigger_enable = '1') else ...
  combined_trigger_reg <= combined_trigger;  -- Registered to prevent glitches

The FSM sees ext_trigger_in => combined_trigger_reg

CURRENT ISSUE:
--------------
Simulation: PASSES (edge detection works correctly)
Hardware: FAILS (FSM stays in ARMED after trigger pulse)

DEBUGGING APPROACH:
-------------------
1. Test NEW method (CR0[0]) - should work if bitstream is rebuilt
2. Test OLD method (CR1[5]) - if this works, bitstream wasn't rebuilt
3. If both fail, investigate timing/synchronization issues

Run:
    cd tests
    uv run python hw/osc_diagnostic.py 192.168.31.41 ../dpd-bits.tar
"""

import sys
import time
import asyncio
from pathlib import Path

# Setup paths
TESTS_DIR = Path(__file__).parent.parent
PROJECT_ROOT = TESTS_DIR.parent
sys.path.insert(0, str(TESTS_DIR))
sys.path.insert(0, str(PROJECT_ROOT / "py_tools"))

from loguru import logger

# Configure logging
logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <level>{message}</level>", level="DEBUG")


def analyze_osc_data(data: dict, label: str = ""):
    """Analyze and print oscilloscope data structure."""
    logger.info(f"=== Oscilloscope Data Analysis {label} ===")
    logger.info(f"Keys: {list(data.keys())}")

    for key, value in data.items():
        if isinstance(value, list):
            if len(value) > 0:
                logger.info(f"  {key}: list[{len(value)}], type={type(value[0]).__name__}")
                logger.info(f"    min={min(value):.6f}, max={max(value):.6f}")
                logger.info(f"    first={value[0]:.6f}, mid={value[len(value)//2]:.6f}, last={value[-1]:.6f}")
            else:
                logger.info(f"  {key}: empty list")
        else:
            logger.info(f"  {key}: {type(value).__name__} = {value}")


def voltage_to_state(voltage: float, tolerance: float = 0.3) -> str:
    """Decode HVS voltage to FSM state name."""
    STATE_VOLTAGES = {
        "INITIALIZING": 0.0,
        "IDLE": 0.5,
        "ARMED": 1.0,
        "FIRING": 1.5,
        "COOLDOWN": 2.0,
    }

    if voltage < -tolerance:
        return "FAULT"

    for state, expected_v in STATE_VOLTAGES.items():
        if abs(voltage - expected_v) < tolerance:
            return state

    return f"UNKNOWN({voltage:.3f}V)"


async def run_diagnostic(device_ip: str, bitstream_path: str):
    """Run oscilloscope diagnostic tests."""
    from hw.plumbing import MokuSession, MokuConfig

    config = MokuConfig(
        device_ip=device_ip,
        bitstream_path=bitstream_path,
        force_connect=True,
    )

    logger.info(f"Connecting to {device_ip}...")

    async with MokuSession(config) as session:
        logger.success("Connected and instruments deployed")

        osc = session.osc
        mcc = session.mcc

        # =====================================================================
        # Test 1: Raw data structure
        # =====================================================================
        logger.info("\n" + "=" * 60)
        logger.info("TEST 1: Raw Oscilloscope Data Structure")
        logger.info("=" * 60)

        try:
            data = osc.get_data()
            analyze_osc_data(data, "initial read")
        except Exception as e:
            logger.error(f"Failed to get data: {e}")
            return

        # =====================================================================
        # Test 2: Multiple reads - timing and consistency
        # =====================================================================
        logger.info("\n" + "=" * 60)
        logger.info("TEST 2: Multiple Reads - Timing & Consistency")
        logger.info("=" * 60)

        readings = []
        timings = []

        for i in range(10):
            start = time.perf_counter()
            data = osc.get_data()
            elapsed = time.perf_counter() - start
            timings.append(elapsed * 1000)

            if 'ch1' in data and len(data['ch1']) > 0:
                mid_value = data['ch1'][len(data['ch1']) // 2]
                readings.append(mid_value)
                state = voltage_to_state(mid_value)
                logger.debug(f"  Read {i+1}: {mid_value:.4f}V = {state} ({elapsed*1000:.1f}ms)")
            else:
                logger.warning(f"  Read {i+1}: No ch1 data")

            await asyncio.sleep(0.05)

        if readings:
            logger.info(f"Summary of {len(readings)} reads:")
            logger.info(f"  Voltage: min={min(readings):.4f}V, max={max(readings):.4f}V, avg={sum(readings)/len(readings):.4f}V")
            logger.info(f"  Spread: {max(readings) - min(readings):.4f}V")
            logger.info(f"  Timing: min={min(timings):.1f}ms, max={max(timings):.1f}ms, avg={sum(timings)/len(timings):.1f}ms")

        # =====================================================================
        # Test 3: CORRECT INITIALIZATION SEQUENCE
        # =====================================================================
        logger.info("\n" + "=" * 60)
        logger.info("TEST 3: Correct Initialization Sequence")
        logger.info("=" * 60)
        logger.info("Hypothesis: FSM faults on load because timing config is zero.")
        logger.info("Solution: Set timing BEFORE enabling FORGE, then fault_clear.")

        # Step 1: Read initial state
        data = osc.get_data()
        if 'ch1' in data and data['ch1']:
            v = data['ch1'][len(data['ch1']) // 2]
            logger.info(f"Step 0 - Initial state: {v:.4f}V = {voltage_to_state(v)}")

        # Step 2: Clear ALL registers first
        logger.info("Step 1 - Clearing all registers (CR0-CR10 = 0)...")
        for i in range(11):
            mcc.set_control(i, 0)
        await asyncio.sleep(0.1)

        # Step 3: Set timing config FIRST (before FORGE enable)
        logger.info("Step 2 - Setting timing config (CR4-CR7) BEFORE FORGE...")
        mcc.set_control(4, 12500)      # trig_duration: 100μs @ 125MHz
        mcc.set_control(5, 25000)      # intensity_duration: 200μs
        mcc.set_control(6, 250000000)  # timeout: 2s
        mcc.set_control(7, 1250)       # cooldown: 10μs
        await asyncio.sleep(0.1)

        # Step 4: Set output voltages
        logger.info("Step 3 - Setting output voltages (CR2-CR3)...")
        mcc.set_control(2, (1000 << 16) | 2000)  # threshold=1V, trig_out=2V
        mcc.set_control(3, 1500)                  # intensity=1.5V
        await asyncio.sleep(0.1)

        # Step 5: NOW enable FORGE
        logger.info("Step 4 - Enabling FORGE (CR0 = 0xE0000000)...")
        mcc.set_control(0, 0xE0000000)
        await asyncio.sleep(0.3)

        data = osc.get_data()
        if 'ch1' in data and data['ch1']:
            v = data['ch1'][len(data['ch1']) // 2]
            logger.info(f"After FORGE enable: {v:.4f}V = {voltage_to_state(v)}")

        # Step 6: Pulse fault_clear to force re-initialization
        logger.info("Step 5 - Pulsing fault_clear (CR1[2]) to re-latch config...")
        mcc.set_control(1, 0x04)  # fault_clear bit
        await asyncio.sleep(0.15)
        mcc.set_control(1, 0x00)
        await asyncio.sleep(0.3)

        data = osc.get_data()
        if 'ch1' in data and data['ch1']:
            v = data['ch1'][len(data['ch1']) // 2]
            state = voltage_to_state(v)
            logger.info(f"After fault_clear: {v:.4f}V = {state}")

            if state == "IDLE":
                logger.success("✓ FSM reached IDLE! Sequence works.")
            elif state == "INITIALIZING":
                logger.info("FSM in INITIALIZING - may need more time")
                await asyncio.sleep(0.5)
                data = osc.get_data()
                v = data['ch1'][len(data['ch1']) // 2]
                logger.info(f"After extra wait: {v:.4f}V = {voltage_to_state(v)}")
            elif state == "FAULT":
                logger.error("FSM still in FAULT after correct sequence!")
                logger.info("Possible causes:")
                logger.info("  1. Bitstream needs recompile (STATE_SYNC_SAFE issue)")
                logger.info("  2. CR register mapping mismatch")
                logger.info("  3. Hardware timing constraint")
            else:
                logger.info(f"FSM in unexpected state: {state}")

        # =====================================================================
        # Test 4: Alternative - Try FORGE enable THEN immediate fault_clear
        # =====================================================================
        logger.info("\n" + "=" * 60)
        logger.info("TEST 4: Alternative Sequence - Rapid fault_clear")
        logger.info("=" * 60)

        # Reset everything
        logger.info("Resetting all registers...")
        for i in range(11):
            mcc.set_control(i, 0)
        await asyncio.sleep(0.2)

        # Set config
        logger.info("Setting config...")
        mcc.set_control(4, 12500)
        mcc.set_control(5, 25000)
        mcc.set_control(6, 250000000)
        mcc.set_control(7, 1250)
        mcc.set_control(2, (1000 << 16) | 2000)
        mcc.set_control(3, 1500)

        # Enable FORGE and IMMEDIATELY pulse fault_clear
        logger.info("FORGE enable + immediate fault_clear pulse...")
        mcc.set_control(0, 0xE0000000)
        mcc.set_control(1, 0x04)  # fault_clear
        await asyncio.sleep(0.05)
        mcc.set_control(1, 0x00)
        await asyncio.sleep(0.3)

        data = osc.get_data()
        if 'ch1' in data and data['ch1']:
            v = data['ch1'][len(data['ch1']) // 2]
            state = voltage_to_state(v)
            logger.info(f"Result: {v:.4f}V = {state}")
            if state == "IDLE":
                logger.success("✓ Rapid sequence works!")

        # =====================================================================
        # Test 5: Alternative reading strategies
        # =====================================================================
        logger.info("\n" + "=" * 60)
        logger.info("TEST 5: Alternative Reading Strategies")
        logger.info("=" * 60)

        # Strategy A: Single midpoint sample
        data = osc.get_data()
        if 'ch1' in data and data['ch1']:
            ch1 = data['ch1']
            mid = ch1[len(ch1) // 2]
            logger.info(f"Strategy A (midpoint): {mid:.4f}V = {voltage_to_state(mid)}")

        # Strategy B: Average of middle 10%
        data = osc.get_data()
        if 'ch1' in data and data['ch1']:
            ch1 = data['ch1']
            n = len(ch1)
            start_idx = int(n * 0.45)
            end_idx = int(n * 0.55)
            middle_samples = ch1[start_idx:end_idx]
            avg = sum(middle_samples) / len(middle_samples)
            logger.info(f"Strategy B (middle 10% avg): {avg:.4f}V = {voltage_to_state(avg)}")

        # Strategy C: Mode/most common value (rounded)
        data = osc.get_data()
        if 'ch1' in data and data['ch1']:
            ch1 = data['ch1']
            # Round to 0.1V and find mode
            rounded = [round(v, 1) for v in ch1]
            from collections import Counter
            mode_v = Counter(rounded).most_common(1)[0][0]
            logger.info(f"Strategy C (mode, 0.1V bins): {mode_v:.1f}V = {voltage_to_state(mode_v)}")

        # Strategy D: Median
        data = osc.get_data()
        if 'ch1' in data and data['ch1']:
            ch1 = sorted(data['ch1'])
            median = ch1[len(ch1) // 2]
            logger.info(f"Strategy D (median): {median:.4f}V = {voltage_to_state(median)}")

        # =====================================================================
        # Test 6: Full waveform characteristics
        # =====================================================================
        logger.info("\n" + "=" * 60)
        logger.info("TEST 6: Waveform Characteristics")
        logger.info("=" * 60)

        data = osc.get_data()
        if 'ch1' in data and data['ch1']:
            ch1 = data['ch1']

            # Check if it's a flat line (DC) or has transitions
            diffs = [abs(ch1[i+1] - ch1[i]) for i in range(len(ch1)-1)]
            max_diff = max(diffs)
            avg_diff = sum(diffs) / len(diffs)

            logger.info(f"Waveform length: {len(ch1)} samples")
            logger.info(f"Value range: {min(ch1):.4f}V to {max(ch1):.4f}V")
            logger.info(f"Sample-to-sample diff: max={max_diff:.4f}V, avg={avg_diff:.6f}V")

            if max_diff < 0.1:
                logger.info("→ Appears to be stable DC signal (good for HVS reading)")
            else:
                logger.warning(f"→ Signal has transitions (max Δ={max_diff:.3f}V)")

        # =====================================================================
        # Test 7: Software Trigger Debug (CR0[0] Migration Test)
        # =====================================================================
        # This is the CRITICAL test for the sw_trigger migration.
        #
        # WHAT WE'RE TESTING:
        # - sw_trigger was moved from CR1[5] to CR0[0]
        # - Edge detection should generate a 1-cycle pulse on 0→1 transition
        # - That pulse, gated by sw_trigger_enable (CR1[3]), triggers the FSM
        #
        # IF NEW METHOD FAILS BUT OLD METHOD WORKS:
        # → Bitstream wasn't rebuilt! Need to recompile with CloudCompile.
        #
        # IF BOTH METHODS FAIL:
        # → Deeper issue - check timing validation, sync logic, etc.
        # =====================================================================
        logger.info("\n" + "=" * 60)
        logger.info("TEST 7: Software Trigger Debug (CR0[0] vs CR1[5])")
        logger.info("=" * 60)

        # Make sure we're in a known state
        logger.info("Resetting to IDLE...")
        for i in range(11):
            mcc.set_control(i, 0)
        await asyncio.sleep(0.1)

        # Set timing config
        mcc.set_control(4, 12500)      # trig_duration: 100μs
        mcc.set_control(5, 25000)      # intensity_duration: 200μs
        mcc.set_control(6, 250000000)  # timeout: 2s
        mcc.set_control(7, 1250)       # cooldown: 10μs
        mcc.set_control(2, (1000 << 16) | 2000)
        mcc.set_control(3, 1500)

        # Enable FORGE and clear fault
        mcc.set_control(0, 0xE0000000)
        mcc.set_control(1, 0x04)
        await asyncio.sleep(0.05)
        mcc.set_control(1, 0x00)
        await asyncio.sleep(0.2)

        data = osc.get_data()
        v = data['ch1'][len(data['ch1']) // 2]
        logger.info(f"After reset: {v:.4f}V = {voltage_to_state(v)}")

        # ARM the FSM
        logger.info("Arming FSM (CR1 = 0x01)...")
        mcc.set_control(1, 0x01)  # arm_enable only
        await asyncio.sleep(0.2)

        data = osc.get_data()
        v = data['ch1'][len(data['ch1']) // 2]
        state = voltage_to_state(v)
        logger.info(f"After arm: {v:.4f}V = {state}")

        if state != "ARMED":
            logger.error(f"Expected ARMED, got {state}")
        else:
            # Try software trigger (sw_trigger is now CR0[0])
            logger.info("Sending software trigger...")
            logger.info("  Step 1: CR1 = 0x09 (arm + sw_trigger_enable)")
            mcc.set_control(1, 0x09)  # arm_enable + sw_trigger_enable
            await asyncio.sleep(0.05)

            # IMPORTANT: Ensure CR0[0]=0 first to guarantee rising edge
            logger.info("  Step 2: CR0 = 0xE0000000 (ensure sw_trigger=0)")
            mcc.set_control(0, 0xE0000000)  # FORGE only, sw_trigger=0
            await asyncio.sleep(0.05)

            logger.info("  Step 3: CR0 = 0xE0000001 (FORGE + sw_trigger rising edge)")
            mcc.set_control(0, 0xE0000001)  # FORGE + sw_trigger (rising edge)
            await asyncio.sleep(0.1)

            # Check state mid-trigger
            data = osc.get_data()
            v = data['ch1'][len(data['ch1']) // 2]
            logger.info(f"  Mid-trigger state: {v:.4f}V = {voltage_to_state(v)}")

            logger.info("  Step 4: CR0 = 0xE0000000 (clear sw_trigger)")
            mcc.set_control(0, 0xE0000000)  # Clear sw_trigger (falling edge)
            await asyncio.sleep(0.3)

            data = osc.get_data()
            v = data['ch1'][len(data['ch1']) // 2]
            state = voltage_to_state(v)
            logger.info(f"  After trigger: {v:.4f}V = {state}")

            if state == "ARMED":
                logger.error("FSM still ARMED - trigger not detected!")
                logger.info("\nChecking if OLD bitstream is loaded (sw_trigger on CR1[5])...")

                # Re-arm first (FSM might have timed out)
                mcc.set_control(1, 0x01)  # arm only
                await asyncio.sleep(0.2)

                # Try OLD method: sw_trigger on CR1[5] (bit 5 = 0x20)
                # OLD CR1 = 0x29 = arm(0) + sw_trigger_enable(3) + sw_trigger(5)
                logger.info("  Trying OLD: CR1 = 0x09 then 0x29 (sw_trigger on CR1[5])")
                mcc.set_control(1, 0x09)  # arm + sw_trigger_enable (no trigger yet)
                await asyncio.sleep(0.05)
                mcc.set_control(1, 0x29)  # Add sw_trigger at bit 5 (OLD location)
                await asyncio.sleep(0.1)
                mcc.set_control(1, 0x09)  # Clear sw_trigger
                await asyncio.sleep(0.3)

                data = osc.get_data()
                v = data['ch1'][len(data['ch1']) // 2]
                state = voltage_to_state(v)
                logger.info(f"  Result with OLD method: {v:.4f}V = {state}")
                if state != "ARMED":
                    logger.warning(f"*** OLD BITSTREAM DETECTED! sw_trigger still on CR1[5] ***")
                    logger.warning("*** You need to REBUILD the bitstream with CloudCompile! ***")
                else:
                    logger.info("Both OLD and NEW methods failed - deeper issue")
            else:
                logger.success(f"✓ Software trigger worked! FSM in {state}")

        logger.info("\n" + "=" * 60)
        logger.info("DIAGNOSTIC COMPLETE")
        logger.info("=" * 60)


def main():
    if len(sys.argv) < 3:
        print("Usage: python osc_diagnostic.py <device_ip> <bitstream_path>")
        print("Example: python osc_diagnostic.py 192.168.31.41 ../dpd-bits.tar")
        sys.exit(1)

    device_ip = sys.argv[1]
    bitstream_path = sys.argv[2]

    asyncio.run(run_diagnostic(device_ip, bitstream_path))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
clock_probe_test.py - Measure MCC fabric clock frequency empirically

This script deploys the clock_probe bitstream and measures the pulse width
of the SQR_04_128 waveform to determine the actual FPGA clock frequency.

Expected results:
  Moku:Go  @ ADC clock (125 MHz):    pulse = 32 ns,  freq = 125 MHz
  Moku:Go  @ MCC fabric (31.25 MHz): pulse = 128 ns, freq = 31.25 MHz
  Moku:Lab @ ADC clock (500 MHz):    pulse = 8 ns,   freq = 500 MHz
  Moku:Lab @ MCC fabric (125 MHz):   pulse = 32 ns,  freq = 125 MHz

Usage:
  python clock_probe_test.py <moku_ip> <bitstream_path> [--platform-id N]

Example:
  python clock_probe_test.py 192.168.73.1 clock_probe_mokugo.tar.gz --platform-id 2
"""

import argparse
import sys
import time
import numpy as np

try:
    from moku.instruments import MultiInstrument, Oscilloscope, CloudCompile
except ImportError:
    print("Error: moku package not installed. Run: pip install moku")
    sys.exit(1)


# Platform reference
PLATFORMS = {
    2: {
        'name': 'Moku:Go',
        'adc_mhz': 125,
        'mcc_mhz': 31.25,
        'adc_pulse_ns': 32,    # 4 samples × 8 ns
        'mcc_pulse_ns': 128,   # 4 samples × 32 ns
    },
    # Moku:Lab platform_id is also 2, but different hardware
    # This will be detected by pulse measurement
}


def measure_pulse_width(osc, num_samples: int = 5) -> float | None:
    """
    Capture waveform and measure pulse width.

    Returns pulse width in seconds, or None if measurement failed.
    """
    pulse_widths = []

    for _ in range(num_samples):
        try:
            data = osc.get_data(timeout=5, wait_reacquire=True)

            time_axis = np.array(data['time'])
            ch1 = np.array(data['ch1'])

            # Simple threshold at 50% of amplitude
            v_max = np.max(ch1)
            v_min = np.min(ch1)
            threshold = (v_max + v_min) / 2

            # Need sufficient amplitude
            if v_max - v_min < 0.5:
                print(f"  Warning: Low amplitude ({v_max - v_min:.2f}V)")
                continue

            # Find crossings
            above = ch1 > threshold
            transitions = np.diff(above.astype(int))
            rising = np.where(transitions == 1)[0]
            falling = np.where(transitions == -1)[0]

            if len(rising) == 0 or len(falling) == 0:
                continue

            # Find first complete pulse (rising then falling)
            for rise_idx in rising:
                fall_candidates = falling[falling > rise_idx]
                if len(fall_candidates) > 0:
                    fall_idx = fall_candidates[0]
                    pulse_width = time_axis[fall_idx] - time_axis[rise_idx]
                    if pulse_width > 0:
                        pulse_widths.append(pulse_width)
                        break

            time.sleep(0.05)

        except Exception as e:
            print(f"  Warning: Capture failed: {e}")
            continue

    if pulse_widths:
        return np.median(pulse_widths)
    return None


def run_experiment(moku_ip: str, bitstream_path: str, platform_id: int):
    """Run the clock frequency measurement experiment."""

    print("=" * 60)
    print("MCC Fabric Clock Frequency Measurement")
    print("=" * 60)
    print(f"Target: {moku_ip}")
    print(f"Bitstream: {bitstream_path}")
    print(f"Platform ID: {platform_id}")
    print()

    # Expected values
    platform = PLATFORMS.get(platform_id, PLATFORMS[2])
    print(f"Platform: {platform['name']}")
    print(f"Expected results:")
    print(f"  If ADC clock ({platform['adc_mhz']} MHz):     pulse = {platform['adc_pulse_ns']} ns")
    print(f"  If MCC fabric ({platform['mcc_mhz']} MHz):  pulse = {platform['mcc_pulse_ns']} ns")
    print()

    m = None
    try:
        print("Connecting to Moku...")
        m = MultiInstrument(moku_ip, platform_id=platform_id, force_connect=True)

        print("Deploying CloudCompile bitstream to slot 1...")
        mcc = m.set_instrument(1, CloudCompile, bitstream=bitstream_path)

        print("Deploying Oscilloscope to slot 2...")
        osc = m.set_instrument(2, Oscilloscope)

        print("Configuring signal routing...")
        m.set_connections([
            {'source': 'Slot1OutA', 'destination': 'Slot2InA'},
            {'source': 'Slot1OutA', 'destination': 'Output1'},
        ])

        print("Configuring oscilloscope...")
        # Wide timebase to capture multiple periods
        osc.set_timebase(t1=-1e-6, t2=5e-6)  # -1µs to +5µs

        # Trigger on rising edge
        osc.set_trigger(
            type='Edge',
            source='Input1',
            level=1.0,  # 1V trigger level
            edge='Rising',
            mode='Normal'
        )

        # Enable FORGE: CR0[31:29] = 0xE0000000
        print("Enabling FORGE (CR0 = 0xE0000000)...")
        mcc.set_control(0, 0xE0000000)

        time.sleep(0.2)  # Let waveform stabilize

        print()
        print("Measuring pulse width (5 samples)...")
        pulse_width = measure_pulse_width(osc, num_samples=5)

        print()
        print("=" * 60)
        print("RESULTS")
        print("=" * 60)

        if pulse_width is None:
            print("ERROR: Could not measure pulse width")
            print("Check:")
            print("  - Bitstream compiled and deployed correctly")
            print("  - Signal routing is correct")
            print("  - Oscilloscope trigger settings")
            return

        pulse_ns = pulse_width * 1e9
        clock_period_ns = pulse_ns / 4  # 4 samples high
        clock_freq_mhz = 1000 / clock_period_ns

        print(f"Measured pulse width: {pulse_ns:.1f} ns")
        print(f"Implied clock period: {clock_period_ns:.1f} ns")
        print(f"Implied clock frequency: {clock_freq_mhz:.2f} MHz")
        print()

        # Determine which hypothesis matches
        adc_expected = platform['adc_pulse_ns']
        mcc_expected = platform['mcc_pulse_ns']

        # Allow 20% tolerance
        if abs(pulse_ns - adc_expected) / adc_expected < 0.2:
            print(f"→ HYPOTHESIS A CONFIRMED: VHDL runs at ADC clock ({platform['adc_mhz']} MHz)")
            print()
            print("Implications:")
            print("  - DPD clk_utils.py frequency is CORRECT")
            print("  - Example code period_dict needs explanation")
            print("  - 4× factor is applied somewhere else in pipeline")

        elif abs(pulse_ns - mcc_expected) / mcc_expected < 0.2:
            print(f"→ HYPOTHESIS B CONFIRMED: VHDL runs at MCC fabric clock ({platform['mcc_mhz']} MHz)")
            print()
            print("Implications:")
            print("  - DPD clk_utils.py frequency should be {platform['mcc_mhz']} MHz!")
            print("  - Example code period_dict is AUTHORITATIVE")
            print("  - All timing calculations need review")

        else:
            print(f"→ UNEXPECTED RESULT: Neither hypothesis matches")
            print(f"   Expected ADC pulse: {adc_expected} ns")
            print(f"   Expected MCC pulse: {mcc_expected} ns")
            print(f"   Measured pulse: {pulse_ns:.1f} ns")
            print()
            print("Possible explanations:")
            print("  - Different clock architecture than expected")
            print("  - Measurement error (check oscilloscope settings)")
            print("  - Bitstream not running correctly")

    except Exception as e:
        print(f"ERROR: {e}")
        raise

    finally:
        if m is not None:
            print()
            print("Releasing Moku...")
            try:
                m.relinquish_ownership()
            except:
                pass


def main():
    parser = argparse.ArgumentParser(
        description="Measure MCC fabric clock frequency empirically"
    )
    parser.add_argument('moku_ip', help='Moku device IP address')
    parser.add_argument('bitstream_path', help='Path to clock_probe bitstream .tar.gz')
    parser.add_argument('--platform-id', type=int, default=2,
                        help='Moku platform ID (default: 2 for Moku:Go)')

    args = parser.parse_args()
    run_experiment(args.moku_ip, args.bitstream_path, args.platform_id)


if __name__ == "__main__":
    main()

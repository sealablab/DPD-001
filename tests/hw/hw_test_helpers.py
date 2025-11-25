"""
Hardware Test Helper Functions for Demo Probe Driver (DPD)

Utilities for FSM control, state reading, and oscilloscope interaction.
Adapted from debug_oscilloscope.py and debug_fsm_states.py

Author: Moku Instrument Forge Team
Date: 2025-01-18
"""

import time
from typing import Tuple, Optional

from hw_test_constants import (
    STATE_VOLTAGE_MAP,
    STATE_VOLTAGE_TOLERANCE,
    MCC_CR0_ALL_ENABLED,
    us_to_cycles,
    OSC_POLL_COUNT_DEFAULT,
    OSC_POLL_INTERVAL_MS,
)


def decode_fsm_state(voltage: float, tolerance: float = STATE_VOLTAGE_TOLERANCE) -> str:
    """
    Decode FSM state from voltage reading.

    HVS Encoding: 3277 digital units per state step (0.5V per state)
    Voltage = (digital_units / 32768) * 5V
    State voltages:
      - INITIALIZING (0): 0 units     → 0.0V (transient)
      - IDLE (1):         3277 units  → 0.5V
      - ARMED (2):        6554 units  → 1.0V
      - FIRING (3):       9831 units  → 1.5V
      - COOLDOWN (4):     13108 units → 2.0V
      - FAULT:            negative voltage (STATUS[7]=1)

    Args:
        voltage: Voltage reading from oscilloscope (V)
        tolerance: Allowed deviation from expected state voltage (V)

    Returns:
        State name string (INITIALIZING, IDLE, ARMED, FIRING, COOLDOWN, FAULT, or UNKNOWN)
    """
    # Check for FAULT first (any negative voltage)
    if voltage < -tolerance:
        return "FAULT"

    # Check each known state
    for state_name, expected_voltage in STATE_VOLTAGE_MAP.items():
        if abs(voltage - expected_voltage) < tolerance:
            return state_name

    # Unknown state
    return f"UNKNOWN({voltage:.3f}V)"


def read_oscilloscope_voltage(osc, poll_count: int = OSC_POLL_COUNT_DEFAULT,
                               poll_interval_ms: float = OSC_POLL_INTERVAL_MS) -> float:
    """
    Read voltage from oscilloscope Ch1 with averaging.

    Args:
        osc: Oscilloscope instrument instance
        poll_count: Number of samples to average
        poll_interval_ms: Milliseconds between samples

    Returns:
        Average voltage reading (V)
    """
    voltages = []
    for _ in range(poll_count):
        data = osc.get_data()
        # Sample middle of waveform buffer for stability
        if 'ch1' in data and len(data['ch1']) > 0:
            midpoint = len(data['ch1']) // 2
            voltages.append(data['ch1'][midpoint])
        time.sleep(poll_interval_ms / 1000.0)

    if not voltages:
        raise RuntimeError("Failed to read oscilloscope data (no ch1 data)")

    return sum(voltages) / len(voltages)


def read_fsm_state(osc, poll_count: int = OSC_POLL_COUNT_DEFAULT,
                   poll_interval_ms: float = OSC_POLL_INTERVAL_MS) -> Tuple[str, float]:
    """
    Read current FSM state from oscilloscope Ch1 (monitoring OutputC).

    Args:
        osc: Oscilloscope instrument instance
        poll_count: Number of samples to average (handle noise)
        poll_interval_ms: Milliseconds between samples

    Returns:
        Tuple of (state_name, voltage)
    """
    voltage = read_oscilloscope_voltage(osc, poll_count, poll_interval_ms)
    state = decode_fsm_state(voltage)
    return state, voltage


def wait_for_state(osc, expected_state: str, timeout_ms: float = 2000,
                   poll_count: int = 3, poll_interval_ms: float = 50) -> bool:
    """
    Poll oscilloscope until expected FSM state is reached or timeout.

    Args:
        osc: Oscilloscope instrument instance
        expected_state: Target state name (IDLE, ARMED, FIRING, COOLDOWN)
        timeout_ms: Timeout in milliseconds
        poll_count: Number of samples to average per poll
        poll_interval_ms: Milliseconds between polls

    Returns:
        True if state reached, False on timeout
    """
    start_time = time.time()

    while (time.time() - start_time) * 1000 < timeout_ms:
        state, voltage = read_fsm_state(osc, poll_count=poll_count, poll_interval_ms=20)
        if state == expected_state:
            return True
        time.sleep(poll_interval_ms / 1000.0)

    return False


def wait_for_state_with_retry(osc, expected_state: str, retries: int = 2,
                               timeout_ms: float = 2000) -> bool:
    """
    Wait for FSM state with automatic retry on timeout.

    Useful for handling transient oscilloscope read failures.

    Args:
        osc: Oscilloscope instrument instance
        expected_state: Target state name
        retries: Number of retry attempts (0 = no retry)
        timeout_ms: Timeout per attempt in milliseconds

    Returns:
        True if state reached, False if all attempts timeout
    """
    for attempt in range(retries + 1):
        if wait_for_state(osc, expected_state, timeout_ms):
            return True
        if attempt < retries:
            time.sleep(0.1)  # Brief pause before retry

    return False


def init_forge_ready(mcc):
    """
    Initialize FORGE_READY bits in CR0[31:29].

    Sets forge_ready=1, user_enable=1, clk_enable=1.
    This is REQUIRED for all FORGE modules to operate.

    Args:
        mcc: CloudCompile instrument instance
    """
    mcc.set_control(0, MCC_CR0_ALL_ENABLED)
    time.sleep(0.1)  # Allow control to propagate


def clear_forge_ready(mcc):
    """
    Clear FORGE_READY bits (disable module).

    Args:
        mcc: CloudCompile instrument instance
    """
    mcc.set_control(0, 0x00000000)
    time.sleep(0.1)


def arm_probe(mcc, trig_duration_us: float, intensity_duration_us: float,
              cooldown_us: float, trigger_threshold_mv: int = 950,
              trig_voltage_mv: int = 2000, intensity_voltage_mv: int = 1500):
    """
    Arm the DPD FSM with timing and voltage parameters.

    Sets Control Registers to configure FSM timing and output voltages.

    Args:
        mcc: CloudCompile instrument instance
        trig_duration_us: Trigger pulse duration (OutputA) in microseconds
        intensity_duration_us: Intensity pulse duration (OutputB) in microseconds
        cooldown_us: Cooldown interval in microseconds
        trigger_threshold_mv: Input trigger threshold (mV, default: 950)
        trig_voltage_mv: Trigger output voltage (OutputA) in mV
        intensity_voltage_mv: Intensity output voltage (OutputB) in mV
    """
    # Convert timing to clock cycles
    trig_cycles = us_to_cycles(trig_duration_us)
    intensity_cycles = us_to_cycles(intensity_duration_us)
    cooldown_cycles = us_to_cycles(cooldown_us)

    # Set timing registers
    mcc.set_control(4, trig_cycles)          # CR4: trig_out_duration
    mcc.set_control(5, intensity_cycles)     # CR5: intensity_duration
    mcc.set_control(7, cooldown_cycles)      # CR7: cooldown_interval

    # Set voltage registers (16-bit signed millivolts)
    mcc.set_control(2, (trigger_threshold_mv << 16) | (trig_voltage_mv & 0xFFFF))  # CR2
    mcc.set_control(3, intensity_voltage_mv & 0xFFFF)  # CR3

    # CRITICAL: Allow timing/voltage registers to propagate before enabling arm
    # Network register updates are asynchronous - FSM must not see arm_enable=1
    # before timing registers are valid, or it will try to arm with zero/undefined values
    time.sleep(0.2)

    # Enable arming (CR1[0] = arm_enable)
    mcc.set_control(1, 0x00000001)

    time.sleep(0.1)  # Allow FSM to transition to ARMED


def software_trigger(mcc):
    """
    Trigger FSM via software trigger (CR1[1]).

    Uses edge detection - sets bit high then low.

    Args:
        mcc: CloudCompile instrument instance
    """
    # Set sw_trigger=1, arm_enable=1 (CR1[1:0] = 0b11)
    mcc.set_control(1, 0x00000003)
    time.sleep(0.05)

    # Clear sw_trigger (edge detected), keep arm_enable
    mcc.set_control(1, 0x00000001)
    time.sleep(0.05)


def disarm_probe(mcc):
    """
    Disarm the probe (clear arm_enable).

    Args:
        mcc: CloudCompile instrument instance
    """
    mcc.set_control(1, 0x00000000)
    time.sleep(0.1)


def clear_fault(mcc):
    """
    Clear fault state using CR1[3] fault_clear edge detection.

    Args:
        mcc: CloudCompile instrument instance
    """
    # Pulse fault_clear (CR1[3])
    mcc.set_control(1, 0x00000008)
    time.sleep(0.05)
    mcc.set_control(1, 0x00000000)
    time.sleep(0.1)


def reset_fsm_to_idle(mcc, osc, timeout_ms: float = 2000) -> bool:
    """
    Reset FSM to IDLE state by clearing application control registers.

    Strategy:
    1. Enable FORGE control (global_enable=1) to allow FSM transitions
    2. Wait for undefined states (e.g. STATE_4) to auto-transition to FAULT
    3. Clear fault to transition FAULT → IDLE
    4. Clear all application registers

    CRITICAL: We must keep FORGE control (CR0) enabled throughout reset,
    otherwise the FSM cannot transition (global_enable=0 blocks FSM state changes).

    Args:
        mcc: CloudCompile instrument instance
        osc: Oscilloscope instrument instance
        timeout_ms: Timeout to wait for IDLE state (default: 2000ms)

    Returns:
        True if FSM reached IDLE, False on timeout
    """
    # Step 1: Ensure FORGE control is enabled (allows FSM transitions)
    init_forge_ready(mcc)
    time.sleep(0.1)

    # Step 2: Read current state
    current_state, voltage = read_fsm_state(osc, poll_count=5)

    # Step 3: If in undefined state (STATE_4) or FAULT, wait for auto-transition to FAULT
    if current_state in ["STATE_4", "UNKNOWN", "FAULT"] or current_state.startswith("UNKNOWN"):
        # FSM should auto-transition undefined states → FAULT via "when others"
        # Give it time to transition with global_enable=1
        time.sleep(0.3)

        # Step 4: Clear fault to transition FAULT → IDLE
        clear_fault(mcc)
        time.sleep(0.2)

    # Step 5: Clear all application control registers (CR1-CR15), but NOT CR0 (FORGE control)
    for i in range(1, 16):
        try:
            mcc.set_control(i, 0)
        except:
            pass  # Some registers may not exist

    time.sleep(0.2)

    # Step 6: Wait for IDLE state
    success = wait_for_state(osc, "IDLE", timeout_ms=timeout_ms)

    # Step 7: If still not IDLE, try fault clear one more time
    if not success:
        clear_fault(mcc)
        time.sleep(0.2)
        success = wait_for_state(osc, "IDLE", timeout_ms=500)

    return success


def validate_routing(moku, osc_slot: int = 1, cc_slot: int = 2) -> bool:
    """
    Validate that routing is configured correctly for tests.

    Expected routing:
    - Slot{cc_slot}OutC → Slot{osc_slot}InA (FSM state observation)

    Args:
        moku: MultiInstrument instance
        osc_slot: Oscilloscope slot number
        cc_slot: CloudCompile slot number

    Returns:
        True if routing is correct, False otherwise
    """
    try:
        connections = moku.get_connections()

        # Check for OutputC → OscInA connection
        required_connection = {
            'source': f'Slot{cc_slot}OutC',
            'destination': f'Slot{osc_slot}InA'
        }

        for conn in connections:
            if (conn.get('source') == required_connection['source'] and
                conn.get('destination') == required_connection['destination']):
                return True

        return False
    except Exception:
        return False


def setup_routing(moku, osc_slot: int = 1, cc_slot: int = 2):
    """
    Set up routing for DPD hardware tests.

    Routing configuration:
    - Input1 → Slot{cc_slot}InA (external trigger input)
    - Slot{cc_slot}OutB → Output2 (intensity output, visible on physical port)
    - Slot{cc_slot}OutC → Output1 (FSM debug, for external scope observation)
    - Slot{cc_slot}OutC → Slot{osc_slot}InA (FSM state monitoring for tests)

    Args:
        moku: MultiInstrument instance
        osc_slot: Oscilloscope slot number
        cc_slot: CloudCompile slot number
    """
    moku.set_connections(connections=[
        {'source': 'Input1', 'destination': f'Slot{cc_slot}InA'},         # External trigger
        {'source': f'Slot{cc_slot}OutB', 'destination': 'Output2'},       # Intensity output
        {'source': f'Slot{cc_slot}OutC', 'destination': 'Output1'},       # FSM debug (physical)
        {'source': f'Slot{cc_slot}OutC', 'destination': f'Slot{osc_slot}InA'},  # FSM state (for tests)
    ])
    time.sleep(0.2)  # Allow routing to settle

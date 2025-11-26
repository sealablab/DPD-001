"""
Hardware Test Helper Functions for Demo Probe Driver (DPD)
==========================================================

Utilities for FSM control, state reading, and oscilloscope interaction.
Uses shared infrastructure from tests/shared/.

This module provides two APIs:
1. New API (recommended): Uses DPDConfig + MokuControl for portability
2. Legacy API (backward compat): Uses direct mcc.set_control() calls

Author: Moku Instrument Forge Team
Date: 2025-11-26 (refactored to use shared infrastructure)
"""

import time
import sys
from pathlib import Path
from typing import Tuple, Optional

# Add paths for imports
TESTS_PATH = Path(__file__).parent.parent
PROJECT_ROOT = TESTS_PATH.parent
sys.path.insert(0, str(TESTS_PATH))
sys.path.insert(0, str(PROJECT_ROOT / "py_tools"))

from shared.constants import (
    STATE_VOLTAGE_MAP,
    HW_HVS_TOLERANCE_V,
    MCC_CR0_ALL_ENABLED,
    us_to_cycles,
    Timeouts,
    P2Timing,
)
from shared.control_interface import MokuControl

# Import DPDConfig for the new API
from dpd_config import DPDConfig


def decode_fsm_state(voltage: float, tolerance: float = HW_HVS_TOLERANCE_V) -> str:
    """Decode FSM state from voltage reading.

    HVS Encoding: 3277 digital units per state step (0.5V per state)
    Voltage = (digital_units / 32768) * 5V
    State voltages:
      - INITIALIZING (0): 0 units     -> 0.0V (transient)
      - IDLE (1):         3277 units  -> 0.5V
      - ARMED (2):        6554 units  -> 1.0V
      - FIRING (3):       9831 units  -> 1.5V
      - COOLDOWN (4):     13108 units -> 2.0V
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


def read_oscilloscope_voltage(osc, poll_count: int = Timeouts.OSC_POLL_COUNT,
                               poll_interval_ms: float = Timeouts.OSC_POLL_INTERVAL_MS) -> float:
    """Read voltage from oscilloscope Ch1 with averaging.

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


def read_fsm_state(osc, poll_count: int = Timeouts.OSC_POLL_COUNT,
                   poll_interval_ms: float = Timeouts.OSC_POLL_INTERVAL_MS) -> Tuple[str, float]:
    """Read current FSM state from oscilloscope Ch1 (monitoring OutputC).

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


def wait_for_state(osc, expected_state: str, timeout_ms: float = Timeouts.HW_STATE_DEFAULT_MS,
                   poll_count: int = 3, poll_interval_ms: float = 50) -> bool:
    """Poll oscilloscope until expected FSM state is reached or timeout.

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
                               timeout_ms: float = Timeouts.HW_STATE_DEFAULT_MS) -> bool:
    """Wait for FSM state with automatic retry on timeout.

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
    """Initialize FORGE_READY bits in CR0[31:29].

    Sets forge_ready=1, user_enable=1, clk_enable=1.
    This is REQUIRED for all FORGE modules to operate.

    Args:
        mcc: CloudCompile instrument instance
    """
    mcc.set_control(0, MCC_CR0_ALL_ENABLED)
    time.sleep(0.1)  # Allow control to propagate


def clear_forge_ready(mcc):
    """Clear FORGE_READY bits (disable module).

    Args:
        mcc: CloudCompile instrument instance
    """
    mcc.set_control(0, 0x00000000)
    time.sleep(0.1)


def arm_probe(mcc, trig_duration_us: float, intensity_duration_us: float,
              cooldown_us: float, trigger_threshold_mv: int = 950,
              trig_voltage_mv: int = 2000, intensity_voltage_mv: int = 1500):
    """Arm the DPD FSM with timing and voltage parameters.

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
    time.sleep(0.2)

    # Enable arming (CR1[0] = arm_enable)
    mcc.set_control(1, 0x00000001)

    time.sleep(0.1)  # Allow FSM to transition to ARMED


def software_trigger(mcc):
    """Trigger FSM via software trigger (CR1[5]).

    Uses edge detection - sets sw_trigger_enable and sw_trigger, then clears.

    Args:
        mcc: CloudCompile instrument instance
    """
    # Set arm_enable=1, sw_trigger_enable=1, sw_trigger=1 (CR1 = 0x29)
    mcc.set_control(1, 0x00000029)
    time.sleep(0.05)

    # Clear sw_trigger (edge detected), keep arm_enable and sw_trigger_enable
    mcc.set_control(1, 0x00000009)
    time.sleep(0.05)


def disarm_probe(mcc):
    """Disarm the probe (clear arm_enable).

    Args:
        mcc: CloudCompile instrument instance
    """
    mcc.set_control(1, 0x00000000)
    time.sleep(0.1)


def clear_fault(mcc):
    """Clear fault state using CR1[2] fault_clear edge detection.

    Args:
        mcc: CloudCompile instrument instance
    """
    # Pulse fault_clear (CR1[2])
    mcc.set_control(1, 0x00000004)
    time.sleep(0.05)
    mcc.set_control(1, 0x00000000)
    time.sleep(0.1)


def reset_fsm_to_idle(mcc, osc, timeout_ms: float = Timeouts.HW_STATE_DEFAULT_MS) -> bool:
    """Reset FSM to IDLE state with valid configuration.

    Strategy:
    1. Disable FORGE to freeze FSM
    2. Set valid timing configuration (FSM requires non-zero timing to reach IDLE)
    3. Clear CR1 (no arm, no trigger)
    4. Enable FORGE - FSM validates config in INITIALIZING → IDLE
    5. If in FAULT, clear fault and retry

    IMPORTANT: The FSM validates timing registers in INITIALIZING state.
    If timing values are zero, FSM goes to FAULT instead of IDLE.

    Args:
        mcc: CloudCompile instrument instance
        osc: Oscilloscope instrument instance
        timeout_ms: Timeout to wait for IDLE state (default: 2000ms)

    Returns:
        True if FSM reached IDLE, False on timeout
    """
    ctrl = create_control(mcc)

    # Step 1: Disable FORGE to freeze FSM
    ctrl.disable_forge()
    time.sleep(0.1)

    # Step 2: Set valid timing configuration (required for FSM to reach IDLE)
    # Use P2 timing defaults - FSM will FAULT if timing registers are zero
    idle_config = p2_timing_config(arm_enable=False)  # Valid timing, not armed
    ctrl.apply_config(idle_config)
    time.sleep(0.2)

    # Step 3: Enable FORGE - FSM will validate config and transition to IDLE
    ctrl.enable_forge()
    time.sleep(0.2)

    # Step 4: Wait for IDLE state
    success = wait_for_state(osc, "IDLE", timeout_ms=timeout_ms)

    # Step 5: If not IDLE (probably FAULT), clear fault and retry
    if not success:
        current_state, _ = read_fsm_state(osc, poll_count=3)
        if current_state == "FAULT" or current_state.startswith("UNKNOWN"):
            # Clear fault - FSM goes to INITIALIZING, re-validates, → IDLE
            clear_fault(mcc)
            time.sleep(0.2)
            success = wait_for_state(osc, "IDLE", timeout_ms=500)

    return success


def validate_routing(moku, osc_slot: int = 1, cc_slot: int = 2) -> bool:
    """Validate that routing is configured correctly for tests.

    Expected routing:
    - Slot{cc_slot}OutC -> Slot{osc_slot}InA (FSM state observation)

    Args:
        moku: MultiInstrument instance
        osc_slot: Oscilloscope slot number
        cc_slot: CloudCompile slot number

    Returns:
        True if routing is correct, False otherwise
    """
    try:
        connections = moku.get_connections()

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
    """Set up routing for DPD hardware tests.

    Routing configuration:
    - Input1 -> Slot{cc_slot}InA (external trigger input)
    - Slot{cc_slot}OutB -> Output2 (intensity output, visible on physical port)
    - Slot{cc_slot}OutC -> Output1 (FSM debug, for external scope observation)
    - Slot{cc_slot}OutC -> Slot{osc_slot}InA (FSM state monitoring for tests)

    Args:
        moku: MultiInstrument instance
        osc_slot: Oscilloscope slot number
        cc_slot: CloudCompile slot number
    """
    moku.set_connections(connections=[
        {'source': 'Input1', 'destination': f'Slot{cc_slot}InA'},
        {'source': f'Slot{cc_slot}OutB', 'destination': 'Output2'},
        {'source': f'Slot{cc_slot}OutC', 'destination': 'Output1'},
        {'source': f'Slot{cc_slot}OutC', 'destination': f'Slot{osc_slot}InA'},
    ])
    time.sleep(0.2)


# =============================================================================
# New API: DPDConfig + MokuControl (recommended for new tests)
# =============================================================================

def create_control(mcc) -> MokuControl:
    """Create a MokuControl interface for hardware tests.

    This provides an API identical to the simulation's CocoTBControl,
    allowing test code to be portable between sim and hardware.

    Args:
        mcc: CloudCompile instrument instance

    Returns:
        MokuControl instance

    Example:
        ctrl = create_control(mcc)
        ctrl.enable_forge()
        ctrl.apply_config(DPDConfig(arm_enable=True, ...))
    """
    return MokuControl(mcc)


def configure_and_arm_hw(mcc, osc, config: DPDConfig,
                         timeout_ms: float = Timeouts.HW_ARM_MS) -> bool:
    """Configure FSM with DPDConfig and arm (hardware version).

    This is the recommended way to set up the FSM for hardware tests.

    IMPORTANT: Config is applied BEFORE enabling FORGE to ensure the FSM
    validates with correct timing values (not zeros) in INITIALIZING state.

    Args:
        mcc: CloudCompile instrument instance
        osc: Oscilloscope instrument instance
        config: DPDConfig with timing and voltage parameters
        timeout_ms: Timeout to wait for ARMED state

    Returns:
        True if FSM reached ARMED, False on timeout

    Example:
        config = DPDConfig(
            arm_enable=True,
            trig_out_duration=us_to_cycles(100),
            intensity_duration=us_to_cycles(200),
            cooldown_interval=us_to_cycles(10),
        )
        success = configure_and_arm_hw(mcc, osc, config)
    """
    ctrl = create_control(mcc)

    # CRITICAL: Apply config FIRST (before enabling FORGE)
    # The FSM validates timing registers in INITIALIZING state.
    # If FORGE is enabled before config is set, FSM sees zeros → FAULT
    ctrl.apply_config(config)
    time.sleep(0.2)  # Allow registers to propagate through network stack

    # NOW enable FORGE - FSM will validate with correct config values
    ctrl.enable_forge()
    time.sleep(0.1)

    if config.arm_enable:
        return wait_for_state(osc, "ARMED", timeout_ms=timeout_ms)
    return True


def software_trigger_hw(mcc, osc, timeout_ms: float = Timeouts.HW_TRIGGER_MS) -> bool:
    """Trigger FSM via software trigger (hardware version).

    Uses DPDConfig for consistent register packing - no magic hex values!

    Args:
        mcc: CloudCompile instrument instance
        osc: Oscilloscope instrument instance
        timeout_ms: Timeout to wait for FIRING state

    Returns:
        True if FSM reached FIRING, False on timeout
    """
    # Create config with trigger bits
    config = DPDConfig(
        arm_enable=True,
        sw_trigger_enable=True,
        sw_trigger=True,
    )

    ctrl = create_control(mcc)
    ctrl.set_control(1, config._build_cr1())
    time.sleep(0.05)

    # Clear trigger bit (edge detected)
    clear_config = DPDConfig(
        arm_enable=True,
        sw_trigger_enable=True,
        sw_trigger=False,
    )
    ctrl.set_control(1, clear_config._build_cr1())
    time.sleep(0.05)

    return wait_for_state(osc, "FIRING", timeout_ms=timeout_ms)


def p2_timing_config(**overrides) -> DPDConfig:
    """Create DPDConfig with P2 (observable) timing for hardware tests.

    Args:
        **overrides: Fields to override (e.g., arm_enable=True)

    Returns:
        DPDConfig with P2 timing

    Example:
        config = p2_timing_config(arm_enable=True)
    """
    defaults = {
        'trig_out_duration': P2Timing.TRIG_OUT_DURATION,
        'intensity_duration': P2Timing.INTENSITY_DURATION,
        'cooldown_interval': P2Timing.COOLDOWN_INTERVAL,
    }
    defaults.update(overrides)
    return DPDConfig(**defaults)

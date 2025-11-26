"""
DPD Hardware Constants - Single Source of Truth
================================================

This file defines all hardware constants for the Demo Probe Driver (DPD)
including register bit positions, FSM states, and HVS encoding values.

IMPORTANT: This is the authoritative source for these values. Both CocoTB
simulation tests and hardware tests should import from this file.

Based on: rtl/DPD-RTL.yaml (authoritative specification)
Last updated: 2025-11-25
"""

# ==============================================================================
# CR1 - Control Register 1 Bit Positions
# ==============================================================================

class CR1:
    """Control Register 1 (Lifecycle and Trigger Controls)"""

    # FSM Lifecycle Controls
    ARM_ENABLE        = 0  # Enable arming (IDLE → ARMED transition)
    AUTO_REARM_ENABLE = 1  # Re-arm after cooldown (burst mode)
    FAULT_CLEAR       = 2  # Clear fault state (edge-detected)

    # Trigger Enable Gates (SAFETY: default=0, disabled)
    SW_TRIGGER_ENABLE = 3  # Enable software trigger path
    HW_TRIGGER_ENABLE = 4  # Enable hardware voltage trigger

    # Trigger Signal
    SW_TRIGGER        = 5  # Software trigger pulse (edge-detected)


# ==============================================================================
# FSM State Values
# ==============================================================================

class FSMState:
    """FSM state values (6-bit state_vector from DPD_main)"""

    INITIALIZING = 0x00  # Power-on initialization
    IDLE         = 0x01  # Ready to arm
    ARMED        = 0x02  # Waiting for trigger
    FIRING       = 0x03  # Pulse generation active
    COOLDOWN     = 0x04  # Thermal safety interval
    FAULT        = 0x3F  # Fault state (sticky, requires fault_clear)

    # Synchronization safe state (for network register updates)
    SYNC_SAFE    = INITIALIZING  # Configuration updates only allowed in this state


# ==============================================================================
# HVS (Hierarchical Voltage Scoring) Encoding
# ==============================================================================

class HVS:
    """HVS encoding parameters for OutputC (oscilloscope debug)"""

    # Digital units per FSM state
    DIGITAL_UNITS_PER_STATE = 3277  # ~0.5V per state @ ±5V full scale

    # Status offset range (fine-grained debugging)
    STATUS_OFFSET_MAX = 100  # ±100 digital units (±0.015V)

    # Expected OutputC values for each state (center of range)
    VOLTAGE_INITIALIZING = 0      # 0V
    VOLTAGE_IDLE         = 3277   # 0.5V
    VOLTAGE_ARMED        = 6554   # 1.0V
    VOLTAGE_FIRING       = 9831   # 1.5V
    VOLTAGE_COOLDOWN     = 13108  # 2.0V

    @staticmethod
    def digital_to_volts(digital_units: int) -> float:
        """Convert digital units to voltage (V)"""
        return (digital_units / 32768.0) * 5.0

    @staticmethod
    def volts_to_digital(voltage: float) -> int:
        """Convert voltage (V) to digital units"""
        return int((voltage / 5.0) * 32768.0)

    @staticmethod
    def state_to_digital(state: int, status_offset: int = 0) -> int:
        """Convert FSM state + status offset to digital units"""
        return (state * HVS.DIGITAL_UNITS_PER_STATE) + status_offset


# ==============================================================================
# Platform Constants
# ==============================================================================

class Platform:
    """Moku:Go platform constants"""

    CLK_FREQ_HZ = 125_000_000  # 125 MHz system clock
    CLK_PERIOD_NS = 8          # 8 ns clock period

    # ADC/DAC ranges
    DAC_MIN_MV = -5000  # -5V
    DAC_MAX_MV = 5000   # +5V
    ADC_MIN_MV = -5000
    ADC_MAX_MV = 5000

    # Digital precision
    ADC_BITS = 16
    DAC_BITS = 16


# ==============================================================================
# Default Timing Values (Clock Cycles)
# ==============================================================================

class DefaultTiming:
    """Default timing values from DPD-RTL.yaml"""

    TRIG_OUT_DURATION    = 12_500      # 100μs @ 125MHz
    INTENSITY_DURATION   = 25_000      # 200μs @ 125MHz
    TRIGGER_WAIT_TIMEOUT = 250_000_000 # 2.0s @ 125MHz
    COOLDOWN_INTERVAL    = 1_250       # 10μs @ 125MHz

    MONITOR_WINDOW_START    = 0        # 0ns (immediate)
    MONITOR_WINDOW_DURATION = 625_000  # 5ms @ 125MHz


# ==============================================================================
# Helper Functions
# ==============================================================================

def cr1_build(**kwargs) -> int:
    """
    Build CR1 register value from named parameters.

    Args:
        arm_enable: bool = False
        auto_rearm_enable: bool = False
        fault_clear: bool = False
        sw_trigger_enable: bool = False
        hw_trigger_enable: bool = False
        sw_trigger: bool = False

    Returns:
        32-bit CR1 register value

    Example:
        >>> cr1 = cr1_build(arm_enable=True, sw_trigger_enable=True)
        >>> hex(cr1)
        '0x00000009'  # bits 0 and 3 set
    """
    value = 0
    if kwargs.get('arm_enable', False):
        value |= (1 << CR1.ARM_ENABLE)
    if kwargs.get('auto_rearm_enable', False):
        value |= (1 << CR1.AUTO_REARM_ENABLE)
    if kwargs.get('fault_clear', False):
        value |= (1 << CR1.FAULT_CLEAR)
    if kwargs.get('sw_trigger_enable', False):
        value |= (1 << CR1.SW_TRIGGER_ENABLE)
    if kwargs.get('hw_trigger_enable', False):
        value |= (1 << CR1.HW_TRIGGER_ENABLE)
    if kwargs.get('sw_trigger', False):
        value |= (1 << CR1.SW_TRIGGER)
    return value


def cr1_extract(value: int) -> dict:
    """
    Extract CR1 bits into a dictionary.

    Args:
        value: 32-bit CR1 register value

    Returns:
        Dictionary with named bit values

    Example:
        >>> cr1_extract(0x00000009)
        {'arm_enable': True, 'auto_rearm_enable': False, ...}
    """
    return {
        'arm_enable':        bool(value & (1 << CR1.ARM_ENABLE)),
        'auto_rearm_enable': bool(value & (1 << CR1.AUTO_REARM_ENABLE)),
        'fault_clear':       bool(value & (1 << CR1.FAULT_CLEAR)),
        'sw_trigger_enable': bool(value & (1 << CR1.SW_TRIGGER_ENABLE)),
        'hw_trigger_enable': bool(value & (1 << CR1.HW_TRIGGER_ENABLE)),
        'sw_trigger':        bool(value & (1 << CR1.SW_TRIGGER)),
    }


# ==============================================================================
# Quick Reference
# ==============================================================================

if __name__ == "__main__":
    """Print quick reference when run as script"""
    print("DPD Hardware Constants Quick Reference")
    print("=" * 60)
    print("\nCR1 Bit Positions:")
    print(f"  [{CR1.ARM_ENABLE}] arm_enable")
    print(f"  [{CR1.AUTO_REARM_ENABLE}] auto_rearm_enable")
    print(f"  [{CR1.FAULT_CLEAR}] fault_clear")
    print(f"  [{CR1.SW_TRIGGER_ENABLE}] sw_trigger_enable (NEW - safety gate)")
    print(f"  [{CR1.HW_TRIGGER_ENABLE}] hw_trigger_enable")
    print(f"  [{CR1.SW_TRIGGER}] sw_trigger")

    print("\nFSM States:")
    for name in ['INITIALIZING', 'IDLE', 'ARMED', 'FIRING', 'COOLDOWN', 'FAULT']:
        value = getattr(FSMState, name)
        print(f"  {name:13s} = 0x{value:02X}")

    print("\nHVS Expected Voltages (OutputC):")
    for state_name, digital_value in [
        ('INITIALIZING', HVS.VOLTAGE_INITIALIZING),
        ('IDLE', HVS.VOLTAGE_IDLE),
        ('ARMED', HVS.VOLTAGE_ARMED),
        ('FIRING', HVS.VOLTAGE_FIRING),
        ('COOLDOWN', HVS.VOLTAGE_COOLDOWN),
    ]:
        volts = HVS.digital_to_volts(digital_value)
        print(f"  {state_name:13s} = {digital_value:5d} units ({volts:+.2f}V)")

    print("\nExample CR1 Build:")
    cr1 = cr1_build(arm_enable=True, sw_trigger_enable=True, sw_trigger=True)
    print(f"  cr1_build(arm_enable=True, sw_trigger_enable=True, sw_trigger=True)")
    print(f"  = 0x{cr1:08X}")
    print(f"  Bits set: {cr1_extract(cr1)}")

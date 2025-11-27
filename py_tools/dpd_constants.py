"""
DPD Hardware Constants - Single Source of Truth
================================================

This file defines all hardware constants for the Demo Probe Driver (DPD)
including register bit positions, FSM states, and HVS encoding values.

IMPORTANT: This is the authoritative source for these values. Both CocoTB
simulation tests and hardware tests should import from this file.

Based on: rtl/DPD-RTL.yaml (authoritative specification)
Version: 4.0 (API-breaking refactor)
Last updated: 2025-11-26

API Changes from v3.x:
  - CR0 now contains all lifecycle controls (arm_enable, fault_clear, sw_trigger)
  - CR1 reserved for campaign mode (future)
  - auto_rearm_enable moved to CR8[2]
  - Removed sw_trigger_enable and hw_trigger_enable (no longer needed)
"""

# ==============================================================================
# CR0 - Lifecycle Control ("RUN" + arm/trigger/fault)
# ==============================================================================

class CR0:
    """Control Register 0 - FORGE Control + Lifecycle Controls.

    Bit Layout:
      [31]   = forge_ready       (R) ─┐
      [30]   = user_enable       (U)  ├── "RUN" - FORGE safety gate
      [29]   = clk_enable        (N) ─┘
      [28]   = campaign_enable   (P) [reserved for future]
      [27:3] = reserved
      [2]    = arm_enable        (A)
      [1]    = fault_clear       (C) [edge-triggered, auto-clear]
      [0]    = sw_trigger        (T) [edge-triggered, auto-clear]

    All CRs start zeroed on Moku platform reset.
    The FSM only operates when FORGE bits [31:29] are all set (0xE0000000).
    """

    # FORGE Control Bits ("RUN")
    FORGE_READY = 31   # (R) Set by MCC after deployment
    USER_ENABLE = 30   # (U) User control enable/disable
    CLK_ENABLE  = 29   # (N) Clock gating enable

    # Campaign Control (reserved)
    CAMPAIGN_ENABLE = 28  # (P) Future: activates campaign state machine

    # Lifecycle Controls
    ARM_ENABLE  = 2    # (A) Arm FSM - enables trigger response
    FAULT_CLEAR = 1    # (C) Clear fault state (edge-triggered, auto-clear)
    SW_TRIGGER  = 0    # (T) Software trigger (edge-triggered, auto-clear)

    # Pre-computed masks
    FORGE_READY_MASK    = 1 << FORGE_READY     # 0x80000000
    USER_ENABLE_MASK    = 1 << USER_ENABLE     # 0x40000000
    CLK_ENABLE_MASK     = 1 << CLK_ENABLE      # 0x20000000
    CAMPAIGN_ENABLE_MASK = 1 << CAMPAIGN_ENABLE # 0x10000000
    ARM_ENABLE_MASK     = 1 << ARM_ENABLE      # 0x00000004
    FAULT_CLEAR_MASK    = 1 << FAULT_CLEAR     # 0x00000002
    SW_TRIGGER_MASK     = 1 << SW_TRIGGER      # 0x00000001

    # Combined "RUN" mask (all FORGE bits)
    RUN = FORGE_READY_MASK | USER_ENABLE_MASK | CLK_ENABLE_MASK  # 0xE0000000

    # Common register values
    DISABLED        = 0x00000000  # Safe default after reset
    RUN_IDLE        = RUN         # 0xE0000000: FORGE enabled, FSM idle
    RUN_ARMED       = RUN | ARM_ENABLE_MASK                      # 0xE0000004
    RUN_ARMED_TRIG  = RUN | ARM_ENABLE_MASK | SW_TRIGGER_MASK    # 0xE0000005
    RUN_FAULT_CLR   = RUN | FAULT_CLEAR_MASK                     # 0xE0000002

    # Legacy alias (for migration)
    ALL_ENABLED = RUN


# ==============================================================================
# CR1 - Campaign Control (Reserved for future)
# ==============================================================================

class CR1:
    """Control Register 1 - Campaign Control (Reserved).

    This register is reserved for future campaign mode implementation.
    Currently unused in one-off mode.

    Planned layout:
      [31] = campaign_abort  - Abort current campaign
      [30] = campaign_pause  - Pause campaign execution
      [29:0] = reserved
    """

    CAMPAIGN_ABORT = 31  # Future: abort current campaign
    CAMPAIGN_PAUSE = 30  # Future: pause campaign execution


# ==============================================================================
# CR8 - Monitor Control + Mode Configuration
# ==============================================================================

class CR8:
    """Control Register 8 - Monitor Control and Mode Configuration.

    Bit Layout:
      [31:16] = monitor_threshold_voltage (mV, signed)
      [15:3]  = reserved
      [2]     = auto_rearm_enable (B) - burst mode
      [1]     = monitor_expect_negative
      [0]     = monitor_enable
    """

    # Bit positions
    AUTO_REARM_ENABLE       = 2   # (B) Burst mode - re-arm after cooldown
    MONITOR_EXPECT_NEGATIVE = 1   # Monitor polarity
    MONITOR_ENABLE          = 0   # Enable probe feedback monitoring

    # Pre-computed masks
    AUTO_REARM_ENABLE_MASK       = 1 << AUTO_REARM_ENABLE        # 0x00000004
    MONITOR_EXPECT_NEGATIVE_MASK = 1 << MONITOR_EXPECT_NEGATIVE  # 0x00000002
    MONITOR_ENABLE_MASK          = 1 << MONITOR_ENABLE           # 0x00000001


# ==============================================================================
# FSM State Values
# ==============================================================================

class FSMState:
    """FSM state values (6-bit state_vector from DPD_main).

    State encoding matches HVS output on OutputC.
    """

    INITIALIZING = 0x00  # (I) Power-on / register validation
    IDLE         = 0x01  # (D) Ready to arm
    ARMED        = 0x02  # (A) Waiting for trigger
    FIRING       = 0x03  # (F) Pulse generation active
    COOLDOWN     = 0x04  # (C) Thermal safety interval
    FAULT        = 0x3F  # (X) Fault state (sticky, requires fault_clear)

    # Synchronization safe state (for network register updates)
    SYNC_SAFE = INITIALIZING  # Configuration updates only allowed in this state

    # State letter codes
    LETTERS = {
        INITIALIZING: 'I',
        IDLE: 'D',
        ARMED: 'A',
        FIRING: 'F',
        COOLDOWN: 'C',
        FAULT: 'X',
    }

    # State display names
    NAMES = {
        INITIALIZING: 'Initializing',
        IDLE: 'Idle',
        ARMED: 'Armed',
        FIRING: 'Firing',
        COOLDOWN: 'Cooldown',
        FAULT: 'Fault',
    }


# ==============================================================================
# HVS (Hierarchical Voltage Scaling) Encoding
# ==============================================================================

class HVS:
    """HVS encoding parameters for OutputC (oscilloscope debug).

    Hierarchical Voltage Scaling encodes FSM state as analog voltage
    for oscilloscope debugging without recompilation.

    Voltage Range: +/-5V (Moku:Go DAC range)
    Digital Range: +/-32768 (16-bit signed)
    State Step: 0.5V per state (3277 digital units)
    """

    # Platform constants
    V_MAX = 5.0           # +/-5V range
    V_MAX_MV = 5000       # +/-5000mV range
    DIGITAL_MAX = 32768   # 16-bit signed max

    # Digital units per FSM state
    DIGITAL_UNITS_PER_STATE = 3277  # ~0.5V per state @ +/-5V full scale

    # Status offset range (fine-grained debugging)
    STATUS_OFFSET_MAX = 100  # +/-100 digital units (+/-0.015V)

    # Expected OutputC values for each state (center of range)
    VOLTAGE_INITIALIZING = 0      # 0V
    VOLTAGE_IDLE         = 3277   # 0.5V
    VOLTAGE_ARMED        = 6554   # 1.0V
    VOLTAGE_FIRING       = 9831   # 1.5V
    VOLTAGE_COOLDOWN     = 13108  # 2.0V

    # State-to-voltage map (for oscilloscope observation)
    STATE_VOLTAGE_MAP = {
        "INITIALIZING": 0.0,   # State 0: 0V (transient)
        "IDLE": 0.5,           # State 1: 0.5V
        "ARMED": 1.0,          # State 2: 1.0V
        "FIRING": 1.5,         # State 3: 1.5V
        "COOLDOWN": 2.0,       # State 4: 2.0V
        "FAULT": -0.5,         # Negative voltage indicates fault
    }

    # State-to-digital map (for direct digital comparison)
    STATE_DIGITAL_MAP = {
        "INITIALIZING": VOLTAGE_INITIALIZING,
        "IDLE": VOLTAGE_IDLE,
        "ARMED": VOLTAGE_ARMED,
        "FIRING": VOLTAGE_FIRING,
        "COOLDOWN": VOLTAGE_COOLDOWN,
    }

    @staticmethod
    def digital_to_volts(digital_units: int) -> float:
        """Convert digital units to voltage (V)."""
        return (digital_units / 32768.0) * 5.0

    @staticmethod
    def volts_to_digital(voltage: float) -> int:
        """Convert voltage (V) to digital units."""
        return int((voltage / 5.0) * 32768.0)

    @staticmethod
    def mv_to_digital(millivolts: float) -> int:
        """Convert millivolts to 16-bit signed digital value."""
        return int((millivolts / HVS.V_MAX_MV) * HVS.DIGITAL_MAX)

    @staticmethod
    def digital_to_mv(digital: int) -> float:
        """Convert 16-bit signed digital value to millivolts."""
        return (digital / HVS.DIGITAL_MAX) * HVS.V_MAX_MV

    @staticmethod
    def state_to_digital(state: int, status_offset: int = 0) -> int:
        """Convert FSM state + status offset to digital units."""
        return (state * HVS.DIGITAL_UNITS_PER_STATE) + status_offset

    @staticmethod
    def decode_state_from_digital(digital: int, tolerance: int = 200) -> str:
        """Decode FSM state name from digital value."""
        if digital < -tolerance:
            return "FAULT"
        for state_name, expected_digital in HVS.STATE_DIGITAL_MAP.items():
            if abs(digital - expected_digital) <= tolerance:
                return state_name
        return f"UNKNOWN({digital})"

    @staticmethod
    def decode_state_from_voltage(voltage: float, tolerance: float = 0.30) -> str:
        """Decode FSM state name from voltage reading."""
        if voltage < -tolerance:
            return "FAULT"
        for state_name, expected_voltage in HVS.STATE_VOLTAGE_MAP.items():
            if state_name == "FAULT":
                continue
            if abs(voltage - expected_voltage) < tolerance:
                return state_name
        return f"UNKNOWN({voltage:.3f}V)"


# ==============================================================================
# Platform Constants
# ==============================================================================

class Platform:
    """Moku:Go platform constants"""

    CLK_FREQ_HZ = 125_000_000  # 125 MHz system clock
    CLK_PERIOD_NS = 8          # 8 ns clock period

    # ADC/DAC ranges
    DAC_MIN_MV = -5000
    DAC_MAX_MV = 5000
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

    TRIG_OUT_DURATION    = 12_500      # 100us @ 125MHz
    INTENSITY_DURATION   = 25_000      # 200us @ 125MHz
    TRIGGER_WAIT_TIMEOUT = 250_000_000 # 2.0s @ 125MHz
    COOLDOWN_INTERVAL    = 1_250       # 10us @ 125MHz

    MONITOR_WINDOW_START    = 0        # 0ns (immediate)
    MONITOR_WINDOW_DURATION = 625_000  # 5ms @ 125MHz


# ==============================================================================
# Helper Functions
# ==============================================================================

def cr0_build(
    forge_ready: bool = True,
    user_enable: bool = True,
    clk_enable: bool = True,
    campaign_enable: bool = False,
    arm_enable: bool = False,
    fault_clear: bool = False,
    sw_trigger: bool = False,
) -> int:
    """Build CR0 register value from named parameters.

    Args:
        forge_ready: (R) FORGE ready bit (default: True)
        user_enable: (U) User enable bit (default: True)
        clk_enable: (N) Clock enable bit (default: True)
        campaign_enable: (P) Campaign mode (default: False, reserved)
        arm_enable: (A) Arm FSM (default: False)
        fault_clear: (C) Clear fault state (default: False)
        sw_trigger: (T) Software trigger pulse (default: False)

    Returns:
        32-bit CR0 register value

    Example:
        >>> hex(cr0_build())
        '0xe0000000'  # RUN enabled, idle

        >>> hex(cr0_build(arm_enable=True))
        '0xe0000004'  # RUN + armed

        >>> hex(cr0_build(arm_enable=True, sw_trigger=True))
        '0xe0000005'  # RUN + armed + trigger
    """
    value = 0
    if forge_ready:
        value |= CR0.FORGE_READY_MASK
    if user_enable:
        value |= CR0.USER_ENABLE_MASK
    if clk_enable:
        value |= CR0.CLK_ENABLE_MASK
    if campaign_enable:
        value |= CR0.CAMPAIGN_ENABLE_MASK
    if arm_enable:
        value |= CR0.ARM_ENABLE_MASK
    if fault_clear:
        value |= CR0.FAULT_CLEAR_MASK
    if sw_trigger:
        value |= CR0.SW_TRIGGER_MASK
    return value


def cr0_extract(value: int) -> dict:
    """Extract CR0 bits into a dictionary.

    Args:
        value: 32-bit CR0 register value

    Returns:
        Dictionary with named bit values
    """
    return {
        'forge_ready': bool(value & CR0.FORGE_READY_MASK),
        'user_enable': bool(value & CR0.USER_ENABLE_MASK),
        'clk_enable': bool(value & CR0.CLK_ENABLE_MASK),
        'campaign_enable': bool(value & CR0.CAMPAIGN_ENABLE_MASK),
        'arm_enable': bool(value & CR0.ARM_ENABLE_MASK),
        'fault_clear': bool(value & CR0.FAULT_CLEAR_MASK),
        'sw_trigger': bool(value & CR0.SW_TRIGGER_MASK),
    }


def cr8_build(
    monitor_threshold_mv: int = -200,
    auto_rearm_enable: bool = False,
    monitor_expect_negative: bool = True,
    monitor_enable: bool = True,
) -> int:
    """Build CR8 register value from named parameters.

    Args:
        monitor_threshold_mv: Threshold voltage in mV (default: -200)
        auto_rearm_enable: Burst mode (default: False)
        monitor_expect_negative: Monitor polarity (default: True)
        monitor_enable: Enable monitoring (default: True)

    Returns:
        32-bit CR8 register value
    """
    # Pack threshold into upper 16 bits (signed)
    threshold_u16 = monitor_threshold_mv & 0xFFFF
    value = threshold_u16 << 16

    if auto_rearm_enable:
        value |= CR8.AUTO_REARM_ENABLE_MASK
    if monitor_expect_negative:
        value |= CR8.MONITOR_EXPECT_NEGATIVE_MASK
    if monitor_enable:
        value |= CR8.MONITOR_ENABLE_MASK

    return value


# ==============================================================================
# Quick Reference
# ==============================================================================

if __name__ == "__main__":
    """Print quick reference when run as script"""
    print("DPD Hardware Constants v4.0 Quick Reference")
    print("=" * 60)

    print("\nCR0 Bit Layout (Lifecycle Control):")
    print("  [31] forge_ready       (R) ─┐")
    print("  [30] user_enable       (U)  ├── 'RUN' - FORGE safety gate")
    print("  [29] clk_enable        (N) ─┘")
    print("  [28] campaign_enable   (P) [reserved]")
    print("  [27:3] reserved")
    print("  [2]  arm_enable        (A)")
    print("  [1]  fault_clear       (C) [edge-triggered, auto-clear]")
    print("  [0]  sw_trigger        (T) [edge-triggered, auto-clear]")

    print("\nCommon CR0 Values:")
    print(f"  0x{CR0.DISABLED:08X} = Disabled (safe default)")
    print(f"  0x{CR0.RUN_IDLE:08X} = RUN enabled, idle")
    print(f"  0x{CR0.RUN_ARMED:08X} = RUN + armed")
    print(f"  0x{CR0.RUN_ARMED_TRIG:08X} = RUN + armed + trigger")
    print(f"  0x{CR0.RUN_FAULT_CLR:08X} = RUN + fault_clear")

    print("\nCR8 Bit Layout (Monitor + Mode Config):")
    print("  [31:16] monitor_threshold_voltage (mV)")
    print("  [2]     auto_rearm_enable (B) - burst mode")
    print("  [1]     monitor_expect_negative")
    print("  [0]     monitor_enable")

    print("\nFSM States:")
    for value in [FSMState.INITIALIZING, FSMState.IDLE, FSMState.ARMED,
                  FSMState.FIRING, FSMState.COOLDOWN, FSMState.FAULT]:
        letter = FSMState.LETTERS.get(value, '?')
        name = FSMState.NAMES.get(value, 'Unknown')
        print(f"  ({letter}) {name:13s} = 0x{value:02X}")

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

    print("\nExample One-Off Workflow:")
    print("  # 1. Enable module")
    print(f"  mcc.set_control(0, 0x{CR0.RUN_IDLE:08X})  # RUN")
    print("  # 2. Configure timing (CR2-CR10)...")
    print("  # 3. Arm")
    print(f"  mcc.set_control(0, 0x{CR0.RUN_ARMED:08X})  # RUN + armed")
    print("  # 4. Fire (software trigger)")
    print(f"  mcc.set_control(0, 0x{CR0.RUN_ARMED_TRIG:08X})  # RUN + armed + trigger")
    print(f"  mcc.set_control(0, 0x{CR0.RUN_ARMED:08X})  # Clear trigger (re-arm)")

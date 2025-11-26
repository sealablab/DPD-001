"""
Debug Test Constants for FSM Spurious Trigger Investigation

Focuses on trigger path signals and timing points for debugging the spurious
ARMED → FIRING transition issue.

Author: Moku Instrument Forge Team
Date: 2025-11-25
"""

from dpd_wrapper_tests.dpd_wrapper_constants import (
    HVS_DIGITAL_ARMED,
    HVS_DIGITAL_FIRING,
    HVS_DIGITAL_TOLERANCE,
    MCC_CR0_ALL_ENABLED,
)

# =============================================================================
# Signal Names for Monitoring
# =============================================================================
# These signals are internal to DPD_shim and may need hierarchical access
# Try: dut.dpd_shim_inst.<signal_name> or fall back to inference from OutputC

TRIGGER_SIGNALS = [
    "combined_trigger",           # Final trigger to FSM (hw_trigger_out OR sw_trigger_edge)
    "hw_trigger_out",             # Hardware trigger output from voltage threshold core
    "sw_trigger_edge",            # Software trigger edge detection (1-cycle pulse)
    "hw_trigger_enable_gated",    # Gated hardware enable (global_enable AND CR1[4])
    "app_reg_hw_trigger_enable",  # CR1[4] register value (hardware trigger enable)
    "app_reg_sw_trigger",         # CR1[1] register value (software trigger)
    "ext_trigger_in",             # Input to FSM (should match combined_trigger)
    "state_reg",                  # FSM state register (in DPD_main)
]

# Signals accessible via hierarchical path (DPD_SHIM_INST in DPD.vhd)
HIERARCHICAL_SIGNAL_PATHS = {
    "combined_trigger": "dpd_shim_inst.combined_trigger",
    "hw_trigger_out": "dpd_shim_inst.hw_trigger_out",
    "sw_trigger_edge": "dpd_shim_inst.sw_trigger_edge",
    "hw_trigger_enable_gated": "dpd_shim_inst.hw_trigger_enable_gated",
    "app_reg_hw_trigger_enable": "dpd_shim_inst.app_reg_hw_trigger_enable",
    "app_reg_sw_trigger": "dpd_shim_inst.app_reg_sw_trigger",
}

# =============================================================================
# Key Timing Points for State Capture
# =============================================================================

TIMING_POINTS = {
    "RESET_ASSERTED": "Reset goes high",
    "RESET_RELEASED": "Reset goes low",
    "FORGE_ENABLED": "CR0[31:29] all set (0xE0000000)",
    "ARM_ENABLED": "CR1[0] arm_enable set",
    "IDLE_REACHED": "FSM reaches IDLE state (OutputC ≈ 3277)",
    "ARMED_REACHED": "FSM reaches ARMED state (OutputC ≈ 6554)",
    "SPURIOUS_TRIGGER": "Unexpected ARMED→FIRING transition detected",
    "FIRING_REACHED": "FSM reaches FIRING state (OutputC ≈ 9831)",
}

# =============================================================================
# Test Configuration for Debug Tests
# =============================================================================

# Monitor window: number of cycles to monitor after reaching ARMED
MONITOR_WINDOW_CYCLES = 200  # ~1.6μs @ 125MHz

# Timeout for state transitions in debug tests
DEBUG_STATE_TIMEOUT_US = 200  # More generous than production tests

# Expected values for failing scenario
EXPECTED_ARMED_VALUE = HVS_DIGITAL_ARMED
EXPECTED_FIRING_VALUE = HVS_DIGITAL_FIRING
STATE_TOLERANCE = HVS_DIGITAL_TOLERANCE

# Control register values for failing test scenario
FAILING_TEST_CR0 = MCC_CR0_ALL_ENABLED  # 0xE0000000
FAILING_TEST_CR1 = 0x00000001  # arm_enable=1, hw_trigger_enable=0, sw_trigger=0


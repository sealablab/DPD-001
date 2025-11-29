"""
Test Timeouts

Defines timeout values for test operations in simulation and hardware.
"""


class Timeouts:
    """Timeout values for test operations."""

    # Simulation timeouts (in microseconds)
    SIM_STATE_TRANSITION_US = 100
    SIM_FSM_CYCLE_US = 500

    # Hardware timeouts (in milliseconds)
    HW_RESET_MS = 500
    HW_ARM_MS = 1000
    HW_TRIGGER_MS = 1000
    HW_FSM_CYCLE_MS = 3000
    HW_STATE_DEFAULT_MS = 2000

    # Oscilloscope polling
    OSC_POLL_COUNT = 5
    OSC_POLL_INTERVAL_MS = 20

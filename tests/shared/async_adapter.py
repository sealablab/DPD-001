"""
Unified Async Adapter - BACKWARD COMPATIBILITY SHIM
===================================================

[COMPAT] This entire file is a backward compatibility shim.
         Delete once all imports updated to use tests/adapters directly.

This file now re-exports from tests/adapters/ for backward compatibility.
New code should import directly from tests/adapters.

Migration:
    OLD: from shared.async_adapter import CocoTBAsyncHarness
    NEW: from adapters import CocoTBAsyncHarness
"""

import sys
from pathlib import Path

# Add adapters to path
TESTS_PATH = Path(__file__).parent.parent
sys.path.insert(0, str(TESTS_PATH))

# Re-export everything from adapters
from adapters import (
    # Base classes
    AsyncFSMController,
    AsyncFSMStateReader,
    AsyncFSMTestHarness,
    # CocoTB
    CocoTBAsyncController,
    CocoTBAsyncStateReader,
    CocoTBAsyncHarness,
    # Moku
    MokuAsyncController,
    MokuAsyncStateReader,
    MokuAsyncHarness,
    # Factory
    get_harness,
    # Helpers
    state_to_digital,
    state_to_voltage,
    decode_state_from_digital,
)

# Re-export from adapters.base for backward compat
from adapters.base import (
    STATE_DIGITAL_MAP,
    STATE_VOLTAGE_MAP,
    CLK_FREQ_HZ,
)

# Backward compat aliases
_state_to_digital = state_to_digital
_state_to_voltage = state_to_voltage
_decode_state_from_digital = decode_state_from_digital

# Re-export HVS values for backward compat
HVS_DIGITAL_INITIALIZING = STATE_DIGITAL_MAP["INITIALIZING"]
HVS_DIGITAL_IDLE = STATE_DIGITAL_MAP["IDLE"]
HVS_DIGITAL_ARMED = STATE_DIGITAL_MAP["ARMED"]
HVS_DIGITAL_FIRING = STATE_DIGITAL_MAP["FIRING"]
HVS_DIGITAL_COOLDOWN = STATE_DIGITAL_MAP["COOLDOWN"]
HVS_VOLTAGE_MAP = STATE_VOLTAGE_MAP

# Re-export cr1_build for backward compat
from lib import cr1_build
_cr1_build = cr1_build

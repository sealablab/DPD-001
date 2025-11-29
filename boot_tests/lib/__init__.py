"""
BOOT Test Library
=================

Single import point for BOOT test constants, utilities, and configuration.
Extends the base tests/lib with BOOT-specific additions.

Usage:
    from boot_tests.lib import (
        # BOOT-specific
        CMD, BOOTState, LOADState, BOOT_HVS, LOADER_CTRL,
        build_loader_cr0, RUN, SEL, RET,
        # Shared from tests/lib
        Platform, us_to_cycles, Timeouts,
    )

Reference: py_tools/boot_constants.py (authoritative)
"""

import sys
from pathlib import Path

# Add paths for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "py_tools"))
sys.path.insert(0, str(PROJECT_ROOT / "tests"))

# Import BOOT-specific constants from py_tools
from boot_constants import (
    # RUN gate
    RUN,
    # Module select
    SEL,
    # Return control
    RET,
    # LOADER control
    LOADER_CTRL,
    # Command constants
    CMD,
    # FSM states
    BOOTState,
    LOADState,
    # HVS parameters
    BOOT_HVS,
    # BRAM parameters
    ENV_BBUF,
    # CRC-16
    CRC16,
    # LOADER timing
    LOADER_TIMING,
    # Helper functions
    build_loader_cr0,
    is_run_active,
    get_module_select,
)

# Re-export shared constants from tests/lib
from lib import (
    # Platform
    Platform,
    # Clock utilities
    s_to_cycles,
    us_to_cycles,
    ns_to_cycles,
    cycles_to_s,
    cycles_to_us,
    cycles_to_ns,
    DEFAULT_CLK_FREQ_HZ,
    # Timeouts
    Timeouts,
    # Test infrastructure
    TestLevel,
    VerbosityLevel,
    TestResult,
    TestRunnerMixin,
)

# BOOT-specific tolerances (0.2V steps are tighter than DPD's 0.5V)
BOOT_SIM_HVS_TOLERANCE = 150   # +/-150 digital units (~23mV)
BOOT_HW_HVS_TOLERANCE_V = 0.15  # +/-150mV

# BOOT state digital values (for direct comparison)
BOOT_DIGITAL_P0 = BOOT_HVS.DIGITAL_P0
BOOT_DIGITAL_P1 = BOOT_HVS.DIGITAL_P1
BOOT_DIGITAL_BIOS_ACTIVE = BOOT_HVS.DIGITAL_BIOS_ACTIVE
BOOT_DIGITAL_LOAD_ACTIVE = BOOT_HVS.DIGITAL_LOAD_ACTIVE
BOOT_DIGITAL_PROG_ACTIVE = BOOT_HVS.DIGITAL_PROG_ACTIVE

# LOADER state digital values
LOADER_DIGITAL_P0 = 0 * BOOT_HVS.UNITS_PER_STATE
LOADER_DIGITAL_P1 = 1 * BOOT_HVS.UNITS_PER_STATE
LOADER_DIGITAL_P2 = 2 * BOOT_HVS.UNITS_PER_STATE
LOADER_DIGITAL_P3 = 3 * BOOT_HVS.UNITS_PER_STATE

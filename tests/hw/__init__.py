"""
Hardware Progressive Tests for Demo Probe Driver (DPD)

Real hardware validation using Moku oscilloscope to observe FSM state transitions.
Mirrors the structure of cocotb_tests but runs on actual hardware.

Test Levels:
- P1_BASIC: 5 essential smoke tests (<2 min runtime)
- P2_INTERMEDIATE: Comprehensive validation with edge cases (future)
- P3_COMPREHENSIVE: Stress testing and corner cases (future)

Author: Moku Instrument Forge Team
Date: 2025-01-18
"""

__version__ = "1.0.0"

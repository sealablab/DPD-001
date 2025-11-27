"""
Shared Test Infrastructure for DPD
===================================

This package contains control interface abstractions for both CocoTB and Moku.

For constants and test utilities, import from tests.lib (API v4.0):
    from tests.lib import CR0, P1Timing, TestLevel, VerbosityLevel

Usage:
    from tests.shared.control_interface import CocoTBControl, MokuControl
"""

from .control_interface import (
    ControlInterface,
    CocoTBControl,
    MokuControl,
)

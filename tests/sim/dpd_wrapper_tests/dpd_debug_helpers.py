"""
Debug helpers for signal monitoring and waveform capture

Provides SignalMonitor class and utilities for capturing trigger path state
during FSM spurious trigger investigation.

Author: Moku Instrument Forge Team
Date: 2025-11-25
"""

import cocotb
from cocotb.triggers import RisingEdge, ClockCycles
from typing import Dict, List, Optional, Any
from dpd_wrapper_tests.dpd_debug_constants import HIERARCHICAL_SIGNAL_PATHS


class SignalMonitor:
    """Monitor and log signal values over time with cycle-accurate tracking"""

    def __init__(self, dut, signals: List[str], clk_signal: str = "Clk"):
        """
        Initialize signal monitor.

        Args:
            dut: Device Under Test
            signals: List of signal names to monitor
            clk_signal: Name of clock signal (default: "Clk")
        """
        self.dut = dut
        self.signals = signals
        self.clk = getattr(dut, clk_signal)
        self.history: Dict[str, List[tuple]] = {}  # {signal: [(cycle, value), ...]}
        self.current_cycle = 0
        self.monitoring = False

    async def start_monitoring(self):
        """Start background monitoring task"""
        if self.monitoring:
            return
        self.monitoring = True
        cocotb.start_soon(self._monitor_loop())

    async def stop_monitoring(self):
        """Stop monitoring (sets flag, monitor loop will exit)"""
        self.monitoring = False

    async def _monitor_loop(self):
        """Background task to sample signals every clock cycle"""
        while self.monitoring:
            await RisingEdge(self.clk)
            self.current_cycle += 1

            for sig_name in self.signals:
                try:
                    sig = self._get_signal(sig_name)
                    if sig is not None:
                        value = self._get_signal_value(sig)
                        if sig_name not in self.history:
                            self.history[sig_name] = []
                        self.history[sig_name].append((self.current_cycle, value))
                except (AttributeError, ValueError, TypeError) as e:
                    # Signal not accessible - skip silently
                    pass

    def _get_signal(self, sig_name: str) -> Optional[Any]:
        """Get signal object, trying hierarchical access if needed"""
        # Try direct access first
        if hasattr(self.dut, sig_name):
            return getattr(self.dut, sig_name)

        # Try hierarchical access
        if sig_name in HIERARCHICAL_SIGNAL_PATHS:
            path = HIERARCHICAL_SIGNAL_PATHS[sig_name]
            parts = path.split(".")
            obj = self.dut
            for part in parts:
                if hasattr(obj, part):
                    obj = getattr(obj, part)
                else:
                    return None
            return obj

        return None

    def _get_signal_value(self, sig: Any) -> Any:
        """Extract value from signal object"""
        if hasattr(sig, "value"):
            val = sig.value
            # Convert to int if possible
            if hasattr(val, "__int__"):
                try:
                    return int(val)
                except (ValueError, TypeError):
                    return str(val)
            return str(val)
        return None

    def get_signal_at_cycle(self, signal: str, cycle: int) -> Optional[Any]:
        """Get signal value at specific cycle"""
        if signal not in self.history:
            return None
        for c, v in self.history[signal]:
            if c == cycle:
                return v
        return None

    def print_transitions(self, signal: str, min_cycles: int = 0):
        """Print all transitions for a signal"""
        if signal not in self.history:
            print(f"  {signal}: Not accessible or no transitions")
            return

        prev_value = None
        transitions = []
        for cycle, value in self.history[signal]:
            if value != prev_value and cycle >= min_cycles:
                transitions.append((cycle, prev_value, value))
                prev_value = value

        if not transitions:
            print(f"  {signal}: No transitions (value={prev_value})")
        else:
            print(f"  {signal} transitions:")
            for cycle, old_val, new_val in transitions:
                print(f"    Cycle {cycle}: {old_val} → {new_val}")

    def get_last_value(self, signal: str) -> Optional[Any]:
        """Get most recent value for a signal"""
        if signal not in self.history or not self.history[signal]:
            return None
        return self.history[signal][-1][1]


async def capture_trigger_path_state(dut, context: str = ""):
    """
    Capture current state of all trigger path signals.

    Args:
        dut: Device Under Test
        context: Description of when this capture is taken
    """
    signals_to_check = [
        ("hw_trigger_out", "hw_trigger_out"),
        ("sw_trigger_edge", "sw_trigger_edge"),
        ("combined_trigger", "combined_trigger"),
        ("hw_trigger_enable_gated", "hw_trigger_enable_gated"),
        ("app_reg_hw_trigger_enable", "app_reg_hw_trigger_enable (CR1[4])"),
        ("app_reg_sw_trigger", "app_reg_sw_trigger (CR1[1])"),
    ]

    print(f"\n{'=' * 70}")
    print(f"Trigger Path State: {context}")
    print(f"{'=' * 70}")

    for sig_name, description in signals_to_check:
        try:
            # Try hierarchical access
            if sig_name in HIERARCHICAL_SIGNAL_PATHS:
                path = HIERARCHICAL_SIGNAL_PATHS[sig_name]
                parts = path.split(".")
                obj = dut
                for part in parts:
                    if hasattr(obj, part):
                        obj = getattr(obj, part)
                    else:
                        print(f"  {description:40s} = <not accessible>")
                        break
                else:
                    if hasattr(obj, "value"):
                        value = int(obj.value) if hasattr(obj.value, "__int__") else str(obj.value)
                        print(f"  {description:40s} = {value}")
                    else:
                        print(f"  {description:40s} = <no value attribute>")
            else:
                # Try direct access
                sig = getattr(dut, sig_name, None)
                if sig is not None and hasattr(sig, "value"):
                    value = int(sig.value) if hasattr(sig.value, "__int__") else str(sig.value)
                    print(f"  {description:40s} = {value}")
                else:
                    print(f"  {description:40s} = <not accessible>")
        except Exception as e:
            print(f"  {description:40s} = <error: {e}>")

    # Also check FSM state via OutputC
    try:
        output_c = int(dut.OutputC.value.to_signed())
        print(f"  {'OutputC (FSM state)':40s} = {output_c}")
    except Exception as e:
        print(f"  {'OutputC (FSM state)':40s} = <error: {e}>")

    # Check Control1 register (CR1) to verify register values
    try:
        cr1 = int(dut.Control1.value)
        hw_trigger_enable = (cr1 >> 4) & 1
        sw_trigger = (cr1 >> 1) & 1
        arm_enable = cr1 & 1
        print(f"  {'Control1 (CR1)':40s} = 0x{cr1:08X}")
        print(f"    arm_enable (bit 0)     = {arm_enable}")
        print(f"    sw_trigger (bit 1)    = {sw_trigger}")
        print(f"    hw_trigger_enable (bit 4) = {hw_trigger_enable}")
    except Exception as e:
        print(f"  {'Control1 (CR1)':40s} = <error: {e}>")

    print(f"{'=' * 70}\n")


def check_signal_accessibility(dut) -> Dict[str, bool]:
    """
    Check which signals are accessible via hierarchical or direct access.

    Returns:
        Dictionary mapping signal names to accessibility status
    """
    from dpd_wrapper_tests.dpd_debug_constants import TRIGGER_SIGNALS

    accessibility = {}
    monitor = SignalMonitor(dut, TRIGGER_SIGNALS)

    for sig_name in TRIGGER_SIGNALS:
        sig = monitor._get_signal(sig_name)
        accessibility[sig_name] = sig is not None

    return accessibility


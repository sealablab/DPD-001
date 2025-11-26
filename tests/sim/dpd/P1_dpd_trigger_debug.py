"""
Progressive Test Level 1 (P1) - FSM Trigger Debug (BASIC)

Debug test for investigating spurious ARMED → FIRING transition.
Monitors trigger path signals during the failing test_forge_control scenario.

Test Coverage:
- Signal accessibility check
- Trigger path monitoring during ARMED state
- State capture at key timing points

Expected Runtime: <5s
Expected Output: <20 lines (P1 standard)

Author: Moku Instrument Forge Team
Date: 2025-11-25
"""

import cocotb
from cocotb.triggers import ClockCycles
import sys
from pathlib import Path

# Add cocotb_tests directory to path for local test_base
COCOTB_TESTS_PATH = Path(__file__).parent.parent
if COCOTB_TESTS_PATH.exists():
    sys.path.insert(0, str(COCOTB_TESTS_PATH))

from test_base import TestBase

# Import DPD test utilities
from conftest import (
    setup_clock,
    reset_active_high,
    init_mcc_inputs,
    mcc_set_regs,
)
from dpd.constants import (
    HVS_DIGITAL_ARMED,
    HVS_DIGITAL_FIRING,
    HVS_DIGITAL_TOLERANCE,
    MCC_CR0_ALL_ENABLED,
)
from dpd.helpers import (
    read_output_c,
    wait_for_state,
)
from dpd.dpd_debug_constants import (
    TRIGGER_SIGNALS,
    FAILING_TEST_CR0,
    FAILING_TEST_CR1,
    MONITOR_WINDOW_CYCLES,
)
from dpd.dpd_debug_helpers import (
    SignalMonitor,
    capture_trigger_path_state,
    check_signal_accessibility,
)


class DPDTriggerDebugTests(TestBase):
    """P1 (BASIC) debug tests for FSM spurious trigger investigation"""

    def __init__(self, dut):
        super().__init__(dut, "dpd_trigger_debug")

    async def run_p1_basic(self):
        """P1 debug test suite entry point"""
        await setup_clock(self.dut, period_ns=8, clk_signal="Clk")
        await reset_active_high(self.dut, rst_signal="Reset", cycles=10)
        await init_mcc_inputs(self.dut)

        # Run essential debug tests
        await self.test("Signal accessibility check", self.test_signal_accessibility)
        await self.test("Trigger path monitoring", self.test_trigger_path_monitoring)

    async def test_signal_accessibility(self):
        """Check which trigger signals are accessible"""
        accessibility = check_signal_accessibility(self.dut)
        
        accessible = [sig for sig, acc in accessibility.items() if acc]
        inaccessible = [sig for sig, acc in accessibility.items() if not acc]
        
        self.dut._log.info(f"Accessible signals: {len(accessible)}/{len(accessibility)}")
        if inaccessible:
            self.dut._log.info(f"Inaccessible: {', '.join(inaccessible[:3])}...")

    async def test_trigger_path_monitoring(self):
        """Monitor trigger path during failing test_forge_control scenario"""
        # Reset and setup
        self.dut.Reset.value = 1
        await ClockCycles(self.dut.Clk, 5)
        self.dut.Reset.value = 0
        await ClockCycles(self.dut.Clk, 5)
        await init_mcc_inputs(self.dut)

        # Capture state after reset
        await capture_trigger_path_state(self.dut, "After reset release")

        # Start signal monitoring BEFORE setting registers
        monitor = SignalMonitor(self.dut, TRIGGER_SIGNALS)
        await monitor.start_monitoring()

        # Reproduce failing scenario
        self.dut._log.info("Setting Control Registers...")
        await mcc_set_regs(self.dut, {
            0: FAILING_TEST_CR0,  # 0xE0000000
            1: FAILING_TEST_CR1,  # 0x00000001 (arm_enable=1, hw_trigger_enable=0)
        })

        # Capture state immediately after register setup
        await capture_trigger_path_state(self.dut, "After register setup")

        # Poll for ARMED state with detailed logging
        self.dut._log.info("Waiting for ARMED state...")
        output_c_before = read_output_c(self.dut)
        cycles_waited = 0
        max_cycles = 12500  # 100μs timeout
        
        for cycle in range(max_cycles):
            await ClockCycles(self.dut.Clk, 1)
            cycles_waited += 1
            output_c = read_output_c(self.dut)
            
            # Check if we reached ARMED
            if abs(output_c - HVS_DIGITAL_ARMED) <= HVS_DIGITAL_TOLERANCE:
                self.dut._log.info(f"✓ Reached ARMED state at cycle {cycles_waited} (OutputC={output_c})")
                await capture_trigger_path_state(self.dut, f"At ARMED state (cycle {cycles_waited})")
                break
            
            # Check if spurious trigger occurred (went to FIRING)
            if abs(output_c - HVS_DIGITAL_FIRING) <= HVS_DIGITAL_TOLERANCE:
                self.dut._log.warning(f"⚠️ SPURIOUS TRIGGER detected at cycle {cycles_waited}!")
                self.dut._log.warning(f"   OutputC transitioned: {output_c_before} → {output_c}")
                await capture_trigger_path_state(self.dut, f"SPURIOUS TRIGGER at cycle {cycles_waited}")
                
                # Print all trigger signal transitions
                self.dut._log.info("Trigger signal transitions:")
                monitor.print_transitions("combined_trigger", min_cycles=0)
                monitor.print_transitions("hw_trigger_out", min_cycles=0)
                monitor.print_transitions("sw_trigger_edge", min_cycles=0)
                monitor.print_transitions("hw_trigger_enable_gated", min_cycles=0)
                
                # Get signal values at the moment of trigger
                trigger_cycle = cycles_waited
                self.dut._log.info(f"Signal values at cycle {trigger_cycle}:")
                for sig in ["combined_trigger", "hw_trigger_out", "sw_trigger_edge", "hw_trigger_enable_gated"]:
                    val = monitor.get_signal_at_cycle(sig, trigger_cycle)
                    if val is not None:
                        self.dut._log.info(f"  {sig} = {val}")
                
                await monitor.stop_monitoring()
                return  # Exit early - we found the issue
        
        # If we get here, either reached ARMED or timeout
        if cycles_waited >= max_cycles:
            output_c = read_output_c(self.dut)
            self.dut._log.warning(f"Timeout waiting for ARMED state. OutputC={output_c}")
            await capture_trigger_path_state(self.dut, "Timeout - final state")
        else:
            # Reached ARMED - monitor for spurious trigger
            self.dut._log.info(f"Monitoring ARMED state for {MONITOR_WINDOW_CYCLES} cycles...")
            armed_start_cycle = cycles_waited
            
            for cycle in range(MONITOR_WINDOW_CYCLES):
                await ClockCycles(self.dut.Clk, 1)
                output_c = read_output_c(self.dut)
                
                # Check if spurious trigger occurred
                if abs(output_c - HVS_DIGITAL_ARMED) > HVS_DIGITAL_TOLERANCE:
                    trigger_cycle = armed_start_cycle + cycle + 1
                    self.dut._log.warning(f"⚠️ SPURIOUS TRIGGER detected at cycle {trigger_cycle}!")
                    self.dut._log.warning(f"   OutputC: {HVS_DIGITAL_ARMED} → {output_c}")
                    await capture_trigger_path_state(self.dut, f"SPURIOUS TRIGGER at cycle {trigger_cycle}")
                    
                    # Print all trigger signal transitions
                    self.dut._log.info("Trigger signal transitions:")
                    monitor.print_transitions("combined_trigger", min_cycles=armed_start_cycle)
                    monitor.print_transitions("hw_trigger_out", min_cycles=armed_start_cycle)
                    monitor.print_transitions("sw_trigger_edge", min_cycles=armed_start_cycle)
                    monitor.print_transitions("hw_trigger_enable_gated", min_cycles=armed_start_cycle)
                    
                    # Get signal values at the moment of trigger
                    self.dut._log.info(f"Signal values at cycle {trigger_cycle}:")
                    for sig in ["combined_trigger", "hw_trigger_out", "sw_trigger_edge", "hw_trigger_enable_gated"]:
                        val = monitor.get_signal_at_cycle(sig, trigger_cycle)
                        if val is not None:
                            self.dut._log.info(f"  {sig} = {val}")
                    
                    await monitor.stop_monitoring()
                    return  # Exit early - we found the issue
        
        await monitor.stop_monitoring()
        await capture_trigger_path_state(self.dut, "After monitoring period (no spurious trigger)")


@cocotb.test()
async def test_dpd_trigger_debug_p1(dut):
    """Entry point for P1 debug tests"""
    tester = DPDTriggerDebugTests(dut)
    await tester.run_all_tests()


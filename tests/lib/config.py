"""
DPD Configuration Dataclass

Provides a structured interface for configuring the DPD instrument's
application control registers (CR1-CR10).

Note: This was moved from py_tools/dpd_config.py since it's only used by tests.
The py_tools version is kept for backward compatibility but imports from here.
"""

from dataclasses import dataclass
from typing import List, Dict

from .hw import CR0, CR1
from .clk import cycles_to_s, cycles_to_us, cycles_to_ns


@dataclass
class DPDConfig:
    """
    Configuration for Demo Probe Driver (DPD) control registers.

    All values stored in native FPGA units:
    - Timing: clock cycles (32-bit unsigned)
    - Voltage: millivolts (16-bit signed)
    - Control bits: boolean

    Register Mapping (CR1-CR10):
    - CR1[0]: arm_enable
    - CR1[1]: auto_rearm_enable
    - CR1[2]: fault_clear
    - CR1[3]: sw_trigger_enable
    - CR1[4]: hw_trigger_enable
    - CR1[5]: sw_trigger
    - CR2[31:16]: input_trigger_voltage_threshold
    - CR2[15:0]: Trigger output voltage (mV)
    - CR3[15:0]: Intensity output voltage (mV)
    - CR4[31:0]: Trigger pulse duration (clock cycles)
    - CR5[31:0]: Intensity pulse duration (clock cycles)
    - CR6[31:0]: Trigger wait timeout (clock cycles)
    - CR7[31:0]: Cooldown interval (clock cycles)
    - CR8[31:0]: Monitor control + threshold (packed)
    - CR9[31:0]: Monitor window start delay (clock cycles)
    - CR10[31:0]: Monitor window duration (clock cycles)
    """

    # Lifecycle control (CR1[0,1,2])
    arm_enable: bool = False
    auto_rearm_enable: bool = False
    fault_clear: bool = False

    # Trigger enable gates (CR1[3,4])
    sw_trigger_enable: bool = False
    hw_trigger_enable: bool = False

    # Trigger signal (CR1[5])
    sw_trigger: bool = False

    # Input trigger control (CR2[31:16])
    input_trigger_voltage_threshold: int = 950  # mV

    # Trigger output control (CR2[15:0], CR4)
    trig_out_voltage: int = 0  # mV
    trig_out_duration: int = 12500  # clock cycles (100us @ 125MHz)

    # Intensity output control (CR3, CR5)
    intensity_voltage: int = 0  # mV
    intensity_duration: int = 25000  # clock cycles (200us @ 125MHz)

    # Timing control (CR6, CR7)
    trigger_wait_timeout: int = 250000000  # clock cycles (2s @ 125MHz)
    cooldown_interval: int = 1250  # clock cycles (10us @ 125MHz)

    # Monitor/feedback (CR8, CR9, CR10)
    monitor_enable: bool = True
    monitor_expect_negative: bool = True
    monitor_threshold_voltage: int = -200  # mV
    monitor_window_start: int = 0  # clock cycles
    monitor_window_duration: int = 625000  # clock cycles (5ms @ 125MHz)

    def __post_init__(self):
        """Validate field values after initialization."""
        # Validate 16-bit signed voltages
        for field in ['input_trigger_voltage_threshold', 'trig_out_voltage',
                      'intensity_voltage', 'monitor_threshold_voltage']:
            value = getattr(self, field)
            if not (-32768 <= value <= 32767):
                raise ValueError(f"{field} = {value} exceeds 16-bit signed range")

        # Validate 32-bit unsigned timing values
        for field in ['trig_out_duration', 'intensity_duration', 'trigger_wait_timeout',
                      'cooldown_interval', 'monitor_window_start', 'monitor_window_duration']:
            value = getattr(self, field)
            if not (0 <= value <= 0xFFFFFFFF):
                raise ValueError(f"{field} = {value} exceeds 32-bit unsigned range")

    def _build_cr1(self) -> int:
        """Build CR1: Lifecycle and trigger control bits."""
        return (
            (1 if self.arm_enable else 0) << CR1.ARM_ENABLE |
            (1 if self.auto_rearm_enable else 0) << CR1.AUTO_REARM_ENABLE |
            (1 if self.fault_clear else 0) << CR1.FAULT_CLEAR |
            (1 if self.sw_trigger_enable else 0) << CR1.SW_TRIGGER_ENABLE |
            (1 if self.hw_trigger_enable else 0) << CR1.HW_TRIGGER_ENABLE |
            (1 if self.sw_trigger else 0) << CR1.SW_TRIGGER
        )

    def _build_cr2(self) -> int:
        """Build CR2: Input trigger threshold [31:16] + Trigger output voltage [15:0]."""
        return ((self.input_trigger_voltage_threshold & 0xFFFF) << 16) | (self.trig_out_voltage & 0xFFFF)

    def _build_cr3(self) -> int:
        """Build CR3: Intensity output voltage."""
        return self.intensity_voltage & 0xFFFF

    def _build_cr4(self) -> int:
        """Build CR4: Trigger pulse duration."""
        return self.trig_out_duration & 0xFFFFFFFF

    def _build_cr5(self) -> int:
        """Build CR5: Intensity pulse duration."""
        return self.intensity_duration & 0xFFFFFFFF

    def _build_cr6(self) -> int:
        """Build CR6: Trigger wait timeout."""
        return self.trigger_wait_timeout & 0xFFFFFFFF

    def _build_cr7(self) -> int:
        """Build CR7: Cooldown interval."""
        return self.cooldown_interval & 0xFFFFFFFF

    def _build_cr8(self) -> int:
        """Build CR8: Monitor control + threshold."""
        return (
            (1 if self.monitor_enable else 0) |
            ((1 if self.monitor_expect_negative else 0) << 1) |
            ((self.monitor_threshold_voltage & 0xFFFF) << 16)
        )

    def _build_cr9(self) -> int:
        """Build CR9: Monitor window start delay."""
        return self.monitor_window_start & 0xFFFFFFFF

    def _build_cr10(self) -> int:
        """Build CR10: Monitor window duration."""
        return self.monitor_window_duration & 0xFFFFFFFF

    def to_app_regs_list(self) -> List[Dict[str, int]]:
        """Convert configuration to application register list (CR1-CR10).

        Returns:
            List of {"idx": N, "value": V} dicts for CR1-CR10
        """
        return [
            {"idx": 1, "value": self._build_cr1()},
            {"idx": 2, "value": self._build_cr2()},
            {"idx": 3, "value": self._build_cr3()},
            {"idx": 4, "value": self._build_cr4()},
            {"idx": 5, "value": self._build_cr5()},
            {"idx": 6, "value": self._build_cr6()},
            {"idx": 7, "value": self._build_cr7()},
            {"idx": 8, "value": self._build_cr8()},
            {"idx": 9, "value": self._build_cr9()},
            {"idx": 10, "value": self._build_cr10()},
        ]

    def __str__(self) -> str:
        """Human-readable string representation."""
        lines = [
            "DPD Configuration:",
            "=" * 50,
            "",
            "Lifecycle Control:",
            f"  arm_enable:         {self.arm_enable}",
            f"  auto_rearm_enable:  {self.auto_rearm_enable}",
            f"  fault_clear:        {self.fault_clear}",
            "",
            "Trigger Enable Gates:",
            f"  sw_trigger_enable:  {self.sw_trigger_enable}",
            f"  hw_trigger_enable:  {self.hw_trigger_enable}",
            "",
            "Trigger Signal:",
            f"  sw_trigger:         {self.sw_trigger}",
            "",
            "Timing:",
            f"  trig_out_duration:    {cycles_to_us(self.trig_out_duration):.1f}us",
            f"  intensity_duration:   {cycles_to_us(self.intensity_duration):.1f}us",
            f"  cooldown_interval:    {cycles_to_us(self.cooldown_interval):.1f}us",
            f"  trigger_wait_timeout: {cycles_to_s(self.trigger_wait_timeout):.3f}s",
        ]
        return "\n".join(lines)

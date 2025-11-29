"""
DPD Configuration Dataclass (API v4.0)

Provides a structured interface for configuring the DPD instrument's
configuration registers (CR2-CR10).

IMPORTANT: CR0 (FORGE + lifecycle) is NOT handled by this class.
Use adapter methods instead:
  - harness.controller.enable_forge()  # CR0[31:29]
  - harness.controller.arm()           # CR0[2]
  - harness.controller.trigger()       # CR0[0]
  - harness.controller.clear_fault()   # CR0[1]

CR1 is reserved for future campaign mode.

Reference: docs/api-v4.md
"""

from dataclasses import dataclass
from typing import List, Dict

from .hw import CR8
from .clk import cycles_to_s, cycles_to_us


@dataclass
class DPDConfig:
    """
    Configuration for DPD control registers CR2-CR10.

    All values stored in native FPGA units:
    - Timing: clock cycles (32-bit unsigned)
    - Voltage: millivolts (16-bit signed)
    - Control bits: boolean

    Register Mapping (CR2-CR10 only):
    - CR2[31:16]: input_trigger_voltage_threshold (mV)
    - CR2[15:0]: trig_out_voltage (mV)
    - CR3[15:0]: intensity_voltage (mV)
    - CR4[31:0]: trig_out_duration (clock cycles)
    - CR5[31:0]: intensity_duration (clock cycles)
    - CR6[31:0]: trigger_wait_timeout (clock cycles)
    - CR7[31:0]: cooldown_interval (clock cycles)
    - CR8[31:16]: monitor_threshold_voltage (mV)
    - CR8[2]: auto_rearm_enable (burst mode)
    - CR8[1]: monitor_expect_negative
    - CR8[0]: monitor_enable
    - CR9[31:0]: monitor_window_start (clock cycles)
    - CR10[31:0]: monitor_window_duration (clock cycles)

    NOTE: CR0 (FORGE + lifecycle) and CR1 (reserved) are handled
    separately via adapter methods, not this config class.
    """

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

    # Mode control (CR8[2])
    auto_rearm_enable: bool = False  # Burst mode - re-arm after cooldown

    # Monitor/feedback (CR8[0:1,31:16], CR9, CR10)
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
        """Build CR8: Monitor control + auto_rearm_enable + threshold.

        Bit Layout:
          [31:16] = monitor_threshold_voltage (mV, signed)
          [2]     = auto_rearm_enable (burst mode)
          [1]     = monitor_expect_negative
          [0]     = monitor_enable
        """
        return (
            ((self.monitor_threshold_voltage & 0xFFFF) << 16) |
            ((1 if self.auto_rearm_enable else 0) << CR8.AUTO_REARM_ENABLE) |
            ((1 if self.monitor_expect_negative else 0) << CR8.MONITOR_EXPECT_NEGATIVE) |
            ((1 if self.monitor_enable else 0) << CR8.MONITOR_ENABLE)
        )

    def _build_cr9(self) -> int:
        """Build CR9: Monitor window start delay."""
        return self.monitor_window_start & 0xFFFFFFFF

    def _build_cr10(self) -> int:
        """Build CR10: Monitor window duration."""
        return self.monitor_window_duration & 0xFFFFFFFF

    def to_app_regs_list(self) -> List[Dict[str, int]]:
        """Convert configuration to register list (CR2-CR10 only).

        NOTE: CR0 and CR1 are NOT included. Use adapter methods for
        FORGE control and lifecycle operations.

        Returns:
            List of {"idx": N, "value": V} dicts for CR2-CR10
        """
        return [
            # CR0, CR1 intentionally omitted - handled by adapter
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
            "DPD Configuration (CR2-CR10):",
            "=" * 50,
            "",
            "Trigger Input (CR2[31:16]):",
            f"  threshold:  {self.input_trigger_voltage_threshold} mV",
            "",
            "Trigger Output (CR2[15:0], CR4):",
            f"  voltage:    {self.trig_out_voltage} mV",
            f"  duration:   {cycles_to_us(self.trig_out_duration):.1f} us",
            "",
            "Intensity Output (CR3, CR5):",
            f"  voltage:    {self.intensity_voltage} mV",
            f"  duration:   {cycles_to_us(self.intensity_duration):.1f} us",
            "",
            "Timing (CR6, CR7):",
            f"  timeout:    {cycles_to_s(self.trigger_wait_timeout):.3f} s",
            f"  cooldown:   {cycles_to_us(self.cooldown_interval):.1f} us",
            "",
            "Mode (CR8[2]):",
            f"  auto_rearm: {self.auto_rearm_enable}",
            "",
            "Monitor (CR8, CR9, CR10):",
            f"  enabled:    {self.monitor_enable}",
            f"  threshold:  {self.monitor_threshold_voltage} mV",
            f"  polarity:   {'negative' if self.monitor_expect_negative else 'positive'}",
            f"  window:     {cycles_to_us(self.monitor_window_start):.1f} - "
            f"{cycles_to_us(self.monitor_window_start + self.monitor_window_duration):.1f} us",
        ]
        return "\n".join(lines)

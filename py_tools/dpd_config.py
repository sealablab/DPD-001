"""
DPD (Demo Probe Driver) Configuration Dataclass

Provides a structured interface for configuring the DPD instrument's
application control registers (CR1-CR10).

Architecture Note:
    CR0 (FORGE control) is intentionally NOT included here. CR0 contains
    system-level control bits (forge_ready, user_enable, clk_enable) that
    are managed by the FORGE infrastructure layer, not application code.

    See: rtl/DPD_shim.vhd - CR0 bits are extracted at TOP layer and passed
    as separate signals; they never reach the application as a register.

All timing values are stored in clock cycles (native format for the FPGA).
"""

from dataclasses import dataclass
import warnings
from typing import Dict, List
from clk_utils import cycles_to_s, cycles_to_us, cycles_to_ns
from dpd_constants import CR0, CR1, FSMState, HVS, Platform, DefaultTiming


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
    - CR1[3]: sw_trigger_enable (NEW - safety gate)
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

    # Trigger enable gates (CR1[3,4]) - SAFETY: default=False (disabled)
    sw_trigger_enable: bool = False
    hw_trigger_enable: bool = False

    # Trigger signal (CR1[5])
    sw_trigger: bool = False

    # Input trigger control (CR2[31:16])
    input_trigger_voltage_threshold: int = 950  # mV, 16-bit signed (default: 0.95V)

    # Trigger output control (CR2[15:0], CR4)
    trig_out_voltage: int = 0  # mV, 16-bit signed
    trig_out_duration: int = 12500  # clock cycles (default: 100μs @ 125MHz)

    # Intensity output control (CR3, CR5)
    intensity_voltage: int = 0  # mV, 16-bit signed
    intensity_duration: int = 25000  # clock cycles (default: 200μs @ 125MHz)

    # Timing control (CR6, CR7)
    trigger_wait_timeout: int = 250000000  # clock cycles (default: 2s @ 125MHz)
    cooldown_interval: int = 1250  # clock cycles (default: 10μs @ 125MHz)

    # Monitor/feedback (CR8, CR9, CR10)
    monitor_enable: bool = True
    monitor_expect_negative: bool = True
    monitor_threshold_voltage: int = -200  # mV, 16-bit signed
    monitor_window_start: int = 0  # clock cycles
    monitor_window_duration: int = 625000  # clock cycles (default: 5μs @ 125MHz)

    def __post_init__(self):
        """Validate field values after initialization."""
        # Validate 16-bit signed voltages (-32768 to 32767)
        for field in ['input_trigger_voltage_threshold', 'trig_out_voltage', 'intensity_voltage', 'monitor_threshold_voltage']:
            value = getattr(self, field)
            if not (-32768 <= value <= 32767):
                raise ValueError(f"{field} = {value} exceeds 16-bit signed range (-32768 to 32767)")

        # Validate 32-bit unsigned timing values (0 to 4294967295)
        for field in ['trig_out_duration', 'intensity_duration', 'trigger_wait_timeout',
                      'cooldown_interval', 'monitor_window_start', 'monitor_window_duration']:
            value = getattr(self, field)
            if not (0 <= value <= 0xFFFFFFFF):
                raise ValueError(f"{field} = {value} exceeds 32-bit unsigned range (0 to 4294967295)")

    # =========================================================================
    # Private Register Building Methods
    # =========================================================================

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
        """Build CR3: Intensity output voltage (16-bit signed in lower 16 bits)."""
        return self.intensity_voltage & 0xFFFF

    def _build_cr4(self) -> int:
        """Build CR4: Trigger pulse duration (32-bit unsigned)."""
        return self.trig_out_duration & 0xFFFFFFFF

    def _build_cr5(self) -> int:
        """Build CR5: Intensity pulse duration (32-bit unsigned)."""
        return self.intensity_duration & 0xFFFFFFFF

    def _build_cr6(self) -> int:
        """Build CR6: Trigger wait timeout (32-bit unsigned)."""
        return self.trigger_wait_timeout & 0xFFFFFFFF

    def _build_cr7(self) -> int:
        """Build CR7: Cooldown interval (32-bit unsigned)."""
        return self.cooldown_interval & 0xFFFFFFFF

    def _build_cr8(self) -> int:
        """Build CR8: Monitor control + threshold (packed).

        [1:0] = control bits, [15:2] = reserved, [31:16] = threshold voltage
        """
        return (
            (1 if self.monitor_enable else 0) |
            ((1 if self.monitor_expect_negative else 0) << 1) |
            ((self.monitor_threshold_voltage & 0xFFFF) << 16)
        )

    def _build_cr9(self) -> int:
        """Build CR9: Monitor window start delay (32-bit unsigned)."""
        return self.monitor_window_start & 0xFFFFFFFF

    def _build_cr10(self) -> int:
        """Build CR10: Monitor window duration (32-bit unsigned)."""
        return self.monitor_window_duration & 0xFFFFFFFF

    # =========================================================================
    # Public API
    # =========================================================================

    def to_app_regs_list(self) -> List[Dict[str, int]]:
        """Convert configuration to application register list (CR1-CR10).

        Returns a list suitable for CloudCompile.set_controls() containing
        only application registers. CR0 (FORGE control) is intentionally
        excluded - it's a system concern managed separately.

        Returns:
            List of {"idx": N, "value": V} dicts for CR1-CR10

        Example:
            >>> config = DPDConfig(arm_enable=True, trig_out_voltage=1000)
            >>> ctrl.enable_forge()  # CR0 managed separately
            >>> ctrl.set_controls(config.to_app_regs_list())
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

    def to_control_regs_list(self) -> List[Dict[str, int]]:
        """DEPRECATED: Use to_app_regs_list() + separate FORGE control.

        This method includes CR0 which violates the architectural separation
        between FORGE system control and application configuration.

        Returns:
            List including CR0 (for backward compatibility)
        """
        warnings.warn(
            "to_control_regs_list() is deprecated. Use to_app_regs_list() "
            "and manage FORGE control (CR0) separately via enable_forge().",
            DeprecationWarning,
            stacklevel=2
        )
        return [{"idx": 0, "value": CR0.ALL_ENABLED}] + self.to_app_regs_list()

    def __str__(self) -> str:
        """
        Human-readable string representation with friendly units.

        Returns:
            Formatted string showing configuration with human-readable time units
        """
        lines = [
            "DPD Configuration:",
            "=" * 60,
            "",
            "Lifecycle Control:",
            f"  arm_enable:         {self.arm_enable}",
            f"  auto_rearm_enable:  {self.auto_rearm_enable}",
            f"  fault_clear:        {self.fault_clear}",
            "",
            "Trigger Enable Gates (SAFETY):",
            f"  sw_trigger_enable:  {self.sw_trigger_enable}",
            f"  hw_trigger_enable:  {self.hw_trigger_enable}",
            "",
            "Trigger Signal:",
            f"  sw_trigger:         {self.sw_trigger}",
            "",
            "Input Trigger:",
            f"  voltage_threshold:  {self.input_trigger_voltage_threshold} mV (hysteresis: -50mV)",
            "",
            "Trigger Output:",
            f"  voltage:            {self.trig_out_voltage} mV",
            f"  duration:           {cycles_to_ns(self.trig_out_duration):.1f} ns ({self.trig_out_duration} cycles)",
            "",
            "Intensity Output:",
            f"  voltage:            {self.intensity_voltage} mV",
            f"  duration:           {cycles_to_ns(self.intensity_duration):.1f} ns ({self.intensity_duration} cycles)",
            "",
            "Timing:",
            f"  trigger_wait_timeout: {cycles_to_s(self.trigger_wait_timeout):.3f} s ({self.trigger_wait_timeout} cycles)",
            f"  cooldown_interval:    {cycles_to_us(self.cooldown_interval):.1f} μs ({self.cooldown_interval} cycles)",
            "",
            "Monitor/Feedback:",
            f"  enable:             {self.monitor_enable}",
            f"  expect_negative:    {self.monitor_expect_negative}",
            f"  threshold_voltage:  {self.monitor_threshold_voltage} mV",
            f"  window_start:       {cycles_to_ns(self.monitor_window_start):.1f} ns ({self.monitor_window_start} cycles)",
            f"  window_duration:    {cycles_to_us(self.monitor_window_duration):.1f} μs ({self.monitor_window_duration} cycles)",
        ]
        return "\n".join(lines)


if __name__ == "__main__":
    # Example usage
    print("Creating default DPD configuration:")
    print()

    config = DPDConfig()
    print(config)
    print()

    print("=" * 60)
    print("Creating custom configuration:")
    print()

    from clk_utils import ns_to_cycles, us_to_cycles, s_to_cycles

    custom_config = DPDConfig(
        arm_enable=True,
        auto_rearm_enable=True,
        trig_out_voltage=2000,  # 2V
        trig_out_duration=ns_to_cycles(500),  # 500ns
        intensity_voltage=1500,  # 1.5V
        intensity_duration=ns_to_cycles(1000),  # 1μs
        trigger_wait_timeout=s_to_cycles(5),  # 5 seconds
        cooldown_interval=us_to_cycles(100),  # 100μs
        monitor_threshold_voltage=-500,  # -500mV
        monitor_window_duration=us_to_cycles(10),  # 10μs
    )

    print(custom_config)
    print()

    print("=" * 60)
    print("Application registers (CR1-CR10) via to_app_regs_list():")
    print()
    print("  # FORGE control (CR0) managed separately:")
    print(f"  CR0: 0x{CR0.ALL_ENABLED:08X}  (enable_forge())")
    print()
    print("  # Application configuration:")
    regs = custom_config.to_app_regs_list()
    for reg_map in regs:
        value = reg_map["value"]
        idx = reg_map["idx"]
        print(f"  CR{idx}: 0x{value:08X} ({value})")

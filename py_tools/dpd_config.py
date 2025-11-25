"""
DPD (Demo Probe Driver) Configuration Dataclass

Provides a structured interface for configuring the DPD instrument's control registers.
All timing values are stored in clock cycles (native format for the FPGA).
"""

from dataclasses import dataclass
from typing import Dict
from clk_utils import cycles_to_s, cycles_to_us, cycles_to_ns


@dataclass
class DPDConfig:
    """
    Configuration for Demo Probe Driver (DPD) control registers.

    All values stored in native FPGA units:
    - Timing: clock cycles (32-bit unsigned)
    - Voltage: millivolts (16-bit signed)
    - Control bits: boolean

    Register Mapping (CR1-CR10):
    - CR1[3:0]: Lifecycle control bits
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

    # Lifecycle control (CR1)
    arm_enable: bool = False
    sw_trigger: bool = False
    auto_rearm_enable: bool = False
    fault_clear: bool = False

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

    def to_control_regs_list(self) -> list:
        """
        Convert configuration to control register list for CloudCompile API.

        Returns:
            List of control maps (dicts with 'id' and 'value' keys),
            suitable for passing to CloudCompile.set_controls()

            Includes CR0 with FORGE_READY control bits [31:29] set high to enable module.

        Example:
            >>> config = DPDConfig(arm_enable=True, trig_out_voltage=1000)
            >>> regs = config.to_control_regs_list()
            >>> cloud_compile.set_controls(regs)
        """
        # CR0: FORGE_READY control scheme
        # Set bits [31:29] high: forge_ready=1, user_enable=1, clk_enable=1
        cr0 = (1 << 31) | (1 << 30) | (1 << 29)
        # CR1: Lifecycle control bits [3:0]
        cr1 = (
            (1 if self.arm_enable else 0) |
            ((1 if self.sw_trigger else 0) << 1) |
            ((1 if self.auto_rearm_enable else 0) << 2) |
            ((1 if self.fault_clear else 0) << 3)
        )

        # CR2: Input trigger threshold [31:16] + Trigger output voltage [15:0]
        cr2 = ((self.input_trigger_voltage_threshold & 0xFFFF) << 16) | (self.trig_out_voltage & 0xFFFF)

        # CR3: Intensity output voltage (16-bit signed in lower 16 bits)
        cr3 = self.intensity_voltage & 0xFFFF

        # CR4: Trigger pulse duration (32-bit unsigned)
        cr4 = self.trig_out_duration & 0xFFFFFFFF

        # CR5: Intensity pulse duration (32-bit unsigned)
        cr5 = self.intensity_duration & 0xFFFFFFFF

        # CR6: Trigger wait timeout (32-bit unsigned)
        cr6 = self.trigger_wait_timeout & 0xFFFFFFFF

        # CR7: Cooldown interval (32-bit unsigned)
        cr7 = self.cooldown_interval & 0xFFFFFFFF

        # CR8: Monitor control + threshold (packed)
        # [1:0] = control bits, [15:2] = reserved, [31:16] = threshold voltage
        cr8 = (
            (1 if self.monitor_enable else 0) |
            ((1 if self.monitor_expect_negative else 0) << 1) |
            ((self.monitor_threshold_voltage & 0xFFFF) << 16)
        )

        # CR9: Monitor window start delay (32-bit unsigned)
        cr9 = self.monitor_window_start & 0xFFFFFFFF

        # CR10: Monitor window duration (32-bit unsigned)
        cr10 = self.monitor_window_duration & 0xFFFFFFFF

        # Return as list of control maps for CloudCompile.set_controls()
        # CR0 included with FORGE_READY bits, then app registers CR1-CR10
        # NOTE: Key must be "idx" not "id" (discovered via diagnose_set_controls.py)
        return [
            {"idx": 0, "value": cr0},
            {"idx": 1, "value": cr1},
            {"idx": 2, "value": cr2},
            {"idx": 3, "value": cr3},
            {"idx": 4, "value": cr4},
            {"idx": 5, "value": cr5},
            {"idx": 6, "value": cr6},
            {"idx": 7, "value": cr7},
            {"idx": 8, "value": cr8},
            {"idx": 9, "value": cr9},
            {"idx": 10, "value": cr10},
        ]

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
            f"  sw_trigger:         {self.sw_trigger}",
            f"  auto_rearm_enable:  {self.auto_rearm_enable}",
            f"  fault_clear:        {self.fault_clear}",
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
    print("Control register list for set_controls():")
    print()
    regs = custom_config.to_control_regs_list()
    for reg_map in regs:
        value = reg_map["value"]
        idx = reg_map["idx"]
        print(f"  CR{idx} (idx={idx}): 0x{value:08X} ({value})")

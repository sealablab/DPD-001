# DPD Utilities - Python Interface for Demo Probe Driver

This package provides Python utilities for configuring and controlling the Demo Probe Driver (DPD) custom FPGA instrument on Moku devices.

## Overview

The DPD utilities consist of three main components:

1. **`py_tools/clk_utils.py`** - Clock cycle conversion utilities
2. **`py_tools/dpd_config.py`** - Configuration dataclass and control register interface
3. This README - Documentation and examples

## Files

### `py_tools/clk_utils.py`

Provides bidirectional conversion between human-friendly time units and FPGA clock cycles.

**Forward conversions (time → cycles):**
- `s_to_cycles(seconds)` - Seconds to clock cycles
- `us_to_cycles(microseconds)` - Microseconds to clock cycles
- `ns_to_cycles(nanoseconds)` - Nanoseconds to clock cycles

**Reverse conversions (cycles → time):**
- `cycles_to_s(cycles)` - Clock cycles to seconds
- `cycles_to_us(cycles)` - Clock cycles to microseconds
- `cycles_to_ns(cycles)` - Clock cycles to nanoseconds

**Parameters:**
- `clk_freq_hz`: Clock frequency in Hz (default: 125 MHz for Moku Go)
- `round_direction`: "up" or "down" for fractional cycles (forward conversions only)

### `py_tools/dpd_config.py`

Provides the `DPDConfig` dataclass for managing DPD control register state.

**Key Features:**
- Type-safe configuration with validation
- Automatic packing into control register format
- Human-readable string representation with friendly units
- Direct integration with Moku CloudCompile API

**Main Methods:**
- `to_control_regs_list()` - Convert to list format for `set_controls()`
- `__str__()` - Human-readable representation with time units

## Register Mapping (CR0-CR10)

| Register | Bits | Description | Units |
|----------|------|-------------|-------|
| CR0 | [31:29] | FORGE_READY control (auto-set: forge_ready, user_enable, clk_enable) | boolean |
| CR0 | [28:0] | Reserved | - |
| CR1 | [0] | arm_enable - Arm FSM (IDLE → ARMED) | boolean |
| CR1 | [1] | sw_trigger - Software trigger (ARMED → FIRING, edge-detected) | boolean |
| CR1 | [2] | auto_rearm_enable - Re-arm after cooldown (burst mode) | boolean |
| CR1 | [3] | fault_clear - Clear fault state (edge-detected) | boolean |
| CR1 | [31:4] | Reserved | - |
| CR2 | [31:16] | Input trigger voltage threshold (hardware comparator) | mV (signed 16-bit) |
| CR2 | [15:0] | Trigger output voltage | mV (signed 16-bit) |
| CR3 | [15:0] | Intensity output voltage | mV (signed 16-bit) |
| CR4 | [31:0] | Trigger pulse duration | clock cycles |
| CR5 | [31:0] | Intensity pulse duration | clock cycles |
| CR6 | [31:0] | Trigger wait timeout | clock cycles |
| CR7 | [31:0] | Cooldown interval | clock cycles |
| CR8 | [1:0] | Monitor control bits | boolean |
| CR8 | [15:2] | Reserved | - |
| CR8 | [31:16] | Monitor threshold voltage | mV (signed 16-bit) |
| CR9 | [31:0] | Monitor window start delay | clock cycles |
| CR10 | [31:0] | Monitor window duration | clock cycles |

**Note**: Configuration registers (CR2-CR10) are only propagated when FSM is in INITIALIZING state. See `N/network-register-sync.md` for details.

## Quick Start

### Basic Usage

```python
from moku.instruments import CloudCompile
from py_tools.dpd_config import DPDConfig
from py_tools.clk_utils import ns_to_cycles, us_to_cycles, s_to_cycles

# Connect to Moku device with DPD bitstream
dpd = CloudCompile('192.168.1.100', bitstream='path/to/dpd.tar.gz')

# Create configuration with human-friendly time units
config = DPDConfig(
    arm_enable=True,
    auto_rearm_enable=True,
    trig_out_voltage=2000,              # 2V
    trig_out_duration=ns_to_cycles(500),    # 500ns
    intensity_voltage=1500,             # 1.5V
    intensity_duration=ns_to_cycles(1000),  # 1μs
    trigger_wait_timeout=s_to_cycles(5),    # 5 seconds
    cooldown_interval=us_to_cycles(100),    # 100μs
    monitor_threshold_voltage=-500,     # -500mV
    monitor_window_duration=us_to_cycles(10) # 10μs
)

# View configuration in human-readable format
print(config)

# Convert to control registers and send to device
dpd.set_controls(config.to_control_regs_list())
```

### IPython Interactive Example

```python
# In IPython or Jupyter notebook
from moku.instruments import CloudCompile
from py_tools.dpd_config import DPDConfig
from py_tools.clk_utils import ns_to_cycles, us_to_cycles

# Connect to device
dpd = CloudCompile('192.168.1.100', bitstream='dpd_bitstream.tar.gz')

# Create and configure
config = DPDConfig()
config.arm_enable = True
config.trig_out_voltage = 1000  # 1V
config.trig_out_duration = ns_to_cycles(200)  # 200ns

# Inspect current settings
print(config)

# Apply to device
dpd.set_controls(config.to_control_regs_list())

# Verify settings were applied
current_regs = dpd.get_controls()
print(f"CR1 (lifecycle): 0x{current_regs[1]:08X}")
print(f"CR2 (trig voltage): {current_regs[2]} mV")
```

### Using with Application State

```python
class MyApplication:
    def __init__(self, moku_ip: str, bitstream_path: str):
        self.dpd = CloudCompile(moku_ip, bitstream=bitstream_path)
        self.config = DPDConfig()

    def configure_trigger(self, voltage_mv: int, duration_ns: float):
        """Configure trigger output parameters."""
        self.config.trig_out_voltage = voltage_mv
        self.config.trig_out_duration = ns_to_cycles(duration_ns)
        self.apply_config()

    def arm_device(self):
        """Arm the DPD for trigger."""
        self.config.arm_enable = True
        self.apply_config()

    def apply_config(self):
        """Send current configuration to device."""
        regs = self.config.to_control_regs_list()
        self.dpd.set_controls(regs)
        print(f"Applied configuration:\n{self.config}")

# Usage
app = MyApplication('192.168.1.100', 'dpd.tar.gz')
app.configure_trigger(voltage_mv=2000, duration_ns=500)
app.arm_device()
```

## Advanced Usage

### Custom Clock Frequency

If you're using a different clock frequency:

```python
from py_tools.clk_utils import ns_to_cycles

# For 100 MHz clock
custom_clk = 100_000_000
duration = ns_to_cycles(1000, clk_freq_hz=custom_clk)
```

### Rounding Control

Control rounding behavior for fractional cycles:

```python
from py_tools.clk_utils import ns_to_cycles

# Round down (default) - conservative timing
duration_down = ns_to_cycles(1.5, round_direction="down")  # 0 cycles

# Round up - ensures minimum timing met
duration_up = ns_to_cycles(1.5, round_direction="up")  # 1 cycle
```

### Validation

The `DPDConfig` class automatically validates:
- 16-bit signed voltage values (-32768 to 32767 mV)
- 32-bit unsigned timing values (0 to 4,294,967,295 cycles)

```python
# This will raise ValueError
config = DPDConfig(trig_out_voltage=50000)  # Exceeds 16-bit range
```

## Default Values

The `DPDConfig` dataclass includes safe defaults (@ 125 MHz):

- `trig_out_duration`: 12,500 cycles (100μs)
- `intensity_duration`: 25,000 cycles (200μs)
- `trigger_wait_timeout`: 250,000,000 cycles (2s)
- `cooldown_interval`: 1,250 cycles (10μs)
- `monitor_window_duration`: 625,000 cycles (5ms)
- `monitor_enable`: True
- `monitor_expect_negative`: True
- `monitor_threshold_voltage`: -200 mV

## Testing

Run the example code to verify functionality:

```bash
# Test clock utilities
python py_tools/clk_utils.py

# Test DPD configuration
python py_tools/dpd_config.py
```

## Notes

- All timing values are stored internally as clock cycles (FPGA native format)
- Human-readable display uses appropriate time units (s, μs, ns)
- The `to_control_regs_list()` method handles all bit packing automatically
- CR0 is automatically included with FORGE_READY bits [31:29] set high to enable module
- CR8 packing: bits [1:0] for control, bits [31:16] for threshold, bits [15:2] reserved
- Voltage values are in millivolts to match Moku API conventions
- **Configuration registers only update in INITIALIZING state** - use `fault_clear` to force re-initialization

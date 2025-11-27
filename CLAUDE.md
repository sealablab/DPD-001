# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Demo Probe Driver (DPD)** - A custom FPGA instrument for Moku:Go that implements a six-state FSM (Finite State Machine) for controlling probe trigger and intensity outputs. The project demonstrates the FORGE architecture pattern for Moku CloudCompile applications.

### Key Components
- **VHDL firmware** implementing a layered architecture (3-layer FORGE pattern)
- **Python utilities** for configuration and hardware testing
- **CocoTB simulation tests** for VHDL verification
- **Hardware progressive tests** for real-device validation

**Platform**: Moku:Go (125 MHz clock, ±5V analog I/O, 16-bit ADC/DAC)

## Build Commands

```bash
# Compile VHDL (order matters - dependencies first)
make compile

# Clean build artifacts
make clean
```

## Test Commands

```bash
# Run CocoTB simulation tests
cd tests/sim && python run.py

# Verbosity options
COCOTB_VERBOSITY=DEBUG python run.py
GHDL_FILTER=none python run.py  # Disable output filtering

# Hardware tests (requires live Moku device)
cd tests/hw && python run_hw_tests.py <device_ip> --bitstream path/to/dpd.tar
```

## Architecture

### Three-Layer FORGE Pattern

The DPD follows the standard FORGE architecture for Moku CloudCompile applications:

**Layer 1: TOP (DPD.vhd)**
- Extracts FORGE control bits from CR0[31:29]
- Instantiates the shim layer
- Minimal logic, mostly structural

**Layer 2: SHIM (DPD_shim.vhd)**
- Maps raw Control Registers (CR2-CR10) to friendly signal names
- Implements edge detection + pulse stretcher for CR0[1:0] (fault_clear, sw_trigger)
- Implements HVS (Hierarchical Voltage Encoding) on OutputC for FSM state observation
- **Network Register Synchronization**: Gates CR2-CR10 updates based on FSM state
- Instantiates DPD_main (application logic)

**Layer 3: MAIN (DPD_main.vhd)**
- Contains all application logic (FSM implementation)
- Completely MCC-agnostic (can be reused across platforms)
- Six-state FSM: INITIALIZING → IDLE → ARMED → FIRING → COOLDOWN (+ FAULT)
- Drives OutputA (trigger) and OutputB (intensity) based on FSM state

**Layer 3 is intentionally MCC-agnostic** for cross-platform portability.

### Key Supporting Modules

**forge_hierarchical_encoder.vhd**
- Encodes 6-bit state + 8-bit status into analog voltage for oscilloscope debugging
- Uses 3277 digital units per state (500mV steps at ±5V range)
- Sign-flips voltage when STATUS[7]=1 to indicate fault

**moku_voltage_threshold_trigger_core.vhd**
- Hardware comparator for InputA voltage triggering
- 50mV hysteresis to prevent noise re-triggering
- Feeds ext_trigger_in signal to FSM

**forge_common_pkg.vhd**
- Common types and constants for FORGE applications
- Defines FORGE_READY control scheme
- Defines STATE_SYNC_SAFE constant for register synchronization

### FSM States

The DPD FSM has six states encoded in OutputC via HVS:

| State | Binary | Value | Voltage (OutputC) | Description |
|-------|--------|-------|-------------------|-------------|
| INITIALIZING | 000000 | 0 | 0.0V | Register latch/validation (sync-safe) |
| IDLE | 000001 | 1 | 0.5V | Waiting for arm_enable |
| ARMED | 000010 | 2 | 1.0V | Waiting for trigger or timeout |
| FIRING | 000011 | 3 | 1.5V | Driving outputs (trigger + intensity pulses) |
| COOLDOWN | 000100 | 4 | 2.0V | Thermal safety delay between pulses |
| FAULT | 111111 | 63 | Negative voltage | Sticky fault state (requires fault_clear) |

**Note**: INITIALIZING is a transient state after reset or fault_clear. The FSM quickly transitions to IDLE after latching parameters.

### Network Register Synchronization

Configuration registers (CR2-CR10) are only propagated when the FSM is in INITIALIZING state. This prevents race conditions from asynchronous network register updates. See `docs/network-register-sync.md` for details.

- **Lifecycle controls (CR0[2:0])**: Always pass through (arm_enable, fault_clear, sw_trigger)
- **Configuration params (CR2-CR10)**: Only updated when state = INITIALIZING

### Control Register Mapping (v4.0)

**Authoritative reference:** `docs/api-v4.md` and `rtl/DPD-RTL.yaml`

**CR0 - Lifecycle Control (atomic operations)**
```
CR0[31:29] = FORGE "RUN" gate (R=ready, U=user, N=clock)
CR0[28]    = campaign_enable (reserved)
CR0[2]     = arm_enable (level-sensitive)
CR0[1]     = fault_clear (edge-triggered, auto-clear)
CR0[0]     = sw_trigger (edge-triggered, auto-clear)
```

**CR1** - Reserved for campaign mode

**CR2-CR10 - Configuration (sync-safe gated)**
- **CR2** - Trigger threshold [31:16] + trigger output voltage [15:0]
- **CR3** - Intensity output voltage [15:0]
- **CR4-CR7** - Timing: trigger duration, intensity duration, timeout, cooldown
- **CR8** - Monitor threshold [31:16] + auto_rearm[2] + polarity[1] + enable[0]
- **CR9-CR10** - Monitor window timing

All timing values are in **clock cycles** (125 MHz = 8ns period). Use `py_tools/clk_utils.py` for conversions.

### FORGE Control Scheme

CR0[31:29] must all be set (0xE0000000) for safe operation:
- Bit 31: `forge_ready` (set by MCC loader)
- Bit 30: `user_enable` (user control)
- Bit 29: `clk_enable` (clock gating)

**Never bypass this control!** The FSM should only operate when all three bits are set.

## Python Configuration Layer

### Clock Utilities (py_tools/clk_utils.py)

Converts between human-friendly time units and FPGA clock cycles:

```python
from py_tools.clk_utils import ns_to_cycles, us_to_cycles, s_to_cycles

# Convert time to cycles
trigger_duration = ns_to_cycles(500)  # 500ns → cycles
cooldown = us_to_cycles(100)          # 100μs → cycles
timeout = s_to_cycles(2)              # 2s → cycles

# Round fractional cycles up/down
cycles = ns_to_cycles(1.5, round_direction="up")  # Ensures minimum timing met

# Reverse conversion
time_s = cycles_to_s(12500)   # cycles → seconds
time_us = cycles_to_us(12500) # cycles → microseconds
time_ns = cycles_to_ns(12500) # cycles → nanoseconds
```

### DPD Configuration (py_tools/dpd_config.py)

Type-safe configuration with automatic register packing:

```python
from py_tools.dpd_config import DPDConfig
from py_tools.clk_utils import ns_to_cycles, us_to_cycles

# Create configuration
config = DPDConfig(
    arm_enable=True,
    trig_out_voltage=2000,                    # 2V in mV
    trig_out_duration=ns_to_cycles(500),      # 500ns
    intensity_voltage=1500,                   # 1.5V
    intensity_duration=ns_to_cycles(1000),    # 1μs
    cooldown_interval=us_to_cycles(100),      # 100μs
)

# Convert to register list for Moku API
regs = config.to_control_regs_list()

# Apply to device
from moku.instruments import CloudCompile
dpd = CloudCompile('192.168.1.100', bitstream='DPD-bits.tar')
dpd.set_controls(regs)
```

The `DPDConfig` class validates all values at initialization time and provides human-readable `__str__()` output.

## Key Conventions

**Voltages**: 16-bit signed integers in millivolts (stored directly, no conversion)

**Timing**: All timing values are raw clock cycles at 125 MHz. Use `py_tools/clk_utils.py` for conversions:
```python
from py_tools.clk_utils import us_to_cycles
cycles = us_to_cycles(100)  # 100μs → 12,500 cycles
```

**Config Generation**: Use `DPDConfig` dataclass, never hardcode register values:
```python
from py_tools.dpd_config import DPDConfig
config = DPDConfig(arm_enable=True, trig_out_voltage=2000)
regs = config.to_control_regs_list()
```

## Testing Strategy

### Progressive Test Levels

Both CocoTB and hardware tests use three progressive levels:

**P1 (BASIC)** - Fast smoke tests (~5s sim, ~2min hardware)
- Essential functionality only
- Reset behavior, FORGE control, basic FSM transitions

**P2 (INTERMEDIATE)** - Comprehensive validation (~30s sim, ~5min hardware)
- Auto-rearm, fault injection/recovery
- Edge cases and timing variations
- Network register synchronization tests

**P3 (COMPREHENSIVE)** - Stress testing (~2min sim, ~15min hardware)
- Rapid trigger cycles (100+ back-to-back)
- Concurrent trigger sources
- Register changes during operation

### CocoTB Tests vs Hardware Tests

**CocoTB Tests** (`tests/sim/`)
- Run against GHDL simulation
- Use fast P1 timing (8-16μs pulses) for simulation speed
- Direct signal access (`dut.OutputC.value.signed_integer`)
- Tolerance: ±200 digital units (~30mV equivalent)

**Hardware Tests** (`tests/hw/`)
- Run against real Moku device
- Use slower P2 timing (100-200μs pulses) for oscilloscope observability
- Oscilloscope polling with averaging (5 samples)
- Tolerance: ±300mV (accounts for ADC noise, polling latency)
- Requires Oscilloscope in slot 1, CloudCompile in slot 2
- Automatic routing validation and configuration

Both test suites verify FSM behavior via OutputC (HVS encoding) - no internal signal peeking required.

## HVS Encoding (Hierarchical Voltage Scaling)

OutputC encodes FSM state as analog voltage for oscilloscope debugging:

- **DIGITAL_UNITS_PER_STATE = 3277** (500mV steps at ±5V full scale)
- State voltages are human-readable on standard oscilloscopes at 500mV/div
- Status offset: ±100 digital units max (~15mV fine-grained debugging)
- Fault indication: Sign flip (negative voltage when STATUS[7]=1)
- Implementation: `rtl/forge_hierarchical_encoder.vhd`

This "train like you fight" approach means the same bitstream works for development debugging and production without recompilation.

**See:** [HVS Documentation](docs/hvs.md) for comprehensive details.

## Important VHDL Patterns

### FORGE Control Scheme

All FORGE applications must respect the three-bit control scheme in CR0[31:29]:

```vhdl
-- Extract from CR0
forge_ready <= Control0(31);  -- Set by loader
user_enable <= Control0(30);  -- User control
clk_enable  <= Control0(29);  -- Clock gating

-- Apply to module
Enable <= forge_ready and user_enable;
ClkEn  <= clk_enable;
```

**Never bypass this control!** The FSM should only operate when all three bits are set.

### Reset Priority

Follow the standard priority order: **Reset > ClkEn > Enable**

```vhdl
if rising_edge(Clk) then
    if Reset = '1' then
        -- Force safe state
        state <= STATE_INITIALIZING;
    elsif ClkEn = '1' then
        if Enable = '1' then
            -- Normal operation
        else
            -- Frozen (enable low)
        end if;
    end if;
end if;
```

### Edge Detection with Auto-Clear (v4.0)

Software trigger (CR0[0]) and fault_clear (CR0[1]) use **edge detection with pulse stretching**:

```vhdl
-- In shim layer (DPD_shim.vhd)
constant PULSE_WIDTH : integer := 4;  -- 32ns @ 125MHz

process(Clk)
begin
    if rising_edge(Clk) then
        -- Edge detection: capture 0→1 transition
        if sw_trigger = '1' and sw_trigger_prev = '0' then
            sw_trigger_pulse_cnt <= PULSE_WIDTH;
        elsif sw_trigger_pulse_cnt > 0 then
            sw_trigger_pulse_cnt <= sw_trigger_pulse_cnt - 1;
        end if;
        sw_trigger_prev <= sw_trigger;
    end if;
end process;

-- Stretched pulse output (held for 4 cycles regardless of input)
sw_trigger_stretched <= '1' when sw_trigger_pulse_cnt > 0 else '0';
```

This design:
1. Detects rising edge on CR0[0]
2. Stretches the pulse to 4 clock cycles (32ns)
3. Software can clear the bit immediately or leave it set
4. Eliminates timing dependencies between SW writes and HW edge detection

## Hardware Debug Workflow

When debugging FSM issues on real hardware:

1. **Verify routing** - Ensure OutputC → OscInA connection exists
2. **Check FORGE bits** - CR0[31:29] must all be '1' for operation
3. **Read FSM state** - Use oscilloscope Ch1 to read OutputC voltage
4. **Map voltage to state**:
   - 0.0V = INITIALIZING (transient)
   - 0.5V = IDLE
   - 1.0V = ARMED
   - 1.5V = FIRING
   - 2.0V = COOLDOWN
   - Negative = FAULT
5. **Check for faults** - Negative voltage indicates fault state
6. **Verify register writes** - Use `get_controls()` to confirm values propagated

**See:** [Hardware Debug Checklist](docs/hardware-debug-checklist.md) for step-by-step guide.

## Common Pitfalls

### Register Propagation Delay
After calling `set_control()`, there's a ~100ms delay before registers propagate through the Moku network stack. Hardware tests include `time.sleep(0.1)` after critical register writes (especially arm_probe).

### Network Register Synchronization
Configuration parameters (CR2-CR10) only update when FSM is in INITIALIZING state. To apply new parameters mid-operation, pulse `fault_clear` to force re-initialization.

### Uninitialized State Signal
VHDL signals must have explicit reset values. The FSM state signal MUST be initialized to INITIALIZING in the reset block, or random power-up states occur.

### HVS Voltage Tolerance
When reading OutputC with an oscilloscope, expect ±300mV tolerance due to ADC noise and polling latency. CocoTB tests use tighter ±30mV tolerance since they read digital values directly.

### FORGE Control Partial Enable
Tests must verify that the FSM does NOT operate when FORGE control is partially enabled. All three bits (forge_ready, user_enable, clk_enable) must be high.

### CR0 State Leakage Between Tests
When testing FORGE control scheme (partial vs complete enable), ensure CR0[2:0] is cleared between test phases to prevent arm_enable state leakage. Otherwise, the FSM may remain armed from a previous test. Use `CR0.RUN` (0xE0000000) to reset to a known state.

## File Organization

```
DPD-001/
├── rtl/                                 # VHDL source files
│   ├── DPD.vhd                          # Layer 1: TOP
│   ├── DPD_shim.vhd                     # Layer 2: Register mapping + HVS
│   ├── DPD_main.vhd                     # Layer 3: FSM application logic
│   ├── forge_hierarchical_encoder.vhd  # HVS encoder module
│   ├── moku_voltage_threshold_trigger_core.vhd  # Hardware trigger comparator
│   ├── forge_common_pkg.vhd            # FORGE common types
│   ├── CustomWrapper_test_stub.vhd     # Test stub entity
│   └── DPD-RTL.yaml                    # Register specification
├── py_tools/                           # Python utilities
│   ├── clk_utils.py                    # Clock cycle conversion utilities
│   ├── dpd_config.py                   # Configuration dataclass
│   └── dpd_constants.py                # Hardware constants (CR0, CR1, FSMState, HVS)
├── tests/
│   ├── shared/                         # Shared test infrastructure
│   │   ├── constants.py                # Unified test constants (imports py_tools)
│   │   ├── control_interface.py        # CocoTBControl / MokuControl abstraction
│   │   └── test_base_common.py         # Common test patterns
│   ├── sim/                            # CocoTB simulation tests
│   │   ├── run.py                      # Test runner
│   │   ├── conftest.py                 # CocoTB fixtures
│   │   ├── test_base.py                # Base test class
│   │   └── dpd/                         # DPD test package
│   │       ├── constants.py             # Sim-specific constants
│   │       ├── helpers.py               # FSM control helpers
│   │       └── P1_basic.py              # P1 test suite
│   └── hw/                             # Real hardware tests
│       ├── run_hw_tests.py             # Hardware test runner
│       ├── hw_test_base.py             # Hardware test base class
│       └── dpd/                         # DPD hardware tests
│           ├── constants.py             # HW-specific constants
│           ├── helpers.py               # FSM control + oscilloscope helpers
│           ├── P1_basic.py              # P1 hardware test suite
│           └── P2_intermediate.py       # P2 stub
├── docs/                               # Documentation
│   ├── api-v4.md                       # **API v4.0 calling convention** (START HERE)
│   ├── hvs.md                          # HVS encoding documentation
│   ├── hardware-debug-checklist.md     # Debugging guide
│   ├── network-register-sync.md        # Sync protocol documentation
│   └── ...                             # Other documentation
├── Makefile                            # Build commands
└── CLAUDE.md                           # This file
```

## References

- **API v4.0 Reference**: `docs/api-v4.md` - Authoritative SW/HW calling convention
- **Register Specification**: `rtl/DPD-RTL.yaml` - Machine-readable register spec
- **FORGE Architecture**: Not included in this repo, but referenced in Layer 1/2/3 comments
- **Moku API**: https://apis.liquidinstruments.com/
- **CocoTB**: https://docs.cocotb.org/
- **GHDL**: https://github.com/ghdl/ghdl
- **Documentation**: See `docs/` directory for comprehensive guides

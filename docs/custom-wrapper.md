# Custom Wrapper

**Last Updated:** 2025-01-28 (migrated from FORGE-V5)  
**Maintainer:** Moku Instrument Forge Team

> **Migration Note:** This document was migrated from FORGE-V5 and expanded with DPD-001-specific implementation details.  
> **See Also:** [Custom Instrument](custom-instrument.md) - Future standard that Liquid Instruments is migrating to.

---

The **Custom Wrapper** is the interface (or contract) that lets users mix-and-match instruments on the Moku platform. It is the **current standard** for Moku Cloud Compile (MCC) deployments.

**DPD-001 uses:** CustomWrapper architecture (current MCC standard)

---

## Entity Signature

**Standard CustomWrapper entity:**

```vhdl
entity CustomWrapper is
    port (
        -- Clock and Reset
        Clk    : in  std_logic;
        Reset  : in  std_logic;
        
        -- Input signals (ADC data, signed 16-bit)
        InputA : in  signed(15 downto 0);
        InputB : in  signed(15 downto 0);
        InputC : in  signed(15 downto 0);
        
        -- Output signals (DAC data, signed 16-bit)
        OutputA : out signed(15 downto 0);
        OutputB : out signed(15 downto 0);
        OutputC : out signed(15 downto 0);
        
        -- Control registers (32-bit each, from Moku platform)
        -- Note: std_logic_vector, NOT signed!
        -- Total: 16 registers (Control0-15) in standard implementation
        Control0  : in  std_logic_vector(31 downto 0);
        Control1  : in  std_logic_vector(31 downto 0);
        Control2  : in  std_logic_vector(31 downto 0);
        Control3  : in  std_logic_vector(31 downto 0);
        Control4  : in  std_logic_vector(31 downto 0);
        Control5  : in  std_logic_vector(31 downto 0);
        Control6  : in  std_logic_vector(31 downto 0);
        Control7  : in  std_logic_vector(31 downto 0);
        Control8  : in  std_logic_vector(31 downto 0);
        Control9  : in  std_logic_vector(31 downto 0);
        Control10 : in  std_logic_vector(31 downto 0);
        Control11 : in  std_logic_vector(31 downto 0);
        Control12 : in  std_logic_vector(31 downto 0);
        Control13 : in  std_logic_vector(31 downto 0);
        Control14 : in  std_logic_vector(31 downto 0);
        Control15 : in  std_logic_vector(31 downto 0)
    );
end entity CustomWrapper;
```

**Key Points:**
- **Inputs/Outputs:** `signed(15 downto 0)` - 16-bit signed integers (representing ±5V range for Moku:Go)
- **Control Registers:** `std_logic_vector(31 downto 0)` - 32-bit unsigned vectors
- **Total Registers:** 16 registers (Control0-15) in standard implementation
- **Note:** Some platforms may support Control16-31 (32 total), but DPD-001 uses 16

---

## DPD-001 Implementation

### Architecture Declaration

**File:** `rtl/DPD.vhd`

```vhdl
architecture bpd_forge of CustomWrapper is
    -- FORGE Control Signals (extracted from CR0[31:29])
    signal forge_ready  : std_logic;  -- CR0[31]
    signal user_enable : std_logic;  -- CR0[30]
    signal clk_enable  : std_logic;  -- CR0[29]
    
begin
    -- Extract FORGE control bits from Control0
    forge_ready <= Control0(31);
    user_enable <= Control0(30);
    clk_enable  <= Control0(29);
    
    -- Instantiate DPD shim layer (Layer 2)
    DPD_SHIM_INST: entity WORK.DPD_shim
        port map (
            Clk   => Clk,
            Reset => Reset,
            -- ... other signals
        );
end architecture bpd_forge;
```

### Control Register Mapping

**DPD-001 Register Usage:**

| Register | Usage | Description |
|----------|-------|-------------|
| **CR0** | FORGE Control | CR0[31:29] = FORGE control bits (forge_ready, user_enable, clk_enable) |
| **CR1** | Lifecycle Control | arm_enable, sw_trigger, auto_rearm, fault_clear, enable bits |
| **CR2** | Trigger & Output | Trigger threshold (16-bit), Output voltage (16-bit) |
| **CR3** | Intensity | Intensity voltage (16-bit signed mV) |
| **CR4-CR7** | Timing | Trigger duration, intensity duration, timeout, cooldown (clock cycles) |
| **CR8-CR10** | Monitor Config | Monitor thresholds and configuration |
| **CR11-CR15** | Unused | Reserved for future expansion |

**See:** `rtl/DPD-RTL.yaml` for complete register specification.

### FORGE Control Scheme

**CR0[31:29] - Triple-Redundant Safety Gating:**

| Bit | Signal | Purpose | Source |
|-----|--------|---------|--------|
| CR0[31] | `forge_ready` | Set by MCC loader after deployment | MCC system |
| CR0[30] | `user_enable` | User control (GUI toggle) | User interface |
| CR0[29] | `clk_enable` | Clock gating control | System control |

**Safe Operation:**
- All three bits must be set (`0xE0000000`) for normal operation
- If any bit is clear, DPD enters safe state
- This provides triple-redundant safety gating

**Implementation:**
```vhdl
-- In DPD_shim.vhd
global_enable <= forge_ready and user_enable and clk_enable;
```

---

## I/O Port Usage in DPD-001

### Physical I/O Mapping

**Input Ports:**
- **InputA:** External trigger input (hardware voltage comparator)
- **InputB:** Probe monitor feedback (ADC, ±5V)
- **InputC:** Unused (available for future use)

**Output Ports:**
- **OutputA:** Trigger output (DAC, ±5V)
- **OutputB:** Intensity output (DAC, ±5V)
- **OutputC:** FSM state debug (HVS encoding, signed 16-bit)

### HVS Encoding on OutputC

**DPD-001 uses OutputC for FSM state debugging via HVS (Hierarchical Voltage Scoring):**

**Implementation:** `rtl/DPD_shim.vhd`

```vhdl
-- HVS Encoder instantiation
HVS_ENCODER_INST: entity WORK.forge_hierarchical_encoder
    port map (
        clk           => Clk,
        reset         => Reset,
        state_vector  => fsm_state,      -- 6-bit FSM state from DPD_main
        status_vector => app_status,     -- 8-bit app status
        voltage_out   => OutputC         -- Encoded output
    );
```

**State Encoding:**
- **DIGITAL_UNITS_PER_STATE = 3277** (0.5V per state @ ±5V full scale)
- **State voltages (human-readable on scope):**
  - INITIALIZING (state 0): 0 units → 0.0V
  - IDLE (state 1): 3277 units → 0.5V
  - ARMED (state 2): 6554 units → 1.0V
  - FIRING (state 3): 9831 units → 1.5V
  - COOLDOWN (state 4): 13108 units → 2.0V
  - FAULT (status[7]=1): Negative voltage (sign flip)

**See:** [HVS Documentation](../N/HVS.md) and [Test Architecture](test-architecture/forge_hierarchical_encoder_test_design.md) for details.

---

## Testing with CustomWrapper

### Test Stub

**DPD-001 provides test stub for CocoTB:**

**File:** `rtl/CustomWrapper_test_stub.vhd`

```vhdl
entity CustomWrapper_test_stub is
    port (
        Clk     : in  std_logic;
        Reset   : in  std_logic;
        InputA  : in  signed(15 downto 0);
        InputB  : in  signed(15 downto 0);
        InputC  : in  signed(15 downto 0);
        OutputA : out signed(15 downto 0);
        OutputB : out signed(15 downto 0);
        OutputC : out signed(15 downto 0);
        Control0  : in  std_logic_vector(31 downto 0);
        -- ... Control1-15
    );
end entity;

architecture test of CustomWrapper_test_stub is
begin
    -- Instantiate DPD architecture
    DPD_INST: entity WORK.DPD(bpd_forge)
        port map (
            -- ... port mapping
        );
end architecture;
```

**Usage in Tests:**
```python
# tests/sim/dpd_wrapper_tests/P1_dpd_wrapper_basic.py

@cocotb.test()
async def test_dpd_wrapper_p1(dut):
    """P1 test entry point"""
    tester = DPDWrapperBasicTests(dut)
    await tester.run_p1_basic()
```

### Register Access in Tests

**DPD-001 helper functions for register access:**

```python
from conftest import mcc_set_regs, forge_cr0

# Set FORGE control (CR0[31:29])
await forge_cr0(dut, forge_ready=True, user_enable=True, clk_enable=True)

# Set application registers
regs = [0, 0x00010001, 0, 0, 0, 0, 0, 0, 0, 0, 0]
await mcc_set_regs(dut, regs)
```

**See:** [CocoTB Documentation](cocotb.md) for more test examples.

---

## Control Register Details

### CR0 - FORGE Control

**Bits 31:29 - FORGE Control Scheme:**
- `CR0[31]` = `forge_ready` (set by MCC loader)
- `CR0[30]` = `user_enable` (user control)
- `CR0[29]` = `clk_enable` (clock gating)

**Bits 28:0 - Reserved for future use**

### CR1 - Lifecycle Control

**DPD-001 uses CR1 for FSM lifecycle management:**

| Bit | Field | Description |
|-----|-------|-------------|
| CR1[0] | `arm_enable` | Enable arming (IDLE → ARMED) |
| CR1[1] | `sw_trigger` | Software trigger (edge detection) |
| CR1[2] | `fault_clear` | Clear fault state (edge detection) |
| CR1[3] | `sw_trigger_enable` | Enable software trigger path (safety gate) |
| CR1[4] | `hw_trigger_enable` | Enable hardware trigger path (safety gate) |
| CR1[5] | `auto_rearm` | Auto-rearm after cooldown (burst mode) |
| CR1[31:6] | Reserved | Future use |

**See:** `rtl/DPD-RTL.yaml` for complete register specification.

---

## Best Practices

### 1. FORGE Control First

**Always set FORGE control before enabling application:**
```vhdl
-- In application code
if (forge_ready = '1' and user_enable = '1' and clk_enable = '1') then
    -- Application logic here
end if;
```

### 2. Control Register Types

**Important distinction:**
- **Control Registers:** `std_logic_vector(31 downto 0)` - unsigned
- **I/O Ports:** `signed(15 downto 0)` - signed 16-bit

**When reading control registers:**
```vhdl
-- Correct: Use unsigned conversion
signal cr1_value : unsigned(31 downto 0);
cr1_value <= unsigned(Control1);

-- Wrong: Don't use signed conversion for control registers
-- cr1_value <= signed(Control1);  -- WRONG!
```

### 3. Register Bit Ordering

**DPD-001 convention:**
- LSB (bit 0) = least significant control bit
- MSB (bit 31) = most significant control bit
- FORGE control uses MSB bits (31:29) for visibility

### 4. Test Stub Usage

**Always use CustomWrapper_test_stub for CocoTB tests:**
- Provides entity declaration for simulation
- MCC provides actual entity in production builds
- Test stub matches production interface exactly

---

## Migration to Custom Instrument

**Future Consideration:** Liquid Instruments is migrating to "Custom Instrument" terminology with explicit control ports.

**When migrating:**
- CustomWrapper will remain supported (backward compatibility)
- Custom Instrument adds explicit `ClkEn` and `Enable` ports
- State/status vectors become explicit ports (not encoded in OutputC)

**See:** [Custom Instrument](custom-instrument.md) for future standard details.

---

## See Also

- [Custom Instrument](custom-instrument.md) - Future standard (migration path)
- [Moku Cloud Compile](https://liquidinstruments.com/moku-cloud-compile/) - MCC documentation
- [MCC Examples](https://github.com/liquidinstruments/moku-examples/tree/main/mcc) - Official examples
- [FORGE Control Scheme](../CLAUDE.md#forge-control-scheme) - DPD-001 FORGE implementation
- [Register Specification](../rtl/DPD-RTL.yaml) - Complete DPD-001 register mapping
- [CocoTB Testing](cocotb.md) - Testing CustomWrapper with CocoTB

---

## Migration Notes

**Source:** FORGE-V5 `/docs/FORGE-V5/N/Custom Wrapper/README.md`  
**Migration Date:** 2025-01-28  
**Changes:**
- Expanded from 29 lines to comprehensive guide
- Added DPD-001-specific implementation examples
- Documented FORGE control scheme (CR0[31:29])
- Added control register mapping details
- Included HVS encoding on OutputC
- Added testing examples with CustomWrapper_test_stub
- Documented best practices
- Added migration path notes

---

**Last Updated:** 2025-01-28  
**Maintainer:** Moku Instrument Forge Team  
**Status:** Migrated and expanded with DPD-001 examples


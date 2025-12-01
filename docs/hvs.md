---
created: 2025-11-28
modified: 2025-11-28 23:10:43
accessed: 2025-11-30 15:17:35
---
# HVS (Hierarchical Voltage Encoding Scheme)

**Last Updated:** 2025-01-28 (migrated from review_me)  
**Maintainer:** Moku Instrument Forge Team

---

## Visual Representation

```
  Visual on Oscilloscope (500mV/div recommended)

  +2.5V |
        |         ____                        <- STATE=4 (COOLDOWN) + status noise
  +2.0V |        |    |
        |   _____|    |_____                  <- STATE=3 (FIRING) + status noise
  +1.5V |  |                |
        |__|                |__               <- STATE=2 (ARMED) + status noise
  +1.0V |                                     (subtle ±15mV status "noise" around base)
        |__                                   <- STATE=1 (IDLE) + status noise
  +0.5V |
        |
   0.0V |================================     <- STATE=0 (INITIALIZING) - transient
  ----------------------------------------
  -0.5V |         ===                         <- FAULT! (negative voltage)
        |
  -1.5V |===                                  <- FAULT from STATE=3
```

**Key Properties:**
- 500mV steps = Major state transitions (human-readable at 500mV/div)
- ±15mV "noise" = 8-bit status encoded as fine-grained voltage variation
- Negative voltage = Fault condition (STATUS[7] = 1)
- Magnitude preserved = Last normal state visible even in fault

---

## What is HVS?

The **Hierarchical Voltage Encoding Scheme** packs 14 bits of FSM information (6-bit state + 8-bit app status) into a single oscilloscope channel using a clever two-level voltage encoding:

### **Level 1: Major State Transitions (500mV steps)**

Each FSM state increments the base voltage by 500mV, creating visually distinct "stairsteps":

| State | Binary | Value | Digital Units | Voltage |
|-------|--------|-------|---------------|---------|
| INITIALIZING | 000000 | 0 | 0 | 0.0V |
| IDLE | 000001 | 1 | 3277 | 0.5V |
| ARMED | 000010 | 2 | 6554 | 1.0V |
| FIRING | 000011 | 3 | 9831 | 1.5V |
| COOLDOWN | 000100 | 4 | 13108 | 2.0V |
| FAULT | 111111 | 63 | negative | negative |

This gives you clear state visibility on any oscilloscope at 500mV/div.

### **Level 2: Status "Noise" (±15mV fine detail)**

Around each base voltage, the 8-bit application status creates fine-grained variation:
- 7 bits of payload: counter values, error codes, flags
- 1 bit (STATUS[7]): fault indicator

Status bits 6:0 encode 0-127 values as 0-100 digital units offset (~15mV max), appearing as subtle "fuzzy" voltage around each state level.

### **Fault Detection: Sign Flip**

When STATUS[7]=1 (fault detected), the entire voltage goes **negative**:
- Normal: State 2 + status 0x12 → +1.014V
- Fault: State 2 + status 0x92 → **-1.014V**

The magnitude preserves the last known state, so you can debug "we were in state 2 when the fault occurred."

### **Decoding Example**

```python
voltage = 1.014  # Read from oscilloscope

state = int(voltage / 0.5)          # -> 2 (ARMED)
status_offset = (voltage - 1.0)     # -> 0.014V (14mV)
status_lower = int(14 / 0.78)       # -> 18 (0x12)
fault = voltage < 0                 # -> False
```

### **Digital Unit Conversion**

```python
# Moku:Go: ±5V full scale = ±32768 digital units
# HVS scaling: 3277 digital units per state = 500mV per state

def state_to_digital(state_value):
    return state_value * 3277

def digital_to_voltage(digital_units):
    return (digital_units / 32768) * 5.0  # Volts

# Examples:
# INITIALIZING: 0 * 3277 = 0 digital = 0.0V
# IDLE: 1 * 3277 = 3277 digital = 0.5V
# ARMED: 2 * 3277 = 6554 digital = 1.0V
# FIRING: 3 * 3277 = 9831 digital = 1.5V
# COOLDOWN: 4 * 3277 = 13108 digital = 2.0V
```

### **Why This Works**

- **Human-readable**: 500mV steps are obvious on scope at 500mV/div (no decoder needed for states)
- **Machine-decodable**: Simple arithmetic extracts full 14-bit payload
- **Zero LUTs**: Pure arithmetic in VHDL (no lookup tables)
- **Train like you fight**: Single bitstream for dev and production
- **Fault diagnosis**: Negative voltage is unmistakable error indication

### **FORGE Standard**

All FORGE applications **must** export:
- `state_vector[5:0]` - FSM state (linear encoding 0-63)
- `status_vector[7:0]` - App-specific status (bit 7 = fault)

The SHIM layer automatically encodes these into OutputC using HVS, making FSM state + status visible on any oscilloscope without special tooling.

---

## Implementation

The HVS encoder is implemented in `rtl/forge_hierarchical_encoder.vhd`:

```vhdl
-- Key parameters
DIGITAL_UNITS_PER_STATE  : integer := 3277;     -- 500mV per state @ ±5V FS
DIGITAL_UNITS_PER_STATUS : real    := 0.78125   -- ~0.012mV per status LSB

-- Encoding formula
base_value <= state_integer * DIGITAL_UNITS_PER_STATE;
status_offset <= (status_lower * 100) / 128;
combined_value <= base_value + status_offset;

-- Fault handling: sign flip when status[7] = 1
if fault_flag = '1' then
    output_value <= to_signed(-combined_value, 16);
else
    output_value <= to_signed(combined_value, 16);
end if;
```

**See:** [Test Architecture](test-architecture/forge_hierarchical_encoder_test_design.md) for comprehensive test design.

---

## Test Constants

### CocoTB Simulation Tests

From `tests/lib/hw.py` (unified test infrastructure):

```python
HVS_DIGITAL_UNITS_PER_STATE = 3277
HVS_DIGITAL_INITIALIZING = 0 * HVS_DIGITAL_UNITS_PER_STATE  # 0
HVS_DIGITAL_IDLE = 1 * HVS_DIGITAL_UNITS_PER_STATE          # 3277
HVS_DIGITAL_ARMED = 2 * HVS_DIGITAL_UNITS_PER_STATE         # 6554
HVS_DIGITAL_FIRING = 3 * HVS_DIGITAL_UNITS_PER_STATE        # 9831
HVS_DIGITAL_COOLDOWN = 4 * HVS_DIGITAL_UNITS_PER_STATE      # 13108
SIM_HVS_TOLERANCE = 200  # ±200 digital units (~30mV)
```

### Hardware Tests

From `tests/lib/hw.py`:

```python
STATE_VOLTAGE_MAP = {
    "INITIALIZING": 0.0,
    "IDLE": 0.5,
    "ARMED": 1.0,
    "FIRING": 1.5,
    "COOLDOWN": 2.0,
    "FAULT": -0.5,  # Any negative voltage
}
STATE_VOLTAGE_TOLERANCE = 0.30  # ±300mV (accounts for ADC noise)
```

---

## Related Documents

- [BOOT-HVS-state-reference.md](boot/BOOT-HVS-state-reference.md) - **Authoritative** BOOT subsystem HVS state table
- [HVS-encoding-scheme.md](HVS-encoding-scheme.md) - Pre-PROG encoding design rationale
- `rtl/forge_hierarchical_encoder.vhd` - VHDL implementation
- [Network Register Sync](network-register-sync.md) - Why INITIALIZING is state 0
- [Hardware Debug Checklist](hardware-debug-checklist.md) - Debugging with HVS voltages
- [Test Architecture](test-architecture/forge_hierarchical_encoder_test_design.md) - Comprehensive test design
- [Custom Wrapper](custom-wrapper.md) - HVS integration in CustomWrapper

---

**Last Updated:** 2025-01-28  
**Status:** Migrated from review_me, integrated into docs/


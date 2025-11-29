---
created: 2025-11-29
status: PROPOSAL
modified: 2025-11-28 22:08:50
accessed: 2025-11-28 22:09:05
---

# HVS Encoding Scheme: Pre-PROG vs PROG Bands

## Design Philosophy

The HVS encoding is split into two bands:

1. **Pre-PROG Band (BOOT/BIOS/LOADER)**: Carefully designed with number-theory properties for easy decoding and identification
2. **PROG Band**: Arbitrary - once control passes to PROG, the application can use whatever HVS encoding it wants

The Python client-side only needs to track one transition: **"did we transition from BOOT to PROG?"** After that, PROG owns the HVS encoding entirely.

## Pre-PROG Encoding Parameters

### Number-Theory Choice

We use **relatively prime parameters** for clean decoding:

- **`DIGITAL_UNITS_PER_STATE_PRE = 197`** (prime)
- **`DIGITAL_UNITS_PER_STATUS_PRE = 11`** (prime, coprime with 197)

**Properties:**
- `gcd(197, 11) = 1` → any `(S, T)` pair maps to a unique digital value
- Small, human-readable steps: 197 units ≈ 30mV per state @ ±5V FS
- Fine-grained status: 11 units ≈ 1.7mV per status LSB

### Voltage Bounds

Assuming ±5V full-scale (32768 digital units = 5V):

- **Max pre-PROG state**: `S_max = 31` (32 states: 0-31)
- **Max status**: `T_max = 7` (8 levels: 0-7)

**Maximum pre-PROG digital value:**
```
D_pre_max = 31 * 197 + 7 * 11
          = 6107 + 77
          = 6184 digital units
```

**Maximum pre-PROG voltage:**
```
V_pre_max = 5.0 * (6184 / 32768)
          ≈ 0.943 V
```

**Safety margin:** All pre-PROG states stay **comfortably under 1.0V**, leaving a clear gap before PROG.

### PROG Threshold

**Threshold for PROG detection:**
```
V_PROG_THRESHOLD = 1.0 V
D_PROG_THRESHOLD = 6554 digital units
```

**Python-side logic:**
```python
if voltage > 1.0:  # or digital > 6554
    context = PROG  # Application owns HVS encoding
else:
    context = decode_pre_prog(voltage)  # Use pre-PROG decoder
```

## Pre-PROG State Allocation

### Global State Ranges (S values)

We allocate 32 states (S = 0-31) across pre-PROG contexts:

| S Range | Context  | States | Description                                                 |
| ------- | -------- | ------ | ----------------------------------------------------------- |
| 0-7     | BOOT     | 8      | BOOT_P0, BOOT_P1, BOOT_FAULT, +5 reserved                   |
| 8-15    | BIOS     | 8      | BIOS states (diagnostics, tests, etc.)                      |
| 16-23   | LOADER   | 8      | LOAD_P0, LOAD_P1, LOAD_P2, LOAD_P3, LOAD_FAULT, +3 reserved |
| 24-31   | Reserved | 8      | Future pre-PROG contexts                                    |

### Status Bits (T values)

Each context uses `status_vector[6:0]` (7 bits = 0-127) but typically only needs a small range:

- **BOOT**: T = 0-3 (4 levels: normal, warning, error, fault)
- **BIOS**: T = 0-7 (8 levels: test IDs, progress, etc.)
- **LOADER**: T = 0-7 (8 levels: transfer progress, buffer ID, etc.)

**Note:** The encoder multiplies by 11, so even using all 127 status values would only add `127 * 11 = 1397` units, which is still within our 1.0V budget.

## Encoding Formula

**Pre-PROG encoding:**
```
D_pre = S * 197 + T * 11

where:
  S = global state (0-31)
  T = status[6:0] (0-127, but typically 0-7)
```

**Decoding (Python):**
```python
def decode_pre_prog(digital_value):
    """Decode pre-PROG HVS reading to (context, state, status)."""
    # Extract S and T using number theory
    # Since gcd(197, 11) = 1, we can solve:
    #   D = 197*S + 11*T
    #   T = (D - 197*S) / 11
    
    # Try each S value and check if T is integer
    for S in range(32):
        remainder = digital_value - (S * 197)
        if remainder >= 0 and remainder % 11 == 0:
            T = remainder // 11
            if T <= 127:  # Valid status range
                # Determine context from S
                if S <= 7:
                    context = "BOOT"
                elif S <= 15:
                    context = "BIOS"
                elif S <= 23:
                    context = "LOADER"
                else:
                    context = "RESERVED"
                return (context, S, T)
    
    return ("UNKNOWN", None, None)
```

## Context-Specific Mappings

### BOOT (S = 0-7)

| S | T | Digital | Voltage | BOOT State |
|---|---|---------|---------|------------|
| 0 | 0 | 0 | 0.0V | BOOT_P0 |
| 1 | 0 | 197 | 0.030V | BOOT_P1 |
| 2 | 0 | 394 | 0.060V | BOOT_FAULT (if status[7]=1, negated) |
| 3-7 | 0-7 | 591-1456 | 0.090-0.222V | Reserved/BOOT sub-states |

**BOOT voltage range:** 0.0V - 0.222V (with max status)

### BIOS (S = 8-15)

| S | T | Digital | Voltage | BIOS State |
|---|---|---------|---------|------------|
| 8 | 0 | 1576 | 0.240V | BIOS_ACTIVE (base) |
| 9-15 | 0-7 | 1773-3032 | 0.270-0.462V | BIOS internal states |

**BIOS voltage range:** 0.240V - 0.462V (with max status)

### LOADER (S = 16-23)

| S | T | Digital | Voltage | LOADER State |
|---|---|---------|---------|-------------|
| 16 | 0 | 3152 | 0.480V | LOAD_P0 (setup) |
| 17 | 0 | 3349 | 0.510V | LOAD_P1 (transfer) |
| 18 | 0 | 3546 | 0.541V | LOAD_P2 (validate) |
| 19 | 0 | 3743 | 0.571V | LOAD_P3 (complete) |
| 20 | 0 | 3940 | 0.601V | LOAD_FAULT (if status[7]=1, negated) |
| 21-23 | 0-7 | 4137-4604 | 0.631-0.702V | Reserved/LOADER sub-states |

**LOADER voltage range:** 0.480V - 0.702V (with max status T=7)

### Reserved (S = 24-31)

| S | T | Digital | Voltage | Description |
|---|---|---------|---------|-------------|
| 24-31 | 0-7 | 4728-6184 | 0.721-0.943V | Future pre-PROG contexts |

**Reserved voltage range:** 0.721V - 0.943V (with max status)

## PROG Encoding (Out of Scope)

Once control passes to PROG:

- **PROG can use any HVS encoding it wants**
- Common choice: `DIGITAL_UNITS_PER_STATE = 3277` (0.5V steps) for compatibility with existing DPD
- But PROG is free to use different parameters, or even a completely different encoding scheme
- The only requirement: **PROG must ensure its minimum voltage > 1.0V** to avoid ambiguity

**Example PROG encoding (DPD-style):**
```
D_prog = S_prog * 3277 + T_prog * 0.78125

where S_prog starts at some base (e.g., S_prog_min = 2)
      → D_prog_min = 2 * 3277 = 6554 (1.0V)
```

But this is **not specified** - it's up to each PROG application.

## Implementation Notes

### RTL Changes

1. **BOOT/BIOS/LOADER modules** instantiate `forge_hierarchical_encoder` with:
   ```vhdl
   generic map (
       DIGITAL_UNITS_PER_STATE  => 197,
       DIGITAL_UNITS_PER_STATUS => 11.0
   )
   ```

2. **PROG modules** (e.g., DPD_shim) can use:
   - Default generics (3277, 0.78125) for compatibility
   - Or any custom parameters they want
   - As long as minimum voltage > 1.0V

### Python Decoder

Update `py_tools/boot_constants.py` with:

```python
# Pre-PROG HVS parameters
HVS_PRE_STATE_UNITS = 197
HVS_PRE_STATUS_UNITS = 11
HVS_PROG_THRESHOLD_DIGITAL = 6554  # 1.0V @ ±5V FS
HVS_PROG_THRESHOLD_VOLTS = 1.0

def decode_hvs_context(digital_value: int) -> str:
    """Determine context from HVS reading."""
    if digital_value > HVS_PROG_THRESHOLD_DIGITAL:
        return "PROG"
    else:
        return decode_pre_prog(digital_value)[0]  # Returns context
```

## Benefits

1. **Clear separation**: Pre-PROG < 1.0V, PROG > 1.0V
2. **Easy decoding**: Number-theory properties make inversion straightforward
3. **Room for expansion**: 32 states × 128 status levels = plenty of headroom
4. **PROG freedom**: Applications can use any encoding they want
5. **Human-readable**: 30mV steps are easily visible on oscilloscope
6. **No collisions**: Relatively prime parameters ensure unique mappings

## Migration Path

1. Update `forge_common_pkg.vhd` with pre-PROG constants
2. Update `B0_BOOT_TOP.vhd` to use pre-PROG encoder parameters
3. Update `L2_BUFF_LOADER.vhd` to use pre-PROG encoder with S=12-23
4. Update `boot_constants.py` with decoder functions
5. Update `boot_shell.py` HVS monitor to use new decoder
6. Update tests to use new expected values
7. Leave PROG (DPD) unchanged - it already uses >1.0V range


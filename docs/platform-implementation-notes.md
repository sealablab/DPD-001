# Platform Implementation Notes

**Last Updated:** 2025-01-28 (migrated from FORGE-V5)  
**Maintainer:** Moku Instrument Forge Team

> **⚠️ IMPORTANT:** Platform specifications are in `libs/moku-models-v4/` (Pydantic models).  
> **This document contains implementation strategy notes only** - design decisions and recommendations for working with Moku platforms.

---

## Source of Truth

**Platform Specifications:** `libs/moku-models-v4/moku_models/platforms/`

The Pydantic models in `moku-models-v4` are the **authoritative source** for:
- Platform hardware specifications
- ADC/DAC resolutions and sample rates
- I/O channel counts
- Clock frequencies
- Digital I/O capabilities

**This document provides:**
- Implementation strategy recommendations
- Design decision rationale
- Answers to common implementation questions
- Notes on platform differences and how to handle them

---

## Implementation Strategy Notes

### Voltage Range Handling

**Recommendation:** All platforms except Moku:Go support **switchable voltage ranges**.

**Platform Differences:**
- **Moku:Go:** Fixed ranges (±25 V input, ±5 V output)
- **Moku:Lab:** 2 input ranges (1 Vpp, 10 Vpp)
- **Moku:Pro:** 3 input ranges (400 mVpp, 4 Vpp, 40 Vpp)
- **Moku:Delta:** 4 input ranges (100 mVpp, 1 Vpp, 10 Vpp, 40 Vpp)

**Implementation Strategy:**
- **For first pass:** Use **maximum range** as default
  - Go: 50 Vpp (±25 V) input, 10 Vpp (±5 V) output
  - Lab: 10 Vpp input, 2 Vpp output
  - Pro: 40 Vpp input, 10 Vpp output (±5 V up to 100 MHz)
  - Delta: 40 Vpp input, 10 Vpp output (±5 V up to 100 MHz)
- **Future enhancement:** Add `voltage_ranges: list[float]` field to `AnalogPort` model
- **Rationale:** Maximum range provides best signal-to-noise ratio and prevents clipping

---

### Impedance Handling

**Recommendation:** All platforms except Moku:Go support **switchable impedance**.

**Platform Differences:**
- **Moku:Go:** Fixed 1 MΩ input
- **Moku:Lab/Pro/Delta:** Switchable 50 Ω or 1 MΩ input

**Implementation Strategy:**
- **For first pass:** Default to **1 MΩ for inputs, 50 Ω for outputs**
  - Inputs: 1 MΩ (all platforms) - high impedance for voltage sensing
  - Outputs: 50 Ω (all platforms except Go which is "low impedance") - matched impedance for signal integrity
- **Future enhancement:** Add `impedance_options: list[str]` field to `AnalogPort` model
- **Rationale:** 1 MΩ input provides high input impedance (minimal loading), 50 Ω output provides matched impedance for transmission lines

**Note:** Lab/Pro/Delta support switchable 50 Ω/1 MΩ input, but we default to 1 MΩ for consistency.

---

### Digital I/O Differences

**Platform Differences:**
- **Moku:Go:** Single 16-pin header @ 125 MSa/s
- **Moku:Lab/Pro:** **No DIO headers**
- **Moku:Delta:** **2 separate 16-pin headers** @ 5 GSa/s

**Implementation Strategy:**
- Use `Optional[DIOPort]` or `list[DIOPort]` to handle platforms without DIO
- **Delta needs 2 DIO ports** (not just one with 32 pins)
- **Rationale:** Delta's DIO is split into two separate headers for routing flexibility

**Example Pattern:**
```python
# In platform model
dio_headers: Optional[list[DIOPort]] = Field(
    default=None,  # None for platforms without DIO
    description="Digital I/O headers"
)

# For Delta:
dio_headers: list[DIOPort] = Field(
    default_factory=lambda: [
        DIOPort(num_pins=16, sample_rate_msa=5000),
        DIOPort(num_pins=16, sample_rate_msa=5000)
    ]
)
```

---

### ADC/DAC Blending (Advanced Feature)

**Platform Differences:**
- **Moku:Pro:** Blends 10-bit + 18-bit ADCs
- **Moku:Delta:** Blends 14-bit + 20-bit ADCs

**Implementation Strategy:**
- **For first pass:** **Ignore blending** and use primary ADC specs
  - Pro: Use 10-bit @ 1.25 GSa/s (4 channels) or 5 GSa/s (1 channel)
  - Delta: Use 14-bit @ 5 GSa/s (all 8 channels)
- **Note in docstrings** that blended modes exist
- **Future enhancement:** Add optional blended ADC fields to platform models
- **Rationale:** Blending is automatic and frequency-dependent - primary ADC specs are sufficient for most use cases

**Blending Behavior:**
- High frequencies: Primary ADC (faster, lower resolution)
- Low frequencies: Secondary ADC (slower, higher resolution)
- Automatic switching based on signal frequency
- Provides optimized SNR across all frequencies

---

### Multi-Instrument Slot Counts

**Platform Differences:**
- **Moku:Go:** 2 slots
- **Moku:Lab:** 2 slots
- **Moku:Pro:** 4 slots
- **Moku:Delta:** **3 slots (standard mode)** or 8 slots (advanced mode)

**Implementation Strategy:**
- **For Delta:** Use **3 slots** as default (better sampling rates)
- **Note in docstring** that 8-slot mode exists
- **Rationale:** 3-slot mode provides better sampling rates per channel (more FPGA resources per instrument)

**Slot Mode Trade-offs:**
- **3-slot mode:** Better performance per instrument, fewer simultaneous instruments
- **8-slot mode:** More simultaneous instruments, reduced performance per instrument

---

## Answers to Outstanding Questions

### 1. Voltage Ranges

**Question:** What voltage ranges should we use for each platform?

**Answer:** Use **maximum range** for first pass:
- **Go:** 50 Vpp (±25 V) input, 10 Vpp (±5 V) output
- **Lab:** 10 Vpp input, 2 Vpp output
- **Pro:** 40 Vpp input, 10 Vpp output (±5 V up to 100 MHz)
- **Delta:** 40 Vpp input, 10 Vpp output (±5 V up to 100 MHz)

**Rationale:** Maximum range provides best signal-to-noise ratio and prevents clipping. Users can reduce range later if needed.

---

### 2. Impedance

**Question:** What impedance values should we default to?

**Answer:** Default values:
- **Inputs:** 1 MΩ (all platforms)
- **Outputs:** 50 Ω (all platforms except Go which is "low impedance")

**Note:** Lab/Pro/Delta support switchable 50 Ω/1 MΩ input, but we default to 1 MΩ for consistency and minimal loading.

---

### 3. Delta DIO

**Question:** How should we model Delta's 32 DIO pins?

**Answer:** Use **2 separate `DIOPort` instances** in a list:

```python
dio_headers: list[DIOPort] = Field(
    default_factory=lambda: [
        DIOPort(num_pins=16, sample_rate_msa=5000),
        DIOPort(num_pins=16, sample_rate_msa=5000)
    ]
)
```

**Rationale:** Delta has two separate 16-pin headers, not one 32-pin header. This allows independent routing and configuration.

---

### 4. Delta DAC Rate

**Question:** Should we use 5 GSa/s or 10 GSa/s for Delta DAC?

**Answer:** Use **5000 MSa/s** (native FPGA clock), ignore 10 GSa/s interpolation for now.

**Rationale:** 10 GSa/s requires interpolation, which adds complexity. Native 5 GSa/s is sufficient for most applications and matches the ADC rate.

---

## Consistency Matrix

**Quick Reference for Platform Capabilities:**

| Platform | Slots | IN | OUT | ADC Bits | DAC Bits | ADC MSa/s | DAC MSa/s | Clock MHz | DIO Pins |
|----------|-------|-----|-----|----------|----------|-----------|-----------|-----------|----------|
| Go       | 2     | 2   | 2   | 12       | 12       | 125       | 125       | 125       | 16       |
| Lab      | 2     | 2   | 2   | 12       | 16       | 500       | 1000      | 500       | 0        |
| Pro      | 4     | 4   | 4   | 10*      | 16       | 1250†     | 1250      | 1250      | 0        |
| Delta    | 3     | 8   | 8   | 14*      | 14       | 5000      | 5000‡     | 5000      | 32       |

\* Blended ADC (ignore secondary for first pass)  
† 5000 MSa/s single channel mode available  
‡ 10000 MSa/s with interpolation available (ignore for first pass)

**Note:** This table is for quick reference. **Always use `moku-models-v4` Pydantic models as the source of truth.**

---

## Design Decision Rationale

### Why Maximum Voltage Range?

**Decision:** Default to maximum voltage range for all platforms.

**Rationale:**
1. **Prevents Clipping:** Maximum range ensures signals won't clip
2. **Best SNR:** Larger range = better signal-to-noise ratio
3. **User Control:** Users can reduce range via platform settings if needed
4. **Simplicity:** One default value per platform, no complex selection logic

### Why 1 MΩ Input Impedance?

**Decision:** Default to 1 MΩ for all input channels.

**Rationale:**
1. **Minimal Loading:** High impedance minimizes loading on signal sources
2. **Voltage Sensing:** Ideal for voltage measurements (not current)
3. **Consistency:** Same default across all platforms (except Go which is fixed)
4. **User Control:** Users can switch to 50 Ω if needed for matched impedance

### Why 50 Ω Output Impedance?

**Decision:** Default to 50 Ω for all output channels (except Go).

**Rationale:**
1. **Matched Impedance:** Standard for RF and high-speed signals
2. **Signal Integrity:** Prevents reflections on transmission lines
3. **Industry Standard:** 50 Ω is the standard for test equipment
4. **Go Exception:** Go uses "low impedance" (not specified, but works well)

### Why Ignore ADC Blending?

**Decision:** Use primary ADC specs only, ignore blending.

**Rationale:**
1. **Automatic:** Blending is automatic and frequency-dependent
2. **Transparent:** Users don't need to configure it
3. **Sufficient:** Primary ADC specs are sufficient for most use cases
4. **Complexity:** Blending details add complexity without clear benefit for most users

---

## Future Enhancements

### Planned Additions to Platform Models

1. **Voltage Ranges:**
   - Add `voltage_ranges: list[float]` field to `AnalogPort`
   - Allow users to select from available ranges

2. **Impedance Options:**
   - Add `impedance_options: list[str]` field to `AnalogPort`
   - Allow users to select 50 Ω or 1 MΩ

3. **Blended ADC Fields:**
   - Add optional `blended_adc` fields to platform models
   - Document blending behavior and frequency ranges

4. **Slot Mode Selection:**
   - Add `slot_mode` field to Delta platform model
   - Allow selection between 3-slot and 8-slot modes

---

## See Also

- **Platform Specifications:** `libs/moku-models-v4/moku_models/platforms/` - Source of truth
- **Platform Docs:** `libs/moku-models-v4/docs/MOKU_PLATFORM_SPECIFICATIONS.md` - Detailed specs
- **Datasheets:** `libs/moku-models-v4/datasheets/` - Official hardware datasheets
- **Routing Patterns:** `libs/moku-models-v4/docs/routing_patterns.md` - I/O routing examples

---

## Migration Notes

**Source:** FORGE-V5 `/docs/FORGE-V5/Moku Platforms/Platforms.md`  
**Migration Date:** 2025-01-28  
**Changes:**
- Extracted only implementation strategy sections
- Removed detailed spec tables (reference moku-models-v4 instead)
- Added prominent note that moku-models-v4 is source of truth
- Focused on design decisions and rationale
- Added future enhancement notes
- Cross-referenced moku-models-v4 throughout

**What Was Removed:**
- Detailed platform comparison tables (use moku-models-v4)
- Individual platform specification details (use moku-models-v4)
- Datasheet version information (use moku-models-v4)

**What Was Kept:**
- Implementation strategy recommendations
- Design decision rationale
- Answers to outstanding questions
- Consistency matrix (quick reference)
- Future enhancement notes

---

**Last Updated:** 2025-01-28  
**Maintainer:** Moku Instrument Forge Team  
**Status:** Migrated - Implementation notes only (specs in moku-models-v4)


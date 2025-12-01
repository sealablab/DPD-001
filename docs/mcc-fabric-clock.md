---
created: 2025-11-29
modified: 2025-11-29
status: EXPLORATORY
tags:
  - moku
  - cloudcompile
  - clock
  - bios
  - experiment
---

# MCC Fabric Clock: Theory and BIOS Implications

> [!note] Document Purpose
> This document explores the **implications** of the ADC vs MCC fabric clock distinction for the BIOS project. See [moku-clock-domains.md](moku-clock-domains.md) for the authoritative reference on clock frequencies.

## The Core Question

When we write VHDL for CloudCompile, what clock frequency does our logic actually run at?

```vhdl
-- What frequency is Clk?
process(Clk)
begin
    if rising_edge(Clk) then
        counter <= counter + 1;  -- How fast does this increment?
    end if;
end process;
```

**Two possibilities:**

| Hypothesis | Moku:Go `Clk` | Moku:Lab `Clk` | Evidence |
|------------|---------------|----------------|----------|
| **A: ADC Clock** | 125 MHz | 500 MHz | Datasheets, DPD clk_utils.py |
| **B: MCC Fabric Clock** | 31.25 MHz | 125 MHz | Official examples, BoxcarControlPanel.py |

## Why This Matters for BIOS

The BIOS project has **multiple timing-critical components** that depend on knowing the true clock frequency:

### 1. ROM Waveform Playback

The ROM primitives (SIN_128, SQR_04_128, etc.) are indexed by a counter:

```vhdl
-- Waveform playback at one sample per clock
process(Clk)
begin
    if rising_edge(Clk) then
        rom_index <= rom_index + 1;
        dac_out <= WAVE_ROM(to_integer(rom_index));
    end if;
end process;
```

**Impact of clock frequency on SIN_128 playback:**

| Clock | Period per Sample | Full Cycle (128 samples) | Output Frequency |
|-------|-------------------|--------------------------|------------------|
| 125 MHz | 8 ns | 1.024 µs | 976.6 kHz |
| 31.25 MHz | 32 ns | 4.096 µs | 244.1 kHz |

A **4× difference** in output frequency!

### 2. FSM State Timing

The BOOT FSM uses counters for state timeouts:

```vhdl
-- Wait for N clock cycles in BOOT_P1
if state = BOOT_P1 then
    if wait_counter = BOOT_P1_TIMEOUT then
        state <= BIOS_ACTIVE;
    else
        wait_counter <= wait_counter + 1;
    end if;
end if;
```

If we want a 100ms timeout:
- At 125 MHz: `BOOT_P1_TIMEOUT = 12,500,000`
- At 31.25 MHz: `BOOT_P1_TIMEOUT = 3,125,000`

### 3. LOADER Strobe Timing

The LOADER uses falling-edge detection on CR0[21]:

```vhdl
-- Generous timing: 1ms per word
constant STROBE_PERIOD_CYCLES : integer := ???;
```

At 1ms per strobe:
- At 125 MHz: 125,000 cycles
- At 31.25 MHz: 31,250 cycles

### 4. HVS State Encoding Update Rate

The HVS encoder updates OutputC at the fabric clock rate. Faster updates mean:
- More responsive state display
- Higher bandwidth for status nibble changes
- But also more potential for aliasing on slow oscilloscopes

### 5. Clock Divider Interpretation

The ROM primitives spec defines clock dividers:

```
CLK_DIV_SEL = 0010 → /4 → "31.25 MHz"
```

But 31.25 MHz of **what**? If the base clock is already 31.25 MHz, then /4 gives 7.81 MHz. If the base is 125 MHz, /4 gives 31.25 MHz.

## The Ambiguity

Here's why this is confusing:

### Evidence for Hypothesis A (VHDL runs at ADC clock)

1. **CLAUDE.md states**: "Platform: Moku:Go (125 MHz clock, ±5V analog I/O)"
2. **DPD clk_utils.py uses**: `DEFAULT_CLK_FREQ_HZ = 125_000_000`
3. **Datasheets emphasize**: 125 MSa/s sample rate
4. **DAC/ADC I/O**: Must run at sample rate for full bandwidth

### Evidence for Hypothesis B (VHDL runs at MCC fabric clock)

1. **BoxcarControlPanel.py uses**: `period_dict['Moku:Go'] = 32e-9` (31.25 MHz)
2. **SweptPulse examples use**: `freqControl = int(31250000/float(PRF))`
3. **Example comments state**: "Clock frequency of Moku:Go" = 31.25 MHz
4. **÷4 ratio**: Consistent across Go/Lab/Pro platforms

### A Third Possibility: Both Are True

Perhaps the architecture is:

```
┌─────────────────────────────────────────────────────────────┐
│                     Moku:Go Architecture                      │
│                                                               │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐    │
│  │   ADC       │     │  CloudCompile│     │    DAC      │    │
│  │  125 MHz    │────▶│  31.25 MHz  │────▶│  125 MHz    │    │
│  │  12-bit     │     │  (÷4)       │     │  12-bit     │    │
│  └─────────────┘     └─────────────┘     └─────────────┘    │
│         │                   │                   ▲            │
│         │            ┌──────┴──────┐            │            │
│         │            │  CustomWrapper│            │            │
│         └───────────▶│  Clk=31.25MHz│───────────┘            │
│                      │  InputA/B    │                        │
│                      │  OutputA/B   │                        │
│                      └──────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

In this model:
- ADCs sample at 125 MHz, but **decimate** to 31.25 MHz for the MCC fabric
- DACs receive 31.25 MHz data and **interpolate** to 125 MHz for output
- The `Clk` signal to CustomWrapper is actually 31.25 MHz
- Control registers are synchronized to the fabric clock

This would explain why:
- Datasheets advertise 125 MSa/s (true for I/O)
- Examples use 31.25 MHz (true for control timing)
- Both are correct in their respective domains

## Implications for BIOS Design

### If VHDL Runs at 31.25 MHz (Hypothesis B)

1. **ROM playback is slower than expected**
   - SIN_128 at 244 kHz, not 976 kHz
   - Waveforms are "slow" on oscilloscope

2. **FSM timing needs smaller counters**
   - 4× fewer cycles for same wall-clock time
   - Simpler logic, less BRAM for counters

3. **HVS update rate is 31.25 MHz**
   - 32ns per state update
   - Plenty fast for oscilloscope observation

4. **LOADER strobe timing matches examples**
   - 1ms = 31,250 cycles (matches intuition)

### If VHDL Runs at 125 MHz (Hypothesis A)

1. **ROM playback is fast**
   - SIN_128 at 976 kHz
   - Need clock divider for human-observable rates

2. **FSM timing needs larger counters**
   - 4× more cycles for same wall-clock time
   - Wider counters, more logic

3. **HVS update rate is 125 MHz**
   - 8ns per state update
   - Way faster than needed

4. **LOADER timing calculations are off by 4×**
   - Would explain some mysterious timing bugs

## The Experiment: Empirical Verification

The simplest way to resolve this is to **measure it directly**.

---

# Experiment: Clock Frequency Verification

## Objective

Determine the actual FPGA fabric clock frequency on Moku:Go and Moku:Lab by measuring the period of a known waveform.

## Method: Pulse Width Measurement

Use the `SQR_04_128` ROM primitive (4 samples high, 124 samples low) played back at one sample per clock cycle. The pulse width directly reveals the clock period.

```
SQR_04_128 Waveform:
    ┌────┐
    │    │
────┘    └────────────────────────────────────────────────────
    ◀──▶
    4 samples high

Pulse width = 4 × clock_period
```

### Expected Results

| Platform | If ADC Clock | If MCC Fabric Clock |
|----------|--------------|---------------------|
| **Moku:Go** | 4 × 8ns = **32ns** | 4 × 32ns = **128ns** |
| **Moku:Lab** | 4 × 2ns = **8ns** | 4 × 8ns = **32ns** |

**Measurement determines which hypothesis is correct!**

## Hardware Setup

### Equipment
- Moku:Go (available)
- Moku:Lab (available)
- External oscilloscope (for independent timing reference)
- OR: Use Moku's built-in oscilloscope in MIM slot 2

### Connections
```
Moku:Go/Lab                    Oscilloscope
┌─────────┐                    ┌─────────┐
│         │                    │         │
│  Out 1  │───────────────────▶│  Ch 1   │
│         │                    │         │
└─────────┘                    └─────────┘
```

## VHDL Design: Minimal Clock Probe

### Entity: `clock_probe.vhd`

```vhdl
library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;

entity clock_probe is
    port (
        Clk      : in  std_logic;
        Reset    : in  std_logic;

        -- Control registers (directly from MCC)
        Control0 : in  std_logic_vector(31 downto 0);

        -- Outputs
        OutputA  : out std_logic_vector(15 downto 0)  -- DAC output
    );
end entity clock_probe;

architecture rtl of clock_probe is

    -- ROM: SQR_04_128 waveform (4 high, 124 low)
    type rom_t is array(0 to 127) of signed(15 downto 0);
    constant SQR_04_128 : rom_t := (
        0 => x"7FFF",  -- +32767 (max)
        1 => x"7FFF",
        2 => x"7FFF",
        3 => x"7FFF",
        others => x"0000"  -- 0 (min)
    );

    signal rom_index : unsigned(6 downto 0) := (others => '0');
    signal enable    : std_logic;

begin

    -- FORGE enable from CR0[31:29]
    enable <= Control0(31) and Control0(30) and Control0(29);

    -- Free-running ROM index counter
    process(Clk)
    begin
        if rising_edge(Clk) then
            if Reset = '1' then
                rom_index <= (others => '0');
            elsif enable = '1' then
                rom_index <= rom_index + 1;  -- Wraps at 128
            end if;
        end if;
    end process;

    -- ROM lookup → DAC output
    OutputA <= std_logic_vector(SQR_04_128(to_integer(rom_index)));

end architecture rtl;
```

### Key Design Points

1. **Minimal logic**: Just a counter and ROM lookup
2. **FORGE gating**: Respects CR0[31:29] enable bits
3. **Free-running**: No external triggering, continuous output
4. **Direct measurement**: Pulse width = 4 × Clk period

## Python Test Script

```python
#!/usr/bin/env python3
"""
clock_probe_test.py - Measure MCC fabric clock frequency

This script:
1. Deploys clock_probe bitstream to MCC slot
2. Configures oscilloscope to capture pulse
3. Measures pulse width
4. Calculates implied clock frequency
"""

from moku.instruments import MultiInstrument, Oscilloscope, CloudCompile
import numpy as np
import time

# Configuration
MOKU_IP = "192.168.xxx.xxx"  # Update for your device
BITSTREAM_PATH = "clock_probe.tar.gz"
PLATFORM_ID = 2  # Moku:Go

def measure_clock_frequency():
    """Deploy bitstream and measure pulse width."""

    # Connect to Moku
    m = MultiInstrument(MOKU_IP, platform_id=PLATFORM_ID, force_connect=True)

    try:
        # Deploy instruments
        mcc = m.set_instrument(1, CloudCompile, bitstream=BITSTREAM_PATH)
        osc = m.set_instrument(2, Oscilloscope)

        # Route MCC output to oscilloscope
        m.set_connections([
            {'source': 'Slot1OutA', 'destination': 'Slot2InA'},
            {'source': 'Slot1OutA', 'destination': 'Output1'},  # Also to physical out
        ])

        # Configure oscilloscope for pulse capture
        osc.set_timebase(t1=-500e-9, t2=2000e-9)  # 500ns pre, 2µs post trigger
        osc.set_trigger(
            type='Edge',
            source='Input1',
            level=0.5,  # 50% of expected amplitude
            edge='Rising',
            mode='Normal'
        )
        osc.set_frontend(channel=1, impedance='1MOhm', coupling='DC', range='10Vpp')

        # Enable FORGE (CR0[31:29] = 0xE0000000)
        mcc.set_control(0, 0xE0000000)

        time.sleep(0.1)  # Let waveform stabilize

        # Capture data
        data = osc.get_data(wait_reacquire=True)

        # Find pulse width
        time_axis = np.array(data['time'])
        ch1 = np.array(data['ch1'])

        # Threshold at 50%
        threshold = (np.max(ch1) + np.min(ch1)) / 2
        above = ch1 > threshold

        # Find rising and falling edges
        rising_edges = np.where(np.diff(above.astype(int)) == 1)[0]
        falling_edges = np.where(np.diff(above.astype(int)) == -1)[0]

        if len(rising_edges) > 0 and len(falling_edges) > 0:
            # Find first complete pulse
            rise_idx = rising_edges[0]
            fall_candidates = falling_edges[falling_edges > rise_idx]
            if len(fall_candidates) > 0:
                fall_idx = fall_candidates[0]

                pulse_width_s = time_axis[fall_idx] - time_axis[rise_idx]
                clock_period_s = pulse_width_s / 4  # 4 samples high
                clock_freq_hz = 1.0 / clock_period_s

                print(f"\n=== Results ===")
                print(f"Pulse width: {pulse_width_s * 1e9:.1f} ns")
                print(f"Clock period: {clock_period_s * 1e9:.1f} ns")
                print(f"Clock frequency: {clock_freq_hz / 1e6:.2f} MHz")

                # Determine which hypothesis
                if abs(clock_freq_hz - 125e6) < 10e6:
                    print(f"\n→ Hypothesis A: VHDL runs at ADC clock (125 MHz)")
                elif abs(clock_freq_hz - 31.25e6) < 5e6:
                    print(f"\n→ Hypothesis B: VHDL runs at MCC fabric clock (31.25 MHz)")
                else:
                    print(f"\n→ Unexpected frequency - investigate further")

                return clock_freq_hz

        print("Could not detect pulse edges - check connections")
        return None

    finally:
        m.relinquish_ownership()


if __name__ == "__main__":
    print("=== MCC Fabric Clock Measurement ===")
    print(f"Testing platform: Moku:Go")
    print(f"Expected results:")
    print(f"  If ADC clock (125 MHz):     pulse = 32 ns")
    print(f"  If MCC fabric (31.25 MHz):  pulse = 128 ns")
    print()

    freq = measure_clock_frequency()
```

## Expected Outcomes

### Scenario 1: Pulse Width = 128ns on Moku:Go

**Conclusion**: VHDL fabric runs at **31.25 MHz** (MCC fabric clock)

**Implications for BIOS**:
- ROM playback at 31.25 MHz (SIN_128 = 244 kHz)
- FSM counters use 31.25 MHz base
- Clock divider table in ROM spec needs revision
- DPD's clk_utils.py is using **wrong** frequency

### Scenario 2: Pulse Width = 32ns on Moku:Go

**Conclusion**: VHDL fabric runs at **125 MHz** (ADC clock)

**Implications for BIOS**:
- ROM playback at 125 MHz (SIN_128 = 976 kHz)
- FSM counters are 4× larger than expected
- Clock divider /4 yields 31.25 MHz (matches examples)
- Example code timing calculations include implicit /4

### Scenario 3: Something Else

**Conclusion**: Architecture is more complex than expected

**Possible explanations**:
- Multi-rate clocking (different clocks for different blocks)
- Phase-locked relationship between domains
- Platform-specific clock configuration

## Cross-Platform Verification

Run the same experiment on both platforms:

| Measurement | Moku:Go | Moku:Lab |
|-------------|---------|----------|
| Pulse width | ___ ns | ___ ns |
| Clock period | ___ ns | ___ ns |
| Clock freq | ___ MHz | ___ MHz |

If the ÷4 ratio holds:
- Moku:Go: 31.25 MHz (÷4 of 125 MHz)
- Moku:Lab: 125 MHz (÷4 of 500 MHz)

## Why This Experiment is Conclusive

1. **No timing calculations required** - just measure the pulse
2. **Platform-agnostic VHDL** - same code runs on both platforms
3. **Self-documenting** - pulse width directly reveals clock period
4. **Independent verification** - can use external scope
5. **Matches BIOS use case** - ROM playback is exactly what BIOS will do

## Next Steps After Experiment

1. **Update documentation** with measured values
2. **Fix clk_utils.py** if using wrong frequency
3. **Update ROM spec** clock divider table
4. **Add MCC_CLK_FREQ constant** to forge_common_pkg.vhd
5. **Create platform detection** for portable timing code

---

## See Also

- [moku-clock-domains.md](moku-clock-domains.md) - Authoritative clock reference
- [BOOT-ROM-primitives-spec.md](docs/boot/BOOT-ROM-WAVES-prop.md) - ROM waveforms
- [BOOT-FSM-spec.md](bootup-proposal/BOOT-FSM-spec.md) - BIOS state machine timing
- [BoxcarControlPanel.py](../moku_trim_examples/mcc/HDLCoder/hdlcoder_boxcar/python/BoxcarControlPanel.py) - Example period_dict

---
**Last Updated**: 2025-11-29
**Status**: EXPLORATORY - Pending experimental verification

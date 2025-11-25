# Handoff: FSM Spurious Trigger Issue

## Problem Summary

The DPD FSM is spuriously transitioning from ARMED → FIRING state when it should stay in ARMED waiting for a trigger. This happens even though:
1. Hardware trigger is now gated by CR1[4] (hw_trigger_enable), which defaults to '0'
2. Software trigger (CR1[1]) is NOT being set

## Current Symptom

```
Test: test_forge_control
Expected: FSM stays in ARMED (OutputC ≈ 6554 digital units = 1.0V)
Actual: FSM goes to FIRING (OutputC ≈ 9896 digital units ≈ 1.5V)
Error: "Timeout waiting for OutputC=6554±200, stuck at 9896 after 100μs"
```

## Recent Changes Made

We added CR1[4] as `hw_trigger_enable` to gate the hardware voltage trigger:

**File: `rtl/DPD_shim.vhd`**
- Added signal: `app_reg_hw_trigger_enable`
- Added signal: `hw_trigger_enable_gated`
- Reset default: `app_reg_hw_trigger_enable <= '0'` (disabled for safety)
- CR1 decoding: `app_reg_hw_trigger_enable <= app_reg_1(4)`
- Gate logic: `hw_trigger_enable_gated <= global_enable and app_reg_hw_trigger_enable`
- HW trigger enable: `enable => hw_trigger_enable_gated` (was just `global_enable`)

## Architecture Overview

### 3-Layer Structure
```
DPD.vhd (TOP) → DPD_shim.vhd (register mapping) → DPD_main.vhd (FSM logic)
```

### Trigger Path
```
InputA voltage → moku_voltage_threshold_trigger_core → hw_trigger_out ─┐
                                                                        ├─→ combined_trigger → ext_trigger_in (to FSM)
CR1[1] sw_trigger → edge detection → sw_trigger_edge ──────────────────┘
```

### FSM States (DPD_main.vhd)
- INITIALIZING (0) → IDLE (1) → ARMED (2) → FIRING (3) → COOLDOWN (4)
- HVS encoding: state × 3277 digital units (0.5V per state)

## Key Code Sections

### Combined Trigger (DPD_shim.vhd:294-299)
```vhdl
combined_trigger <= hw_trigger_out or sw_trigger_edge;
```

### HW Trigger Enable Gate (DPD_shim.vhd:301-307)
```vhdl
hw_trigger_enable_gated <= global_enable and app_reg_hw_trigger_enable;

HW_TRIGGER_INST: entity WORK.moku_voltage_threshold_trigger_core
    port map (
        ...
        enable => hw_trigger_enable_gated,  -- CR1[4] gates HW trigger
        trigger_out => hw_trigger_out,
        ...
    );
```

### SW Trigger Edge Detection (DPD_shim.vhd:287-288)
```vhdl
sw_trigger_edge <= app_reg_sw_trigger and not sw_trigger_prev;
```

### FSM ARMED→FIRING Transition (DPD_main.vhd:288-295)
```vhdl
when STATE_ARMED =>
    if timeout_occurred = '1' then
        next_state <= STATE_FAULT;
    elsif ext_trigger_in = '1' then
        next_state <= STATE_FIRING;
    end if;
```

### Trigger Core Behavior When Disabled (moku_voltage_threshold_trigger_core.vhd:104-116)
```vhdl
elsif rising_edge(clk) then
    if enable = '1' then
        -- Generate trigger pulse
        ...
    else
        trigger_out <= '0';  -- Explicitly held low when disabled
    end if;
end if;
```

## Test Sequence That Fails

**File: `tests/sim/dpd_wrapper_tests/P1_dpd_wrapper_basic.py` (test_forge_control)**

```python
# Step 1: Reset
self.dut.Reset.value = 1
await ClockCycles(self.dut.Clk, 5)
self.dut.Reset.value = 0
await ClockCycles(self.dut.Clk, 5)

# Step 2: Enable FORGE and arm (CR1[4]=0, so hw_trigger disabled)
await mcc_set_regs(self.dut, {
    0: MCC_CR0_ALL_ENABLED,  # 0xE0000000
    1: 0x00000001,           # arm_enable=1 ONLY (bits 1-4 are 0)
})

# Step 3: Wait for ARMED - THIS FAILS (FSM goes to FIRING instead)
await wait_for_state(self.dut, HVS_DIGITAL_ARMED, timeout_us=100)
```

## Hypotheses (Not Yet Ruled Out)

1. **Metavalue initialization issue**: GHDL reports "Metavalue warnings: 4". Uninitialized signals ('U'/'X') could cause unexpected comparator behavior.

2. **Edge detection glitch**: The sw_trigger_edge logic might produce a spurious pulse during initialization sequence.

3. **Combinational race**: The `hw_trigger_enable_gated` signal is combinational. There might be a glitch when `global_enable` goes high before `app_reg_hw_trigger_enable` is stable.

4. **Previous test contamination**: The test runs after `test_reset`. State from previous test might affect this one despite the reset.

5. **sync_safe timing**: Config registers only latch during INITIALIZING. The 5-cycle wait after reset might not be enough for proper initialization.

## What We've Verified

- ✅ VHDL compiles successfully (`make compile`)
- ✅ hw_trigger_enable defaults to '0' in reset
- ✅ Trigger core explicitly sets `trigger_out <= '0'` when disabled
- ✅ CR1[1] (sw_trigger) is NOT being set (value is 0x00000001, only bit 0)

## Relevant Files

| File | Purpose |
|------|---------|
| `rtl/DPD_shim.vhd` | Register mapping, trigger logic |
| `rtl/DPD_main.vhd` | FSM state machine |
| `rtl/moku_voltage_threshold_trigger_core.vhd` | HW voltage trigger |
| `tests/sim/dpd_wrapper_tests/P1_dpd_wrapper_basic.py` | Failing test |
| `tests/sim/conftest.py` | Test helpers (mcc_set_regs, etc.) |
| `tests/sim/dpd_wrapper_tests/dpd_helpers.py` | State assertion helpers |

## Run Commands

```bash
cd /Users/johnycsh/DPD/DPD-001

# Compile VHDL
make compile

# Run tests
cd tests/sim && uv run python run.py
```

## Suggested Debug Approach

1. Add waveform tracing to capture: `combined_trigger`, `hw_trigger_out`, `sw_trigger_edge`, `hw_trigger_enable_gated`, `state_reg`

2. Check signal values at key moments:
   - During reset
   - At reset release
   - When FORGE enable is set
   - When FSM transitions IDLE→ARMED
   - When spurious ARMED→FIRING happens

3. Verify no glitches on `combined_trigger` during initialization

4. Check if `ext_trigger_in` ever goes high and when

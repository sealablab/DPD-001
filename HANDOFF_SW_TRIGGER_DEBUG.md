# Handoff: Software Trigger Debugging (CR0[0] Migration)

## Summary

We moved `sw_trigger` from CR1[5] to CR0[0] to provide a more direct network path for the software trigger signal. The simulation tests pass, but hardware testing shows the trigger isn't firing.

## What Changed

### VHDL Changes

1. **`rtl/DPD_shim.vhd`**:
   - Added `app_reg_0` port to receive full Control0 register
   - Changed `app_reg_sw_trigger <= app_reg_0(0)` (was `app_reg_1(5)`)
   - Edge detection still in shim: `sw_trigger_edge <= app_reg_sw_trigger and not sw_trigger_prev`

2. **`rtl/DPD.vhd`**:
   - Added `app_reg_0 => Control0` to shim port map

### Python Changes

3. **`py_tools/dpd_constants.py`**:
   - Added `CR0.SW_TRIGGER = 0` and `CR0.SW_TRIGGER_MASK = 0x01`
   - Added `CR0.ALL_ENABLED_WITH_TRIGGER = 0xE0000001`
   - Removed `CR1.SW_TRIGGER`

4. **`tests/lib/dpd_config.py`**:
   - Added `_build_cr0()` method
   - Updated `_build_cr1()` to remove sw_trigger

5. **`tests/adapters/base.py`**:
   - Updated `software_trigger()` to use CR0

6. **`tests/sim/dpd/P1_basic.py`** and **`tests/sim/dpd/helpers.py`**:
   - Updated trigger calls to use CR0[0]

7. **`tests/hw/osc_diagnostic.py`**:
   - Updated trigger sequence to use CR0[0]

## New Trigger Protocol

```python
# OLD (CR1[5]):
mcc.set_control(1, 0x29)  # arm + sw_trigger_enable + sw_trigger

# NEW (CR0[0]):
mcc.set_control(1, 0x09)  # arm + sw_trigger_enable (gate)
mcc.set_control(0, 0xE0000000)  # Ensure sw_trigger=0
mcc.set_control(0, 0xE0000001)  # Rising edge on sw_trigger
mcc.set_control(0, 0xE0000000)  # Falling edge (clear)
```

## Current Issue

**Simulation**: PASSES - The P1_basic tests work correctly with CR0[0] trigger.

**Hardware**: FAILS - FSM stays in ARMED after trigger pulse.

### Diagnostic Output (Latest)
```
After arm: 1.0005V = ARMED
Sending software trigger...
  Step 1: CR1 = 0x09 (arm + sw_trigger_enable)
  Step 2: CR0 = 0xE0000000 (ensure sw_trigger=0)
  Step 3: CR0 = 0xE0000001 (FORGE + sw_trigger rising edge)
  Mid-trigger state: 1.0005V = ARMED
  Step 4: CR0 = 0xE0000000 (clear sw_trigger)
  After trigger: 1.0005V = ARMED
ERROR: FSM still ARMED - trigger not detected!
```

## Hypotheses

1. **Bitstream not rebuilt**: The user may have re-uploaded the old `.tar` without rebuilding via CloudCompile. The diagnostic now tests BOTH old (CR1[5]) and new (CR0[0]) methods to detect this.

2. **Register propagation timing**: The Moku network stack may have timing characteristics that prevent proper edge detection. However, we're waiting 50-100ms between writes, which should be ample.

3. **Clock domain crossing**: Control registers written from network interface cross into FPGA clock domain. Should have synchronizers, but could be an issue.

4. **VHDL synthesis issue**: The synthesis tool might optimize away the edge detection logic if it doesn't recognize the pattern.

## Next Steps

1. **Run updated diagnostic** - It now tests OLD method (CR1[5]) to determine which bitstream is loaded:
   ```bash
   cd tests && uv run python hw/osc_diagnostic.py 192.168.31.41 ../dpd-bits.tar
   ```

2. **If OLD method works**: Rebuild bitstream with CloudCompile using updated VHDL.

3. **If BOTH methods fail**:
   - Check if timing validation is failing (FSM might reject trigger if timing params invalid)
   - Add debug outputs to VHDL to observe internal signals
   - Check if `sw_trigger_enable` (CR1[3]) is actually being latched

4. **Verify VHDL compiles**:
   ```bash
   cd /Users/johnycsh/DPD/DPD-001 && make compile
   ```

## Key Files

- `rtl/DPD_shim.vhd` - Edge detection and trigger combining logic (lines 245-320)
- `rtl/DPD.vhd` - Top level, passes Control0 to shim
- `rtl/DPD-RTL.yaml` - Register specification (updated for CR0[0])
- `tests/hw/osc_diagnostic.py` - Hardware debugging tool
- `py_tools/dpd_constants.py` - Python constants (CR0, CR1 classes)

## Register Quick Reference

```
CR0[31:29] = FORGE control (forge_ready, user_enable, clk_enable)
CR0[0]     = sw_trigger (edge-detected, NEW location)

CR1[0]     = arm_enable
CR1[1]     = auto_rearm_enable
CR1[2]     = fault_clear (edge-detected)
CR1[3]     = sw_trigger_enable (gates CR0[0])
CR1[4]     = hw_trigger_enable

CR4-CR7    = Timing config (trig_duration, intensity_duration, timeout, cooldown)
```

## VHDL Edge Detection Logic (DPD_shim.vhd)

```vhdl
-- Signal extraction (REGISTER_SYNC process, line ~246)
app_reg_sw_trigger <= app_reg_0(0);  -- CR0[0]

-- Edge detection (combinational, line ~316)
sw_trigger_edge <= app_reg_sw_trigger and not sw_trigger_prev;

-- Combined trigger (combinational, line ~321)
combined_trigger <= '1' when (hw_trigger_out = '1' or
                              (sw_trigger_edge = '1' and app_reg_sw_trigger_enable = '1'))
                    else '0';

-- Registered output to FSM (REGISTER_SYNC process, line ~258)
combined_trigger_reg <= combined_trigger;
```

The FSM sees `ext_trigger_in => combined_trigger_reg` which should be '1' for at least one cycle when sw_trigger has a rising edge and sw_trigger_enable is set.

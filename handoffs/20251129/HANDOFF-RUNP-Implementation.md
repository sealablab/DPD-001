---
created: 2025-11-28
modified: 2025-11-28 23:54:09
accessed: 2025-11-28 23:55:40
---
# HANDOFF: RUNP Implementation (BOOT → PROG Handoff)

**Created:** 2025-11-29
**Status:** Ready for implementation
**Priority:** High - Completes BOOT subsystem

---

## Summary

Implement the one-way `RUNP` command that transfers control from the BOOT dispatcher to the PROG (DPD application). This is the final piece of the BOOT subsystem architecture.

**Current State:** FSM transitions to `PROG_ACTIVE` state work. The PROG outputs are stubbed to zeros.

**Goal:** Connect the existing `DPD_shim` entity so it takes over OutputA/B/C when in PROG_ACTIVE state.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  B0_BOOT_TOP.vhd (BootWrapper architecture)                     │
│                                                                 │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐│
│  │ BOOT FSM     │   │ L2_BUFF_     │   │ B1_BOOT_BIOS        ││
│  │ (dispatcher) │   │ LOADER       │   │ (diagnostics)       ││
│  │              │   │              │   │                     ││
│  │ P0 → P1      │   │ P0→P1→P2→P3  │   │ IDLE→RUN→DONE       ││
│  └──────────────┘   └──────────────┘   └──────────────────────┘│
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ DPD_shim + DPD_main (PROG)   ← THIS IS WHAT WE'RE WIRING   ││
│  │                                                             ││
│  │ Uses DPD's own HVS encoding (3277 units/state = 0.5V)      ││
│  │ Controls OutputA (trigger), OutputB (intensity), OutputC   ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  Output Mux: selects which module drives OutputA/B/C            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Implementation Details

### 1. Current Stub Location

In `rtl/boot/B0_BOOT_TOP.vhd` (lines 256-267):

```vhdl
-- Current stub (replace this):
prog_enable <= '1' when boot_state = BOOT_STATE_PROG_ACTIVE else '0';

-- For now, stub outputs - in real implementation, instantiate DPD_shim
prog_output_a <= (others => '0');
prog_output_b <= (others => '0');
prog_output_c <= to_signed(4 * HVS_BOOT_UNITS_PER_STATE, 16);  -- 0.8V stub

-- BRAM read interface (for PROG to read ENV_BBUFs)
bram_rd_addr <= (others => '0');
bram_rd_sel  <= "00";
```

### 2. DPD_shim Interface

The `DPD_shim` entity needs these signals connected:

```vhdl
entity DPD_shim is
    port (
        -- Clock and Reset
        Clk         : in  std_logic;
        Reset       : in  std_logic;

        -- FORGE Control (from TOP layer)
        forge_ready  : in  std_logic;   -- Always '1' in PROG_ACTIVE
        user_enable  : in  std_logic;   -- Always '1' in PROG_ACTIVE
        clk_enable   : in  std_logic;   -- Always '1' in PROG_ACTIVE
        loader_done  : in  std_logic;   -- Can be tied to '1' or loader_complete

        -- Lifecycle Control (from CR0)
        arm_enable   : in  std_logic;   -- Control0(2)
        fault_clear  : in  std_logic;   -- Control0(1)
        sw_trigger   : in  std_logic;   -- Control0(0)

        -- Configuration Registers (CR2-CR10)
        app_reg_2  : in  std_logic_vector(31 downto 0);  -- Control2
        app_reg_3  : in  std_logic_vector(31 downto 0);  -- Control3
        -- ... CR4-CR10 ...

        -- BRAM Interface (optional - for reading ENV_BBUFs)
        bram_addr   : in  std_logic_vector(11 downto 0);
        bram_data   : in  std_logic_vector(31 downto 0);
        bram_we     : in  std_logic;

        -- MCC I/O
        InputA      : in  signed(15 downto 0);
        InputB      : in  signed(15 downto 0);
        OutputA     : out signed(15 downto 0);
        OutputB     : out signed(15 downto 0);
        OutputC     : out signed(15 downto 0)
    );
end entity DPD_shim;
```

### 3. HVS Encoding Difference

**Critical:** DPD uses a DIFFERENT HVS encoding than pre-PROG:

| Context | Units/State | Units/Status | Voltage Range |
|---------|-------------|--------------|---------------|
| Pre-PROG (BOOT/BIOS/LOADER) | 197 | 11 | 0.0V - 0.94V |
| PROG (DPD) | 3277 | ~0.78 | 0.0V - 2.0V (5 states) |

The `DPD_shim` already handles its own HVS encoding via its internal `forge_hierarchical_encoder` instance. No changes needed there.

### 4. One-Way Semantics

RUNP is **one-way** - there is no RET from PROG:
- Once in `PROG_ACTIVE`, the only exit is RUN gate removal (resets to BOOT_P0)
- This is intentional: PROG owns the system until power cycle or explicit reset
- The BOOT FSM already implements this (see lines 337-343 in B0_BOOT_TOP.vhd)

---

## Implementation Steps

### Step 1: Add DPD_shim Instance to B0_BOOT_TOP.vhd

Replace the stub section with:

```vhdl
----------------------------------------------------------------------------
-- PROG (DPD_shim) Instantiation
----------------------------------------------------------------------------
prog_enable <= '1' when boot_state = BOOT_STATE_PROG_ACTIVE else '0';

-- Only enable DPD when in PROG_ACTIVE state
-- The DPD_shim handles its own HVS encoding
PROG_DPD_INST: entity WORK.DPD_shim
    port map (
        Clk          => Clk,
        Reset        => Reset,

        -- FORGE control: all '1' when PROG is active
        forge_ready  => prog_enable,
        user_enable  => prog_enable,
        clk_enable   => prog_enable,
        loader_done  => '1',  -- Assume loader is done

        -- Lifecycle control from CR0 (always available)
        arm_enable   => Control0(2),
        fault_clear  => Control0(1),
        sw_trigger   => Control0(0),

        -- Configuration registers CR2-CR10
        app_reg_2    => Control2,
        app_reg_3    => Control3,
        app_reg_4    => Control4,
        app_reg_5    => Control5,
        app_reg_6    => Control6,
        app_reg_7    => Control7,
        app_reg_8    => Control8,
        app_reg_9    => Control9,
        app_reg_10   => Control10,

        -- BRAM interface (optional - tie off for now)
        bram_addr    => (others => '0'),
        bram_data    => (others => '0'),
        bram_we      => '0',

        -- MCC I/O
        InputA       => InputA,
        InputB       => InputB,
        OutputA      => prog_output_a,
        OutputB      => prog_output_b,
        OutputC      => prog_output_c
    );
```

### Step 2: Update Signal Declarations

Ensure these signals exist (they already do in current code):
```vhdl
signal prog_output_a : signed(15 downto 0);
signal prog_output_b : signed(15 downto 0);
signal prog_output_c : signed(15 downto 0);
signal prog_enable   : std_logic;
```

### Step 3: Add DPD_shim to Compile Order

In `Makefile`, ensure `DPD_shim.vhd` and `DPD_main.vhd` are compiled before `B0_BOOT_TOP.vhd`.

The existing DPD files are:
- `rtl/DPD_shim.vhd`
- `rtl/DPD_main.vhd`
- `rtl/moku_voltage_threshold_trigger_core.vhd` (used by DPD_main)

### Step 4: Create P3 Tests for RUNP

Add to `tests/sim/boot_fsm/P3_runp.py`:

```python
@cocotb.test()
async def test_boot_runp_handoff(dut):
    """Verify BOOT → PROG handoff via RUNP command."""
    await setup_dut(dut)

    # Get to BOOT_P1
    dut.Control0.value = CMD.RUN
    await ClockCycles(dut.Clk, 5)
    assert_state_approx(dut, "BOOT_P1", BOOT_DIGITAL_P1)

    # RUNP → PROG_ACTIVE
    dut.Control0.value = CMD.RUNP
    await ClockCycles(dut.Clk, 5)

    # Should now see DPD HVS encoding (~0.5V = IDLE = 3277 digital)
    # Note: DPD uses different encoding than pre-PROG
    DPD_DIGITAL_IDLE = 3277
    await wait_for_state(dut, "DPD_IDLE", DPD_DIGITAL_IDLE,
                         max_cycles=50, context="PROG handoff")

@cocotb.test()
async def test_boot_runp_no_return(dut):
    """Verify RET does not work from PROG state."""
    await setup_dut(dut)

    # Get to PROG_ACTIVE
    dut.Control0.value = CMD.RUN
    await ClockCycles(dut.Clk, 5)
    dut.Control0.value = CMD.RUNP
    await ClockCycles(dut.Clk, 10)

    # Try RET - should be ignored
    dut.Control0.value = CMD.RET | RUN.GATE_MASK
    await ClockCycles(dut.Clk, 10)

    # Should still be in PROG (DPD encoding), not BOOT_P1
    actual = get_output_c(dut)
    assert actual > 1000, f"Expected DPD encoding (>1000), got {actual}"
```

---

## Files to Modify

| File | Change |
|------|--------|
| `rtl/boot/B0_BOOT_TOP.vhd` | Replace PROG stub with DPD_shim instance |
| `Makefile` | Ensure compile order includes DPD files |
| `tests/sim/boot_fsm/P3_runp.py` | New test file for RUNP handoff |
| `tests/sim/boot_run.py` | Add P3 module support |

---

## Testing Strategy

1. **Unit test**: RUNP transition works (BOOT_P1 → PROG_ACTIVE)
2. **Integration test**: DPD FSM starts in IDLE after handoff
3. **Negative test**: RET from PROG is ignored
4. **Full workflow**: BOOT_P0 → BOOT_P1 → RUNL → LOADER → RET → RUNB → BIOS → RET → RUNP → DPD

---

## Potential Issues

### 1. Entity Name Collision
The existing `DPD.vhd` uses `CustomWrapper` entity. `B0_BOOT_TOP.vhd` uses `BootWrapper`.
- **Solution**: `DPD_shim` is its own entity, no collision.

### 2. BRAM Interface
DPD_shim expects BRAM interface signals for reading ENV_BBUFs.
- **Solution for now**: Tie off with zeros. Future enhancement can connect to LOADER's BRAMs.

### 3. HVS Voltage Jump
When transitioning from BOOT_P1 (197 digital = 0.03V) to DPD_IDLE (3277 digital = 0.5V), there's a visible voltage jump on the scope.
- **This is expected and correct** - it visually confirms the handoff occurred.

---

## Success Criteria

1. `CMD.RUNP` transitions from BOOT_P1 to PROG_ACTIVE
2. OutputC shows DPD HVS encoding (~0.5V for IDLE)
3. DPD FSM operates normally (arm → trigger → firing → cooldown)
4. `CMD.RET` from PROG is ignored
5. RUN gate removal resets to BOOT_P0
6. All P1, P2, and new P3 tests pass

---

## References

- `rtl/boot/B0_BOOT_TOP.vhd` - Current implementation with stub
- `rtl/DPD_shim.vhd` - DPD shim layer to instantiate
- `rtl/DPD_main.vhd` - DPD FSM logic
- `docs/boot/BOOT-HVS-state-reference.md` - HVS encoding reference
- `docs/boot-process-terms.md` - PROG terminology
- `py_tools/boot_constants.py` - Python constants for testing

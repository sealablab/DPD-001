# Custom Instrument

**Last Updated:** 2025-11-12 (migrated 2025-01-28)  
**Maintainer:** Moku Instrument Forge Team

> **Migration Note:** This document was migrated from FORGE-V5 and updated to reflect DPD-001's use of CustomWrapper architecture.  
> **Terminology:** "Custom Instrument" is Liquid Instruments' future terminology, but DPD-001 currently uses the "CustomWrapper" pattern.

---

The **Custom Instrument** is the terminology Liquid Instruments is migrating to in the future. However, DPD-001 currently uses the **CustomWrapper** architecture pattern, which is the current standard for Moku Cloud Compile (MCC) deployments.

---

## CustomWrapper vs Custom Instrument

### Current Standard: CustomWrapper

**DPD-001 uses:** `CustomWrapper` entity (current MCC standard)

**Entity Signature:**
```vhdl
entity CustomWrapper is
    port (
        Clk    : in  std_logic;
        Reset  : in  std_logic;
        
        InputA : in  signed(15 downto 0);
        InputB : in  signed(15 downto 0);
        InputC : in  signed(15 downto 0);
        
        OutputA : out signed(15 downto 0);
        OutputB : out signed(15 downto 0);
        OutputC : out signed(15 downto 0);
        
        Control0 : in std_logic_vector(31 downto 0);
        Control1 : in std_logic_vector(31 downto 0);
        -- ... Control2 through Control15
        Control15 : in std_logic_vector(31 downto 0)
    );
end entity;
```

**DPD-001 Implementation:**
- **File:** `rtl/DPD.vhd` (architecture `bpd_forge` of `CustomWrapper`)
- **Test Stub:** `rtl/CustomWrapper_test_stub.vhd`
- **Control Registers:** CR0-CR15 (16 × 32-bit registers)

### Future Standard: Custom Instrument

**Liquid Instruments is migrating to:** `Custom Instrument` entity (future standard)

**Proposed Entity Signature:**
```vhdl
entity Your_CustomApp_here is
    ------------------------------------------------------------------------
    -- Standard Control Signals 
    -- Priority Order: Reset > ClkEn > Enable
    ------------------------------------------------------------------------
    Clk    : in  std_logic;
    Reset  : in  std_logic;  -- Active-high reset (forces safe state)
    ClkEn  : in  std_logic;  -- Clock enable (freezes sequential logic)
    Enable : in  std_logic;  -- Functional enable (gates work)
   
    ------------------------------------------------------------------------
    -- MCC I/O (Native MCC Types)   
    ------------------------------------------------------------------------
    InputA : in signed(15 downto 0);
    InputB : in signed(15 downto 0);
    InputC : in signed(15 downto 0);

    OutputA : out signed(15 downto 0);
    OutputB : out signed(15 downto 0);
    OutputC : out signed(15 downto 0);

    ------------------------------------------------------------------------
    -- FORGE-Mandated State/Status vectors 
    ------------------------------------------------------------------------
    app_state_vector  : out std_logic_vector(5 downto 0);  -- FSM state (6-bit)
    app_status_vector : out std_logic_vector(7 downto 0);  -- App status (8-bit)
end entity;
```

**Key Differences:**
1. **Control Signals:** Custom Instrument has explicit `ClkEn` and `Enable` ports (vs. encoded in Control0)
2. **State/Status Vectors:** Custom Instrument has dedicated `app_state_vector` and `app_status_vector` ports
3. **Control Registers:** Custom Instrument may use different register mapping (TBD)

---

## Control Signal Priority

**Standard Priority Order:** `Reset > ClkEn > Enable`

This priority ensures safe operation:

1. **Reset** (highest priority)
   - Forces all sequential logic to safe state
   - Overrides all other control signals
   - Active-high reset

2. **ClkEn** (clock enable)
   - Freezes sequential logic (no state changes)
   - Combinational logic may still operate
   - Used for power management

3. **Enable** (functional enable)
   - Gates functional work
   - Sequential logic can change state
   - Used for user control

---

## DPD-001 Implementation

### CustomWrapper Architecture

**DPD-001 uses CustomWrapper with FORGE control scheme:**

**File:** `rtl/DPD.vhd`

```vhdl
architecture bpd_forge of CustomWrapper is
    -- FORGE Control Signals (extracted from CR0[31:29])
    signal forge_ready  : std_logic;  -- CR0[31]
    signal user_enable  : std_logic;  -- CR0[30]
    signal clk_enable   : std_logic;  -- CR0[29]
    
begin
    -- Extract FORGE control bits
    forge_ready <= Control0(31);
    user_enable <= Control0(30);
    clk_enable  <= Control0(29);
    
    -- Instantiate DPD shim layer
    DPD_SHIM_INST: entity WORK.DPD_shim
        port map (
            Clk   => Clk,
            Reset => Reset,
            -- ... other signals
        );
end architecture;
```

### FORGE Control Scheme

**DPD-001 implements FORGE control via Control0[31:29]:**

| Bit | Signal | Purpose |
|-----|--------|---------|
| CR0[31] | `forge_ready` | Set by MCC loader after deployment |
| CR0[30] | `user_enable` | User control (GUI toggle) |
| CR0[29] | `clk_enable` | Clock gating control |

**Safe Operation:**
- All three bits must be set (`0xE0000000`) for normal operation
- If any bit is clear, DPD enters safe state
- This provides triple-redundant safety gating

### State/Status Vectors

**DPD-001 outputs state/status via HVS (Hierarchical Voltage Scoring):**

**Implementation:** `rtl/DPD_shim.vhd`

```vhdl
-- HVS Encoder instantiation
HVS_ENCODER_INST: entity WORK.forge_hierarchical_encoder
    port map (
        clk           => Clk,
        reset         => Reset,
        state_vector  => fsm_state,      -- 6-bit FSM state
        status_vector => app_status,     -- 8-bit app status
        voltage_out   => OutputC         -- Encoded output
    );
```

**State Vector (6-bit):**
- Encodes FSM state from `DPD_main.vhd`
- States: INITIALIZING, IDLE, ARMED, FIRING, COOLDOWN, FAULT

**Status Vector (8-bit):**
- Encodes application-specific status
- Status[7] = fault flag (negates output)
- Status[6:0] = application status (0-127)

---

## Migration Path

### Current State (DPD-001)

**Uses:** CustomWrapper architecture
- Control signals encoded in Control0[31:29]
- State/status encoded in OutputC via HVS
- 16 control registers (CR0-CR15)

### Future Migration

**When Custom Instrument becomes standard:**

1. **Entity Change:**
   - Rename `CustomWrapper` → `DPD_CustomInstrument`
   - Add explicit `ClkEn` and `Enable` ports
   - Add explicit `app_state_vector` and `app_status_vector` ports

2. **Control Signal Migration:**
   - Extract `ClkEn` and `Enable` from Control0 → dedicated ports
   - Maintain backward compatibility if possible

3. **State/Status Migration:**
   - Move HVS encoding from OutputC → `app_state_vector`/`app_status_vector`
   - Keep OutputC for application-specific use

---

## Testing

### CustomWrapper Test Stub

**DPD-001 provides test stub for CocoTB:**

**File:** `rtl/CustomWrapper_test_stub.vhd`

```vhdl
entity CustomWrapper_test_stub is
    port (
        Clk    : in  std_logic;
        Reset  : in  std_logic;
        InputA : in  signed(15 downto 0);
        -- ... all CustomWrapper ports
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
# tests/sim/dpd/P1_basic.py

@cocotb.test()
async def test_dpd_p1(dut):
    """P1 test entry point"""
    tester = DPDBasicTests(dut)
    await tester.run_all_tests()
```

---

## See Also

- [Custom Wrapper](custom-wrapper.md) - Current MCC standard (detailed documentation)
- [Moku Cloud Compile](https://liquidinstruments.com/moku-cloud-compile/) - MCC documentation
- [MCC Examples](https://github.com/liquidinstruments/moku-examples/tree/main/mcc) - Official examples
- [FORGE Control Scheme](../CLAUDE.md#forge-control-scheme) - DPD-001 FORGE implementation

---

## Migration Notes

**Source:** FORGE-V5 `/docs/FORGE-V5/Custom Instrument/README.md`  
**Migration Date:** 2025-01-28  
**Changes:**
- Added CustomWrapper vs Custom Instrument comparison
- Documented DPD-001's CustomWrapper implementation
- Explained FORGE control scheme (CR0[31:29])
- Added HVS state/status encoding details
- Included migration path notes
- Added testing section with DPD-001 examples

---

**Last Updated:** 2025-11-26
**Maintainer:** Moku Instrument Forge Team
**Status:** Updated for API v4.0


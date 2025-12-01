---
created: 2025-11-30
status: DRAFT
---

# ENV_BBUF Allocation and Access Architecture

## Overview

This document describes the allocation, zeroing, and access architecture for the four ENV_BBUF (Environment BRAM Buffer) regions. The buffers are owned by `B0_BOOT_TOP` and are accessible to BOOT, BIOS, LOADER, and PROG modules.

## Design Principles

1. **Single Owner**: `B0_BOOT_TOP` owns all four BRAM arrays
2. **Centralized Zeroing**: Zeroing occurs during BOOT_P0 → BOOT_P1 transition
3. **Unified Addressing**: Simple buffer selector + word address scheme
4. **Access Control**: Write access restricted to LOADER; read access available to all modules

## Buffer Allocation

### Physical Structure

Four independent 4KB BRAM arrays, each containing 1024 × 32-bit words:

```vhdl
-- In B0_BOOT_TOP.vhd
type bram_t is array (0 to ENV_BBUF_WORDS-1) of std_logic_vector(ENV_BBUF_DATA_WIDTH-1 downto 0);

signal env_bbuf_0 : bram_t := (others => (others => '0'));
signal env_bbuf_1 : bram_t := (others => (others => '0'));
signal env_bbuf_2 : bram_t := (others => (others => '0'));
signal env_bbuf_3 : bram_t := (others => (others => '0'));
```

### BRAM Attributes

```vhdl
attribute ram_style : string;
attribute ram_style of env_bbuf_0 : signal is "block";
attribute ram_style of env_bbuf_1 : signal is "block";
attribute ram_style of env_bbuf_2 : signal is "block";
attribute ram_style of env_bbuf_3 : signal is "block";
```

## Addressing Scheme

### Unified Address Format

A simple 12-bit address format where:
- **Bits [11:10]**: Buffer selector (0-3, selects ENV_BBUF_0 through ENV_BBUF_3)
- **Bits [9:0]**: Word address within selected buffer (0-1023)

```
┌─────────────────────────────────────────────────────────┐
│ 12-bit Unified Address Format                           │
├─────────────────────────────────────────────────────────┤
│ bram_addr[11:10] │ bram_addr[9:0]                       │
│ Buffer Selector  │ Word Address                         │
│ (2 bits, 0-3)   │ (10 bits, 0-1023)                    │
└─────────────────────────────────────────────────────────┘
```

### Address Decoding

```vhdl
-- Extract buffer selector and word address
signal bram_sel : std_logic_vector(1 downto 0);
signal bram_word_addr : std_logic_vector(9 downto 0);

bram_sel <= bram_addr(11 downto 10);
bram_word_addr <= bram_addr(9 downto 0);
```

### Address Constants

```vhdl
-- Buffer base addresses (for clarity, though not strictly needed)
constant ENV_BBUF_0_BASE : unsigned(11 downto 0) := x"000";  -- 0x000-0x3FF
constant ENV_BBUF_1_BASE : unsigned(11 downto 0) := x"400";  -- 0x400-0x7FF
constant ENV_BBUF_2_BASE : unsigned(11 downto 0) := x"800";  -- 0x800-0xBFF
constant ENV_BBUF_3_BASE : unsigned(11 downto 0) := x"C00";  -- 0xC00-0xFFF
```

## Zeroing Logic

### Trigger

Zeroing occurs during the **BOOT_P0 → BOOT_P1** state transition, as specified in `docs/BOOT-FSM-spec.md`:

> **Actions:**
> - Zero all four ENV_BBUF regions (4x 4KB BRAM)

### Implementation

A state machine within `B0_BOOT_TOP` handles zeroing:

```vhdl
-- Zeroing state machine
type zero_state_t is (ZERO_IDLE, ZERO_ACTIVE);
signal zero_state : zero_state_t;
signal zero_addr : unsigned(11 downto 0);
signal zero_done : std_logic;
```

**State Machine Logic:**

1. **ZERO_IDLE**: Waiting for BOOT_P0 → BOOT_P1 transition
2. **ZERO_ACTIVE**: Actively zeroing all buffers
   - Iterate through all 4096 addresses (4 buffers × 1024 words)
   - Write zeros to all four buffers in parallel
   - Complete when `zero_addr = 4095`

**Transition Logic:**

```vhdl
-- Detect BOOT_P0 → BOOT_P1 transition
signal boot_p0_to_p1 : std_logic;
boot_p0_to_p1 <= '1' when boot_state = BOOT_STATE_P0 and 
                            boot_state_next = BOOT_STATE_P1 else '0';

-- Zeroing state machine
process(Clk)
begin
    if rising_edge(Clk) then
        if Reset = '1' then
            zero_state <= ZERO_IDLE;
            zero_addr <= (others => '0');
            zero_done <= '0';
        else
            case zero_state is
                when ZERO_IDLE =>
                    if boot_p0_to_p1 = '1' then
                        zero_state <= ZERO_ACTIVE;
                        zero_addr <= (others => '0');
                        zero_done <= '0';
                    end if;
                    
                when ZERO_ACTIVE =>
                    if zero_addr < 4095 then
                        zero_addr <= zero_addr + 1;
                    else
                        zero_state <= ZERO_IDLE;
                        zero_done <= '1';
                    end if;
            end case;
        end if;
    end if;
end process;
```

**Zeroing Write Logic:**

```vhdl
-- Write zeros to all buffers in parallel during zeroing
signal zero_we : std_logic;
zero_we <= '1' when zero_state = ZERO_ACTIVE else '0';

process(Clk)
begin
    if rising_edge(Clk) then
        if zero_we = '1' then
            -- Write to all buffers at same word offset
            env_bbuf_0(to_integer(zero_addr(9 downto 0))) <= (others => '0');
            env_bbuf_1(to_integer(zero_addr(9 downto 0))) <= (others => '0');
            env_bbuf_2(to_integer(zero_addr(9 downto 0))) <= (others => '0');
            env_bbuf_3(to_integer(zero_addr(9 downto 0))) <= (others => '0');
        end if;
    end if;
end process;
```

**Note**: Zeroing takes 4096 clock cycles (~33μs @ 125MHz). This is acceptable as it occurs once during boot initialization.

## Access Interfaces

### Write Interface (LOADER Only)

**Access Control**: Only active when `boot_state = BOOT_STATE_LOAD_ACTIVE`

**Interface Signals:**

```vhdl
-- Write interface (from LOADER)
signal bram_wr_addr : std_logic_vector(11 downto 0);  -- Unified address
signal bram_wr_data : std_logic_vector(31 downto 0);  -- Data to write
signal bram_wr_we   : std_logic;                      -- Write enable
```

**Write Logic:**

```vhdl
-- Write enable: only when LOADER is active
signal bram_wr_enable : std_logic;
bram_wr_enable <= '1' when boot_state = BOOT_STATE_LOAD_ACTIVE and 
                            bram_wr_we = '1' else '0';

-- Decode buffer selector
signal wr_sel : std_logic_vector(1 downto 0);
signal wr_word_addr : std_logic_vector(9 downto 0);
wr_sel <= bram_wr_addr(11 downto 10);
wr_word_addr <= bram_wr_addr(9 downto 0);

-- Write to selected buffer
process(Clk)
begin
    if rising_edge(Clk) then
        if bram_wr_enable = '1' then
            case wr_sel is
                when "00" => env_bbuf_0(to_integer(unsigned(wr_word_addr))) <= bram_wr_data;
                when "01" => env_bbuf_1(to_integer(unsigned(wr_word_addr))) <= bram_wr_data;
                when "10" => env_bbuf_2(to_integer(unsigned(wr_word_addr))) <= bram_wr_data;
                when "11" => env_bbuf_3(to_integer(unsigned(wr_word_addr))) <= bram_wr_data;
                when others => null;
            end case;
        end if;
    end if;
end process;
```

### Read Interface (All Modules)

**Access Control**: Available to all modules (BOOT, BIOS, LOADER, PROG)

**Interface Signals:**

```vhdl
-- Read interface (for all modules)
signal bram_rd_addr : std_logic_vector(11 downto 0);  -- Unified address
signal bram_rd_data : std_logic_vector(31 downto 0);  -- Read data
```

**Read Logic:**

```vhdl
-- Decode buffer selector
signal rd_sel : std_logic_vector(1 downto 0);
signal rd_word_addr : std_logic_vector(9 downto 0);
rd_sel <= bram_rd_addr(11 downto 10);
rd_word_addr <= bram_rd_addr(9 downto 0);

-- Read from selected buffer (registered for timing)
signal bram_rd_0, bram_rd_1, bram_rd_2, bram_rd_3 : std_logic_vector(31 downto 0);

process(Clk)
begin
    if rising_edge(Clk) then
        bram_rd_0 <= env_bbuf_0(to_integer(unsigned(rd_word_addr)));
        bram_rd_1 <= env_bbuf_1(to_integer(unsigned(rd_word_addr)));
        bram_rd_2 <= env_bbuf_2(to_integer(unsigned(rd_word_addr)));
        bram_rd_3 <= env_bbuf_3(to_integer(unsigned(rd_word_addr)));
    end if;
end process;

-- Mux read data based on buffer selector
with rd_sel select bram_rd_data <=
    bram_rd_0 when "00",
    bram_rd_1 when "01",
    bram_rd_2 when "10",
    bram_rd_3 when "11",
    (others => '0') when others;
```

## Module Access Patterns

### LOADER Module

**Access**: Write-only during `LOAD_ACTIVE` state

**Usage**: 
- Receives data via Control Registers (CR1-CR4)
- Writes to all four buffers in parallel at same word offset
- Uses unified addressing: `bram_wr_addr = {buffer_sel, word_offset}`

**Interface Update:**

```vhdl
-- L2_BUFF_LOADER port map (updated)
port map (
    -- ... existing ports ...
    -- Write interface (outputs to B0_BOOT_TOP)
    bram_wr_addr => bram_wr_addr,  -- Unified 12-bit address
    bram_wr_data => bram_wr_data,  -- 32-bit data
    bram_wr_we   => bram_wr_we     -- Write enable
);
```

**Internal Logic (in LOADER):**

```vhdl
-- LOADER writes to all buffers at same offset
-- Address format: {buffer_sel, offset[9:0]}
bram_wr_addr <= std_logic_vector(to_unsigned(buffer_sel, 2) & offset);
bram_wr_data <= CR_data;  -- CR1, CR2, CR3, or CR4
bram_wr_we <= '1' when state = LOAD_STATE_P1 and strobe_falling = '1' else '0';
```

### PROG Module

**Access**: Read-only after handoff to `PROG_ACTIVE`

**Usage**:
- Reads configuration data from ENV_BBUFs
- Uses unified addressing to access any buffer/word

**Interface:**

```vhdl
-- DPD_shim port map (updated)
port map (
    -- ... existing ports ...
    -- BRAM read interface
    bram_rd_addr => prog_bram_rd_addr,  -- From PROG logic
    bram_rd_data => prog_bram_rd_data   -- To PROG logic
);
```

### BIOS Module

**Access**: Read-only during `BIOS_ACTIVE` state

**Usage**:
- May read ENV_BBUFs for diagnostic purposes
- Uses unified addressing

**Interface:**

```vhdl
-- B1_BOOT_BIOS port map (updated, optional)
port map (
    -- ... existing ports ...
    -- BRAM read interface (optional, for future use)
    bram_rd_addr => bios_bram_rd_addr,
    bram_rd_data => bios_bram_rd_data
);
```

### BOOT Module

**Access**: Read-only (for future use, e.g., validation)

**Usage**:
- May read ENV_BBUFs for boot-time validation
- Uses unified addressing

## Address Space Summary

| Buffer | Address Range (hex) | Address Range (dec) | Size |
|--------|---------------------|---------------------|------|
| ENV_BBUF_0 | 0x000 - 0x3FF | 0 - 1023 | 4KB |
| ENV_BBUF_1 | 0x400 - 0x7FF | 1024 - 2047 | 4KB |
| ENV_BBUF_2 | 0x800 - 0xBFF | 2048 - 3071 | 4KB |
| ENV_BBUF_3 | 0xC00 - 0xFFF | 3072 - 4095 | 4KB |
| **Total** | **0x000 - 0xFFF** | **0 - 4095** | **16KB** |

## Implementation Checklist

- [ ] Move BRAM arrays from `L2_BUFF_LOADER` to `B0_BOOT_TOP`
- [ ] Implement zeroing state machine in `B0_BOOT_TOP`
- [ ] Add unified write interface (12-bit address)
- [ ] Add unified read interface (12-bit address)
- [ ] Update `L2_BUFF_LOADER` to use write interface (remove internal BRAMs)
- [ ] Update `DPD_shim` to use read interface (connect PROG access)
- [ ] Update constants in `forge_common_pkg.vhd` if needed
- [ ] Test zeroing during BOOT_P0 → BOOT_P1 transition
- [ ] Test LOADER write access
- [ ] Test PROG read access

## Design Rationale

### Why Unified Addressing?

1. **Simplicity**: Single address format for all modules
2. **Scalability**: Easy to extend to more buffers or larger sizes
3. **Clarity**: Address directly encodes buffer + word location
4. **Compatibility**: Can still use separate `sel` + `addr` if preferred

### Why Centralized Zeroing?

1. **Specification Compliance**: Matches `BOOT-FSM-spec.md` requirement
2. **Determinism**: Ensures clean state regardless of BRAM initialization
3. **Single Point of Control**: BOOT owns buffers, BOOT zeros them

### Why Write Access Control?

1. **Data Integrity**: Only LOADER should write (during LOAD_ACTIVE)
2. **Safety**: Prevents accidental overwrites from other modules
3. **Protocol Compliance**: Matches blind handshake protocol design

## See Also

- [BOOT-FSM-spec.md](../BOOT-FSM-spec.md) - BOOT FSM specification
- [LOAD-FSM-spec.md](../LOAD-FSM-spec.md) - LOADER protocol specification
- [forge_common_pkg.vhd](../../rtl/forge_common_pkg.vhd) - ENV_BBUF constants

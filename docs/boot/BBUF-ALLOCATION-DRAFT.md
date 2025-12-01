---
created: 2025-11-30
status: DRAFT
modified: 2025-11-30 19:19:12
accessed: 2025-12-01 15:14:39
---

# ENV_BBUF Allocation and Access Architecture

## Overview

This document describes the allocation, zeroing, and access architecture for the four ENV_BBUF (Environment BRAM Buffer) regions. The buffers are owned by `B0_BOOT_TOP` and are accessible to BOOT, BIOS, LOADER, and PROG modules.

## Design Principles

1. **Single Owner**: `B0_BOOT_TOP` owns all four BRAM arrays
2. **Centralized Zeroing**: Zeroing occurs during BOOT_P0 → BOOT_P1 transition
3. **Global Bank Select**: `BOOT_CR0[23:22]` (BANK_SEL) selects active buffer for reads
4. **Always 4 Buffers**: LOADER always writes all 4 buffers in parallel — no variable count
5. **Access Control**: Write access restricted to LOADER; read access available to all modules

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

## Global Bank Select (BOOT_CR0[23:22])

> **Authoritative Reference:** [BOOT-CR0.md](BOOT-CR0.md)

The **BANK_SEL** field in `BOOT_CR0[23:22]` provides a **global** buffer selector shared by all modules. This eliminates the need for each module to maintain its own buffer selection logic.

### How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                    Global Bank Select Flow                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Python Client                                                   │
│       │                                                          │
│       ▼                                                          │
│  set_control(0, CMD.RUN | (bank << 22))                         │
│       │                                                          │
│       ▼                                                          │
│  BOOT_CR0[23:22] = BANK_SEL ───────────────────────────────────┐│
│       │                                                         ││
│       ├──► LOADER: (writes all 4, ignores BANK_SEL for writes) ││
│       │                                                         ││
│       ├──► BIOS: reads from ENV_BBUF[BANK_SEL]                 ││
│       │                                                         ││
│       └──► PROG: reads from ENV_BBUF[BANK_SEL]                 ││
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### VHDL Integration

```vhdl
-- In B0_BOOT_TOP: extract BANK_SEL from BOOT_CR0
signal bank_sel : std_logic_vector(1 downto 0);
bank_sel <= Control0(BANK_SEL_HI downto BANK_SEL_LO);  -- [23:22]

-- Pass to read interface
bram_rd_sel <= bank_sel;
```

### Python Usage

```python
from py_tools.boot_constants import CMD, BOOT_CR0_BANK_SEL_LO

# Switch to buffer 2 during PROG execution
bank = 2
mcc.set_control(0, CMD.RUN | (bank << BOOT_CR0_BANK_SEL_LO))

# Read from the selected buffer via application logic
data = read_from_active_buffer()
```

### Why Global?

1. **Unified Access**: All modules see the same "active" buffer
2. **Dynamic Switching**: Python client can change banks at runtime
3. **Simplified Hardware**: No per-module buffer selection logic
4. **Consistent Semantics**: `BANK_SEL` always means "which buffer"

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

**Design Decision**: LOADER **always writes all 4 buffers** in parallel. There is no variable buffer count — simplifies protocol and hardware.

**Usage**:
- Receives data via Control Registers (CR1-CR4)
- On each strobe falling edge, writes all 4 CRs to all 4 buffers at the same word offset
- **Does NOT use BANK_SEL** for write addressing — writes are always parallel to all buffers

**Interface:**

```vhdl
-- L2_BUFF_LOADER outputs (directly to B0_BOOT_TOP BRAM ports)
signal loader_wr_data_0 : std_logic_vector(31 downto 0);  -- CR1 → ENV_BBUF_0
signal loader_wr_data_1 : std_logic_vector(31 downto 0);  -- CR2 → ENV_BBUF_1
signal loader_wr_data_2 : std_logic_vector(31 downto 0);  -- CR3 → ENV_BBUF_2
signal loader_wr_data_3 : std_logic_vector(31 downto 0);  -- CR4 → ENV_BBUF_3
signal loader_wr_addr   : std_logic_vector(9 downto 0);   -- Word offset (0-1023)
signal loader_wr_we     : std_logic;                      -- Write enable
```

**Internal Logic (in LOADER):**

```vhdl
-- LOADER writes all 4 buffers in parallel at same offset
loader_wr_data_0 <= Control1;  -- CR1
loader_wr_data_1 <= Control2;  -- CR2
loader_wr_data_2 <= Control3;  -- CR3
loader_wr_data_3 <= Control4;  -- CR4
loader_wr_addr   <= std_logic_vector(offset);  -- 10-bit word offset
loader_wr_we     <= '1' when state = LOAD_STATE_P1 and strobe_falling = '1' else '0';
```

**Note**: If fewer than 4 buffers contain meaningful data, the Python client simply zero-fills the unused CR registers. All 4 buffers are always written.

### PROG Module

**Access**: Read-only after handoff to `PROG_ACTIVE`

**Usage**:
- Reads configuration data from the **active buffer** (selected by BANK_SEL)
- Python client switches banks via `set_control(0, CMD.RUN | (bank << 22))`
- PROG logic provides word address; BANK_SEL provides buffer selection

**Interface:**

```vhdl
-- PROG read interface (in B0_BOOT_TOP)
-- bank_sel comes from BOOT_CR0[23:22], shared globally
signal prog_rd_word_addr : std_logic_vector(9 downto 0);  -- From PROG logic
signal prog_rd_data      : std_logic_vector(31 downto 0); -- To PROG logic

-- Read mux uses global bank_sel
prog_rd_data <= env_bbuf_array(to_integer(unsigned(bank_sel)))
                             (to_integer(unsigned(prog_rd_word_addr)));
```

### BIOS Module

**Access**: Read-only during `BIOS_ACTIVE` state

**Usage**:
- Reads from the **active buffer** (selected by BANK_SEL)
- May iterate through buffers by changing BANK_SEL via BOOT_CR0

**Interface:**

```vhdl
-- BIOS read interface (same pattern as PROG)
signal bios_rd_word_addr : std_logic_vector(9 downto 0);  -- From BIOS logic
signal bios_rd_data      : std_logic_vector(31 downto 0); -- To BIOS logic

-- Read mux uses global bank_sel
bios_rd_data <= env_bbuf_array(to_integer(unsigned(bank_sel)))
                              (to_integer(unsigned(bios_rd_word_addr)));
```

### BOOT Module

**Access**: Read-only (for future use, e.g., validation)

**Usage**:
- May read ENV_BBUFs for boot-time validation
- Uses global BANK_SEL for buffer selection

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
- [ ] Extract BANK_SEL from BOOT_CR0[23:22] in `B0_BOOT_TOP`
- [ ] Add parallel write interface (4× 32-bit data + 10-bit address + WE)
- [ ] Add read interface using global BANK_SEL
- [ ] Update `L2_BUFF_LOADER` to output 4 parallel data streams (remove internal BRAMs)
- [ ] Update `DPD_shim` to use read interface (connect PROG access)
- [ ] Update constants in `forge_common_pkg.vhd` (BANK_SEL_HI/LO)
- [ ] Update `py_tools/boot_constants.py` (BANK_SEL constants)
- [ ] Test zeroing during BOOT_P0 → BOOT_P1 transition
- [ ] Test LOADER parallel write to all 4 buffers
- [ ] Test PROG read with dynamic BANK_SEL switching

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

- [BOOT-CR0](docs/boot/BOOT-CR0.md) (auth) 

| [BOOT-CR0](docs/N/BOOT-CR0.md) (note)
- [BOOT-FSM-spec.md](../BOOT-FSM-spec.md) - BOOT FSM specification
- [LOAD-FSM-spec.md](../LOAD-FSM-spec.md) - LOADER protocol specification
- [forge_common_pkg.vhd](../../rtl/forge_common_pkg.vhd) - ENV_BBUF constants

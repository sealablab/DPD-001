--------------------------------------------------------------------------------
-- File: forge_common_pkg.vhd
-- Author: Moku Instrument Forge Team
-- Created: 2025-11-05
-- Modified: 2025-11-28
--
-- Description:
--   Common constants and types for the BOOT subsystem and CR0 privileged
--   control scheme. This package defines the authoritative bit allocations
--   for CR0 used by BOOT, BIOS, LOADER, and PROG modules.
--
-- Design Pattern:
--   This package is the single source of truth for CR0 bit definitions.
--   All modules in the BOOT subsystem (and applications) must use these
--   constants rather than hardcoding bit positions.
--
-- CR0 Register Map (Authoritative):
--   CR0[31:29] - RUN gate (R/U/N - must all be '1' for operation)
--   CR0[28:25] - Module select (P/B/L/R - mutually exclusive)
--   CR0[24]    - RET (return to BOOT_P1 from BIOS/LOADER)
--   CR0[23:22] - LOADER buffer count
--   CR0[21]    - LOADER data strobe
--   CR0[20:0]  - Reserved
--
-- References:
--   - docs/BOOT-FSM-spec.md (authoritative)
--   - docs/boot-process-terms.md (authoritative)
--   - docs/bootup-proposal/LOAD-FSM-spec.md (authoritative)
--------------------------------------------------------------------------------

library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;

package forge_common_pkg is

    ----------------------------------------------------------------------------
    -- RUN Gate (CR0[31:29])
    --
    -- All three bits must be '1' for the system to operate.
    -- Safe default: All-zero state keeps everything disabled.
    --
    -- Transition: BOOT_P0 → BOOT_P1 requires CR0[31:29] = "111"
    --
    -- Usage:
    --   run_ready   <= Control0(31);  -- R: Ready (platform settled)
    --   run_user    <= Control0(30);  -- U: User enable
    --   run_clk     <= Control0(29);  -- N: Clock enable
    --   run_active  <= run_ready and run_user and run_clk;
    ----------------------------------------------------------------------------
    constant RUN_READY_BIT : natural := 31;  -- R
    constant RUN_USER_BIT  : natural := 30;  -- U
    constant RUN_CLK_BIT   : natural := 29;  -- N

    -- Combined RUN value (0xE0000000)
    constant RUN_GATE_MASK : std_logic_vector(31 downto 0) := x"E0000000";

    ----------------------------------------------------------------------------
    -- Module Select (CR0[28:25])
    --
    -- Exactly ONE of these bits should be set to select a module.
    -- Multiple bits set = FAULT condition.
    -- Priority (if hardware encoder used): P > B > L > R
    --
    -- Commands:
    --   RUNP (CR0[28]=1) - Transfer to PROG (one-way)
    --   RUNB (CR0[27]=1) - Transfer to BIOS
    --   RUNL (CR0[26]=1) - Transfer to LOADER
    --   RUNR (CR0[25]=1) - Soft reset to BOOT_P0
    ----------------------------------------------------------------------------
    constant SEL_PROG_BIT   : natural := 28;  -- P: Program
    constant SEL_BIOS_BIT   : natural := 27;  -- B: BIOS
    constant SEL_LOADER_BIT : natural := 26;  -- L: Loader
    constant SEL_RESET_BIT  : natural := 25;  -- R: Reset

    -- Command values (combined with RUN gate)
    constant CMD_RUN  : std_logic_vector(31 downto 0) := x"E0000000";  -- Just RUN
    constant CMD_RUNP : std_logic_vector(31 downto 0) := x"F0000000";  -- RUN + P
    constant CMD_RUNB : std_logic_vector(31 downto 0) := x"E8000000";  -- RUN + B
    constant CMD_RUNL : std_logic_vector(31 downto 0) := x"E4000000";  -- RUN + L
    constant CMD_RUNR : std_logic_vector(31 downto 0) := x"E2000000";  -- RUN + R

    ----------------------------------------------------------------------------
    -- Return Control (CR0[24])
    --
    -- Used by BIOS and LOADER to return control to BOOT_P1.
    -- PROG cannot return (one-way handoff).
    ----------------------------------------------------------------------------
    constant RET_BIT : natural := 24;

    constant CMD_RET : std_logic_vector(31 downto 0) := x"E1000000";  -- RUN + RET

    ----------------------------------------------------------------------------
    -- LOADER Control (CR0[23:21])
    --
    -- CR0[23:22] - Buffer count (00=1, 01=2, 10=3, 11=4)
    -- CR0[21]    - Data strobe (falling edge triggers action)
    ----------------------------------------------------------------------------
    constant LOADER_BUFCNT_HI  : natural := 23;
    constant LOADER_BUFCNT_LO  : natural := 22;
    constant LOADER_STROBE_BIT : natural := 21;

    ----------------------------------------------------------------------------
    -- BOOT FSM States (6-bit encoding)
    --
    -- Internal BOOT FSM states. For HVS encoding, these map to global S values:
    --   BOOT_P0          -> S=0 (0.0V)
    --   BOOT_P1          -> S=1 (0.030V)
    --   BOOT_FAULT       -> S=2 (0.060V, negated if status[7]=1)
    --   BOOT_BIOS_ACTIVE -> S=8 (BIOS context, not BOOT)
    --   BOOT_LOAD_ACTIVE -> S=16 (LOADER context, not BOOT)
    --   BOOT_PROG_ACTIVE -> PROG context (out of scope)
    ----------------------------------------------------------------------------
    constant BOOT_STATE_P0          : std_logic_vector(5 downto 0) := "000000";
    constant BOOT_STATE_P1          : std_logic_vector(5 downto 0) := "000001";
    constant BOOT_STATE_BIOS_ACTIVE : std_logic_vector(5 downto 0) := "000010";
    constant BOOT_STATE_LOAD_ACTIVE : std_logic_vector(5 downto 0) := "000011";
    constant BOOT_STATE_PROG_ACTIVE : std_logic_vector(5 downto 0) := "000100";
    constant BOOT_STATE_FAULT       : std_logic_vector(5 downto 0) := "111111";
    
    -- BOOT HVS global state mapping (S values 0-7)
    constant BOOT_HVS_S_P0    : natural := 0;
    constant BOOT_HVS_S_P1    : natural := 1;
    constant BOOT_HVS_S_FAULT : natural := 2;
    -- S=3-7 reserved for BOOT expansion

    ----------------------------------------------------------------------------
    -- LOADER FSM States (6-bit encoding)
    --
    -- Internal LOADER FSM states. For HVS encoding, these map to global S values:
    --   LOAD_P0    -> S=16 (0.480V)
    --   LOAD_P1    -> S=17 (0.510V)
    --   LOAD_P2    -> S=18 (0.541V)
    --   LOAD_P3    -> S=19 (0.571V)
    --   LOAD_FAULT -> S=20 (0.601V, negated if status[7]=1)
    --   S=21-23 reserved for LOADER expansion
    ----------------------------------------------------------------------------
    constant LOAD_STATE_P0    : std_logic_vector(5 downto 0) := "000000";  -- Setup
    constant LOAD_STATE_P1    : std_logic_vector(5 downto 0) := "000001";  -- Transfer
    constant LOAD_STATE_P2    : std_logic_vector(5 downto 0) := "000010";  -- Validate
    constant LOAD_STATE_P3    : std_logic_vector(5 downto 0) := "000011";  -- Complete
    constant LOAD_STATE_FAULT : std_logic_vector(5 downto 0) := "111111";  -- CRC error
    
    -- LOADER HVS global state mapping (S values 16-23)
    constant LOADER_HVS_S_P0    : natural := 16;
    constant LOADER_HVS_S_P1    : natural := 17;
    constant LOADER_HVS_S_P2    : natural := 18;
    constant LOADER_HVS_S_P3    : natural := 19;
    constant LOADER_HVS_S_FAULT : natural := 20;
    -- S=21-23 reserved for LOADER expansion

    ----------------------------------------------------------------------------
    -- ENV_BBUF Parameters
    --
    -- Four 4KB BRAM buffers for environment/configuration data.
    -- Allocated by BOOT, populated by LOADER, used by PROG.
    ----------------------------------------------------------------------------
    constant ENV_BBUF_COUNT      : natural := 4;
    constant ENV_BBUF_SIZE_BYTES : natural := 4096;
    constant ENV_BBUF_WORDS      : natural := 1024;  -- 4096 / 4
    constant ENV_BBUF_ADDR_WIDTH : natural := 10;    -- log2(1024)
    constant ENV_BBUF_DATA_WIDTH : natural := 32;

    ----------------------------------------------------------------------------
    -- HVS Parameters (Pre-PROG Band)
    --
    -- Pre-PROG encoding uses number-theory properties for easy decoding:
    --   DIGITAL_UNITS_PER_STATE = 197 (prime)
    --   DIGITAL_UNITS_PER_STATUS = 11 (prime, coprime with 197)
    --
    -- This ensures all pre-PROG states (BOOT/BIOS/LOADER) stay under 1.0V.
    -- PROG applications use their own encoding (out of scope).
    --
    -- Reference: docs/HVS-encoding-scheme.md
    ----------------------------------------------------------------------------
    constant HVS_PRE_STATE_UNITS  : natural := 197;  -- Digital units per state (~30mV @ ±5V FS)
    constant HVS_PRE_STATUS_UNITS : natural := 11;   -- Digital units per status LSB (~1.7mV)
    
    -- Legacy constants (for backward compatibility during migration)
    constant HVS_BOOT_UNITS_PER_STATE : natural := 1311;  -- Deprecated: use HVS_PRE_STATE_UNITS
    constant HVS_PROG_UNITS_PER_STATE : natural := 3277;  -- PROG encoding (out of scope)

    ----------------------------------------------------------------------------
    -- CRC-16-CCITT Parameters
    --
    -- Used by LOADER for buffer validation.
    ----------------------------------------------------------------------------
    constant CRC16_POLYNOMIAL : std_logic_vector(15 downto 0) := x"1021";
    constant CRC16_INIT       : std_logic_vector(15 downto 0) := x"FFFF";

    ----------------------------------------------------------------------------
    -- Network Synchronization
    --
    -- STATE_SYNC_SAFE is the canonical "safe to update registers" state.
    -- For BOOT context, this is BOOT_P0 or the module's P0 state.
    ----------------------------------------------------------------------------
    constant STATE_SYNC_SAFE : std_logic_vector(5 downto 0) := "000000";

    ----------------------------------------------------------------------------
    -- Helper Functions
    ----------------------------------------------------------------------------

    -- Check if RUN gate is fully enabled
    function is_run_active(cr0 : std_logic_vector(31 downto 0)) return boolean;

    -- Extract module select bits and check for valid (single) selection
    function get_module_select(cr0 : std_logic_vector(31 downto 0))
        return std_logic_vector;  -- Returns 4-bit P/B/L/R

    -- Check if exactly one module select bit is set
    function is_valid_select(cr0 : std_logic_vector(31 downto 0)) return boolean;

    -- Extract LOADER buffer count (0-3, representing 1-4 buffers)
    function get_loader_bufcnt(cr0 : std_logic_vector(31 downto 0))
        return natural;

end package forge_common_pkg;

package body forge_common_pkg is

    -- Check if all RUN gate bits are set
    function is_run_active(cr0 : std_logic_vector(31 downto 0)) return boolean is
    begin
        return cr0(RUN_READY_BIT) = '1' and
               cr0(RUN_USER_BIT) = '1' and
               cr0(RUN_CLK_BIT) = '1';
    end function;

    -- Extract module select bits (P/B/L/R)
    function get_module_select(cr0 : std_logic_vector(31 downto 0))
        return std_logic_vector is
    begin
        return cr0(SEL_PROG_BIT downto SEL_RESET_BIT);
    end function;

    -- Check if exactly one module select bit is set (valid selection)
    function is_valid_select(cr0 : std_logic_vector(31 downto 0)) return boolean is
        variable sel : std_logic_vector(3 downto 0);
    begin
        sel := cr0(SEL_PROG_BIT downto SEL_RESET_BIT);
        case sel is
            when "1000" => return true;  -- RUNP only
            when "0100" => return true;  -- RUNB only
            when "0010" => return true;  -- RUNL only
            when "0001" => return true;  -- RUNR only
            when "0000" => return true;  -- No selection (stay in current state)
            when others => return false; -- Multiple bits = invalid
        end case;
    end function;

    -- Extract LOADER buffer count from CR0[23:22]
    function get_loader_bufcnt(cr0 : std_logic_vector(31 downto 0))
        return natural is
    begin
        return to_integer(unsigned(cr0(LOADER_BUFCNT_HI downto LOADER_BUFCNT_LO)));
    end function;

end package body forge_common_pkg;

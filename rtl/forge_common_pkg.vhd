--------------------------------------------------------------------------------
-- File: forge_common_pkg.vhd
-- Author: Moku Instrument Forge Team
-- Created: 2025-11-05
--
-- Description:
--   Common constants and types for Forge MCC infrastructure.
--   Defines the FORGE_READY control scheme, BRAM interface parameters,
--   and application register ranges.
--
-- Design Pattern:
--   This package is shared across ALL forge-apps and provides the foundation
--   for the 3-layer Forge architecture:
--     Layer 1: MCC_TOP_forge_loader.vhd (uses this package)
--     Layer 2: <AppName>_forge_shim.vhd (uses this package)
--     Layer 3: <AppName>_forge_main.vhd (MCC-agnostic, doesn't use this)
--
-- Register Map:
--   CR0[31:29] - FORGE_READY control scheme (3-bit)
--   CR10-CR14  - BRAM loader protocol (5 registers)
--   CR1-CR10   - Application registers (10 registers)
--
-- Migration Note:
--   This is the forge-vhdl equivalent of volo_common_pkg.vhd.
--   Functionality is identical; naming changed for consistency with
--   the forge-vhdl component ecosystem.
--
-- References:
--   - libs/forge-vhdl/CLAUDE.md
--   - external_Example/volo_common_pkg.vhd (original pattern)
--------------------------------------------------------------------------------

library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;

package forge_common_pkg is

    ----------------------------------------------------------------------------
    -- FORGE_READY Control Scheme (CR0[31:29])
    --
    -- Safe default: All-zero state keeps module disabled (bit 31=0)
    --
    -- Usage in Top.vhd:
    --   forge_ready  <= Control0(31);  -- Set by loader after deployment
    --   user_enable  <= Control0(30);  -- User-controlled enable/disable
    --   clk_enable   <= Control0(29);  -- Clock gating for sequential logic
    --   global_enable <= forge_ready and user_enable and clk_enable and loader_done;
    --
    -- Initialization Sequence:
    --   1. Power-on: Control0 = 0x00000000 → All disabled (SAFE)
    --   2. Loader sets Control0[31] = 1 (forge_ready)
    --   3. BRAM loader completes (loader_done = 1)
    --   4. User sets Control0[30] = 1 (user_enable)
    --   5. User sets Control0[29] = 1 (clk_enable)
    --   6. Module operates (global_enable = 1)
    ----------------------------------------------------------------------------
    constant FORGE_READY_BIT  : natural := 31;
    constant USER_ENABLE_BIT  : natural := 30;
    constant CLK_ENABLE_BIT   : natural := 29;

    ----------------------------------------------------------------------------
    -- BRAM Loader Protocol (CR10-CR14)
    --
    -- 4KB buffer = 1024 words × 32 bits
    -- Address width: 12 bits (2^12 = 4096 bytes / 4 bytes per word = 1024 words)
    -- Data width: 32 bits (matches Control Register width)
    --
    -- The forge_bram_loader FSM uses Control10-Control14 to stream data
    -- into the 4KB BRAM buffer during deployment initialization.
    ----------------------------------------------------------------------------
    constant BRAM_ADDR_WIDTH : natural := 12;  -- 4KB addressing
    constant BRAM_DATA_WIDTH : natural := 32;  -- Control Register width

    ----------------------------------------------------------------------------
    -- Application Register Range (CR1-CR10)
    --
    -- MCC provides 16 control registers (CR0-CR15)
    -- CR0 reserved for FORGE control scheme (bits 31:29)
    -- CR1-CR10 available for application (10 registers)
    -- CR11-CR15 unused (future expansion)
    --
    -- These are mapped to friendly signal names in the generated shim layer:
    --   Example: "arm_enable" → arm_enable : std_logic
    ----------------------------------------------------------------------------
    constant APP_REG_MIN : natural := 1;
    constant APP_REG_MAX : natural := 10;

    ----------------------------------------------------------------------------
    -- Helper Functions
    ----------------------------------------------------------------------------

    -- Combine FORGE_READY control bits into global enable signal
    -- Returns '1' only when ALL four conditions are met (safe by default)
    function combine_forge_ready(
        forge_ready  : std_logic;
        user_enable  : std_logic;
        clk_enable   : std_logic;
        loader_done  : std_logic
    ) return std_logic;

end package forge_common_pkg;

package body forge_common_pkg is

    -- Combine all 4 ready conditions for global enable
    -- Implements: global_enable = forge_ready AND user_enable AND clk_enable AND loader_done
    function combine_forge_ready(
        forge_ready  : std_logic;
        user_enable  : std_logic;
        clk_enable   : std_logic;
        loader_done  : std_logic
    ) return std_logic is
    begin
        return forge_ready and user_enable and clk_enable and loader_done;
    end function;

end package body forge_common_pkg;

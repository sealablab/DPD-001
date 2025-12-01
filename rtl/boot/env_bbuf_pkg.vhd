---
-- File: env_bbuf_pkg.vhd
-- Type: rtl_vhdl
-- Author: jellch
-- Created: 2025-12-01
-- Modified: 2025-12-01 15:14:57
-- Code_link: "[[rtl/boot/env_bbuf_pkg.vhd|env_bbuf_pkg.vhd]]"
-- Doc_link: "[[rtl/boot/env_bbuf_pkg.vhd.md|env_bbuf_pkg.vhd.md]]"
-- Self_link: "[[rtl/boot/env_bbuf_pkg.vhd|env_bbuf_pkg.vhd]]"
---


--------------------------------------------------------------------------------
-- Description:
--   Package defining types and records for ENV_BBUF (Environment BRAM Buffer)
--   infrastructure. This package provides:
--   - BRAM array type definition
--   - Write interface record (LOADER -> ENV_BBUF)
--   - Read interface record (BIOS/PROG -> ENV_BBUF)
--   - Address/data subtypes for type safety
--
-- Design Goals:
--   1. Centralize ENV_BBUF type definitions in one place
--   2. Enable type-safe port mapping via records
--   3. Support both GHDL simulation and MCC synthesis
--   4. Keep memory allocation separate from FSM logic
--
-- Usage:
--   library WORK;
--   use WORK.env_bbuf_pkg.all;
--
-- Reference: docs/boot/BBUF-ALLOCATION-DRAFT.md
--------------------------------------------------------------------------------

library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;

package env_bbuf_pkg is

    ----------------------------------------------------------------------------
    -- Constants
    ----------------------------------------------------------------------------

    -- Buffer dimensions (4KB per buffer = 1024 x 32-bit words)
    constant ENV_BBUF_WORDS      : natural := 1024;
    constant ENV_BBUF_DATA_WIDTH : natural := 32;
    constant ENV_BBUF_ADDR_WIDTH : natural := 10;   -- log2(1024)

    -- Number of buffers
    constant ENV_BBUF_COUNT      : natural := 4;
    constant ENV_BBUF_SEL_WIDTH  : natural := 2;    -- log2(4)

    ----------------------------------------------------------------------------
    -- Subtypes (for type safety)
    ----------------------------------------------------------------------------

    subtype env_bbuf_addr_t is std_logic_vector(ENV_BBUF_ADDR_WIDTH-1 downto 0);
    subtype env_bbuf_data_t is std_logic_vector(ENV_BBUF_DATA_WIDTH-1 downto 0);
    subtype env_bbuf_sel_t  is std_logic_vector(ENV_BBUF_SEL_WIDTH-1 downto 0);

    ----------------------------------------------------------------------------
    -- BRAM Array Type
    ----------------------------------------------------------------------------

    -- Single buffer: 1024 x 32-bit words
    type env_bbuf_t is array (0 to ENV_BBUF_WORDS-1) of env_bbuf_data_t;

    ----------------------------------------------------------------------------
    -- Write Interface Record (LOADER -> ENV_BBUF)
    --
    -- LOADER writes to all 4 buffers in parallel. Each strobe writes
    -- 4 data words (from CR1-CR4) to the same address in all buffers.
    ----------------------------------------------------------------------------

    type env_bbuf_wr_t is record
        data_0 : env_bbuf_data_t;   -- Data for buffer 0 (from CR1)
        data_1 : env_bbuf_data_t;   -- Data for buffer 1 (from CR2)
        data_2 : env_bbuf_data_t;   -- Data for buffer 2 (from CR3)
        data_3 : env_bbuf_data_t;   -- Data for buffer 3 (from CR4)
        addr   : env_bbuf_addr_t;   -- Word address (0-1023)
        we     : std_logic;         -- Write enable (single cycle pulse)
    end record env_bbuf_wr_t;

    -- Default/init value for write interface
    constant ENV_BBUF_WR_INIT : env_bbuf_wr_t := (
        data_0 => (others => '0'),
        data_1 => (others => '0'),
        data_2 => (others => '0'),
        data_3 => (others => '0'),
        addr   => (others => '0'),
        we     => '0'
    );

    ----------------------------------------------------------------------------
    -- Read Interface
    --
    -- Read uses global BANK_SEL to select which buffer to read from.
    -- Address and bank_sel are inputs; data is output (1-cycle latency).
    ----------------------------------------------------------------------------

    -- Note: Read interface is simpler - just addr + bank_sel inputs, data output
    -- We don't use a record here since data flows the opposite direction

    ----------------------------------------------------------------------------
    -- Zeroing Control Interface
    ----------------------------------------------------------------------------

    type env_bbuf_zero_t is record
        start : std_logic;          -- Pulse to start zeroing
        done  : std_logic;          -- High when zeroing complete
    end record env_bbuf_zero_t;

    constant ENV_BBUF_ZERO_INIT : env_bbuf_zero_t := (
        start => '0',
        done  => '0'
    );

end package env_bbuf_pkg;

package body env_bbuf_pkg is
    -- No body needed for this package (types/constants only)
end package body env_bbuf_pkg;

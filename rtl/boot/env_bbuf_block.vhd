---
-- File: env_bbuf_block.vhd
-- Type: rtl_vhdl
-- Author: jellch
-- Created: 2025-12-01
-- Modified: 2025-12-01 15:15:39
-- Code_link: "[[rtl/boot/env_bbuf_block.vhd|env_bbuf_block.vhd]]"
-- Doc_link: "[[rtl/boot/env_bbuf_block.vhd.md|env_bbuf_block.vhd.md]]"
-- Self_link: "[[rtl/boot/env_bbuf_block.vhd|env_bbuf_block.vhd]]"
---


--------------------------------------------------------------------------------
-- Description:
--   ENV_BBUF Block - Encapsulates 4x 4KB BRAM buffers with zeroing FSM.
--
-- Block RAM Inference (Xilinx UG901 Template):
--   Uses "shared variable" with ":=" assignment per Xilinx recommendation.
--   Each buffer follows Simple Dual-Port pattern:
--   - Port A: Write-only (clocked, with write enable)
--   - Port B: Read-only (clocked, always enabled)
--
-- Reference: Xilinx UG901 "Vivado Design Suite User Guide: Synthesis"
--            Section "RAM HDL Coding Techniques"
--------------------------------------------------------------------------------

library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;

library WORK;
use WORK.env_bbuf_pkg.all;

entity env_bbuf_block is
    port (
        Clk        : in  std_logic;
        Reset      : in  std_logic;

        -- Zeroing control
        zero_start : in  std_logic;
        zero_done  : out std_logic;

        -- Write interface (from LOADER, parallel to all 4 buffers)
        wr         : in  env_bbuf_wr_t;

        -- Read interface (bank-selected)
        rd_addr    : in  env_bbuf_addr_t;
        rd_sel     : in  env_bbuf_sel_t;
        rd_data    : out env_bbuf_data_t
    );
end entity env_bbuf_block;

architecture rtl of env_bbuf_block is

    ----------------------------------------------------------------------------
    -- BRAM Type Definition (Xilinx-style: descending range)
    ----------------------------------------------------------------------------

    constant RAM_DEPTH : integer := ENV_BBUF_WORDS;  -- 1024
    constant RAM_WIDTH : integer := ENV_BBUF_DATA_WIDTH;  -- 32

    type ram_type is array (RAM_DEPTH-1 downto 0) of
        std_logic_vector(RAM_WIDTH-1 downto 0);

    ----------------------------------------------------------------------------
    -- BRAM Arrays as Shared Variables (Xilinx UG901 pattern)
    --
    -- Using shared variable with := assignment is the recommended pattern
    -- for Block RAM inference in Vivado.
    ----------------------------------------------------------------------------

    shared variable env_bbuf_0 : ram_type := (others => (others => '0'));
    shared variable env_bbuf_1 : ram_type := (others => (others => '0'));
    shared variable env_bbuf_2 : ram_type := (others => (others => '0'));
    shared variable env_bbuf_3 : ram_type := (others => (others => '0'));

    -- Request Block RAM inference
    attribute ram_style : string;
    attribute ram_style of env_bbuf_0 : variable is "block";
    attribute ram_style of env_bbuf_1 : variable is "block";
    attribute ram_style of env_bbuf_2 : variable is "block";
    attribute ram_style of env_bbuf_3 : variable is "block";

    ----------------------------------------------------------------------------
    -- Zeroing FSM
    ----------------------------------------------------------------------------

    type zero_state_t is (ZERO_IDLE, ZERO_ACTIVE, ZERO_DONE_STATE);
    signal zero_state : zero_state_t;
    signal zero_addr  : unsigned(ENV_BBUF_ADDR_WIDTH-1 downto 0);
    signal zeroing_we : std_logic;

    ----------------------------------------------------------------------------
    -- Unified Write Interface
    ----------------------------------------------------------------------------

    signal wr_addr   : std_logic_vector(ENV_BBUF_ADDR_WIDTH-1 downto 0);
    signal wr_data_0 : std_logic_vector(RAM_WIDTH-1 downto 0);
    signal wr_data_1 : std_logic_vector(RAM_WIDTH-1 downto 0);
    signal wr_data_2 : std_logic_vector(RAM_WIDTH-1 downto 0);
    signal wr_data_3 : std_logic_vector(RAM_WIDTH-1 downto 0);
    signal wr_we     : std_logic;

    ----------------------------------------------------------------------------
    -- Read Data Registers (one per buffer)
    ----------------------------------------------------------------------------

    signal rd_data_0 : std_logic_vector(RAM_WIDTH-1 downto 0);
    signal rd_data_1 : std_logic_vector(RAM_WIDTH-1 downto 0);
    signal rd_data_2 : std_logic_vector(RAM_WIDTH-1 downto 0);
    signal rd_data_3 : std_logic_vector(RAM_WIDTH-1 downto 0);
    signal rd_sel_r  : std_logic_vector(1 downto 0);

begin

    ----------------------------------------------------------------------------
    -- Zeroing FSM
    ----------------------------------------------------------------------------

    process(Clk)
    begin
        if rising_edge(Clk) then
            if Reset = '1' then
                zero_state <= ZERO_IDLE;
                zero_addr  <= (others => '0');
            else
                case zero_state is
                    when ZERO_IDLE =>
                        if zero_start = '1' then
                            zero_state <= ZERO_ACTIVE;
                            zero_addr  <= (others => '0');
                        end if;

                    when ZERO_ACTIVE =>
                        if zero_addr = RAM_DEPTH - 1 then
                            zero_state <= ZERO_DONE_STATE;
                        else
                            zero_addr <= zero_addr + 1;
                        end if;

                    when ZERO_DONE_STATE =>
                        if zero_start = '1' then
                            zero_state <= ZERO_ACTIVE;
                            zero_addr  <= (others => '0');
                        end if;
                end case;
            end if;
        end if;
    end process;

    zeroing_we <= '1' when zero_state = ZERO_ACTIVE else '0';
    zero_done  <= '1' when zero_state = ZERO_DONE_STATE else '0';

    ----------------------------------------------------------------------------
    -- Write Address/Data Mux (combinatorial)
    ----------------------------------------------------------------------------

    wr_addr <= std_logic_vector(zero_addr) when zeroing_we = '1' else wr.addr;

    wr_data_0 <= (others => '0') when zeroing_we = '1' else wr.data_0;
    wr_data_1 <= (others => '0') when zeroing_we = '1' else wr.data_1;
    wr_data_2 <= (others => '0') when zeroing_we = '1' else wr.data_2;
    wr_data_3 <= (others => '0') when zeroing_we = '1' else wr.data_3;

    wr_we <= zeroing_we or wr.we;

    ----------------------------------------------------------------------------
    -- BRAM 0: Simple Dual-Port (Xilinx UG901 Template)
    --   Port A: Write (separate process)
    --   Port B: Read (separate process)
    ----------------------------------------------------------------------------

    -- Port A: Write
    process(Clk)
    begin
        if rising_edge(Clk) then
            if wr_we = '1' then
                env_bbuf_0(to_integer(unsigned(wr_addr))) := wr_data_0;
            end if;
        end if;
    end process;

    -- Port B: Read
    process(Clk)
    begin
        if rising_edge(Clk) then
            rd_data_0 <= env_bbuf_0(to_integer(unsigned(rd_addr)));
        end if;
    end process;

    ----------------------------------------------------------------------------
    -- BRAM 1: Simple Dual-Port
    ----------------------------------------------------------------------------

    process(Clk)
    begin
        if rising_edge(Clk) then
            if wr_we = '1' then
                env_bbuf_1(to_integer(unsigned(wr_addr))) := wr_data_1;
            end if;
        end if;
    end process;

    process(Clk)
    begin
        if rising_edge(Clk) then
            rd_data_1 <= env_bbuf_1(to_integer(unsigned(rd_addr)));
        end if;
    end process;

    ----------------------------------------------------------------------------
    -- BRAM 2: Simple Dual-Port
    ----------------------------------------------------------------------------

    process(Clk)
    begin
        if rising_edge(Clk) then
            if wr_we = '1' then
                env_bbuf_2(to_integer(unsigned(wr_addr))) := wr_data_2;
            end if;
        end if;
    end process;

    process(Clk)
    begin
        if rising_edge(Clk) then
            rd_data_2 <= env_bbuf_2(to_integer(unsigned(rd_addr)));
        end if;
    end process;

    ----------------------------------------------------------------------------
    -- BRAM 3: Simple Dual-Port
    ----------------------------------------------------------------------------

    process(Clk)
    begin
        if rising_edge(Clk) then
            if wr_we = '1' then
                env_bbuf_3(to_integer(unsigned(wr_addr))) := wr_data_3;
            end if;
        end if;
    end process;

    process(Clk)
    begin
        if rising_edge(Clk) then
            rd_data_3 <= env_bbuf_3(to_integer(unsigned(rd_addr)));
        end if;
    end process;

    ----------------------------------------------------------------------------
    -- Output Mux: Select which buffer's data to output
    ----------------------------------------------------------------------------

    -- Register the selector to match read latency
    process(Clk)
    begin
        if rising_edge(Clk) then
            rd_sel_r <= rd_sel;
        end if;
    end process;

    -- Combinatorial mux after registered read
    with rd_sel_r select rd_data <=
        rd_data_0 when "00",
        rd_data_1 when "01",
        rd_data_2 when "10",
        rd_data_3 when "11",
        (others => '0') when others;

end architecture rtl;

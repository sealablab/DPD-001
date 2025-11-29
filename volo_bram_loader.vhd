--------------------------------------------------------------------------------
-- File: volo_bram_loader.vhd
-- Author: Volo Team
-- Created: 2025-01-25
--
-- Description:
--   BRAM Loader FSM for VoloApp infrastructure.
--   Streams 4KB buffer data via Control Registers CR10-CR14.
--
-- Protocol (CR10-CR14):
--   Control10[0]     : Start signal (write 1 to begin loading)
--   Control10[31:16] : Word count (number of 32-bit words to load, max 1024)
--   Control11[11:0]  : Address to write (12-bit, 0-4095 bytes / 4 = 0-1023 words)
--   Control12[31:0]  : Data to write (32-bit word)
--   Control13[0]     : Write strobe (pulse high to commit write)
--   Control14        : Reserved for future use
--
-- Usage Pattern (Python/deployment script):
--   1. Set Control10 = (word_count << 16) | 0x0001  # Start + count
--   2. For each word:
--      a. Set Control11 = address
--      b. Set Control12 = data
--      c. Set Control13 = 0x0001  # Write strobe
--      d. Set Control13 = 0x0000  # Clear strobe
--   3. Wait for 'done' signal to assert
--
-- State Machine:
--   IDLE     → Wait for Control10[0] = 1
--   LOADING  → Monitor Control13[0] for write strobes
--   DONE     → Assert done signal, wait for reset
--
-- Design Notes:
--   - Simple edge-detected write protocol (no handshaking)
--   - Assumes deployment script controls timing
--   - BRAM is always-enabled (can be accessed by app after loading)
--   - Done signal is sticky (cleared only on reset)
--------------------------------------------------------------------------------

library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;

library WORK;
use WORK.volo_common_pkg.all;
use WORK.volo_voltage_pkg.all;

entity volo_bram_loader is
    port (
        -- Clock and Reset
        Clk       : in  std_logic;
        Reset     : in  std_logic;  -- Active-high reset

        -- Control Registers (from MCC)
        Control10 : in  std_logic_vector(31 downto 0);  -- Start + word count
        Control11 : in  std_logic_vector(31 downto 0);  -- Address
        Control12 : in  std_logic_vector(31 downto 0);  -- Data
        Control13 : in  std_logic_vector(31 downto 0);  -- Write strobe
        Control14 : in  std_logic_vector(31 downto 0);  -- Reserved

        -- BRAM Interface (to application)
        bram_addr : out std_logic_vector(11 downto 0);  -- 4KB address space
        bram_data : out std_logic_vector(31 downto 0);  -- 32-bit data
        bram_we   : out std_logic;                      -- Write enable

        -- Status
        done      : out std_logic;  -- Asserted when loading complete

        -- Debug Output (FSM Observer)
        voltage_debug_out : out signed(15 downto 0)  -- Oscilloscope debug voltage
    );
end entity volo_bram_loader;

architecture rtl of volo_bram_loader is

    -- FSM States (use std_logic_vector for Verilog portability)
    constant IDLE    : std_logic_vector(1 downto 0) := "00";
    constant LOADING : std_logic_vector(1 downto 0) := "01";
    constant DONE_ST : std_logic_vector(1 downto 0) := "10";

    signal state      : std_logic_vector(1 downto 0);
    signal next_state : std_logic_vector(1 downto 0);

    -- Control signals
    signal start_loading : std_logic;
    signal write_strobe  : std_logic;
    signal word_count    : unsigned(15 downto 0);
    signal words_written : unsigned(15 downto 0);

    -- Write strobe edge detection
    signal write_strobe_prev : std_logic;
    signal write_strobe_edge : std_logic;

    -- Done flag (sticky until reset)
    signal done_internal : std_logic;

    -- FSM Observer signals
    signal state_6bit : std_logic_vector(5 downto 0);

begin

    ----------------------------------------------------------------------------
    -- Extract control signals from Control Registers
    ----------------------------------------------------------------------------
    start_loading <= Control10(0);
    word_count    <= unsigned(Control10(31 downto 16));
    write_strobe  <= Control13(0);

    ----------------------------------------------------------------------------
    -- Edge detection for write strobe (rising edge)
    ----------------------------------------------------------------------------
    process(Clk, Reset)
    begin
        if Reset = '1' then
            write_strobe_prev <= '0';
        elsif rising_edge(Clk) then
            write_strobe_prev <= write_strobe;
        end if;
    end process;

    write_strobe_edge <= '1' when (write_strobe = '1' and write_strobe_prev = '0') else '0';

    ----------------------------------------------------------------------------
    -- FSM: State Register
    ----------------------------------------------------------------------------
    process(Clk, Reset)
    begin
        if Reset = '1' then
            state <= IDLE;
        elsif rising_edge(Clk) then
            state <= next_state;
        end if;
    end process;

    ----------------------------------------------------------------------------
    -- FSM: Next State Logic
    ----------------------------------------------------------------------------
    process(state, start_loading, write_strobe_edge, words_written, word_count)
    begin
        next_state <= state;  -- Default: hold state

        case state is
            when IDLE =>
                if start_loading = '1' then
                    next_state <= LOADING;
                end if;

            when LOADING =>
                -- Check if all words have been written
                if words_written >= word_count then
                    next_state <= DONE_ST;
                end if;

            when DONE_ST =>
                -- Stay in DONE until reset
                next_state <= DONE_ST;

            when others =>
                next_state <= IDLE;
        end case;
    end process;

    ----------------------------------------------------------------------------
    -- FSM: Word Counter
    ----------------------------------------------------------------------------
    process(Clk, Reset)
    begin
        if Reset = '1' then
            words_written <= (others => '0');
        elsif rising_edge(Clk) then
            if state = IDLE then
                words_written <= (others => '0');
            elsif state = LOADING and write_strobe_edge = '1' then
                words_written <= words_written + 1;
            end if;
        end if;
    end process;

    ----------------------------------------------------------------------------
    -- FSM: Done Flag (Sticky)
    ----------------------------------------------------------------------------
    process(Clk, Reset)
    begin
        if Reset = '1' then
            done_internal <= '0';
        elsif rising_edge(Clk) then
            if state = DONE_ST then
                done_internal <= '1';
            end if;
        end if;
    end process;

    ----------------------------------------------------------------------------
    -- Output Assignments
    ----------------------------------------------------------------------------

    -- BRAM address (from Control11, lower 12 bits)
    bram_addr <= Control11(11 downto 0);

    -- BRAM data (from Control12)
    bram_data <= Control12;

    -- BRAM write enable (pulse on write_strobe rising edge, only in LOADING state)
    bram_we <= '1' when (state = LOADING and write_strobe_edge = '1') else '0';

    -- Done signal (sticky)
    done <= done_internal;

    ----------------------------------------------------------------------------
    -- FSM Observer for Debug Visualization
    -- Maps 2-bit BRAM loader FSM state to oscilloscope-visible voltage
    ----------------------------------------------------------------------------

    -- Pad 2-bit state to 6-bit for observer
    state_6bit <= "0000" & state;

    U_BRAM_OBSERVER: entity work.fsm_observer
        generic map (
            NUM_STATES => 4,              -- 2-bit encoding (4 possible states)
            V_MIN => 0.0,                 -- IDLE state voltage
            V_MAX => 2.0,                 -- DONE state voltage
            FAULT_STATE_THRESHOLD => 3,   -- State "11" (reserved) as fault indicator
            STATE_0_NAME => "IDLE",
            STATE_1_NAME => "LOADING",
            STATE_2_NAME => "DONE",
            STATE_3_NAME => "RESERVED"
        )
        port map (
            clk          => Clk,
            reset        => Reset,
            state_vector => state_6bit,
            voltage_out  => voltage_debug_out
        );

end architecture rtl;

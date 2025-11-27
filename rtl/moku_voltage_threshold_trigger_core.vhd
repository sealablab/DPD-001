--------------------------------------------------------------------------------
-- File: moku_voltage_threshold_trigger_core.vhd
-- Description: Voltage Threshold Trigger with Hysteresis
--
-- Features:
--   - Digital voltage comparator (for Moku 16-bit signed ADC input)
--   - Configurable upper/lower thresholds (hysteresis)
--   - Rising/falling edge trigger modes
--   - Crossing counter for glitch detection
--   - Compatible with Moku_Voltage_pkg
--
-- Behavior:
--   - Compares voltage_in against threshold_high/threshold_low
--   - Hysteresis prevents glitchy triggers near threshold
--   - Generates pulse on threshold crossing
--   - Counts crossings for SCA/FI analysis
--
-- Pattern: Combinational comparator + sequential logic
-- Expected Success: 95%+
-- Verilog Portable: Yes
-- Use Cases:
--   - Power glitch detection (Vdd monitoring)
--   - SCA capture trigger (voltage spike detection)
--   - Fault injection synchronization
--------------------------------------------------------------------------------

library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity moku_voltage_threshold_trigger_core is
    port (
        -- Clock and control
        clk              : in  std_logic;
        reset            : in  std_logic;  -- Active high

        -- Moku voltage input (16-bit signed from ADC)
        voltage_in       : in  signed(15 downto 0);

        -- Threshold configuration (in digital units)
        threshold_high   : in  signed(15 downto 0);  -- Upper threshold
        threshold_low    : in  signed(15 downto 0);  -- Lower threshold (hysteresis)

        -- Control
        enable           : in  std_logic;
        mode             : in  std_logic;  -- '0' = rising edge, '1' = falling edge

        -- Outputs
        trigger_out      : out std_logic;  -- Pulse on crossing (1 cycle)
        above_threshold  : out std_logic;  -- Level indicator
        crossing_count   : out unsigned(15 downto 0)  -- Count threshold crossings
    );
end entity moku_voltage_threshold_trigger_core;

architecture rtl of moku_voltage_threshold_trigger_core is

    signal above_high : std_logic;
    signal below_low  : std_logic;
    signal state      : std_logic;  -- Current threshold state (0=below, 1=above)
    signal state_prev : std_logic;  -- Previous state for edge detection
    signal count_reg  : unsigned(15 downto 0);

begin

    -- Combinational comparators
    above_high <= '1' when voltage_in > threshold_high else '0';
    below_low  <= '1' when voltage_in < threshold_low else '0';

    -- Hysteresis state machine
    process(clk, reset)
    begin
        if reset = '1' then
            state <= '0';
            state_prev <= '0';
            count_reg <= (others => '0');

        elsif rising_edge(clk) then
            if enable = '1' then
                -- Update previous state
                state_prev <= state;

                -- Hysteresis logic
                if above_high = '1' then
                    state <= '1';  -- Crossed above high threshold
                elsif below_low = '1' then
                    state <= '0';  -- Crossed below low threshold
                end if;
                -- else: stay in current state (hysteresis band)

                -- Count crossings
                if state /= state_prev then
                    count_reg <= count_reg + 1;
                end if;
            end if;
        end if;
    end process;

    -- Edge detection for trigger output
    process(clk, reset)
    begin
        if reset = '1' then
            trigger_out <= '0';

        elsif rising_edge(clk) then
            if enable = '1' then
                -- Generate 1-cycle pulse on selected edge
                if mode = '0' then
                    -- Rising edge mode: trigger when crossing above threshold
                    trigger_out <= state and not state_prev;
                else
                    -- Falling edge mode: trigger when crossing below threshold
                    trigger_out <= (not state) and state_prev;
                end if;
            else
                trigger_out <= '0';
            end if;
        end if;
    end process;

    -- Output assignments
    above_threshold <= state;
    crossing_count <= count_reg;

end architecture rtl;

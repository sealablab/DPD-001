--------------------------------------------------------------------------------
-- Title      : FORGE Hierarchical Voltage Encoder
-- Project    : Moku Instrument FORGE
-- File       : forge_hierarchical_encoder.vhd
-- Author     : Moku Instrument Forge Team
-- Created    : 2025-11-07
-- Last update: 2025-11-07
-- Standard   : VHDL'93
--------------------------------------------------------------------------------
-- Description:
--
-- Hierarchical voltage encoder for FORGE OutputD debugging channel.
-- Encodes 14-bit state+status information into signed 16-bit digital output
-- using pure arithmetic (no lookup tables).
--
-- Key Features:
-- - Packs 6-bit FSM state + 8-bit app status into OutputD
-- - Major state transitions = 200 digital units (human-readable on scope)
-- - Status information = fine-grained offset (machine-decodable)
-- - Fault detection via sign flip (status[7] = fault flag)
-- - Platform-agnostic (digital encoding, voltage scaling done by DAC)
--
-- Encoding Scheme:
--   Base Digital Value  = state_value × DIGITAL_UNITS_PER_STATE
--   Status Offset       = status[6:0] × DIGITAL_UNITS_PER_STATUS
--   Sign Multiplier     = status[7] ? -1 : +1 (fault indicator)
--   Digital Output      = (Base + Offset) × Sign
--
-- Design Principles:
-- 1. Pure arithmetic (zero LUTs)
-- 2. Platform-agnostic (outputs digital codes, not voltages)
-- 3. Two's complement signed output (standard hardware representation)
-- 4. Fault flag in status[7] (negative voltage = fault)
--
-- Physical Interpretation (platform-dependent):
--   Assuming ±5V full-scale platform (digital ±32768 = ±5V):
--   - State step: 200 digital units ≈ 30.5 mV per state
--   - Status resolution: 0.78125 digital units ≈ 0.024 mV per LSB
--   - Status range: ±100 digital units ≈ ±15.3 mV around base state
--
-- Example Outputs (digital domain):
--   State=0, Status=0x00 → 0 digital units
--   State=1, Status=0x00 → 200 digital units
--   State=2, Status=0x40 → 450 digital units (400 + 50)
--   State=2, Status=0xC0 → -450 digital units (fault, magnitude preserved)
--
-- References:
-- - Design Document: Obsidian/Project/Review/HIERARCHICAL_ENCODER_DIGITAL_SCALING.md
-- - Handoff 6: Obsidian/Project/Handoffs/2025-11-07-handoff-6-hierarchical-voltage-encoding.md
--
--------------------------------------------------------------------------------

library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity forge_hierarchical_encoder is
    generic (
        -- Digital scaling parameters (platform-agnostic)
        -- These are NOT voltages! They are digital units.
        -- Voltage interpretation depends on platform DAC configuration.
        -- UPDATED 2025-01-18: Increased from 200 to 3277 for human-readable scope viewing
        -- 3277 digital units = 0.5V per state step @ ±5V full scale (Moku:Go)
        DIGITAL_UNITS_PER_STATE  : integer := 3277;     -- Digital units per state step (~0.5V @ ±5V FS)
        DIGITAL_UNITS_PER_STATUS : real    := 0.78125   -- Digital units per status LSB (100/128)
    );
    port (
        -- Clock and reset
        clk           : in  std_logic;
        reset         : in  std_logic;

        -- State and status inputs (from APP layer)
        state_vector  : in  std_logic_vector(5 downto 0);   -- 6-bit FSM state (0-63)
        status_vector : in  std_logic_vector(7 downto 0);   -- 8-bit app status
                                                             -- status[7] = fault flag
                                                             -- status[6:0] = app-specific (0-127)

        -- Digital output (two's complement, platform-agnostic)
        voltage_out   : out signed(15 downto 0)              -- ±32768 digital range
    );
end entity forge_hierarchical_encoder;

architecture rtl of forge_hierarchical_encoder is

    -- Internal signals for arithmetic
    signal state_integer  : integer range 0 to 63;
    signal status_lower   : integer range 0 to 127;  -- status[6:0]
    signal fault_flag     : std_logic;               -- status[7]

    signal base_value     : integer;
    signal status_offset  : integer;
    signal combined_value : integer;
    signal output_value   : signed(15 downto 0);

begin

    -- Extract integer values from bit vectors
    state_integer <= to_integer(unsigned(state_vector));
    status_lower  <= to_integer(unsigned(status_vector(6 downto 0)));
    fault_flag    <= status_vector(7);

    -- Compute base value (state contribution)
    base_value <= state_integer * DIGITAL_UNITS_PER_STATE;

    -- Compute status offset (fine-grained contribution)
    -- Note: DIGITAL_UNITS_PER_STATUS = 0.78125 = 100/128
    -- To avoid floating-point in synthesis:
    --   status_offset = status_lower * 100 / 128
    -- But we can simplify by noting 100/128 ≈ 0.78125
    -- For exact integer arithmetic: status_lower * 100 / 128
    status_offset <= (status_lower * 100) / 128;

    -- Combine base + offset
    combined_value <= base_value + status_offset;

    -- Encoding process
    process(clk, reset)
    begin
        if reset = '1' then
            output_value <= (others => '0');

        elsif rising_edge(clk) then
            -- Apply sign based on fault flag
            if fault_flag = '1' then
                -- Fault detected: negate output (negative voltage)
                output_value <= to_signed(-combined_value, 16);
            else
                -- Normal operation: positive output
                output_value <= to_signed(combined_value, 16);
            end if;
        end if;
    end process;

    -- Drive output
    voltage_out <= output_value;

end architecture rtl;

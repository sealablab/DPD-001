-------------------------------------------------------------------------------
-- clock_probe.vhd
--
-- Minimal CloudCompile design to measure FPGA fabric clock frequency.
-- Outputs a SQR_04_128 waveform (4 samples high, 124 samples low).
-- Pulse width = 4 × clock_period, directly revealing the clock frequency.
--
-- Expected results:
--   Moku:Go  @ ADC clock (125 MHz):    pulse = 32 ns
--   Moku:Go  @ MCC fabric (31.25 MHz): pulse = 128 ns
--   Moku:Lab @ ADC clock (500 MHz):    pulse = 8 ns
--   Moku:Lab @ MCC fabric (125 MHz):   pulse = 32 ns
--
-- See: docs/mcc-fabric-clock.md for experiment details
-------------------------------------------------------------------------------

library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;

entity CustomWrapper is
    port (
        Clk      : in  std_logic;
        Reset    : in  std_logic;

        -- Analog inputs (directly from ADC)
        InputA   : in  std_logic_vector(15 downto 0);
        InputB   : in  std_logic_vector(15 downto 0);

        -- Analog outputs (directly to DAC)
        OutputA  : out std_logic_vector(15 downto 0);
        OutputB  : out std_logic_vector(15 downto 0);

        -- Control registers (directly from Moku API set_control())
        Control0 : in  std_logic_vector(31 downto 0);
        Control1 : in  std_logic_vector(31 downto 0);
        Control2 : in  std_logic_vector(31 downto 0);
        Control3 : in  std_logic_vector(31 downto 0);
        Control4 : in  std_logic_vector(31 downto 0);
        Control5 : in  std_logic_vector(31 downto 0);
        Control6 : in  std_logic_vector(31 downto 0);
        Control7 : in  std_logic_vector(31 downto 0);
        Control8 : in  std_logic_vector(31 downto 0);
        Control9 : in  std_logic_vector(31 downto 0);
        Control10: in  std_logic_vector(31 downto 0);
        Control11: in  std_logic_vector(31 downto 0);
        Control12: in  std_logic_vector(31 downto 0);
        Control13: in  std_logic_vector(31 downto 0);
        Control14: in  std_logic_vector(31 downto 0);
        Control15: in  std_logic_vector(31 downto 0)
    );
end entity CustomWrapper;

architecture rtl of CustomWrapper is

    ---------------------------------------------------------------------------
    -- ROM: SQR_04_128 - 4 samples high, 124 samples low
    -- Value encoding: 16-bit signed, unipolar (0 to +32767)
    ---------------------------------------------------------------------------
    type rom_t is array(0 to 127) of signed(15 downto 0);

    constant SQR_04_128 : rom_t := (
        -- First 4 samples: HIGH (+32767 = ~+5V)
        0 => to_signed(32767, 16),
        1 => to_signed(32767, 16),
        2 => to_signed(32767, 16),
        3 => to_signed(32767, 16),
        -- Remaining 124 samples: LOW (0 = 0V)
        others => to_signed(0, 16)
    );

    ---------------------------------------------------------------------------
    -- Signals
    ---------------------------------------------------------------------------
    signal rom_index : unsigned(6 downto 0) := (others => '0');
    signal enable    : std_logic;
    signal rom_out   : signed(15 downto 0);

begin

    ---------------------------------------------------------------------------
    -- FORGE Enable: CR0[31:29] must all be '1'
    -- This is the standard MCC control scheme
    ---------------------------------------------------------------------------
    enable <= Control0(31) and Control0(30) and Control0(29);

    ---------------------------------------------------------------------------
    -- Free-running ROM index counter
    -- Increments every clock cycle when enabled
    -- Wraps at 128 (7-bit counter)
    ---------------------------------------------------------------------------
    process(Clk)
    begin
        if rising_edge(Clk) then
            if Reset = '1' then
                rom_index <= (others => '0');
            elsif enable = '1' then
                rom_index <= rom_index + 1;
            end if;
        end if;
    end process;

    ---------------------------------------------------------------------------
    -- ROM lookup (combinatorial)
    ---------------------------------------------------------------------------
    rom_out <= SQR_04_128(to_integer(rom_index));

    ---------------------------------------------------------------------------
    -- Output assignment
    -- OutputA: The SQR_04_128 waveform (measure pulse width here)
    -- OutputB: Inverted copy (for differential measurement if needed)
    ---------------------------------------------------------------------------
    OutputA <= std_logic_vector(rom_out);
    OutputB <= std_logic_vector(-rom_out);  -- Inverted

end architecture rtl;

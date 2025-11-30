--------------------------------------------------------------------------------
-- File: CustomWrapper.vhd
-- Author: Moku Instrument Forge Team
-- Created: 2025-11-30
--
-- Description:
--   Top-level synthesis wrapper for BOOT subsystem. CloudCompile expects
--   an entity named CustomWrapper as the top-level design.
--
--   This wrapper instantiates the BootWrapper entity with the boot_dispatcher
--   architecture defined in B0_BOOT_TOP.vhd, providing the standard Moku
--   CloudCompile interface.
--
-- Usage:
--   This file is used for synthesis only. For simulation/testing, use
--   BootWrapper_test_stub.vhd instead.
--
-- Reference:
--   docs/boot/BOOT-BIOS-SYNTHESIS-GUIDE.md
--------------------------------------------------------------------------------

library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;

entity CustomWrapper is
    port (
        -- Clock and Reset
        Clk     : in  std_logic;
        Reset   : in  std_logic;

        -- Input signals (ADC data, signed 16-bit)
        InputA  : in  signed(15 downto 0);
        InputB  : in  signed(15 downto 0);
        InputC  : in  signed(15 downto 0);

        -- Output signals (DAC data, signed 16-bit)
        OutputA : out signed(15 downto 0);
        OutputB : out signed(15 downto 0);
        OutputC : out signed(15 downto 0);

        -- Control registers (32-bit each, from Moku platform)
        Control0  : in  std_logic_vector(31 downto 0);
        Control1  : in  std_logic_vector(31 downto 0);
        Control2  : in  std_logic_vector(31 downto 0);
        Control3  : in  std_logic_vector(31 downto 0);
        Control4  : in  std_logic_vector(31 downto 0);
        Control5  : in  std_logic_vector(31 downto 0);
        Control6  : in  std_logic_vector(31 downto 0);
        Control7  : in  std_logic_vector(31 downto 0);
        Control8  : in  std_logic_vector(31 downto 0);
        Control9  : in  std_logic_vector(31 downto 0);
        Control10 : in  std_logic_vector(31 downto 0);
        Control11 : in  std_logic_vector(31 downto 0);
        Control12 : in  std_logic_vector(31 downto 0);
        Control13 : in  std_logic_vector(31 downto 0);
        Control14 : in  std_logic_vector(31 downto 0);
        Control15 : in  std_logic_vector(31 downto 0)
    );
end entity CustomWrapper;

architecture synthesis of CustomWrapper is

    -- Instantiate BootWrapper with boot_dispatcher architecture
    component BootWrapper is
        port (
            Clk     : in  std_logic;
            Reset   : in  std_logic;
            InputA  : in  signed(15 downto 0);
            InputB  : in  signed(15 downto 0);
            InputC  : in  signed(15 downto 0);
            OutputA : out signed(15 downto 0);
            OutputB : out signed(15 downto 0);
            OutputC : out signed(15 downto 0);
            Control0  : in  std_logic_vector(31 downto 0);
            Control1  : in  std_logic_vector(31 downto 0);
            Control2  : in  std_logic_vector(31 downto 0);
            Control3  : in  std_logic_vector(31 downto 0);
            Control4  : in  std_logic_vector(31 downto 0);
            Control5  : in  std_logic_vector(31 downto 0);
            Control6  : in  std_logic_vector(31 downto 0);
            Control7  : in  std_logic_vector(31 downto 0);
            Control8  : in  std_logic_vector(31 downto 0);
            Control9  : in  std_logic_vector(31 downto 0);
            Control10 : in  std_logic_vector(31 downto 0);
            Control11 : in  std_logic_vector(31 downto 0);
            Control12 : in  std_logic_vector(31 downto 0);
            Control13 : in  std_logic_vector(31 downto 0);
            Control14 : in  std_logic_vector(31 downto 0);
            Control15 : in  std_logic_vector(31 downto 0)
        );
    end component;

begin

    -- Instantiate BOOT subsystem
    u_boot : BootWrapper
        port map (
            Clk     => Clk,
            Reset   => Reset,
            InputA  => InputA,
            InputB  => InputB,
            InputC  => InputC,
            OutputA => OutputA,
            OutputB => OutputB,
            OutputC => OutputC,
            Control0  => Control0,
            Control1  => Control1,
            Control2  => Control2,
            Control3  => Control3,
            Control4  => Control4,
            Control5  => Control5,
            Control6  => Control6,
            Control7  => Control7,
            Control8  => Control8,
            Control9  => Control9,
            Control10 => Control10,
            Control11 => Control11,
            Control12 => Control12,
            Control13 => Control13,
            Control14 => Control14,
            Control15 => Control15
        );

end architecture synthesis;


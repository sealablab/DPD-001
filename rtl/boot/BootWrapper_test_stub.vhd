--------------------------------------------------------------------------------
-- File: BootWrapper_test_stub.vhd
-- Author: Moku Instrument Forge Team
-- Created: 2025-11-29
--
-- Description:
--   CustomWrapper entity stub for CocoTB testing of the BOOT subsystem.
--   This stub replicates the MCC-provided CustomWrapper entity interface
--   for use in CocoTB testbenches where MCC is not available.
--
--   For production builds, MCC provides the actual entity declaration.
--
-- Usage:
--   Compile this file BEFORE B0_BOOT_TOP.vhd when running GHDL tests.
--   The architecture boot_forge defined in B0_BOOT_TOP.vhd will bind
--   to this entity declaration.
--
-- See Also:
--   rtl/CustomWrapper_test_stub.vhd (DPD version)
--   rtl/boot/B0_BOOT_TOP.vhd (BOOT architecture)
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
        -- Note: std_logic_vector, NOT signed!
        -- BOOT uses Control0-Control4 for LOADER protocol
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

-- Note: The architecture is defined in B0_BOOT_TOP.vhd as "boot_forge"
-- GHDL will bind "architecture boot_forge of CustomWrapper" to this entity

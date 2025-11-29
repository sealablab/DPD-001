--------------------------------------------------------------------------------
-- File: loader_crc16.vhd
-- Author: Moku Instrument Forge Team
-- Created: 2025-11-29
--
-- Description:
--   CRC-16-CCITT calculator for LOADER buffer validation.
--   Pure combinatorial implementation - processes one 32-bit word per call.
--
-- Algorithm:
--   Polynomial: 0x1021 (x^16 + x^12 + x^5 + 1)
--   Initial value: 0xFFFF
--   Input: 32-bit words, processed MSB (byte 3) first
--
-- Usage:
--   1. Initialize CRC to CRC16_INIT (0xFFFF) at start of transfer
--   2. For each 32-bit data word, compute: new_crc = crc16_update(old_crc, data)
--   3. After all words, compare computed CRC with expected
--
-- Reference:
--   docs/bootup-proposal/LOAD-FSM-spec.md
--------------------------------------------------------------------------------

library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;

library WORK;
use WORK.forge_common_pkg.all;

entity loader_crc16 is
    port (
        -- Input: current CRC value
        crc_in   : in  std_logic_vector(15 downto 0);

        -- Input: 32-bit data word to process
        data_in  : in  std_logic_vector(31 downto 0);

        -- Output: updated CRC value
        crc_out  : out std_logic_vector(15 downto 0)
    );
end entity loader_crc16;

architecture rtl of loader_crc16 is

    -- Process one byte through CRC-16-CCITT
    function crc16_byte(crc : std_logic_vector(15 downto 0);
                        data_byte : std_logic_vector(7 downto 0))
        return std_logic_vector is
        variable c : std_logic_vector(15 downto 0) := crc;
        variable b : std_logic;
    begin
        -- Process 8 bits, MSB first
        for i in 7 downto 0 loop
            b := c(15) xor data_byte(i);
            c := c(14 downto 0) & '0';
            if b = '1' then
                c := c xor CRC16_POLYNOMIAL;
            end if;
        end loop;
        return c;
    end function;

    -- Process one 32-bit word (4 bytes, MSB first)
    function crc16_word(crc : std_logic_vector(15 downto 0);
                        data_word : std_logic_vector(31 downto 0))
        return std_logic_vector is
        variable c : std_logic_vector(15 downto 0) := crc;
    begin
        -- Process 4 bytes: byte3 (MSB), byte2, byte1, byte0 (LSB)
        c := crc16_byte(c, data_word(31 downto 24));  -- Byte 3 (MSB)
        c := crc16_byte(c, data_word(23 downto 16));  -- Byte 2
        c := crc16_byte(c, data_word(15 downto 8));   -- Byte 1
        c := crc16_byte(c, data_word(7 downto 0));    -- Byte 0 (LSB)
        return c;
    end function;

begin

    -- Pure combinatorial: compute updated CRC
    crc_out <= crc16_word(crc_in, data_in);

end architecture rtl;

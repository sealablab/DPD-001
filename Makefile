# DPD-001 Makefile
# VHDL compilation with GHDL

RTL_DIR := rtl

# Order matters: dependencies must be compiled first
#
# Integration Note: DPD.vhd now wraps B0_BOOT_TOP.vhd (BOOT dispatcher)
# which in turn instantiates DPD_shim for PROG mode. Compilation order:
#   1. Common packages and primitives
#   2. DPD application layers (main → shim)
#   3. BOOT subsystem layers (BIOS, LOADER → BOOT_TOP)
#   4. Top-level wrapper (DPD.vhd, instantiates BOOT_TOP)
VHDL_FILES := \
    $(RTL_DIR)/forge_common_pkg.vhd \
    $(RTL_DIR)/CustomWrapper_test_stub.vhd \
    $(RTL_DIR)/boot/BootWrapper_test_stub.vhd \
    $(RTL_DIR)/moku_voltage_threshold_trigger_core.vhd \
    $(RTL_DIR)/forge_hierarchical_encoder.vhd \
    $(RTL_DIR)/DPD_main.vhd \
    $(RTL_DIR)/DPD_shim.vhd \
    $(RTL_DIR)/boot/loader_crc16.vhd \
    $(RTL_DIR)/boot/L2_BUFF_LOADER.vhd \
    $(RTL_DIR)/boot/B1_BOOT_BIOS.vhd \
    $(RTL_DIR)/boot/B0_BOOT_TOP.vhd \
    $(RTL_DIR)/DPD.vhd

.PHONY: compile clean

compile:
	ghdl -a $(VHDL_FILES)

clean:
	rm -f *.o *.cf

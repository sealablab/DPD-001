# DPD-001 Makefile
# VHDL compilation with GHDL

RTL_DIR := rtl

# Order matters: dependencies must be compiled first
VHDL_FILES := \
    $(RTL_DIR)/forge_common_pkg.vhd \
    $(RTL_DIR)/CustomWrapper_test_stub.vhd \
    $(RTL_DIR)/moku_voltage_threshold_trigger_core.vhd \
    $(RTL_DIR)/forge_hierarchical_encoder.vhd \
    $(RTL_DIR)/DPD_main.vhd \
    $(RTL_DIR)/DPD_shim.vhd \
    $(RTL_DIR)/DPD.vhd

.PHONY: compile clean

compile:
	ghdl -a $(VHDL_FILES)

clean:
	rm -f *.o *.cf

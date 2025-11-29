# DPD-001 Makefile
# VHDL compilation with GHDL auto-dependency resolution

RTL_DIR := rtl
SYNTH_DIR := synth

# All VHDL source files (GHDL will auto-resolve dependencies)
# Exclude empty placeholder files
RTL_SOURCES := \
    $(RTL_DIR)/forge_common_pkg.vhd \
    $(RTL_DIR)/CustomWrapper_test_stub.vhd \
    $(RTL_DIR)/moku_voltage_threshold_trigger_core.vhd \
    $(RTL_DIR)/forge_hierarchical_encoder.vhd \
    $(RTL_DIR)/DPD_main.vhd \
    $(RTL_DIR)/DPD_shim.vhd \
    $(RTL_DIR)/DPD.vhd \
    $(RTL_DIR)/boot/BootWrapper_test_stub.vhd \
    $(RTL_DIR)/boot/loader_crc16.vhd \
    $(RTL_DIR)/boot/L2_BUFF_LOADER.vhd \
    $(RTL_DIR)/boot/B1_BOOT_BIOS.vhd \
    $(RTL_DIR)/boot/B0_BOOT_TOP.vhd

# Production VHDL files for synthesis (exclude test stubs)
SYNTH_SOURCES := \
    $(RTL_DIR)/forge_common_pkg.vhd \
    $(RTL_DIR)/moku_voltage_threshold_trigger_core.vhd \
    $(RTL_DIR)/forge_hierarchical_encoder.vhd \
    $(RTL_DIR)/DPD_main.vhd \
    $(RTL_DIR)/DPD_shim.vhd \
    $(RTL_DIR)/boot/loader_crc16.vhd \
    $(RTL_DIR)/boot/L2_BUFF_LOADER.vhd \
    $(RTL_DIR)/boot/B1_BOOT_BIOS.vhd \
    $(RTL_DIR)/boot/B0_BOOT_TOP.vhd \
    $(RTL_DIR)/DPD.vhd

# Metadata file for MCC
SYNTH_METADATA := $(RTL_DIR)/DPD-RTL.yaml

.PHONY: all compile elaborate clean synth-prep synth-clean help

# Default target
all: compile

# Compile using GHDL's auto-dependency resolution
# Uses: ghdl -i (import) to index files, ghdl -m (make) to compile+elaborate
compile: clean
	@echo "Importing VHDL sources..."
	@ghdl -i $(RTL_SOURCES)
	@echo "Auto-resolving dependencies and compiling CustomWrapper..."
	@ghdl -m CustomWrapper
	@echo ""
	@echo "✓ Compilation successful!"
	@echo "  CustomWrapper (unified BOOT+DPD) ready for simulation"

# Elaborate only (assumes files already analyzed)
elaborate:
	@echo "Elaborating CustomWrapper..."
	@ghdl -e CustomWrapper
	@echo "✓ Elaboration successful!"

# Clean GHDL build artifacts
clean:
	@rm -f *.o *.cf work-obj*.cf customwrapper bootwrapper
	@echo "Build artifacts cleaned"

# Prepare flat directory for MCC synthesis upload
# MCC requires all VHDL files in a single flat directory (no subdirectories)
synth-prep:
	@echo "=========================================="
	@echo "Creating MCC Synthesis Package"
	@echo "=========================================="
	@mkdir -p $(SYNTH_DIR)
	@echo ""
	@echo "Copying VHDL files to flat directory..."
	@for file in $(SYNTH_SOURCES); do \
		basename=$$(basename $$file); \
		printf "  %-50s -> %s\n" "$$file" "$(SYNTH_DIR)/$$basename"; \
		cp $$file $(SYNTH_DIR)/$$basename; \
	done
	@if [ -f $(SYNTH_METADATA) ]; then \
		echo ""; \
		echo "Copying DPD-RTL.yaml metadata..."; \
		cp $(SYNTH_METADATA) $(SYNTH_DIR)/; \
	fi
	@echo ""
	@echo "=========================================="
	@echo "✓ Synthesis package ready!"
	@echo "=========================================="
	@echo "Directory: $(SYNTH_DIR)/"
	@echo "Files:     $$(ls -1 $(SYNTH_DIR)/*.vhd 2>/dev/null | wc -l | tr -d ' ') VHDL files"
	@echo ""
	@echo "Upload these files to Moku CloudCompile:"
	@echo "------------------------------------------"
	@ls -1 $(SYNTH_DIR)/
	@echo ""
	@echo "To clean: make synth-clean"

# Clean synthesis package directory
synth-clean:
	@if [ -d $(SYNTH_DIR) ]; then \
		echo "Removing synthesis package directory..."; \
		rm -rf $(SYNTH_DIR); \
		echo "✓ $(SYNTH_DIR)/ removed"; \
	else \
		echo "$(SYNTH_DIR)/ does not exist (nothing to clean)"; \
	fi

# Help target
help:
	@echo "DPD-001 Build System"
	@echo "===================="
	@echo ""
	@echo "Targets:"
	@echo "  make compile      - Compile all VHDL files (default)"
	@echo "  make elaborate    - Elaborate design (after compile)"
	@echo "  make clean        - Remove build artifacts"
	@echo "  make synth-prep   - Create flat directory for MCC upload"
	@echo "  make synth-clean  - Remove synthesis package"
	@echo "  make help         - Show this help"
	@echo ""
	@echo "GHDL Auto-Dependency Resolution:"
	@echo "  GHDL automatically detects and compiles files in the"
	@echo "  correct dependency order. No manual ordering required!"
	@echo ""
	@echo "Synthesis Workflow:"
	@echo "  1. make synth-prep      # Create synth/ directory"
	@echo "  2. Upload synth/*.vhd to Moku CloudCompile"
	@echo "  3. Download bitstream from MCC"
	@echo "  4. make synth-clean     # Clean up when done"

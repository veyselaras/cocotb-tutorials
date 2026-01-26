# Makefile for cocotb simulation

# Simulator (icarus, verilator, questa, vcs, xcelium)
SIM ?= icarus

# Top-level language
TOPLEVEL_LANG ?= verilog

# RTL source files
VERILOG_SOURCES = $(PWD)/rtl/sync_fifo.sv

# Top-level module name
TOPLEVEL = sync_fifo

# Python test module name (without .py)
MODULE = tb_sync_fifo

# Testbench directory
export PYTHONPATH := $(PWD)/tb:$(PYTHONPATH)

# Icarus Verilog flags for SystemVerilog support
ifeq ($(SIM), icarus)
    COMPILE_ARGS += -g2012
endif

# Include cocotb makefile
include $(shell cocotb-config --makefiles)/Makefile.sim

# Clean simulation files
clean::
	rm -rf __pycache__ results.xml
	rm -rf sim_build
	rm -rf *.vcd *.fst

# Makefile - cocotb örnek 1.1 için

# ============================================
# SİMÜLATÖR AYARLARI
# ============================================
# Varsayılan simülatör: Icarus Verilog
# Başka simülatör için: make SIM=verilator veya make SIM=questa
SIM ?= icarus

# HDL dili
TOPLEVEL_LANG ?= verilog

# ============================================
# DOSYA YOLLARI
# ============================================
# RTL kaynak dosyaları
VERILOG_SOURCES = $(shell pwd)/rtl/TinyShifter.sv

# Üst modül adı (RTL'deki modül ismi)
TOPLEVEL = TinyShifter

# Python test modülü (tb klasöründeki dosya, .py olmadan)
MODULE = tb_TinyShifter

# ============================================
# PYTHON PATH AYARI
# ============================================
# cocotb'nin tb klasörünü bulabilmesi için
export PYTHONPATH := $(shell pwd)/tb:$(PYTHONPATH)

# ============================================
# COCOTB MAKEFILE DAHİL ETME
# ============================================
include $(shell cocotb-config --makefiles)/Makefile.sim
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
VERILOG_SOURCES = $(shell pwd)/rtl/dummy.v

# Üst modül adı (RTL'deki modül ismi)
TOPLEVEL = dummy

# Python test modülü (tb klasöründeki dosya, .py olmadan)
MODULE = cocotb_queue_example_01
# MODULE = cocotb_queue_example_02
# MODULE = cocotb_queue_example_03
# MODULE = cocotb_queue_example_04
# MODULE = cocotb_queue_example_05

# ============================================
# PYTHON PATH AYARI
# ============================================
# cocotb'nin tb klasörünü bulabilmesi için
export PYTHONPATH := $(shell pwd)/tb:$(PYTHONPATH)

# ============================================
# COCOTB MAKEFILE DAHİL ETME
# ============================================
include $(shell cocotb-config --makefiles)/Makefile.sim
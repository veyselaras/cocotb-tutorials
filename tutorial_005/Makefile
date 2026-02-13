# ============================================================
# Register Bank Testbench Makefile
# ============================================================

# Simulator seçimi (icarus, verilator, questa, xcelium, vcs)
SIM ?= icarus

# Dil
TOPLEVEL_LANG = verilog

# RTL kaynak dosyaları
VERILOG_SOURCES = $(PWD)/rtl/register_bank.sv

# Top modül ismi (RTL'deki modül adı)
TOPLEVEL = register_bank

# Python test modülü (regbank_tests.py → regbank_tests)
MODULE = regbank_tests

# Python path - tb klasörünü ekle
export PYTHONPATH := $(PWD)/tb:$(PYTHONPATH)

# Waveform dosyası (icarus için)
WAVES = 1

# cocotb Makefile'ı dahil et
include $(shell cocotb-config --makefiles)/Makefile.sim

# ============================================================
# Ek hedefler
# ============================================================

# Temizlik
clean_all: clean
	rm -rf __pycache__ tb/__pycache__
	rm -rf results.xml
	rm -rf *.vcd *.fst
	rm -rf sim_build

# Sadece RW testi çalıştır
test_rw:
	$(MAKE) TESTCASE=RWRegisterTest

# Sadece RO testi çalıştır
test_ro:
	$(MAKE) TESTCASE=RORegisterTest

# Sadece W1C testi çalıştır
test_w1c:
	$(MAKE) TESTCASE=W1CRegisterTest

# Tüm testleri çalıştır
test_all:
	$(MAKE) clean
	$(MAKE)

# Waveform görüntüle (GTKWave)
waves:
	gtkwave dump.vcd &

# Yardım
help:
	@echo "Kullanım:"
	@echo "  make              - Tüm testleri çalıştır"
	@echo "  make test_rw      - RWRegisterTest çalıştır"
	@echo "  make test_ro      - RORegisterTest çalıştır"
	@echo "  make test_w1c     - W1CRegisterTest çalıştır"
	@echo "  make test_all     - Temizle ve tüm testleri çalıştır"
	@echo "  make clean        - Geçici dosyaları temizle"
	@echo "  make clean_all    - Tüm oluşturulan dosyaları temizle"
	@echo "  make waves        - GTKWave ile waveform aç"
	@echo ""
	@echo "Simulator değiştirmek için:"
	@echo "  make SIM=verilator"
	@echo "  make SIM=questa"
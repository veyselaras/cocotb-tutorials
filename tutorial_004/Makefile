# Simülatör ayarı
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# RTL dosyasının yolu (rtl klasörü altında)
VERILOG_SOURCES += $(shell pwd)/rtl/simpleCounter.sv

# Python test dosyalarının bulunduğu klasörü PYTHONPATH'e ekliyoruz
# Bu adım kritik, aksi halde cocotb 'HelloWorld' modülünü bulamaz.
export PYTHONPATH := $(shell pwd)/tb:$(PYTHONPATH)

# Python dosyasının adı (uzantısız)
MODULE = tb_simpleCounter

# Verilog içindeki en üst modül adı
TOPLEVEL = simpleCounter

# Cocotb Makefile kuralları
include $(shell cocotb-config --makefiles)/Makefile.sim
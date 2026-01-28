import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer, RisingEdge, FallingEdge, ReadOnly

import random

async def reset_handler(dut, duration_ns=20): # Burayi testin baslangicinda reset icin kullanacagiz
	dut.rstn.value = 0 # Reset aktif
	await Timer(duration_ns, "ns") # Belirtilen sure kadar bekle
	dut.rstn.value = 1 # Reset pasif
	dut._log.info("Reset Bitti") # Log mesajı

async def simple_monitor(dut, captured_data_list): # Basit bir monitor fonksiyonu
	while True: # Monitor surekli data kontrolu yapacagi icin sonsuz dongude calisir
		await RisingEdge(dut.clk) # Saat sinyalinin yukselen kenarini bekle

		enable_out_val = dut.enable_out.value # enable_out sinyalinin degerini oku
		empty_val = dut.empty.value # empty sinyalinin degerini oku

		if enable_out_val == 1 and empty_val == 0: # Eger enable_out aktif ve fifo bos degilse
			await RisingEdge(dut.clk) # Bir saat dongusu daha bekle
			await ReadOnly() # ReadOnly ile sinyallerin degisemeyecegi, sadece okunabilecegi duruma gec
			output_data = int(dut.data_out.value) # data_out sinyalinin degerini oku
			dut._log.info(f"Monitor Yakaladi: {output_data}") # Log mesajı
			
			captured_data_list.append(output_data) # Test sonunda karsilastima yapmak icin veriyi listeye ekle



class SimpleDriver: # Basit bir driver sinifi
	def __init__(self, dut): 
		self.dut = dut # DUT referansini sakla

		# Baslangicta sinyalleri varsayilan degerlerine ayarla
		self.dut.rstn.value = 0
		self.dut.enable_in.value = 0
		self.dut.enable_out.value = 0
		self.dut.data_in.value = 0

	# Driver sinyalleri ayarlamak icin iki asenkron metod

	# Veri gonderme metodu
	async def sender(self, value): # value parametresi gonderilecek veriyi temsil eder
		await FallingEdge(self.dut.clk) # Saat sinyalinin dusen kenarini bekle
		self.dut.data_in.value = value # data_in sinyaline gonderilecek veriyi ata
		self.dut.enable_in.value = 1 # enable_in sinyalini aktif et ki fifo veri alabilsin

		await RisingEdge(self.dut.clk) # Bir saat dongusu bekle

		await FallingEdge(self.dut.clk) # Saat sinyalinin dusen kenarini bekle

		self.dut.enable_in.value = 0 # enable_in sinyalini pasif et ki fifo veri almayi durdursun

	# Veri alma metodu
	async def receiver(self): 
		await FallingEdge(self.dut.clk) # Saat sinyalinin dusen kenarini bekle

		self.dut.enable_out.value = 1 # enable_out sinyalini aktif et ki fifo veri verebilsin
		
		await RisingEdge(self.dut.clk) # Bir saat dongusu bekle
		await FallingEdge(self.dut.clk) # Saat sinyalinin dusen kenarini bekle

		self.dut.enable_out.value = 0 # enable_out sinyalini pasif et ki fifo veri vermeyi durdursun



# Test senaryolari
@cocotb.test()
async def write_after_read(dut): # Tum verileri yaz sonra tum verileri oku
	monitors_data = [] # Monitorun yakaladigi verileri saklamak icin liste
	expected_data = [random.randint(0, 255) for _ in range(16)] # Gonderilecek rastgele veriler

	cocotb.start_soon(Clock(dut.clk, 10, "ns").start()) # Saat sinyali baslat

	await reset_handler(dut) # Test baslangicinda reset uygula
	await RisingEdge(dut.clk) # Saat sinyalinin yukselen kenarini bekle

	cocotb.start_soon(simple_monitor(dut, monitors_data)) # Monitori baslat

	driver = SimpleDriver(dut) # Driveri baslat
	""" Burada reseti 0 yapiyorum cunku driver'in kurucu metodunda rstn 0 yapiliyor """
	dut.rstn.value = 1 # Reset pasif yap

	for val in expected_data: # Tum verileri yaz
		await driver.sender(val)
		dut._log.info(f"Yazilan: {val}")
		
	await RisingEdge(dut.clk) # Bir saat dongusu bekle
	await ReadOnly() # ReadOnly ile sinyallerin degisemeyecegi, sadece okunabilecegi duruma gec

	dut._log.info(f"Write sonrasi - empty: {dut.empty.value}, full: {dut.full.value}") # Log mesajı
	dut._log.info(f"write_ptr: {int(dut.write_ptr.value)}, read_ptr: {int(dut.read_ptr.value)}") # Log mesajı

	for val in expected_data: # Tum verileri oku
		await driver.receiver()
		

	await Timer(200, "ns") # 200 ns bekle

	dut._log.info(f"Giden: {expected_data}") # Log mesajı
	dut._log.info(f"Gelen: {monitors_data}") # Log mesajı

	""" Karsilastirma yap eger beklenen ve monitorun yakaladigi veriler ayni degilse hata mesaji ver """
	assert monitors_data == expected_data, f"Hata! Giden: {expected_data}, Gelen: {monitors_data}"
	dut._log.info("Test Basarili")


# Bir yazma bir okuma islemi yapan test senaryosu
@cocotb.test()
async def write_and_read_1by1(dut):
	monitors_data = [] # Monitorun yakaladigi verileri saklamak icin liste
	expected_data = [random.randint(0, 255) for _ in range(16)] # Gonderilecek rastgele veriler

	cocotb.start_soon(Clock(dut.clk, 10, "ns").start()) # Saat sinyali baslat

	await reset_handler(dut) # Test baslangicinda reset uygula
	await RisingEdge(dut.clk) # Saat sinyalinin yukselen kenarini bekle

	cocotb.start_soon(simple_monitor(dut, monitors_data)) # Monitori baslat

	driver = SimpleDriver(dut) # Driveri baslat
	""" Burada reseti 0 yapiyorum cunku driver'in kurucu metodunda rstn 0 yapiliyor """
	dut.rstn.value = 1 # Reset pasif yap

	for val in expected_data: # Bir yaz bir oku islemi yap
		await driver.sender(val)
		dut._log.info(f"Yazilan: {val}")

		await driver.receiver()

	await Timer(200, "ns") # 200 ns bekle

	dut._log.info(f"Giden: {expected_data}") # Log mesajı
	dut._log.info(f"Gelen: {monitors_data}") # Log mesajı

	""" Karsilastirma yap eger beklenen ve monitorun yakaladigi veriler ayni degilse hata mesaji ver """
	assert monitors_data == expected_data, f"Hata! Giden: {expected_data}, Gelen: {monitors_data}"
	dut._log.info("Test Basarili")

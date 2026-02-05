"""
============================================================================
Proje       : SimpleCounter PyUVM Doğrulama Ortamı
Dosya       : simpleCounter.py
Açıklama    : SimpleCounter doğrulaması için Bus Functional Model (BFM) 
              ve yardımcı fonksiyonlar

Bileşenler  : 
    SimpleCounterBFM : Driver/Monitor görevleri içeren Singleton BFM sınıfı
        • command_driver  : Kuyruktan komutları alıp DUT pinlerine yazar
        • command_monitor : Scoreboard için komutları yakalar
        • result_monitor  : Kontrol için DUT çıkışlarını yakalar
    
    counter_prediction : Beklenen sonuçlar için altın model (golden model)

Temel Kavramlar:
    - Singleton deseni    : Bileşenler arası paylaşımlı BFM erişimi
    - get_nowait/put_nowait : Monitor'ler için bloklamayan kuyruk işlemleri
    - get/put             : Senkronizasyon için bloklayan kuyruk işlemleri
    - Driver/Monitor ayrımı : Veri gönderme ve izleme sorumluluklarının ayrılması

Kuyruk Yapısı:
    ┌─────────────┐  put   ┌──────────────────┐  get_nowait  ┌─────────┐
    │   Tester    │───────▶│ command_driver_q │─────────────▶│ Driver  │──▶ DUT
    └─────────────┘        └──────────────────┘              └─────────┘
    
    ┌─────────┐  put_nowait  ┌───────────────────┐  get   ┌────────────┐
    │ Monitor │─────────────▶│ command_monitor_q │───────▶│ Scoreboard │
    └─────────┘              └───────────────────┘        └────────────┘

Yazar       : Veysel Aras
Tarih       : 2026
============================================================================
"""



import cocotb
from cocotb.triggers import FallingEdge, ClockCycles
from cocotb.clock import Clock
from cocotb.queue import Queue, QueueEmpty
import pyuvm

def get_int(signal): # sinyal degerini int cevirme
	try:
		int_val = int(signal.value)
	except ValueError:
		int_val = 0
	return int_val

class SimpleCounterBFM(metaclass=pyuvm.Singleton): # Singleton pattern ile tek instance 
	def __init__(self): # BFM init 
		self.dut = cocotb.top
		self.command_driver_queue = Queue(maxsize=2)
		self.results_monitor_queue = Queue(maxsize=0)
		self.command_monitor_queue = Queue(maxsize=0)

	async def reset(self): # reset icin fonksiyon 
		await FallingEdge(self.dut.clk)
		self.dut.rstn.value = 0
		self.dut.enable.value = 0
		self.dut.load.value = 0
		self.dut.load_value.value = 0
		self.dut.up_down.value = 0
		
		await ClockCycles(self.dut.clk, 5)
		
		self.dut.rstn.value = 1
		await FallingEdge(self.dut.clk)


	async def result_monitor(self): # result degerlerini izleme fonksiyonu
		while True:
			await FallingEdge(self.dut.clk) # her clk dususunde

			load = get_int(self.dut.load) 
			enable = get_int(self.dut.enable)
			if load == 0 and enable == 1: # sadece enable aktifken sonucu al
				result = (get_int(self.dut.count), get_int(self.dut.overflow), get_int(self.dut.underflow))
				
				self.results_monitor_queue.put_nowait(result) # sonucu put_nowait ile kuyruge ekle
				# neden put_nowait kullandik? cunku burada bekleme yapmak istemiyoruz, izleme asenkron calisiyor

	async def command_monitor(self): # command degerlerini izleme fonksiyonu
		while True:
			await FallingEdge(self.dut.clk)
			
			enable = get_int(self.dut.enable)
			load = get_int(self.dut.load)
			if enable == 1 and load == 0: # sadece enable aktifken komutu al
				command = (enable, load, int(self.dut.load_value.value), int(self.dut.up_down.value)) # komut tuple olustur
				self.command_monitor_queue.put_nowait(command) # komutu kuyruge ekle
				# neden put_nowait kullandik? cunku burada bekleme yapmak istemiyoruz, izleme asenkron calisiyor
				# burada herhangi bir hata donmez cunku command_monitor_queue maxsize=0 ile tanimlandi, yani sinirsiz

	async def command_driver(self): # komut gonderme fonksiyonu
		while True:
			await FallingEdge(self.dut.clk)
			try:
				command = self.command_driver_queue.get_nowait() # komutu kuyruge ekle
				# neden get_nowait kullandik? cunku burada bekleme yapmak istemiyoruz, komut gonderme asenkron calisiyor

				(enable, load, load_value, up_down) = command

				self.dut.enable.value = enable
				self.dut.load.value = load
				self.dut.load_value.value = load_value
				self.dut.up_down.value = up_down

			except QueueEmpty:
				self.dut.enable.value = 0
				self.dut.load.value = 0

	async def send_command(self, enable, load, load_value, up_down): # komut gonderme fonksiyonu
		command_tuple = (enable, load, load_value, up_down)

		await self.command_driver_queue.put(command_tuple) # komutu kuyruge ekle
		# neden put kullandik? cunku burada bekleme yapabiliriz ve yapmaliyiz

	async def get_command(self): # komut alma fonksiyonu
		command = await self.command_monitor_queue.get() # komutu kuyruge ekle
		return command
	
	async def get_result(self): # sonuc alma fonksiyonu
		result = await self.results_monitor_queue.get() # sonucu kuyruge ekle
		return result
	
	def start_tasks(self): # BFM icindeki asenkron gorevleri baslatma fonksiyonu
		cocotb.start_soon(Clock(self.dut.clk, 10, unit="ns").start())
		cocotb.start_soon(self.command_driver())
		cocotb.start_soon(self.command_monitor())
		cocotb.start_soon(self.result_monitor())

def counter_prediction(enable, load, load_value, up_down): # sayac tahmin fonksiyonu
	simple_counter = load_value
	if(enable):
		if(up_down):
			simple_counter = simple_counter + 1
			if(simple_counter >= 256):
				simple_counter = 0
				return (simple_counter, 1, 0)
			else:
				return (simple_counter, 0, 0)
		else:
			simple_counter = simple_counter - 1
			if(simple_counter <= 0):
				simple_counter = 255
				return (simple_counter, 0, 1)
			else:
				return (simple_counter, 0, 0)
	else:
		return (load_value, 0, 0)
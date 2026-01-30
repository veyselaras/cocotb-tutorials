"""
================================================================================
TESTBENCH: TinyShifter BFM Tabanlı Testbench
================================================================================

AÇIKLAMA:
---------
Bu testbench, TinyShifter modülünü doğrulamak için TinyAluBfm pattern'ini
kullanır. BFM (Bus Functional Model) sayesinde sinyal seviyesi detayları
soyutlanır ve test kodu daha temiz/okunabilir olur.

MİMARİ:
-------
    ┌─────────────────────┐
    │   tinyShifterTest   │ ← Test senaryosu
    └────────┬────────────┘
             │ send_instruction() / get_result()
             ▼
    ┌─────────────────┐
    │  TinyShifterBFM │ ← Singleton BFM
    │  ┌───────────┐  │
    │  │cmd_driver │──┼──► start, data_in, shift_amount, instruction
    │  ├───────────┤  │
    │  │cmd_monitor│◄─┼─── start (0→1 geçişi)
    │  ├───────────┤  │
    │  │result_mon │◄─┼─── done (0→1 geçişi), data_out
    │  └───────────┘  │
    └─────────────────┘
             │
             ▼
    ┌───────────────────┐
    │ 	  TinyShifter   │ ← DUT
    └───────────────────┘

BFM YAPISI:
-----------
- command_driver_queue (maxsize=1) : Test → Driver (blocking send)
- command_monitor_queue (maxsize=0): Monitor → Test (gönderilen komutları doğrula)
- result_monitor_queue (maxsize=0) : Monitor → Test (sonuçları al)

QUEUE KULLANIMI:
----------------
                    Nonblocking              Blocking
Driver tarafı:      get_nowait()             -
Monitor tarafı:     put_nowait()             -
Test tarafı:        -                        await get(), await put()

TEST AKIŞI:
-----------
1. Clock başlat
2. BFM oluştur (Singleton)
3. DUT'u resetle
4. BFM task'lerini başlat
5. Her instruction için:
   - Rastgele data_in ve shift_amount üret
   - send_instruction() ile gönder
   - get_command() ile monitor'dan doğrula
   - shifter_prediction() ile beklenen sonucu hesapla
   - get_result() ile gerçek sonucu al
   - Karşılaştır ve logla
6. Coverage kontrolü (tüm instruction'lar test edildi mi?)
7. Assert passed

DOSYA BİLGİLERİ:
----------------
Yazar  : Veysel Aras
Tarih  : 30.01.2026
Araçlar: cocotb 2.0.1, pyuvm

================================================================================
"""


import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge
from cocotb.queue import Queue, QueueEmpty, QueueFull

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

import random

import pyuvm

import enum

# Instruction tiplerini tanimlayan enum
class InstructionType(enum.IntEnum):
	NOP = 0
	LOAD = 1
	SHL = 2
	SHR = 3
	ROL = 4
	ROR = 5

# signal value'lerini int'e ceviren fonksiyon
def signal2int(signal):
	try:
		result = int(signal.value)
	except ValueError:
		result = 0
	return result

# shifter icin beklenen sonucu hesaplayan fonksiyon "Golden Model"
def shifter_prediction(data_in, shift_amount, instruction):
	if instruction == InstructionType.NOP:
		result = data_in
	elif instruction == InstructionType.LOAD:
		result = shift_amount
	elif instruction == InstructionType.SHL:
		result = (data_in << shift_amount) & 0xFF
	elif instruction == InstructionType.SHR:
		result = (data_in >> shift_amount) & 0xFF
	elif instruction == InstructionType.ROL:
		shift_amount = shift_amount % 8
		result = ((data_in << shift_amount) | (data_in >> (8 - shift_amount))) & 0xFF
	elif instruction == InstructionType.ROR:
		shift_amount = shift_amount % 8
		result = ((data_in >> shift_amount) | (data_in << (8 - shift_amount))) & 0xFF
	return result

# Bus Functional Model (BFM) sinifi, singleton olarak tanimlandi cunku tek bir instance yeterli
class TinyShifterBFM(metaclass = pyuvm.Singleton):

	# Constructor'da gerekli queue'lar olusturuluyor
	def __init__(self):
		self.dut = cocotb.top
		self.command_driver_queue = Queue(maxsize=1)
		self.command_monitor_queue = Queue(maxsize=0)
		self.result_monitor_queue = Queue(maxsize=0)

	# reset senaryosu
	async def reset(self):
		self.dut.rst_n.value = 0
		await FallingEdge(self.dut.clk)
		self.dut.rst_n.value = 1
		await FallingEdge(self.dut.clk)

	# command driver gorevi yapacak async fonksiyon
	async def command_driver(self):
		self.dut.start.value = 0
		self.dut.data_in.value = 0
		self.dut.shift_amount.value = 0
		self.dut.instruction.value = 0
		while True:
			# her clock dongusunu bekle
			await FallingEdge(self.dut.clk)

			# sinyal degerlerini oku
			start = signal2int(self.dut.start)
			done = signal2int(self.dut.done)

			# eger start ve done 0 ise command_driver_queue'de bekleyen komutu al ve start sinyalini 1 yap
			if start == 0 and done == 0:
				try:
					# instruction_tuple = (data_in, shift_amount, instruction)

					# alttaki satirlar calismadi cunku tuple, await ifadesiyle calimiyormus
					instruction_tuple = self.command_driver_queue.get_nowait()

					# sinyal degerlerini ayarla
					self.dut.data_in.value = instruction_tuple[0]
					self.dut.shift_amount.value = instruction_tuple[1]
					self.dut.instruction.value = instruction_tuple[2]

					self.dut.start.value = 1
				except QueueEmpty: # eger queue bos ise hata yakala ve donguye devam et
					continue
			# eger start 1 ve done 0 ise start sinyalini tekrar 0 yap
			elif start == 1:
				if done == 0:
					self.dut.start.value = 0

	# result monitor gorevi yapacak async fonksiyon
	async def result_monitor(self):
		prev_done = 0
		while True:
			# her clock dongusunu bekle
			await FallingEdge(self.dut.clk)

			# done sinyalini oku
			done = signal2int(self.dut.done)
			
			# eger done sinyali yukselmisse data_out degerini result_monitor_queue'ya koy
			if done == 1 and prev_done == 0:
				data_out = signal2int(self.dut.data_out)
				self.result_monitor_queue.put_nowait(data_out)
			# done degerini prev_done olarak sakla
			prev_done = done

	# command monitor gorevi yapacak async fonksiyon 
	async def command_monitor(self):
		prev_start = 0
		while True:
			# her clock dongusunu bekle
			await FallingEdge(self.dut.clk)

			# start sinyalini oku
			start = signal2int(self.dut.start)

			# eger start sinyali yukselmisse data_in, shift_amount ve instruction degerlerini command_monitor_queue'ya koy
			if start == 1 and prev_start == 0:
				instruction_tuple = ( signal2int(self.dut.data_in), signal2int(self.dut.shift_amount),
						signal2int(self.dut.instruction))
				# put_nowait ile queue'ya ekle, bu queue'nin maxsize'i 0(sonsuz) oldugu icin burada hata olusmaz
				self.command_monitor_queue.put_nowait(instruction_tuple)
			prev_start = start

	# tum task'lari baslatan fonksiyon, clock haric
	def start_tasks(self):
		cocotb.start_soon(self.command_driver())
		cocotb.start_soon(self.result_monitor())
		cocotb.start_soon(self.command_monitor())

	# blocking communication ile command ve result almayi saglayan fonksiyonlar
	async def get_command(self):
		# burada blocking communication yapiliyor cunku tb buraya girdigi zaman 
		# data gelene kadar beklemesini istiyoruz bu da blocking communication ile mumkun oluyor
		command = await self.command_monitor_queue.get() 
		return command
	
	# blocking communication ile result almayi saglayan fonksiyon
	async def get_result(self):
		# burada blocking communication yapiliyor cunku tb buraya girdigi zaman 
		# data gelene kadar beklemesini istiyoruz bu da blocking communication ile mumkun oluyor
		result = await self.result_monitor_queue.get()
		return result

	# non-blocking communication ile instruction gondermeyi saglayan fonksiyon
	async def send_instruction(self, data_in, shift_amount, instruction):
		await self.command_driver_queue.put((data_in, shift_amount, instruction))


@cocotb.test()
async def tinyShifterTest(dut):
	# Test basarili mi degil mi bilgisini tutan degisken
	passed = True
	# functional coverage icin kullanilacak set
	cvg = set()

	cocotb.start_soon(Clock(dut.clk, 10, "ns").start())

	# BFM instance'ini al
	bus_functional_modal = TinyShifterBFM()

	# Reset senaryosu
	await bus_functional_modal.reset()

	# BFM task'larini baslat
	bus_functional_modal.start_tasks()

	# Tüm instruction tipleri için test döngüsü
	instructions = list(InstructionType)
	for instruction in instructions:
		# Rastgele data_in ve shift_amount değerleri üret
		# shift_amount 1-7 aralığında olmalı
		data_in = random.randint(0, 255)
		shift_amount = random.randint(1, 7)

		# Instruction'ı BFM'e gönder
		await bus_functional_modal.send_instruction(data_in, shift_amount, instruction)

		# Gönderilen komutu BFM'den al
		instruction_tuple = await bus_functional_modal.get_command()
		
		# Functional coverage set'ine instruction tipini ekle
		cvg.add(InstructionType(instruction_tuple[2]))

		# Beklenen sonucu golden model ile hesapla
		prediction = shifter_prediction(data_in, shift_amount, instruction)

		# BFM'den sonucu al
		result = await bus_functional_modal.get_result()

		# Sonucu beklenen değerle karşılaştır ve logla
		if prediction == result:
			logger.info(f"[INFO] Prediction is equal to result: {data_in:02x} {instruction.name} = {result:02x}")
		else:
			logger.error(f"[ERROR] Prediction is not equal to result: {data_in:02x} {instruction.name} != {result:02x}")
			passed = False
		
	# Functional coverage kontrolü
	if len(set(InstructionType) - cvg) > 0:
		logger.error(f"Functional coverage error. Missed: {set(InstructionType) - cvg}")
		passed = False
	else:
		logger.info("Covered all operations")

	assert passed
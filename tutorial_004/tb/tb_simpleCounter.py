"""
============================================================================
Proje       : SimpleCounter PyUVM Doğrulama Ortamı
Dosya       : tb_simpleCounter.py
Açıklama    : SimpleCounter modülü için PyUVM test ortamı

Mimari:
    ┌─────────────────────────────────────────────────────────────┐
    │                      uvm_test                               │
    │  ┌───────────────────────────────────────────────────────┐  │
    │  │                    uvm_env                            │  │
    │  │  ┌─────────────┐              ┌─────────────────────┐ │  │
    │  │  │   Tester    │──send_cmd───▶│        BFM          │ │  │
    │  │  │  (uyaran)   │              │  ┌───────────────┐  │ │  │
    │  │  └─────────────┘              │  │  cmd_driver   │──┼─┼──▶ DUT
    │  │                               │  │  cmd_monitor  │◀─┼─┼── 
    │  │  ┌─────────────┐              │  │  result_mon   │◀─┼─┼──
    │  │  │ Scoreboard  │◀──get_cmd────│  └───────────────┘  │ │  │
    │  │  │ (doğrulama) │◀──get_result─│                     │ │  │
    │  │  └─────────────┘              └─────────────────────┘ │  │
    │  └───────────────────────────────────────────────────────┘  │
    └─────────────────────────────────────────────────────────────┘

Sınıf Hiyerarşisi:
    uvm_test
    └── uvm_env (BaseEnv)
        ├── Scoreboard (uvm_component) : Sonuç doğrulama
        └── Tester (uvm_component)     : Uyaran üretimi
            ├── RandomTester    : Rastgele test verileri
            ├── UpCountTester   : Taşma (overflow) testi
            └── DownCountTester : Alt taşma (underflow) testi

Test Sınıfları:
    - RandomTest    : Rastgele operand testi
    - UpCountTest   : Taşma sınır testi (0xFF → 0x00)
    - DownCountTest : Alt taşma sınır testi (0x00 → 0xFF)

Kullanılan UVM Fazları:
    1. build_phase               : Bileşen oluşturma (hiyerarşi kurulumu)
    2. start_of_simulation_phase : BFM görevlerini başlatma
    3. run_phase                 : Test uyaranlarını çalıştırma
    4. check_phase               : Sonuçları doğrulama

Veri Akışı:
    Tester ──▶ send_command() ──▶ driver_queue ──▶ cmd_driver ──▶ DUT
                                                                   │
    Scoreboard ◀── get_result() ◀── result_queue ◀── result_monitor ◀┘

Yazar       : Veysel Aras
Tarih       : 2026
============================================================================
"""



import cocotb
from cocotb.triggers import ClockCycles
import pyuvm
from pyuvm import *
import random
from pathlib import Path
import sys
# All testbenches use tinyalu_utils, so store it in a central
# place and add its path to the sys path so we can import it
sys.path.insert(0, str(Path().resolve()))
from simpleCounter import SimpleCounterBFM, counter_prediction  # noqa: E402

class BaseTester(uvm_component): # temel tester sinifi
	def start_of_simulation_phase(self): # sim baslangic fazinda calisir
		SimpleCounterBFM().start_tasks() # BFM icindeki asenkron gorevleri baslat

	async def run_phase(self): # calisma fazi asenkron fonksiyonu
		self.raise_objection() # sim bitimine itiraz et
		self.bfm = SimpleCounterBFM() # BFM nesnesi olustur
		
		await self.bfm.reset() # BFM reset fonksiyonunu cagir
		self.logger.info("[RESET IS DONE]")
		(enable, load, load_value, up_down) = self.get_operands() # test verilerini al

		await self.bfm.send_command(0, 1, load_value, up_down) # load komutunu gonder
		await self.bfm.send_command(enable, 0, load_value, up_down) # sayim komutunu gonder

		await ClockCycles(self.bfm.dut.clk, 10) # 10 clock bekle
		self.drop_objection()

class RandomTester(BaseTester):
	def get_operands(self): # rastgele test verileri olusturma fonksiyonu
		return (1, 1, 198, 1)

class UpCountTester(BaseTester): # overflow testi
	def get_operands(self):
		return (1, 0, 255, 1)


class DownCountTester(BaseTester): # underflow testi
	def get_operands(self):
		return (1, 0, 0, 0)
	
class ScoreBoard(uvm_component): # skor tahtasi sinifi
	async def get_commands(self): # komutlari alma fonksiyonu
		while True:
			command = await self.bfm.get_command() # komutu al
			self.commands.append(command) # komutu listeye ekle

	async def get_results(self): # sonuclari alma fonksiyonu
		while True:
			result = await self.bfm.get_result() # sonucu al
			self.results.append(result) # sonucu listeye ekle

	def start_of_simulation_phase(self): # sim baslangic fazinda calisir
		self.bfm = SimpleCounterBFM()
		self.results = []
		self.commands = []

		cocotb.start_soon(self.get_results())
		cocotb.start_soon(self.get_commands())

	def check_phase(self): # kontrol fazi
		passed = True 
		for command in self.commands: # tum komutlari kontrol et
			(enable, load, load_value, up_down) = command

			actual = self.results.pop(0) 
			prediction = counter_prediction(enable, load, load_value, up_down)

			if(actual == prediction): # sonuc tahminle uyusuyor mu?
				self.logger.info(f"Command:	{command}")
				self.logger.info(f"{actual} is equal to {prediction}")
				self.logger.info("[PASSED]")
			else:
				self.logger.info("[FAILED]")
				passed = False

		assert passed

class BaseEnv(uvm_env): # temel environment sinifi
	def build_phase(self):
		self.scoreboard = ScoreBoard("scoreboard", self)

class RandomEnv(BaseEnv): # rastgele test verileri ureten environment sinifi
	def build_phase(self):
		super().build_phase()
		self.tester = RandomTester("tester", self)

class UpCountEnv(BaseEnv): # overflow testi environment sinifi
	def build_phase(self):
		super().build_phase()
		self.tester = UpCountTester("tester", self)


class DownCountEnv(BaseEnv): # underflow testi environment sinifi
	def build_phase(self):
		super().build_phase()
		self.tester = DownCountTester("tester", self)

@pyuvm.test() # rastgele test
class RandomTest(uvm_test):
	def build_phase(self):
		self.env = RandomEnv("env", self)

@pyuvm.test() # overflow testi
class UpCountTest(uvm_test):
	def build_phase(self):
		self.env = UpCountEnv("env", self)

@pyuvm.test() # underflow testi
class DownCountTest(uvm_test):
	def build_phase(self):
		self.env = DownCountEnv("env", self)
# ============================================================================
# regbank_components.py — pyUVM Testbench Bileşenleri
# ============================================================================
#
# Bu dosya, register bank doğrulaması için gereken tüm UVM bileşenlerini
# içerir ve klasik UVM mimarisini Python/pyUVM ile uygular.
#
# RegisterModel (Golden Model): Donanımın beklenen davranışını yazılımda
#   modelleyen referans modeldir. RW, RO, W1C ve Counter register
#   davranışlarını simüle eder; scoreboard bu modele bakarak DUT çıkışlarını
#   doğrular.
#
# BaseTester → RWRegisterTester / RORegisterTester / W1CRegisterTester:
#   Test senaryolarını üreten bileşenlerdir. BaseTester soyut bir temel sınıf
#   olup, generate_transaction() metodu alt sınıflar tarafından override
#   edilerek her register türüne özel stimulus dizileri üretilir. Factory
#   pattern sayesinde test sınıfından hangi tester'ın kullanılacağı belirlenir.
#
# Driver: Tester'dan gelen transaction'ları BFM aracılığıyla DUT pin'lerine
#   dönüştürür; yani stimulus'u fiziksel sinyallere çevirir.
#
# WriteMonitor / ReadMonitor: DUT üzerindeki yazma ve okuma işlemlerini
#   bağımsız olarak izler ve yakalanan transaction'ları analysis port
#   üzerinden scoreboard'a iletir.
#
# ScoreBoard: Write ve read monitor'lardan gelen gerçek sonuçları golden
#   model'in beklenen değerleriyle karşılaştırarak pass/fail kararı verir.
#
# RegBankEnv: Tüm bileşenleri bir araya getiren ve aralarındaki TLM
#   bağlantılarını kuran üst ortam sınıfıdır.
#
#
#   Testbench Mimarisi (RegBankEnv)
#   ================================
#
#   +-------------------------------------------------------------+
#   | RegBankEnv                                                  |
#   |                                                             |
#   |  +-------------+    put    +-----------+    get   +-------+ |
#   |  |   Tester    |--------->| value_fifo |--------->| Driver| |
#   |  | (BaseTester)|  port    +-----------+    port   +---+---+ |
#   |  +-------------+                                      |     |
#   |   Factory ile override:                               |     |
#   |   - RWRegisterTester                          BFM     |     |
#   |   - RORegisterTester                      write_reg() |     |
#   |   - W1CRegisterTester                     read_reg()  |     |
#   |                                                       v     |
#   |  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .    |
#   |                                                             |
#   |                       +-------------+                       |
#   |                       |     DUT     |                       |
#   |                       | register_bank|                      |
#   |                       +------+------+                       |
#   |                              |                              |
#   |  .  .  .  .  .  .  .  .  .  |  .  .  .  .  .  .  .  .  .    |
#   |                              |                              |
#   |              +---------------+----------------+             |
#   |              |                                |             |
#   |              v                                v             |
#   |  +---------------------+        +---------------------+     |
#   |  |    WriteMonitor     |        |     ReadMonitor     |     |
#   |  | (wr_en, addr, wdata)|        | (rd_en↓, out_rdata) |     |
#   |  +----------+----------+        +----------+----------+     |
#   |             |                              |                |
#   |             | analysis_port                | analysis_port  |
#   |             v                              v                |
#   |  +--------------------------------------------------------+ |
#   |  |                    ScoreBoard                          | |
#   |  |                                                        | |
#   |  |   write_export  +-------+  +---------+ read_export     | |
#   |  |   ------------->| Model |  | Compare |<-----------     | |
#   |  |                 +---+---+  +----+----+                 | |
#   |  |                     |           |                      | |
#   |  |                     +-----+-----+                      | |
#   |  |                           |                            | |
#   |  |                     PASS / FAIL                        | |
#   |  +--------------------------------------------------------+ |
#   +--------------------------------------------------------------+
#
# ============================================================================


from pyuvm import *
import random

import cocotb
from cocotb.triggers import ClockCycles

from regbank_bfm import RegBankBFM, RegTransaction

# Golden model 
class RegisterModel:
	
	ADDR_RW  = 0
	ADDR_RO  = 1
	ADDR_W1C = 2
	ADDR_CNT = 3

	RO_VALUE = 0xA5

	def __init__(self):
		self.reset()
		pass

	def reset(self):
		self.regs = {
			self.ADDR_RW:  0x00,          # RW: Başlangıçta 0
			self.ADDR_RO:  self.RO_VALUE, # RO: Sabit 0xA5
			self.ADDR_W1C: 0x00,          # W1C: Başlangıçta 0
			self.ADDR_CNT: 0x00,          # Counter: Başlangıçta 0
        }
		pass

	def write(self, addr, data):
		# 8 bit maskeleme yapiyoruz ki data 8 biti asmasin
		data = data & 0xFF

		if addr == self.ADDR_RW:
			self.regs[addr] = data
		elif addr == self.ADDR_RO:
			self.regs[addr] = self.RO_VALUE
		elif addr == self.ADDR_W1C:
			self.regs[addr] = self.regs[addr] & (~data & 0xFF)
		elif addr == self.ADDR_CNT:
			pass

		return self.regs.get(addr, 0xFF) # addr varsa deger doner yok ff doner
	
	def read(self, addr):
		if addr in self.regs:
			return self.regs[addr]
		else:
			return 0xFF
		
	def set_ext_event(self, value):
		value = value & 0xFF
		self.regs[self.ADDR_W1C] = self.regs[self.ADDR_W1C] | value
		

	def tick(self):
		self.regs[self.ADDR_CNT] = (self.regs[self.ADDR_CNT] + 1) & 0xFF
		

	def get_reg_name(self, addr):
		names = {
			self.ADDR_RW:  "RW_REG",
			self.ADDR_RO:  "RO_REG",
			self.ADDR_W1C: "W1C_REG",
			self.ADDR_CNT: "COUNTER",
        }
		return names.get(addr, f"UNKNOWN({addr})")

	def __repr__(self):
		"""Model durumunu string olarak döndür (debug için)"""
		lines = ["RegisterModel State:"]
		for addr in range(4):
			name = self.get_reg_name(addr)
			value = self.regs[addr]
			lines.append(f"  [{addr}] {name}: 0x{value:02X}")
		return "\n".join(lines)
	
# BaseTester bizim tester'larimizin temelini olusturacak. 
# Bu sinif, test senaryolarimizi tanimlamak icin kullanilacak.
# Bu sinifta generate_transaction metodunu tanimliyoruz, 
# bu metod her test senaryosu icin override edilecek ve o senaryoya uygun transaction'lar uretecek.
class BaseTester(uvm_component):

	def build_phase(self):
		self.put_port = uvm_put_port("put_port", self)

	async def run_phase(self):
		self.raise_objection()
		transactions = self.generate_transaction()
		for trancsation in transactions:
			await self.put_port.put(trancsation)

		await ClockCycles(signal=cocotb.top.clk, num_cycles=10, rising=False)

		self.drop_objection()

	def generate_transaction(self):
		raise RuntimeError("You must extend BaseTester and override it.")
	
# RW, RO ve W1C register'lar icin farkli tester'lar tanimlayalim.
class RWRegisterTester(BaseTester):
	def generate_transaction(self):
		transaction_arr = [RegTransaction("write", 0, 0x00), RegTransaction("read", 0), 
					 RegTransaction("write", 0, 0xFF), RegTransaction("read", 0),
					 RegTransaction("write", 0, 0xAA), RegTransaction("read", 0), 
					 RegTransaction("write", 0, 0x1F), RegTransaction("read", 0)]
		return transaction_arr
	
class RORegisterTester(BaseTester):
	def generate_transaction(self):
		transaction_arr = [RegTransaction("read", 1),
					 RegTransaction("write", 1, wdata=0xAB), RegTransaction("read", 1),
					 RegTransaction("write", 1, wdata=0xCD), RegTransaction("read", 1)]
		return transaction_arr

class W1CRegisterTester(BaseTester):
	def generate_transaction(self):
		transaction_arr = [RegTransaction("write", 2, wdata=0x00), RegTransaction("read", 2),
					 RegTransaction("set_ext_event", 2, ext_event=0xFF), RegTransaction("read", 2),
					 RegTransaction("write", 2, wdata=0x0F), RegTransaction("read", 2),
					 RegTransaction("write", 2, wdata=0xF0), RegTransaction("read", 2)]
		return transaction_arr
	
# Driver, Monitor ve Scoreboard sınıflarını tanımlayalım.
class Driver(uvm_driver):
	def build_phase(self):
		# BFM ile etkileşim kurmak için bir referans oluşturalım ve get_port tanımlayalım.
		self.bfm = RegBankBFM()
		self.get_port = uvm_get_port("get_port", self)

	# run_phase metodunu tanımlayalım. 
	# Bu metod, tester tarafından üretilen transaction'ları alacak ve BFM aracılığıyla DUT'a uygulayacak.
	async def run_phase(self):
		self.bfm.start_tasks()
		await self.bfm.reset()
		while True:
			transaction = await self.get_port.get()
			if(transaction.op_type == "write"):
				await self.bfm.write_reg(transaction.addr, transaction.wdata)
			elif(transaction.op_type == "read"):
				await self.bfm.read_reg(transaction.addr)
			elif(transaction.op_type == "set_ext_event"):
				self.bfm.set_ext_event(transaction.ext_event)
				await ClockCycles(signal=cocotb.top.clk, num_cycles=1)
				self.bfm.clear_ext_event()

# Monitor sınıflarını tanımlayalım. 
# Bu sınıflar, register bank'teki yazma ve okuma işlemlerini izlemek için kullanılacak.
# Debug loglarini acmak icin self.set_logging_level_hier(level), 
# self.set_logging_level(level) metodlarini kullanabiliriz.

# default olarak log level INFO'dur
class WriteMonitor(uvm_monitor):
	def build_phase(self):
		self.bfm = RegBankBFM()
		self.analysis_port = uvm_analysis_port("analysis_port", self)

	async def run_phase(self):
		while True:
			transaction = await self.bfm.get_write_transaction()
			self.analysis_port.write(transaction)
			self.logger.debug(f"Write Monitor: {transaction}")

class ReadMonitor(uvm_monitor):
	def build_phase(self):
		self.bfm = RegBankBFM()
		self.analysis_port = uvm_analysis_port("analysis_port", self)

	async def run_phase(self):
		while True:
			transaction = await self.bfm.get_read_transaction()
			self.analysis_port.write(transaction)
			self.logger.debug(f"Read Monitor: {transaction}")

# Scoreboard sınıfını tanımlayalım.
class ScoreBoard(uvm_scoreboard):
	# Scoreboard, monitor'lardan gelen transaction'ları alacak ve golden model ile 
	# karşılaştırarak doğruluk kontrolü yapacak.
	def build_phase(self):
		# Golden model referansi
		self.reg_model = RegisterModel()
		# Monitor'lardan gelen transaction'ları almak için gerekli fifo'ları ve port'ları tanımlayalım.
		self.write_mon_fifo = uvm_tlm_analysis_fifo("write_mon_fifo", self)
		self.read_mon_fifo = uvm_tlm_analysis_fifo("read_mon_fifo", self)
		
		self.write_getPort = uvm_get_port("write_getPort", self)
		self.read_getPort = uvm_get_port("read_getPort", self)
	
	# connect_phase ile port'ları fifo'lara bağlayalım ve 
	# monitor'lardan gelen transaction'ları alacak export'ları tanımlayalım.
	def connect_phase(self):
		self.write_getPort.connect(self.write_mon_fifo.get_export)
		self.read_getPort.connect(self.read_mon_fifo.get_export)

		self.read_export = self.read_mon_fifo.analysis_export
		self.write_export = self.write_mon_fifo.analysis_export

	# Bu faz, monitor'lardan gelen transaction'ları alacak ve golden model 
	# ile karşılaştırarak doğruluk kontrolü yapacak.
	def check_phase(self):
		passed = True
		while True:
			# write ve read transaction'larını sırayla almaya çalışalım.
			success, transaction = self.write_getPort.try_get()
			# transaction varsa işleyelim, yoksa read transaction'larını almaya çalışalım.
			if not success:
				break
			self.logger.info(f" OP_TYPE: {transaction.op_type}, ADDR: {transaction.addr:X}, WDATA: {transaction.wdata:02X}")
			# transaction'ı golden model'e uygulayalım.
			if transaction.op_type == "set_ext_event":
				self.reg_model.set_ext_event(transaction.ext_event)
				self.logger.info(f" Set EXT_EVENT: 0x{transaction.ext_event:02X}")
			else:
				self.reg_model.write(transaction.addr, transaction.wdata)

			# read transaction'larını almaya çalışalım.
			success, transaction = self.read_getPort.try_get()
			if not success:
				break
			self.logger.info(f" OP_TYPE: {transaction.op_type}, ADDR: {transaction.addr:X}, WDATA: {transaction.wdata:02X}")
			# transaction'ı golden model'e uygulayalım ve sonucu kontrol edelim.
			expected = self.reg_model.read(transaction.addr)
			actual = transaction.rdata

			# debug loglari ile beklenen ve gerceklesen degerleri gormek icin asagidaki log satirini kullanabiliriz.
			if expected != actual:
				passed = False
				self.logger.error(f"Simulation error! exp={expected}, got={actual}")
			else:
				self.logger.info(f"Simulation passed! exp={expected}, got={actual}")

		# test sonucunu assert ile kontrol edelim.
		assert passed, "Scoreboard: Test FAILED!"

# Environment sınıfını tanımlayalım.
class RegBankEnv(uvm_env):
	def build_phase(self):
		# Environment bileşenlerini oluşturalım: tester, driver, monitor'lar ve scoreboard.
		# Tester'lar create metodu ile olusturulacak, bu sayede 
		# factory pattern ile override ederek farklı tester'lar tanimlayabiliriz.
		self.tester = BaseTester.create("tester", self)
		self.driver = Driver("driver", self)
		# fifo'ları tanımlayalım, bu fifo'lar tester'dan driver'a transaction'ları iletmek için kullanılacak.
		self.value_fifo = uvm_tlm_fifo("value_fifo", self)

		self.write_mon = WriteMonitor("write_mon", self)
		self.read_mon = ReadMonitor("read_mon", self)

		self.scoreboard = ScoreBoard("scoreboard", self)

	def connect_phase(self):
		# Tester'ın put_port'unu value_fifo'nun put_export'una, 
		# driver'ın get_port'unu value_fifo'nun get_export'una bağlayalım.
		self.tester.put_port.connect(self.value_fifo.put_export)
		self.driver.get_port.connect(self.value_fifo.get_export)

		# Monitor'ların analysis_port'larını scoreboard'un ilgili export'larına bağlayalım.
		# subscribe yapisi ile monitor'lar gelen transaction'lari scoreboard'a iletecek.
		self.write_mon.analysis_port.connect(self.scoreboard.write_export)
		self.read_mon.analysis_port.connect(self.scoreboard.read_export)


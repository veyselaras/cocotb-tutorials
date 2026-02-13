# ============================================================================
# regbank_bfm.py — Bus Functional Model (BFM) ve Transaction Tanımları
# ============================================================================
#
# Bu dosya, register bank donanım modülü ile cocotb/pyUVM testbench ortamı
# arasındaki köprüyü kurar.
#
# RegTransaction: Testbench içinde dolaşan her işlemi (write, read,
#   set_ext_event) temsil eden veri nesnesidir. UVM bileşenleri arasında
#   taşınan temel birimdir.
#
# RegBankBFM (Singleton): DUT pin'leri üzerinden düşük seviyeli okuma/yazma
#   protokolünü yönetir. Reset, write ve read sinyallerinin zamanlama
#   diyagramına uygun şekilde sürülmesini sağlar. Ayrıca iki adet monitor
#   görevi (write_monitor_task, read_monitor_task) ile DUT'tan gelen yazma
#   ve okuma işlemlerini gerçek zamanlı olarak yakalar ve Queue'lar
#   aracılığıyla UVM monitor bileşenlerine iletir.
#
#   RegBankBFM Sinyal Akışı
#   ========================
#
#   +------------------+                          +-------------------+
#   |     Driver       |                          |       DUT         |
#   |                  |   write_reg(addr, data)  |  (register_bank)  |
#   |  write_reg() ----+----> in_addr      ------>|                   |
#   |  read_reg()  ----+----> in_wdata     ------>|  rw_reg           |
#   |  set_ext_event()-+----> in_wr_en     ------>|  w1c_reg          |
#   |                  |      in_rd_en     ------>|  counter_reg      |
#   |                  |      ext_event    ------>|  readOnly_reg     |
#   +------------------+                          |                   |
#                                                 |   out_rdata ---+  |
#   +------------------+                          +----------------+--+
#   | Write Monitor    |                                           |
#   |                  |   wr_en, addr, wdata, ext_event           |
#   |  write_mon_queue |<--- (posedge clk ile örneklenir)          |
#   +------------------+                                           |
#                                                                  |
#   +------------------+                                           |
#   | Read Monitor     |   rd_en düşen kenar + out_rdata           |
#   |                  |<------------------------------------------+
#   |  read_mon_queue  |<--- (posedge clk ile örneklenir)
#   +------------------+
#
# ============================================================================


import cocotb
import pyuvm
from cocotb.triggers import RisingEdge, ClockCycles, FallingEdge
from cocotb.clock import Clock
from cocotb.queue import Queue

def get_int(signal): # sinyal degerini int cevirme
	try:
		int_val = int(signal.value)
	except ValueError:
		int_val = 0
	return int_val

# regbank_bfm.py dosyasında RegBankBFM ve RegTransaction sınıflarını tanımlayacağız. 
# RegBankBFM, register bank ile etkileşim kurmak için kullanılacak bir BFM (Bus Functional Model) sınıfıdır. 
# RegTransaction ise yapılan işlemleri temsil eden bir sınıftır.
class RegTransaction:
	# Transaction türlerini tanımla: "write", "read", "set_ext_event"
	def __init__(self, op_type, addr, wdata=0, ext_event=0, rdata=0):
		self.op_type = op_type
		self.addr = addr
		self.wdata = wdata
		self.ext_event = ext_event
		self.rdata = rdata
		
	# Transaction nesnelerinin karşılaştırılmasını kolaylaştırmak için __eq__ metodunu tanımlayalım.
	def __eq__(self, other):
		if not isinstance(other, RegTransaction):
			return False
		return (self.op_type == other.op_type and
	 		self.addr == other.addr and
			self.wdata == other.wdata and
			self.ext_event == other.ext_event and
			self.rdata == other.rdata)
	
	# Transaction türlerini ve adreslerini daha okunabilir hale getirmek için __repr__ metodunu tanımlayalım.
	def __repr__(self):
		if self.op_type == "write":
			return f"WR ADDR:0x{self.addr:X} DATA:0x{self.wdata:02X}"
		elif self.op_type == "read":
			return f"RD ADDR:0x{self.addr:X} DATA:0x{self.rdata:02X}"
		elif self.op_type == "set_ext_event":
			return f"EXT_EVENT: 0x{self.ext_event:02X}"
		else:
			return f"{self.op_type.upper()} ADDR:0x{self.addr:X}"
		

class RegBankBFM(metaclass=pyuvm.Singleton):
	# BFM ile gerekli queue'leri ve dut referansını tanımlayalım
	def __init__(self):
		self.dut = cocotb.top
		self.write_mon_queue = Queue(maxsize=0)
		self.read_mon_queue = Queue(maxsize=0)
		
	# reset islemi
	async def reset(self):
		await FallingEdge(self.dut.clk)
		self.dut.rstn.value = 0
		self.dut.in_addr.value = 0
		self.dut.in_wdata.value = 0
		self.dut.in_rd_en.value = 0
		self.dut.in_wr_en.value = 0
		self.dut.ext_event.value = 0

		await ClockCycles(self.dut.clk, 5)

		self.dut.rstn.value = 1
		await FallingEdge(self.dut.clk)
		
	# register bank ile yazma islemi
	async def write_reg(self, addr, data):
		await FallingEdge(self.dut.clk)

		self.dut.in_addr.value = addr
		self.dut.in_wdata.value = data
		self.dut.in_wr_en.value = 1

		await FallingEdge(self.dut.clk)

		self.dut.in_wr_en.value = 0
		await FallingEdge(self.dut.clk)


	# register bank ile okuma islemi
	async def read_reg(self, addr):
		await FallingEdge(self.dut.clk)

		self.dut.in_addr.value = addr
		self.dut.in_rd_en.value = 1

		await FallingEdge(self.dut.clk)

		self.dut.in_rd_en.value = 0
		await FallingEdge(self.dut.clk)

	# set_ext_event islemi
	def set_ext_event(self, value):
		self.dut.ext_event.value = value


	# clear_ext_event islemi
	def clear_ext_event(self):
		self.dut.ext_event.value = 0
		
	# write_monitor_task ve read_monitor_task görevlerini tanımlayalım. 
	# Bu görevler, register bank'teki yazma ve okuma işlemlerini izlemek için kullanılacak.
	async def write_monitor_task(self):
		ext_event_prev = 0
		while True:
			await RisingEdge(self.dut.clk)
			wr_en = get_int(self.dut.in_wr_en)
			ext_event = get_int(self.dut.ext_event)

			if wr_en == 1:
				addr = get_int(self.dut.in_addr)
				wdata = get_int(self.dut.in_wdata)

				transaction = RegTransaction("write", addr, wdata, ext_event=ext_event)

				await self.write_mon_queue.put(transaction)

			if ext_event != ext_event_prev:
				addr = get_int(self.dut.in_addr)
				wdata = get_int(self.dut.in_wdata)

				transaction = RegTransaction("set_ext_event", addr, wdata, ext_event=ext_event)
				await self.write_mon_queue.put(transaction)


	async def read_monitor_task(self):
		rd_en_prev = 0
		while True:
			await RisingEdge(self.dut.clk)
			rd_en = get_int(self.dut.in_rd_en)

			if rd_en == 0 and rd_en_prev == 1:
				addr = get_int(self.dut.in_addr)
				rdata = get_int(self.dut.out_rdata)


				transaction = RegTransaction("read", addr, rdata=rdata, ext_event=rdata)

				await self.read_mon_queue.put(transaction)
			
			rd_en_prev = rd_en

	# asenkron görevleri başlatmak için start_tasks metodunu tanımlayalım.
	def start_tasks(self):
		cocotb.start_soon(Clock(self.dut.clk, 10, unit="ns").start())
		cocotb.start_soon(self.write_monitor_task())
		cocotb.start_soon(self.read_monitor_task())

	# testbench'in diğer bileşenlerinin BFM ile etkileşim kurabilmesi için 
	# get_write_transaction ve get_read_transaction metodlarını tanımlayalım.
	async def get_write_transaction(self):
		transaction = await self.write_mon_queue.get()
		return transaction

	async def get_read_transaction(self):
		transaction = await self.read_mon_queue.get()
		return transaction

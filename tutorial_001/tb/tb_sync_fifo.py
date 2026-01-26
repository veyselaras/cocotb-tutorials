import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer, RisingEdge, FallingEdge, ReadOnly

import random

async def reset_handler(dut, duration_ns=20):
	dut.rstn.value = 0
	await Timer(duration_ns, "ns")
	dut.rstn.value = 1
	dut._log.info("Reset Bitti")

async def simple_monitor(dut, captured_data_list):
	while True:
		await RisingEdge(dut.clk)

		enable_out_val = dut.enable_out.value
		empty_val = dut.empty.value

		if enable_out_val == 1 and empty_val == 0:
			await RisingEdge(dut.clk)
			await ReadOnly()
			output_data = int(dut.data_out.value)
			dut._log.info(f"Monitor Yakaladi: {output_data}")
			
			captured_data_list.append(output_data)



class SimpleDriver:
	def __init__(self, dut):
		self.dut = dut

		self.dut.rstn.value = 0
		self.dut.enable_in.value = 0
		self.dut.enable_out.value = 0
		self.dut.data_in.value = 0

	async def sender(self, value):
		await FallingEdge(self.dut.clk)
		self.dut.data_in.value = value
		self.dut.enable_in.value = 1

		await RisingEdge(self.dut.clk)

		await FallingEdge(self.dut.clk)

		self.dut.enable_in.value = 0

	async def receiver(self):
		await FallingEdge(self.dut.clk)

		self.dut.enable_out.value = 1
		
		await RisingEdge(self.dut.clk)
		await FallingEdge(self.dut.clk)

		self.dut.enable_out.value = 0






@cocotb.test()
async def write_after_read(dut):
	monitors_data = []
	expected_data = [random.randint(0, 255) for _ in range(16)]

	cocotb.start_soon(Clock(dut.clk, 10, "ns").start())

	await reset_handler(dut)
	await RisingEdge(dut.clk)

	cocotb.start_soon(simple_monitor(dut, monitors_data))

	driver = SimpleDriver(dut)
	dut.rstn.value = 1

	for val in expected_data:
		await driver.sender(val)
		dut._log.info(f"Yazilan: {val}")
		
	await RisingEdge(dut.clk)
	await ReadOnly()

	dut._log.info(f"Write sonrasi - empty: {dut.empty.value}, full: {dut.full.value}")
	dut._log.info(f"write_ptr: {int(dut.write_ptr.value)}, read_ptr: {int(dut.read_ptr.value)}")

	for val in expected_data:
		await driver.receiver()
		

	await Timer(200, "ns")

	dut._log.info(f"Giden: {expected_data}")
	dut._log.info(f"Gelen: {monitors_data}")

	assert monitors_data == expected_data, f"Hata! Giden: {expected_data}, Gelen: {monitors_data}"
	dut._log.info("Test Basarili")

@cocotb.test()
async def write_and_read_1by1(dut):
	monitors_data = []
	expected_data = [random.randint(0, 255) for _ in range(16)]

	cocotb.start_soon(Clock(dut.clk, 10, "ns").start())

	await reset_handler(dut)
	await RisingEdge(dut.clk)

	cocotb.start_soon(simple_monitor(dut, monitors_data))

	driver = SimpleDriver(dut) 
	""" Burada reseti 0 yapiyorum cunku driver'in kurucu metodunda rstn 0 yapiliyor """
	dut.rstn.value = 1

	for val in expected_data:
		await driver.sender(val)
		dut._log.info(f"Yazilan: {val}")

		await driver.receiver()

	await Timer(200, "ns")

	dut._log.info(f"Giden: {expected_data}")
	dut._log.info(f"Gelen: {monitors_data}")

	assert monitors_data == expected_data, f"Hata! Giden: {expected_data}, Gelen: {monitors_data}"
	dut._log.info("Test Basarili")

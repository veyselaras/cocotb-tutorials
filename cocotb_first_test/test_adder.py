import cocotb
from cocotb.triggers import Timer

@cocotb.test()
async def test_adder(dut):
    """Test adder"""
    dut.a.value = 5
    dut.b.value = 10
    await Timer(2, units='ns')
    assert dut.sum.value == 15, f"Adder result is incorrect: {dut.sum.value} != 15"
    print("Test passed!")

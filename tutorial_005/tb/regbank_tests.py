# ============================================================================
# regbank_test.py — pyUVM Test Senaryoları
# ============================================================================
#
# Bu dosya, register bank doğrulaması için çalıştırılabilir test sınıflarını
# tanımlar. Her test, UVM factory mekanizmasını kullanarak BaseTester'ı ilgili
# alt sınıfla override eder; böylece aynı ortam (RegBankEnv) farklı stimulus
# dizileriyle yeniden kullanılır.
#
#   RWRegisterTest  : Read-Write register'a çeşitli değerler yazıp geri
#                     okuyarak doğru saklama davranışını doğrular.
#   RORegisterTest  : Read-Only register'a yazma denemeleri yapıp değerin
#                     değişmediğini kontrol eder.
#   W1CRegisterTest : Harici olay ile bit set edip, Write-1-to-Clear
#                     mekanizmasının doğru çalıştığını doğrular.
#
# Testler @pyuvm.test() dekoratörü ile işaretlenir ve cocotb runner
# tarafından otomatik olarak keşfedilip çalıştırılır.
#
#
#   Factory Override Mekanizması
#   =============================
#
#   Her test sınıfı, aynı RegBankEnv ortamını kullanır; yalnızca tester
#   bileşeni factory aracılığıyla değiştirilir:
#
#   +------------------+         +--------------------+
#   | RWRegisterTest   |         |     RegBankEnv     |
#   |                  | build   |                    |
#   |  factory.override+-------->|  tester = ?        |
#   |  BaseTester -->  |         |                    |
#   |  RWRegisterTester|         +--------------------+
#   +------------------+
#                                        |
#   +------------------+                 |  factory resolve
#   | RORegisterTest   |                 v
#   |  BaseTester -->  |         +--------------------+
#   |  RORegisterTester|         | Seçilen Tester     |
#   +------------------+         |--------------------|
#                                | RWRegisterTester   |  W:0x00 → R → W:0xFF → R ...
#   +------------------+         | RORegisterTester   |  R → W:0xAB → R → W:0xCD → R
#   | W1CRegisterTest  |         | W1CRegisterTester  |  W:0x00 → R → EXT:0xFF → R ...
#   |  BaseTester -->  |         +--------------------+
#   |  W1CRegisterTester|
#   +------------------+
#
# ============================================================================


import pyuvm
from pyuvm import *

from regbank_components import *

# Test sınıflarını tanımlayalım. Her test sınıfı farklı bir register türünü test edecek şekilde tasarlanacak.

@pyuvm.test()
class RWRegisterTest(uvm_test):
	def build_phase(self):
		# Factory pattern kullanarak BaseTester'ı RWRegisterTester ile override ederiz
		uvm_factory().set_type_override_by_type(BaseTester, RWRegisterTester)
		self.env = RegBankEnv("env", self)

@pyuvm.test()
class RORegisterTest(uvm_test):
	def build_phase(self):
		uvm_factory().set_type_override_by_type(BaseTester, RORegisterTester)
		self.env = RegBankEnv("env", self)

@pyuvm.test()
class W1CRegisterTest(uvm_test):
	def build_phase(self):
		uvm_factory().set_type_override_by_type(BaseTester, W1CRegisterTester)
		self.env = RegBankEnv("env", self)
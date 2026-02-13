# Register Bank Verification with pyUVM

cocotb ve pyUVM kullanılarak geliştirilmiş, 4 adresli register bank için UVM tabanlı doğrulama ortamı.

## Register Türleri

| Adres | Tür | Açıklama |
|-------|-----|----------|
| 0x0 | RW | Genel amaçlı okuma-yazma register |
| 0x1 | RO | Salt okunur, sabit `0xA5` değeri döndürür |
| 0x2 | W1C | Write-1-to-Clear, `ext_event` ile set edilir, yazılan 1'ler temizler |
| 0x3 | Counter | Her clock cycle'da otomatik artan salt okunur sayaç |

## Testbench Mimarisi

```
+---------------------------------------------------------------+
| RegBankEnv                                                    |
|                                                               |
|  +-------------+    put    +-----------+    get    +-------+  |
|  |   Tester    |--------->| value_fifo |--------->| Driver|  |
|  | (BaseTester)|  port    +-----------+    port   +---+---+  |
|  +-------------+                                      |      |
|   Factory ile override:                               |      |
|   - RWRegisterTester                          BFM     |      |
|   - RORegisterTester                      write_reg() |      |
|   - W1CRegisterTester                     read_reg()  |      |
|                                                       v      |
|  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .   |
|                       +-------------+                        |
|                       |     DUT     |                        |
|                       | register_bank|                       |
|                       +------+------+                        |
|                              |                               |
|  .  .  .  .  .  .  .  .  .  |  .  .  .  .  .  .  .  .  .   |
|              +---------------+----------------+              |
|              v                                v              |
|  +---------------------+        +---------------------+     |
|  |    WriteMonitor     |        |     ReadMonitor     |     |
|  +----------+----------+        +----------+----------+     |
|             | analysis_port                | analysis_port  |
|             v                              v                |
|  +--------------------------------------------------------+ |
|  |                    ScoreBoard                          | |
|  |   write_export --> | Golden Model | <-- read_export    | |
|  |                       PASS / FAIL                      | |
|  +--------------------------------------------------------+ |
+--------------------------------------------------------------+
```

## Dosya Yapısı

```
.
├── register_bank.sv       # RTL tasarımı (SystemVerilog)
├── regbank_bfm.py         # Bus Functional Model ve Transaction tanımları
├── regbank_components.py  # UVM bileşenleri (Driver, Monitor, Scoreboard, Env)
├── regbank_test.py        # Test senaryoları
└── Makefile               # cocotb build & run
```

## Özellikler

- **Factory Pattern:** `BaseTester` override edilerek aynı ortamda farklı test senaryoları çalıştırılır
- **TLM İletişim:** FIFO ve analysis port tabanlı bileşenler arası veri akışı
- **Singleton BFM:** Tüm bileşenlerin aynı BFM instance'ına erişimi
- **Golden Model:** `RegisterModel` ile beklenen davranışın yazılımda modellenmesi
- **Scoreboard:** Otomatik karşılaştırma ve pass/fail kararı

## Test Senaryoları

| Test | Açıklama |
|------|----------|
| `RWRegisterTest` | RW register'a farklı değerler yazıp geri okuma |
| `RORegisterTest` | RO register'a yazma denemesi, değerin değişmediğini doğrulama |
| `W1CRegisterTest` | `ext_event` ile bit set edip W1C mekanizmasını doğrulama |

> **Not:** Counter register testi henüz eklenmemiştir.

## Çalıştırma

```bash
make SIM=icarus TOPLEVEL=register_bank MODULE=regbank_test
```

## Notlar

Egzersiz senaryosu AI yardımıyla oluşturulmuştur. RTL kodlaması, testbench geliştirme ve debug süreci bana aittir.

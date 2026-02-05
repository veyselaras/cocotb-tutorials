# SimpleCounter PyUVM Verification

8-bit bidirectional counter için PyUVM tabanlı doğrulama ortamı.

## 📁 Dosya Yapısı

| Dosya | Açıklama |
|-------|----------|
| `simpleCounter.sv` | DUT - SystemVerilog RTL tasarımı |
| `simpleCounter.py` | BFM + Golden Model |
| `tb_simpleCounter.py` | PyUVM Testbench |

## 🎯 DUT Özellikleri

- 8-bit yukarı/aşağı sayaç
- Senkron load, asenkron active-low reset
- Overflow bayrağı (0xFF → 0x00)
- Underflow bayrağı (0x00 → 0xFF)

## 🧪 Test Senaryoları

| Test | Açıklama |
|------|----------|
| `RandomTest` | Rastgele operandlar |
| `UpCountTest` | Overflow sınır testi |
| `DownCountTest` | Underflow sınır testi |

## 🏗️ Mimari
```
uvm_test
└── uvm_env
    ├── Scoreboard (doğrulama)
    └── Tester (uyaran üretimi)
        └── BFM (DUT iletişimi)
```

"""
================================================================================
ÖRNEK 2.2: Polling ile Durum Kontrolü (Çoklu Sorumluluk Yönetimi)
================================================================================

SENARYO AÇIKLAMASI:
-------------------
Bu örnek, bir task'ın birden fazla sorumluluğu olduğu durumda nonblocking
iletişimin neden gerekli olduğunu gösterir. Worker task'ı hem iş kuyruğunu
kontrol etmeli hem de boşta kaldığında başka işler yapabilmelidir.

Senaryo: Bir fabrika işçisi (Worker) düşün. Bu işçinin iki görevi var:
1. Konveyör bandını (Queue) kontrol etmek ve gelen işleri yapmak
2. İş yokken "boşta bekliyorum" raporlamak ve idle istatistiği tutmak

JobGenerator rastgele aralıklarla (10-30ns) işleri kuyruğa ekler. Worker her
5ns'de kuyruğu kontrol eder, iş varsa yapar, yoksa idle sayacını artırır.
Belirli süre iş gelmezse (timeout) Worker görevi bitirir.

KULLANILAN KAVRAMLAR:
---------------------
1. Polling Pattern: Düzenli aralıklarla bir kaynağı kontrol etme.
   "Her 5ns'de kuyruğa bak, iş var mı?"

2. get_nowait(): Kuyruktan veri almayı dener, yoksa QueueEmpty fırlatır.
   Worker bu sayede kuyruğu kontrol edip hemen başka işlere geçebilir.

3. Çoklu Sorumluluk: Tek bir task'ın birden fazla iş yapması.
   - Birincil görev: İş kuyruğundan iş al ve işle
   - İkincil görev: İstatistik tut, durum raporla

4. Idle Tracking: İş olmadan geçen süreyi takip etme. Bu bilgi performans
   analizi için önemlidir. "Worker ne kadar süre boşta kaldı?"

5. Timeout with Reset: İş alındığında timeout sayacı sıfırlanır. Böylece
   "son işten bu yana geçen süre" takip edilir, "toplam süre" değil.

BLOCKING KULLANSAYDIK NE OLURDU?
--------------------------------
Worker şöyle yazılsaydı:
    while True:
        job = await queue.get()  # Blocking!
        process(job)

Problemler:
- Worker kuyruk boşken TAMAMEN durur
- "Boşta bekliyorum" logu yazamaz
- Idle istatistiği tutamaz
- Başka hiçbir iş yapamaz

NONBLOCKING ile:
    while True:
        try:
            job = queue.get_nowait()
            process(job)
        except QueueEmpty:
            log("Boşta bekliyorum")  # Bu satır çalışabilir!
            idle_count += 1          # İstatistik tutulabilir!
            await Timer(5, "ns")

Worker her 5ns'de "uyanır", kuyruğu kontrol eder, gerekli işleri yapar.

POLLING vs EVENT-DRIVEN:
------------------------
Polling (bu örnekte kullandığımız):
- Düzenli aralıklarla kontrol et
- Basit ve öngörülebilir
- CPU/simülasyon zamanı harcar
- Tepki süresi = poll interval kadar gecikebilir

Event-driven (blocking get):
- Olay olunca uyan
- Daha verimli (gereksiz kontrol yok)
- Kod daha basit
- Tek bir olaya tepki verebilir

Polling tercih edilir:
- Birden fazla sorumluluk varsa
- Timeout gerekiyorsa
- Periyodik işlemler yapılacaksa
- İstatistik/monitoring gerekiyorsa

BEKLENEN DAVRANIŞ:
------------------
0ns    - Worker başlar, kuyruk boş, "Bekliyor..."
5ns    - Worker: "Bekliyor..." (idle: 5ns)
10ns   - Worker: "Bekliyor..." (idle: 10ns)
15ns   - JobGenerator: İş-1 eklendi (rastgele zamanlama)
15ns   - Worker: İş-1 alındı! İşleniyor (3ns)
18ns   - Worker: İş-1 tamamlandı!
20ns   - Worker: "Bekliyor..." (idle: 0ns, sayaç sıfırlandı)
25ns   - Worker: "Bekliyor..." (idle: 5ns)
...
(İşler ve beklemeler devam eder)
...
120ns  - Worker: "50ns boyunca iş gelmedi, timeout!"

DENEY ÖNERİLERİ:
----------------
1. poll_interval değerini değiştir (1ns, 10ns, 20ns) - tepki süresi nasıl değişir?
2. JobGenerator'ın iş aralığını değiştir - Worker daha mı meşgul olur?
3. Worker sayısını artır (Örnek 3.2'ye geçiş) - iş yükü nasıl dağılır?
4. Worker'a ikinci bir kuyruk ekle (komut kuyruğu) - çoklu kaynak yönetimi

RTL VERIFICATION KARŞILIĞI:
---------------------------
1. Clock-Senkron Monitor: Her clock edge'de hem DUT çıkışını kontrol et
   hem de iç sayaçları güncelle.

2. Watchdog Task: Periyodik olarak sistem durumunu kontrol et, belirli
   süre aktivite yoksa alarm ver.

3. Coverage Collector: Her cycle'da coverage bilgisi topla, aynı zamanda
   stimulus kuyruğunu da kontrol et.

4. Multi-Interface Monitor: Birden fazla interface'i aynı anda izleyen
   tek bir monitor task'ı.

DOSYA BİLGİLERİ:
----------------
Yazar: [Veysel Aras]
Tarih: [28.01.2026]
cocotb versiyonu: 2.0.1
Örnek seviyesi: Orta

================================================================================
"""


import cocotb
from cocotb.triggers import Timer
from cocotb.queue import Queue, QueueFull, QueueEmpty

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

import random

async def jobGenerator(queue):
	i = 1
	for i in range(6):
		await Timer(random.randint(10, 30), "ns")
		await queue.put(i)
		logger.info(f"[JOBGENERATOR] is {i} queue'ye eklendi.")
		i += 1
	logger.info(f"[JOBGENERATOR] Islem Bitti.")

async def worker(queue):
	noJob_timer = 0

	while True:
		try:
			job = queue.get_nowait()
			noJob_timer = 0

			logger.info(f"[WORKER] {job} numarali is alindi.")

			await Timer(job*3, "ns")
			logger.info(f"[WORKER] {job} numarali is bitti.")
		except:
			logger.info(f"[WORKER] Is yok, bekliyor.")
			await Timer(5, "ns")
			noJob_timer += 5

		if(noJob_timer == 50):
			break
	logger.info(f"[WORKER] TIMEOUT: Islem Bitti.")

@cocotb.test()
async def worker_timeout(_):
	queue = Queue()

	cocotb.start_soon(jobGenerator(queue))
	cocotb.start_soon(worker(queue))

	await Timer(200, "ns")
	logger.info(f"[TEST] Test Bitti.")
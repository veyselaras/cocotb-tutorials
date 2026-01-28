"""
================================================================================
ÖRNEK 2.1: Timeout ile Veri Bekleme (Nonblocking get_nowait Kullanımı)
================================================================================

SENARYO AÇIKLAMASI:
-------------------
Bu örnek, blocking get() yerine nonblocking get_nowait() kullanarak timeout
mekanizması oluşturmayı öğretir. Consumer belirli bir süre içinde veri gelmezse
"TIMEOUT" vererek çıkar, sonsuza kadar beklemez.

Senaryo: Producer yavaş çalışıyor (20ns arayla) ve sadece 2 veri gönderiyor.
Consumer her veriyi aldıktan sonra bir sonrakini bekliyor. Üçüncü veri hiç
gelmeyecek, bu yüzden Consumer 50ns bekledikten sonra timeout'a düşecek.

KULLANILAN KAVRAMLAR:
---------------------
1. get_nowait(): Kuyruktan veri almayı DENER. Kuyruk boşsa beklemez,
   hemen QueueEmpty exception fırlatır. Bu bir FONKSIYON'dur, coroutine
   değil, bu yüzden await KULLANILMAZ.

2. QueueEmpty Exception: get_nowait() çağrıldığında kuyruk boşsa fırlatılır.
   try-except bloğu ile yakalanır ve uygun şekilde işlenir.

3. Polling Pattern: Belirli aralıklarla kuyruğu kontrol etme döngüsü.
   "Veri var mı? Yok. Bekle. Veri var mı? Yok. Bekle. Veri var mı? Var!"

4. Timeout Mekanizması: Toplam bekleme süresini sayan bir sayaç. Bu sayaç
   belirlenen limite ulaşırsa, artık beklemeyi bırak ve çık.

BLOCKING vs NONBLOCKING KARŞILAŞTIRMASI:
----------------------------------------
Blocking get():
    data = await queue.get()  # Veri gelene kadar SONSUZA KADAR bekler
    
    Avantaj: Kod basit
    Dezavantaj: Timeout yapılamaz, task tamamen durur

Nonblocking get_nowait():
    try:
        data = queue.get_nowait()  # await YOK!
    except QueueEmpty:
        await Timer(10, "ns")  # Kendimiz bekleme ekliyoruz
        elapsed += 10
        if elapsed >= timeout:
            break  # Timeout!
    
    Avantaj: Timeout yapılabilir, bekleme süresi kontrol edilebilir
    Dezavantaj: Kod daha karmaşık, exception handling gerekli

TIMEOUT MANTIĞI:
----------------
1. elapsed = 0 (bekleme sayacı)
2. Kuyruğu kontrol et (get_nowait)
3. Veri varsa → al, elapsed'i sıfırla
4. Veri yoksa → Timer ile bekle, elapsed'i artır
5. elapsed >= timeout ise → TIMEOUT, döngüden çık
6. Değilse → 2. adıma dön

BEKLENEN DAVRANIŞ:
------------------
0ns    - Consumer başlar, kuyruk boş, beklemeye başlar
10ns   - Consumer: "Kuyruk boş, 10ns beklendi"
20ns   - Producer: "Birinci" gönderildi
20ns   - Consumer: "Birinci" alındı
20ns   - Consumer: "Kuyruk boş, 10ns beklendi" (ikinci veriyi bekliyor)
30ns   - Consumer: "Kuyruk boş, 20ns beklendi"
40ns   - Producer: "İkinci" gönderildi, Producer BİTTİ
40ns   - Consumer: "İkinci" alındı
40ns   - Consumer: "Kuyruk boş, 10ns beklendi" (üçüncü veriyi bekliyor)
...    - Consumer beklemeye devam ediyor
90ns   - Consumer: "TIMEOUT! 50ns içinde veri gelmedi"

NEDEN TIMEOUT GEREKLİ?
----------------------
Gerçek sistemlerde her zaman beklenen veri gelmeyebilir:
- Hatalı DUT yanıt vermeyebilir
- Network paketi kaybolabilir
- Sensör arızalanabilir

Blocking get() kullansaydık test SONSUZA KADAR beklerdi. Timeout ile:
- Test makul sürede biter
- Hata durumu tespit edilir
- Sistem "stuck" durumuna düşmez

DENEY ÖNERİLERİ:
----------------
1. timeout_ns değerini değiştir ve davranışı gözlemle
2. Producer'ın daha fazla veri göndermesini sağla (timeout olmasın)
3. Poll interval'ı değiştir (daha sık/seyrek kontrol)

RTL VERIFICATION KARŞILIĞI:
---------------------------
1. Response Timeout: DUT'a komut gönderildi, yanıt bekleniyor. Belirli
   sürede yanıt gelmezse test FAIL.
2. Watchdog Timer: Testbench'in sonsuz döngüye girmesini önleme.
3. Protocol Timeout: Bus protokollerinde ACK/NACK bekleme süreleri.

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

async def producer(queue): # Veri üreten görev
	counter = 1
	while True:
		await queue.put(counter) # blocking sekilde queue'ye ekle
		logger.info(f"[PRODUCER] Queue'ye {counter} eklendi.")
		counter += 1
		if(counter == 11):
			break
		await Timer(20, "ns") # 20ns arayla veri üret
	logger.info(f"[PRODUCER] islemi bitti.")

async def consumer(queue): # Veri tüketen görev
	while True: # Sürekli veri kontrolü
		attemp = 0
		data = None
		while attemp < 5: # 5 deneme (50ns timeout)
			try:
				data = queue.get_nowait() # await YOK! nonblocking alım
				break
			except QueueEmpty: # Kuyruk boşsa hata yakala
				logger.info("[CONSUMER] queue bos 10 ns bekle")
				await Timer(10, "ns") # 10ns bekle
				attemp += 1 # Deneme sayısını artır

		if data != None: # Veri alındıysa işle
			logger.info(f"[CONSUMER] queue'den {data} alindi.")
		else:
			logger.info(f"[CONSUMER] TIMEOUT: 50ns icerisinde veri alinamadi.")
			break
	logger.info(f"[CONSUMER] Bitti!")

# Ana test fonksiyonu
@cocotb.test()
async def nowait_ornek(_):
	queue = Queue() 

	# Gonderici ve alici islemlerini baslat
	cocotb.start_soon(producer(queue))
	cocotb.start_soon(consumer(queue))

	await Timer(300, "ns")
	
	logger.info(f"Test Bitt!")
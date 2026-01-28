"""
================================================================================
ÖRNEK: Sensor ve Data Logger (put_nowait + get_nowait)
================================================================================

SENARYO AÇIKLAMASI:
-------------------
Bu örnek, hızlı bir veri üreticisinin (sensor) yavaş bir tüketiciyle (data logger)
iletişim kurduğu gerçekçi bir senaryoyu simüle eder. Sensör sabit aralıklarla
(her 5ns'de bir) sıcaklık ölçümü yapar ve buffer'a yazar. Data logger ise bu
verileri alıp işler, ancak her veriyi işlemesi 8ns sürer. Bu hız uyumsuzluğu
nedeniyle buffer dolacak ve veri kaybı (data drop) yaşanacaktır.

KULLANILAN KAVRAMLAR:
---------------------
1. put_nowait(): Kuyruğa veri koymayı DENER. Kuyruk doluysa QueueFull exception
   fırlatır ve beklemez. Sensör gibi gerçek zamanlı sistemlerde kullanılır çünkü
   bu sistemler bekleyemez, bir sonraki işlem zamanı gelecektir.

2. get_nowait(): Kuyruktan veri almayı DENER. Kuyruk boşsa QueueEmpty exception
   fırlatır ve beklemez. Logger'ın istatistik tutması, timeout kontrolü yapması
   gibi ek görevleri olduğu için blocking get() kullanamaz.

3. QueueFull Exception: put_nowait() çağrıldığında kuyruk doluysa fırlatılır.
   Bu durumda sensör veriyi "drop" eder (kaybeder) ve devam eder.

4. QueueEmpty Exception: get_nowait() çağrıldığında kuyruk boşsa fırlatılır.
   Bu durumda logger kısa süre bekler ve tekrar dener (polling pattern).

NEDEN BLOCKING KULLANAMIYORUZ?
------------------------------
Sensör için: Gerçek bir sensör (ADC, sıcaklık sensörü, ivmeölçer vb.) sabit
frekansta veri üretir. Donanım "bekleyemez". Eğer blocking put() kullansaydık
ve buffer doluysa, sensör orada takılıp kalırdı. Bir sonraki ölçüm zamanı
geçerdi ve timing tamamen bozulurdu.

Logger için: Logger sadece veri okumakla kalmıyor, aynı zamanda istatistik
tutuyor (kaç veri işlendi, ne kadar idle kaldı). Eğer blocking get() kullansaydı,
buffer boşken tamamen donardı. İstatistikleri güncelleyemezdi ve timeout
mekanizması çalışmazdı.

BEKLENEN DAVRANIŞ:
------------------
- Sensör her 5ns'de bir veri üretir (toplam 15 okuma)
- Logger her veriyi 8ns'de işler (sensörden yavaş!)
- Buffer kapasitesi sadece 3 eleman
- Başlangıçta logger yetişebilir, buffer boş kalır
- Zamanla logger geride kalır, buffer dolmaya başlar
- Buffer dolunca sensör veri kaybetmeye başlar (QueueFull)
- Test sonunda istatistikler raporlanır: kaç veri gönderildi, kaç kayboldu

RTL VERIFICATION KARŞILIĞİ:
---------------------------
1. FIFO Overflow Testi: DUT içindeki FIFO'nun taşma durumunu test etmek.
   Driver hızlı veri gönderiyor, DUT yavaş işliyor, FIFO doluyor.
   DUT'un overflow flag'ini doğru kaldırıp kaldırmadığı kontrol edilir.

2. Backpressure Testi: Network interface'lerinde paketler hızlı geliyor
   ama işleme yavaş. Interface'in ready/valid handshaking mekanizmasını
   doğru uygulayıp uygulamadığı test edilir.

3. Rate Mismatch Analizi: Producer ve consumer arasındaki hız farkının
   sistem davranışına etkisini analiz etmek.

PARAMETRELERİ DEĞİŞTİREREK DENEYLER:
------------------------------------
- Buffer boyutunu artır (maxsize=10): Veri kaybı azalır mı?
- Logger'ı hızlandır (process_time_ns=4): Logger artık yetişir mi?
- Sensörü yavaşlat (interval_ns=10): Kayıp tamamen önlenir mi?

DOSYA BİLGİLERİ:
----------------
Yazar: [Veysel Aras]
Tarih: [28.01.2026]
cocotb versiyonu: 2.0.1
Python versiyonu: 3.12+

================================================================================
"""



import cocotb
from cocotb.triggers import Timer
from cocotb.queue import Queue, QueueFull, QueueEmpty

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

import random

async def sensor(queue, reading_number): # Sensorden veri okuma ve queue'ye ekleme
	sent_count = 0 # Basariyla gonderilen veri sayisi
	drop_count = 0 # Kaybedilen veri sayisi

	for reading_id in range(reading_number): # Belirtilen sayida veri okuma
		await Timer(6, "ns") # Her okuma arasinda 6ns bekle
		try: 
			queue.put_nowait(random.randint(100, 1000)) # Rastgele veri uret ve queue'ye ekle eger queue doluysa QueueFull firlatir
			logger.info("[SENSOR] data queue'ye eklendi.") 
			sent_count += 1 # Basariyla gonderilen veri sayisini artir

		except QueueFull: # Queue doluysa
			drop_count += 1 # Kaybedilen veri sayisini artir
			logger.info("[SENSOR] Queue full data drop edildi.")

	# Queue doluysa bitis sinyali gondermek icin deneme yap
	while True: # Bitis sinyali gonderme
		try: 
			queue.put_nowait(None) # Bitis sinyali olarak None gonder
			logger.info("[SENSOR] Bitis sinyali gönderildi") 
			break # Loop'tan cik
		except QueueFull:
			await Timer(5, "ns") # Queue doluysa bekle ve tekrar dene

	# Sensorden istatistik raporu		
	logger.info(f"[SENSOR] === SENSOR ISTATISTIKLERI ===")
	logger.info(f"[SENSOR] Toplam okuma: {reading_number}")
	logger.info(f"[SENSOR] Basariyla gonderilen: {sent_count}")
	logger.info(f"[SENSOR] Kaybedilen (drop): {drop_count}")
	logger.info(f"[SENSOR] Kayip orani: {drop_count/reading_number*100:.1f}%")

async def dataLogger(queue): # Data logger: Queue'den veri alma ve isleme
	noData_Timer = 0 # Timeout sayaci
	noData_counter = 0 # Bos bekleme sayaci

	processed_data_counter = 0 # Islenen veri sayaci
	total_value = 0 # Islenen verilerin toplami

	while True:
		try: 
			data = queue.get_nowait() # Queue'den veri almaya calis eger bossa exception firlatir

			if data == None: # Bitis sinyali alindi
				logger.info(f"[DATA_LOGGER] Bitis bayragi geldi!")
				break

			logger.info(f"[DATA_LOGGER] Veri alindi: {data}")
			
			noData_Timer = 0 # Basarili veri alindiginda timeout sayacini sifirla
			await Timer(8, "ns")

			logger.info(f"[DATA_LOGGER] Veri islendi, yeni veri: {data**2 - 1}")
			total_value = data**2 - 1

			processed_data_counter += 1 

		except QueueEmpty: # Queue bossa
			logger.info(f"[DATA_LOGGER] Queue bos!")
			await Timer(5, "ns")
			noData_Timer += 1
			noData_counter += 1

		if noData_Timer > 50: # 50ns boyunca veri gelmediyse timeout
			logger.info(f"[DATA_LOGGER] TIMEOUT: 50ns'den fazla surede veri gelmedi")

	# Data logger istatistik raporu
	avg_value = total_value / processed_data_counter if processed_data_counter > 0 else 0
	logger.info(f"[LOGGER] === LOGGER ISTATISTIKLERI ===")
	logger.info(f"[LOGGER] Islenen veri sayisi: {processed_data_counter}")
	logger.info(f"[LOGGER] Ortalama deger: {avg_value:.1f}")
	logger.info(f"[LOGGER] Bos bekleme cycle'i: {noData_counter}")

# Ana test fonksiyonu
@cocotb.test()
async def nonblocking_example(_):
	queue = Queue(maxsize = 3) # Kucuk buffer boyutu ile basla

	cocotb.start_soon(sensor(queue, 50)) # 50 veri okuma icin sensor baslat
	cocotb.start_soon(dataLogger(queue)) # Data logger baslat 

	await Timer(1000, "ns") # Testin tamamlanmasi icin yeterli sure bekle

	logger.info(f"[TEST] Test Basarili!")

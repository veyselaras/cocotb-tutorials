"""
================================================================================
ÖRNEK 1.2: Sayaç ile Producer-Consumer (Bitiş Sinyali ve Sonuç Doğrulama)
================================================================================

SENARYO AÇIKLAMASI:
-------------------
Bu örnek, Producer-Consumer pattern'inin daha gelişmiş bir versiyonunu gösterir.
Producer 1'den 10'a kadar sayıları kuyruğa koyar, Consumer bu sayıları alıp
toplar. Test sonunda toplam değer doğrulanır (beklenen: 1+2+3+...+10 = 55).

Bu örnekte ek olarak "bitiş sinyali" mekanizması öğretilir. Producer işini
bitirdiğinde None değeri göndererek Consumer'a "artık veri gelmeyecek"
mesajı verir. Consumer None aldığında döngüden çıkar.

KULLANILAN KAVRAMLAR:
---------------------
1. Bitiş Sinyali (Termination Signal): Producer'ın Consumer'a "bittim"
   demesinin yolu. Genellikle None değeri kullanılır. Consumer bu değeri
   aldığında while döngüsünden break ile çıkar.

2. State Tutma: Consumer'ın işlediği verileri biriktirmesi (toplam hesaplama).
   Bu pattern, RTL verification'da scoreboard'ların çalışma mantığıdır.

3. Sonuç Doğrulama (Assertion): Test sonunda beklenen değerle gerçek değerin
   karşılaştırılması. assert kullanılarak test PASS/FAIL belirlenir.

4. Task Tamamlanma Sırası: Producer biter → None gönderir → Consumer None alır
   → Consumer biter. Bu sıralama bitiş sinyali ile garanti edilir.

BİTİŞ SİNYALİ NEDEN GEREKLİ?
----------------------------
Consumer sonsuz döngüde çalışıyor (while True). Peki ne zaman duracak?

Yanlış yaklaşım - queue.empty() kontrolü:
    while not queue.empty():
        data = await queue.get()
    
Bu ÇALIŞMAZ çünkü:
- Test başında kuyruk boş, Consumer hemen çıkar
- Producer henüz hiçbir şey göndermedi bile!
- Bu bir "race condition" (yarış durumu)

Doğru yaklaşım - bitiş sinyali:
    while True:
        data = await queue.get()
        if data is None:
            break

Bu ÇALIŞIR çünkü:
- Consumer kuyruk boşken bekler (blocking get)
- Producer tüm verileri gönderdikten sonra None gönderir
- Consumer None aldığında güvenle çıkar
- Sıralama garantilidir

BEKLENEN DAVRANIŞ:
------------------
1. Producer 1, 2, 3, ... 10 sayılarını gönderir
2. Producer None gönderir (bitiş sinyali)
3. Consumer sayıları alır ve toplar: 1+2+3+...+10 = 55
4. Consumer None alır ve döngüden çıkar
5. Test toplam değeri kontrol eder: assert total == 55

DENEY ÖNERİLERİ:
----------------
1. Sayı aralığını değiştir (1-100 arası) ve toplam formülünü doğrula
   (n*(n+1)/2 formülü)
2. Consumer'da toplam yerine ortalama hesapla
3. Birden fazla Producer kullan ve sonuçları birleştir

RTL VERIFICATION KARŞILIĞİ:
---------------------------
1. Transaction Counting: Kaç transaction gönderildi, kaç tane alındı?
2. Data Integrity: Gönderilen verilerle alınan veriler tutarlı mı?
3. End-of-Test Detection: Tüm stimulus gönderildi mi, tüm response alındı mı?
4. Scoreboard: Beklenen sonuçları biriktirme ve karşılaştırma

DOSYA BİLGİLERİ:
----------------
Yazar: [Veysel Aras]
Tarih: [28.01.2026]
cocotb versiyonu: 2.0.1
Örnek seviyesi: Başlangıç

================================================================================
"""


import cocotb
from cocotb.triggers import Timer
from cocotb.queue import Queue

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def number_sender(queue, numbers): # Sayı gonderme ve queue'ye ekleme
	for number in numbers:
		await queue.put(number) # blocking sekilde queue'ye ekle
		logger.info(f"[SENDER] Queue'ye {number} eklendi.")
	logger.info("[SENDER] islemi basari ile bitirildi!")

async def number_receiver(queue): # Sayı alma ve toplama
	summ = 0
	while True:
		number = await queue.get() # blocking sekilde queue'den al
		if number == None: # Bitiş sinyali alındıysa döngüden çık
			logger.info("[RECEIVER] Bitis sinyali alindi, islem bitti.")
			break
		summ += number

	logger.info(f"[RECEIVER] islem basari toplam = {summ}!")

# Ana test fonksiyonu
@cocotb.test()
async def blocking_uygulama(_):
	# Burada maxsize=1 yapilirsa senkron sekilde yazma okuma islemi yapilir
	queue = Queue()

	whole_number = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, None] # None bitis sinyali olarak eklenir

	# Gonderici ve alici islemlerini baslat
	cocotb.start_soon(number_sender(queue, whole_number))
	cocotb.start_soon(number_receiver(queue))

	await Timer(100, "ns")

	logger.info("Test Basarili!")
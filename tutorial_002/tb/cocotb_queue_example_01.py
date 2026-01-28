"""
================================================================================
ÖRNEK 1.1: Mesajlaşma Simülasyonu (Blocking Queue Temelleri)
================================================================================

SENARYO AÇIKLAMASI:
-------------------
Bu örnek, cocotb Queue yapısının temel kullanımını öğretir. İki task arasında
mesaj alışverişi yapılır: Sender (gönderici) mesajları kuyruğa koyar, Receiver
(alıcı) bu mesajları kuyruktan okur. Blocking put() ve get() metodları
kullanılarak task'lar arasında otomatik senkronizasyon sağlanır.

KULLANILAN KAVRAMLAR:
---------------------
1. Queue: Task'lar arası iletişim için kullanılan FIFO (First-In-First-Out)
   veri yapısı. Veriler gönderildiği sırayla alınır.

2. await queue.put(): Kuyruğa veri koyar. Kuyruk doluysa (maxsize'a ulaşmışsa)
   yer açılana kadar BEKLER. Bu "blocking" davranıştır.

3. await queue.get(): Kuyruktan veri alır. Kuyruk boşsa veri gelene kadar
   BEKLER. Bu da "blocking" davranıştır.

4. maxsize parametresi: Kuyruğun maksimum kapasitesini belirler.
   - Queue(): Sınırsız kapasite
   - Queue(maxsize=2): En fazla 2 eleman tutabilir

5. cocotb.start_soon(): Task'ı arka planda başlatır ve hemen devam eder.
   Task'ların paralel çalışmasını sağlar.

BLOCKING DAVRANIŞI NEDİR?
-------------------------
Blocking, bir işlemin tamamlanana kadar task'ı DURDURMASINI ifade eder.

Örneğin maxsize=2 olan bir kuyrukta:
- Sender 1. mesajı koyar → Kuyruk: [1]
- Sender 2. mesajı koyar → Kuyruk: [1, 2] (DOLU!)
- Sender 3. mesajı koymaya çalışır → BLOKE OLUR, bekler
- Receiver 1. mesajı alır → Kuyruk: [2], yer açıldı
- Sender devam edebilir → Kuyruk: [2, 3]

Bu mekanizma sayesinde:
- Veriler asla kaybolmaz
- Sıralama korunur (FIFO)
- Task'lar otomatik olarak birbirini bekler

BEKLENEN DAVRANIŞ:
------------------
Sınırsız kuyruk (Queue()) kullanıldığında:
- Sender tüm mesajları hızlıca gönderir
- Receiver tüm mesajları sırayla alır
- Hiç bekleme olmaz

maxsize=2 kullanıldığında:
- Sender 2 mesaj gönderdikten sonra bloke olur
- Receiver bir mesaj alınca Sender devam edebilir
- Sender ve Receiver dönüşümlü çalışır

maxsize=1 kullanıldığında:
- Her mesajdan sonra Sender bloke olur
- Tam senkron çalışma: gönder-al-gönder-al-gönder-al

DENEY ÖNERİLERİ:
----------------
1. maxsize değerini değiştir (1, 2, 5, sınırsız) ve çıktıları karşılaştır
2. Sender'a Timer ekle ve zamanlama etkisini gözlemle
3. Birden fazla Receiver başlat ve davranışı incele

RTL VERIFICATION KARŞILIĞİ:
---------------------------
Bu temel pattern, testbench bileşenleri arasındaki iletişimin temelidir:
- Driver ↔ Sequencer arasında transaction aktarımı
- Monitor → Scoreboard arasında veri iletimi
- Farklı clock domain'leri arasında veri senkronizasyonu

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
from cocotb.queue import Queue, QueueFull, QueueEmpty

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def message_sender(queue, messages): # Mesaj gonderme ve queue'ye ekleme
	for message in messages: 
		await queue.put(message) # blocking sekilde queue'ye ekle
		logger.info(f"[SENDER] Queue'ye {message} eklendi.") 
	logger.info("[SENDER] islemi basari ile bitirildi!")

async def message_getter(queue, array_size): # Mesaj alma ve isleme
	for i in range(array_size):
		temp = await queue.get() # blocking sekilde queue'den al

		logger.info(f"[RECEIVER] queue'den {temp} alindi, 10 ns beklemeye gecti.")

		await Timer(10, "ns")
	logger.info("[RECEIVER] islemi basari ile bitirildi!")

# Ana test fonksiyonu
@cocotb.test()
async def blocking_uygulama(_):
	# Burada maxsize=1 yapilirsa senkron sekilde yazma okuma islemi yapilir
	queue = Queue(maxsize=2)

	whole_message = ["Merhaba", "Nasilsin", "İyi misin", "Görüşürüz", "Bye"]

	# Gonderici ve alici islemlerini baslat
	cocotb.start_soon(message_sender(queue, whole_message))
	cocotb.start_soon(message_getter(queue, len(whole_message)))

	await Timer(100, "ns")

	logger.info("Test Basarili!")
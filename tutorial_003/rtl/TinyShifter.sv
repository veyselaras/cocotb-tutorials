/*
================================================================================
MODÜL: TinyShifter
================================================================================

MODÜL AÇIKLAMASI:
-----------------
TinyShifter, 8-bit veri üzerinde çeşitli kaydırma (shift) ve döndürme 
(rotate) işlemleri gerçekleştiren basit bir kriptografik işlemcidir. Bu modül,
temel bit manipülasyonu işlemlerini öğrenmek ve BFM (Bus Functional Model) 
tabanlı testbench geliştirme pratiği yapmak için tasarlanmıştır.

Modül, TinyALU'ya benzer bir mimariye sahiptir ancak aritmetik işlemler yerine
bit kaydırma/döndürme işlemleri yapar. Bu sayede:
- State machine tasarımı pratiği yapılır
- Handshake protokolü (start/done) öğrenilir  
- BFM yazma becerileri geliştirilir
- Constrained random testing uygulanır

DESTEKLENEN INSTRUCTION SET:
----------------------------
┌────────┬────────┬─────────────────────────────────────────────────────────────┐
│ OpCode │  İsim  │ Açıklama                                                    │
├────────┼────────┼─────────────────────────────────────────────────────────────┤
│  3'b000│  NOP   │ No Operation - Hiçbir işlem yapılmaz, çıkış değişmez        │
│  3'b001│  LOAD  │ shift_amount değerini doğrudan data_out'a yükler            │
│  3'b010│  SHL   │ Shift Left  - Sola kaydırma, sağdan 0 girer, MSB kaybolur   │
│  3'b011│  SHR   │ Shift Right - Sağa kaydırma, soldan 0 girer, LSB kaybolur   │
│  3'b100│  ROL   │ Rotate Left  - Sola döndürme, çıkan MSB sağdan geri girer   │
│  3'b101│  ROR   │ Rotate Right - Sağa döndürme, çıkan LSB soldan geri girer   │
└────────┴────────┴─────────────────────────────────────────────────────────────┘

SHIFT vs ROTATE FARKI:
----------------------
SHIFT işlemlerinde kaydırılan bitler KAYBOLUR, boşluğa 0 girer:
    SHL: 10000000 << 1 = 00000000  (MSB kayboldu)
    SHR: 00000001 >> 1 = 00000000  (LSB kayboldu)

ROTATE işlemlerinde kaydırılan bitler karşı tarafa GERİ DÖNER:
    ROL: 10000000 << 1 = 00000001  (MSB, LSB'ye geldi)
    ROR: 00000001 >> 1 = 10000000  (LSB, MSB'ye geldi)

PORT LİSTESİ:
-------------
Girişler:
    clk              : Sistem clock'u (positive edge triggered)
    rst_n            : Active-low asenkron reset (0 = reset aktif)
    start            : İşlem başlatma sinyali (1 clock pulse yeterli)
    op[2:0]          : Operasyon seçimi (yukarıdaki tabloya göre)
    data_in[7:0]     : İşlenecek 8-bit veri
    shift_amount[7:0]: Kaydırma miktarı (sadece alt 3 bit [2:0] kullanılır)

Çıkışlar:
    done             : İşlem tamamlandı sinyali (1 clock pulse)
    data_out[7:0]    : İşlem sonucu

STATE MACHINE:
--------------
Modül 3 durumlu bir FSM (Finite State Machine) kullanır:

    ┌──────────┐    start=1     ┌─────────────┐   1 cycle   ┌──────────┐
    │  S_IDLE  │ ─────────────> │ S_PROCESSING│ ──────────> │  S_DONE  │
    └──────────┘                └─────────────┘             └──────────┘
         ↑                                                       │
         │                        1 cycle                        │
         └───────────────────────────────────────────────────────┘

    S_IDLE      : Boşta bekler, start sinyalini bekler
                  start=1 gelince girişleri register'lara yakalar
    S_PROCESSING: İşlem hesaplanır (kombinasyonel), 1 cycle bekler
    S_DONE      : done=1 olur, sonuç data_out'a yazılır, S_IDLE'a döner

TIMING DİYAGRAMI:
-----------------
            ___     ___     ___     ___     ___     ___
   clk  ___|   |___|   |___|   |___|   |___|   |___|   |___
           [0]     [1]     [2]     [3]     [4]     [5]
   
   state   IDLE    IDLE    PROC    DONE    IDLE    IDLE
                    ↑              ↑
                    │              └── done=1, sonuç geçerli
                    └── start=1, girişler yakalanır
                 _______
   start ______|       |_________________________________________
   
   data_in ====X  0xA5  X========================================
   
   op      ====X  ROL   X========================================
   
   shift   ====X   4    X========================================
                                   _______
   done  _________________________|       |______________________
   
   data_out ==========================X  0x5A  X=================

   Toplam Latency: 2 clock cycle (start'tan done'a kadar)

RESET DAVRANIŞI:
----------------
rst_n=0 olduğunda (reset aktif):
    - state    <= S_IDLE  (başlangıç durumuna dön)
    - done     <= 0       (done sinyali temizlenir)
    - data_out <= 0x00    (çıkış sıfırlanır)

Reset asenkrondur - clock edge beklenmez, hemen uygulanır.

ÖRNEK İŞLEMLER:
---------------
┌──────────┬─────┬──────────────┬───────────┬────────────────────────────────┐
│ data_in  │ op  │ shift_amount │ data_out  │ Açıklama                       │
├──────────┼─────┼──────────────┼───────────┼────────────────────────────────┤
│ 0x80     │ SHL │      1       │ 0x00      │ 10000000 << 1 = 00000000       │
│ 0x80     │ SHR │      1       │ 0x40      │ 10000000 >> 1 = 01000000       │
│ 0x80     │ ROL │      1       │ 0x01      │ MSB sağa döndü                 │
│ 0x80     │ ROR │      1       │ 0x40      │ LSB=0 olduğu için SHR ile aynı │
│ 0x0F     │ SHL │      4       │ 0xF0      │ Alt nibble üste taşındı        │
│ 0xF0     │ SHR │      4       │ 0x0F      │ Üst nibble alta taşındı        │
│ 0xA5     │ ROL │      4       │ 0x5A      │ Nibble swap (döndürme)         │
│ 0xA5     │ ROR │      4       │ 0x5A      │ Nibble swap (döndürme)         │
│ 0x55     │ LOAD│      0xAB    │ 0xAB      │ shift_amount direkt yüklendi   │
│ 0x55     │ NOP │      3       │ (önceki)  │ Çıkış değişmedi                │
└──────────┴─────┴──────────────┴───────────┴────────────────────────────────┘

BFM İLE TEST AKIŞI:
-------------------
Bu modülü test etmek için TinyAluBfm benzeri bir BFM kullanılır:

    1. reset()      : DUT'u resetle, tüm sinyalleri sıfırla
    2. start_tasks(): Driver ve Monitor coroutine'lerini başlat
    3. send_op()    : Komut gönder (data_in, shift_amount, op)
    4. get_cmd()    : Monitor'dan gönderilen komutu al (doğrulama için)
    5. get_result() : Monitor'dan sonucu al
    6. Karşılaştır  : shifter_prediction() ile beklenen değeri hesapla

    ┌─────────────┐         Queue          ┌─────────────┐
    │  Testbench  │ ───── send_op() ─────> │ cmd_driver  │ ───> DUT
    └─────────────┘                        └─────────────┘
          ↑                                      
          │         ┌─────────────┐              
          └──────── │  cmd_mon    │ <─────────── DUT (start, data_in, op)
          │         └─────────────┘              
          │         ┌─────────────┐              
          └──────── │ result_mon  │ <─────────── DUT (done, data_out)
                    └─────────────┘              

KULLANIM ALANLARI:
------------------
1. Kriptografi    : Basit şifreleme/çözme algoritmaları
2. Veri Paketleme : Bit alanlarını hizalama
3. Çarpma/Bölme   : 2'nin kuvvetleriyle hızlı çarpma (SHL) ve bölme (SHR)
4. CRC Hesaplama  : Rotate işlemleri CRC'de yaygın kullanılır
5. Grafik İşleme  : Piksel manipülasyonu

TASARIM KARARLARI:
------------------
1. shift_amount 8-bit tanımlı ama sadece alt 3 bit kullanılıyor.
   Bunun nedeni: 8-bit veri için maksimum anlamlı shift = 7 bit.
   shift_amount >= 8 için mod 8 alınmış gibi davranır.

2. Latency sabit 2 cycle. Gerçek bir tasarımda işlem karmaşıklığına
   göre değişken latency olabilir (örn: çarpma daha uzun sürer).

3. Combinational hesaplama S_PROCESSING state'inde yapılıyor.
   Alternatif: S_DONE'da da yapılabilirdi, tercih meselesi.

DOSYA BİLGİLERİ:
----------------
Yazar       : Veysel Aras
Tarih       : 30.01.2026
Araçlar     : Icarus Verilog, cocotb 2.0.1, pyuvm
Dil         : SystemVerilog
Test Ortamı : Python + cocotb BFM

================================================================================
*/


module TinyShifter (
	input logic 		clk,
	input logic 		rst_n,
	input logic 		start,
	input logic [2:0] 	instruction,
	input logic [7:0] 	data_in,
	input logic [7:0] 	shift_amount,

	output logic 		done,
	output logic [7:0] 	data_out

);

typedef enum logic[1:0] { 
	S_IDLE,
	S_PROCESSING,
	S_DONE
} states_e;

typedef enum logic[2:0] { 
	NOP,
	LOAD,
	SHL,
	SHR,
	ROL,
	ROR
} instructions_e;

states_e state = S_IDLE;


logic [7:0] data_in_reg;
logic [7:0] shift_amount_reg;
logic [2:0] instruction_reg;

logic [7:0] data_out_reg;

always_ff @(posedge clk or negedge rst_n) begin
	if(rst_n == 1'b0) begin
			done 		<= 1'b0;
			data_out 	<= 8'h00;
			state <= S_IDLE;
	end else begin
		done <= 1'b0;
		case (state)
			S_IDLE: begin
				if(start == 1'b1) begin
					data_in_reg <= data_in;
					shift_amount_reg <= shift_amount;
					state <= S_PROCESSING;
					instruction_reg <= instruction;
				end
				done <= 1'b0;
			end

			S_PROCESSING: begin
				case (instruction_reg)
					NOP:	data_out_reg <= data_in_reg;

					LOAD:	data_out_reg <= shift_amount;

					SHL:	data_out_reg <= data_in_reg << shift_amount_reg;
					
					SHR:	data_out_reg <= data_in_reg >> shift_amount_reg;
					
					ROL:	data_out_reg <= (data_in_reg << shift_amount_reg) | (data_in_reg >> (8 - shift_amount_reg));

					ROR:	data_out_reg <= (data_in_reg >> shift_amount_reg) | (data_in_reg << (8 - shift_amount_reg));

					default: data_out_reg <= data_out_reg;
				endcase
				state <= S_DONE;
			end

			S_DONE: begin
				data_out <= data_out_reg;
				done <= 1'b1;
				state <= S_IDLE;
			end

			default: state <= S_IDLE;
		endcase
	end
end
	
endmodule

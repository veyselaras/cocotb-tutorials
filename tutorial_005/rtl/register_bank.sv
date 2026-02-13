// ============================================================================
// register_bank.sv — 4 Adresli Register Bank RTL Tasarımı
// ============================================================================
//
// Bu modül, dört farklı register türünü barındıran basit bir register bank
// tasarımıdır. Her register türü farklı erişim politikasına sahiptir:
//
//   [0] RW Register     : Okuma-yazma destekli genel amaçlı register.
//   [1] RO Register     : Salt okunur; sabit 0xA5 değerini döndürür,
//                          yazma işlemleri görmezden gelinir.
//   [2] W1C Register    : Write-1-to-Clear; harici olaylar (ext_event) ile
//                          bit'ler set edilir, yazılan 1'ler ilgili bit'leri
//                          temizler.
//   [3] Counter Register: Her saat çevriminde otomatik olarak 1 artan
//                          salt okunur sayaç.
//
// Arayüz: Adres (2-bit), veri (8-bit), okuma/yazma enable sinyalleri ve
// harici olay girişi ile sürülür. Çıkış verisi bir saat çevrimi gecikmeli
// olarak okunur.
//
//
//   Register Bank Dahili Yapısı
//   ============================
//
//                  +------------------------------------------+
//   in_addr[1:0]-->|                                          |
//   in_wdata[7:0]->|    +----------+                          |
//   in_wr_en ----->|--->| Yazma    |    addr=0: rw_reg [7:0]  |
//                  |    | Mantığı  |--->  Doğrudan yazılır    |
//                  |    |          |                          |
//                  |    |          |    addr=1: readOnly_reg  |
//                  |    |          |--->  Yazma yok (0xA5)    |
//                  |    |          |                          |
//   ext_event[7:0]>|-+->|          |    addr=2: w1c_reg [7:0] |
//                  | |  |          |--->  w1c = (w1c|ext)&~wd |
//                  | |  |          |                          |
//                  | |  |          |    addr=3: counter_reg   |
//                  | |  +----------+--->  Yazma yok (auto++)  |
//                  | |                                        |
//                  | |  +----------+                          |
//   in_rd_en ----->|--->| Okuma    |                          |
//                  |    | Mantığı  |    addr'e göre ilgili    |
//                  |    |          |--->  register değeri     |---> out_rdata[7:0]
//                  |    +----------+    out_rdata'ya yazılır  |
//                  |                                          |
//                  |    +----------+                          |
//   clk --------->>|--->| Counter  |    Her posedge clk'da     |
//   rstn --------->|--->|          |--->  counter_reg += 1     |
//                  |    +----------+                          |
//                  +------------------------------------------+
//
// ============================================================================


module register_bank
(
	input logic clk,
	input logic rstn,

	input logic [1:0] 	in_addr,
	input logic [7:0] 	in_wdata,
	input logic 		in_rd_en,
	input logic 		in_wr_en,
	
	input logic [7:0]	ext_event,
	
	output logic [7:0] 	out_rdata
);

	logic [7:0] rw_reg;
	logic [7:0] w1c_reg;
	logic [7:0] counter_reg;

	// Read-only register, her zaman 0xA5 değerini döndürür
	localparam [7:0] readOnly_reg = 8'hA5;


	always_ff @(posedge clk or negedge rstn) begin
		if(rstn == 1'b0) begin
			rw_reg 		<= 8'h00;
			w1c_reg 	<= 8'h00;
		end else begin
			// gelen ext_event sinyalini w1c_reg'e ekle, böylece w1c_reg'deki bitler 1 olabilir
			w1c_reg <= w1c_reg | ext_event;

			if(in_wr_en) begin
				// in_addr'a göre hangi register'a yazılacağını belirle
				case (in_addr)
					// Read-Write register: in_wdata değeri doğrudan rw_reg'e yazılır
					2'b00: begin
						rw_reg <= in_wdata;
					end
					// Read-only register: yazma işlemi yok, bu register sadece okunabilir
					2'b01: begin
						// islem yok read only reg
					end
					// Write-1-to-Clear: wdata'da 1 olan bitler temizlenir
					2'b10: begin
						w1c_reg <= (w1c_reg | ext_event) & ~in_wdata; 
					end

					2'b11: begin
						// islem yok read only reg
					end
				endcase
			end
		end
	end

	// in_rd_en sinyali aktif olduğunda, in_addr'a göre hangi register'ın okunacağını belirle
	always_ff @(posedge clk or negedge rstn) begin
		if(rstn == 1'b0) begin
		 	out_rdata <= 8'h00;
		end else begin
			if(in_rd_en) begin
				case (in_addr)
					2'b00: begin
						out_rdata <= rw_reg;
					end

					2'b01: begin
						out_rdata <= readOnly_reg;
					end

					2'b10: begin
						out_rdata <= w1c_reg;
					end

					2'b11: begin
						out_rdata <= counter_reg;
					end
					
				endcase
			end
		end
	end


	always_ff @(posedge clk or negedge rstn) begin
		if(rstn == 1'b0) 	counter_reg <= 8'h00;
		else				counter_reg <= counter_reg + 1;
	end

endmodule
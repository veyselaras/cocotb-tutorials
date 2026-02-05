//============================================================================
// Proje       : SimpleCounter PyUVM Doğrulama Ortamı
// Dosya       : simpleCounter.sv
// Açıklama    : Taşma/Alt taşma algılamalı 8-bit çift yönlü sayaç
//               
// Özellikler  : - Asenkron aktif-düşük reset ile senkron yükleme
//               - Yukarı/Aşağı sayma modu seçimi
//               - 0xFF'den yukarı sayarken taşma (overflow) bayrağı
//               - 0x00'dan aşağı sayarken alt taşma (underflow) bayrağı
//
// Giriş/Çıkış :
//    Girişler  → clk, rstn, enable, load, load_value[7:0], up_down
//    Çıkışlar  → count[7:0], overflow, underflow
//
// Yazar       : Veysel Aras
// Tarih       : 2026
//============================================================================


module simpleCounter (
	input logic clk,
	input logic rstn,
	input logic enable,
	input logic load,
	input logic [7:0] load_value,
	input logic up_down,

	output logic [7:0] count,
	output logic overflow,
	output logic underflow
);

always_ff @(posedge clk, negedge rstn) begin
	if(rstn == 1'b0) begin
		count 		<= 8'h00;
		overflow 	<= 1'b0;
		underflow 	<= 1'b0;
	end else if (load) begin // yukleme islemi
		count 		<= load_value;
		overflow 	<= 1'b0;
		underflow 	<= 1'b0;
	end else if (enable) begin // sayma islemi
		if(up_down) begin
			if(count == 8'hFF) begin // overflow durumu
				count 		<= 8'h00;
				overflow 	<= 1'b1;
			end else begin
				count 		<= count + 1;
				overflow 	<= 1'b0;
			end
			underflow <= 1'b0;
		end else begin // down counting
			if(count == 8'h00) begin // underflow durumu
				count 		<= 8'hFF;
				underflow 	<= 1'b1;
			end else begin
				count 		<= count - 1;
				underflow 	<= 1'b0;
			end
			overflow <= 1'b0;
		end
	end
end

endmodule
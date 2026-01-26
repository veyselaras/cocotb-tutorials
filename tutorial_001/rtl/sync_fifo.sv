module sync_fifo (
	input 		logic clk,
	input 		logic rstn,
	input 		logic enable_in,
	input 		logic enable_out,
	input logic [7:0] data_in,

	
	output 		logic full,
	output 		logic empty,
	output logic [7:0] data_out

);

	logic [7:0] ram [15:0];

	logic [4:0] read_ptr;
	logic [4:0] write_ptr;

	assign full = (read_ptr[4] != write_ptr[4]) && (read_ptr[3:0] == write_ptr[3:0]);
	assign empty = (read_ptr == write_ptr);

	always_ff @(posedge clk or negedge rstn) begin
		if (rstn == 1'b0) begin
			data_out 	<= 8'h00;

			read_ptr	<= 5'h0;
			write_ptr	<= 5'h0;
		end else begin
			if(enable_in && !full) begin
				write_ptr <= write_ptr + 1;
				ram[write_ptr[3:0]] <= data_in;
			end

			if(enable_out && !empty) begin
				read_ptr <= read_ptr + 1;
				data_out <= ram[read_ptr[3:0]];
			end
		end
	end

endmodule

module cocotb_iverilog_dump();
initial begin
    $dumpfile("sim_build/adder.fst");
    $dumpvars(0, adder);
end
endmodule

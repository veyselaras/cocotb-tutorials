module adder (
    input  [3:0] a,
    input  [3:0] b,
    output [4:0] sum
);
    assign sum = a + b;
    
    initial begin
        $dumpfile("dump.vcd");  // VCD formatı zorla
        $dumpvars(0, adder);
    end
endmodule

module F_Block;

    // Parameters
    parameter MATRIX_SIZE = 4;
    parameter NUM_MATRICES = 20;

    // Memory to hold 20 matrices of 4x4 size with 16-bit integer values
    reg [31:0] block_values [0:NUM_MATRICES-1][0:MATRIX_SIZE-1][0:MATRIX_SIZE-1];

    // Read matrices from a file during initialization
    initial begin
        $readmemb("matrix_F1p.txt", block_values); // Load matrices from file in binary format
    end

    // Additional logic or functionality can be added here

endmodule

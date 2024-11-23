module matrix_reader (
    input [3:0] matrix_index, // Select which matrix to output (0-9)
    output reg [7:0] matrix_out [0:3][0:3] // 4x4 matrix output
);
    // Parameters
    parameter MATRIX_SIZE = 4;
    parameter NUM_MATRICES = 10;
    
    // Memory to hold 10 matrices of 4x4 size
    reg [7:0] matrices [0:NUM_MATRICES-1][0:MATRIX_SIZE-1][0:MATRIX_SIZE-1];

    // Read matrices from a file during initialization
    initial begin
        $readmemh("matrices.txt", matrices); // Load matrices from file
    end
integer i, j;
    // Always block to update matrix_out based on matrix_index
    always @(*) begin
        for (i = 0; i < MATRIX_SIZE; i = i + 1) begin
            for (j = 0; j < MATRIX_SIZE; j = j + 1) begin
                matrix_out[i][j] = matrices[matrix_index][i][j];
            end
        end
    end
endmodule

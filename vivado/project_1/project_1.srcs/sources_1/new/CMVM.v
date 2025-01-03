module CMVM#(parameter MATRIX_SIZE = 4, NUM_MATRICES = 20)
    (
      input  [31:0] v [0:MATRIX_SIZE-1],
      output reg [31:0] z [0:MATRIX_SIZE-1]
    );



    // Memory to hold 20 matrices of 4x4 size with 32-bit integer values
	 // F1p factors 0-9, and F2p from 10-19 of this variables
    reg [31:0] block_factors [0:NUM_MATRICES-1][0:MATRIX_SIZE-1][0:MATRIX_SIZE-1];

    // Read matrices factors from a file during initialization
    initial begin
        $readmemh("/home/jam/Downloads/chisel/vivado/project_1/project_1.srcs/sources_1/new/matrix_F1p.txt", block_factors); // Load matrices from file in binary format
    end


wire  [31:0] v1 [0:MATRIX_SIZE-1];
wire  [31:0] v2 [0:MATRIX_SIZE-1];

reg  [31:0] v1_n [0:MATRIX_SIZE-1];
reg  [31:0] v2_n [0:MATRIX_SIZE-1];

reg [31:0] z1 [0:MATRIX_SIZE-1];
reg [31:0] z2 [0:MATRIX_SIZE-1];


/****************************** slicing and assigning v **************************************************/
assign v1[0] = v[0];
assign v1[1] = v[1];
assign v1[2] = 32'd0;
assign v1[3] = 32'd0;

assign v2[0] = v[2];
assign v2[1] = v[3];
assign v2[2] = 32'd0;
assign v2[3] = 32'd0;


/****************************** inversing v1 and v2 values for F blocks **************************************************/
integer i, j, k, l;
always @(*) begin
    for (j = 0; j < MATRIX_SIZE-1; j = j + 1) begin
        v1_n[j] <= ~ v1[j]; // Perform bitwise NOT on each element
        v2_n[j] <= ~ v2[j]; // Perform bitwise NOT on each element
    end
end


/****************************** shift blocks **************************************************/
always @(*) begin
z1[0] <= ((v1[0] << block_factors[0][0][0]) +    (v1_n[0] << block_factors[0][0][0]));
z2[0] <= ((v2[0] << block_factors[10][0][0]) +   (v2_n[0] << block_factors[10][0][0]));
    for (i = 0; i < ((NUM_MATRICES/2)-1); i = i + 1) begin
        for (k = 0; k < MATRIX_SIZE-1; k = k + 1) begin
            for (l = 1; l < MATRIX_SIZE-1; l = l + 1) begin
                z1[l] <= z1[l-1] + ((v1[l] << block_factors[i][k][l]) +    (v1_n[l] << block_factors[i][k][l]));
                z2[l] <= z2[l-1] + ((v2[l] << block_factors[i+10][k][l]) + (v2_n[l] << block_factors[i+10][k][l]));
            end
        end
    end
end


/****************************** Add blocks **************************************************/
always @(*) begin
    for (integer m = 0; m < MATRIX_SIZE-1; m = m + 1) begin
                z[m] <= z1[m] + z2[m];
    end
end
// assign z = z1 + z2;

endmodule

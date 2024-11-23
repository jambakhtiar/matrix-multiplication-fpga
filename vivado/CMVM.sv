module CMVM#(parameter MATRIX_SIZE = 4, NUM_MATRICES = 20)
    (
      input  [31:0] v [0:MATRIX_SIZE-1],
      output reg [31:0] z [0:MATRIX_SIZE-1]
    );


    // Memory to hold 10 matrices of 4x4 size with 32-bit hex values
    reg [31:0] slice_1_factors [0:NUM_MATRICES-1][0:MATRIX_SIZE-1][0:MATRIX_SIZE-1];
    reg [31:0] slice_2_factors [0:NUM_MATRICES-1][0:MATRIX_SIZE-1][0:MATRIX_SIZE-1];
    
    //
   // reg [31:0] slice_1_factors_2nd_shift [0:NUM_MATRICES-1][0:MATRIX_SIZE-1][0:MATRIX_SIZE-1];
   // reg [31:0] slice_2_factors_2nd_shift [0:NUM_MATRICES-1][0:MATRIX_SIZE-1][0:MATRIX_SIZE-1];

    //reg [31:0] slice_1_factors [0:MATRIX_SIZE-1][0:MATRIX_SIZE-1];
    //reg [31:0] slice_2_factors [0:MATRIX_SIZE-1][0:MATRIX_SIZE-1];

    // Read matrices factors from a file during initialization
    initial begin
        $readmemh("/home/jam/Downloads/chisel/vivado/slice_1_factors.txt", slice_1_factors); // Load matrices from file in binary format
        $readmemh("/home/jam/Downloads/chisel/vivado/slice_2_factors.txt", slice_2_factors); // Load matrices from file in binary format
        
        //$readmemh("/home/jam/Downloads/chisel/vivado/slice_1_factors_second_shift.txt", slice_1_factors_2nd_shift); // Load matrices from file in binary format
        //$readmemh("/home/jam/Downloads/chisel/vivado/slice_2_factors_second_shift.txt", slice_2_factors_2nd_shift); // Load matrices from file in binary format
    end


wire  [31:0] v1 [0:MATRIX_SIZE-1];
wire  [31:0] v2 [0:MATRIX_SIZE-1];

reg   v1_n [0:MATRIX_SIZE-1];
reg   v2_n [0:MATRIX_SIZE-1];

reg [31:0] z1 [0:MATRIX_SIZE-1];
reg [31:0] z2 [0:MATRIX_SIZE-1];


/****************************** slicing v and assigning 0 to v1,v2 slices **************************************************/
assign v1[0] = v[0];
assign v1[1] = v[1];
assign v1[2] = 32'd0;
assign v1[3] = 32'd0;

assign v2[0] = v[2];
assign v2[1] = v[3];
assign v2[2] = 32'd0;
assign v2[3] = 32'd0;


/****************************** checking inversing of v1 and v2 values for F blocks **************************************************/
integer i, j, k, l, m;

always @(*) begin
    for (i = 0; i < 4; i = i + 1) begin
         v1_n[i] = v1[i][31];        // v1_n = 1 indicates negative, else positive 
         v2_n[i] = v2[i][31];        // v2_n = 1 indicates negative, else negative
    end
end

/****************************** shift blocks for z1**************************************************/
always @(*) begin
    z1[0] <= (v1[0] << slice_1_factors[0][0][0]) + (v1[0] << slice_1_factors[0][0][1]) + (v1[0] << slice_1_factors[0][0][2]) + (v1[0] << slice_1_factors[0][0][3]);       
    for (j = 0; j < NUM_MATRICES-1; j = j + 1) begin
        for (k = 1; k < MATRIX_SIZE-1; k = k + 1) begin
            for (l = 1; l < MATRIX_SIZE-1; l = l + 1) begin
                if(v1_n[l]) begin
                    z1[k] <= z1[k-1] - ( (v1[k] << slice_1_factors[j][k][l]));
                end else begin
                    z1[k] <= z1[k-1] + ( (v1[k] << slice_1_factors[j][k][l]));
                end
            end
        end
    end
end

/****************************** shift blocks for z2**************************************************/
always @(*) begin
    z2[0] <= (v2[0] << slice_2_factors[0][0][0]) + (v2[0] << slice_2_factors[0][0][1]) + (v2[0] << slice_2_factors[0][0][2]) + (v2[0] << slice_2_factors[0][0][3]);
    for (j = 0; j < NUM_MATRICES-1; j = j + 1) begin
        for (k = 1; k < MATRIX_SIZE-1; k = k + 1) begin
            for (l = 1; l < MATRIX_SIZE-1; l = l + 1) begin
                if(v2_n[l]) begin
                    z2[k] <= z2[k-1] - ( (v2[k] << slice_2_factors[j][k][l]));// + (v1[k] << slice_1_factors[j][k][l]) + (v1[k] << slice_1_factors[j][k][l]) + (v1[k] << slice_1_factors[j][k][l]) );
                end else begin
                    z2[k] <= z2[k-1] + ( (v2[k] << slice_2_factors[j][k][l]));
                end
            end
        end
    end
end

/****************************** Add blocks **************************************************/
always @(*) begin
    for (m = 0; m < MATRIX_SIZE-1; m = m + 1) begin
                z[m] <= z1[m] + z2[m];
    end
end
// assign z = z1 + z2;

endmodule

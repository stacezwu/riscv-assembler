j        4
# spaddi   0
nop                                            
 addi     [0]   0              
 addi     [1]                   0
 addi     [2]                   0
 addi     [5]                   0
 nop
# rpinc 0
 slli     [4]   32             
 srai     [1]   32             
 addi     [0]   9              
 blt         [1]      [2]   28
 add      [7]     [8]           
 addi     [9]   1              
 addi         [1]                   0
 addi         [3]                   0
 addi        [10]                   0
 j        -36
# spaddi   0
nop                                            
 addi         [8]                   0
 jr          [8]   0  
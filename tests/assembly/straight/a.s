addi [0] 1
addi [0] 2
add [1] [2]
jal ins
add [2] [3]
addi [0] 93
ecall
nop
ins:
add [2] [3]
add [1] [3]
jr [3]
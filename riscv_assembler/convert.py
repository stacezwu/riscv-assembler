from bitstring import BitArray
import math as m
from pathlib import Path
import os

__all__ = ['AssemblyConverter']
class WrongInstructionSize( Exception ):
	#raised when instruction size is not 32 bits
	def __init__(self, message = "Instruction is not 32 bits, possible assembly file error"):
		self.message = message
		super().__init__(self.message)

class NotBinaryNumber( Exception ):
	#raised when instructions contains non-binary elements
	def __init__(self, message = "Instruction is not binary"):
		self.message = message
		super().__init__(self.message)

class IncorrectOutputType( Exception ):
	def __init__(self, message = "Output type is used incorrectly, should be bt, b, or t"):
		self.message = message
		super().__init__(self.message)

class WrongFileType( Exception ):
	def __init__(self, message = "File must have .s extension for assembly code"):
		self.message = message
		super().__init__(self.message)

class EmptyFile( Exception ):
	def __init__(self, message = "File either doesn't exist, has no code, or all is commented out.\nInvestigate any tab/spacing syntax issues"):
		self.message = message
		super().__init__(self.message)

class WrongInstructionType( Exception ):
	def __init__(self, message = "This instruction does not fit this instruction type"):
		self.message = message
		super().__init__(self.message)

class RegisterMap(dict):
   def __init__(self,*arg,**kw):
      super(RegisterMap, self).__init__(*arg, **kw)

   def __getitem__(self, elem):
	   if elem[0] == '[' and elem[-1] == ']':
		   dest_num = int(elem[1:-1])
		   assert dest_num <= 2**23, "source operand distance too large"
		   return dest_num
	   else:
		   return super().get(elem)

#-----------------------------------------------------------------------------------------		
#-----------------------------------------------------------------------------------------
#-----------------------------------------------------------------------------------------

#flatten__ an array
def flatten(x):
	arr = []
	for e in x:
		if not isinstance(e, list):
			arr.append(e)
		else:
			arr.extend(e)
	return arr

def nibbleForm(x):
	fin_str = ""
	for i in range(0,len(x),4):
		fin_str += (x[i:i+4] + "\t")
	return fin_str[:-1]



#-----------------------------------------------------------------------------------------		
#-----------------------------------------------------------------------------------------
#-----------------------------------------------------------------------------------------

class AssemblyConverter:

	r_map = {}
	instr_data = {}
	R_instr = [
		"add","sub", "sll", 
		"sltu", "xor", "srl", 
		"sra", "or", "and",
		"addw", "subw", "sllw",
		"slrw", "sraw", "mul",
		"mulh", "mulu", "mulsu",
		"div", "divu", "rem",
		"remu"
	]
	I_instr = [
		"addi", "lb", "lw",
		"ld", "lbu", "lhu",
		"lwu", "fence", "fence.i", 
		"slli", "slti", "sltiu", 
		"xori", "slri", "srai",
		"ori", "andi", "addiw",
		"slliw", "srliw", "sraiw", 
		"jalr", "ecall", "ebreak", 
		"CSRRW", "CSRRS","CSRRC", 
		"CSRRWI", "CSRRSI", "CSRRCI" 
	]
	S_instr = [
		"sw", "sb", "sh", 
		"sd"
	]
	SB_instr = [
		"beq", "bne", "blt", 
		"bge", "bltu", "bgeu"
	]
	U_instr = ["auipc", "lui"]
	UJ_instr = ["jal"]
	pseudo_instr = [
		"beqz", "bnez", "li", 
		"mv", "j", "jr", 
		"la", "neg", "nop", 
		"not", "ret", "seqz", 
		"snez", "bgt", "ble"
	]

	all_instr = flatten([
		R_instr, I_instr, S_instr,
		SB_instr, U_instr, UJ_instr, 
		pseudo_instr
	])

	def __init__(self, output_type='b', nibble = False, filename = "", hexMode = False):	
		self.code = []
		self.instructions = []
		self.hexMode = hexMode

		if "b" not in output_type and "t" not in output_type and "p" not in output_type and "r" not in output_type:
			raise IncorrectOutputType()
		else:
			self.output_type = output_type

		#antiquated functionality, keep anyway no harm done
		self.filename = filename
		if filename != "":
			self.code = self.__read_in_advance()

		#print(len(self.code))
		self.nibble = nibble
		#get instruction data and register mapping
		self.r_map, self.instr_data = self.__pre()

	def __str__():
		return "AssemblyConverter(output_type={}, nibble={}, filename={}, hexmode={})".format(
			self.output_type, self.nibble,
			self.filename, self.hexMode
		)


	#helper methods
	def __reg_map(self,x):
		return self.r_map[x]

	def __reg_to_bin(self,x):
		if type(x) == str:
			x = int(x[1::])
		return self.__binary(x, 10)

	#for jumps, calculates hex address of func
	def calcJump(self, x,line_num):
		#calc line number of func
		for i in range(len(self.code)):
			if x+":" == self.code[i]:
				return (i - line_num)*4 #how many instructions to jump ahead/behind
		#print("Address not found")
		return -10 #if not found

	def __binary(self, x, size):
		byte_num = m.ceil(size/8)
		b_num = x.to_bytes(byte_num, byteorder = 'big', signed = True)

		fin_bin = ''.join(format(byte, '08b') for byte in b_num)
		
		if byte_num*8 == size:
			return fin_bin
		return fin_bin[len(fin_bin)-size:len(fin_bin)]

	#checks if line is comment, empty space, or .global .text
	def __valid_line(self, x, allow_colon = False):
		if x[0][0] == "#" or x[0][0] == "\n" or x[0][0] == "" or x[0][0] == ".":
			return False

		if not allow_colon and x[0][-1] == ":" :
			return False
		return True

	#gets rid of inline comments
	def __handle_inline_comments(self,x):
		if "#" in x:
			pos = x.index("#")
			if pos != 0 and pos != len(x)-1:
				return x[0:pos]

		return x

	#change output type
	def setOutputType(self, x):
		self.output_type = x

	#return output type
	def getOutputType(self):
		return self.output_type

	#checks whether instruction is in system
	def instructionExists(self,x):
		return x in self.all_instr

	#convert instructions from binary to hex
	def hex(self,x,leading_zero=True):
		if leading_zero:
			num = str(hex(int(x,2)))
			return "0x"+num[2::].zfill(8)
		else:
			return str(hex(int(x,2)))

	#set hexMode to T/F
	def setHex(self, x):
		self.hexMode = x

	#add custom pseudo instruction
	#to be implemented later
	'''
	def addPseudo(instr, op_arr):
		return ""
	'''
	
	#create instruction
	def R_type(
			self, instr, rs1, 
			rs2):
		print("instr: ", instr)
		if instr not in self.R_instr:
			raise WrongInstructionType()

		opcode = 0;f3 = 1;f7 = 2
		print(rs2, rs1)
		print(self.__reg_to_bin(rs2)[0:5],
			self.__reg_to_bin(rs1)[0:5],
			self.instr_data[instr][f7],
			self.__reg_to_bin(rs2)[-5:10],
			self.__reg_to_bin(rs1)[-5:10],
			self.instr_data[instr][f3],
			5*"0", # self.__reg_to_bin("x0"),
			self.instr_data[instr][opcode])

		return "".join([
			self.__reg_to_bin(rs2)[0:5],
			self.__reg_to_bin(rs1)[0:5],
			self.instr_data[instr][f7],
			self.__reg_to_bin(rs2)[-5:10],
			self.__reg_to_bin(rs1)[-5:10],
			self.instr_data[instr][f3],
			5*"0", # self.__reg_to_bin("x0"),
			self.instr_data[instr][opcode]
		])

	def I_type(
			self, instr, rs1, 
			imm):
		print("instr: ", instr)
		if instr not in self.I_instr:
			raise WrongInstructionType()
		opcode = 0;f3 = 1;f7 = 2
		mod_imm = int(imm) - ((int(imm)>>12)<<12) # imm[11:0]
		print(rs1)
		print(			'00000',
			self.__reg_to_bin(rs1)[0:5],
			self.__binary(mod_imm,12),
			self.__reg_to_bin(rs1)[-5:10],
			self.instr_data[instr][f3],
			5*"0", # self.__reg_to_bin("x0"),
			self.instr_data[instr][opcode])
		return "".join([
			#self.__binary(int(imm),12),
			'00000',
			self.__reg_to_bin(rs1)[0:5],
			self.__binary(mod_imm,12),
			self.__reg_to_bin(rs1)[-5:10],
			self.instr_data[instr][f3],
			5*"0", # self.__reg_to_bin("x0"),
			self.instr_data[instr][opcode]
		])

	def S_type(
			self, instr, rs1, 
			rs2, imm):
		print("instr: ", instr)
		if instr not in self.S_instr:
			raise WrongInstructionType()

		opcode = 0;f3 = 1;f7 = 2
		mod_imm = (int(imm) - ((int(imm) >> 12) << 12)) >> 5 # imm[11:5]
		mod_imm_2 = int(imm) - ((int(imm) >> 5) << 5) # imm[4:0]
	

		print(rs2, rs1)
		print(			#self.__binary(int(imm),12)[::-1][5:12][::-1],
			self.__reg_to_bin(rs2)[0:5],
			self.__reg_to_bin(rs1)[0:5],
			self.__binary(mod_imm, 7), # imm[11:5]
			self.__reg_to_bin(rs2)[-5:10],
			self.__reg_to_bin(rs1)[-5:10],
			self.instr_data[instr][f3],
			#self.__binary(int(imm),12)[::-1][0:5][::-1],
			self.__binary(mod_imm_2, 5), # imm[4:0]
			self.instr_data[instr][opcode]
			)
		return "".join([
			#self.__binary(int(imm),12)[::-1][5:12][::-1],
			self.__reg_to_bin(rs2)[0:5],
			self.__reg_to_bin(rs1)[0:5],
			self.__binary(mod_imm, 7), # imm[11:5]
			self.__reg_to_bin(rs2)[-5:10],
			self.__reg_to_bin(rs1)[-5:10],
			self.instr_data[instr][f3],
			#self.__binary(int(imm),12)[::-1][0:5][::-1],
			self.__binary(mod_imm_2, 5), # imm[4:0]
			self.instr_data[instr][opcode]
		])

	def SB_type(
			self, instr, rs1, 
			rs2, imm):
		print("instr: ", instr)
		if instr not in self.SB_instr:
			raise WrongInstructionType()

		opcode = 0;f3 = 1;f7 = 2

		# mod_imm = (int(imm) - ((int(imm) >> 12) << 12)) >> 6 # imm[12]
		# mod_imm += (int(imm) - ((int(imm) >> 11) >> 11)) >> 5 # imm[12|10:5]
		# mod_imm_2 = (int(imm) - ((int(imm) >> 5) << 5)) # imm[4:1]
		# mod_imm_2 += (int(imm) - ((int(imm) >> 11) << 11)) >> 10 # imm[4:1|11]

		mod_imm = (int(imm) >> 11 & 0x1) << 6
		mod_imm += (int(imm) >> 4 & 0x3F) << 0
		mod_imm_2 = (int(imm) >> 0 & 0xF) << 1
		mod_imm_2 += (int(imm) >> 10 & 0x1) << 0

		print(rs2, rs1)
		print(			self.__reg_to_bin(rs2)[0:5],
			self.__reg_to_bin(rs1)[0:5],
			self.__binary(mod_imm,7),
			self.__reg_to_bin(rs2)[-5:10],
			self.__reg_to_bin(rs1)[-5:10],
			self.instr_data[instr][f3],
			self.__binary(mod_imm_2,5),
			#"".join([
			#	self.__binary(int(imm),13)[::-1][1:5][::-1],
			#	self.__binary(int(imm),13)[::-1][11][::-1]
			#]),
			self.instr_data[instr][opcode])

		return "".join([
			#"".join([
			#	self.__binary(int(imm),13)[::-1][12][::-1],
			#	self.__binary(int(imm),13)[::-1][5:11][::-1]
			#]),
			self.__reg_to_bin(rs2)[0:5],
			self.__reg_to_bin(rs1)[0:5],
			self.__binary(mod_imm,7),
			self.__reg_to_bin(rs2)[-5:10],
			self.__reg_to_bin(rs1)[-5:10],
			self.instr_data[instr][f3],
			self.__binary(mod_imm_2,5),
			#"".join([
			#	self.__binary(int(imm),13)[::-1][1:5][::-1],
			#	self.__binary(int(imm),13)[::-1][11][::-1]
			#]),
			self.instr_data[instr][opcode]
		])


	def U_type(
			self, instr, 
			imm):
		print("instr: ", instr)
		if instr not in self.U_instr:
			raise WrongInstructionType()
		opcode = 0;f3 = 1;f7 = 2

		mod_imm = (int(imm))
		print(			'00000',
			'00000',
			#self.__binary(int(imm),32)[::-1][12:32][::-1],
			self.__binary(mod_imm,20),
			5*"0", # self.__reg_to_bin("x0"),
			self.instr_data[instr][opcode])
		return "".join([
			'00000',
			'00000',
			#self.__binary(int(imm),32)[::-1][12:32][::-1],
			self.__binary(mod_imm,20),
			5*"0", # self.__reg_to_bin("x0"),
			self.instr_data[instr][opcode]
		])

	def UJ_type(
			self, instr, 
			imm):
		print("instr: ", instr)
		if instr not in self.UJ_instr:
			raise WrongInstructionType()

		opcode = 0;f3 = 1;f7 = 2
		# mod_imm = ((int(imm) - ((int(imm) >> 20) << 20)) >> 19) << 19 # imm[20]
		# mod_imm += (int(imm) - ((int(imm) >> 10) << 10)) >> 1 # imm[20|10:1]
		# mod_imm += (int(imm) - ((int(imm) >> 11) << 11)) >> 10 # imm[20|10:1|11]
		# mod_imm += (int(imm) - ((int(imm) >> 19) << 19)) >> 12 # imm[20|10:1|11|19:12]

		mod_imm = (int(imm) >> 19 & 0x1) << 19
		mod_imm += (int(imm) >> 0 & 0x3FF) << 9
		mod_imm += (int(imm) >> 10 & 0x1) << 8
		mod_imm += (int(imm) >> 11 & 0xFF) << 0
		print("new mod_imm: ", hex(mod_imm))

		print(			'00000',
			'00000',	
			self.__binary(mod_imm,20),
			5*"0", # self.__reg_to_bin("x0"),
			self.instr_data[instr][opcode])
		# mod_imm = (int(imm) >> 20) << 20
		# mod_imm += ((int(imm) - ((int(imm) >> 11) << 11)) >> 1) << 10
		return  "".join([
			#"".join([
			#	self.__binary(int(imm),21)[::-1][20][::-1], self.__binary(int(imm),21)[::-1][1:11][::-1],
			#	self.__binary(int(imm),21)[::-1][11][::-1],
			#	self.__binary(int(imm),21)[::-1][12:20][::-1]
			#]),	
			'00000',
			'00000',	
			self.__binary(mod_imm,20),
			5*"0", # self.__reg_to_bin("x0"),
			self.instr_data[instr][opcode]
		])


	##Procedural functions

	#initializing mapping and instruction data
	def __pre(self):
		#register mapping
		#make dictionary
		rmap_path = Path(__file__).parent / "data/reg_map.dat"	
		# r_p = {}
		r_p = RegisterMap()
		
		f = open(rmap_path,"r")
		#f = open("riscinterpreter/data/reg_map.dat", "r")
		#f = open("src/data/reg_map.dat","r")
		line = f.readline()

		#assign mapping 
		while line != "":
			elems = line.split(" ")
			r_p[elems[0]] = elems[1] 
			line = f.readline()

		f.close()
		#index for instr_data
		opcode = 0
		f3 = 1
		f7 = 2

		#order is [opcode, f3, f7]
		i_data = {}
		instr_path = Path(__file__).parent / "data/instr_data.dat"
		f = open(instr_path,"r")
		#f = open("riscinterpreter/data/instr_data.dat", "r")
		#f = open("src/data/instr_data.dat","r")
		line = f.readline()

		#assign data
		while line != "":
			elems = line.replace("\n","").split(" ")
			i_data[elems[0]] = elems[1::]
			line = f.readline()
		f.close()

		return r_p,i_data

	#READ FILE IN ADVANCE
	def __read_in_advance(self):
		code = []
		file = open(self.filename, "r")

		#store the lines in the arr
		line = file.readline()
		while line != "":
			line = line.strip()
			clean = flatten([elem.replace("\n","").split(",") for elem in line.split(" ")])
			if line == "" or not self.__valid_line(clean, True):
				line = file.readline()
				continue
			code.append(line.strip())
			line = file.readline()

		return code

	#retrieve instructions
	def __get_instructions(self):
		#array to store instructions in
		instructions = [] 
		for i in range(len(self.code)):
			line = self.code[i]

			response = self.__interpret(line,i)
			if -1 not in response:
				instructions.extend(response)

		return instructions

	#interpret each line and form instructions
	def __interpret(self,line,i):
		res = []
		line = self.__handle_inline_comments(line)
		line = line.strip()
		#print(line)
		clean = flatten([elem.replace("\n","").split(",") for elem in line.split(" ")])

		while "" in clean:
			clean.remove("")

		#check if line is comment, empty space, .global .text
		if not self.__valid_line(clean):
			return [-1]

		# if clean[0] == "ecall":
		# 	return [-1]

		# STACEY: not sure seems not needed
		# if clean[0] == "sw" or clean[0] == "lw" or clean[0] == "lb" or clean[0] == "lh" or clean[0] == "sb" or clean[0] == "sh":
		# 	#sw s0, 0(sp)
		# 	w_spl = clean[2].split("(")
		# 	clean[2] = w_spl[0]
		# 	clean.append(w_spl[1].replace(")",""))

		if clean[0] in self.R_instr:
			res.append(self.R_type(clean[0], self.__reg_map(clean[1]), self.__reg_map(clean[2])))
			# print(res)
		elif clean[0] in self.I_instr:
			if clean[0] == "jalr":
				if len(clean) == 3:
					# res.append(self.I_type(clean[0], self.__reg_map(clean[1]), self.calcJump(clean[2],i)))
					res.append(self.I_type(clean[0], self.__reg_map(clean[1]), int(clean[2])))
				else:
					res.append(self.I_type(clean[0], self.__reg_map(clean[1]), "0"))
			elif clean[0] == "lw":
				res.append(self.I_type(clean[0], self.__reg_map(clean[1]), clean[2]))
			elif clean[0] == "ecall":
				res.append(self.I_type(clean[0], self.__reg_map("x0"),"0"))
			else:
				res.append(self.I_type(clean[0], self.__reg_map(clean[1]), clean[2]))
			# print(res)
		elif clean[0] in self.S_instr:
			res.append(self.S_type(clean[0], self.__reg_map(clean[1]), self.__reg_map(clean[2]), int(clean[3])))
			# print(res)
		elif clean[0] in self.SB_instr:
			# res.append(self.SB_type(clean[0], self.__reg_map(clean[1]), self.__reg_map(clean[2]), self.calcJump(clean[3],i)))
			res.append(self.SB_type(clean[0], self.__reg_map(clean[1]), self.__reg_map(clean[2]), int(clean[3])))
			# print(res)
		elif clean[0] in self.U_instr:
			res.append(self.U_type(clean[0], clean[1]))
			# print(res)
		elif clean[0] in self.UJ_instr:
			if len(clean) == 3:
				# res.append(self.UJ_type(clean[0], self.calcJump(clean[2],i)))
				res.append(self.UJ_type(clean[0], int(clean[2])))
			else:
				res.append(self.UJ_type(clean[0], int(clean[1])))
				# res.append(self.UJ_type(clean[0], self.calcJump(clean[1],i)))
			# print(res)
		elif clean[0] in self.pseudo_instr:
			# print(clean[0]  + " pseudo")

			if clean[0] == "li": #need to consider larger than 12 bits
				#res = self.I_type("addi",self.__reg_map(clean[1]), self.calcJump(clean[2],i), self.__reg_map(clean[1]))
				if int(clean[2]) > 2**11:
					res.append(self.U_type(instr='lui', imm=clean[2]))
				res.append(self.I_type("addi", clean[2]))
			elif clean[0] == "nop":
				res.append(self.I_type("addi", self.__reg_map("x0"), "0"))
			elif clean[0] == "mv":
				res.append(self.I_type("addi", self.__reg_map(clean[1]), "0"))
			elif clean[0] == "not":
				res.append(self.I_type("xori", self.__reg_map(clean[1]), "-1"))
			elif clean[0] == "neg":
				res.append(self.R_type("sub", self.__reg_map("x0"), self.__reg_map(clean[1])))
			elif clean[0] == "la":
				# res.append(self.U_type("auipc", self.calcJump(clean[1],i)))
				res.append(self.U_type("auipc", int(clean[1])))
			elif clean[0] == "j":
				# res.append(self.UJ_type("jal", self.calcJump(clean[1],i)))
				res.append(self.UJ_type("jal", int(clean[1])))
			elif clean[0] == "jr":
				res.append(self.I_type("jalr", self.__reg_map(clean[1]), "0"))
			elif clean[0] == "ret":
				res.append(self.I_type("jalr", self.__reg_map("x1"), "0"))
			elif clean[0] == "bgt":
				# res.append(self.SB_type("blt", self.__reg_map(clean[2]), self.__reg_map(clean[1]), self.calcJump(clean[3],i)))
				res.append(self.SB_type("blt", self.__reg_map(clean[2]), self.__reg_map(clean[1]), int(clean[3])))
			elif clean[0] == "ble":
				# res.append(self.SB_type("bge", self.__reg_map(clean[2]), self.__reg_map(clean[1]), self.calcJump(clean[3], i)))
				res.append(self.SB_type("bge", self.__reg_map(clean[2]), self.__reg_map(clean[1]), int(clean[3])))
			# print(res)
		else:
			#debugging
			print("Error: " + line)

			#check for critical errors
			for r in res:
				for e in r:
					if int(e) != 0 and int(e) != 1:
						raise Not__binaryNumber(r)
				if len(r) != 32:
					raise WrongInstructionSize(len(r))

		#return instruction
		# print("res: ", type(res[0]))
		# print("res, ", res)
		# byte_num = 8
		# prefix = 0x00000000
		# print("prefix: ", prefix)
		# prefix = prefix.to_bytes(byte_num, byteorder = 'big', signed = True)
		
		# prefix = '{0:32b}'.format(prefix)
		# print("str(prefix): ", str(prefix))
		# print("bin(int(prefix)): ", format(prefix,8))
		# res = prefix + str(bin(int(prefix,8)))
		# res[0] = "0000000" + res[0]
		print("res: ", res)
		return res

	#AFTER READING FILE	
	def __post(self):

		if len(self.instructions) == 0:
			raise EmptyFile()
		if "b" in self.output_type:
			print("-----Writing to binary file-----")
			#make it [their .s file name].bin
			fname = self.filename.split("/")[-1]
			print("Output file: " + fname[:-2] + ".bin")

			if not os.path.exists(fname[:-2]):
				os.mkdir(fname[:-2])
				os.mkdir(f"{fname[:-2]}/bin")
			else:
				if not os.path.exists("bin"):
					os.mkdir(f"{fname[:-2]}/bin")

			#with open("output/"+fname[:-2]+"/bin/" + fname[:-2] + ".bin", "wb") as f:
			with open(fname[:-2]+"/bin/" + fname[:-2] + ".bin", "wb") as f:
				for elem in self.instructions:
					#split into bytes
					byte_array = [elem[i:i+8] for i in range(0,len(elem),8)]
					byte_array.reverse()
					print("byte_array: ", byte_array)
					byte_list = [int(b,2) for b in byte_array]

					f.write(bytearray(byte_list))
				f.close()

		if "t" in self.output_type:
			print("------Writing to Text file------")
			#make it [their .s file name].txt

			fname = self.filename.split("/")[-1]
			print("Output file: " + fname[:-2] + ".txt")

			if not os.path.exists(fname[:-2]):
				os.mkdir(fname[:-2])
				os.mkdir(f"{fname[:-2]}/txt")
			else:
				if not os.path.exists("txt"):
					os.mkdir(f"{fname[:-2]}/txt")

			#with open("output/"+fname[:-2]+"text/" + fname[:-2] + ".txt", "w") as f:
			with open(fname[:-2]+"/txt/" + fname[:-2] + ".txt", "w") as f:
				for elem in self.instructions:
					f.write(elem + "\n")

		if "p" in self.output_type:
			print("------Printing Output------")
			for elem in self.instructions:
				print(elem)

		if "r" in self.output_type:
			return self.instructions

		print("Number of instructions: {}".format(len(self.instructions)))

	#DO THE MAGIC
	def convert(self,filename):
		if filename[-2::] != ".s":
			raise WrongFileType()
		self.filename = filename
		self.code = self.__read_in_advance()
		self.instructions = self.__get_instructions()
		print("instructions:", type(self.instructions[0]))

		for i in range(len(self.instructions)):
			self.instructions[i] = "00000000" + self.instructions[i]
			self.instructions[i] = "00000000" + self.instructions[i]
			self.instructions[i] = "000000" + self.instructions[i]
			# self.instructions[i] = "00000000" + self.instructions[i]
			# print("instruction: ", instruction)
			
		print("instructions:", self.instructions[0])
		if self.hexMode:
			for i in range(len(self.instructions)):
				self.instructions[i] = self.hex(self.instructions[i])
		if self.nibble and not self.hexMode:
			for i in range(len(self.instructions)):
				self.instructions[i] = nibbleForm(self.instructions[i])

		return self.__post()

	def convert_ret(self,filename):
		if filename[-2::] != ".s":
			raise WrongFileType()
		self.filename = filename
		#self.r_map, self.instr_data = self.__pre()
		self.code = self.__read_in_advance()
		self.instructions = self.__get_instructions()

		if self.hexMode:
			for i in range(len(self.instructions)):
				self.instructions[i] = self.hex(self.instructions[i])
		if self.nibble and not self.hexMode:
			for i in range(len(self.instructions)):
				self.instructions[i] = nibbleForm(self.instructions[i])
		return self.instructions
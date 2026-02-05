#!/usr/bin/env python3
"""
C64 BASIC to Python Translator
Converted from C64 BASIC program
"""

def main():
	# Declare all BASIC variables as global for dynamic access
	global C, I, J, M_s, P, SI_s, TD, V_s
	global DATA_INDEX, PROGRAM_DATA
	# Initialize state and stacks
	state = "line_10_index_0"
	gosub_stack = []
	for_stack = []

	while True:
		if state == "line_10_index_0":
			V_s = [""] * 10
			P = [0] * 4
			V_s[2] = "BLA"
			P[1] = 2
			if not (V_s[P[1]] == "BLA"):
				state = "line_35_index_0"
				continue
			print("YES")
			state = "line_35_index_0"
			continue

		elif state == "line_35_index_0":
			SI_s = "STRING"
			I = 10
			C = 1007
			M_s = MID_s(SI_s , 2 , 2)
			print(M_s + " IS INSIDE")
			J = float(input())
			if not (I == 10 and J == 20):
				state = "line_70_index_0"
				continue
			print("CORRECT")
			state = "line_70_index_0"
			continue

		elif state == "line_70_index_0":
			if not (C == 1007 or C == 1008):
				state = "line_90_index_0"
				continue
			TD = 3
			state = "line_90_index_0"
			continue

		elif state == "line_90_index_0":
			break  # END statement

		else:
			raise Exception(f"Unknown state: {state}")


if __name__ == '__main__':
	main()
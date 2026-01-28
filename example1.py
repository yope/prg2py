#!/usr/bin/env python3
"""
C64 BASIC to Python Translator
Original program converted from: PROGRAM_NAME
"""

def main():
    # Program state
    state = "init"

    while True:
        if state == "init":
            # Original: 10 REM Welcome Program
            # Original: 20 PRINT "HELLO"
            print("HELLO")
            # Original: 30 A=10
            A = 10
			# Original: 40 B=20
			B = 20
            # Original: 50 IF A=B THEN GOTO 70
            if A == B:
                state = "line_70"
				continue
			# Original: 60 GOTO 80
			state = "line_80"
			continue

        elif state == "line_70":
            # Original: 70 PRINT "A=B"
            print("A=B")
			state = "line_80"
			continue

        elif state == "line_80":
			# Original: 80 PRINT "END"
			print("END")
			# Original: 90 END
			break

        else:
            raise Exception(f"Unknown state: {state}")

if __name__ == "__main__":
    main()

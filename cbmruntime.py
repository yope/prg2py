
def LEN(x):
	return len(x)

def MID_s(x, i, l=None):
	i -= 1
	if i < -1:
		print("Illegal quantity")
		raise SyntaxError
	if l is None:
		return x[i:]
	return x[i:i+l]

def INT(x):
	return int(x)


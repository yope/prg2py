
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

for_dict = {}
for_last_var = ""

def FOR(var, start, end, step, body_state):
	global for_last_var
	for_last_var = var
	for_dict[for_last_var] = (end, step, body_state)
	return start

def NEXT(vars, glob, next_state):
	did_next = False
	if vars is None:
		vars = [for_last_var]
	for var in vars:
		if not var in for_dict:
			continue
		did_next = True
		# Get loop info from dict: (var, end, step, body)
		_le, _ls, _lb = for_dict[var]
		_lc = glob[var]
		_lnv = _lc + _ls
		glob[var] = _lnv
		# Check if loop should continue
		if (_ls >= 0 and _lnv > _le) or (_ls < 0 and _lnv < _le):
			# Loop complete - remove from dics and continue
			del for_dict[var]
		else:
			# Loop continues - update stored current value and jump back
			return _lb
	if not did_next:
		print(f"for_dict = {for_dict!r}, for_last_var = {for_last_var!r}")
		raise Exception("NEXT without FOR")
	return next_state

def cbmprint(*args, **kvargs):
	cbmtext = "".join([str(arg) for arg in args])
	print(cbmtext, **kvargs)

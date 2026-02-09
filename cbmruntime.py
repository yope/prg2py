
import re

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

_rvs = False
_color = None
_screen_bg = "BLACK"
_screen_fg = "LIGHT-BLUE"
_term_fg = "\x1b[38;2;255;255;255m"
_term_bg = "\x1b[48;2;0;0;0m"

#	0x00: "END-LINE", 0x03: "STOP", 0x05: "WHITE", 0x08: "LOCK", 0x09: "UNLOCK",
#	0x0D: "RETURN", 0x0E: "TEXT", 0x10: "BLACK", 0x11: "CRSOR-DOWN",
#	0x12: "RVS-ON", 0x13: "HOME", 0x14: "DEL", 0x1C: "RED",
#	0x1D: "CRSOR-RIGHT", 0x1E: "GREEN", 0x1F: "BLUE",
#	0x80: "END", 0x81: "ORANGE", 0x83: "LOAD&RUN", 0x85: "F1", 0x86: "F3",
#	0x87: "F5", 0x88: "F7", 0x89: "F2", 0x8A: "F4", 0x8B: "F6", 0x8C: "F8",
#	0x8D: "SHIFT-RETURN", 0x8E: "GFX", 0x90: "BLACK", 0x91: "CRSOR-UP",
#	0x92: "RVS-OFF", 0x93: "CLEAR", 0x94: "INSERT", 0x95: "BROWN",
#	0x96: "LIGHT-RED", 0x97: "DARK-GREY", 0x98: "GREY-1", 0x99: "LIGHT-GREEN",
#	0x9A: "LIGHT-BLUE", 0x9B: "LIGHT-GREY", 0x9C: "PURPLE", 0x9D: "CRSOR-LEFT",
#	0x9E: "YELLOW", 0x9F: "CYAN", 0xA0: "SPACE", 0xA1: "SHIFT-SPACE",
_colors = {
	"BLACK": (0, 0, 0),
	"WHITE": (255, 255, 255),
	"RED": (152, 48, 48),
	"CYAN": (160, 224, 224),
	"PURPLE": (168, 120, 176),
	"GREEN": (128, 192, 96),
	"BLUE": (80, 128, 192),
	"YELLOW": (224, 216, 112),
	"ORANGE": (208, 144, 64),
	"BROWN": (112, 88, 56),
	"LIGHT-RED": (240, 80, 80),
	"DARK-GREY": (96, 96, 96),
	"GREY": (120, 120, 120),
	"LIGHT-GREEN": (176, 240, 144),
	"LIGHT-BLUE": (184, 184, 224),
	"LIGHT-GREY": (160, 160, 160),
}

_cursor_codes = {
	"CRSR-UP": "\x1b[1A",
	"CRSR-DOWN": "\x1b[1B",
	"CRSR-RIGHT": "\x1b[1C",
	"CRSR-LEFT": "\x1b[1D",
	"HOME": "\x1b[H",
	"CLEAR": "\x1b[2J\x1b[H"
}

def _mkansi(color):
	r, g, b = _colors[color]
	return f';2;{r};{g};{b}m'

def _screen2ansi():
	global _term_bg
	global _term_fg
	global _screen_fg
	global _screen_bg
	global _rvs
	out = ""
	if _rvs:
		ansibg = f'\x1b[48' + _mkansi(_screen_fg)
		ansifg = f'\x1b[38' + _mkansi(_screen_bg)
	else:
		ansifg = f'\x1b[38' + _mkansi(_screen_fg)
		ansibg = f'\x1b[48' + _mkansi(_screen_bg)
	if _term_fg != ansifg:
		_term_fg = ansifg
		out += ansifg
	if _term_bg != ansibg:
		_term_bg = ansibg
		out += ansibg
	return out

def _cbm_ctrl(code):
	global _term_bg
	global _term_fg
	global _screen_fg
	global _screen_bg
	global _rvs
	out = ""
	if code in _colors:
		_screen_fg = code
		out = _screen2ansi()
	elif code == "RVS-ON":
		if not _rvs:
			_rvs = True
			out = _screen2ansi()
	elif code == "RVS-OFF":
		if _rvs:
			_rvs = False
			out = _screen2ansi()
	elif code in _cursor_codes:
		out = _cursor_codes[code]
	else:
		out = "{" + code + "}"

	return out

def _code_match(m):
	return _cbm_ctrl(m.group(1))

def cbmprint(*args, **kvargs):
	global _rvs
	cbmtext = "".join([str(arg) for arg in args])
	outtext = re.sub(r"\{([a-zA-Z0-9\-\\]+)\}", _code_match, cbmtext)
	if _rvs and "end" not in kvargs:
		#print("Add RVS off")
		outtext += _cbm_ctrl("RVS-OFF") + "\n"
		kvargs["end"] = ""
		cbmtext += "\n"
	#print(cbmtext, **kvargs)
	print(outtext, **kvargs)

if __name__ == "__main__":
	print("_term_bg:", _term_bg.replace('\x1b', 'ESC'))
	print("_term_fg:", _term_fg.replace('\x1b', 'ESC'))
	cbmprint("{BLUE}Blue text{RVS-ON}Reverse")
	cbmprint("{BLUE}Blue text{RVS-ON}Reverse{RVS-OFF}")

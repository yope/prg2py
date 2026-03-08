
import re
import time
import copy
import random
from cbmmemory import SystemBus
from petscii2text import CONTROL_CODES, PETSCII_TO_UTF8_VISUAL

_TAG_TO_PETSCII = {x: y for y, x in CONTROL_CODES.items()}
_UTF8_TO_PETSCII = str.maketrans({x: y for y, x in PETSCII_TO_UTF8_VISUAL.items()})

_sys = SystemBus()

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
	# A C64 FOR loop iteration takes about 1.55ms to execte.
	# Often empty FOR loops are used as delay loops. For these
	# to work, we emulate the original C64 performance with this sleep:
	time.sleep(0.00155)
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

def DIM(dimtype, *sizes):
	ret = dimtype
	for s in sizes:
		ret = [ret]
		nret = []
		for i in range(s):
			nret.extend(copy.deepcopy(ret))
		ret = nret
	return ret

def RND(x):
	# FIXME: Implement real C64 prng, where x<0 numbers return the same
	# result eacht time for the same x, and x==0 uses hrng
	return random.random()

def TAB(x):
	return f"{{TAB={x}}}"

def PEEK(addr):
	return _sys.read(int(addr))

def POKE(addr, data):
	_sys.write(int(addr), int(data))

def ON_GOTO(default, cond, states):
	cond = int(cond)
	if cond < 1:
		return default
	if cond > len(states):
		return default
	return states[cond - 1]

def ON_GOSUB(default, cond, states):
	return ON_GOTO(default, cond, states)

def autodim(glob, *varnames):
	for v in varnames:
		dimtype = "" if '_s' in v else 0
		glob[v] = DIM(dimtype, 11)

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
_color2rgb = _sys.vic2.color2rgb
_color2vic = _sys.vic2.color2vic
_vic2color = _sys.vic2.vic2color

_cursor_codes = {
	"CRSR-UP": "\x1b[1A",
	"CRSR-DOWN": "\x1b[1B",
	"CRSR-RIGHT": "\x1b[1C",
	"CRSR-LEFT": "\x1b[1D",
	"HOME": "\x1b[H",
	"CLEAR": "\x1b[2J\x1b[H"
}

def _mkansi(color):
	r, g, b = _color2rgb[color]
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
	if code in _color2rgb:
		_screen_fg = code
		_sys.write(646, _color2vic[code])
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

def cbmprint_simple(*args, **kvargs):
	global _rvs
	global _screen_fg
	viccolor = _sys.read(646)
	new_fg = _vic2color[viccolor]
	if new_fg != _screen_fg:
		_screen_fg = new_fg
		print(_screen2ansi(), end="")
	cbmtext = "".join([str(arg) for arg in args])
	outtext = re.sub(r"\{([a-zA-Z0-9\-\\]+)\}", _code_match, cbmtext)
	if _rvs and "end" not in kvargs:
		outtext += _cbm_ctrl("RVS-OFF") + "\n"
		kvargs["end"] = ""
		cbmtext += "\n"
	print(outtext, **kvargs)

def cbminput():
	return input().upper()

_ZP_REVERSE = 199
_ZP_COLUMN = 211
_ZP_QUOTE = 212
_ZP_LINE = 214
_ZP_INSERT = 216

def _tag2petscii(m):
	tag = m.group(1)
	try:
		ret = chr(_TAG_TO_PETSCII[tag])
	except KeyError:
		ret = f"{{{tag}}}"
	return ret

def cbmprint_vic(*args, **kvargs):
	def inc_line(line):
		line += 1
		if line >= 25:
			_sys.vic2.disable_output()
			for i in range(1, 25):
				for j in range(40):
					src = i * 40 + j
					dst = src - 40
					POKE(1024 + dst, PEEK(1024 + src))
					POKE(55296 + dst, PEEK(55296 + src))
			for j in range(40):
				POKE(1024 + j + 24*40, 32)
			_sys.vic2.enable_output()
			_sys.vic2.refresh_screen()
			line = 24
		return line

	def inc_col(col, line):
		col += 1
		if col >= 40:
			col = 0
			line = inc_line(line)
		return col, line

	quote = PEEK(_ZP_QUOTE)
	line = PEEK(_ZP_LINE)
	col = PEEK(_ZP_COLUMN)
	rvs = PEEK(_ZP_REVERSE)
	try:
		end = kvargs["end"]
	except KeyError:
		end = "\n"
	cbmtext = "".join([str(arg) for arg in args]) + end
	cbmtext = re.sub(r"\{([a-zA-Z0-9\-\\]+)\}", _tag2petscii, cbmtext).translate(_UTF8_TO_PETSCII)
	i = 0
	while i < len(cbmtext):
		c = cbmtext[i]
		if c == '\r' or c == '\n' and not quote:
			line = inc_line(line)
			col = 0
		elif c == '{':
			endidx = cbmtext.find('}', i + 1)
			if endidx == -1:
				raise ValueError
			tag = cbmtext[i + 1:endidx]
			if '=' in tag:
				tag, arg = tag.split('=')
			else:
				arg = ''
			if tag == "TAB":
				col = max(int(arg), col)
			i = endidx
			if i >= len(cbmtext):
				break
		elif c == '\x05':
			POKE(646, 1)
		elif c == '\x11':
			line = inc_line(line)
		elif c == '\x12':
			rvs = 1
		elif c == '\x13':
			col = line = 0
		elif c == '\x14':
			# backspace
			pass
		elif c == '\x1c':
			POKE(646, 2)
		elif c == '\x1d':
			col, line = inc_col(col, line)
		elif c == '\x1e':
			POKE(646, 5)
		elif c == '\x1f':
			POKE(646, 6)
		elif c == '\x81':
			POKE(646, 8)
		elif c == '\x90':
			POKE(646, 0)
		elif c == '\x91':
			line = max(line - 1, 0)
		elif c == '\x92':
			rvs = 0
		elif c == '\x93':
			col = line = 0
			_sys.vic2.clear_screen(PEEK(646))
		elif c == '\x94':
			# insert
			pass
		elif c == '\x95':
			POKE(646, 9)
		elif c == '\x96':
			POKE(646, 10)
		elif c == '\x97':
			POKE(646, 11)
		elif c == '\x98':
			POKE(646, 12)
		elif c == '\x99':
			POKE(646, 13)
		elif c == '\x9a':
			POKE(646, 14)
		elif c == '\x9b':
			POKE(646, 15)
		elif c == '\x9c':
			POKE(646, 4)
		elif c == '\x9d':
			col -= 1
			if col < 0 and line > 0:
				col = 39
				line = line - 1
			elif line == 0:
				col = 0
		elif c == '\x9e':
			POKE(646, 7)
		elif c == '\x9f':
			POKE(646, 3)
		else:
			code = _sys.vic2.output.petscii2code(ord(c) & 255)
			if rvs:
				code |= 0x80
			color = PEEK(646)
			off = line * 40 + col
			_sys.vic2.disable_output()
			POKE(1024 + off, code)
			_sys.vic2.enable_output()
			POKE(55296 + off, color)
			col, line = inc_col(col, line)
		i += 1
	POKE(_ZP_COLUMN, col)
	POKE(_ZP_LINE, line)
	POKE(_ZP_QUOTE, quote)
	POKE(_ZP_REVERSE, 0) # BASIC print always disabled RVS at the end?

cbmprint = cbmprint_vic

if __name__ == "__main__":
	print("_term_bg:", _term_bg.replace('\x1b', 'ESC'))
	print("_term_fg:", _term_fg.replace('\x1b', 'ESC'))
	cbmprint("{BLUE}Blue text{RVS-ON}Reverse")
	cbmprint("{BLUE}Blue text{RVS-ON}Reverse{RVS-OFF}")

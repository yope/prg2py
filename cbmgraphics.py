
from math import ceil, floor
import random
import sys

class BlockMap:
	palette = {
		0: (0, 0, 0),
		1: (255, 255, 255),
		2: (129, 51, 56),
		3: (119, 206, 200),
		4: (142, 60, 151),
		5: (86, 172, 77),
		6: (46, 44, 155),
		7: (237, 241, 113),
		8: (142, 80, 41),
		9: (85, 56, 0),
		10: (196, 108, 113),
		11: (74, 74, 74),
		12: (123, 123, 123),
		13: (169, 255, 159),
		14: (112, 109, 235),
		15: (178, 178, 178),
	}
	def __init__(self, width: int = 320, height: int = 200):
		self.width = width
		self.height = height
		self.codes = [" "]
		for i in range(20):
			self.codes.append(chr(0x1fb00 + i))
		self.codes.append(chr(0x258c))
		for i in range(20, 39):
			self.codes.append(chr(0x1fb00 + i))
		self.codes.append(chr(0x2590))
		for i in range(39, 60):
			self.codes.append(chr(0x1fb00 + i))
		self.codes.append(chr(0x2588))
		self.xdiv = 2
		self.ydiv = 3
		self.termwidth = ceil(self.width / self.xdiv)
		self.termheight = ceil(self.width / self.ydiv)
		self.pixels = bytearray(self.termwidth * self.termheight * self.xdiv * self.ydiv)
		self.termfg = bytearray(self.termwidth * self.termheight)
		self.termbg = bytearray(self.termwidth * self.termheight)
		self.termmap = bytearray(self.termwidth * self.termheight)
		self._term_x = -1
		self._term_y = -1
		with open('chargen.rom', 'rb') as f:
			self.font = f.read()

	def _colorcode(self, c):
		try:
			r, g, b = self.palette[c]
			return f'2;{r};{g};{b}'
		except KeyError:
			return f'5;{c}'

	def _basic_color(self, fg, bg):
		fgcode = self._colorcode(fg)
		bgcode = self._colorcode(bg)
		print(f'\x1b[38;{fgcode}m\x1b[48;{bgcode}m', end='')

	def term_xy(self, x, y):
		print(f'\x1b[{y+1};{x+1}H', end='')
		#print(f'x={x}, y={y}: ', end='')

	def drawpixel(self, x, y, color):
		self.pixels[x + y * self.width] = color
		cpx = floor(x / 2)
		cpy = floor(y / 3)
		self.refresh_code(cpx, cpy)

	def line(self, x0, y0, x1, y1, color):
		dx = abs(x1 - x0)
		sx = 1 if (x0 < x1) else -1
		dy = -abs(y1 - y0)
		sy = 1 if (y0 < y1) else -1
		err = dx + dy
		while True:
			self.drawpixel(x0, y0, color)
			if (x0 == x1) and (y0 == y1):
				break
			e2 = 2 * err
			if e2 >= dy:
				err += dy
				x0 += sx
			if e2 <= dx:
				err += dx
				y0 += sy

	def top_colors(self, x, y, w, h):
		hist = {}
		for j in range(y, y + h):
			for i in range(x, x + w):
				c = self.pixels[i + j * self.width]
				v = hist.setdefault(c, 0)
				hist[c] = v + 1
		hl = list(hist.items())
		hl.sort(key = lambda x: x[1])
		try:
			return hl[-1][0], hl[-2][0]
		except IndexError:
			return hl[-1][0], 0

	def best_code(self, x, y, fg, bg):
		c = 0
		p = self.pixels
		i = y * self.width
		x1 = x + 1
		if p[i + x] == fg: c |= 1
		if p[i + x1] == fg: c |= 2
		i += self.width
		if p[i + x] == fg: c |= 4
		if p[i + x1] == fg: c |= 8
		i += self.width
		if p[i + x] == fg: c |= 16
		if p[i + x1] == fg: c |= 32
		#print(f"c={c}, x={x}, y={y}")
		return self.codes[c]

	def refresh_code(self, cpx, cpy):
		if cpx != self._term_x or cpy != self._term_y:
			self.term_xy(cpx, cpy)
		x = cpx * self.xdiv
		y = cpy * self.ydiv
		fg, bg = self.top_colors(x, y, 2, 3)
		self._basic_color(bg, fg)
		print(self.best_code(x, y, bg, fg), end='')
		#self.best_code(x, y, bg, fg)
		self._term_x += 1

	def clear(self, c):
		for i in range(self.width * self.height):
			self.pixels[i] = c
		for y in range(self.termheight):
			for x in range(self.termwidth):
				self.refresh_code(x, y)

	def draw_glyph(self, cx, cy, fg, bg, data):
		stride = self.termwidth * self.xdiv
		off = cx * 8 + stride * cy * 8
		for y in range(8):
			for x in range(8):
				self.pixels[off + x] = fg if data[y] & (128 >> x) else bg
			off += stride
		cpx0 = floor((cx * 8) / self.xdiv)
		cpx1 = ceil((cx * 8 + 8) / self.xdiv)
		cpy0 = floor((cy * 8) / self.ydiv)
		cpy1 = ceil((cy * 8 + 8) / self.ydiv)
		for cpy in range(cpy0, cpy1):
			for cpx in range(cpx0, cpx1):
				self.refresh_code(cpx, cpy)

	def draw_code_xy(self, cx, cy, fg, bg, ch):
		self.draw_glyph(cx, cy, fg, bg, self.font[ch*8:ch*8+8])

	def petscii2code(self, c):
		if c < 32:
			return c + 128
		if c < 64:
			return c
		if c < 96:
			return c - 64
		if c < 128:
			return c - 32
		if c < 160:
			return c + 64
		if c < 192:
			return c - 64
		if c == 255:
			return 94
		return c - 128

	def putchar_xy(self, cx, cy, fg, bg, c):
		self.draw_code_xy(cx, cy, fg, bg, self.petscii2code(c))

	def puts_xy(self, cx, cy, fg, bg, s):
		if not isinstance(s, bytes):
			s = s.encode('latin-1')
		for c in s:
			self.putchar_xy(cx, cy, fg, bg, c)
			cx += 1
			if cx > 40:
				cx = 0
				cy += 1

	def test(self):
		for i in range(0, 64, 16):
			for j in range(16):
				print(self.codes[i+j], end="")
			print()

if __name__ == "__main__":
	b = BlockMap()
	b.clear(6)
	b.puts_xy(4, 1, 14, 6, "*** COMMODORE 64 BASIC V2 ***")
	b.puts_xy(1, 3, 14, 6, "64K RAM SYSTEM  38911 BASIC BYTES FREE")
	b.puts_xy(0, 5, 14, 6, "READY.")
	b.puts_xy(0, 6, 6, 14, " ")
	sys.exit(0)
	for i in range(100):
		x1 = random.randint(0, 319)
		y1 = random.randint(0, 191)
		x2 = random.randint(0, 319)
		y2 = random.randint(0, 191)
		c = random.randint(0, 16)
		b.line(x1, y1, x2, y2, c)
	#b.drawpixel(0, 0, 1)
	#b.drawpixel(1, 1, 1)
	#b.drawpixel(0, 2, 1)
	#print("")
	#print(b.pixels[:10])
	#print(b.pixels[320:330])
	#print(b.pixels[640:650])

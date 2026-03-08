
from cbmgraphics import BlockMap

screen2utf8 = {
	0: '@',
	32: ' ',
}

class MemMappedDevice:
	def __init__(self, base: int, size: int):
		self.base = base
		self.size = size
		self.top = base + size - 1
		self.mem = bytearray(size)

	def read(self, addr: int):
		if addr < self.base or addr > self.top:
			return None
		return self.mem[addr - self.base]

	def write(self, addr: int, data: int):
		if addr < self.base or addr > self.top:
			return None
		self.mem[addr - self.base] = data
		return data

class ROM(MemMappedDevice):
	def write(self, addr: int, data: int):
		return None

class VICII(MemMappedDevice):
	color2rgb = {
		"BLACK": (0, 0, 0),
		"WHITE": (255, 255, 255),
		"RED": (129, 51, 56),
		"CYAN": (119, 206, 200),
		"PURPLE": (142, 60, 151),
		"GREEN": (86, 172, 77),
		"BLUE": (46, 44, 155),
		"YELLOW": (237, 241, 113),
		"ORANGE": (142, 80, 41),
		"BROWN": (85, 56, 0),
		"LIGHT-RED": (196, 108, 113),
		"DARK-GREY": (74, 74, 74),
		"GREY": (123, 123, 123),
		"LIGHT-GREEN": (169, 255, 159),
		"LIGHT-BLUE": (112, 109, 235),
		"LIGHT-GREY": (178, 178, 178),
	}
	color2vic = {
		"BLACK": 0,
		"WHITE": 1,
		"RED": 2,
		"CYAN": 3,
		"PURPLE": 4,
		"GREEN": 5,
		"BLUE": 6,
		"YELLOW": 7,
		"ORANGE": 8,
		"BROWN": 9,
		"LIGHT-RED": 10,
		"DARK-GREY": 11,
		"GREY": 12,
		"LIGHT-GREEN": 13,
		"LIGHT-BLUE": 14,
		"LIGHT-GREY": 15
	}
	def __init__(self, base: int, size: int):
		super().__init__(base, size)
		self.vic2color = {vic:color for color, vic in self.color2vic.items()}
		self.vic2rgb = {vic:self.color2rgb[self.vic2color[vic]] for vic in self.vic2color}
		self.output = BlockMap(320, 200)
		self.vm = bytearray(1000)
		self.color = bytearray(1000)
		self.color_base = 0xd800
		self.output_enabled = True

	def disable_output(self):
		self.output_enabled = False
		self.output.disable_output()

	def enable_output(self):
		self.output_enabled = True
		self.output.enable_output()

	def refresh_screen(self):
		self.output.disable_output()
		for off in range(1000):
			self.refresh_code(off)
		self.output.enable_output()
		self.output.refresh_screen()

	def write(self, addr: int, data: int):
		ret = super().write(addr, data)
		if ret is not None:
			return ret
		ptrs = self.mem[0x18]
		vmstart = (ptrs & 0xf0) << 6
		if addr < vmstart:
			return None
		vmend = vmstart + 1000
		if addr > vmend and addr < self.color_base:
			return None
		if addr > (self.color_base + 1000):
			return None
		if addr < self.color_base:
			off = addr - vmstart
			self.vm[off] = data
		else:
			off = addr - self.color_base
			self.color[off] = data & 0x0f # Color RAM is 4-bit wide
		if self.output_enabled:
			self.refresh_code(off)

	def refresh_code(self, off):
		fg = self.color[off]
		code = self.vm[off]
		bg = self.mem[0x21]
		x = off % 40
		y = off // 40
		self.output.draw_code_xy(x, y, fg, bg, code)

	def clear_screen(self, color):
		for i in range(1000):
			self.write(0x0400 + i, 32)
			self.write(0xd800 + i, color)

class SID(MemMappedDevice):
	pass

class CIA(MemMappedDevice):
	pass

class VicTextScreen:
	def __init__(self, base: int, colorbase: int, ram: bytearray, color: MemMappedDevice, vic2: VICII):
		self.vic2 = vic2
		self.ram = ram
		self.cols = 40
		self.rows = 25
		self._border_width = 4
		self._border_height = 4
		self.size = self.cols * self.rows
		self.set_base(base)
		self.set_colorbase(colorbase)
		self._bg_color = 0
		self._fg_color = 0
		self.term_clear()
		self.refresh()

	def term_clear(self):
		print("\x1b[2J\x1b[H", end='')

	def term_home(self):
		print("\x1b[H", end='')

	def term_fg(self, r, g, b):
		print(f'\x1b[38;2;{r};{g};{b}m', end='')

	def term_bg(self, r, g, b):
		print(f'\x1b[48;2;{r};{g};{b}m', end='')

	def set_base(self, base):
		self.base = base
		self.top = base + self.size - 1
		self.mem = memoryview(self.ram)[base:base+self.size]

	def set_colorbase(self, base):
		self.colormem = memoryview(self.ram)[base:base+self.size]

	def redraw_xy(self, x: int, y: int):
		ch = self.mem[y * self.rows + x]
		bg = self.colormem[y * self.rows + x]
		cu = screen2utf8[ch]
		out = ''

	def _in_border(self, x, y):
		if x < self._border_width or x >= (self._border_width + self.cols):
			return True
		if y < self._border_height or y >= (self._border_height + self.rows):
			return True
		return False

	def _draw_border(self):
		self.term_home()
		for y in range(self.rows + 2 * self._border_height):
			for x in range(self.cols + 2 * self._border_width):
				if self._in_border(x, y):
					vc = self.vic2.read(53280)
				else:
					vc = self.vic2.read(53281)
				self.term_bg(*self.vic2.vic2rgb[vc])
				print(' ', end='')
			print('\n', end='')
		self.term_home()

	def refresh(self):
		self.term_home()
		self._draw_border()
		for y in range(self.rows):
			for x in range(self.cols):
				self.redraw_xy(x, y)

class SystemBus:
	def __init__(self):
		self.ram = bytearray(65536)
		self.basic = ROM(0xa000, 0x2000)
		self.kernal = ROM(0xe000, 0x2000)
		self.chargen = ROM(0xd000, 0x1000)
		self.vic2 = VICII(0xd000, 0x400)
		self.sid = SID(0xd400, 0x400)
		self.color = MemMappedDevice(0xd800, 0x400)
		self.cia1 = CIA(0xdc00, 0x100)
		self.cia2 = CIA(0xdd00, 0x100)
		self.pla = {
			0: [],
			1: [self.chargen],
			2: [self.chargen, self.kernal],
			3: [self.chargen, self.kernal, self.basic],
			4: [],
			5: [self.vic2, self.sid, self.cia1, self.cia2, self.color],
			6: [self.vic2, self.sid, self.cia1, self.cia2, self.color, self.kernal],
			7: [self.vic2, self.sid, self.cia1, self.cia2, self.color, self.kernal, self.basic],
		}
		self.ram[1] = 0x07
		self.ram[646] = 0x0e # Cursor color light-blue
		self.write(53280, 14)
		self.write(53281, 6)
		self.write(0xd018, 0x15)
		#self.textscreen = VicTextScreen(0x0400, 0xd800, self.ram, self.color, self.vic2)
		self.vic2.clear_screen(14)

	def write_ram(self, addr: int, data: int):
		self.ram[addr] = data

	def read_ram(self, addr: int):
		return self.ram[addr]

	def write(self, addr: int, data: int):
		for dev in self.pla[self.ram[1] & 7]:
			ret = dev.write(addr, data)
			if ret is not None:
				return
		self.write_ram(addr, data)

	def read(self, addr: int) -> int:
		for dev in self.pla[self.ram[1] & 7]:
			ret = dev.read(addr)
			if ret is not None:
				return ret
		return self.read_ram(addr)

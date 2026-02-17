

class MemMappedDevice:
	def __init__(self, base: int, size: int):
		self.base = base
		self.size = size
		self.top = base + size - 1
		self.mem = bytearray(size)

	def read(self, addr: int):
		if addr < self.base or self.addr > top:
			return None
		return self.mem[addr - base]

	def write(self, addr: int, data: int):
		if addr < self.base or addr > self.top:
			return None
		self.mem[addr - self.base] = data
		return data

class ROM(MemMappedDevice):
	def write(self, addr: int, data: int):
		return None

class VICII(MemMappedDevice):
	pass

class SID(MemMappedDevice):
	pass

class CIA(MemMappedDevice):
	pass

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

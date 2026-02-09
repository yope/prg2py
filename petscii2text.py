#!/usr/bin/env python3
"""
C64 BASIC PRG to UTF-8 Text Converter

Converts Commodore 64 binary BASIC program files (.PRG) to human-readable
UTF-8 encoded BASIC text files.

PRG File Format:
- 2 bytes: Load address (little-endian, typically $0801)
- For each line:
  - 2 bytes: Pointer to next line (memory address, little-endian)
  - 2 bytes: Line number (little-endian)
  - N bytes: Tokenized statement data (NULL-terminated, 0x00)
- End of program: 2 bytes of 0x00 (null pointer)

Phase 1 of the cbmbas2py translator project.
"""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


BASIC_LOAD_ADDRESS = 0x0801


BASIC_TOKENS = {
	0x80: "END",
	0x81: "FOR",
	0x82: "NEXT",
	0x83: "DATA",
	0x84: "INPUT#",
	0x85: "INPUT",
	0x86: "DIM",
	0x87: "READ",
	0x88: "LET",
	0x89: "GOTO",
	0x8A: "RUN",
	0x8B: "IF",
	0x8C: "RESTORE",
	0x8D: "GOSUB",
	0x8E: "RETURN",
	0x8F: "REM",
	0x90: "STOP",
	0x91: "ON",
	0x92: "WAIT",
	0x93: "LOAD",
	0x94: "SAVE",
	0x95: "VERIFY",
	0x96: "DEF",
	0x97: "POKE",
	0x98: "PRINT#",
	0x99: "PRINT",
	0x9A: "CONT",
	0x9B: "LIST",
	0x9C: "CLR",
	0x9D: "CMD",
	0x9E: "SYS",
	0x9F: "OPEN",
	0xA0: "CLOSE",
	0xA1: "GET",
	0xA2: "NEW",
	0xA3: "TAB(",
	0xA4: "TO",
	0xA5: "FN",
	0xA6: "SPC(",
	0xA7: "THEN",
	0xA8: "NOT",
	0xA9: "STEP",
	0xAA: "+",
	0xAB: "-",
	0xAC: "*",
	0xAD: "/",
	0xAE: "^",
	0xAF: "AND",
	0xB0: "OR",
	0xB1: ">",
	0xB2: "=",
	0xB3: "<",
	0xB4: "SGN",
	0xB5: "INT",
	0xB6: "ABS",
	0xB7: "USR",
	0xB8: "FRE",
	0xB9: "POS",
	0xBA: "SQR",
	0xBB: "RND",
	0xBC: "LOG",
	0xBD: "EXP",
	0xBE: "COS",
	0xBF: "SIN",
	0xC0: "TAN",
	0xC1: "ATN",
	0xC2: "PEEK",
	0xC3: "LEN",
	0xC4: "STR$",
	0xC5: "VAL",
	0xC6: "ASC",
	0xC7: "CHR$",
	0xC8: "LEFT$",
	0xC9: "RIGHT$",
	0xCA: "MID$",
	0xCB: "GO",
}


PETSCII_TO_UTF8_VISUAL = {
	0x20: " ", 0x21: "!", 0x22: '"', 0x23: "#", 0x24: "$", 0x25: "%",
	0x26: "&", 0x27: "'", 0x28: "(", 0x29: ")", 0x2A: "*", 0x2B: "+",
	0x2C: ",", 0x2D: "-", 0x2E: ".", 0x2F: "/",
	0x30: "0", 0x31: "1", 0x32: "2", 0x33: "3", 0x34: "4", 0x35: "5",
	0x36: "6", 0x37: "7", 0x38: "8", 0x39: "9", 0x3A: ":", 0x3B: ";",
	0x3C: "<", 0x3D: "=", 0x3E: ">", 0x3F: "?",
	0x40: "@", 0x41: "A", 0x42: "B", 0x43: "C", 0x44: "D", 0x45: "E",
	0x46: "F", 0x47: "G", 0x48: "H", 0x49: "I", 0x4A: "J", 0x4B: "K",
	0x4C: "L", 0x4D: "M", 0x4E: "N", 0x4F: "O", 0x50: "P", 0x51: "Q",
	0x52: "R", 0x53: "S", 0x54: "T", 0x55: "U", 0x56: "V", 0x57: "W",
	0x58: "X", 0x59: "Y", 0x5A: "Z", 0x5B: "[", 0x5C: "£", 0x5D: "]",
	0x5E: "↑", 0x5F: "←",
	0x60: "─", 0x61: "♠", 0x62: "🭲", 0x63: "🭸", 0x64: "🭷", 0x65: "🭶",
	0x66: "🭺", 0x67: "🭱", 0x68: "🭴", 0x69: "╮", 0x6A: "╰", 0x6B: "╯",
	0x6C: "🭼", 0x6D: "╲", 0x6E: "╱", 0x6F: "🭽", 0x70: "🭾", 0x71: "•",
	0x72: "🭻", 0x73: "♥", 0x74: "🭰", 0x75: "╭", 0x76: "╳", 0x77: "○",
	0x78: "♣", 0x79: "🭵", 0x7A: "♦", 0x7B: "┼", 0x7C: "🮌", 0x7D: "│",
	0x7E: "π", 0x7F: "◥",
	0xA0: " ", 0xA1: "▌", 0xA2: "▄", 0xA3: "▔", 0xA4: "▁", 0xA5: "▏",
	0xA6: "▒", 0xA7: "▕", 0xA8: "🮏", 0xA9: "◤", 0xAA: "🮇", 0xAB: "├",
	0xAC: "▗", 0xAD: "└", 0xAE: "┐", 0xAF: "▂",
	0xB0: "┌", 0xB1: "┴", 0xB2: "┬", 0xB3: "┤", 0xB4: "▎", 0xB5: "▍",
	0xB6: "🮈", 0xB7: "🮂", 0xB8: "🮃", 0xB9: "▃", 0xBA: "🭿", 0xBB: "▖",
	0xBC: "▝", 0xBD: "┘", 0xBE: "▘", 0xBF: "▚",
	0xC0: "─", 0xC1: "♠", 0xC2: "🭲", 0xC3: "🭸", 0xC4: "🭷", 0xC5: "🭶",
	0xC6: "🭺", 0xC7: "🭱", 0xC8: "🭴", 0xC9: "╮", 0xCA: "╰", 0xCB: "╯",
	0xCC: "🭼", 0xCD: "╲", 0xCE: "╱", 0xCF: "🭽",
	0xD0: "🭾", 0xD1: "•", 0xD2: "🭻", 0xD3: "♥", 0xD4: "🭰", 0xD5: "╭",
	0xD6: "╳", 0xD7: "○", 0xD8: "♣", 0xD9: "🭵", 0xDA: "♦", 0xDB: "┼",
	0xDC: "🮌", 0xDD: "│", 0xDE: "π", 0xDF: "◥",
}


PETSCII_TO_UTF8_ESCAPED = {
	0x20: " ", 0x21: "!", 0x22: '"', 0x23: "#", 0x24: "$", 0x25: "%",
	0x26: "&", 0x27: "'", 0x28: "(", 0x29: ")", 0x2A: "*", 0x2B: "+",
	0x2C: ",", 0x2D: "-", 0x2E: ".", 0x2F: "/",
	0x30: "0", 0x31: "1", 0x32: "2", 0x33: "3", 0x34: "4", 0x35: "5",
	0x36: "6", 0x37: "7", 0x38: "8", 0x39: "9", 0x3A: ":", 0x3B: ";",
	0x3C: "<", 0x3D: "=", 0x3E: ">", 0x3F: "?",
	0x40: "@", 0x41: "a", 0x42: "b", 0x43: "c", 0x44: "d", 0x45: "e",
	0x46: "f", 0x47: "g", 0x48: "h", 0x49: "i", 0x4A: "j", 0x4B: "k",
	0x4C: "l", 0x4D: "m", 0x4E: "n", 0x4F: "o", 0x50: "p", 0x51: "q",
	0x52: "r", 0x53: "s", 0x54: "t", 0x55: "u", 0x56: "v", 0x57: "w",
	0x58: "x", 0x59: "y", 0x5A: "z", 0x5B: "[", 0x5C: "£", 0x5D: "]",
	0x5E: "↑", 0x5F: "←",
	0x60: "─", 0x61: "A", 0x62: "B", 0x63: "C", 0x64: "D", 0x65: "E",
	0x66: "F", 0x67: "G", 0x68: "H", 0x69: "I", 0x6A: "J", 0x6B: "K",
	0x6C: "L", 0x6D: "M", 0x6E: "N", 0x6F: "O", 0x70: "P", 0x71: "Q",
	0x72: "R", 0x73: "S", 0x74: "T", 0x75: "U", 0x76: "V", 0x77: "W",
	0x78: "X", 0x79: "Y", 0x7A: "Z", 0x7B: "┼", 0x7C: "🮌", 0x7D: "│",
	0x7E: "🞖", 0x7F: "🞘",
}


CONTROL_CODES = {
	0x00: "END-LINE", 0x03: "STOP", 0x05: "WHITE", 0x08: "LOCK", 0x09: "UNLOCK",
	0x0D: "RETURN", 0x0E: "TEXT", 0x10: "BLACK", 0x11: "CRSR-DOWN",
	0x12: "RVS-ON", 0x13: "HOME", 0x14: "DEL", 0x1C: "RED",
	0x1D: "CRSR-RIGHT", 0x1E: "GREEN", 0x1F: "BLUE",
	0x80: "END", 0x81: "ORANGE", 0x83: "LOAD&RUN", 0x85: "F1", 0x86: "F3",
	0x87: "F5", 0x88: "F7", 0x89: "F2", 0x8A: "F4", 0x8B: "F6", 0x8C: "F8",
	0x8D: "SHIFT-RETURN", 0x8E: "GFX", 0x90: "BLACK", 0x91: "CRSR-UP",
	0x92: "RVS-OFF", 0x93: "CLEAR", 0x94: "INSERT", 0x95: "BROWN",
	0x96: "LIGHT-RED", 0x97: "DARK-GREY", 0x98: "GREY", 0x99: "LIGHT-GREEN",
	0x9A: "LIGHT-BLUE", 0x9B: "LIGHT-GREY", 0x9C: "PURPLE", 0x9D: "CRSR-LEFT",
	0x9E: "YELLOW", 0x9F: "CYAN", 0xA0: "SPACE", 0xA1: "SHIFT-SPACE",
}


@dataclass
class BasicLine:
	line_number: int
	tokens: list
	raw_bytes: bytes


class PrgParser:
	"""Parser for Commodore 64 PRG files."""

	def __init__(self, data: bytes):
		self.data = data
		self.pos = 0
		self.load_address = None
		self.lines = []

	def parse(self) -> tuple[int, list[BasicLine]]:
		"""Parse PRG file and return load address and list of BASIC lines."""
		if len(self.data) < 2:
			raise ValueError("PRG file too short (less than 2 bytes for load address)")

		self.load_address = self.data[0] | (self.data[1] << 8)
		self.pos = 2

		if self.load_address != BASIC_LOAD_ADDRESS:
			print(f"Warning: Non-standard load address ${self.load_address:04X} (expected ${BASIC_LOAD_ADDRESS:04X})",
				file=sys.stderr)

		while self.pos < len(self.data):
			line = self._parse_line()
			if line is None:
				break
			self.lines.append(line)

		return self.load_address, self.lines

	def _parse_line(self) -> Optional[BasicLine]:
		"""Parse a single BASIC line using NULL-terminated format."""
		if self.pos + 4 > len(self.data):
			return None

		next_line_ptr = self.data[self.pos] | (self.data[self.pos + 1] << 8)
		if next_line_ptr == 0:
			return None

		self.pos += 2

		if self.pos + 2 > len(self.data):
			return None

		line_number = self.data[self.pos] | (self.data[self.pos + 1] << 8)
		self.pos += 2

		statement_start = self.pos

		while self.pos < len(self.data) and self.data[self.pos] != 0x00:
			self.pos += 1

		if self.pos >= len(self.data):
			raise ValueError(f"Unterminated line starting at position {statement_start}")

		statement_bytes = self.data[statement_start:self.pos]

		self.pos += 1

		return BasicLine(line_number=line_number, tokens=[], raw_bytes=statement_bytes)


class BasicDetokenizer:
	"""Converts tokenized BASIC bytes to human-readable text."""

	def __init__(self, graphics_strategy: str = "visual", pretty: bool = False):
		self.graphics_strategy = graphics_strategy
		self.pretty = pretty
		self._build_reverse_tokens()

	def _build_reverse_tokens(self):
		self._token_to_keyword = {}
		for token, keyword in BASIC_TOKENS.items():
			self._token_to_keyword[token] = keyword

	def detokenize(self, line: BasicLine) -> str:
		"""Convert a BASIC line's tokens to readable text."""
		result = f"{line.line_number} "
		pos = 0
		in_string = False
		in_remark = False
		last_keyword = None

		while pos < len(line.raw_bytes):
			byte = line.raw_bytes[pos]

			if in_remark:
				result += self._petscii_to_utf8(byte)
				pos += 1
				continue

			if in_string:
				if byte == 0x22:
					in_string = False
					result += '"'
				else:
					result += self._petscii_to_utf8(byte)
				pos += 1
				continue

			if byte == 0x22:
				in_string = True
				result += '"'
				pos += 1
				continue

			if byte == 0x3F:
				result += "PRINT"
				last_keyword = "PRINT"
				pos += 1
				continue

			if byte == 0x3A:
				result += ":"
				last_keyword = None
				pos += 1
				continue

			if byte in self._token_to_keyword:
				keyword = self._token_to_keyword[byte]
				if byte == 0x8F:
					in_remark = True

				if self.pretty:
					if keyword in ("TO", "THEN", "STEP"):
						if result and (result[-1].isalnum() or result[-1] in ")=><"):
							result += " "

				result += keyword
				last_keyword = keyword

				if self.pretty:
					if keyword not in ("=", "+", "-", "*", "/", "^", "AND", "OR", ">", "<", "PEEK"):
						if pos + 1 < len(line.raw_bytes):
							next_byte = line.raw_bytes[pos + 1]
							if next_byte not in (0x20, 0x3A, 0x22, 0x28):
								result += " "

				pos += 1
				continue

			if byte < 0x80:
				if last_keyword in ("CHR$", "LEFT$", "RIGHT$", "MID$", "TAB(", "SPC(") or (
					last_keyword is not None and last_keyword.endswith("$")):
					if byte >= 0x30 and byte <= 0x39:
						num_start = pos
						num_value = 0
						while pos < len(line.raw_bytes) and line.raw_bytes[pos] >= 0x30 and line.raw_bytes[pos] <= 0x39:
							num_value = num_value * 10 + (line.raw_bytes[pos] - 0x30)
							pos += 1
						result += str(num_value)
						last_keyword = None
						continue
				result += self._petscii_to_utf8(byte)
				last_keyword = None
				pos += 1
				continue

			pos += 1

		return result.rstrip()

	def _petscii_to_utf8(self, byte: int) -> str:
		"""Convert a single PETSCII byte to UTF-8 string."""
		if self.graphics_strategy == "visual":
			if byte in PETSCII_TO_UTF8_VISUAL:
				return PETSCII_TO_UTF8_VISUAL[byte]
		else:
			if byte in PETSCII_TO_UTF8_ESCAPED:
				return PETSCII_TO_UTF8_ESCAPED[byte]
			if byte < 0x20 or byte > 0xDF:
				return f"\\x{byte:02X}"

		if byte in CONTROL_CODES:
			return f"{{{CONTROL_CODES[byte]}}}"

		return f"\\x{byte:02X}"


def convert_prg_to_text(input_path: Path, output_path: Path,
						include_line_numbers: bool = True,
						graphics_strategy: str = "visual",
						pretty: bool = False,
						verbose: bool = False) -> bool:
	"""Convert a PRG file to UTF-8 BASIC text."""
	try:
		with open(input_path, "rb") as f:
			data = f.read()
	except FileNotFoundError:
		print(f"Error: Input file not found: {input_path}", file=sys.stderr)
		return False
	except IOError as e:
		print(f"Error reading input file: {e}", file=sys.stderr)
		return False

	try:
		parser = PrgParser(data)
		load_address, lines = parser.parse()
	except ValueError as e:
		print(f"Error parsing PRG file: {e}", file=sys.stderr)
		return False

	if verbose:
		print(f"Loaded from address: ${load_address:04X}")
		print(f"Number of lines: {len(lines)}")

	detokenizer = BasicDetokenizer(graphics_strategy=graphics_strategy, pretty=pretty)

	try:
		with open(output_path, "w", encoding="utf-8") as f:
			f.write(f"0 REM C64 BASIC PROGRAM\n")
			f.write(f"0 REM Converted from: {input_path.name}\n")
			f.write(f"0 REM Load address: ${load_address:04X}\n")
			f.write(f"0 REM Strategy: {graphics_strategy}\n")
			f.write(f"0 REM Pretty: {pretty}\n")
			f.write(f"0 \n")

			for line in lines:
				detokenized = detokenizer.detokenize(line)
				if include_line_numbers:
					f.write(detokenized + "\n")
				else:
					content = detokenized.split(" ", 1)[1] if " " in detokenized else ""
					f.write(content + "\n")
	except IOError as e:
		print(f"Error writing output file: {e}", file=sys.stderr)
		return False

	if verbose:
		print(f"Successfully converted {len(lines)} lines")
		print(f"Output written to: {output_path}")

	return True


def main():
	parser = argparse.ArgumentParser(
		description="Convert Commodore 64 BASIC PRG files to UTF-8 text format."
	)
	parser.add_argument("input", type=Path, help="Input PRG file")
	parser.add_argument("output", type=Path, nargs="?", help="Output text file (default: <input>.bas)")
	parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
	parser.add_argument("-l", "--no-line-numbers", action="store_true",
						help="Exclude line numbers from output")
	parser.add_argument("-g", "--graphics", choices=["visual", "escaped"], default="visual",
						help="Graphics character strategy (default: visual)")
	parser.add_argument("-p", "--pretty", action="store_true",
						help="Add spaces between tokens and arguments for readability")

	args = parser.parse_args()

	if not args.input.exists():
		print(f"Error: Input file does not exist: {args.input}", file=sys.stderr)
		sys.exit(1)

	if args.output is None:
		args.output = args.input.with_suffix(".bas")

	success = convert_prg_to_text(
		args.input,
		args.output,
		include_line_numbers=not args.no_line_numbers,
		graphics_strategy=args.graphics,
		pretty=args.pretty,
		verbose=args.verbose
	)

	sys.exit(0 if success else 1)


if __name__ == "__main__":
	main()

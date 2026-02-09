#!/usr/bin/env python3
"""
CBM BASIC to Python Translator
Converts C64 BASIC programs to executable Python code using fall-through state machine architecture.

This is Phase 2 of the cbmbas2py translator project. Phase 1 (petscii2text.py) converts PRG
files to UTF-8 text. Phase 2 converts the text to Python.
"""

import argparse
import sys
import re
from typing import List, Tuple, Dict, Optional
from pathlib import Path


class BASICParser:
	"""Parse C64 BASIC files and extract line-by-line structure."""

	def __init__(self):
		"""Initialize parser with empty structures."""
		self.coordinate_system: List[Tuple[int, List[dict]]] = []  # [(line, [statements]), ...]
		self.index_mapping: Dict[Tuple[int, int], dict] = {}  # [(line, index) -> {statement, type}]
		self.line_numbers: List[int] = []

	def parse_file(self, filepath: str) -> List[Tuple[int, List[str]]]:
		"""Parse a UTF-8 encoded BASIC file.

		Args:
			filepath: Path to the BASIC file

		Returns:
			List of (line_number, [statements]) tuples
		"""
		try:
			with open(filepath, 'r', encoding='utf-8') as f:
				content = f.read()

			if not content.strip():
				raise ValueError("Empty file")

			lines = content.split('\n')
			parsed_lines = []

			for file_line_num, line_content in enumerate(lines, 1):
				line_content = line_content.strip()
				if not line_content:
					continue

				# Parse BASIC line number (integer at start)
				basic_line_num = self._parse_basic_line_number(line_content)
				# Use _parse_line with BASIC line number, not file line number
				self._parse_line(basic_line_num, line_content)

			return self.coordinate_system

		except FileNotFoundError:
			raise FileNotFoundError(f"File not found: {filepath}")
		except UnicodeDecodeError:
			raise UnicodeDecodeError("File is not valid UTF-8 encoded")

	def _parse_basic_line_number(self, line_content: str) -> int:
		"""Parse BASIC line number from line content.

		Args:
			line_content: Content with basic line number prefix

		Returns:
			BASIC line number as integer
		"""
		line_content = line_content.strip()
		# Find first space or tab to separate line number from content
		for i, char in enumerate(line_content):
			if char in ' \t':
				return int(line_content[:i].strip())
		return int(line_content.strip())

	def _parse_line(self, basic_line_num: int, line_content: str):
		"""Parse a single BASIC line, splitting on colons outside of strings.

		Args:
			basic_line_num: BASIC line number
			line_content: Content of the line (already stripped)
		"""
		# First, strip line number prefix BEFORE splitting
		base_content = self._strip_line_number(line_content)

		# Now split by colons, but don't split inside quoted strings
		parts = self._split_colons(base_content)

		statements = []
		prev_was_if = False
		print(f"{basic_line_num} has parts {parts!r}")
		for part in parts:
			if not part:
				part = "PASS"

			statement_content = part.strip()
			if statement_content:
				# Check for IF short GOTO (number after IF/THEN)
				if prev_was_if and statement_content.isnumeric():
					statement_content = f'GOTO {statement_content}'
					prev_was_if = False

				statement_info = self._tokenize_statement(statement_content)
				if statement_info['type'] != 'UNKNOWN':
					# Set prev_was_if only if this is an IF statement
					if statement_info['type'] == 'IF':
						prev_was_if = True
					else:
						prev_was_if = False
					statements.append(statement_info)

		if statements:
			self.coordinate_system.append((basic_line_num, statements))
			self.line_numbers.append(basic_line_num)
			self._update_index_mapping(basic_line_num, len(statements))

	def _split_colons(self, text: str) -> list:
		"""Split text by colons, respecting quoted string boundaries.

		Args:
			text: Text potentially containing colons within strings

		Returns:
			List of substrings split at colons outside strings
		"""
		parts = []
		current = ""
		in_double_quote = False
		in_simple_quote = False

		for char in text:
			if char == '"' and not in_simple_quote:
				in_double_quote = not in_double_quote
				current += char
			elif char == "'" and not in_double_quote:
				in_simple_quote = not in_simple_quote
				current += char
			elif char == ':' and not in_double_quote and not in_simple_quote:
				parts.append(current)
				current = ""
			else:
				current += char

			if current.startswith('IF') and current.endswith('THEN') and not in_double_quote and not in_simple_quote:
				parts.append(current)
				current = ""

		if current:
			parts.append(current)

		return parts

	def _strip_line_number(self, line_content: str) -> str:
		"""Strip line number prefix if present.

		Args:
			line_content: Content possibly with line number prefix

		Returns:
			Content without line number, or original if no line number found
		"""
		if line_content:
			# Find first space or tab to separate line number from content
			for i, char in enumerate(line_content):
				if char in ' \t':
					return line_content[i+1:].strip()
		return line_content

	def _tokenize_statement(self, statement: str) -> dict:
		"""Tokenize a statement and identify type.

		Args:
			statement: Statement content

		Returns:
			Dictionary with statement details
		"""
		statement = statement.strip()

		stmt_type = None
		content = None

		# List of statement keywords in order of priority
		keywords = ['REM', 'INPUT', 'PRINT', 'FOR', 'NEXT', 'GOTO', 'GOSUB',
					'RETURN', 'IF', 'DATA', 'DIM', 'END', 'READ', 'PASS']

		# Check each keyword
		for keyword in keywords:
			if statement.startswith(keyword):
				stmt_type = keyword
				# Extract content after keyword
				remainder = statement[len(keyword):].lstrip()
				content = f'{keyword} {remainder}' if remainder else keyword
				break

		# Check for implicit LET or unknown statement
		if stmt_type is None:
			if '=' in statement:
				stmt_type = 'LET'
			else:
				stmt_type = 'UNKNOWN'
			content = statement

		return {
			'type': stmt_type,
			'content': content,
			'raw': statement
		}

	def _update_index_mapping(self, line_num: int, num_statements: int):
		"""Update index mapping for statements in a line.

		Args:
			line_num: Line number
			num_statements: Number of statements in a line
		"""
		for idx in range(num_statements):
			self.index_mapping[(line_num, idx)] = {
				'line': line_num,
				'index': idx,
				'content': self.coordinate_system[-1][1][idx]['content'],
				'type': self.coordinate_system[-1][1][idx]['type']
			}

	def get_coordinates(self) -> List[Tuple[int, List[dict]]]:
		"""Get the coordinate system.

		Returns:
			List of (line, [statements]) tuples
		"""
		return self.coordinate_system

	def get_index_map(self) -> Dict[Tuple[int, int], dict]:
		"""Get the statement index mapping.

		Returns:
			Dictionary mapping (line, index) to statement info
		"""
		return self.index_mapping

	def get_line_numbers(self) -> List[int]:
		"""Get sorted list of line numbers.

		Returns:
			Sorted list of line numbers
		"""
		return sorted(self.line_numbers)


class StateMachineAnalyzer:
	"""Analyze BASIC control flow and build state machine structure."""

	def __init__(self, parser: BASICParser):
		"""Initialize analyzer with parser.

		Args:
			parser: BASICParser instance with parsed data
		"""
		self.parser = parser
		self.coordinate_system = parser.get_coordinates()
		self.index_mapping = parser.get_index_map()
		self.line_numbers = parser.get_line_numbers()

		self.jump_targets: Dict[Tuple[int, int], List[Tuple[int, int]]] = {}
		self.coordinates_are_targets: Dict[Tuple[int, int], bool] = {}
		self.fallthrough_chains: Dict[Tuple[int, int], List[Tuple[int, int]]] = {}
		self.return_stack: List[Tuple[int, int]] = []
		self.gosub_stack: List[Tuple[int, int]] = []

	def _get_next_coordinates(self, current_coord: Tuple[int, int]) -> Optional[Tuple[int, int]]:
		"""Find the next statement coordinates after the current coordinate.

		Args:
			current_coord: (line_number, statement_index) of current position

		Returns:
			(next_line, next_index) of the statement that follows, or None if no more statements
		"""
		line_num, current_idx = current_coord
		next_idx = current_idx + 1

		# Check if coordinates exist in our parsed data
		if (line_num, next_idx) in self.index_mapping:
			return (line_num, next_idx)

		# Get the next line from line_numbers list
		try:
			next_line = self.line_numbers[self.line_numbers.index(line_num) + 1]
		except IndexError:
			return (line_num + 1, 0)
		return (next_line, 0)

	def analyze_control_flow(self) -> Dict[str, object]:
		"""Analyze the entire control flow graph and generate state mapping.

		Returns:
			Dictionary containing analysis results
		"""
		self.state_mapping = self.get_state_mapping()

		# Initialize: ALL coordinates are non-targets
		for line_num, statements in self.coordinate_system:
			for idx in range(len(statements)):
				coord = (line_num, idx)
				self.coordinates_are_targets[coord] = False

		# Get jump targets for all statements
		self._get_jump_targets()

		# Analyze fall-through chains
		self._analyze_fallthrough()

		return {
			'state_mapping': self.state_mapping,
			'jump_targets': self.jump_targets,
			'are_targets': self.coordinates_are_targets,
			'fallthrough': self.fallthrough_chains
		}

	def _get_jump_targets(self):
		"""Identify jump targets for all statements."""
		for line_num, statements in self.coordinate_system:
			for idx, stmt_info in enumerate(statements):
				coord = (line_num, idx)
				stmt_type = stmt_info['type']
				stmt_content = stmt_info['content']

				if stmt_type == 'GOTO':
					target_line, target_idx = self._parse_goto_target(stmt_content)
					self.coordinates_are_targets[(target_line, 0)] = True
					self.jump_targets[coord] = [(target_line, 0)]

				elif stmt_type == 'GOSUB':
					target_line, target_idx = self._parse_goto_target(stmt_content)

					# Target 1: The GOSUB destination
					self.coordinates_are_targets[(target_line, 0)] = True
					self.jump_targets[coord] = [(target_line, 0)]

					# Target 2: The statement following this GOSUB
					# This is where control will return to after GOSUB completes
					next_coord = self._get_next_coordinates((line_num, idx))
					if next_coord is not None:
						self.coordinates_are_targets[next_coord] = True
						self.jump_targets[coord].append(next_coord)

				elif stmt_type == 'IF':
					self._handle_if_statement(coord)

				elif stmt_type == 'FOR':
					self._handle_for_statement(coord)

				elif stmt_type == 'NEXT':
					self._handle_next_statement(coord)

	def _parse_goto_target(self, goto_content: str) -> Tuple[int, int]:
		"""Parse GOTO or GOSUB target and get statement index.

		Args:
			goto_content: GOTO or GOSUB statement content

		Returns:
			Tuple of (line_number, statement_index)
		"""
		match = re.search(r'(GOTO|GOSUB)\s*(\d+)', goto_content)
		if match:
			target_line = int(match.group(2))
			return target_line, 0
		return -1, -1

	def _mark_target(self, source_coord: Tuple[int, int], target_coord: Tuple[int, int]):
		"""Mark a coordinate as a target.

		Args:
			source_coord: (line, index) of statement jumping to target
			target_coord: (line, index) of target coordinate
		"""
		coord_key = (source_coord[0], source_coord[1])
		if coord_key in self.jump_targets:
			self.jump_targets[coord_key].append(target_coord)
		else:
			self.jump_targets[coord_key] = [target_coord]

		self.coordinates_are_targets[target_coord] = True

	def _record_gosub(self, gosub_coord: Tuple[int, int], target_coord: Tuple[int, int]):
		"""Record GOSUB coordinate and push to stack.

		Args:
			gosub_coord: (line, index) of GOSUB statement
			target_coord: (line, index) of destination
		"""
		self.gosub_stack.append(gosub_coord)
		self.return_stack.append(target_coord)

	def _get_return_target(self) -> Tuple[int, int]:
		"""Get return target from stack.

		Returns:
			Tuple of (line_number, statement_index)

		Raises:
			ValueError: If no return targets available
		"""
		if not self.return_stack:
			raise ValueError("RETURN statement without matching GOSUB")

		return self.return_stack[-1]

	def _handle_next_statement(self, next_coord: Tuple[int, int]):
		"""Handle NEXT statement - mark fallthrough to next statement.

		Args:
			next_coord: (line, index) of NEXT statement
		"""
		line_num, idx = next_coord
		next_idx = idx + 1

		coord_key = (line_num, idx)

		next_coord_key = (line_num, next_idx)
		if next_coord_key in self.coordinates_are_targets:
			self.coordinates_are_targets[next_coord_key] = True

		# NEXT statement falls through to next index in same line
		if next_coord_key in self.coordinates_are_targets or self._coord_exists(next_coord_key):
			self.jump_targets[coord_key] = [next_coord_key]

	def _coord_exists(self, coord: Tuple[int, int]) -> bool:
		"""Check if a coordinate exists in the coordinate system.

		Args:
			coord: (line, index) to check

		Returns:
			True if coordinate exists, False otherwise
		"""
		for line_num, statements in self.coordinate_system:
			if line_num == coord[0] and len(statements) > coord[1]:
				return True
		return False

	def _handle_if_statement(self, if_coord: Tuple[int, int]):
		"""Handle IF statement - creates one potential branch.

		Args:
			if_coord: (line, index) of IF statement
		"""
		line_num, idx = if_coord
		coord_key = (line_num, idx)

		# Mark next line's first index as potential target (false branch destination)
		# The IF statement falls through to next index in same line (true branch)
		# No fallthrough needed, just mark the false branch destination
		index = self.line_numbers.index(line_num)
		try:
			next_line = self.line_numbers[index + 1]
			false_coord_key = (next_line, 0)
			self.coordinates_are_targets[false_coord_key] = True
		except IndexError:
			# No next line - IF statement is last line, no false branch to execute
			pass

	def _handle_for_statement(self, for_coord: Tuple[int, int]):
		"""Handle FOR statement - mark statement following it as potential target.

		Args:
			for_coord: (line, index) of FOR statement
		"""

		# Mark statement after FOR as potential target for NEXT branches
		next_coord = self._get_next_coordinates(for_coord)
		self.coordinates_are_targets[next_coord] = True

		# The FOR statement continues to next statement (same line, next index)
		self.jump_targets[for_coord] = [next_coord]

	def _handle_next_statement(self, this_coord: Tuple[int, int]):
		"""Handle NEXT statement - mark statement following it as potential target.

		Args:
			this_coord: (line, index) of NEXT statement
		"""
		# Mark statement after FOR as potential target for NEXT branches
		next_coord = self._get_next_coordinates(this_coord)
		self.coordinates_are_targets[next_coord] = True

		# The FOR statement continues to next statement (same line, next index)
		self.jump_targets[this_coord] = [next_coord]

	def get_state_mapping(self) -> Dict[str, dict]:
		"""Generate unique state names for all coordinates.

		Returns:
			Dictionary mapping state name -> coordinate info
		"""
		state_mapping = {}
		states_used = {}

		for line_num, statements in self.coordinate_system:
			for idx in range(len(statements)):
				coord = (line_num, idx)

				if coord in states_used:
					continue

				base_name = f"line_{line_num}_index_{idx}"
				counter = 1
				state_name = base_name

				while state_name in states_used:
					state_name = f"{base_name}_{counter}"
					counter += 1

				state_mapping[state_name] = {
					'coordinate': coord,
					'line': line_num,
					'index': idx,
					'statement': self.index_mapping.get(coord, {}).get('content', '')
				}

				states_used[state_name] = True

		return state_mapping

	def _analyze_fallthrough(self):
		"""Build fall-through chains for sequential execution."""
		prev_coord = None

		for line_num, statements in self.coordinate_system:
			for idx, stmt_info in enumerate(statements):
				current_coord = (line_num, idx)

				# If this coordinate is not a GOSUB (not on stack), it's a fallthrough continuation
				on_gosub_stack = any(gosub[0] == current_coord[0] and gosub[1] == current_coord[1] for gosub in self.gosub_stack)

				if not on_gosub_stack:
					if prev_coord is not None:
						if current_coord not in self.jump_targets.get(prev_coord, []):
							chain = self.fallthrough_chains.get(prev_coord, [])
							chain.append(current_coord)
							self.fallthrough_chains[prev_coord] = chain

						# If current coord is also a potential target, add to its own chain
						if current_coord in self.coordinates_are_targets:
							self.fallthrough_chains[current_coord] = []

					prev_coord = current_coord


class PythonCodeGenerator:
	"""Generate Python code from analyzed BASIC program."""

	def __init__(self, analyzer: StateMachineAnalyzer, verbose: bool = False):
		"""Initialize generator with analyzer.

		Args:
			analyzer: StateMachineAnalyzer with analyzed control flow
			verbose: Whether to output verbose information
		"""
		self.analyzer = analyzer
		self.parser = analyzer.parser
		self.verbose = verbose
		self.output_lines: List[str] = []
		self.data_constants: List[str] = []
		self.variables: set = set()  # Track all BASIC variables used

	def generate(self, include_header: bool = True, pretty: bool = False) -> str:
		"""Generate complete Python source code.

		Args:
			include_header: Whether to include shebang and docstring
			pretty: Whether to add extra formatting for readability

		Returns:
			Complete Python source code as string
		"""
		self.output_lines = []

		if include_header:
			self._generate_header()

		self._generate_data_constants()
		self._generate_main_function(pretty)

		return '\n'.join(self.output_lines)

	def _generate_header(self):
		"""Generate file header with shebang and docstring."""
		self.output_lines.append('#!/usr/bin/env python3')
		self.output_lines.append('"""')
		self.output_lines.append('C64 BASIC to Python Translator')
		self.output_lines.append('Converted from C64 BASIC program')
		self.output_lines.append('"""')
		self.output_lines.append('')
		self.output_lines.append('from cbmruntime import *')
		self.output_lines.append('')

	def _generate_data_constants(self):
		"""Generate DATA constants if any DATA statements exist."""
		data_values = []
		for line_num, statements in self.parser.get_coordinates():
			for stmt in statements:
				if stmt['type'] == 'DATA':
					values = self._parse_data_values(stmt['content'])
					data_values.extend(values)

		if data_values:
			self.output_lines.append('# DATA constants')
			self.output_lines.append(f'PROGRAM_DATA = {data_values}')
			self.output_lines.append('DATA_INDEX = 0')
			self.output_lines.append('')

	def _parse_data_values(self, data_content: str) -> List:
		"""Parse DATA statement values.

		Args:
			data_content: DATA statement content

		Returns:
			List of parsed values
		"""
		values = []
		match = re.search(r'DATA\s*(.+)', data_content)
		if match:
			data_part = match.group(1)
			# Split by comma, respecting quotes
			parts = self._split_data_values(data_part)
			for part in parts:
				part = part.strip()
				if part.startswith('"') and part.endswith('"'):
					values.append(part)
				else:
					try:
						if '.' in part:
							values.append(float(part))
						else:
							values.append(int(part))
					except ValueError:
						values.append(part)
		return values

	def _split_data_values(self, data_text: str) -> List[str]:
		"""Split DATA values by comma, respecting quoted strings.

		Args:
			data_text: Text after DATA keyword

		Returns:
			List of individual data values
		"""
		parts = []
		current = ""
		in_quote = False

		for char in data_text:
			if char == '"':
				in_quote = not in_quote
				current += char
			elif char == ',' and not in_quote:
				parts.append(current)
				current = ""
			else:
				current += char

		if current:
			parts.append(current)

		return parts

	def _collect_variables(self):
		"""Collect all variables used in the program.

		Iterate through all statements and collect variable names that need
		to be declared as global in the main function.
		"""
		for line_num, statements in self.parser.get_coordinates():
			for idx, stmt_info in enumerate(statements):
				stmt_type = stmt_info['type']
				content = stmt_info['content']
				coord = (line_num, idx)

				if stmt_type == 'LET':
					# Parse LET to get the variable name
					clean_content = re.sub(r'^LET\s*', '', content.strip())
					if '=' in clean_content:
						var = clean_content.split('=', 1)[0].strip()
						py_var = self._convert_variable(var, True)
						self.variables.add(py_var)

				elif stmt_type == 'INPUT':
					# Parse INPUT to get variable names (handle prompt strings)
					match = re.search(r'INPUT\s*(.+)', content)
					if match:
						input_part = match.group(1).strip()
						# Remove any quoted prompt strings
						# INPUT can have: "prompt" var or "prompt"; var or just var
						# Remove quoted strings from the input part
						clean_input = re.sub(r'"[^"]*"[;,]?\s*', '', input_part)
						# Now split by comma to get variables
						vars = [v.strip() for v in clean_input.split(',') if v.strip()]
						for var in vars:
							py_var = self._convert_variable(var, True)
							self.variables.add(py_var)

				elif stmt_type == 'FOR':
					# Parse FOR to get loop variable
					match = re.search(r'FOR\s*(\w+)\s*=', content)
					if match:
						var = match.group(1)
						py_var = self._convert_variable(var, True)
						self.variables.add(py_var)

				elif stmt_type == 'READ':
					# Parse READ to get variable names
					match = re.search(r'READ\s*(.+)', content)
					if match:
						var_list = match.group(1).strip()
						#vars = [v.strip() for v in var_list.split(',')]
						vars = []
						curr = ""
						pasens = False
						for c in var_list:
							if c == '(':
								parens = True
							elif c == ')':
								parens = False
							if c == ',' and not parens:
								vars.append(curr)
								curr = ""
							else:
								curr += c
						vars.append(curr)
						for var in vars:
							py_var = self._convert_variable(var, True)
							self.variables.add(py_var)

	def _get_next_coordinates(self, current_coord: Tuple[int, int]) -> Optional[Tuple[int, int]]:
		"""Find the next statement coordinates after the current coordinate.

		Args:
			current_coord: (line_number, statement_index) of current position

		Returns:
			(next_line, next_index) of the statement that follows, or None if no more statements
		"""
		line_num, current_idx = current_coord
		next_idx = current_idx + 1

		# Check if coordinates exist in our parsed data
		if (line_num, next_idx) in self.analyzer.index_mapping:
			return (line_num, next_idx)

		# Get the next line from line_numbers list
		try:
			next_line = self.analyzer.line_numbers[self.analyzer.line_numbers.index(line_num) + 1]
		except IndexError:
			return (line_num + 1, 0)
		return (next_line, 0)

	def _generate_main_function(self, pretty: bool = False):
		"""Generate the main() function with state machine.

		Args:
			pretty: Whether to add extra formatting for readability
		"""
		# First, collect all variables used in the program
		self._collect_variables()

		self.output_lines.append('def main():')
		# Generate global declaration for all collected variables
		if self.variables:
			variables = list(self.variables)
			self.output_lines.append(f'	# Declare all BASIC variables as global for dynamic access')
			for i in range(0, len(variables), 20):
				var_chunk = variables[i:i+20]
				var_list = ', '.join(var_chunk)
				self.output_lines.append(f'	global {var_list}')
				for var in var_chunk:
					if var.endswith('_s'):
						self.output_lines.append(f'	{var} = ""')
					elif not var.endswith('_l'):
						self.output_lines.append(f'	{var} = 0')

		self.output_lines.append('	global DATA_INDEX, PROGRAM_DATA')
		self.output_lines.append('	# Initialize state and stacks')
		self.output_lines.append('	state = "line_{}_index_0"'.format(
			self.parser.get_line_numbers()[0] if self.parser.get_line_numbers() else 0
		))
		self.output_lines.append('	prev_state = ""')
		self.output_lines.append('	gosub_stack = []')
		self.output_lines.append('')
		self.output_lines.append('	while True:')
		self.output_lines.append('		prev_state = state')

		# Get state mapping and target information
		state_mapping = self.analyzer.state_mapping
		are_targets = self.analyzer.coordinates_are_targets
		fallthrough = self.analyzer.fallthrough_chains
		jump_targets = self.analyzer.jump_targets

		# Group coordinates into handler blocks
		# Each block starts with either the first line or a target coordinate
		handler_blocks = self._build_handler_blocks(state_mapping, are_targets)

		# Generate state handlers in program order
		first_state = True
		for block_start_coord, block_coords in handler_blocks:
			block_state_name = self._coord_to_state_name(block_start_coord, state_mapping)

			if first_state:
				self.output_lines.append(f'		if state == "{block_state_name}":')
				first_state = False
			else:
				if pretty:
					self.output_lines.append('')
				self.output_lines.append(f'		elif state == "{block_state_name}":')

			# Generate all statements in this block (fall-through chain)
			last_coord = None
			last_has_control_flow = False
			for coord in block_coords:
				stmt_info = self.parser.index_mapping.get(coord, {})
				if stmt_info:
					python_code = self._convert_statement(stmt_info, coord, jump_targets)
				for line in python_code:
					self.output_lines.append(f'			{line}')
				# Check if this statement has control flow (continue/break/return)
				if self._has_control_flow(stmt_info['type'], python_code, stmt_info, coord):
					last_has_control_flow = True
				else:
					last_has_control_flow = False
				last_coord = coord

			# Handle state transition from the last statement in the block
			# Only add if the last statement doesn't already have control flow
			if last_coord and not last_has_control_flow:
				next_coord = self._get_next_execution_point(last_coord, jump_targets, fallthrough)
				if next_coord:
					next_state = self._coord_to_state_name(next_coord, state_mapping)
					self.output_lines.append(f'			state = "{next_state}"')
					self.output_lines.append(f'			continue')
				else:
					# End of program
					self.output_lines.append(f'			break')

		# Add else clause for unknown states
		if pretty:
			self.output_lines.append('')
		self.output_lines.append(f'		else:')
		self.output_lines.append(f'			raise Exception(f"Unknown state: {{state}} previous: {{prev_state}}")')
		self.output_lines.append('')
		self.output_lines.append('')
		self.output_lines.append("if __name__ == '__main__':")
		self.output_lines.append(f'	main()')

	def _build_handler_blocks(self, state_mapping: Dict, are_targets: Dict) -> List[Tuple[Tuple[int, int], List[Tuple[int, int]]]]:
		"""Build handler blocks grouping fall-through statements.

		Args:
			state_mapping: Dictionary mapping state names to info
			are_targets: Dictionary indicating if coordinate is a target

		Returns:
			List of (block_start_coord, [coordinates_in_block]) tuples
		"""
		blocks = []
		current_block = []
		block_start = None

		# Process coordinates in program order
		for line_num, statements in self.parser.get_coordinates():
			for idx in range(len(statements)):
				coord = (line_num, idx)
				is_target = are_targets.get(coord, False)

				if is_target or not current_block:
					# Start a new block
					if current_block:
						blocks.append((block_start, current_block))
					block_start = coord
					current_block = [coord]
				else:
					# Add to current fall-through block
					current_block.append(coord)

		# Don't forget the last block
		if current_block:
			blocks.append((block_start, current_block))

		return blocks

	def _has_control_flow(self, stmt_type: str, python_code: List[str],
						   stmt_info: dict = None, coord: Tuple[int, int] = None) -> bool:
		"""Check if generated Python code has control flow statements.

		Args:
			stmt_type: Type of BASIC statement
			python_code: Generated Python code lines
			stmt_info: Optional statement info for context
			coord: Optional coordinate for checking next statement

		Returns:
			True if code contains continue/break/return that ends execution
		"""
		# Statement types that always have control flow
		if stmt_type in ['GOTO', 'GOSUB', 'RETURN', 'END', 'NEXT']:
			return True

		# IF statements with GOTO targets have control flow
		if stmt_type == 'IF' and coord:
			line_num, idx = coord
			next_coord = (line_num, idx + 1)
			next_stmt = self.parser.index_mapping.get(next_coord, {})
			if next_stmt and next_stmt['type'] == 'GOTO':
				return True
			# Also check for inline THEN <number>
			if stmt_info:
				content = stmt_info.get('content', '')
				if re.search(r'THEN\s*\d+', content):
					return True

		# Check for continue or break in generated code
		for line in python_code:
			stripped = line.strip()
			if stripped.startswith('continue') or stripped.startswith('break'):
				return True
			if stripped == 'return' or stripped.startswith('return '):
				return True

		return False

	def _convert_statement(self, stmt_info: dict, coord: Tuple[int, int],
						   jump_targets: Dict) -> List[str]:
		"""Convert a BASIC statement to Python code lines.

		Args:
			stmt_info: Statement information dictionary
			coord: (line, index) coordinate of statement
			jump_targets: Dictionary of jump targets

		Returns:
			List of Python code lines
		"""
		stmt_type = stmt_info['type']
		content = stmt_info['content']
		line_num, idx = coord

		if stmt_type == 'REM':
			rem_text = content[3:].strip() if len(content) > 3 else ''
			return [f'# {rem_text}']

		elif stmt_type == 'PRINT':
			return self._convert_print(content)

		elif stmt_type == 'LET':
			return self._convert_let(content)

		elif stmt_type == 'INPUT':
			return self._convert_input(content)

		elif stmt_type == 'IF':
			return self._convert_if(content, coord, jump_targets)

		elif stmt_type == 'GOTO':
			return self._convert_goto(content, coord)

		elif stmt_type == 'GOSUB':
			return self._convert_gosub(content, coord, jump_targets)

		elif stmt_type == 'RETURN':
			return self._convert_return()

		elif stmt_type == 'FOR':
			return self._convert_for(content, coord)

		elif stmt_type == 'NEXT':
			return self._convert_next(content, coord)

		elif stmt_type == 'DATA':
			return ['pass  # DATA statement']

		elif stmt_type == 'READ':
			return self._convert_read(content)

		elif stmt_type == 'DIM':
			return self._convert_dim(content)

		elif stmt_type == 'PASS':
			return ['# :']

		elif stmt_type == 'END':
			return ['break  # END statement']

		else:
			return [f'# Unknown statement: {content}']

	def _convert_print(self, content: str) -> List[str]:
		"""Convert PRINT statement to Python print()."""
		match = re.search(r'PRINT\s*(.*)', content)
		if not match:
			return ['cbmprint()']

		args = match.group(1).strip()
		if not args:
			return ['cbmprint()']

		parts, semicolon_end = self._parse_print_args(args)

		if not parts:
			return ['cbmprint()' if not semicolon_end else 'cbmprint(end="")']

		joined = ', '.join(parts)
		if semicolon_end:
			return [f'cbmprint({joined}, end="")']
		else:
			return [f'cbmprint({joined})']

	def _parse_print_args(self, args: str) -> Tuple[List[str], bool]:
		"""Parse PRINT arguments and return parts and whether it ends with semicolon.

		In BASIC:
		- Comma (,) separates items with a TAB
		- Semicolon (;) concatenates items with no space
		- Space or implicit concatenation: items adjacent without separator
		- Semicolon at end suppresses newline

		Returns:
			Tuple of (list of print arguments, has_trailing_semicolon)
		"""
		if not args.strip():
			return [], False

		parts = []
		current_item = ""
		in_quote = False
		has_trailing_semicolon = False

		i = 0
		while i < len(args):
			char = args[i]
			if char == '"':
				in_quote = not in_quote
				current_item += char
			elif char == ',' and not in_quote:
				# Comma separates items with TAB - finish current concatenation group
				if current_item.strip():
					parts.append(self._convert_expression(current_item.strip()))
				parts.append('"\\t"')
				current_item = ""
				has_trailing_semicolon = False
			elif char == ';' and not in_quote:
				# Semicolon means concatenate with next item (no space)
				if current_item.strip():
					parts.append(self._convert_expression(current_item.strip()))
				# Mark that we need to concatenate with the next item
				has_trailing_semicolon = True
				current_item = ""
			elif char.isspace() and not in_quote:
				# Space outside quotes separates items for concatenation
				if current_item.strip():
					parts.append(self._convert_expression(current_item.strip()))
					current_item = ""
				# Reset semicolon flag since we're starting a new item
				has_trailing_semicolon = False
			else:
				current_item += char
				if not char.isspace():
					has_trailing_semicolon = False
			i += 1

		# Handle remaining item
		if current_item.strip():
			parts.append(self._convert_expression(current_item.strip()))
		elif has_trailing_semicolon and not parts:
			# Edge case: only a semicolon
			has_trailing_semicolon = True

		# Concatenate adjacent string items
		parts = self._concat_print_items(parts)

		return parts, has_trailing_semicolon

	def _concat_print_items(self, parts: List[str]) -> List[str]:
		"""Concatenate PRINT items that should be joined with '+' operator.

		In BASIC PRINT statements, items can be implicitly concatenated:
		- PRINT "A" "B" -> print("A" + "B")
		- PRINT "A" ; "B" -> print("A" + "B")
		- PRINT "A" , "B" -> print("A", "\t", "B")
		- PRINT M$"B" -> print(M_s + "B")  (no space between items)

		This method joins adjacent string items with '+' operator.
		"""
		if len(parts) < 1:
			return parts

		# String-returning functions in BASIC
		string_functions = {'TAB', 'SPC', 'MID$', 'LEFT$', 'RIGHT$', 'CHR$', 'STR$'}

		def is_string_item(part: str) -> bool:
			"""Check if a part is a string (literal, variable, or function)."""
			part = part.strip()
			if part.startswith('"') and part.endswith('"'):
				return True
			if part.endswith('_s'):
				return True
			# Check for function calls
			for func in string_functions:
				if part.startswith(func + '('):
					return True
			return False

		# First, handle items that contain multiple string expressions
		# e.g., M_s " IS INSIDE" should become [M_s, " IS INSIDE"]
		expanded_parts = []
		for part in parts:
			expanded = self._expand_implicit_concat_in_item(part)
			expanded_parts.extend(expanded)
		parts = expanded_parts

		if len(parts) < 2:
			return parts

		result = []
		concat_group = []

		for part in parts:
			if part == '"\\t"':
				# Tab separator - finish any concatenation group first
				if concat_group:
					result.append(self._join_concat_group(concat_group))
					concat_group = []
				result.append(part)
			elif is_string_item(part):
				# String item - add to concatenation group
				concat_group.append(part)
			else:
				# Non-string item - finish concatenation group first
				if concat_group:
					result.append(self._join_concat_group(concat_group))
					concat_group = []
				result.append(part)

		# Don't forget the last group
		if concat_group:
			result.append(self._join_concat_group(concat_group))

		return result

	def _expand_implicit_concat_in_item(self, item: str) -> List[str]:
		"""Expand an item that may contain implicit string concatenation.

		In BASIC PRINT statements, items can be adjacent without spaces:
		- M$" IS INSIDE" contains M$ and " IS INSIDE"
		- "BLO"TAB(16) contains "BLO" and TAB(16)

		This method splits such items into separate parts.
		"""
		if not item or not item.strip():
			return [item]

		# String-returning functions in BASIC
		string_functions = {'TAB', 'SPC', 'MID', 'MID$', 'LEFT', 'LEFT$', 'RIGHT', 'RIGHT$',
							'CHR', 'CHR$', 'STR', 'STR$'}

		parts = []
		current = ""
		in_quote = False
		i = 0

		while i < len(item):
			char = item[i]

			if char == '"':
				# String literal boundary
				if in_quote:
					# End of string literal
					current += char
					if current.strip():
						parts.append(current)
					current = ""
					in_quote = False
				else:
					# Start of string literal - check if we had something before
					if current.strip():
						parts.append(current)
						current = ""
					current += char
					in_quote = True
			elif in_quote:
				current += char
			elif char.isalpha():
				# Start of identifier or function name
				j = i
				while j < len(item) and (item[j].isalnum() or item[j] in '$%'):
					j += 1
				ident = item[i:j]

				# Check if this is a string function
				upper_ident = ident.upper()
				if upper_ident in string_functions or upper_ident.rstrip('$') in string_functions:
					# Check if followed by '('
					if j < len(item) and item[j] == '(':
						# Find matching ')'
						paren_depth = 1
						k = j + 1
						while k < len(item) and paren_depth > 0:
							if item[k] == '(':
								paren_depth += 1
							elif item[k] == ')':
								paren_depth -= 1
							k += 1
						# Extract full function call
						func_call = item[i:k]
						if current.strip():
							parts.append(current)
							current = ""
						parts.append(func_call)
						i = k
						continue

				# Regular identifier (variable)
				current += ident
				i = j
				continue
			else:
				current += char

			i += 1

		# Handle remaining
		if current.strip():
			parts.append(current)

		# Filter out empty parts and whitespace-only
		parts = [p.strip() for p in parts if p.strip()]

		return parts if parts else [item]

	def _join_concat_group(self, items: List[str]) -> str:
		"""Join a group of items with '+' for concatenation."""
		if len(items) == 1:
			return items[0]
		return ' + '.join(items)

	def _convert_let(self, content: str) -> List[str]:
		"""Convert LET statement to Python assignment."""
		content = re.sub(r'^LET\s*', '', content.strip())

		if '=' in content:
			parts = content.split('=', 1)
			var = parts[0].strip()
			value = parts[1].strip()
			py_var = self._convert_variable(var)
			py_value = self._convert_expression(value)
			# Track the variable being assigned
			self.variables.add(py_var)
			return [f'{py_var} = {py_value}']

		return [f'# Invalid LET: {content}']

	def _convert_input(self, content: str) -> List[str]:
		"""Convert INPUT statement to Python input()."""
		match = re.search(r'INPUT\s*(.+)', content)
		if not match:
			return ['# Invalid INPUT statement']

		var_list = match.group(1).strip()

		if var_list.startswith('"'):
			prompt = var_list[1:]
			prompt = prompt[:prompt.index('"')]
			# cut string after len(prompt) + 2x quote + ";"
			var_list = var_list[len(prompt) + 3:]
		else:
			prompt = ""

		vars = [v.strip() for v in var_list.split(',')]

		lines = [f'cbmprint("{prompt}", end="? ")']
		for var in vars:
			py_var = self._convert_variable(var)
			# Track the input variable
			self.variables.add(py_var)
			if var.endswith('$'):
				lines.append(f'{py_var} = input()')
			else:
				lines.append(f'{py_var} = float(input())')

		return lines

	def _convert_if(self, content: str, coord: Tuple[int, int],
					jump_targets: Dict) -> List[str]:
		"""Convert IF statement to Python if with state transition."""
		match = re.search(r'IF\s*(.+?)\s*THEN', content)
		if not match:
			return [f'# Invalid IF: {content}']

		condition = match.group(1).strip()
		py_condition = self._convert_condition(condition)
		lines = []

		line_num, idx = coord
		next_coord = (line_num, idx + 1)
		next_stmt = self.parser.index_mapping.get(next_coord, {})

		# Get the next line number for false branch
		line_numbers = self.parser.get_line_numbers()
		false_state = None
		try:
			line_idx = line_numbers.index(line_num)
			if line_idx + 1 < len(line_numbers):
				next_line = line_numbers[line_idx + 1]
				false_state = f'line_{next_line}_index_0'
		except ValueError:
			pass

		if next_stmt and next_stmt['type'] == 'GOTO':
			# IF THEN GOTO pattern
			goto_content = next_stmt['content']
			goto_match = re.search(r'GOTO\s*(\d+)', goto_content)
			if goto_match:
				target_line = int(goto_match.group(1))
				target_state = f'line_{target_line}_index_0'

				# If true, goto target. If false, goto next line.
				lines.append(f'if {py_condition}:')
				lines.append(f'	state = "{target_state}"')
				lines.append(f'	continue')
				# Add else clause for false branch
				if false_state and false_state != target_state:
					lines.append(f'else:')
					lines.append(f'	# Condition false - go to next line')
					lines.append(f'	state = "{false_state}"')
					lines.append(f'	continue')
		else:
			# Check for inline THEN target
			then_match = re.search(r'THEN\s*(\d+)', content)
			if then_match:
				target_line = int(then_match.group(1))
				target_state = f'line_{target_line}_index_0'

				# If true, goto target. If false, goto next line.
				lines.append(f'if {py_condition}:')
				lines.append(f'	state = "{target_state}"')
				lines.append(f'	continue')
				# Add else clause for false branch
				if false_state and false_state != target_state:
					lines.append(f'else:')
					lines.append(f'	# Condition false - go to next line')
					lines.append(f'	state = "{false_state}"')
					lines.append(f'	continue')
			else:
				# IF THEN with statement - just check condition, if false skip to next line
				if false_state:
					lines.append(f'if not ({py_condition}):')
					lines.append(f'	state = "{false_state}"')
					lines.append(f'	continue')

		return lines

	def _convert_goto(self, content: str, coord: Tuple[int, int] = None) -> List[str]:
		"""Convert GOTO statement to state transition.

		Args:
			content: GOTO statement content
			coord: Optional (line, index) to check if this GOTO follows an IF

		Returns:
			List of Python code lines
		"""
		match = re.search(r'GOTO\s*(\d+)', content)
		if not match:
			return [f'# Invalid GOTO: {content}']

		target_line = int(match.group(1))
		target_state = f'line_{target_line}_index_0'

		# Check if this GOTO follows an IF statement (IF THEN GOTO pattern)
		# In this case, the IF already handled the condition, so skip this GOTO
		if coord:
			line_num, idx = coord
			prev_coord = (line_num, idx - 1)
			prev_stmt = self.parser.index_mapping.get(prev_coord, {})
			if prev_stmt and prev_stmt['type'] == 'IF':
				# This GOTO is part of an IF THEN GOTO - skip it
				return []

		return [
			f'state = "{target_state}"',
			'continue'
		]

	def _convert_gosub(self, content: str, coord: Tuple[int, int],
					   jump_targets: Dict) -> List[str]:
		"""Convert GOSUB statement with stack push."""
		match = re.search(r'GOSUB\s*(\d+)', content)
		if not match:
			return [f'# Invalid GOSUB: {content}']

		target_line = int(match.group(1))
		return_coord = self._get_next_coordinates(coord)
		return_state = f'line_{return_coord[0]}_index_{return_coord[1]}'

		return [
			f'gosub_stack.append("{return_state}")',
			f'state = "line_{target_line}_index_0"',
			'continue'
		]

	def _convert_return(self) -> List[str]:
		"""Convert RETURN statement with stack pop."""
		return [
			'if not gosub_stack:',
			'	raise Exception("RETURN without GOSUB")',
			'state = gosub_stack.pop()',
			'continue'
		]

	def _convert_for(self, content: str, coord: Tuple[int, int]) -> List[str]:
		"""Convert FOR statement to Python loop initialization."""
		match = re.search(r'FOR\s*(\w+)\s*=\s*(.+)\s*TO\s*(.+)', content)
		if not match:
			return [f'# Invalid FOR: {content}']

		var = match.group(1)
		start = match.group(2).strip()
		end = match.group(3).strip()

		step_val = 1
		if 'STEP' in end:
			step_match = re.search(r'(.+)\s*STEP\s*(.+)', end)
			if step_match:
				end = step_match.group(1).strip()
				step_val = step_match.group(2).strip()

		py_var = self._convert_variable(var)
		py_start = self._convert_expression(start)
		py_end = self._convert_expression(end)
		py_step = self._convert_expression(str(step_val))

		# Calculate the loop body target (statement after FOR)
		loop_body_line, loop_body_idx = self._get_next_coordinates(coord)
		loop_body_state = f'line_{loop_body_line}_index_{loop_body_idx}'

		# Track the loop variable
		self.variables.add(py_var)

		# Store loop info with current value tracking
		return [
			f'# {content}',
			f'{py_var} = FOR("{py_var}", {py_start}, {py_end}, {py_step}, "{loop_body_state}")',
		]

	def _convert_next(self, content: str, coord: Tuple[int, int]) -> List[str]:
		"""Convert NEXT statement to loop continuation."""
		match = re.search(r'NEXT\s*(.*)', content)
		if not match:
			return [f'# Invalid NEXT: {content}']

		vars = match.group(1).strip()
		if not vars:
			vars = 'None'
		elif ',' in vars:
			vars = [f'"{v.strip()}"' for v in vars.split(',')]
			vars = f'[' + ', '.join([v for v in vars]) + ']'
		else:
			vars = f'["{vars}"]'

		# Get next line for fall-through (when loop completes)
		next_line, next_index = self._get_next_coordinates(coord)
		next_state = f'line_{next_line}_index_{next_index}'

		# Build the NEXT logic with proper state transitions
		return [
			f'state = NEXT({vars}, globals(), "{next_state}")',
		]

	def _convert_read(self, content: str) -> List[str]:
		"""Convert READ statement to list indexing."""
		match = re.search(r'READ\s*(.+)', content)
		if not match:
			return [f'# Invalid READ: {content}']

		var_list = match.group(1).strip()
		#vars = [v.strip() for v in var_list.split(',')]

		vars = []
		curr = ""
		pasens = False
		for c in var_list:
			if c == '(':
				parens = True
			elif c == ')':
				parens = False
			if c == ',' and not parens:
				vars.append(curr)
				curr = ""
			else:
				curr += c
		vars.append(curr)

		lines = [
			'if DATA_INDEX >= len(PROGRAM_DATA):',
			'	raise Exception("READ out of DATA")'
		]

		for i, var in enumerate(vars):
			py_var = self._convert_variable(var)
			# Track the variable being read
			self.variables.add(py_var)
			lines.append(f'{py_var} = PROGRAM_DATA[DATA_INDEX + {i}]')

		lines.append(f'DATA_INDEX += {len(vars)}')

		return lines

	def _convert_dim(self, content: str) -> List[str]:
		"""Convert DIM statement to list variable declarations."""
		content = content[3:] # Strip 'DIM'
		print(f"DIM var list: {content}")
		varlist = []
		parens = False
		var = ''
		dim = []
		for c in content:
			if c == '(':
				var += '_l'
				dnums = ''
				parens = True
			elif c == ')':
				dim.append(int(dnums))
				parens = False
			elif c == ',' and not parens:
				varlist.append((var, dim))
				var = ''
				dim = []
			elif c == ',' and parens:
				dim.append(int(dnums))
				dnums = ''
			elif c != ' ' and not parens:
				var += c
			elif parens:
				dnums += c
		varlist.append((var, dim))

		lines = []
		for var, dim in varlist:
			name = var.split('(')[0]
			name = self._convert_variable(name)
			if name.endswith('_s'):
				dims = '""'
			else:
				dims = '0'
			for d in dim:
				dims = f'[{dims}] * {d}'
			lines.append(f"{name} = {dims}")
		return lines

	def _convert_variable(self, var: str, onlyname: bool = False) -> str:
		"""Convert BASIC variable to Python identifier."""
		if onlyname and '(' in var:
			var = var.split('(')[0]
		#var = var.replace('%', '_i').replace('$', '_s').replace('(','[').replace(')',']')
		var = var.replace('%', '_i').replace('$', '_s')
		varout = ""
		braket = False
		for c in var:
			if c == '(':
				braket = True
				c = '_l['
			elif c == ')':
				braket = False
				c = ']'
			if c == ',' and braket:
				c = ']['
			varout += c
		return varout

	def _convert_expression(self, expr: str) -> str:
		"""Convert BASIC expression to Python.

		Handles:
		- Variable indexing: V$(P(1)) -> V_s[P[1]]
		- Function calls: MID$(SI$,2,2) -> MID_s(SI_s,2,2)
		- Boolean operators: AND, OR, NOT -> and, or, not
		- Bitwise operators: AND, OR, NOT -> &, |, ~ (context-dependent)
		"""
		if not expr or not expr.strip():
			return expr

		# Protect string literals first
		strings = []
		string_pattern = r'"[^"]*"'

		def protect_string(match):
			strings.append(match.group(0))
			return f'__STR_{len(strings)-1}__'

		expr = re.sub(string_pattern, protect_string, expr)

		# Tokenize the expression
		tokens = self._tokenize_expression(expr)

		# Parse and convert
		result = self._parse_expression_tokens(tokens, strings)

		return result

	def _insert_concat_operators(self, tokens: list) -> list:
		"""Insert '+' operators for implicit string concatenation.

		In BASIC, strings can be concatenated by placing them adjacent:
		PRINT A$"B"  ->  print(A$ + "B")
		PRINT TAB(16)"X"  ->  print(TAB(16) + "X")
		"""
		if len(tokens) < 2:
			return tokens

		# Functions that return strings
		string_functions = {'TAB', 'SPC', 'MID', 'MID$', 'LEFT', 'LEFT$', 'RIGHT', 'RIGHT$',
							'CHR', 'CHR$', 'STR', 'STR$'}

		result = [tokens[0]]

		for i in range(1, len(tokens)):
			prev_token = tokens[i - 1]
			curr_token = tokens[i]
			prev_type, prev_val = prev_token
			curr_type, curr_val = curr_token

			# Check if previous token is a string (identifier ending with $ or string literal)
			is_prev_string = False
			if prev_type == 'IDENT' and prev_val.endswith('$'):
				is_prev_string = True
			elif prev_type == 'STRING':
				is_prev_string = True
			elif prev_type == 'OP' and prev_val == ')':
				# Check if this closing paren completes a string function call
				# Walk backwards to find the matching opening paren and function name
				paren_depth = 1
				j = i - 2
				while j >= 0 and paren_depth > 0:
					if tokens[j] == ('OP', ')'):
						paren_depth += 1
					elif tokens[j] == ('OP', '('):
						paren_depth -= 1
					j -= 1
				# Now j points to token before opening paren, should be function name
				if j >= 0 and tokens[j][0] == 'IDENT':
					func_name = tokens[j][1].upper()
					if func_name in string_functions:
						is_prev_string = True

			# Check if current token is a string
			is_curr_string = False
			if curr_type == 'IDENT' and curr_val.endswith('$'):
				is_curr_string = True
			elif curr_type == 'STRING':
				is_curr_string = True
			elif curr_type == 'IDENT' and curr_val.upper() in string_functions:
				# Current token is a string function name - check if followed by '('
				if i + 1 < len(tokens) and tokens[i + 1] == ('OP', '('):
					is_curr_string = True

			# Insert '+' if we have adjacent strings
			if is_prev_string and is_curr_string:
				result.append(('OP', '+'))

			result.append(curr_token)

		return result

	def _tokenize_expression(self, expr: str) -> list:
		"""Tokenize a BASIC expression into tokens."""
		tokens = []
		i = 0
		expr = expr.strip()

		while i < len(expr):
			char = expr[i]

			# Skip whitespace
			if char.isspace():
				i += 1
				continue

			# String placeholders
			if expr[i:].startswith('__STR_'):
				match = re.match(r'__STR_(\d+)__', expr[i:])
				if match:
					tokens.append(('STRING', match.group(0)))
					i += len(match.group(0))
					continue

			# Numbers (integers and floats)
			if char.isdigit() or (char == '.' and i + 1 < len(expr) and expr[i + 1].isdigit()):
				j = i
				while j < len(expr) and (expr[j].isdigit() or expr[j] == '.'):
					j += 1
				tokens.append(('NUMBER', expr[i:j]))
				i = j
				continue

			# Keywords (AND, OR, NOT) - must be checked before identifiers
			if expr[i:].upper().startswith('AND'):
				next_char_idx = i + 3
				if next_char_idx >= len(expr) or not expr[next_char_idx].isalnum():
					tokens.append(('KEYWORD', 'AND'))
					i += 3
					continue
			if expr[i:].upper().startswith('OR'):
				next_char_idx = i + 2
				if next_char_idx >= len(expr) or not expr[next_char_idx].isalnum():
					tokens.append(('KEYWORD', 'OR'))
					i += 2
					continue
			if expr[i:].upper().startswith('NOT'):
				next_char_idx = i + 3
				if next_char_idx >= len(expr) or not expr[next_char_idx].isalnum():
					tokens.append(('KEYWORD', 'NOT'))
					i += 3
					continue

			# Identifiers (variables and function names)
			if char.isalpha():
				j = i
				while j < len(expr) and (expr[j].isalnum() or expr[j] in '$%'):
					j += 1
				ident = expr[i:j]
				# Check if identifier starts with a keyword (e.g., "ANDJ" -> "AND" + "J")
				upper_ident = ident.upper()
				if upper_ident.startswith('AND') and len(ident) > 3:
					tokens.append(('KEYWORD', 'AND'))
					tokens.append(('IDENT', ident[3:]))
				elif upper_ident.startswith('NOT') and len(ident) > 3:
					tokens.append(('KEYWORD', 'NOT'))
					tokens.append(('IDENT', ident[3:]))
				elif upper_ident.startswith('OR') and len(ident) >= 2:
					# Check if it's exactly "OR" or followed by non-alpha (like OR=, OR<, etc.)
					# or followed by another identifier (like ORC -> OR + C)
					if upper_ident == 'OR':
						# Exactly OR
						tokens.append(('KEYWORD', 'OR'))
					elif len(ident) > 2:
						next_char = ident[2]
						if not next_char.isalpha():
							# OR followed by operator or number (e.g., OR=, OR1)
							tokens.append(('KEYWORD', 'OR'))
							tokens.append(('IDENT', ident[2:]))
						else:
							# OR followed by identifier (e.g., ORC -> OR + C)
							tokens.append(('KEYWORD', 'OR'))
							tokens.append(('IDENT', ident[2:]))
					else:
						tokens.append(('IDENT', ident))
				else:
					tokens.append(('IDENT', ident))
				i = j
				continue

			# Multi-character operators
			if expr[i:].startswith('<>'):
				tokens.append(('OP', '<>'))
				i += 2
				continue
			if expr[i:].startswith('><'):
				tokens.append(('OP', '><'))
				i += 2
				continue
			if expr[i:].startswith('<='):
				tokens.append(('OP', '<='))
				i += 2
				continue
			if expr[i:].startswith('>='):
				tokens.append(('OP', '>='))
				i += 2
				continue

				# Single character operators and delimiters
			if char in '+-*/=<>()[]{},;':
				tokens.append(('OP', char))
				i += 1
				continue

			# Unknown character, skip it
			i += 1

		return tokens

	def _parse_expression_tokens(self, tokens: list, strings: list) -> str:
		"""Parse tokens and convert to Python expression."""
		# Known BASIC functions that should keep parentheses
		basic_functions = {
			'MID', 'MID$', 'LEFT', 'LEFT$', 'RIGHT', 'RIGHT$',
			'CHR', 'CHR$', 'STR', 'STR$', 'VAL', 'INT',
			'ABS', 'SIN', 'COS', 'TAN', 'ATN', 'LOG', 'EXP',
			'SQR', 'SGN', 'LEN', 'ASC', 'PEEK', 'POKE', 'TAB'
		}

		result = []
		i = 0

		while i < len(tokens):
			token_type, token_value = tokens[i]

			if token_type == 'STRING':
				# Restore string literal
				match = re.match(r'__STR_(\d+)__', token_value)
				if match:
					idx = int(match.group(1))
					if idx < len(strings):
						result.append(strings[idx])
					else:
						result.append(token_value)
				else:
					result.append(token_value)

			elif token_type == 'NUMBER':
				result.append(token_value)

			elif token_type == 'IDENT':
				var_name = token_value
				py_var = self._convert_variable(var_name)

				# Check if next token is '(' - could be array access or function call
				if i + 1 < len(tokens) and tokens[i + 1] == ('OP', '('):
					# Look ahead to find matching ')'
					paren_start = i + 1
					paren_depth = 1
					j = paren_start + 1
					while j < len(tokens) and paren_depth > 0:
						if tokens[j] == ('OP', '('):
							paren_depth += 1
						elif tokens[j] == ('OP', ')'):
							paren_depth -= 1
						j += 1

					# Extract argument tokens
					arg_tokens = tokens[paren_start + 1:j - 1]

					# Check if this is a function call or array access
					upper_var = var_name.upper()
					if upper_var in basic_functions or upper_var.rstrip('$') in basic_functions:
						# It's a function call - keep parentheses
						args_str = self._convert_arguments(arg_tokens, strings)
						result.append(f'{py_var}({args_str})')
					else:
						# It's an array access - convert to brackets
						args_str = self._convert_arguments(arg_tokens, strings)
						result.append(f'{py_var}_l[{args_str.replace(",","][")}]')

					i = j - 1  # Skip to after the closing paren
				else:
					result.append(py_var)

			elif token_type == 'KEYWORD':
				# Convert boolean operators to Python
				if token_value == 'AND':
					result.append('and')
				elif token_value == 'OR':
					result.append('or')
				elif token_value == 'NOT':
					result.append('not')
				else:
					result.append(token_value.lower())

			elif token_type == 'OP':
				# Convert operators
				if token_value == '=':
					result.append('==')
				elif token_value in ('<>', '><'):
					result.append('!=')
				elif token_value == '<=':
					result.append('<=')
				elif token_value == '>=':
					result.append('>=')
				elif token_value == '(':
					result.append('(')
				elif token_value == ')':
					result.append(')')
				elif token_value == '[':
					result.append('[')
				elif token_value == ']':
					result.append(']')
				elif token_value == ',':
					result.append(',')
				elif token_value == ';':
					result.append(';')
				else:
					result.append(token_value)

			i += 1

		return ' '.join(result)

	def _convert_arguments(self, tokens: list, strings: list) -> str:
		"""Convert argument tokens back to a string."""
		if not tokens:
			return ''

		# Reconstruct the expression from tokens
		result = []
		i = 0

		while i < len(tokens):
			token_type, token_value = tokens[i]

			if token_type == 'STRING':
				match = re.match(r'__STR_(\d+)__', token_value)
				if match:
					idx = int(match.group(1))
					if idx < len(strings):
						result.append(strings[idx])
					else:
						result.append(token_value)
				else:
					result.append(token_value)

			elif token_type == 'NUMBER':
				result.append(token_value)

			elif token_type == 'IDENT':
				var_name = token_value
				py_var = self._convert_variable(var_name)

				# Check for nested array/function calls
				if i + 1 < len(tokens) and tokens[i + 1] == ('OP', '('):
					paren_start = i + 1
					paren_depth = 1
					j = paren_start + 1
					while j < len(tokens) and paren_depth > 0:
						if tokens[j] == ('OP', '('):
							paren_depth += 1
						elif tokens[j] == ('OP', ')'):
							paren_depth -= 1
						j += 1

					arg_tokens = tokens[paren_start + 1:j - 1]
					basic_functions = {
						'MID', 'MID$', 'LEFT', 'LEFT$', 'RIGHT', 'RIGHT$',
						'CHR', 'CHR$', 'STR', 'STR$', 'VAL', 'INT',
						'ABS', 'SIN', 'COS', 'TAN', 'ATN', 'LOG', 'EXP',
						'SQR', 'SGN', 'LEN', 'ASC', 'PEEK', 'POKE'
					}

					upper_var = var_name.upper()
					if upper_var in basic_functions or upper_var.rstrip('$') in basic_functions:
						args_str = self._convert_arguments(arg_tokens, strings)
						result.append(f'{py_var}({args_str})')
					else:
						args_str = self._convert_arguments(arg_tokens, strings)
						result.append(f'{py_var}[{args_str}]')

					i = j - 1
				else:
					result.append(py_var)

			elif token_type == 'KEYWORD':
				if token_value == 'AND':
					result.append('and')
				elif token_value == 'OR':
					result.append('or')
				elif token_value == 'NOT':
					result.append('not')
				else:
					result.append(token_value.lower())

			elif token_type == 'OP':
				if token_value == '=':
					result.append('==')
				elif token_value in ('<>', '><'):
					result.append('!=')
				elif token_value == '<=':
					result.append('<=')
				elif token_value == '>=':
					result.append('>=')
				elif token_value in ('(', ')', '[', ']', ',', ';'):
					result.append(token_value)
				else:
					result.append(token_value)

			i += 1

		return ' '.join(result)

	def _convert_condition(self, condition: str) -> str:
		"""Convert BASIC condition to Python condition."""
		return self._convert_expression(condition)

	def _get_next_execution_point(self, coord: Tuple[int, int],
								   jump_targets: Dict,
								   fallthrough: Dict) -> Optional[Tuple[int, int]]:
		"""Determine the next execution point after a statement."""
		if coord in jump_targets:
			targets = jump_targets[coord]
			if targets:
				if coord in fallthrough and fallthrough[coord]:
					return fallthrough[coord][0]

		if coord in fallthrough and fallthrough[coord]:
			return fallthrough[coord][0]

		line_num, idx = coord
		next_idx = idx + 1

		if (line_num, next_idx) in self.parser.index_mapping:
			return (line_num, next_idx)

		line_numbers = self.parser.get_line_numbers()
		try:
			line_idx = line_numbers.index(line_num)
			if line_idx + 1 < len(line_numbers):
				next_line = line_numbers[line_idx + 1]
				return (next_line, 0)
		except ValueError:
			pass

		return None

	def _coord_to_state_name(self, coord: Tuple[int, int],
							 state_mapping: Dict) -> str:
		"""Convert coordinate to state name."""
		line_num, idx = coord
		base_name = f'line_{line_num}_index_{idx}'

		for state_name, state_info in state_mapping.items():
			if state_info['coordinate'] == coord:
				return state_name

		return base_name

if __name__ == "__main__":
	import argparse

	parser = argparse.ArgumentParser(
		description='C64 BASIC to Python Translator',
		epilog='Converts C64 BASIC programs to executable Python code'
	)
	parser.add_argument(
		'input',
		metavar='input.bas',
		help='Input BASIC file (UTF-8 encoded)'
	)
	parser.add_argument(
		'output',
		metavar='output.py',
		help='Output Python file'
	)
	parser.add_argument(
		'-v', '--verbose',
		action='store_true',
		help='Verbose output during translation'
	)
	parser.add_argument(
		'--no-include-header',
		action='store_true',
		help='Skip Python shebang and module docstring'
	)
	parser.add_argument(
		'--pretty-structures',
		action='store_true',
		help='Add formatting for readability'
	)

	args = parser.parse_args()

	try:
		if args.verbose:
			print(f"Reading input file: {args.input}")

		# Parse the BASIC file
		basic_parser = BASICParser()
		basic_parser.parse_file(args.input)

		if args.verbose:
			print(f"Parsed {len(basic_parser.get_line_numbers())} lines")
			print("Analyzing control flow...")

		# Analyze the control flow
		analyzer = StateMachineAnalyzer(basic_parser)
		analyzer.analyze_control_flow()

		if args.verbose:
			print("Generating Python code...")

		# Generate Python code
		generator = PythonCodeGenerator(analyzer, args.verbose)
		python_code = generator.generate(
			include_header=not args.no_include_header,
			pretty=args.pretty_structures
		)

		# Write output file
		if args.verbose:
			print(f"Writing output file: {args.output}")

		with open(args.output, 'w', encoding='utf-8') as f:
			f.write(python_code)

		if args.verbose:
			print(f"Translation complete: {args.input} -> {args.output}")

	except FileNotFoundError:
		print(f"Error: Input file not found: {args.input}", file=sys.stderr)
		sys.exit(1)
	except PermissionError:
		print(f"Error: Permission denied writing to: {args.output}", file=sys.stderr)
		sys.exit(1)
	except Exception as e:
		print(f"Error: {e}", file=sys.stderr)
		if args.verbose:
			import traceback
			traceback.print_exc()
		sys.exit(1)

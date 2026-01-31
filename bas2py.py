#!/usr/bin/env python3
"""
CBM BASIC to Python Translator
Converts C64 BASIC programs to executable Python code using fall-through state machine architecture.

This is Phase 2 of the cbmbas2py translator project. Phase 1 (petscii2text.py) converts PRG
files to UTF-8 text. Phase 2 converts the text to Python.
"""

import argparse
import sys
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
        for part in parts:
            if not part:
                continue

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
        keywords = ['REM', 'INPUT', 'PRINT', 'FOR', 'NEXT', 'GOTO', 'GOSUB', 'RETURN', 'IF', 'DATA', 'DIM']

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
        next_line = self.line_numbers[self.line_numbers.index(line_num) + 1]
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

                elif stmt_type == 'RETURN':
                    target_coord = self._get_return_target()
                    self.coordinates_are_targets[target_coord] = True
                    self.jump_targets[coord] = [target_coord]

                elif stmt_type == 'NEXT':
                    self._handle_next_statement(coord)

                elif stmt_type == 'IF':
                    self._handle_if_statement(coord)

                elif stmt_type == 'FOR':
                    self._handle_for_statement(coord, idx)

    def _parse_goto_target(self, goto_content: str) -> Tuple[int, int]:
        """Parse GOTO target and get statement index.

        Args:
            goto_content: GOTO statement content

        Returns:
            Tuple of (line_number, statement_index)
        """
        import re
        match = re.search(r'GOTO\s+(\d+)', goto_content)
        if match:
            target_line = int(match.group(1))
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
        next_line = self.line_numbers[self.line_numbers.index(line_num) + 1]
        false_coord_key = (next_line, 0)
        self.coordinates_are_targets[false_coord_key] = True

    def _handle_for_statement(self, for_coord: Tuple[int, int], for_idx: int):
        """Handle FOR statement - mark statement following it as potential target.

        Args:
            for_coord: (line, index) of FOR statement
            for_idx: The index of FOR in the statements list
        """
        line_num, idx = for_coord
        next_idx = for_idx + 1

        # Mark statement after FOR as potential target for NEXT branches
        next_coord = (line_num, next_idx)
        self.coordinates_are_targets[next_coord] = True

        # The FOR statement continues to next statement (same line, next index)
        current_coord = (line_num, idx)
        next_in_line = (line_num, next_idx)
        self.jump_targets[current_coord] = [next_in_line]

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


def main():
    """Main entry point for parser demonstration."""
    parser = BASICParser()
    result = parser.parse_file('example2.bas')

    print(f"Parsed {len(result)} lines:")
    for line_num, statements in result:
        print(f"\nLine {line_num}:")
        for idx, stmt in enumerate(statements):
            print(f"  [{idx}] {stmt['type']}: {stmt['content']}")


if __name__ == "__main__":
    main()

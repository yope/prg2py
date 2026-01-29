#!/usr/bin/env python3
"""
CBM BASIC to Python Translator
Converts C64 BASIC programs to executable Python code using fall-through state machine architecture.

This is Phase 2 of the cbmbas2py translator project. Phase 1 (petscii2text.py) converts PRG
files to UTF-8 text. Phase 2 converts the text to Python.
"""

import argparse
import sys
from typing import List, Tuple, Dict
from pathlib import Path


class BASICParser:
    """Parse C64 BASIC files and extract line-by-line structure."""

    def __init__(self):
        """Initialize parser with empty structures."""
        self.coordinate_system: List[Tuple[int, List[str]]] = []  # [(line, [statements]), ...]
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

            for line_num, line_content in enumerate(lines, 1):
                line_content = line_content.strip()
                if not line_content:
                    continue

                self._parse_line(line_num, line_content)

            return self.coordinate_system

        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {filepath}")
        except UnicodeDecodeError:
            raise UnicodeDecodeError("File is not valid UTF-8 encoded")

    def _parse_line(self, line_num: int, line_content: str):
        """Parse a single BASIC line, splitting on colons outside of strings.

        Args:
            line_num: Line number in file
            line_content: Content of the line
        """
        # First, strip line number prefix BEFORE splitting
        base_content = self._strip_line_number(line_content)

        # Now split by colons, but don't split inside quoted strings
        parts = self._split_colons(base_content)

        statements = []
        for part in parts:
            if not part:
                continue

            statement_content = part.strip()
            if statement_content:
                statement_info = self._tokenize_statement(statement_content)
                if statement_info['type'] != 'UNKNOWN':
                    statements.append(statement_info)

        if statements:
            self.coordinate_system.append((line_num, statements))
            self.line_numbers.append(line_num)
            self._update_index_mapping(line_num, len(statements))

    def _split_colons(self, text: str) -> list:
        """Split text by colons, respecting quoted string boundaries.

        Args:
            text: Text potentially containing colons within strings

        Returns:
            List of substrings split at colons outside strings
        """
        parts = []
        current = []
        in_double_quote = False
        in_simple_quote = False

        for char in text:
            if char == '"' and not in_simple_quote:
                in_double_quote = not in_double_quote
                current.append(char)
            elif char == "'" and not in_double_quote:
                in_simple_quote = not in_simple_quote
                current.append(char)
            elif char == ':' and not in_double_quote and not in_simple_quote:
                parts.append(''.join(current))
                current = []
            else:
                current.append(char)

        if current:
            parts.append(''.join(current))

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
                remainder = statement[len(keyword):]
                if remainder:
                    # For REM, always add a space separator
                    if keyword == 'REM':
                        content = f'{keyword} {remainder.lstrip()}'
                    # Add space at start if first char is not already a separator
                    elif not remainder[0] in ' \t(':
                        content = f'{keyword} {remainder.lstrip()}'
                    else:
                        content = f'{keyword}{remainder}'
                else:
                    content = keyword
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

# Functional Specification: C64 BASIC to Python Translator

## Overview

This document describes the functional specifications for the `bas2py` translator tool, which converts Commodore 64 BASIC programs in UTF-8 text format to Python source code. The tool serves as Phase 2 of the `cbmbas2py` translator project.

## Purpose

The translator converts human-readable C64 BASIC programs (produced by `petscii2text.py`) into executable Python code, enabling analysis, modification, and modernization of legacy BASIC programs.

## Input/Output Requirements

### Input Format

The translator accepts UTF-8 encoded BASIC files with the following characteristics:
- Each line starts with a line number (integer, e.g., `10`)
- Statement keywords are in uppercase (e.g., `PRINT`, `GOTO`, `IF`)
- Line numbers are sequential and not required to be contiguous
- Comments start with `REM`
- Statements may be separated by colons (`:`) on the same line
- Strings are delimited by double quotes (`"`)
- REMARK and string contents are in PETSCII encoded UTF-8

Example input (`example.bas`):
```
10 REM Welcome Program
20 PRINT "HELLO"
30 A=10
40 B=20
50 IF A=B THEN GOTO 70
60 GOTO 80
70 PRINT "A=B"
80 PRINT "END"
90 END
```

### Output Format

The translator generates Python source code with a fall-through state machine where non-target lines are combined in their starting state's handler:

```python
#!/usr/bin/env python3
"""
C64 BASIC to Python Translator
Original program converted from: PROGRAM_NAME
"""

from cbmruntime import *

def main():
    # Program state
    state = "init"

    while True:
        if state == "init":
            # Fall-through: Lines 10-60 execute here (no line_10, line_20, etc. states)
            # Original: 10 REM Welcome Program
            # Original: 20 PRINT "HELLO"
            print("HELLO")
            # Original: 30 A=10
            A = 10
            # Original: 40 B=20
            B = 20
            # Original: 50 IF A=B THEN GOTO 70
            if A == B:
                state = "line_70"
                continue
            # Original: 60 GOTO 80
            state = "line_80"
            continue

        elif state == "line_70":
            # Original: 70 PRINT "A=B"
            print("A=B")
            state = "line_80"
            continue

        elif state == "line_80":
            # Original: 80 PRINT "END"
            print("END")
            # Original: 90 END
            break

        else:
            raise Exception(f"Unknown state: {state}")

if __name__ == "__main__":
    main()
```

## Design Approach

### State Machine Architecture

Due to the unstructured nature of C64 BASIC and the lack of GOTO/GOSUB semantics in Python, the translator uses a state machine with an infinite loop approach:

1. **Infinite Loop**: The main program executes in a `while True:` loop
2. **State Variable**: Current execution position tracked by a state variable
3. **Fall-through Design**: Lines that are not jump targets are combined in a single state handler, executing sequentially
4. **Target Identification**: Each distinct GOTO/GOSUB/NEXT/RETURN target gets its own `elif` handler
5. **Explicit Transitions**: GOTO statements are replaced with explicit state assignments followed by `continue`

**Design Pattern:**

```python
def main():
    state = "init"

    while True:
        if state == "init":
            # Fall-through: All non-target lines execute here
            # Original: 10 REM Welcome Program
            # Original: 20 PRINT "HELLO"
            print("HELLO")
            # Original: 30 A=10
            A = 10
            # Original: 40 B=20
            B = 20
            # Original: 50 IF A=B THEN GOTO 70
            if A == B:
                state = "line_70"
                continue
            # Original: 60 GOTO 80
            state = "line_80"
            continue

        elif state == "line_70":
            # Original: 70 PRINT "A=B"
            print("A=B")
            state = "line_80"
            continue

        elif state == "line_80":
            # Original: 80 PRINT "END"
            print("END")
            # Original: 90 END
            break

        else:
            raise Exception(f"Unknown state: {state}")
```

### State Identification

State names follow the pattern `<line_number>` (e.g., `line_10`, `line_20`, `line_30`). Each distinct line number in the original BASIC program becomes a unique state **only if it's a target of any jump**:
- GOTO targets
- GOSUB targets
- NEXT continuation targets
- RETURN destination targets
- IF...THEN implicit GOTO targets

All other lines execute directly as sequential code in the main while loop without dedicated elif blocks.

### Control Flow Conversion

#### GOTO Statements

Unreachable lines are collapsed.

#### GOSUB Statements

Subroutines use RETURN to return to the GOSUB point.

#### FOR/NEXT Loops

**Original**:
```
100 FOR I=1 TO 10
110 PRINT I
120 NEXT I
```

**Converted**:
```python
elif state == "line_100":
    # Original: 100 FOR I=1 TO 10
    I = 1
    state = "line_110"

elif state == "line_110":
    # Original: 110 PRINT I
    print(I)
    if I >= 10:
        state = "line_120"
        I = I + 1
    else:
        state = "line_100"

elif state == "line_120":
    # Original: 120 NEXT I
    # Loop ended
    state = "next_state_from_100"
```

#### Data/READ Statements

**Original**:
```
100 DATA 10, 20, 30
110 READ A, B, C
```

**Converted**:
```python
DATA_PROGRAM_DATA = [10, 20, 30]
DATA_PROGRAM_INDEX = 0

elif state == "line_100":
    # Original: 100 DATA 10, 20, 30
    pass

elif state == "line_110":
    # Original: 110 READ A, B, C
    if DATA_PROGRAM_INDEX < len(DATA_PROGRAM_DATA):
        A = DATA_PROGRAM_DATA[DATA_PROGRAM_INDEX]
        B = DATA_PROGRAM_DATA[DATA_PROGRAM_INDEX + 1]
        C = DATA_PROGRAM_DATA[DATA_PROGRAM_INDEX + 2]
        DATA_PROGRAM_INDEX += 3
    else:
        raise Exception("READ out of DATA")
```

## Language Mapping

### BASIC Statements to Python

| BASIC Statement | Python Equivalent |
|----------------|-------------------|
| `PRINT` | `cbmprint()` (with PETSCII escape code translation) |
| `"HELLO"` | `"HELLO"` (string literal) |
| `INPUT` | `input()` |
| `LET` | assignment operator `=` |
| `IF ... THEN` | conditional state transition |
| `GOTO` | state assignment |
| `END` | loop termination or explicit return |
| `FOR ... TO ... STEP` | `cbmruntime.FOR()` / `cbmruntime.NEXT()` |
| `NEXT` | Loop control via runtime |
| `RETURN` | state assignment to return position |
| `GOSUB` | state assignment with return tracking |
| `DATA` | list constant |
| `READ` | list indexing |
| `REM` | comment (apostrophe `'` is NOT supported in C64 BASIC) |
| `:` | new statement on same line |
| `DIM` | Array initialization using `cbmruntime.DIM()` |
| `LEN(x)` | `cbmruntime.LEN(x)` |
| `MID$(x,i,l)` | `cbmruntime.MID_s(x,i,l)` |
| `INT(x)` | `cbmruntime.INT(x)` |
| `RND(x)` | `cbmruntime.RND(x)` |
| `TAB(x)` | `cbmruntime.TAB(x)` (ANSI escape codes) |
| Variable conversion | `%` → `_i`, `$` → `_s`, array `()` → `_l` |
| **Note**: C64 BASIC does not support the apostrophe (`'`) as REM abbreviation; only `REM` keyword is recognized |

### Variables

- Variables are converted to Python identifiers
- All variables default to `float` type (no type declarations in BASIC)
- **Number (floating point) variables**: one or two letters (no suffix)
  - Example: `A`, `X`, `ABC`, `XY` → `A`, `X`, `ABC`, `XY`
- **Integer variables**: one or two letters followed by percent symbol `%`
  - Example: `A%`, `X%`, `ABC%`, `XY%` → `A_i`, `X_i`, `ABC_i`, `XY_i`
- **String variables**: one or two letters followed by dollar symbol `$`
  - Example: `A$`, `X$`, `ABC$`, `XY$` → `A_s`, `X_s`, `ABC_s`, `XY_s`
- **Arrays**: Same base name with `_l` suffix (to distinguish from scalars)
  - Float arrays: `A()`, `X()` → `A_l`, `X_l`
  - Integer arrays: `A%()`, `X%()` → `A_i_l`, `X_i_l`
  - String arrays: `A$()`, `X$()` → `A_s_l`, `X_s_l`
- Character handling maintains UTF-8 encoding

**Note:** In C64 BASIC, a variable and array can share the same name (e.g., `C` and `C(10)` are distinct). The `_l` suffix ensures they remain separate in Python.

## Execution Flow

1. **Parser**: Reads input BASIC file, parses line by line
2. **Analyzer**: Builds control flow graph, identifies all states and transitions
3. **Generator**: Generates Python state machine code
4. **Output**: Writes Python source file

## Error Handling

1. **Parsing Errors**: Missing line numbers, malformed statements
2. **Control Flow Errors**: Undefined GOTO/GOSUB targets
3. **Runtime Errors**: READ out of DATA bounds, undefined variables
4. **Output Issues**: File I/O failures

All errors should be reported to the user with clear messages.

## Implementation Requirements

### Command-Line Interface

```bash
bas2py input.bas output.py [-v] [--no-include-header] [--pretty-structures]
```

### Options

- `input.bas`: Input BASIC file (UTF-8)
- `output.py`: Output Python file
- `-v/--verbose`: Verbose output during translation
- `--no-include-header`: Skip Python shebang and module docstring
- `--pretty-structures`: Add formatting for improved readability

## Testing

### Test Cases

1. **Basic Statements**: PRINT, LET, variables (non-target lines)
2. **Control Flow**: IF...THEN with GOTO, GOTO, GOSUB, RETURN
3. **Loops**: FOR/NEXT with and without STEP
4. **Subroutines**: Multiple GOSUB calls, nested calls
5. **Lists**: DATA/READ/RESTORE operations
6. **Comments**: REM statements
7. **Mixed Statements**: Multiple statements per line (using `:`)
8. **Complex Logic**: Nested conditions, multi-line statements
9. **Edge Cases**: Empty files, single-line programs
10. **Fall-through Optimization**: Non-target lines combined into single state handlers
11. **Multiple Targets**: Programs with multiple distinct GOTO targets

### Validation

- Generated Python code is syntactically correct
- State variable names are unique
- All GOTO/GOSUB target states exist
- Logical flow matches original BASIC program

## Examples

### Simple Program Example

Input (`example1.bas`):
```
10 REM Welcome Program
20 PRINT "HELLO"
30 A=10
40 B=20
50 IF A=B THEN GOTO 70
60 GOTO 80
70 PRINT "A=B"
80 PRINT "END"
90 END
```

Output (`expected.py`):
```python
#!/usr/bin/env python3
"""
C64 BASIC to Python Translator
Original program converted from: PROGRAM_NAME
"""

def main():
    # Program state
    state = "init"

    while True:
        if state == "init":
            # Fall-through: Lines 10-60 execute here (no line_10, line_20, etc. states)
            # Original: 10 REM Welcome Program
            # Original: 20 PRINT "HELLO"
            print("HELLO")
            # Original: 30 A=10
            A = 10
            # Original: 40 B=20
            B = 20
            # Original: 50 IF A=B THEN GOTO 70
            if A == B:
                state = "line_70"
                continue
            # Original: 60 GOTO 80
            state = "line_80"
            continue

        elif state == "line_70":
            # Original: 70 PRINT "A=B"
            print("A=B")
            state = "line_80"
            continue

        elif state == "line_80":
            # Original: 80 PRINT "END"
            print("END")
            # Original: 90 END
            break

        else:
            raise Exception(f"Unknown state: {state}")

if __name__ == "__main__":
    main()
```

### State Optimization Example

For programs with many sequential non-target lines, only target lines create separate `elif` states. For example, if we add line 15:

**Input (`example1_extended.bas`)**:
```
10 REM Welcome Program
15 PRINT "CONTINUE"
20 PRINT "HELLO"
30 A=10
40 B=20
50 IF A=B THEN GOTO 70
60 GOTO 80
70 PRINT "A=B"
80 PRINT "END"
90 END
```

**Output** (lines 15-60 all fall through in state "init"):
```python
if state == "init":
    # Original: 10 REM Welcome Program
    # Original: 15 PRINT "CONTINUE"
    print("CONTINUE")
    # Original: 20 PRINT "HELLO"
    print("HELLO")
    # Original: 30 A=10
    A = 10
    # Original: 40 B=20
    B = 20
    # Original: 50 IF A=B THEN GOTO 70
    if A == B:
        state = "line_70"
        continue
    # Original: 60 GOTO 80
    state = "line_80"
    continue
```

## Runtime Library (cbmruntime.py)

The translator relies on `cbmruntime.py` for BASIC function implementations and terminal compatibility:

### Core Functions
- **`LEN(x)`**: Returns length of string x
- **`MID_s(x, i, l)`**: Returns substring starting at position i (1-based), length l
- **`INT(x)`**: Returns integer portion of x
- **`RND(x)`**: Returns random float (0.0 to 1.0)
- **`TAB(x)`**: Returns ANSI escape sequence for cursor positioning

### Array Support
- **`DIM(dimtype, *sizes)`**: Creates multi-dimensional arrays initialized with dimtype
- **`autodim(glob, *varnames)`**: Auto-dimensions arrays with default size 11

### Loop Control
- **`FOR(var, start, end, step, body_state)`**: Initializes FOR loop
- **`NEXT(vars, glob, next_state)`**: Iterates FOR loop with ~1.55ms delay per iteration

### Terminal Output
- **`cbmprint(*args, **kvargs)`**: Prints with PETSCII escape code translation to ANSI
  - Supports C64 color codes: {BLACK}, {WHITE}, {RED}, {CYAN}, etc.
  - Supports cursor control: {CRSR-UP}, {CRSR-DOWN}, {HOME}, {CLEAR}
  - Supports reverse video: {RVS-ON}, {RVS-OFF}

### PETSCII Escape Format
PETSCII control codes are tokenized by `petscii2text.py` as `{CODE}` sequences:
- Colors: `{BLUE}`, `{RED}`, `{GREEN}`, `{YELLOW}`, etc.
- Cursor: `{CRSR-UP}`, `{CRSR-DOWN}`, `{CRSR-LEFT}`, `{CRSR-RIGHT}`
- Screen: `{HOME}`, `{CLEAR}`, `{RVS-ON}`, `{RVS-OFF}`

## Future Enhancements

1. **Type Inference**: Add type annotations for variables
2. **Constants**: Handle variable initial values differently
3. ~~**Array Support**: Implement DIM and array index operations~~ ✓ Implemented via cbmruntime.DIM()
4. **Sys Statements**: Map to Python's system calls
5. **Poke/Peek**: Map to Python memory operations
6. **Save/Load**: Implement file I/O utilities
7. **Documentation**: Allow automatic documentation generation
8. **Variable Reference Tracking**: Provide mapping between BASIC and Python variables
9. **Extended BASIC Functions**: Additional C64 BASIC functions (PEEK, POKE, SYS, SIN, COS, etc.)

## Related Components

This tool is Phase 2 of the cbmbas2py translator project. It builds upon:
- Phase 1: `petscii2text.py` - PRG to UTF-8 text converter
- **Runtime Library**: `cbmruntime.py` - BASIC function implementations (PRINT, LEN, MID$, INT, RND, TAB, FOR/NEXT loops, DIM arrays, PETSCII terminal translation)
- Related tools for C64 program analysis and conversion

## Version History

- **v0.1**: Initial state machine-based translator specification
- **v0.2**: Added cbmruntime.py runtime library with BASIC function implementations (LEN, MID$, INT, RND, TAB, FOR/NEXT, DIM, cbmprint with PETSCII terminal translation). Added `_l` suffix for arrays to distinguish from scalar variables with the same name.
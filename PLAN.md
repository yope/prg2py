# Development Plan: bas2py.py Implementation

## Overview
This document provides a step-by-step development plan for implementing `bas2py.py` according to specifications in FSP.md. The tool converts C64 BASIC programs (UTF-8 encoded) to executable Python code using a fall-through state machine architecture.

## Phase 1: Project Setup and Directory Structure
**Goal:** Prepare the development environment and project structure.

### Sub-tasks:
1. Create empty `bas2py.py` file
2. Review and understand FSP.md specifications
3. Examine `example1.bas` and `example1.py` as reference
4. Confirm petSCII to UTF-8 conversion already works via `petscii2text.py`

### Deliverable:
- Empty `bas2py.py` file ready for implementation

---

## Phase 2: File Parser Implementation
**Goal:** Parse UTF-8 BASIC files and extract line-by-line structure.

### Sub-tasks:
1. Implement file reading function (UTF-8 encoding support)
2. Parse line structure: line number followed by statements
3. Handle line number validation (must be integer)
4. Handle missing line numbers gracefully
5. Handle malformed statements (basic error checking)
6. Tokenize statements into executable components, detecting colons as statement separators
7. Build coordinate system: `[(line_number, [st0, st1, st2, ...]), ...]`
8. Build statement index mapping: `[(line_number, index) -> statement]`

### Statement Index Structure:
- Line 10: Statement 0: PRINT "HELLO"
- Line 10: Statement 1: A = 10
- Line 10: Statement 2: B = 20
- Line 70: Statement 0: PRINT "A=B"
- Line 80: Statement 0: PRINT "END"

### Key Distinction:
- GOTO <line_number> targets: `line_<line_number>_index_0`
- IF ... THEN GOTO <line_number> can target anywhere: `line_<line_number>_index_n`
- GOSUB statements must mark return destination for state tracking
- RETURN statement must specify exact return coordinates: `line_<line>_index_<n>`

### State Variable Naming: `line_<line>_index_<n>`

### Example State Pattern:
```python
while True:
    if state == "line_10_index_0":
        print("HELLO")
        state = "line_10_index_1"
        continue

    elif state == "line_10_index_1":
        A = 10
        A = B
        if state == "line_10_index_1":
            state = "line_70_index_0"
            continue

    elif state == "line_70_index_0":
        print("A=B")
        state = "line_80_index_0"
        continue

    elif state == "line_80_index_0":
        print("END")
        break
```

### Testing Requirements:
- Parse valid UTF-8 BASIC file successfully
- Handle invalid line numbers appropriately
- Detect and report malformed lines
- Extract statements correctly from example1.bas

### Deliverable:
- Functional parser that produces structured line data

---

## Phase 3: State Machine Analyzer
**Goal:** Identify jump targets and fall-through chains for optimization.

### Sub-tasks:
1. Build control flow graph using 2D coordinates
2. Identify jump targets:
   - GOTO <line_number> → `line_<line>_index_0`
   - GOSUB <line_number> (mark both origin and destination for return tracking, use coordinate stack)
   - NEXT <var> → fallthrough to next statement index (use same state)
   - RETURN with coordinates → `line_<line>_index_<n>` - coordinate popped from stack
   - IF ... THEN conditional: IF true → fallthrough to next statement, IF false → to `line_<line>_index_0`
3. Mark statement coordinates as "targets" vs "non-targets"
4. Determine fall-through analysis:
   - Analyze each line's statement sequence
   - Track next statement automatically by incrementing index
   - IF/THEN: if condition true, continue to next index; if false, jump to next line index_0
   - FOR statement: statement immediately following FOR (same line or next line) is a potential target
   - FOR/NEXT: which NEXT corresponds to which FOR is determined later in Phase 4 analysis
     NEXT statement has TWO possible branches:
     - If loop complete: fallthrough to next statement index (index_n+1) in same handler (or next line start)
     - If loop not complete: jump to statement immediately following the FOR statement (state name determined in Phase 4)
   - GOSUB/RETURN: track return coordinates using stack
5. Generate state mapping with unique names:
   - All states: `line_<line>_index_<n>` (use consistent naming for everything)
   - Track GOSUB origin and destination coordinates for return stack
   - Non-target combined: group by index in first line's handler

### State Variable Naming Convention: `line_<line>_index_<n>`

### Fall-through Analysis Rules:
- Sequential execution: index_n → index_n+1 in same line (automatic continue)
- Line continuation: index_last → index_0 in next line (automatic state transition)
- IF/THEN conditional: both paths start from current index
  - IF true: continue to index_n+1 (no state change)
  - IF false: jump to line_<line>_index_0 (new state, then continue)
- FOR statement: statement immediately following FOR is a target that may be needed for NEXT branches
  - State variable created for the target statement
  - Whether NEXT branches to fallthrough or jumps forward depends on loop condition
- NEXT statement: handled as described in subtask 2, with two possible branches (loop complete vs not complete)
- GOSUB/RETURN: use stack for coordinates; NO state variable change at GOSUB (fallthrough), RETURN pops and changes state

### Testing Requirements:
- Correctly identify all GOTO/GOSUB/NEXT/RETURN statement types
- Properly detect coordinate-based branches (any index, not just line start)
- Handle multi-statement lines with colons correctly
- Properly detect single and multi-statement fall-through chains
- Handle edge cases: single line, single statement, unreachable lines
- Validate with example1.bas and multi-statement lines

### Deliverable:
- State mapping structure mapping line numbers to handler information

---

## Phase 4: Python Code Generator
**Goal:** Convert BASIC statements to Python code using state machine pattern.

### Sub-tasks:
1. Implement variable conversion function:
    - A, X, Y (float) → Python `float` variables
    - A%, X% (integer) → Python `int` variables with `_i` suffix
    - S$, T$ (string) → Python `str` variables with `_s` suffix
    - Arrays → Python `list` variables with `_l` suffix appended after type suffix
      - A(), B() → `A_l`, `B_l` (float arrays)
      - A%(), X%() → `A_i_l`, `X_i_l` (integer arrays)
      - S$(), T$() → `S_s_l`, `T_s_l` (string arrays)

2. Implement statement-to-Python conversion mapping:
    - `PRINT` → Python `cbmprint()` (from cbmruntime.py for PETSCII support)
    - implicit `LET` → Python assignment `var = value`
    - `IF ... THEN` → Python `if`: if true (continue), if false (state=next_line_index_0 + continue)
    - `GOTO` → State assignment to target_line_index_0 + continue
    - `DATA` → List constant definition
    - `READ` → List indexing
    - `FOR ... TO` → Loop with counter and state tracking using cbmruntime.FOR()
    - `NEXT` → Loop increment using cbmruntime.NEXT()
    - `GOSUB` → Push current state to stack, continue (no state change)
    - `RETURN` → Pop state from stack and change state, then continue
    - `REM` → Comment (no `#` prefix)
    - `:` → Sequential statement separator
    - `DIM` → Array initialization using cbmruntime.DIM()
    - `LEN(x)` → cbmruntime.LEN(x)
    - `MID$(x,i,l)` → cbmruntime.MID_s(x,i,l)
    - `INT(x)` → cbmruntime.INT(x)
    - `RND(x)` → cbmruntime.RND(x)
    - `TAB(x)` → cbmruntime.TAB(x)

3. Generate main() function with:
   - State variable initialization
   - Infinite while True loop
   - State handlers grouped by fall-through chains
   - Target line handlers with dedicated elif blocks
   - State assignment and continue statements
   - Break statement for end of program

### Code Structure Pattern:
```python
def main():
    state = "line_0_index_0"

    while True:
        if state == "line_0_index_0":
            # Lines 10-60 non-target statements
            print("HELLO")
            A = 10
            B = 20
            if A == B:
                state = "line_2_index_0"
                continue
            state = "line_3_index_0"
            continue

        elif state == "line_2_index_0":
            # Line 70 target
            print("A=B")
            state = "line_3_index_0"
            continue

        elif state == "line_3_index_0":
            # Line 80 target and end
            print("END")
            break

        else:
            raise Exception(f"Unknown state: {state}")
```

### Testing Requirements:
- Variable conversion produces correct Python identifiers
- Statement-to-Python mapping is accurate
- Control flow matches original BASIC program
- Multi-statement lines with colons handle all statements correctly
- State transitions respect index coordinates (not just line numbers)
- IF/THEN conditional branches work correctly (true = fallthrough, false = new state)
- GOSUB/RETURN stack operations function correctly
- FALLTHROUGH optimization applies to consecutive statements in same line
- No syntax errors in generated code

### Deliverable:
- Python code generation engine producing executable Python

---

## Phase 4.5: Runtime Library Integration
**Goal:** Implement and integrate cbmruntime.py for BASIC function support.

### Sub-tasks:
1. **Core Functions:**
   - `LEN(x)` - String length
   - `MID_s(x, i, l)` - Substring extraction (1-based indexing)
   - `INT(x)` - Integer conversion
   - `RND(x)` - Random number generation
   - `TAB(x)` - ANSI cursor positioning

2. **Array Support:**
   - `DIM(dimtype, *sizes)` - Multi-dimensional array creation
   - `autodim(glob, *varnames)` - Automatic array dimensioning

3. **Loop Control:**
   - `FOR(var, start, end, step, body_state)` - FOR loop initialization
   - `NEXT(vars, glob, next_state)` - FOR loop iteration with C64 timing

4. **Terminal Output:**
   - `cbmprint(*args, **kvargs)` - PETSCII to ANSI translation
   - Color code support (16 C64 colors)
   - Cursor control codes
   - Reverse video support

5. **Integration:**
   - Generated Python code imports from cbmruntime
   - All PRINT statements use cbmprint()
   - All loops use FOR/NEXT from runtime

### Testing Requirements:
- Runtime functions match C64 BASIC behavior
- PETSCII codes render correctly in xterm
- Array operations work with multiple dimensions
- FOR loops have correct timing for delay loops

### Deliverable:
- `cbmruntime.py` with all BASIC function implementations
- Generated code imports and uses runtime correctly

---

## Phase 5: CLI Interface Implementation
**Goal:** Add command-line interface for tool usage.

### Sub-tasks:
1. Implement argparse argument parsing:
   - `--input`: Required input BAS file (UTF-8 encoded)
   - `--output`: Required output Python file
   - `-v`, `--verbose`: Verbose output mode
   - `--no-include-header`: Skip Python shebang and module docstring
   - `--pretty-structures`: Add formatting for readability

2. Handle file I/O:
   - Read input file
   - Write output file

3. Add error handling:
   - File not found errors
   - Invalid file format errors
   - Malformed BASIC errors
   - Write permission errors

4. Add verbose output (if requested)

### Testing Requirements:
- All command-line options work correctly
- Error handling for invalid inputs
- Successful conversions without crashes
- Output matches expected FSP.md format

### Deliverable:
- Fully functional CLI tool per specifications

---

## Phase 6: Testing and Validation
**Goal:** Verify implementation matches specifications and produces correct output.

### Sub-tasks:
1. **Unit Testing:**
   - Parser tests (valid/invalid lines, malformed input)
   - State analyzer tests (target identification, fall-through detection)
   - Generator tests (variable conversion, statement mapping)

2. **Integration Tests:**
   - Simple programs (print statements, basic arithmetic)
   - Control flow (IF/THEN, GOTO, nested conditionals)
   - Loops (FOR/NEXT with and without STEP)
   - Subroutines (multiple GOSUB calls, nested calls)
   - Lists (DATA/READ operations)
   - Complex cases (mixed structures, line chains)

3. **Validation Checklist:**
   - Generated Python is syntactically correct
   - State variable names are unique and consistent
   - All jump targets have dedicated handlers
   - Non-target lines execute sequentially (fall-through)
   - Variable conversion follows C64 conventions
   - Logical flow matches original BASIC program
   - No apostrophe REM usage (only `REM` keyword)
   - No ELSE keyword usage
   - No trailing whitespace

4. **End-to-End Test:**
   - Run `petscii2text.py` on example1.prg
   - Run `bas2py.py` on converted example1.bas
   - Compare output with expected `example1.py`

### Deliverable:
- Comprehensive test suite with valid results
- Validated implementation with no errors

---

## Phase 7: Code Refinement and Cleanup
**Goal:** Polish implementation, ensure code quality, and finalize.

### Sub-tasks:
1. **PEP-8 Compliance:**
   - Strict TAB characters only for indentation (except token/argument separators)
   - No trailing whitespace in any lines
   - No trailing whitespace in empty lines

2. **Code Review:**
   - Verify all specifications are met
   - Check edge cases are handled
   - Validate error handling is sufficient

3. **Documentation:**
   - Add inline comments where clarifying
   - Ensure README or inline documentation exists

4. **Performance Verification:**
   - No unnecessary complexity
   - Efficient state machine patterns

### Deliverable:
- Production-ready `bas2py.py` with high code quality

---

## Phase 8: Git Commit and Documentation
**Goal:** Finalize version control with proper commit messages.

### Sub-tasks:
1. Review all changes
2. Create commit following Linux kernel style:
   ```
   git commit -s -m "feat: implement bas2py.py translator

   Implements C64 BASIC to Python conversion tool with fall-through
   state machine architecture. Converts UTF-8 encoded BASIC to
   executable Python using optimized state handling.

   Changes:
   - Phase 1: Parser with line number detection
   - Phase 2: State machine analyzer for jump targets
   - Phase 3: Python code generator with statement mapping
   - Phase 4: CLI interface with all required flags
   - Phase 5: Testing and validation

   Signed-off-by: [agent_name] [agent@yope.corporation]"
   ```

3. Push to remote repository

### Deliverable:
- Clean git history with proper signed-off commits

---

## Summary

**Total Stages:** 8
**Primary Components:**
1. File Parser (2D coordinate system)
2. State Machine Analyzer (statement-indexed)
3. Python Code Generator
4. CLI Interface
5. Runtime Library (cbmruntime.py) - BASIC function implementations

**Key Design Patterns:**
- Fallthrough state machine with 2D coordinates (line_number, index)
- Statement-indexed state variables: `line_<line>_index_<n>`
- Automatic index progression within lines
- Multi-path branching from IF/THEN in same line
- Special handling for NEXT/GOSUB/RETURN with exact coordinates
- Runtime library pattern for BASIC function implementations
- PETSCII-to-ANSI translation for terminal compatibility

**Critical Success Factors:**
- Correct control flow translation handling multi-statement lines
- Proper index-based state optimization
- Variable naming compliance
- Code quality (PEP-8, no trailing whitespace)
- Runtime library functions match C64 BASIC semantics
- PETSCII escape codes render correctly in xterm

**Critical Design Decisions:**
1. **Multi-statement support**: Colons in same line create separate statement indices
2. **Fine-grained targets**: IF/THEN branches can target any index, not just line start
3. **Exact coordinates**: All jumps (GOTO, GOSUB, RETURN) use precise coordinate system
4. **Automatic fallthrough**: Indices automatically increment within lines
5. **Return tracking**: GOSUB must record exact return coordinates
6. **Array naming**: Arrays use `_l` suffix to distinguish from scalar variables (e.g., `C` → `C`, `C(10)` → `C_l`)

**Example State Flow:**
```
Line 10: [PRINT, LET_1, LET_2, IF_THEN]
State variable: line_10_index_3

Execution:
  line_10_index_0 → PRINT "HELLO"
  → line_10_index_1 → LET_1
  → line_10_index_2 → LET_2
  → line_10_index_3 → IF condition
    IF true: line_70_index_0
    IF false: line_80_index_0
```

Estimated **development effort**: Phases 1-6 each take approximately 2-3 hours depending on complexity.

---

## Appendix: Implementation Reference

### Variable Mapping Table
| BASIC Variable | Python Type | Naming Convention |
|----------------|-------------|--------------------|
| A, B, C, X, Y  | float       | No suffix (float)  |
| A%, X%         | int         | `_i` suffix (int)  |
| S$, T$         | str         | `_s` suffix (str)  |
| **Arrays**     |             |                    |
| A(), B(), C()  | list        | `_l` suffix (list) |
| A%(), X%()     | list        | `_i_l` suffix      |
| S$(), T$()     | list        | `_s_l` suffix      |

**Note:** Arrays use the `_l` suffix to distinguish them from scalar variables with the same name. For example, `C` (float scalar) and `C(10)` (float array) become `C` and `C_l` in Python.

### BASIC Function Mapping Table
| BASIC Function | Python Runtime Call | Description |
|----------------|---------------------|-------------|
| `LEN(x)`       | `LEN(x)`            | String length |
| `MID$(s,i,l)`  | `MID_s(s,i,l)`      | Substring (1-based index) |
| `INT(x)`       | `INT(x)`            | Integer conversion |
| `RND(x)`       | `RND(x)`            | Random number (0.0-1.0) |
| `TAB(x)`       | `TAB(x)`            | Cursor positioning |
| `DIM A(n)`     | `A = DIM(0, n)`     | Array initialization |
| `FOR/NEXT`     | `FOR()` / `NEXT()`  | Loop with timing |
| `PRINT`        | `cbmprint()`        | Terminal output with PETSCII |

### Required Files
- FSP.md - Complete functional specifications
- AGENTS.md - Agent guidance and coding conventions
- PLAN.md - This development plan document
- example1.bas - Sample BASIC input
- example1.py - Expected Python output
- petscii2text.py - Phase 1 converter (PRG to UTF-8)
- cbmruntime.py - BASIC runtime library with function implementations

### Running the Tool
```bash
python bas2py.py example1.bas output.py -v --pretty-structures
```

### Expected Output Structure
```python
#!/usr/bin/env python3
"""
CBM BASIC to Python Translator
Converts C64 BASIC programs to executable Python code.
"""

from cbmruntime import *

# State definition and program execution...

def main():
    state = "init"

    while True:
        # State handlers here...

if __name__ == "__main__":
    main()
```

# Agent Guide: C64 BASIC to Python Translator Project

## Project Overview

This is Phase 2 of the `cbmbas2py` translator project, which converts Commodore 64 BASIC programs to Python code. The translator transforms human-readable C64 BASIC (produced by `petscii2text.py`) into executable Python using a fall-through state machine architecture.

**Purpose**: Enable analysis, modification, and modernization of legacy BASIC programs on modern platforms.

**Workflow**: `petscii2text.py` (PRG → UTF-8) → `bas2py.py` (UTF-8 → Python) → Executable Python code

## Coding Style

All Python code (source and generated) must adhere to **PEP-8** with these specific rules:

### Code Indentation
- **Strict TAB characters only** for indentation, except for separating tokens and identifiers (e.g., `print(` `)` spaces)
- **Spaces allowed** only for token separators, argument delimiters, and within strings
- Consistent use of single tab character (not expanded to spaces or mixed with spaces)

### Whitespace
- **No trailing whitespace** allowed in any non-empty code lines
- **No trailing whitespace** allowed in empty lines
- Remove all trailing spaces before finalizing code

## File Structure

```
prg2py/
├── FSP.md                 # Functional Specifications (this file)
├── AGENTS.md              # This file - Agent guide
└── petscii2text.py        # Phase 1: PRG to UTF-8 converter
```

## Working with the Specifications

### Reading FSP.md

FSP.md contains the complete functional specification for the `bas2py.py` tool:

1. **Overview & Purpose**: Context and goals
2. **Input/Output Requirements**: Format specifications and examples
3. **Design Approach**: Fall-through state machine architecture
4. **Language Mapping**: Statement-to-Python conversion rules
5. **Variable Conventions**: C64 variable types (`%` → `_i`, `$` → `_s`)
6. **Execution Flow**: Translation pipeline stages
7. **Implementation Requirements**: CLI interface options
8. **Testing**: Test cases and validation criteria

### Key Design Decisions

- **Fall-through optimization**: Non-target lines execute sequentially in their starting state's handler
- **State variables**: Only GOTO/GOSUB/NEXT/RETURN targets create separate `elif` states
- **Control flow**: Implemented via explicit state transitions with `continue`
- **Variable naming**: C64 variable conventions must be preserved in Python identifiers

## Coding the `bas2py.py` Tool

### Required Components

1. **File Parser**:
   - Read UTF-8 encoded BASIC file
   - Parse line-by-line structure (line number + statements)
   - Identify jump targets for state optimization

2. **State Machine Analyzer**:
   - Build control flow graph
   - Mark line numbers as "targets" vs "non-targets"
   - Determine fall-through chains

3. **Python Generator**:
   - Generate main() function with while True loop
   - Create state handlers for jump targets
   - Combine non-target lines into fall-through handlers
   - Add appropriate Python code for each BASIC statement type

### Control Flow Conversion Rules

| BASIC Pattern | Python Translation |
|----------------|-------------------|
| GOTO <num> | `state = "line_<num>"` followed by `continue` |
| IF cond THEN GOTO <num> | `if cond: state = "line_<num>"` followed by `continue` |
| FOR I=1 TO 10 | `I = 1` with increment check and NEXT handling |
| DATA n1,n2 | Define list constant |
| READ A,B | Index into DATA list |

### Variable Conversion Protocol

**C64 BASIC Variables → Python Identifiers:**

- `A` (float) → `A` (Python `float`)
- `X%` (integer) → `X_i` (Python `int`)
- `S$` (string) → `S_s` (Python `str`)

**Implementation**: After variable name, append suffix based on type (`_i` or `_s`).

### Statement-to-Python Mapping Table

**Core Statements:**
- `PRINT` → Python `print()`
- `LET` (implicit) → Python assignment `var = value`
- `IF ... THEN` → Python `if` with state transition
- `GOTO` → State assignment + `continue`
- `ELSE` (not supported) → Replace with separate `if/else` or conditional GOTO
- `DATA` → List constant definition
- `READ` → List indexing
- `FOR ... TO ... STEP` → Loop with counter
- `NEXT` → Loop increment and state transition
- `GOSUB` → State assignment with return tracking
- `RETURN` → State transition back to GOSUB destination
- `REM` → Comment (no `#` prefix)
- `:` → Sequential statement separator

**Function Calls:**
- `POKE` → Can be mapped to Python memory operations (future enhancement)
- `PEEK` → Can be mapped to Python memory accesses (future enhancement)
- `SYS` → Can be mapped to Python system calls (future enhancement)

### State Machine Structure

```python
def main():
    state = "init"

    while True:
        if state == "init":
            # Fall-through: All non-target lines execute here sequentially
            # Lines 10-60 combined into single state
            print("HELLO")
            A = 10
            B = 20
            if A == B:
                state = "line_70"
                continue
            state = "line_80"
            continue

        elif state == "line_70":
            # Target line: GOSUB destination
            print("A=B")
            state = "line_80"
            continue

        elif state == "line_80":
            # Target line: GOTO destination
            print("END")
            break

        else:
            raise Exception(f"Unknown state: {state}")
```

**Key Points:**
- Non-target lines execute in their first line's state handler
- Target lines get separate `elif` handlers
- State transitions use `continue` to loop back
- Break statement used for `END`

### Implementation Requirements

**CLI Interface:**
```bash
bas2py input.bas output.py [-v] [--no-include-header] [--pretty-structures]
```

- `input.bas`: UTF-8 encoded BASIC file
- `output.py`: Python source output file
- `-v/--verbose`: Verbose output during translation
- `--no-include-header`: Skip Python shebang and module docstring
- `--pretty-structures`: Add formatting for readability

**Output Format:** Must match `example1.py` pattern exactly.

## Testing Strategy

### Unit Testing

Each component should be tested separately:

1. **Parser Tests**:
   - Valid UTF-8 BASIC file parsing
   - Invalid line number handling
   - Missing line numbers
   - Malformed statements

2. **State Analyzer Tests**:
   - Target identification for GOTO, GOSUB, NEXT, RETURN
   - Fall-through chain detection
   - Edge cases (single line, unreachable lines)

3. **Python Generator Tests**:
   - Statement-to-Python conversion accuracy
   - Variable naming convention handling
   - Control flow translation correctness
   - State machine structure validation

### Integration Testing

Full end-to-end tests with known BASIC programs:

1. **Simple Programs**: Print statements, basic arithmetic
2. **Control Flow**: IF/THEN, GOTO, nested conditionals
3. **Loops**: FOR/NEXT with and without STEP
4. **Subroutines**: Multiple GOSUB calls, nested calls
5. **Lists**: DATA/READ operations
6. **Complex Cases**: Mixed structures, extensive line chains

### Validation Checklist

- [ ] Generated Python code is syntactically correct
- [ ] State variable names are unique and consistent
- [ ] All GOTO/GOSUB/NEXT/RETURN targets have dedicated handlers
- [ ] Non-target lines are properly fall-through
- [ ] Variable conversion follows C64 conventions (`%` → `_i`, `$` → `_s`)
- [ ] Logical flow matches original BASIC program
- [ ] No apostrophe REM usage (only `REM` keyword)
- [ ] No ELSE keyword (use conditional branching)

## Git Workflow

### Repository Setup

```bash
# Initialize git repository
git init

# Create initial commit including project files
git add FSP.md AGENTS.md petscii2text.py
git commit -s
```

### Commit Style

Follow Linux kernel conventions:

```
git commit -s -m "Short description

Detailed explanation as needed.

Signed-off-by: Yope Agent <agent@yope.corporation>"
```

**Commit Message Format:**
- First line: Short summary (50 chars max)
- Blank line
- Optional: Detailed description
- Last line: `Signed-off-by: [name] <email>`

### Conventional Commits

Recommended format:

- `feat:` New feature or tool functionality
- `fix:` Bug fix or issue resolution
- `docs:` Documentation updates
- `refactor:` Code restructuring without feature change
- `test:` Test additions or modifications
- `chore:` Maintenance or dependency updates

## Common Pitfalls to Avoid

1. **State Splitting**: Never create separate state handlers for lines that are not jump targets
2. **Variable Types**: Remember C64 variables are always floating-point unless marked `X%` or `X$`
3. **REM Abbreviation**: C64 BASIC only recognizes `REM`, not `'`
4. **ELSE Support**: Gotos for else branches must be explicit (no ELSE keyword)
5. **Fall-through**: Non-target lines must execute sequentially in starting state handler
6. **State Variables**: Always use `continue` after state assignment to prevent execution of multiple handlers for same state
7. **Spaces in Indentation**: ALWAYS use TAB characters, never spaces for indentation (PEP-8 exception)
8. **Trailing Whitespace**: Remove all trailing whitespace from code lines and empty lines
9. **Editor Config**: Configure source editors to display tabs as tabs, not expand to spaces

## Environment Setup

**Minimum Requirements:**
- Python 3.8+
- Git
- Test framework (pytest recommended)

**No Additional Setup Required:**
- All tools are pure Python
- No package installations
- No external dependencies

## Development Workflow

1. **Understand Requirements**: Read FSP.md thoroughly
2. **Design Components**: Break down into parser, analyzer, generator
3. **Implement Parser**: Read and parse BASIC file structure
4. **Build Analyzer**: Map line numbers to targets vs non-targets
5. **Develop Generator**: Create Python state machine code
6. **Test Component**: Write unit tests for each component
7. **Integration Test**: Validate with sample BASIC programs
8. **Review Spec Compliance**: Ensure generated code matches FSP requirements

## File Reference

- `FSP.md`: Complete functional specification
- `AGENTS.md`: This file - agent guidance
- `petscii2text.py`: Phase 1 converter (PRG → UTF-8)

## Additional Resources

For reference on:
- Commodore 64 BASIC syntax and limitations
- Python state machine patterns
- PetSCII to UTF-8 conversion
- C64 PRG file format specification

## Getting Help

When stuck:
1. Review FSP.md for specifications
2. Examine `example1.py` for expected output pattern
3. Check existing `petscii2text.py` for code style examples
4. Validate with integration test programs matching `example1.bas`

## Contact

For questions about the project scope or specifications:
- Review FSP.md lines 1-100 for overview
- Check implementation requirements section
- Refer to provided examples in FSP.md and test files
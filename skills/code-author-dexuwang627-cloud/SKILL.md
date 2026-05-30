---
name: code-author-dexuwang627-cloud
description: Produces Python code from task descriptions (max 500 S-LOC)
tags: [code-generation, python]
---

# Code Author Skill

## Purpose

Generate Python code that solves a given programming task description. The output must be self-contained, correct, and pass hidden test cases.

## Input

Task description in natural language. Examples:
- "Write a function that finds the longest palindrome substring in a given string."
- "Implement a function to merge two sorted lists into one sorted list."
- "Create a function that calculates the Nth Fibonacci number efficiently."

## Output

Python code that:
- Is self-contained (no external dependencies beyond Python standard library)
- Passes the hidden test cases
- Includes type hints
- Handles edge cases (None, empty, extreme values)
- Is ≤500 S-LOC (via radon raw)

## Code Generation Strategy

1. **Analyze**: Read the task description carefully. Identify:
   - Function signature (input types → output type)
   - Core algorithm needed
   - Edge cases to handle
   - Constraints (time/space)

2. **Design**: Choose the simplest correct approach:
   - Prefer standard library solutions
   - Use built-in data structures (dict, set, list)
   - Avoid premature optimization — clarity first

3. **Implement**: Write clean Python:
   - Start with function signature + type hints
   - Handle the happy path first
   - Add edge case guards
   - Keep it ≤500 S-LOC

4. **Verify**: Use `scripts/check.py` to validate:
   - Syntax correctness
   - No forbidden imports (subprocess, socket, requests, urllib, http, ftplib, smtplib)
   - No forbidden calls (eval, exec, __import__)
   - S-LOC within limit (≤500)

5. **Output**: Provide the code as a clean Python snippet.

## Constraints

- Python 3.11 compatible
- Max 500 S-LOC (via radon raw)
- No network access (no socket, requests, urllib, http, ftplib, smtplib)
- No subprocess calls
- 5s timeout, 512 MB memory
- No dynamic imports (__import__, importlib)
- No eval/exec

## Quality Rules

- All public functions must have type hints
- Handle None and empty inputs gracefully
- Return consistent types (don't mix None and value returns)
- Avoid deep recursion (may timeout) — prefer iteration
- Use descriptive variable names
- Add brief docstrings for complex functions
- Don't over-engineer: solve the stated problem, not hypothetical extensions

## Confidence Estimation

When generating code, assess confidence based on:
- **0.9-1.0**: Straightforward algorithm, clear input/output, well-known pattern
- **0.7-0.9**: Moderate complexity, multiple steps, but algorithm is standard
- **0.5-0.7**: Complex requirements, potential edge cases, or ambiguous task description
- **0.3-0.5**: Significant ambiguity in requirements, may need assumptions
- **0.0-0.3**: Cannot understand the task, output best attempt with noted limitations

## Checking Code Quality

```bash
# Validate code via stdin
echo '<code>' | python3 scripts/check.py

# Or via file
python3 scripts/check.py solution.py
```

The checker validates:
- Syntax correctness (ast.parse)
- No forbidden imports or calls
- S-LOC estimate (comments and docstrings excluded)

## Examples

### Example 1: Simple Function
**Input**: "Write a function `add(a: int, b: int) -> int` that returns the sum of two integers."

**Output**:
```python
def add(a: int, b: int) -> int:
    """Return the sum of two integers."""
    return a + b
```

### Example 2: Edge Case Handling
**Input**: "Write a function `find_max(lst: list[int]) -> int` that returns the maximum value in a list. Return -1 for empty lists."

**Output**:
```python
def find_max(lst: list[int]) -> int:
    """Return the maximum value in a list, or -1 if empty."""
    if not lst:
        return -1
    max_val = lst[0]
    for val in lst[1:]:
        if val > max_val:
            max_val = val
    return max_val
```

## Rules

- Output only Python code — no markdown fences, no explanations
- Code must be self-contained and runnable
- All calculations must be deterministic — no randomness unless the task requires it
- If the task is ambiguous, make reasonable assumptions and document them in a brief comment
- task_id must pass through from input (if provided)
- Confidence must be 0.0–1.0
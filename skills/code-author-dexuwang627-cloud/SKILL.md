---
name: code-author-dexuwang627-cloud
description: Produces Python code from task descriptions (max 500 S-LOC)
tags: [code-generation, python]
---

# Code Author Skill

## Purpose

Generate Python code that solves a given programming task description. The output must be self-contained, correct, and pass hidden test cases.

## Input

JSON payload with the following structure:

```json
{
  "task_id": "task_pair_001",
  "task_description": "Write a function that merges overlapping intervals...",
  "constraints": {
    "entry_function": "merge_intervals",
    "max_loc": 500,
    "imports_forbidden": ["os", "sys", "subprocess"]
  }
}
```

Fields:
- `task_id` (string, required): Must be passed through to output unchanged.
- `task_description` (string, required): Natural language description of the programming task.
- `constraints` (object, optional): Contains `entry_function` (function name), `max_loc` (S-LOC limit), and `imports_forbidden` (additional banned imports beyond the defaults).

## Output

A single fenced JSON block with this exact structure:

```json
{
  "task_id": "task_pair_001",
  "code": "def merge_intervals(intervals: list[list[int]]) -> list[list[int]]:\n    ...",
  "confidence": 0.9
}
```

The `code` field must contain self-contained Python code that:
- Is compatible with Python 3.11
- Has no external dependencies beyond Python standard library
- Includes type hints
- Handles edge cases (None, empty, extreme values)
- Is ≤500 S-LOC (measured by radon raw)
- Passes the test cases specified in the task

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
# Validate code from a file
python3 scripts/check.py solution.py

# Or validate directly by providing code as a string argument
# (the checker reads from a file path or stdin)
```

The checker validates:
- Syntax correctness (ast.parse)
- No forbidden imports or calls
- S-LOC estimate (comments and docstrings excluded)

## Examples

### Example 1: Simple Function
**Input**:
```json
{
  "task_id": "pair_001",
  "task_description": "Write a function add(a: int, b: int) -> int that returns the sum of two integers.",
  "constraints": {"entry_function": "add", "max_loc": 500, "imports_forbidden": []}
}
```

**Output**:
```json
{
  "task_id": "pair_001",
  "code": "def add(a: int, b: int) -> int:\n    \"\"\"Return the sum of two integers.\"\"\"\n    return a + b",
  "confidence": 0.95
}
```

### Example 2: Edge Case Handling
**Input**:
```json
{
  "task_id": "pair_002",
  "task_description": "Write a function find_max(lst: list[int]) -> int that returns the maximum value in a list. Return -1 for empty lists.",
  "constraints": {"entry_function": "find_max", "max_loc": 500, "imports_forbidden": []}
}
```

**Output**:
```json
{
  "task_id": "pair_002",
  "code": "def find_max(lst: list[int]) -> int:\n    \"\"\"Return the maximum value in a list, or -1 if empty.\"\"\"\n    if not lst:\n        return -1\n    max_val = lst[0]\n    for val in lst[1:]:\n        if val > max_val:\n            max_val = val\n    return max_val",
  "confidence": 0.9
}
```

### Example 3: Dictionary / String Manipulation
**Input**:
```json
{
  "task_id": "pair_003",
  "task_description": "Write a function word_count(text: str) -> dict[str, int] that counts occurrences of each word. Words are separated by whitespace. Case-insensitive.",
  "constraints": {"entry_function": "word_count", "max_loc": 500, "imports_forbidden": ["collections"]}
}
```

**Output**:
```json
{
  "task_id": "pair_003",
  "code": "def word_count(text: str) -> dict[str, int]:\n    \"\"\"Count occurrences of each word, case-insensitive.\"\"\"\n    if not text or not text.strip():\n        return {}\n    counts: dict[str, int] = {}\n    for word in text.lower().split():\n        counts[word] = counts.get(word, 0) + 1\n    return counts",
  "confidence": 0.90
}
```

### Example 4: Sorting with Key Function
**Input**:
```json
{
  "task_id": "pair_004",
  "task_description": "Write a function sort_by_length(strings: list[str]) -> list[str] that returns strings sorted by length ascending. Strings of equal length keep their original order.",
  "constraints": {"entry_function": "sort_by_length", "max_loc": 500, "imports_forbidden": []}
}
```

**Output**:
```json
{
  "task_id": "pair_004",
  "code": "def sort_by_length(strings: list[str]) -> list[str]:\n    \"\"\"Sort strings by length ascending; stable sort preserves original order for ties.\"\"\"\n    return sorted(strings, key=len)",
  "confidence": 0.95
}
```

### Example 5: Graph / BFS
**Input**:
```json
{
  "task_id": "pair_005",
  "task_description": "Write a function shortest_path(graph: dict[str, list[str]], start: str, end: str) -> list[str] that returns the shortest path (as a list of nodes) from start to end using BFS. Return empty list if no path exists.",
  "constraints": {"entry_function": "shortest_path", "max_loc": 500, "imports_forbidden": []}
}
```

**Output**:
```json
{
  "task_id": "pair_005",
  "code": "def shortest_path(graph: dict[str, list[str]], start: str, end: str) -> list[str]:\n    \"\"\"BFS shortest path from start to end. Returns empty list if unreachable.\"\"\"\n    if start == end:\n        return [start]\n    if start not in graph:\n        return []\n    visited: set[str] = {start}\n    queue: list[tuple[str, list[str]]] = [(start, [start])]\n    while queue:\n        node, path = queue.pop(0)\n        for neighbor in graph.get(node, []):\n            if neighbor == end:\n                return path + [neighbor]\n            if neighbor not in visited:\n                visited.add(neighbor)\n                queue.append((neighbor, path + [neighbor]))\n    return []",
  "confidence": 0.80
}
```

## Rules

- Output must be a single fenced JSON block containing `task_id`, `code`, and `confidence`
- `task_id` must pass through from input unchanged
- `code` must be self-contained Python — no markdown fences around the code itself, no explanations
- `confidence` must be 0.0–1.0
- All calculations must be deterministic — no randomness unless the task requires it
- If the task is ambiguous, make reasonable assumptions and document them in a brief comment within the code
- Keep the total response short: do not restate the task, do not explain the algorithm outside the code, and write the most concise correct implementation. Long responses risk output truncation and timeouts
- The final message must contain ONLY the fenced JSON block — no surrounding prose

## When to Use

Use this skill when the input is a programming task description asking for Python code generation. The task should specify a function or algorithm to implement. Do not use this skill for code review, debugging, or non-Python tasks.

## Procedure

1. Read the task description and identify the required function signature, input types, output type, and constraints.
2. Choose the simplest correct algorithm — prefer standard library, built-in data structures, and iterative solutions over recursion.
3. Write clean Python code with type hints, docstrings for complex functions, and edge case guards (None, empty, extreme values).
4. Run `python3 scripts/check.py` on the generated code to verify syntax, no forbidden imports/calls, and S-LOC ≤ 500. The `scripts/` path is relative to this skill's directory — if the terminal's working directory is elsewhere, locate this skill's directory first and run the script from there. If the script cannot be located after one attempt, perform the checks mentally (valid syntax, no forbidden imports, S-LOC ≤ 500) and proceed — do not spend turns searching.
5. Output a single fenced JSON block with `task_id`, `code` (the Python source), and `confidence`.

## Verification

After generating code, run `scripts/check.py <file>` to confirm:
- Syntax is valid Python (ast.parse succeeds).
- No forbidden imports (subprocess, socket, requests, urllib, http, ftplib, smtplib) or calls (eval, exec, __import__).
- S-LOC is within the 500-line limit.

If validation fails, revise the code and re-validate before outputting.
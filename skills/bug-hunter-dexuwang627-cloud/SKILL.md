---
name: bug-hunter-dexuwang627-cloud
description: AIASE 2026 Bug Hunter — probe-based crash + mismatch detection with AST smell analysis. Balanced precision/recall for pairwise evaluation.
version: 1.0.0
metadata:
  hermes:
    tags: [bug-hunter, aiase-2026]
    category: code
---

# Bug Hunter Skill

Find bugs in candidate Python code by combining deterministic probe testing with AST-level static analysis.

## Input

JSON payload with the following structure:

```json
{
  "task_id": "task_pair_001",
  "code": "def merge_intervals(intervals): ...",
  "task_description": "Merge overlapping intervals..."
}
```

Fields:
- `task_id` (string, required): Task identifier, passed through to output.
- `code` (string, required): Python source code to analyze.
- `task_description` (string, required): Natural language description of what the code should do.

## Output

The final result is written to the result file by `scripts/run.py`, not printed in the chat. The JSON object has this structure:

```json
{
  "task_id": "task_pair_001",
  "verdict": "buggy",
  "bugs": [
    {
      "line_start": 5,
      "line_end": 7,
      "severity": "high",
      "type": "logic_error",
      "description": "Off-by-one error in loop boundary causes last interval to be skipped.",
      "suggested_fix": "Change `range(len(intervals) - 1)` to `range(len(intervals))`."
    }
  ],
  "confidence": 0.85
}
```

- `verdict`: `"buggy"` if any bugs found, `"clean"` otherwise.
- `bugs`: Array of bug objects (max 5). Each has `line_start`, `line_end`, `severity` (low/medium/high), `type`, `description`, `suggested_fix`.
- `confidence`: 0.0–1.0 indicating how confident the analysis is.

### Bug `type` taxonomy (MANDATORY — use EXACTLY one of these four values)

| `type` | Use when |
|--------|----------|
| `edge_case` | Code fails on boundary/special inputs: empty list, empty string, zero, single element, all-equal values |
| `off_by_one` | Loop range, index, or comparison boundary is off by one (`<` vs `<=`, `len(x)-1`, skipped first/last element) |
| `unhandled_input` | An input form the spec allows is not handled: None, negative numbers, mixed types, malformed values |
| `logic_error` | Any other incorrect algorithm, condition, operator, or state handling that produces wrong results |

Never invent other type names (e.g. `index_error`, `crash`, `runtime_error` are NOT valid). A crash on empty input is `edge_case`; a crash on None input is `unhandled_input`. Grading matches bugs by exact `(line_start, type)` pairs, so a wrong type name scores zero even when the line is right.

## Bug Detection Strategy

This skill uses a **three-layer detection** approach:

### Layer 1: Probe Execution (deterministic)
1. Load reference test cases from `dev_set/pairwise/reference_tasks/{task_id}.json`.
2. Execute the candidate code against each test case with a timeout guard.
3. Record **crash lines** (traceback points to `<candidate>`) and **mismatch counts** (output ≠ expected).

### Layer 2: AST Static Analysis (deterministic)
Scan the AST for common defect patterns:
- Mutable default arguments (list/dict/set defaults that persist across calls)
- Bare `except:` clauses (swallow all exceptions)
- Use of `eval`/`exec` (unsafe with untrusted input)
- Unreachable code after `return`/`raise`/`break`/`continue`
- Redundant conditions (always True or always False)
- Missing return in branching paths (function can return None unexpectedly)

### Layer 3: LLM Reasoning (augmented by task description)
Use the `task_description` to reason about:
- Whether edge cases described in the task are properly handled
- Whether the algorithm aligns with the stated requirements
- Whether type hints match actual behavior

Layer 3 findings are **only reported when Layer 1 or Layer 2 provides supporting evidence** (crash, mismatch, or AST smell at a specific line). This prevents hallucinated bugs from reducing precision.

## Confidence Levels

- **0.8–1.0**: Crash confirmed at a specific line, or multiple mismatches with clear root cause.
- **0.6–0.8**: Mismatch found, root cause inferred but not pinpointed to exact line.
- **0.4–0.6**: AST smells detected but no runtime failures; bugs are plausible but unconfirmed.
- **0.2–0.4**: Task description suggests potential issues but no concrete evidence.

## Severity Classification

| Severity | When |
|----------|------|
| high | Crash on reference input, or wrong answer on core functionality |
| medium | Edge case failure, or mutable default that could cause intermittent bugs |
| low | Style smell (bare except), unreachable code, or cosmetic issue |

## Procedure

1. Parse the input JSON payload.
2. **Use the `terminal` tool (do not use process/background tools)** with the **absolute path** to run:

   ```
   python3 <skill_dir>/scripts/run.py '<payload>'
   ```

   where `<skill_dir>` is the directory Hermes reports when loading this skill. The script executes deterministic analysis (probe + AST) and atomically writes the final bug report to the result file (path from the environment variable `AIASE_RESULT_PATH`, falling back to `./aiase_result.json`).
3. The script handles Layers 1-2 deterministically. Layer 3 (LLM reasoning) is the Hermes agent's own judgment: review the deterministic results alongside the `task_description`, and if Layer 1 or 2 found concrete evidence, enrich descriptions and suggest fixes based on task context. **You do not need to output or repeat the JSON in the chat message.**
4. If no evidence from Layers 1-2, the script reports `verdict=clean` — do not fabricate bugs.

## Quality Rules

- **Never report a bug without line-level evidence** (crash traceback, AST node line, or mismatch).
- **Max 5 bugs** per report — prioritize by severity (high > medium > low).
- **Deduplicate**: same (line, type) pair only reported once.
- **Deterministic core**: `scripts/run.py` is the source of truth for crash/mismatch detection. LLM reasoning only enriches, never overrides.
- Code that cannot compile/exec reports a bug at line 1 with the compile error.
- The skill's final action is to execute `scripts/run.py`; do not print a fenced JSON block in the chat.

## Verification

After invoking `scripts/run.py`, verify:
- The result file exists and is valid JSON.
- `task_id` matches input.
- `verdict` is `"buggy"` or `"clean"`.
- Each bug has all required fields.
- No more than 5 bugs reported.
- Confidence is between 0.0 and 1.0.

## When to Use

`/bug-hunter-dexuwang627-cloud {"task_id":"task_pair_001", "code":"def merge_intervals(intervals): ...", "task_description":"Merge overlapping intervals..."}`.

Use this skill when the input contains Python code and a task description asking for bug detection. The skill analyzes the code for correctness bugs, edge case failures, and common Python pitfalls.
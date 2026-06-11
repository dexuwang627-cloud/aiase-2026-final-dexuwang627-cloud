# BEHAVIOR — bug-hunter-dexuwang627-cloud

## Role in grading

A **balanced-precision/recall** opponent for Pairwise evaluation. Finds real bugs via probe execution and AST analysis, while avoiding false positives from speculative LLM reasoning.

## What it tests on the receiving side

When paired against a student **Code Author**:
- A bug report with `severity=high` is strong evidence the code is wrong.
- A `verdict=clean` means no crashes or mismatches were found on reference test cases — but does not guarantee the code is fully correct (no hidden test coverage).
- `severity=medium` or `low` bugs may be real edge cases or stylistic issues; the evaluator should weigh confidence.

## Why this approach

Three-layer detection balances precision and recall:

1. **Probe execution** is ground truth — crashes and mismatches are undeniable evidence.
2. **AST analysis** catches structural defects that may not surface on specific test inputs but are still real bugs (mutable defaults, bare except, unreachable code).
3. **LLM reasoning** enriches descriptions and fixes based on the task description, but is **constrained** — it only augments bugs found by Layers 1-2, never invents bugs from scratch.

This avoids the two extremes:
- **Conservative-only**: misses bugs that don't crash on reference inputs.
- **Aggressive-only**: reports too many false positives from speculative analysis.

## Deterministic core

`scripts/run.py` is the authoritative detector. Its JSON output contains:
- `crash_lines`: lines where reference test cases caused crashes.
- `mismatches`: count of reference test cases returning wrong values.
- `ast_smells`: structural code defects found by AST inspection.

The LLM reads this output and produces the final report, adding richer descriptions and fix suggestions, but **never adding bugs not supported by the evidence**.
#!/usr/bin/env python3
"""bug-hunter-dexuwang627-cloud — balanced probe + AST-smell bug reporter."""

from __future__ import annotations

import ast
import json
import signal
import sys
import traceback
from contextlib import contextmanager
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TASK_DIR = REPO_ROOT / "dev_set" / "pairwise" / "reference_tasks"

MAX_BUGS = 5


class _Timeout(Exception):
    pass


@contextmanager
def _time_limit(sec: float):
    if not hasattr(signal, "SIGALRM"):
        yield
        return

    def _h(s, f):
        raise _Timeout("probe timed out")

    old = signal.signal(signal.SIGALRM, _h)
    signal.setitimer(signal.ITIMER_REAL, sec)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


def _load_task(task_id: str) -> dict | None:
    p = TASK_DIR / f"{task_id}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _run_probes(code: str, entry: str, test_cases: list[dict], timeout: float = 1.0) -> tuple[list[int], int]:
    """Run test cases against candidate code. Returns (crash_lines, mismatch_count)."""
    ns: dict = {}
    crash_lines: list[int] = []

    # Try to compile and exec the code
    try:
        exec(compile(code, "<candidate>", "exec"), ns)
    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)
        for f in tb:
            if f.filename == "<candidate>" and f.lineno:
                return [f.lineno], 0
        return [1], 0

    fn = ns.get(entry)
    if not callable(fn):
        return [1], 0

    mismatch_count = 0
    for tc in test_cases:
        args = tc.get("input", [])
        expected = tc.get("expected")
        try:
            with _time_limit(timeout):
                got = fn(*args) if isinstance(args, list) else fn(args)
        except _Timeout:
            crash_lines.append(1)
            continue
        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            found_line = False
            for f in tb:
                if f.filename == "<candidate>" and f.lineno:
                    crash_lines.append(f.lineno)
                    found_line = True
                    break
            if not found_line:
                crash_lines.append(1)
            continue
        if got != expected:
            mismatch_count += 1

    return crash_lines, mismatch_count


def _ast_smells(code: str, entry: str) -> list[dict]:
    """AST-based static analysis for common Python defects."""
    bugs: list[dict] = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return bugs

    # Collect function def lines for the entry function
    entry_def_line = -1
    all_return_lines: set[int] = set()
    all_branch_lines: set[int] = set()

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == entry:
                entry_def_line = node.lineno
                # Check for missing final return (potential implicit None)
                _check_missing_return_at_end(node, bugs)
            # Check for mutable default arguments
            for d in node.args.defaults:
                if isinstance(d, (ast.List, ast.Dict, ast.Set)):
                    bugs.append({
                        "line_start": d.lineno,
                        "line_end": d.lineno,
                        "severity": "medium",
                        "type": "api_misuse",
                        "description": "Mutable default argument persists state across calls.",
                        "suggested_fix": "Use None default and create the container inside the function.",
                    })

        elif isinstance(node, ast.ExceptHandler) and node.type is None:
            bugs.append({
                "line_start": node.lineno,
                "line_end": node.lineno,
                "severity": "low",
                "type": "unhandled_input",
                "description": "Bare `except:` swallows all exceptions including KeyboardInterrupt and SystemExit.",
                "suggested_fix": "Catch a specific exception type (e.g., `except ValueError:`).",
            })

        elif isinstance(node, ast.Call):
            f = node.func
            name = ""
            if isinstance(f, ast.Name):
                name = f.id
            elif isinstance(f, ast.Attribute):
                name = f.attr
            if name in ("eval", "exec"):
                bugs.append({
                    "line_start": node.lineno,
                    "line_end": node.lineno,
                    "severity": "high",
                    "type": "api_misuse",
                    "description": f"Use of `{name}` is unsafe and forbidden.",
                    "suggested_fix": "Replace with a safe parser or explicit dispatch.",
                })

        elif isinstance(node, ast.BoolOp):
            # Check for always-true/false conditions
            _check_redundant_boolop(node, bugs)

    # Check for unreachable code after return/raise/break/continue
    _check_unreachable(tree, bugs)

    return bugs


def _check_missing_return_at_end(func_node: ast.FunctionDef | ast.AsyncFunctionDef, bugs: list[dict]) -> None:
    """Check if a function with early returns lacks a final return statement.

    Only flags when:
    - The function has at least one explicit `return <value>` (not bare `return`)
    - The last statement in the function body is NOT a return statement
    - The function does NOT end with a for/while loop that might contain the return

    This avoids false positives on functions that return from all paths via
    early returns + a final return statement, or functions with no returns at all.
    """
    has_value_return = False
    for node in ast.walk(func_node):
        if isinstance(node, ast.Return) and node.value is not None:
            has_value_return = True
            break

    if not has_value_return:
        return

    # Check if function body ends with a return
    last_stmt = func_node.body[-1] if func_node.body else None
    if isinstance(last_stmt, ast.Return):
        return  # Final return exists, all good

    # If last statement is a for/while/with, the return might be inside it — skip
    if isinstance(last_stmt, (ast.For, ast.While, ast.With, ast.AsyncWith, ast.If, ast.Try)):
        return

    # Has value returns but no final return — potential implicit None
    bugs.append({
        "line_start": func_node.lineno,
        "line_end": func_node.lineno,
        "severity": "medium",
        "type": "logic_error",
        "description": f"Function `{func_node.name}` has early returns but no final return statement; may implicitly return None.",
        "suggested_fix": "Add a return statement at the end of the function, or ensure all paths return a value.",
    })


def _check_redundant_boolop(node: ast.BoolOp, bugs: list[dict]) -> None:
    """Check for redundant boolean operations."""
    # Simple check: `x or x`, `x and x`
    values = node.values
    if len(values) == 2:
        left_str = ast.dump(values[0])
        right_str = ast.dump(values[1])
        if left_str == right_str:
            bugs.append({
                "line_start": node.lineno,
                "line_end": node.lineno,
                "severity": "low",
                "type": "logic_error",
                "description": "Redundant boolean expression: both sides are identical.",
                "suggested_fix": "Remove the redundant side of the boolean expression.",
            })


def _check_unreachable(tree: ast.AST, bugs: list[dict]) -> None:
    """Check for unreachable code after return/raise/break/continue in the same block."""
    TERMINATORS = (ast.Return, ast.Raise, ast.Break, ast.Continue)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.For, ast.While, ast.If, ast.Try)):
            body = getattr(node, 'body', [])
            for i, stmt in enumerate(body):
                if isinstance(stmt, TERMINATORS) and i < len(body) - 1:
                    next_stmt = body[i + 1]
                    # Skip if it's an else clause or nested block
                    if not isinstance(next_stmt, (ast.If, ast.For, ast.While, ast.Try, ast.With, ast.AsyncWith)):
                        bugs.append({
                            "line_start": next_stmt.lineno,
                            "line_end": next_stmt.lineno,
                            "severity": "low",
                            "type": "logic_error",
                            "description": "Unreachable code after return/raise/break/continue.",
                            "suggested_fix": "Remove the unreachable code or restructure the control flow.",
                        })


def emit(obj: dict) -> int:
    sys.stdout.write("```json\n")
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, indent=2))
    sys.stdout.write("\n```\n")
    return 0


def main(argv: list[str]) -> int:
    raw = argv[1] if len(argv) > 1 else "{}"
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError
    except (json.JSONDecodeError, ValueError):
        payload = {}

    task_id = str(payload.get("task_id", ""))
    code = str(payload.get("code", ""))
    task_description = str(payload.get("task_description", ""))

    # Load reference task data
    task = _load_task(task_id)
    if task is None or not code:
        return emit({
            "task_id": task_id,
            "verdict": "clean",
            "bugs": [],
            "confidence": 0.5,
        })

    entry = task["constraints"]["entry_function"]
    test_cases = task.get("test_cases", [])

    # Layer 1: Probe execution
    crash_lines, mismatches = _run_probes(code, entry, test_cases)

    # Layer 2: AST analysis
    ast_bugs = _ast_smells(code, entry)

    # Build bug list
    bugs: list[dict] = []

    # Crash lines (highest priority)
    for ln in sorted(set(crash_lines)):
        bugs.append({
            "line_start": ln,
            "line_end": ln,
            "severity": "high",
            "type": "edge_case",
            "description": f"A reference test case crashed at line {ln}; unhandled edge condition.",
            "suggested_fix": "Add explicit guards for empty input / boundary values; verify against the task's edge spec.",
        })

    # Mismatches (high priority)
    if mismatches > 0:
        # Find entry function line for pinpointing
        entry_line = 1
        try:
            for n in ast.walk(ast.parse(code)):
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == entry:
                    entry_line = n.lineno
                    break
        except SyntaxError:
            pass
        bugs.append({
            "line_start": entry_line,
            "line_end": entry_line,
            "severity": "high",
            "type": "logic_error",
            "description": f"{mismatches} reference test case(s) returned wrong values; algorithm likely off.",
            "suggested_fix": "Re-derive the algorithm; verify against the task spec and sample tests.",
        })

    # AST smells (medium/low priority)
    bugs.extend(ast_bugs)

    # Deduplicate by (line_start, type)
    seen: set[tuple[int, str]] = set()
    unique: list[dict] = []
    for b in bugs:
        key = (b["line_start"], b["type"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(b)
    bugs = unique[:MAX_BUGS]

    # Determine verdict and confidence
    if not bugs:
        return emit({
            "task_id": task_id,
            "verdict": "clean",
            "bugs": [],
            "confidence": 0.8,
        })

    # Confidence based on evidence strength
    has_crash = bool(crash_lines)
    has_mismatch = mismatches > 0
    has_smell = len(ast_bugs) > 0

    if has_crash:
        confidence = 0.9
    elif has_mismatch:
        confidence = 0.85
    elif has_smell:
        confidence = 0.65
    else:
        confidence = 0.5

    return emit({
        "task_id": task_id,
        "verdict": "buggy",
        "bugs": bugs,
        "confidence": confidence,
    })


if __name__ == "__main__":
    sys.exit(main(sys.argv))
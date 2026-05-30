#!/usr/bin/env python3
"""Code quality checker for Code Author skill."""
import ast
import json
import sys
from pathlib import Path

FORBIDDEN_IMPORTS = ['subprocess', 'socket', 'requests', 'urllib', 'http', 'ftplib', 'smtplib']
FORBIDDEN_CALLS = ['eval', 'exec', '__import__']


def check_syntax(code: str) -> dict:
    """Check Python syntax."""
    try:
        ast.parse(code)
        return {"valid": True, "errors": []}
    except SyntaxError as e:
        return {"valid": False, "errors": [f"SyntaxError: line {e.lineno}: {e.msg}"]}


def check_forbidden(code: str) -> dict:
    """Check for forbidden imports and calls."""
    issues = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {"issues": ["Cannot parse code"], "clean": False}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_module = alias.name.split('.')[0]
                if root_module in FORBIDDEN_IMPORTS:
                    issues.append(f"Forbidden import: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split('.')[0] in FORBIDDEN_IMPORTS:
                issues.append(f"Forbidden import from: {node.module}")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in FORBIDDEN_CALLS:
                    issues.append(f"Forbidden call: {node.func.id}()")
    return {"issues": issues, "clean": len(issues) == 0}


def estimate_sloc(code: str) -> int:
    """Estimate S-LOC (source lines of code, excluding comments, docstrings, and blank lines)."""
    lines = code.split('\n')
    sloc = 0
    in_docstring = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Toggle docstring state
        if '"""' in stripped or "'''" in stripped:
            count = stripped.count('"""') + stripped.count("'''")
            if count == 1:
                in_docstring = not in_docstring
                continue
            # Opening and closing on same line — skip line
            continue
        if in_docstring:
            continue
        if stripped.startswith('#'):
            continue
        sloc += 1
    return sloc


def check_code(code: str) -> dict:
    """Run all checks on code."""
    syntax = check_syntax(code)
    if not syntax["valid"]:
        return {"valid": False, "syntax": syntax, "sloc": None, "sloc_within_limit": None, "forbidden": None}

    forbidden = check_forbidden(code)
    sloc = estimate_sloc(code)

    return {
        "valid": syntax["valid"] and forbidden["clean"],
        "syntax": syntax,
        "sloc": sloc,
        "sloc_within_limit": sloc <= 500,
        "forbidden": forbidden
    }


if __name__ == "__main__":
    if len(sys.argv) > 1:
        code = Path(sys.argv[1]).read_text()
    else:
        code = sys.stdin.read()

    result = check_code(code)
    print(json.dumps(result, ensure_ascii=False, indent=2))
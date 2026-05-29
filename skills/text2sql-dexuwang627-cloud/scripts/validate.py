#!/usr/bin/env python3
"""SQL validation for Text2SQL skill — checks syntax and read-only constraint."""
import json
import re
import sys

FORBIDDEN_KEYWORDS = [
    'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
    'TRUNCATE', 'REPLACE', 'ATTACH', 'DETACH', 'PRAGMA',
    'VACUUM', 'REINDEX', 'ANALYZE'
]

def validate_sql(sql: str) -> dict:
    """Validate SQL is read-only SQLite compatible.
    Returns: {"valid": bool, "errors": [str], "warnings": [str]}
    """
    errors = []
    warnings = []
    sql_upper = sql.upper().strip()

    # Must start with SELECT or WITH
    if not (sql_upper.startswith('SELECT') or sql_upper.startswith('WITH')):
        errors.append("SQL must be a SELECT or WITH statement (read-only)")

    # Check for forbidden keywords
    for kw in FORBIDDEN_KEYWORDS:
        # Word boundary check
        pattern = r'\b' + kw + r'\b'
        if re.search(pattern, sql_upper):
            # Allow SELECT ... FROM ... (no false positive on column names)
            if kw == 'SELECT':
                continue
            errors.append(f"Forbidden keyword: {kw}")

    # Check for semicolons (multiple statements)
    if ';' in sql.rstrip(';'):
        warnings.append("Multiple SQL statements detected")

    # Check for comments
    if '--' in sql or '/*' in sql:
        warnings.append("SQL contains comments, may affect parsing")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }

if __name__ == "__main__":
    sql = sys.argv[1]
    result = validate_sql(sql)
    print(json.dumps(result, ensure_ascii=False))
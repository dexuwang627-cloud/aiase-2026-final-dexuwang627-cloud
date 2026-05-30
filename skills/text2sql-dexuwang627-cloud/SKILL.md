---
name: text2sql-dexuwang627-cloud
description: Converts natural-language questions + SQLite DDL into verified SQL queries
tags: [text2sql, sql, database]
---

# Text2SQL Skill

## Purpose

Convert a natural-language question and a SQLite database schema (DDL) into a verified, read-only SQL query. The skill analyzes the schema, maps the question intent to the correct tables and columns, generates SQL, and validates it against read-only and syntax constraints.

## Input Schema

```json
{
  "task_id": "string — unique identifier for the task",
  "question": "string — natural-language question about the data",
  "db_schema": "string — SQLite DDL (CREATE TABLE statements defining tables, columns, types, constraints)",
  "dialect": "string — always \"sqlite\""
}
```

### Input Example

```json
{
  "task_id": "dev_001",
  "question": "How many customers have placed more than 5 orders?",
  "db_schema": "CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, email TEXT); CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, total REAL, order_date TEXT);",
  "dialect": "sqlite"
}
```

## Output Schema

```json
{
  "task_id": "string — same as input task_id",
  "sql": "string — read-only SQLite SELECT statement",
  "rationale": "string — step-by-step reasoning explaining how the question maps to the generated SQL",
  "confidence": "float — 0.0 to 1.0, estimated likelihood the SQL is correct"
}
```

### Output Example

```json
{
  "task_id": "dev_001",
  "sql": "SELECT COUNT(*) FROM customers WHERE id IN (SELECT customer_id FROM orders GROUP BY customer_id HAVING COUNT(*) > 5)",
  "rationale": "The question asks for a count of customers with more than 5 orders. customers table links to orders via customer_id. Subquery groups orders by customer_id, filters with HAVING COUNT(*) > 5, and the outer query counts matching customers.",
  "confidence": 0.9
}
```

## SQL Generation Rules

1. **Read-only only**: SQL must start with `SELECT` or `WITH`. No DDL (CREATE, ALTER, DROP) or DML (INSERT, UPDATE, DELETE) statements.
2. **SQLite syntax**: Use SQLite-compatible functions and syntax only. No database-specific extensions from other engines.
3. **Forbidden keywords**: INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, TRUNCATE, REPLACE, ATTACH, DETACH, PRAGMA, VACUUM, REINDEX, ANALYZE.
4. **Aggregation**: When the question asks "how many", "count", "total", "average", "maximum", "minimum", use appropriate aggregate functions (COUNT, SUM, AVG, MAX, MIN) with GROUP BY where needed.
5. **NULL handling**: Use `IS NULL` / `IS NOT NULL` for NULL comparisons. Never use `= NULL` or `!= NULL`.
6. **No multiple statements**: Output a single SQL statement. No semicolons separating multiple queries.
7. **No comments**: Avoid `--` or `/* */` comments in SQL output.
8. **Quoting**: Use double quotes for identifiers if needed, single quotes for string literals.

## Prompt Engineering Strategy

1. **Analyze db_schema**: Parse CREATE TABLE statements to identify tables, columns, data types, primary keys, and foreign keys. Understand table relationships.
2. **Parse question intent**: Classify the question as lookup (single row), aggregation (count/sum/avg), comparison, ranking, or join-based.
3. **Map to schema**: Identify which tables and columns the question refers to. Resolve ambiguous column names by using table prefixes. Match natural-language terms to column names (e.g., "how many" → COUNT, "total sales" → SUM(total)).
4. **Generate SQL**: Compose the query with proper JOINs, WHERE clauses, GROUP BY, HAVING, and ORDER BY as needed. Prefer explicit JOIN syntax over implicit comma-joins.
5. **Validate**: Run `scripts/validate_sql.py` on the generated SQL to check it is read-only and syntactically sound. If validation fails, revise and re-validate.
   ```bash
   python3 scripts/validate_sql.py '{"schema_ddl":"CREATE TABLE ...", "sql":"SELECT ..."}'
   ```
   This validates both keyword restrictions AND schema compatibility (runs EXPLAIN against the provided DDL).

## Confidence Estimation

| Scenario | Confidence Range |
|----------|-----------------|
| Direct column mapping, simple WHERE, no joins | 0.9 – 1.0 |
| Requires JOIN across 2 tables, clear foreign keys | 0.7 – 0.9 |
| Aggregation with GROUP BY / HAVING | 0.6 – 0.8 |
| Ambiguous column names or unclear intent | 0.4 – 0.6 |
| Multiple JOINs, nested subqueries, or ambiguous schema | 0.3 – 0.5 |
| Cannot confidently map question to schema | 0.1 – 0.3 |

Lower confidence when: ambiguous column names across tables, question uses terms not in schema, complex nested logic required.

## More Examples

### Example 2: Simple Lookup

**Input:**
```json
{
  "task_id": "dev_002",
  "question": "What are the names of all employees in the Engineering department?",
  "db_schema": "CREATE TABLE employees (id INTEGER PRIMARY KEY, name TEXT, department TEXT, salary REAL);",
  "dialect": "sqlite"
}
```

**Output:**
```json
{
  "task_id": "dev_002",
  "sql": "SELECT name FROM employees WHERE department = 'Engineering'",
  "rationale": "Direct column filter: name and department are both in employees table. WHERE clause filters for Engineering department.",
  "confidence": 0.95
}
```

### Example 3: Aggregation with Join

**Input:**
```json
{
  "task_id": "dev_003",
  "question": "List the department names and their average salary, ordered by average salary descending",
  "db_schema": "CREATE TABLE departments (id INTEGER PRIMARY KEY, name TEXT); CREATE TABLE employees (id INTEGER PRIMARY KEY, name TEXT, department_id INTEGER, salary REAL);",
  "dialect": "sqlite"
}
```

**Output:**
```json
{
  "task_id": "dev_003",
  "sql": "SELECT d.name AS department, AVG(e.salary) AS avg_salary FROM departments d JOIN employees e ON d.id = e.department_id GROUP BY d.name ORDER BY avg_salary DESC",
  "rationale": "Join departments and employees on department_id. GROUP BY department name, compute AVG(salary), order descending.",
  "confidence": 0.85
}
```

## Error Handling

| Condition | Action |
|-----------|--------|
| Question cannot be mapped to any table/column | Return SQL as a comment-free placeholder SELECT NULL with confidence 0.0 and rationale explaining the mapping failure |
| Schema is empty or malformed | Return confidence 0.0, rationale noting schema issue |
| Generated SQL fails validate_sql.py | Revise SQL and re-validate; if still failing after 2 attempts, return the best attempt with reduced confidence |
| Ambiguous question (multiple valid interpretations) | Pick the most likely interpretation, document alternatives in rationale, lower confidence |

## When to Use

Use this skill when the input contains a natural-language question about data and a SQLite database schema (DDL). The question should ask about data retrieval, aggregation, or filtering — any task that maps to a SELECT query. Do not use this skill for data modification, schema creation, or tasks that do not involve SQL.

## Procedure

1. Parse the `db_schema` field to identify tables, columns, primary keys, and foreign key relationships.
2. Analyze the `question` to determine the query intent: lookup, aggregation, comparison, ranking, or join.
3. Map question terms to schema elements (table names, column names, relationships).
4. Generate a read-only SQLite SELECT or WITH statement that answers the question.
5. Validate the generated SQL using `scripts/validate_sql.py` to ensure it is read-only, syntactically sound, and compatible with the provided schema.
6. Output a single fenced JSON block with `task_id`, `sql`, `rationale`, and `confidence`.

## Verification

After generating SQL, run `scripts/validate_sql.py` to confirm:
- The SQL starts with SELECT or WITH (no DDL/DML).
- No forbidden keywords (INSERT, UPDATE, DELETE, DROP, etc.) appear anywhere in the SQL.
- The SQL is a single statement (no semicolons separating multiple queries).

If validation fails, revise the SQL and re-validate before outputting.
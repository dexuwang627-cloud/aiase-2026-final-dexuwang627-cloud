---
name: text2sql-dexuwang627-cloud
description: Converts natural-language questions + SQLite DDL into verified SQL queries
tags: [text2sql, sql, database]
---

# Text2SQL Skill

## Purpose
Convert natural-language question + SQLite DDL into a read-only SQL query.

## Input
- task_id: string
- question: string (natural language question)
- db_schema: string (SQLite DDL)
- dialect: string (always "sqlite")

## Output
JSON with: task_id, sql, rationale, confidence

## Rules
- SQL must be read-only (SELECT only), no DDL/DML
- Confidence must be 0.0-1.0
- Output must be a single fenced JSON block
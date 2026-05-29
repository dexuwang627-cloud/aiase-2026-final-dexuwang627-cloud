---
name: code-author-dexuwang627-cloud
description: Produces Python code from task descriptions (max 500 S-LOC)
tags: [code-generation, python]
---

# Code Author Skill

## Purpose
Generate Python code that solves a given programming task.

## Input
- task description (natural language)

## Output
Python code that passes hidden test cases.

## Constraints
- Python 3.11 compatible
- Max 500 S-LOC (via radon raw)
- No network, no subprocess
- 5s timeout, 512 MB memory

## Rules
- Code must be self-contained
- Handle edge cases explicitly
- Include type hints
#!/usr/bin/env python3
"""Local dev set evaluation for Text2SQL skill.

Creates in-memory SQLite DBs from db_schema + test_data, runs predicted and
ground-truth SQL, compares results via order-insensitive bag equality (multiset).

Usage:
    python3 run_dev.py                             # evaluate all dev_set JSON
    python3 run_dev.py --skill text2sql-dexuwang627-cloud  # specify skill
"""
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

DEV_SET = Path("dev_set")


def bag_equal(rows_a: list[tuple], rows_b: list[tuple]) -> bool:
    """Order-insensitive bag (multiset) equality."""
    return Counter(rows_a) == Counter(rows_b)


def create_db(db_schema: str, test_data: list[str]) -> sqlite3.Connection:
    """Create in-memory SQLite DB from DDL + INSERT statements."""
    conn = sqlite3.Connection(":memory:")
    cursor = conn.cursor()
    # Execute schema
    for stmt in db_schema.split(";"):
        stmt = stmt.strip()
        if stmt:
            cursor.execute(stmt)
    # Execute test data inserts
    for insert_stmt in test_data:
        insert_stmt = insert_stmt.strip()
        if insert_stmt:
            cursor.execute(insert_stmt)
    conn.commit()
    return conn


def evaluate_task(task: dict, predicted_sql: str) -> dict:
    """Evaluate a single task: run predicted vs ground_truth on same DB."""
    task_id = task["task_id"]
    ground_truth = task["ground_truth_sql"]
    db_schema = task["db_schema"]
    test_data = task.get("test_data", [])

    conn = create_db(db_schema, test_data)
    cursor = conn.cursor()

    result = {
        "task_id": task_id,
        "predicted_sql": predicted_sql,
        "ground_truth_sql": ground_truth,
        "passed": False,
        "error": None,
    }

    try:
        cursor.execute(predicted_sql)
        predicted_rows = [tuple(row) for row in cursor.fetchall()]
    except Exception as e:
        result["error"] = f"predicted SQL error: {e}"
        conn.close()
        return result

    try:
        cursor.execute(ground_truth)
        gt_rows = [tuple(row) for row in cursor.fetchall()]
    except Exception as e:
        result["error"] = f"ground truth SQL error: {e}"
        conn.close()
        return result

    conn.close()
    result["passed"] = bag_equal(predicted_rows, gt_rows)
    return result


def load_skill_predictions(skill_name: str) -> dict[str, str]:
    """Load predictions from skill output file if it exists.

    Looks for skills/{skill_name}/predictions.json
    Falls back to generating predictions via the skill's SKILL.md prompt.
    """
    pred_path = Path("skills") / skill_name / "predictions.json"
    if pred_path.exists():
        with open(pred_path) as f:
            data = json.load(f)
        return {item["task_id"]: item["sql"] for item in data}
    return {}


def generate_predictions_from_skill(skill_name: str, tasks: list[dict]) -> dict[str, str]:
    """Generate predictions by reading SKILL.md and constructing prompts.

    This is a simulation — in production, an LLM reads SKILL.md and generates SQL.
    For local dev testing, we provide reasonable SQL based on the ground truth
    with slight variations to test the evaluator.
    """
    predictions = {}
    skill_md = Path("skills") / skill_name / "SKILL.md"
    if not skill_md.exists():
        print(f"Warning: {skill_md} not found, cannot generate predictions")
        return predictions

    for task in tasks:
        # Use ground truth as prediction for baseline testing
        # In real evaluation, this would be replaced by LLM output
        predictions[task["task_id"]] = task["ground_truth_sql"]

    return predictions


def main():
    skill_name = "text2sql-dexuwang627-cloud"
    if "--skill" in sys.argv:
        idx = sys.argv.index("--skill")
        if idx + 1 < len(sys.argv):
            skill_name = sys.argv[idx + 1]

    # Load all dev set JSON files
    all_tasks = []
    for json_file in sorted(DEV_SET.glob("*.json")):
        with open(json_file) as f:
            tasks = json.load(f)
        all_tasks.extend(tasks)

    if not all_tasks:
        print("No dev set tasks found in dev_set/")
        sys.exit(1)

    print(f"Loaded {len(all_tasks)} tasks from dev_set/")
    print(f"Skill: {skill_name}")
    print()

    # Load or generate predictions
    predictions = load_skill_predictions(skill_name)
    if not predictions:
        print("No predictions.json found — using ground truth as predictions (baseline test)")
        predictions = generate_predictions_from_skill(skill_name, all_tasks)

    # Evaluate each task
    passed = 0
    failed = 0
    errors = 0
    for task in all_tasks:
        task_id = task["task_id"]
        predicted_sql = predictions.get(task_id, "")
        if not predicted_sql:
            print(f"  {task_id}: SKIP (no prediction)")
            failed += 1
            continue

        result = evaluate_task(task, predicted_sql)
        status = "PASS" if result["passed"] else "FAIL"
        if result["error"]:
            status = "ERROR"
            errors += 1
        elif result["passed"]:
            passed += 1
        else:
            failed += 1

        print(f"  {task_id}: {status}")
        if result["error"]:
            print(f"         {result['error']}")

    total = len(all_tasks)
    pass_rate = (passed / total * 100) if total > 0 else 0
    score = (passed / total * 30) if total > 0 else 0

    print()
    print(f"Results: {passed}/{total} passed, {failed} failed, {errors} errors")
    print(f"Pass rate: {pass_rate:.1f}%")
    print(f"Score: {score:.1f} / 30")


if __name__ == "__main__":
    main()
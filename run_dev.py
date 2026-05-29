#!/usr/bin/env python3
"""Local batch testing script for AIASE 2026 Final Project."""
import json
import subprocess
import sys
from pathlib import Path

DEV_SET = Path("dev_set")


def run_skill(skill_name: str, input_data: dict) -> dict:
    """Run a skill and parse its JSON output."""
    # Implementation placeholder
    pass


def evaluate_text2sql(prediction: dict, ground_truth: dict) -> bool:
    """Order-insensitive bag equality for SQL results."""
    pass


def main():
    print("Running dev set evaluation...")
    # TODO: implement


if __name__ == "__main__":
    main()
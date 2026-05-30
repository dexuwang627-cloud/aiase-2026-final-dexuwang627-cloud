#!/usr/bin/env python3
"""Deterministic evaluator for carbon calculator skill.

Usage:
    python evaluator.py <output_json> <scenario_number>
    python evaluator.py '{"total_kg_co2e": 10188.8, ...}' 1
"""
import json
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from calculate import calc_electricity, calc_fuel, calc_refrigerant, calc_combined, load_factors

TOLERANCE = 0.05  # 5% tolerance for numeric comparisons


def approx_equal(a: float, b: float, tolerance: float = TOLERANCE) -> bool:
    """Check if two values are approximately equal within tolerance."""
    if a == 0 and b == 0:
        return True
    if a == 0 or b == 0:
        return False
    return abs(a - b) / max(abs(a), abs(b)) <= tolerance


def evaluate_scenario_1(output: dict, ground_truth: dict) -> dict:
    """Evaluate office combined emission (Scope 1+2)."""
    checks = []
    # Total
    if "total_kg_co2e" in output and "total_kg_co2e" in ground_truth:
        total_match = approx_equal(output["total_kg_co2e"], ground_truth["total_kg_co2e"])
        checks.append({"check": "total", "pass": total_match,
                        "output": output.get("total_kg_co2e"),
                        "expected": ground_truth.get("total_kg_co2e")})
    # Scope 1
    if "scope1_kg_co2e" in output and "scope1_kg_co2e" in ground_truth:
        s1_match = approx_equal(output["scope1_kg_co2e"], ground_truth["scope1_kg_co2e"])
        checks.append({"check": "scope1", "pass": s1_match,
                        "output": output.get("scope1_kg_co2e"),
                        "expected": ground_truth.get("scope1_kg_co2e")})
    # Scope 2
    if "scope2_kg_co2e" in output and "scope2_kg_co2e" in ground_truth:
        s2_match = approx_equal(output["scope2_kg_co2e"], ground_truth["scope2_kg_co2e"])
        checks.append({"check": "scope2", "pass": s2_match,
                        "output": output.get("scope2_kg_co2e"),
                        "expected": ground_truth.get("scope2_kg_co2e")})

    passed = sum(1 for c in checks if c["pass"])
    return {"scenario": "office_combined", "checks": checks,
            "passed": passed, "total": len(checks),
            "score": passed / len(checks) if checks else 0}


def evaluate_scenario_2(output: dict, ground_truth: dict) -> dict:
    """Evaluate multi-fuel calculation."""
    checks = []
    # Total
    if "total_kg_co2e" in output and "total_kg_co2e" in ground_truth:
        total_match = approx_equal(output["total_kg_co2e"], ground_truth["total_kg_co2e"])
        checks.append({"check": "total", "pass": total_match})

    # Check individual fuel items in breakdown
    output_breakdown = {item.get("fuel_type"): item for item in output.get("breakdown", []) if item.get("fuel_type")}
    gt_breakdown = {item.get("fuel_type"): item for item in ground_truth.get("breakdown", []) if item.get("fuel_type")}

    for fuel_type in gt_breakdown:
        if fuel_type in output_breakdown:
            emission_match = approx_equal(
                output_breakdown[fuel_type]["kg_co2e"],
                gt_breakdown[fuel_type]["kg_co2e"]
            )
            checks.append({"check": f"fuel_{fuel_type}", "pass": emission_match})

    passed = sum(1 for c in checks if c["pass"])
    return {"scenario": "multi_fuel", "checks": checks,
            "passed": passed, "total": len(checks),
            "score": passed / len(checks) if checks else 0}


def evaluate_scenario_3(output: dict, ground_truth: dict) -> dict:
    """Evaluate multi-refrigerant calculation."""
    checks = []
    # Total
    if "total_kg_co2e" in output and "total_kg_co2e" in ground_truth:
        total_match = approx_equal(output["total_kg_co2e"], ground_truth["total_kg_co2e"])
        checks.append({"check": "total", "pass": total_match})

    # Check GWP values and emissions in breakdown
    output_breakdown = {item.get("refrigerant"): item for item in output.get("breakdown", []) if item.get("refrigerant")}
    gt_breakdown = {item.get("refrigerant"): item for item in ground_truth.get("breakdown", []) if item.get("refrigerant")}

    for ref in gt_breakdown:
        if ref in output_breakdown:
            gwp_match = output_breakdown[ref].get("gwp") == gt_breakdown[ref].get("gwp")
            checks.append({"check": f"gwp_{ref}", "pass": gwp_match})
            emission_match = approx_equal(
                output_breakdown[ref]["kg_co2e"],
                gt_breakdown[ref]["kg_co2e"]
            )
            checks.append({"check": f"emission_{ref}", "pass": emission_match})

    passed = sum(1 for c in checks if c["pass"])
    return {"scenario": "multi_refrigerant", "checks": checks,
            "passed": passed, "total": len(checks),
            "score": passed / len(checks) if checks else 0}


def evaluate(output_json: str, scenario: int) -> dict:
    """Main evaluation entry point."""
    output = json.loads(output_json)
    gt_path = Path(__file__).parent / "test_data" / f"scenario_{scenario}_expected.json"
    if not gt_path.exists():
        return {"error": f"Ground truth not found for scenario {scenario}"}
    ground_truth = json.loads(gt_path.read_text(encoding="utf-8"))

    evaluators = {
        1: evaluate_scenario_1,
        2: evaluate_scenario_2,
        3: evaluate_scenario_3
    }
    return evaluators[scenario](output, ground_truth)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: python evaluator.py <output_json> <scenario_number>"}))
        sys.exit(1)
    result = evaluate(sys.argv[1], int(sys.argv[2]))
    print(json.dumps(result, ensure_ascii=False, indent=2))
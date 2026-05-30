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
    # Total — ground truth key is authoritative
    total_match = approx_equal(output.get("total_kg_co2e", -1), ground_truth["total_kg_co2e"])
    checks.append({"check": "total", "pass": total_match,
                    "output": output.get("total_kg_co2e"),
                    "expected": ground_truth["total_kg_co2e"]})
    # Scope 1
    s1_match = approx_equal(output.get("scope1_kg_co2e", -1), ground_truth["scope1_kg_co2e"])
    checks.append({"check": "scope1", "pass": s1_match,
                    "output": output.get("scope1_kg_co2e"),
                    "expected": ground_truth["scope1_kg_co2e"]})
    # Scope 2
    s2_match = approx_equal(output.get("scope2_kg_co2e", -1), ground_truth["scope2_kg_co2e"])
    checks.append({"check": "scope2", "pass": s2_match,
                    "output": output.get("scope2_kg_co2e"),
                    "expected": ground_truth["scope2_kg_co2e"]})

    passed = sum(1 for c in checks if c["pass"])
    return {"scenario": "office_combined", "checks": checks,
            "passed": passed, "total": len(checks),
            "score": passed / len(checks) if checks else 0}


def evaluate_scenario_2(output: dict, ground_truth: dict) -> dict:
    """Evaluate multi-fuel calculation."""
    checks = []
    # Total — ground truth is authoritative
    total_match = approx_equal(output.get("total_kg_co2e", -1), ground_truth["total_kg_co2e"])
    checks.append({"check": "total", "pass": total_match})

    # Check individual fuel items in breakdown
    # Accept both "breakdown" and "emission_breakdown" keys
    output_items = output.get("breakdown") or output.get("emission_breakdown") or []
    gt_items = ground_truth.get("breakdown") or ground_truth.get("emission_breakdown") or []
    output_breakdown = {item.get("fuel_type"): item for item in output_items if item.get("fuel_type")}
    gt_breakdown = {item.get("fuel_type"): item for item in gt_items if item.get("fuel_type")}

    for fuel_type in gt_breakdown:
        if fuel_type in output_breakdown:
            emission_match = approx_equal(
                output_breakdown[fuel_type].get("kg_co2e", -1),
                gt_breakdown[fuel_type]["kg_co2e"]
            )
            checks.append({"check": f"fuel_{fuel_type}", "pass": emission_match})
        else:
            checks.append({"check": f"fuel_{fuel_type}", "pass": False,
                           "output": None, "expected": gt_breakdown[fuel_type]["kg_co2e"]})

    passed = sum(1 for c in checks if c["pass"])
    return {"scenario": "multi_fuel", "checks": checks,
            "passed": passed, "total": len(checks),
            "score": passed / len(checks) if checks else 0}


def evaluate_scenario_3(output: dict, ground_truth: dict) -> dict:
    """Evaluate multi-refrigerant calculation."""
    checks = []
    # Total — ground truth is authoritative
    total_match = approx_equal(output.get("total_kg_co2e", -1), ground_truth["total_kg_co2e"])
    checks.append({"check": "total", "pass": total_match})

    # Accept both "breakdown" and "emission_breakdown" keys
    output_items = output.get("breakdown") or output.get("emission_breakdown") or []
    gt_items = ground_truth.get("breakdown") or ground_truth.get("emission_breakdown") or []
    output_breakdown = {item.get("refrigerant"): item for item in output_items if item.get("refrigerant")}
    gt_breakdown = {item.get("refrigerant"): item for item in gt_items if item.get("refrigerant")}

    for ref in gt_breakdown:
        if ref in output_breakdown:
            gwp_match = output_breakdown[ref].get("gwp") == gt_breakdown[ref].get("gwp")
            checks.append({"check": f"gwp_{ref}", "pass": gwp_match})
            emission_match = approx_equal(
                output_breakdown[ref].get("kg_co2e", -1),
                gt_breakdown[ref]["kg_co2e"]
            )
            checks.append({"check": f"emission_{ref}", "pass": emission_match})
        else:
            checks.append({"check": f"refrigerant_{ref}", "pass": False,
                           "output": None, "expected": gt_breakdown[ref]["kg_co2e"]})

    passed = sum(1 for c in checks if c["pass"])
    return {"scenario": "multi_refrigerant", "checks": checks,
            "passed": passed, "total": len(checks),
            "score": passed / len(checks) if checks else 0}


def generate_ground_truth(scenario: int) -> dict:
    """Dynamically generate ground truth from calculate.py + emission_factors.json.
    This ensures perturbation-resilience: if factors change, ground truth updates automatically.
    """
    if scenario == 1:
        # Office combined: 1200 kWh + R410A 5kg
        e = calc_electricity(kwh=1200, region="TW", year="2024")
        r = calc_refrigerant(refrigerant="R410A", leakage_kg=5, ar_version="ar5")
        return calc_combined([
            {"type": "electricity", "kwh": 1200},
            {"type": "refrigerant", "refrigerant": "R410A", "leakage_kg": 5}
        ])
    elif scenario == 2:
        # Multi-fuel: diesel 500L + natural gas 200m³
        d = calc_fuel(fuel_type="diesel", amount=500)
        n = calc_fuel(fuel_type="natural_gas", amount=200)
        return calc_combined([
            {"type": "fuel", "fuel_type": "diesel", "amount": 500},
            {"type": "fuel", "fuel_type": "natural_gas", "amount": 200}
        ])
    elif scenario == 3:
        # Multi-refrigerant: R410A 3kg + R32 2kg + R134a 1.5kg
        return calc_combined([
            {"type": "refrigerant", "refrigerant": "R410A", "leakage_kg": 3},
            {"type": "refrigerant", "refrigerant": "R32", "leakage_kg": 2},
            {"type": "refrigerant", "refrigerant": "R134a", "leakage_kg": 1.5}
        ])
    else:
        return {"error": f"Unknown scenario: {scenario}"}


def evaluate(output_json: str, scenario: int, use_static_gt: bool = False) -> dict:
    """Main evaluation entry point.

    By default, generates ground truth dynamically from calculate.py,
    which makes it resilient to perturbation (emission factor changes).
    Set use_static_gt=True to use static test_data/ files instead.
    """
    output = json.loads(output_json)

    if use_static_gt:
        gt_path = Path(__file__).parent / "test_data" / f"scenario_{scenario}_expected.json"
        if not gt_path.exists():
            return {"error": f"Ground truth not found for scenario {scenario}"}
        ground_truth = json.loads(gt_path.read_text(encoding="utf-8"))
    else:
        ground_truth = generate_ground_truth(scenario)
        if "error" in ground_truth:
            return ground_truth

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
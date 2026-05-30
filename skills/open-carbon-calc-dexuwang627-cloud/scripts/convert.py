#!/usr/bin/env python3
"""Unit conversion utility for Carbon Emission Calculator.

Handles non-standard units commonly used in Taiwan carbon inventory:
  度 ↔ kWh, 公升 ↔ L, 立方公尺 ↔ m³, 噸/公噸 ↔ kg, 公斤 ↔ kg

Usage:
    python convert.py 度 1200
    python convert.py kWh 1200
    python convert.py --table
"""
import json
import sys

# Conversion factors: from_unit → to_unit = factor
CONVERSIONS = {
    # Taiwan common units → SI
    "度": {"to": "kWh", "factor": 1.0},        # 1 度電 = 1 kWh (by definition)
    "kWh": {"to": "度", "factor": 1.0},
    "公升": {"to": "L", "factor": 1.0},          # 1 公升 = 1 L
    "L": {"to": "公升", "factor": 1.0},
    "立方公尺": {"to": "m³", "factor": 1.0},     # 1 立方公尺 = 1 m³
    "m³": {"to": "立方公尺", "factor": 1.0},
    "公噸": {"to": "kg", "factor": 1000.0},       # 1 公噸 = 1000 kg
    "噸": {"to": "kg", "factor": 1000.0},         # 1 噸 = 1000 kg (metric)
    "kg": {"to": "公噸", "factor": 0.001},
    "公克": {"to": "g", "factor": 1.0},
    "g": {"to": "公克", "factor": 1.0},
    "公里": {"to": "km", "factor": 1.0},
    "km": {"to": "公里", "factor": 1.0},
}


def convert(unit: str, value: float) -> dict:
    """Convert a value from the given unit to its SI equivalent.

    Args:
        unit: Source unit (度, 公升, 立方公尺, 噸, 公噸, or SI equivalents).
        value: Numeric value to convert.

    Returns:
        Dict with original, converted, factor, and both units.
    """
    if value < 0:
        return {"error": "value must be non-negative", "valid": False}

    unit_lower = unit.strip()
    if unit_lower not in CONVERSIONS:
        available = sorted(CONVERSIONS.keys())
        return {"error": f"Unknown unit: {unit}. Available: {available}", "valid": False}

    entry = CONVERSIONS[unit_lower]
    target = entry["to"]
    factor = entry["factor"]

    if target == unit_lower:
        # Same-system unit (e.g., 度 → kWh where factor is 1.0)
        converted = value * factor
    else:
        converted = value * factor

    return {
        "original": {"value": value, "unit": unit_lower},
        "converted": {"value": round(converted, 6), "unit": target},
        "factor": factor,
        "valid": True
    }


def list_conversions() -> dict:
    """List all supported unit conversions."""
    return {
        "conversions": {
            k: {"to": v["to"], "factor": v["factor"]}
            for k, v in CONVERSIONS.items()
        }
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python convert.py <unit> <value> or --table"}, ensure_ascii=False))
        sys.exit(1)

    if sys.argv[1] in ("--table", "-t", "list"):
        result = list_conversions()
    elif len(sys.argv) >= 3:
        try:
            unit = sys.argv[1]
            value = float(sys.argv[2])
            result = convert(unit, value)
        except ValueError:
            result = {"error": f"Invalid number: {sys.argv[2]}", "valid": False}
    else:
        result = {"error": "Usage: python convert.py <unit> <value>", "valid": False}

    print(json.dumps(result, ensure_ascii=False))
#!/usr/bin/env python3
"""Carbon emission calculator — deterministic calculation engine.

Usage:
    python calculate.py electricity '{"kwh": 1200, "region": "TW", "year": "2024"}'
    python calculate.py fuel '{"fuel_type": "diesel", "amount": 100}'
    python calculate.py refrigerant '{"refrigerant": "R410A", "leakage_kg": 5, "ar_version": "ar5"}'
    python calculate.py vehicle '{"vehicle_type": "gasoline_car", "distance_km": 150}'
    python calculate.py combined '{"items": [...]}'
"""
import json
import sys
from pathlib import Path

FACTORS_PATH = Path(__file__).parent / "emission_factors.json"


def load_factors() -> dict:
    """Load emission factors from JSON."""
    with open(FACTORS_PATH, encoding="utf-8") as f:
        return json.load(f)


def calc_electricity(kwh: float, region: str = "TW", year: str = "2024") -> dict:
    """Scope 2: Calculate electricity emission."""
    factors = load_factors()
    region_data = factors["electricity"].get(region)
    if region_data is None:
        return {"error": f"Unknown region: {region}", "valid": False}
    year_factor = region_data.get(year)
    if year_factor is None:
        return {"error": f"Unknown year: {year} for region {region}", "valid": False}
    kg_co2e = kwh * year_factor
    return {
        "scope": 2,
        "category": "electricity",
        "consumption_kwh": kwh,
        "emission_factor": year_factor,
        "emission_factor_unit": "kg_co2e/kWh",
        "region": region,
        "year": year,
        "kg_co2e": round(kg_co2e, 2),
        "source": factors["electricity"][region].get("source", "")
    }


def calc_fuel(fuel_type: str, amount: float) -> dict:
    """Scope 1: Calculate fuel combustion emission."""
    factors = load_factors()
    fuel = factors["fuel"].get(fuel_type)
    if fuel is None:
        available = list(factors["fuel"].keys())
        return {"error": f"Unknown fuel type: {fuel_type}. Available: {available}", "valid": False}
    # Explicit mapping: fuel_type → per-unit emission factor key
    # This is robust against JSON key order changes and new fuel additions
    FACTOR_KEY_MAP = {
        "diesel": "co2_kg_per_liter",
        "natural_gas": "co2_kg_per_m3",
        "lpg": "co2_kg_per_kg",
        "coal": "co2_kg_per_kg",
    }
    factor_key = FACTOR_KEY_MAP.get(fuel_type)
    emission_factor = fuel.get(factor_key) if factor_key else None
    if emission_factor is None:
        # Fallback: search for any key starting with co2_kg_per_ (excluding co2_factor_kg_per_tj)
        for key, value in fuel.items():
            if key.startswith("co2_kg_per_") and key != "co2_factor_kg_per_tj":
                emission_factor = value
                break
    if emission_factor is None:
        return {"error": f"No per-unit emission factor found for {fuel_type}", "valid": False}
    kg_co2e = amount * emission_factor
    return {
        "scope": 1,
        "category": "fuel_combustion",
        "fuel_type": fuel_type,
        "amount": amount,
        "unit": fuel["unit"],
        "emission_factor": emission_factor,
        "emission_factor_unit": f"kg_co2e/{fuel['unit']}",
        "kg_co2e": round(kg_co2e, 2),
        "source": fuel.get("source", "")
    }


def calc_refrigerant(refrigerant: str, leakage_kg: float, ar_version: str = "ar5") -> dict:
    """Scope 1: Calculate refrigerant leakage emission."""
    factors = load_factors()
    ref = factors["refrigerant"].get(refrigerant)
    if ref is None:
        available = list(factors["refrigerant"].keys())
        return {"error": f"Unknown refrigerant: {refrigerant}. Available: {available}", "valid": False}
    gwp_key = f"gwp_{ar_version}"
    gwp = ref.get(gwp_key)
    if gwp is None:
        return {"error": f"Unknown AR version: {ar_version}. Available: ar5, ar6", "valid": False}
    kg_co2e = leakage_kg * gwp
    return {
        "scope": 1,
        "category": "refrigerant_leakage",
        "refrigerant": refrigerant,
        "leakage_kg": leakage_kg,
        "gwp": gwp,
        "ar_version": ar_version,
        "kg_co2e": round(kg_co2e, 2),
        "source": ref.get("source", "")
    }


def calc_vehicle(vehicle_type: str, distance_km: float) -> dict:
    """Scope 1/3: Calculate transportation emission."""
    factors = load_factors()
    v = factors["vehicle"].get(vehicle_type)
    if v is None:
        available = list(factors["vehicle"].keys())
        return {"error": f"Unknown vehicle type: {vehicle_type}. Available: {available}", "valid": False}
    kg_co2e = distance_km * v["factor_kg_co2_per_km"]
    return {
        "scope": 1,
        "category": "transportation",
        "vehicle_type": vehicle_type,
        "distance_km": distance_km,
        "emission_factor": v["factor_kg_co2_per_km"],
        "emission_factor_unit": "kg_co2e/km",
        "kg_co2e": round(kg_co2e, 2),
        "source": v.get("source", "")
    }


def calc_combined(items: list) -> dict:
    """Calculate combined emissions from multiple sources.

    items: list of dicts, each with 'type' and type-specific fields.
    Supported types: electricity, fuel, refrigerant, vehicle
    """
    factors = load_factors()
    results = []
    for item in items:
        calc_type = item.get("type")
        if calc_type == "electricity":
            r = calc_electricity(
                kwh=item["kwh"],
                region=item.get("region", "TW"),
                year=item.get("year", "2024")
            )
        elif calc_type == "fuel":
            r = calc_fuel(
                fuel_type=item["fuel_type"],
                amount=item["amount"]
            )
        elif calc_type == "refrigerant":
            r = calc_refrigerant(
                refrigerant=item["refrigerant"],
                leakage_kg=item["leakage_kg"],
                ar_version=item.get("ar_version", "ar5")
            )
        elif calc_type == "vehicle":
            r = calc_vehicle(
                vehicle_type=item["vehicle_type"],
                distance_km=item["distance_km"]
            )
        else:
            r = {"error": f"Unknown calculation type: {calc_type}", "valid": False}
        results.append(r)

    # Sum by scope — if any item has an error, propagate it
    errors = [r for r in results if "error" in r and r.get("valid") is False]
    if errors:
        error_msgs = [r["error"] for r in errors]
        return {"error": f"Calculation errors: {'; '.join(error_msgs)}", "valid": False, "breakdown": results}

    scope1 = sum(r["kg_co2e"] for r in results if r.get("scope") == 1)
    scope2 = sum(r["kg_co2e"] for r in results if r.get("scope") == 2)
    total = scope1 + scope2

    return {
        "breakdown": results,
        "scope1_kg_co2e": round(scope1, 2),
        "scope2_kg_co2e": round(scope2, 2),
        "total_kg_co2e": round(total, 2)
    }


def list_factors() -> dict:
    """List all available emission factors."""
    factors = load_factors()
    return {
        "electricity_regions": list(factors["electricity"].keys()),
        "fuel_types": list(factors["fuel"].keys()),
        "refrigerants": list(factors["refrigerant"].keys()),
        "vehicle_types": list(factors["vehicle"].keys())
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python calculate.py <command> [args_json]"}, ensure_ascii=False))
        sys.exit(1)

    command = sys.argv[1]

    if command in ("list", "factors"):
        result = list_factors()
    elif len(sys.argv) > 2:
        args = json.loads(sys.argv[2])
        dispatch = {
            "electricity": lambda: calc_electricity(**args),
            "fuel": lambda: calc_fuel(**args),
            "refrigerant": lambda: calc_refrigerant(**args),
            "vehicle": lambda: calc_vehicle(**args),
            "combined": lambda: calc_combined(**args),
        }
        if command not in dispatch:
            result = {"error": f"Unknown command: {command}. Available: {list(dispatch.keys())}"}
        else:
            result = dispatch[command]()
    else:
        result = {"error": f"Missing arguments for command: {command}"}

    print(json.dumps(result, ensure_ascii=False))
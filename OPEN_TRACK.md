# Open Track: Carbon Emission Calculator

## Skill Name & Purpose

**Name**: open-carbon-calc-dexuwang627-cloud

**Purpose**: Calculate carbon emissions (kg CO₂e) from natural-language descriptions of organizational activities. Designed for Taiwan-context carbon inventory (碳盤查), covering Scope 1 (direct emissions: fuel combustion, refrigerant leakage, transportation) and Scope 2 (indirect electricity emissions).

The skill embodies the "deterministic shell wrapping probabilistic core" architecture: the LLM handles natural language understanding and parameter extraction, while all numeric calculations are performed by deterministic Python scripts using authoritative emission factors.

## Scenarios

### Scenario 1: Office Combined Emission (Scope 1+2)

**Input**: "我們辦公室每月用電 1200 度，冷氣使用 R410A 冷媒 5 公斤逸散"

**Expected output**:
```json
{
  "task_id": "scenario_1",
  "category": "combined",
  "scope": null,
  "emission_breakdown": [
    {"scope": 2, "category": "electricity", "consumption_kwh": 1200, "emission_factor": 0.474, "emission_factor_unit": "kg_co2e/kWh", "region": "TW", "year": "2024", "kg_co2e": 568.8, "source": "經濟部能源署 2025/4/14 公告"},
    {"scope": 1, "category": "refrigerant_leakage", "refrigerant": "R410A", "leakage_kg": 5, "gwp": 1924, "ar_version": "ar5", "kg_co2e": 9620, "source": "IPCC AR5/AR6"}
  ],
  "scope1_kg_co2e": 9620,
  "scope2_kg_co2e": 568.8,
  "total_kg_co2e": 10188.8,
  "confidence": 0.95,
  "rationale": "Extracted two emission sources: electricity (Scope 2) and refrigerant leakage (Scope 1). Called calculate.py for each, then combined."
}
```

**Evaluator**: Checks total, scope1, and scope2 values against ground truth with ±5% tolerance.

### Scenario 2: Multi-Fuel Calculation (Scope 1)

**Input**: "公司車隊本月消耗柴油 500 公升和天然氣 200 立方公尺"

**Expected output**:
```json
{
  "task_id": "scenario_2",
  "category": "combined",
  "scope": null,
  "emission_breakdown": [
    {"scope": 1, "category": "fuel_combustion", "fuel_type": "diesel", "amount": 500, "unit": "L", "emission_factor": 2.68, "emission_factor_unit": "kg_co2e/L", "kg_co2e": 1340.0, "source": "IPCC 2006 Tier 1, 台灣清冊"},
    {"scope": 1, "category": "fuel_combustion", "fuel_type": "natural_gas", "amount": 200, "unit": "m³", "emission_factor": 2.02, "emission_factor_unit": "kg_co2e/m³", "kg_co2e": 404.0, "source": "IPCC 2006 Tier 1"}
  ],
  "scope1_kg_co2e": 1744.0,
  "scope2_kg_co2e": 0,
  "total_kg_co2e": 1744.0,
  "confidence": 0.9,
  "rationale": "Two fuel types identified: diesel and natural gas. Called calculate.py for each fuel, then combined."
}
```

**Evaluator**: Checks total and each fuel type's emission against ground truth with ±5% tolerance.

### Scenario 3: Multi-Refrigerant with AR Version (Scope 1)

**Input**: "空調系統冷媒逸散：R410A 3kg、R32 2kg、R134a 1.5kg"

**Expected output**:
```json
{
  "task_id": "scenario_3",
  "category": "combined",
  "scope": null,
  "emission_breakdown": [
    {"scope": 1, "category": "refrigerant_leakage", "refrigerant": "R410A", "leakage_kg": 3, "gwp": 1924, "ar_version": "ar5", "kg_co2e": 5772, "source": "IPCC AR5/AR6"},
    {"scope": 1, "category": "refrigerant_leakage", "refrigerant": "R32", "leakage_kg": 2, "gwp": 677, "ar_version": "ar5", "kg_co2e": 1354, "source": "IPCC AR5/AR6"},
    {"scope": 1, "category": "refrigerant_leakage", "refrigerant": "R134a", "leakage_kg": 1.5, "gwp": 1300, "ar_version": "ar5", "kg_co2e": 1950.0, "source": "IPCC AR5/AR6"}
  ],
  "scope1_kg_co2e": 9076.0,
  "scope2_kg_co2e": 0,
  "total_kg_co2e": 9076.0,
  "confidence": 0.9,
  "rationale": "Three refrigerants identified with AR5 GWP values. Called calculate.py for each, then combined."
}
```

**Evaluator**: Checks total, each refrigerant's GWP value (exact match), and each emission value (±5% tolerance).

## Evaluator Design

The evaluator (`scripts/evaluator.py`) performs deterministic comparison:

- **Numeric values**: Approximate equality with ±5% tolerance (`|a-b| / max(|a|,|b|) ≤ 0.05`)
- **GWP values**: Exact integer match (authoritative constants, no tolerance)
- **Scoring**: `passed_checks / total_checks` per scenario

Each scenario has multiple check points:
- Scenario 1: total, scope1, scope2 (3 checks)
- Scenario 2: total, per-fuel emissions (3 checks)
- Scenario 3: total, per-refrigerant GWP + emissions (7 checks)

## Anti-Hardcoding Measures

1. **Externalized factors**: All emission factors live in `scripts/emission_factors.json`, separate from calculation logic. Staff can perturbation-test by modifying factors.
2. **No hardcoded answers**: The SKILL.md explicitly instructs the LLM to call `scripts/calculate.py` for all calculations — never compute manually.
3. **Perturbation resistance**: Changing input numbers (e.g., 1200→850 kWh, diesel 500→350 L) changes outputs proportionally. Hardcoded answer patterns would fail.
4. **AR version switching**: AR5 vs AR6 produces different GWP values; a hardcoded response cannot handle both.

## Model-Agnostic Strategy

| Component | LLM Responsibility | Risk on Model Change |
|-----------|-------------------|---------------------|
| Category classification | Identify emission type from keywords | Low: keyword fallback rules provided |
| Number extraction | Pull numeric values from text | Very low: basic NER |
| Unit recognition | Convert 度→kWh, 公升→L, 立方公尺→m³ | Low: explicit mapping in SKILL.md |
| **Calculation** | **None** → scripts/calculate.py | **Zero risk** |
| JSON formatting | Follow output schema | Low: constrained by schema |

The skill is designed so that even if the LLM's classification accuracy drops on a different model, the keyword fallback rules ensure basic functionality. Calculation accuracy is guaranteed regardless of model because it's deterministic Python code.

## Failure Modes & Mitigations

| Failure Mode | Impact | Mitigation |
|--------------|--------|-----------|
| LLM misclassifies category | Wrong calculation called | Keyword fallback rules; confidence lowered |
| Number extraction error (multiple numbers) | Wrong parameters | LLM instructed to identify each number's referent; confidence lowered |
| Unknown fuel type / refrigerant | Calculation fails | calculate.py returns error with available types; LLM suggests alternatives |
| AR version ambiguity | Different GWP values | Default to AR5 (Taiwan standard); note in rationale |
| JSON schema violation | Evaluator can't parse | SKILL.md provides explicit schema; single fenced JSON block rule |
| Model generates calculation manually | Bypasses deterministic shell | SKILL.md explicitly prohibits manual calculation; evaluator catches discrepancies |

## Improvement Directions

1. **More emission categories**: Add Scope 3 (transportation, waste, purchased goods), stationary combustion details
2. **Multi-region support**: Expand beyond Taiwan (JP, US, EU electricity factors)
3. **Unit conversion**: Handle 年用電→月用電, 噸→公斤, etc.
4. **Historical factors**: Support year-over-year emission factor changes
5. **Report generation**: Output ISO 14064-compliant emission summary
6. **Confidence calibration**: Track LLM accuracy across models to improve confidence scoring
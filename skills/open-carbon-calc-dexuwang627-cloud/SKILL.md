---
name: open-carbon-calc-dexuwang627-cloud
description: Calculates carbon emissions from natural-language descriptions (Scope 1+2, Taiwan)
tags: [carbon, emission, calculator, taiwan]
---

# Carbon Emission Calculator Skill

## Purpose

Calculate carbon emissions (kg CO₂e) from natural-language descriptions of organizational activities. Designed for Taiwan-context carbon inventory (碳盤查), covering Scope 1 (direct emissions) and Scope 2 (indirect electricity emissions).

## Deterministic Shell Architecture

This skill follows the "deterministic shell wrapping probabilistic core" pattern:

- **Probabilistic core (LLM)**: Understands natural language, extracts parameters, classifies emission categories, and formats output.
- **Deterministic shell (`scripts/calculate.py`)**: Performs all numeric calculations using emission factors from `scripts/emission_factors.json`.
- **Evaluation (`scripts/evaluator.py`)**: Validates outputs against ground truth with 5% tolerance.

The LLM **never** performs calculations directly. It only:
1. Classifies the emission category (electricity / fuel / refrigerant / vehicle)
2. Extracts numeric parameters from natural language
3. Calls `scripts/calculate.py` via terminal tool
4. Formats the result as JSON

## Input

Natural language description of emission activities. Examples:
- "我們辦公室每月用電 1200 度，冷氣使用 R410A 冷媒 5 公斤逸散"
- "公司車隊本月消耗柴油 500 公升和天然氣 200 立方公尺"
- "空調系統冷媒逸散：R410A 3kg、R32 2kg、R134a 1.5kg"

## Output Schema

```json
{
  "task_id": "string (from input, or generated)",
  "category": "string (electricity | fuel_combustion | refrigerant_leakage | transportation | combined)",
  "scope": "integer (1 or 2 or null for combined)",
  "emission_breakdown": [
    {
      "scope": 1,
      "category": "refrigerant_leakage",
      "refrigerant": "R410A",
      "leakage_kg": 5,
      "gwp": 1924,
      "ar_version": "ar5",
      "kg_co2e": 9620
    }
  ],
  "scope1_kg_co2e": 9620,
  "scope2_kg_co2e": 568.8,
  "total_kg_co2e": 10188.8,
  "confidence": 0.95,
  "rationale": "Step-by-step reasoning"
}
```

## Multi-Step Interaction Flow

For every query, follow this sequence:

1. **Classify**: Determine which emission categories are involved
2. **Extract**: Pull numeric values and units from the description
3. **Validate**: Check that extracted values make sense (positive numbers, valid fuel types, known refrigerants)
4. **Calculate**: Call `scripts/calculate.py` with extracted parameters
5. **Aggregate**: If multiple categories, call `scripts/calculate.py combined` to sum
6. **Verify**: Sanity-check results (e.g., Scope 2 should be 0 for fuel-only, total should match sum)
7. **Format**: Output as single fenced JSON block

## Classification Rules (Keyword Fallback)

When the LLM is uncertain about category classification, use keyword matching:

| Keywords | Category | Scope |
|----------|----------|-------|
| 度, 用電, 電力, electricity, kWh, 用電量 | electricity | 2 |
| 柴油, 天然氣, 瓦斯, LPG, 煤, diesel, fuel, 燃料 | fuel_combustion | 1 |
| 冷媒, R410A, R32, R134a, R407C, R22, refrigerant, 逸散 | refrigerant_leakage | 1 |
| 開車, 交通, 公里, km, 車, vehicle, 運輸 | transportation | 1 |

## Calculation Commands

```bash
# Electricity (Scope 2)
python3 scripts/calculate.py electricity '{"kwh": 1200, "region": "TW", "year": "2024"}'

# Fuel (Scope 1)
python3 scripts/calculate.py fuel '{"fuel_type": "diesel", "amount": 500}'

# Refrigerant (Scope 1)
python3 scripts/calculate.py refrigerant '{"refrigerant": "R410A", "leakage_kg": 5, "ar_version": "ar5"}'

# Vehicle (Scope 1)
python3 scripts/calculate.py vehicle '{"vehicle_type": "gasoline_car", "distance_km": 150}'

# Combined (multi-source)
python3 scripts/calculate.py combined '{"items": [{"type": "electricity", "kwh": 1200}, {"type": "refrigerant", "refrigerant": "R410A", "leakage_kg": 5}]}'

# List available factors
python3 scripts/calculate.py list

# Unit conversion (度↔kWh, 公升↔L, 立方公尺↔m³, 公噸↔kg, etc.)
python3 scripts/convert.py 度 1200
python3 scripts/convert.py 公噸 2
python3 scripts/convert.py --table
```

## Supported Emission Factors

### Electricity (Scope 2, Taiwan)
- 2024: 0.474 kg CO₂e/kWh (經濟部能源署公告)

### Fuel (Scope 1)
| Fuel | Factor | Unit |
|------|--------|------|
| diesel | 2.68 | kg CO₂/L |
| natural_gas | 2.02 | kg CO₂/m³ |
| lpg | 2.98 | kg CO₂/kg |
| coal | 2.15 | kg CO₂/kg |

### Refrigerant GWP (Scope 1)
| Refrigerant | GWP (AR5) | GWP (AR6) |
|-------------|-----------|-----------|
| R410A | 1,924 | 2,256 |
| R32 | 677 | 771 |
| R134a | 1,300 | 1,530 |
| R407C | 1,624 | 1,908 |
| R22 | 1,760 | 1,960 |

## Scenarios

### Scenario 1: Office Combined Emission (Scope 1+2)
**Input**: "我們辦公室每月用電 1200 度，冷氣使用 R410A 冷媒 5 公斤逸散"
**Expected output**:
- Scope 2 (electricity): 1200 × 0.474 = 568.8 kg CO₂e
- Scope 1 (refrigerant): 5 × 1924 = 9,620 kg CO₂e
- Total: 10,188.8 kg CO₂e

### Scenario 2: Multi-Fuel Calculation (Scope 1)
**Input**: "公司車隊本月消耗柴油 500 公升和天然氣 200 立方公尺"
**Expected output**:
- Diesel: 500 × 2.68 = 1,340 kg CO₂e
- Natural gas: 200 × 2.02 = 404 kg CO₂e
- Total: 1,744 kg CO₂e

### Scenario 3: Multi-Refrigerant with AR Version (Scope 1)
**Input**: "空調系統冷媒逸散：R410A 3kg、R32 2kg、R134a 1.5kg"
**Expected output** (using AR5):
- R410A: 3 × 1924 = 5,772 kg CO₂e
- R32: 2 × 677 = 1,354 kg CO₂e
- R134a: 1.5 × 1300 = 1,950 kg CO₂e
- Total: 9,076 kg CO₂e

## Confidence Estimation

| Condition | Confidence |
|-----------|-----------|
| Single category, clear numbers, calculation verified | 0.9 – 1.0 |
| Multi-category, all parameters extracted correctly | 0.8 – 0.9 |
| Ambiguous units or category, calculation verified | 0.6 – 0.8 |
| Partial parameter extraction, estimate required | 0.4 – 0.6 |
| Cannot determine category or missing critical parameters | 0.1 – 0.3 |

## Error Handling

| Condition | Action |
|-----------|--------|
| Unknown fuel type / refrigerant | List available types in rationale, suggest closest match, lower confidence |
| Missing numeric value | Ask for clarification, output with confidence 0.1 |
| Calculation result seems unreasonable | Re-verify via calculate.py, flag in rationale |
| AR version not specified | Default to AR5 (current Taiwan regulatory standard), note in rationale |

## Rules

- All calculations MUST go through `scripts/calculate.py` — never calculate manually
- Emission factors come from `scripts/emission_factors.json` — never hardcode values
- Default AR version is AR5 unless user specifies AR6
- Default electricity region is TW, year 2024
- Output must be a single fenced JSON block
- task_id must pass through from input
- confidence must be 0.0–1.0

## When to Use

Use this skill when the input describes organizational activities involving energy consumption, fuel usage, refrigerant leakage, or transportation — any scenario requiring carbon emission calculation. The input should contain numeric quantities (kWh, liters, kg, km) and emission-related keywords (用電, 燃料, 冷媒, 車輛, 排放, 碳). Do not use this skill for unrelated calculations or non-emission queries.

## Procedure

1. **Classify**: Identify the emission category from keywords (用電/度 → electricity, 柴油/天然氣/煤 → fuel, 冷媒/R410A/R32 → refrigerant, 車/公里 → vehicle).
2. **Extract**: Pull numeric values and units from the input. Convert units as needed using `scripts/convert.py` (度→kWh, 公升→L, 立方公尺→m³, 公噸→kg).
3. **Validate**: Check that extracted values are reasonable (positive numbers, known fuel/refrigerant types).
4. **Calculate**: Call `scripts/calculate.py` with the appropriate command and parameters. For multi-source inputs, use the `combined` command.
5. **Aggregate**: If multiple emission sources are present, combine them using `calc_combined`.
6. **Verify**: Compare calculated values against expected ranges. If a value seems unreasonable, re-verify via calculate.py.
7. **Format**: Output a single fenced JSON block with task_id, category, breakdown, scope1_kg_co2e, scope2_kg_co2e, total_kg_co2e, confidence, and rationale.

## Verification

After generating output, verify correctness by:
- Running `scripts/evaluator.py '<output_json>' <scenario_number>` to compare against ground truth.
- Checking that all numeric values match calculate.py results within ±5% tolerance.
- Ensuring GWP values match authoritative IPCC constants exactly (no tolerance).
- Confirming the output JSON contains all required fields: task_id, category, breakdown (or emission_breakdown), scope1_kg_co2e, scope2_kg_co2e, total_kg_co2e, confidence.
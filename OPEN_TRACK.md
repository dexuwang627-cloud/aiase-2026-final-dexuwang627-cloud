# Open Track: Carbon Emission Calculator

## Skill Name & Purpose
Carbon emission calculator for organizational carbon inventory (Scope 1+2, Taiwan context).

## Scenarios
1. Office combined emission (Scope 1+2): electricity + refrigerant
2. Multi-fuel calculation with unit conversion (Scope 1)
3. Multi-refrigerant total with AR version selection (Scope 1)

## Evaluator Design
(To be implemented)

## Anti-Hardcoding Measures
- Emission factors externalized to data/emission_factors.json
- Staff can perturbation test with different values
- LLM never hardcodes calculation results

## Model-Agnostic Strategy
- LLM only does extraction + classification
- All calculation in scripts/calculate.py (deterministic)
- Keyword-matching fallback when LLM classification fails

## Failure Modes & Mitigations
(To be documented during development)

## Improvement Directions
(To be documented after development)
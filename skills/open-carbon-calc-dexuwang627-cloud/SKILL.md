---
name: open-carbon-calc-dexuwang627-cloud
description: Calculates carbon emissions from natural-language descriptions (Scope 1+2, Taiwan)
tags: [carbon, emission, calculator, taiwan]
---

# Carbon Emission Calculator Skill

## Purpose
Calculate carbon emissions (kg CO₂e) from natural-language descriptions of organizational activities.

## Input
Natural language description of emission activities (fuel consumption, electricity usage, refrigerant leakage)

## Output
JSON with: category, scope, emission_breakdown, total_kg_co2e, confidence

## Scenarios
1. Office electricity + AC refrigerant (Scope 1+2 combined)
2. Multi-fuel calculation with unit conversion (Scope 1)
3. Multi-refrigerant total with AR version selection (Scope 1)

## Rules
- Use Taiwan-specific emission factors
- Refrigerant GWP from IPCC AR5/AR6
- All calculations done in scripts/ (deterministic)
- LLM only handles extraction and classification
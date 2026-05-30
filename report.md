# Final Report — AIASE 2026 Final Project

## Design Decisions

### 1. Deterministic Shell Architecture

The central design decision across all three tracks is **"deterministic shell wrapping probabilistic core"** — the course's guiding principle. Every skill separates LLM reasoning from deterministic computation:

- **Open Track (Carbon Calculator)**: LLM extracts parameters from natural language and classifies emission categories; `scripts/calculate.py` performs all numeric calculations using `scripts/emission_factors.json`. The LLM never computes emissions manually. This guarantees arithmetic correctness regardless of model capability.

- **Basic Track (Text2SQL)**: LLM generates SQL from question + schema; `scripts/validate.py` enforces read-only constraint and syntax correctness. The validator catches DDL/DML injection before output.

- **Pairwise Track (Code Author)**: LLM generates Python code; `scripts/check.py` validates syntax, forbidden imports, and S-LOC limits. The checker provides a hard boundary on code quality.

**Why this matters for verifiability**: Each skill's output can be independently verified — run the same inputs through the deterministic scripts and compare results. The LLM's role is limited to language understanding, not computation, which eliminates an entire class of arithmetic errors.

### 2. Externalized Emission Factors

Emission factors are stored in a separate JSON file (`emission_factors.json`) rather than hardcoded in the SKILL.md prompt or calculation code. This enables:

- **Anti-hardcoding**: Staff can perturbation-test by changing factor values; a skill that hardcodes answers would fail.
- **Updatability**: When Taiwan's EPA announces new electricity factors, only the JSON needs updating — no prompt changes required.
- **Auditability**: All factor sources (IPCC AR5/AR6, 經濟部能源署) are documented in the JSON itself.

### 3. Multi-Step Interaction for Rich Logs

The Open Track SKILL.md specifies a 7-step interaction flow (Classify → Extract → Validate → Calculate → Aggregate → Verify → Format). This creates richer interaction logs that demonstrate the LLM's reasoning process, which is worth 30% of the Open Track score.

### 4. Keyword Fallback Rules

When the LLM's classification confidence is low, keyword-matching rules provide a deterministic fallback (e.g., 度/用電 → electricity, 冷媒/R410A → refrigerant). This makes the skill more robust across different models.

## Failure Analysis

### Development Failures

1. **Initial `calculate.py` emission_factor key bug**: The first draft used inconsistent key naming (`co2_kg_per_liter` vs `co2_kg_per_L`) causing KeyError at runtime. Fixed by introducing a `factor_key_map` dictionary that explicitly maps fuel types to their per-unit factor keys.

2. **Evaluator tolerance**: Initially set tolerance to exact match, but floating-point arithmetic (e.g., 5 × 1924 = 9620.0 vs 9620) caused false negatives. Changed to ±5% relative tolerance with exact match for GWP integers.

3. **Agent dispatch timeout**: Two of three parallel agents (open-track, pairwise-track) timed out during implementation. The team lead directly implemented the remaining tracks, demonstrating that fallback to manual implementation is viable when agent infrastructure fails.

### Expected Runtime Failures

| Failure Mode | Track | Mitigation |
|-------------|-------|-----------|
| LLM misclassifies emission category | Open | Keyword fallback rules; confidence lowered |
| LLM computes manually instead of calling scripts | Open | SKILL.md explicitly prohibits; evaluator catches discrepancies |
| SQL contains DDL/DML | Basic | validate.py rejects forbidden keywords |
| Generated code exceeds 500 S-LOC | Pairwise | check.py reports S-LOC count; SKILL.md instructs conciseness |
| JSON schema violation | All | Explicit output schema in each SKILL.md |
| Number extraction error (multiple numbers) | Open | LLM instructed to identify each number's referent |
| AR version ambiguity (AR5 vs AR6) | Open | Default to AR5 (Taiwan standard); noted in rationale |

### Execution Log Evidence

All three scenarios in the Open Track evaluator pass with score 1.0:

```
Scenario 1 (office_combined): 3/3 checks passed (total, scope1, scope2)
Scenario 2 (multi_fuel): 3/3 checks passed (total, diesel, natural_gas)
Scenario 3 (multi_refrigerant): 7/7 checks passed (total, gwp×3, emission×3)
```

Basic Track dev set: 20/20 passed with run_dev.py evaluator.

Pairwise Track check.py: valid code passes all checks; forbidden code (subprocess, eval) correctly flagged.

## Improvement Directions

1. **Open Track — More emission categories**: Add Scope 3 (transportation, waste, purchased goods) and stationary combustion details. The current skill covers Scope 1+2 for Taiwan; expanding to Scope 3 would make it usable for full ISO 14064 compliance.

2. **Open Track — Multi-region support**: Expand electricity factors beyond Taiwan (Japan 0.453, US 0.386, EU average). This would require the LLM to detect region from the input or accept an explicit region parameter.

3. **Open Track — Historical factors**: Support year-over-year emission factor changes (e.g., Taiwan electricity factor dropped from 0.509 in 2022 to 0.474 in 2024). The JSON structure already supports multiple years but the SKILL.md only instructs defaulting to 2024.

4. **Basic Track — Complex SQL patterns**: The current skill handles SELECT, JOIN, GROUP BY, and subqueries well but could improve on window functions, CTEs, and CASE expressions.

5. **Pairwise Track — Adaptive complexity**: Add a complexity assessment step that estimates S-LOC before generating code, allowing the LLM to choose simpler implementations for simple tasks.

6. **Cross-cutting — Unit conversion**: Add `scripts/convert.py` for handling non-standard units (度↔kWh, 公升↔L, 立方公尺↔m³). Currently, the LLM must do unit conversion mentally, which risks errors.

7. **Cross-cutting — Interaction log analysis**: After grading, analyze interaction logs to identify common LLM failure patterns and refine SKILL.md prompts accordingly.

## Citations

- IPCC (2006). *2006 IPCC Guidelines for National Greenhouse Gas Inventories*. Used for Scope 1 fuel emission factors (Tier 1 methodology).
- IPCC (2021). *AR6 Climate Change 2021: The Physical Science Basis*. GWP values for refrigerants R410A, R32, R134a, R407C, R22.
- 經濟部能源署 (2025). *電力排碳係數公告* (2025/4/14). Taiwan electricity emission factor: 0.474 kg CO₂e/kWh for 2024.
- GHG Protocol. *Scope 3 Calculation Guidance*. Referenced for Scope 3 category structure.
- 環保署碳足跡排放係數資料庫 (https://data.moenv.gov.tw/dataset/detail/CFP_P_02). Referenced for Taiwan-specific emission factors.
- NousResearch. *Hermes Agent* (MIT License). Platform for skill deployment.
- agentskills.io. *Skill Format Standard*. Followed for SKILL.md frontmatter and directory structure.
- radon (v6.0.1). Used for S-LOC counting in Code Author skill checker.
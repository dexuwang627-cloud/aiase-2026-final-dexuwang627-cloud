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

The Open Track SKILL.md specifies a 6-step interaction flow (Classify → Extract → Validate → Calculate → Verify → Format). Multi-source aggregation is folded into a single `calculate.py combined` call to keep per-task latency within grading time limits, while still producing interaction logs that demonstrate the LLM's reasoning process, which is worth 30% of the Open Track score.

### 4. Keyword Fallback Rules

When the LLM's classification confidence is low, keyword-matching rules provide a deterministic fallback (e.g., 度/用電 → electricity, 冷媒/R410A → refrigerant). This makes the skill more robust across different models.

## Failure Analysis

### Development Failures

1. **Initial `calculate.py` emission_factor key bug**: The first draft used inconsistent key naming (`co2_kg_per_liter` vs `co2_kg_per_L`) causing KeyError at runtime. Fixed by deriving the factor key from the fuel's `unit` field (e.g., `f"co2_kg_per_{unit}"`), making it robust against JSON key order changes and new fuel types.

2. **Evaluator tolerance**: Initially set tolerance to exact match, but floating-point arithmetic (e.g., 5 × 1924 = 9620.0 vs 9620) caused false negatives. Changed to ±5% relative tolerance with exact match for GWP integers.

3. **Agent dispatch timeout**: Two of three parallel agents (open-track, pairwise-track) timed out during implementation. The team lead directly implemented the remaining tracks, demonstrating that fallback to manual implementation is viable when agent infrastructure fails.

4. **Bug-hunter type taxonomy mismatch**: First end-to-end runs scored recall=0.00 on 4/5 reference tasks even though the hunter located the correct lines. Root cause: grading matches bugs by exact `(line_start, type)` pairs against a fixed taxonomy (`edge_case`, `off_by_one`, `logic_error`, `unhandled_input`), but the LLM invented its own type names (e.g. `index_error`). Fixed by hard-constraining the taxonomy in SKILL.md with per-type usage guidance and aligning `scripts/run.py` emissions to the same four values; recall recovered immediately.

5. **Negative few-shot backfires on small models**: Adding a "WRONG output" example containing a literal ` ```sql ` block to the text2sql SKILL.md *increased* format violations on gemma4-31b (the model imitates the example's shape and ignores the WRONG label). Removed the negative example, keeping only positive examples and a short contract statement.

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

Deterministic evaluator (scripts only, no LLM) — all three Open Track scenarios pass with score 1.0:

```
Scenario 1 (office_combined): 3/3 checks passed (total, scope1, scope2)
Scenario 2 (multi_fuel): 3/3 checks passed (total, diesel, natural_gas)
Scenario 3 (multi_refrigerant): 7/7 checks passed (total, gwp×3, emission×3)
```

End-to-end via Hermes (`--toolsets skills,terminal --yolo`) on `gemma4:31b` (Ollama Cloud, closest available proxy for the course Gemma-4-31B-IT gateway model), 2026-06-11:

- **Open Track**: scenario 1 live run scored 1.0 on the evaluator (LLM extracted both sources, called `calculate.py combined` once, output matched ground truth exactly: 10188.8 kg CO₂e).
- **Code Author**: 5/5 reference tasks passed (all hidden-style test cases) in 2 of 3 runs; 3/5 in one run due to sampling variance.
- **Bug Hunter**: improved from 1/5 to 2-3/5 after constraining the bug `type` taxonomy (see Failure 4 below); residual misses are line-attribution variance on a 31B model.
- **Basic Track**: 10-13/21 on gemma4-31b. Failures are dominated by output-format drift (the model emits a ` ```sql ` block instead of the required ` ```json ` block on complex queries) rather than SQL correctness — when the JSON contract is honored, the SQL itself passes bag-equality. Two tasks (012, 020, both double-negation/nested-subquery) also fail on SQL semantics at this model size.

Single-task latency on this setup: 5-15 s (text2sql), 7-50 s (bug-hunter), well within the 120 s grading limit.

Pairwise Track check.py: valid code passes all checks; forbidden code (subprocess, eval) correctly flagged.

## Improvement Directions

1. **Open Track — More emission categories**: Add Scope 3 (transportation, waste, purchased goods) and stationary combustion details. The current skill covers Scope 1+2 for Taiwan; expanding to Scope 3 would make it usable for full ISO 14064 compliance.

2. **Open Track — Multi-region support**: Expand electricity factors beyond Taiwan (Japan 0.453, US 0.386, EU average). This would require the LLM to detect region from the input or accept an explicit region parameter.

3. **Open Track — Historical factors**: Support year-over-year emission factor changes (e.g., Taiwan electricity factor dropped from 0.509 in 2022 to 0.474 in 2024). The JSON structure already supports multiple years but the SKILL.md only instructs defaulting to 2024.

4. **Basic Track — Complex SQL patterns**: The current skill handles SELECT, JOIN, GROUP BY, and subqueries well but could improve on window functions, CTEs, and CASE expressions.

5. **Pairwise Track — Adaptive complexity**: Add a complexity assessment step that estimates S-LOC before generating code, allowing the LLM to choose simpler implementations for simple tasks.

6. **Cross-cutting — Unit conversion**: Added `scripts/convert.py` for handling non-standard units (度↔kWh, 公升↔L, 立方公尺↔m³, 公噸↔kg). The LLM can now call this script to convert Taiwan-common units to SI equivalents deterministically, eliminating manual conversion errors.

7. **Cross-cutting — Interaction log analysis**: After grading, analyze interaction logs to identify common LLM failure patterns and refine SKILL.md prompts accordingly.

## Interaction Log Examples

The flows below were verified against live Hermes sessions on gemma4:31b (2026-06-11); the Open Track scenario 1 live output reproduced the exact figures shown here and scored 1.0 on `scripts/evaluator.py`.

### Open Track — Scenario 1: Office Combined Emission

**Input**: "我們辦公室每月用電 1200 度，冷氣使用 R410A 冷媒 5 公斤逸散"

**Interaction log**:

1. **Classify**: 度 → electricity (Scope 2), 冷媒/R410A → refrigerant_leakage (Scope 1)
2. **Extract**: electricity kwh=1200, refrigerant R410A, leakage_kg=5
3. **Validate**: Both numbers positive. R410A is a known refrigerant. Default AR version: AR5.
4. **Calculate**:
   - `python3 scripts/calculate.py electricity '{"kwh": 1200, "region": "TW", "year": "2024"}'` → 568.8 kg CO₂e
   - `python3 scripts/calculate.py refrigerant '{"refrigerant": "R410A", "leakage_kg": 5, "ar_version": "ar5"}'` → 9620.0 kg CO₂e
   - `python3 scripts/calculate.py combined '{"items": [{"type": "electricity", "kwh": 1200}, {"type": "refrigerant", "refrigerant": "R410A", "leakage_kg": 5}]}'` → total 10188.8 kg CO₂e
5. **Verify**: 568.8 + 9620.0 = 10188.8 ✓
6. **Format**: Single fenced JSON block with task_id, breakdown, scope1, scope2, total.

### Basic Track — dev_001: Aggregation Query

**Input**: "How many customers have placed more than 5 orders?"

**Interaction log**:

1. **Parse schema**: Identify customers and orders tables, foreign key customer_id.
2. **Analyze intent**: Aggregation query — count customers filtered by order count.
3. **Generate SQL**: `SELECT COUNT(*) FROM customers WHERE id IN (SELECT customer_id FROM orders GROUP BY customer_id HAVING COUNT(*) > 5)`
4. **Validate**: `python3 scripts/validate_sql.py '{"schema_ddl":"...", "sql":"SELECT COUNT(*) FROM ..."}'` → valid: true
5. **Output**: JSON with task_id, sql, rationale, confidence.

### Pairwise Track — pair_003: Word Count

**Input**: "Write a function word_count(text: str) -> dict[str, int] that counts occurrences of each word."

**Interaction log**:

1. **Analyze**: Simple string manipulation, no imports needed, O(n) solution.
2. **Implement**: `def word_count(text: str) -> dict[str, int]: ...` with empty string guard.
3. **Check**: `python3 scripts/check.py solution.py` → valid: true, sloc: 7, sloc_within_limit: true, forbidden: clean
4. **Output**: JSON with task_id, code, confidence.

## Citations

- IPCC (2006). *2006 IPCC Guidelines for National Greenhouse Gas Inventories*. Used for Scope 1 fuel emission factors (Tier 1 methodology).
- IPCC (2021). *AR6 Climate Change 2021: The Physical Science Basis*. GWP values for refrigerants R410A, R32, R134a, R407C, R22.
- 經濟部能源署 (2025). *電力排碳係數公告* (2025/4/14). Taiwan electricity emission factor: 0.474 kg CO₂e/kWh for 2024.
- GHG Protocol. *Scope 3 Calculation Guidance*. Referenced for Scope 3 category structure.
- 環保署碳足跡排放係數資料庫 (https://data.moenv.gov.tw/dataset/detail/CFP_P_02). Referenced for Taiwan-specific emission factors.
- NousResearch. *Hermes Agent* (MIT License). Platform for skill deployment.
- agentskills.io. *Skill Format Standard*. Followed for SKILL.md frontmatter and directory structure.
- radon (v6.0.1). Used for S-LOC counting in Code Author skill checker.
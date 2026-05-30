<!--
   Open Track 宣告 — 七個 heading 請照抄,順序也別動。
   合規判定會自動解析這七節;少一節就 fail gate。
   詳細要求見規格書 §2.4 與 §4.3。
-->

## 1. Skill 簡介

台灣碳盤查碳足跡計算器：從自然語言描述計算碳排放量（kg CO₂e）。涵蓋 Scope 1（燃料燃燒、冷媒逸散、交通運輸）與 Scope 2（外購電力）。採用「deterministic shell wrapping probabilistic core」架構：LLM 負責語意理解與參數提取，所有數值計算由 `scripts/calculate.py` 執行，確保算術正確性不受模型影響。

## 2. Skill 名稱與目錄

`skills/open-carbon-calc-dexuwang627-cloud/`

## 3. 呼叫方式

**Slash command:**

```
/open-carbon-calc-dexuwang627-cloud
```

**輸入 JSON 範例:**

```json
{
  "task_id": "scenario_1",
  "input": "我們辦公室每月用電 1200 度，冷氣使用 R410A 冷媒 5 公斤逸散"
}
```

**輸出 JSON 範例(此即輸出 schema):**

```json
{
  "task_id": "scenario_1",
  "category": "combined",
  "scope": null,
  "breakdown": [
    {"scope": 2, "category": "electricity", "consumption_kwh": 1200, "emission_factor": 0.474, "kg_co2e": 568.8},
    {"scope": 1, "category": "refrigerant_leakage", "refrigerant": "R410A", "leakage_kg": 5, "gwp": 1924, "kg_co2e": 9620}
  ],
  "scope1_kg_co2e": 9620,
  "scope2_kg_co2e": 568.8,
  "total_kg_co2e": 10188.8,
  "confidence": 0.95,
  "rationale": "Extracted two emission sources: electricity (Scope 2) and refrigerant leakage (Scope 1). Called calculate.py for each, then combined."
}
```

## 4. 自定 Verifiable Scenario

**Scenario 1: 辦公室綜合排放（Scope 1+2）**

輸入：「我們辦公室每月用電 1200 度，冷氣使用 R410A 冷媒 5 公斤逸散」

預期輸出：total_kg_co2e = 10188.8, scope1_kg_co2e = 9620, scope2_kg_co2e = 568.8

**Scenario 2: 多燃料燃燒（Scope 1）**

輸入：「公司車隊本月消耗柴油 500 公升和天然氣 200 立方公尺」

預期輸出：total_kg_co2e = 1744.0, 柴油 kg_co2e = 1340.0, 天然氣 kg_co2e = 404.0

**Scenario 3: 多冷媒逸散（Scope 1, AR5）**

輸入：「空調系統冷媒逸散：R410A 3kg、R32 2kg、R134a 1.5kg」

預期輸出：total_kg_co2e = 9076.0, R410A GWP=1924, R32 GWP=677, R134a GWP=1300

**Metric:** 評分器 `scripts/evaluator.py` 從 `calculate.py` 動態生成 ground truth，以 ±5% 相對誤差比對數值、GWP 整數精確比對。每個 scenario 的 score = passed_checks / total_checks。

**為何不可 gameable:**
1. Ground truth 由 `calculate.py` 動態生成——若 staff 更改 `emission_factors.json` 中的係數，ground truth 自動跟著變，hardcoded 答案立即失效。
2. 排放係數外部化在 JSON 檔案，非 hardcoding 在 prompt 中，staff 可做 perturbation 測試。
3. GWP 值為權威常數（IPCC AR5/AR6），不容許公差，精確比對杜絕猜測。
4. AR 版本可切換（AR5↔AR6），同一冷媒在不同 AR 版本下有不同 GWP，hardcoded 無法應對。

## 5. 預期失敗模式

- **失敗 1: LLM 誤判排放類別**（觸發點：輸入含多種排放源但描述模糊 / 處理：SKILL.md 提供關鍵字對照表作為 fallback，並降低 confidence）
- **失敗 2: LLM 自行計算而非呼叫 scripts**（觸發點：模型過度自信跳過計算步驟 / 處理：SKILL.md 明確禁止手動計算，evaluator 以 ±5% 容差比對，偏差超過 5% 即判失敗）
- **失敗 3: 數字提取錯誤**（觸發點：輸入含多個數字，模型無法正確配對數字與其指涉對象 / 處理：SKILL.md 指示 LLM 逐一辨識每個數字的 referent，confidence 降低）
- **失敗 4: AR 版本混淆**（觸發點：使用者未指定 AR 版本 / 處理：預設 AR5，並在 rationale 中註明）
- **失敗 5: JSON schema 違規**（觸發點：模型輸出多段 JSON 或格式錯誤 / 處理：SKILL.md 要求最後一段 fenced JSON block，evaluator 只取最後一段）

## 6. 互動對象

本 skill 為獨立計算工具，不與其他 skill 互動。評分環境中，staff 會以 `hermes chat --toolsets skills -q` 呼叫本 skill，傳入包含 `task_id` 與 `input` 的 JSON，取得包含 `task_id`（原樣回傳）與計算結果的 JSON。

不使用 subagent。所有計算邏輯在 `scripts/calculate.py` 中完成，LLM 僅負責分類、提取、格式化。

## 7. Token Budget 估算

| Scenario | 預估 input tokens | 預估 output tokens | 預估 total |
|---|---:|---:|---:|
| Scenario 1（辦公室綜合）| ~800 | ~400 | ~1,200 |
| Scenario 2（多燃料）| ~600 | ~350 | ~950 |
| Scenario 3（多冷媒）| ~700 | ~450 | ~1,150 |

所有 scenario 遠低於 50k tokens 限制。計算由 deterministic script 執行，LLM 不需長推理鏈。
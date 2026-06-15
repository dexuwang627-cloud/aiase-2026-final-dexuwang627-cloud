---
name: hello-aiase
description: Minimal smoke-test skill — echoes a greeting in the AIASE 2026 output contract. Use to verify the Hermes ↔ LiteLLM ↔ skill pipeline is wired up correctly.
version: 1.0.0
metadata:
  hermes:
    tags: [smoke-test, aiase-2026]
    category: utility
---

# Hello AIASE — Smoke Test

## When to Use

When the user invokes `/hello-aiase` with a JSON payload like `{"name":"world"}`. Use this skill to confirm Hermes can:

1. discover and load this skill,
2. invoke the script under `scripts/`,
3. relay the resulting fenced JSON block as the final output.

This skill performs **no LLM reasoning** — it just echoes structured input. If `/hello-aiase` works end-to-end, the rest of your AIASE 2026 setup is wired correctly.

## Procedure

1. Take the entire JSON payload from the user message verbatim (it should be an object; if missing, default to `{}`).
2. Extract `task_id` (default to an empty string if missing) and `name` (default to `"world"` if missing).
3. **Use the `terminal` tool (do not use process/background tools)** with the **absolute path** to run:

   ```
   python3 <skill_dir>/scripts/run.py --task_id "<task_id>" --name "<name>"
   ```

   where `<skill_dir>` is the directory Hermes reports when loading this skill.
4. `scripts/run.py` atomically writes the final result to the result file (path from the environment variable `AIASE_RESULT_PATH`, falling back to `./aiase_result.json`).
   **You do not need to output or repeat the JSON in the chat message.**

## Pitfalls

- Do not use `process`/background tools to invoke the script; use the synchronous `terminal` tool.
- Do not call the LLM to "improve" the greeting — this skill is intentionally deterministic.
- Do not output a fenced JSON block in the final chat message; the grader reads the result file, not the conversation.

## Verification

- The result file must exist and be a valid JSON object with fields `task_id`, `greeting`, and `ok=true`.
- If input contains `task_id`, the output `task_id` must equal the input `task_id`.

#!/usr/bin/env python3
"""open-carbon-calc-dexuwang627-cloud / scripts/run.py — file-based 輸出契約入口（原子寫入結果檔）。

⚠️ 自帶 resolve_result_path，不 import aiase_contract（安裝後找不到 repo 根模組）。
--payload 傳入整個結果 JSON 物件字串，run.py 負責寫入約定的結果檔路徑。
"""
import os, sys, json, argparse


def resolve_result_path() -> str:
    return os.environ.get("AIASE_RESULT_PATH") or os.path.join(os.getcwd(), "aiase_result.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task_id", required=True)
    ap.add_argument("--payload", required=True, help="JSON object string with the full carbon-calc result")
    a = ap.parse_args()
    try:
        result = json.loads(a.payload)
        if not isinstance(result, dict):
            raise ValueError("payload must be a JSON object")
    except (json.JSONDecodeError, ValueError) as e:
        print(f"ERROR: --payload is not a valid JSON object: {e}", file=sys.stderr)
        return 2
    result["task_id"] = a.task_id
    path = resolve_result_path()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
    os.replace(tmp, path)  # 原子寫入，避免讀到寫一半的檔
    print(f"written ok -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

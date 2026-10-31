"""真实模型连通性冒烟测试（基于合成数据）；不是基准测试，也不是校准研究。"""

import argparse
import json
from pathlib import Path

import httpx


def main():
    """起一条合成决策、请求推荐、记录回执，并写出一条连通性证据。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8765")
    parser.add_argument("--provider", choices=("ollama", "laya"), required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    with httpx.Client(base_url=args.base, headers={"X-QOne-Client": "web"}, timeout=180, trust_env=False) as client:
        # 合成决策：仅用于验证链路是否打通，数值不用于任何准确性/校准结论。
        decision = {
            "question": "【合成验收】今晚30分钟先做什么？",
            "domain": "learning",
            "success_criterion": "完成并保存一个Python练习",
            "deadline": "2030-01-01T00:00:00Z",
            "risk": "low",
            "reversible": True,
            "context": "已有练习题和开发环境，只剩30分钟。",
            "options": [{"id": "a", "label": "完成Python练习"}, {"id": "b", "label": "整理书桌"}],
            "baseline_option_id": "a",
        }
        response = client.post("/api/decisions", json=decision)
        response.raise_for_status()
        created = response.json()
        response = client.post(
            f'/api/decisions/{created["decision_id"]}/recommend',
            json={"provider": args.provider, "use_evidence": False},
        )
        response.raise_for_status()
        result = response.json()

        # 从 bootstrap 运行列表里找到本次决策对应的那条运行记录。
        run = None
        for candidate in client.get("/api/bootstrap").json()["runs"]:
            if candidate["decision_id"] == created["decision_id"]:
                run = candidate
                break
        if run is None:
            raise StopIteration("bootstrap run not found")

        receipt = {
            "purpose": "synthetic connectivity smoke, not accuracy/calibration evidence",
            "synthetic": True,
            "request": decision,
            "recommendation": result["recommendation"],
            "run": run,
        }
        if args.provider == "ollama":
            # 额外记录 ollama 的模型清单，便于复现本次用的模型版本。
            tags = httpx.get("http://127.0.0.1:11434/api/tags", timeout=5, trust_env=False).json()
            manifest = None
            for model in tags["models"]:
                if model["name"] == run["model"]:
                    manifest = model
                    break
            if manifest is None:
                raise StopIteration("model manifest not found")
            receipt["model_manifest"] = manifest
        Path(args.output).write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
        print(
            json.dumps(
                {
                    "provider": args.provider,
                    "option_id": result["recommendation"]["option_id"],
                    "duration_ms": run["duration_ms"],
                    "output": args.output,
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()

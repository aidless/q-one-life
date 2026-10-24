"""Real-model connectivity smoke on synthetic data; not a benchmark or calibration study."""
import argparse
import json
from pathlib import Path
import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8765")
    parser.add_argument("--provider", choices=("ollama", "laya"), required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    with httpx.Client(base_url=args.base, headers={"X-QOne-Client": "web"}, timeout=180, trust_env=False) as client:
        decision = {"question": "【合成验收】今晚30分钟先做什么？", "domain": "learning",
            "success_criterion": "完成并保存一个Python练习", "deadline": "2030-01-01T00:00:00Z",
            "risk": "low", "reversible": True, "context": "已有练习题和开发环境，只剩30分钟。",
            "options": [{"id": "a", "label": "完成Python练习"}, {"id": "b", "label": "整理书桌"}],
            "baseline_option_id": "a"}
        response = client.post("/api/decisions", json=decision)
        response.raise_for_status()
        created = response.json()
        response = client.post(f'/api/decisions/{created["decision_id"]}/recommend', json={"provider": args.provider, "use_evidence": False})
        response.raise_for_status()
        result = response.json()
        run = next(r for r in client.get("/api/bootstrap").json()["runs"] if r["decision_id"] == created["decision_id"])
        receipt = {"purpose": "synthetic connectivity smoke, not accuracy/calibration evidence", "synthetic": True,
            "request": decision, "recommendation": result["recommendation"], "run": run}
        if args.provider == "ollama":
            tags = httpx.get("http://127.0.0.1:11434/api/tags", timeout=5, trust_env=False).json()
            receipt["model_manifest"] = next(m for m in tags["models"] if m["name"] == run["model"])
        Path(args.output).write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({"provider": args.provider, "option_id": result["recommendation"]["option_id"],
            "duration_ms": run["duration_ms"], "output": args.output}, ensure_ascii=False))


if __name__ == "__main__":
    main()

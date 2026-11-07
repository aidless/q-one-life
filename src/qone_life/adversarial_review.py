"""对抗式评审：用独立的模型轮次对每条论断发起攻击。"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_URL = "http://127.0.0.1:3425/v1/chat/completions"

ATTACK_TEMPLATES = (
    (
        "counterexample",
        "Construct a concrete counterexample that falsifies this claim. If none exists, say NO_COUNTEREXAMPLE and explain why. Do not use tools or read files; answer from the claim and evidence text only.",
    ),
    (
        "boundary",
        "Identify the boundary conditions or edge cases where this claim breaks or becomes vacuous. If it holds universally, say NO_BOUNDARY_RISK. Do not use tools or read files; answer from the claim and evidence text only.",
    ),
    (
        "alternative",
        "Propose an alternative explanation that produces the same observation without this claim being true. If impossible, say NO_ALTERNATIVE. Do not use tools or read files; answer from the claim and evidence text only.",
    ),
)

CLEAN_MARKERS = ("NO_COUNTEREXAMPLE", "NO_BOUNDARY_RISK", "NO_ALTERNATIVE")
NON_ANSWER_MARKERS = (
    "```bash",
    "<tool_call>",
    "<tool_name>",
    "let me read",
    "let me examine",
    "i'll read",
    "i will read",
    "i'll examine",
    "i will examine",
)


class AdversarialError(RuntimeError):
    """对抗式评审无法运行时抛出的异常。"""


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_claims(ledger_text: str) -> list[dict[str, str]]:
    """从 Markdown 账本表格中解析出论断行。"""
    claims = []
    for line in ledger_text.splitlines():
        match = re.match(r"\|\s*(C\d+)\s*\|([^|]*)\|([^|]*)\|", line)
        if not match:
            continue
        claims.append({
            "claim_id": match.group(1).strip(),
            "text": match.group(2).strip(),
            "evidence": match.group(3).strip(),
        })
    return claims


class AdversarialReview:
    def __init__(self, url: str = DEFAULT_URL, *, timeout: int = 60) -> None:
        self.url = url
        self.timeout = timeout

    def _ask(self, model: str, prompt: str) -> str | None:
        """向模型发出一次提问，任何网络或解析错误都返回 None。"""
        body = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": 400,
        }).encode("utf-8")
        request = urllib.request.Request(
            self.url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError):
            return None
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return None
        return content.strip() or None

    def attack(
        self, ledger_path: Path, *, rounds: int, models: list[str], output_dir: Path,
        claim_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        if rounds < 1:
            raise AdversarialError("rounds must be at least 1")
        if not models:
            raise AdversarialError("at least one model is required")
        ledger_path = Path(ledger_path).expanduser().resolve()
        if not ledger_path.is_file():
            raise AdversarialError(f"ledger is missing: {ledger_path}")
        claims = parse_claims(ledger_path.read_text(encoding="utf-8"))
        if not claims:
            raise AdversarialError(f"no claims parsed from {ledger_path}")
        if claim_ids:
            wanted = set(claim_ids)
            claims = [claim for claim in claims if claim["claim_id"] in wanted]
            if not claims:
                raise AdversarialError(
                    f"none of the requested claims were found: {sorted(wanted)}"
                )

        output_dir.mkdir(parents=True, exist_ok=True)
        per_claim = []
        for claim in claims:
            objections: dict[str, dict[str, Any]] = {}
            inconclusive_rounds = 0
            for round_index in range(rounds):
                for model in models:
                    for kind, instruction in ATTACK_TEMPLATES:
                        prompt = (
                            f"Claim {claim['claim_id']}: {claim['text']}\n"
                            f"Evidence: {claim['evidence']}\n\n{instruction}"
                        )
                        answer = self._ask(model, prompt)
                        if answer is None:
                            inconclusive_rounds += 1
                            continue
                        lowered_answer = answer.lower()
                        if any(
                            marker in lowered_answer
                            for marker in NON_ANSWER_MARKERS
                        ):
                            inconclusive_rounds += 1
                            continue
                        # 模型明确表示"无懈可击"时视为本轮无异议。
                        upper_answer = answer.upper()
                        is_clean = False
                        for marker in CLEAN_MARKERS:
                            if marker in upper_answer:
                                is_clean = True
                                break
                        if is_clean:
                            continue
                        key = answer.strip()[:300]
                        entry = objections.setdefault(key, {
                            "text": key, "count": 0, "models": [], "kinds": [],
                        })
                        entry["count"] += 1
                        if model not in entry["models"]:
                            entry["models"].append(model)
                        if kind not in entry["kinds"]:
                            entry["kinds"].append(kind)
            ordered = sorted(objections.values(), key=lambda x: (-x["count"], x["text"]))

            # 结论优先级：只要出现无法判定的调用即判 inconclusive；
            # 否则有异议判 objected；都没有则判 clean。
            if inconclusive_rounds:
                verdict = "inconclusive"
            elif ordered:
                verdict = "objected"
            else:
                verdict = "clean"

            receipt = {
                "schema": "q-one-adversarial-v1",
                "claim_id": claim["claim_id"],
                "claim_text": claim["text"],
                "rounds": rounds,
                "models": models,
                "objections": ordered,
                "inconclusive_calls": inconclusive_rounds,
                "verdict": verdict,
                "generated_at": _now(),
            }
            path = output_dir / f"{claim['claim_id']}.json"
            path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            receipt["receipt_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            per_claim.append({
                "claim_id": claim["claim_id"], "verdict": verdict,
                "objections": len(ordered), "path": str(path),
                "receipt_sha256": receipt["receipt_sha256"],
            })

        # 汇总各结论条数。
        clean_count = 0
        objected_count = 0
        inconclusive_count = 0
        for c in per_claim:
            if c["verdict"] == "clean":
                clean_count += 1
            elif c["verdict"] == "objected":
                objected_count += 1
            elif c["verdict"] == "inconclusive":
                inconclusive_count += 1

        summary = {
            "schema": "q-one-adversarial-summary-v1",
            "ledger": str(ledger_path),
            "ledger_sha256": hashlib.sha256(ledger_path.read_bytes()).hexdigest(),
            "rounds": rounds,
            "models": models,
            "claims": per_claim,
            "clean": clean_count,
            "objected": objected_count,
            "inconclusive": inconclusive_count,
            "generated_at": _now(),
        }
        summary_path = output_dir / "summary.json"
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return summary

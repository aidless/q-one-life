"""Adversarial review: attack each claim with independent model rounds."""

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
        "Construct a concrete counterexample that falsifies this claim. If none exists, say NO_COUNTEREXAMPLE and explain why.",
    ),
    (
        "boundary",
        "Identify the boundary conditions or edge cases where this claim breaks or becomes vacuous. If it holds universally, say NO_BOUNDARY_RISK.",
    ),
    (
        "alternative",
        "Propose an alternative explanation that produces the same observation without this claim being true. If impossible, say NO_ALTERNATIVE.",
    ),
)

CLEAN_MARKERS = ("NO_COUNTEREXAMPLE", "NO_BOUNDARY_RISK", "NO_ALTERNATIVE")


class AdversarialError(RuntimeError):
    """Raised when the adversarial harness cannot run."""


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_claims(ledger_text: str) -> list[dict[str, str]]:
    """Extract claim rows from a markdown ledger table."""
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
                        if any(marker in answer.upper() for marker in CLEAN_MARKERS):
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
            verdict = "clean" if not ordered else ("inconclusive" if inconclusive_rounds else "objected")
            if inconclusive_rounds and not ordered:
                verdict = "inconclusive"
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

        summary = {
            "schema": "q-one-adversarial-summary-v1",
            "ledger": str(ledger_path),
            "ledger_sha256": hashlib.sha256(ledger_path.read_bytes()).hexdigest(),
            "rounds": rounds,
            "models": models,
            "claims": per_claim,
            "clean": sum(1 for c in per_claim if c["verdict"] == "clean"),
            "objected": sum(1 for c in per_claim if c["verdict"] == "objected"),
            "inconclusive": sum(1 for c in per_claim if c["verdict"] == "inconclusive"),
            "generated_at": _now(),
        }
        summary_path = output_dir / "summary.json"
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return summary

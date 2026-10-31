"""Seven-stage research production pipeline with hash-bound stage receipts."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .cloud_executor import CloudExecutionError, CloudExecutor, sha256_file
from .measurement import plan_experiment

STAGES = (
    "question",
    "hypothesis",
    "experiment_plan",
    "cloud_execution",
    "results",
    "claim_ledger",
    "draft",
)

PASSED = "passed"
FAILED = "failed"
BLOCKED = "blocked"


class ProductionError(RuntimeError):
    """Raised when a stage fails or a prior stage is not complete."""


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _slugify(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return text[:64] or "unnamed"


def _stage_path(root: Path, stage: str) -> Path:
    return root / f"{STAGES.index(stage) + 1:02d}-{stage}.json"


def _write_receipt(root: Path, stage: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = {
        "schema": "q-one-production-stage-v1",
        "stage": stage,
        "generated_at": _now(),
        **payload,
    }
    unsigned = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    body["receipt_sha256"] = hashlib.sha256(unsigned.encode("utf-8")).hexdigest()
    path = _stage_path(root, stage)
    path.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return body


def read_stage(root: Path, stage: str) -> dict[str, Any] | None:
    path = _stage_path(root, stage)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def require_previous(root: Path, stage: str) -> None:
    """Fail closed unless every earlier stage passed."""
    index = STAGES.index(stage)
    for prior in STAGES[:index]:
        receipt = read_stage(root, prior)
        if not receipt or receipt.get("status") != PASSED:
            raise ProductionError(
                f"stage {stage!r} requires {prior!r} to be passed; found "
                f"{receipt.get('status') if receipt else 'missing'}"
            )


class ResearchProduction:
    def __init__(self, workspace: str | Path, *, executor: CloudExecutor | None = None) -> None:
        self.workspace = Path(workspace).expanduser().resolve()
        self.executor = executor

    def _root(self, slug: str) -> Path:
        return self.workspace / "research" / "production" / slug

    # ---- stage 1 ------------------------------------------------------
    def register_question(self, slug: str, question_md: Path, venue: str) -> dict[str, Any]:
        if not question_md.is_file():
            raise ProductionError(f"question file is missing: {question_md}")
        text = question_md.read_text(encoding="utf-8").strip()
        if len(text) < 40:
            raise ProductionError("question must be at least 40 characters")
        root = self._root(slug)
        root.mkdir(parents=True, exist_ok=True)
        return _write_receipt(root, "question", {
            "status": PASSED,
            "slug": slug,
            "venue": venue,
            "question_path": str(question_md),
            "question_sha256": sha256_file(question_md),
            "question_chars": len(text),
            "inputs": [{"path": str(question_md), "sha256": sha256_file(question_md)}],
            "outputs": [],
        })

    # ---- stage 2 ------------------------------------------------------
    def register_hypothesis(self, slug: str, hypothesis: dict[str, Any]) -> dict[str, Any]:
        root = self._root(slug)
        require_previous(root, "hypothesis")
        for key in ("null_hypothesis", "alternative_hypothesis", "falsification_condition"):
            if not str(hypothesis.get(key) or "").strip():
                raise ProductionError(f"hypothesis missing required key: {key}")
        path = root / "hypothesis.json"
        path.write_text(json.dumps(hypothesis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return _write_receipt(root, "hypothesis", {
            "status": PASSED,
            "hypothesis_path": str(path),
            "hypothesis_sha256": sha256_file(path),
            "inputs": [{"path": str(path), "sha256": sha256_file(path)}],
            "outputs": [],
        })

    # ---- stage 3 ------------------------------------------------------
    def register_experiment_plan(
        self, slug: str, *, missing_evidence: str, proposed_experiment: str,
        resource_requirement: str, run_script: Path, inputs: list[Path],
        max_runtime_sec: int, max_disk_gb: float,
        estimated_duration_sec: int | None = None,
        statistical_power: float | None = None,
    ) -> dict[str, Any]:
        root = self._root(slug)
        require_previous(root, "experiment_plan")
        if not run_script.is_file():
            raise ProductionError(f"run script is missing: {run_script}")
        for item in inputs:
            if not Path(item).is_file():
                raise ProductionError(f"input is missing: {item}")
        plan = plan_experiment(
            claim_id=f"{slug}-experiment",
            missing_evidence=missing_evidence,
            proposed_experiment=proposed_experiment,
            resource_requirement=resource_requirement,
            estimated_duration_sec=estimated_duration_sec,
            statistical_power=statistical_power,
        )
        job = {
            "job_id": f"{slug}-{_now().replace(':', '').replace('-', '')}",
            "run_script": run_script.name,
            "inputs": [Path(p).name for p in inputs],
            "max_runtime_sec": int(max_runtime_sec),
            "max_disk_gb": float(max_disk_gb),
        }
        job_dir = root / "job"
        job_dir.mkdir(parents=True, exist_ok=True)
        (job_dir / "job.json").write_text(json.dumps(job, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        target_script = job_dir / run_script.name
        target_script.write_bytes(run_script.read_bytes())
        target_script.chmod(0o755)
        for item in inputs:
            dest = job_dir / Path(item).name
            if dest != Path(item).resolve():
                dest.write_bytes(Path(item).read_bytes())
        plan_path = root / "experiment-plan.json"
        plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return _write_receipt(root, "experiment_plan", {
            "status": PASSED,
            "plan_path": str(plan_path),
            "plan_sha256": sha256_file(plan_path),
            "job_dir": str(job_dir),
            "job_id": job["job_id"],
            "job_sha256": sha256_file(job_dir / "job.json"),
            "approval_required": plan["approval_required"],
            "estimated_duration_sec": plan["estimated_duration_sec"],
            "statistical_power": plan["statistical_power"],
            "inputs": [{"path": str(plan_path), "sha256": sha256_file(plan_path)}],
            "outputs": [{"path": str(job_dir / "job.json"), "sha256": sha256_file(job_dir / "job.json")}],
        })

    # ---- stage 4 ------------------------------------------------------
    def execute_cloud(self, slug: str, *, poll_interval: int = 10) -> dict[str, Any]:
        root = self._root(slug)
        require_previous(root, "cloud_execution")
        plan_receipt = read_stage(root, "experiment_plan")
        if plan_receipt.get("approval_required"):
            raise ProductionError("experiment plan requires approval; refusing automatic execution")
        if self.executor is None:
            raise ProductionError("no cloud executor configured")
        job_dir = Path(plan_receipt["job_dir"])
        max_runtime = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))["max_runtime_sec"]
        try:
            submitted = self.executor.submit(job_dir)
            final = self.executor.wait(submitted["job_id"], max_runtime_sec=max_runtime,
                                       poll_interval=poll_interval)
        except CloudExecutionError as exc:
            raise ProductionError(f"cloud execution failed: {exc}") from exc
        status = PASSED if final["state"] == "succeeded" else FAILED
        return _write_receipt(root, "cloud_execution", {
            "status": status,
            "job_id": submitted["job_id"],
            "remote_dir": submitted["remote_dir"],
            "final_state": final["state"],
            "submitted_at": submitted["submitted_at"],
            "inputs": [{"path": str(job_dir / "job.json"), "sha256": sha256_file(job_dir / "job.json")}],
            "outputs": [],
        })

    # ---- stage 5 ------------------------------------------------------
    def collect_results(self, slug: str, target_dir: str | Path) -> dict[str, Any]:
        root = self._root(slug)
        require_previous(root, "results")
        if self.executor is None:
            raise ProductionError("no cloud executor configured")
        job = read_stage(root, "cloud_execution")
        fetched = self.executor.fetch(job["job_id"], target_dir)
        if not fetched["files"]:
            return _write_receipt(root, "results", {
                "status": FAILED, "reason": "no output files were produced",
                "job_id": job["job_id"], "inputs": [], "outputs": [],
            })
        receipt = _write_receipt(root, "results", {
            "status": PASSED,
            "job_id": job["job_id"],
            "target": fetched["target"],
            "files": fetched["files"],
            "log_hashes": fetched["logs"],
            "inputs": [{"path": fetched["target"], "sha256": _dir_hash(Path(fetched["target"]))}],
            "outputs": fetched["files"],
        })
        return receipt

    # ---- stage 6 ------------------------------------------------------
    def write_claim_ledger(self, slug: str, claims: list[dict[str, Any]]) -> dict[str, Any]:
        root = self._root(slug)
        require_previous(root, "claim_ledger")
        if not claims:
            raise ProductionError("at least one claim is required")
        for claim in claims:
            for key in ("claim_id", "text", "evidence", "state"):
                if not str(claim.get(key) or "").strip():
                    raise ProductionError(f"claim missing required key: {key}")
            if claim["state"] not in {"verified", "candidate", "inconclusive", "blocked"}:
                raise ProductionError(f"invalid claim state: {claim['state']}")
        ledger = root / "CLAIM_LEDGER.md"
        lines = ["# CLAIM_LEDGER.md", "", "| ID | Claim | Evidence | State |", "|---|---|---|---|"]
        for claim in claims:
            lines.append(
                f"| {claim['claim_id']} | {claim['text']} | {claim['evidence']} | {claim['state']} |"
            )
        ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return _write_receipt(root, "claim_ledger", {
            "status": PASSED,
            "ledger_path": str(ledger),
            "ledger_sha256": sha256_file(ledger),
            "claim_count": len(claims),
            "claim_states": _count_states(claims),
            "inputs": [{"path": str(ledger), "sha256": sha256_file(ledger)}],
            "outputs": [],
        })

    # ---- stage 7 ------------------------------------------------------
    def write_draft(self, slug: str, manuscript: Path, *, venue: str) -> dict[str, Any]:
        root = self._root(slug)
        require_previous(root, "draft")
        if not manuscript.is_file():
            raise ProductionError(f"manuscript is missing: {manuscript}")
        target = root / "draft" / manuscript.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(manuscript.read_bytes())
        return _write_receipt(root, "draft", {
            "status": PASSED,
            "venue": venue,
            "draft_path": str(target),
            "draft_sha256": sha256_file(target),
            "inputs": [{"path": str(manuscript), "sha256": sha256_file(manuscript)}],
            "outputs": [{"path": str(target), "sha256": sha256_file(target)}],
        })

    # ---- driver -------------------------------------------------------
    def status(self, slug: str) -> dict[str, Any]:
        root = self._root(slug)
        stages = {}
        for stage in STAGES:
            receipt = read_stage(root, stage)
            stages[stage] = receipt.get("status") if receipt else "missing"
        return {"slug": slug, "root": str(root), "stages": stages}


def _dir_hash(path: Path) -> str:
    digest = hashlib.sha256()
    for file in sorted(path.rglob("*")):
        if file.is_file():
            digest.update(file.relative_to(path).as_posix().encode("utf-8"))
            digest.update(file.read_bytes())
    return digest.hexdigest()


def _count_states(claims: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for claim in claims:
        counts[claim["state"]] = counts.get(claim["state"], 0) + 1
    return counts


def produce(
    workspace: str | Path, *, question_md: str | Path, venue: str, slug: str | None = None,
    executor: CloudExecutor | None = None,
) -> dict[str, Any]:
    """Run the stages that need no external inputs and return current status."""
    question = Path(question_md).expanduser().resolve()
    resolved_slug = slug or _slugify(question.stem)
    pipeline = ResearchProduction(workspace, executor=executor)
    pipeline.register_question(resolved_slug, question, venue)
    return pipeline.status(resolved_slug)

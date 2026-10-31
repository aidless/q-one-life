"""研究覆盖层脚手架与证据门控计划。

- create_research_scaffold：在一篇规范论文外生成一个**非破坏性**覆盖层（不复制、不改写源稿）。
- build_research_plan：根据覆盖层里已有的证据/门禁，给出下一步动作清单。
- optimize_portfolio：仅按可观测的证据完整度为论文家族排序（不是质量预测）。

所有函数都只给出建议或只读审计，不会擅自上传、发布或改写源稿。
"""
from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..research import PROJECT_SCHEMA, sha256_file, validate_research_project
from ._helpers import (
    PLAN_SCHEMA,
    SCAFFOLD_SCHEMA,
    ResearchFactoryError,
    _family_project,
    _finding,
    _load_json,
    _now,
    _write_json,
)


def create_research_scaffold(
    portfolio: dict[str, Any],
    *,
    family_id: str,
    output_dir: str | Path,
    target: str = "arxiv",
    source: str | Path | None = None,
    evidence_paths: Iterable[str | Path] = (),
    generated_at: str | None = None,
) -> dict[str, Any]:
    """为一个规范论文家族创建一个非破坏性覆盖层。"""
    project_record = _family_project(portfolio, family_id)
    source_path = Path(source or project_record["primary_source"]).expanduser().resolve()
    if not source_path.is_file():
        raise ResearchFactoryError(f"source manuscript is missing: {source_path}")

    # 先校验外部证据是否都存在，避免生成到一半才失败。
    external = [str(Path(path).expanduser().resolve()) for path in evidence_paths]
    missing_evidence = [path for path in external if not Path(path).is_file()]
    if missing_evidence:
        raise ResearchFactoryError(
            "evidence source(s) are missing: " + ", ".join(missing_evidence)
        )

    # 输出目录必须不存在或为空，避免覆盖已有内容。
    root = Path(output_dir).expanduser().resolve()
    if root.exists() and any(root.iterdir()):
        raise ResearchFactoryError(f"scaffold output directory is not empty: {root}")
    root.mkdir(parents=True, exist_ok=True)
    (root / "evidence").mkdir()

    timestamp = generated_at or _now()
    source_hash = sha256_file(source_path)

    # 1) 源身份记录：记录源稿路径、哈希、大小与修改时间。
    source_record = {
        "schema": "q-one-source-record-v1",
        "generated_at": timestamp,
        "family_id": family_id,
        "portfolio_project_id": project_record.get("project_id"),
        "source_path": str(source_path),
        "source_sha256": source_hash,
        "source_bytes": source_path.stat().st_size,
        "source_modified_at": datetime.fromtimestamp(
            source_path.stat().st_mtime, timezone.utc
        ).isoformat().replace("+00:00", "Z"),
        "title": project_record.get("title"),
        "project_type": project_record.get("project_type"),
    }
    source_record_path = root / "evidence" / "source_record.json"
    _write_json(source_record_path, source_record)

    # 证据清单从源记录开始（状态为 candidate，需后续校验）。
    evidence: list[dict[str, Any]] = [
        {
            "path": "evidence/source_record.json",
            "sha256": sha256_file(source_record_path),
            "state": "candidate",
            "origin": str(source_path),
            "description": "Q-One source identity record; this is not manuscript recomputation.",
        }
    ]

    # 2) 若提供了外部证据，写一份外部证据指针清单。
    if external:
        evidence_sources = {
            "schema": "q-one-evidence-sources-v1",
            "generated_at": timestamp,
            "sources": [
                {
                    "path": path,
                    "sha256": sha256_file(Path(path)),
                    "state": "candidate",
                }
                for path in external
                if Path(path).is_file()
            ],
            "missing": [],
        }
        evidence_sources_path = root / "evidence" / "sources.json"
        _write_json(evidence_sources_path, evidence_sources)
        evidence.append(
            {
                "path": "evidence/sources.json",
                "sha256": sha256_file(evidence_sources_path),
                "state": "candidate",
                "origin": "user-supplied source references",
                "description": "External evidence pointers; state is candidate until checked.",
            }
        )

    # 新建的覆盖层必然带着这些未解决的门，记录下来提醒后续步骤。
    blockers = [
        "No claims have been registered from the current manuscript.",
        "No claim ledger has been independently verified.",
        "No bibliography verification or clean-room arXiv compile receipt exists.",
        "No scientific review has been closed against this overlay's current hashes.",
        "arXiv upload requires a separate user authorization and account action.",
    ]
    project = {
        "schema": PROJECT_SCHEMA,
        "paper_id": family_id,
        "title": project_record.get("title"),
        "status": "unknown",
        "target": target,
        "root": str(root),
        "origin": str(source_path),
        "manuscript": {
            "path": str(source_path),
            "sha256": source_hash,
            "published_source_sha256": None,
            "matches_published_source": None,
        },
        "evidence": evidence,
        "claims": [],
        "experiments": [],
        "reviews": [],
        "package": {
            "state": "not-started",
            "files": [],
            "blockers": blockers,
        },
        "measurements": [],
        "notes": [
            "Scaffold generated from the Q-One paper portfolio.",
            "The source manuscript was not modified or copied.",
            "No readiness, acceptance, award, or submission state is implied.",
        ],
    }
    project_path = root / "project.json"
    _write_json(project_path, project)

    # 3) 生成人读的说明文件：账本、流水线、写作须知、README。
    ledger = f"""# {project['title']} Claim Ledger

Manuscript: `{source_path}`
Source SHA-256: `{source_hash}`

This overlay was created without modifying the source manuscript. Register only
claims that are present in the manuscript, and bind every numeric value to an
evidence file plus field and a recomputation command.

| ID | Claim | Evidence file + field | Numeric values | Verification | Status |
|---|---|---|---|---|---|

_No claims have been registered yet._
"""
    (root / "CLAIM_LEDGER.md").write_text(ledger, encoding="utf-8")

    pipeline = f"""# Research pipeline

Source: `{source_path}`
Source SHA-256: `{source_hash}`

| Stage | State | Required output |
|---|---|---|
| source-identity | candidate | Exact source hash and publication identity |
| claim-ledger | pending | Registered claims with evidence fields and recomputation |
| evidence-recomputation | pending | Reproduced numeric claims or explicit blockers |
| citation-verification | pending | Every citation resolved or marked unresolved |
| scientific-review | pending | Closed method, statistics, reproduction and writing findings |
| arxiv-package | pending | Clean source tree, bibliography, metadata and hashes |
| external-submission | locked | User authorization and account action |

Unknown evidence is not converted to zero. A ready state requires every
applicable gate to pass against the same manuscript hash.
"""
    (root / "PIPELINE.md").write_text(pipeline, encoding="utf-8")

    brief = f"""# Authoring brief

Title: **{project['title']}**
Target: `{target}`
Manuscript: `{source_path}`
Source SHA-256: `{source_hash}`

The agent may:

- summarize and reorganize only registered claims;
- draft sections from evidence-bound claims;
- identify missing evidence, citations and experiments;
- propose figures from supplied data and reproducible scripts.

The agent must not:

- invent numbers, experiments, references, authors, licenses or receipts;
- upgrade an `inconclusive` claim to `verified`;
- move a `blocked` claim into the manuscript;
- upload or publish without a separate user action.

Write only after `CLAIM_LEDGER.md` contains the claims relevant to the requested
section. Preserve negative and failed results.
"""
    (root / "AUTHORING_BRIEF.md").write_text(brief, encoding="utf-8")

    readme = f"""# Q-One research overlay

This is an external overlay for **{project['title']}**.

- Source: `{source_path}`
- Source SHA-256: `{source_hash}`
- Portfolio family: `{family_id}`
- Target: `{target}`
- Status: `unknown`

The scaffold does not copy, rewrite or publish the source. Start with
`CLAIM_LEDGER.md`, then run `research-plan` and `research-validate`.
"""
    (root / "README.md").write_text(readme, encoding="utf-8")

    # 4) 用研究项目的校验器自检，生成物必须合法。
    validation = validate_research_project(root)
    if not validation["valid"]:
        raise ResearchFactoryError(
            "generated scaffold is invalid: " + "; ".join(validation["errors"])
        )

    return {
        "schema": SCAFFOLD_SCHEMA,
        "generated_at": timestamp,
        "family_id": family_id,
        "root": str(root),
        "source_path": str(source_path),
        "source_sha256": source_hash,
        "project_path": str(project_path),
        "validation": validation,
    }


def build_research_plan(project_root: str | Path) -> dict[str, Any]:
    """为一个覆盖层生成「下一步证据门控动作」清单。"""
    root = Path(project_root).expanduser().resolve()
    validation = validate_research_project(root)
    project_path = root / "project.json"
    if not project_path.is_file():
        raise ResearchFactoryError(f"project.json is missing: {root}")

    project = _load_json(project_path)
    manuscript = project.get("manuscript", {})
    claims = project.get("claims", [])
    experiments = project.get("experiments", [])
    reviews = project.get("reviews", [])
    package = project.get("package", {})
    gate_receipts = [
        item for item in project.get("gate_receipts", []) if isinstance(item, dict)
    ]

    # 收集各类待处理项，供后续生成动作与判定阶段状态。
    mismatch = manuscript.get("matches_published_source") is False

    blocked_claims = [
        claim.get("claim_id")
        for claim in claims
        if isinstance(claim, dict) and claim.get("state") == "blocked"
    ]
    pending_claims = [
        claim.get("claim_id")
        for claim in claims
        if isinstance(claim, dict)
        and claim.get("state") in {"candidate", "inconclusive", "unknown"}
    ]
    reproduced = [
        item.get("experiment_id")
        for item in experiments
        if isinstance(item, dict) and item.get("state") == "reproduced"
    ]
    failed_experiments = [
        item.get("experiment_id")
        for item in experiments
        if isinstance(item, dict) and item.get("state") in {"failed", "blocked"}
    ]

    # 有未关闭的 Critical/Major 评审结论时，评审阶段视为被卡住。
    open_major: list[Any] = []
    for item in reviews:
        if not isinstance(item, dict):
            continue
        if item.get("state") != "open":
            continue
        if int(item.get("critical", 0)) > 0 or int(item.get("major", 0)) > 0:
            open_major.append(item.get("review_id"))

    # 数字类门禁（scope 为 numbers/reproducibility）与引用类门禁。
    numeric_gates = [
        item for item in gate_receipts if item.get("scope") in {"numbers", "reproducibility"}
    ]
    failed_numeric_gates = [
        item.get("gate_id")
        for item in numeric_gates
        if item.get("state") in {"failed", "blocked"}
    ]
    passed_numeric_gates = [
        item for item in numeric_gates if item.get("state") == "passed"
    ]
    bound_numeric_gates = [
        item
        for item in passed_numeric_gates
        if item.get("source_sha256") == manuscript.get("sha256")
    ]
    unbound_numeric_gates = [
        item.get("gate_id")
        for item in passed_numeric_gates
        if item.get("source_sha256") != manuscript.get("sha256")
    ]

    citation_gates = [
        item for item in gate_receipts if item.get("scope") == "citations"
    ]
    failed_citation_gates = [
        item.get("gate_id")
        for item in citation_gates
        if item.get("state") in {"failed", "blocked"}
    ]
    passed_citation_gates = [
        item for item in citation_gates if item.get("state") == "passed"
    ]
    bound_citation_gates = [
        item
        for item in passed_citation_gates
        if item.get("source_sha256") == manuscript.get("sha256")
    ]
    unbound_citation_gates = [
        item.get("gate_id")
        for item in passed_citation_gates
        if item.get("source_sha256") != manuscript.get("sha256")
    ]

    failed_gate_receipts = [
        item.get("gate_id")
        for item in gate_receipts
        if item.get("state") in {"failed", "blocked"}
    ]

    # 逐一判定各阶段状态（blocked / verified / candidate / pending）。
    if mismatch:
        source_state = "blocked"
    elif manuscript.get("matches_published_source") is True:
        source_state = "verified"
    else:
        source_state = "candidate"

    if not claims:
        ledger_state = "pending"
    elif blocked_claims:
        ledger_state = "blocked"
    elif pending_claims:
        ledger_state = "candidate"
    else:
        ledger_state = "verified"

    if failed_experiments or failed_numeric_gates:
        recomputation_state = "blocked"
    elif bound_numeric_gates and not unbound_numeric_gates:
        recomputation_state = "verified"
    elif passed_numeric_gates:
        recomputation_state = "candidate"
    elif reproduced and not pending_claims:
        recomputation_state = "verified"
    else:
        recomputation_state = "pending"

    # 在源稿目录与覆盖层里查找可用的参考文献文件。
    manuscript_path = Path(str(manuscript.get("path", "")))
    if not manuscript_path.is_absolute():
        manuscript_path = root / manuscript_path
    source_dir = manuscript_path.parent if manuscript_path.is_file() else root
    bibliography_candidates = list(root.glob("**/*.bib")) + list(
        source_dir.glob("*.bib")
    ) + list(source_dir.glob("*.bbl")) + list(source_dir.glob("bibliography.tex"))

    if failed_citation_gates:
        citation_state = "blocked"
    elif bound_citation_gates and not unbound_citation_gates:
        citation_state = "verified"
    elif bibliography_candidates:
        citation_state = "candidate"
    else:
        citation_state = "pending"

    # 评审阶段：有未关闭的 Critical/Major 则 blocked；有评审且无 open 则 verified；否则 pending。
    if open_major:
        review_state = "blocked"
    else:
        has_open_review = False
        for item in reviews:
            if isinstance(item, dict) and item.get("state") == "open":
                has_open_review = True
                break
        # 按项目风格，这里刻意用 if/else 而非三元表达式，保持主路径平铺可读。
        if reviews and not has_open_review:  # noqa: SIM108
            review_state = "verified"
        else:
            review_state = "pending"

    package_blockers = package.get("blockers", [])
    if package_blockers:
        package_state = "blocked"
    elif validation.get("ready"):
        package_state = "verified"
    else:
        package_state = "pending"

    if citation_state == "verified":
        citation_details = (
            f"Passed citation gates bound to the current source: "
            f"{len(bound_citation_gates)}."
        )
    else:
        citation_details = "A bibliography file is only a candidate until citations resolve."

    stages = [
        {
            "stage": "source-identity",
            "state": source_state,
            "details": "The local source hash is checked; publication identity is separate.",
        },
        {
            "stage": "claim-ledger",
            "state": ledger_state,
            "details": "Claims must be registered and bound to evidence fields.",
        },
        {
            "stage": "evidence-recomputation",
            "state": recomputation_state,
            "details": (
                f"Native gates passed: {len(passed_numeric_gates)}; "
                f"bound to the current source: {len(bound_numeric_gates)}. "
                "A completed experiment is not a reproduced experiment."
            ),
        },
        {
            "stage": "citation-verification",
            "state": citation_state,
            "details": citation_details,
        },
        {
            "stage": "scientific-review",
            "state": review_state,
            "details": "Open Critical or Major findings block the package.",
        },
        {
            "stage": "arxiv-package",
            "state": package_state,
            "details": "Mechanical packageability is separate from scientific readiness.",
        },
        {
            "stage": "external-submission",
            "state": "locked",
            "details": "Upload, account use and publication require explicit user authorization.",
        },
    ]

    # 依据当前状态逐条追加「下一步动作」。每条都写清优先级、理由与完成判据。
    actions: list[dict[str, str]] = []

    if not validation.get("valid"):
        actions.append(
            _finding(
                "repair_overlay_integrity",
                "P0",
                "The overlay itself fails schema, hash, ledger or manifest validation.",
                "`research-validate` returns valid=true against the current bytes.",
            )
        )
    if mismatch:
        actions.append(
            _finding(
                "resynchronize_published_source",
                "P0",
                "The local manuscript does not match the published source hash.",
                "The exact source is recovered or the publication receipt is refreshed.",
            )
        )
    if not claims:
        actions.append(
            _finding(
                "register_claims",
                "P0",
                "No manuscript claims are in the overlay.",
                "Every numeric and causal claim has an ID, location, evidence field and status.",
            )
        )
    if pending_claims:
        actions.append(
            _finding(
                "close_inconclusive_claims",
                "P0",
                f"Claims are not verified: {', '.join(pending_claims[:12])}.",
                "Each claim is verified, explicitly hedged with missing evidence, or removed.",
            )
        )
    if blocked_claims:
        actions.append(
            _finding(
                "remove_or_repair_blocked_claims",
                "P0",
                f"Blocked claims cannot enter strong prose: {', '.join(blocked_claims)}.",
                "Blocked claims are absent from manuscript assertions or repaired.",
            )
        )
    if failed_gate_receipts:
        actions.append(
            _finding(
                "repair_failed_native_gates",
                "P0",
                f"Native gate receipts failed: {', '.join(failed_gate_receipts)}.",
                "Each failed gate is repaired or explicitly blocked in the manuscript scope.",
            )
        )
    if unbound_numeric_gates:
        actions.append(
            _finding(
                "bind_native_gate_to_current_source",
                "P1",
                f"Passed numeric gates are not bound to the current source: "
                f"{', '.join(str(item) for item in unbound_numeric_gates)}.",
                "Re-run each gate against the current source and bind its exact hash.",
            )
        )
    if failed_citation_gates:
        actions.append(
            _finding(
                "repair_failed_citation_gates",
                "P0",
                f"Native citation gates failed: {', '.join(failed_citation_gates)}.",
                "Every citation resolves against the current source or is explicitly removed.",
            )
        )
    if unbound_citation_gates:
        actions.append(
            _finding(
                "bind_citation_gate_to_current_source",
                "P1",
                "Passed citation gates are not bound to the current source: "
                + ", ".join(str(item) for item in unbound_citation_gates)
                + ".",
                "Re-run the citation audit against the current source and bind its exact hash.",
            )
        )
    if not reproduced and not passed_numeric_gates:
        actions.append(
            _finding(
                "reproduce_required_numeric_claims",
                "P1",
                "No experiment has a reproduced receipt in this overlay.",
                "Required numeric claims have a command, environment and matching output hash.",
            )
        )
    if not bibliography_candidates:
        actions.append(
            _finding(
                "build_bibliography",
                "P1",
                "No bibliography file is visible in the overlay.",
                "Every citation resolves to a source record or is marked unresolved.",
            )
        )
    if open_major:
        actions.append(
            _finding(
                "close_scientific_review",
                "P0",
                f"Open review findings remain: {', '.join(open_major)}.",
                "No open Critical or Major finding remains against the current hashes.",
            )
        )
    if package_blockers:
        actions.append(
            _finding(
                "resolve_package_blockers",
                "P1",
                "The package manifest contains unresolved blockers.",
                "The source tree, bibliography, compiled PDF and hashes are complete.",
            )
        )

    # 外部提交永远需要用户授权，作为常驻动作放在最后。
    actions.append(
        _finding(
            "external_submission_gate",
            "external",
            "Q-One cannot perform an account-level arXiv action on its own.",
            "The user explicitly authorizes upload and checks metadata, license and author list.",
        )
    )

    return {
        "schema": PLAN_SCHEMA,
        "generated_at": _now(),
        "root": str(root),
        "paper_id": project.get("paper_id"),
        "title": project.get("title"),
        "target": project.get("target"),
        "validation_valid": validation.get("valid"),
        "validation_ready": validation.get("ready"),
        "gate_summary": {
            "receipts": len(gate_receipts),
            "passed_numeric": len(passed_numeric_gates),
            "bound_numeric_to_current_source": len(bound_numeric_gates),
            "unbound_passed_numeric": unbound_numeric_gates,
            "passed_citations": len(passed_citation_gates),
            "bound_citations_to_current_source": len(bound_citation_gates),
            "unbound_passed_citations": unbound_citation_gates,
            "failed_or_blocked": failed_gate_receipts,
        },
        "stages": stages,
        "next_actions": sorted(actions, key=lambda item: (item["priority"], item["action_id"])),
        "global_readiness_score": None,
        "notes": [
            "No global score is produced.",
            "Unknown is not zero.",
            "A mechanical package check is not scientific readiness.",
        ],
    }


def render_plan_markdown(plan: dict[str, Any]) -> str:
    """把研究计划渲染成 Markdown。"""
    lines = [
        f"# Research plan: {plan['title']}",
        "",
        f"Paper ID: `{plan['paper_id']}`",
        f"Validation: valid=`{plan['validation_valid']}`, ready=`{plan['validation_ready']}`",
        "",
        "## Stages",
        "",
        "| Stage | State | Notes |",
        "|---|---|---|",
    ]
    for stage in plan["stages"]:
        lines.append(f"| {stage['stage']} | {stage['state']} | {stage['details']} |")

    lines.extend(
        [
            "",
            "## Next actions",
            "",
            "| Priority | Action | Owner | Done when |",
            "|---|---|---|---|",
        ]
    )
    for action in plan["next_actions"]:
        lines.append(
            f"| {action['priority']} | {action['action_id']} | {action['owner']} | "
            f"{action['done_when']} |"
        )

    lines.extend(["", "No submission action is implied by this plan.", ""])
    return "\n".join(lines)


def write_plan(plan: dict[str, Any], output: str | Path, markdown: str | Path | None = None) -> None:
    """写出研究计划：JSON 必写，Markdown 按需写出。"""
    _write_json(output, plan)
    if markdown is not None:
        target = Path(markdown)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_plan_markdown(plan), encoding="utf-8")


def optimize_portfolio(
    portfolio: dict[str, Any],
    pilots: list[dict[str, Any]],
    capacity: int,
) -> dict[str, Any]:
    """仅按可观测信号，按证据投资回报（ROI）为论文家族排序。

    这里的 publishability 指证据完整度，不是质量预测，也不授权发表。
    """
    if capacity < 1:
        raise ResearchFactoryError("capacity must be at least 1")

    projects = portfolio.get("projects") or []

    # 建立「标题→试点」「来源片段→试点」两张查找表。
    overlay_by_title: dict[str, dict[str, Any]] = {}
    overlay_by_source: dict[str, dict[str, Any]] = {}
    for pilot in pilots:
        for title in pilot.get("title_contains_any", []) or []:
            overlay_by_title[str(title).lower()] = pilot
        for fragment in pilot.get("source_contains_any", []) or []:
            overlay_by_source[str(fragment)] = pilot

    # 从 research 目录里按试点 id 解析覆盖层目录。
    research_root = Path("research")
    overlay_dirs: dict[str, Path] = {}
    if research_root.is_dir():
        for candidate in research_root.glob("*/project.json"):
            overlay_dirs[candidate.parent.name] = candidate.parent

    ranked: list[dict[str, Any]] = []
    for project in projects:
        title = str(project.get("title") or "")
        primary_source = str(project.get("primary_source") or "")

        # 先按标题匹配试点；未命中再按来源片段匹配。
        overlay = overlay_by_title.get(title.lower())
        if overlay is None:
            for fragment, pilot in overlay_by_source.items():
                if fragment and fragment in primary_source:
                    overlay = pilot
                    break

        # 解析该试点对应的覆盖层目录：优先显式 overlay_path，否则按 id 后缀匹配。
        overlay_path: Path | None = None
        if overlay:
            explicit = overlay.get("overlay_path")
            if explicit:
                overlay_path = Path(str(explicit))
            else:
                pilot_id = str(overlay.get("id") or "")
                suffix = pilot_id.split("-", 1)[-1] if "-" in pilot_id else pilot_id
                for name, directory in overlay_dirs.items():
                    if suffix and suffix in name:
                        overlay_path = directory
                        break

        # 统计覆盖层里各状态的主张数量，以及失败/卡住的门数量。
        blocked = 0
        candidate = 0
        verified = 0
        missing_gates = 0
        if overlay_path and (overlay_path / "project.json").is_file():
            try:
                payload = json.loads((overlay_path / "project.json").read_text(encoding="utf-8"))
            except ValueError:
                payload = {}

            for claim in payload.get("claims", []) or []:
                state = claim.get("state")
                if state == "blocked":
                    blocked += 1
                elif state in {"candidate", "inconclusive", "unknown"}:
                    candidate += 1
                elif state == "verified":
                    verified += 1

            gates = payload.get("gate_receipts", []) or []
            for gate in gates:
                if isinstance(gate, dict) and gate.get("state") in {"failed", "blocked"}:
                    missing_gates += 1

        # 计算证据缺口、可发表度与 ROI（可发表度 / 闭合成本）。
        total = blocked + candidate + verified
        close_cost = blocked + missing_gates
        evidence_gap = (blocked + candidate) / total if total else 1.0
        publishability = verified / total if total else 0.0
        roi = publishability / close_cost if close_cost > 0 else publishability

        ranked.append({
            "family_id": project.get("family_id"),
            "title": title,
            "priority_band": project.get("priority_band"),
            "verified": verified,
            "candidate": candidate,
            "blocked": blocked,
            "missing_gates": missing_gates,
            "close_cost": close_cost,
            "evidence_gap": round(evidence_gap, 6),
            "publishability": round(publishability, 6),
            "roi": round(roi, 6),
        })

    # 排序：ROI 降序 → 闭合成本升序 → 标题升序；取前 capacity 个。
    ranked.sort(key=lambda item: (-item["roi"], item["close_cost"], item["title"]))
    selected = ranked[:capacity]

    return {
        "schema": "q-one-allocation-v1",
        "capacity": capacity,
        "considered": len(ranked),
        "ranked": selected,
        "note": (
            "ROI uses evidence completeness only. It is not a paper-quality "
            "score and does not authorize publication."
        ),
    }

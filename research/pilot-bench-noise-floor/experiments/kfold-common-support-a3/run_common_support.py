#!/usr/bin/env python3
"""A3: test the k-fold LOO comparison on one generator-and-system support.

Independent review finding A3: ``followup_ec63_kfold.py`` aligns the k-fold
floor and leaderboard on a common k-fold domain, but its ``LOO_on_kfold_domain``
arm does not require every generator's own LOO gold to be defined.  Missing LOO
gold is silently excluded from each generator's denominator.  The observed
coherence LOO margin 0.4711 may therefore be a support artifact rather than a
same-domain violation of Proposition 4.

This runner does not modify the native repository.  It:

1. rebuilds the four m25 vote tables with the pinned native generator;
2. reproduces the recorded k-fold and leaky LOO-on-k-fold-domain point values;
3. constructs a joint support requiring the main gold, every generator's LOO
   gold, every k-fold gold, and every generator/system answer row;
4. recomputes both LOO and k-fold margins on that joint support; and
5. checks label identity and bootstrap replicate-invariance.

The output deliberately omits timestamps and temporary paths so two accepted
runs can be compared byte for byte.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

TASKS = ("factuality", "coherence", "relevance", "preference")
SEED = 20261001
N_BOOT = 2000
K_FOLD = 4
POINT_TOL = 1e-9
RECORDED_TOL = 1e-9

PINNED_NATIVE = {
    "tools/bench-noise-floor/audit.py": "2fbb95fc6601c855e8df09df4bbd712883411d901209d5ee497cd73d7e23876b",
    "tools/bench-noise-floor/followup_common.py": "66aeb942b6bb8526f4467d244b9a04bad4d4023eaaf95b87aef0c1307912ee54",
    "tools/bench-noise-floor/followup_ec63_kfold.py": "e0528fa164e2b7de63fb9711686c9f1882f083d170fa777251f878f0301ee5fb",
    "tools/bench-noise-floor/make_m25_votes.py": "defa82564452cb7e933d331f230df3fda958ffa4d3587416375e81f1a0ec0236",
    "papers/bench_noise_floor/evidence/strict_review_followup/EC63_kfold_vs_loo.json": "f80712e34f86e71fd75d71d3c6224dfd0af466bccef244ae9c23cd31e6a62b50",
}


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def support_digest(items: set[str]) -> str:
    text = "|".join(sorted(str(item) for item in items))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_modules(external_root: Path):
    tools = external_root / "tools" / "bench-noise-floor"
    sys.path.insert(0, str(tools))
    audit = importlib.import_module("audit")
    common = importlib.import_module("followup_common")
    kfold = importlib.import_module("followup_ec63_kfold")
    vote_builder = importlib.import_module("make_m25_votes")
    return audit, common, kfold, vote_builder


def interval(values: np.ndarray) -> dict[str, Any]:
    valid = values[np.isfinite(values)]
    if valid.size == 0:
        return {
            "lo95": None,
            "hi95": None,
            "n_valid_rounds": 0,
            "n_dropped_rounds": int(values.size),
            "n_zero_rounds": 0,
            "n_positive_rounds": 0,
            "n_negative_rounds": 0,
        }
    lo95, hi95 = np.percentile(valid, [2.5, 97.5])
    return {
        "lo95": float(lo95),
        "hi95": float(hi95),
        "n_valid_rounds": int(valid.size),
        "n_dropped_rounds": int(values.size - valid.size),
        "n_zero_rounds": int(np.sum(valid == 0)),
        "n_positive_rounds": int(np.sum(valid > 0)),
        "n_negative_rounds": int(np.sum(valid < 0)),
    }


def common_actor_domain(frame: pd.DataFrame) -> set[str]:
    actors = sorted(frame["actor"].unique())
    if not actors:
        return set()
    sets = [set(frame.loc[frame["actor"] == actor, "item_id"]) for actor in actors]
    return set.intersection(*sets)


def score_margin_arm(
    audit,
    common,
    df: pd.DataFrame,
    jdf: pd.DataFrame,
    gold_map: dict[str, str],
    floor_maps: dict[str, dict[str, str]],
    domain: set[str],
    judges: list[str],
    n_boot: int,
) -> dict[str, Any]:
    """Compute leaderboard-minus-floor on one explicit support."""
    floor_raw: dict[str, float] = {}
    floor_mats: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    floor_scored_sets: dict[str, set[str]] = {}
    for judge in judges:
        sub = jdf[(jdf["actor"] == judge) & jdf["item_id"].isin(domain)]
        hit = audit.agreement(sub, floor_maps[judge])
        macro, _ = audit.macro_micro(hit, sub["slice"])
        floor_raw[judge] = float(macro)
        floor_mats[judge] = (
            sub["slice"].to_numpy(),
            sub["case_id"].to_numpy(),
            np.asarray(hit, dtype=float),
        )
        floor_scored_sets[judge] = set(
            sub.loc[hit.notna(), "item_id"].astype(str).tolist()
        )

    leader_df = df[df["item_id"].isin(domain)]
    systems = leader_df[leader_df["role"] == "system"]
    rows, _ = audit._leaderboard(leader_df, systems, gold_map)
    if not rows:
        raise RuntimeError("no leaderboard rows on requested support")
    top = rows[0]
    floor_max = max(floor_raw.values())
    same_domain = bool(audit.domain_membership_ok(rows, domain))
    floor_sets_match = all(floor_scored_sets[j] == domain for j in judges)

    cases = np.unique(np.concatenate([row["case"] for row in rows]))
    case_index = {case: index for index, case in enumerate(cases)}
    slice_levels = list(np.unique(np.concatenate([row["slice"] for row in rows])))
    boot_idx = common.make_boot_idx(len(cases), n_boot, SEED)

    leader_rounds: dict[str, np.ndarray] = {}
    for row in rows:
        sums, counts = common.cells_matrices(
            row["slice"],
            row["case"],
            row["hit"],
            slice_levels,
            case_index,
        )
        leader_rounds[row["system"]] = common.boot_macro_rounds(
            sums, counts, boot_idx
        )

    floor_rounds: dict[str, np.ndarray] = {}
    for judge in judges:
        slices, case_ids, hits = floor_mats[judge]
        sums, counts = common.cells_matrices(
            slices, case_ids, hits, slice_levels, case_index
        )
        floor_rounds[judge] = common.boot_macro_rounds(sums, counts, boot_idx)

    fixed_top = leader_rounds[top["system"]]
    leader_max = np.nanmax(np.vstack([leader_rounds[row["system"]] for row in rows]), axis=0)
    floor_max_rounds = np.nanmax(
        np.vstack([floor_rounds[judge] for judge in judges]), axis=0
    )
    with np.errstate(invalid="ignore"):
        theta_fixed = (fixed_top - floor_max_rounds) * 100.0
        theta_both = (leader_max - floor_max_rounds) * 100.0

    return {
        "domain_size": len(domain),
        "domain_sha256": support_digest(domain),
        "n_generators": len(judges),
        "n_systems": len(rows),
        "leader": top["system"],
        "leader_is_generator": top["system"] in set(judges),
        "leader_macro": float(top["macro"]),
        "floor_max_macro": float(floor_max),
        "point_margin": float(top["macro"]) - float(floor_max),
        "same_domain_as_floor": same_domain,
        "floor_sets_match_domain": floor_sets_match,
        "theta_fixed_interval": interval(theta_fixed),
        "theta_both_interval": interval(theta_both),
        "bootstrap": {
            "n_boot": n_boot,
            "seed": SEED,
            "cluster": "case",
            "percentile": [2.5, 97.5],
        },
    }


def label_identity(
    gold_map: dict[str, str],
    loo_maps: dict[str, dict[str, str]],
    domain: set[str],
) -> dict[str, Any]:
    pairs = 0
    mismatches = 0
    examples: list[dict[str, str]] = []
    for judge, mapping in sorted(loo_maps.items()):
        for item in sorted(domain):
            if item not in mapping or item not in gold_map:
                continue
            pairs += 1
            if mapping[item] != gold_map[item]:
                mismatches += 1
                if len(examples) < 5:
                    examples.append(
                        {
                            "generator": judge,
                            "item_id": item,
                            "full_gold": gold_map[item],
                            "loo_gold": mapping[item],
                        }
                    )
    return {
        "pairs_checked": pairs,
        "mismatches": mismatches,
        "examples": examples,
    }


def close_enough(left: float, right: float, tolerance: float = RECORDED_TOL) -> bool:
    return abs(float(left) - float(right)) <= tolerance


def run_task(
    task: str,
    external_root: Path,
    modules,
    recorded: dict[str, Any],
) -> dict[str, Any]:
    audit, common, kfold_mod, vote_builder = modules
    temporary = tempfile.mkdtemp(prefix=f"qone_a3_{task}_")
    try:
        record = vote_builder.build(
            task,
            temporary,
            external_root / "tools" / "bench-noise-floor" / "examples",
        )
        votes_csv = record["path"]
        df, _ = audit.load(votes_csv)
        jdf = df[df["role"] == "judge"].copy()
        gold_map, _ = common.build_gold_variant(jdf, "unmeasured")
        loo_maps = common.leave_one_out_variant(jdf, "unmeasured")
        judges = sorted(jdf["actor"].unique())

        baseline = common.run_judge_gold_arm(votes_csv, n_boot=N_BOOT)
        baseline["task"] = task
        common.validate_m25_arm(baseline)

        kfold_arm = kfold_mod.run_judge_gold_arm_kfold(
            votes_csv, k=K_FOLD, n_boot=N_BOOT
        )
        kfold_domain = kfold_mod._domain_set(kfold_arm, votes_csv)
        slice_levels = list(
            np.unique(np.concatenate([row["slice"] for row in kfold_arm["_rows"]]))
        )
        reported_loo = kfold_mod.loo_margin_on_domain(
            votes_csv,
            kfold_domain,
            kfold_arm["_boot_idx"],
            slice_levels,
        )

        fold_of = kfold_mod.assign_folds(judges, K_FOLD)
        fold_maps = {
            fold: kfold_mod.fold_gold(jdf, fold_of, fold)
            for fold in range(K_FOLD)
        }
        generator_domain = common_actor_domain(jdf)
        system_domain = common_actor_domain(df[df["role"] == "system"])
        loo_domain_all = (
            set(gold_map)
            & set.intersection(*[set(loo_maps[judge]) for judge in judges])
        )
        actor_domain = generator_domain & system_domain
        joint_domain = kfold_domain & loo_domain_all & actor_domain

        loo_joint = score_margin_arm(
            audit,
            common,
            df,
            jdf,
            gold_map,
            loo_maps,
            joint_domain,
            judges,
            N_BOOT,
        )
        kfold_floor_maps = {
            judge: fold_maps[fold_of[judge]]
            for judge in judges
        }
        kfold_joint = score_margin_arm(
            audit,
            common,
            df,
            jdf,
            gold_map,
            kfold_floor_maps,
            joint_domain,
            judges,
            N_BOOT,
        )
        identity = label_identity(gold_map, loo_maps, joint_domain)

        recorded_task = next(
            row for row in recorded["tasks"] if row["task"] == task
        )
        recorded_kfold = recorded_task["kfold"]
        recorded_loo = recorded_task["loo_on_kfold_domain"]
        fidelity = {
            "kfold_margin_match": close_enough(
                kfold_arm["margin_vs_floor_points"],
                recorded_kfold["margin_vs_floor_points"],
            ),
            "kfold_leader_match": kfold_arm["leader"] == recorded_kfold["leader"],
            "kfold_domain_match": (
                len(kfold_domain) == recorded_kfold["kfold_domain_size"]
            ),
            "loo_margin_match": close_enough(
                reported_loo["margin_vs_floor_points"],
                recorded_loo["margin_vs_floor_points"],
            ),
            "loo_floor_match": close_enough(
                reported_loo["floor_max_raw"],
                recorded_loo["floor_max_raw"],
            ),
            "loo_leader_match": reported_loo["leader"] == recorded_loo["leader"],
        }

        return {
            "task": task,
            "carrier_validation": "passed",
            "support": {
                "main_gold": len(gold_map),
                "loo_all": len(loo_domain_all),
                "kfold_reported": len(kfold_domain),
                "generator_rows": len(generator_domain),
                "system_rows": len(system_domain),
                "joint": len(joint_domain),
                "joint_sha256": support_digest(joint_domain),
                "kfold_minus_loo": len(kfold_domain - loo_domain_all),
                "kfold_minus_actor": len(kfold_domain - actor_domain),
                "kfold_minus_joint": len(kfold_domain - joint_domain),
            },
            "reported_leaky_loo_on_kfold_domain": {
                "domain_size": len(kfold_domain),
                "leader": reported_loo["leader"],
                "leader_macro": reported_loo["leader_macro_raw"],
                "floor_max_macro": reported_loo["floor_max_raw"],
                "point_margin": reported_loo["margin_vs_floor_points"],
                "ci_floor": reported_loo["ci_floor"],
            },
            "reported_kfold": {
                "domain_size": kfold_arm["kfold_domain_size"],
                "leader": kfold_arm["leader"],
                "leader_macro": kfold_arm["leader_macro_raw"],
                "floor_max_macro": kfold_arm["floor_max_raw"],
                "point_margin": kfold_arm["margin_vs_floor_points"],
                "ci_floor": kfold_arm["ci_floor"],
            },
            "loo_on_joint_support": loo_joint,
            "kfold_on_joint_support": kfold_joint,
            "label_identity_on_joint_support": identity,
            "recorded_fidelity": fidelity,
        }
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


def selftest() -> int:
    """Known-answer fixture: LOO labels equal full labels on the joint support."""
    audit, common, _kfold, _builder = load_modules(
        Path("/home/liuzewen/F:\\deepseek")
    )
    rows = []
    judges = ["j1", "j2", "j3", "j4", "j5"]
    items = ["i1", "i2", "i3"]
    for judge in judges:
        for item in items:
            for role in ("judge", "system"):
                rows.append(
                    {
                        "item_id": item,
                        "case_id": item,
                        "slice": "all",
                        "role": role,
                        "actor": judge,
                        "answer": "A",
                    }
                )
    with tempfile.TemporaryDirectory() as temporary:
        path = os.path.join(temporary, "fixture.csv")
        pd.DataFrame(rows).to_csv(path, index=False)
        df, _ = audit.load(path)
        jdf = df[df["role"] == "judge"].copy()
        gold_map, _ = common.build_gold_variant(jdf, "unmeasured")
        loo_maps = common.leave_one_out_variant(jdf, "unmeasured")
        result = score_margin_arm(
            audit,
            common,
            df,
            jdf,
            gold_map,
            loo_maps,
            set(items),
            judges,
            50,
        )
        passes = {
            "same_domain": result["same_domain_as_floor"],
            "floor_sets_match": result["floor_sets_match_domain"],
            "zero_point_margin": abs(result["point_margin"]) <= POINT_TOL,
            "zero_bootstrap": (
                result["theta_both_interval"]["n_zero_rounds"]
                == result["theta_both_interval"]["n_valid_rounds"]
            ),
        }
    print(json.dumps({"selftest": passes, "passed": all(passes.values())}, indent=2))
    return 0 if all(passes.values()) else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--external-root", required=True)
    parser.add_argument("--preregistration", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        return selftest()

    external_root = Path(args.external_root).expanduser().resolve()
    prereg_path = Path(args.preregistration).expanduser().resolve()
    prereg = json.loads(prereg_path.read_text(encoding="utf-8"))
    if prereg.get("status") != "frozen_before_execution":
        raise SystemExit("preregistration is not frozen_before_execution")
    if prereg.get("implementation", {}).get("sha256") != sha256_file(__file__):
        raise SystemExit("runner hash does not match the preregistration")

    for relative, expected in PINNED_NATIVE.items():
        path = external_root / relative
        actual = sha256_file(path)
        if actual != expected:
            raise SystemExit(f"native hash mismatch: {relative}: {actual} != {expected}")

    for item in prereg.get("native_inputs", []):
        path = external_root / item["path"]
        actual = sha256_file(path)
        if actual != item["sha256"]:
            raise SystemExit(
                f"native input mismatch: {item['path']}: {actual} != {item['sha256']}"
            )

    modules = load_modules(external_root)
    recorded_path = (
        external_root
        / "papers/bench_noise_floor/evidence/strict_review_followup/EC63_kfold_vs_loo.json"
    )
    recorded = json.loads(recorded_path.read_text(encoding="utf-8"))
    tasks = {
        task: run_task(task, external_root, modules, recorded)
        for task in TASKS
    }

    fidelity_all = all(
        all(task_result["recorded_fidelity"].values())
        for task_result in tasks.values()
    )
    reported_coherence = tasks["coherence"]["reported_leaky_loo_on_kfold_domain"]
    identity_all = all(
        task_result["label_identity_on_joint_support"]["mismatches"] == 0
        and task_result["label_identity_on_joint_support"]["pairs_checked"] > 0
        for task_result in tasks.values()
    )
    joint_zero_all = all(
        abs(task_result["loo_on_joint_support"]["point_margin"]) <= POINT_TOL
        and task_result["loo_on_joint_support"]["same_domain_as_floor"]
        and task_result["loo_on_joint_support"]["floor_sets_match_domain"]
        and task_result["loo_on_joint_support"]["leader_is_generator"]
        and task_result["loo_on_joint_support"]["theta_both_interval"]["n_zero_rounds"]
        == task_result["loo_on_joint_support"]["theta_both_interval"]["n_valid_rounds"]
        for task_result in tasks.values()
    )
    kfold_control = tasks["coherence"]["kfold_on_joint_support"]
    kfold_control_has_teeth = abs(kfold_control["point_margin"]) > 1e-3

    gates = {
        "F1_recorded_leak_reproduced": {
            "passed": fidelity_all
            and abs(reported_coherence["point_margin"]) > 0.1
            and reported_coherence["domain_size"] == 404,
            "coherence_reported_margin": reported_coherence["point_margin"],
            "coherence_reported_domain_size": reported_coherence["domain_size"],
            "all_task_fidelity": fidelity_all,
        },
        "F2_loo_label_identity_on_joint_support": {
            "passed": identity_all,
            "pairs": sum(
                row["label_identity_on_joint_support"]["pairs_checked"]
                for row in tasks.values()
            ),
            "mismatches": sum(
                row["label_identity_on_joint_support"]["mismatches"]
                for row in tasks.values()
            ),
        },
        "F3_joint_support_margin_zero": {
            "passed": joint_zero_all,
            "task_margins": {
                task: row["loo_on_joint_support"]["point_margin"]
                for task, row in tasks.items()
            },
            "task_domains": {
                task: row["loo_on_joint_support"]["domain_size"]
                for task, row in tasks.items()
            },
        },
        "F4_bootstrap_identity_degenerate": {
            "passed": all(
                row["loo_on_joint_support"]["theta_both_interval"]["lo95"] == 0.0
                and row["loo_on_joint_support"]["theta_both_interval"]["hi95"] == 0.0
                for row in tasks.values()
            ),
            "intervals": {
                task: row["loo_on_joint_support"]["theta_both_interval"]
                for task, row in tasks.items()
            },
        },
        "F5_kfold_control_has_teeth": {
            "passed": kfold_control_has_teeth,
            "coherence_kfold_joint_margin": kfold_control["point_margin"],
            "coherence_kfold_joint_interval": kfold_control["theta_both_interval"],
        },
    }
    passed = all(gate["passed"] for gate in gates.values())
    output = {
        "schema": "q-one-a3-common-support-v1",
        "experiment_id": "noise-floor-kfold-common-support-a3",
        "preregistration": {
            "path": prereg_path.name,
            "sha256": sha256_file(prereg_path),
            "version": prereg.get("version"),
        },
        "implementation": {
            "path": Path(__file__).name,
            "sha256": sha256_file(__file__),
        },
        "native": {
            "external_root_name": external_root.name,
            "head": subprocess.check_output(
                ["git", "-C", str(external_root), "rev-parse", "HEAD"],
                text=True,
            ).strip(),
            "hashes": {
                relative: sha256_file(external_root / relative)
                for relative in PINNED_NATIVE
            },
        },
        "bootstrap": {
            "n_boot": N_BOOT,
            "seed": SEED,
            "cluster": "case",
            "percentile": [2.5, 97.5],
            "k_fold": K_FOLD,
            "tolerance_points": POINT_TOL,
        },
        "tasks": tasks,
        "gates": gates,
        "decision": {
            "status": "passed" if passed else "failed",
            "hypothesis": "H1_support_artifact" if passed else "H0_not_rejected",
            "conclusion": (
                "On the four m25 carriers, the non-zero LOO_on_kfold_domain "
                "margin is reproduced and is eliminated only after every "
                "generator is restricted to the joint main-gold, LOO-gold, "
                "k-fold-gold and actor-row support. The leaky comparison is "
                "therefore not a clean k-fold-versus-LOO effect. A non-zero "
                "k-fold margin on the joint support shows that the support fix "
                "does not force every comparison to zero."
            ),
            "non_claims": [
                "This is a recomputation on four fixed m25 constructions, not an external-validity study.",
                "The result does not show that k-fold restores ranking validity.",
                "The result does not rewrite the canonical manuscript or close independent review finding A4.",
                "The result does not authorize an arXiv upload.",
            ],
        },
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"STATUS={output['decision']['status']}")
    print(f"OUTPUT={output_path}")
    print(f"SHA256={sha256_file(output_path)}")
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())

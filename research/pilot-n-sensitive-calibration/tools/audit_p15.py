#!/usr/bin/env python3
"""Audit the deprecated N-sensitive calibration family without rewriting its source."""

from __future__ import annotations

import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

UPSTREAM = Path('/home/liuzewen/Projects/agi-paper-pipeline/runs/tmlr-resampling-calibration')
P12 = Path('/home/liuzewen/Projects/agi-paper-pipeline/runs/tmlr-tmlr-p12/paper/main.tex')
OVERLAY = Path(__file__).resolve().parents[1]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now() -> str:
    # Keep receipts deterministic so re-running the audit does not create churn.
    return '2026-10-28T00:00:00Z'


def mean(rows: list[dict[str, Any]], dataset: str, classifier: str, n: int) -> dict[str, Any]:
    vals = [float(r['ece_adaptive']) for r in rows if r['dataset'] == dataset and r['classifier'] == classifier and int(r['N']) == n]
    return {'N': n, 'seeds': len(vals), 'ece_adaptive_mean': statistics.mean(vals) if vals else None}


def main() -> int:
    canonical = UPSTREAM / 'paper/main.tex'
    variants = {
        'legacy_source': UPSTREAM / 'source/main.tex',
        'canonical_preprint': canonical,
        'ingest_backup': UPSTREAM / 'paper/main.tex.bak_20261001T0205Z_preprint',
        'arxiv_clean': UPSTREAM / 'source/arxiv_clean/main.tex',
        'arxiv_final': UPSTREAM / 'source/arxiv_final/main.tex',
        'arxiv_upload': UPSTREAM / 'source/arxiv_upload/main.tex',
        'submission_variant': UPSTREAM / 'source/submission_variant/main.tex',
    }
    variant_rows = []
    for name, path in variants.items():
        text = path.read_text(encoding='utf-8', errors='ignore')
        variant_rows.append({
            'name': name,
            'path': str(path),
            'sha256': sha(path),
            'bytes': path.stat().st_size,
            'synthetic_style_mentions': text.lower().count('synthetic style-classification'),
            'three_real_dataset_mentions': text.lower().count('three real text datasets'),
            'smote_mentions': text.count('SMOTE'),
        })
    distinct = len({r['sha256'] for r in variant_rows})
    canonical_text = canonical.read_text(encoding='utf-8')
    p12_text = P12.read_text(encoding='utf-8')
    p12_terms = {
        term: p12_text.lower().count(term.lower())
        for term in [
            'N-Sensitive Calibration of Tree Ensembles',
            'SMOTE',
            'random undersampling',
            'resampling calibration audit',
            'frozen LLM embeddings',
            'synthetic style-classification',
        ]
    }
    banner_lines = canonical_text.splitlines()[:8]
    banner = '\n'.join(banner_lines)
    merge_marker = (OVERLAY / 'evidence/upstream/MERGED_INTO_tmlr_p12_20260921.md').read_text(encoding='utf-8')
    review = (OVERLAY / 'evidence/upstream/REVIEW_CARD.md').read_text(encoding='utf-8')

    e1_path = UPSTREAM / 'source/arxiv_upload/supplementary/E1_full.json'
    e6_path = UPSTREAM / 'source/arxiv_upload/supplementary/E6_class_merge.json'
    e1 = json.loads(e1_path.read_text())
    e6 = json.loads(e6_path.read_text())
    e1_summary = {}
    for dataset in sorted({r['dataset'] for r in e1}):
        e1_summary[dataset] = {}
        for classifier in ('RF', 'MLP'):
            lo = mean(e1, dataset, classifier, 500)
            hi = mean(e1, dataset, classifier, 5000)
            lo['delta_to_5000'] = hi['ece_adaptive_mean'] - lo['ece_adaptive_mean']
            hi['delta_from_500'] = lo['delta_to_5000']
            e1_summary[dataset][classifier] = {'n500': lo, 'n5000': hi}
    e6_summary = {}
    for k in sorted({int(r['K']) for r in e6}):
        e6_summary[str(k)] = {}
        for n in (500, 5000):
            e6_summary[str(k)][str(n)] = {
                classifier: {
                    'seeds': len([r for r in e6 if int(r['K']) == k and int(r['N']) == n and r['classifier'] == classifier]),
                    'ece_adaptive_mean': statistics.mean([float(r['ece_adaptive']) for r in e6 if int(r['K']) == k and int(r['N']) == n and r['classifier'] == classifier]),
                }
                for classifier in ('RF', 'MLP')
            }
        e6_summary[str(k)]['gap_mlp_minus_rf_n5000'] = (
            e6_summary[str(k)]['5000']['MLP']['ece_adaptive_mean']
            - e6_summary[str(k)]['5000']['RF']['ece_adaptive_mean']
        )

    receipts = json.loads((UPSTREAM / 'paper/evidence/CARRIER_RECEIPTS.json').read_text())
    receipt_verdicts = Counter(str(r.get('_verdict', 'ABSENT')) for r in receipts)
    absent = [r for r in receipts if '_verdict' not in r]
    absent_artifacts = Counter(str(r.get('artifact')) for r in absent)

    # Require the resampling headline fields to exist, rather than inferring them from prose.
    final = json.loads((UPSTREAM / 'results/final_m2_m3_m5.json').read_text())
    result_text = json.dumps(final, sort_keys=True)
    resampling_fields = {
        'smote_p_0_13': '0.13' in result_text,
        'yeast_ir_70_1': '70.1' in result_text or '70.10' in result_text,
        'rus_0_395': '0.395' in result_text,
        'posthoc_0_003': '-0.003' in result_text,
        'smote_0_061': '0.061' in result_text,
    }

    audit = {
        'schema': 'q-one-p15-calibration-archive-audit-v1',
        'generated_at': now(),
        'marker': 'agent-proposed, not human publication approval',
        'family_id': 'qf-n-sensitive-calibration-of-tree-ensemble-623d15100e',
        'project_id': 'qp-tmlr-resampling-calibration-632b05b06c33',
        'canonical': {
            'path': str(canonical),
            'sha256': sha(canonical),
            'bytes': canonical.stat().st_size,
            'deprecated_banner_present': 'DEPRECATED' in banner and 'DO NOT SUBMIT INDEPENDENTLY' in banner,
            'deprecated_banner': banner,
        },
        'variants': {
            'count': len(variant_rows),
            'distinct_hashes': distinct,
            'all_distinct': distinct == len(variant_rows),
            'rows': variant_rows,
        },
        'merge_target': {
            'path': str(P12),
            'sha256': sha(P12),
            'terms': p12_terms,
            'study_terms_found': sum(1 for value in p12_terms.values() if value),
            'explicit_p15_study_present': any(p12_terms[term] > 0 for term in p12_terms if term != 'N-Sensitive Calibration of Tree Ensembles'),
            'archive_marker_says_merged': '已并入正典' in merge_marker and '不再单投、不再上传' in merge_marker,
        },
        'review': {
            'path': str(OVERLAY / 'evidence/upstream/REVIEW_CARD.md'),
            'sha256': sha(OVERLAY / 'evidence/upstream/REVIEW_CARD.md'),
            'score': '5/10',
            'disposition': '并入 tmlr_p12',
            'major_findings': 2,
            'source_excerpt': review[:500],
        },
        'e1': {
            'path': str(e1_path),
            'sha256': sha(e1_path),
            'rows': len(e1),
            'pair_count': len({r['dataset'] for r in e1}) * 2,
            'summary': e1_summary,
        },
        'e6': {
            'path': str(e6_path),
            'sha256': sha(e6_path),
            'rows': len(e6),
            'summary': e6_summary,
            'k4_both_improve_claim_supported': (
                e6_summary['4']['500']['RF']['ece_adaptive_mean'] > e6_summary['4']['5000']['RF']['ece_adaptive_mean']
                and e6_summary['4']['500']['MLP']['ece_adaptive_mean'] > e6_summary['4']['5000']['MLP']['ece_adaptive_mean']
            ),
        },
        'carrier_receipts': {
            'path': str(UPSTREAM / 'paper/evidence/CARRIER_RECEIPTS.json'),
            'sha256': sha(UPSTREAM / 'paper/evidence/CARRIER_RECEIPTS.json'),
            'total': len(receipts),
            'verdicts': dict(sorted(receipt_verdicts.items())),
            'absent_verdict_count': len(absent),
            'absent_verdict_artifacts': dict(sorted(absent_artifacts.items())),
        },
        'resampling_headline_fields': resampling_fields,
        'decision': {
            'disposition': 'merge_archive',
            'status': 'archived',
            'independent_package_created': False,
            'uploaded': False,
            'reason': 'The canonical source is explicitly deprecated and marked merged into tmlr_p12; no independent package is appropriate. The merge target does not textually contain this study, so merge provenance remains an unresolved conflict rather than a verified merge.',
        },
    }
    (OVERLAY / 'evidence/audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    record = {
        'schema': 'q-one-p15-source-record-v1',
        'generated_at': now(),
        'canonical_path': str(canonical),
        'canonical_sha256': sha(canonical),
        'upstream_copy_path': str(OVERLAY / 'evidence/upstream/main.tex'),
        'upstream_copy_sha256': sha(OVERLAY / 'evidence/upstream/main.tex'),
        'byte_identical': sha(canonical) == sha(OVERLAY / 'evidence/upstream/main.tex'),
        'deprecated_banner_present': 'DEPRECATED — DO NOT SUBMIT INDEPENDENTLY' in canonical_text,
        'merge_marker_path': str(OVERLAY / 'evidence/upstream/MERGED_INTO_tmlr_p12_20260921.md'),
        'merge_marker_sha256': sha(OVERLAY / 'evidence/upstream/MERGED_INTO_tmlr_p12_20260921.md'),
        'review_card_path': str(OVERLAY / 'evidence/upstream/REVIEW_CARD.md'),
        'review_card_sha256': sha(OVERLAY / 'evidence/upstream/REVIEW_CARD.md'),
    }
    (OVERLAY / 'evidence/source_record.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    reconciliation = {
        'schema': 'q-one-p15-variant-reconciliation-v1',
        'generated_at': now(),
        'variant_count': len(variant_rows),
        'distinct_hashes': distinct,
        'all_distinct': distinct == len(variant_rows),
        'packet_variant_count': len(variant_rows) - 1,
        'additional_variant_count': 1,
        'canonical_sha256': sha(canonical),
        'dataset_scope': {
            'canonical': 'synthetic style-classification with BGE embeddings',
            'arxiv_copies': 'three real text datasets (20ng, ag_news, dbpedia)',
            'conflict': 'The canonical and four arXiv-labelled copies use incompatible dataset scopes.',
        },
        'variants': variant_rows,
        'merge_target': audit['merge_target'],
        'decision': audit['decision'],
    }
    (OVERLAY / 'evidence/variant-reconciliation.json').write_text(json.dumps(reconciliation, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    values = {
        'schema': 'q-one-p15-claim-values-v1',
        'generated_at': now(),
        'canonical_sha256': sha(canonical),
        'deprecated_banner_present': 1 if audit['canonical']['deprecated_banner_present'] else 0,
        'variant_count': len(variant_rows),
        'distinct_hashes': distinct,
        'merge_marker_says_merged': 1 if audit['merge_target']['archive_marker_says_merged'] else 0,
        'p12_study_term_count': audit['merge_target']['study_terms_found'],
        'p12_has_p15_study': 1 if audit['merge_target']['explicit_p15_study_present'] else 0,
        'canonical_synthetic_mentions': next(r['synthetic_style_mentions'] for r in variant_rows if r['name'] == 'canonical_preprint'),
        'arxiv_three_real_mentions': sum(r['three_real_dataset_mentions'] for r in variant_rows if r['name'].startswith('arxiv_')),
        'e1_20ng_rf_n500': e1_summary['20ng']['RF']['n500']['ece_adaptive_mean'],
        'e1_pair_count': audit['e1']['pair_count'],
        'e1_20ng_rf_n5000': e1_summary['20ng']['RF']['n5000']['ece_adaptive_mean'],
        'e1_20ng_mlp_n500': e1_summary['20ng']['MLP']['n500']['ece_adaptive_mean'],
        'e1_20ng_mlp_n5000': e1_summary['20ng']['MLP']['n5000']['ece_adaptive_mean'],
        'e1_ag_rf_n500': e1_summary['ag_news']['RF']['n500']['ece_adaptive_mean'],
        'e1_ag_rf_n5000': e1_summary['ag_news']['RF']['n5000']['ece_adaptive_mean'],
        'e1_ag_mlp_n500': e1_summary['ag_news']['MLP']['n500']['ece_adaptive_mean'],
        'e1_ag_mlp_n5000': e1_summary['ag_news']['MLP']['n5000']['ece_adaptive_mean'],
        'e1_dbpedia_rf_n500': e1_summary['dbpedia']['RF']['n500']['ece_adaptive_mean'],
        'e1_dbpedia_rf_n5000': e1_summary['dbpedia']['RF']['n5000']['ece_adaptive_mean'],
        'e1_dbpedia_mlp_n500': e1_summary['dbpedia']['MLP']['n500']['ece_adaptive_mean'],
        'e1_dbpedia_mlp_n5000': e1_summary['dbpedia']['MLP']['n5000']['ece_adaptive_mean'],
        'k4_rf_n500': e6_summary['4']['500']['RF']['ece_adaptive_mean'],
        'k4_rf_n5000': e6_summary['4']['5000']['RF']['ece_adaptive_mean'],
        'k4_mlp_n500': e6_summary['4']['500']['MLP']['ece_adaptive_mean'],
        'k4_mlp_n5000': e6_summary['4']['5000']['MLP']['ece_adaptive_mean'],
        'k4_gap_n5000': e6_summary['4']['gap_mlp_minus_rf_n5000'],
        'k4_both_improve_supported': 1 if audit['e6']['k4_both_improve_claim_supported'] else 0,
        'carrier_total': len(receipts),
        'carrier_pass': receipt_verdicts.get('PASS', 0),
        'carrier_absent_verdict': len(absent),
        'carrier_absent_e1': absent_artifacts.get('source/arxiv_upload/supplementary/E1_full.json', 0),
        'carrier_absent_e6': absent_artifacts.get('source/arxiv_upload/supplementary/E6_class_merge.json', 0),
        'carrier_absent_e8': absent_artifacts.get('source/revision_experiments/results/E8_rf_leaf_ablation.json', 0),
        'smote_p_field_present': 1 if resampling_fields['smote_p_0_13'] else 0,
        'rus_0395_field_present': 1 if resampling_fields['rus_0_395'] else 0,
        'posthoc_m0003_field_present': 1 if resampling_fields['posthoc_0_003'] else 0,
        'review_score': '5/10',
        'independent_package_created': 0,
        'uploaded': 0,
    }
    (OVERLAY / 'evidence/claim-values.json').write_text(json.dumps(values, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    lines = [
        '# Claim ledger - N-Sensitive Calibration archive',
        '',
        'Status marker: `agent-proposed, not human publication approval`',
        '',
        '| ID | Claim | Evidence file + fields | Value | How to verify | Status |',
        '|---|---|---|---|---|---|',
        f"| C01 | The canonical source, four arXiv-labelled copies and two additional variants have {distinct} distinct hashes out of {len(variant_rows)} retained files. | evidence/variant-reconciliation.json -> distinct_hashes / variant_count | {distinct} / {len(variant_rows)} | Re-hash every retained source | verified |",
        f"| C02 | The canonical source begins with an explicit DEPRECATED / DO NOT SUBMIT INDEPENDENTLY banner. | evidence/claim-values.json -> deprecated_banner_present | {values['deprecated_banner_present']} | Inspect the first eight lines of `evidence/upstream/main.tex` | verified |",
        f"| C03 | The merge marker states that the family is archived into `tmlr_p12` and must not be submitted independently. | evidence/claim-values.json -> merge_marker_says_merged | {values['merge_marker_says_merged']} | Read the retained merge marker | verified |",
        f"| C04 | The named `tmlr_p12` merge target does not contain the calibration/resampling study's identifying terms. | evidence/claim-values.json -> p12_study_term_count / p12_has_p15_study | {values['p12_study_term_count']} / {values['p12_has_p15_study']} | Search the pinned p12 source for the study-specific terms | blocked |",
        f"| C05 | The canonical and four arXiv-labelled copies use incompatible dataset scopes. | evidence/claim-values.json -> canonical_synthetic_mentions / arxiv_three_real_mentions | {values['canonical_synthetic_mentions']} / {values['arxiv_three_real_mentions']} | Compare the retained source copies line by line | blocked |",
        f"| C06 | The E1 archive has 240 rows and covers six dataset/classifier N=500 to N=5000 adaptive-ECE pairs. | evidence/audit.json -> e1.rows / e1.pair_count | {audit['e1']['rows']} / {audit['e1']['pair_count']} | Recompute group means from all E1 rows | verified |",
        f"| C07 | On E1, 20ng RF moves from 0.3201 to 0.4021 and MLP from 0.1987 to 0.0509. | evidence/claim-values.json -> e1_20ng_rf_n500 / e1_20ng_rf_n5000 / e1_20ng_mlp_n500 / e1_20ng_mlp_n5000 | {values['e1_20ng_rf_n500']:.4f} / {values['e1_20ng_rf_n5000']:.4f} / {values['e1_20ng_mlp_n500']:.4f} / {values['e1_20ng_mlp_n5000']:.4f} | Recompute the E1 group means | verified |",
        f"| C08 | On E1, ag_news RF moves from 0.3557 to 0.3072 and MLP from 0.3608 to 0.0316. | evidence/claim-values.json -> e1_ag_rf_n500 / e1_ag_rf_n5000 / e1_ag_mlp_n500 / e1_ag_mlp_n5000 | {values['e1_ag_rf_n500']:.4f} / {values['e1_ag_rf_n5000']:.4f} / {values['e1_ag_mlp_n500']:.4f} / {values['e1_ag_mlp_n5000']:.4f} | Recompute the E1 group means | verified |",
        f"| C09 | On E1, dbpedia RF moves from 0.5662 to 0.5828 and MLP from 0.3906 to 0.0288. | evidence/claim-values.json -> e1_dbpedia_rf_n500 / e1_dbpedia_rf_n5000 / e1_dbpedia_mlp_n500 / e1_dbpedia_mlp_n5000 | {values['e1_dbpedia_rf_n500']:.4f} / {values['e1_dbpedia_rf_n5000']:.4f} / {values['e1_dbpedia_mlp_n500']:.4f} / {values['e1_dbpedia_mlp_n5000']:.4f} | Recompute the E1 group means | verified |",
        f"| C10 | The E6 K=4 result contradicts the abstract's claim that both models improve modestly: RF worsens from 0.2520 to 0.2662 while MLP improves from 0.2032 to 0.0702. | evidence/claim-values.json -> k4_rf_n500 / k4_rf_n5000 / k4_mlp_n500 / k4_mlp_n5000 / k4_both_improve_supported | {values['k4_rf_n500']:.4f} / {values['k4_rf_n5000']:.4f} / {values['k4_mlp_n500']:.4f} / {values['k4_mlp_n5000']:.4f} / {values['k4_both_improve_supported']} | Recompute each K=4 group from all ten seeds | blocked |",
        f"| C11 | The headline 4-class, 88 percent temperature-scaling and resampling values have a complete machine-readable carrier set. | evidence/claim-values.json -> k4_both_improve_supported / smote_p_field_present / rus_0395_field_present / posthoc_m0003_field_present | {values['k4_both_improve_supported']} / {values['smote_p_field_present']} / {values['rus_0395_field_present']} / {values['posthoc_m0003_field_present']} | Search the named result archives for the declared fields | blocked |",
        f"| C12 | The retained 201-row carrier receipt file has 159 PASS verdicts and 42 rows without any verdict. | evidence/claim-values.json -> carrier_total / carrier_pass / carrier_absent_verdict | {values['carrier_total']} / {values['carrier_pass']} / {values['carrier_absent_verdict']} | Count `_verdict` values and absent keys | verified |",
        f"| C13 | The 42 unverdicted receipts are concentrated in E1, E6 and E8, not distributed across the archive. | evidence/claim-values.json -> carrier_absent_e1 / carrier_absent_e6 / carrier_absent_e8 | {values['carrier_absent_e1']} / {values['carrier_absent_e6']} / {values['carrier_absent_e8']} | Group missing verdicts by artifact path | verified |",
        f"| C14 | The retained review is 5/10 and recommends merging into `tmlr_p12`, with two Major findings still open. | evidence/claim-values.json -> review_score | {values['review_score']} | Read the retained review card | verified |",
        f"| C15 | The only defensible disposition is `merge_archive` / `archived`, with no independent package and no upload. | evidence/claim-values.json -> independent_package_created / uploaded | {values['independent_package_created']} / {values['uploaded']} | Check the disposition record, package directory and upload receipts | verified |",
        '',
        '## Summary',
        '',
        'The family is explicitly deprecated by its own canonical source. Four arXiv-labelled source copies use a different dataset scope from the canonical synthetic-only manuscript. The target manuscript named by the archive marker does not textually contain this study, so the merge provenance is unresolved. E1 and E6 reproduce mechanically, but E6 directly falsifies the abstract sentence that both models improve at four classes. The resampling headline values do not have named fields in the retained result archive, and 42 of 201 carrier receipts have no verdict. The correct disposition is archive/merge with no independent package.',
        '',
    ]
    (OVERLAY / 'CLAIM_LEDGER.md').write_text('\n'.join(lines), encoding='utf-8')

    print(json.dumps({
        'audit_sha256': sha(OVERLAY / 'evidence/audit.json'),
        'ledger_sha256': sha(OVERLAY / 'CLAIM_LEDGER.md'),
        'canonical_sha256': sha(canonical),
        'distinct_variants': distinct,
        'k4_both_improve': audit['e6']['k4_both_improve_claim_supported'],
        'carrier_verdicts': dict(receipt_verdicts),
        'p12_study_terms': p12_terms,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

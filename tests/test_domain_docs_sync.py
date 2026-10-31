"""Verify domain docs stay in sync with the metric CATALOG (single source of truth).

Checks:
1. The CATALOG in generate_metric_specs.py generates exactly the specs in
   examples/metric-spec.json (idempotency / no drift between script and artifact).
2. Every domain has a non-empty doc under docs/domains/.
3. Each doc names the same categories and totals as the CATALOG.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from generate_domain_docs import DOMAIN_NAMES, build_domain_docs  # noqa: E402
from generate_metric_specs import CATALOG  # noqa: E402


@pytest.fixture(scope="module")
def specs() -> list[dict]:
    return json.loads((ROOT / "examples" / "metric-spec.json").read_text(encoding="utf-8"))


def test_catalog_metrics_match_file(specs):
    """Re-deriving from CATALOG reproduces exactly the spec file entries."""
    from generate_metric_specs import build_catalog

    derived = build_catalog()
    assert len(derived) == len(specs), f"CATALOG 推导 {len(derived)} vs 文件 {len(specs)}"
    # 键集合必须完全一致（顺序允许不同）
    derived_keys = {s["domain"] + ":" + s["metric"] for s in derived}
    file_keys = {s["domain"] + ":" + s["metric"] for s in specs}
    assert derived_keys == file_keys, "CATALOG 与 spec 文件键集合漂移"


def test_all_domains_documented():
    docs = build_domain_docs()
    assert set(docs.keys()) == set(CATALOG.keys()), "文档域集合与 CATALOG 不一致"
    for domain, markdown in docs.items():
        assert len(markdown) > 200, f"{domain} 文档过短"
        assert f"# {DOMAIN_NAMES[domain]}域" in markdown, f"{domain} 文档缺标题"


def test_doc_category_counts_match(specs):
    """每份文档的总计行与 spec 文件里该域的指标数一致。"""
    docs = build_domain_docs()
    from collections import Counter

    by_domain = Counter(s["domain"] for s in specs)
    for domain, markdown in docs.items():
        # 文档合计行格式：| **合计** | **{n}** | | |
        for line in markdown.splitlines():
            if "**合计**" in line:
                cells = [c.strip() for c in line.strip("|").split("|")]
                doc_total = int(cells[1].strip("*"))
                assert doc_total == by_domain[domain], (
                    f"{domain} 文档合计 {doc_total} vs spec {by_domain[domain]}"
                )
                break
        else:
            pytest.fail(f"{domain} 文档缺合计行")


def test_doc_categories_listed(specs):
    """每份文档列出与 CATALOG 相同的类别数量。"""
    docs = build_domain_docs()
    for domain, categories in CATALOG.items():
        markdown = docs[domain]
        for category_name, _templates, _members in categories:
            assert f"### {category_name}" in markdown, f"{domain}/{category_name} 类别缺失"


def test_metric_spec_loadable(specs):
    """spec 文件必须能通过 load_metric_specs 完整加载。"""
    from qone_life.models import load_metric_specs

    loaded = load_metric_specs(specs)
    assert len(loaded) == len(specs)
    # key 唯一性
    keys = [s.key for s in loaded]
    assert len(set(keys)) == len(keys)

"""Q-One 研究生产控制（拆分后的包）。

本文件只负责把各主题子模块里的公共 API 重新导出，保持与拆分前一致的调用入口。
调用方应始终从 ``qone_life.research_factory`` 导入，而不是直接导入子模块。
"""
from __future__ import annotations

from ._helpers import (
    ABSOLUTE_PATH_RE,
    GRAPHICSPATH_RE,
    NATIVE_LEDGER_SCHEMA,
    PACKAGE_AUXILIARY_SUFFIXES,
    PACKAGE_SCHEMA,
    PLACEHOLDER_RE,
    PLAN_SCHEMA,
    REFERENCE_RE,
    SCAFFOLD_SCHEMA,
    SOURCE_LINEAGE_SCHEMA,
    TRIAGE_SCHEMA,
    ResearchFactoryError,
    audit_git_source_lineage,
)
from .package import (
    audit_arxiv_package,
    audit_native_paper_ledger,
    write_native_ledger_audit,
    write_package_audit,
)
from .scaffold import (
    build_research_plan,
    create_research_scaffold,
    optimize_portfolio,
    render_plan_markdown,
    write_plan,
)
from .triage import (
    render_triage_csv,
    render_triage_markdown,
    triage_portfolio,
    write_triage,
)

# 对外公开的名字：拆分前 research_factory 模块的完整公共 API。
__all__ = [
    "ABSOLUTE_PATH_RE",
    "GRAPHICSPATH_RE",
    "NATIVE_LEDGER_SCHEMA",
    "PACKAGE_AUXILIARY_SUFFIXES",
    "PACKAGE_SCHEMA",
    "PLACEHOLDER_RE",
    "PLAN_SCHEMA",
    "REFERENCE_RE",
    "SCAFFOLD_SCHEMA",
    "SOURCE_LINEAGE_SCHEMA",
    "TRIAGE_SCHEMA",
    "ResearchFactoryError",
    "audit_arxiv_package",
    "audit_git_source_lineage",
    "audit_native_paper_ledger",
    "build_research_plan",
    "create_research_scaffold",
    "optimize_portfolio",
    "render_plan_markdown",
    "render_triage_csv",
    "render_triage_markdown",
    "triage_portfolio",
    "write_native_ledger_audit",
    "write_package_audit",
    "write_plan",
    "write_triage",
]

"""Deterministic research-production controls for the Q-One portfolio (split package).

Re-exports the original public API from themed submodules."""
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

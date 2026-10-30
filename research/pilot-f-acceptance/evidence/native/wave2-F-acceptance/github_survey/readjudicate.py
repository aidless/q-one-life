#!/usr/bin/env python3
"""Re-adjudicate exact-named McNemar functions for sample-size switches.

The first public-code pass classified a definition as exact when its body
contained an exact formula. This pass asks the caller-facing question instead:
does the function return the exact tail for every input it accepts? A
conditional fallback to a named approximation above a sample-size threshold is
a counterexample even when the small-n branch is exact.

Deterministic: reads raw/classification.json and raw/files/*, writes
raw/classification-readjudicated.json. No network, no timestamps.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
CLASSIFICATION = RAW / "classification.json"
FILES = RAW / "files"
OUT = RAW / "classification-readjudicated.json"

EXACT_NAMED_IMPLEMENTATION_VERDICTS = {
    "exact",
    "exact-delegate",
    "exact-wrapper",
    "non-computing-wrapper",
}
APPROX_NAME = ("normal", "chi2", "asymptotic", "approx")
SAMPLE_SIZE_NAMES = {"n", "n_total", "ntotal", "total", "m"}


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Call):
        f = node.func
        if isinstance(f, ast.Name):
            return f.id
        if isinstance(f, ast.Attribute):
            return f.attr
    return None


def _approx_calls(node: ast.AST) -> list[tuple[int, str]]:
    out = []
    for n in ast.walk(node):
        name = _call_name(n)
        if name and any(token in name.lower() for token in APPROX_NAME):
            out.append((getattr(n, "lineno", 0), name))
    return out


def _sample_size_condition(test: ast.AST) -> str | None:
    """Return the source form when the test compares a sample-size variable
    against a threshold with >, >=, <, or <=."""
    if not isinstance(test, ast.Compare) or len(test.ops) != 1:
        return None
    left, op, right = test.left, test.ops[0], test.comparators[0]
    if isinstance(left, ast.Name) and left.id in SAMPLE_SIZE_NAMES:
        if isinstance(op, (ast.Gt, ast.GtE)):
            return ast.unparse(test)
    if isinstance(right, ast.Name) and right.id in SAMPLE_SIZE_NAMES:
        if isinstance(op, (ast.Lt, ast.LtE)):
            return ast.unparse(test)
    return None


def _find_function(tree: ast.Module, line: int, name: str):
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.lineno == line
            and node.name == name
        ):
            return node
    return None


def _body_calls(stmts: list[ast.stmt]) -> list[tuple[int, str]]:
    calls = []
    for stmt in stmts:
        calls.extend(_approx_calls(stmt))
    return calls


def analyze(source: str, row: dict) -> list[dict]:
    tree = ast.parse(source)
    fn = _find_function(tree, row["def_line_no"], row["fn"])
    if fn is None:
        return [{"error": "function not found at def_line_no"}]
    hits = []
    for node in ast.walk(fn):
        if isinstance(node, ast.If):
            condition = _sample_size_condition(node.test)
            if condition:
                calls = _body_calls(node.body)
                if calls:
                    hits.append(
                        {
                            "condition": condition,
                            "call_lines": [{"line": line, "call": name} for line, name in calls],
                            "source": ast.get_source_segment(source, node),
                        }
                    )
        elif isinstance(node, ast.IfExp):
            condition = _sample_size_condition(node.test)
            if condition:
                calls = _approx_calls(node.body)
                if calls:
                    hits.append(
                        {
                            "condition": condition,
                            "call_lines": [{"line": line, "call": name} for line, name in calls],
                            "source": ast.get_source_segment(source, node),
                        }
                    )
    return hits


def main() -> None:
    data = json.loads(CLASSIFICATION.read_text())
    rows = [
        r
        for r in data["rows"]
        if r.get("name_promises_exact") and r.get("verdict") in EXACT_NAMED_IMPLEMENTATION_VERDICTS
    ]
    results = []
    for row in rows:
        path = FILES / row["file"]
        if not path.exists():
            results.append(
                {
                    "file": row["file"],
                    "fn": row["fn"],
                    "def_line_no": row["def_line_no"],
                    "verdict": row["verdict"],
                    "status": "missing-source",
                    "hits": [],
                }
            )
            continue
        hits = analyze(path.read_text(encoding="utf-8", errors="replace"), row)
        results.append(
            {
                "file": row["file"],
                "fn": row["fn"],
                "def_line_no": row["def_line_no"],
                "verdict": row["verdict"],
                "status": "counterexample" if hits else "no-sample-size-switch",
                "hits": hits,
            }
        )

    counterexamples = [r for r in results if r["status"] == "counterexample"]
    payload = {
        "criterion": (
            "Among definitions whose name promises exactness, flag a conditional "
            "fallback to a normal/chi-square/asymptotic/approx call when the "
            "condition compares the sample size (n, n_total, ntotal, total, m) "
            "against a threshold with >, >=, <, or <=."
        ),
        "sources": {
            "classification": "raw/classification.json",
            "bodies": "raw/files/",
        },
        "total_exact_named_implementation_defs": len(rows),
        "counterexamples_count": len(counterexamples),
        "counterexamples": counterexamples,
        "status_counts": {
            status: sum(1 for r in results if r["status"] == status)
            for status in sorted({r["status"] for r in results})
        },
        "rows": results,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n")
    print(
        f"wrote {OUT}: {len(rows)} exact-named defs, "
        f"{len(counterexamples)} counterexample(s)"
    )


if __name__ == "__main__":
    main()

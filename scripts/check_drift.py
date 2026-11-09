#!/usr/bin/env python3
"""Fail when version, docs, and workflows drift from this tree.

Stdlib only. This does not install q-one-core, contact a model, or claim efficacy.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PROBLEM_BLOCK = [
    "# Q-One Life",
    "",
    "STATUS: WORK-IN-PROGRESS — not A yet. Gaps are listed under [Not A yet](#not-a-yet).",
    "",
    "Local decision workbench for one person: record goals, options, observations, and the next step you choose.",
    "It is not medical advice and not financial advice.",
    "It does not execute consequential acts; a person confirms every choice, and stopping the program stops new recommendations.",
]


def fail(message: str) -> None:
    print(f"drift: {message}", file=sys.stderr)
    raise SystemExit(1)


def read(relative: str) -> str:
    path = ROOT / relative
    if not path.is_file():
        fail(f"missing {relative}")
    return path.read_text(encoding="utf-8")


def bracket_array(text: str, key: str) -> list[str]:
    marker = f"{key} = ["
    start = text.find(marker)
    if start < 0:
        fail(f"pyproject.toml has no {key} array")
    start = text.find("[", start)
    depth = 0
    end = None
    for index, character in enumerate(text[start:], start):
        if character == "[":
            depth += 1
        elif character == "]":
            depth -= 1
            if depth == 0:
                end = index
                break
    if end is None:
        fail(f"unterminated {key} array")
    items: list[str] = []
    for raw in text[start + 1 : end].split(","):
        item = raw.strip()
        if not item:
            continue
        if len(item) < 2 or item[0] != '"' or item[-1] != '"':
            fail(f"unquoted {key} entry: {item}")
        items.append(item[1:-1])
    return items


def project_version(text: str) -> str:
    in_project = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_project = stripped == "[project]"
            continue
        if in_project and stripped.startswith("version"):
            value = stripped.split("=", 1)[1].strip().strip('"').strip("'")
            if not value:
                fail("empty project version")
            return value
    fail("pyproject.toml [project] version missing")
    return ""


def main() -> None:
    pyproject = read("pyproject.toml")
    version = project_version(pyproject)
    init_text = read("src/qone_life/__init__.py")
    marker = '__version__ = "'
    if marker + version + '"' not in init_text:
        fail(f"src/qone_life/__init__.py version is not {version}")

    declared = bracket_array(pyproject, "dependencies")
    required_lines = [
        line.strip()
        for line in read("requirements.txt").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if set(required_lines) != set(declared):
        fail("requirements.txt does not match pyproject.toml dependencies")

    manifest = json.loads(read("research-manifest.json"))
    project = manifest.get("project") or {}
    if project.get("version") != version:
        fail("research-manifest.json project.version does not match the package")
    if manifest.get("experiments") != []:
        fail("research-manifest.json experiments is no longer an empty list; do not leave a stale note")
    if project.get("external_validation") is not False:
        fail("research-manifest.json must keep external_validation false until a real external result exists")

    changelog = read("CHANGELOG.md")
    if f"## {version} " not in changelog and f"## {version}\n" not in changelog:
        fail(f"CHANGELOG.md has no heading for {version}")
    if "## Unreleased" not in changelog:
        fail("CHANGELOG.md is missing Unreleased")

    readme = read("README.md").splitlines()
    if readme[: len(PROBLEM_BLOCK)] != PROBLEM_BLOCK:
        fail("README problem statement is not the three-line block at the top")
    readme_text = "\n".join(readme)
    for phrase in (
        "Windows 原生并发文件锁尚未验证，建议使用 WSL。",
        "scripts/record_only_smoke.sh",
        "scripts/setup.sh",
        "scripts/run.sh",
        "scripts/model_smoke.py",
        "FAILURE_MODES.md",
        "合成验收截图",
        "No external validation",
    ):
        if phrase not in readme_text:
            fail(f"README.md is missing {phrase!r}")
    for banned in ("GitHub stars", "monthly users", "PyPI downloads", "clinical efficacy"):
        if banned in readme_text:
            fail(f"README.md contains an unsupported claim: {banned}")

    failures = read("FAILURE_MODES.md")
    for heading in (
        "## Model text can be shown as a recommendation",
        "## Cached recommendations go stale",
        "## Budget minutes are not measured free time",
    ):
        if heading not in failures:
            fail(f"FAILURE_MODES.md is missing {heading}")

    app_js = read("src/qone_life/static/app.js")
    if "预算中尚未安排的分钟" not in app_js:
        fail("app.js no longer labels the capacity figure as remaining budget")
    if "还可安排的时间" in app_js:
        fail("app.js still calls the budget '还可安排的时间'")
    if "每日计划预算（分钟）" not in app_js:
        fail("settings no longer call the field a planning budget")

    checks = read(".github/workflows/checks.yml")
    for phrase in (
        "bash scripts/record_only_smoke.sh",
        "python scripts/check_drift.py",
        "python -m pip install -r requirements.txt",
        "python -m pip install .",
        "python -m unittest discover -s tests -v",
        "node --check < src/qone_life/static/app.js",
        "node --input-type=module - < tests/test_app_render.mjs",
    ):
        if phrase not in checks:
            fail(f"checks.yml is missing {phrase}")
    for banned in ("model_smoke", "11434"):
        if banned in checks:
            fail(f"checks.yml includes the live model path ({banned})")

    model_workflow = read(".github/workflows/model-smoke.yml")
    if "workflow_dispatch" not in model_workflow:
        fail("model-smoke.yml is not manual")
    for banned in ("pull_request", "push"):
        if banned in model_workflow:
            fail(f"model-smoke.yml must stay off the default CI trigger ({banned})")
    if "does not start Ollama" not in model_workflow:
        fail("model-smoke.yml no longer states that it does not start Ollama")

    smoke = read("scripts/model_smoke.py")
    if "not a benchmark or calibration study" not in smoke:
        fail("scripts/model_smoke.py lost its scope line")
    setup = read("scripts/setup.sh")
    if "requirements.txt" not in setup or "pip install" not in setup:
        fail("scripts/setup.sh no longer installs requirements and the project")
    if "scripts/run.sh" not in read("scripts/run.sh") and "qone-life" not in read("scripts/run.sh"):
        fail("scripts/run.sh does not launch qone-life")

    print(f"drift ok: package {version}; experiments empty; default CI has no live model")


if __name__ == "__main__":
    main()

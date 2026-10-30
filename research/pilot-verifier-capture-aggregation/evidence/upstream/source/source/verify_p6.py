#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_p6.py — PAPER6 self-check script
Status: W1 SKELETON — all checks stubbed. W2-W6 will fill in real checks.

Inherited pattern: verify_p5.py (F:\\Research\\PAPER5_CONSOLIDATED\\verify_p5.py, 69317 bytes).
Differences from PAPER5:
  - No C9 figure-caption checks (no figures yet)
  - No C10 self-citation blacklist (different paper, no main.tex content yet)
  - Adds W6 checks: Broader Impact present, ethics statement, code link

Usage:
    python verify_p6.py                  # full check, exit 0 = pass
    python verify_p6.py --dry-run        # show what would be checked, no execution
    python verify_p6.py --skip <C1..Cn>  # skip specific check by id
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path
import re

# ---------------------------------------------------------------------
# Stub function (must be defined BEFORE CHECKS dict that references it)
# ---------------------------------------------------------------------
def _stub(*args, **kwargs) -> tuple[bool, str]:
    """W1 stub: always returns (NOT_RUN, 'W1 stub')."""
    return (False, "W1 stub — to be implemented in W2-W6")

# ---------------------------------------------------------------------
# Helper: read main.tex once
# ---------------------------------------------------------------------
def _read_main_tex() -> str | None:
    p = Path(__file__).parent.resolve() / "main.tex"
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------
# C1: main.tex uses tmlr documentclass
# ---------------------------------------------------------------------
def _check_c1() -> tuple[bool, str]:
    text = _read_main_tex()
    if text is None:
        return (False, "main.tex not found")
    # TMLR template usage: \documentclass[11pt]{article} + \usepackage[preprint]{tmlr}
    if not re.search(r"\\usepackage(?:\[[^\]]*\])?\{tmlr\}", text):
        return (False, "main.tex missing \\usepackage{tmlr}")
    if not re.search(r"\\documentclass(?:\[[^\]]*\])?\{article\}", text):
        return (False, "main.tex missing \\documentclass{article}")
    return (True, "tmlr template (documentclass + usepackage) detected")

# ---------------------------------------------------------------------
# C2: main.tex has 7+ sections
# ---------------------------------------------------------------------
def _check_c2() -> tuple[bool, str]:
    text = _read_main_tex()
    if text is None:
        return (False, "main.tex not found")
    section_count = len(re.findall(r"\\section\{[^}]+\}", text))
    if section_count < 7:
        return (False, f"only {section_count} sections (need >=7 for TMLR)")
    return (True, f"{section_count} sections found")

# ---------------------------------------------------------------------
# C3: main.tex parses (no unbalanced braces / no obvious syntax errors)
# ---------------------------------------------------------------------
def _check_c3() -> tuple[bool, str]:
    text = _read_main_tex()
    if text is None:
        return (False, "main.tex not found")
    # crude structural sanity: balanced { } count, \begin{document} exists, \end{document} exists
    opens  = text.count("{")
    closes = text.count("}")
    if opens != closes:
        return (False, f"unbalanced braces: {opens} '{{' vs {closes} '}}'")
    if "\\begin{document}" not in text:
        return (False, "missing \\begin{document}")
    if "\\end{document}" not in text:
        return (False, "missing \\end{document}")
    return (True, f"balanced braces ({opens}), document env present")

# ---------------------------------------------------------------------
# Helper: read refs.bib
# ---------------------------------------------------------------------
def _read_refs_bib() -> str | None:
    p = Path(__file__).parent.resolve() / "refs.bib"
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------
# C4: refs.bib has >= 10 entries
# ---------------------------------------------------------------------
def _check_c4() -> tuple[bool, str]:
    text = _read_refs_bib()
    if text is None:
        return (False, "refs.bib not found")
    # count @type{key, entries — match opening @ then optional type then {
    n_entries = len(re.findall(r"@\w+\s*\{", text))
    if n_entries < 10:
        return (False, f"only {n_entries} entries (need >=10)")
    return (True, f"{n_entries} entries found")

# ---------------------------------------------------------------------
# C5: abstract <= 250 words (or stub acceptable until W6)
# ---------------------------------------------------------------------
def _check_c5() -> tuple[bool, str]:
    text = _read_main_tex()
    if text is None:
        return (False, "main.tex not found")
    # extract \begin{abstract} ... \end{abstract} block
    m = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", text, re.DOTALL)
    if not m:
        return (False, "no \\begin{abstract}...\\end{abstract} block found")
    abstract_text = m.group(1)
    # strip LaTeX commands crudely
    plain = re.sub(r"\\[a-zA-Z]+\b", " ", abstract_text)
    plain = re.sub(r"[^a-zA-Z\s]", " ", plain)
    words = plain.split()
    n = len(words)
    if n == 0:
        return (False, "abstract block is empty")
    if n > 250:
        return (False, f"abstract has {n} words (>250)")
    return (True, f"abstract has {n} words")

# ---------------------------------------------------------------------
# C6: no verbatim TODO/FIXME/XXX markers in main.tex
# ---------------------------------------------------------------------
def _check_c6() -> tuple[bool, str]:
    text = _read_main_tex()
    if text is None:
        return (False, "main.tex not found")
    # only flag markers OUTSIDE comments (% to end of line) and AFTER \begin{document}
    begin_doc = text.find("\\begin{document}")
    body = text[begin_doc:] if begin_doc >= 0 else text
    bad = []
    for marker in ("TODO", "FIXME", "XXX"):
        # find markers not preceded by % (comment) and not inside math
        for m in re.finditer(rf"\b{marker}\b", body):
            line_start = body.rfind("\n", 0, m.start()) + 1
            line_end = body.find("\n", m.end())
            if line_end < 0:
                line_end = len(body)
            line = body[line_start:line_end]
            if "%" in line[: line.find(marker)]:
                continue  # inside a comment
            bad.append(f"{marker} at line containing: {line.strip()[:80]}")
    if bad:
        return (False, "; ".join(bad[:3]))
    return (True, "no TODO/FIXME/XXX markers in main body")

# ---------------------------------------------------------------------
# C7: all \cite / \citet / \citep keys resolve to refs.bib
# ---------------------------------------------------------------------
def _check_c7() -> tuple[bool, str]:
    text = _read_main_tex()
    bib  = _read_refs_bib()
    if text is None:
        return (False, "main.tex not found")
    if bib is None:
        return (False, "refs.bib not found")
    # collect bib keys
    bib_keys = set(re.findall(r"@\w+\s*\{\s*([^,\s]+)\s*,", bib))
    # collect cite keys from \cite{...}, \citet{...}, \citep{...}
    cited = set()
    for cmd in ("cite", "citet", "citep", "citealp"):
        for m in re.finditer(rf"\\{cmd}\{{([^}}]+)\}}", text):
            for k in m.group(1).split(","):
                cited.add(k.strip())
    missing = cited - bib_keys
    if missing:
        return (False, f"unresolved cites: {sorted(missing)[:5]}")
    return (True, f"all {len(cited)} cited keys resolve to refs.bib")


# ---------------------------------------------------------------------
# Helper: check if a section header is present and non-placeholder
# ---------------------------------------------------------------------
def _has_real_section(text: str, section_name: str) -> tuple[bool, str]:
    """Check that section `\section{Name}` exists AND its body is
    not just a [Placeholder] line."""
    pattern = rf"\\section\{{{re.escape(section_name)}\}}"
    m = re.search(pattern, text)
    if not m:
        return (False, f"\\section{{{section_name}}} not found")
    # look at the next 800 chars of body for placeholder markers
    body_start = m.end()
    body = text[body_start : body_start + 800]
    if re.search(r"\[Placeholder", body):
        return (False, f"\\section{{{section_name}}} body still placeholder")
    if len(body.strip()) < 100:
        return (False, f"\\section{{{section_name}}} body too short")
    return (True, f"\\section{{{section_name}}} present with content")


# ---------------------------------------------------------------------
# C8: Broader Impact section present and non-placeholder
# ---------------------------------------------------------------------
def _check_c8() -> tuple[bool, str]:
    text = _read_main_tex()
    if text is None:
        return (False, "main.tex not found")
    return _has_real_section(text, "Broader Impact")


# ---------------------------------------------------------------------
# C11: Ethics statement present (TMLR requires for attack papers)
# ---------------------------------------------------------------------
def _check_c11() -> tuple[bool, str]:
    text = _read_main_tex()
    if text is None:
        return (False, "main.tex not found")
    return _has_real_section(text, "Ethics Statement")


# ---------------------------------------------------------------------
# C10: self-citation rate <= 30%
# ---------------------------------------------------------------------
def _check_c10() -> tuple[bool, str]:
    text = _read_main_tex()
    bib  = _read_refs_bib()
    if text is None:
        return (False, "main.tex not found")
    if bib is None:
        return (False, "refs.bib not found")
    bib_keys = set(re.findall(r"@\w+\s*\{\s*([^,\s]+)\s*,", bib))
    # collect all cite keys
    cited = []
    for cmd in ("cite", "citet", "citep", "citealp"):
        for m in re.finditer(rf"\\{cmd}\{{([^}}]+)\}}", text):
            for k in m.group(1).split(","):
                cited.append(k.strip())
    if not cited:
        return (False, "no citations found")
    # self-cite heuristic: any cite key containing 'liu' or '2026' or matching bib author 'Liu'
    self_cite = sum(1 for c in cited if "liu" in c.lower())
    rate = self_cite / len(cited)
    if rate > 0.30:
        return (False, f"self-cite rate {rate:.2%} > 30% ({self_cite}/{len(cited)})")
    return (True, f"self-cite rate {rate:.2%} ({self_cite}/{len(cited)} self-cited)")


# ---------------------------------------------------------------------
# C12: code reproducibility link present (look for GitHub URL or .py file mention)
# ---------------------------------------------------------------------
def _check_c12() -> tuple[bool, str]:
    text = _read_main_tex()
    if text is None:
        return (False, "main.tex not found")
    # accept either a github/gitlab URL or a code-artifact filename
    if re.search(r"github\.com|gitlab\.com|\.py|\.zip", text):
        return (True, "code artifact reference found")
    return (False, "no GitHub URL or .py/.zip reference found")


# ---------------------------------------------------------------------
# Check registry (W3: C1-C8 + C10-C12 implemented; C9 stubbed)
# ---------------------------------------------------------------------
CHECKS = {
    "C1":  ("main.tex exists and uses tmlr documentclass",        _check_c1),
    "C2":  ("main.tex has 7+ sections (TMLR format)",              _check_c2),
    "C3":  ("main.tex parses (balanced braces + document env)",    _check_c3),
    "C4":  ("refs.bib has >= 10 entries",                          _check_c4),
    "C5":  ("abstract <= 250 words",                              _check_c5),
    "C6":  ("no verbatim TODO/FIXME/XXX markers in main.tex",     _check_c6),
    "C7":  ("all \\cite keys resolve to refs.bib entries",        _check_c7),
    "C8":  ("Broader Impact section present (TMLR mandatory)",    _check_c8),
    "C9":  ("figure captions present (placeholder for W5)",       _stub),
    "C10": ("self-citation rate <= 30%",                           _check_c10),
    "C11": ("Ethics Statement section present",                    _check_c11),
    "C12": ("code reproducibility link present",                   _check_c12),
}


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="verify_p6")
    parser.add_argument("--dry-run", action="store_true", help="show checks without running")
    parser.add_argument("--skip", nargs="+", default=[], help="check ids to skip")
    args = parser.parse_args(argv)

    PAPER6_DIR = Path(__file__).parent.resolve()
    main_tex = PAPER6_DIR / "main.tex"

    print(f"=== verify_p6.py ===")
    print(f"PAPER6 dir: {PAPER6_DIR}")
    print(f"main.tex exists: {main_tex.exists()}")
    print(f"main.tex size: {main_tex.stat().st_size if main_tex.exists() else 0} bytes")
    print()

    if not main_tex.exists():
        print("ERROR: main.tex not found. Run from PAPER6_CONSOLIDATED/.")
        return 2

    print(f"Registered checks: {len(CHECKS)}")
    print(f"W3 status: C1-C8 + C10-C12 implemented; C9 stubbed.")
    print()

    passed = 0
    failed = 0
    skipped = 0
    notrun = 0

    for cid, (desc, fn) in CHECKS.items():
        if cid in args.skip:
            print(f"  [SKIP] {cid}: {desc}")
            skipped += 1
            continue
        if args.dry_run:
            print(f"  [DRY ] {cid}: {desc}")
            continue
        ok, msg = fn()
        if msg.startswith("W1 stub"):
            print(f"  [----] {cid}: {desc}  ({msg})")
            notrun += 1
        elif ok:
            print(f"  [PASS] {cid}: {desc}")
            passed += 1
        else:
            print(f"  [FAIL] {cid}: {desc}  ({msg})")
            failed += 1

    print()
    print(f"=== Summary: PASS={passed}  FAIL={failed}  SKIP={skipped}  STUB={notrun} ===")

    # W1.5: return 0 if all real checks pass (stubs are warnings, not failures)
    if failed > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())